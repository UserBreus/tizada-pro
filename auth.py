"""
USUARIOS / ROLES / PERMISOS — TIZADA PRO.

Los permisos son POR ACCIÓN (`pedido.crear`, `molde.editar`), NO por pantalla: las pantallas
cambian todo el tiempo, las acciones no. Atarlos a pantallas rompe los permisos en cada rediseño.

Contraseñas: PBKDF2-HMAC-SHA256 con salt por usuario. NUNCA en texto plano, nunca reversibles.
"""
import hashlib
import os
import secrets

import db

ITERACIONES = 260_000   # costo del PBKDF2 (frena la fuerza bruta si se filtra la base)

# ── CATÁLOGO DE PERMISOS (la fuente de verdad; el seed los sincroniza) ────────
PERMISOS = [
    ("pedido.ver",       "pedido",  "Ver pedidos",                 "Entrar al Panel de Pedidos y ver los pedidos."),
    ("pedido.crear",     "pedido",  "Crear pedidos",               "Armar un pedido nuevo y cargar la planilla."),
    ("pedido.generar",   "pedido",  "Generar tizadas",             "Enviar la planilla y generar las tizadas."),
    ("pedido.descargar", "pedido",  "Descargar tizadas",           "Bajar los PDF de las mesas generadas."),
    ("molde.ver",        "molde",   "Ver moldes",                  "Ver la moldería y sus piezas."),
    ("molde.crear",      "molde",   "Crear moldes",                "Dar de alta un molde nuevo (.ai/.pdf/.dxf)."),
    ("molde.editar",     "molde",   "Editar moldes",               "Nombrar piezas, variables, grupos, telas."),
    ("molde.borrar",     "molde",   "Borrar moldes",               "Eliminar un molde del catálogo."),
    ("arte.cargar",      "arte",    "Cargar arte",                 "Subir el arte de un diseño y mapearlo."),
    ("arte.editar",      "arte",    "Editar objetos editables",    "Mover/rotar/escalar los editables del arte."),
    ("config.ver",       "config",  "Ver configuración",           "Entrar al Panel de Configuración."),
    ("config.editar",    "config",  "Editar configuración",        "Nesting, perfil de color, reglas de planilla."),
    ("fuente.ver",       "config",  "Ver catálogo de fuentes",     "Ver las tipografías registradas."),
    ("fuente.gestionar", "config",  "Gestionar fuentes",           "Subir y eliminar tipografías del catálogo."),
    ("usuario.ver",      "usuario", "Ver usuarios",                "Ver usuarios, roles y permisos."),
    ("usuario.gestionar","usuario", "Gestionar usuarios y roles",  "Crear/editar usuarios, roles y sus permisos."),
]

# Roles propuestos por defecto (el usuario los puede editar/borrar desde la pantalla).
# `admin` es de SISTEMA: no se borra, para no quedarse sin quién gestione permisos.
ROLES_DEFAULT = [
    ("admin", "Administrador", "Acceso total al sistema.", True, [p[0] for p in PERMISOS]),
    ("operario", "Operario", "Hace pedidos y genera tizadas. No configura el sistema.", False,
     ["pedido.ver", "pedido.crear", "pedido.generar", "pedido.descargar", "molde.ver"]),
    ("disenador", "Diseñador", "Configura moldes, artes y el sistema. También puede hacer pedidos.", False,
     ["pedido.ver", "pedido.crear", "pedido.generar", "pedido.descargar",
      "molde.ver", "molde.crear", "molde.editar", "arte.cargar", "arte.editar",
      "config.ver", "config.editar", "fuente.ver", "fuente.gestionar"]),
]


# ── Contraseñas ──────────────────────────────────────────────────────────────
def hashear(password, salt=None):
    salt = salt or secrets.token_bytes(32)
    h = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, ITERACIONES)
    return h, salt


def verificar_password(password, hash_guardado, salt):
    h, _ = hashear(password, bytes(salt))
    # compare_digest: comparación en tiempo constante (una comparación normal filtra el hash
    # por el tiempo que tarda en fallar).
    return secrets.compare_digest(h, bytes(hash_guardado))


# ── Seed ─────────────────────────────────────────────────────────────────────
def sincronizar_permisos():
    """Deja en la base EXACTAMENTE los permisos del catálogo (agrega los nuevos, actualiza textos).
    No borra los que ya no están: podrían estar asignados; se limpian a mano si hace falta."""
    n = 0
    for clave, modulo, nombre, desc in PERMISOS:
        if db.valor("SELECT id FROM permiso WHERE clave=?", clave) is None:
            db.insertar("INSERT INTO permiso (clave, modulo, nombre, descripcion) VALUES (?,?,?,?)",
                        clave, modulo, nombre, desc)
            n += 1
        else:
            db.ejecutar("UPDATE permiso SET modulo=?, nombre=?, descripcion=? WHERE clave=?",
                        modulo, nombre, desc, clave)
    return n


