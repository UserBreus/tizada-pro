# -*- coding: utf-8 -*-
"""
CONTRATO: EL NAVEGADOR ACOMODA LAS PIEZAS EN LA TELA IGUAL QUE EL SERVIDOR — `py verificar_navegador_nesting.py`

PLAN_NAVEGADOR.md, etapa 4, punto 1. El nesting por contorno (`nesting_contorno.anidar_contorno`)
tiene su traducción en `frontend/src/motor/nesting/contorno.js`. Acá se arman escenarios con
contornos REALES (el molde del camino B `entrada/prod_20260916_095236_ef99`, sólo lectura), se
corre el nesting de los dos lados sobre el MISMO JSON y se comparan las colocaciones EXACTAS:
misma cantidad de hojas, mismas piezas en el mismo orden en cada hoja, mismo ángulo, mismos
`cx`/`cy` (float igual), misma área y mismo consumo de tela.

⚠️ Lo que se compara con tolerancia y por qué: `bw`/`bh` (el bbox matemático de la pieza girada)
salen de `math.cos/sin`; la UCRT de Windows y V8 difieren en el último bit para 19 de los 360
grados enteros (medido 2026-09-17), así que en rotación «libre» se aceptan 1e-9 de diferencia
relativa. En los ángulos múltiplos de 90° coinciden bit a bit y la comparación es exacta. El área
usa `** 2` (pow) contra `k * k`: misma tolerancia.

Python corre SIEMPRE por el camino del contorno (`_mascara_contorno`): las piezas traen `base.cont`
y no traen `doc`, y `TIZADA_MASCARA_LEGACY` se quita del entorno. El navegador no tiene otro camino.

⚠️ No toca nada del usuario: `db` es un doble, la base apunta a un servidor inexistente, el molde
sólo se LEE y el fixture va a un temporal.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_AQUI = os.path.dirname(os.path.abspath(__file__))
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
os.environ.pop("TIZADA_MASCARA_LEGACY", None)          # el contorno, nunca el raster del documento
os.environ.pop("TIZADA_NESTING_SIN_BLOQUES", None)
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: None)
sys.modules["db"] = _falso
sys.path.insert(0, _AQUI)
import nesting_contorno as NC                 # noqa: E402

NODE = os.path.join(_AQUI, "frontend", "src", "motor", "pruebas", "nesting.mjs")
MOLDE = os.path.join(_AQUI, "entrada", "prod_20260916_095236_ef99", "desplegado", "m1.json")
MM = 2.83465
TOL = 1e-9


def _cont_de_json(c):
    c = dict(c)
    c["segmentos"] = [tuple(s) for s in c["segmentos"]]
    c["bbox_raw"] = tuple(c["bbox_raw"])
    c["bbox_mu"] = tuple(c["bbox_mu"])
    return c


def _piezas_de(talles, talle, copias, rotacion, molde="m1", solo=None, borde_mm=2.0):
    """Las piezas de un talle como las arma `generar_pedido` (una entrada por prenda y pieza):
    `w`/`h` = página de la pieza (contorno + 2·B), `base` = lo que lee `_mascara_contorno`."""
    out = []
    B = borde_mm * MM
    for nro in range(copias):
        for k, cont in enumerate(talles[talle]):
            if solo is not None and k not in solo:
                continue
            x0, y0, _, _ = cont["bbox_raw"]
            W, H = cont["w"], cont["h"]
            S = cont["user_unit"]
            base = {"cont": cont, "S": S, "x0": x0, "y0": y0, "B": B, "W": W, "Hp": H + 2 * B}
            out.append({"w": float(W) + 2 * float(B), "h": float(H + 2 * B), "base": base,
                        "pieza": f"Pieza {k + 1}", "talle": talle, "variante": None, "_molde": molde,
                        "etiqueta": f"{nro + 1:02d}", "rotacion": rotacion, "borde_cm": 0})
    return out


def armar_fixture():
    with open(MOLDE, encoding="utf-8") as fh:
        d = json.load(fh)
    talles = {t: [_cont_de_json(c) for c in lst] for t, lst in d["talles"].items()}
    # la config de producción real: mesa Principal 1,80 × 5 m, 5 mm de separación, 10 mm de
    # margen, resolución 4 mm (`TIZADA_RES_MM`), estrategias bl + bandas
    cfg = {"ancho_cm": 180, "altura_max_cm": 500, "espaciado_cm": 0.5,
           "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1},
           "resolucion_mm": 4.0, "estrategias": ["bl", "bandas"]}
    esc = []
    # A · un talle, 3 prendas, sin rotación: 21 piezas (> 15 → un orden, sólo bl) con geometrías
    #     repetidas → el camino de los BLOQUES
    esc.append({"nombre": "un talle × 3 prendas, sin rotación", "cfg": dict(cfg),
                "piezas": _piezas_de(talles, "M", 3, "ninguna")})
    # B · talles mezclados (M, 2XL, Sfem), rotación 180 (la del preset de producción)
    esc.append({"nombre": "tres talles, rotación 180", "cfg": dict(cfg),
                "piezas": _piezas_de(talles, "M", 1, "180") + _piezas_de(talles, "2XL", 1, "180")
                + _piezas_de(talles, "Sfem", 1, "180")})
    # C · pocas piezas (8 → 4 órdenes × 2 estrategias), rotación 90
    esc.append({"nombre": "8 piezas, rotación 90, todos los órdenes y estrategias", "cfg": dict(cfg),
                "piezas": _piezas_de(talles, "M", 1, "90", solo={0, 1, 2, 3, 4, 5})
                + _piezas_de(talles, "2XL", 1, "90", solo={0, 5})})
    # D · rotación libre cada 15° (grueso → fino, ndimage.rotate), 5 piezas
    esc.append({"nombre": "5 piezas, rotación libre cada 15°", "cfg": dict(cfg, paso_libre_grados=15),
                "piezas": _piezas_de(talles, "Sfem", 1, "libre", solo={0, 1, 3, 5, 6})})
    # E · pedido grande: 11 prendas de 3 talles → varias hojas, rotación 180
    esc.append({"nombre": "11 prendas de 3 talles, varias hojas, rotación 180", "cfg": dict(cfg),
                "piezas": _piezas_de(talles, "M", 5, "180") + _piezas_de(talles, "2XL", 3, "180")
                + _piezas_de(talles, "Sfem", 3, "180")})
    for e in esc:
        for i, p in enumerate(e["piezas"]):
            p["idx"] = i
    return {"escenarios": esc}


def correr_python(esc):
    piezas = copy.deepcopy(esc["piezas"])
    t = time.time()
    coloc, area = NC.anidar_contorno(piezas, dict(esc["cfg"]))
    seg = time.time() - t
    hojas = [[{"idx": c["pieza"]["idx"], "ang": c["ang"], "cx": c["cx"], "cy": c["cy"], "bw": c["bw"], "bh": c["bh"]}
              for c in h] for h in coloc]
    consumo = sum(max(c["cy"] + c["bh"] / 2 for c in h) for h in coloc if h)
    # la máscara de cada pieza: alto, ancho, celdas ocupadas y suma ponderada por posición (1-based)
    mascaras = {}
    for p in piezas:
        m = p["_mask"]
        flat = m.ravel().astype(np.int64)
        mascaras[str(p["idx"])] = [int(m.shape[0]), int(m.shape[1]), int(flat.sum()),
                                   int((flat * np.arange(1, flat.size + 1)).sum())]
    return {"segundos": seg, "area": area, "consumo": consumo, "hojas": hojas, "debug": dict(NC._DEBUG),
            "mascaras": mascaras}


def _cerca(a, b):
    return a == b or abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def comparar(py, js):
    """Lista de diferencias (vacía = iguales)."""
    dif = []
    for k, a in py["mascaras"].items():
        b = js["mascaras"].get(k)
        if a != b:
            dif.append(f"máscara de la pieza {k}: (alto, ancho, celdas, hash) {a} vs {b}")
            if len(dif) > 6:
                return dif
    if len(py["hojas"]) != len(js["hojas"]):
        dif.append(f"hojas: {len(py['hojas'])} vs {len(js['hojas'])}")
        return dif
    for hi, (hp, hj) in enumerate(zip(py["hojas"], js["hojas"])):
        if len(hp) != len(hj):
            dif.append(f"hoja {hi + 1}: {len(hp)} vs {len(hj)} piezas")
            continue
        for k, (a, b) in enumerate(zip(hp, hj)):
            for campo in ("idx", "ang", "cx", "cy"):
                if a[campo] != b[campo]:
                    dif.append(f"hoja {hi + 1} #{k}: {campo} {a[campo]!r} vs {b[campo]!r} (pieza {a['idx']}/{b['idx']})")
            for campo in ("bw", "bh"):
                if not _cerca(a[campo], b[campo]):
                    dif.append(f"hoja {hi + 1} #{k}: {campo} {a[campo]!r} vs {b[campo]!r}")
            if len(dif) > 12:
                return dif
    if not _cerca(py["area"], js["area"]):
        dif.append(f"área {py['area']!r} vs {js['area']!r}")
    if not _cerca(py["consumo"], js["consumo"]):
        dif.append(f"consumo {py['consumo']!r} vs {js['consumo']!r}")
    return dif


def main():
    tmp = tempfile.mkdtemp(prefix="verif_nesting_")
    try:
        fx = armar_fixture()
        f_in, f_out = os.path.join(tmp, "fixture.json"), os.path.join(tmp, "salida.json")
        with open(f_in, "w", encoding="utf-8") as fh:
            json.dump(fx, fh)
        print(f"· fixture: {len(fx['escenarios'])} escenarios · {os.path.getsize(f_in) / 1e6:.1f} MB")
        py = [correr_python(e) for e in fx["escenarios"]]
        t = time.time()
        rr = subprocess.run(["node", NODE, f_in, f_out], capture_output=True, text=True, encoding="utf-8", timeout=1800)
        t_node = time.time() - t
        if rr.returncode != 0:
            print("  Node falló:\n" + rr.stderr[-1500:])
            print("\n❌ CONTRATO ROTO — el nesting del navegador no corrió")
            return 1
        with open(f_out, encoding="utf-8") as fh:
            js = json.load(fh)["escenarios"]
        todo_ok = True
        t_py = t_js = 0.0
        for e, a, b in zip(fx["escenarios"], py, js):
            dif = comparar(a, b)
            ok = not dif
            todo_ok = todo_ok and ok
            t_py += a["segundos"]; t_js += b["segundos"]
            n = len(e["piezas"])
            print(f"  {'✓' if ok else '✗'} {e['nombre']}: {n} piezas · {len(a['hojas'])} hoja(s) · "
                  f"consumo {a['consumo'] / NC.CM:.1f} cm · Python {a['segundos']:.2f} s · navegador {b['segundos']:.2f} s"
                  f" · bloques/búsquedas {a['debug'].get('bloque')}/{a['debug'].get('fft')}"
                  f" vs {b['debug'].get('bloque')}/{b['debug'].get('fft')}")
            for d in dif[:12]:
                print("      " + d)
        print(f"  tiempo total: Python {t_py:.2f} s · navegador {t_js:.2f} s (proceso Node entero {t_node:.2f} s)")
        print()
        print("✅ CONTRATO VERDE — el navegador acomoda las piezas exactamente como el servidor" if todo_ok
              else "❌ CONTRATO ROTO — el nesting del navegador difiere del servidor")
        return 0 if todo_ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
