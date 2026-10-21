# -*- coding: utf-8 -*-
# CONTRATO_LENTO (MAPA 728): ~15 min con el optimizador; va con `correr_contratos.py --todos`
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

EL OPTIMIZADOR (MAPA 728): el navegador corre la búsqueda y los carriles EN VARIOS HILOS (`nesting/carriles.js`)
y Python en orden; tienen que dar lo mismo. Los escenarios usan un optimizador CHICO (`optimizar` = 3 carriles × 2
intentos: el carril 0 —lo de antes, pulido—, el 1 —desde la búsqueda— y uno mezclado) porque Python tarda; uno
usa 6 carriles para pasar por los dos juegos de giros. El mecanismo es el mismo que con los 16 de verdad.

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

# 🔴 LENTO (MAPA 728): con el optimizador, Python corre los carriles EN ORDEN y compacta con FFT (~15 min)
CONTRATO_LENTO = True

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


def _forma_cont(pts):
    """Un contorno SINTÉTICO (pt) para probar formas que no están en el molde: `pts` = polígono
    [(x, y)…] o `("circulo", r)`. Mismo formato que `desplegado/m1.json` (segmentos m/l/c/h)."""
    if isinstance(pts, tuple) and pts[0] == "circulo":
        r = pts[1]
        k = 0.5522847498 * r
        cx = cy = r
        seg = [["m", cx + r, cy],
               ["c", cx + r, cy + k, cx + k, cy + r, cx, cy + r],
               ["c", cx - k, cy + r, cx - r, cy + k, cx - r, cy],
               ["c", cx - r, cy - k, cx - k, cy - r, cx, cy - r],
               ["c", cx + k, cy - r, cx + r, cy - k, cx + r, cy],
               ["h"]]
        w = h = 2 * r
    else:
        seg = [["m", pts[0][0], pts[0][1]]] + [["l", x, y] for x, y in pts[1:]] + [["h"]]
        w = max(x for x, _ in pts) - min(x for x, _ in pts)
        h = max(y for _, y in pts) - min(y for _, y in pts)
    return {"segmentos": [tuple(x) for x in seg], "bbox_raw": (0.0, 0.0, w, h), "bbox_mu": (0.0, 0.0, w, h),
            "w": w, "h": h, "user_unit": 1.0}


def _piezas_forma(nombre, cont, n, rotacion, borde_mm=2.0):
    """`n` piezas iguales de un contorno sintético (como las arma `generar_pedido`)."""
    B = borde_mm * MM
    W, H = cont["w"], cont["h"]
    out = []
    for k in range(n):
        base = {"cont": cont, "S": 1.0, "x0": 0.0, "y0": 0.0, "B": B, "W": W, "Hp": H + 2 * B}
        out.append({"w": float(W) + 2 * float(B), "h": float(H + 2 * B), "base": base, "pieza": nombre,
                    "talle": "U", "variante": None, "_molde": "sint", "etiqueta": f"{k + 1:02d}",
                    "rotacion": rotacion, "borde_cm": 0})
    return out