def sincronizar_roles():
    """Crea los roles por defecto SI NO EXISTEN. No pisa los permisos de un rol ya creado:
    si el usuario los editó desde la pantalla, mandan los suyos."""
    n = 0
    for clave, nombre, desc, sistema, permisos in ROLES_DEFAULT:
        rid = db.valor("SELECT id FROM rol WHERE clave=?", clave)
        if rid is not None:
            continue
        rid = db.insertar("INSERT INTO rol (clave, nombre, descripcion, es_sistema) VALUES (?,?,?,?)",
                          clave, nombre, desc, 1 if sistema else 0)
        for p in permisos:
            pid = db.valor("SELECT id FROM permiso WHERE clave=?", p)
            if pid:
                db.ejecutar("INSERT INTO rol_permiso (rol_id, permiso_id) VALUES (?,?)", rid, pid)
        n += 1
    return n


def crear_usuario(usuario, nombre, password, roles=None, email=None, por=None):
    if not usuario or not password:
        raise ValueError("usuario y contraseña son obligatorios")
    if db.valor("SELECT id FROM usuario WHERE usuario=?", usuario) is not None:
        raise ValueError(f"ya existe un usuario '{usuario}'")
    h, salt = hashear(password)
    uid = db.insertar(
        "INSERT INTO usuario (usuario, nombre, email, password_hash, password_salt, creado_por) "
        "VALUES (?,?,?,?,?,?)", usuario, nombre or usuario, email, h, salt, por)
    for r in (roles or []):
        asignar_rol(uid, r)
    return uid


def asignar_rol(usuario_id, rol_clave):
    rid = db.valor("SELECT id FROM rol WHERE clave=?", rol_clave)
    if rid is None:
        raise ValueError(f"no existe el rol '{rol_clave}'")
    if db.valor("SELECT COUNT(*) FROM usuario_rol WHERE usuario_id=? AND rol_id=?", usuario_id, rid):
        return False
    db.ejecutar("INSERT INTO usuario_rol (usuario_id, rol_id) VALUES (?,?)", usuario_id, rid)
    return True


def autenticar(usuario, password):
    """Devuelve el usuario (dict) o None. No distingue 'no existe' de 'clave mal': decirlo
    permite enumerar usuarios válidos."""
    u = db.fila("SELECT id, usuario, nombre, password_hash, password_salt, activo FROM usuario WHERE usuario=?",
                usuario)
    if not u or not u["activo"]:
        return None
    if not verificar_password(password, u["password_hash"], u["password_salt"]):
        return None
    db.ejecutar("UPDATE usuario SET ultimo_acceso=SYSUTCDATETIME() WHERE id=?", u["id"])
    return {"id": u["id"], "usuario": u["usuario"], "nombre": u["nombre"],
            "permisos": permisos_de(u["id"]), "roles": roles_de(u["id"])}


def permisos_de(usuario_id):
    return [r["clave"] for r in db.filas(
        "SELECT DISTINCT p.clave FROM permiso p "
        "JOIN rol_permiso rp ON rp.permiso_id=p.id "
        "JOIN usuario_rol ur ON ur.rol_id=rp.rol_id "
        "WHERE ur.usuario_id=? ORDER BY p.clave", usuario_id)]


def roles_de(usuario_id):
    return [r["clave"] for r in db.filas(
        "SELECT r.clave FROM rol r JOIN usuario_rol ur ON ur.rol_id=r.id "
        "WHERE ur.usuario_id=? ORDER BY r.clave", usuario_id)]


def tiene_permiso(usuario_id, clave):
    return db.valor(
        "SELECT COUNT(*) FROM permiso p "
        "JOIN rol_permiso rp ON rp.permiso_id=p.id "
        "JOIN usuario_rol ur ON ur.rol_id=rp.rol_id "
        "WHERE ur.usuario_id=? AND p.clave=?", usuario_id, clave) > 0


def bootstrap(admin_pass=None):
    """Deja el sistema utilizable: permisos + roles + un admin.
    Devuelve (permisos_nuevos, roles_nuevos, password_del_admin_o_None)."""
    np_ = sincronizar_permisos()
    nr = sincronizar_roles()
    pw = None
    if db.valor("SELECT COUNT(*) FROM usuario") == 0:
        # Si no se pasa contraseña se genera una al azar y se MUESTRA una sola vez:
        # un admin/admin por defecto es una puerta abierta en producción.
        pw = admin_pass or secrets.token_urlsafe(12)
        crear_usuario("admin", "Administrador", pw, roles=["admin"])
    return np_, nr, pw
