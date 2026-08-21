"""
MOLDE REAL (.ai) — extracción de contornos por capa/talle y generación de piezas
================================================================================
Trabaja directamente sobre los .ai de USER (guardados con compatibilidad PDF):
  - dbPruebaCompleta.ai : la moldería. 1 mesa de trabajo por pieza; los talles
    viven en CAPAS superpuestas (XS..6XL, línea fem, 0..16).
  - Arte*.ai            : la plantilla de arte con el diseño aplicado a sangre
    sobre las mismas mesas.

Pipeline por pieza/talle:
  1. extraer_contorno_mesa(molde, mesa, talle)
        -> filtra los trazados de la capa del talle en esa mesa y toma el
           contorno (el cerrado de mayor área). Serializable -> BD del sistema.
  2. limpiar_capas(arte, mesa, capas_a_borrar)
        -> ELIMINA físicamente del content stream los bloques de contenido
           opcional (BDC /OC ... EMC) de las capas de moldería. No es un
           "ocultar": el contenido borrado no llega al RIP de imprenta.
  3. generar_pieza_real(...)
        -> PDF de la pieza = clip(contorno del talle) sobre el arte limpio,
           100 % vectorial, alineado en coordenadas de la mesa.
"""

import pymupdf as fitz
import pikepdf
from pikepdf import Name, parse_content_stream, unparse_content_stream
from pikepdf.models import PdfParsingError


# ─────────────────────────────────────────────────────────────────
# 1. CONTORNO DEL MOLDE (por mesa y talle)
# ─────────────────────────────────────────────────────────────────
def _contorno_de_drawing(d, cb, U, mesa, talle):
    """Convierte un trazado de page.get_drawings() en el dict de contorno
    serializable (segmentos en coords crudas del lienzo PDF + bounding boxes)."""
    r = d["rect"]

    def pt(p):  # MuPDF (y abajo, escala real) -> unidades CRUDAS del lienzo PDF (y arriba)
        return (p.x / U + cb.x0, cb.y1 - p.y / U)

    def mismo(a, b):
        return a is not None and abs(a.x - b.x) < 0.05 and abs(a.y - b.y) < 0.05

    seg, actual = [], None
    for item in d["items"]:
        t = item[0]
        if t == "l":
            p1, p2 = item[1], item[2]
            if not mismo(actual, p1):
                seg.append(("m", *pt(p1)))
            seg.append(("l", *pt(p2)))
            actual = p2
        elif t == "c":
            p1, c1, c2, p2 = item[1], item[2], item[3], item[4]
            if not mismo(actual, p1):
                seg.append(("m", *pt(p1)))
            seg.append(("c", *pt(c1), *pt(c2), *pt(p2)))
            actual = p2
        elif t == "re":
            rr = item[1]
            x0r, y0r = pt(fitz.Point(rr.x0, rr.y1))
            seg.append(("re", x0r, y0r, rr.width / U, rr.height / U))
            actual = None
        elif t == "qu":
            # CUADRILÁTERO. PyMuPDF lo devuelve como un item propio, y no estaba contemplado: una
            # pieza dibujada SÓLO con quads salía con `segmentos == [("h",)]` — sin un solo punto.
            # No fallaba: la pieza se DETECTABA (tiene bbox) pero después `_bbox_segs` devolvía
            # None y quedaba fuera del nido en silencio. Pasó con dos tiras finas del molde real
            # («Cuello 4» y «Tapa costura»): la variable decía 8 piezas y se veían menos.
            q = item[1]
            ps = [q.ul, q.ur, q.lr, q.ll]
            if not mismo(actual, ps[0]):
                seg.append(("m", *pt(ps[0])))
            for _p in ps[1:]:
                seg.append(("l", *pt(_p)))
            seg.append(("l", *pt(ps[0])))
            actual = ps[0]
    seg.append(("h",))
    bbox_raw = (r.x0 / U + cb.x0, cb.y1 - r.y1 / U, r.x1 / U + cb.x0, cb.y1 - r.y0 / U)
    return {"segmentos": seg, "bbox_raw": bbox_raw, "user_unit": U,
            "bbox_mu": (r.x0, r.y0, r.x1, r.y1),
            "w": r.width, "h": r.height, "mesa": mesa, "talle": talle}


def _candidatos_mesa(page, talle):
    pr = page.rect
    return [d for d in page.get_drawings()
            if d.get("layer") == talle
            and d["rect"].width < pr.width * 1.2
            and d["rect"].height < pr.height * 1.2]


def extraer_contorno_mesa(doc_molde, mesa, talle):
    """Devuelve el contorno del talle en esa mesa (el trazado de mayor área),
    en coordenadas PDF de la mesa, más su bounding box. Listo para guardar en BD."""
    page = doc_molde[mesa - 1]
    cb = page.cropbox  # las mesas de un .ai comparten lienzo: convertir a coords de lienzo PDF
    U = page.rect.width / cb.width if cb.width else 1.0  # /UserUnit (mesas grandes de Illustrator)
    candidatos = _candidatos_mesa(page, talle)
    if not candidatos:
        raise ValueError(f"Mesa {mesa}: no hay trazados en la capa {talle!r}.")
    cont = max(candidatos, key=lambda d: d["rect"].width * d["rect"].height)
    return _contorno_de_drawing(cont, cb, U, mesa, talle)


