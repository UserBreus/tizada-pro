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
import os
import pikepdf
from pikepdf import Name, parse_content_stream, unparse_content_stream

# ⚡ NIVEL DE COMPRESIÓN al escribir PDFs (2026-09-07). qpdf deflatea con el nivel por defecto de
# zlib (6): guardar la hoja aplanada del pedido de 5 prendas costaba 6,9 s; con nivel 1 son 1,7 s
# y el archivo pasa de 18,0 a 20,4 MB. Es SIN PÉRDIDA (flate es flate: ni un byte del contenido
# cambia, sólo cuánto se empaqueta), así que el color y el vector siguen exactos. Vale para todo
# el proceso (es un ajuste global de pikepdf). `TIZADA_FLATE=6` vuelve al de siempre.
try:
    pikepdf.settings.set_flate_compression_level(int(os.environ.get("TIZADA_FLATE") or 1))
except Exception:
    pass


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


def _instr(operands, op):
    """Una instrucción de content-stream. 🔴 SIEMPRE `ContentStreamInstruction`, nunca la tupla
    `(operandos, op)`: `unparse_content_stream` acepta las dos, pero con tuplas tarda **40 veces
    más** (medido: 322 mil ops → 0,4 s como instrucciones, 16,6 s como tuplas). Este módulo
    armaba TODO con tuplas y la hoja de 900 mil operadores pasaba por ahí dos veces: de los 542 s
    que tardaba el aplanado de un pedido real, 367 eran eso."""
    return pikepdf.ContentStreamInstruction(operands, op if isinstance(op, pikepdf.Operator) else pikepdf.Operator(op))


def _remap_ops(ops, remap):
    """Renombra los recursos que `remap` dice, dejando las demás instrucciones TAL CUAL (el mismo
    objeto, sin copiar): sólo se crea una instrucción nueva cuando un operando cambia."""
    if not remap:
        return ops
    out = []
    for inst in ops:
        k = _OPKIND.get(str(inst.operator))
        if k and k in remap:
            r = remap[k]
            operands = [pikepdf.Name(r.get(str(o), str(o))) if isinstance(o, pikepdf.Name) else o
                        for o in inst.operands]
            inst = _instr(operands, inst.operator)
        out.append(inst)
    return out


def _flatten(pdf, container, es_pagina=False, _hechos=None):
    """Des-anida los XObject de Form: su contenido pasa al stream que los usaba. Devuelve las
    instrucciones ya aplanadas del contenedor (la página las recibe en memoria y
    `_procesar_contenido` sigue con ellas sin volver a parsear 900 mil operadores).

    🔴 `_hechos` guarda, por objeto, sus instrucciones YA aplanadas. Una tizada coloca la misma
    pieza una vez por prenda —45 colocaciones de 27 piezas en un pedido real— y cada `Do`
    disparaba un `_flatten` completo del mismo XObject: parsear y reescribir su stream, una vez
    por colocación. Y cada nivel de anidado (la página → el envoltorio de `show_pdf_page` → la
    pieza → la mesa del molde) volvía a parsear lo que el nivel de abajo acababa de escribir.
    Ahora cada XObject se parsea UNA vez y sus instrucciones se reusan tal cual: aplanar un
    objeto ya aplanado da lo mismo, pero cuesta. Los XObjects no se reescriben: al terminar
    quedan huérfanos y `_procesar_contenido` los saca de los recursos.
    """
    if _hechos is None:
        _hechos = {}
    try:
        _id = container.objgen if hasattr(container, "objgen") else None
    except Exception:
        _id = None
    if _id == (0, 0):
        _id = None
    if _id is not None and _id in _hechos:
        return _hechos[_id]
    try:
        ops = list(parse_content_stream(container))
    except Exception:
        if not es_pagina:
            raise                     # un XObject ilegible aborta el aplanado (best-effort, como siempre)
        return None                   # la página no se toca; `_procesar_contenido` lo reintenta y saltea
    res = container.get("/Resources")
    xobjs = res.get("/XObject") if res is not None else None
    if xobjs is None or not ops:
        if _id is not None:
            _hechos[_id] = ops
        return ops
    new_ops = []
    _num = lambda v: pikepdf.Object.parse(f"{float(v):.6f}".encode("ascii"))
    for inst in ops:
        operands = inst.operands
        if str(inst.operator) == "Do" and len(operands) and isinstance(operands[0], pikepdf.Name):
            nm = str(operands[0])
            xo = xobjs.get(nm) if nm in xobjs else None
            if xo is not None and xo.get("/Subtype") == Name("/Form"):
                sub = _flatten(pdf, xo, es_pagina=False, _hechos=_hechos)
                remap = _merge_res(res, xo.get("/Resources", pikepdf.Dictionary()))
                sub = _remap_ops(sub, remap)
                new_ops.append(_instr([], "q"))
                mtx = xo.get("/Matrix")
                if mtx is not None:
                    new_ops.append(_instr([_num(x) for x in mtx], "cm"))
                bbox = xo.get("/BBox")
                if bbox is not None:
                    x0, y0, x1, y1 = [float(v) for v in bbox]
                    new_ops.append(_instr([_num(v) for v in (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))], "re"))
                    new_ops.append(_instr([], "W"))
                    new_ops.append(_instr([], "n"))
                new_ops.extend(sub)
                new_ops.append(_instr([], "Q"))
                continue
        new_ops.append(inst)
    if _id is not None:
        _hechos[_id] = new_ops
    if es_pagina:
        container.Contents = pdf.make_stream(unparse_content_stream(new_ops))
    return new_ops


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


