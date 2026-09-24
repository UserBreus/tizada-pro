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

# 🔴 SIN RECICLADO DE CONEXIONES (2026-09-23). `pyodbc.pooling` viene prendido: el `close()` de
# `cursor()` NO cerraba la conexión, la dejaba guardada para reusarla, y como ningún servidor tiene
# `CPTimeout` configurado en el driver, las guardadas no vencían nunca: el publicado juntó 134
# sesiones dormidas en 24 minutos de vida (medido por el usuario, sys.dm_exec_sessions). Apagado,
# `close()` cierra de verdad. Cuesta reconectar en cada operación (milisegundos), que no se nota: el
# trabajo pesado ya lo hace el navegador. Va en el CÓDIGO (y no en /etc/odbcinst.ini) para que
# viaje con el paquete y no dependa de cómo esté configurado cada servidor.
# ⚠️ Tiene que quedar ANTES de la primera conexión del proceso (el driver lo toma al conectar la
# primera vez): por eso vive acá, al importar este módulo, que es el único que conecta.
pyodbc.pooling = False

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


# 🔴 TECHO DE ESPERA DE UNA CONSULTA. `timeout=10` en `pyodbc.connect` es sólo el tiempo para
# CONECTAR: una vez conectado, la consulta esperaba PARA SIEMPRE (`cn.timeout = 0`), y el motor
# tampoco corta la espera por un candado (`LOCK_TIMEOUT = -1`, medido). O sea: dos operaciones que
# se pisan no dan error — dejan la petición colgada, con su transacción y su conexión abiertas,
# tomando candados que hacen esperar al resto. Eso es lo que «queda ahí jodiendo»: no falla, no
# avisa, y sólo se nota porque el sistema se pone lento o no responde.
# El techo es generoso a propósito: lo más pesado que hace el sistema —reescribir las piezas de un
# molde— son ~1.000 filas en un solo `executemany` (milisegundos). Si algo tarda 30 s es que está
# trabado, y entonces es mejor que falle y se vea.
TIMEOUT_CONSULTA = int(os.environ.get("TIZADA_DB_TIMEOUT", "30"))


def conectar(base=DB_NAME, autocommit=False, timeout_consulta=None):
    cn = pyodbc.connect(_cadena(base), autocommit=autocommit, timeout=10)
    # Se pone del lado del CLIENTE (`cn.timeout`) y no con `SET LOCK_TIMEOUT`: así no cuesta una
    # ida y vuelta más por cada conexión —que es justo lo que la auditoría 386-393 vino a bajar— y
    # cubre toda espera, no sólo la de un candado (una consulta lenta, la base que dejó de contestar).
    _t = TIMEOUT_CONSULTA if timeout_consulta is None else timeout_consulta
    if _t:
        cn.timeout = int(_t)
    return cn


@contextlib.contextmanager
def cursor(commit=True):
    """Cursor con transacción: commit al salir bien, ROLLBACK si algo falla.

    Que el rollback sea automático es medio punto de tener la base: una operación a medias
    (p. ej. crear el usuario pero no asignarle el rol) no puede quedar guardada.

    🔴 LEER NO ABRE TRANSACCIÓN (2026-09-22, el usuario con la captura de `sys.dm_exec_sessions`:
    9 sesiones dormidas con `open_transaction_count = 1`, una de 1420 minutos, todas con el mismo
    `SELECT registro_rev FROM producto`). Con `autocommit=False` el driver pone IMPLICIT_TRANSACTIONS
    ON y el primer SELECT ABRE una transacción; `filas()`/`valor()` entran con `commit=False`, así
    que nadie la cerraba, y como pyodbc reusa las conexiones (pool del driver ODBC), la sesión
    quedaba dormida con la transacción abierta hasta que a alguien le tocara esa conexión. Eso deja
    el log de la base sin poder truncarse y traba cualquier cambio de estructura (ALTER/CREATE
    INDEX espera por el Sch-S de la transacción viva). La lectura ahora va en autocommit: no hay
    transacción que cerrar y no cuesta ninguna ida y vuelta de más.
    """
    cn = conectar(autocommit=not commit)
    try:
        cur = cn.cursor()
        yield cur
        if commit:
            cn.commit()
    except Exception:
        # ⚠️ El rollback va PROTEGIDO: si la conexión ya se cayó (la base se reinició, se cortó la
        # red), `rollback()` lanza SU PROPIA excepción y ésa TAPA la original — te quedabas sin
        # saber qué falló de verdad. La transacción no queda abierta igual: al cerrar la conexión,
        # el motor descarta lo que no se confirmó.
        try:
            cn.rollback()
        except Exception:
            pass
        raise
    finally:
        # SIEMPRE se cierra, pase lo que pase: es lo que impide que queden sesiones colgadas.
        try:
            cn.close()
        except Exception:
            pass


def filas(sql, *args):
    """SELECT -> lista de dicts (no tuplas: el código de arriba no debe depender del orden).

    `commit=False` = SÓLO LECTURA (va en autocommit): no escribir nada acá adentro."""
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
    # Techo aparte: esto es DDL de arranque (crear 26 tablas y sus índices en una base fría puede
    # tardar), y no compite con nadie. Igual lleva uno: si DOS servidores arrancan a la vez, el
    # segundo se quedaría esperando el candado del esquema para siempre.
    with contextlib.closing(conectar(autocommit=True, timeout_consulta=180)) as cn:
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


class ConflictoVersion(Exception):
    """Otro proceso guardó ese documento entre que lo leíste y lo escribiste."""


def get_doc_ver(clave, default=None):
    """El documento Y su versión: `(obj, version)`. La versión es lo que después permite escribir
    CONDICIONALMENTE — «guardá esto sólo si nadie lo tocó desde que lo leí»."""
    r = filas("SELECT valor, [version] FROM config WHERE producto_id IS NULL AND clave=?", clave)
    if not r:
        return default, 0
    try:
        return _json.loads(r[0]["valor"]), int(r[0]["version"] or 0)
    except Exception:
        return default, int(r[0]["version"] or 0)


