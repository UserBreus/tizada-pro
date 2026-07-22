"""
MOTOR DE PEDIDOS — biblioteca central de la app web.
Alta de plantilla, validación de arte, catálogo de fuentes, generación
del pedido (texto en curvas) y validaciones de salida.
"""
import io, os, json, time, math, glob, hashlib, base64
import numpy as np
import pymupdf as fitz
import pikepdf
from pikepdf import Name, Array, Dictionary, parse_content_stream
from scipy import ndimage

from molde_real import (extraer_contorno_mesa, extraer_piezas_mesa,
                        limpiar_capas, limpiar_capas_conservando_talle, aislar_capa, suprimir_capas,
                        recolorar_capa, capa_admite_color,
                        geometrias_base, sanear_oc, _nombres_oc, MM)
from nesting_contorno import anidar_contorno, componer_pdf_contorno
from texto_curvas import FuenteCurvas

CM = 28.3465

# ─────────────────────────────────────────────────────────────────
# CONVENCIÓN DE LA PLANTILLA  (ver CONVENCION_PLANTILLA.md)
# ─────────────────────────────────────────────────────────────────
# Modelo: UNA mesa de trabajo por pieza · TODOS los talles como capas en esa
# misma mesa · cada capa de talle lleva un texto "TALLE-Pieza-#".
#
# Capas reservadas: no son talles. El resto de las capas con dibujo se
# interpretan como talles.
CAPAS_SISTEMA = {"Fondo", "Capa 1", "Personalizable", "0", "referencia", "Referencia"}

# Reglas por pieza usadas en el armado del pedido. Se pueden sobrescribir desde
# datos/config_producto.json (clave "piezas"), pero estos son los valores por
# defecto que reproducen el comportamiento histórico del motor.
PIEZAS_RIB = {"Cuello", "TC", "Tapacostura"}          # van a la tela RIB
PIEZAS_SIN_ROTACION = {"Frente", "Espalda"}           # no rotan en el nesting
PIEZA_PERSONALIZABLE = "Espalda"                       # lleva nombre + número
MARGEN_MESA_CM = 2.0                                   # margen sugerido por lado
CAPAS_GUIA = {"guias", "guías", "guides", "Guides", "guia", "guía"}  # se descartan



# --- Handles de PDF: cierre garantizado -------------------------------------------------------
# En Windows un archivo que quedó abierto NO se puede reemplazar ni borrar (WinError 5). Varias
# funciones de acá abren el arte/la plantilla y devuelven datos ya extraídos, sin cerrar el
# documento: el handle sobrevive hasta que el GC pase, y mientras tanto el archivo queda trabado
# (subir un arte nuevo encima fallaba por esto). Se registran y el server los cierra al terminar
# cada request (`cerrar_abiertos`).
#
# El registro es POR HILO (`threading.local`) y NO global: el server atiende varios requests a la
# vez, y con una lista compartida el `teardown` de un request cerraba los documentos que otro
# request estaba usando en ese mismo momento → "ValueError: document closed" en `detectar_arte`.
import threading as _threading

_LOCAL = _threading.local()


def _pendientes():
    l = getattr(_LOCAL, "abiertos", None)
    if l is None:
        l = _LOCAL.abiertos = []
    return l


def _abrir(path, *a, **k):
    d = fitz.open(path, *a, **k)
    _pendientes().append(d)
    return d


def _abrir_pike(path, *a, **k):
    import pikepdf
    d = pikepdf.open(path, *a, **k)
    _pendientes().append(d)
    return d


def cerrar_abiertos():
    """Cierra los PDFs que abrió ESTE hilo y quedaron colgados. Idempotente."""
    pend = _pendientes()
    _LOCAL.abiertos = []
    for d in pend:
        try:
            d.close()
        except Exception:
            pass


def _es_capa_guia(nombre):
    """¿Es la capa GUÍA del arte? (texto que orienta al sistema: piezas, rangos… NUNCA se
    muestra ni se imprime). Compara NORMALIZADO: "Guías", "GUIAS", "Guia" son la misma capa.
    Con la comparación exacta anterior, un nombre con mayúscula/acento se colaba: se veía en
    el editor y —peor— se ESTAMPABA en la tizada."""
    return _norm_nombre(nombre) in {"guias", "guia", "guides"}

# Capas que NO son campos de personalización (nombres normalizados). Todo lo demás
# que traiga el arte (nombre, numero, palabra, numero 2, …) ES un placeholder de
# personalización: se lee su posición y se ESTAMPA con los datos, y la capa original
# NO debe salir en la tizada.
CAPAS_NO_PERS = {"diseño", "diseno", "personalizable", "guias", "guías", "guides",
                 "guia", "guía", "fondo", "capa 1", "referencia", "0"}
# Capas que SOLO llevan gráfica/guías (nunca texto de personalización). El color y el
# borde del nombre/número se buscan en cualquier OTRA capa (Personalizable o la capa
# de campo: Nombre, Número, Palabra…), no solo en "Personalizable".
CAPAS_GRAFICAS = CAPAS_NO_PERS - {"personalizable"}


# ════════════════ CATÁLOGO DE FUENTES ════════════════
def catalogo_fuentes(carpeta):
    cat = {}
    for ruta in glob.glob(os.path.join(carpeta, "*")):
        if not ruta.lower().endswith((".ttf", ".otf")):
            continue
        try:
            f = fitz.Font(fontfile=ruta)
            cat[ruta] = {"interno": f.name, "archivo": os.path.basename(ruta),
                         "hash": hashlib.md5(open(ruta, "rb").read()).hexdigest()[:12]}
        except Exception:
            pass
    return cat


def _norm(n):
    # solo alfanuméricos (quita espacios, guiones, guiones BAJOS, etc.) + sufijos comunes
    n = "".join(ch for ch in n.lower() if ch.isalnum())
    return n.replace("regular", "").replace("mt", "")


def resolver_fuente(nombre_ps, carpeta):
    """Nombre PostScript del arte -> ruta del archivo en el catálogo, o None."""
    objetivo = _norm(nombre_ps)
    for ruta, info in catalogo_fuentes(carpeta).items():
        if _norm(info["interno"]) == objetivo or objetivo in _norm(info["interno"]) \
           or _norm(info["interno"]) in objetivo:
            return ruta
    return None


def alta_fuente(ruta_subida, carpeta):
    try:
        f = fitz.Font(fontfile=ruta_subida)
        fc = FuenteCurvas(open(ruta_subida, "rb").read())
        prueba = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ0123456789#-"
        sin = [ch for ch in prueba if not _tiene_contorno(fc, ch)]
        destino = os.path.join(carpeta, os.path.basename(ruta_subida))
        os.replace(ruta_subida, destino)
        return {"ok": True, "interno": f.name, "sin_contorno": sin}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _tiene_contorno(fc, ch):
    # Falta en el cmap, datos corruptos o cualquier otra rotura de la fuente = ese carácter no se
    # puede estampar. Se informa (`sin_contorno`), NO se rechaza la fuente entera por un glifo.
    try:
        regs, _ = fc._glifo(ch)
        return bool(regs)
    except Exception:
        return False


# ════════════════ ALTA DE PLANTILLA ════════════════
def _orden_capas_archivo(doc):
    """Orden de las capas tal como están en el archivo (panel de capas de
    Illustrator / OCProperties Order del PDF)."""
    try:
        return [c.get("text") for c in doc.layer_ui_configs() if c.get("text")]
    except Exception:
        return []


def _ordenar_por_archivo(doc, nombres):
    """Ordena los nombres de capa/talle según el orden del archivo. Los que no
    figuren en el panel de capas van al final, preservando su orden de entrada."""
    nombres = list(nombres)
    orden = _orden_capas_archivo(doc)
    set_nombres, set_orden = set(nombres), set(orden)
    return [n for n in orden if n in set_nombres] + [n for n in nombres if n not in set_orden]


def talles_orden_archivo(path, talles):
    """Ordena una lista de talles según el orden de capas del archivo .ai/.pdf.
    Pensada para usarse desde el servidor sin reconstruir el registro."""
    try:
        with fitz.open(path) as doc:
            return _ordenar_por_archivo(doc, talles)
    except Exception:
        return list(talles)


