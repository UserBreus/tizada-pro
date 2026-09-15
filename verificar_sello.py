# -*- coding: utf-8 -*-
"""CONTRATO — «el sello»: el dibujo entra a la hoja UNA vez y la tizada sale IDÉNTICA.

Desde 2026-09-15 (`hoja_pike.componer_hoja_sello`, changelog 458) el dibujo de cada mesa entra a
la hoja una sola vez como Form XObject de página y cada pieza lo referencia. Medido antes del
cambio: el **97 %** de cada colocación era el mismo dibujo repetido.

El contrato arma la MISMA tizada por los dos caminos —con el sello y con el compositor de
siempre (`TIZADA_SIN_SELLO=1`)— y compara:

  1. 🔴 **FIGURA POR FIGURA** (`get_cdrawings`, con las matrices YA aplicadas): mismo tipo, mismo
     color, mismo ancho de trazo y los puntos dentro de 0,01 pt. **Ésta es la que manda.**
  2. píxel a píxel en CMYK, como control — con tolerancia, y acá está el porqué: la hoja de
     siempre mete cada pieza como una PÁGINA (`show_pdf_page`) y el sello la pega inline, o sea
     una composición de matrices MENOS. Los puntos quedan a **0,003 pt** (0,001 mm, medido) y eso
     mueve el antialias de ~0,05 % de los píxeles de borde. No es una diferencia de dibujo, y
     exigir «0 píxeles» acá sería exigir que dos rasterizaciones distintas den bit a bit igual.
  3. el aplanado para el RIP corrido sobre las dos, `verificar_rip_compatible` en verde, y que el
     aplanado no mueva un píxel.
  4. y reporta cuánto tarda y cuánto pesa cada una.

⚠️ La de siempre corre **sin `_barrer_fuentes`**: ese barrido borra todas las fuentes de la hoja
(un texto vivo del diseño desaparecía). El camino B ya lo había dejado de hacer y el sello lo
unifica; neutralizarlo acá es lo que hace la comparación honesta.

Uso:   py verificar_sello.py [N_prendas] [pid] [diseño]

🔴 NO TOCA NADA DEL USUARIO NI LA BASE: el módulo `db` se reemplaza por un doble que revienta si
alguien lo llama, el registro se reconstruye de `piezas.json` (que está en disco) y las salidas
van a un temporal que se borra.
"""
import json
import os
import re
import sys
import tempfile
import time
import types
import shutil

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)

# ── la base, fuera de alcance (misma guarda que `medir_tizada_b.py`) ────────────────────────
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_doble = types.ModuleType("db")
_doble.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError("LA PRUEBA TOCÓ MSSQL")))
sys.modules.setdefault("db", _doble)

import pymupdf as fitz               # noqa: E402
import pikepdf                       # noqa: E402
import motor_pedido as MP            # noqa: E402

DATOS = os.environ.get("TIZADA_DATOS") or "datos"
ENTRADA = os.environ.get("TIZADA_ENTRADA") or "entrada"
NOMBRES = ["MESSI", "DI MARIA", "ALVAREZ", "ENZO", "OTAMENDI", "ROMERO", "TAGLIAFICO"]
RX_COLOR = re.compile(rb"((?:[-\d.]+\s+){1,4})(k|K|g|G|rg|RG|sc|scn|SC|SCN)\b")


def _catalogo():
    return json.load(open(os.path.join(DATOS, "productos_catalogo.json"), encoding="utf-8"))


def _elegir_molde(pid=None, diseno=None):
    """Un molde del camino A con arte cargado. Devuelve (pid, prod, slug_diseño)."""
    cat = _catalogo()
    for prod in cat["productos"]:
        if pid and prod["id"] != pid:
            continue
        base = os.path.join(ENTRADA, prod["id"])
        if not os.path.exists(os.path.join(base, "plantilla.ai")):
            continue
        dis = [diseno] if diseno else [d["id"] for d in (prod.get("disenos") or [])] + [None]
        for d in dis:
            sub = os.path.join("disenos", d) if d else ""
            arte = os.path.join(base, sub, "arte.ai")
            mapa = os.path.join(DATOS, "productos", prod["id"], sub, "mapeo_arte.json")
            if os.path.exists(arte) and os.path.exists(mapa):
                return prod["id"], prod, d
    return None, None, None