def _escribir_doc(cur, clave, obj, version_esperada=None):
    """UPSERT del documento dentro de una transacción que ya está abierta. Devuelve la versión
    nueva. Con `version_esperada`, si otro lo cambió antes, levanta `ConflictoVersion` — y como
    estamos dentro de la transacción de quien llama, ahí no se guarda NADA."""
    txt = _json.dumps(obj, ensure_ascii=False)
    # `OUTPUT INSERTED.[version]` devuelve la versión nueva EN LA MISMA sentencia: sin eso hacía
    # falta un SELECT más por cada guardado, y bajar los viajes a la base es justo lo que buscaba
    # la auditoría 386-393.
    _sql = ("UPDATE config SET valor=?, [version]=[version]+1 OUTPUT INSERTED.[version] "
            "WHERE producto_id IS NULL AND clave=?")
    if version_esperada is None:
        cur.execute(_sql, txt, clave)
    else:
        cur.execute(_sql + " AND [version]=?", txt, clave, int(version_esperada))
    _r = cur.fetchone()
    if _r is not None:
        return int(_r[0])
    if version_esperada is not None:
        # No actualizó: o la versión cambió, o el documento no existe todavía. Distinguirlo importa:
        # lo primero es un choque de verdad y lo segundo es la primera escritura de todas.
        cur.execute("SELECT [version] FROM config WHERE producto_id IS NULL AND clave=?", clave)
        _v = cur.fetchone()
        if _v is not None:
            raise ConflictoVersion(
                f"«{clave}» cambió mientras lo editabas (versión {int(_v[0])}, esperaba {version_esperada})")
    cur.execute("INSERT INTO config (producto_id, clave, valor, [version]) VALUES (NULL, ?, ?, 1)",
                clave, txt)
    return 1


def set_doc(clave, obj, version_esperada=None):
    with cursor() as cur:
        return _escribir_doc(cur, clave, obj, version_esperada)


# ════════════════ TRABAJOS DE TIZADA (el ESTADO; los PDF siguen en trabajos/<id>/) ════════════
# Vivían en un `dict` en memoria. Eso significaba dos cosas malas: un reinicio dejaba a todos los
# pedidos en curso sondeando un id que ya no existía, y un SEGUNDO servidor no veía nada de lo que
# hacía el primero — o sea, no se podía crecer de una máquina. Acá vive el estado; el proceso que
# genera igual guarda su copia en memoria (lee más rápido y ahí está el aviso de cancelación), pero
# la verdad que puede ver cualquiera está en la base.


def trabajo_crear(legacy_id, usuario_id=None, molde_nombre=None, moldes=None):
    with cursor() as cur:
        cur.execute("DELETE FROM trabajo WHERE legacy_id=?", legacy_id)   # reintento con el mismo id
        cur.execute(
            "INSERT INTO trabajo (legacy_id, estado, creado_por, molde_nombre, moldes, progreso) "
            "VALUES (?,?,?,?,?,?)",
            legacy_id, "en cola", usuario_id, (molde_nombre or "")[:400], (moldes or "")[:400], "")


def trabajo_actualizar(legacy_id, **campos):
    """Escribe sólo lo que se le pasa. `resultado` va como JSON (es lo que la pantalla ya lee)."""
    _permitidos = ("estado", "progreso", "error", "resultado", "cancelar")
    sets, args = [], []
    for k in _permitidos:
        if k not in campos:
            continue
        v = campos[k]
        if k == "resultado" and v is not None and not isinstance(v, str):
            v = _json.dumps(v, ensure_ascii=False)
        if k == "progreso" and v is not None:
            v = str(v)[:300]
        sets.append(f"{k}=?")
        args.append(v)
    if not sets:
        return 0
    sets.append("actualizado=SYSUTCDATETIME()")
    with cursor() as cur:
        cur.execute(f"UPDATE trabajo SET {', '.join(sets)} WHERE legacy_id=?", *args, legacy_id)
        return cur.rowcount


def trabajo_leer(legacy_id):
    """El trabajo como lo espera la pantalla, o None. `resultado` vuelve ya parseado."""
    r = filas("SELECT legacy_id, estado, progreso, error, resultado, cancelar, creado_por, "
              "       molde_nombre, moldes, "
              "       DATEDIFF(second, '1970-01-01', creado_en) AS creado "
              "  FROM trabajo WHERE legacy_id=?", legacy_id)
    if not r:
        return None
    d = r[0]
    try:
        d["resultado"] = _json.loads(d["resultado"]) if d.get("resultado") else None
    except Exception:
        d["resultado"] = None
    return {"estado": d.get("estado") or "en cola", "progreso": d.get("progreso") or "",
            "resultado": d.get("resultado"), "error": d.get("error"),
            "cancelar_pedido": bool(d.get("cancelar")), "usuario": d.get("creado_por"),
            "producto_nombre": d.get("molde_nombre") or "", "producto_id": d.get("moldes") or "",
            "creado": float(d.get("creado") or 0)}


def trabajo_cancelar(legacy_id):
    """Pide la cancelación. La ATIENDE el proceso que está generando (mira este campo entre fases),
    que puede no ser este: por eso es una marca en la base y no un aviso en memoria."""
    with cursor() as cur:
        cur.execute("UPDATE trabajo SET cancelar=1, actualizado=SYSUTCDATETIME() "
                    " WHERE legacy_id=? AND estado NOT IN ('listo','error','cancelado')", legacy_id)
        return cur.rowcount > 0


def trabajo_cancelado(legacy_id):
    v = valor("SELECT cancelar FROM trabajo WHERE legacy_id=?", legacy_id)
    return bool(v)


