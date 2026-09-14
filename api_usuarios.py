"""
API de USUARIOS / ROLES / PERMISOS + login.

Se registra en `servidor.py` como Blueprint. La sesión va en una cookie firmada de Flask
(`session`), así el permiso se resuelve en el servidor: el frontend puede OCULTAR botones,
pero quien decide es el backend. Ocultar no es proteger.
"""
import functools
import os
import time

from flask import Blueprint, g, has_request_context, jsonify, request, session

import auth
import db

bp = Blueprint("usuarios", __name__)


# ── Sesión / guardas ─────────────────────────────────────────────────────────
def usuario_actual():
    """Quién está logueado, con sus roles y permisos. **Una vez por request.**

    Son TRES consultas (el usuario, sus roles, sus permisos) y cada una abre su propia conexión.
    Se lo pregunta el guardia de `servidor.py` para toda la API, y después casi cada endpoint lo
    vuelve a pedir para saber de quién es el molde: eran 6 a 9 conexiones por request sólo para
    saber quién sos. La memoria va con la CLAVE del usuario de la sesión, así un login o un
    logout en el medio no devuelve al de antes.

    Sigue leyendo `activo` de la base en cada request: desactivar a alguien lo saca al toque."""
    uid = session.get("uid")
    if not uid:
        return None
    if has_request_context():
        _memo = getattr(g, "_usuario_memo", None)
        if _memo is not None and _memo[0] == uid:
            return _memo[1]
    u = db.fila("SELECT id, usuario, nombre, activo FROM usuario WHERE id=?", uid)
    if not u or not u["activo"]:
        return None
    yo = {"id": u["id"], "usuario": u["usuario"], "nombre": u["nombre"],
          "roles": auth.roles_de(uid), "permisos": auth.permisos_de(uid)}
    if has_request_context():
        g._usuario_memo = (uid, yo)
    return yo


def _olvidar_usuario_memo():
    """Después de tocar los roles/permisos de alguien, lo de la mano ya no sirve."""
    if has_request_context():
        try:
            g.pop("_usuario_memo", None)
        except Exception:
            pass


def requiere(*permisos):
    """Guarda de endpoint: 401 si no hay sesión, 403 si le falta el permiso."""
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **kw):
            u = usuario_actual()
            if not u:
                return jsonify({"error": "no hay sesión iniciada"}), 401
            if permisos and not any(p in u["permisos"] for p in permisos):
                return jsonify({"error": f"te falta el permiso: {' o '.join(permisos)}"}), 403
            return fn(*a, **kw)
        return wrap
    return deco


# ── Login ────────────────────────────────────────────────────────────────────
# 🔴 FRENO A LA FUERZA BRUTA. No había ninguno: se podían probar contraseñas todo lo rápido que
# aguantara la red, y este endpoint va a estar expuesto a internet. Se cuenta por usuario Y por
# dirección de origen; tras `_INTENTOS_MAX` fallidos seguidos hay que esperar `_ESPERA_SEG`. Un
# login bueno borra la cuenta. Vive en memoria a propósito: con varios servidores cada uno frena
# lo suyo, que es suficiente para el ataque que importa (uno solo probando en serie).
_FALLOS = {}                 # clave → [cuántos, cuándo fue el último]
_INTENTOS_MAX = int(os.environ.get("TIZADA_LOGIN_INTENTOS") or 8)
_ESPERA_SEG = int(os.environ.get("TIZADA_LOGIN_ESPERA") or 60)


def _claves_intento(usuario):
    return (f"u:{(usuario or '').lower()}", f"ip:{request.remote_addr or '?'}")


def _frenado(usuario):
    """Segundos que faltan para poder volver a probar (0 = se puede)."""
    ahora = time.time()
    falta = 0
    for k in _claves_intento(usuario):
        n, ult = _FALLOS.get(k, (0, 0))
        if n >= _INTENTOS_MAX:
            resto = _ESPERA_SEG - (ahora - ult)
            if resto > 0:
                falta = max(falta, int(resto) + 1)
            else:
                _FALLOS.pop(k, None)          # cumplió la espera: se le da otra ronda
    return falta


def _anotar_fallo(usuario):
    ahora = time.time()
    for k in _claves_intento(usuario):
        n, ult = _FALLOS.get(k, (0, 0))
        if ahora - ult > _ESPERA_SEG * 5:     # hace rato que no falla: se empieza de nuevo
            n = 0
        _FALLOS[k] = (n + 1, ahora)
    if len(_FALLOS) > 5000:                   # que no crezca sin fin
        _FALLOS.clear()


def _limpiar_fallos(usuario):
    for k in _claves_intento(usuario):
        _FALLOS.pop(k, None)