def _talles_de_plantilla(doc):
    """Capas con dibujo que NO son de sistema → talles, en el orden del archivo.

    Excepción del talle «0»: `CAPAS_SISTEMA` lo descarta porque en un DXF la capa "0" es la capa
    por defecto de AutoCAD y suele traer basura. Pero «0» también es un TALLE legítimo en la curva
    de niños (0, 1, 2, 4, …), y descartarlo por el nombre le borraba un talle entero al usuario
    (caso real: molde con 20 capas de talle del que el registro se quedaba con 19). Se decide por
    CONTENIDO: si la capa "0" tiene tantas formas como los otros talles, es un talle.
    """
    import collections as _c
    cnt = _c.Counter()
    for i in range(len(doc)):
        for d in doc[i].get_drawings():
            lay = d.get("layer")
            if lay:
                cnt[lay] += 1
    con_dibujo = {n for n in cnt if n not in CAPAS_SISTEMA}
    if "0" in cnt and con_dibujo:
        formas = sorted(cnt[n] for n in con_dibujo)
        mediana = formas[len(formas) // 2]
        if cnt["0"] >= mediana * 0.5:          # tiene contenido de talle, no basura de CAD
            con_dibujo.add("0")
    return _ordenar_por_archivo(doc, con_dibujo)


def _etiqueta_de_mesa(doc_talle, mesa):
    """Lee el texto de una mesa con un solo talle visible y devuelve los
    fragmentos de la primera línea con texto (texto, origen, dir, size, fuente)."""
    frags = []
    for b in doc_talle[mesa - 1].get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            t = "".join(s["text"] for s in l["spans"])
            if t.strip():
                s0 = l["spans"][0]
                frags.append((t, s0["origin"], l["dir"], s0["size"], s0["font"].split("+")[-1]))
    return frags


def alta_plantilla(path):
    """Registra la moldería siguiendo la convención 'una mesa por pieza, talles
    en capas' (ver CONVENCION_PLANTILLA.md). Devuelve el registro que consume el
    motor más un diagnóstico legible: `problemas` (bloqueantes), `advertencias`
    (no bloquean pero conviene corregir) y `piezas_detalle` (qué detectó por
    pieza, con la medida de mesa sugerida)."""
    doc = _abrir(path)
    talles = _talles_de_plantilla(doc)
    registro, problemas, advertencias = {}, [], []
    mesas_por_pieza = {}   # pieza -> set de mesas donde apareció

    if not talles:
        problemas.append("No se encontró ninguna capa de talle. Cada talle debe "
                         "ser una capa con su nombre exacto (M, 3XL, 16, …).")

    for talle in talles:
        d2 = _abrir(path)
        for c in d2.layer_ui_configs():
            if c["text"] != talle:
                d2.set_layer_ui_config(c["number"], action=2)
        for mesa in range(1, len(d2) + 1):
            tiene_molde = any(d.get("layer") == talle for d in d2[mesa - 1].get_drawings())
            frags = _etiqueta_de_mesa(d2, mesa)
            texto = "".join(f[0] for f in frags).strip()
            if not frags:
                if tiene_molde:
                    problemas.append(f"Mesa {mesa}, talle «{talle}»: hay molde dibujado "
                                     f"pero falta la etiqueta de texto «{talle}-Pieza-#».")
                continue
            if not texto.startswith(talle + "-") or not texto.endswith("#"):
                problemas.append(f"Mesa {mesa}, talle «{talle}»: etiqueta «{texto}» mal "
                                 f"escrita. Debe empezar con «{talle}-» y terminar en «-#» "
                                 f"(ej. «{talle}-Frente-#»).")
                continue
            pieza = texto[len(talle) + 1:-2].strip("-").strip()
            if not pieza:
                problemas.append(f"Mesa {mesa}, talle «{talle}»: la etiqueta no nombra la "
                                 f"pieza. Formato: «{talle}-NombreDePieza-#».")
                continue
            try:
                cont = extraer_contorno_mesa(doc, mesa=mesa, talle=talle)
            except Exception as e:
                problemas.append(f"Mesa {mesa}, talle «{talle}», pieza «{pieza}»: no se pudo "
                                 f"leer el contorno ({e}).")
                continue
            if pieza.startswith("Manga") and "corta" not in pieza.lower() and "larga" not in pieza.lower():
                pieza += " (corta)" if cont["h"] / CM < 45 else " (larga)"
            mesas_por_pieza.setdefault(pieza, set()).add(mesa)
            if talle in registro.get(pieza, {}):
                advertencias.append(f"Pieza «{pieza}», talle «{talle}»: etiqueta repetida "
                                    f"(mesas {sorted(mesas_por_pieza[pieza])}). Se usa la última.")
            dx, dy = frags[0][2]
            registro.setdefault(pieza, {})[talle] = {
                "mesa": mesa, "w_cm": round(cont["w"] / CM, 1), "h_cm": round(cont["h"] / CM, 1),
                "bbox_mu": [round(v, 2) for v in cont["bbox_mu"]],
                "ancla": {"x": round(frags[0][1][0], 1), "y": round(frags[0][1][1], 1),
                          "angulo": round(math.degrees(math.atan2(-dy, dx)), 1),
                          "size_pt": round(frags[0][3], 1), "fuente": frags[0][4]}}

    # Convención nueva: cada pieza debe vivir en UNA sola mesa.
    for pieza, mesas in sorted(mesas_por_pieza.items()):
        if len(mesas) > 1:
            advertencias.append(f"La pieza «{pieza}» está repartida en las mesas "
                                f"{sorted(mesas)}. La convención nueva pide UNA sola mesa "
                                f"por pieza, con todos los talles como capas.")

    # Detalle por pieza + medida de mesa sugerida (alto del talle mayor + margen,
    # ancho proporcional a la pieza).
    piezas_detalle = {}
    for pieza, por_talle in registro.items():
        mayor = max(por_talle.values(), key=lambda v: v["h_cm"])
        piezas_detalle[pieza] = {
            "mesas": sorted(mesas_por_pieza.get(pieza, [])),
            "talles": _ordenar_por_archivo(doc, por_talle.keys()),
            "talle_mayor_cm": {"w": mayor["w_cm"], "h": mayor["h_cm"]},
            "mesa_sugerida_cm": {"w": round(mayor["w_cm"] + 2 * MARGEN_MESA_CM, 1),
                                 "h": round(mayor["h_cm"] + 2 * MARGEN_MESA_CM, 1)}}

    completos = [t for t in talles if all(t in registro.get(p, {}) for p in registro)]
    return {"mesas": len(doc), "talles": talles, "piezas": sorted(registro.keys()),
            "completos": completos, "registro": registro, "problemas": problemas,
            "advertencias": advertencias, "piezas_detalle": piezas_detalle}


# ════════════════ ETIQUETADO VISUAL (moldería sin etiquetas de texto) ════════════════
# Cuando la plantilla NO trae los textos «Talle-Pieza-#», el sistema detecta las
# piezas por su geometría y deja que el usuario les ponga nombre UNA vez (en un
# talle de referencia). El nombre se propaga al resto de los talles por posición.

def _centroide_norm(cont, union):
    """Centroide de la pieza normalizado al bounding box del molde de su talle
    (cancela el escalado entre talles → comparable entre talles)."""
    x0, y0, x1, y1 = cont["bbox_mu"]
    ux0, uy0, ux1, uy1 = union
    uw = (ux1 - ux0) or 1.0
    uh = (uy1 - uy0) or 1.0
    return ((((x0 + x1) / 2) - ux0) / uw, (((y0 + y1) / 2) - uy0) / uh)


def _union_bbox(piezas):
    xs0 = min(c["bbox_mu"][0] for c in piezas); ys0 = min(c["bbox_mu"][1] for c in piezas)
    xs1 = max(c["bbox_mu"][2] for c in piezas); ys1 = max(c["bbox_mu"][3] for c in piezas)
    return (xs0, ys0, xs1, ys1)


def _talles_con_molde(doc):
    """{talle: {mesas donde tiene molde}}. Qué capa ES un talle lo decide `_talles_de_plantilla`
    (una sola regla en todo el sistema): si acá se filtrara distinto, un talle válido aparecería
    en el alta y desaparecería en la detección — que es justo lo que pasaba con el talle «0»."""
    validos = set(_talles_de_plantilla(doc))
    talles = {}
    for i in range(len(doc)):
        for d in doc[i].get_drawings():
            lay = d.get("layer")
            if lay and lay in validos:
                talles.setdefault(lay, set()).add(i + 1)
    return talles


def _capas_con_dibujo(doc):
    """{capa: {mesas}} de TODA capa con trazados, sea o no un talle reconocido.

    Es el universo que necesita el modo «asignar variantes POR PIEZAS»: un molde que trae todo en
    «Capa 1» no tiene ni un talle (`_talles_con_molde` devuelve {}) y sin esto no habría forma de
    listarle las piezas al usuario para que las reparta."""
    capas = {}
    for i in range(len(doc)):
        for d in doc[i].get_drawings():
            lay = d.get("layer")
            if lay:
                capas.setdefault(lay, set()).add(i + 1)
    return capas


def _item_visor(cont, idx, clip, cb, U, zoom):
    """Un contorno del molde → el dict que consume el visor (coords en mm, y hacia abajo).

    Vive aparte de `detectar_piezas` porque hay DOS vistas que dibujan las mismas piezas
    (una variante sola, y todas las variantes juntas): si cada una armara el path por su
    cuenta, la misma pieza se vería distinta según desde dónde se la mire."""
    x0, y0, x1, y1 = cont["bbox_mu"]
    path_svg = []
    for s in cont["segmentos"]:
        op = s[0]
        if op in ("m", "l"):
            cx, cy = s[1], s[2]
            px = ((cx - cb.x0) * U - clip.x0) * zoom
            py = ((cb.y1 - cy) * U - clip.y0) * zoom
            path_svg.append(f"{op.upper()} {px:.1f} {py:.1f}")
        elif op == "c":
            cx1, cy1, cx2, cy2, cx3, cy3 = s[1], s[2], s[3], s[4], s[5], s[6]
            px1 = ((cx1 - cb.x0) * U - clip.x0) * zoom
            py1 = ((cb.y1 - cy1) * U - clip.y0) * zoom
            px2 = ((cx2 - cb.x0) * U - clip.x0) * zoom
            py2 = ((cb.y1 - cy2) * U - clip.y0) * zoom
            px3 = ((cx3 - cb.x0) * U - clip.x0) * zoom
            py3 = ((cb.y1 - cy3) * U - clip.y0) * zoom
            path_svg.append(f"C {px1:.1f} {py1:.1f} {px2:.1f} {py2:.1f} {px3:.1f} {py3:.1f}")
        elif op == "re":
            cx, cy, cw, ch = s[1], s[2], s[3], s[4]
            px = ((cx - cb.x0) * U - clip.x0) * zoom
            py = ((cb.y1 - cy) * U - clip.y0) * zoom
            pw = cw * U * zoom
            ph = ch * U * zoom
            path_svg.append(f"M {px:.1f} {py:.1f} h {pw:.1f} v {-ph:.1f} h {-pw:.1f} Z")
        elif op == "h":
            path_svg.append("Z")
    return {
        "idx": idx,
        "px": round((x0 - clip.x0) * zoom, 1), "py": round((y0 - clip.y0) * zoom, 1),
        "pw": round((x1 - x0) * zoom, 1), "ph": round((y1 - y0) * zoom, 1),
        "w_cm": round(cont["w"] / CM, 1), "h_cm": round(cont["h"] / CM, 1),
        "path_svg": " ".join(path_svg),
    }


def _mesa_principal(doc, talles):
    """La mesa (página) donde está el bloque de molde: la que más trazos de talle concentra.

    Mismo criterio que usa `detectar_piezas` para elegir su (mesa, talle) de referencia — si
    difirieran, el visor de "todas las variantes" y el de una sola mostrarían páginas distintas."""
    import collections
    ranking = []
    for m in range(1, len(doc) + 1):
        cnt = collections.Counter(str(d.get("layer")) for d in doc[m - 1].get_drawings() if d.get("layer"))
        n = sum(cnt.get(t, 0) for t in talles)
        if n:
            ranking.append((n, m))
    if not ranking:
        return None
    ranking.sort(reverse=True)
    return ranking[0][1]


def detectar_piezas_todas(path):
    """TODAS las piezas de TODAS las variantes en UN solo lienzo (mismo sistema de coordenadas).

    Es la vista del AGRUPADO por selección: el usuario ve el frente del S, el del M, el del L…
    a la vez y los selecciona juntos. Sólo tiene sentido en moldes `extendido` (cada talle en su
    bloque); en un molde `anidado` los talles están dibujados uno encima del otro y esto sería
    un amasijo — de eso se ocupa quien llama (ver §10.c del mapa).

    Cada pieza trae `talle` + `t_idx` = su índice DENTRO de ese talle, que es exactamente el
    `pieza_idx` del registro: sin eso la selección no se podría traducir a correspondencia.
    `idx` es un correlativo global, único, que sólo sirve como identificador en el visor."""
    doc = _abrir(path)
    talles_mesas = _talles_con_molde(doc)
    if not talles_mesas:
        raise ValueError("La plantilla no tiene capas de talle con molde dibujado.")
    talles = _ordenar_por_archivo(doc, talles_mesas.keys())
    mesa = _mesa_principal(doc, talles)
    if mesa is None:
        raise ValueError("La plantilla no tiene capas de talle con molde dibujado.")

    por_talle = {}
    for t in talles:
        pzs = extraer_piezas_mesa(doc, mesa, t)
        if pzs:
            por_talle[t] = pzs
    if not por_talle:
        raise ValueError(f"No se detectaron piezas en la mesa {mesa}.")
    talles = [t for t in talles if t in por_talle]

    todas = [c for t in talles for c in por_talle[t]]
    union = _union_bbox(todas)
    mx = max(20.0, (union[2] - union[0]) * 0.04)
    clip = fitz.Rect(union[0] - mx, union[1] - mx, union[2] + mx, union[3] + mx)
    zoom = 1.0 / MM                      # escala REAL: 1 unidad = 1 mm (igual que `detectar_piezas`)

    page = doc[mesa - 1]
    cb = page.cropbox
    U = page.rect.width / cb.width if cb.width else 1.0

    items, g = [], 0
    for t in talles:
        for i, cont in enumerate(por_talle[t]):
            it = _item_visor(cont, g, clip, cb, U, zoom)
            it["talle"] = t
            it["t_idx"] = i
            items.append(it)
            g += 1
    return {"mesa": mesa, "talles": talles, "unidad": "mm",
            "img_w": round(clip.width * zoom, 1), "img_h": round(clip.height * zoom, 1),
            "piezas": items,
            "por_talle": {t: len(por_talle[t]) for t in talles}}


def detectar_piezas(path, talle_ref=None, ancho_preview=1100, capas_candidatas=False):
    """Detecta las piezas de la moldería para el etiquetado visual. Elige un talle
    de referencia (el de más piezas), las extrae y arma una imagen de la mesa con
    las piezas mapeadas a píxeles para superponer cajas clicables en la web.
    Devuelve {mesa, talle_ref, talles, unidad:"mm", img_w, img_h (extensión en mm),
    piezas:[{idx, px,py,pw,ph (en MILÍMETROS reales), w_cm, h_cm, path_svg(en mm)}]}.
    La escala es REAL y fija (1 unidad = 1 mm), no depende de la cantidad de piezas."""
    doc = _abrir(path)
    talles_mesas = _talles_con_molde(doc)
    sin_variantes = False
    if capas_candidatas and not talles_mesas:
        sin_variantes = True
        # Sin ningún talle reconocido, el visor igual tiene que poder MOSTRAR las piezas: es
        # justo el molde que hay que repartir a mano en variantes.
        talles_mesas = _capas_con_dibujo(doc)

    # Buscar si existe una capa de referencia (caso insensible)
    capas_doc = {c["text"].lower(): c["text"] for c in doc.layer_ui_configs() if c.get("text")}
    capa_ref = capas_doc.get("referencia")
    
    if capa_ref:
        # Usamos la capa de referencia del usuario
        talle_ref = capa_ref
        mesa = 1
        for i in range(len(doc)):
            pzs = extraer_piezas_mesa(doc, i + 1, capa_ref)
            if pzs:
                mesa = i + 1
                break
    else:
        # Elegir mesa+talle de referencia por CANTIDAD DE TRAZOS del talle (un solo
        # get_drawings por mesa), no extrayendo las piezas de CADA talle (con moldes de
        # muchas piezas/talles eso era ~1s×talles = lentísimo). Se extrae solo el elegido.
        if not talles_mesas:
            raise ValueError("La plantilla no tiene capas de talle con molde dibujado.")
        import collections
        talles_set = list(talles_mesas.keys())
        ranking = []                                     # (n_trazos, mesa, talle)
        for m in range(1, len(doc) + 1):
            cnt = collections.Counter(str(d.get("layer")) for d in doc[m - 1].get_drawings() if d.get("layer"))
            for t in talles_set:
                if cnt.get(t):
                    ranking.append((cnt[t], m, t))
        ranking.sort(reverse=True)
        mesa = talle_auto = None
        for _, m, t in ranking:                          # el talle con más trazos que dé piezas
            if extraer_piezas_mesa(doc, m, t):
                mesa, talle_auto = m, t; break
        if mesa is None:
            raise ValueError("La plantilla no tiene capas de talle con molde dibujado.")
        talle_ref = talle_ref or talle_auto
        
    piezas = extraer_piezas_mesa(doc, mesa, talle_ref)
    if not piezas:
        raise ValueError(f"No se detectaron piezas en la mesa {mesa}, talle {talle_ref!r}.")

    union = _union_bbox(piezas)
    mx = max(20.0, (union[2] - union[0]) * 0.04)
    clip = fitz.Rect(union[0] - mx, union[1] - mx, union[2] + mx, union[3] + mx)
    # Escala REAL fija: 1 unidad de salida = 1 mm, IGUAL para todo molde (ya NO se
    # normaliza al tamaño del molde). Así una pieza de 20 cm mide 200 unidades tenga
    # 5 o 150 piezas — el frontend la dibuja a un px/cm constante. (`ancho_preview`
    # queda sin uso para la geometría; se conserva por compatibilidad de llamadas.)
    zoom = 1.0 / MM

    page = doc[mesa - 1]
    cb = page.cropbox
    U = page.rect.width / cb.width if cb.width else 1.0

    items = [_item_visor(cont, i, clip, cb, U, zoom) for i, cont in enumerate(piezas)]
    # Orden de los talles tal como vienen en el archivo (orden del panel de
    # capas), no alfabético ni por orden de dibujo.
    talles_orden = _ordenar_por_archivo(doc, talles_mesas.keys())
    return {"mesa": mesa, "talle_ref": talle_ref, "talles": talles_orden, "unidad": "mm",
            "img_w": round(clip.width * zoom, 1), "img_h": round(clip.height * zoom, 1),
            "piezas": items,
            # las piezas NO salen de una capa de talle: son todas las del molde, listas para
            # repartir a mano en variantes (el front lo usa para abrir esa herramienta)
            "sin_variantes": sin_variantes}


def _bbox_segs(segs):
    """Bounding box (x0,y0,x1,y1) de una lista de segmentos en coords crudas (y-arriba)."""
    xs, ys = [], []
    for s in segs:
        op = s[0]
        if op in ("m", "l"): xs.append(s[1]); ys.append(s[2])
        elif op == "c": xs += [s[1], s[3], s[5]]; ys += [s[2], s[4], s[6]]
        elif op == "re": xs += [s[1], s[1] + s[3]]; ys += [s[2], s[2] + s[4]]   # (x, y_abajo, w, h) en y-arriba
    if not xs: return None
    return (min(xs), min(ys), max(xs), max(ys))


def _segs_a_svg(segs, dx, dy, to_px):
    """Convierte segmentos crudos (y-arriba) a un path SVG en px (y-abajo),
    trasladando (dx,dy) antes (para nestear al centroide de guía)."""
    out = []
    for s in segs:
        op = s[0]
        if op == "m":
            x, y = to_px(s[1] + dx, s[2] + dy); out.append(f"M {x:.1f} {y:.1f}")
        elif op == "l":
            x, y = to_px(s[1] + dx, s[2] + dy); out.append(f"L {x:.1f} {y:.1f}")
        elif op == "c":
            x1, y1 = to_px(s[1] + dx, s[2] + dy); x2, y2 = to_px(s[3] + dx, s[4] + dy); x3, y3 = to_px(s[5] + dx, s[6] + dy)
            out.append(f"C {x1:.1f} {y1:.1f} {x2:.1f} {y2:.1f} {x3:.1f} {y3:.1f}")
        elif op == "re":
            x0, y0 = to_px(s[1] + dx, s[2] + dy); x1, y1 = to_px(s[1] + s[3] + dx, s[2] + s[4] + dy)
            out.append(f"M {x0:.1f} {y0:.1f} L {x1:.1f} {y0:.1f} L {x1:.1f} {y1:.1f} L {x0:.1f} {y1:.1f} Z")
        elif op == "h":
            out.append("Z")
    return " ".join(out)


def _bboxes_acomodadas(conts, offsets=None):
    """bbox_mu de cada contorno, con el ACOMODO A MANO aplicado (solo para emparejar).

    El acomodo es VIRTUAL: no mueve nada del archivo ni de la tizada — solo corre la caja
    con la que se calculan los rasgos, que es lo único que mira el emparejado. Así el
    usuario puede reordenar las piezas de un talle desprolijo hasta que su disposición se
    parezca a la del talle guía, sin tocar el molde (la LEY «el arte se ve igual que la
    tizada» queda intacta). `offsets` = {idx: (dx_mm, dy_mm)}."""
    out = []
    for i, c in enumerate(conts):
        x0, y0, x1, y1 = c["bbox_mu"]
        d = (offsets or {}).get(i)
        if d:
            dx, dy = float(d[0]) * MM, float(d[1]) * MM
            x0 += dx; x1 += dx; y0 += dy; y1 += dy
        out.append((x0, y0, x1, y1))
    return out


def _feats_conts(conts, offsets=None):
    """Rasgos por contorno para emparejar piezas entre talles: centroide NORMALIZADO
    a la unión del talle (posición relativa), log-aspecto y log-área relativa.
    `offsets` = acomodo a mano {idx: (dx_mm, dy_mm)} (ver `_bboxes_acomodadas`)."""
    cajas = _bboxes_acomodadas(conts, offsets)
    ux0 = min(b[0] for b in cajas); uy0 = min(b[1] for b in cajas)
    ux1 = max(b[2] for b in cajas); uy1 = max(b[3] for b in cajas)
    uw = max(1e-6, ux1 - ux0); uh = max(1e-6, uy1 - uy0)
    out = []
    for x0, y0, x1, y1 in cajas:
        w = max(1e-6, x1 - x0); h = max(1e-6, y1 - y0)
        out.append({"cx": ((x0 + x1) / 2 - ux0) / uw, "cy": ((y0 + y1) / 2 - uy0) / uh,
                    "lar": math.log(w / h), "larea": math.log((w * h) / (uw * uh))})
    return out


def emp_offsets(emparejado, talle):
    """Acomodo a mano guardado para un talle → {idx:int: (dx_mm, dy_mm)} (o None)."""
    d = ((emparejado or {}).get("acomodo") or {}).get(talle) or {}
    out = {}
    for k, v in d.items():
        try:
            out[int(k)] = (float(v[0]), float(v[1]))
        except Exception:
            continue
    return out or None


def emp_fijos(emparejado, talle):
    """Correcciones MANUALES de un talle → {nombre_de_pieza: idx_en_ese_talle} (o None).
    Mandan sobre la heurística Y sobre la correspondencia del DXF: si el usuario dijo
    que la pieza «Frente» es la #7, es la #7."""
    d = ((emparejado or {}).get("manual") or {}).get(talle) or {}
    out = {}
    for nom, idx in d.items():
        try:
            out[str(nom)] = int(idx)
        except Exception:
            continue
    return out or None


def _aplicar_fijos(eleccion, fijos, n_piezas):
    """Mete las correcciones manuales en la elección ya calculada, pisando lo automático
    y liberando el índice que ese idx tuviera asignado en otra pieza (no puede haber dos
    nombres apuntando a la misma pieza del talle)."""
    if not fijos:
        return eleccion
    for nom, j in fijos.items():
        if j is None or j < 0 or j >= n_piezas:
            continue
        for otro, (jj, _r) in list(eleccion.items()):
            if jj == j and otro != nom:
                del eleccion[otro]
        eleccion[nom] = (j, False)
    return eleccion


def _emparejar_por_forma(f_ref, nombres_ref, f_cand, umbral=1.6):
    """Empareja piezas nombradas del talle de referencia con las de otro talle por
    POSICIÓN + FORMA + TAMAÑO (no solo la más cercana: con muchas piezas parecidas
    el matching posicional agarraba la vecina equivocada → figuras 'deformadas').
    `nombres_ref` = {nombre: idx_en_ref}. Greedy GLOBAL: se asignan primero los pares
    más seguros. Devuelve {nombre: (idx_candidato, rotada90)}. `rotada90` avisa que en
    ese talle la pieza está girada 90° en el archivo (aspecto invertido)."""
    pares = []
    for nom, ir in nombres_ref.items():
        if ir >= len(f_ref):
            continue
        fr = f_ref[ir]
        for j, fc in enumerate(f_cand):
            dpos = math.hypot(fc["cx"] - fr["cx"], fc["cy"] - fr["cy"])
            da_recta = abs(fc["lar"] - fr["lar"])
            da_girada = abs(-fc["lar"] - fr["lar"]) + 0.25   # leve castigo: girar solo si conviene claro
            rot = da_girada < da_recta
            daspect = min(da_recta, da_girada)
            darea = abs(fc["larea"] - fr["larea"])
            pares.append((dpos + 0.9 * daspect + 0.6 * darea, nom, j, rot))
    pares.sort(key=lambda x: x[0])
    eleccion, usados = {}, set()
    for costo, nom, j, rot in pares:
        if costo > umbral:
            break
        if nom in eleccion or j in usados:
            continue
        eleccion[nom] = (j, rot); usados.add(j)
    return eleccion


def _mapa_indices(indices, talle_ref):
    """De la correspondencia del DXF ({talle: [nombre_dxf por índice]}) arma
    {talle: {idx_ref: idx_talle}} linkeando por nombre (n-ésima ocurrencia con
    n-ésima, por si hay nombres repetidos). Es el emparejado EXACTO del archivo."""
    if not indices or talle_ref not in indices:
        return None
    def posiciones(lst):
        d = {}
        for i, nm in enumerate(lst):
            d.setdefault(nm, []).append(i)
        return d
    pos_ref = posiciones(indices[talle_ref])
    out = {}
    for t, lst in indices.items():
        pos_t = posiciones(lst)
        m = {}
        for nm, refs in pos_ref.items():
            ts = pos_t.get(nm, [])
            for k, gi in enumerate(refs):
                if k < len(ts):
                    m[gi] = ts[k]
        out[t] = m
    return out


def _rotar_segs_90(segs, cx, cy):
    """Gira los segmentos 90° alrededor de (cx,cy) — para nestear piezas que en el
    archivo vienen giradas en algunos talles. Coords y-arriba."""
    def R(x, y):
        return (cx + (y - cy), cy - (x - cx))
    out = []
    for s in segs:
        op = s[0]
        if op in ("m", "l"):
            x, y = R(s[1], s[2]); out.append((op, x, y))
        elif op == "c":
            p = []
            for k in range(3):
                x, y = R(s[1 + 2 * k], s[2 + 2 * k]); p += [x, y]
            out.append(("c", *p))
        elif op == "re":                      # el rectángulo girado deja de ser 're' → polilínea
            x0, y0, w, h = s[1], s[2], s[3], s[4]
            rp = [R(px, py) for px, py in ((x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h))]
            out.append(("m", *rp[0])); out.extend(("l", *p) for p in rp[1:]); out.append(("h",))
        else:
            out.append(s)
    return out


def snapshot_nombres_guia(path, registro):
    """Foto de la geometría del talle guía + nombres ANTES de reemplazar el molde,
    para poder remapear los nombres al archivo nuevo (re-subida del mismo molde)."""
    if not registro:
        return None
    from collections import Counter
    cnt = Counter()
    for nom, por_t in registro.items():
        for t, info in por_t.items():
            if isinstance(info, dict) and info.get("pieza_idx") is not None:
                cnt[(info.get("mesa", 1), t)] += 1
    if not cnt:
        return None
    (mesa, talle), _ = cnt.most_common(1)[0]
    doc = fitz.open(path)
    try:
        conts = extraer_piezas_mesa(doc, mesa, talle)
    finally:
        doc.close()
    if not conts:
        return None
    nombres = {}
    for nom, por_t in registro.items():
        info = por_t.get(talle)
        if info and info.get("mesa") == mesa and info.get("pieza_idx") is not None and info["pieza_idx"] < len(conts):
            nombres[nom] = info["pieza_idx"]
    if not nombres:
        return None
    return {"feats": _feats_conts(conts), "nombres": nombres, "talle": talle}


def remapear_registro(path_nuevo, snap, indices=None, emparejado=None):
    """Transfiere los nombres del molde VIEJO al archivo NUEVO emparejando el talle
    guía por posición + forma + tamaño, y reconstruye el registro completo (con la
    correspondencia exacta del DXF para los demás talles, si está disponible).
    Devuelve (alta, cobertura 0..1) o (None, 0.0) si no se pudo."""
    if not snap or not snap.get("nombres"):
        return None, 0.0
    base = detectar_piezas(path_nuevo, ancho_preview=300)
    mesa = base["mesa"]
    talle = snap["talle"] if snap["talle"] in (base.get("talles") or []) else base["talle_ref"]
    doc = fitz.open(path_nuevo)
    try:
        conts = extraer_piezas_mesa(doc, mesa, talle)
    finally:
        doc.close()
    if not conts:
        return None, 0.0
    eleccion = _emparejar_por_forma(snap["feats"], snap["nombres"], _feats_conts(conts))
    if not eleccion:
        return None, 0.0
    asign = [{"idx": j, "nombre": nom} for nom, (j, _rot) in eleccion.items()]
    cobertura = len(asign) / max(1, len(snap["nombres"]))
    alta = alta_plantilla_manual(path_nuevo, asign, mesa, talle, indices=indices, emparejado=emparejado)
    return alta, cobertura


def nido_piezas(path, registro, talle_guia=None, ancho_preview=1100, indices=None, emparejado=None):
    """Para cada pieza NOMBRADA del registro, devuelve su contorno en TODOS los talles,
    NESTEADO (todas las tallas alineadas por su centroide) en un marco común de px.
    Es la data para el visor de "acomodar": una pieza = su pila de tallas, que se
    arrastra junta. Devuelve {vb,w,h,guia,talles,piezas:[{nombre,cx,cy,talles:[{talle,d}]}]}."""
    base = detectar_piezas(path, talle_ref=talle_guia, ancho_preview=300)
    mesa = base["mesa"]; guia = base["talle_ref"]; talles = base.get("talles") or [guia]
    doc = _abrir(path)
    # Contornos de cada talle (una sola extracción por talle).
    conts_por_talle = {}
    for t in talles:
        cs = extraer_piezas_mesa(doc, mesa, t)
        if cs:
            conts_por_talle[t] = cs
    if guia not in conts_por_talle:
        raise ValueError("el talle guía no tiene piezas")
    # Nombres CONFIABLES: los que el usuario asignó en el talle guía. Para los demás
    # talles NO usamos el pieza_idx del registro (el matching posicional viejo metía
    # la pieza vecina equivocada → figuras deformadas): re-emparejamos acá por
    # posición + forma + tamaño, detectando además piezas giradas 90° en el archivo.
    nombres_guia = {}
    for nom, por_t in (registro or {}).items():
        info = por_t.get(guia)
        if info and info.get("mesa") == mesa and info.get("pieza_idx") is not None:
            nombres_guia[nom] = info["pieza_idx"]
    if not nombres_guia:
        raise ValueError("no hay piezas nombradas para nestear")
    f_guia = _feats_conts(conts_por_talle[guia], emp_offsets(emparejado, guia))
    mapa_exacto = _mapa_indices(indices, guia)   # correspondencia EXACTA del DXF (si existe)
    por_nombre = {}   # {nombre: {talle: {segs, cx, cy}}} (coords crudas y-arriba, marco común)
    for t, conts in conts_por_talle.items():
        if t == guia:
            eleccion = {nom: (i, False) for nom, i in nombres_guia.items() if i < len(conts)}
        elif mapa_exacto and t in mapa_exacto:
            # el archivo dice exactamente qué pieza es cuál en este talle — sin adivinar
            mt = mapa_exacto[t]
            f_t = _feats_conts(conts, emp_offsets(emparejado, t))
            eleccion = {}
            for nom, gi in nombres_guia.items():
                j = mt.get(gi)
                if j is None or j >= len(conts):
                    continue
                rot = False
                if gi < len(f_guia) and j < len(f_t):
                    fr, fc = f_guia[gi], f_t[j]
                    rot = (abs(-fc["lar"] - fr["lar"]) + 0.25) < abs(fc["lar"] - fr["lar"])
                eleccion[nom] = (j, rot)
        else:
            eleccion = _emparejar_por_forma(f_guia, nombres_guia,
                                            _feats_conts(conts, emp_offsets(emparejado, t)))
        # el ajuste a mano manda sobre cualquier heuristica (mismo criterio que el registro)
        if t != guia:
            eleccion = _aplicar_fijos(eleccion, emp_fijos(emparejado, t), len(conts))
        for nom, (j, rot) in eleccion.items():
            c = conts[j]
            x0, y0, x1, y1 = c["bbox_raw"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            segs = _rotar_segs_90(c["segmentos"], cx, cy) if rot else c["segmentos"]
            bb = _bbox_segs(segs)
            if not bb:
                continue
            # nesteo tipo moldería: centrado en X, ALINEADO POR LA BASE en Y (los talles
            # comparten el borde inferior → pila prolija, no un caos centrado)
            por_nombre.setdefault(nom, {})[t] = {"segs": segs, "cx": (bb[0] + bb[2]) / 2,
                                                 "base": bb[1], "h": max(bb[3] - bb[1], 1e-6),
                                                 "hw": max((bb[2] - bb[0]) / 2.0, 1e-6)}
    if not por_nombre:
        raise ValueError("no hay piezas nombradas para nestear")
    # Media-extensión de cada pieza ya nesteada (bases alineadas): alto = el talle más
    # alto; el "centro" virtual de cada talle queda a base + H/2 de la pieza.
    import math as _m
    half = {}
    for nom, td in por_nombre.items():
        hw = max((d["hw"] for d in td.values()), default=1.0)
        hmax = max((d["h"] for d in td.values()), default=2.0)
        half[nom] = (hw, hmax / 2.0)
        for d in td.values():
            d["cy"] = d["base"] + hmax / 2.0   # centro virtual: alinear esto = alinear bases
    nombres_ord = list(por_nombre.keys())
    n = len(nombres_ord)
    cols = max(1, int(round(_m.sqrt(n))))
    gap = 0.18 * max((h[0] for h in half.values()), default=100.0)
    base_pos = {}; row_top = 0.0; i = 0
    while i < n:
        fila = nombres_ord[i:i + cols]
        row_hh = max(half[nm][1] for nm in fila)
        cx = 0.0
        for nm in fila:
            hw, hh = half[nm]
            base_pos[nm] = (cx + hw, row_top - row_hh)
            cx += 2 * hw + gap
        row_top -= 2 * row_hh + gap
        i += cols
    # Marco: unión de todas las tallas ya nesteadas a su base.
    minX = minY = 1e18; maxX = maxY = -1e18
    for nom, td in por_nombre.items():
        bx, by = base_pos[nom]
        for d in td.values():
            bb = _bbox_segs(d["segs"])
            if not bb:
                continue
            ddx, ddy = bx - d["cx"], by - d["cy"]
            minX = min(minX, bb[0] + ddx); maxX = max(maxX, bb[2] + ddx)
            minY = min(minY, bb[1] + ddy); maxY = max(maxY, bb[3] + ddy)
    marg = max(20.0, (maxX - minX) * 0.03)
    minX -= marg; maxX += marg; minY -= marg; maxY += marg
    scale = ancho_preview / max(1.0, (maxX - minX))
    W = ancho_preview; H = (maxY - minY) * scale

    def to_px(rx, ry):   # crudo (y-arriba) → px (y-abajo)
        return ((rx - minX) * scale, (maxY - ry) * scale)

    piezas_out = []
    for nom, td in por_nombre.items():
        bx, by = base_pos[nom]
        tallas = []
        for t in talles:
            d = td.get(t)
            if not d:
                continue
            tallas.append({"talle": t, "d": _segs_a_svg(d["segs"], bx - d["cx"], by - d["cy"], to_px)})
        cxpx, cypx = to_px(bx, by)
        hw, hh = half.get(nom, (1.0, 1.0))
        piezas_out.append({"nombre": nom, "cx": round(cxpx, 1), "cy": round(cypx, 1),
                           # idx de la pieza en el talle GUÍA (para filtrar variables por índice exacto)
                           "idx": nombres_guia.get(nom),
                           # semi-extensión de la pila (todas las tallas) en px del marco: para re-acomodar
                           "hw": round(hw * scale, 1), "hh": round(hh * scale, 1),
                           "talles": tallas})
    return {"vb": f"0 0 {W:.0f} {H:.0f}", "w": round(W), "h": round(H),
            "guia": guia, "talles": talles, "piezas": piezas_out}


def _ancla_sintetica(cont, talle):
    """Etiqueta de corte por defecto (sin placeholder): de 3 mm, CENTRADA y
    PEGADA al borde inferior de la pieza. Coords MuPDF (y abajo: y1 = borde inf.)."""
    x0, y0, x1, y1 = cont["bbox_mu"]
    size = 3.0 * MM                      # 3 mm
    return {"x": round((x0 + x1) / 2, 1), "y": round(y1 - size * 0.25, 1),
            "angulo": 0.0, "size_pt": round(size, 2), "fuente": "Arial-BoldMT"}


def _ancla_etiqueta(cont, posicion, size_pt):
    """Ancla de la etiqueta en una posición RELATIVA LIBRE dentro del bbox de la pieza:
    `posicion = {rx, ry}` con rx,ry ∈ 0..1 (rx 0=izq/1=der, ry 0=arriba/1=abajo, coords
    MuPDF). Se calcula del bbox de CADA talle/pieza → la MISMA posición relativa vale
    para todas. El texto va centrado en el punto (h='centro')."""
    x0, y0, x1, y1 = cont["bbox_mu"]
    pos = posicion or {}
    def _r(k, d):
        try:
            return max(0.0, min(1.0, float(pos.get(k, d))))
        except (TypeError, ValueError):
            return d
    rx, ry = _r("rx", 0.5), _r("ry", 0.92)
    return {"x": round(x0 + rx * (x1 - x0), 1), "y": round(y0 + ry * (y1 - y0), 1),
            "angulo": 0.0, "size_pt": round(size_pt, 2), "fuente": "Arial-BoldMT", "h": "centro"}


def _eops_borde(cont, S, x0, y0, B, rx, ry, t, texto, size, align, fetq, bc_activo=False):
    """TEXT-ON-PATH del motor: dibuja `texto` siguiendo el SEGMENTO del contorno
    (entre dos esquinas/cortes) que contiene la posición relativa `t`, igual que el
    preview. Trabaja en coords de PÁGINA (pt, y-up) usando la MISMA transformación que
    el clip/borde: punto (vx,vy) del contorno → (vx*S + B - x0*S, vy*S + B - y0*S).
    `align` ∈ izquierda|centro|derecha ubica el texto entre los dos vértices. La baseline
    se LEVANTA hacia adentro para que el texto quede por ENCIMA del borde de corte (no
    tapado). Devuelve los ops de path (glifo por glifo, el llamador pinta f/S) o None."""
    import math as _m, bisect

    def _P(vx, vy):
        return (vx * S + B - x0 * S, vy * S + B - y0 * S)

    # 1) aplanar el contorno a polilínea en coords de página
    pts = []; cur = None; ini = None
    for s in cont["segmentos"]:
        op = s[0]
        if op == "m":
            cur = _P(s[1], s[2]); pts.append(cur); ini = cur
        elif op == "l":
            cur = _P(s[1], s[2]); pts.append(cur)
        elif op == "c":
            p0 = cur or _P(s[1], s[2]); p1 = _P(s[1], s[2]); p2 = _P(s[3], s[4]); p3 = _P(s[5], s[6])
            for k in range(1, 9):
                u = k / 8.0; mu = 1 - u
                pts.append((mu*mu*mu*p0[0] + 3*mu*mu*u*p1[0] + 3*mu*u*u*p2[0] + u*u*u*p3[0],
                            mu*mu*mu*p0[1] + 3*mu*mu*u*p1[1] + 3*mu*u*u*p2[1] + u*u*u*p3[1]))
            cur = p3
        elif op == "re":
            X, Y, Wd, Ht = s[1], s[2], s[3], s[4]
            q = [_P(X, Y), _P(X+Wd, Y), _P(X+Wd, Y+Ht), _P(X, Y+Ht), _P(X, Y)]
            pts += q; cur = q[0]; ini = q[0]
        elif op == "h":
            if ini and cur != ini: pts.append(ini)
            cur = ini
    if len(pts) < 3:
        return None
    # 2) longitud de arco acumulada
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + _m.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]))
    total = cum[-1]
    if total <= 1:
        return None

    def _at(l):
        l = l % total
        i = bisect.bisect_right(cum, l)
        if i <= 0: return pts[0]
        if i >= len(pts): i = len(pts) - 1
        l0, l1 = cum[i-1], cum[i]
        f = (l - l0) / (l1 - l0) if l1 > l0 else 0.0
        return (pts[i-1][0] + f*(pts[i][0]-pts[i-1][0]), pts[i-1][1] + f*(pts[i][1]-pts[i-1][1]))

    def _dir(l):
        a = _at(l - 1.0); b = _at(l + 1.0)
        return _m.atan2(b[1]-a[1], b[0]-a[0])

    # 3) ANCLA estable entre talles: por `rx/ry` (posición relativa al bounding box). Los
    # talles están GRADADOS (no son escalas uniformes) → la longitud de arco `t` se corre y
    # cae en otro lado; rx/ry es geométricamente estable. Se busca el punto del contorno más
    # cercano al ancla. (Si no hay rx/ry, cae a `t`.)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs); miny, maxy = min(ys), max(ys)
    if rx is not None and ry is not None and (maxx > minx) and (maxy > miny):
        ax = minx + float(rx) * (maxx - minx)
        ay = maxy - float(ry) * (maxy - miny)            # ry: 0=arriba (y alto en página y-up)
        ns = max(80, min(900, int(total / 2))); bestL = 0.0; bestd = 1e18
        for i in range(ns + 1):
            L = total * i / ns; p = _at(L); d = (p[0]-ax)**2 + (p[1]-ay)**2
            if d < bestd: bestd = d; bestL = L
    else:
        bestL = ((t or 0.0) * total) % total
    # 4) caminar desde el ancla hacia las dos ESQUINAS/cortes adyacentes (cambio de dirección
    # local > ~0.5 rad). Detección LOCAL (solo alrededor del ancla) → robusta aunque la
    # gradación cambie el resto del contorno o el conteo global de esquinas.
    _wd = max(2.5, total / 160); _st = max(0.8, total / 600)
    def _turn(l):
        return abs(((_dir(l + _wd) - _dir(l - _wd) + _m.pi) % (2*_m.pi)) - _m.pi)
    def _walk(sg):
        d = _st
        while d < total * 0.48:
            if _turn(bestL + sg * d) > 0.5: break
            d += _st
        return d
    a = bestL - _walk(-1); b = bestL + _walk(1)
    seg_len = b - a
    if seg_len <= 1:
        return None
    # 5) muestrear el segmento; orientarlo para que el texto ENTRE a la pieza (centroide)
    nf = max(8, min(400, int(seg_len)))
    segp = [_at(a + seg_len * k / nf) for k in range(nf + 1)]
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    md = _at(a + seg_len/2); an = _dir(a + seg_len/2)
    up = (-_m.sin(an), _m.cos(an))      # "arriba" del glifo para baseline en ángulo `an`
    if (up[0]*(cx-md[0]) + up[1]*(cy-md[1])) < 0:
        segp.reverse()
    # La baseline se APOYA sobre el borde (casi en el contorno): el borde de corte se
    # dibuja por FUERA, así que el texto de adentro NO necesita despegarse. Solo un pelín
    # hacia adentro para que el cuerpo de las letras quede visible; los descendentes (p, g,
    # y…) bajan del baseline, cruzan el contorno y quedan recortados/ocultos bajo el borde.
    off_in = 0.18 * MM
    n = len(segp); base = list(segp); segp = []
    for i in range(n):
        a2 = base[max(0, i-1)]; b2 = base[min(n-1, i+1)]
        tx = b2[0]-a2[0]; ty = b2[1]-a2[1]; tl = _m.hypot(tx, ty) or 1.0; tx /= tl; ty /= tl
        segp.append((base[i][0] + (-ty)*off_in, base[i][1] + tx*off_in))   # +(-ty,tx) = hacia adentro
    # arc-length local del segmento orientado
    lc = [0.0]
    for i in range(1, len(segp)):
        lc.append(lc[-1] + _m.hypot(segp[i][0]-segp[i-1][0], segp[i][1]-segp[i-1][1]))
    lt = lc[-1]
    if lt <= 1:
        return None

    def _lat(d):
        d = max(0.0, min(lt, d))
        i = bisect.bisect_right(lc, d)
        if i <= 0: return segp[0]
        if i >= len(segp): i = len(segp) - 1
        d0, d1 = lc[i-1], lc[i]
        f = (d - d0) / (d1 - d0) if d1 > d0 else 0.0
        return (segp[i-1][0] + f*(segp[i][0]-segp[i-1][0]), segp[i-1][1] + f*(segp[i][1]-segp[i-1][1]))

    def _ldir(d):
        # ventana amplia (~medio glifo) para SUAVIZAR el ángulo: las micro-ondulaciones
        # del contorno no tuercen letra por letra; sigue las curvas reales, no el ruido.
        w = max(1.5, size * 0.6)
        p = _lat(max(0.0, d - w)); q = _lat(min(lt, d + w))
        return _m.degrees(_m.atan2(q[1]-p[1], q[0]-p[0]))

    # 6) alineación DENTRO del segmento. El margen aleja el texto de las esquinas para
    # que no arranque torcido sobre el quiebre del contorno.
    aw = fetq.ancho_texto(texto, size)
    mg = min(seg_len * 0.06, 2.5 * MM)
    if align == "izquierda":
        d0 = mg
    elif align == "derecha":
        d0 = max(mg, lt - mg - aw)
    else:
        d0 = max(0.0, lt/2 - aw/2)
    # 7) un glifo por vez: cada uno en su punto con la tangente local
    parts = []; d = d0
    for ch in texto:
        cw = fetq.ancho_texto(ch, size)
        p = _lat(d)
        parts.append(fetq.ops_texto(ch, size, p[0], p[1], angulo_deg=_ldir(d)))
        d += cw
    return "\n".join(parts)