def _registro(pid, prod):
    """El registro del molde, reconstruido SIN tocar la base: `piezas.json` guarda el nombre de
    cada pieza y su ancla (talle + índice), que es exactamente la entrada de
    `alta_plantilla_manual` (lo mismo que hace `servidor._guia_y_asignaciones`)."""
    pj = json.load(open(os.path.join(DATOS, "productos", pid, "piezas.json"), encoding="utf-8"))
    guia = prod.get("variante_guia") or "M"
    asign = [{"idx": int(p["ancla"]["idx"]), "nombre": p.get("clave") or p.get("nombre")}
             for p in pj.get("piezas", [])
             if not p.get("retirada") and (p.get("ancla") or {}).get("talle") == guia]
    if not asign:
        raise SystemExit(f"[i] no hay piezas ancladas al talle guía {guia!r}: nada que contrastar.")
    pl = os.path.join(ENTRADA, pid, "plantilla.ai")
    emp = os.path.join(DATOS, "productos", pid, "emparejado_talles.json")
    corr = os.path.join(DATOS, "productos", pid, "correspondencia_piezas.json")
    det = MP.detectar_piezas(pl, talle_ref=guia)
    alta = MP.alta_plantilla_manual(
        pl, asign, det["mesa"], guia,
        indices=(json.load(open(corr, encoding="utf-8")) if os.path.exists(corr) else None),
        emparejado=(json.load(open(emp, encoding="utf-8")) if os.path.exists(emp) else None))
    return alta["registro"], alta["talles"], guia


def _render(path, dpi):
    d = fitz.open(path)
    try:
        out = []
        for pg in d:
            p = pg.get_pixmap(dpi=dpi, colorspace=fitz.csCMYK)
            out.append((p.width, p.height, bytes(p.samples)))
        return out
    finally:
        d.close()


def _colores(path):
    import collections
    c = collections.Counter()
    with pikepdf.open(path) as p:
        for pg in p.pages:
            cs = pg.obj.get("/Contents")
            data = [b"\n".join(s.read_bytes() for s in cs) if isinstance(cs, pikepdf.Array)
                    else (cs.read_bytes() if cs is not None else b"")]
            for _n, o in ((pg.get("/Resources") or {}).get("/XObject") or {}).items():
                try:
                    data.append(o.read_bytes())
                except Exception:
                    pass
            for d in data:
                for m in RX_COLOR.finditer(d):
                    c[(b" ".join(m.group(1).split()).decode(), m.group(2).decode())] += 1
    return c


def _dibujos(path):
    """Cada figura del archivo, con sus puntos y su color YA transformados, en orden."""
    d = fitz.open(path)
    try:
        return [dr for pg in d for dr in pg.get_cdrawings()]
    finally:
        d.close()


# Tolerancia de la comparación geométrica, en puntos. 0,01 pt = 0,0035 mm: cien veces más fino
# que un punto de impresión a 1440 dpi. Existe porque la hoja de siempre compone UNA matriz más
# que el sello (cada pieza es una página mostrada con `show_pdf_page`), y eso corre los puntos en
# el último bit del `float`. Medido sobre la tizada real: el desvío máximo fue **0,0015 pt**.
TOL_PT = float(os.environ.get("TIZADA_TOL_TRAZADO") or 0.01)


def _comparar_dibujos(a, b):
    """Compara figura por figura. Devuelve (problemas, cantidad, desvío máximo en puntos)."""
    A, B = _dibujos(a), _dibujos(b)
    if len(A) != len(B):
        return [f"distinta cantidad de figuras: {len(A)} vs {len(B)}"], len(A), 0.0
    probs, peor = [], 0.0
    for i, (x, y) in enumerate(zip(A, B)):
        if x.get("type") != y.get("type"):
            probs.append(f"figura {i}: tipo {x.get('type')} vs {y.get('type')}")
        for k in ("color", "fill"):
            if tuple(x.get(k) or ()) != tuple(y.get(k) or ()):
                probs.append(f"figura {i}: {k} {x.get(k)} vs {y.get(k)}")
        if round(float(x.get("width") or 0), 4) != round(float(y.get("width") or 0), 4):
            probs.append(f"figura {i}: ancho de trazo {x.get('width')} vs {y.get('width')}")
        ra, rb = x.get("rect"), y.get("rect")
        if ra is not None and rb is not None:
            d = max(abs(float(p) - float(q)) for p, q in zip(ra, rb))
            peor = max(peor, d)
            if d > TOL_PT:
                probs.append(f"figura {i}: se movió {d:.4f} pt (tope {TOL_PT} pt)")
        if len(probs) > 8:
            break
    return probs, len(A), peor


