# -*- coding: utf-8 -*-
"""CONTRATO: EN UN MOLDE CON DISEÑO, LA PIEZA i ES LA MISMA EN TODOS LOS TALLES
`py verificar_orden_talles_camino_b.py [ruta.ai]`

🔴 EL BUG (2026-09-16, «BUZO CON CIERRE VOLEY»). El usuario: *«cuando nombre una de estas piezas en
el sistema se nombran las otras. ejemplo nombro las verdes y se nombran las naranjas»*.

Todo el camino B descansa en que la pieza *i* de una mesa es la misma en todos los talles (registro,
«homólogas» del visor, nombrado, configuraciones guardadas, etiqueta del archivo). Pero *i* salía
del ORDEN EN QUE ESTÁ DIBUJADO cada talle, y en el buzo los 10 talles femeninos traen las dos piezas
curvas (51 × 10,5 cm, una girada) al revés que los otros 20: al tocar la verde se elegía la naranja
en esos talles, y la tela, la etiqueta y la variable de una iban a la otra.

Ahora `piezas_con_diseno.canonizar_orden` pone las piezas de cada talle en el orden del talle de
referencia, emparejadas por SUPERPOSICIÓN (la misma regla del camino A).

Lo que se verifica:
  1. La regla pura, con contornos armados a mano: un talle cruzado se endereza; con el dibujo en
     orden no cambia NADA; un talle con otra cantidad de piezas no se toca; sin superposición cada
     pieza conserva su número.
  2. Con el archivo real (si está): tras el alta, cada pieza del registro queda del MISMO LADO de la
     mesa en los 30 talles, y el visor no rotula ninguna pieza con el nombre de otra.
  3. Las versiones que obligan a rehacer lo guardado con el orden viejo subieron (contornos, decisión
     de la etiqueta, caché del desplegado, visor guardado).

⚠️ No toca nada del usuario: el archivo se copia a un temporal y un test no toca la base.
"""
import io
import os
import re
import shutil
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.chdir(AQUI)
sys.modules.setdefault("db", types.ModuleType("db"))       # un test no toca MSSQL

import piezas_con_diseno as PD      # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\user2\Downloads\BUZO CON CIERRE VOLEY .ai"
FALLAS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLAS.append(msg)


def pz(x0, y0, x1, y1, etiqueta):
    return {"bbox_mu": [x0, y0, x1, y1], "id": etiqueta}


def ids(lista):
    return [p["id"] for p in lista]