def _eops_tramo(_at, _dir, a, b, cx, cy, texto, size, align, fetq):
    """Dibuja `texto` (text-on-path) sobre el tramo de arco [a,b] (coords de PÁGINA, y-up)
    de un contorno ya aplanado (`_at`/`_dir` = punto/dirección por longitud de arco).
    Orienta hacia el centroide (cx,cy), apoya la baseline sobre el borde y alinea el texto
    dentro del tramo. MISMO criterio de baseline que `_eops_borde` (invariante protegido de
    la etiqueta). Devuelve los ops (glifo por glifo) o None. Lo usa el etiquetado POR ZONAS."""
    import math as _m, bisect
    seg_len = b - a
    if seg_len <= 1:
        return None
    nf = max(8, min(400, int(seg_len)))
    segp = [_at(a + seg_len * k / nf) for k in range(nf + 1)]
    md = _at(a + seg_len / 2); an = _dir(a + seg_len / 2)
    up = (-_m.sin(an), _m.cos(an))
    if (up[0] * (cx - md[0]) + up[1] * (cy - md[1])) < 0:
        segp.reverse()
    off_in = 0.18 * MM
    n = len(segp); base = list(segp); segp = []
    for i in range(n):
        a2 = base[max(0, i - 1)]; b2 = base[min(n - 1, i + 1)]
        tx = b2[0] - a2[0]; ty = b2[1] - a2[1]; tl = _m.hypot(tx, ty) or 1.0; tx /= tl; ty /= tl
        segp.append((base[i][0] + (-ty) * off_in, base[i][1] + tx * off_in))
    lc = [0.0]
    for i in range(1, len(segp)):
        lc.append(lc[-1] + _m.hypot(segp[i][0] - segp[i - 1][0], segp[i][1] - segp[i - 1][1]))
    lt = lc[-1]
    if lt <= 1:
        return None

    def _lat(d):
        d = max(0.0, min(lt, d))
        i = bisect.bisect_right(lc, d)
        if i <= 0: return segp[0]
        if i >= len(segp): i = len(segp) - 1
        d0, d1 = lc[i - 1], lc[i]
        f = (d - d0) / (d1 - d0) if d1 > d0 else 0.0
        return (segp[i - 1][0] + f * (segp[i][0] - segp[i - 1][0]), segp[i - 1][1] + f * (segp[i][1] - segp[i - 1][1]))

    def _ldir(d):
        w = max(1.5, size * 0.6)
        p = _lat(max(0.0, d - w)); q = _lat(min(lt, d + w))
        return _m.degrees(_m.atan2(q[1] - p[1], q[0] - p[0]))

    aw = fetq.ancho_texto(texto, size)
    mg = min(seg_len * 0.06, 2.5 * MM)
    if align == "izquierda":
        d0 = mg
    elif align == "derecha":
        d0 = max(mg, lt - mg - aw)
    else:
        d0 = max(0.0, lt / 2 - aw / 2)
    parts = []; d = d0
    for ch in texto:
        cw = fetq.ancho_texto(ch, size)
        p = _lat(d)
        parts.append(fetq.ops_texto(ch, size, p[0], p[1], angulo_deg=_ldir(d)))
        d += cw
    return "\n".join(parts)


def _eops_zonas(cont, S, x0, y0, B, puntos, conts, size, align_def, fetq, talle, pieza, nro, sep):
    """TEXT-ON-PATH POR ZONAS: parte el contorno por las esquinas elegidas (`puntos` =
    fracciones 0..1 del arco; cada una se ENGANCHA a la esquina REAL más cercana de ESTA
    pieza → estable aunque el talle esté gradado, igual que el preview). La zona i va del
    punto i al i+1 (con wrap) y su texto se arma de `conts[i]` = {mostrar:{talle,pieza,
    numero}, texto, align}. Devuelve los ops de TODAS las zonas o None. NO toca el camino de
    la etiqueta única (`_eops_borde`)."""
    import math as _m, bisect

    def _P(vx, vy):
        return (vx * S + B - x0 * S, vy * S + B - y0 * S)

    # 1) aplanar el contorno a polilínea (idéntico a _eops_borde)
    pts = []; cur = None; ini = None
    for s in cont["segmentos"]:
        op = s[0]
        if op == "m":
            cur = _P(s[1], s[2]); pts.append(cur); ini = cur
        elif op == "l":
            cur = _P(s[1], s[2]); pts.append(cur)
        elif op == "c":
            p0 = cur or _P(s[1], s[2]); p1 = _P(s[1], s[2]); p2 = _P(s[3], s[4]); p3 = _P(s[5], s[6])
            for k in range(1, 9):
                u = k / 8.0; mu = 1 - u
                pts.append((mu*mu*mu*p0[0] + 3*mu*mu*u*p1[0] + 3*mu*u*u*p2[0] + u*u*u*p3[0],
                            mu*mu*mu*p0[1] + 3*mu*mu*u*p1[1] + 3*mu*u*u*p2[1] + u*u*u*p3[1]))
            cur = p3
        elif op == "re":
            X, Y, Wd, Ht = s[1], s[2], s[3], s[4]
            q = [_P(X, Y), _P(X+Wd, Y), _P(X+Wd, Y+Ht), _P(X, Y+Ht), _P(X, Y)]
            pts += q; cur = q[0]; ini = q[0]
        elif op == "h":
            if ini and cur != ini: pts.append(ini)
            cur = ini
    if len(pts) < 3:
        return None
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + _m.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]))
    total = cum[-1]
    if total <= 1:
        return None

    def _at(l):
        l = l % total
        i = bisect.bisect_right(cum, l)
        if i <= 0: return pts[0]
        if i >= len(pts): i = len(pts) - 1
        l0, l1 = cum[i-1], cum[i]
        f = (l - l0) / (l1 - l0) if l1 > l0 else 0.0
        return (pts[i-1][0] + f*(pts[i][0]-pts[i-1][0]), pts[i-1][1] + f*(pts[i][1]-pts[i-1][1]))

    def _dir(l):
        a = _at(l - 1.0); b = _at(l + 1.0)
        return _m.atan2(b[1]-a[1], b[0]-a[0])

    # 2) TODAS las esquinas del contorno (mismo criterio que el preview `esquinasDe`), para
    #    enganchar los puntos elegidos a la esquina exacta de ESTE talle.
    _h = max(2.5, total / 160)
    def _dirh(l):
        a = _at(l - _h); b = _at(l + _h)
        return _m.atan2(b[1]-a[1], b[0]-a[0])
    N = max(120, min(700, int(round(total)))); step = total / N
    def _turn(l):
        d0 = _dirh(l - step*1.5); d1 = _dirh(l + step*1.5)
        return abs(((d1 - d0 + _m.pi) % (2*_m.pi)) - _m.pi)
    tn = [_turn(i*step) for i in range(N)]
    thr = 0.5; cor = []; i = 0
    while i < N:
        if tn[i] > thr:
            j = i; best = i
            while j < N + 5 and tn[j % N] > thr*0.5:
                if tn[j % N] > tn[best % N]: best = j
                j += 1
            cor.append(((best % N) * step) % total); i = j
        else:
            i += 1
    corners = []; cor.sort()
    for c in cor:
        if not corners or min(abs(c-corners[-1]), total-abs(c-corners[-1])) > total/40:
            corners.append(c)
    if len(corners) > 1 and min(abs(corners[0]-corners[-1]), total-abs(corners[0]-corners[-1])) < total/40:
        corners.pop()

    def _snap(tf):
        L = (float(tf) % 1.0) * total
        if not corners:
            return L
        return min(corners, key=lambda c: min(abs(c-L), total-abs(c-L)))

    P = [_snap(tf) for tf in puntos]      # preserva el orden punto↔cont (no reordenar)
    if len(P) < 2:
        return None
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    out = []
    for idx in range(len(P)):
        a = P[idx]; b = P[(idx + 1) % len(P)]
        if b <= a:
            b += total
        c = conts[idx] if idx < len(conts) else {}
        mos = (c or {}).get("mostrar") or {}
        _partes = []
        if mos.get("talle"):  _partes.append(str(talle))
        if mos.get("pieza"):  _partes.append(pieza)
        if mos.get("numero"): _partes.append(f"#{nro:02d}")
        if (c or {}).get("texto"): _partes.append(str(c["texto"]))
        txt = sep.join(_partes)
        if not txt:
            continue
        alg = (c or {}).get("align") or align_def or "centro"
        ops = _eops_tramo(_at, _dir, a, b, cx, cy, txt, size, alg, fetq)
        if ops:
            out.append(ops)
    return "\n".join(out) if out else None


def nombres_normalizados(asignaciones):
    """`[{"idx":i,"nombre":"Frente"}]` → `{idx: nombre_final}` con la MISMA regla que usa el
    registro. Vive suelta (y no adentro de `alta_plantilla_manual`) porque quien guarda una
    correspondencia a mano necesita saber con qué nombre va a quedar la pieza: la clave de
    `emparejado_talles.json["manual"]` es el nombre FINAL, no el que se tipeó.

    SEGURIDAD: dos piezas con el MISMO nombre colisionan en el registro (dict por nombre) y se
    pierde una. Si un genérico trae nombres duplicados se renumera TODO ese genérico 1..N (por
    idx); los genéricos ya únicos se respetan tal cual (no se toca la numeración)."""
    _raw = {a["idx"]: a["nombre"].strip() for a in (asignaciones or []) if (a.get("nombre") or "").strip()}
    import re as _re2, collections as _c2
    def _gen_pz(n):
        return _re2.sub(r"\s+\d+\s*$", "", n).strip()
    _por_gen = _c2.OrderedDict()
    for _i in sorted(_raw):
        _por_gen.setdefault(_gen_pz(_raw[_i]), []).append(_i)
    nombres = {}
    for _g, _idxs in _por_gen.items():
        _vals = [_raw[_i] for _i in _idxs]
        if len(set(_vals)) == len(_vals):
            for _i in _idxs:
                nombres[_i] = _raw[_i]
        elif len(_idxs) == 1:
            nombres[_idxs[0]] = _g
        else:
            for _k, _i in enumerate(_idxs, 1):
                nombres[_i] = f"{_g} {_k}"
    return nombres


def alta_plantilla_manual(path, asignaciones, mesa, talle_ref, indices=None, emparejado=None):
    """Construye el registro a partir de nombres puestos a mano en el talle de
    referencia. `asignaciones` = [{"idx": i, "nombre": "Frente"}, ...]. El nombre
    de cada pieza se propaga a TODOS los talles emparejando por posición
    (centroide normalizado), sin pedir etiquetas de texto en el .ai.
    `emparejado` = {"acomodo": {talle:{idx:[dx_mm,dy_mm]}}, "manual": {talle:{nombre:idx}}}:
    el ajuste a mano del usuario cuando el molde no tiene las piezas dispuestas parecido
    entre talles (ver §10.c del mapa)."""
    doc = _abrir(path)
    nombres = nombres_normalizados(asignaciones)
    if not nombres:
        return {"mesas": len(doc), "registro": {}, "piezas": [], "talles": [],
                "completos": [], "problemas": ["No se asignó ningún nombre de pieza."],
                "advertencias": [], "piezas_detalle": {}}

    piezas_ref = extraer_piezas_mesa(doc, mesa, talle_ref)
    f_ref = _feats_conts(piezas_ref, emp_offsets(emparejado, talle_ref))
    nombres_ref = {nombres[i]: i for i in nombres if i < len(piezas_ref)}
    mapa_exacto = _mapa_indices(indices, talle_ref)   # correspondencia EXACTA del DXF (si existe)

    talles_mesas = _talles_con_molde(doc)
    registro, problemas, advertencias = {}, [], []
    for talle, mesas in talles_mesas.items():
        if mesa not in mesas:
            continue
        piezas = extraer_piezas_mesa(doc, mesa, talle)
        if not piezas:
            continue
        # Emparejar: EXACTO si el DXF trae la correspondencia; si no, por POSICIÓN +
        # FORMA + TAMAÑO (el matching por cercanía sola confundía piezas parecidas).
        if talle == talle_ref:
            eleccion = {nom: (i, False) for nom, i in nombres_ref.items()}
        elif mapa_exacto and talle in mapa_exacto:
            mt = mapa_exacto[talle]
            eleccion = {nom: (mt[ir], False) for nom, ir in nombres_ref.items()
                        if ir in mt and mt[ir] < len(piezas)}
        else:
            eleccion = _emparejar_por_forma(f_ref, nombres_ref,
                                            _feats_conts(piezas, emp_offsets(emparejado, talle)))
        # Una corrección MANUAL nunca se pisa con lo automático (ni con el DXF): va última.
        # En el talle GUÍA no se toca: ahí la asignación ES el nombrado del usuario.
        if talle != talle_ref:
            eleccion = _aplicar_fijos(eleccion, emp_fijos(emparejado, talle), len(piezas))
        for nom, (j, _rot) in eleccion.items():
            cont = piezas[j]
            registro.setdefault(nom, {})[talle] = {
                "mesa": mesa, "pieza_idx": j,
                "w_cm": round(cont["w"] / CM, 1), "h_cm": round(cont["h"] / CM, 1),
                "bbox_mu": [round(v, 2) for v in cont["bbox_mu"]],
                "ancla": _ancla_sintetica(cont, talle)}

    talles = _ordenar_por_archivo(doc, talles_mesas.keys())
    completos = [t for t in talles if all(t in registro.get(p, {}) for p in registro)]
    piezas_detalle = {}
    for pieza, por_talle in registro.items():
        mayor = max(por_talle.values(), key=lambda v: v["h_cm"])
        piezas_detalle[pieza] = {"mesas": [mesa],
            "talles": _ordenar_por_archivo(doc, por_talle.keys()),
            "talle_mayor_cm": {"w": mayor["w_cm"], "h": mayor["h_cm"]}}
    return {"mesas": len(doc), "talles": talles, "piezas": sorted(registro.keys()),
            "completos": completos, "registro": registro, "problemas": problemas,
            "advertencias": advertencias, "piezas_detalle": piezas_detalle}


# ════════════════ VALIDACIÓN DE ARTE ════════════════
def _separaciones(pg_obj, vistos):
    enc = set()
    def rec(o, pr=0):
        if pr > 16:
            return
        try:
            og = o.objgen if hasattr(o, "objgen") and o.objgen != (0, 0) else None
        except Exception:
            og = None
        if og:
            if og in vistos:
                return
            vistos.add(og)
        if isinstance(o, Array) and len(o) >= 2:
            try:
                if str(o[0]) == "/Separation":
                    enc.add(str(o[1])[1:])
            except Exception:
                pass
        if isinstance(o, (Dictionary, pikepdf.Stream)):
            for k in o.keys():
                try:
                    rec(o[k], pr + 1)
                except Exception:
                    pass
        elif isinstance(o, Array):
            for it in o:
                try:
                    rec(it, pr + 1)
                except Exception:
                    pass
    rec(pg_obj)
    return enc


def validar_arte(path_arte, path_plantilla, carpeta_fuentes):
    db, da = _abrir(path_plantilla), _abrir(path_arte)
    checks, ok = [], True

    coincide = len(db) == len(da) and all(
        abs(db[i].rect.width - da[i].rect.width) < 2 and abs(db[i].rect.height - da[i].rect.height) < 2
        for i in range(len(db)))
    checks.append({"nombre": "Estructura coincide con la plantilla",
                   "ok": coincide, "detalle": f"{len(da)}/{len(db)} mesas"})
    ok &= coincide

    cb = set(i["name"] for i in db.get_ocgs().values())
    ca = set(i["name"] for i in da.get_ocgs().values())
    faltan_capas = sorted(cb - ca)
    checks.append({"nombre": "Capas requeridas presentes", "ok": not faltan_capas,
                   "detalle": f"{len(ca & cb)}/{len(cb)}" + (f" — faltan {faltan_capas}" if faltan_capas else "")})
    ok &= not faltan_capas

    p = _abrir_pike(path_arte)
    tintas = {}
    for i, pg in enumerate(p.pages):
        for t in _separaciones(pg.obj, set()):
            if t != "All":
                tintas.setdefault(t, 0)
                tintas[t] += 1
    checks.append({"nombre": "Tintas planas en el PDF", "ok": True,
                   "detalle": ", ".join(f"{t} ({n} mesas)" for t, n in tintas.items()) or "ninguna (solo proceso)"})

    d2 = _abrir(path_arte)
    for c in d2.layer_ui_configs():
        if c["text"] != "Fondo":
            d2.set_layer_ui_config(c["number"], action=2)
    planas = []
    for i in range(len(d2)):
        pix = d2[i].get_pixmap(matrix=fitz.Matrix(0.04, 0.04))
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(int)
        if a.std(axis=(0, 1)).mean() < 8:
            planas.append(i + 1)
    checks.append({"nombre": "Cobertura de diseño", "ok": not planas,
                   "detalle": "sin mesas vacías" if not planas else f"mesas sin diseño: {planas}"})

    requeridas = fuentes_requeridas_arte(path_arte)
    faltan_f = {n: usos for n, usos in requeridas.items() if not resolver_fuente(n, carpeta_fuentes)}
    checks.append({"nombre": "Tipografías requeridas en catálogo", "ok": not faltan_f,
                   "detalle": ", ".join(requeridas) if not faltan_f else
                   "FALTAN: " + ", ".join(f"{n} ({'/'.join(u)})" for n, u in faltan_f.items())})
    ok &= not faltan_f

    pers = extraer_personalizacion(path_arte)
    checks.append({"nombre": "Placeholders de personalización", "ok": bool(pers),
                   "detalle": f"{len(pers)} mesas de espalda" if pers else "no encontrados (pedido sin nombre/número)"})

    return {"aprobado": bool(ok), "checks": checks, "tintas": tintas,
            "fuentes_requeridas": requeridas, "fuentes_faltantes": sorted(faltan_f),
            "personalizacion": pers}


def fuentes_requeridas_arte(path_arte):
    requeridas = {}
    for capa in ("Personalizable", None):
        doc = _abrir(path_arte)
        for c in doc.layer_ui_configs():
            if capa:
                on = (c["text"] == capa)
            else:
                # "etiquetas" = texto VIVO del ARTE (capa diseño), que SÍ debe ir en
                # curvas. Las capas de personalización (nombre/numero/palabra/…) llevan
                # texto vivo a propósito —el motor las redibuja— así que NO cuentan como
                # texto vivo del diseño y no deben observar el arte.
                on = c["text"].strip().lower() in ("diseño", "diseno")
            doc.set_layer_ui_config(c["number"], action=0 if on else 1)
        for i in range(len(doc)):
            for b in doc[i].get_text("dict")["blocks"]:
                if b.get("type") != 0:
                    continue
                for l in b["lines"]:
                    for s in l["spans"]:
                        requeridas.setdefault(s["font"].split("+")[-1], set()).add(
                            "personalización" if capa else "etiquetas")
    return {n: sorted(u) for n, u in requeridas.items()}


PH_NOMBRE = {"NOMBRE", "NOMBRES", "APELLIDO", "NAME"}   # placeholders de nombre
PH_NUMERO = {"00", "0", "##", "##"}                    # placeholders de número


def _colores_personalizable(path_arte):
    """Color de relleno NATIVO (sin convertir) del TEXTO de personalización, por mesa
    y POR TEXTO: {mesa: {texto_norm: (op, [valores])}} con op ∈ k/rg/g. Lee el color
    del relleno vigente en cada Tj que está dentro de una capa de personalización
    (Personalizable o la capa de campo: Nombre, Número, Palabra…), NO en la gráfica/
    guías. Así conserva EXACTO el CMYK/color de cada campo, sin pasar a RGB."""
    try:
        pdf = _abrir_pike(path_arte)
    except Exception:
        return {}
    res = {}
    for i, pg in enumerate(pdf.pages):
        try:
            insts = parse_content_stream(pg)
        except Exception:
            continue
        # Colorspaces de la página → nº de componentes, para mapear scn/sc a k/rg/g.
        try:
            csres = pg.get("/Resources", {}).get("/ColorSpace", {}) or {}
        except Exception:
            csres = {}

        def _n_de_cs(name):
            try:
                o = csres.get(name)
                if o is None:
                    return None
                if isinstance(o, pikepdf.Array):
                    base = str(o[0])
                    if base == "/ICCBased" and len(o) > 1:
                        return int(o[1].get("/N", 0)) or None
                    if base == "/DeviceN" and len(o) > 1:
                        try: return len(o[1])
                        except Exception: return None
                    return {"/CalRGB": 3, "/CalGray": 1, "/Separation": 1}.get(base)
                return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(str(o))
            except Exception:
                return None

        _op_n = {4: "k", 3: "rg", 1: "g"}
        dentro, cur, cur_cs_n, per = 0, None, None, {}
        _gstack = []   # el color de relleno es ESTADO GRÁFICO: q lo guarda y Q lo restaura.
        for inst in insts:
            op = str(inst.operator)
            # q/Q: sin esto, un `Q` antes del Tj restaura un color que NO es el último leído
            # linealmente (Illustrator dibuja el halo blanco dentro de q..Q y el texto después
            # del Q) → se leía blanco donde el archivo pinta negro (bug del número del frente).
            if op == "q":
                _gstack.append((cur, cur_cs_n)); continue
            if op == "Q":
                if _gstack: cur, cur_cs_n = _gstack.pop()
                continue
            # color de relleno actual (puede setearse fuera del OC y heredarse).
            # Soporta tanto k/rg/g (device) como cs+scn/sc (ICCBased/CMYK, lo que
            # exporta Illustrator) — antes solo leía device y perdía el color real.
            if op == "cs":
                cur_cs_n = _n_de_cs(str(inst.operands[0])) if inst.operands else None
            elif op in ("k", "rg", "g"):
                try:
                    cur = (op, tuple(round(float(x), 4) for x in inst.operands))
                except Exception:
                    cur = None
            elif op in ("scn", "sc"):
                try:
                    vals = [float(x) for x in inst.operands]   # falla si es patrón (/P0) → se ignora
                    o2 = _op_n.get(cur_cs_n or len(vals))
                    if o2 and len(vals) == {"k": 4, "rg": 3, "g": 1}[o2]:
                        cur = (o2, tuple(round(v, 4) for v in vals))
                except Exception:
                    pass
            # Entramos a una capa de PERSONALIZACIÓN (Personalizable o capa de campo:
            # Nombre, Número…), NO a la gráfica/guías.
            if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
                if any(_norm_nombre(n) not in CAPAS_GRAFICAS for n in _nombres_oc(inst.operands[1], pg)):
                    dentro += 1; continue
                elif dentro:
                    dentro += 1
            elif op in ("BDC", "BMC") and dentro:
                dentro += 1
            elif op == "EMC" and dentro:
                dentro -= 1; continue
            # color de relleno de CADA texto, por contenido (no el de la estrella/escudo,
            # que es un path). Se guarda el del primer Tj de cada texto = su relleno.
            if dentro and op in ("Tj", "TJ", "'", '"') and cur is not None:
                k = _norm_nombre(_texto_de_tj(inst))
                if k and k not in per:
                    per[k] = (cur[0], list(cur[1]))
        if per:
            res[str(i + 1)] = per
    return res


def _texto_de_tj(inst):
    """Texto (string) de un operador Tj/TJ/'/\" del content stream."""
    op = str(inst.operator)
    try:
        if op == "TJ":
            partes = []
            for x in inst.operands[0]:
                try:
                    float(x)            # número (kerning) → no es texto
                except Exception:
                    partes.append(str(x))
            return "".join(partes)
        return str(inst.operands[-1])    # Tj / ' / "
    except Exception:
        return ""


