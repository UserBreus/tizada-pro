# -*- coding: utf-8 -*-
"""
CONTRATO: EL ESQUEMA LLEGA SOLO Y LOS ÍNDICES ESTÁN — `py verificar_schema_indices.py`.

Dos cosas que se arreglaron el 2026-09-07 y hay que sostener:

  1. **`db/schema.sql` se aplica al ARRANCAR.** Antes lo corría sólo el instalador: una tabla o un
     índice agregados después **no llegaban nunca** a una base ya instalada, y `/api/salud` se
     quejaba de lo que faltaba sin que nadie supiera cómo ponerlo (pasó en el VPS recién
     publicado). Es idempotente: cada trozo va guardado por un `IF NOT EXISTS`.
  2. **Las claves foráneas que se recorren dentro de una escritura tienen índice.** SQL Server
     indexa la PK y los UNIQUE, no las FK; y en varias tablas la columna que se busca es la
     SEGUNDA de una clave compuesta, o sea inservible. Sin índice, borrar un molde recorre tablas
     enteras **con los locks tomados**: no rompe nada, pero todo se va poniendo lento.

Y una tercera, que era código muerto: `/api/salud` decía «sin driver ODBC → el sistema corre con
archivos». `db.driver_disponible()` devuelve el nombre del driver o **levanta**: nunca algo falso,
así que esa rama no se ejecutaba jamás. Y desde que la base es la fuente de verdad, sin driver no
hay sistema: tiene que salir en rojo, con un mensaje que diga qué instalar.

⚠️ No abre ninguna conexión: se lee `schema.sql` y se corre `/api/salud` con un doble.
"""
import os
import re
import sys
import tempfile
import types