def armar_fixture():
    with open(MOLDE, encoding="utf-8") as fh:
        d = json.load(fh)
    talles = {t: [_cont_de_json(c) for c in lst] for t, lst in d["talles"].items()}
    # la config de producción real: mesa Principal 1,80 × 5 m, 5 mm de separación, 10 mm de
    # margen, resolución 4 mm (`TIZADA_RES_MM`), estrategias bl + bandas
    cfg = {"ancho_cm": 180, "altura_max_cm": 500, "espaciado_cm": 0.5,
           "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1},
           "resolucion_mm": 4.0, "estrategias": ["bl", "bandas"],
           "optimizar": {"carriles": 3, "intentos": 2}}     # MAPA 728: chico, ver arriba
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
    # C' · las mismas, con 6 carriles: pasan los dos juegos de giros (todos y sólo 0/180) por los carriles mezclados
    esc.append({"nombre": "8 piezas, giro 90, optimizador con 6 carriles", "cfg": dict(cfg, optimizar={"carriles": 6, "intentos": 4}),
                "piezas": esc[-1]["piezas"]})
    # D · rotación libre cada 15° (grueso → fino, ndimage.rotate), 5 piezas
    esc.append({"nombre": "5 piezas, rotación libre cada 15°", "cfg": dict(cfg, paso_libre_grados=15),
                "piezas": _piezas_de(talles, "Sfem", 1, "libre", solo={0, 1, 3, 5, 6})})
    # E · pedido grande: 11 prendas de 3 talles → varias hojas, rotación 180
    esc.append({"nombre": "11 prendas de 3 talles, varias hojas, rotación 180", "cfg": dict(cfg),
                "piezas": _piezas_de(talles, "M", 5, "180") + _piezas_de(talles, "2XL", 3, "180")
                + _piezas_de(talles, "Sfem", 3, "180")})
    # F · COPIA QUE LLENA EL ANCHO (MAPA 701): tres filas sueltas con 19, 3 y 1 copias. Dos piezas
    #     chicas por fila → entran varias a lo ancho: 19 = mesa llena ×N + resto; 3 = una mesa de 3
    #     (no llena: se achica); 1 = sin repetir.
    _f = []
    for fila, cop in ((0, 19), (1, 3), (2, 1)):
        for p in _piezas_de(talles, "M", 1, "180", solo={4, 5}):
            p["_fila"], p["_copias"] = fila, cop
            _f.append(p)
    esc.append({"nombre": "copia: 19, 3 y 1 copias (mejor acomodo)", "cfg": dict(cfg, por_fila=True), "piezas": _f})
    # G · COPIA CON GIRO 90: las copias en una mesa del largo máximo que se repite (MAPA 720; antes la
    #     franja del alto de la pieza, 703); una pieza sola de 13 copias y dos piezas de 7
    _g = []
    for fila, cop, solo in ((0, 13, {5}), (1, 7, {4, 5})):
        for p in _piezas_de(talles, "M", 1, "90", solo=solo):
            p["_fila"], p["_copias"] = fila, cop
            _g.append(p)
    esc.append({"nombre": "copia con giro 90: el mejor acomodo de las copias", "cfg": dict(cfg, por_fila=True), "piezas": _g})
    # L · TALLES SEPARADOS EN LA MISMA MESA (MAPA 710): M y 2XL juntos (grupo 1), Sfem aparte (2); cada
    #     bloque solo y apilados, con las líneas punteadas (`cortes`) en `mesas`
    _l = []
    for t, g in (("M", 1), ("2XL", 1), ("Sfem", 2)):
        for p in _piezas_de(talles, t, 2, "180"):
            p["_grupo_mesa"] = g
            _l.append(p)
    esc.append({"nombre": "talles separados en la misma mesa", "cfg": dict(cfg, por_talles_mesa=True, talles_mesa_modo="separados"), "piezas": _l})
    # H-K · FORMAS DE TODO TIPO (MAPA 706-708): el acomodo tiene que ser bueno con cualquier forma, no
    #     sólo con el banderín. Contornos sintéticos en cm: triángulo (banderín 30×45), rectángulo
    #     (bandera 60×90), círculo Ø40 y una mezcla.
    cm = NC.CM
    tri = _forma_cont([(0, 0), (30 * cm, 0), (15 * cm, 45 * cm)])
    rec = _forma_cont([(0, 0), (60 * cm, 0), (60 * cm, 90 * cm), (0, 90 * cm)])
    cir = _forma_cont(("circulo", 20 * cm))
    cfg_b = dict(cfg, ancho_cm=157, altura_max_cm=5000)
    esc.append({"nombre": "40 triángulos (banderín), giro 90", "cfg": cfg_b,
                "piezas": _piezas_forma("Banderin", tri, 40, "90")})
    esc.append({"nombre": "24 rectángulos 60×90, giro 90", "cfg": cfg_b,
                "piezas": _piezas_forma("Bandera", rec, 24, "90")})
    esc.append({"nombre": "30 círculos Ø40, giro 90", "cfg": cfg_b,
                "piezas": _piezas_forma("Circulo", cir, 30, "90")})
    esc.append({"nombre": "mezcla: 16 triángulos + 8 rectángulos + 10 círculos", "cfg": cfg_b,
                "piezas": _piezas_forma("Banderin", tri, 16, "90") + _piezas_forma("Bandera", rec, 8, "90")
                + _piezas_forma("Circulo", cir, 10, "90")})
    # P · EL PATRÓN (MAPA 736): piezas iguales → el dibujo que se repite, calculado con todas juntas, compite con
    #     el acomodo pieza por pieza. 60 círculos (gana el patrón) y una unidad de DOS formas en proporción
    #     (20 triángulos + 10 rectángulos chicos = 2 + 1 por unidad)
    esc.append({"nombre": "60 círculos Ø40, giro 90 (el patrón)", "cfg": cfg_b,
                "piezas": _piezas_forma("Circulo", cir, 60, "90")})
    rec_ch = _forma_cont([(0, 0), (30 * cm, 0), (30 * cm, 20 * cm), (0, 20 * cm)])
    esc.append({"nombre": "patrón de dos formas: 20 triángulos + 10 rectángulos, giro 90", "cfg": cfg_b,
                "piezas": _piezas_forma("Banderin", tri, 20, "90") + _piezas_forma("Chico", rec_ch, 10, "90")})
    # M · COPIA CON EL MISMO MOLDE EN DOS DISEÑOS (MAPA 717): dos filas de banderines (33 y 34 copias) con
    #     la MISMA geometría y distinto diseño → mesas MEZCLADAS que se repiten (`filas` en `mesas`); y una
    #     tercera fila de otra forma, que va sola
    _m = []
    for fila, (dis, cop, forma) in enumerate((("jugador", 33, tri), ("golero", 34, tri), ("jugador", 5, rec))):
        for p in _piezas_forma("Banderin" if forma is tri else "Bandera", forma, 1, "90"):
            p.update(_fila=fila, _copias=cop, _diseno=dis, _diseno_nombre=dis.upper())
            _m.append(p)
    esc.append({"nombre": "copia: mismo molde en dos diseños se mezcla", "cfg": dict(cfg_b, por_fila=True), "piezas": _m})
    # N · SEPARAR DISEÑOS (MAPA 717): lo mismo con «Separar diseños» (cada diseño en sus mesas) y el modo
    #     normal separando diseños
    _n = [dict(p) for p in _m]
    esc.append({"nombre": "copia separando diseños", "cfg": dict(cfg_b, por_fila=True, separar_disenos=True), "piezas": _n})
    _o = []
    for dis, n in (("jugador", 10), ("golero", 12)):
        for p in _piezas_forma("Banderin", tri, n, "90"):
            p.update(_diseno=dis, _diseno_nombre=dis.upper())
            _o.append(p)
    esc.append({"nombre": "normal separando diseños", "cfg": dict(cfg_b, separar_disenos=True), "piezas": _o})
    for e in esc:
        for i, p in enumerate(e["piezas"]):
            p["idx"] = i
    return {"escenarios": esc}


