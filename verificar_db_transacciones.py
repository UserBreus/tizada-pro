# -*- coding: utf-8 -*-
"""
CONTRATO: LO QUE VA JUNTO SE GUARDA JUNTO — `py verificar_db_transacciones.py`.

La auditoría anterior (changelog 278) comprobó que `db.cursor()` cierra bien y que no quedan
transacciones fantasma. Cierto — y no era el problema. El problema era **cuántas transacciones
sueltas** forman una operación que el usuario ve como UNA:

  · Editar los roles de un usuario BORRABA los suyos (confirmado) y después los asignaba de a uno.
    Una clave de rol inexistente devolvía 400 **con el usuario ya sin ningún rol**. Si era el
    último administrador, nadie podía volver a entrar a arreglarlo.
  · Lo mismo al cambiarle los permisos a un rol, y al crear un usuario (podía quedar sin roles —
    justo el ejemplo que el docstring de `db.cursor()` decía que no podía pasar).
  · Guardar la configuración proyectaba **un molde por transacción**, después de confirmar el
    documento: si fallaba en el medio, la base contaba dos historias distintas.
  · Borrar un usuario reventaba con FK 547 (`producto.creado_por`) para cualquiera que hubiera
    subido un molde.

Cómo se prueba SIN tocar la base: se reemplaza `db.conectar` por una conexión de mentira que
ANOTA cada sentencia y en qué conexión (o sea, en qué transacción) fue. Así se puede afirmar
«esto fue UNA transacción» y «esto no llegó a escribir nada».

⚠️ No toca la base real ni datos del usuario.
"""
import os
import sys
import tempfile

os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"
os.environ["TIZADA_DATOS"] = tempfile.mkdtemp(prefix="verif_tx_")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db   # noqa: E402   ← el de VERDAD: lo que se prueba es su SQL

sys.stdout.reconfigure(encoding="utf-8")
FALLOS = []
SQL = []          # [(nro_de_conexion, sql, args)]
_TABLAS = {}      # respuestas preparadas: (fragmento del sql) -> filas


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def _columnas(sql):
    """Nombres de columna de un SELECT, para que `db.filas()` pueda armar sus dicts."""
    up = sql.upper()
    if not up.startswith("SELECT") or " FROM " not in up:
        return None
    trozo = sql[len("SELECT"):up.index(" FROM ")]
    for pref in ("DISTINCT ", "TOP 1 ", "TOP 1 1"):
        if trozo.strip().upper().startswith(pref.strip().upper()):
            trozo = trozo.strip()[len(pref.strip()):]
    cols = []
    for c in trozo.split(","):
        c = c.strip()
        if " AS " in c.upper():
            c = c[c.upper().rindex(" AS ") + 4:].strip()
        elif "." in c:
            c = c.split(".")[-1].strip()
        cols.append((c or "col", None))
    return cols


class _Cursor:
    def __init__(self, n):
        self.n = n
        self._filas = []
        self.rowcount = 1
        self.description = None
        self.fast_executemany = False

    def execute(self, sql, *args):
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            args = tuple(args[0])
        limpio = " ".join(sql.split())
        SQL.append((self.n, limpio, args))
        self._filas = []
        for frag, filas in _TABLAS.items():
            if frag in limpio:
                self._filas = list(filas)
                break
        # `db.filas()` arma dicts con los nombres de columna: se sacan del propio SELECT para que
        # el doble sirva también para lo que devuelve filas con nombre (y no sólo valores sueltos).
        self.description = _columnas(limpio) if self._filas else None
        return self

    def executemany(self, sql, filas):
        SQL.append((self.n, " ".join(sql.split()), f"<{len(filas)} filas>"))
        return self

    def fetchone(self):
        return self._filas.pop(0) if self._filas else None

    def fetchall(self):
        f, self._filas = self._filas, []
        return f

    def fetchval(self):
        r = self.fetchone()
        return r[0] if r else None


class _Conexion:
    """Cada instancia = una transacción distinta (así se cuentan)."""
    contador = 0

    def __init__(self):
        _Conexion.contador += 1
        self.n = _Conexion.contador

    def cursor(self):
        return _Cursor(self.n)

    def commit(self):
        SQL.append((self.n, "COMMIT", ()))

    def rollback(self):
        SQL.append((self.n, "ROLLBACK", ()))

    def close(self):
        pass