def extraer_piezas_mesa(doc_molde, mesa, talle, area_min_cm2=0.25, lado_min_cm=0.3):
    """Devuelve TODAS las piezas (contornos significativos) de una capa de talle,
    no solo la mayor — para moldería con varias piezas en la misma mesa.
    Orden DETERMINISTA por bounding box (x0, y0): el índice de cada pieza es
    estable para un mismo archivo+talle, así se puede referenciar por índice."""
    CM = 28.3465
    page = doc_molde[mesa - 1]
    cb = page.cropbox
    U = page.rect.width / cb.width if cb.width else 1.0
    piezas = []
    for d in _candidatos_mesa(page, talle):
        r = d["rect"]
        w_cm, h_cm = r.width / U / CM, r.height / U / CM
        if w_cm * h_cm < area_min_cm2 or min(w_cm, h_cm) < lado_min_cm:
            continue
        piezas.append(_contorno_de_drawing(d, cb, U, mesa, talle))
    # ⛔ NO SE REORDENA (regla del usuario, 2026-08-18): las piezas quedan **en el orden del
    # archivo** — el mismo que se ve en el panel de capas de Illustrator. Antes se ordenaban
    # por posición en el lienzo (`bbox_mu` x,y) buscando un índice estable, pero eso es
    # justamente «acomodarlas»: cuando dos piezas están SUPERPUESTAS (moldería anidada) el
    # orden por posición cambia de un talle a otro, el índice deja de corresponder y el
    # nombre termina asignado a otra pieza. El orden de dibujo es igual de determinista y
    # además es el que el usuario ve y espera.
    return piezas


# ─────────────────────────────────────────────────────────────────
# 2. LIMPIEZA DE CAPAS (borrado físico del contenido opcional)
# ─────────────────────────────────────────────────────────────────
def _nombres_oc(operando, page):
    """Resuelve el operando de un BDC /OC al/los nombre(s) de capa (OCG)."""
    try:
        obj = operando
        if isinstance(obj, Name):
            props = page.Resources.Properties
            obj = props[str(obj)]
        if Name.Type in obj and obj.Type == Name.OCG:
            return [str(obj.Name)]
        if Name.Type in obj and obj.Type == Name.OCMD:
            ocgs = obj.OCGs
            if isinstance(ocgs, pikepdf.Array):
                return [str(o.Name) for o in ocgs]
            return [str(ocgs.Name)]
    except Exception:
        pass
    return []


def limpiar_capas(pdf, page, capas_a_borrar, conservar=None):
    """Reescribe el content stream de la página eliminando los bloques
    BDC /OC ... EMC cuya capa esté en `capas_a_borrar`.
    Si `conservar` (set de nombres NORMALIZADOS) se pasa → modo AISLAR: se borra todo
    bloque /OC cuya capa objetivo NO esté entre sus nombres (sirve para dejar SOLO una
    capa, aunque su contenido esté tagueado con varias capas a la vez — OCMD)."""
    def _n(s):
        return " ".join(str(s).lower().replace("-", " ").split())
    instrucciones = parse_content_stream(page)
    salida, oculto, prof_q = [], 0, 0
    for inst in instrucciones:
        op = str(inst.operator)
        if oculto > 0:
            if op in ("BDC", "BMC"):
                oculto += 1
            elif op == "EMC":
                oculto -= 1
            continue
        if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
            nombres = _nombres_oc(inst.operands[1], page)
            if conservar is not None:
                quitar = not any(_n(n) in conservar for n in nombres)
            else:
                quitar = any(n in capas_a_borrar for n in nombres)
            if quitar:
                oculto = 1
                continue
        if op in ("BDC", "BMC", "EMC", "MP", "DP"):
            continue  # quitar TODOS los marcadores de capa del contenido conservado
        # contabilidad de estado gráfico: el borrado de bloques puede dejar
        # aperturas/cierres huérfanos que Acrobat NO tolera (aborta el render)
        if op == "q":
            prof_q += 1
        elif op == "Q":
            if prof_q == 0:
                continue          # Q huérfana (su q vivía en un bloque borrado)
            prof_q -= 1
        salida.append(inst)
    for _ in range(prof_q):          # cerrar aperturas pendientes
        salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("Q")))
    page.Contents = pdf.make_stream(unparse_content_stream(salida))


# Operadores de PINTADO (lo único que se suprime para el contenido que NO es del objeto).
_PAINT_PATH = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*"}   # -> se reemplazan por `n`
_PAINT_TEXT = {"Tj", "TJ", "'", '"'}                            # -> se eliminan (glifos)
_PAINT_DROP = {"Do", "sh"}                                      # XObject / sombreado
_CLIP_OPS = {"W", "W*"}                                          # recorte


