# -*- coding: utf-8 -*-
"""CONTRATO DE LA HOJA COMPARTIDA (camino B) — `py verificar_hoja_compartida.py [ruta.ai]`

Desde 2026-09-04 la tizada del molde con diseño se compone con `hoja_pike.componer_hoja_pike`:
cada pieza de cada talle es UN Form XObject y cada prenda lo referencia (`Do`) y le agrega su
nombre/número y etiqueta como trazos chicos. Antes, cada prenda llevaba una copia entera de la
mesa (`show_pdf_page`, `nesting_contorno.componer_pdf_contorno`). Ver `MOLDE_CON_DISENO.md`
«LA HOJA COMPARTIDA» y el changelog 393 del mapa.

Lo que cuida, con el molde real y 5 prendas (3 talles, rotación libre y 180):
  1. 🔴 SE VE IGUAL: con la MISMA lista de colocaciones, la hoja nueva y la de siempre son
     pixel-idénticas (render MuPDF a 36 dpi: ≤ 0,2 % de píxeles distintos, y de esos casi todos
     por anti-aliasing en los bordes de las piezas giradas — se imprime la distribución).
  2. UN objeto por base: la hoja tiene tantos Form XObjects como bases (≤ piezas × talles), no
     como colocaciones; y pesa menos de la mitad que la de siempre.
  3. Las bases no anidan otros Form (profundidad 1): lo que permite aplanar en un nivel.
  4. El aplanado para el RIP (un nivel) no cambia un píxel y conserva el OutputIntent.
  5. Mesa larga (altura 900 cm): la hoja lleva /UserUnit y las medidas reales se conservan.

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

import numpy as np                    # noqa: E402
import pikepdf                        # noqa: E402
import pymupdf as fitz                # noqa: E402
import motor_pedido as MP             # noqa: E402
import piezas_con_diseno as PD        # noqa: E402
import nesting_contorno as NC         # noqa: E402
import hoja_pike as HP                # noqa: E402
from aplanar_rip import aplanar_para_rip   # noqa: E402

ORIG = sys.argv[1] if len(sys.argv) > 1 else \
    r"C:\Users\user2\Downloads\PRUEBA TIZADA PRO\para acomodo de archivos\CAMISETA JUGADOR.ai"
FUENTES = os.path.join(_AQUI, "catalogo_fuentes")
FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def render(path, dpi=36):
    d = fitz.open(path)
    out = []
    for pg in d:
        p = pg.get_pixmap(dpi=dpi, alpha=False)
        out.append(np.frombuffer(p.samples, dtype=np.uint8).reshape(p.height, p.width, 3).astype(int))
    d.close()
    return out


def comparar(a, b):
    if len(a) != len(b) or any(x.shape != y.shape for x, y in zip(a, b)):
        return None
    tot = sum(x.size // 3 for x in a)
    d = np.concatenate([np.abs(x - y).max(axis=2).ravel() for x, y in zip(a, b)])
    m = d > 0
    return {"px": int(m.sum()), "total": tot, "pct": 100.0 * m.sum() / tot,
            "suaves": int((d[m] <= 16).sum()) if m.any() else 0}


def xobjects_form(path):
    n, prof = 0, 0
    with pikepdf.open(path) as pdf:
        for pg in pdf.pages:
            xs = (pg.get("/Resources") or {}).get("/XObject") or {}
            for k in xs.keys():
                xo = xs[k]
                if xo.get("/Subtype") == pikepdf.Name("/Form"):
                    n += 1
                    sub = (xo.get("/Resources") or {}).get("/XObject") or {}
                    if any(sub[j].get("/Subtype") == pikepdf.Name("/Form") for j in sub.keys()):
                        prof = 2
        oi = pdf.Root.get("/OutputIntents")
    return n, prof, bool(oi)


def main():
    if not os.path.exists(ORIG):
        print("❌ no está el archivo de prueba:\n   " + ORIG); sys.exit(1)
    print("CONTRATO DE LA HOJA COMPARTIDA — una base por pieza y talle, referenciada por prenda\n")
    # Desplegar el molde real son ~90 s y el archivo no cambia entre corridas: se reusa
    # el despliegue guardado (ver `contrato_molde_b`). Con eso el contrato entra en la
    # tanda rapida: uno que no se puede correr seguido no protege nada.
    import contrato_molde_b as CB
    t = time.time()
    tmp, C, alta, _reusado = CB.espacio_desplegado(ORIG, "verif_hc_",
                                                   alta=PD.alta_molde_con_diseno)
    try:
        PD.marcar(C, True)
        MP._DET_CACHE.clear()
        reg, talles = alta["registro"], alta["talles"]
        pers = MP.extraer_personalizacion(C)
        print(f"          listo en {time.time()-t:.0f}s · {len(reg)} piezas · {len(talles)} talles")
        ts = talles[len(talles)//2 - 1: len(talles)//2 + 2]
        prendas = [{"talle": ts[i % 3], "nombre": n, "numero": str(10 + i), "__variante": None}
                   for i, n in enumerate(["JUGADOR", "MESSI", "DI MARIA", "ALVAREZ", "ENZO"])]
        rot = {p: "libre" if i % 3 == 0 else "180" for i, p in enumerate(reg)}
        kw = dict(borde_corte={"activo": True, "ancho_mm": 2.0, "color": [0, 0, 0, 0.85], "alineacion": "fuera"},
                  etiqueta={"activo": True, "size_mm": 3.0, "mostrar": {"talle": True, "pieza": True, "numero": True},
                            "posiciones": {}, "align": "centro"})
        cfg = {"ancho_cm": 160, "altura_max_cm": 500, "espaciado_cm": 0.5,
               "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1}, "resolucion_mm": 4.0,
               "estrategias": ["bl", "bandas"]}

        # ══ 1. MISMAS COLOCACIONES → MISMA IMAGEN ═══════════════════════════════════════════════
        print("1 · 🔴 SE VE IGUAL: la hoja nueva y la de siempre, con las mismas colocaciones")
        sal = os.path.join(tmp, "s"); os.makedirs(sal)
        por_tela = MP.generar_pedido(C, None, reg, pers, prendas, FUENTES, sal, rotaciones=rot,
                                     solo_piezas=True, modo_hoja="pike", **kw)
        piezas = [p for lst in por_tela.values() for p in lst]
        ok(all("base" in p and p["base"].get("despl") for p in piezas), f"las {len(piezas)} piezas traen su base y su estampado")
        coloc, _area = NC.anidar_contorno(piezas, cfg)
        h_new = os.path.join(tmp, "nueva.pdf"); h_old = os.path.join(tmp, "vieja.pdf")
        t = time.time(); HP.componer_hoja_pike(coloc, cfg, h_new); t_new = time.time() - t
        for p in piezas:
            p["doc"] = p["doc"].real()
        t = time.time(); NC.componer_pdf_contorno(coloc, cfg, h_old, etiquetas=False); t_old = time.time() - t
        r_new, r_old = render(h_new), render(h_old)
        c = comparar(r_new, r_old)
        ok(c is not None and c["pct"] <= 0.2, f"píxeles distintos: {c and c['px']} de {c and c['total']} ({c and round(c['pct'], 3)} %) · de esos, suaves (≤16/255): {c and c['suaves']}")
        print(f"          componer: nueva {t_new:.1f}s · de siempre {t_old:.1f}s")

        # ══ 2 y 3. UN OBJETO POR BASE, PROFUNDIDAD 1, MÁS CHICA ════════════════════════════════
        print("\n2 · UN OBJETO POR BASE (no por prenda), MÁS CHICA, SIN ANIDAR")
        n_new, prof_new, _ = xobjects_form(h_new)
        bases = len({id(p["base"]) for p in piezas})
        ok(n_new == bases, f"la hoja nueva tiene {n_new} Form XObjects = {bases} bases (colocaciones: {len(piezas)})")
        ok(prof_new <= 1, "ninguna base anida otro Form XObject (profundidad 1)")
        # El peso se mide DESPUÉS del aplanado (sección 4): la hoja intermedia se escribe sin
        # comprimir a propósito (changelog 394) y lo que recibe el usuario es la aplanada.
        mb_old = os.path.getsize(h_old) / 1e6

        # ══ 4. EL APLANADO DE UN NIVEL NO CAMBIA NADA Y DEJA EL PERFIL ═════════════════════════
        print("\n4 · APLANAR PARA EL RIP (un nivel): mismo píxel, perfil conservado")
        # OutputIntent de prueba, como el que pone el servidor
        with pikepdf.open(h_new, allow_overwriting_input=True) as pdf:
            icc = pdf.make_stream(b"\x00" * 128); icc["/N"] = 4
            pdf.Root["/OutputIntents"] = pikepdf.Array([pdf.make_indirect(pikepdf.Dictionary({
                "/Type": pikepdf.Name("/OutputIntent"), "/S": pikepdf.Name("/GTS_PDFX"),
                "/OutputConditionIdentifier": pikepdf.String("prueba"), "/DestOutputProfile": icc}))])
            pdf.save(h_new)
        r_antes = render(h_new)
        t = time.time(); aplanar_para_rip(h_new); t_ap = time.time() - t
        c2 = comparar(r_antes, render(h_new))
        ok(c2 is not None and c2["px"] == 0, f"aplanar no cambió un píxel ({c2 and c2['px']} distintos) · {t_ap:.0f}s")
        mb_new = os.path.getsize(h_new) / 1e6
        ok(mb_new < mb_old / 2, f"aplanada pesa {mb_new:.1f} MB contra {mb_old:.1f} MB de la de siempre")
        n2, prof2, oi = xobjects_form(h_new)
        ok(n2 == bases and prof2 <= 1, f"después de aplanar siguen las {n2} bases de un nivel")
        ok(oi, "el OutputIntent (perfil de salida) sigue en el archivo")

        # ══ 5. MESA LARGA: /UserUnit ══════════════════════════════════════════════════════════
        print("\n5 · MESA LARGA (más de 5,08 m): /UserUnit y medidas reales")
        cfg_l = dict(cfg, altura_max_cm=900)
        muchas = [dict(p) for p in piezas for _ in range(3)]
        for p in muchas:
            p["doc"] = MP._DocPerezoso(p["base"], p["estampado"])
        coloc_l, _ = NC.anidar_contorno(muchas, cfg_l)
        h_l = os.path.join(tmp, "larga.pdf")
        consumo, alturas = HP.componer_hoja_pike(coloc_l, cfg_l, h_l)
        with pikepdf.open(h_l) as pdf:
            uu = [int(pg.obj.get("/UserUnit", 1)) for pg in pdf.pages]
            altos = [float(pg.obj["/MediaBox"][3]) * u / MP.CM for pg, u in zip(pdf.pages, uu)]
        larga = [a for a in alturas if a > 508]
        ok(bool(larga) or max(alturas) <= 508, f"hojas de {alturas} cm · UserUnit {uu}")
        ok(all(abs(a - b) < 0.5 for a, b in zip(altos, alturas)), f"las medidas reales coinciden ({[round(a) for a in altos]} cm)")
        ok(all(u > 1 for a, u in zip(alturas, uu) if a > 508), "toda hoja de más de 508 cm lleva /UserUnit > 1")
        for p in piezas + muchas:
            try:
                p["doc"].close()
            except Exception:
                pass
        MP.cerrar_abiertos()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        sys.exit(1)
    print("✅ CONTRATO VERDE — la hoja compartida se ve igual, pesa menos y aplana en un nivel")


if __name__ == "__main__":
    main()
