# -*- coding: utf-8 -*-
"""Aplanado de la HOJA de tizada para que el RIP la procese SIN error, dejándola como el PDF que
exporta Illustrator (que sí funciona):
  1. DES-ANIDA los Form XObjects (el motor arma cada pieza con `show_pdf_page` → 3 capas de XObject
     anidado; muchos RIPs no resuelven el color escondido tan adentro → error).
  2. CONSOLIDA los perfiles ICC repetidos (cada pieza traía su propio ICCBased idéntico → el RIP se
     atraganta con perfiles duplicados) en UNO solo.
  3. DECLARA el estado gráfico (ExtGState con overprint/SMask=None) — Illustrator y Ghostscript lo
     ponen; el del sistema no, y sin eso el RIP no sabe cómo tratar color/transparencia.
  4. Limpia la estructura con MuPDF (garbage collect) y guarda en PDF 1.6 (como Illustrator).
TODO preservando los valores CMYK EXACTOS byte a byte (NO usa Ghostscript, que re-cuantiza los
colores: 0.9 → 0.90039). Verificado pixel-idéntico a la salida original.
"""
import io
import pikepdf
from pikepdf import Name, parse_content_stream, unparse_content_stream

_RES_KINDS = ["/ColorSpace", "/XObject", "/Font", "/ExtGState", "/Shading", "/Pattern", "/Properties"]
_OPKIND = {"Do": "/XObject", "gs": "/ExtGState", "cs": "/ColorSpace", "CS": "/ColorSpace",
           "scn": "/ColorSpace", "SCN": "/ColorSpace", "sh": "/Shading", "Tf": "/Font",
           "BDC": "/Properties", "DP": "/Properties"}


def _merge_res(dst_res, src_res):
    remap = {}
    for kind in _RES_KINDS:
        s = src_res.get(kind)
        if s is None:
            continue
        d = dst_res.get(kind)
        if d is None:
            d = pikepdf.Dictionary(); dst_res[kind] = d
        for nm, obj in s.items():
            nm = str(nm)
            if kind == "/XObject" and obj.get("/Subtype") == Name("/Form"):
                continue   # los Form ya se inlinearon → NO mergearlos (quedarían huérfanos)
            if nm in d:
                try:
                    if d[nm].objgen == obj.objgen:
                        continue
                except Exception:
                    pass
                i = 1
                while f"{nm}_fl{i}" in d:
                    i += 1
                newnm = f"{nm}_fl{i}"; d[newnm] = obj
                remap.setdefault(kind, {})[nm] = newnm
            else:
                d[nm] = obj
    return remap


def _remap_ops(ops, remap):
    out = []
    for operands, op in ops:
        k = _OPKIND.get(str(op))
        if k and k in remap:
            operands = [pikepdf.Name(remap[k].get(str(o), str(o))) if isinstance(o, pikepdf.Name) else o
                        for o in operands]
        out.append((operands, op))
    return out


def _flatten(pdf, container, es_pagina=False):
    res = container.get("/Resources")
    if res is None:
        return
    xobjs = res.get("/XObject")
    if xobjs is None:
        return
    try:
        ops = list(parse_content_stream(container))
    except Exception:
        return
    new_ops = []
    for operands, op in ops:
        if str(op) == "Do" and operands and isinstance(operands[0], pikepdf.Name):
            nm = str(operands[0])
            xo = xobjs.get(nm) if nm in xobjs else None
            if xo is not None and xo.get("/Subtype") == Name("/Form"):
                _flatten(pdf, xo, es_pagina=False)
                remap = _merge_res(res, xo.get("/Resources", pikepdf.Dictionary()))
                sub = _remap_ops(list(parse_content_stream(xo)), remap)
                _num = lambda v: pikepdf.Object.parse(f"{float(v):.6f}".encode("ascii"))
                new_ops.append(([], pikepdf.Operator("q")))
                mtx = xo.get("/Matrix")
                if mtx is not None:
                    new_ops.append(([_num(x) for x in mtx], pikepdf.Operator("cm")))
                bbox = xo.get("/BBox")
                if bbox is not None:
                    x0, y0, x1, y1 = [float(v) for v in bbox]
                    new_ops.append(([_num(v) for v in (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))], pikepdf.Operator("re")))
                    new_ops.append(([], pikepdf.Operator("W")))
                    new_ops.append(([], pikepdf.Operator("n")))
                new_ops.extend(sub)
                new_ops.append(([], pikepdf.Operator("Q")))
                continue
        new_ops.append((operands, op))
    data = unparse_content_stream(new_ops)
    if es_pagina:
        container.Contents = pdf.make_stream(data)
    else:
        container.write(data)


