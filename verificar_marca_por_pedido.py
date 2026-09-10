# -*- coding: utf-8 -*-
"""
CONTRATO: LO QUE NO SE SUBLIMA ES DEL PEDIDO — `py verificar_marca_por_pedido.py`.

El caso real (2026-09-10): el usuario armó un pedido y la ficha técnica salió diciendo
**«escudo · se hace en TPU»** en los dos diseños. Nadie lo eligió en ese pedido. Estaba guardado en
el CATÁLOGO del molde (`producto.editables[diseño][variable][objeto].marca`) desde un pedido
anterior, y se aplicó solo. Sus palabras: *«eso no puede pasar ni quedar bugiado una elección de un
pedido anterior; por cada pedido y por cada molde elegimos si el escudo va en TPU»*.

Y eligió cómo: **cada pedido arranca en cero — todo se sublima** — y la marca se pone en el paso
Arte, sobre el objeto.

🔴 Por qué importa tanto: una marca heredada hace que un objeto **no se imprima** cuando tenía que
imprimirse (o al revés). No falla, no avisa: sale de la máquina y se descubre con la tela cortada
([[traba-antes-de-fabricar]], [[marcas-proceso]]).

Lo que candamos:
  1. sin nada en el pedido, NO hay marcas — aunque el molde tenga guardadas de antes;
  2. lo que manda el pedido es lo que se usa, y sólo para SU molde y SU diseño;
  3. la ficha técnica lee las mismas (si no, diría una cosa y la tela saldría con otra);
  4. la pantalla no las guarda más en el molde, y «Nuevo pedido» las deja en cero.

⚠️ No toca nada del usuario: `db` es un doble, DATOS a un temporal.
"""
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_AQUI = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_marca_ped_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
_falso.get_doc = lambda c, default=None: default
_falso.get_doc_ver = lambda c, default=None: (default, 0)
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

sys.path.insert(0, _AQUI)
import tempfile as _tl, registro as _LG      # noqa: E402
_LG.usar_carpeta(_tl.mkdtemp(prefix="verif_marca_logs_"))
import servidor as S                          # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


# El molde TAL CUAL quedó el del usuario: con la marca vieja pegada en el catálogo.
MOLDE = {"id": "p1", "nombre": "Camiseta de futbol",
         "editables": {"jugador": {"v_1": {"escudo": {"marca": "tpu", "sin_marca": True}}},
                       "golero": {"v_1": {"escudo": {"marca": "tpu"}}}}}

print("1 · UN PEDIDO QUE NO ELIGIÓ NADA NO LLEVA NINGUNA MARCA")
# 🔴 Es el bug tal cual: el molde tiene «escudo en TPU» de antes y el pedido no pidió nada.
ok(S._marcas_del_pedido({}, "p1", "jugador") == {},
   "sin `marcas_pedido` en el cuerpo, no hay marcas (el molde ya no decide)")
ok(S._marcas_del_pedido({"marcas_pedido": {}}, "p1", "jugador") == {},
   "con el campo vacío, tampoco")
ok(S._marcas_del_pedido({}, "p1", "jugador", "sin_marca_pedido") == {},
   "y lo mismo con «sin marca»")

print("\n2 · LO QUE MANDA EL PEDIDO ES LO QUE VALE, Y SÓLO PARA SU MOLDE Y SU DISEÑO")
CUERPO = {"marcas_pedido": {"p1": {"golero": {"v_1": {"escudo": "tpu"}}}},
          "sin_marca_pedido": {"p1": {"golero": {"v_1": {"escudo": True}}}}}
ok(S._marcas_del_pedido(CUERPO, "p1", "golero") == {"v_1": {"escudo": "tpu"}},
   "el diseño que lo pidió lo recibe")
ok(S._marcas_del_pedido(CUERPO, "p1", "jugador") == {},
   "🔴 el OTRO diseño del mismo molde NO (era el caso del usuario: salió en los dos)")
ok(S._marcas_del_pedido(CUERPO, "p2", "golero") == {},
   "🔴 y otro molde tampoco, aunque el diseño se llame igual")
ok(S._marcas_del_pedido(CUERPO, "p1", "golero", "sin_marca_pedido") == {"v_1": {"escudo": True}},
   "«sin marca» viaja por su propio canal (son campos separados: ver [[marcas-proceso]])")

print("\n3 · LA GENERACIÓN Y LA FICHA LEEN LAS MISMAS")
# Si la tizada mirara una cosa y la ficha otra, el taller aplicaría un proceso que la tela no pidió.
_src = open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
_gm = _src[_src.index('@app.post("/api/generar_multi")'):]
ok('"editables_marca": _marcas_del_pedido(cuerpo, pid, dslug)' in _gm,
   "🔴 el motor recibe las del pedido")
ok('"editables_sin_marca": _marcas_del_pedido(cuerpo, pid, dslug, "sin_marca_pedido")' in _gm,
   "y las de «sin marca» también")
ok("marcas_ped=_marcas_del_pedido(cuerpo, _pf, _dsf)" in _gm,
   "la ficha técnica recibe las mismas")
_mg = _src[_src.index("def _molde_guia_ficha("):_src.index("@app.post(\"/api/generar_multi\")")]
ok("_editables_marca(prod" not in _mg and "_editables_sin_marca(prod" not in _mg,
   "🔴 y el molde guía de la ficha ya NO las saca del catálogo")

print("\n4 · LA PANTALLA NO LAS GUARDA EN EL MOLDE, Y «NUEVO PEDIDO» LAS BORRA")
_app = open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("const [marcasPedido, setMarcasPedido]" in _app, "viven con el pedido (`marcasPedido`)")
ok("'/api/productos/editable_marca'" not in _app,
   "🔴 elegir la marca ya NO escribe en el catálogo del molde (era la causa)")
ok("marcas_pedido: marcasPedido, sin_marca_pedido: sinMarcaPedido" in _app,
   "y viajan con el pedido al generar")
ok("setMarcasPedido({}); setSinMarcaPedido({})" in _app,
   "🔴 «Nuevo pedido» las deja en cero")
ok("marcasPedido, sinMarcaPedido," in _app,
   "y se recuerdan mientras ESE pedido siga abierto (sobreviven a recargar la página)")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("  OK: lo que no se sublima lo decide cada pedido, y nunca se hereda del anterior")