def trabajos_podar(horas=6, vivos=200):
    """Saca los TERMINADOS viejos. Nunca toca uno que esté corriendo (perderlo dejaría a la pantalla
    sondeando un id que desapareció) ni los archivos del disco."""
    with cursor() as cur:
        cur.execute("DELETE FROM trabajo WHERE estado IN ('listo','error','cancelado') "
                    "   AND DATEDIFF(hour, actualizado, SYSUTCDATETIME()) > ?", int(horas))
        n = cur.rowcount
        cur.execute("DELETE FROM trabajo WHERE id IN ("
                    "  SELECT id FROM trabajo WHERE estado IN ('listo','error','cancelado') "
                    "   ORDER BY actualizado DESC OFFSET ? ROWS)", int(vivos))
        return n + cur.rowcount


def trabajo_borrar(legacy_id):
    """Saca la fila de un trabajo (los archivos los borra el servidor). Cuántas filas se fueron."""
    with cursor() as cur:
        cur.execute("DELETE FROM trabajo WHERE legacy_id=?", legacy_id)
        return cur.rowcount


def trabajos_terminados_de(usuario_id):
    """`legacy_id` de los trabajos TERMINADOS de ese usuario (None = los que no tienen dueño).
    Lo usa «Nuevo pedido» para llevarse las tizadas del pedido anterior aunque la pantalla ya no
    las tenga anotadas (recarga, otra pestaña)."""
    if usuario_id is None:
        r = filas("SELECT legacy_id FROM trabajo WHERE creado_por IS NULL "
                  "   AND estado IN ('listo','error','cancelado')")
    else:
        r = filas("SELECT legacy_id FROM trabajo WHERE creado_por=? "
                  "   AND estado IN ('listo','error','cancelado')", usuario_id)
    return [x["legacy_id"] for x in r]


# ════════════════ RESERVAS («esto lo está editando fulano») ════════════════
# El candado de edición del servidor dura lo que dura un guardado. Esto es otra cosa: dura lo que
# dura una PERSONA con el editor abierto, cruza procesos y máquinas, y sobre todo **se puede
# mostrar**. Sin esto, dos operarios editan la misma regla de nesting sin enterarse y el segundo
# pisa al primero (ya no lo pierde —la versión del documento lo evita— pero igual le cambia el
# valor y nadie se entera).
# Se suelta SOLA: la pantalla renueva con el latido que ya hace, y si se cierra o se cuelga, el
# `latido` deja de avanzar. Nunca queda algo trabado porque alguien se fue a almorzar.
RESERVA_SEGUNDOS = int(os.environ.get("TIZADA_RESERVA_SEG", "90"))


def tomar_reserva(recurso, usuario_id, usuario=None, segundos=None):
    """Toma (o renueva) la reserva. Devuelve `(la_tengo, dueño)`.

    Es UNA sentencia condicionada: `WHERE` acepta sólo si la reserva es MÍA o si está vencida. Dos
    personas tocando el mismo botón en el mismo instante no pueden quedársela las dos — decide la
    base, no el orden en que llegaron a la memoria de un proceso."""
    # `or` no sirve acá: 0 segundos es un valor válido («todo vencido») y `0 or 90` da 90.
    seg = RESERVA_SEGUNDOS if segundos is None else int(segundos)
    with cursor() as cur:
        cur.execute(
            "UPDATE reserva SET usuario_id=?, usuario=?, latido=SYSUTCDATETIME(), "
            "       tomada=CASE WHEN usuario_id=? THEN tomada ELSE SYSUTCDATETIME() END "
            " WHERE recurso=? AND (usuario_id=? OR usuario_id IS NULL "
            "                      OR DATEDIFF(second, latido, SYSUTCDATETIME()) >= ?)",
            usuario_id, usuario, usuario_id, recurso, usuario_id, seg)
        if cur.rowcount == 0:
            cur.execute("SELECT usuario_id, usuario, latido FROM reserva WHERE recurso=?", recurso)
            r = cur.fetchone()
            if r is not None:
                return False, {"usuario_id": r[0], "usuario": r[1]}
            try:
                cur.execute("INSERT INTO reserva (recurso, usuario_id, usuario) VALUES (?,?,?)",
                            recurso, usuario_id, usuario)
            except Exception:
                # Otro la insertó en el mismo instante (choque contra la PK): gana ése.
                cur.execute("SELECT usuario_id, usuario FROM reserva WHERE recurso=?", recurso)
                r = cur.fetchone()
                if r is not None and r[0] != usuario_id:
                    return False, {"usuario_id": r[0], "usuario": r[1]}
        return True, {"usuario_id": usuario_id, "usuario": usuario}


def soltar_reserva(recurso, usuario_id):
    """La suelta SÓLO si es tuya (si no, soltar la de otro sería un botón para robarla)."""
    with cursor() as cur:
        cur.execute("DELETE FROM reserva WHERE recurso=? AND usuario_id=?", recurso, usuario_id)
        return cur.rowcount > 0


def soltar_reservas_de(usuario_id):
    """Todas las de una persona (al cerrar sesión, o cuando su pantalla avisa que se va)."""
    with cursor() as cur:
        cur.execute("DELETE FROM reserva WHERE usuario_id=?", usuario_id)
        return cur.rowcount


def reservas_vivas(segundos=None):
    """Las que siguen latiendo: `{recurso: {usuario_id, usuario, hace_seg}}`. De paso borra las
    vencidas — la limpieza va acá y no en un hilo aparte, que sería un proceso más que cuidar."""
    # `or` no sirve acá: 0 segundos es un valor válido («todo vencido») y `0 or 90` da 90.
    seg = RESERVA_SEGUNDOS if segundos is None else int(segundos)
    with cursor() as cur:
        cur.execute("DELETE FROM reserva WHERE DATEDIFF(second, latido, SYSUTCDATETIME()) >= ?", seg)
        cur.execute("SELECT recurso, usuario_id, usuario, "
                    "       DATEDIFF(second, tomada, SYSUTCDATETIME()) FROM reserva")
        return {r[0]: {"usuario_id": r[1], "usuario": r[2], "hace_seg": int(r[3] or 0)}
                for r in cur.fetchall()}


def doc_existe(clave):
    return valor("SELECT COUNT(*) FROM config WHERE producto_id IS NULL AND clave=?", clave) > 0