_TMP = tempfile.mkdtemp(prefix="verif_schema_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = "localhost\\NO_EXISTE_ES_UNA_PRUEBA"

_AQUI = os.path.dirname(os.path.abspath(__file__))
_LOTES = []            # lo que `aplicar_schema` le manda a la base

_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
_falso.tablas = lambda: []
sys.modules["db"] = _falso

sys.path.insert(0, _AQUI)
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S   # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


with open(os.path.join(_AQUI, "db", "schema.sql"), encoding="utf-8") as f:
    SQL = f.read()
# Se parte igual que `db.aplicar_schema`: `GO` no es SQL, es un separador del cliente.
LOTES = [b.strip() for b in re.split(r"(?im)^\s*GO\s*$", SQL) if b.strip()]

# Los que el sistema necesita sí o sí, con la tabla y la columna que tienen que cubrir.
ESPERADOS = {
    "IX_pieza_talle_talle": ("pieza_talle", "talle_id"),
    "IX_variable_pieza_pieza": ("variable_pieza", "pieza_id"),
    "IX_junta_pieza_pieza": ("junta_pieza", "pieza_id"),
    "IX_editable_variable": ("editable", "variable_id"),
    "IX_editable_talle": ("editable", "talle_id"),
    "IX_mapeo_arte_variable": ("mapeo_arte", "variable_id"),
    "IX_mapeo_arte_pieza": ("mapeo_arte", "pieza_id"),
    "IX_pedido_fila_talle": ("pedido_fila", "talle_id"),
    "IX_pedido_fila_variable": ("pedido_fila", "variable_id"),
    "IX_pedido_fila_diseno": ("pedido_fila", "diseno_id"),
    "IX_usuario_rol_rol": ("usuario_rol", "rol_id"),
    "IX_rol_permiso_permiso": ("rol_permiso", "permiso_id"),
}

print("1) Están todos los índices que hacen falta, sobre la columna correcta")
for nombre, (tabla, col) in ESPERADOS.items():
    m = re.search(r"CREATE\s+INDEX\s+%s\s+ON\s+dbo\.(\w+)\s*\(([^)]*)\)" % re.escape(nombre),
                  SQL, re.I)
    ok(bool(m) and m.group(1).lower() == tabla and col in m.group(2),
       f"{nombre} → {tabla}({col})")

print("\n2) Ninguno se crea sin preguntar antes si ya está (aplicarlo dos veces no puede romper)")
for lote in LOTES:
    for nombre in re.findall(r"CREATE\s+INDEX\s+(\w+)", lote, re.I):
        guarda = re.search(r"IF\s+NOT\s+EXISTS\s*\(\s*SELECT[^)]*sys\.indexes[^)]*name\s*=\s*'(\w+)'",
                           lote, re.I)
        ok(bool(guarda) and guarda.group(1).lower() == nombre.lower(),
           f"{nombre} va guardado por su propio IF NOT EXISTS")

print("\n3) El esquema se aplica AL ARRANCAR (no sólo al instalar)")
_srv = open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
ok("db.aplicar_schema()" in _srv, "el servidor aplica `db/schema.sql` al arrancar")
_i_schema = _srv.index("db.aplicar_schema()")
_i_func = _srv.index("def _poner_base_al_dia_al_arrancar")
_i_fin = _srv.index("\ndef ", _i_func + 10)
ok(_i_func < _i_schema < _i_fin, "y lo hace dentro de `_poner_base_al_dia_al_arrancar`")
ok("aplicar_schema" not in open(os.path.join(_AQUI, "actualizador.py"), encoding="utf-8").read(),
   "🔴 pero NO desde el actualizador (ahí el servidor viejo todavía está vivo)")

print("\n4) Sin driver ODBC, la salud sale en ROJO y explica")
_srv_fuente = _srv
ok("sin driver ODBC (el sistema corre con archivos)" not in _srv_fuente,
   "se fue el mensaje que decía que el sistema corre con archivos (ya no existe ese modo)")
# Se miran sólo las líneas de CÓDIGO: en los comentarios el texto sigue, contando qué pasaba.
_codigo = [l for l in _srv_fuente.split("\n") if not l.strip().startswith("#")]
ok(not [l for l in _codigo if "if not db.driver_disponible()" in l],
   "🔴 y se fue la comparación que nunca era cierta (esa función levanta, no devuelve falso)")

S._USUARIOS_ON = False


def _sin_driver():
    raise RuntimeError("No hay ningún driver ODBC de SQL Server instalado. Instalá "
                       "'ODBC Driver 18 for SQL Server'.")


_falso.driver_disponible = _sin_driver
C = S.app.test_client()
r = C.get("/api/salud")
d = r.get_json()
ok(r.status_code == 503, f"contesta 503, no 200 (contestó {r.status_code})")
ok("base" in (d.get("fallas") or []), f"y la falla es la base (fallas: {d.get('fallas')})")
_det = (d.get("chequeos", {}).get("base") or {}).get("detalle", "")
ok("ODBC" in _det, f"con un mensaje que dice qué instalar: «{_det[:70]}»")

print("\n5) Con la base sana, la salud cuenta tablas e índices")
_falso.driver_disponible = lambda: "ODBC Driver 18 for SQL Server"
_falso.valor = lambda *a, **k: 1
_tablas = {m.lower() for m in re.findall(r"CREATE\s+TABLE\s+(?:\[?dbo\]?\.)?\[?(\w+)\]?", SQL, re.I)}
_falso.tablas = lambda: sorted(_tablas)
_indices = {m.lower() for m in re.findall(r"CREATE\s+INDEX\s+\[?(\w+)\]?", SQL, re.I)}
_falso.filas = lambda *a, **k: [{"name": n} for n in _indices]
d = C.get("/api/salud").get_json()
_det = (d.get("chequeos", {}).get("esquema_base") or {}).get("detalle", "")
ok((d.get("chequeos", {}).get("esquema_base") or {}).get("ok") is True, "el esquema da verde")
ok("índices" in _det, f"y dice cuántos índices hay: «{_det}»")

_falso.filas = lambda *a, **k: [{"name": n} for n in list(_indices)[:2]]
d = C.get("/api/salud").get_json()
_det = (d.get("chequeos", {}).get("esquema_base") or {}).get("detalle", "")
ok("faltan" in _det and "índice" in _det,
   f"y AVISA si faltan índices, en vez de dejar que todo se ponga lento sin motivo: «{_det[:80]}»")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}:")
    for f in FALLOS:
        print("  -", f)
    sys.exit(1)
print("TODO OK: el esquema llega solo, los índices están y sin driver la salud lo dice")
