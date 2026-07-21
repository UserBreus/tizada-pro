"""
CAPA DE ACCESO A LA BASE (MSSQL) — TIZADA PRO.

`servidor.py` y `motor_pedido.py` NO deben hablar SQL directo: todo pasa por acá.

Conexión por ENV (nunca credenciales en el código):
    TIZADA_DB_SERVER   (default: localhost\\SQLEXPRESS  — el SQL Server Express ya instalado)
    TIZADA_DB_NAME     (default: TizadaPro)
    TIZADA_DB_DRIVER   (default: el ODBC Driver de SQL Server más nuevo que haya)
    TIZADA_DB_USER / TIZADA_DB_PASSWORD  (si no están → autenticación de Windows)
"""
import os
import contextlib

import pyodbc

DB_SERVER = os.environ.get("TIZADA_DB_SERVER") or r"localhost\SQLEXPRESS"
DB_NAME = os.environ.get("TIZADA_DB_NAME") or "TizadaPro"
DB_USER = os.environ.get("TIZADA_DB_USER")
DB_PASSWORD = os.environ.get("TIZADA_DB_PASSWORD")


def driver_disponible():
    """El ODBC Driver de SQL Server más NUEVO instalado (18 > 17 > …).

    Se elige en runtime a propósito: fijar '18' rompe en una máquina que sólo tiene el 17
    (es el caso de esta: tiene el 17). El error de un driver ausente es feo y tardío.
    """
    forzado = os.environ.get("TIZADA_DB_DRIVER")
    if forzado:
        return forzado
    cands = [d for d in pyodbc.drivers() if "ODBC Driver" in d and "SQL Server" in d]
    if cands:
        def _ver(d):
            try:
                return int("".join(c for c in d if c.isdigit()) or 0)
            except ValueError:
                return 0
        return sorted(cands, key=_ver, reverse=True)[0]
    if "SQL Server" in pyodbc.drivers():
        return "SQL Server"
    raise RuntimeError(
        "No hay ningún driver ODBC de SQL Server instalado. Instalá 'ODBC Driver 18 for SQL Server'."
    )


def _cadena(base=None):
    p = [f"DRIVER={{{driver_disponible()}}}", f"SERVER={DB_SERVER}"]
    if base:
        p.append(f"DATABASE={base}")
    if DB_USER:
        p += [f"UID={DB_USER}", f"PWD={DB_PASSWORD or ''}"]
    else:
        p.append("Trusted_Connection=yes")   # autenticación de Windows
    # El driver 18 exige cifrado y, con SQL Express local, el certificado es autofirmado.
    p.append("TrustServerCertificate=yes")
    return ";".join(p) + ";"


def conectar(base=DB_NAME, autocommit=False):
    return pyodbc.connect(_cadena(base), autocommit=autocommit, timeout=10)


@contextlib.contextmanager
def cursor(commit=True):
    """Cursor con transacción: commit al salir bien, ROLLBACK si algo falla.

    Que el rollback sea automático es medio punto de tener la base: una operación a medias
    (p. ej. crear el usuario pero no asignarle el rol) no puede quedar guardada.
    """
    cn = conectar()
    try:
        cur = cn.cursor()
        yield cur
        if commit:
            cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()


def filas(sql, *args):
    """SELECT -> lista de dicts (no tuplas: el código de arriba no debe depender del orden)."""
    with cursor(commit=False) as cur:
        cur.execute(sql, args)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def fila(sql, *args):
    r = filas(sql, *args)
    return r[0] if r else None


def valor(sql, *args):
    with cursor(commit=False) as cur:
        cur.execute(sql, args)
        r = cur.fetchone()
        return r[0] if r else None


def ejecutar(sql, *args):
    """INSERT/UPDATE/DELETE. Devuelve las filas afectadas."""
    with cursor() as cur:
        cur.execute(sql, args)
        return cur.rowcount


def insertar(sql, *args):
    """INSERT que devuelve el id nuevo (IDENTITY)."""
    with cursor() as cur:
        cur.execute(sql + "; SELECT SCOPE_IDENTITY();", args)
        while cur.description is None:
            if not cur.nextset():
                return None
        r = cur.fetchone()
        return int(r[0]) if r and r[0] is not None else None