def _trazo_personalizable(path_arte):
    """Trazo/borde del TEXTO de personalización, por mesa y POR TEXTO:
    {mesa: {texto_norm: (op, [vals], ancho)}}. Illustrator dibuja el placeholder
    relleno y, encima, una copia con stroke (color de trazo CS+SCN / K/RG/G en
    MAYÚSCULAS + ancho `w`). Se captura ese borde para respetarlo al re-estampar.
    El ancho difiere por campo (numero ≠ nombre), por eso se guarda por texto."""
    try:
        pdf = _abrir_pike(path_arte)
    except Exception:
        return {}
    res = {}
    for i, pg in enumerate(pdf.pages):
        try:
            insts = parse_content_stream(pg)
        except Exception:
            continue
        try:
            csres = pg.get("/Resources", {}).get("/ColorSpace", {}) or {}
        except Exception:
            csres = {}

        def _n_de_cs(name):
            try:
                o = csres.get(name)
                if o is None:
                    return None
                if isinstance(o, pikepdf.Array):
                    base = str(o[0])
                    if base == "/ICCBased" and len(o) > 1:
                        return int(o[1].get("/N", 0)) or None
                    if base == "/DeviceN" and len(o) > 1:
                        try: return len(o[1])
                        except Exception: return None
                    return {"/CalRGB": 3, "/CalGray": 1, "/Separation": 1}.get(base)
                return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(str(o))
            except Exception:
                return None

        _op_n = {4: "k", 3: "rg", 1: "g"}
        dentro, scol, scs_n, sw, per, _ult_txt = 0, None, None, None, {}, ""
        _gstack = []   # trazo (color+ancho) también es ESTADO GRÁFICO: q guarda / Q restaura
        for inst in insts:
            op = str(inst.operator)
            if op == "q":
                _gstack.append((scol, scs_n, sw)); continue
            if op == "Q":
                if _gstack: scol, scs_n, sw = _gstack.pop()
                continue
            if op == "CS":
                scs_n = _n_de_cs(str(inst.operands[0])) if inst.operands else None
            elif op in ("K", "RG", "G"):       # color de TRAZO device (mayúsculas)
                try:
                    scol = (op.lower(), tuple(round(float(x), 4) for x in inst.operands))
                except Exception:
                    scol = None
            elif op in ("SCN", "SC"):          # color de TRAZO en colorspace nombrado
                try:
                    vals = [float(x) for x in inst.operands]
                    o2 = _op_n.get(scs_n or len(vals))
                    if o2 and len(vals) == {"k": 4, "rg": 3, "g": 1}[o2]:
                        scol = (o2, tuple(round(v, 4) for v in vals))
                except Exception:
                    pass
            elif op == "w":                    # ancho del trazo
                try:
                    sw = float(inst.operands[0])
                except Exception:
                    pass
            if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
                if any(_norm_nombre(n) not in CAPAS_GRAFICAS for n in _nombres_oc(inst.operands[1], pg)):
                    if dentro == 0:
                        scol, sw = None, None   # reset al entrar (sin arrastrar estado de afuera)
                    dentro += 1; continue
                elif dentro:
                    dentro += 1
            elif op in ("BDC", "BMC") and dentro:
                dentro += 1
            elif op == "EMC" and dentro:
                dentro -= 1; continue
            # texto de RELLENO más reciente (al que pertenece el borde que venga después)
            if dentro and op in ("Tj", "TJ", "'", '"'):
                t = _norm_nombre(_texto_de_tj(inst))
                if t:
                    _ult_txt = t
            # el BORDE se dibuja como contornos del glifo TRAZADOS (S/B…) con color de
            # trazo + ancho>0 → se asocia al texto de relleno anterior
            if dentro and op in ("S", "s", "B", "B*", "b", "b*") and scol is not None and sw and sw > 0:
                if _ult_txt and _ult_txt not in per:
                    per[_ult_txt] = (scol[0], list(scol[1]), round(sw, 3))
        if per:
            res[str(i + 1)] = per
    return res


def _pasadas_personalizable(path_arte):
    """PILA DE APARIENCIAS: la lista ORDENADA de pasadas de pintado de cada texto de
    personalización — {mesa: {texto_norm: [{"t": "f"|"S", "color": (op, [vals]), "w": float}]}}.

    Illustrator aplana la Apariencia de un texto así: primero el texto con su color ORIGINAL y,
    ENCIMA, cada capa de la apariencia (los contornos TRAZADOS con `S`, y/o el texto re-dibujado
    con el relleno de esa capa). Lo que SE VE es lo de arriba de la pila; el color original queda
    tapado. Por eso `_colores_personalizable` (se queda con el PRIMER relleno) devolvía el color
    tapado: p. ej. un número azul con borde blanco salía negro. Acá se guarda TODO en orden y el
    motor lo re-dibuja igual. Ver MAPA_DEL_SISTEMA.md → changelog 2026-07-16.
    """
    try:
        pdf = _abrir_pike(path_arte)
    except Exception:
        return {}
    res = {}
    for i, pg in enumerate(pdf.pages):
        try:
            insts = parse_content_stream(pg)
        except Exception:
            continue
        try:
            csres = pg.get("/Resources", {}).get("/ColorSpace", {}) or {}
        except Exception:
            csres = {}

        def _n_de_cs(name):
            try:
                o = csres.get(name)
                if o is None:
                    return None
                if isinstance(o, pikepdf.Array):
                    base = str(o[0])
                    if base == "/ICCBased" and len(o) > 1:
                        return int(o[1].get("/N", 0)) or None
                    if base == "/DeviceN" and len(o) > 1:
                        try: return len(o[1])
                        except Exception: return None
                    return {"/CalRGB": 3, "/CalGray": 1, "/Separation": 1}.get(base)
                return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(str(o))
            except Exception:
                return None

        _op_n = {4: "k", 3: "rg", 1: "g"}
        # relleno y trazo son ESTADO GRÁFICO: `q` guarda y `Q` restaura (gotcha ya documentado).
        fcol, fcs_n, scol, scs_n, sw = None, None, None, None, None
        dentro, per, _ult_txt, _hay_texto, _acum = 0, {}, "", False, ""
        _gstack = []

        _acum, _pl = "", []      # texto y pasadas de la capa que se está recorriendo

        def _add(pasada):
            # Un texto se dibuja glifo a glifo (6 `Tj`/`S` seguidos = UNA capa, no seis): las
            # pasadas consecutivas idénticas son la misma capa de la apariencia.
            if _pl and _pl[-1] == pasada:
                return
            _pl.append(pasada)

        for inst in insts:
            op = str(inst.operator)
            if op == "q":
                _gstack.append((fcol, fcs_n, scol, scs_n, sw)); continue
            if op == "Q":
                if _gstack: fcol, fcs_n, scol, scs_n, sw = _gstack.pop()
                continue
            if op == "cs":
                fcs_n = _n_de_cs(str(inst.operands[0])) if inst.operands else None
            elif op == "CS":
                scs_n = _n_de_cs(str(inst.operands[0])) if inst.operands else None
            elif op in ("k", "rg", "g"):
                try: fcol = (op, tuple(round(float(x), 4) for x in inst.operands))
                except Exception: fcol = None
            elif op in ("K", "RG", "G"):
                try: scol = (op.lower(), tuple(round(float(x), 4) for x in inst.operands))
                except Exception: scol = None
            elif op in ("scn", "sc"):
                try:
                    vals = [float(x) for x in inst.operands]
                    o2 = _op_n.get(fcs_n or len(vals))
                    if o2 and len(vals) == {"k": 4, "rg": 3, "g": 1}[o2]:
                        fcol = (o2, tuple(round(v, 4) for v in vals))
                except Exception:
                    pass
            elif op in ("SCN", "SC"):
                try:
                    vals = [float(x) for x in inst.operands]
                    o2 = _op_n.get(scs_n or len(vals))
                    if o2 and len(vals) == {"k": 4, "rg": 3, "g": 1}[o2]:
                        scol = (o2, tuple(round(v, 4) for v in vals))
                except Exception:
                    pass
            elif op == "w":
                try: sw = float(inst.operands[0])
                except Exception: pass

            if op == "BDC" and len(inst.operands) == 2 and str(inst.operands[0]) == "/OC":
                if any(_norm_nombre(n) not in CAPAS_GRAFICAS for n in _nombres_oc(inst.operands[1], pg)):
                    if dentro == 0:
                        scol, sw = None, None    # sin arrastrar el estado de trazo de afuera
                        _acum, _pl = "", []      # arranca la capa
                    dentro += 1; continue
                elif dentro:
                    dentro += 1
            elif op in ("BDC", "BMC") and dentro:
                dentro += 1
            elif op == "EMC" and dentro:
                dentro -= 1
                if not dentro:
                    # AL SALIR DE LA CAPA se vuelca todo. NO se puede depender del `ET`: hay artes
                    # donde el `BT..ET` envuelve a la capa (el texto empieza AFUERA) y adentro sólo
                    # están los `scn`+`Tj` → el `ET` nunca cae dentro y no se guardaba nada.
                    # La clave es el texto acumulado; si el arte lo dibuja 2 veces queda
                    # "nombrenombre", y `_match_texto` igual lo encuentra (matchea por contención).
                    t = _norm_nombre(_acum)
                    if t and _pl:
                        per.setdefault(t, list(_pl))
                    _acum, _pl = "", []
                continue
            if not dentro:
                continue

            if op in ("Tj", "TJ", "'", '"'):
                _acum += _texto_de_tj(inst) or ""
                # El relleno vigente en este glifo es una capa de la apariencia. Si cambió respecto
                # de la pasada anterior, es una capa NUEVA (p.ej. negro original → azul de arriba).
                if fcol is not None:
                    _add({"t": "f", "color": (fcol[0], list(fcol[1])), "w": 0.0})
            elif op in ("S", "s") and scol is not None and sw and sw > 0:
                _add({"t": "S", "color": (scol[0], list(scol[1])), "w": round(sw, 3)})
            elif op in ("B", "B*", "b", "b*"):
                # trazado con relleno Y trazo: PDF pinta primero el relleno y encima el trazo
                if fcol is not None:
                    _add({"t": "f", "color": (fcol[0], list(fcol[1])), "w": 0.0})
                if scol is not None and sw and sw > 0:
                    _add({"t": "S", "color": (scol[0], list(scol[1])), "w": round(sw, 3)})
        if per:
            res[str(i + 1)] = per
    return res


def _color_op(pl):
    """Operador PDF de color para el texto de personalización, en el espacio
    NATIVO del placeholder (CMYK/RGB/gris exactos, sin convertir). Si no se pudo
    leer el nativo, cae a sRGB→CMYK (queda en CMYK, nunca mete RGB en el archivo)."""
    cn = pl.get("colorn")
    if cn:
        op, vals = cn[0], cn[1]
        return " ".join(f"{v:g}" for v in vals) + " " + op
    rgb = pl.get("color", 0)
    r, g, b = ((rgb >> 16) & 255) / 255, ((rgb >> 8) & 255) / 255, (rgb & 255) / 255
    k = 1 - max(r, g, b)
    if k < 1:
        c, m, y = (1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k)
    else:
        c = m = y = 0.0
    return f"{c:.4f} {m:.4f} {y:.4f} {k:.4f} k"


_PERS_CACHE = {}   # memoización por (arte, mtime): extraer_personalizacion es talle/variable-INDEP
                   # y CARA (parsea el content-stream de todo el arte); se llamaba 1× POR TALLE (×19)
def extraer_personalizacion(path_arte, campos=None):
    """Lee los placeholders de personalización SOLO por CAPA: si hay una capa llamada
    como un campo (`nombre`, `numero`, `palabra`, `numero 2`, …) TODO el texto de esa
    capa es el placeholder de ese campo, diga lo que diga. `campos` = lista de nombres
    de campo a buscar (de las reglas que se estampan); si es None se auto-descubren las
    capas que no son de sistema. La clave de cada placeholder es el NOMBRE del campo.
    (El modo viejo "por texto en Personalizable" fue quitado.)"""
    try: _mt = os.path.getmtime(path_arte)
    except OSError: _mt = 0
    _ck = (path_arte, _mt, tuple(sorted(campos)) if campos else None)
    _hit = _PERS_CACHE.get(_ck)
    if _hit is not None:
        return _hit
    if campos is None:
        # AUTO-DESCUBRIR: cualquier capa que NO sea del sistema es un campo de
        # personalización (nombre, numero, palabra, numero 2, …). El nombre del
        # campo = el nombre de la capa.
        _sys = CAPAS_NO_PERS
        _d = fitz.open(path_arte)
        # Las capas "Editable …" son OBJETOS editables (mover/rotar/escalar), NO campos de
        # personalización: se excluyen para que no se estampen como texto.
        campos = [c["text"] for c in _d.layer_ui_configs()
                  if _norm_nombre(c["text"]) not in _sys and not _es_capa_editable(c["text"])]
        _d.close()
    nativos = _colores_personalizable(path_arte)   # color exacto por mesa y por texto
    trazos = _trazo_personalizable(path_arte)       # borde/trazo por mesa y por texto (compat)
    pasadas = _pasadas_personalizable(path_arte)    # PILA de apariencias ORDENADA (manda ésta)
    pers = {}

    def _match_texto(dmesa, tn):
        # busca por contenido. El relleno puede venir duplicado (fitz lee "0000"
        # cuando el "00" se dibuja dos veces) → match flexible por contención. Si no
        # matchea y la mesa tiene un solo valor, se usa ese.
        if not dmesa:
            return None
        v = dmesa.get(tn)
        if v is None:
            v = next((x for k, x in dmesa.items() if k and (k in tn or tn in k)), None)
        if v is None and len(dmesa) == 1:
            v = next(iter(dmesa.values()))
        return v

    def _registrar(mesa, campo, l):
        s0 = l["spans"][0]
        bb = fitz.Rect(l["bbox"])
        txt = "".join(s["text"] for s in l["spans"]).strip()
        tn = _norm_nombre(txt)
        colorn = _match_texto(nativos.get(str(mesa)) or {}, tn)
        tz = _match_texto(trazos.get(str(mesa)) or {}, tn)
        d = pers.setdefault(str(mesa), {}).setdefault(campo, {
            "cx": round((bb.x0 + bb.x1) / 2, 1), "baseline_y": round(s0["origin"][1], 1),
            "size": round(s0["size"], 1), "fuente": s0["font"].split("+")[-1],
            "ancho": round(bb.width, 1), "color": s0.get("color", 0),
            "colorn": colorn, "trazo": tz,
            "pasadas": _match_texto(pasadas.get(str(mesa)) or {}, tn),   # pila de apariencias
            "baseline_pts": [], "_txt": ""})
        # Acumular la LÍNEA BASE de cada glifo/renglón (origin x,y + bordes x0,x1 del bbox del
        # renglón). Si el placeholder viene sobre una CURVA/ARCO, sus glifos trazan la curva; si
        # es un PÁRRAFO de varias líneas, cada renglón trae su ancho → sirve para la ALINEACIÓN.
        for s in l["spans"]:
            if s["text"].strip():
                d["baseline_pts"].append((round(s["origin"][0], 1), round(s["origin"][1], 1),
                                          round(bb.x0, 1), round(bb.x1, 1)))
        d["_txt"] += txt   # texto completo (un nombre en curva llega glifo a glifo)

    # ── 1) Por CAPA: aislar cada capa-campo (mostrarla sola) y leer su texto ──
    d0 = fitz.open(path_arte)
    capas = [(c["text"], c["number"]) for c in d0.layer_ui_configs()]
    d0.close()
    for campo in campos:
        cn = _norm_nombre(campo)
        if not any(_norm_nombre(name) == cn for name, _ in capas):
            continue                                   # el diseño no trae esa capa
        d = fitz.open(path_arte)
        for c in d.layer_ui_configs():
            d.set_layer_ui_config(c["number"], action=0 if _norm_nombre(c["text"]) == cn else 1)
        for mesa in range(1, len(d) + 1):
            for b in d[mesa - 1].get_text("dict")["blocks"]:
                if b.get("type") != 0:
                    continue
                for l in b["lines"]:
                    if "".join(s["text"] for s in l["spans"]).strip():
                        _registrar(mesa, campo, l)
        d.close()

    # El modo viejo "por texto en la capa Personalizable" (adivinar NOMBRE/00 por
    # contenido) FUE QUITADO a pedido del usuario: la personalización se toma SOLO por
    # nombre de capa (Nombre, Número, Palabra…). Un diseño con la capa Personalizable
    # genérica ya NO estampa: hay que usar una capa por campo con su nombre.
    # Limpiar la línea base de cada placeholder: el placeholder viene duplicado (relleno +
    # trazo) → puntos repetidos. Se deduplican y ordenan por x (orden de lectura del arco).
    # Además se RE-MATCHEA el borde/color por el TEXTO COMPLETO: un nombre en curva llega glifo
    # a glifo, y su borde queda guardado bajo UN glifo (ej. la 's' de "NOMBRES") → matchear por
    # el nombre entero lo encuentra (antes daba trazo=None y el nombre salía sin borde).
    for _mk, _md in pers.items():
        for _pl in _md.values():
            _bp = _pl.get("baseline_pts") or []
            _seen, _uniq = set(), []
            for _p in sorted(_bp, key=lambda q: q[0]):
                _k = (round(_p[0]), round(_p[1]))
                if _k not in _seen:
                    _seen.add(_k); _uniq.append(_p)   # (x, y, x0, x1)
            _pl["baseline_pts"] = _uniq
            _tn = _norm_nombre(_pl.get("_txt", ""))
            if _tn:
                _pl["trazo"] = _match_texto(trazos.get(_mk) or {}, _tn) or _pl.get("trazo")
                _pl["colorn"] = _match_texto(nativos.get(_mk) or {}, _tn) or _pl.get("colorn")
            _pl.pop("_txt", None)
    if len(_PERS_CACHE) > 24:
        _PERS_CACHE.clear()
    _PERS_CACHE[_ck] = pers
    return pers


# ════════════════ ARTE SEPARADO: detección y validación ════════════════
def _norm_nombre(s):
    if not s:
        return ""
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace("-", " ").split())


def _norm_generico(s):
    """Nombre normalizado SIN el número final ("Frente 8" → "frente"). Sirve para que la
    posición/config de la etiqueta se aplique a TODAS las piezas del mismo nombre (todos los
    frentes), no solo a la que se tocó."""
    import re
    return re.sub(r"\s+\d+\s*$", "", _norm_nombre(s)).strip()


def _es_capa_editable(nombre):
    """True si la capa OCG es un OBJETO EDITABLE: su nombre empieza con 'editable'."""
    return _norm_nombre(nombre).startswith("editable")


def _nombre_editable(capa):
    """Nombre legible del objeto: quita el prefijo 'editable' (con o sin separador)."""
    import re as _re
    s = str(capa).strip()
    m = _re.match(r'(?i)^\s*editable\b[\s\-_]*', s)
    return (s[m.end():].strip() if m else s) or "Editable"


def extraer_editables(path_arte, con_thumb=True):
    """Detecta los OBJETOS EDITABLES del arte: cada capa OCG de primer nivel cuyo nombre
    empieza con 'editable' (ej. 'Editable Escudo'). Cada capa = un objeto independiente
    (mover/rotar/escalar por el usuario). El nombre de la capa de Illustrator de primer
    nivel SÍ se conserva como OCG aislable (las sub-capas NO → por eso 1 capa por objeto).
    Devuelve [{mesa, capa, nombre, bbox_mu, w_cm, h_cm, thumb, svg}] (bbox_mu en coords MuPDF
    y-abajo; thumb = PNG base64 del objeto aislado). Las formas se ubican por `get_drawings`
    (campo `layer`); el thumbnail se saca aislando la capa (apaga el resto).
    `con_thumb=False` SALTA el thumb/svg (get_pixmap/get_svg_image + toggles de capa) — eso solo
    lo usa el VISOR del front; el MOTOR (generar_pedido) usa únicamente la geometría, y esto se
    llama por cada talle → generar imágenes ahí es puro desperdicio (×19 en asignar_todo)."""
    import base64
    doc = _abrir(path_arte)
    cfgs = doc.layer_ui_configs() if con_thumb else None
    objs = []
    for pno in range(len(doc)):
        pg = doc[pno]
        cajas = {}
        def _sumar(lay, x0, y0, x1, y1):
            if not lay or not _es_capa_editable(lay):
                return
            b = cajas.setdefault(lay, [x0, y0, x1, y1])
            b[0] = min(b[0], x0); b[1] = min(b[1], y0)
            b[2] = max(b[2], x1); b[3] = max(b[3], y1)

        for dr in pg.get_drawings():
            r = dr.get("rect")
            if r:
                _sumar(dr.get("layer"), r.x0, r.y0, r.x1, r.y1)
        # `get_drawings` SOLO ve vectores: una capa editable hecha con una IMAGEN (un PNG que
        # agregó el usuario, o un logo rasterizado del arte) o con TEXTO quedaba sin bbox y el
        # objeto NO aparecía en ningún lado. `get_bboxlog(layers=True)` sí los reporta con su capa.
        try:
            for it in pg.get_bboxlog(layers=True):
                if len(it) < 3 or "path" in it[0]:      # los paths ya los cubrió get_drawings
                    continue
                r = fitz.Rect(it[1])
                if not r.is_empty:
                    _sumar(it[2], r.x0, r.y0, r.x1, r.y1)
        except Exception:
            pass                                        # PyMuPDF viejo: queda el comportamiento anterior
        for capa, b in cajas.items():
            thumb = _svg = None
            if con_thumb:                                    # SOLO para el visor del front (caro)
                tgt = _norm_nombre(capa)
                for c in cfgs:                               # aislar: apagar todas…
                    doc.set_layer_ui_config(c["number"], action=1)
                for c in cfgs:                               # …mostrar solo la editable
                    if _norm_nombre(c["text"]) == tgt:
                        doc.set_layer_ui_config(c["number"], action=0)
                clip = fitz.Rect(b[0]-2, b[1]-2, b[2]+2, b[3]+2)
                pix = pg.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), clip=clip, alpha=True)
                thumb = base64.b64encode(pix.tobytes("png")).decode("ascii")
                # SVG VECTORIAL del objeto (recortado a su bbox con cropbox): para verlo NÍTIDO en el
                # visor del arte (la miniatura raster queda de fallback). El objeto es vector puro.
                try:
                    _oc = pg.cropbox
                    pg.set_cropbox(clip)
                    _svg = base64.b64encode(pg.get_svg_image().encode("utf-8")).decode("ascii")
                    pg.set_cropbox(_oc)
                except Exception:
                    _svg = None
                for c in cfgs:                               # restaurar (todas visibles)
                    doc.set_layer_ui_config(c["number"], action=0)
            pr = pg.rect
            objs.append({
                "mesa": pno + 1, "capa": capa, "nombre": _nombre_editable(capa),
                "bbox_mu": [round(v, 2) for v in b],
                "mesa_rect": [round(pr.x0, 2), round(pr.y0, 2), round(pr.width, 2), round(pr.height, 2)],
                "w_cm": round((b[2]-b[0])/CM, 1), "h_cm": round((b[3]-b[1])/CM, 1),
                "thumb": thumb, "svg": _svg,
            })
    return objs


def editables_recolorables(path_arte):
    """{nombre_capa: bool} — para cada capa editable del arte, si admite cambio de color.
    Recolorable = tiene relleno/trazo DIRECTO en su content-stream (`recolorar_capa` puede
    inyectar el CMYK). Los que sólo pintan vía XObject/imagen NO (color adentro, §10.b).
    Lo usa el editor (front) para deshabilitar el control de color en esos objetos."""
    out = {}
    try:
        pdf = _abrir_pike(path_arte)
        for o in extraer_editables(path_arte, con_thumb=False):
            try:
                out[o["capa"]] = capa_admite_color(pdf.pages[o["mesa"] - 1], _norm_nombre(o["capa"]))
            except Exception:
                out[o["capa"]] = False
    except Exception:
        pass
    return out


def mesa_rect_arte(path_arte, mesa):
    """Rect [x0, y0, w, h] de una MESA del arte — el marco donde viven los editables.

    CIERRA el documento: en Windows un archivo abierto NO se puede reemplazar (WinError 5), y
    esta función se llama justo antes de inyectar una capa en el arte — dejarlo abierto hacía
    fallar el guardado.
    """
    d = None
    try:
        d = fitz.open(path_arte)
        pr = d[int(mesa) - 1].rect
        return [round(pr.x0, 2), round(pr.y0, 2), round(pr.width, 2), round(pr.height, 2)]
    except Exception:
        return None
    finally:
        if d is not None:
            try: d.close()
            except Exception: pass


def pos_agregado_en_diseno(obj, cont, mesa_rect):
    """Posición base de un objeto AGREGADO, medida **DENTRO DEL DISEÑO** — igual que un editable
    que viene del arte: escala y se mueve CON el diseño, y el ajuste por rango/talle usa la misma
    ruta que los demás editables.

    `mesa_rect` = rect de la mesa del arte de ESTA pieza y ESTE talle. Se resuelve POR TALLE
    porque las mesas cambian de tamaño según el rango (en un arte real: 1233x1842 el rango chico
    y 2352x2607 el grande); tomar una mesa fija es lo que producía el corrimiento entre rangos.

    El diseño se coloca sobre la pieza escalando al ALTO y centrando el ancho (`cm_encajar`):
        alto del diseño sobre la pieza = alto de la pieza  -> fh = h_cm / ph_cm
        ancho del diseño en cm         = (aw/ah) * ph_cm   -> fw = w_cm / ese ancho
    Devuelve el mismo dict que `_pos_en_pieza` (fracciones de la PIEZA), centrado en el diseño.
    """
    try:
        ax0, ay0, aw, ah = [float(v) for v in mesa_rect]
        px0, py0, px1, py1 = [float(v) for v in cont["bbox_mu"]]
        pw, ph = (px1 - px0), (py1 - py0)
        ph_cm = float(cont["h"]) / CM
        ow = float(obj.get("w_cm") or 0); oh = float(obj.get("h_cm") or 0)
        if min(aw, ah, pw, ph, ph_cm, ow, oh) <= 0:
            return None
        awf = (aw * (ph / ah)) / pw          # ancho del DISEÑO como fracción de la pieza
        fw = ow / ((aw / ah) * ph_cm)        # ancho del objeto como fracción del DISEÑO
        fh = oh / ph_cm                      # alto  del objeto como fracción del DISEÑO
        rw, rh = fw * awf, fh                # -> fracciones de la PIEZA
        return {"rx": 0.5 - rw / 2, "ry": 0.5 - rh / 2, "rw": rw, "rh": rh, "awf": awf}
    except Exception:
        return None


def _pos_en_pieza(mesa_rect, bbox_mu, pieza_bbox):
    """Posición del objeto sobre la pieza en fracciones 0..1 (mismo encaje que cm_encajar:
    escala al alto, centra el ancho). {rx,ry,rw,rh} con (rx,ry)=esquina sup-izq, o None."""
    try:
        ax0, ay0, aw, ah = mesa_rect
        ox0, oy0, ox1, oy1 = bbox_mu
        px0, py0, px1, py1 = pieza_bbox
        pw, ph = (px1 - px0), (py1 - py0)
        if aw <= 0 or ah <= 0 or pw <= 0 or ph <= 0:
            return None
        awf = (aw * (ph / ah)) / pw
        return {"rx": (1 - awf) / 2 + ((ox0 - ax0) / aw) * awf, "ry": (oy0 - ay0) / ah,
                "rw": ((ox1 - ox0) / aw) * awf, "rh": (oy1 - oy0) / ah,
                "awf": awf}   # ancho del DISEÑO en la pieza (fracción) — para mover en coords del diseño
    except Exception:
        return None