def _producto_id(cur, legacy, crear=False, nombre=None):
    """Id numérico del molde, resuelto CON EL MISMO CURSOR (una sola transacción).

    `UPDLOCK, HOLDLOCK`: antes se preguntaba en una conexión y se insertaba en OTRA. Dos altas del
    mismo molde a la vez veían las dos que no existía y la segunda chocaba contra el UNIQUE de
    `legacy_id` (error 2627, un 500 sin explicación). Con el lock, la segunda espera y lo encuentra."""
    cur.execute("SELECT id FROM producto WITH (UPDLOCK, HOLDLOCK) WHERE legacy_id=?", legacy)
    r = cur.fetchone()
    if r is not None:
        return int(r[0])
    if not crear:
        return None
    cur.execute("INSERT INTO producto (nombre, legacy_id, activo) OUTPUT INSERTED.id VALUES (?,?,1)",
                nombre or legacy, legacy)
    return int(cur.fetchone()[0])


def sync_productos(cat, cur=None):
    """Refleja la IDENTIDAD de cada producto del catálogo en la tabla `producto` (id numérico).
    El id viejo del JSON ('prod_…') se guarda en legacy_id para poder cruzarlo; el id que manda
    de acá en más es el numérico. Idempotente: por legacy_id, inserta o actualiza.
    Devuelve {legacy_id: id_numérico}.

    Con `cur` participa de la transacción de quien llama. Antes abría **2 o 3 conexiones NUEVAS
    por molde** (con 30 moldes eran ~120 conexiones por cada guardado de la configuración)."""
    if cur is None:
        with cursor() as c2:
            return sync_productos(cat, c2)
    ids = {}
    for p in (cat.get("productos") or []):
        leg = p.get("id")
        if not leg:
            continue
        nombre = p.get("nombre") or "Molde"
        activo = 0 if p.get("archivado") else 1
        vguia = p.get("variante_guia")
        # DUEÑO del molde: los que sube un usuario son suyos ("Mis artículos"). Se persiste acá
        # porque el catálogo JSON es un documento y la tabla es la identidad: si el dueño vive
        # sólo en el JSON, se pierde en cuanto la base pase a ser la fuente de verdad.
        dueno = p.get("creado_por")
        pid = _producto_id(cur, leg)
        if pid is None:
            cur.execute("INSERT INTO producto (nombre, legacy_id, variante_guia, activo, creado_por) "
                        "OUTPUT INSERTED.id VALUES (?,?,?,?,?)", nombre, leg, vguia, activo, dueno)
            pid = int(cur.fetchone()[0])
        else:
            cur.execute("UPDATE producto SET nombre=?, variante_guia=?, activo=? WHERE id=?",
                        nombre, vguia, activo, pid)
            # el dueño se escribe una sola vez y no se pisa: quién lo creó no cambia
            if dueno:
                cur.execute("UPDATE producto SET creado_por=? WHERE id=? AND creado_por IS NULL",
                            dueno, pid)
        ids[leg] = pid
    # BORRADO LÓGICO: un molde borrado del catálogo dejaba su fila viva para siempre (quedaban
    # decenas de moldes de prueba). No se borra la fila —hay pedidos y piezas que la referencian—
    # pero se marca inactiva para que no aparezca como si existiera.
    if ids:
        marcas = ",".join("?" * len(ids))
        cur.execute(f"UPDATE producto SET activo=0 WHERE legacy_id NOT IN ({marcas}) AND activo=1",
                    *list(ids.keys()))
    return ids


def sync_piezas_molde(legacy_pid, piezas):
    """⚠️ SUPERADA — hoy **no la llama nadie**: `guardar_registro()` reconstruye `pieza`,
    `pieza_talle` y `variable_pieza` del molde entero en cada guardado del registro, que es
    más completo (esto sólo sincronizaba id y nombre, sin la geometría por talle). Se
    conserva por si hiciera falta sincronizar los nombres sin tocar la geometría. **No
    volver a llamarla desde `_regenerar_piezas_index`**: la copia vieja del servidor lo hace
    y duplicar la escritura no aporta nada.

    Guarda las PIEZAS de un molde en la tabla `pieza`. Cada pieza queda con su id numérico propio y su pertenencia al molde
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

    🔴 TODO EN UNA TRANSACCIÓN (2026-09-07). Antes era `sync_productos` con sus 2-3 conexiones por
    molde y DESPUÉS una transacción **por cada molde**: si el molde 7 de 20 fallaba (un choque de
    locks, una FK), los 6 primeros quedaban proyectados, los otros 13 con la config vieja y el
    documento JSON —que se guarda ANTES— ya confirmado. La base quedaba contando dos historias
    distintas y nada avisaba.
    """
    with cursor() as cur:
        prod_ids = sync_productos(cat, cur)
        for p in (cat.get("productos") or []):
            pid = prod_ids.get(p.get("id"))
            if pid is None:
                continue
            _proyectar_un_producto(pid, p, cur)


def guardar_catalogo(cat, version_esperada=None):
    """El documento del catálogo Y su proyección a las tablas, en UNA sola transacción.
    Devuelve la versión nueva.

    Separados, un fallo al proyectar dejaba el documento nuevo guardado con las tablas viejas.

    🔴 Con `version_esperada` la escritura es CONDICIONAL: si otro proceso guardó entre medio,
    levanta `ConflictoVersion` y no se guarda nada. Es lo único que evita el *lost update* cuando
    hay MÁS DE UN PROCESO — el candado de `servidor.py` vive en la memoria de uno solo."""
    with cursor() as cur:
        _ver = _escribir_doc(cur, "catalogo", cat, version_esperada)
        prod_ids = sync_productos(cat, cur)
        for p in (cat.get("productos") or []):
            pid = prod_ids.get(p.get("id"))
            if pid is None:
                continue
            _proyectar_un_producto(pid, p, cur)
    return _ver