def _procesar_contenido(pdf, page, ops=None):
    """UNA sola pasada por el content-stream de la página (ya aplanada) que hace lo que antes eran
    4 pasadas separadas (cada una re-parseaba el stream GIGANTE): (1) saca los bloques de texto
    fantasma (fuente inexistente / sin glifos), (2) saca los marcadores de capa OCG (BMC/BDC/EMC/
    MP/DP), (3) remapea los ColorSpace ICCBased duplicados a uno canónico, (4) junta los XObjects
    realmente usados para borrar los huérfanos. Mismo resultado byte a byte que las 4 pasadas, pero
    parseando el stream una vez → ~4× menos parse/unparse en hojas con muchas piezas.
    `ops` = las instrucciones que `_flatten` acaba de armar: con ellas no se parsea nada."""
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
    def _rmp(inst, o):
        if remap and o in _CS_OPS:
            operands = [pikepdf.Name(remap.get(str(x), str(x))) if isinstance(x, pikepdf.Name) else x for x in inst.operands]
            return _instr(operands, inst.operator)
        return inst                                        # sin cambio: la MISMA instrucción, sin copiar
    if ops is None:
        try:
            ops = list(parse_content_stream(page))
        except Exception:
            ops = None
    usados = set()
    _es_xobj = isinstance(page, pikepdf.Stream)   # un Form XObject: su contenido es el propio stream
    if ops is not None:
        out, block, in_bt = [], [], False
        falta_fuente = tiene_texto = False
        _MC = ("BDC", "BMC", "EMC", "MP", "DP")
        for inst in ops:
            o = str(inst.operator)
            if o in _MC:
                continue                                   # marcador de capa/estructura → fuera (no marca nada)
            if o == "BT":
                in_bt = True; block = [inst]; falta_fuente = tiene_texto = False
                continue
            if in_bt:
                block.append(_rmp(inst, o))
                if o == "Tf":
                    operands = inst.operands
                    if len(operands) and isinstance(operands[0], Name) and str(operands[0]) not in fonts:
                        falta_fuente = True
                elif o in ("Tj", "TJ", "'", '"'):
                    tiene_texto = True
                if o == "ET":
                    in_bt = False
                    if not (falta_fuente or not tiene_texto):
                        out.extend(block)                  # bloque de texto válido → se conserva
                    block = []
                continue
            if o == "Do":
                operands = inst.operands
                if len(operands) and isinstance(operands[0], Name):
                    usados.add(str(operands[0]))
            out.append(_rmp(inst, o))
        if _es_xobj:
            page.write(unparse_content_stream(out))
        else:
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