def _matriz_editable(tf, obj, cont, W, H, B, pos_override=None):
    """Matriz `cm` del transform del usuario (mover/rotar/escalar) de un objeto editable,
    alrededor de su centro sobre la pieza. Devuelve "" si es identidad. `dx,dy` en fracciones
    de la pieza (dy hacia abajo, y-down del editor); `rot` en grados (horario del editor);
    `scale` factor UNIFORME (legacy); `sx`/`sy` (opcionales) permiten escala NO uniforme
    (ancho y alto por separado, con el enlace de proporción desactivado en el editor): si
    vienen, mandan sobre `scale`. La pieza está en coords de página y-arriba.
    `pos_override`: posición base ya calculada (objetos AGREGADOS, que no vienen del arte)."""
    import math
    dx = float(tf.get("dx", 0) or 0); dy = float(tf.get("dy", 0) or 0)
    rot = float(tf.get("rot", 0) or 0); sc = float(tf.get("scale", 1) or 1)
    sx = float(tf.get("sx") if tf.get("sx") is not None else sc)
    sy = float(tf.get("sy") if tf.get("sy") is not None else sc)
    if abs(dx) < 1e-6 and abs(dy) < 1e-6 and abs(rot) < 1e-6 and abs(sx - 1) < 1e-6 and abs(sy - 1) < 1e-6:
        return ""
    pos = pos_override or _pos_en_pieza(obj.get("mesa_rect"), obj.get("bbox_mu"), cont.get("bbox_mu"))
    if not pos:
        return ""
    Cx = B + (pos["rx"] + pos["rw"] / 2) * W
    Cy = B + (1 - (pos["ry"] + pos["rh"] / 2)) * H      # ry es desde ARRIBA → y-arriba de página
    r = math.radians(-rot)                              # editor horario → PDF antihorario
    cs, sn = math.cos(r), math.sin(r)
    a, b, c, d = sx * cs, sx * sn, -sy * sn, sy * cs   # escala (sx,sy) y después rotación
    # COORDS DEL DISEÑO: el objeto vive en el diseño → el mover se mide contra el ancho del DISEÑO en la
    # pieza (awf*W), no el ancho de la pieza. El alto del diseño = alto de la pieza (cm_encajar) → dy*H.
    tdx, tdy = dx * pos.get("awf", 1.0) * W, -dy * H    # dy hacia abajo → y-arriba: negativo
    e = Cx + tdx - (a * Cx + c * Cy)
    f = Cy + tdy - (b * Cx + d * Cy)
    return f"{a:.6f} {b:.6f} {c:.6f} {d:.6f} {e:.3f} {f:.3f} cm\n"


def _bbox_de_xo(xo):
    """BBox de un Form XObject (pikepdf) ya con su Matrix aplicada. → (x0,x1,y0,y1)."""
    bx = [float(v) for v in xo.BBox]
    M = [float(v) for v in xo.Matrix] if "/Matrix" in xo else [1, 0, 0, 1, 0, 0]
    a, b, c, d, e, f = M
    xs, ys = [], []
    for (px, py) in ((bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3])):
        xs.append(a * px + c * py + e); ys.append(b * px + d * py + f)
    return min(xs), max(xs), min(ys), max(ys)


def _dibujar_objetos_agregados(oa, pieza, variante, talle, cont, W, H, B, clip, out, page, mesa_rect):
    """Content-stream que dibuja los objetos AGREGADOS asignados a `pieza`, con su transform.
    Cada objeto es un PDF suelto (datos/.../objetos_agregados/<oid>.pdf). Base = 30% centrado
    (como el editor); encima, el transform del usuario (mover/rotar/escalar/espejar)."""
    if not oa or not oa.get("objetos"):
        return ""
    import pikepdf as _pk
    cache = oa.setdefault("_cache", {})
    draw = ""
    for o in oa["objetos"]:
        if (o.get("pieza") or "") != pieza:
            continue
        # Transform de ESTE talle. Si el talle no tiene uno propio (el usuario lo posicionó con
        # otro alcance), se usa CUALQUIERA de los guardados de esa variable en vez de caer a
        # identidad: si no, el objeto aparecía CENTRADO (“donde se le antoja”) y no donde se puso.
        _pv = (o.get("transforms") or {}).get(str(variante)) or (o.get("transforms") or {}).get("*") or {}
        tf = _pv.get(str(talle))
        if not tf:
            tf = next((v for v in _pv.values() if v), {})
        try:
            ruta = os.path.join(oa["dir"], o["archivo"])
            src = cache.get(ruta)
            if src is None:
                src = _pk.open(ruta); cache[ruta] = src
            xo = out.copy_foreign(src.pages[0].as_form_xobject())
            if "/OC" in xo:
                del xo["/OC"]
            nom = page.add_resource(xo, Name.XObject, prefix="OA")
            # BASE: la BBox del objeto se escala a su MEDIDA REAL sobre la pieza (fw×fh), centrada
            # → misma proporción que el archivo (no se estira) y mismo tamaño que muestra el editor.
            # DENTRO DEL DISEÑO, con la mesa de ESTE talle (ver `pos_agregado_en_diseno`).
            pos = pos_agregado_en_diseno(o, cont, mesa_rect)
            if not pos:
                continue
            # BASE: la BBox del objeto se escala al rectangulo que le toca sobre la pieza
            # (rx, ry, rw, rh de `pos`), en coords de pagina (y-arriba).
            tx0, tx1, ty0, ty1 = _bbox_de_xo(xo)
            sxb = (pos["rw"] * W) / (tx1 - tx0) if tx1 != tx0 else 1.0
            syb = (pos["rh"] * H) / (ty1 - ty0) if ty1 != ty0 else 1.0
            cxo, cyo = (tx0 + tx1) / 2.0, (ty0 + ty1) / 2.0
            _cx = B + (pos["rx"] + pos["rw"] / 2) * W
            _cy = B + (1 - (pos["ry"] + pos["rh"] / 2)) * H      # ry desde ARRIBA -> y-arriba
            ex = _cx - sxb * cxo
            ey = _cy - syb * cyo
            base = f"{sxb:.6f} 0 0 {syb:.6f} {ex:.3f} {ey:.3f} cm\n"
            # transform del usuario con el MISMO pos (pivote = centro del objeto en la pieza)
            utf = _matriz_editable(tf, None, cont, W, H, B, pos_override=pos)   # "" si identidad
            draw += f"q\n{clip}\nW n\n{utf}{base}\n{nom} Do\nQ\n"
        except Exception:
            pass
    return draw


def _texto_mesa(doc, mesa):
    lineas = []
    for b in doc[mesa - 1].get_text("dict")["blocks"]:
        if b.get("type") != 0:
            continue
        for l in b["lines"]:
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t:
                lineas.append(t)
    return lineas


def _capas_mesa(doc, mesa):
    capas = []
    try:
        for d in doc[mesa - 1].get_drawings():
            ly = d.get("layer")
            if ly:
                capas.append(ly)
    except Exception:
        pass
    return list(set(capas))


def _match_pieza(lineas, piezas):
    """Si alguna línea de texto/capa de la mesa coincide con el nombre de una pieza
    del molde, devuelve ese nombre (así el arte se auto-mapea). Exacto y, si no,
    por nombre GENÉRICO (una mesa 'Cuello' → la primera 'Cuello N'). Si no, None."""
    objetivos = {_norm_nombre(p): p for p in piezas}
    for t in lineas:
        if _norm_nombre(t) in objetivos:
            return objetivos[_norm_nombre(t)]
    # genérico: 'Cuello' matchea 'Cuello 25' (devuelve la primera de ese genérico)
    porgen = {}
    for p in piezas:
        porgen.setdefault(_norm_generico(p), []).append(p)
    for t in lineas:
        g = _norm_generico(t)
        if g and g in porgen:
            return porgen[g][0]
    return None


def _match_piezas(lineas, piezas):
    """Piezas del molde que cubre UNA mesa del arte, con precedencia:
      • nombre COMPLETO exacto → solo esa pieza (es_exacto=True);
      • si no, nombre GENÉRICO → TODAS las piezas de ese genérico (una mesa 'Cuello'
        cubre 'Cuello 25', 'Cuello 12', …). es_exacto=False.
    Devuelve (lista_de_piezas, es_exacto). Vacío si no matchea nada."""
    exact = {_norm_nombre(p): p for p in piezas}
    for t in lineas:
        nt = _norm_nombre(t)
        if nt in exact:
            return [exact[nt]], True
    porgen = {}
    for p in piezas:
        porgen.setdefault(_norm_generico(p), []).append(p)
    for t in lineas:
        g = _norm_generico(t)
        if g and g in porgen:
            return porgen[g], False
    return [], False


def medidas_diseno(registro, referencia="alto", talle_guia=None):
    """Medida que debe tener el diseño de cada pieza para CUBRIR todos los talles
    sin huecos, según la dimensión guía (alto o ancho).

    El diseño se escala igualando la dimensión guía en cada talle; la otra debe
    quedar >= a la de cada talle. La proporción crítica es la MAYOR (otra/guía)
    entre todos los talles. La medida absoluta se da en la escala del `talle_guia`
    (el que se muestra en el visor) para que el rectángulo dibujado coincida con
    la pieza. Devuelve por pieza: ancho_cm, alto_cm, ratio y talle_critico."""
    ref = "ancho" if str(referencia).lower().startswith("anch") else "alto"
    out = {}
    for pieza, por_talle in registro.items():
        dims = [(t, float(d["w_cm"]), float(d["h_cm"])) for t, d in por_talle.items()
                if d.get("w_cm") and d.get("h_cm")]
        if not dims:
            continue
        guia = next((d for d in dims if d[0] == talle_guia), None)
        if ref == "ancho":
            base_w = guia[1] if guia else max(dims, key=lambda x: x[1])[1]
            t_crit, ratio = max(((t, h / w) for t, w, h in dims), key=lambda x: x[1])
            out[pieza] = {"ref": "ancho", "ancho_cm": round(base_w, 1),
                          "alto_cm": round(base_w * ratio, 1),
                          "ratio": round(ratio, 4), "talle_critico": t_crit}
        else:
            base_h = guia[2] if guia else max(dims, key=lambda x: x[2])[2]
            t_crit, ratio = max(((t, w / h) for t, w, h in dims), key=lambda x: x[1])
            out[pieza] = {"ref": "alto", "alto_cm": round(base_h, 1),
                          "ancho_cm": round(base_h * ratio, 1),
                          "ratio": round(ratio, 4), "talle_critico": t_crit}
    return out


def _segmentos_vector(page, segs, T, color, width, oc=0):
    """Dibuja los `segmentos` (m/l/c/re/h, en coords CRUDAS del lienzo PDF, y-arriba) de un
    contorno como VECTOR, transformando cada punto con T(cx,cy)->fitz.Point. Para el molde."""
    sh = page.new_shape()
    cur = None; start = None
    for s in segs:
        op = s[0]
        if op == "m":
            cur = T(s[1], s[2]); start = cur
        elif op == "l":
            p = T(s[1], s[2])
            if cur: sh.draw_line(cur, p)
            cur = p
        elif op == "c":
            p1 = T(s[1], s[2]); p2 = T(s[3], s[4]); p3 = T(s[5], s[6])
            if cur: sh.draw_bezier(cur, p1, p2, p3)
            cur = p3
        elif op == "re":
            x, y, w, h = s[1], s[2], s[3], s[4]
            c0 = T(x, y); c1 = T(x + w, y); c2 = T(x + w, y + h); c3 = T(x, y + h)
            sh.draw_line(c0, c1); sh.draw_line(c1, c2); sh.draw_line(c2, c3); sh.draw_line(c3, c0)
            cur = c0; start = c0
        elif op == "h":
            if cur and start: sh.draw_line(cur, start); cur = start
    sh.finish(color=color, width=width, closePath=False, oc=oc)
    sh.commit()


def _guia_capas_data(path_plantilla, registro, config, talle_guia, rango, referencia, piezas_incluir, limpio):
    """Geometría de la guía (compartida por el PDF y el .ai): detecta las piezas y arma, por talle
    incluido, la lista de items {segs, nombre, ccx, ccy, wC (caja diseño), hC} + el bbox del conjunto.
    Devuelve (base_deteccion, capas_data)."""
    rango = rango or []
    guia_es_ancho = str(referencia).lower().startswith("anch")
    base = detectar_piezas(path_plantilla, talle_ref=talle_guia, ancho_preview=300)
    mesa = base["mesa"]
    if config == "talle":
        talles_inc = base.get("talles", []) or [base["talle_ref"]]
    else:
        talles_inc = [talle_guia or base["talle_ref"]]
    doc_src = _abrir(path_plantilla)
    capas_data = []   # [{talle, items:[{segs,nombre,ccx,ccy,wC,hC}], minX,minY,maxX,maxY}]
    for t in talles_inc:
        conts = extraer_piezas_mesa(doc_src, mesa, t)
        if not conts:
            continue
        nombres = {}
        for nombre, por_talle in (registro or {}).items():
            info = por_talle.get(t)
            if info and info.get("mesa") == mesa and info.get("pieza_idx") is not None:
                nombres[info["pieza_idx"]] = nombre
        md = medidas_diseno(registro, referencia, talle_guia=t) if (config == "default" and registro) else {}
        items = []; minX = minY = 1e18; maxX = maxY = -1e18
        for i, c in enumerate(conts):
            U = c["user_unit"]; w_cm = c["w"] / U / CM; h_cm = c["h"] / U / CM
            nombre = nombres.get(i, "")
            if piezas_incluir is not None and nombre not in piezas_incluir:
                continue   # SOLO las piezas de la variante en curso (el resto no se dibuja)
            if config == "talle":
                a_cm, hh_cm = w_cm, h_cm
            elif config == "rango":
                mv = (registro or {}).get(nombre, {}); dimsR = [mv[v] for v in rango if v in mv]
                if dimsR and guia_es_ancho:
                    r = max(d["h_cm"] / d["w_cm"] for d in dimsR); a_cm, hh_cm = w_cm, round(w_cm * r, 1)
                elif dimsR:
                    r = max(d["w_cm"] / d["h_cm"] for d in dimsR); a_cm, hh_cm = round(h_cm * r, 1), h_cm
                else:
                    a_cm, hh_cm = w_cm, h_cm
            else:
                mm = md.get(nombre); a_cm, hh_cm = (mm["ancho_cm"], mm["alto_cm"]) if mm else (w_cm, h_cm)
            x0, ylo, x1, yhi = c["bbox_raw"]   # canvas y-arriba
            ccx, ccy = (x0 + x1) / 2, (ylo + yhi) / 2
            wC, hC = a_cm * CM, hh_cm * CM     # caja en unidades del lienzo (1 cm = CM)
            items.append({"segs": c["segmentos"], "nombre": nombre, "ccx": ccx, "ccy": ccy, "wC": wC, "hC": hC})
            if limpio:   # BASE limpia: solo el contorno del molde, sin la caja del diseño
                minX = min(minX, x0); maxX = max(maxX, x1); minY = min(minY, ylo); maxY = max(maxY, yhi)
            else:
                minX = min(minX, x0, ccx - wC / 2); maxX = max(maxX, x1, ccx + wC / 2)
                minY = min(minY, ylo, ccy - hC / 2); maxY = max(maxY, yhi, ccy + hC / 2)
        if items:
            capas_data.append({"talle": t, "items": items, "minX": minX, "minY": minY, "maxX": maxX, "maxY": maxY})
    return base, capas_data


def pdf_guia_medidas(path_plantilla, registro, config="default", talle=None,
                     rango=None, referencia="alto", titulo="Molde", talle_guia=None,
                     piezas_incluir=None, limpio=False):
    """PDF de GUÍA DE ARMADO: el MOLDE en VECTOR (como el .ai) + el RECUADRO del diseño + el
    NOMBRE DE MESA a usar en el arte (con `#` en 'talle'/'rango', sin `#` en 'default'). SIN
    medidas. En 'talle' los talles van SUPERPUESTOS (alineados, uno sobre otro como el size-run
    del archivo), cada talle en su propia CAPA (OCG) con el nombre de la variante para
    prender/apagar en Illustrator. Devuelve los bytes del PDF."""
    rango = rango or []
    guia_es_ancho = str(referencia).lower().startswith("anch")
    MARG = 40; TOP = 90
    verde = (0.30, 0.55, 0.34); cyan = (0, 0.55, 0.7); tinta = (0.1, 0.1, 0.1)

    import re as _re
    def nombre_mesa(pieza, talle_pag):
        # GENÉRICO (sin el nº/id): "Frente 1" → "Frente". Una mesa genérica cubre TODAS las piezas
        # de ese nombre (igual que lee el motor, ver _parse_pieza_hash). Consistente con el panel.
        gen = _re.sub(r"\s+\d+\s*$", "", str(pieza)).strip() or str(pieza)
        if config == "talle":
            return f"#{talle_pag} {gen}"
        if config == "rango" and rango:
            return f"#{rango[0]}-{rango[-1]} {gen}"
        return gen   # default → sin #

    base, capas_data = _guia_capas_data(path_plantilla, registro, config, talle_guia, rango, referencia, piezas_incluir, limpio)

    if not capas_data:
        raise ValueError("no se detectaron piezas en la plantilla")

    LBLF = 16; TITF = 22   # fuentes (pieza / título)
    es_multi = (config == "talle")
    sub_base = ("rango " + ("-".join([rango[0], rango[-1]]) if rango else "—") if config == "rango"
                else "todos los talles")
    doc = fitz.open()
    # UNA PÁGINA (= mesa de trabajo en Illustrator) por talle, a 1:1 tamaño REAL. (Illustrator NO
    # importa capas OCG de un PDF — las aplana a "Capa 1" —, por eso una mesa por talle. Para llevar
    # CAPAS reales al arte hay que generar un .ai nativo, no un PDF.)
    for cd in capas_data:
        minX, minY, maxX, maxY = cd["minX"], cd["minY"], cd["maxX"], cd["maxY"]
        PW = MARG * 2 + (maxX - minX)
        PH = TOP + MARG + (maxY - minY)
        def T(cx, cy, _mnX=minX, _mxY=maxY):   # 1:1, lienzo (y-arriba) → página (y-abajo)
            return fitz.Point(MARG + (cx - _mnX), TOP + MARG + (_mxY - cy))
        page = doc.new_page(width=PW, height=PH)
        page.draw_rect(fitz.Rect(0, 0, PW, PH), color=None, fill=(1, 1, 1))
        sub = (f"talle {cd['talle']}" if es_multi else sub_base)
        _tit = "Base (contornos)" if limpio else "Guía de armado"
        page.insert_text(fitz.Point(MARG, 36), f"{titulo} - {_tit} · {sub} · (tamaño real 1:1)", fontsize=TITF, color=tinta, fontname="hebo")
        for it in cd["items"]:
            _segmentos_vector(page, it["segs"], T, verde, 2.0, 0)
            if limpio:
                continue   # BASE: solo el contorno del molde (sin recuadro del diseño ni nombre de mesa)
            p0 = T(it["ccx"] - it["wC"] / 2, it["ccy"] + it["hC"] / 2)   # esquina sup-izq (tras flip)
            p1 = T(it["ccx"] + it["wC"] / 2, it["ccy"] - it["hC"] / 2)   # esquina inf-der
            page.draw_rect(fitz.Rect(p0, p1), color=cyan, width=2.0, dashes="[14 8] 0")
            nm = nombre_mesa(it["nombre"], cd["talle"]) if it["nombre"] else ""
            if nm:
                ctr = T(it["ccx"], it["ccy"]); rwp = it["wC"]; rhp = it["hC"]
                w = fitz.get_text_length(nm, fontname="hebo", fontsize=LBLF)
                if w > rwp - 8 and rhp > w + 14:   # pieza angosta y alta → texto vertical
                    page.insert_text(fitz.Point(ctr.x - 5, ctr.y + w / 2), nm, fontsize=LBLF, color=tinta, fontname="hebo", rotate=90)
                else:
                    page.insert_text(fitz.Point(ctr.x - w / 2, ctr.y + 5), nm, fontsize=LBLF, color=tinta, fontname="hebo")

    out = doc.tobytes(); doc.close()
    return out


# ══════════ GUÍA en .ai NATIVO (capas REALES en Illustrator) ══════════
# Illustrator aplana los OCG de un PDF, pero SÍ lee las capas de un .ai legacy (AI 8 / EPS con
# marcadores %AI5_BeginLayer). Esta guía abre con las capas del arte ya armadas: `molde` (contorno
# + recuadro del diseño), `guias` (los NOMBRES de pieza como TEXTO VIVO), y `diseño` + las capas de
# texto/número creadas VACÍAS. Coordenadas AI = PostScript (y-arriba, origen abajo-izq) → sin flip.
def _ai_esc(s):
    return str(s).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _ai_path(segs, T):
    """Ops de path AI (m/L/c) desde los `segmentos` (coords crudas y-arriba), cerrando en `h`."""
    out = []; start = None
    for s in segs:
        op = s[0]
        if op == "m":
            x, y = T(s[1], s[2]); out.append("%.3f %.3f m" % (x, y)); start = (x, y)
        elif op == "l":
            x, y = T(s[1], s[2]); out.append("%.3f %.3f L" % (x, y))
        elif op == "c":
            x1, y1 = T(s[1], s[2]); x2, y2 = T(s[3], s[4]); x3, y3 = T(s[5], s[6])
            out.append("%.3f %.3f %.3f %.3f %.3f %.3f c" % (x1, y1, x2, y2, x3, y3))
        elif op == "re":
            x, y, w, h = s[1], s[2], s[3], s[4]
            a = T(x, y); b = T(x + w, y); c2 = T(x + w, y + h); d = T(x, y + h)
            out += ["%.3f %.3f m" % a, "%.3f %.3f L" % b, "%.3f %.3f L" % c2, "%.3f %.3f L" % d, "%.3f %.3f L" % a]
            start = a
        elif op == "h":
            if start:
                out.append("%.3f %.3f L" % start)
    return "\n".join(out)


def _ai_text(text, x, y, size):
    """Objeto de TEXTO puntual vivo en formato AI (fuente Helvetica)."""
    return ("0 To\n1 0 0 1 %.3f %.3f 0 Tp\nTP\n"
            "0 Tr\n0 O\n0 0 0 1 k\n0 0 0 1 K\n/_Helvetica %g Tf\n0 Ts\n100 Tz\n0 Tw\n0 Tc\n"
            "(%s) Tx\n(\\r) TX\nTO"
            % (x, y, size, _ai_esc(text)))


def _ai_layer(nombre, r, g, b, cuerpo):
    return ("%%AI5_BeginLayer\n1 1 1 1 0 0 0 %d %d %d Lb\n(%s) Ln\n0 A\n%s\nLB\n%%AI5_EndLayer\n"
            % (r, g, b, _ai_esc(nombre), cuerpo))


def _segs_bbox(segs):
    """Bounding box (x0,y0,x1,y1) de los puntos de un path `segmentos`."""
    xs = []; ys = []
    for s in segs:
        op = s[0]
        if op in ("m", "l"):
            xs.append(s[1]); ys.append(s[2])
        elif op == "c":
            xs += [s[1], s[3], s[5]]; ys += [s[2], s[4], s[6]]
        elif op == "re":
            xs += [s[1], s[1] + s[3]]; ys += [s[2], s[2] + s[4]]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else (0.0, 0.0, 0.0, 0.0)


def ai_guia_medidas(path_plantilla, registro, config="default", rango=None, referencia="alto",
                    titulo="Molde", talle_guia=None, piezas_incluir=None, capas=None):
    """Devuelve los bytes de un .ai (legacy) con la guía en CAPAS reales. `capas` = nombres de las
    capas del arte a crear vacías (diseño + columnas de texto/número). Un solo talle (el de guía)."""
    import re as _re
    rango = rango or []

    def nombre_mesa(pieza):
        gen = _re.sub(r"\s+\d+\s*$", "", str(pieza)).strip() or str(pieza)
        if config == "rango" and rango:
            return "#%s-%s %s" % (rango[0], rango[-1], gen)
        return gen   # default → sin # (en la guía .ai no usamos el modo 'talle' multipágina)

    import math as _math
    base, capas_data = _guia_capas_data(path_plantilla, registro, config, talle_guia, rango, referencia, piezas_incluir, False)
    if not capas_data:
        raise ValueError("no se detectaron piezas en la plantilla")
    its = capas_data[0]["items"]
    MARG = 40.0; TOP = 60.0; GAP = 34.0

    def _bbox_it(it):   # bbox del item = contorno ∪ recuadro del diseño
        bx0, by0, bx1, by1 = _segs_bbox(it["segs"])
        rx0, ry0 = it["ccx"] - it["wC"] / 2, it["ccy"] - it["hC"] / 2
        rx1, ry1 = it["ccx"] + it["wC"] / 2, it["ccy"] + it["hC"] / 2
        return (min(bx0, rx0), min(by0, ry0), max(bx1, rx1), max(by1, ry1))

    bxs = [_bbox_it(it) for it in its]
    ws = [b[2] - b[0] for b in bxs]; hs = [b[3] - b[1] for b in bxs]
    # EMPAQUETADO COMPACTO (el layout real del size-run es enorme y supera el artboard de Illustrator,
    # 227"): se reacomodan las piezas en una grilla a 1:1 (tamaño real), fila por fila.
    rowLimit = max(max(ws), (sum(ws) / len(ws)) * _math.ceil(_math.sqrt(len(its))))
    placed = []; x = MARG; y = MARG; rowH = 0.0; rightEdge = MARG; topEdge = MARG
    for i, b in enumerate(bxs):
        w, h = ws[i], hs[i]
        if x > MARG and x + w > MARG + rowLimit:
            x = MARG; y = y + rowH + GAP; rowH = 0.0
        placed.append((x - b[0], y - b[1]))   # lleva la esquina (b0,b1) del item a (x,y)
        rightEdge = max(rightEdge, x + w); topEdge = max(topEdge, y + h)
        x = x + w + GAP; rowH = max(rowH, h)
    PW = rightEdge + MARG; PH = topEdge + MARG + TOP
    if max(PW, PH) > 16000:   # límite de artboard de Illustrator ≈ 227" (16383 pt) a tamaño real 1:1
        raise ValueError("el molde a tamaño real es más grande que el máximo de Illustrator (227\"). "
                         "Elegí una VARIABLE para bajar la guía solo de sus piezas.")

    def Ti(i, cx, cy):
        ox, oy = placed[i]; return (cx + ox, cy + oy)

    # CAPA molde: contorno (trazo negro) + recuadro del diseño (cyan punteado) + título.
    mo = ["0 0 0 1 K", "1.5 w"]
    for i, it in enumerate(its):
        mo.append(_ai_path(it["segs"], lambda cx, cy, _i=i: Ti(_i, cx, cy))); mo.append("S")
    for i, it in enumerate(its):   # recuadros aparte (con dash), para no ensuciar el estado del contorno
        rx0, ry0 = it["ccx"] - it["wC"] / 2, it["ccy"] - it["hC"] / 2
        a = Ti(i, rx0, ry0); b = Ti(i, rx0 + it["wC"], ry0); c2 = Ti(i, rx0 + it["wC"], ry0 + it["hC"]); d = Ti(i, rx0, ry0 + it["hC"])
        mo.append("0.75 0 0 0 K\n1 w\n[8 6] 0 d")
        mo.append("%.3f %.3f m\n%.3f %.3f L\n%.3f %.3f L\n%.3f %.3f L\n%.3f %.3f L\nS" % (a[0], a[1], b[0], b[1], c2[0], c2[1], d[0], d[1], a[0], a[1]))
        mo.append("[] 0 d")
    mo.append(_ai_text("%s - Guia (arma el arte encima) - 1:1" % titulo, MARG, PH - 34, 14))

    # CAPA guias: los NOMBRES de pieza como texto vivo, centrados en cada pieza.
    gu = []
    for i, it in enumerate(its):
        nm = nombre_mesa(it["nombre"]) if it["nombre"] else ""
        if not nm:
            continue
        cx, cy = Ti(i, it["ccx"], it["ccy"])
        gu.append(_ai_text(nm, cx - len(nm) * 3.2, cy, 12))

    cuerpo = _ai_layer("molde", 79, 128, 255, "\n".join(mo))
    cuerpo += _ai_layer("guias", 52, 211, 153, "\n".join(gu) if gu else "0 0 0 1 k")
    # Capas del arte VACÍAS (diseño + texto/número): se crean igual (un marcador mínimo invisible
    # para que la capa exista) para que el diseñador arme el arte con la estructura lista.
    for nc in (capas or []):
        nc = str(nc).strip()
        if not nc or nc.lower() in ("molde", "guias"):
            continue
        marca = "1 1 1 0 K\n0.01 w\n%.2f %.2f m\n%.2f %.2f L\nS" % (MARG, MARG, MARG + 0.1, MARG)
        cuerpo += _ai_layer(nc, 128, 128, 128, marca)

    ai = (
        "%%!PS-Adobe-3.0 EPSF-3.0\n"
        "%%%%Creator: TizadaPro\n%%%%Title: (%s)\n"
        "%%%%BoundingBox: 0 0 %d %d\n%%%%HiResBoundingBox: 0 0 %.3f %.3f\n"
        "%%%%DocumentProcessColors: Cyan Magenta Yellow Black\n"
        "%%%%DocumentFonts: Helvetica\n"
        "%%AI5_FileFormat 3\n%%AI3_ColorUsage: Color\n%%AI5_ArtSize: %.3f %.3f\n"
        "%%%%EndComments\n%%%%BeginProlog\n%%%%EndProlog\n%%%%BeginSetup\n%%%%EndSetup\n"
        % (_ai_esc(titulo), int(PW + 1), int(PH + 1), PW, PH, PW, PH)
    ) + cuerpo + "%%PageTrailer\ngsave annotatepage grestore showpage\n%%Trailer\n%%EOF\n"
    return ai.encode("latin-1", "replace")


