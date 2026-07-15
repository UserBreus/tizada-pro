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
import os
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


def _sanear_texto(pdf, page):
    """Quita los bloques de texto BT..ET que referencian una FUENTE INEXISTENTE (o que no muestran
    ningún glifo). El arte trae bloques de texto 'fantasma' — prenden una fuente `/T1_0`/`/TT0` que
    no está declarada y no dibujan nada — y muchos RIPs los rechazan como 'recurso indefinido' →
    error RIP. gs los convierte a curvas e Illustrator declara la fuente; el sistema los arrastraba.
    Como no marcan nada, borrarlos NO cambia un solo píxel."""
    res = page.get("/Resources")
    fonts = set(str(k) for k in (res.get("/Font", {}) or {}).keys()) if res else set()
    try:
        ops = list(parse_content_stream(page))
    except Exception:
        return 0, 0
    out, block, in_bt = [], [], False
    falta_fuente = tiene_texto = False
    quitados = perdidos = 0
    for operands, op in ops:
        o = str(op)
        if o == "BT":
            in_bt = True; block = [(operands, op)]; falta_fuente = tiene_texto = False
            continue
        if in_bt:
            block.append((operands, op))
            if o == "Tf" and operands and isinstance(operands[0], Name) and str(operands[0]) not in fonts:
                falta_fuente = True
            elif o in ("Tj", "TJ", "'", '"'):
                tiene_texto = True
            if o == "ET":
                in_bt = False
                if falta_fuente or not tiene_texto:
                    quitados += 1
                    if tiene_texto:
                        perdidos += 1   # texto REAL con fuente inexistente (no debería pasar en la tizada)
                else:
                    out.extend(block)
                block = []
            continue
        out.append((operands, op))
    if quitados:
        page.Contents = pdf.make_stream(unparse_content_stream(out))
    return quitados, perdidos


def _quitar_ocg(pdf, page):
    """Elimina las CAPAS OPCIONALES (OCG) del molde/arte (Diseño, molde, Nombre, guías, ...). El
    motor las arrastra desde el .ai y quedan como OCG SIN registrar en /OCProperties → 'capas
    huérfanas' que PhotoPRINT rechaza (error RIP). gs las aplana (0 OCG). Se quitan los marcadores
    de contenido (BMC/BDC/EMC/MP/DP), el /Properties de recursos y el /OCProperties del catálogo;
    los OCG quedan sin referencia y qpdf los limpia al guardar. NO producen marcas → 0 cambio visual."""
    try:
        ops = list(parse_content_stream(page))
        nuevos = [(o, op) for (o, op) in ops if str(op) not in ("BDC", "BMC", "EMC", "MP", "DP")]
        if len(nuevos) != len(ops):
            page.Contents = pdf.make_stream(unparse_content_stream(nuevos))
    except Exception:
        pass
    res = page.get("/Resources")
    if res is not None and "/Properties" in res:
        del res["/Properties"]
    if res is not None:
        for k, v in list((res.get("/XObject", {}) or {}).items()):
            if "/OC" in v:
                del v["/OC"]
    if "/OCProperties" in pdf.Root:
        del pdf.Root["/OCProperties"]


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
    """Deja los ExtGState 'opacos como gs': overprint off (OP/op=False, OPM=1), stroke adjust on
    (SA=True). QUITA de los ExtGState existentes las claves que un preflight lee como transparencia
    (SMask, BM, CA, ca, AIS) SÓLO cuando su valor ya es el opaco por defecto (/None, /Normal, 1,
    False) → 0 cambio visual pero sin 'transparencia detectada'. Agrega y aplica /GSflat al inicio."""
    res = page.Resources
    if "/ExtGState" not in res:
        res.ExtGState = pikepdf.Dictionary()
    for k, v in list(res.ExtGState.items()):
        if v.get("/SMask") == Name("/None"):
            del v["/SMask"]
        if v.get("/BM") == Name("/Normal"):
            del v["/BM"]
        try:
            if "/CA" in v and float(v["/CA"]) == 1:
                del v["/CA"]
            if "/ca" in v and float(v["/ca"]) == 1:
                del v["/ca"]
        except Exception:
            pass
        if "/AIS" in v and v["/AIS"] == False:  # noqa: E712 (pikepdf Boolean)
            del v["/AIS"]
    res.ExtGState["/GSflat"] = pdf.make_indirect(pikepdf.Dictionary(
        Type=Name("/ExtGState"), OP=False, op=False, OPM=1, SA=True))
    cont = page.Contents
    if isinstance(cont, pikepdf.Array):
        cont = cont[0]
    page.Contents = pdf.make_stream(b"/GSflat gs\n" + cont.read_bytes())