db.conectar = lambda *a, **k: _Conexion()


def limpiar(**respuestas):
    SQL.clear()
    _TABLAS.clear()
    _TABLAS.update(respuestas)
    _Conexion.contador = 0


def conexiones():
    return len({n for n, _s, _a in SQL})


def transacciones_que_escriben():
    """Cuántas transacciones DISTINTAS escribieron. Es lo que importa: un SELECT suelto antes
    («¿existe este rol?») no rompe nada; lo que no puede partirse en dos es la ESCRITURA."""
    return len({n for n, s, _a in SQL
                if s.startswith(("INSERT", "UPDATE", "DELETE"))})


def sentencias(*palabras):
    return [s for _n, s, _a in SQL if all(p in s for p in palabras)]


import auth            # noqa: E402
import api_usuarios    # noqa: E402

print("1) Crear un usuario: el usuario y sus roles, o nada")
limpiar(**{"FROM usuario WHERE usuario": [], "FROM rol WHERE clave": [(7,)],
           "INSERT INTO usuario": [(42,)]})
uid = auth.crear_usuario("nuevo", "Nuevo", "unaclavelarga", roles=["admin"])
ok(uid == 42, "devuelve el id del usuario creado")
ok(conexiones() == 1, f"todo en UNA transacción (fueron {conexiones()})")
ok(len(sentencias("INSERT INTO usuario_rol")) == 1, "y el rol entra en esa misma transacción")

limpiar(**{"FROM usuario WHERE usuario": [], "FROM rol WHERE clave": []})
try:
    auth.crear_usuario("nuevo", "Nuevo", "unaclavelarga", roles=["no_existe"])
    ok(False, "un rol inexistente tiene que cortar")
except ValueError:
    ok(True, "un rol inexistente corta con un error claro")
ok(not sentencias("INSERT INTO usuario"),
   "🔴 y NO se llegó a insertar el usuario (antes quedaba creado, sin roles)")

print("\n2) Editar los roles de un usuario: si uno no existe, no se toca NADA")
api_usuarios.usuario_actual = lambda: {"id": 1, "usuario": "yo", "permisos": ["usuario.gestionar"]}
api_usuarios._seria_el_ultimo_admin = lambda uid, roles: False
app = api_usuarios.Flask(__name__) if hasattr(api_usuarios, "Flask") else None
import flask   # noqa: E402
_app = flask.Flask(__name__)
_app.secret_key = "prueba"
_app.register_blueprint(api_usuarios.bp)
C = _app.test_client()

limpiar(**{"COUNT(*) FROM usuario WHERE id": [(1,)], "FROM rol WHERE clave": []})
r = C.put("/api/usuarios/5", json={"roles": ["no_existe"]})
ok(r.status_code == 400, f"contesta 400 (contestó {r.status_code})")
ok(not sentencias("DELETE FROM usuario_rol"),
   "🔴 y NO borró los roles que tenía (antes el usuario quedaba sin ninguno)")

limpiar(**{"COUNT(*) FROM usuario WHERE id": [(1,)], "FROM rol WHERE clave": [(3,)]})
r = C.put("/api/usuarios/5", json={"nombre": "Otro", "roles": ["operario"]})
ok(r.status_code == 200, "con roles válidos guarda")
ok(transacciones_que_escriben() == 1,
   f"el cambio entero se ESCRIBE en una transacción (fueron {transacciones_que_escriben()})")
_orden = [s for s in sentencias("usuario_rol")]
ok(len(sentencias("DELETE FROM usuario_rol")) == 1 and len(sentencias("INSERT INTO usuario_rol")) == 1,
   "borra los viejos e inserta los nuevos, junto con el resto del cambio")

print("\n3) Los permisos de un rol se cambian de una vez")
limpiar(**{"FROM rol WHERE id": [(2, "operario", 0)], "FROM permiso WHERE clave": [(9,)]})
r = C.put("/api/roles/2", json={"permisos": ["molde.ver", "pedido.crear"]})
ok(r.status_code == 200, "guarda los permisos del rol")
ok(transacciones_que_escriben() == 1,
   f"en UNA transacción de escritura (fueron {transacciones_que_escriben()})")