def _proyectar_un_producto(pid, p, cur=None):
    """Proyecta la config del producto a la base por UPSERT (clave natural: talle.nombre,
    variable.clave, diseno.nombre). NUNCA borrar-y-recrear: `pieza_talle`, `editable`,
    `mapeo_arte` y `pedido_fila` referencian estas filas SIN cascade -- el DELETE masivo
    reventaba con error 547 (FK pieza_talle->talle, reportado 2026-08-19) y, aunque no
    reventara, recrear cambiaba los ids y dejaba esas referencias apuntando a filas muertas."""
    import json as _j
    if cur is None:                    # sin cursor propio: se abre uno (uso suelto)
        with cursor() as c2:
            return _proyectar_un_producto(pid, p, c2)
    # ── TALLES: upsert por nombre; el orden se actualiza ────────────────────────────────
    cur.execute("SELECT id, nombre FROM talle WHERE producto_id=?", pid)
    t_exist = {r[1]: r[0] for r in cur.fetchall()}
    cfg_talles = []
    for i, t in enumerate(p.get("talles") or p.get("variantes_talles") or []):
        nom = t if isinstance(t, str) else t.get("nombre")
        if not nom:
            continue
        cfg_talles.append(nom)
        if nom in t_exist:
            cur.execute("UPDATE talle SET orden=? WHERE id=?", i, t_exist[nom])
        else:
            cur.execute("INSERT INTO talle (producto_id, nombre, orden) VALUES (?,?,?)", pid, nom, i)
    # Talles que la config ya no lista: se van SOLO si nada los referencia. Si el registro
    # del molde todavia los tiene (pieza_talle) se quedan: la geometria manda sobre la config.
    for nom, tid in t_exist.items():
        if nom in cfg_talles:
            continue
        # con el MISMO cursor: valor() abre otra conexión y en medio de esta
        # transacción se puede quedar esperando los locks de acá mismo
        cur.execute("SELECT TOP 1 1 FROM pieza_talle WHERE talle_id=?", tid)
        if cur.fetchone():
            continue
        cur.execute("DELETE FROM editable WHERE talle_id=?", tid)
        cur.execute("UPDATE pedido_fila SET talle_id=NULL WHERE talle_id=?", tid)
        cur.execute("DELETE FROM talle WHERE id=?", tid)

    # piezas existentes del molde, indexadas por su legacy_id ('pz_0001') para vincular.
    cur.execute("SELECT id, legacy_id FROM pieza WHERE producto_id=?", pid)
    pieza_por_leg = {r[1]: r[0] for r in cur.fetchall()}

    # ── VARIABLES: upsert por clave; la relacion con piezas se rehace entera ───────────
    cur.execute("SELECT id, clave FROM variable WHERE producto_id=?", pid)
    v_exist = {r[1]: r[0] for r in cur.fetchall()}
    cur.execute("DELETE FROM variable_pieza WHERE variable_id IN (SELECT id FROM variable WHERE producto_id=?)", pid)
    cfg_claves = set()
    for i, v in enumerate(p.get("variantes") or []):
        clave = v.get("clave")
        if not clave:
            continue
        cfg_claves.add(clave)
        _aco = _j.dumps(v.get("acomodo")) if v.get("acomodo") is not None else None
        _ord = _j.dumps(v.get("orden")) if v.get("orden") is not None else None
        if clave in v_exist:
            vid = v_exist[clave]
            cur.execute("UPDATE variable SET label=?, acomodo=?, orden=? WHERE id=?",
                        v.get("label") or clave, _aco, _ord, vid)
        else:
            cur.execute("INSERT INTO variable (producto_id, clave, label, acomodo, orden) OUTPUT INSERTED.id VALUES (?,?,?,?,?)",
                        pid, clave, v.get("label") or clave, _aco, _ord)
            vid = int(cur.fetchone()[0])
        for val in (v.get("valores") or []):
            nid = pieza_por_leg.get(val.get("pieza_id"))   # la pieza YA existe (del molde)
            if nid is None:
                continue   # la variable referencia una pieza que no esta en el molde: se ignora
            cur.execute("IF NOT EXISTS (SELECT 1 FROM variable_pieza WHERE variable_id=? AND pieza_id=?) "
                        "INSERT INTO variable_pieza (variable_id, pieza_id) VALUES (?,?)", vid, nid, vid, nid)
    # Variables borradas de la config: se van CON sus referencias derivadas (mapeo/editable
    # son config tambien); las filas de pedidos historicos quedan con la variable en NULL.
    for clave, vid in v_exist.items():
        if clave in cfg_claves:
            continue
        cur.execute("DELETE FROM mapeo_arte WHERE variable_id=?", vid)
        cur.execute("DELETE FROM editable WHERE variable_id=?", vid)
        cur.execute("UPDATE pedido_fila SET variable_id=NULL WHERE variable_id=?", vid)
        cur.execute("DELETE FROM variable WHERE id=?", vid)   # junta/variable_pieza: CASCADE

    # ── DISENOS: upsert por nombre ─────────────────────────────────────────────────────
    cur.execute("SELECT id, nombre FROM diseno WHERE producto_id=?", pid)
    d_exist = {r[1]: r[0] for r in cur.fetchall()}
    cfg_dis = set()
    disenos = p.get("disenos") or []
    if isinstance(disenos, list):
        for d in disenos:
            nom = d if isinstance(d, str) else (d.get("nombre") or d.get("id"))
            if not nom:
                continue
            cfg_dis.add(nom)
            slug = None if isinstance(d, str) else d.get("slug")
            _pri = 1 if (isinstance(d, dict) and d.get("principal")) else 0
            if nom in d_exist:
                cur.execute("UPDATE diseno SET slug=?, es_principal=? WHERE id=?", slug, _pri, d_exist[nom])
            else:
                cur.execute("INSERT INTO diseno (producto_id, nombre, slug, es_principal) VALUES (?,?,?,?)",
                            pid, nom, slug, _pri)
    for nom, did in d_exist.items():
        if nom in cfg_dis:
            continue
        cur.execute("UPDATE pedido_fila SET diseno_id=NULL WHERE diseno_id=?", did)
        cur.execute("DELETE FROM diseno WHERE id=?", did)     # mapeo_arte/editable: CASCADE

