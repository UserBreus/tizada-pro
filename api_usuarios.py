"""
API de USUARIOS / ROLES / PERMISOS + login.

Se registra en `servidor.py` como Blueprint. La sesión va en una cookie firmada de Flask
(`session`), así el permiso se resuelve en el servidor: el frontend puede OCULTAR botones,
pero quien decide es el backend. Ocultar no es proteger.
"""
import functools

from flask import Blueprint, jsonify, request, session

import auth
import db

bp = Blueprint("usuarios", __name__)


# ── Sesión / guardas ─────────────────────────────────────────────────────────
def usuario_actual():
    uid = session.get("uid")
    if not uid:
        return None
    u = db.fila("SELECT id, usuario, nombre, activo FROM usuario WHERE id=?", uid)
    if not u or not u["activo"]:
        return None
    return {"id": u["id"], "usuario": u["usuario"], "nombre": u["nombre"],
            "roles": auth.roles_de(uid), "permisos": auth.permisos_de(uid)}


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
@bp.post("/api/auth/login")
def login():
    d = request.get_json(silent=True) or {}
    u = auth.autenticar((d.get("usuario") or "").strip(), d.get("password") or "")
    if not u:
        return jsonify({"error": "usuario o contraseña incorrectos"}), 401
    session["uid"] = u["id"]
    session.permanent = True
    return jsonify({"ok": True, "usuario": u})


@bp.post("/api/auth/logout")
def logout():
    session.pop("uid", None)
    return jsonify({"ok": True})


@bp.get("/api/auth/yo")
def yo():
    """Quién soy y qué puedo. El front lo usa para pintar la UI (ocultar ≠ proteger)."""
    u = usuario_actual()
    return jsonify({"ok": bool(u), "usuario": u})


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

    if "nombre" in d or "email" in d or "activo" in d:
        db.ejecutar("UPDATE usuario SET nombre=COALESCE(?,nombre), email=COALESCE(?,email), "
                    "activo=COALESCE(?,activo), modificado_en=SYSUTCDATETIME(), modificado_por=? WHERE id=?",
                    (d.get("nombre") or "").strip() or None, (d.get("email") or "").strip() or None,
                    None if d.get("activo") is None else (1 if d["activo"] else 0), yo_["id"], uid)
    if d.get("password"):
        if len(d["password"]) < 8:
            return jsonify({"error": "la contraseña tiene que tener al menos 8 caracteres"}), 400
        h, salt = auth.hashear(d["password"])
        db.ejecutar("UPDATE usuario SET password_hash=?, password_salt=? WHERE id=?", h, salt, uid)
    if "roles" in d:
        db.ejecutar("DELETE FROM usuario_rol WHERE usuario_id=?", uid)
        for r in d["roles"]:
            try:
                auth.asignar_rol(uid, r)
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
    return jsonify({"ok": True})


@bp.delete("/api/usuarios/<int:uid>")
@requiere("usuario.gestionar")
def borrar_usuario(uid):
    yo_ = usuario_actual()
    if uid == yo_["id"]:
        return jsonify({"error": "no podés borrarte a vos mismo"}), 400
    if _seria_el_ultimo_admin(uid, []):
        return jsonify({"error": "no podés dejar el sistema sin ningún administrador activo"}), 400
    db.ejecutar("DELETE FROM usuario WHERE id=?", uid)
    return jsonify({"ok": True})


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
    if db.valor("SELECT id FROM rol WHERE clave=?", clave) is not None:
        return jsonify({"error": f"ya existe un rol '{clave}'"}), 400
    rid = db.insertar("INSERT INTO rol (clave, nombre, descripcion) VALUES (?,?,?)",
                      clave, (d.get("nombre") or clave).strip(), (d.get("descripcion") or "").strip() or None)
    _set_permisos(rid, d.get("permisos") or [])
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
    if "nombre" in d or "descripcion" in d:
        db.ejecutar("UPDATE rol SET nombre=COALESCE(?,nombre), descripcion=? WHERE id=?",
                    (d.get("nombre") or "").strip() or None, (d.get("descripcion") or "").strip() or None, rid)
    if "permisos" in d:
        _set_permisos(rid, d["permisos"])
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


def _set_permisos(rid, claves):
    db.ejecutar("DELETE FROM rol_permiso WHERE rol_id=?", rid)
    for c in claves or []:
        pid = db.valor("SELECT id FROM permiso WHERE clave=?", c)
        if pid:
            db.ejecutar("INSERT INTO rol_permiso (rol_id, permiso_id) VALUES (?,?)", rid, pid)