@bp.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    _usr = (d.get("usuario") or "").strip()
    _espera = _frenado(_usr)
    if _espera:
        return jsonify({"error": f"demasiados intentos. Probá de nuevo en {_espera} segundos.",
                        "espera": _espera}), 429
    try:
        u = auth.autenticar(_usr, d.get("password") or "")
    except Exception as e:   # la base caída no es «usuario o contraseña incorrectos»
        return jsonify({"error": "no hay conexión con la base de datos del sistema",
                        "base": False, "detalle": str(e)[:200]}), 503
    if not u:
        _anotar_fallo(_usr)
        return jsonify({"error": "usuario o contraseña incorrectos"}), 401
    _limpiar_fallos(_usr)
    session["uid"] = u["id"]
    session.permanent = True
    return jsonify({"ok": True, "usuario": u})


@bp.post("/api/auth/logout")
def logout():
    session.pop("uid", None)
    return jsonify({"ok": True})


@bp.get("/api/auth/yo")
def yo():
    """Quién soy y qué puedo. El front lo usa para pintar la UI (ocultar ≠ proteger).

    ⚠️ Si la BASE no responde hay que decirlo con todas las letras (**503 + `base: false`**). Antes
    salía un 500 con el traceback de Flask: el front no lo podía leer como JSON, se iba al `catch`
    y concluía «este sistema no tiene usuarios» — entraba igual y después todo daba 401."""
    try:
        u = usuario_actual()
        if u is None:
            # SIN SESIÓN `usuario_actual` corta antes de tocar la base, así que no alcanza para
            # afirmar que la base está viva: se comprueba. Si no, el front vería «no hay sesión»
            # (login) cuando en realidad no hay CONTRA QUÉ validar.
            db.valor("SELECT 1")
    except Exception as e:
        return jsonify({"ok": False, "usuario": None, "base": False,
                        "error": "no hay conexión con la base de datos del sistema",
                        "detalle": str(e)[:200]}), 503
    return jsonify({"ok": bool(u), "usuario": u, "base": True})


@bp.post("/api/auth/password")
def cambiar_mi_password():
    u = usuario_actual()
    if not u:
        return jsonify({"error": "no hay sesión iniciada"}), 401
    d = request.get_json(silent=True) or {}
    actual, nueva = d.get("actual") or "", d.get("nueva") or ""
    if len(nueva) < 8:
        return jsonify({"error": "la contraseña nueva tiene que tener al menos 8 caracteres"}), 400
    if not auth.autenticar(u["usuario"], actual):
        return jsonify({"error": "la contraseña actual no es correcta"}), 403
    h, salt = auth.hashear(nueva)
    db.ejecutar("UPDATE usuario SET password_hash=?, password_salt=?, modificado_en=SYSUTCDATETIME(), "
                "modificado_por=? WHERE id=?", h, salt, u["id"], u["id"])
    return jsonify({"ok": True})


# ── Usuarios ─────────────────────────────────────────────────────────────────
@bp.get("/api/usuarios")
@requiere("usuario.ver", "usuario.gestionar")
def listar_usuarios():
    us = db.filas("SELECT id, usuario, nombre, email, activo, creado_en, ultimo_acceso "
                  "FROM usuario ORDER BY usuario")
    for u in us:
        u["roles"] = auth.roles_de(u["id"])
        u["creado_en"] = str(u["creado_en"] or "")
        u["ultimo_acceso"] = str(u["ultimo_acceso"] or "")
        u["activo"] = bool(u["activo"])
    return jsonify({"ok": True, "usuarios": us})


@bp.post("/api/usuarios")
@requiere("usuario.gestionar")
def crear_usuario_api():
    d = request.get_json(silent=True) or {}
    if len((d.get("password") or "")) < 8:
        return jsonify({"error": "la contraseña tiene que tener al menos 8 caracteres"}), 400
    try:
        uid = auth.crear_usuario((d.get("usuario") or "").strip(), (d.get("nombre") or "").strip(),
                                 d.get("password"), roles=d.get("roles") or [],
                                 email=(d.get("email") or "").strip() or None,
                                 por=usuario_actual()["id"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True, "id": uid})


