# -*- coding: utf-8 -*-
"""CONTRATO DE NOMBRAR UNA PIEZA DEL CAMINO B — `py verificar_nombrar_con_diseno.py`

En el camino de siempre, nombrar una pieza RE-ARMA el registro entero (`alta_plantilla_manual`):
hace falta, porque hay que emparejar la pieza del talle que se está mirando con su homóloga en los
otros, y eso se resuelve por forma y posición.

En el camino B eso no sólo sobra: **rompe**. El molde tiene varias mesas (una por pieza) y los
talles son capas de la misma mesa, así que la correspondencia ya está resuelta desde el alta.
`alta_plantilla_manual` asume UNA sola mesa y volvería a emparejar por forma piezas que ya estaban
correctamente pareadas — y con el `mesa=None` que devuelve el visor del camino B, directamente
revienta. Acá nombrar es cambiar la clave de un dict, y eso es lo que se verifica.

⚠️ No toca nada del usuario: trabaja sobre un registro sintético en memoria y no abre la base.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import motor_pedido as MP           # noqa: E402
import piezas_con_diseno as PD      # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


TALLES = ["0", "2", "4", "6", "8", "10", "12", "14", "16",
          "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL", "7XL"]


def registro(n=9):
    """Como lo deja `alta_molde_con_diseno`: n piezas (una por mesa) × 20 talles, con nombres
    provisorios y los DOS índices — `pieza_idx` correlativo del talle, `idx_mesa` = 0 porque cada
    pieza es la única de su mesa."""
    reg = {}
    for i in range(n):
        reg[f"Pieza {i + 1}"] = {
            t: {"mesa": i + 1, "pieza_idx": i, "idx_mesa": 0,
                "w_cm": 30.0 + i, "h_cm": 40.0 + i, "bbox_mu": [0, 0, 100 + i, 200 + i],
                "ancla": {"x": 50.0, "y": 190.0, "size_pt": 8.5, "fuente": "Arial-BoldMT"}}
            for t in TALLES}
    return reg


print("CONTRATO DE NOMBRAR — molde con el diseño adentro\n")

# ══ 1. NOMBRAR UNA PIEZA NO TOCA NADA MÁS ════════════════════════════════════════════════════
print("1 · NOMBRAR CAMBIA EL NOMBRE Y SÓLO EL NOMBRE")
reg = registro()
antes = {n: dict(v) for n, v in reg.items()}
reg2, ren = PD.renombrar(reg, mesa=4, idx_mesa=0, nombre="Frente")
ok(ren == {"Pieza 4": "Frente"}, f"renombró {ren}, esperaba sólo 'Pieza 4' → 'Frente'")
ok("Frente" in reg2 and "Pieza 4" not in reg2, "la pieza no quedó con el nombre nuevo")
ok(len(reg2) == 9, f"el registro quedó con {len(reg2)} piezas, tenía 9")
ok(len(reg2["Frente"]) == len(TALLES),
   f"🔴 la pieza renombrada quedó con {len(reg2['Frente'])} talles, tenía {len(TALLES)}")
ok(reg2["Frente"] == antes["Pieza 4"],
   "🔴 al renombrar se tocó la GEOMETRÍA de la pieza (mesa/idx_mesa/pieza_idx/bbox/ancla)")
_otras_igual = all(reg2[n] == antes[n] for n in reg2 if n != "Frente")
ok(_otras_igual, "🔴 renombrar una pieza cambió los datos de las OTRAS")
print(f"    OK    'Pieza 4' → 'Frente' en los {len(TALLES)} talles, con su geometría intacta")

print("\n1b · Y EL ORDEN DE LAS PIEZAS SE CONSERVA")
# De ese orden salen los `id_en_molde` con los que se numeran las piezas en la base: si el
# renombrado reordenara, las piezas cambiarían de id al ponerles nombre.
ok(list(reg2.keys()) == ["Pieza 1", "Pieza 2", "Pieza 3", "Frente",
                         "Pieza 5", "Pieza 6", "Pieza 7", "Pieza 8", "Pieza 9"],
   f"🔴 el orden cambió: {list(reg2.keys())}")
print("    OK    la pieza renombrada se queda en su lugar")

# ══ 2. SE ENCUENTRA POR (mesa, idx_mesa), QUE NO DEPENDE DEL TALLE ═══════════════════════════
print("\n2 · LA PIEZA SE UBICA POR (mesa, idx_mesa)")
reg3, _ = PD.renombrar(registro(), mesa=1, idx_mesa=0, nombre="Espalda")
ok("Espalda" in reg3 and reg3["Espalda"]["M"]["mesa"] == 1, "no se ubicó la pieza de la mesa 1")
for _mesa, _idx in ((99, 0), (1, 5)):
    try:
        PD.renombrar(registro(), mesa=_mesa, idx_mesa=_idx, nombre="X")
        FALLOS.append(f"2. renombró una pieza que no existe (mesa {_mesa}, idx {_idx})")
    except ValueError:
        pass
print("    OK    encuentra la que corresponde y avisa si no existe")

# ══ 3. DOS PIEZAS NO PUEDEN QUEDAR CON EL MISMO NOMBRE ═══════════════════════════════════════
print("\n3 · 🔴 REPETIR UN NOMBRE NO PUEDE PERDER UNA PIEZA")
# El registro es un dict POR NOMBRE: dos piezas con el mismo nombre colapsan y una desaparece,
# sin error. Por eso el nombre final lo decide la MISMA regla del camino A.
reg4, _ = PD.renombrar(registro(), mesa=1, idx_mesa=0, nombre="Manga")
reg4, ren4 = PD.renombrar(reg4, mesa=2, idx_mesa=0, nombre="Manga")
ok(len(reg4) == 9, f"🔴 quedaron {len(reg4)} piezas: se perdió una al repetir el nombre")
_mangas = sorted(n for n in reg4 if n.startswith("Manga"))
ok(len(_mangas) == 2 and len(set(_mangas)) == 2,
   f"las dos piezas llamadas «Manga» no quedaron desambiguadas: {_mangas}")
ok(reg4[_mangas[0]]["M"]["mesa"] != reg4[_mangas[1]]["M"]["mesa"],
   "las dos «Manga» apuntan a la misma mesa (se pisaron)")
print(f"    OK    dos «Manga» conviven como {_mangas}, con la regla de siempre")

print("\n3b · Y LA REGLA ES LA DEL CAMINO A, NO UNA PROPIA")
_esperado = MP.nombres_normalizados([{"idx": 0, "nombre": "Manga"}, {"idx": 1, "nombre": "Manga"}])
ok(sorted(_esperado.values()) == _mangas,
   f"🔴 el renombrado numera distinto que `nombres_normalizados`: {sorted(_esperado.values())} vs {_mangas}")
print(f"    OK    numera igual que el camino A ({sorted(_esperado.values())})")

# ══ 4. NO SE PASA POR alta_plantilla_manual ══════════════════════════════════════════════════
print("\n4 · 🔴 NO SE RE-ARMA EL REGISTRO POR EL CAMINO A")
_real = MP.alta_plantilla_manual
_llamadas = []
MP.alta_plantilla_manual = lambda *a, **k: _llamadas.append(a) or (_ for _ in ()).throw(
    AssertionError("se llamó a alta_plantilla_manual"))
try:
    PD.renombrar(registro(), mesa=3, idx_mesa=0, nombre="Cuello")
except AssertionError:
    pass
finally:
    MP.alta_plantilla_manual = _real
ok(not _llamadas,
   "🔴 nombrar una pieza del camino B pasó por `alta_plantilla_manual` — eso RE-ARMA el registro "
   "asumiendo una sola mesa y emparejando los talles por forma: destruye el alta exacta")
print("    OK    el registro no se re-arma: sólo cambia la clave")

# ══ 5. LO QUE NO SE PUEDE HACER ══════════════════════════════════════════════════════════════
print("\n5 · CASOS BORDE")
for _n, _desc in ((" ", "un nombre en blanco"), ("", "un nombre vacío"), (None, "sin nombre")):
    try:
        PD.renombrar(registro(), mesa=1, idx_mesa=0, nombre=_n)
        FALLOS.append(f"5. aceptó {_desc}")
    except ValueError:
        pass
try:
    PD.renombrar({}, mesa=1, idx_mesa=0, nombre="Frente")
    FALLOS.append("5. aceptó renombrar en un molde sin piezas")
except ValueError:
    pass
_r, _ren = PD.renombrar(registro(), mesa=1, idx_mesa=0, nombre="Pieza 1")
ok(_ren == {}, "renombrar una pieza con el nombre que ya tenía igual reporta un cambio")
print("    OK    nombre vacío, molde vacío y «el mismo nombre» se manejan sin romper nada")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — nombrar es renombrar: nada más se mueve")