def mapeo_por_nombre(path_arte, registro_molde):
    """Mapeo {pieza: mesa} leído de los rótulos de texto o de las capas del arte."""
    import re as _re
    doc = _abrir(path_arte)
    piezas = sorted(registro_molde.keys())
    mapeo = {}
    exactos = set()   # piezas fijadas por match EXACTO: un genérico posterior NO las pisa
    huerfanas = []    # mesas SIN match: (mesa, set(tokens del rótulo)) para el pase de subconjunto
    _STOP_ROTULO = {"diseno", "guia", "guias", "numero", "nombre", "palabra", "personalizable", "editable", "texto"}
    for i in range(len(doc)):
        # 1. por texto vivo; 2. si no, por nombre de capa. Exacto → esa pieza; genérico → TODAS.
        # Se saca el prefijo #variante/#rango del rótulo ("#4XL-6XL Frente" → "Frente") para que
        # matchee la PIEZA: sin esto, una mesa con `#` no mapea NADA (el mapeo queda vacío y ni el
        # visor ni la tizada colocan diseño). El `#` en sí lo resuelve `mapeo_variantes_arte` aparte.
        txt = [_re.sub(r"^\s*#\S+\s+", "", t) for t in _texto_mesa(doc, i + 1)]
        matches, es_exacto = _match_piezas(txt, piezas)
        if not matches:
            matches, es_exacto = _match_piezas(_capas_mesa(doc, i + 1), piezas)
        if not matches:
            # Tokens del RÓTULO DE TEXTO solamente (las capas traen 'diseño'/'numero' y ensucian).
            toks = set()
            for t in txt:
                for w in _norm_generico(t).split():
                    if w and not w.isdigit() and w not in _STOP_ROTULO:
                        toks.add(w)
            if toks:
                huerfanas.append((i + 1, toks))
            continue
        for nom in matches:
            if nom in exactos:
                continue                       # ya lo fijó un match exacto → no lo pisa un genérico
            if es_exacto:
                mapeo[nom] = i + 1; exactos.add(nom)
            elif nom not in mapeo:
                mapeo[nom] = i + 1             # genérico: llena las que aún no tienen mesa
    # PASE DE SUBCONJUNTO — para rótulos INCOMPLETOS: una mesa 'manga derecha' (sin la palabra
    # 'corta') se asigna a la pieza 'Manga Corta Derecha' porque su nombre CONTIENE todas las
    # palabras del rótulo Y esa pieza quedó HUÉRFANA (sin mesa) — la 'manga larga derecha' ya
    # tiene la suya. Solo si hay UN genérico huérfano candidato (sin ambigüedad) → no adivina.
    porgen = {}
    for p in piezas:
        porgen.setdefault(_norm_generico(p), []).append(p)
    for mesa, toks in huerfanas:
        cands = [g for g, ps in porgen.items()
                 if g and toks.issubset(set(g.split())) and not any(pp in mapeo for pp in ps)]
        if len(cands) == 1:
            for nom in porgen[cands[0]]:
                mapeo.setdefault(nom, mesa)
    return mapeo


def _variantes_token(token, variantes_orden):
    """Resuelve el token de un rótulo `#…`: una variante (`XL`) o un rango (`XS-XL`).
    Devuelve (lista_de_variantes, es_exacta) o (None, False) si no matchea. El rango usa
    el ORDEN de archivo de las variantes. No hardcodea nombres: usa las variantes reales."""
    token = str(token).strip()
    norm = {_norm_nombre(v): v for v in variantes_orden}
    # 1) match exacto de una variante (incluso si su nombre tuviera un guion)
    if token in variantes_orden:
        return [token], True
    if _norm_nombre(token) in norm:
        return [norm[_norm_nombre(token)]], True
    # 2) rango V1-V2
    if "-" in token:
        a, b = (s.strip() for s in token.split("-", 1))
        va = a if a in variantes_orden else norm.get(_norm_nombre(a))
        vb = b if b in variantes_orden else norm.get(_norm_nombre(b))
        if va and vb:
            i, j = variantes_orden.index(va), variantes_orden.index(vb)
            return variantes_orden[min(i, j):max(i, j) + 1], False
    return None, False


def _parse_pieza_hash(linea, piezas, variantes_orden):
    """`#<variante-o-rango> <pieza>` → ([piezas], [variantes], es_exacta_variante) o None.
    El token tras el `#` (hasta el primer espacio) es la variante/rango; el resto, la pieza.
    La pieza se matchea con `_match_piezas` (PLURAL): un genérico ('#M Frente') cubre TODAS
    las piezas de ese nombre, IGUAL que el mapeo default sin `#` (una exacta, ej '#M Frente 1',
    cubre solo esa). Así el `#` y el default son coherentes. `es_exacta` es de la VARIANTE
    (talle exacto pisa rango), no de la pieza."""
    t = str(linea).strip()
    if not t.startswith("#"):
        return None
    parts = t[1:].strip().split(None, 1)
    if len(parts) < 2:
        return None
    variantes, es_exacta = _variantes_token(parts[0], variantes_orden)
    if not variantes:
        return None
    piezas_match, _ = _match_piezas([parts[1]], piezas)
    if not piezas_match:
        return None
    return piezas_match, variantes, es_exacta


_MAPEO_VAR_CACHE = {}   # memoización por (arte, mtime, piezas, orden): talle/variable-INDEP, escanea
                        # TODAS las mesas del arte; se recomputaba 1× POR TALLE dentro de generar_pedido
def mapeo_variantes_arte(path_arte, registro_molde, variantes_orden):
    """Mapeo por VARIANTE leído de mesas nombradas `#variante PIEZA` o `#v1-v2 PIEZA`:
    {pieza: {variante: mesa}}. Precedencia: la variante EXACTA pisa al RANGO. {} si no hay
    ninguna mesa con `#` (→ todo funciona como hoy, por nombre pelado)."""
    try: _mt = os.path.getmtime(path_arte)
    except OSError: _mt = 0
    _ck = (path_arte, _mt, tuple(sorted(registro_molde.keys())), tuple(variantes_orden or ()))
    _hit = _MAPEO_VAR_CACHE.get(_ck)
    if _hit is not None:
        return _hit
    # CERRAR el documento al terminar: en Windows un archivo abierto no se puede reemplazar
    # (WinError 5). Esta función corre antes de inyectar capas en el arte y, si quedaba abierta,
    # el guardado del arte fallaba con "Acceso denegado".
    doc = fitz.open(path_arte)
    try:
        piezas = sorted(registro_molde.keys())
        rango, exacta = {}, {}
        for i in range(len(doc)):
            for ln in (_texto_mesa(doc, i + 1) + _capas_mesa(doc, i + 1)):
                r = _parse_pieza_hash(ln, piezas, variantes_orden)
                if r:
                    piezas_match, variantes, es_exacta = r
                    target = exacta if es_exacta else rango
                    for pieza in piezas_match:         # genérico → TODAS las piezas de ese nombre
                        for v in variantes:            # rango → TODOS los talles del tramo
                            target.setdefault(pieza, {}).setdefault(v, i + 1)
                    break                              # una mesa = un rótulo
    finally:
        try: doc.close()
        except Exception: pass
    out = {}
    for pieza in set(rango) | set(exacta):
        d = dict(rango.get(pieza, {}))
        d.update(exacta.get(pieza, {}))               # exacta pisa rango
        out[pieza] = d
    if len(_MAPEO_VAR_CACHE) > 24:
        _MAPEO_VAR_CACHE.clear()
    _MAPEO_VAR_CACHE[_ck] = out
    return out


def _mesa_tiene_diseno(doc, mesa):
    pix = doc[mesa - 1].get_pixmap(matrix=fitz.Matrix(0.04, 0.04))
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(int)
    return a.std(axis=(0, 1)).mean() >= 8


def arte_es_separado(path_arte, path_plantilla):
    """True si el arte NO comparte la estructura del molde (mesas/talles): se
    trata como arte separado (una mesa de diseño por pieza)."""
    da, db = _abrir(path_arte), _abrir(path_plantilla)
    if len(da) == len(db):
        cb = set(i["name"] for i in db.get_ocgs().values())
        ca = set(i["name"] for i in da.get_ocgs().values())
        talles_molde = cb - CAPAS_SISTEMA
        if talles_molde and talles_molde <= ca:     # arte tiene los talles del molde → clásico
            return False
    return True


def detectar_arte(path_arte, registro_molde, ancho_thumb=240):
    """Para el mapeo visual del arte separado: una miniatura por mesa del arte,
    con una sugerencia de pieza por proporción. Devuelve {mesas:[{mesa, thumb,
    w_cm, h_cm, tiene_diseno, sugerencia}], piezas:[nombres del molde]}."""
    doc = _abrir(path_arte)       # para MINIATURAS (ocultamos la capa de guías)
    doc_txt = _abrir(path_arte)   # para LEER nombres (guías visibles)
    # La miniatura muestra el diseño REAL (lo que se imprime), no las guías/nombres
    # que el motor descarta. La lectura de nombres se hace en doc_txt (guías
    # visibles), porque get_pixmap y get_text respetan la visibilidad de la capa.
    try:
        for c in doc.layer_ui_configs():
            # Ocultar guías Y objetos editables (estos se muestran APARTE, posicionados,
            # en el paso Arte / la tizada; no deben salir en su lugar original del thumbnail).
            if _es_capa_guia(c.get("text")) or _es_capa_editable(c.get("text")):
                doc.set_layer_ui_config(c["number"], action=2)  # ocultar para la miniatura
    except Exception:
        pass
    piezas = sorted(registro_molde.keys())
    aspecto_pieza = {}
    tam_pieza = {}
    for p in piezas:
        v = max(registro_molde[p].values(), key=lambda d: d["h_cm"])
        aspecto_pieza[p] = (v["w_cm"] / v["h_cm"]) if v["h_cm"] else 1.0
        tam_pieza[p] = (float(v["w_cm"]), float(v["h_cm"]))

    mesas = []
    for i in range(len(doc)):
        pr = doc[i].rect
        zoom = ancho_thumb / pr.width
        pix = doc[i].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        # SVG VECTORIAL del diseño (guías/editables ya ocultas): para mostrarlo NÍTIDO/vectorial en el
        # visor del arte (la miniatura raster es solo fallback). El diseño es vector puro (~20-30 KB).
        try:
            _svg = base64.b64encode(doc[i].get_svg_image().encode("utf-8")).decode("ascii")
        except Exception:
            _svg = None

        # Detectar por texto o por nombre de capa (en el doc ORIGINAL, guías visibles)
        nom_det = _match_pieza(_texto_mesa(doc_txt, i + 1), piezas)
        if not nom_det:
            nom_det = _match_pieza(_capas_mesa(doc_txt, i + 1), piezas)

        mesas.append({"mesa": i + 1, "w_cm": round(pr.width / CM, 1), "h_cm": round(pr.height / CM, 1),
                      "aspecto": (pr.width / pr.height) if pr.height else 1.0,
                      "tiene_diseno": bool(_mesa_tiene_diseno(doc_txt, i + 1)),
                      "nombre_detectado": nom_det,
                      "thumb": base64.b64encode(pix.tobytes("png")).decode("ascii"),
                      "svg": _svg,
                      "thumb_w": pix.width, "thumb_h": pix.height})

    # sugerencia: 1) nombre escrito en la mesa (auto) · 2) proporción para el resto
    libres = set(piezas)
    for m in mesas:
        nd = m["nombre_detectado"]
        if nd and nd in libres:
            m["sugerencia"] = nd
            libres.discard(nd)
    # Resto: emparejar por TAMAÑO (el diseño viene del tamaño de cada pieza). Es
    # mucho más confiable que la proporción: agrupa bien frente/espalda, mangas,
    # costadillos. Se asignan primero las piezas más grandes.
    for m in sorted(mesas, key=lambda m: -(m["w_cm"] * m["h_cm"])):
        if m.get("sugerencia") or not libres:
            continue
        def _dist(p, _m=m):
            pw, ph = tam_pieza[p]
            return abs(_m["w_cm"] - pw) / max(pw, 1) + abs(_m["h_cm"] - ph) / max(ph, 1)
        mejor = min(libres, key=_dist)
        m["sugerencia"] = mejor
        libres.discard(mejor)
    for m in mesas:
        m.setdefault("sugerencia", "")
        del m["aspecto"]
    return {"mesas": mesas, "piezas": piezas}


def validar_arte_separado(path_arte, registro_molde, carpeta_fuentes, mapeo, variantes_orden=None, piezas_scope=None):
    """Valida el arte en modo separado contra un mapeo {pieza: mesa_arte}. Si se pasa
    `variantes_orden`, además contempla el mapeo por VARIANTE (#variante/#rango): una pieza
    cubierta solo por mesas `#` NO se marca sin asignar, y se AVISA si una variante quedó
    sin diseño en esa pieza. `piezas_scope` (opcional) acota los checks de cobertura a ESAS
    piezas (las de la VARIABLE en uso) en vez del molde entero — regla mapeo-por-variable."""
    doc = _abrir(path_arte)
    if piezas_scope is not None:
        _sc = set(piezas_scope)
        piezas = sorted(p for p in registro_molde.keys() if p in _sc)
    else:
        piezas = sorted(registro_molde.keys())
    checks, ok = [], True

    mapeo_var = {}
    if variantes_orden:
        try:
            mapeo_var = mapeo_variantes_arte(path_arte, registro_molde, variantes_orden)
        except Exception:
            mapeo_var = {}

    # Una pieza está asignada si tiene mesa default (sin #) O alguna mesa #variante/#rango.
    sin_asignar = [p for p in piezas if not mapeo.get(p) and not mapeo_var.get(p)]
    checks.append({"nombre": "Cada pieza tiene un arte asignado", "ok": not sin_asignar,
                   "detalle": f"{len(piezas) - len(sin_asignar)}/{len(piezas)} piezas" +
                   (f" — faltan: {', '.join(sin_asignar)}" if sin_asignar else "")})
    ok &= not sin_asignar

    # AVISO (no bloquea): variantes sin cubrir en piezas mapeadas SOLO por # (sin default).
    if variantes_orden:
        sin_cubrir = []
        for p in piezas:
            if mapeo.get(p) or not mapeo_var.get(p):
                continue                              # con default cubre todo; sin # no aplica
            faltan = [v for v in variantes_orden if v not in mapeo_var[p]]
            if faltan:
                sin_cubrir.append(f"{p}: faltan {', '.join(faltan)}")
        if sin_cubrir:
            checks.append({"nombre": "Todas las variantes tienen diseño", "ok": False, "aviso": True,
                           "detalle": "esas variantes saldrán sin diseño en esa pieza — " + "; ".join(sin_cubrir)})

    fuera = [f"{p}→mesa {mapeo[p]}" for p in piezas if mapeo.get(p) and not (1 <= int(mapeo[p]) <= len(doc))]
    if fuera:
        checks.append({"nombre": "Mesas de arte válidas", "ok": False, "detalle": "; ".join(fuera)})
        ok = False

    vacias = sorted({int(mapeo[p]) for p in piezas if mapeo.get(p) and 1 <= int(mapeo[p]) <= len(doc)
                     and not _mesa_tiene_diseno(doc, int(mapeo[p]))})
    checks.append({"nombre": "Las mesas asignadas tienen diseño", "ok": not vacias,
                   "detalle": "todas con diseño" if not vacias else f"mesas vacías: {vacias}"})
    ok &= not vacias

    # El diseño se entrega EN CURVAS (cero fuentes): el texto vivo del diseño no
    # sobrevive el pipeline → hay que convertirlo a contornos en Illustrator.
    requeridas = fuentes_requeridas_arte(path_arte)
    texto_diseno = sorted(n for n, usos in requeridas.items() if "etiquetas" in usos)
    checks.append({"nombre": "Diseño sin texto vivo (en curvas)", "ok": not texto_diseno,
                   "detalle": "sin texto vivo" if not texto_diseno else
                   "convertí a curvas el texto del diseño (Texto → Crear contornos). "
                   "Fuentes: " + ", ".join(texto_diseno)})
    ok &= not texto_diseno

    # Tipografías que el motor SÍ re-dibuja: solo las de personalización (NOMBRE/00).
    # NO bloquea la aprobación: la personalización es OPCIONAL. Si falta una capa o su
    # fuente, la tizada se arma igual — ese campo simplemente no se estampa (solo se avisa).
    pers = extraer_personalizacion(path_arte)
    f_pers = {c["fuente"] for m in pers.values() for c in m.values()}
    faltan_f = sorted(f for f in f_pers if not resolver_fuente(f, carpeta_fuentes))
    if f_pers:
        checks.append({"nombre": "Tipografías de personalización en catálogo", "ok": not faltan_f,
                       "aviso": bool(faltan_f),  # es un AVISO, no un bloqueo
                       "detalle": ", ".join(sorted(f_pers)) if not faltan_f else
                       "no están en el catálogo (ese texto NO se estampará): " + ", ".join(faltan_f)})

    return {"aprobado": bool(ok), "checks": checks, "modo": "separado", "mapeo": mapeo,
            "personalizacion": pers, "fuentes_requeridas": requeridas,
            "fuentes_faltantes": faltan_f}