def existe_base():
    with contextlib.closing(pyodbc.connect(_cadena("master"), autocommit=True, timeout=10)) as cn:
        return cn.cursor().execute("SELECT DB_ID(?)", DB_NAME).fetchval() is not None


def crear_base():
    """Crea la base si no existe (idempotente)."""
    with contextlib.closing(pyodbc.connect(_cadena("master"), autocommit=True, timeout=10)) as cn:
        cur = cn.cursor()
        if cur.execute("SELECT DB_ID(?)", DB_NAME).fetchval() is None:
            cur.execute(f"CREATE DATABASE [{DB_NAME}]")
            return True
        return False


def aplicar_schema(path=None):
    """Aplica db/schema.sql. Es idempotente (el script crea sólo lo que falta).

    Se parte por GO: no es un comando de SQL, es un separador de lotes del cliente —
    pyodbc lo rechaza si se lo mandás.
    """
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "schema.sql")
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    lotes = [b.strip() for b in __import__("re").split(r"(?im)^\s*GO\s*$", sql) if b.strip()]
    with contextlib.closing(conectar(autocommit=True)) as cn:
        cur = cn.cursor()
        for b in lotes:
            cur.execute(b)
    return len(lotes)


def tablas():
    return [r["name"] for r in filas(
        "SELECT t.name FROM sys.tables t WHERE t.is_ms_shipped=0 ORDER BY t.name")]


# ════════════════ DOCUMENTOS (config global clave→JSON) ════════════════
# Los documentos ricos y muy anidados (el catálogo entero, con reglas de planilla, presets de
# nesting, plantillas…) viven en `config` con producto_id NULL. Esto ya NO es un archivo JSON:
# es la base la fuente de verdad (transaccional, respaldada con la base). La IDENTIDAD de cada
# producto SÍ se normaliza aparte en la tabla `producto` (id numérico) — ver sync_productos.
import json as _json


def get_doc(clave, default=None):
    v = valor("SELECT valor FROM config WHERE producto_id IS NULL AND clave=?", clave)
    if v is None:
        return default
    try:
        return _json.loads(v)
    except Exception:
        return default


def set_doc(clave, obj):
    txt = _json.dumps(obj, ensure_ascii=False)
    with cursor() as cur:
        # UPSERT: un solo documento por clave (producto_id NULL).
        cur.execute("UPDATE config SET valor=? WHERE producto_id IS NULL AND clave=?", txt, clave)
        if cur.rowcount == 0:
            cur.execute("INSERT INTO config (producto_id, clave, valor) VALUES (NULL, ?, ?)", clave, txt)


def doc_existe(clave):
    return valor("SELECT COUNT(*) FROM config WHERE producto_id IS NULL AND clave=?", clave) > 0


def sync_productos(cat):
    """Refleja la IDENTIDAD de cada producto del catálogo en la tabla `producto` (id numérico).
    El id viejo del JSON ('prod_…') se guarda en legacy_id para poder cruzarlo; el id que manda
    de acá en más es el numérico. Idempotente: por legacy_id, inserta o actualiza.
    Devuelve {legacy_id: id_numérico}."""
    ids = {}
    for p in (cat.get("productos") or []):
        leg = p.get("id")
        if not leg:
            continue
        pid = valor("SELECT id FROM producto WHERE legacy_id=?", leg)
        nombre = p.get("nombre") or "Molde"
        activo = 0 if p.get("archivado") else 1
        vguia = p.get("variante_guia")
        # DUEÑO del molde: los que sube un usuario son suyos ("Mis artículos"). Se persiste acá
        # porque el catálogo JSON es un documento y la tabla es la identidad: si el dueño vive
        # sólo en el JSON, se pierde en cuanto la base pase a ser la fuente de verdad.
        dueno = p.get("creado_por")
        if pid is None:
            pid = insertar("INSERT INTO producto (nombre, legacy_id, variante_guia, activo, creado_por) "
                           "VALUES (?,?,?,?,?)", nombre, leg, vguia, activo, dueno)
        else:
            ejecutar("UPDATE producto SET nombre=?, variante_guia=?, activo=? WHERE id=?",
                     nombre, vguia, activo, pid)
            # el dueño se escribe una sola vez y no se pisa: quién lo creó no cambia
            if dueno:
                ejecutar("UPDATE producto SET creado_por=? WHERE id=? AND creado_por IS NULL",
                         dueno, pid)
        ids[leg] = pid
    # BORRADO LÓGICO: un molde borrado del catálogo dejaba su fila viva para siempre (quedaban
    # decenas de moldes de prueba). No se borra la fila —hay pedidos y piezas que la referencian—
    # pero se marca inactiva para que no aparezca como si existiera.
    if ids:
        marcas = ",".join("?" * len(ids))
        ejecutar(f"UPDATE producto SET activo=0 WHERE legacy_id NOT IN ({marcas}) AND activo=1",
                 *list(ids.keys()))
    return ids