def _norm_capa(s):
    """Normaliza un nombre de capa EXACTAMENTE igual que motor_pedido._norm_nombre
    (NFKD + sin acentos + minúsculas + guiones→espacio): si difiere, las capas con
    acentos (Diseño, Año…) nunca matchean y el objeto sale vacío."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace("-", " ").split())


def _raspar_pintado(pdf, page, suprimir_fn):
    """Núcleo: reescribe el content-stream conservando TODO el estado gráfico (color, CTM,
    q/Q, estado de texto) en su orden ORIGINAL, y suprimiendo SOLO el PINTADO del contenido
    para el cual `suprimir_fn(pila_de_capas)` da True (`pila` = lista de sets de nombres OC
    abiertos). Conservar las órdenes de color/estado es CLAVE: borrar bloques enteros
    desbalancea el estado y le cambia el color HEREDADO a otras capas (ej. el editable sin
    color propio que terminaba verde/negro). Los trazos suprimidos se descartan con `n`, los
    glifos/imágenes/sombreados se omiten, los recortes ajenos se quitan."""
    instrucciones = parse_content_stream(page)
    salida, pila = [], []
    for inst in instrucciones:
        op = str(inst.operator)
        if op in ("BDC", "BMC"):
            nombres = set()
            if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
                nombres = {_norm_capa(x) for x in _nombres_oc(inst.operands[1], page)}
            pila.append(nombres)
            continue
        if op == "EMC":
            if pila:
                pila.pop()
            continue
        if op in ("MP", "DP"):
            continue
        if suprimir_fn(pila):
            if op in _PAINT_PATH:
                salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("n")))
                continue
            if op in _PAINT_TEXT:
                if op == "'":                                   # avanzar línea sin pintar
                    salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("T*")))
                elif op == '"' and len(inst.operands) == 3:
                    salida.append(pikepdf.ContentStreamInstruction([inst.operands[0]], pikepdf.Operator("Tw")))
                    salida.append(pikepdf.ContentStreamInstruction([inst.operands[1]], pikepdf.Operator("Tc")))
                    salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("T*")))
                continue                                        # Tj/TJ: descartar glifos
            if op in _PAINT_DROP or op.upper().replace("_", " ") == "INLINE IMAGE":
                continue                                        # XObject/sombreado/imagen inline
            if op in _CLIP_OPS:
                continue                                        # no dejar recortes ajenos
        salida.append(inst)
    page.Contents = pdf.make_stream(unparse_content_stream(salida))


def aislar_capa(pdf, page, objetivo):
    """AÍSLA una capa OCG dejando SOLO su contenido pintado (suprime el pintado de TODO lo
    demás), conservando el estado gráfico → el objeto se pinta con su color EXACTO (CMYK/spot).
    `objetivo` = nombre(s) de la capa a conservar (str o set)."""
    obj = {_norm_capa(objetivo)} if isinstance(objetivo, str) else {_norm_capa(o) for o in objetivo}
    _raspar_pintado(pdf, page, lambda pila: not any(frame and (obj & frame) for frame in pila))


_FILL_PATH = {"f", "F", "f*", "b", "b*", "B", "B*"}   # ops que RELLENAN (llevan color de fill)
_STROKE_PATH = {"S", "s", "b", "b*", "B", "B*"}       # ops que TRAZAN (llevan color de stroke)


def recolorar_capa(pdf, page, objetivo, cmyk_fill=None, cmyk_stroke=None):
    """Cambia el COLOR de una capa OCG editable sin tocar su forma ni el resto del arte.

    Recorre el content-stream y, DENTRO del frame de la capa objetivo, antes de cada operación
    que rellena/traza inyecta el color CMYK pedido (`k` para relleno, `K` para trazo). No borra
    ninguna orden del stream: sólo agrega la orden de color justo antes de pintar, así el estado
    gráfico queda intacto (mismo criterio que `_raspar_pintado`: no desbalancear q/Q ni heredar
    colores a otras capas). CMYK directo = exacto para sublimación (sin re-cuantizar).

    `cmyk_fill` / `cmyk_stroke` = tupla (c, m, y, k) en 0..1, o None para no tocar ese canal.
    OJO: sólo alcanza al contenido dibujado DENTRO de la capa; si el objeto es un XObject (`Do`),
    el color vive adentro del XObject y esto no lo cambia (limitación conocida, ver §10.b)."""
    obj = {_norm_capa(objetivo)} if isinstance(objetivo, str) else {_norm_capa(o) for o in objetivo}
    dentro = lambda pila: any(frame and (obj & frame) for frame in pila)

    def _op_color(vals, letra):
        return pikepdf.ContentStreamInstruction(
            [pikepdf.Object.parse(f"{v:.6f}".encode()) for v in vals], pikepdf.Operator(letra))

    instrucciones = parse_content_stream(page)
    salida, pila = [], []
    for inst in instrucciones:
        op = str(inst.operator)
        if op in ("BDC", "BMC"):
            nombres = set()
            if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
                nombres = {_norm_capa(x) for x in _nombres_oc(inst.operands[1], page)}
            pila.append(nombres)
            salida.append(inst)
            continue
        if op == "EMC":
            if pila:
                pila.pop()
            salida.append(inst)
            continue
        # Justo antes de PINTAR dentro de la capa objetivo, fijar el color pedido.
        if dentro(pila):
            if cmyk_fill is not None and op in _FILL_PATH:
                salida.append(_op_color(cmyk_fill, "k"))
            if cmyk_stroke is not None and op in _STROKE_PATH:
                salida.append(_op_color(cmyk_stroke, "K"))
        salida.append(inst)
    page.Contents = pdf.make_stream(unparse_content_stream(salida))


def capa_admite_color(page, objetivo):
    """True si la capa OCG `objetivo` puede RECOLOREARSE con `recolorar_capa`: tiene al menos
    una operación de relleno/trazo (f/S/b…) DENTRO de su frame. Si sólo pinta vía XObject (`Do`)
    o imagen, el color vive adentro del XObject y NO se puede cambiar (limitación §10.b) → False.
    Se usa para deshabilitar el control de color en el editor para esos objetos."""
    obj = {_norm_capa(objetivo)} if isinstance(objetivo, str) else {_norm_capa(o) for o in objetivo}
    dentro = lambda pila: any(frame and (obj & frame) for frame in pila)
    pila = []
    for inst in parse_content_stream(page):
        op = str(inst.operator)
        if op in ("BDC", "BMC"):
            nombres = set()
            if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
                nombres = {_norm_capa(x) for x in _nombres_oc(inst.operands[1], page)}
            pila.append(nombres)
            continue
        if op == "EMC":
            if pila:
                pila.pop()
            continue
        if dentro(pila) and op in (_FILL_PATH | _STROKE_PATH):
            return True
    return False


def suprimir_capas(pdf, page, capas):
    """QUITA capas (guías, personalización…) SIN romper el estado gráfico: suprime SOLO su
    pintado pero conserva todas las órdenes de color/estado en orden → las demás capas
    heredan los colores EXACTOS. Reemplaza a `limpiar_capas` cuando hay objetos que heredan
    color (ej. editables sin color propio), que con el borrado de bloques salían de otro color."""
    sup = {_norm_capa(c) for c in capas}
    if not sup:
        return
    _raspar_pintado(pdf, page, lambda pila: any(frame and (sup & frame) for frame in pila))


# ─────────────────────────────────────────────────────────────────
# 2.b OBJETOS DENTRO DE UNA CAPA — partir una capa «Editable …» en objetos
#     INDEPENDIENTES (mover/color/aislar por separado). Una capa OCG puede traer
#     VARIOS objetos pintados; el frame OCG es UNO solo, así que `aislar_capa` los
#     deja a TODOS. Para tratar cada objeto por su cuenta se recorre el content-stream
#     llevando la CTM (q/Q/cm) y el frame OCG, se agrupan construcción+pintado en
#     UNIDADES, y se opera por índice de instrucción (no por frame). Reusa el mismo
#     criterio que `variantes_molde._unidades_de_trazado` (que parte el molde en piezas).
# ─────────────────────────────────────────────────────────────────
import hashlib as _hashlib

_CONSTRUCCION = {"m", "l", "c", "v", "y", "re", "h"}
_TERMINADORES = _PAINT_PATH | {"n"}                 # cierran un trazado (pintado o clip/descarte)


def _mmul(a, b):
    """Composición de matrices PDF: `a` aplicada ANTES que `b` (lo que hace el operador `cm`)."""
    return (a[0]*b[0] + a[1]*b[2], a[0]*b[1] + a[1]*b[3],
            a[2]*b[0] + a[3]*b[2], a[2]*b[1] + a[3]*b[3],
            a[4]*b[0] + a[5]*b[2] + b[4], a[4]*b[1] + a[5]*b[3] + b[5])


def _mpt(m, x, y):
    return (m[0]*x + m[2]*y + m[4], m[1]*x + m[3]*y + m[5])


def _bbox_xobject(page, nombre, ctm):
    """BBox (coords PDF de la página) de un Form XObject `nombre Do` con la CTM vigente.
    None si no se puede resolver (imagen inline, recurso ausente…): el llamador usa un punto."""
    try:
        xo = page.Resources.XObject[nombre]
        bx = [float(v) for v in xo.BBox]
        M = [float(v) for v in xo.Matrix] if "/Matrix" in xo else [1, 0, 0, 1, 0, 0]
        m = _mmul(tuple(M), ctm)
        xs, ys = [], []
        for (px, py) in ((bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3])):
            qx, qy = _mpt(m, px, py)
            xs.append(qx); ys.append(qy)
        return (min(xs), min(ys), max(xs), max(ys))
    except Exception:
        return None


def _analizar_capa(page, objetivo):
    """Recorre el content-stream UNA vez y devuelve, para la capa OCG `objetivo`:
      • `instrucciones`: la lista parseada (para reescribir sin re-parsear → índices alineados).
      • `objetos`: [{obj_id, kind, bbox(PDF y-arriba), fill(cmyk|None), recolorable, i_paints:set}]
        — un objeto por trazado pintado / XObject de la capa. Se agrupa relleno+trazo del MISMO
        trazado (misma firma de puntos) en un solo objeto, pero se dejan SEPARADOS trazados
        distintos aunque compartan centro (ej. dos elipses CONCÉNTRICAS de un escudo — cada una es
        su propio objeto editable). `obj_id` = hash de la geometría (puntos de construcción) →
        ESTABLE ante reordenamiento del stream. Los clips (`W n`) NO son objetos.
      • `clips_capa_idx`: índices de instrucción de los clips que viven DENTRO de la capa (hay
        que conservarlos al aislar un objeto: recortan el dibujo).
      • `paint_idx_todos`: índices de TODAS las instrucciones de pintado real (cualquier capa)."""
    obj = _norm_capa(objetivo)
    instrucciones = list(parse_content_stream(page))
    ctm = (1, 0, 0, 1, 0, 0)
    pila_ctm, pila_oc = [], []
    ini = None; pts = []; clip = False
    fill = None
    unidades = []            # dicts: i, bbox, es_clip, capas, kind, fill_op, stroke_op, fill, sig
    paint_idx_todos = set()

    def _frame_capas():
        s = set()
        for f in pila_oc:
            s |= f
        return frozenset(s)

    for i, it in enumerate(instrucciones):
        op = str(it.operator)
        if op == "q":
            pila_ctm.append(ctm)
        elif op == "Q":
            ctm = pila_ctm.pop() if pila_ctm else ctm
        elif op == "cm":
            try:
                ctm = _mmul(tuple(float(v) for v in it.operands), ctm)
            except Exception:
                pass
        elif op == "k":                                   # color de RELLENO (device CMYK)
            try:
                fill = tuple(float(v) for v in it.operands)[:4]
            except Exception:
                fill = None
        elif op in ("scn", "sc"):
            # Illustrator pinta el relleno con `scn` sobre un ColorSpace ICCBased de 4 canales
            # (CMYK con perfil), no con `k`: sin esto el color de la figura salía vacío en el
            # editor. Solo se toma cuando son 4 números (CMYK); patrones/spot (con /Nombre) no.
            try:
                vals = [float(v) for v in it.operands]
                fill = tuple(vals) if len(vals) == 4 else fill
            except Exception:
                pass
        elif op in ("BDC", "BMC"):
            nombres = set()
            if op == "BDC" and len(it.operands) == 2 and str(it.operands[0]) == "/OC":
                nombres = {_norm_capa(x) for x in _nombres_oc(it.operands[1], page)}
            pila_oc.append(nombres)
        elif op == "EMC":
            if pila_oc:
                pila_oc.pop()
        elif op in _CONSTRUCCION:
            if ini is None:
                ini, pts, clip = i, [], False
            try:
                f = [float(v) for v in it.operands]
            except Exception:
                f = []
            if op == "re" and len(f) == 4:
                x, y, w, h = f
                for px, py in ((x, y), (x+w, y), (x, y+h), (x+w, y+h)):
                    pts.append(_mpt(ctm, px, py))
            else:
                for k in range(0, len(f) - 1, 2):
                    pts.append(_mpt(ctm, f[k], f[k+1]))
        elif op in ("W", "W*"):
            clip = True
        elif op in _TERMINADORES:
            if pts:
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                bbox = (min(xs), min(ys), max(xs), max(ys))
                es_clip = clip or op == "n"
                fill_op = op in _FILL_PATH
                stroke_op = op in _STROKE_PATH
                if not es_clip:
                    paint_idx_todos.add(i)
                # FIRMA de geometría = puntos de construcción redondeados: dos ops que pintan el
                # MISMO trazado (relleno y trazo del mismo path) comparten firma → un solo objeto;
                # trazados distintos (aunque concéntricos) tienen firma distinta → objetos aparte.
                sig = ("v",) + tuple((round(px, 1), round(py, 1)) for px, py in pts)
                unidades.append({"i": i, "bbox": bbox, "es_clip": es_clip, "capas": _frame_capas(),
                                 "kind": "vector", "fill_op": fill_op, "stroke_op": stroke_op,
                                 "fill": (fill if fill_op else None), "sig": sig})
            ini, pts, clip = None, [], False
        elif op == "Do":
            nom = str(it.operands[0]) if it.operands else ""
            bbox = _bbox_xobject(page, nom, ctm)
            if bbox is None:
                bbox = (ctm[4], ctm[5], ctm[4], ctm[5])
            paint_idx_todos.add(i)
            sig = ("do", nom, round(ctm[0], 3), round(ctm[3], 3), round(ctm[4], 1), round(ctm[5], 1))
            unidades.append({"i": i, "bbox": bbox, "es_clip": False, "capas": _frame_capas(),
                             "kind": "xobject", "fill_op": False, "stroke_op": False, "fill": None, "sig": sig})
        elif op in _PAINT_TEXT:
            # El TEXTO también es pintado: si no se cataloga, el aislado por índice deja el texto
            # de las OTRAS capas (se colaba el rótulo de «guías» arriba de la mesa) y, al revés,
            # se comería el texto de la capa objetivo. Una unidad por operador de texto.
            bbox = (ctm[4], ctm[5], ctm[4], ctm[5])
            paint_idx_todos.add(i)
            sig = ("tx", i)
            unidades.append({"i": i, "bbox": bbox, "es_clip": False, "capas": _frame_capas(),
                             "kind": "texto", "fill_op": False, "stroke_op": False, "fill": None, "sig": sig})
        elif op == "sh":
            bbox = (ctm[4], ctm[5], ctm[4], ctm[5])
            paint_idx_todos.add(i)
            sig = ("sh", round(ctm[4], 1), round(ctm[5], 1), i)
            unidades.append({"i": i, "bbox": bbox, "es_clip": False, "capas": _frame_capas(),
                             "kind": "shading", "fill_op": False, "stroke_op": False, "fill": None, "sig": sig})

    # Unidades de la capa objetivo (las que llevan la capa en su frame OCG).
    de_capa = [u for u in unidades if obj in u["capas"]]
    clips_capa_idx = {u["i"] for u in de_capa if u["es_clip"]}   # clips de la capa → conservar al aislar
    pintadas = [u for u in de_capa if not u["es_clip"]]

    # Agrupar por FIRMA de geometría: relleno+trazo del mismo trazado juntos; trazados distintos
    # (incluidas figuras concéntricas) separados. Cada firma = un objeto editable.
    por_sig = {}
    orden_sig = []
    for u in pintadas:
        s = u["sig"]
        if s not in por_sig:
            por_sig[s] = []; orden_sig.append(s)
        por_sig[s].append(u)

    objetos = []
    for s in orden_sig:
        us = por_sig[s]
        b = [min(u["bbox"][0] for u in us), min(u["bbox"][1] for u in us),
             max(u["bbox"][2] for u in us), max(u["bbox"][3] for u in us)]
        oid = _hashlib.sha1(repr(s).encode()).hexdigest()[:8]      # id ESTABLE por la geometría
        i_paints = {u["i"] for u in us}
        fill_op = any(u["fill_op"] for u in us)
        stroke_op = any(u["stroke_op"] for u in us)
        fillc = next((list(u["fill"]) for u in us if u["fill"] is not None), None)
        objetos.append({
            "obj_id": oid, "kind": us[0]["kind"], "bbox": tuple(b),
            "fill": fillc, "recolorable": bool(fill_op or stroke_op),
            "fill_op": fill_op, "stroke_op": stroke_op, "i_paints": i_paints,
        })
    # Orden de dibujo estable (por la 1ª instrucción de cada objeto): así el redibujo respeta
    # el apilado original cuando dos objetos se solapan.
    objetos.sort(key=lambda o: min(o["i_paints"]))
    return {"instrucciones": instrucciones, "objetos": objetos,
            "clips_capa_idx": clips_capa_idx, "paint_idx_todos": paint_idx_todos}


def objetos_de_capa(page, objetivo):
    """Objetos editables INDEPENDIENTES de la capa OCG `objetivo` (para la detección). Cada uno
    = un trazado pintado o un XObject de la capa. `bbox` en coords PDF (y-arriba)."""
    return _analizar_capa(page, objetivo)["objetos"]


def _cmyk_op(vals, letra):
    return pikepdf.ContentStreamInstruction(
        [pikepdf.Object.parse(f"{v:.6f}".encode()) for v in vals], pikepdf.Operator(letra))


def _reescribir_por_indice(pdf, page, instrucciones, suprimir_idx, recolor_idx=None,
                           conservar_marcadores=False):
    """Reescribe el content-stream a partir de `instrucciones` (ya parseadas): para cada
    instrucción de PINTADO cuyo índice está en `suprimir_idx`, SUPRIME el pintado (misma mecánica
    que `_raspar_pintado`: trazos→`n`, glifos/imágenes/XObjects se omiten, clips se descartan);
    conserva el resto del estado gráfico intacto. `recolor_idx` = {idx: (cmyk_fill|None,
    cmyk_stroke|None)} inyecta el color justo antes de esa instrucción de relleno/trazo.
    `conservar_marcadores`: si False (aislar) los marcadores /OC se descartan (`sanear_oc` corre
    después); si True (suprimir un objeto en la base) se CONSERVAN → una `suprimir_capas` posterior
    todavía encuentra los frames OCG (un raspado consume los marcadores: por eso el orden importa)."""
    recolor_idx = recolor_idx or {}
    salida = []
    for i, inst in enumerate(instrucciones):
        op = str(inst.operator)
        if op in ("BDC", "BMC", "EMC", "MP", "DP"):
            if conservar_marcadores:
                salida.append(inst)
            continue                                      # marcadores de contenido opcional
        if i in suprimir_idx:
            if op in _PAINT_PATH:
                salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("n")))
                continue
            if op in _PAINT_TEXT:
                if op == "'":
                    salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("T*")))
                elif op == '"' and len(inst.operands) == 3:
                    salida.append(pikepdf.ContentStreamInstruction([inst.operands[0]], pikepdf.Operator("Tw")))
                    salida.append(pikepdf.ContentStreamInstruction([inst.operands[1]], pikepdf.Operator("Tc")))
                    salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("T*")))
                continue
            if op in _PAINT_DROP or op.upper().replace("_", " ") == "INLINE IMAGE":
                continue
            if op in _CLIP_OPS:
                continue
        cr = recolor_idx.get(i)
        if cr:
            if cr[0] is not None and op in _FILL_PATH:
                salida.append(_cmyk_op(cr[0], "k"))
            if cr[1] is not None and op in _STROKE_PATH:
                salida.append(_cmyk_op(cr[1], "K"))
        salida.append(inst)
    page.Contents = pdf.make_stream(unparse_content_stream(salida))


def aislar_objeto(pdf, page, objetivo, obj_id, cmyk_fill=None, cmyk_stroke=None):
    """AÍSLA UN objeto (por su `obj_id` de geometría) dentro de la capa OCG `objetivo`: deja SOLO
    su pintado (suprime el de los DEMÁS objetos de la capa y el del resto del arte), conservando
    los clips de la capa. Opcionalmente lo RECOLOREA (CMYK, sin tocar los otros). Espejo de
    `aislar_capa` pero a nivel objeto. Si `obj_id` no aparece → no deja nada de la capa (seguro)."""
    a = _analizar_capa(page, objetivo)
    tgt = next((o for o in a["objetos"] if o["obj_id"] == obj_id), None)
    keep = set(tgt["i_paints"]) if tgt else set()
    keep |= a["clips_capa_idx"]                           # conservar los recortes de la capa
    suprimir = a["paint_idx_todos"] - keep
    recolor = {}
    if tgt and (cmyk_fill is not None or cmyk_stroke is not None):
        for i in tgt["i_paints"]:
            recolor[i] = (cmyk_fill, cmyk_stroke)
    _reescribir_por_indice(pdf, page, a["instrucciones"], suprimir, recolor)


def aislar_capa_objetos(pdf, page, objetivo, colores=None):
    """AÍSLA la capa OCG `objetivo` ENTERA (TODOS sus objetos, como una sola unidad) pero
    RECOLOREANDO CADA OBJETO POR SEPARADO: `colores` = {obj_id: (cmyk_fill|None, cmyk_stroke|None)}.

    Es la mezcla de `aislar_capa` (la capa es UNA unidad: se mueve/escala junta) y `aislar_objeto`
    (el color es de CADA figura). Se usa SOLO cuando hay color por objeto; sin colores por objeto
    el motor sigue por `aislar_capa` (camino verificado, y el único que respeta el TEXTO de una
    capa: el recorrido por índice sólo cataloga trazados/XObjects/shadings)."""
    a = _analizar_capa(page, objetivo)
    keep = set(a["clips_capa_idx"])                       # conservar los recortes de la capa
    recolor = {}
    for o in a["objetos"]:
        keep |= o["i_paints"]
        c = (colores or {}).get(o["obj_id"])
        if c and (c[0] is not None or c[1] is not None):
            for i in o["i_paints"]:
                recolor[i] = (c[0], c[1])
    _reescribir_por_indice(pdf, page, a["instrucciones"], a["paint_idx_todos"] - keep, recolor)


def suprimir_objetos(pdf, page, objetivo, obj_ids, conservar_marcadores=False):
    """QUITA del arte SOLO los objetos indicados (por `obj_id`) de la capa OCG `objetivo`,
    dejando el resto de la capa (y del arte) intacto. `obj_ids=None` → suprime la capa ENTERA
    (equivale a `suprimir_capas({objetivo})`, para las capas de un solo objeto = compat).
    `conservar_marcadores=True` (base): mantiene los marcadores OCG para que una `suprimir_capas`
    POSTERIOR (guías/personalización) todavía encuentre sus frames."""
    if obj_ids is None:
        return suprimir_capas(pdf, page, {objetivo})
    ids = set(obj_ids)
    if not ids:
        return
    a = _analizar_capa(page, objetivo)
    suprimir = set()
    for o in a["objetos"]:
        if o["obj_id"] in ids:
            suprimir |= o["i_paints"]
    _reescribir_por_indice(pdf, page, a["instrucciones"], suprimir, None, conservar_marcadores)


def capa_admite_color_objeto(page, objetivo, obj_id):
    """True si el objeto `obj_id` de la capa `objetivo` puede recolorearse (tiene relleno/trazo
    DIRECTO; XObject/imagen no). Espejo de `capa_admite_color` a nivel objeto."""
    o = next((o for o in objetos_de_capa(page, objetivo) if o["obj_id"] == obj_id), None)
    return bool(o and o["recolorable"])


# ─────────────────────────────────────────────────────────────────
# 3. GENERACIÓN DE LA PIEZA
# ─────────────────────────────────────────────────────────────────
def generar_pieza_real(contorno, path_arte, capas_molde, path_salida=None,
                       borde_mm=2.0, color_borde_cmyk=(0, 0, 0, 0.85)):
    """Pieza = clip(contorno del talle) sobre el arte de la misma mesa,
    con las capas indicadas borradas, más un BORDE DE CORTE impreso:
    `borde_mm` EXTERNO al contorno (no invade el diseño), en `color_borde_cmyk`.
    Técnica: se traza el contorno con grosor 2×borde DEBAJO del arte recortado;
    el arte cubre la mitad interna y queda visible solo la mitad externa."""
    x0, y0, x1, y1 = contorno["bbox_raw"]
    W, H = contorno["w"], contorno["h"]  # tamaño real en puntos (sin UserUnit)
    b = borde_mm / 10 * 28.3465          # mm -> puntos

    arte = pikepdf.open(path_arte)
    pag = arte.pages[contorno["mesa"] - 1]
    limpiar_capas(arte, pag, set(capas_molde))
    xobj_src = pag.as_form_xobject()

    out = pikepdf.Pdf.new()
    page = out.add_blank_page(page_size=(W + 2 * b, H + 2 * b))
    xobj = out.copy_foreign(xobj_src)
    # la Matrix del XObject ya incorpora /UserUnit (pikepdf la genera): leerla y componer en su espacio
    S = float(xobj.Matrix[0]) if "/Matrix" in xobj else 1.0
    nombre = page.add_resource(xobj, Name.XObject, prefix="Arte")

    def fseg(s):
        coords = " ".join(f"{v * S:.3f}" for v in s[1:])
        return f"{coords} {s[0]}".strip()

    ops = "\n".join(fseg(s) for s in contorno["segmentos"])
    c, m, y, k = color_borde_cmyk
    borde = ""
    if borde_mm > 0:
        # clip par-impar (rectángulo grande + contorno) = SOLO el exterior de la pieza;
        # el trazo de grosor 2×b queda recortado a su mitad externa: borde de `b` exacto
        # que no puede invadir el diseño, sea cual sea la opacidad del arte.
        rx, ry = x0 * S - 4 * b, y0 * S - 4 * b
        borde = (f"q\n"
                 f"{rx:.3f} {ry:.3f} {W + 8 * b:.3f} {H + 8 * b:.3f} re\n"
                 f"{ops}\nW* n\n"
                 f"{ops}\n"
                 f"{2 * b:.3f} w 1 j 1 J {c} {m} {y} {k} K\n"
                 f"S\nQ\n")
    stream = (f"q\n1 0 0 1 {b - x0 * S:.3f} {b - y0 * S:.3f} cm\n"
              f"{borde}"
              f"q\n{ops}\nW n\n"
              f"{nombre} Do\nQ\nQ\n")
    page.Contents = out.make_stream(stream.encode())
    if path_salida:
        out.save(path_salida)
    return out


# ─────────────────────────────────────────────────────────────────
# 4. ETIQUETA DE PIEZA (Talle-Pieza-#) desde el ancla de la plantilla
# ─────────────────────────────────────────────────────────────────
import math

MM = 2.83465  # puntos por mm


def extraer_ancla_etiqueta(path_molde, mesa, talle, patron="Talle-Pieza"):
    """Busca el placeholder de etiqueta en la capa del talle y devuelve su
    ancla: origen, ángulo (grados) y tamaño de fuente. El diseñador define
    DÓNDE y CÓMO va la etiqueta posicionando el placeholder en la plantilla."""
    doc = fitz.open(path_molde)
    for c in doc.layer_ui_configs():
        if c["text"] != talle:
            doc.set_layer_ui_config(c["number"], action=2)
    page = doc[mesa - 1]
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            texto = "".join(s["text"] for s in line["spans"])
            if patron in texto:
                s0 = line["spans"][0]
                dx, dy = line["dir"]
                return {"origen": tuple(s0["origin"]),
                        "angulo": math.degrees(math.atan2(-dy, dx)),
                        "size": s0["size"]}
    return None


def estampar_etiqueta(pieza_fitz, contorno, ancla, texto, borde_mm=2.0,
                      color_cmyk=(0, 0, 0, 1), escala=1.0,
                      fontname="helvetica-bold", fontfile=None):
    """Estampa la etiqueta real (ej. 'M-Espalda-#01') en la pieza generada,
    en la posición y ángulo del placeholder de la plantilla."""
    b = borde_mm * MM
    x0m, y0m, _, _ = contorno["bbox_mu"]
    px = ancla["origen"][0] - x0m + b
    py = ancla["origen"][1] - y0m + b
    page = pieza_fitz[0]
    punto = fitz.Point(px, py)
    page.insert_text(punto, texto, fontsize=ancla["size"] * escala,
                     fontname=fontname, fontfile=fontfile, color=color_cmyk,
                     morph=(punto, fitz.Matrix(ancla["angulo"])))


# ─────────────────────────────────────────────────────────────────
# 5. SANEAMIENTO PARA ACROBAT: eliminar todo contenido opcional
# ─────────────────────────────────────────────────────────────────
def _quitar_marcadores(pdf, stream_obj):
    try:
        inst = parse_content_stream(stream_obj)
        fuera, prof_q, cambio = [], 0, False
        for i in inst:
            op = str(i.operator)
            if op in ("BDC", "BMC", "EMC", "MP", "DP"):
                cambio = True
                continue
            if op == "q":
                prof_q += 1
            elif op == "Q":
                if prof_q == 0:
                    cambio = True
                    continue
                prof_q -= 1
            fuera.append(i)
        for _ in range(prof_q):
            fuera.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("Q")))
            cambio = True
        if cambio:
            stream_obj.write(unparse_content_stream(fuera))
    except Exception:
        pass


def sanear_oc(pdf, page, _vistos=None):
    """Recorre los XObjects anidados de la página borrando claves /OC y
    marcadores de contenido opcional. Sin esto, Acrobat oculta los grupos
    cuyo OCG quedó huérfano (Illustrator y MuPDF los muestran igual)."""
    if _vistos is None:
        _vistos = set()

    def caminar(res):
        if res is None or "/XObject" not in res:
            return
        for k in list(res.XObject.keys()):
            try:
                xo = res.XObject[k]
                og = xo.objgen
                if og in _vistos:
                    continue
                _vistos.add(og)
                if "/OC" in xo:
                    del xo["/OC"]
                subtipo = str(xo.get("/Subtype", ""))
                if subtipo == "/Form":
                    _quitar_marcadores(pdf, xo)
                    caminar(xo.get("/Resources"))
            except Exception:
                pass

    caminar(page.get("/Resources"))


# ─────────────────────────────────────────────────────────────────
# 6. CATÁLOGO DE TIPOGRAFÍAS — validación en el alta del arte (Fase B)
# ─────────────────────────────────────────────────────────────────
def fuentes_requeridas(path_arte, capa_personalizable="Personalizable"):
    """Fuentes que el MOTOR va a necesitar como ARCHIVO para estampar texto
    dinámico: las que usan los placeholders de personalización y de etiqueta.
    Devuelve nombres PostScript sin prefijo de subset (ABCDEF+)."""
    requeridas = {}
    for capa in (capa_personalizable, None):  # None = capas de talles (etiquetas)
        doc = fitz.open(path_arte)
        for c in doc.layer_ui_configs():
            on = (c["text"] == capa) if capa else (c["text"] not in ("Fondo", "Capa 1", capa_personalizable))
            doc.set_layer_ui_config(c["number"], action=0 if on else 2)
        for i in range(len(doc)):
            for b in doc[i].get_text("dict")["blocks"]:
                if b.get("type") != 0:
                    continue
                for l in b["lines"]:
                    for s in l["spans"]:
                        nombre = s["font"].split("+")[-1]
                        uso = "personalización" if capa else "etiquetas"
                        requeridas.setdefault(nombre, set()).add(uso)
    return {n: sorted(usos) for n, usos in requeridas.items()}


def validar_fuente_subida(path_ttf, nombre_postscript_pedido):
    """Verifica que el archivo subido por el cliente sea realmente la fuente
    pedida (compara el nombre interno del archivo). Devuelve (ok, nombre)."""
    try:
        f = fitz.Font(fontfile=path_ttf)
        interno = f.name.replace(" ", "")
        pedido = nombre_postscript_pedido.replace(" ", "").replace("-", "")
        return (pedido.lower() in interno.replace("-", "").lower()
                or interno.replace("-", "").lower() in pedido.lower()), f.name
    except Exception as e:
        return False, str(e)


def chequear_catalogo(path_arte, catalogo):
    """Chequeo de intake: ¿están en el catálogo todas las fuentes que el motor
    necesita? `catalogo` = {nombre_postscript: ruta_ttf}. Devuelve (faltantes,
    requeridas) — si hay faltantes, el pedido NO entra hasta que se suban."""
    req = fuentes_requeridas(path_arte)
    faltantes = {n: usos for n, usos in req.items() if n not in catalogo}
    return faltantes, req


# ─────────────────────────────────────────────────────────────────
# 7. OBJETOS POR TALLE — conservar la capa del talle, sin la moldería
# ─────────────────────────────────────────────────────────────────
def geometrias_base(doc_base, mesa, talle):
    """Bounding boxes (en unidades crudas del lienzo) de la moldería de la
    plantilla BASE en esa mesa+talle: lo que hay que QUITAR de la capa del
    talle al generar (contornos, piquetes, líneas internas)."""
    page = doc_base[mesa - 1]
    cb = page.cropbox
    U = page.rect.width / cb.width if cb.width else 1.0
    geoms = []
    for d in page.get_drawings():
        if d.get("layer") != talle:
            continue
        r = d["rect"]
        geoms.append((r.x0 / U + cb.x0, cb.y1 - r.y1 / U, r.x1 / U + cb.x0, cb.y1 - r.y0 / U))
    return geoms


def limpiar_capas_conservando_talle(pdf, page, capas_a_borrar, talle, geoms_base, tol=0.8):
    """Como limpiar_capas, pero CONSERVA la capa `talle`: dentro de ella
    elimina la moldería de la plantilla (paths cuyo bbox coincide con la
    base) y todo el texto (placeholders); lo demás —objetos del diseñador
    específicos de ese talle, ej. vivos— se conserva VERBATIM (colores y
    tintas intactos)."""
    instrucciones = parse_content_stream(page)
    salida, prof_q = [], 0
    oculto, en_talle, prof_mc = 0, False, 0
    camino, pts, en_texto = [], [], False

    def coincide_base(bb):
        if bb is None:
            return False
        for g in geoms_base:
            if (abs(bb[0]-g[0]) < tol and abs(bb[1]-g[1]) < tol and
                    abs(bb[2]-g[2]) < tol and abs(bb[3]-g[3]) < tol):
                return True
        return False

    PINTURA = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"}
    for inst in instrucciones:
        op = str(inst.operator)
        if oculto > 0:
            if op in ("BDC", "BMC"):
                oculto += 1
            elif op == "EMC":
                oculto -= 1
            continue
        if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
            nombres = _nombres_oc(inst.operands[1], page)
            if talle in nombres:
                en_talle, prof_mc = True, 1
                continue
            if any(n in capas_a_borrar for n in nombres):
                oculto = 1
                continue
        if en_talle:
            if op in ("BDC", "BMC"):
                prof_mc += 1; continue
            if op == "EMC":
                prof_mc -= 1
                if prof_mc == 0:
                    en_talle = False
                continue
            if op == "BT":
                en_texto = True; continue
            if op == "ET":
                en_texto = False; continue
            if en_texto:
                continue                      # texto de la capa del talle: fuera (placeholders)
            if op in ("m", "l", "c", "v", "y", "re", "h", "W", "W*"):
                camino.append(inst)
                for k in range(0, len(inst.operands) - 1, 2):
                    try:
                        pts.append((float(inst.operands[k]), float(inst.operands[k+1])))
                    except Exception:
                        pass
                if op == "re" and len(inst.operands) == 4:
                    x, y, w, h = (float(v) for v in inst.operands)
                    pts.extend([(x, y), (x + w, y + h)])
                continue
            if op in PINTURA:
                bb = (min(p[0] for p in pts), min(p[1] for p in pts),
                      max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None
                if not coincide_base(bb):
                    salida.extend(camino)
                    salida.append(inst)       # objeto del diseñador: se conserva
                camino, pts = [], []
                continue
            # operadores de estado (colores, cm, gs, q/Q): conservar
        if op in ("BDC", "BMC", "EMC", "MP", "DP"):
            continue
        if op == "q":
            prof_q += 1
        elif op == "Q":
            if prof_q == 0:
                continue
            prof_q -= 1
        salida.append(inst)
    for _ in range(prof_q):
        salida.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator("Q")))
    page.Contents = pdf.make_stream(unparse_content_stream(salida))