@bp.put("/api/usuarios/<int:uid>")
@requiere("usuario.gestionar")
def editar_usuario(uid):
    d = request.get_json(silent=True) or {}
    yo_ = usuario_actual()
    if not db.valor("SELECT COUNT(*) FROM usuario WHERE id=?", uid):
        return jsonify({"error": "no existe el usuario"}), 404
    # No dejar que alguien se desactive a sí mismo ni se saque el último admin: el sistema
    # quedaría sin nadie que pueda gestionar permisos y habría que arreglarlo a mano en la base.
    if uid == yo_["id"] and d.get("activo") is False:
        return jsonify({"error": "no podés desactivarte a vos mismo"}), 400
    if "roles" in d and _seria_el_ultimo_admin(uid, d.get("roles") or []):
        return jsonify({"error": "no podés dejar el sistema sin ningún administrador activo"}), 400

    if d.get("password") and len(d["password"]) < 8:
        return jsonify({"error": "la contraseña tiene que tener al menos 8 caracteres"}), 400
    # El hasheo (260k iteraciones) va FUERA de la transacción: no se tienen tomados locks de la
    # base durante ~200 ms de CPU.
    _pw = auth.hashear(d["password"]) if d.get("password") else None
    # 🔴 TODO EL CAMBIO EN UNA TRANSACCIÓN. Antes eran varias sueltas: el `DELETE` de los roles se
    # confirmaba y recién después se asignaban de a uno, así que una clave de rol inexistente
    # devolvía 400 **con el usuario ya sin ningún rol** (y si era el último admin, nadie podía
    # volver a entrar a arreglarlo).
    try:
        with db.cursor() as cur:
            rids = auth.ids_de_roles(cur, d["roles"]) if "roles" in d else None   # valida primero
            if "nombre" in d or "email" in d or "activo" in d:
                cur.execute("UPDATE usuario SET nombre=COALESCE(?,nombre), email=COALESCE(?,email), "
                            "activo=COALESCE(?,activo), modificado_en=SYSUTCDATETIME(), modificado_por=? "
                            "WHERE id=?",
                            (d.get("nombre") or "").strip() or None,
                            (d.get("email") or "").strip() or None,
                            None if d.get("activo") is None else (1 if d["activo"] else 0),
                            yo_["id"], uid)
            if _pw:
                cur.execute("UPDATE usuario SET password_hash=?, password_salt=? WHERE id=?",
                            _pw[0], _pw[1], uid)
            if rids is not None:
                cur.execute("DELETE FROM usuario_rol WHERE usuario_id=?", uid)
                for rid in rids:
                    cur.execute("INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (?,?)", uid, rid)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400          # nada se escribió: la transacción se deshizo
    _olvidar_usuario_memo()      # si me edité a mí mismo, lo que tengo en la mano ya no vale
    return jsonify({"ok": True})


@bp.delete("/api/usuarios/<int:uid>")
@requiere("usuario.gestionar")
def borrar_usuario(uid):
    yo_ = usuario_actual()
    if uid == yo_["id"]:
        return jsonify({"error": "no podés borrarte a vos mismo"}), 400
    if _seria_el_ultimo_admin(uid, []):
        return jsonify({"error": "no podés dejar el sistema sin ningún administrador activo"}), 400
    # 🔴 SE DESACTIVA, NO SE BORRA LA FILA. Dos razones, y las dos importan:
    #   · `DELETE FROM usuario` **REVENTABA** con error 547 para cualquiera que hubiera subido un
    #     molde: `producto.creado_por` (y `diseno`/`pedido`/`trabajo`) apuntan al usuario y no
    #     tienen ON DELETE. Salía como un 500 con el mensaje crudo de SQL Server.
    #   · `creado_por` es AUTORÍA (ver §8): borrar la fila la destruye, y con ella el rastro de
    #     quién dio de alta cada molde.
    # Desactivado NO puede entrar (`usuario_actual` mira `activo` en CADA request) y pierde todos
    # sus roles, que es lo que el administrador quería lograr.
    with db.cursor() as cur:
        cur.execute("DELETE FROM usuario_rol WHERE usuario_id=?", uid)
        cur.execute("UPDATE usuario SET activo=0, modificado_en=SYSUTCDATETIME(), modificado_por=? "
                    "WHERE id=?", yo_["id"], uid)
    return jsonify({"ok": True, "desactivado": True})


def _seria_el_ultimo_admin(uid, roles_nuevos):
    """¿Sacarle el admin a este usuario deja al sistema sin ninguno activo?"""
    if "admin" in (roles_nuevos or []):
        return False
    return db.valor(
        "SELECT COUNT(*) FROM usuario_rol ur JOIN rol r ON r.id=ur.rol_id "
        "JOIN usuario u ON u.id=ur.usuario_id "
        "WHERE r.clave='admin' AND u.activo=1 AND u.id<>?", uid) == 0