def _limpiar_huerfanos(page):
    res = page.get("/Resources"); xo = res.get("/XObject") if res else None
    if not xo:
        return
    usados = set()
    try:
        for operands, op in parse_content_stream(page):
            if str(op) == "Do" and operands and isinstance(operands[0], pikepdf.Name):
                usados.add(str(operands[0]))
    except Exception:
        return
    for nm in [str(k) for k in xo.keys()]:
        if nm not in usados:
            del xo[nm]


def _consolidar_iccbased(pdf, page):
    import hashlib
    res = page.get("/Resources"); cs = res.get("/ColorSpace") if res else None
    if not cs:
        return
    by_hash, remap = {}, {}
    for nm in [str(k) for k in cs.keys()]:
        v = cs[nm]
        try:
            if isinstance(v, pikepdf.Array) and str(v[0]) == "/ICCBased":
                h = hashlib.sha1(bytes(v[1].read_raw_bytes())).hexdigest()
                if h in by_hash:
                    remap[nm] = by_hash[h]; del cs[nm]
                else:
                    by_hash[h] = nm
        except Exception:
            pass
    if remap:
        ops = _remap_ops(list(parse_content_stream(page)), {"/ColorSpace": remap})
        page.Contents = pdf.make_stream(unparse_content_stream(ops))


def _declarar_estado_grafico(pdf, page):
    """Agrega y APLICA un ExtGState 'normal' (overprint/SMask=None) al inicio del content, como
    hace Illustrator. Sin esto el RIP no sabe cómo tratar color/transparencia."""
    res = page.Resources
    if "/ExtGState" not in res:
        res.ExtGState = pikepdf.Dictionary()
    res.ExtGState["/GSflat"] = pdf.make_indirect(pikepdf.Dictionary(
        Type=Name("/ExtGState"), OP=False, op=False, OPM=1, SA=True,
        SMask=Name("/None"), BM=Name("/Normal"), CA=1, ca=1))
    cont = page.Contents
    if isinstance(cont, pikepdf.Array):
        cont = cont[0]
    page.Contents = pdf.make_stream(b"/GSflat gs\n" + cont.read_bytes())


def aplanar_para_rip(path):
    """Aplana la HOJA in-place: des-anida + consolida ICC + declara estado gráfico + PDF 1.6, con
    los colores CMYK EXACTOS. Best-effort: si algo falla, deja el PDF como estaba (no rompe la tizada)."""
    try:
        pdf = pikepdf.open(path, allow_overwriting_input=True)
        for page in pdf.pages:
            _flatten(pdf, page, es_pagina=True)
            _limpiar_huerfanos(page)
            _consolidar_iccbased(pdf, page)
            _declarar_estado_grafico(pdf, page)
        if "/OutputIntents" in pdf.Root:
            del pdf.Root["/OutputIntents"]   # Illustrator no lo tiene; el ICCBased de la página alcanza
        # DECLARAR Creator/Producer: los PDFs que pasan el RIP (Illustrator, Ghostscript) lo declaran;
        # el original (que falla) queda "no declarado". Algunos RIPs desconfían de un PDF sin Producer.
        try:
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta["dc:creator"] = ["TIZADA PRO"]
                meta["xmp:CreatorTool"] = "TIZADA PRO"
                meta["pdf:Producer"] = "TIZADA PRO"
        except Exception:
            pass
        pdf.docinfo["/Creator"] = "TIZADA PRO"
        pdf.docinfo["/Producer"] = "TIZADA PRO"
        pdf.remove_unreferenced_resources()
        pdf.save(path, force_version="1.6")   # PDF 1.6 como Illustrator (máx. compat. RIP)
        pdf.close()
        return True
    except Exception as e:
        try:
            print(f"  [aplanar_rip] no se pudo aplanar {path}: {e}")
        except Exception:
            pass
        return False