def main():
    print("CONTRATO — LA PIEZA i ES LA MISMA EN TODOS LOS TALLES (camino B)\n")

    print("1 · LA REGLA, CON CONTORNOS ARMADOS A MANO")
    derecha, izquierda, frente = (3000, 200, 4500, 500), (800, 200, 2200, 500), (100, 1000, 900, 2000)
    conts = {
        "M":    [pz(*frente, "frente"), pz(*derecha, "der"), pz(*izquierda, "izq")],
        "L":    [pz(*frente, "frente"), pz(3010, 190, 4520, 510, "der"), pz(790, 190, 2210, 510, "izq")],
        # el talle femenino dibujó las dos curvas AL REVÉS
        "Mfem": [pz(*frente, "frente"), pz(790, 200, 2210, 500, "izq"), pz(2990, 200, 4510, 500, "der")],
        # otra cantidad de piezas: no se puede expresar un hueco en una lista → no se toca
        "0":    [pz(700, 200, 2100, 500, "izq"), pz(*frente, "frente")],
    }
    out, cambio = PD.canonizar_orden(conts, ["M", "L", "Mfem", "0"])
    ok(ids(out["Mfem"]) == ["frente", "der", "izq"], f"🔴 el talle cruzado se endereza ({ids(out['Mfem'])})")
    ok(cambio, "…y avisa que cambió (lo guardado por índice con el orden viejo no se reusa)")
    ok(ids(out["M"]) == ["frente", "der", "izq"] and ids(out["L"]) == ["frente", "der", "izq"],
       "los talles que ya venían en orden quedan igual")
    ok(ids(out["0"]) == ["izq", "frente"], "un talle con otra cantidad de piezas no se toca")
    en_orden = {k: v for k, v in conts.items() if k in ("M", "L")}
    out2, cambio2 = PD.canonizar_orden(en_orden, ["M", "L"])
    ok(not cambio2 and ids(out2["L"]) == ["frente", "der", "izq"], "con el dibujo en orden no cambia NADA")
    lejos = {"A": [pz(0, 0, 10, 10, "a0"), pz(20, 0, 30, 10, "a1")],
             "B": [pz(500, 500, 510, 510, "b0"), pz(600, 500, 610, 510, "b1")]}
    out3, cambio3 = PD.canonizar_orden(lejos, ["A", "B"])
    ok(not cambio3 and ids(out3["B"]) == ["b0", "b1"], "sin superposición, cada pieza conserva su número")
    empate = {"A": [pz(*derecha, "der"), pz(*izquierda, "izq")],
              "B": [pz(*izquierda, "izq"), pz(*derecha, "der")]}
    out4, _ = PD.canonizar_orden(empate, ["A", "B"])
    ok(ids(out4["A"]) == ["der", "izq"] and ids(out4["B"]) == ["der", "izq"],
       "con la misma cantidad, la referencia es el PRIMER talle del archivo (determinista)")

    print("\n2 · CON EL ARCHIVO REAL")
    if not os.path.exists(ORIG):
        print(f"    ⚠️    no está el archivo de prueba ({ORIG}): se saltea")
    else:
        tmp = tempfile.mkdtemp(prefix="verif_orden_b_")
        try:
            C = os.path.join(tmp, "plantilla.ai")
            shutil.copy2(ORIG, C)
            alta = PD.alta_molde_con_diseno(C)
            PD.marcar(C, True)
            reg = alta["registro"]
            ancho_mesa = max(inf["bbox_mu"][2] for por_t in reg.values() for inf in por_t.values())
            mixtas = []
            for nom, por_t in reg.items():
                lados = {("der" if (inf["bbox_mu"][0] + inf["bbox_mu"][2]) / 2 > ancho_mesa * 0.3 else "izq")
                         for inf in por_t.values()}
                # sólo miden las piezas que no cruzan el umbral (una pieza centrada no dice nada)
                if len(lados) > 1 and all(abs((inf["bbox_mu"][0] + inf["bbox_mu"][2]) / 2 - ancho_mesa * 0.3) > 300
                                          for inf in por_t.values()):
                    mixtas.append(nom)
            ok(not mixtas, f"🔴 cada pieza del registro queda del MISMO LADO de la mesa en los "
                           f"{len(alta['talles'])} talles{'' if not mixtas else f' — cruzadas: {mixtas}'}")
            cruz = 0
            for tl, vi in (alta.get("visor") or {}).items():
                pos = {nom: por_t[tl]["pieza_idx"] for nom, por_t in reg.items() if tl in por_t}
                por_idx = {v: k for k, v in pos.items()}
                for p in vi["piezas"]:
                    nom = por_idx.get(p["idx"])
                    if nom is None:
                        continue
                    b = reg[nom][tl]["bbox_mu"]
                    ref = reg[nom][next(iter(reg[nom]))]["bbox_mu"]
                    # la pieza que el visor rotula con ese nombre se superpone con la de ese nombre
                    ix = max(0, min(b[2], ref[2]) - max(b[0], ref[0]))
                    iy = max(0, min(b[3], ref[3]) - max(b[1], ref[1]))
                    cruz += (ix * iy == 0)
            ok(cruz == 0, f"el visor no rotula ninguna pieza con el nombre de otra ({cruz})")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n3 · LO GUARDADO CON EL ORDEN VIEJO SE REHACE")
    ok(PD._V_CONTORNOS >= 4, f"versión de contornos ≥ 4 ({PD._V_CONTORNOS})")
    ok(PD._V_ETQ >= 2, f"versión de la decisión de la etiqueta ≥ 2 ({PD._V_ETQ})")
    srv = io.open(os.path.join(AQUI, "servidor.py"), encoding="utf-8").read()
    ok('_CACHE_DESPL_VERSION = "v466d"' in srv or re.search(r'_CACHE_DESPL_VERSION = "v4[6-9]\d', srv) is not None,
       "la caché del desplegado por archivo cambió de versión")
    ok('_VISOR_JSON = "visor_contornos.v4.json"' in srv and "_refrescar_registro_b(pid)" in srv,
       "el visor guardado tiene versión y, al rehacerse, pone al día la geometría del registro")

    print()
    print("✅ CONTRATO VERDE — la pieza i es la misma en todos los talles" if not FALLAS
          else f"❌ CONTRATO ROTO — {len(FALLAS)} falla(s)")
    return 1 if FALLAS else 0


if __name__ == "__main__":
    sys.exit(main())