def _aplanar_un_nivel(pdf, page, _hechos):
    """UN SOLO NIVEL (2026-09-04, la hoja compartida): la página CONSERVA sus `Do` y se sanea el
    interior de cada Form XObject UNA vez —lo de adentro se des-anida y se limpia como siempre—,
    en vez de expandir cada colocación inline. Con 45 colocaciones de 27 piezas el aplanado total
    escribía 900.000 operadores (87 s); a 100 prendas eran ~30 min. Acá cada pieza se procesa una
    vez y la página queda con 900 `Do`.

    Lo que va al RIP es PDF/X-1a-like: XObjects de un nivel (permitidos por la norma y por
    cualquier RIP), sin capas, sin transparencia, fuentes embebidas o en curvas, ICC consolidado.
    El «error RIP» que originó este módulo era con tres niveles anidados + capas OCG: eso ya no
    existe por construcción. `TIZADA_APLANADO_TOTAL=1` vuelve al inline de siempre."""
    res = page.get("/Resources")
    xobjs = res.get("/XObject") if res is not None else None
    if xobjs is not None:
        for nm in [str(k) for k in xobjs.keys()]:
            xo = xobjs[nm]
            if xo.get("/Subtype") != Name("/Form"):
                continue
            try:
                _id = xo.objgen
            except Exception:
                _id = None
            if _id is not None and _id in _hechos:
                continue
            if xo.get("/TizadaBase") is not None and "/XObject" not in (xo.get("/Resources") or {}):
                # Base de la hoja compartida: nace de una página desplegada, sin marcadores de
                # capa y con las fuentes declaradas (contrato del desplegado). Parsear sus
                # 20.000 operadores para no cambiar nada costaba ~0,3 s por base.
                if _id is not None:
                    _hechos[_id] = True
                for _k in ("/OC", "/Group"):
                    if _k in xo:
                        del xo[_k]
                continue
            sub_ops = _flatten(pdf, xo, es_pagina=False, _hechos=_hechos)   # des-anida lo de ADENTRO
            _procesar_contenido(pdf, xo, sub_ops)                              # y lo sanea, una vez
            if _id is not None:
                _hechos[_id] = sub_ops
            if "/OC" in xo:
                del xo["/OC"]
            if "/Group" in xo:
                del xo["/Group"]              # sin grupos de transparencia (lo inline tampoco los tenía)
    try:
        ops = list(parse_content_stream(page))
    except Exception:
        ops = None
    _procesar_contenido(pdf, page, ops)       # la página: sus propios trazos (estampados) + los Do
    _declarar_estado_grafico(pdf, page)


def _unificar_icc(pdf):
    """Un solo stream ICC por perfil en TODO el archivo (página y XObjects): las bases copian el
    perfil de su mesa y con 9 mesas había hasta 9 copias del mismo perfil. Se reemplaza el stream
    dentro de cada `[/ICCBased s]` por el canónico; los nombres no cambian, así que ningún
    content-stream se reescribe."""
    import hashlib
    canon, vistos = {}, set()

    def _res(d):
        try:
            cs = d.get("/ColorSpace") if d is not None else None
        except Exception:
            cs = None
        if cs:
            for k in [str(x) for x in cs.keys()]:
                v = cs[k]
                try:
                    if isinstance(v, pikepdf.Array) and str(v[0]) == "/ICCBased":
                        h = hashlib.sha1(bytes(v[1].read_raw_bytes())).hexdigest()
                        if h in canon:
                            if v[1].objgen != canon[h].objgen:
                                v[1] = canon[h]
                        else:
                            canon[h] = v[1]
                except Exception:
                    pass
        try:
            xs = d.get("/XObject") if d is not None else None
        except Exception:
            xs = None
        if xs:
            for k in [str(x) for x in xs.keys()]:
                xo = xs[k]
                try:
                    og = xo.objgen
                except Exception:
                    og = None
                if og in vistos:
                    continue
                vistos.add(og)
                _res(xo.get("/Resources"))
    for page in pdf.pages:
        _res(page.get("/Resources"))


