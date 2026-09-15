# -*- coding: utf-8 -*-
"""CONTRATO — el corte por bytes de las capas tiene que dar EXACTAMENTE lo mismo que antes.

`cortar_capas.py` ubica por bytes dónde empieza y termina cada capa OCG para no parsear la mesa
entera una vez por talle (ver changelog 457 del mapa). El contrato compara, talle por talle, el
desplegado hecho CON el corte contra el hecho SIN el corte:

  1. **el mismo dibujo, píxel a píxel** (CMYK), talle por talle;
  2. los mismos placeholders, la misma línea de corte y la misma etiqueta del archivo;
  3. y de paso mide cuánto más rápido es y cuánto más chica queda la página.

⚠️ **No se comparan bytes, y es a propósito.** El corte además descarta los grupos `q … Q` de los
OTROS talles, que el camino de siempre dejaba como operadores MUERTOS (trazados sin pintar que el
RIP igual tenía que leer). La página nueva es más chica y dibuja exactamente lo mismo.

Uso:
    py verificar_corte_capas.py [ruta_del_molde.ai] [mesa]

Sin argumentos busca un molde del camino B en `entrada/`. Si no hay ninguno, avisa y sale sin
fallar (no hay nada que contrastar).

🔴 SÓLO LEE. No escribe nada al lado del molde: las salidas van a un temporal propio.
"""
import os
import sys
import tempfile
import time

import pikepdf

import cortar_capas as CC
import piezas_con_diseno as PD


def _molde_de_prueba():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]
    entrada = os.environ.get("TIZADA_ENTRADA") or "entrada"
    if os.path.isdir(entrada):
        for pid in sorted(os.listdir(entrada)):
            p = os.path.join(entrada, pid, "plantilla.ai")
            if os.path.exists(p):
                try:
                    if PD.es_camino_b(p):
                        return p
                except Exception:
                    pass
    return None


def _contenidos(path):
    out = []
    with pikepdf.open(path) as p:
        for pg in p.pages:
            c = pg.obj.get("/Contents")
            out.append(b"\n".join(s.read_bytes() for s in c) if isinstance(c, pikepdf.Array)
                       else (c.read_bytes() if c is not None else b""))
    return out


def main():
    molde = _molde_de_prueba()
    if not molde:
        print("[i] no hay ningún molde del camino B a mano: no hay nada que contrastar.")
        return 0
    mesa = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    print(f"molde: {molde}  (mesa {mesa})")

    import fitz
    d = fitz.open(molde)
    talles = PD.talles_del_molde(d)
    d.close()
    if not talles:
        print("[i] el molde no declara talles: nada que contrastar.")
        return 0
    print(f"talles: {len(talles)} -> {', '.join(talles[:8])}{' ...' if len(talles) > 8 else ''}")

    with pikepdf.open(molde) as p:
        corte = CC.cortar(p.pages[mesa - 1])
    if corte is None:
        print("[i] esta mesa no se puede cortar por bytes -> el sistema usa el camino de siempre."
              "\n    El contrato pasa igual: eso es exactamente lo previsto.")
        return 0
    print(f"capas encontradas por el corte: {len(CC.capas(corte))}")

    tmp = tempfile.mkdtemp(prefix="corte_capas_")
    a = os.path.join(tmp, "con_corte.pdf")
    b = os.path.join(tmp, "sin_corte.pdf")
    conts = {}
    marco, U = None, None
    idx = PD._leer_desplegado(molde, mesa) or {}
    conts = {t: [PD._cont_de_json(c) for c in lst] for t, lst in (idx.get("talles") or {}).items()}
    marco, U = idx.get("marco"), idx.get("U")
    if marco is None:
        d = fitz.open(molde)
        _pg = d[mesa - 1]
        _cb = _pg.cropbox
        marco = [_cb.x0, _cb.y0, _cb.x1, _cb.y1]
        U = _pg.rect.width / _cb.width if _cb.width else 1.0
        d.close()

    t0 = time.time()
    r_a = PD._paginas_de_talles(molde, mesa, list(talles), conts, marco, U, set(), a)
    t_a = time.time() - t0

    _real = CC.cortar
    CC.cortar = lambda *args, **kw: None          # forzar el camino de siempre
    try:
        t0 = time.time()
        r_b = PD._paginas_de_talles(molde, mesa, list(talles), conts, marco, U, set(), b)
        t_b = time.time() - t0
    finally:
        CC.cortar = _real

    ca, cb = _contenidos(a), _contenidos(b)
    fallas = []
    if len(ca) != len(cb):
        fallas.append(f"distinta cantidad de páginas: {len(ca)} vs {len(cb)}")
    for nombre, x, y in (("placeholders", r_a[0], r_b[0]),
                         ("línea de corte", r_a[1], r_b[1]),
                         ("etiqueta del archivo", r_a[2], r_b[2])):
        if x != y:
            fallas.append(f"{nombre}: distinto")

    # 🔴 LA COMPARACIÓN ES POR PÍXELES, NO POR BYTES. El corte además descarta los grupos
    # `q … Q` de los OTROS talles que el camino de siempre dejaba como operadores muertos (dibujo
    # sin pintar, que el RIP igual tenía que leer): la página nueva es MÁS CHICA y dibuja lo
    # mismo. Byte a byte no puede dar igual; píxel a píxel, sí.
    dpi = int(os.environ.get("TIZADA_DPI_CONTRATO") or 24)
    import fitz as _f
    da, db = _f.open(a), _f.open(b)
    try:
        for i in range(min(len(da), len(db))):
            pa = da[i].get_pixmap(dpi=dpi, colorspace=_f.csCMYK)
            pb = db[i].get_pixmap(dpi=dpi, colorspace=_f.csCMYK)
            if (pa.width, pa.height) != (pb.width, pb.height):
                fallas.append(f"talle {talles[i]}: distinto tamaño de página")
                continue
            dif = sum(1 for x, y in zip(pa.samples, pb.samples) if x != y)
            if dif:
                fallas.append(f"talle {talles[i]}: {dif:,} píxeles distintos de {len(pa.samples):,}")
    finally:
        da.close(); db.close()

    print(f"\n  con el corte : {t_a:6.2f} s   ·  {os.path.getsize(a)/1048576:6.1f} MB")
    print(f"  sin el corte : {t_b:6.2f} s   ·  {os.path.getsize(b)/1048576:6.1f} MB")
    print(f"  páginas: {len(ca)}  ·  contenido: {sum(len(x) for x in ca)/1048576:.1f} MB "
          f"(antes {sum(len(x) for x in cb)/1048576:.1f} MB)")
    print(f"  píxeles comparados a {dpi} dpi en CMYK")

    for f in os.listdir(tmp):
        try:
            os.remove(os.path.join(tmp, f))
        except Exception:
            pass
    try:
        os.rmdir(tmp)
    except Exception:
        pass

    if fallas:
        print("\n[FALLA] el corte por bytes NO da lo mismo:")
        for f in fallas:
            print("   -", f)
        return 1
    print("\n[OK] el corte por bytes da EXACTAMENTE el mismo desplegado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