# ── Roles y permisos ─────────────────────────────────────────────────────────
@bp.get("/api/roles")
@requiere("usuario.ver", "usuario.gestionar")
def listar_roles():
    rs = db.filas("SELECT id, clave, nombre, descripcion, es_sistema FROM rol ORDER BY id")
    for r in rs:
        r["es_sistema"] = bool(r["es_sistema"])
        r["permisos"] = [x["clave"] for x in db.filas(
            "SELECT p.clave FROM permiso p JOIN rol_permiso rp ON rp.permiso_id=p.id "
            "WHERE rp.rol_id=? ORDER BY p.clave", r["id"])]
        r["usuarios"] = db.valor("SELECT COUNT(*) FROM usuario_rol WHERE rol_id=?", r["id"])
    return jsonify({"ok": True, "roles": rs})


@bp.get("/api/permisos")
@requiere("usuario.ver", "usuario.gestionar")
def listar_permisos():
    return jsonify({"ok": True, "permisos": db.filas(
        "SELECT id, clave, modulo, nombre, descripcion FROM permiso ORDER BY modulo, clave")})


@bp.post("/api/roles")
@requiere("usuario.gestionar")
def crear_rol():
    d = request.get_json(silent=True) or {}
    clave = (d.get("clave") or "").strip().lower().replace(" ", "_")
    if not clave:
        return jsonify({"error": "falta la clave del rol"}), 400
    # El rol y sus permisos, en UNA transacción: un rol creado sin permisos no le sirve a nadie
    # y encima parece configurado.
    with db.cursor() as cur:
        cur.execute("SELECT id FROM rol WHERE clave=?", clave)
        if cur.fetchone() is not None:
            return jsonify({"error": f"ya existe un rol '{clave}'"}), 400
        cur.execute("INSERT INTO rol (clave, nombre, descripcion) OUTPUT INSERTED.id VALUES (?,?,?)",
                    clave, (d.get("nombre") or clave).strip(),
                    (d.get("descripcion") or "").strip() or None)
        rid = int(cur.fetchone()[0])
        _set_permisos(rid, d.get("permisos") or [], cur)
    return jsonify({"ok": True, "id": rid})


@bp.put("/api/roles/<int:rid>")
@requiere("usuario.gestionar")
def editar_rol(rid):
    d = request.get_json(silent=True) or {}
    r = db.fila("SELECT id, clave, es_sistema FROM rol WHERE id=?", rid)
    if not r:
        return jsonify({"error": "no existe el rol"}), 404
    # Al rol de sistema (admin) se le puede cambiar el texto, pero NO los permisos: si se le
    # sacan, nadie puede volver a dárselos y el sistema queda trabado.
    if r["es_sistema"] and "permisos" in d:
        return jsonify({"error": "el rol de sistema no puede cambiar sus permisos"}), 400
    with db.cursor() as cur:          # el texto y los permisos, juntos
        if "nombre" in d or "descripcion" in d:
            cur.execute("UPDATE rol SET nombre=COALESCE(?,nombre), descripcion=? WHERE id=?",
                        (d.get("nombre") or "").strip() or None,
                        (d.get("descripcion") or "").strip() or None, rid)
        if "permisos" in d:
            _set_permisos(rid, d["permisos"], cur)
    _olvidar_usuario_memo()      # los permisos que tengo en la mano pueden ser los de este rol
    return jsonify({"ok": True})


@bp.delete("/api/roles/<int:rid>")
@requiere("usuario.gestionar")
def borrar_rol(rid):
    r = db.fila("SELECT id, es_sistema FROM rol WHERE id=?", rid)
    if not r:
        return jsonify({"error": "no existe el rol"}), 404
    if r["es_sistema"]:
        return jsonify({"error": "el rol de sistema no se puede borrar"}), 400
    n = db.valor("SELECT COUNT(*) FROM usuario_rol WHERE rol_id=?", rid)
    if n:
        return jsonify({"error": f"el rol está asignado a {n} usuario/s: sacáselo primero"}), 400
    db.ejecutar("DELETE FROM rol WHERE id=?", rid)
    return jsonify({"ok": True})


def _set_permisos(rid, claves, cur=None):
    """Deja el rol con EXACTAMENTE esos permisos, en UNA transacción.

    🔴 Antes el `DELETE` se confirmaba solo y después se insertaban de a uno: si algo fallaba en el
    medio (o el proceso se moría), el rol quedaba **sin ningún permiso**, guardado y sin aviso —
    o sea, todos los que lo tenían perdían el acceso de golpe."""
    if cur is None:
        with db.cursor() as c2:
            return _set_permisos(rid, claves, c2)
    cur.execute("DELETE FROM rol_permiso WHERE rol_id=?", rid)
    for c in claves or []:
        cur.execute("SELECT id FROM permiso WHERE clave=?", c)
        r = cur.fetchone()
        if r:
            cur.execute("INSERT INTO rol_permiso (rol_id, permiso_id) VALUES (?,?)", rid, int(r[0]))