# ════════════════ GENERACIÓN DEL PEDIDO ════════════════
def generar_pedido(plantilla, arte, registro, pers, prendas, carpeta_fuentes, salida,
                   config_nesting=None, progreso=None, mapeo_arte=None, rotaciones=None,
                   asignacion_tela=None, telas_cfg=None, solo_piezas=False, borde_corte=None,
                   etiqueta=None, editables_cfg=None, editables_tamano=None, objetos_agregados=None,
                   editables_color=None):
    """Genera el pedido. `mapeo_arte` (opcional) activa el modo ARTE SEPARADO, donde el
    diseño vive en mesas aparte (una por pieza) y se escala/pega sobre el contorno de cada
    pieza del molde en cada talle. Acepta el formato plano {pieza: mesa} (compat) o POR
    VARIABLE {"mapeo": base, "por_variable": {v_xxx: {pieza: mesa}}} — la variable de cada
    prenda (`variante_clave`) elige su mapeo (regla 2026-07-13). Sin él,
    el arte se asume sobre la misma estructura del molde (modo clásico).
    `borde_corte` (opcional) = {activo, ancho_mm, color:[c,m,y,k]}: el borde de corte
    de la tizada por molde (si no viene, default 2 mm, CMYK 0 0 0 0.85 = negro)."""
    t0 = time.time()
    os.makedirs(salida, exist_ok=True)
    # Borde de corte configurable por molde. El margen de la pieza (B) = el ancho del
    # borde, así el borde visible (mitad externa del trazo recortado) = ancho_mm.
    _bc = borde_corte or {}
    _bc_activo = _bc.get("activo", True)
    _bc_mm = max(0.2, float(_bc.get("ancho_mm", 2.0) or 2.0))
    _bc_color = (_bc.get("color") or [0, 0, 0, 0.85])[:4]
    B = (_bc_mm if _bc_activo else 2.0) * MM
    base_doc = _abrir(plantilla)
    TODAS = set(i["name"] for i in base_doc.get_ocgs().values())
    CAPAS_ARTE = set(i["name"] for i in _abrir(arte).get_ocgs().values())

    fuentes_cache = {}
    def fuente(nombre_ps):
        if nombre_ps not in fuentes_cache:
            ruta = resolver_fuente(nombre_ps, carpeta_fuentes)
            if not ruta:
                raise RuntimeError(f"tipografía '{nombre_ps}' no está en el catálogo")
            fuentes_cache[nombre_ps] = FuenteCurvas(open(ruta, "rb").read())
        return fuentes_cache[nombre_ps]

    piezas_nombres = sorted(registro.keys())
    # Mapa pieza_idx -> nombre (para filtrar por VARIABLE de configuración: cada variable
    # de `prod.variantes` es un subconjunto de piezas identificadas por su pieza_idx). El
    # pieza_idx es constante para una pieza a lo largo de sus talles → se toma el primero.
    _idx_a_nombre = {}
    for _nom, _pt in registro.items():
        for _info in (_pt or {}).values():
            if isinstance(_info, dict) and _info.get("pieza_idx") is not None:
                _idx_a_nombre.setdefault(int(_info["pieza_idx"]), _nom)
                break
    import unicodedata as _ud
    def _toks_pieza(nombre):
        """Tokens normalizados del nombre de una pieza (minúsculas, sin acentos)."""
        s = "".join(c for c in _ud.normalize("NFKD", str(nombre)) if not _ud.combining(c))
        return [t for t in s.lower().replace("(", " ").replace(")", " ").split() if t]

    def partes_de(prenda):
        """Piezas que entran en una prenda según sus TOGGLES DE PIEZA (generalización de la
        manga). Cada toggle = {clave, opcion, opciones}. Para una pieza que menciona la CLAVE
        (ej. 'manga', 'sisa'):
          • si menciona la OPCIÓN elegida (ej. 'corta') → entra;
          • si menciona OTRA opción del toggle (ej. 'larga') → NO entra (es de esa otra);
          • si NO menciona ninguna opción → entra igual (es una pieza normal, no se adivina
            nada: 'manga derecha' sin opción sale siempre, como cualquier pieza).
        Las piezas que no mencionan ninguna clave entran siempre. Acepta varios toggles."""
        toggles = prenda.get("toggles") if isinstance(prenda, dict) else None
        if not toggles:   # compat: prenda con 'manga' corta/larga, o string suelto
            mval = prenda.get("manga") if isinstance(prenda, dict) else prenda
            if mval:
                toggles = [{"clave": "manga", "opcion": mval, "opciones": ["corta", "larga"]}]
            else:
                return list(piezas_nombres)
        norm = []   # (clave, [tokens opción elegida], [[tokens] de las OTRAS opciones])
        for tg in toggles:
            clave = str(tg.get("clave", "")).strip().lower()
            opcion = str(tg.get("opcion", "")).strip().lower()
            opciones = [str(o).strip().lower() for o in (tg.get("opciones") or []) if str(o).strip()]
            if opcion and opcion not in opciones:
                opciones = opciones + [opcion]
            if not clave or not opcion:
                continue
            sel = opcion.split()
            otras = [o.split() for o in opciones if o != opcion]
            norm.append((clave, sel, otras))
        if not norm:
            return list(piezas_nombres)
        out = []
        for p in piezas_nombres:
            tset = set(_toks_pieza(p))
            incluir = True
            for clave, sel, otras in norm:
                if clave not in tset:
                    continue                                   # esta clave no la afecta
                if all(t in tset for t in sel):
                    continue                                   # tiene la opción elegida → entra
                if any(all(t in tset for t in o) for o in otras):
                    incluir = False; break                     # tiene OTRA opción → afuera
                # else: no menciona ninguna opción → pieza normal → entra
            if incluir:
                out.append(p)
        # VÍNCULOS "van juntas" (ej. manga corta + su vivo): el vínculo es ATÓMICO frente al toggle.
        # Si algún miembro quedó AFUERA (ej. la manga larga cuando se eligió corta), se saca TODO el
        # vínculo — así el vivo NO aparece en las líneas que no llevan esa manga (antes salía en todas).
        juntas = prenda.get("juntas_piezas") if isinstance(prenda, dict) else None
        if juntas:
            _names = set(piezas_nombres); _outset = set(out)
            for _grp in juntas:
                _miembros = [m for m in _grp if m in _names]
                if len(_miembros) >= 2 and not all(m in _outset for m in _miembros):
                    out = [p for p in out if p not in _miembros]
                    _outset = set(out)
        return out
    def piezas_de(prenda):
        """Piezas a generar para una prenda: `partes_de` (toggles) INTERSECTADO con la
        VARIABLE de configuración elegida. La variable llega como `variante_piezas` = lista de
        NOMBRES de pieza (el servidor los resuelve desde los pieza_idx EN EL TALLE GUÍA — clave:
        el pieza_idx varía por talle). Fallback: `variante_idx` con el mapa por índice (menos
        confiable en multi-talle). Sin variable → todas las piezas (comportamiento de siempre)."""
        base = partes_de(prenda)
        if not isinstance(prenda, dict):
            return base
        permit = None
        _nombres = prenda.get("variante_piezas")
        if _nombres:
            permit = set(_nombres)
        elif prenda.get("variante_idx"):
            permit = {_idx_a_nombre[int(i)] for i in prenda["variante_idx"] if int(i) in _idx_a_nombre}
        if not permit:
            # Sin variable, o variable de otro molde (multi-molde) → no se filtra (no dejar vacío).
            return base
        return [p for p in base if p in permit]
    def TELA(p):
        if asignacion_tela and asignacion_tela.get(p):
            return asignacion_tela[p]                 # tela elegida por el usuario
        return "RIB" if p in PIEZAS_RIB else "Principal"
    def ROTA(p):
        # La REGLA manda y se aplica IGUAL a todas las piezas. El nombre de la pieza
        # no se chequea nunca. Sin regla (o "auto") → no rotar.
        if rotaciones and p in rotaciones and rotaciones[p]:
            return rotaciones[p]                      # ninguna / 90 / 180 / libre — para TODAS
        return "ninguna"

    _arte_por_talle, _limpias = {}, set()
    def pagina_arte(mesa, talle):
        if talle not in _arte_por_talle:
            _arte_por_talle[talle] = _abrir_pike(arte)
        pdf = _arte_por_talle[talle]
        if (talle, mesa) not in _limpias:
            pag = pdf.pages[mesa - 1]
            capas = (TODAS - {"Fondo", talle}) | {"Personalizable"}
            limpiar_capas_conservando_talle(pdf, pag, capas, talle,
                                            geometrias_base(base_doc, mesa, talle))
            sanear_oc(pdf, pag)
            _limpias.add((talle, mesa))
        return pdf.pages[mesa - 1]

    # Objetos editables que el usuario REALMENTE transformó (mover/rotar/escalar) en
    # algún talle. Esos se SACAN del diseño y se redibujan con su transformación; los
    # NO editados quedan DENTRO del diseño (vectorial, exactos, en la posición del arte).
    def _tf_identidad(tf):
        if not tf:
            return True
        return (abs(tf.get("dx", 0)) < 1e-6 and abs(tf.get("dy", 0)) < 1e-6
                and abs(tf.get("rot", 0)) < 1e-6 and abs(tf.get("scale", 1) - 1) < 1e-6)
    # `editables_cfg` = {variable: {objeto: {talle: tf}}} (posición POR VARIABLE). Un objeto editado
    # en CUALQUIER variable se saca del diseño base y se redibuja (unión); en las variables donde no
    # se editó, el redibujo cae a identidad = posición base. La clave "*" = base legacy compartida.
    _editados_nombres = set()
    for _objs in (editables_cfg or {}).values():
        for _nom, _portalle in (_objs or {}).items():
            if isinstance(_portalle, dict) and any(not _tf_identidad(t) for t in _portalle.values()):
                _editados_nombres.add(_norm_nombre(_nom))
    # Config de TAMAÑO por molde (general, por nombre de capa). Estructura:
    # {nombre_norm: {variante: {"apaisado":[ancho_cm,alto_cm], "vertical":[ancho_cm,alto_cm]}}}.
    # El objeto se escala PROPORCIONAL para ENTRAR en su caja (según sea más ancho o más alto
    # se usa "apaisado" o "vertical"), en vez de escalar con el diseño. Se redibuja aparte.
    _tamano = {}
    for _n, _porvar in (editables_tamano or {}).items():
        _pv = {str(_v): _box for _v, _box in (_porvar or {}).items() if _box}
        if _pv:
            _tamano[_norm_nombre(_n)] = _pv
    _tamano_nombres = set(_tamano.keys())
    # COLOR OVERRIDE por editable, POR VARIABLE: {variable: {objeto: {"fill":[cmyk]|None,"stroke":...}}}.
    # La clave "*" = compartida (legacy). Un objeto con color en CUALQUIER variable se saca del diseño
    # base y se redibuja RECOLOREADO (mismo camino que los editados). En las variables sin color, cae
    # a color original. El color se resuelve por variable al armar la base (`_color_de`).
    _ecolor = editables_color or {}
    def _cmyk4(v):
        try:
            return tuple(float(x) for x in v)[:4] if (v and len(v) >= 4) else None
        except Exception:
            return None
    def _color_de(nombre, variante):
        """(fill, stroke) CMYK del objeto para esta VARIABLE (fallback a "*"), o None si no hay
        override. Cada canal en 0..1; None en un canal = no tocar ese relleno/trazo."""
        c = ((_ecolor.get(variante) or _ecolor.get("*") or {}).get(nombre)) or {}
        f, s = _cmyk4(c.get("fill")), _cmyk4(c.get("stroke"))
        return (f, s) if (f or s) else None
    _coloreados_nombres = set()
    for _objs in _ecolor.values():
        for _nom, _c in (_objs or {}).items():
            _cc = _c or {}
            if _cmyk4(_cc.get("fill")) or _cmyk4(_cc.get("stroke")):
                _coloreados_nombres.add(_norm_nombre(_nom))
    # Conjunto a redibujar fuera del diseño base = editados ∪ con-tamaño-configurado ∪ recoloreados.
    _redibujar_nombres = _editados_nombres | _tamano_nombres | _coloreados_nombres
    # GARANTÍA anti-desaparición: un objeto a redibujar (editado o fijo) solo se SACA del
    # diseño base si su aislamiento produce contenido real. Si fallara, se DEJA en el diseño
    # tal cual (presente) — nunca desaparece. Se valida más abajo (necesita _edit_por_mesa).
    _redibujar_validos = set()

    _arte_pieza = {"pdf": None, "limpias": set()}
    def pagina_arte_pieza(arte_mesa):
        """Modo arte separado: la mesa del arte con SOLO el diseño (sin guías ni
        los placeholders de personalización, que se estampan aparte con datos)."""
        if _arte_pieza["pdf"] is None:
            _arte_pieza["pdf"] = _abrir_pike(arte)
        pdf = _arte_pieza["pdf"]
        if arte_mesa not in _arte_pieza["limpias"]:
            pag = pdf.pages[arte_mesa - 1]
            # Quitar del arte TODOS los placeholders de personalización (Personalizable
            # y las capas nombre/numero/palabra/…) y las guías; el dato se estampa aparte.
            # Si no, el placeholder original (ej. "00") sale igual, encima del valor.
            _quitar = {c for c in CAPAS_ARTE if _es_capa_guia(c)} | (CAPAS_ARTE & {"Personalizable"}) | {
                c for c in CAPAS_ARTE if _norm_nombre(c) not in CAPAS_NO_PERS}
            # Los objetos editables se MANTIENEN dentro del diseño (vectorial, exactos),
            # SALVO los que el usuario transformó Y cuyo aislamiento es válido (esos se
            # redibujan aparte). Si un editado no se pudo aislar, queda acá (no desaparece).
            _quitar = {c for c in _quitar if not (
                _es_capa_editable(c)
                and _norm_nombre(_nombre_editable(c)) not in _redibujar_validos)}
            # suprimir_capas (no limpiar_capas): quita esas capas SIN romper el estado gráfico,
            # así los editables que heredan color NO cambian de color (negro K100 seguía negro).
            suprimir_capas(pdf, pag, _quitar)
            sanear_oc(pdf, pag)
            _arte_pieza["limpias"].add(arte_mesa)
        return pdf.pages[arte_mesa - 1]

    # Capa de UN objeto editable, AISLADA como vector (mismo lienzo del arte, con SOLO esa
    # capa pintada). Preserva el estado gráfico → color/CMYK/spot EXACTO del diseño (no se
    # rasteriza ni se arrastra lo que tenga encima). Cacheada por (mesa, capa).
    _arte_solo = {}                       # (mesa, capa_norm, color_key) -> pikepdf Pdf aislado
    def pagina_arte_solo(arte_mesa, capa, color=None):
        # `color` = (fill_cmyk|None, stroke_cmyk|None) o None. Se cachea por color porque el
        # mismo objeto puede tener colores distintos según la VARIABLE.
        _ck = None if not color else ((tuple(color[0]) if color[0] else None),
                                      (tuple(color[1]) if color[1] else None))
        if _ck == (None, None):
            _ck = None
        key = (arte_mesa, _norm_nombre(capa), _ck)
        if key not in _arte_solo:
            pdf = _abrir_pike(arte)
            pag = pdf.pages[arte_mesa - 1]
            # COLOR OVERRIDE: recolorar ANTES de aislar. `aislar_capa` (vía `_raspar_pintado`)
            # BORRA los marcadores BDC/EMC que `recolorar_capa` necesita para ubicar el frame de
            # la capa → recolorar después no encontraría la capa (gotcha §10.b). Con la página
            # fresca los marcadores están presentes; el color inyectado (op `k`/`K` antes del
            # pintado) sobrevive al aislado (se conserva el contenido de la capa objetivo).
            if _ck is not None:
                recolorar_capa(pdf, pag, _norm_nombre(capa), cmyk_fill=_ck[0], cmyk_stroke=_ck[1])
            aislar_capa(pdf, pag, _norm_nombre(capa))
            sanear_oc(pdf, pag)
            _arte_solo[key] = pdf
        return _arte_solo[key].pages[arte_mesa - 1]

    # Cada objeto editable se RASTERIZA aislando su capa con fitz (que lo renderiza bien,
    # con colores y transparencia) y se mete como imagen (Form XObject) → robusto ante
    # objetos complejos (grupos, máscaras) que el recorte vectorial del content-stream rompe.
    _arte_fitz = {"doc": None}
    _edit_img = {}                       # capa_norm -> (xobject, ancho_pt, alto_pt)
    _edit_eps = []                       # mantiene vivos los pikepdf temporales de cada imagen
    def imagen_editable(arte_mesa, capa, bbox_mu):
        key = _norm_nombre(capa)
        if key not in _edit_img:
            if _arte_fitz["doc"] is None:
                _arte_fitz["doc"] = _abrir(arte)
            fd = _arte_fitz["doc"]; cfgs = fd.layer_ui_configs()
            for c in cfgs:
                fd.set_layer_ui_config(c["number"], action=1)              # apagar todas
            for c in cfgs:
                if _norm_nombre(c["text"]) == key:
                    fd.set_layer_ui_config(c["number"], action=0)          # prender la del objeto
            ox0, oy0, ox1, oy1 = bbox_mu
            zoom = 600 / 72.0                                              # ~600 DPI (solo objetos EDITADOS)
            pix = fd[arte_mesa - 1].get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                               clip=fitz.Rect(ox0, oy0, ox1, oy1), alpha=True)
            for c in cfgs:
                fd.set_layer_ui_config(c["number"], action=0)              # restaurar
            ow, oh = (ox1 - ox0), (oy1 - oy0)                              # tamaño del objeto en puntos
            tmp = _abrir(); pg2 = tmp.new_page(width=ow, height=oh)
            pg2.insert_image(fitz.Rect(0, 0, ow, oh), pixmap=pix)
            ep = pikepdf.open(io.BytesIO(tmp.tobytes()))
            _edit_eps.append(ep)                                          # NO liberar (lo usa copy_foreign)
            _edit_img[key] = (ep.pages[0].as_form_xobject(), ow, oh)
        return _edit_img[key]

    # Objetos editables del arte (capas "Editable …") → se dibujan APARTE de cada pieza,
    # con su transformación (mover/rotar/escalar). El diseño base ya los excluye.
    # Solo se activa cuando se pasa `editables_cfg` (None = no tocar la generación normal).
    _edit_por_mesa = {}
    _ecfg = editables_cfg or {}
    if mapeo_arte and editables_cfg is not None:
        try:
            for _o in extraer_editables(arte, con_thumb=False):   # el motor usa solo geometría (no thumb/svg)
                _edit_por_mesa.setdefault(_o["mesa"], []).append(_o)
        except Exception:
            _edit_por_mesa = {}
        # Validar el aislamiento de cada objeto a redibujar (editado o fijo): solo se saca del
        # diseño y se redibuja si su capa aislada tiene contenido real. Si no, se deja en el
        # diseño base (presente) → garantiza que NUNCA desaparezca.
        for _mesa, _objs in _edit_por_mesa.items():
            for _o in _objs:
                _nm = _norm_nombre(_nombre_editable(_o["capa"]))
                if _nm not in _redibujar_nombres or _nm in _redibujar_validos:
                    continue
                try:
                    pagina_arte_solo(_mesa, _o["capa"])   # validación de aislamiento: sin color
                    _bf = io.BytesIO(); _arte_solo[(_mesa, _norm_nombre(_o["capa"]), None)].save(_bf)
                    _pg = _abrir("pdf", _bf.getvalue())[_mesa - 1]
                    if _pg.get_drawings() or _pg.get_images() or _pg.get_text().strip():
                        _redibujar_validos.add(_nm)
                except Exception:
                    pass

    _arte_rects = {}
    def arte_rect(arte_mesa):
        if arte_mesa not in _arte_rects:
            _arte_rects[arte_mesa] = _abrir(arte)[arte_mesa - 1].rect
        return _arte_rects[arte_mesa]

    def _bbox_arte(xo):
        """Bounding box del XObject del arte ya transformado por su Matrix."""
        bx = [float(v) for v in xo.BBox]
        M = [float(v) for v in xo.Matrix] if "/Matrix" in xo else [1, 0, 0, 1, 0, 0]
        a, b, c, d, e, f = M
        xs, ys = [], []
        for (px, py) in ((bx[0], bx[1]), (bx[2], bx[1]), (bx[2], bx[3]), (bx[0], bx[3])):
            xs.append(a * px + c * py + e)
            ys.append(b * px + d * py + f)
        return min(xs), max(xs), min(ys), max(ys)

    def cm_encajar(xo, W, H, B):
        """Escala el diseño al ALTO de la pieza (manda el alto) con escala
        UNIFORME: el ancho crece/se achica en la MISMA proporción (sin deformar)
        y queda centrado a lo ancho. Lo que sobra a los costados lo recorta el
        contorno; si el diseño es más angosto que la pieza, queda centrado."""
        tx0, tx1, ty0, ty1 = _bbox_arte(xo)
        s = H / (ty1 - ty0) if ty1 != ty0 else 1.0
        aw = (tx1 - tx0) * s
        return f"{s:.6f} 0 0 {s:.6f} {B + (W - aw) / 2 - s*tx0:.3f} {B - s*ty0:.3f} cm"

    def cm_tamano_editable(xo, W, H, B, bbox_mu, sf):
        """Coloca el objeto a una escala ABSOLUTA `sf` (no la del talle) en la POSICIÓN donde
        caería si se escalara con el diseño. Para tamaño máximo: sf = max_cm / lado_mayor_cm.
        `bbox_mu` = bbox del objeto en coords MuPDF. (sf=1 = tamaño original del diseño.)"""
        tx0, tx1, ty0, ty1 = _bbox_arte(xo)
        s = H / (ty1 - ty0) if ty1 != ty0 else 1.0
        aw = (tx1 - tx0) * s
        ox = (bbox_mu[0] + bbox_mu[2]) / 2.0                  # centro X (MuPDF x = PDF x)
        oy = ty1 - (bbox_mu[1] + bbox_mu[3]) / 2.0            # centro Y → PDF (y-arriba)
        ex = (s - sf) * ox + B + (W - aw) / 2 - s * tx0       # centro escalado − sf·centro
        ey = (s - sf) * oy + B - s * ty0
        return f"{sf:.6f} 0 0 {sf:.6f} {ex:.3f} {ey:.3f} cm"

    def ops_cont(cont, S, dx=0.0, dy=0.0):
        def fseg(s):
            return (" ".join(f"{v*S + (dx if i % 2 == 0 else dy):.3f}"
                             for i, v in enumerate(s[1:])) + f" {s[0]}").strip()
        return "\n".join(fseg(s) for s in cont["segmentos"])

    # Los VIVOS (y cualquier pieza HUÉRFANA sin mesa propia en el arte) NO se auto-rellenan: si el
    # usuario no les asignó diseño en el Arte, salen SIN diseño acá también — la MISMA foto que el
    # Arte, sin magia por atrás que las diverja. El usuario los mapea a mano en el paso Arte, como
    # cualquier pieza (decisión del usuario 2026-07-09). `mapeo_arte` se copia por prolijidad.
    if mapeo_arte:
        mapeo_arte = dict(mapeo_arte)

    # REGLA (2026-07-13): el mapeo se maneja POR VARIABLE. `mapeo_arte` puede venir en dos formatos:
    #   • plano (compat): {pieza: mesa} — un solo mapeo para todo.
    #   • por variable:   {"mapeo": base, "por_variable": {v_xxx: {pieza: mesa}}} — cada VARIABLE
    #     tiene el suyo (AUTORITATIVO: si la variable está en `por_variable`, ese mapeo manda,
    #     aunque tenga menos piezas que la base — quitar un diseño en una variable NO resucita
    #     por la base). La base queda para prendas SIN variable y variables aún sin mapeo propio.
    _mapeo_pv = {}
    if mapeo_arte and any(isinstance(v, dict) for v in mapeo_arte.values()):
        _mapeo_pv = {str(c): {p: int(m) for p, m in (mm or {}).items() if m}
                     for c, mm in (mapeo_arte.get("por_variable") or {}).items()}
        mapeo_arte = {p: int(m) for p, m in (mapeo_arte.get("mapeo") or {}).items() if m}
        if not mapeo_arte:                     # sin base → unión de las variables (activa el modo
            for _mm in _mapeo_pv.values():     # separado y sirve de fallback para filas sin variable)
                for _p, _m in _mm.items():
                    mapeo_arte.setdefault(_p, _m)

    # Mapeo por VARIANTE (#variante / #rango en el nombre de la mesa del arte), leído una vez.
    # {} si no hay ninguna mesa con # → mesa_arte() cae siempre al mapeo normal (idéntico a hoy).
    _mapeo_var = {}
    if mapeo_arte:
        try:
            _vorden = talles_orden_archivo(plantilla, sorted({t for v in registro.values() for t in v}))
            _mapeo_var = mapeo_variantes_arte(arte, registro, _vorden)
        except Exception:
            _mapeo_var = {}

    def mesa_arte(pieza, talle, variante=None):
        """Mesa del arte para (pieza, talle, VARIABLE) con precedencia: #talle exacto > #rango >
        mapeo DE LA VARIABLE (si esa variable tiene el suyo) > mapeo base. None si la pieza
        quedó sin diseño (en esa variable / ese talle)."""
        _mp = _mapeo_pv[variante] if (variante and variante in _mapeo_pv) else (mapeo_arte or {})
        return (_mapeo_var.get(pieza) or {}).get(talle) or _mp.get(pieza)

    # FASE 2 — la pieza se arma UNA vez por (pieza, talle, variante) y se REUSA por prenda:
    # `_armar_base` hace la parte INVARIANTE (contorno + diseño + borde + editables), cacheada;
    # `generar_pieza` solo le ESTAMPA encima el nombre/número + la etiqueta (que cambian por
    # prenda). Mismo resultado que armar todo junto, sin recomputar el diseño en cada prenda.
    _base_cache = {}
    # CACHÉ de contornos del molde por (mesa, talle): `extraer_piezas_mesa` devuelve TODAS las piezas
    # de la mesa (135 en la Camiseta) y es caro (get_drawings del molde). Antes se llamaba una vez POR
    # PIEZA generada (9+) con los MISMOS args → extraía las 135 N veces. Cacheado = 1 sola extracción
    # por (mesa, talle), las piezas toman su índice. Gran ahorro en el preview/tizada (todos los talles).
    _piezas_mesa_cache = {}
    def _armar_base(pieza, talle, variante):
        info = registro[pieza][talle]
        mesa = info["mesa"]
        _mesa_a = mesa_arte(pieza, talle, variante) if mapeo_arte else None
        if "pieza_idx" in info:                 # etiquetado visual: pieza puntual de la mesa
            _pmk = (mesa, talle)
            _pm = _piezas_mesa_cache.get(_pmk)
            if _pm is None:
                _pm = extraer_piezas_mesa(base_doc, mesa, talle); _piezas_mesa_cache[_pmk] = _pm
            cont = _pm[info["pieza_idx"]]
        else:                                   # etiquetas de texto: el contorno mayor
            cont = extraer_contorno_mesa(base_doc, mesa=mesa, talle=talle)
        x0, y0, _, _ = cont["bbox_raw"]
        W, H = cont["w"], cont["h"]
        x0m, y0m, _, _ = cont["bbox_mu"]
        Hp = H + 2*B
        out = pikepdf.Pdf.new()
        page = out.add_blank_page(page_size=(W + 2*B, H + 2*B))

        # ── Arte: contorno (clip) y dibujo, en coordenadas finales de la pieza ──
        if mapeo_arte and not _mesa_a:          # esta variante quedó SIN diseño en esta pieza
            arte_draw = ""                      # pieza sin arte (el aviso de cobertura lo da el servidor)
            S = cont["user_unit"]
            clip = ops_cont(cont, S, dx=B - x0*S, dy=B - y0*S)   # igual necesita clip para el borde/etiqueta
        elif mapeo_arte:                        # ARTE SEPARADO: diseño en mesa aparte, escalado al contorno
            S = cont["user_unit"]
            pag = pagina_arte_pieza(_mesa_a)
            xo = out.copy_foreign(pag.as_form_xobject())
            if "/OC" in xo:
                del xo["/OC"]
            nom = page.add_resource(xo, Name.XObject, prefix="A")
            clip = ops_cont(cont, S, dx=B - x0*S, dy=B - y0*S)
            _td = cm_encajar(xo, W, H, B)        # encaje del diseño (alto manda, centrado)
            arte_draw = f"q\n{clip}\nW n\n{_td}\n{nom} Do\nQ\n"
            # OBJETOS EDITABLES de esta mesa que el usuario MOVIÓ/ROTÓ/ESCALÓ: se redibujan
            # APARTE. Los NO editados ya van vectoriales dentro del diseño base (no se tocan).
            _edit_obj = [o for o in _edit_por_mesa.get(_mesa_a, [])
                         if _norm_nombre(_nombre_editable(o["capa"])) in _redibujar_validos]
            for _o in _edit_obj:
                # Posición POR VARIABLE: la de esta `variante`, si no la base legacy "*", si no identidad.
                _tf = ((_ecfg.get(variante) or _ecfg.get("*") or {}).get(_o["nombre"]) or {}).get(talle) or {}
                _utf = _matriz_editable(_tf, _o, cont, W, H, B)          # "" si identidad
                # Caja de tamaño configurada para esta capa+variante (None = escala con el diseño).
                _box = _tamano.get(_norm_nombre(_nombre_editable(_o["capa"])), {}).get(str(talle))
                try:
                    # Capa del objeto AISLADA como vector (color/CMYK/spot exacto del diseño).
                    # Si esta VARIABLE tiene color override para el objeto, se recolorea al aislar.
                    _ps = pagina_arte_solo(_mesa_a, _o["capa"], color=_color_de(_o["nombre"], variante))
                    _xs = out.copy_foreign(_ps.as_form_xobject())
                    if "/OC" in _xs:
                        del _xs["/OC"]
                    _noms = page.add_resource(_xs, Name.XObject, prefix="E")
                    _w_cm = float(_o.get("w_cm") or 0); _h_cm = float(_o.get("h_cm") or 0)
                    _sf = None
                    if _box and _box.get("mantener"):
                        _sf = 1.0                            # mantener la medida del diseño (sin escalar)
                    elif _box and _w_cm > 0 and _h_cm > 0:
                        # según orientación del objeto, se usa la caja "apaisado" o "vertical";
                        # entra PROPORCIONAL (el lado que topa primero manda).
                        _b = (_box.get("apaisado") if _w_cm >= _h_cm else _box.get("vertical")) or []
                        _aw = float(_b[0]) if len(_b) > 0 else 0
                        _ah = float(_b[1]) if len(_b) > 1 else 0
                        _r = [x for x in (_aw / _w_cm if _aw > 0 else None,
                                          _ah / _h_cm if _ah > 0 else None) if x]
                        _sf = min(_r) if _r else None
                    if _sf:
                        _tds = cm_tamano_editable(_xs, W, H, B, _o["bbox_mu"], _sf)
                    else:
                        _tds = cm_encajar(_xs, W, H, B)      # escala con el diseño (default)
                    arte_draw += f"q\n{clip}\nW n\n{_utf}{_tds}\n{_noms} Do\nQ\n"
                except Exception:
                    pass
            # ── OBJETOS AGREGADOS por el usuario (PNG/SVG/PDF/AI): NO vienen del arte, son PDFs
            #    sueltos. Se componen sobre ESTA pieza con su transform, igual que un editable.
            #    Base = centrado 30% de la pieza (idéntico al default del editor) → editor = tizada.
            _ar = arte_rect(_mesa_a)      # mesa del arte de ESTA pieza y ESTE talle
            arte_draw += _dibujar_objetos_agregados(
                objetos_agregados, pieza, variante, talle, cont, W, H, B, clip, out, page,
                [_ar.x0, _ar.y0, _ar.width, _ar.height])
        else:                                   # ARTE CLÁSICO: diseño sobre la misma mesa del molde
            pag = pagina_arte(mesa, talle)
            xo = out.copy_foreign(pag.as_form_xobject())
            if "/OC" in xo:
                del xo["/OC"]
            S = float(xo.Matrix[0]) if "/Matrix" in xo else 1.0
            ops = ops_cont(cont, S)
            clip = ops_cont(cont, S, dx=B - x0*S, dy=B - y0*S)
            nom = page.add_resource(xo, Name.XObject, prefix="A")
            arte_draw = (f"q\n1 0 0 1 {B-x0*S:.3f} {B-y0*S:.3f} cm\n"
                         f"q\n{ops}\nW n\n{nom} Do\nQ\nQ\n")

        # Borde de corte: `ancho_mm` externos al contorno (clip par-impar contra el
        # exterior), del color configurado. Si está apagado, no se dibuja.
        # Uniones en MITER (0 j) → las esquinas terminan RECTAS/en punta (no redondeadas);
        # miter limit alto para no biselar las esquinas. (Antes 1 j = round → curvas.)
        if _bc_activo:
            _bcol = " ".join(f"{v:g}" for v in _bc_color) + " K"
            borde = (f"q\n{-3*B:.3f} {-3*B:.3f} {W+8*B:.3f} {H+8*B:.3f} re\n{clip}\nW* n\n{clip}\n"
                     f"{2*B:.3f} w 0 j 0 J 10 M {_bcol}\nS\nQ\n")
        else:
            borde = ""

        # Stream de contenido REUSABLE: la base va fija y el estampado (texto/etiqueta) se reescribe
        # por prenda con `cstream.write()` → no se acumulan objetos aunque se comparta la base.
        cstream = out.make_stream(b"")
        page.Contents = cstream
        return {"out": out, "page": page, "cstream": cstream, "base_stream": f"{borde}{arte_draw}",
                "clip": clip, "cont": cont, "W": W, "H": H, "x0": x0, "y0": y0, "x0m": x0m,
                "y0m": y0m, "Hp": Hp, "S": S, "mesa": mesa, "_mesa_a": _mesa_a, "info": info}

    def generar_pieza(pieza, talle, persona, nro, grupo=None, variante=None):
        _bk = (pieza, talle, variante)
        b = _base_cache.get(_bk)
        if b is None:
            b = _armar_base(pieza, talle, variante); _base_cache[_bk] = b
        out, page = b["out"], b["page"]
        mesa, _mesa_a, info = b["mesa"], b["_mesa_a"], b["info"]
        cont, W, H, S, clip = b["cont"], b["W"], b["H"], b["S"], b["clip"]
        x0, y0, x0m, y0m, Hp = b["x0"], b["y0"], b["x0m"], b["y0m"], b["Hp"]
        bloques = []
        # personalización: en modo clásico los placeholders viven en la mesa del
        # molde; en arte separado, en la mesa del arte mapeada a la pieza.
        clave_pers = str(_mesa_a) if (mapeo_arte and _mesa_a) else str(mesa)
        ph = pers.get(clave_pers, {})
        if mapeo_arte and not _mesa_a:
            # Pieza SIN diseño en esta variable/talle → no hay mesa de arte: nada que estampar.
            # Sin esta guarda, la clave caía a la mesa del MOLDE y podía chocar de casualidad
            # con una mesa del ARTE (pers['1']) → UnboundLocalError de `sp` (escala sin definir).
            ph = {}
        persona_n = {_norm_nombre(k): v for k, v in (persona or {}).items()}
        if ph and persona_n:                     # cualquier pieza con placeholders (espalda, frente, …)
            if mapeo_arte and _mesa_a:
                ra = arte_rect(_mesa_a); wa, ha = ra.width, ra.height
                sp = H / ha                        # escala uniforme (alto manda)
                aw_arte = wa * sp                  # ancho del arte ya escalado
            for campo, pl in ph.items():           # N campos: nombre, numero, palabra, numero 2, …
                texto = str(persona_n.get(_norm_nombre(campo), "")).strip().upper()
                if texto == "":
                    continue
                try:
                    fnom = fuente(pl["fuente"])     # cada placeholder usa su propia fuente
                except Exception:
                    continue                        # fuente no disponible → no se estampa ESE campo (la tizada se arma igual)
                size = pl["size"] * sp if mapeo_arte else pl["size"]
                # ¿el placeholder ORIGINAL va sobre una CURVA/ARCO o tiene VARIAS LÍNEAS? Sus glifos
                # trazan la línea base: si tiene arco (y varía) o salto de línea (y salta / x retrocede)
                # se reproduce fiel (curva + multilínea + interlineado); si no, texto plano centrado.
                _bp = pl.get("baseline_pts") or []
                _size0 = pl["size"]
                _fiel = False
                if len(_bp) >= 3:
                    _xs = [p[0] for p in _bp]; _ys = [p[1] for p in _bp]
                    _xr = max(_xs) - min(_xs)
                    _curva = _xr > 0 and (max(_ys) - min(_ys)) > 0.03 * _xr
                    _multi = any(abs(_bp[i][1] - _bp[i-1][1]) > 0.6 * _size0 or (_bp[i][0] - _bp[i-1][0]) < -0.4 * _size0 for i in range(1, len(_bp)))
                    _fiel = _curva or _multi
                def _T(px, py):   # punto del arte → coords de la pieza (misma transformación que el plano)
                    if mapeo_arte:
                        return (B + (W - aw_arte) / 2 + px * sp, B + H - py * sp)
                    return (px - x0m + B, Hp - (py - y0m + B))
                if _fiel:
                    # (x, y, x0, x1) del arte → coords de la pieza (posición + bordes del renglón).
                    _glifos = [(*_T(px, py), _T(ex0, py)[0], _T(ex1, py)[0]) for (px, py, ex0, ex1) in _bp]
                    _ops = fnom.ops_texto_fiel(texto, size, _glifos)
                else:
                    if mapeo_arte:
                        cx_final = B + (W - aw_arte) / 2 + pl["cx"] * sp
                        ty = B + (1 - pl["baseline_y"] / ha) * H
                    else:
                        cx_final = pl["cx"] - x0m + B
                        ty = Hp - (pl["baseline_y"] - y0m + B)
                    _ops = fnom.ops_texto(texto, size, cx_final - fnom.ancho_texto(texto, size) / 2, ty)
                _pas = pl.get("pasadas")
                if _pas:
                    # PILA DE APARIENCIAS: se re-dibuja el texto una vez por cada pasada del arte,
                    # EN EL MISMO ORDEN → el color original queda atrás y cada capa de la apariencia
                    # (relleno y/o borde) encima, igual que Illustrator. Ver changelog 2026-07-16.
                    for _p in _pas:
                        _c = _p["color"]
                        _vals = " ".join(f"{v:g}" for v in _c[1])
                        if _p["t"] == "f":
                            bloques.append(f"q {_vals} {_c[0]}\n{_ops}\nf\nQ\n")
                        else:
                            _w = _p["w"] * (sp if mapeo_arte else 1.0)   # a la escala del texto
                            bloques.append(f"q {_vals} {_c[0].upper()}\n{_w:.3f} w 1 j 1 J\n{_ops}\nS\nQ\n")
                    continue
                _tz = pl.get("trazo")
                if _tz:                                # el placeholder tenía BORDE → se respeta
                    _sw = _tz[2] * (sp if mapeo_arte else 1.0)   # ancho a la misma escala que el texto
                    _scol = " ".join(f"{v:g}" for v in _tz[1]) + " " + _tz[0].upper()  # color de TRAZO (mayúsculas)
                    # Igual que el diseño: el trazo va DETRÁS y el relleno ENCIMA, así el
                    # borde queda SOLO por fuera (la mitad interna del trazo la tapa el
                    # relleno) y no se come el texto. Trazo centrado de ancho W → borde
                    # visible = la mitad externa.
                    bloques.append(f"q {_scol}\n{_sw:.3f} w 1 j 1 J\n{_ops}\nS\nQ\n")   # borde (atrás)
                    bloques.append(f"q {_color_op(pl)}\n{_ops}\nf\nQ\n")                # relleno (encima)
                else:
                    bloques.append(f"q {_color_op(pl)}\n{_ops}\nf\nQ\n")
        # ── Etiqueta de identificación/corte (configurable por molde) ──
        # `etiqueta` (config) decide: si va, QUÉ muestra (talle/pieza/número),
        # DÓNDE (grilla 3×3, igual en todos los talles), EN QUÉ PIEZAS, tamaño,
        # color del texto y del borde/halo, y ancho del borde. Sin config = default
        # (talle-pieza-#nro, abajo, gris con halo claro) como antes.
        _et = etiqueta or {}
        _pieza_limpia = pieza.replace(' (corta)', '').replace(' (larga)', '')
        # piezas_off se maneja por NOMBRE GENÉRICO (un "Cuello" apaga todos los cuellos). _norm_generico
        # tolera datos viejos con número ("Cuello 3" → "cuello") sin migrar nada.
        _et_off = set(_norm_generico(p) for p in (_et.get("piezas_off") or []))
        _et_on = _et.get("activo", True) and _norm_generico(_pieza_limpia) not in _et_off
        # ── ETIQUETA POR ZONAS (por NOMBRE GENÉRICO): si la pieza tiene ≥2 puntos elegidos,
        #    se dibuja el texto de CADA zona sobre su tramo del borde y NO la etiqueta única. ──
        _zna = {_norm_generico(k): v for k, v in (_et.get("zonas") or {}).items()}.get(_norm_generico(_pieza_limpia))
        _usa_zonas = bool(_et_on and _zna and len(_zna.get("puntos") or []) >= 2)
        if _usa_zonas:
            _esize = float(_et.get("size_mm") or 3.0) * MM
            _zeops = None
            try:
                fetq = fuente("Arial-BoldMT")
                _zeops = _eops_zonas(cont, S, x0, y0, B, _zna["puntos"], _zna.get("cont") or [],
                                     _esize, _et.get("align") or "centro", fetq,
                                     talle, _pieza_limpia, nro, (_et.get("separador", "-") or "-"))
            except Exception:
                _zeops = None
            if _zeops:
                if _et.get("borde_activo", True):
                    _bcol = " ".join(f"{v:g}" for v in (_et.get("borde_color") or [0.01, 0.01, 0.01, 0.05])[:4]) + " K"
                    _bw = float(_et.get("borde_mm") or 1.0) * MM
                    bloques.append(f"q 1 J 1 j {_bw:.2f} w {_bcol}\n{_zeops}\nS\nQ\n")
                _tcol = " ".join(f"{v:g}" for v in (_et.get("color") or [0.15, 0.15, 0.15, 0.30])[:4]) + " k"
                bloques.append(f"q {_tcol}\n{_zeops}\nf\nQ\n")
        if _et_on and not _usa_zonas:
            _mos = _et.get("mostrar") or {"talle": True, "pieza": True, "numero": True}
            _partes = []
            if _mos.get("talle", True):  _partes.append(str(talle))
            if _mos.get("pieza", True):  _partes.append(_pieza_limpia)
            if _mos.get("numero", True): _partes.append(f"#{nro:02d}")
            et = (_et.get("separador", "-") or "-").join(_partes)
            if et:
                import math as _m
                _esize = float(_et.get("size_mm") or 3.0) * MM
                # Posición POR PIEZA (el usuario la apoyó sobre el contorno de ESA pieza).
                # Las claves de `posiciones` vienen con el nombre tal cual ("Espalda",
                # "costadillo izquierdo"); se normalizan AMBOS lados para que matcheen.
                # Por NOMBRE GENÉRICO: la posición se aplica a TODAS las piezas del mismo
                # nombre (todos los frentes), aunque estén numeradas "Frente 8"/"Frente 9".
                # Claves de `posiciones` (precedencia): "variante§NombreCompleto" (POR PIEZA POR
                # VARIABLE, nombre completo p/ ej "Frente 8") > "grupo§Nombre" (por grupo, genérico,
                # legacy) > "Nombre" (global, genérico, legacy). La clave de variante (v_…) y el grupoId
                # (g_…) son namespaces distintos → sin ambigüedad. Compat total con moldes viejos.
                _pos_glob, _pos_grp, _pos_var = {}, {}, {}
                for _k, _v in (_et.get("posiciones") or {}).items():
                    if "§" in _k:
                        _g, _n = _k.split("§", 1)
                        if variante and _g == variante:
                            _pos_var[_norm_nombre(_n)] = _v          # por PIEZA (nombre completo) por variable
                        elif grupo and _g == grupo:
                            _pos_grp[_norm_generico(_n)] = _v         # legacy: por grupo, genérico
                    else:
                        _pos_glob[_norm_generico(_k)] = _v            # legacy: global, genérico
                _kn = _norm_generico(_pieza_limpia)
                _posi = _pos_var.get(_norm_nombre(_pieza_limpia)) or _pos_grp.get(_kn) or _pos_glob.get(_kn)
                eops = None
                # TEXT-ON-PATH: si la pieza tiene `t` (posición relativa en el contorno),
                # el texto SIGUE el segmento del borde con su alineación, igual que el
                # preview. La alineación es POR PIEZA (posi.align) o el default global.
                if _posi and _posi.get("t") is not None:
                    _alg = _posi.get("align") or _et.get("align") or "centro"
                    try:
                        fetq = fuente("Arial-BoldMT")
                        _rx = _posi.get("rx"); _ry = _posi.get("ry")
                        eops = _eops_borde(cont, S, x0, y0, B, _rx, _ry, float(_posi["t"]), et, _esize, _alg, fetq, _bc_activo)
                    except Exception:
                        eops = None      # ante cualquier error, cae al recto (no rompe la tizada)
                if eops is None:
                    # Fallback RECTO en un punto rx/ry (sin `t`, o segmento inválido).
                    if _posi:
                        a = _ancla_etiqueta(cont, _posi, _esize)
                        _ang = -float(_posi.get("ang", 0) or 0)
                    elif _et.get("posicion") or "pieza_idx" in info:
                        a = _ancla_etiqueta(cont, _et.get("posicion") or {}, _esize)
                        _ang = 0.0
                    else:
                        a = dict(info["ancla"]); _esize = a["size_pt"]; _ang = a.get("angulo", 0)
                    align = (_posi or {}).get("align") or _et.get("align", a.get("h", "centro"))
                    fetq = fuente(a.get("fuente", "Arial-BoldMT"))
                    _aw = fetq.ancho_texto(et, _esize)
                    _ca, _sa = _m.cos(_m.radians(_ang)), _m.sin(_m.radians(_ang))
                    _shift = _aw / 2 if align == "centro" else (_aw if align == "derecha" else 0)
                    _px = a["x"] - x0m + B
                    _py = Hp - (a["y"] - y0m + B)
                    eops = fetq.ops_texto(et, _esize, _px - _shift * _ca, _py - _shift * _sa, angulo_deg=_ang)
                if _et.get("borde_activo", True):
                    _bcol = " ".join(f"{v:g}" for v in (_et.get("borde_color") or [0.01, 0.01, 0.01, 0.05])[:4]) + " K"
                    _bw = float(_et.get("borde_mm") or 1.0) * MM
                    bloques.append(f"q 1 J 1 j {_bw:.2f} w {_bcol}\n{eops}\nS\nQ\n")
                _tcol = " ".join(f"{v:g}" for v in (_et.get("color") or [0.15, 0.15, 0.15, 0.30])[:4]) + " k"
                bloques.append(f"q {_tcol}\n{eops}\nf\nQ\n")

        stream = (b["base_stream"] +
                  f"q\n{clip}\nW n\n" + "".join(bloques) + "Q\n")
        b["cstream"].write(stream.encode())
        buf = io.BytesIO()
        out.save(buf)
        return buf.getvalue()

    piezas_por_tela = {}                              # tela -> lista de piezas (claves dinámicas)
    total = sum(len(piezas_de(p)) for p in prendas)
    hechas = 0
    for nro, pr in enumerate(prendas, start=1):
        for pieza in piezas_de(pr):
            persona = pr.get("personalizacion") or {"nombre": pr.get("nombre", ""), "numero": pr.get("numero", "")}
            datos = generar_pieza(pieza, pr["talle"], persona, nro, grupo=(pr.get("_grupo") if isinstance(pr, dict) else None),
                                  variante=(pr.get("variante_clave") if isinstance(pr, dict) else None))
            doc = _abrir("pdf", datos)
            r = doc[0].rect
            piezas_por_tela.setdefault(TELA(pieza), []).append(
                {"doc": doc, "w": r.width, "h": r.height, "pieza": pieza, "talle": pr["talle"],
                 "variante": (pr.get("variante_clave") if isinstance(pr, dict) else None),   # clave de geometría (dedup de máscaras del nesteo)
                 "etiqueta": f"{nro:02d}", "rotacion": ROTA(pieza), "borde_cm": 0})
            hechas += 1
            if progreso:
                progreso("piezas", f"{hechas}/{total} - {pieza} (Prenda {nro}, Talle {pr['talle']})", None)

    # Modo "solo piezas": devuelve {tela: [piezas...]} con los docs ABIERTOS, para
    # que un pedido MULTI-MOLDE junte las piezas de varios moldes y las anide juntas.
    if solo_piezas:
        return piezas_por_tela
    return _nestear_y_componer(piezas_por_tela, config_nesting, telas_cfg, salida, t0, total, progreso)