_PT_IDX_MESA = None


def _pt_tiene_idx_mesa(cur=None):
    """¿La base ya tiene la columna `idx_mesa` (camino B)? Cacheado: es una pregunta por proceso.

    Se pregunta en vez de asumir porque un servidor publicado puede estar corriendo con el
    esquema viejo (el arranque AVISA que faltan tablas, no las aplica — ver `_faltan_tablas`).
    Sin la columna, escribir el INSERT nuevo tiraría «Invalid column name» en CADA guardado y
    rompería el camino A entero; así, degrada a lo que hacía antes."""
    global _PT_IDX_MESA
    if _PT_IDX_MESA is None:
        try:
            # con `cur`, en la MISMA conexión de quien llama: dentro de una transacción de
            # escritura no se abre una segunda conexión (ver el comentario de `_producto_id`)
            if cur is not None:
                cur.execute("SELECT COL_LENGTH('dbo.pieza_talle','idx_mesa')")
                _r = cur.fetchone()
                _PT_IDX_MESA = bool(_r) and _r[0] is not None
            else:
                _PT_IDX_MESA = valor("SELECT COL_LENGTH('dbo.pieza_talle','idx_mesa')") is not None
        except Exception:
            _PT_IDX_MESA = False
    return _PT_IDX_MESA


def guardar_registro(legacy_pid, piezas, reg):
    """Reconstruye las piezas del molde en la base. `piezas` = piezas.json['piezas'] (ids 1..N
    numéricos), `reg` = el registro {clave: {talle: {...}}}. Idempotente: upsert por
    (producto_id, id_en_molde); las piezas que ya no están se borran con lo suyo."""
    import json as _j
    with cursor() as cur:
        # El id del molde se resuelve CON ESTE MISMO cursor (antes eran dos conexiones distintas:
        # dos altas a la vez chocaban contra el UNIQUE de `legacy_id`).
        pid = _producto_id(cur, legacy_pid, crear=True)
        # RECONSTRUCCIÓN TOTAL por molde: fuera lo del producto (cualquier residuo de caminos
        # anteriores incluido) y se inserta el estado actual. Idempotente; la relación con las
        # variables la rehace `proyectar_catalogo` en cada guardado del catálogo.
        # ⚠️ EL ORDEN IMPORTA: `mapeo_arte` y `junta_pieza` apuntan a `pieza` **sin cascade**, así
        # que hay que sacarlos ANTES o SQL Server corta con el error 547 (es exactamente lo que
        # pasó con `pieza_talle`→`talle` el 2026-08-19). Hoy esas dos tablas están vacías, pero
        # este es el guardado más caliente del sistema: el día que se llenen, revienta acá.
        _de_este_molde = "IN (SELECT id FROM pieza WHERE producto_id=?)"
        cur.execute(f"DELETE FROM mapeo_arte WHERE pieza_id {_de_este_molde}", pid)
        cur.execute(f"DELETE FROM junta_pieza WHERE pieza_id {_de_este_molde}", pid)
        cur.execute(f"DELETE FROM variable_pieza WHERE pieza_id {_de_este_molde}", pid)
        cur.execute(f"DELETE FROM pieza_talle WHERE pieza_id {_de_este_molde}", pid)
        cur.execute("DELETE FROM pieza WHERE producto_id=?", pid)
        # TALLES del molde (upsert por nombre)
        talles = sorted({t for por_t in (reg or {}).values() for t in (por_t or {})})
        cur.execute("SELECT id, nombre FROM talle WHERE producto_id=?", pid)
        t_id = {r[1]: r[0] for r in cur.fetchall()}
        for i, t in enumerate(talles):
            if t not in t_id:
                cur.execute("INSERT INTO talle (producto_id, nombre, orden) OUTPUT INSERTED.id VALUES (?,?,?)",
                            pid, t, i)
                t_id[t] = int(cur.fetchone()[0])
        fila_id = {}
        for pz in (piezas or []):
            num = pz.get("id")
            clave = pz.get("clave")
            if num is None or clave is None:
                continue
            try:
                num = int(num)
            except (TypeError, ValueError):
                # ids legacy 'pz_0001': se numeran por posición para no perder la pieza
                num = len(fila_id) + 1
            gen, n2 = _norm_generico(clave)
            cur.execute("INSERT INTO pieza (producto_id, id_en_molde, nombre, nombre_generico, numero) "
                        "OUTPUT INSERTED.id VALUES (?,?,?,?,?)", pid, num, clave, gen or None, n2)
            fila_id[clave] = int(cur.fetchone()[0])
        # nueva REVISIÓN del registro: es la señal de invalidación de todos los cachés
        # (antes era el mtime del espejo JSON; sin espejo, la versión vive acá)
        cur.execute("UPDATE producto SET registro_rev = registro_rev + 1 WHERE id=?", pid)
        # EN LOTE: con 30 talles son ~1000 filas; de a una eran ~1000 idas y vueltas al
        # server por cada guardado de un nombre. `fast_executemany` las manda juntas.
        _con_im = _pt_tiene_idx_mesa(cur)
        _filas_pt = []
        for clave, por_t in (reg or {}).items():
            fid = fila_id.get(clave)
            if fid is None:
                continue
            for t, inf in (por_t or {}).items():
                tid = t_id.get(t)
                if tid is None or not isinstance(inf, dict):
                    continue
                _f = (fid, tid, inf.get("mesa"), inf.get("pieza_idx"),
                      _j.dumps(inf.get("ancla"), ensure_ascii=False) if inf.get("ancla") is not None else None,
                      _j.dumps(inf.get("bbox_mu")) if inf.get("bbox_mu") is not None else None,
                      inf.get("w_cm"), inf.get("h_cm"))
                _filas_pt.append((_f + (inf.get("idx_mesa"),)) if _con_im else _f)
        if _filas_pt:
            try:
                cur.fast_executemany = True
            except Exception:
                pass
            cur.executemany(
                "INSERT INTO pieza_talle (pieza_id, talle_id, mesa, pieza_idx, ancla, bbox_mu, ancho_cm, alto_cm"
                + (", idx_mesa) VALUES (?,?,?,?,?,?,?,?,?)" if _con_im else ") VALUES (?,?,?,?,?,?,?,?)"),
                _filas_pt)
            try:
                cur.fast_executemany = False
            except Exception:
                pass
    return pid