def correr_python(esc):
    piezas = copy.deepcopy(esc["piezas"])
    t = time.time()
    mesas = None
    if esc["cfg"].get("por_fila") or esc["cfg"].get("por_talles_mesa") or esc["cfg"].get("separar_disenos"):
        coloc, area, mesas = NC.anidar_por_fila(piezas, dict(esc["cfg"]))
    else:
        coloc, area = NC.anidar_contorno(piezas, dict(esc["cfg"]))
    seg = time.time() - t
    hojas = [[{"idx": c["pieza"]["idx"], "ang": c["ang"], "cx": c["cx"], "cy": c["cy"], "bw": c["bw"], "bh": c["bh"]}
              for c in h] for h in coloc]
    consumo = sum(max(c["cy"] + c["bh"] / 2 for c in h) for h in coloc if h)
    # la máscara de cada pieza: alto, ancho, celdas ocupadas y suma ponderada por posición (1-based)
    mascaras = {}
    for p in piezas:
        # con la Copia mezclada (MAPA 717) las filas se acomodan con copias de la primera: la pieza de la
        # fila nunca se prepara y no tiene máscara propia (en los dos motores)
        if "_mask" not in p:
            mascaras[str(p["idx"])] = None
            continue
        m = p["_mask"]
        flat = m.ravel().astype(np.int64)
        mascaras[str(p["idx"])] = [int(m.shape[0]), int(m.shape[1]), int(flat.sum()),
                                   int((flat * np.arange(1, flat.size + 1)).sum())]
    comun = None
    return {"segundos": seg, "area": area, "consumo": consumo, "hojas": hojas, "debug": dict(NC._DEBUG),
            "mascaras": mascaras, "mesas": mesas, "comun": comun}


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
    if py.get("mesas") != js.get("mesas"):
        dif.append(f"mesas {py.get('mesas')!r} vs {js.get('mesas')!r}")
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
            if a.get("comun") is not None:
                print(f"      acomodo común solo: {a['comun'] / NC.CM:.1f} cm → ahora {a['consumo'] / NC.CM:.1f} cm"
                      f" ({100 * (a['comun'] - a['consumo']) / a['comun']:.1f} % menos tela)")
                if a["consumo"] > a["comun"] + 1e-6:
                    print("      ✗ el acomodo nuevo NUNCA puede gastar más que el común")
                    todo_ok = False
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