ok(len(sentencias("DELETE FROM rol_permiso")) == 1 and len(sentencias("INSERT INTO rol_permiso")) == 2,
   "🔴 el borrado y las altas van juntos (antes el borrado se confirmaba solo: un fallo dejaba "
   "el rol SIN permisos)")

print("\n4) Un usuario no se borra: se desactiva (y no revienta con FK 547)")
limpiar()
r = C.delete("/api/usuarios/5")
ok(r.status_code == 200, "contesta 200")
ok(not sentencias("DELETE FROM usuario WHERE"),
   "🔴 NO se borra la fila (reventaba con error 547 si el usuario había subido un molde)")
ok(len(sentencias("UPDATE usuario SET activo=0")) == 1, "se desactiva")
ok(len(sentencias("DELETE FROM usuario_rol")) == 1, "y pierde sus roles")
ok(r.get_json().get("desactivado") is True, "y lo dice, para que la pantalla no mienta")

print("\n5) El catálogo entero se proyecta en UNA transacción")
limpiar(**{"FROM producto WITH (UPDLOCK": [(11,)]})
cat = {"productos": [{"id": f"prod_{i}", "nombre": f"Molde {i}"} for i in range(3)]}
db.proyectar_catalogo(cat)
ok(transacciones_que_escriben() == 1,
   f"3 moldes = 1 transacción (fueron {transacciones_que_escriben()}; antes eran ~4 conexiones POR MOLDE)")
limpiar(**{"FROM producto WITH (UPDLOCK": [(11,)]})
db.guardar_catalogo(cat)
ok(transacciones_que_escriben() == 1,
   f"y el documento va en la MISMA (fueron {transacciones_que_escriben()})")
ok(bool(sentencias("config")) and bool(sentencias("INSERT INTO producto") or sentencias("UPDATE producto")),
   "el documento y las tablas se escriben en la misma transacción")

print("\n6) Borrar lo de un molde limpia PRIMERO lo que lo referencia")
limpiar(**{"FROM producto WITH (UPDLOCK": [(11,)]})
db.borrar_piezas_molde("prod_x")
_sec = [s for _n, s, _a in SQL]


def antes_que(a, b):
    ia = next((i for i, s in enumerate(_sec) if a in s), None)
    ib = next((i for i, s in enumerate(_sec) if b in s), None)
    return ia is not None and ib is not None and ia < ib


ok(antes_que("DELETE FROM mapeo_arte", "DELETE FROM variable"), "`mapeo_arte` se limpia antes que `variable`")
ok(antes_que("DELETE FROM editable", "DELETE FROM talle"), "`editable` antes que `talle`")
ok(antes_que("UPDATE pedido_fila", "DELETE FROM talle"),
   "las filas de pedidos viejos se sueltan antes (no se borran: el pedido es del usuario)")
ok(antes_que("DELETE FROM junta_pieza", "DELETE FROM pieza"), "`junta_pieza` antes que `pieza`")
ok(transacciones_que_escriben() == 1,
   f"y todo en una transacción (fueron {transacciones_que_escriben()})")

print("\n7) Guardar el registro del molde también limpia antes de borrar piezas")
limpiar(**{"FROM producto WITH (UPDLOCK": [(11,)], "INSERT INTO pieza (": [(5,)],
           "INSERT INTO talle": [(6,)]})
db.guardar_registro("prod_x", [{"id": 1, "clave": "Frente"}], {"Frente": {"M": {"mesa": 1}}})
_sec = [s for _n, s, _a in SQL]
ok(antes_que("DELETE FROM mapeo_arte", "DELETE FROM pieza WHERE producto_id"),
   "`mapeo_arte` se limpia antes de borrar las piezas")
ok(antes_que("DELETE FROM junta_pieza", "DELETE FROM pieza WHERE producto_id"),
   "`junta_pieza` también")
ok(bool([s for s in _sec if "UPDLOCK" in s]),
   "🔴 el id del molde se busca con UPDLOCK (dos altas a la vez chocaban contra el UNIQUE)")
ok(transacciones_que_escriben() == 1,
   f"y todo en una transacción (fueron {transacciones_que_escriben()})")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK: cada operación es UNA transacción, y nada se borra antes de soltar lo que lo apunta")