def leer_registro(legacy_pid):
    """El registro del molde desde la base, en el formato de siempre
    {clave: {talle: {mesa, pieza_idx, w_cm, h_cm, bbox_mu, ancla}}}. None si el molde no está."""
    import json as _j
    pid = valor("SELECT id FROM producto WHERE legacy_id=?", legacy_pid)
    if pid is None:
        return None
    _con_im = _pt_tiene_idx_mesa()
    rows = filas(
        "SELECT p.nombre AS clave, t.nombre AS talle, pt.mesa, pt.pieza_idx, pt.ancla, "
        "pt.bbox_mu, pt.ancho_cm, pt.alto_cm"
        + (", pt.idx_mesa " if _con_im else " ") +
        "FROM pieza p JOIN pieza_talle pt ON pt.pieza_id=p.id JOIN talle t ON t.id=pt.talle_id "
        "WHERE p.producto_id=? ORDER BY p.id_en_molde", pid)
    if not rows:
        return None
    reg = {}
    for r in rows:
        inf = {"mesa": r["mesa"], "pieza_idx": r["pieza_idx"],
               "w_cm": float(r["ancho_cm"]) if r["ancho_cm"] is not None else None,
               "h_cm": float(r["alto_cm"]) if r["alto_cm"] is not None else None}
        # 🔴 La clave va SÓLO si tiene valor. El motor hace `info.get("idx_mesa", info["pieza_idx"])`
        # y `.get` cae al default sólo si la clave NO ESTÁ: escribir None acá haría `_pm[None]`
        # (TypeError) en TODOS los moldes del camino A.
        if _con_im and r["idx_mesa"] is not None:
            inf["idx_mesa"] = int(r["idx_mesa"])
        for k in ("bbox_mu", "ancla"):
            if r[k]:
                try:
                    inf[k] = _j.loads(r[k])
                except Exception:
                    pass
        reg.setdefault(r["clave"], {})[r["talle"]] = inf
    return reg


def borrar_piezas_molde(legacy_pid, cur=None):
    """Borra TODO lo del molde en la base (piezas, geometría, relaciones, talles).
    Para «borrar molde = borrar todo» y para el reset al re-subir.

    Con `cur` participa de la transacción de quien llama (lo usa `borrar_producto`, que borra
    esto Y la fila del molde: son UNA operación y no pueden quedar a medias una de otra)."""
    if cur is None:
        with cursor() as c2:
            return borrar_piezas_molde(legacy_pid, c2)
    pid = _producto_id(cur, legacy_pid)
    if pid is None:
        return 0
    # ⚠️ PRIMERO lo que APUNTA a estas filas sin cascade, si no salta el error 547 y no se
    # borra nada (`_proyectar_un_producto` ya hacía esta limpieza; acá faltaba).
    _pz = "IN (SELECT id FROM pieza WHERE producto_id=?)"
    _va = "IN (SELECT id FROM variable WHERE producto_id=?)"
    _ta = "IN (SELECT id FROM talle WHERE producto_id=?)"
    cur.execute(f"DELETE FROM mapeo_arte WHERE variable_id {_va}", pid)
    cur.execute(f"DELETE FROM mapeo_arte WHERE pieza_id {_pz}", pid)
    cur.execute(f"DELETE FROM editable WHERE variable_id {_va}", pid)
    cur.execute(f"DELETE FROM editable WHERE talle_id {_ta}", pid)
    # Las filas de pedidos históricos NO se borran: quedan sin la variable/el talle (el pedido
    # es del usuario; el molde es lo que se está borrando).
    cur.execute(f"UPDATE pedido_fila SET variable_id=NULL WHERE variable_id {_va}", pid)
    cur.execute(f"UPDATE pedido_fila SET talle_id=NULL WHERE talle_id {_ta}", pid)
    cur.execute(f"DELETE FROM junta_pieza WHERE pieza_id {_pz}", pid)
    cur.execute(f"DELETE FROM variable_pieza WHERE pieza_id {_pz}", pid)
    cur.execute(f"DELETE FROM pieza_talle WHERE pieza_id {_pz}", pid)
    cur.execute("DELETE FROM variable WHERE producto_id=?", pid)   # junta: CASCADE
    cur.execute("DELETE FROM pieza WHERE producto_id=?", pid)      # pieza_tela: CASCADE
    cur.execute("DELETE FROM talle WHERE producto_id=?", pid)
    return 1


def borrar_producto(legacy_pid):
    """Borra el molde ENTERO de la base, incluida su fila en `producto`. Devuelve 1 si la borró.

    `sync_productos` hace borrado LÓGICO (`activo=0`) porque un molde sacado del catálogo puede
    tener historia. Un molde EFÍMERO del camino B no: se sube para un pedido y no existe después,
    así que dejar su fila acumularía una por cada subida para siempre.
    🔴 La fila NO se borra si algún pedido la referencia (`dbo.pedido` no tiene cascade): ahí se
    cae al borrado lógico de siempre. Hoy nadie escribe pedidos, pero el día que se escriban,
    borrar un efímero no puede llevarse un pedido histórico por delante."""
    # UNA sola transacción para toda la operación: antes eran tres (buscar el id · borrar las
    # piezas · borrar la fila), y si se cortaba en el medio el molde quedaba a mitad de borrar.
    with cursor() as cur:
        pid = _producto_id(cur, legacy_pid)
        if pid is None:
            return 0
        borrar_piezas_molde(legacy_pid, cur)
        for t in ("diseno", "producto_tela", "config"):
            try:
                cur.execute(f"DELETE FROM {t} WHERE producto_id=?", pid)
            except Exception:
                pass                     # tabla ausente en una base a medio migrar: no es fatal
        cur.execute("DELETE FROM producto WHERE id=? AND NOT EXISTS "
                    "(SELECT 1 FROM pedido WHERE producto_id=?)", pid, pid)
        if cur.rowcount == 0:
            cur.execute("UPDATE producto SET activo=0 WHERE id=?", pid)
            return 0
    return 1


