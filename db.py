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