def sync_piezas_molde(legacy_pid, piezas):
    """Guarda las PIEZAS de un molde en la tabla `pieza` — se llama AL CARGAR el molde (y al
    re-etiquetar). Cada pieza queda con su id numérico propio y su pertenencia al molde
    (producto_id). El nombre es DATO editable; la identidad es el id.

    `piezas` = lista de {id: 'pz_0001' (id estable del molde), nombre, numero, clave}.
    Idempotente: por (producto_id, legacy_id 'pz_xxxx') inserta o actualiza. Las piezas del
    molde que ya no están se borran (con lo suyo derivado)."""
    pid = valor("SELECT id FROM producto WHERE legacy_id=?", legacy_pid)
    if pid is None:
        pid = insertar("INSERT INTO producto (nombre, legacy_id, activo) VALUES (?,?,1)",
                       legacy_pid, legacy_pid)
    with cursor() as cur:
        vivos = []
        for i, pz in enumerate(piezas, start=1):
            leg = pz.get("id")                       # 'pz_0001' (estable dentro del molde)
            if not leg:
                continue
            vivos.append(leg)
            nombre = pz.get("nombre") or None
            gen, num = _norm_generico(pz.get("nombre") or "")
            if pz.get("numero") is not None:
                num = pz.get("numero")
            cur.execute("SELECT id FROM pieza WHERE producto_id=? AND legacy_id=?", pid, leg)
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE pieza SET id_en_molde=?, nombre=?, nombre_generico=?, numero=? "
                            "WHERE id=?", i, nombre, gen or None, num, row[0])
            else:
                cur.execute("INSERT INTO pieza (producto_id, id_en_molde, nombre, nombre_generico, "
                            "numero, legacy_id) VALUES (?,?,?,?,?,?)", pid, i, nombre, gen or None, num, leg)
        # sacar las que ya no vienen en el molde (junto con lo derivado)
        if vivos:
            placeholders = ",".join("?" * len(vivos))
            cur.execute(f"SELECT id FROM pieza WHERE producto_id=? AND legacy_id NOT IN ({placeholders})",
                        pid, *vivos)
            muertas = [r[0] for r in cur.fetchall()]
        else:
            cur.execute("SELECT id FROM pieza WHERE producto_id=?", pid)
            muertas = [r[0] for r in cur.fetchall()]
        for mid in muertas:
            cur.execute("DELETE FROM variable_pieza WHERE pieza_id=?", mid)
            cur.execute("DELETE FROM pieza_talle WHERE pieza_id=?", mid)
            cur.execute("DELETE FROM pieza WHERE id=?", mid)
    return pid


def piezas_de_molde(legacy_pid):
    """Las piezas de un molde tal como están en la base (para leer por id)."""
    pid = valor("SELECT id FROM producto WHERE legacy_id=?", legacy_pid)
    if pid is None:
        return []
    return filas("SELECT id, id_en_molde, nombre, nombre_generico, numero, legacy_id "
                 "FROM pieza WHERE producto_id=? ORDER BY id_en_molde", pid)