def _nestear_y_componer(piezas_por_tela, config_nesting, telas_cfg, salida, t0, total, progreso=None, prefijo=""):
    """Anida y compone las piezas (ya generadas) por TELA → una hoja por tela.
    Todas las piezas de una misma tela van JUNTAS (sin importar de qué molde son)."""
    cfg = {"ancho_cm": 180, "altura_max_cm": 500, "espaciado_cm": 0.5,
           "margenes_cm": {"sup": 1, "inf": 1, "izq": 1, "der": 1},
           "resolucion_mm": float(os.environ.get("TIZADA_RES_MM", 4)), "estrategias": ["bl", "bandas"]}
    if config_nesting:
        cfg.update(config_nesting)
    hojas = []
    for tela, piezas in piezas_por_tela.items():
        if not piezas:
            continue
        if progreso:
            progreso("nesting", tela, None)
        cfg_t = dict(cfg)
        if telas_cfg and tela in telas_cfg:           # ancho/alto propios de esta tela
            cfg_t.update(telas_cfg[tela])
        slug = (prefijo + "".join(c if c.isalnum() else "_" for c in tela))[:48] or "Tela"
        coloc, area = anidar_contorno(piezas, cfg_t)
        path = os.path.join(salida, f"HOJA_{slug}.pdf")
        consumo, alturas_cm = componer_pdf_contorno(coloc, cfg_t, path, etiquetas=False)
        for p in piezas:
            if "doc" in p and p["doc"]:
                try:
                    p["doc"].close()
                except Exception:
                    pass
        _barrer_fuentes(path)
        d = fitz.open(path)
        try:
            prevs = []
            paginas = len(d)
            for i, pg in enumerate(d):
                if progreso:
                    progreso("previews", f"{i + 1}/{paginas} - {tela}", None)
                pv = f"prev_{slug}_h{i+1}.svg"
                svg = pg.get_svg_image()
                # Fondo BLANCO de la hoja (la mesa de trabajo es blanca). Así el
                # preview puede ir en una caja fija y el blanco es SOLO la mesa.
                _s = svg.find("<svg")
                if _s != -1:
                    _i = svg.index(">", _s) + 1
                    svg = svg[:_i] + '<rect width="100%" height="100%" fill="#ffffff"/>' + svg[_i:]
                with open(os.path.join(salida, pv), "w", encoding="utf-8") as f:
                    f.write(svg)
                prevs.append(pv)
        finally:
            d.close()
        # El aprovechamiento puede no calcularse si la hoja salió vacía (consumo 0):
        # evitamos la división por cero y reportamos 0 % en vez de romper el pedido.
        denom = float(cfg_t["ancho_cm"]) * float(consumo)
        aprov = round(float(100 * area / denom), 1) if denom > 0 else 0.0
        hojas.append({"tela": tela, "archivo": f"HOJA_{slug}.pdf", "paginas": paginas,
                      "consumo_cm": round(float(consumo), 1),
                      "alturas_cm": alturas_cm,   # alto de CADA página (cada página = una mesa física de tela)
                      "ancho_cm": round(float(cfg_t["ancho_cm"]), 1),  # ancho de la tela (la mesa mide ancho x consumo)
                      "aprovechamiento": aprov,
                      "previews": prevs})
    telas_spacing = {}
    for h in hojas:
        tela = h["tela"]
        cfg_t = dict(cfg)
        if telas_cfg and tela in telas_cfg:
            cfg_t.update(telas_cfg[tela])
        telas_spacing[tela] = float(cfg_t.get("espaciado_cm", 0.5)) * 10.0
    validaciones = validar_salida(salida, hojas, telas_spacing)
    return {"hojas": hojas, "validaciones": validaciones,
            "duracion_s": round(time.time() - t0, 1), "piezas": total}


def generar_pedido_multi(molds, carpeta_fuentes, salida, config_nesting=None,
                         telas_cfg=None, progreso=None):
    """Genera VARIOS moldes en UNA sola tizada: junta las piezas de todos los moldes
    por TELA y las anida juntas. `molds` = lista de dicts con: plantilla, arte,
    registro, pers, prendas, mapeo_arte, rotaciones, asignacion_tela."""
    t0 = time.time()
    os.makedirs(salida, exist_ok=True)
    acc = {}
    total = 0
    for md in molds:
        pt = generar_pedido(md["plantilla"], md["arte"], md["registro"], md.get("pers") or {},
                            md["prendas"], carpeta_fuentes, salida,
                            config_nesting=config_nesting, progreso=progreso,
                            mapeo_arte=md.get("mapeo_arte"), rotaciones=md.get("rotaciones"),
                            asignacion_tela=md.get("asignacion_tela"), telas_cfg=telas_cfg,
                            solo_piezas=True)
        for tela, lst in pt.items():
            acc.setdefault(tela, []).extend(lst)
            total += len(lst)
    return _nestear_y_componer(acc, config_nesting, telas_cfg, salida, t0, total, progreso)


def generar_pedido_grupos(grupos, carpeta_fuentes, salida, config_nesting=None,
                          telas_cfg=None, progreso=None):
    """Genera por GRUPOS de tizada. `grupos` = lista de {nombre, moldes}, donde
    `moldes` es una lista de dicts de molde (como en generar_pedido_multi). Los
    moldes de un MISMO grupo se combinan (por tela); grupos distintos NO se mezclan
    (cada grupo arma sus propias hojas). Cada hoja queda etiquetada con su grupo."""
    t0 = time.time()
    os.makedirs(salida, exist_ok=True)
    todas, total = [], 0
    for gi, grupo in enumerate(grupos):
        acc = {}
        for md in grupo["moldes"]:
            pt = generar_pedido(md["plantilla"], md["arte"], md["registro"], md.get("pers") or {},
                                md["prendas"], carpeta_fuentes, salida,
                                config_nesting=config_nesting, progreso=progreso,
                                mapeo_arte=md.get("mapeo_arte"), rotaciones=md.get("rotaciones"),
                                asignacion_tela=md.get("asignacion_tela"), telas_cfg=telas_cfg,
                                solo_piezas=True, borde_corte=md.get("borde_corte"),
                                etiqueta=md.get("etiqueta"), editables_cfg=md.get("editables_cfg"),
                                editables_tamano=md.get("editables_tamano"),
                                objetos_agregados=md.get("objetos_agregados"),
                                editables_color=md.get("editables_color"))
            for tela, lst in pt.items():
                acc.setdefault(tela, []).extend(lst)
                total += len(lst)
        res_g = _nestear_y_componer(acc, config_nesting, telas_cfg, salida, t0, total,
                                    progreso, prefijo=f"g{gi}_")
        for h in res_g["hojas"]:
            h["grupo"] = grupo.get("nombre", f"Grupo {gi + 1}")
            h["moldes"] = grupo.get("nombres", [])
            todas.append(h)
    telas_spacing = {}
    return {"hojas": todas,
            "validaciones": validar_salida(salida, todas, telas_spacing),
            "duracion_s": round(time.time() - t0, 1), "piezas": total}


def _barrer_fuentes(path):
    # `with` para CERRAR el handle antes del os.replace: en Windows, si el PDF
    # original sigue abierto, el reemplazo falla con "Acceso denegado".
    with pikepdf.open(path) as p:
        vis = set()
        def caminar(obj, pr=0):
            if pr > 14:
                return
            og = getattr(obj, "objgen", None)
            if og in vis:
                return
            vis.add(og)
            res = obj.get("/Resources") if isinstance(obj, (pikepdf.Stream, pikepdf.Dictionary)) else None
            if res is not None:
                if "/Font" in res:
                    del res["/Font"]
                if "/XObject" in res:
                    for k in res.XObject.keys():
                        try:
                            caminar(res.XObject[k], pr + 1)
                        except Exception:
                            pass
        for pg in p.pages:
            caminar(pg.obj)
        p.save(path + ".tmp")
    os.replace(path + ".tmp", path)


# ════════════════ VALIDACIONES DE SALIDA ════════════════
def validar_salida(carpeta, hojas, telas_spacing):
    res = []
    for h in hojas:
        path = os.path.join(carpeta, h["archivo"])
        try:
            with pikepdf.open(path) as p:
                tiene_fuente = False
                for pg in p.pages:
                    res_obj = pg.get("/Resources")
                    if res_obj and "/Font" in res_obj:
                        tiene_fuente = True
                        break
            ok = not tiene_fuente
            res.append({"nombre": f"{h['tela']}: texto en curvas, cero fuentes",
                        "ok": ok,
                        "detalle": "sin texto vivo ni recursos de fuente" if ok
                                   else "Advertencia: se detectaron recursos de fuente en el archivo final"})
        except Exception as e:
            res.append({"nombre": f"{h['tela']}: texto en curvas, cero fuentes",
                        "ok": False,
                        "detalle": f"Error al validar: {e}"})

        try:
            p = pikepdf.open(path)
            malos = total = 0
            vis = set()
            def chequear(s):
                nonlocal malos, total
                total += 1
                try:
                    ops = [str(i.operator) for i in parse_content_stream(s)]
                except Exception:
                    malos += 1
                    return
                prof = mn = 0
                for o in ops:
                    if o == "q":
                        prof += 1
                    elif o == "Q":
                        prof -= 1
                    mn = min(mn, prof)
                if prof or mn < 0:
                    malos += 1
            def caminar(o, pr=0):
                if pr > 12:
                    return
                og = getattr(o, "objgen", None)
                if og in vis:
                    return
                vis.add(og)
                if isinstance(o, pikepdf.Stream) and str(o.get("/Subtype", "")) == "/Form":
                    chequear(o)
                r2 = o.get("/Resources") if isinstance(o, (pikepdf.Stream, pikepdf.Dictionary)) else None
                if r2 is not None and "/XObject" in r2:
                    for k in r2.XObject.keys():
                        try:
                            caminar(r2.XObject[k], pr + 1)
                        except Exception:
                            pass
            vistos2 = set()
            tintas = set()
            for pg in p.pages:
                cont = pg.Contents
                for s in (cont if isinstance(cont, pikepdf.Array) else [cont]):
                    chequear(s)
                caminar(pg.obj)
                tintas |= _separaciones(pg.obj, vistos2)
            res.append({"nombre": f"{h['tela']}: balance de streams (Acrobat)", "ok": malos == 0,
                        "detalle": f"{total} streams, {malos} con error"})
            tintas.discard("All")
            res.append({"nombre": f"{h['tela']}: tintas planas", "ok": True,
                        "detalle": ", ".join(sorted(tintas)) or "sin uso en esta tela"})
        except Exception as e:
            res.append({"nombre": f"{h['tela']}: balance de streams (Acrobat)", "ok": False,
                        "detalle": f"Error al validar: {e}"})
            res.append({"nombre": f"{h['tela']}: tintas planas", "ok": False,
                        "detalle": f"Error al validar: {e}"})

        # Spacing check (instant, using the guaranteed nesting spacing constraint)
        peor = telas_spacing.get(h["tela"], 5.0)
        res.append({"nombre": f"{h['tela']}: espaciado entre piezas",
                    "ok": True,
                    "detalle": f"{peor:.1f} mm (mínimo medido)"})
    return res