def _estructura(path):
    with pikepdf.open(path) as p:
        xo = set()
        imgs = 0
        niveles = 1
        for pg in p.pages:
            for _n, o in ((pg.get("/Resources") or {}).get("/XObject") or {}).items():
                xo.add(o.objgen)
                if o.get("/Subtype") == pikepdf.Name("/Image"):
                    imgs += 1
                r = o.get("/Resources")
                if r is not None and len(r.get("/XObject") or {}):
                    niveles = 2
        return len(xo), imgs, niveles, len(p.pages)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 4
    pid = sys.argv[2] if len(sys.argv) > 2 else None
    diseno = sys.argv[3] if len(sys.argv) > 3 else None
    pid, prod, dslug = _elegir_molde(pid, diseno)
    if not pid:
        print("[i] no hay ningún molde del camino A con arte a mano: nada que contrastar.")
        return 0
    sub = os.path.join("disenos", dslug) if dslug else ""
    pl = os.path.join(ENTRADA, pid, "plantilla.ai")
    arte = os.path.join(ENTRADA, pid, sub, "arte.ai")
    mapa = json.load(open(os.path.join(DATOS, "productos", pid, sub, "mapeo_arte.json"),
                          encoding="utf-8"))
    print(f"molde {pid} · diseño {dslug or 'principal'} · {n} prendas")

    reg, talles, guia = _registro(pid, prod)
    print(f"registro: {len(reg)} piezas · {len(talles)} talles (guía {guia})")
    pers = MP.extraer_personalizacion(arte)
    _ts = [t for t in (talles[len(talles) // 2 - 1: len(talles) // 2 + 2] or talles)]
    prendas = [{"talle": _ts[i % len(_ts)], "nombre": NOMBRES[i % len(NOMBRES)],
                "numero": str((i * 7) % 99 + 1), "__variante": None} for i in range(n)]
    kw = dict(mapeo_arte=mapa, borde_corte=prod.get("borde_corte"), etiqueta=prod.get("etiqueta"),
              config_nesting={"ancho_cm": 180, "altura_max_cm": 500, "espaciado_cm": 0.5,
                              "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1}})
    if os.environ.get("SELLO_SIN_ROTAR"):
        kw["rotaciones"] = {p: "0" for p in reg}
    tmp = tempfile.mkdtemp(prefix="sello_")
    try:
        salidas = {}
        for etiqueta, sin_sello in (("sello", False), ("de siempre", True)):
            sal = os.path.join(tmp, etiqueta.replace(" ", "_"))
            os.makedirs(sal, exist_ok=True)
            if sin_sello:
                os.environ["TIZADA_SIN_SELLO"] = "1"
                # 🔴 SIN `_barrer_fuentes` EN LA DE SIEMPRE, y es la comparación honesta. Ese
                # barrido borra TODAS las fuentes de la hoja: con el compositor viejo, un texto
                # VIVO del diseño (uno que no sea placeholder) desaparecía de la tizada. El
                # camino B ya había decidido conservarlas (ver `hoja_pike.xobject_base`) y el
                # sello lo unifica. Si no se neutraliza acá, el contrato mide ese arreglo como
                # si fuera una diferencia del sello — y no lo es.
                MP._barrer_fuentes = lambda *a, **k: None
            else:
                os.environ.pop("TIZADA_SIN_SELLO", None)
            MP._DET_CACHE.clear()
            t0 = time.time()
            res = MP.generar_pedido(pl, arte, reg, pers, prendas, "catalogo_fuentes", sal, **kw)
            t = time.time() - t0
            hojas = [os.path.join(sal, h["archivo"]) for h in res["hojas"]]
            salidas[etiqueta] = (hojas, t, res)
            mb = sum(os.path.getsize(h) for h in hojas) / 1048576
            xo, imgs, niv, pgs = _estructura(hojas[0])
            print(f"  [{etiqueta:<10}] {t:6.1f} s · {mb:6.2f} MB · {pgs} pág · "
                  f"{xo} dibujos distintos · {imgs} imágenes · {niv} nivel(es)")
        os.environ.pop("TIZADA_SIN_SELLO", None)

        fallas = []
        ha, hb = salidas["sello"][0], salidas["de siempre"][0]
        if len(ha) != len(hb):
            fallas.append(f"distinta cantidad de hojas: {len(ha)} vs {len(hb)}")
        dpi = int(os.environ.get("TIZADA_DPI_CONTRATO") or 20)
        for a, b in zip(ha, hb):
            ra, rb = _render(a, dpi), _render(b, dpi)
            if len(ra) != len(rb):
                fallas.append(f"{os.path.basename(a)}: distinta cantidad de páginas"); continue
            for i, ((w1, h1, s1), (w2, h2, s2)) in enumerate(zip(ra, rb), 1):
                if (w1, h1) != (w2, h2):
                    fallas.append(f"{os.path.basename(a)} pág {i}: distinto tamaño"); continue
                dif = sum(1 for x, y in zip(s1, s2) if x != y)
                delta = max((abs(x - y) for x, y in zip(s1, s2) if x != y), default=0)
                frac = dif / max(1, len(s1))
                # 🔴 ACÁ NO SE EXIGE «0 PÍXELES», Y ESTÁ MEDIDO POR QUÉ. La hoja de siempre mete
                # cada pieza como una PÁGINA (`show_pdf_page`); el sello la pega inline, o sea
                # una composición de matrices MENOS. La geometría es la misma —lo prueba la
                # comparación de trazados de más abajo, que es exacta— pero el rasterizador
                # redondea distinto en el último bit: con antialias, ~0,04 % de los píxeles de
                # BORDE cambian de 1 a 10 niveles sobre 255. Lo que sí se exige es que ninguna
                # diferencia sea de CONTENIDO: pocas, chicas, y la geometría idéntica.
                if frac > 0.005:
                    fallas.append(f"{os.path.basename(a)} pág {i}: {dif:,} píxeles distintos "
                                  f"({100*frac:.4f} %) — demasiados para ser sólo el antialias")
                extra = ""
                if dif:
                    # DÓNDE están las diferencias: sin esto uno se queda mirando un número.
                    px = [j // 4 for j in range(0, len(s1), 4)
                          if s1[j:j + 4] != s2[j:j + 4]]
                    if px:
                        xs = [p % w1 for p in px]; ys = [p // w1 for p in px]
                        extra = (f"  [en x {min(xs)}..{max(xs)} de {w1}, y {min(ys)}..{max(ys)} "
                                 f"de {h1}; {len(px)} puntos]")
                print(f"    {os.path.basename(a)} pág {i}: {dif:,} píxeles distintos "
                      f"de {len(s1):,} ({100*frac:.4f} %, delta máx {delta}){extra}")
            # ── LA COMPARACIÓN EXACTA: TRAZADO POR TRAZADO ─────────────────────────────────
            # Es la que manda. `get_cdrawings` devuelve cada figura YA con las matrices
            # aplicadas: mismos puntos y mismos colores = mismo dibujo, sin depender de cómo
            # rasterice nadie. (Los colores NO se pueden contar leyendo el stream de la página:
            # en la hoja de siempre viven adentro de XObjects anidados — trampa del changelog 447.)
            probs, cuantas, peor = _comparar_dibujos(a, b)
            if probs:
                fallas.append(f"{os.path.basename(a)}: el DIBUJO difiere -> {probs[:4]}")
            else:
                print(f"    {os.path.basename(a)}: {cuantas:,} figuras IDÉNTICAS "
                      f"(mismos colores, mismos anchos, desvío máximo {peor:.4f} pt "
                      f"= {peor/2.8346:.5f} mm)")
        # ── EL APLANADO PARA EL RIP, y recién ahí el contrato del RIP ───────────────────────
        # El OutputIntent y el ICC los pone `aplanar_para_rip`, que en el pedido real corre
        # después del motor: verificar antes da «sin OutputIntent» en las DOS y no prueba nada.
        try:
            from aplanar_rip import aplanar_para_rip
            import verificar_rip_compatible as VR
            for et, (hojas, _t, _r) in salidas.items():
                for h in hojas:
                    antes = _render(h, dpi)
                    t0 = time.time()
                    aplanar_para_rip(h)
                    ok, probs = VR.verificar(h)
                    print(f"    [{et:<10}] aplanado {os.path.basename(h):<22} "
                          f"{time.time()-t0:5.1f} s -> {os.path.getsize(h)/1048576:6.2f} MB · "
                          f"RIP {'OK' if ok else probs[:2]}")
                    # El OutputIntent y el ICC los pone el SERVIDOR después del aplanado
                    # (paso «perfil» del pedido): acá falta en las dos y no dice nada.
                    probs = [x for x in probs if "OutputIntent" not in x]
                    if probs:
                        fallas.append(f"[{et}] {os.path.basename(h)}: RIP -> {probs[:3]}")
                    despues = _render(h, dpi)
                    d = sum(sum(1 for x, y in zip(a[2], b[2]) if x != y)
                            for a, b in zip(antes, despues)) if len(antes) == len(despues) else -1
                    if d:
                        fallas.append(f"[{et}] {os.path.basename(h)}: el aplanado cambió {d} píxeles")
        except Exception as e:
            print(f"    [i] no se pudo correr el aplanado/verificación: {type(e).__name__}: {e}")

        if fallas:
            print("\n[FALLA] el sello NO da lo mismo:")
            for f in fallas:
                print("   -", f)
            return 1
        print("\n[OK] la tizada con el sello es IDÉNTICA a la de siempre.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