def _norm_generico(nombre):
    """'Manga 2' -> ('Manga', 2). Para separar el nombre de uso del número."""
    import re
    m = re.match(r"^(.*?)[\s]*(\d+)\s*$", (nombre or "").strip())
    if m and m.group(1).strip():
        return m.group(1).strip(), int(m.group(2))
    return (nombre or "").strip(), None


def proyectar_catalogo(cat):
    """Proyecta el catálogo a las TABLAS NORMALIZADAS (id numérico) — la verdad real de la base.

    El documento JSON sigue siendo la estructura de trabajo que lee la app; ESTA función deja
    además cada entidad en su tabla con id propio: pieza, variable, variable_pieza, talle, diseno.
    Acá muere la identidad-por-nombre: cada pieza es una FILA con id, dos 'Manga' conviven, y la
    membresía de la variable es por pieza_id (no por nombre → adiós al 'un solo slot por nombre').

    Derivado: se reconstruye por producto (borrar hijos + reinsertar). Idempotente y sin residuos.
    """
    prod_ids = sync_productos(cat)
    for p in (cat.get("productos") or []):
        pid = prod_ids.get(p.get("id"))
        if pid is None:
            continue
        _proyectar_un_producto(pid, p)


def _proyectar_un_producto(pid, p):
    with cursor() as cur:
        # Las PIEZAS ya NO se tocan acá: son propiedad del molde (sync_piezas_molde, al cargar el
        # molde). Acá sólo se rehacen las cosas DERIVADAS de la config: talles, diseños, variables
        # y su relación con piezas EXISTENTES (por id). No se borra ni se crea ninguna pieza.
        cur.execute("DELETE FROM variable_pieza WHERE variable_id IN (SELECT id FROM variable WHERE producto_id=?)", pid)
        cur.execute("DELETE FROM variable WHERE producto_id=?", pid)
        cur.execute("DELETE FROM talle WHERE producto_id=?", pid)
        cur.execute("DELETE FROM diseno WHERE producto_id=?", pid)

        # TALLES (variantes de tamaño)
        for i, t in enumerate(p.get("talles") or p.get("variantes_talles") or []):
            nom = t if isinstance(t, str) else t.get("nombre")
            if nom:
                cur.execute("INSERT INTO talle (producto_id, nombre, orden) VALUES (?,?,?)", pid, nom, i)

        # piezas existentes del molde, indexadas por su legacy_id ('pz_0001') para vincular.
        cur.execute("SELECT id, legacy_id FROM pieza WHERE producto_id=?", pid)
        pieza_por_leg = {r[1]: r[0] for r in cur.fetchall()}

        # VARIABLES + su relación con piezas (POR ID, referenciando las existentes)
        import json as _j
        for v in (p.get("variantes") or []):
            clave = v.get("clave")
            if not clave:
                continue
            cur.execute("INSERT INTO variable (producto_id, clave, label, acomodo, orden) OUTPUT INSERTED.id VALUES (?,?,?,?,?)",
                        pid, clave, v.get("label") or clave,
                        _j.dumps(v.get("acomodo")) if v.get("acomodo") is not None else None,
                        _j.dumps(v.get("orden")) if v.get("orden") is not None else None)
            vid = int(cur.fetchone()[0])
            for val in (v.get("valores") or []):
                nid = pieza_por_leg.get(val.get("pieza_id"))   # la pieza YA existe (del molde)
                if nid is None:
                    continue   # la variable referencia una pieza que no está en el molde: se ignora
                cur.execute("IF NOT EXISTS (SELECT 1 FROM variable_pieza WHERE variable_id=? AND pieza_id=?) "
                            "INSERT INTO variable_pieza (variable_id, pieza_id) VALUES (?,?)", vid, nid, vid, nid)

        # DISEÑOS
        disenos = p.get("disenos") or []
        if isinstance(disenos, list):
            for d in disenos:
                nom = d if isinstance(d, str) else (d.get("nombre") or d.get("id"))
                if not nom:
                    continue
                slug = None if isinstance(d, str) else d.get("slug")
                cur.execute("INSERT INTO diseno (producto_id, nombre, slug, es_principal) VALUES (?,?,?,?)",
                            pid, nom, slug, 1 if (isinstance(d, dict) and d.get("principal")) else 0)