def _procesar_contenido(pdf, page):
    """UNA sola pasada por el content-stream de la página (ya aplanada) que hace lo que antes eran
    4 pasadas separadas (cada una re-parseaba el stream GIGANTE): (1) saca los bloques de texto
    fantasma (fuente inexistente / sin glifos), (2) saca los marcadores de capa OCG (BMC/BDC/EMC/
    MP/DP), (3) remapea los ColorSpace ICCBased duplicados a uno canónico, (4) junta los XObjects
    realmente usados para borrar los huérfanos. Mismo resultado byte a byte que las 4 pasadas, pero
    parseando el stream una vez → ~4× menos parse/unparse en hojas con muchas piezas."""
    import hashlib
    res = page.get("/Resources")
    # ICC: dedup por contenido → remap {nombre_dup: canónico}
    remap = {}
    cs = res.get("/ColorSpace") if res else None
    if cs:
        by_hash = {}
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
    fonts = set(str(k) for k in (res.get("/Font", {}) or {}).keys()) if res else set()
    _CS_OPS = ("cs", "CS", "scn", "SCN")   # operadores que referencian un ColorSpace por Name
    def _rmp(operands, op):
        if remap and str(op) in _CS_OPS:
            operands = [pikepdf.Name(remap.get(str(o), str(o))) if isinstance(o, pikepdf.Name) else o for o in operands]
        return (operands, op)
    try:
        ops = list(parse_content_stream(page))
    except Exception:
        ops = None
    usados = set()
    if ops is not None:
        out, block, in_bt = [], [], False
        falta_fuente = tiene_texto = False
        _MC = ("BDC", "BMC", "EMC", "MP", "DP")
        for operands, op in ops:
            o = str(op)
            if o in _MC:
                continue                                   # marcador de capa/estructura → fuera (no marca nada)
            if o == "BT":
                in_bt = True; block = [(operands, op)]; falta_fuente = tiene_texto = False
                continue
            if in_bt:
                block.append(_rmp(operands, op))
                if o == "Tf" and operands and isinstance(operands[0], Name) and str(operands[0]) not in fonts:
                    falta_fuente = True
                elif o in ("Tj", "TJ", "'", '"'):
                    tiene_texto = True
                if o == "ET":
                    in_bt = False
                    if not (falta_fuente or not tiene_texto):
                        out.extend(block)                  # bloque de texto válido → se conserva
                    block = []
                continue
            if o == "Do" and operands and isinstance(operands[0], Name):
                usados.add(str(operands[0]))
            out.append(_rmp(operands, op))
        page.Contents = pdf.make_stream(unparse_content_stream(out))
    # huérfanos: quitar los XObjects que ya no se referencian con Do
    xo = res.get("/XObject") if res else None
    if xo is not None and ops is not None:
        for nm in [str(k) for k in xo.keys()]:
            if nm not in usados:
                del xo[nm]
    # limpiar residuo de OCG (capas opcionales)
    if res is not None and "/Properties" in res:
        del res["/Properties"]
    if res is not None:
        for k, v in list((res.get("/XObject", {}) or {}).items()):
            if "/OC" in v:
                del v["/OC"]
    if "/OCProperties" in pdf.Root:
        del pdf.Root["/OCProperties"]


def _aplanar_archivo(path):
    """Núcleo SERIAL: aplana TODAS las páginas del PDF in-place (des-anida + 1 pasada de saneo +
    estado gráfico + Creator/Producer + PDF 1.6, colores CMYK EXACTOS). Lanza si algo falla."""
    pdf = pikepdf.open(path, allow_overwriting_input=True)
    for page in pdf.pages:
        _flatten(pdf, page, es_pagina=True)      # des-anida los Form XObjects (inline byte a byte)
        _procesar_contenido(pdf, page)           # 1 pasada: sanea texto + saca OCG + consolida ICC + huérfanos
        _declarar_estado_grafico(pdf, page)      # ExtGState opaco + /GSflat
    if "/OutputIntents" in pdf.Root:
        del pdf.Root["/OutputIntents"]           # Illustrator no lo tiene; el ICCBased de la página alcanza
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
    pdf.save(path, force_version="1.6")          # PDF 1.6 como Illustrator (máx. compat. RIP)
    pdf.close()


def _aplanar_una_pagina(path):
    """Worker de ProcessPool (spawn-safe: recibe una RUTA). Aplana un PDF de 1 página."""
    try:
        _aplanar_archivo(path)
        return True
    except Exception:
        return False


def aplanar_para_rip(path):
    """Aplana la HOJA in-place para el RIP. Con >1 página, aplana cada página EN PARALELO
    (ProcessPool — pikepdf/fitz NO son thread-safe → procesos, nunca hilos) y las reensambla:
    cada página es independiente y ya se aplanaba por separado → MISMO resultado, mucho más rápido
    en hojas con muchas piezas. Best-effort con fallback SERIAL si algo del paralelo falla."""
    try:
        src = pikepdf.open(path)
        npag = len(src.pages)
        if npag <= 1:
            src.close()
            _aplanar_archivo(path)
            return True
        # 1) partir en 1 PDF por página (aún SIN aplanar)
        tmps = []
        for i, pg in enumerate(src.pages):
            d = pikepdf.new(); d.pages.append(pg)
            tmp = f"{path}.__p{i}.pdf"
            d.save(tmp); d.close(); tmps.append(tmp)
        src.close()
        # 2) aplanar cada página en PARALELO
        from concurrent.futures import ProcessPoolExecutor
        try:
            with ProcessPoolExecutor(max_workers=min(len(tmps), max(2, (os.cpu_count() or 4) - 1))) as ex:
                oks = list(ex.map(_aplanar_una_pagina, tmps))
        except Exception:
            oks = [_aplanar_una_pagina(t) for t in tmps]   # si el pool no arranca, serial
        if not all(oks):
            raise RuntimeError("una página no se aplanó en paralelo")
        # 3) reensamblar las páginas ya aplanadas
        out = pikepdf.new()
        for tmp in tmps:
            s = pikepdf.open(tmp); out.pages.extend(s.pages); s.close()
        out.docinfo["/Creator"] = "TIZADA PRO"
        out.docinfo["/Producer"] = "TIZADA PRO"
        out.remove_unreferenced_resources()
        out.save(path, force_version="1.6")
        out.close()
        for tmp in tmps:
            try: os.remove(tmp)
            except Exception: pass
        return True
    except Exception as e:
        try:
            print(f"  [aplanar_rip] paralelo falló ({e}); aplano serial")
        except Exception:
            pass
        try:
            _aplanar_archivo(path)
            return True
        except Exception as e2:
            try:
                print(f"  [aplanar_rip] no se pudo aplanar {path}: {e2}")
            except Exception:
                pass
            return False