def registro_rev(legacy_pid):
    """Revisión actual del registro del molde (para claves de caché). None si el molde no está."""
    return valor("SELECT registro_rev FROM producto WHERE legacy_id=?", legacy_pid)


# ── CONFIGURACIONES GUARDADAS DE UN MOLDE (camino B) ──────────────────────────────────────────
# Un molde que trae el diseño adentro se sube PARA UN PEDIDO y se borra con él: el nombrado de las
# piezas, los grupos, las variables y las telas se perdían, y al volver a usar el MISMO archivo en
# otro pedido había que hacer todo de nuevo (pedido del usuario 2026-09-08). Acá se guarda esa
# configuración, atada al ARCHIVO (sha1) y no al molde, para poder ofrecerla la próxima vez.
_CONFIG_MOLDE_LISTA = False


def _asegurar_config_molde():
    """Crea la tabla si falta. Va acá y no sólo en `schema.sql` porque las bases que ya están
    instaladas no vuelven a pasar por el instalador: la primera vez que alguien guarda una
    configuración, la tabla tiene que aparecer sola."""
    global _CONFIG_MOLDE_LISTA
    if _CONFIG_MOLDE_LISTA:
        return
    with cursor() as cur:
        cur.execute("""
IF OBJECT_ID('dbo.config_molde') IS NULL
CREATE TABLE dbo.config_molde (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    nombre      NVARCHAR(160) NOT NULL,
    sha1        NVARCHAR(40)  NULL,     -- del archivo del molde: identifica el MISMO archivo
    molde       NVARCHAR(240) NULL,     -- de qué molde salió (para reconocerla en la lista)
    piezas_n    INT NULL,               -- cuántas piezas tenía (compatibilidad a ojo)
    mesas_n     INT NULL,
    creado_en   DATETIME2 NOT NULL CONSTRAINT DF_config_molde_creado DEFAULT SYSUTCDATETIME(),
    creado_por  INT NULL,
    datos       NVARCHAR(MAX) NOT NULL  -- el JSON con todo lo guardado
)""")
        # HUELLA DE LA GEOMETRÍA: identifica al MOLDE, no al archivo. El mismo molde con otro
        # diseño adentro es otro archivo (otro sha1) pero las piezas miden lo mismo, así que la
        # huella coincide y la configuración se reconoce igual. Va aparte y como columna porque
        # es lo que se compara al listar: leer el JSON de cada una para eso era un viaje por fila.
        cur.execute("IF COL_LENGTH('dbo.config_molde','huella') IS NULL "
                    "ALTER TABLE dbo.config_molde ADD huella NVARCHAR(40) NULL")
    _CONFIG_MOLDE_LISTA = True


def guardar_config_molde(nombre, sha1, molde, piezas_n, mesas_n, datos, creado_por=None, id_=None,
                         huella=None):
    """Guarda (o pisa, si viene `id_`) una configuración. Devuelve su id.

    `sha1` es del ARCHIVO y `huella` del MOLDE (las medidas de sus piezas): con el mismo molde y
    otro diseño adentro cambia el primero y NO el segundo, que es lo que permite reconocerlo."""
    _asegurar_config_molde()
    txt = _json.dumps(datos, ensure_ascii=False)
    with cursor() as cur:
        if id_:
            cur.execute("UPDATE config_molde SET nombre=?, sha1=?, molde=?, piezas_n=?, mesas_n=?, "
                        "datos=?, huella=? WHERE id=?",
                        nombre, sha1, molde, piezas_n, mesas_n, txt, huella, int(id_))
            if cur.rowcount:
                return int(id_)
        cur.execute("INSERT INTO config_molde (nombre, sha1, molde, piezas_n, mesas_n, datos, "
                    "creado_por, huella) OUTPUT INSERTED.id VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    nombre, sha1, molde, piezas_n, mesas_n, txt, creado_por, huella)
        return int(cur.fetchone()[0])


def listar_configs_molde(creado_por=None, todas=False):
    """Las configuraciones guardadas, sin el JSON (la lista no lo necesita).

    🔴 POR USUARIO (decisión del usuario 2026-09-09): cada uno ve LAS SUYAS. Antes se listaban
    todas y en un taller con varias personas la lista se llenaba de recetas ajenas. Sin sesión
    (taller sin usuarios) las de nadie son `creado_por IS NULL`, que es justo lo que se guardó.
    `todas=True` es para el mantenimiento, no para la pantalla."""
    _asegurar_config_molde()
    cols = ("SELECT id, nombre, sha1, molde, piezas_n, mesas_n, creado_en, creado_por, huella "
            "FROM config_molde ")
    if todas:
        return filas(cols + "ORDER BY creado_en DESC")
    if creado_por is None:
        return filas(cols + "WHERE creado_por IS NULL ORDER BY creado_en DESC")
    return filas(cols + "WHERE creado_por=? ORDER BY creado_en DESC", int(creado_por))


def leer_config_molde(id_):
    _asegurar_config_molde()
    f = fila("SELECT id, nombre, sha1, molde, piezas_n, mesas_n, creado_en, creado_por, huella, "
             "datos FROM config_molde WHERE id=?", int(id_))
    if not f:
        return None
    try:
        f["datos"] = _json.loads(f["datos"] or "{}")
    except Exception:
        f["datos"] = {}
    return f


def borrar_config_molde(id_):
    _asegurar_config_molde()
    return ejecutar("DELETE FROM config_molde WHERE id=?", int(id_))