def _aplanar_archivo(path):
    """Núcleo SERIAL: aplana TODAS las páginas del PDF in-place (des-anida + 1 pasada de saneo +
    estado gráfico + Creator/Producer + PDF 1.6, colores CMYK EXACTOS). Lanza si algo falla.
    Default: UN NIVEL (ver `_aplanar_un_nivel`); `TIZADA_APLANADO_TOTAL=1`: todo inline."""
    # `with`: si el aplanado falla a mitad, el que llama REINTENTA sobre el MISMO archivo — y con
    # el handle anterior todavía abierto ese reintento se topaba con el archivo tomado.
    with pikepdf.open(path, allow_overwriting_input=True) as pdf:
        _total = bool(os.environ.get("TIZADA_APLANADO_TOTAL"))
        for page in pdf.pages:
            # 🔴 EL MEMO ES **POR PÁGINA**, NO POR ARCHIVO. `_hechos` guarda, por cada Form
            # XObject, su LISTA COMPLETA DE OPERADORES (una pieza de la tizada son ~2.900), y con
            # un dict único para todo el archivo esas listas quedaban vivas hasta el final: medido
            # 2026-09-15 sobre una hoja de 5 páginas y 112 piezas, el pico del aplanado pasa de
            # **+1.253 MB a +257 MB** (−80 %) creándolo acá adentro. En la hoja cada página es una
            # mesa independiente, así que casi no hay XObjects compartidos que reaprovechar: el
            # tiempo quedó igual (10,4 s las dos) y la salida es **idéntica** — mismo hash de la
            # página y de todos sus XObjects, y los mismos operadores de color con las mismas
            # cantidades. (El mismo razonamiento que ya estaba escrito en la rama `_total`.)
            _hechos = {}

            if _total:
                # `_hechos` es por página: en la hoja cada página es independiente y así el memo de las
                # piezas no crece con las páginas.
                ops = _flatten(pdf, page, es_pagina=True)            # des-anida los Form XObjects (inline byte a byte)
                _procesar_contenido(pdf, page, ops)                  # 1 pasada, sobre las instrucciones en memoria
                _declarar_estado_grafico(pdf, page)      # ExtGState opaco + /GSflat
            else:
                _aplanar_un_nivel(pdf, page, _hechos)
        _unificar_icc(pdf)
        # El OutputIntent (perfil de salida) se CONSERVA: es lo que le dice al RIP con qué perfil
        # se armó el archivo. Antes se borraba acá («Illustrator no lo tiene») y el servidor lo había
        # incrustado justo antes → el archivo final salía sin perfil (2026-09-04).
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
        # SERIAL por defecto (garantiza el mismo resultado que siempre, sin riesgo de perder
        # contenido al partir/reensamblar según la estructura del arte). El paralelo por página
        # (más rápido en hojas con muchas páginas) es OPT-IN con TIZADA_APLANADO_PARALELO=1.
        if not os.environ.get("TIZADA_APLANADO_PARALELO"):
            # 🔴 PERO EN UN PROCESO APARTE. El aplanado es, de lejos, lo que más memoria pide de
            # toda la tizada: medido 2026-09-15, **+622 MB** dentro del servidor, y no es un
            # desperdicio evitable — son las instrucciones ya parseadas de las mesas de diseño,
            # que el memo mantiene vivas A PROPÓSITO (sacarlas fue el arreglo que bajó el aplanado
            # de 542 s). O sea: no se puede achicar, pero SÍ se puede sacar de acá.
            #
            # En un hijo de un solo uso corre EL MISMO `_aplanar_archivo` —mismo código, mismo
            # resultado, sin partir ni reensamblar nada— y al terminar el proceso muere y el
            # sistema operativo recupera TODO. El servidor pasa de un pico de 938 MB a 418, que
            # importa de verdad cuando la máquina tiene además otros proyectos encima.
            # `TIZADA_APLANADO_EN_PROCESO=1` vuelve al de siempre (para depurar).
            if os.environ.get("TIZADA_APLANADO_EN_PROCESO"):
                _aplanar_archivo(path)
                return True
            try:
                from concurrent.futures import ProcessPoolExecutor
                with ProcessPoolExecutor(max_workers=1) as ex:
                    if ex.submit(_aplanar_una_pagina, path).result():
                        return True
                print("  [aplanar_rip] el proceso aparte no pudo; aplano acá mismo")
            except Exception as e:
                print(f"  [aplanar_rip] no se pudo aplanar aparte ({e}); aplano acá mismo")
            # Reintentar acá es seguro: `_aplanar_archivo` guarda al final, así que un fallo a
            # mitad deja el archivo SIN tocar (es la misma garantía en la que ya se apoyaba el
            # reintento serial del camino paralelo).
            _aplanar_archivo(path)
            return True
        # 🔴 TODO lo de abajo va con `finally`: si el paralelo falla, el que llama REINTENTA en
        # serie sobre el MISMO archivo. Sin cerrar los handles y sin borrar los temporales, ese
        # reintento se topaba con la hoja tomada y la carpeta del trabajo quedaba sembrada de
        # `<hoja>.__pN.pdf` para siempre.
        tmps, abiertos, out = [], [], None
        try:
            with pikepdf.open(path) as src:
                una_sola = len(src.pages) <= 1
                if not una_sola:
                    # 1) partir en 1 PDF por página (aún SIN aplanar)
                    for i, pg in enumerate(src.pages):
                        tmp = f"{path}.__p{i}.pdf"
                        tmps.append(tmp)      # se anota ANTES de escribir: si falla, se borra igual
                        with pikepdf.new() as d:
                            d.pages.append(pg)
                            d.save(tmp)
            if una_sola:                      # una sola página: el camino serial de siempre
                _aplanar_archivo(path)
                return True
            # 2) aplanar cada página en PARALELO
            from concurrent.futures import ProcessPoolExecutor
            try:
                # `TIZADA_PROCESOS` acota el paralelismo en servidores con poca RAM (cada worker
                # pesa ~200 MB). Sin la variable: como siempre (núcleos - 1).
                try:
                    _tope = int(os.environ.get("TIZADA_PROCESOS") or 0)
                except ValueError:
                    _tope = 0
                _w = max(1, _tope) if _tope else max(2, (os.cpu_count() or 4) - 1)
                with ProcessPoolExecutor(max_workers=min(len(tmps), _w)) as ex:
                    oks = list(ex.map(_aplanar_una_pagina, tmps))
            except Exception:
                oks = [_aplanar_una_pagina(t) for t in tmps]   # si el pool no arranca, serial
            if not all(oks):
                raise RuntimeError("una página no se aplanó en paralelo")
            # 3) reensamblar las páginas ya aplanadas. IMPORTANTE: mantener CADA PDF fuente ABIERTO
            # hasta después de out.save() — pikepdf copia perezoso y cerrar antes deja referencias
            # colgadas → se pierde contenido en algunas páginas. Por eso se cierran en el `finally`
            # (que corre DESPUÉS del save), y no de a uno acá.
            out = pikepdf.new()
            for tmp in tmps:
                s = pikepdf.open(tmp)
                out.pages.extend(s.pages)
                abiertos.append(s)
            out.docinfo["/Creator"] = "TIZADA PRO"
            out.docinfo["/Producer"] = "TIZADA PRO"
            out.remove_unreferenced_resources()
            out.save(path, force_version="1.6")
            return True
        finally:
            for _d in ([out] if out is not None else []) + abiertos:
                try:
                    _d.close()
                except Exception:
                    pass
            for tmp in tmps:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
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
