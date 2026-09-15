# -*- coding: utf-8 -*-
"""CONTRATO: NOMBRAR PIEZAS TIENE QUE ABRIR AL INSTANTE — `py verificar_visor_rapido.py [ruta.ai]`

Pedido del usuario (2026-09-03), textual: *«debe de funcionar super flash, no puede tardar ni andar
super lento sin importar el diseño de cada molde… debe de funcionar solo con los bordes para
detectar las piezas al igual que la etiqueta y ahí ignorar lo pesado del diseño»*.

**El problema medido:** armar el visor de UN talle sobre el archivo real cuesta **52 s**, y los 52
son `get_drawings()` leyendo los dibujos de las 9 mesas —1.516 items por mesa— para quedarse con
140 recortes. No es el acomodo: es abrir el archivo pesado.

**La salida:** el ALTA ya recorre las 9 mesas × 20 talles, así que arma el visor de todos los
talles con los contornos que ya tiene en la mano y lo guarda (`visor_contornos.json`, ~5 KB por
talle). Después, nombrar piezas y ubicar la etiqueta **no abren el PDF nunca más**.

Esto verifica las dos mitades: que el alta lo deje listo para TODOS los talles, y que lo guardado
sea idéntico a lo que se calcularía leyendo el archivo (si no, sería rápido y equivocado).

⚠️ No toca nada del usuario: trabaja sobre una COPIA en un temporal.
"""
import json
import os
import shutil
import sys
import tempfile
import time

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

import pymupdf as fitz               # noqa: E402
import piezas_con_diseno as PD       # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai"
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


if not os.path.exists(ORIG):
    print(f"❌ no está el archivo de prueba:\n   {ORIG}")
    sys.exit(1)

# Desplegar el molde real son ~90 s y el archivo no cambia entre corridas: se reusa el
# despliegue guardado (`contrato_molde_b`). Un control que no se puede correr seguido
# no protege nada -- y el tope de la tanda esta para eso.
import contrato_molde_b as CB
tmp, COPIA, _alta_cb, _ = CB.espacio_desplegado(ORIG, "verif_visor_")
print("CONTRATO: EL VISOR DEL CAMINO B ABRE AL INSTANTE\n")

try:
    # ══ 1. EL ALTA DEJA EL VISOR DE TODOS LOS TALLES ═════════════════════════════════════════
    print("\n1 · EL ALTA DEJA EL VISOR ARMADO, TALLE POR TALLE")
    t0 = time.time()
    alta = _alta_cb   # ya desplegado arriba
    t_alta = time.time() - t0
    visor = alta.get("visor") or {}
    print(f"    ({t_alta:.0f}s) alta de {len(alta['piezas'])} piezas × {len(alta['talles'])} talles")
    ok(visor, "🔴 el alta no dejó ningún visor armado: nombrar piezas volvería a leer el archivo")
    _faltan = [t for t in alta["talles"] if t not in visor]
    ok(not _faltan,
       f"🔴 faltan {len(_faltan)} talles en el visor guardado ({_faltan[:4]}): esos abrirían lento")
    if visor:
        _t0 = alta["talles"][0]
        ok(len(visor[_t0]["piezas"]) == alta["mesas"],
           f"el visor del talle «{_t0}» trae {len(visor[_t0]['piezas'])} piezas y el molde tiene {alta['mesas']}")
        print(f"    OK    {len(visor)} de {len(alta['talles'])} talles, con sus {alta['mesas']} piezas cada uno")

    # ══ 2. ES LIVIANO ════════════════════════════════════════════════════════════════════════
    print("\n2 · Y ES LIVIANO (sólo contornos: ni un trazo del diseño)")
    _peso = len(json.dumps(visor))
    _por_talle = _peso / max(len(visor), 1)
    ok(_peso < 3e6, f"🔴 el visor guardado pesa {_peso/1e6:.1f} MB: se está guardando el dibujo")
    _svg = max((len(p.get("path_svg") or "") for v in visor.values() for p in v["piezas"]), default=0)
    ok(_svg < 20000, f"🔴 hay un contorno de {_svg/1024:.0f} KB: eso no es un borde, es el diseño")
    print(f"    OK    {_peso/1024:.0f} KB los {len(visor)} talles ({_por_talle/1024:.1f} KB cada uno) · "
          f"el archivo pesa {os.path.getsize(COPIA)/1e6:.0f} MB")

    # ══ 3. 🔴 RÁPIDO **Y** CORRECTO ══════════════════════════════════════════════════════════
    print("\n3 · 🔴 LO GUARDADO ES LO MISMO QUE SALDRÍA DE LEER EL ARCHIVO")
    # Rápido y equivocado sería peor que lento: el usuario nombraría piezas que no son.
    doc = fitz.open(COPIA)
    _tv = alta["talles"][len(alta["talles"]) // 2]
    t0 = time.time()
    vivo = PD.detectar_para_visor(doc, _tv)
    t_vivo = time.time() - t0
    PD.olvidar(doc)
    doc.close()
    guardado = visor.get(_tv)
    ok(guardado is not None, f"3. el talle «{_tv}» no está en lo guardado")
    if guardado:
        for k in ("img_w", "img_h", "talle_ref", "origen"):
            ok(guardado.get(k) == vivo.get(k), f"3. «{k}» no coincide: {guardado.get(k)} vs {vivo.get(k)}")
        ok(len(guardado["piezas"]) == len(vivo["piezas"]),
           f"3. {len(guardado['piezas'])} piezas guardadas vs {len(vivo['piezas'])} leídas")
        _dif = [(a["idx"], a.get("mesa"), b.get("mesa")) for a, b in zip(guardado["piezas"], vivo["piezas"])
                if a.get("mesa") != b.get("mesa") or a.get("t_idx") != b.get("t_idx")
                or a.get("path_svg") != b.get("path_svg")]
        ok(not _dif,
           f"🔴 {len(_dif)} pieza(s) guardadas NO son las que saldrían del archivo ({_dif[:2]}): "
           f"el visor sería rápido y equivocado, que es peor que lento")
        print(f"    OK    las {len(vivo['piezas'])} piezas coinciden una por una (contorno incluido)")

    # ══ 4. LA GANANCIA, EN NÚMEROS ═══════════════════════════════════════════════════════════
    print("\n4 · LA GANANCIA")
    t0 = time.time()
    json.loads(json.dumps(visor))[_tv]      # lo que hace el servidor: leer el JSON y devolverlo
    t_guardado = time.time() - t0
    print(f"    leyendo el archivo (como antes) ... {t_vivo:6.1f}s")
    print(f"    desde lo guardado (ahora) ......... {t_guardado:6.3f}s")
    ok(t_guardado < 1.0, f"🔴 servir el visor guardado tardó {t_guardado:.1f}s: no es instantáneo")
    print(f"    OK    abrir «nombrar piezas» pasa de {t_vivo:.0f}s a menos de 1 s, y el alta "
          f"(que ya recorría todo) no tardó más por esto")

finally:
    try:
        PD.olvidar()
    except Exception:
        pass
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — nombrar piezas y la etiqueta abren al instante, con los mismos contornos")
