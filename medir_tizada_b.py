# -*- coding: utf-8 -*-
"""MEDIDOR DE LA TIZADA DEL CAMINO B — `py medir_tizada_b.py [N_prendas] [ruta.ai]`

Arma un pedido de N prendas (ciclando talles) con el molde real, corre el motor + el aplanado
para el RIP y escribe cuánto tardó CADA etapa y cuánto pesa lo que salió. Es el número que dice
si una entrega del plan «tizada rápida» (2026-09-04) cumplió. Variables de entorno:
  TIZADA_HOJA_LEGACY=1        hoja de siempre (una copia de la pieza por prenda)
  TIZADA_APLANADO_TOTAL=1     aplanado inline de siempre
  MEDIR_COMPARAR=1            además arma la hoja legacy y compara el render (0 px distintos)
  MEDIR_SALIDA=<carpeta>      deja las hojas ahí (si no, temporal que se borra)

⚠️ No toca nada del usuario: copia del archivo en un temporal, `db` reemplazado por un doble.
"""
import os
import shutil
import sys
import tempfile
import time
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_f = types.ModuleType("db")
_f.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError("LA PRUEBA TOCÓ MSSQL")))
sys.modules.setdefault("db", _f)

import pymupdf as fitz               # noqa: E402
import motor_pedido as MP            # noqa: E402
import piezas_con_diseno as PD       # noqa: E402
from aplanar_rip import aplanar_para_rip   # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5
ORIG = next((a for a in sys.argv[1:] if a.lower().endswith((".ai", ".pdf"))),
            r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai")
FUENTES = os.path.join(_AQUI, "catalogo_fuentes")
NOMBRES = ["JUGADOR", "MESSI", "DI MARIA", "ALVAREZ", "ENZO", "MAC ALLISTER", "OTAMENDI", "ROMERO", "TAGLIAFICO", "MARTINEZ"]


def render(path, dpi=36):
    d = fitz.open(path)
    pms = [pg.get_pixmap(dpi=dpi, alpha=False) for pg in d]
    out = [(p.width, p.height, bytes(p.samples)) for p in pms]
    d.close()
    return out


def distintos(a, b):
    if len(a) != len(b):
        return -1
    tot = 0
    for (w1, h1, s1), (w2, h2, s2) in zip(a, b):
        if (w1, h1) != (w2, h2):
            return -1
        tot += sum(1 for i in range(0, len(s1), 3) if s1[i:i + 3] != s2[i:i + 3])
    return tot


def main():
    if not os.path.exists(ORIG):
        print("❌ no está el archivo:", ORIG); sys.exit(1)
    tmp = tempfile.mkdtemp(prefix="medir_tz_")
    salida_fija = os.environ.get("MEDIR_SALIDA")
    try:
        import json
        # Con MEDIR_SALIDA el alta se hace UNA vez y se reutiliza en las corridas siguientes
        # (el desplegado completo tarda 1-3 min; iterar sobre el motor no debería pagarlo).
        C = os.path.join(salida_fija or tmp, "plantilla.ai")
        _alta_json = C + ".alta.json"
        if salida_fija and os.path.exists(_alta_json) and PD.desplegado_listo(C):
            alta = json.load(open(_alta_json, encoding="utf-8"))
            print("alta reutilizada de", _alta_json)
        else:
            print(f"copiando el archivo ({os.path.getsize(ORIG)/1e6:.0f} MB)…")
            shutil.copy2(ORIG, C)
            t = time.time()
            alta = PD.alta_molde_con_diseno(C, procesos=max(2, (os.cpu_count() or 4) - 1))
            PD.marcar(C, True)
            print(f"alta (desplegado completo): {time.time()-t:.0f}s")
            if salida_fija:
                json.dump({"registro": alta["registro"], "talles": alta["talles"]}, open(_alta_json, "w", encoding="utf-8"))
        PD.marcar(C, True)               # la marca «camino B» (por si el alta se reutilizó)
        MP._DET_CACHE.clear()
        reg, talles = alta["registro"], alta["talles"]
        print(f"{len(reg)} piezas · {len(talles)} talles")
        pers = MP.extraer_personalizacion(C)
        # N prendas ciclando MEDIR_TALLES talles del medio (un pedido real repite talles: 5
        # camisetas suelen ser 2-3 talles; 100, unos 8), nombres y números distintos
        _k = int(os.environ.get("MEDIR_TALLES") or (3 if N <= 10 else 8))
        _ts = talles[len(talles)//2 - _k // 2: len(talles)//2 - _k // 2 + _k] or talles
        prendas = [{"talle": _ts[i % len(_ts)], "nombre": NOMBRES[i % len(NOMBRES)], "numero": str((i * 7) % 99 + 1),
                    "__variante": None} for i in range(N)]
        kw = dict(borde_corte={"activo": True, "ancho_mm": 2.0, "color": [0, 0, 0, 0.85], "alineacion": "fuera"},
                  etiqueta={"activo": True, "size_mm": 3.0, "mostrar": {"talle": True, "pieza": True, "numero": True},
                            "posiciones": {}, "align": "centro"},
                  config_nesting={"ancho_cm": 160, "altura_max_cm": 500, "espaciado_cm": 0.5,
                                  "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1}})
        rot = {p: "libre" if i % 3 == 0 else "180" for i, p in enumerate(reg)}   # mezcla de rotaciones

        def correr(sal, modo):
            os.makedirs(sal, exist_ok=True)
            t0 = time.time()
            res = MP.generar_pedido(C, None, reg, pers, prendas, FUENTES, sal, rotaciones=rot, modo_hoja=modo, **kw)
            t_motor = time.time() - t0
            hojas = [os.path.join(sal, h["archivo"]) for h in res["hojas"]]
            mb = sum(os.path.getsize(h) for h in hojas) / 1e6
            svg = sum(os.path.getsize(os.path.join(sal, pv)) for h in res["hojas"] for pv in h.get("previews", [])) / 1e6
            r0 = render(hojas[0]) if os.environ.get("MEDIR_COMPARAR") else None
            t1 = time.time()
            for h in hojas:
                aplanar_para_rip(h)
            t_rip = time.time() - t1
            mb2 = sum(os.path.getsize(h) for h in hojas) / 1e6
            r1 = render(hojas[0]) if os.environ.get("MEDIR_COMPARAR") else None
            print(f"\n[{modo}] motor {t_motor:.0f}s ({' · '.join(f'{k} {v:.0f}s' for k, v in res['tiempos'].items())})"
                  f" · aplanado RIP {t_rip:.0f}s · hoja {mb:.1f} MB → {mb2:.1f} MB · previews {svg:.1f} MB"
                  f" · validaciones ok: {all(v.get('ok') for v in res['validaciones'])}")
            if r0 is not None and r1 is not None:
                print(f"          aplanar no cambió un píxel: {'SÍ' if distintos(r0, r1) == 0 else 'NO (%s)' % distintos(r0, r1)}")
            return res, hojas, r0, time.time() - t0

        sal_p = os.path.join(salida_fija or tmp, "pike")
        res_p, hojas_p, rp, tt_p = correr(sal_p, "legacy" if os.environ.get("TIZADA_HOJA_LEGACY") else "pike")
        print(f"\n★ {N} prendas: TOTAL {tt_p:.0f}s  ({tt_p / N:.1f} s/prenda)")
        if os.environ.get("MEDIR_COMPARAR") and not os.environ.get("TIZADA_HOJA_LEGACY"):
            sal_l = os.path.join(salida_fija or tmp, "legacy")
            os.environ["TIZADA_APLANADO_TOTAL"] = "1"
            res_l, hojas_l, rl, tt_l = correr(sal_l, "legacy")
            del os.environ["TIZADA_APLANADO_TOTAL"]
            d = distintos(rp, rl) if (rp is not None and rl is not None) else None
            print(f"\n★ legacy {tt_l:.0f}s vs pike {tt_p:.0f}s · píxeles distintos entre las dos hojas (antes de aplanar): {d}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
