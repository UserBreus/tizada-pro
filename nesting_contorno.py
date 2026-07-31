"""
NESTING POR CONTORNO (true-shape) — Motor de Sublimación USER v2
================================================================
Las piezas se anidan por su silueta real, no por su rectángulo contenedor.

Cómo funciona:
  - Cada pieza vectorial se rasteriza a una grilla de ocupación (resolución
    configurable, p. ej. 2 mm/celda). SOLO para calcular posiciones: la salida
    sigue siendo el vector original, intacto.
  - Rotación POR PIEZA según manifest: "ninguna" | "90" (0/90/180/270) | "libre"
    (ángulos cada `paso_libre_grados`).
  - "borde_cm" POR PIEZA: espacio reservado alrededor del contorno (sangrado /
    margen de corte).
  - "espaciado_cm" POR TELA: distancia mínima GARANTIZADA entre contornos
    (entre dos piezas: borde_A + espaciado + borde_B).
  - Colocación greedy bottom-left con búsqueda de posiciones válidas por
    convolución FFT (rápida incluso con grillas grandes), eligiendo el ángulo
    que menos altura de tela consume.
"""

import numpy as np
import pymupdf as fitz
import math
from math import ceil
from scipy import ndimage
from scipy.signal import fftconvolve

CM = 28.3465


def _disco(r):
    if r <= 0:
        return None
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def _mascara(doc, cell_pt, sobre=4):
    """Rasteriza la pieza a la grilla con SOBRE-COBERTURA: se muestrea a
    `sobre`× la resolución y una celda cuenta como tinta si CUALQUIER
    submuestra tiene tinta. Así la máscara nunca subestima la pieza
    (la subestimación se comía hasta 2 mm del espaciado por lado)."""
    zoom = float(sobre) / cell_pt
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    fino = ~np.all(a > 245, axis=2)
    # RELLENAR el interior: el contorno de corte (línea oscura) encierra la pieza,
    # pero si el diseño es claro/blanco el interior no es "tinta" y la máscara
    # quedaría HUECA → otras piezas se anidarían adentro y se encimarían. Rellenar
    # los huecos da la silueta MACIZA real, sin importar el color del diseño.
    fino = ndimage.binary_fill_holes(fino)
    H = (fino.shape[0] + sobre - 1) // sobre * sobre
    W = (fino.shape[1] + sobre - 1) // sobre * sobre
    rell = np.zeros((H, W), bool)
    rell[:fino.shape[0], :fino.shape[1]] = fino
    m = rell.reshape(H // sobre, sobre, W // sobre, sobre).any(axis=(1, 3))
    return m if m.any() else np.ones((H // sobre, W // sobre), bool)


def _angulos(modo, paso_libre):
    if modo in ("ninguna", "0", None):
        return [0]
    if modo == "90":
        return [0, 90, 180, 270]
    if modo == "180":
        return [0, 180]
    if modo == "libre":
        return [a for a in range(0, 360, max(1, int(paso_libre)))]
    raise ValueError(f"Modo de rotación desconocido: {modo!r}")


def _rotar(mask, ang):
    """Rota la máscara en el MISMO sentido que page.show_pdf_page(rotate=ang)
    (verificado por calibración: ndimage.rotate(+ang) ↔ fitz rotate=+ang)."""
    ang = ang % 360
    if ang == 0:
        return mask
    if ang % 90 == 0:
        return np.rot90(mask, k=ang // 90)
    return ndimage.rotate(mask, ang, reshape=True, order=0)


def _elegir_posicion(valid, hh, estrategia):
    """Devuelve (y, x, score) de la mejor posición válida según la estrategia."""
    ys, xs = np.where(valid)
    if estrategia == "bl":            # bottom-left estricto: menor altura resultante
        k = np.lexsort((xs, ys + hh))
        y, x = int(ys[k[0]]), int(xs[k[0]])
        return y, x, (y + hh, x)
    if estrategia == "bandas":        # tolera ~5 cm de altura para compactar a la izquierda
        Q = 25
        k = np.lexsort((xs, (ys + hh) // Q))
        y, x = int(ys[k[0]]), int(xs[k[0]])
        return y, x, ((y + hh) // Q, x)
    raise ValueError(f"Estrategia desconocida: {estrategia!r}")


def _preparar(piezas, cfg):
    """Parámetros de grilla + máscaras base (cacheadas por resolución)."""
    cell_pt = cfg.get("resolucion_mm", 2) / 10 * CM
    m = cfg["margenes_cm"]
    ancho_c = int((cfg["ancho_cm"] - m["izq"] - m["der"]) * CM / cell_pt)
    # El alto de la mesa ya NO se recorta a 14400 pt: las mesas largas se resuelven con /UserUnit al
    # componer (ver `componer_pdf_contorno`). El tope real lo pone la configuración de nesting.
    alto_c = int((cfg["altura_max_cm"] * CM - (m["sup"] + m["inf"]) * CM) / cell_pt)
    esp_c = max(1, ceil(cfg["espaciado_cm"] * CM / cell_pt))  # respeta la separación, sin la celda extra de antes
    paso = cfg.get("paso_libre_grados", 15)
    # DEDUP por GEOMETRÍA: muchas piezas comparten silueta (mismo (pieza,talle,variante,
    # rotación,borde,grilla)). La máscara sale SOLO del contorno de corte exterior
    # (umbral + fill_holes; el estampado interior no la cambia) → misma clave = máscara y
    # candidatos IDÉNTICOS. Se computan UNA vez y se comparten (solo lectura en la colocación),
    # evitando N rasterizaciones/dilataciones. No afecta la salida (solo posiciona; se dibuja
    # el `doc` propio de cada pieza). Base cacheada por (pieza,talle,variante) en el motor.
    _geo = {}
    for p in piezas:
        cache_key = (cell_pt, esp_c, paso, p["rotacion"], p.get("borde_cm", 0))
        if p.get("_cache_key") == cache_key:               # ya computada (mismo objeto, otra orden)
            continue
        geo_key = (p.get("pieza"), p.get("talle"), p.get("variante"), p["rotacion"],
                   p.get("borde_cm", 0), cell_pt, esp_c, paso)
        hit = _geo.get(geo_key)
        if hit is not None:                                # otra instancia con MISMA geometría
            p["_mask"] = hit["_mask"]; p["_borde_c"] = hit["_borde_c"]
            p["_cell_pt"] = hit["_cell_pt"]; p["_candidatos_angulo"] = hit["_candidatos_angulo"]
            p["_cache_key"] = cache_key
            continue
        p["_mask"] = _mascara(p["doc"], cell_pt)
        p["_borde_c"] = ceil(p.get("borde_cm", 0) * CM / cell_pt)
        p["_cell_pt"] = cell_pt

        # Precalcular candidatos por ángulo (rotación y dilataciones)
        candidatos_angulo = []
        for ang in _angulos(p["rotacion"], paso):
            mr = _rotar(p["_mask"], ang)
            pad = p["_borde_c"] + esp_c
            mr_p = np.pad(mr, pad)
            if p["_borde_c"]:
                mr_col = ndimage.binary_dilation(mr_p, _disco(p["_borde_c"]))
            else:
                mr_col = mr_p
            d = _disco(esp_c)
            mr_test = ndimage.binary_dilation(mr_col, d) if d is not None else mr_col

            # Si mr_test es más alto que la hoja o más ancho, no sirve
            if mr_test.shape[0] > alto_c or mr_test.shape[1] > ancho_c:
                continue
            candidatos_angulo.append((ang, mr_col, mr_test))

        p["_candidatos_angulo"] = candidatos_angulo
        p["_cache_key"] = cache_key
        _geo[geo_key] = {"_mask": p["_mask"], "_borde_c": p["_borde_c"],
                         "_cell_pt": p["_cell_pt"], "_candidatos_angulo": p["_candidatos_angulo"]}

    return cell_pt, ancho_c, alto_c, esp_c, paso


def anidar_contorno(piezas, cfg):
    """Tizada más eficiente: prueba VARIOS órdenes de inserción × estrategias y
    devuelve el layout de MENOR consumo de tela (menos espacio en blanco)."""
    if not piezas:
        return [], 0.0
    prep = _preparar(piezas, cfg)
    idx = list(range(len(piezas)))
    
    # Pruning de candidatos de ordenación según cantidad de piezas
    if len(piezas) > 15:
        # Solo área descendente para muchas piezas (es el más eficiente)
        A = [int(piezas[i]["_mask"].sum()) for i in idx]
        ordenes = [sorted(idx, key=lambda i: A[i], reverse=True)]
    elif len(piezas) > 8:
        # Área desc y max(H, W) desc
        A = [int(piezas[i]["_mask"].sum()) for i in idx]
        Hh = [piezas[i]["_mask"].shape[0] for i in idx]
        Ww = [piezas[i]["_mask"].shape[1] for i in idx]
        candidatos = [sorted(idx, key=lambda i: A[i], reverse=True),
                      sorted(idx, key=lambda i: max(Hh[i], Ww[i]), reverse=True)]
        ordenes, vistos = [], set()
        for o in candidatos:
            if tuple(o) not in vistos:
                vistos.add(tuple(o)); ordenes.append(o)
    else:
        # Evaluar todo para pocas piezas
        A = [int(piezas[i]["_mask"].sum()) for i in idx]
        Hh = [piezas[i]["_mask"].shape[0] for i in idx]
        Ww = [piezas[i]["_mask"].shape[1] for i in idx]
        candidatos = [sorted(idx, key=lambda i: A[i], reverse=True),
                      sorted(idx, key=lambda i: Hh[i], reverse=True),
                      sorted(idx, key=lambda i: Ww[i], reverse=True),
                      sorted(idx, key=lambda i: max(Hh[i], Ww[i]), reverse=True)]
        ordenes, vistos = [], set()
        for o in candidatos:
            if tuple(o) not in vistos:
                vistos.add(tuple(o)); ordenes.append(o)
                
    # Pruning de estrategias para reducir tiempos en pedidos grandes
    estrategias = cfg.get("estrategias", ["bl", "bandas"])
    if len(piezas) > 12:
        estrategias = ["bl"]
        
    mejor = None
    for orden in ordenes:
        for est in estrategias:
            coloc, area = _anidar_estrategia(piezas, cfg, est, orden, prep)
            consumo = sum(max(c["cy"] + c["bh"] / 2 for c in h) for h in coloc if h)
            if mejor is None or consumo < mejor[0]:
                mejor = (consumo, coloc, area)
    return mejor[1], mejor[2]


def _anidar_estrategia(piezas, cfg, estrategia, orden, prep):
    """Coloca las piezas en el `orden` dado con la `estrategia`. Devuelve
    (hojas, area_piezas_cm2). hoja = [colocacion, ...]."""
    cell_pt, ancho_c, alto_c, esp_c, paso = prep

    hojas_G, hojas_sky, colocaciones = [], [], []

    def nueva_hoja():
        hojas_G.append(np.zeros((alto_c, ancho_c), bool))
        hojas_sky.append(0)
        colocaciones.append([])
        return len(hojas_G) - 1

    nueva_hoja()
    area_piezas_c2 = 0

    for i in orden:
        p = piezas[i]
        candidatos_por_angulo = p["_candidatos_angulo"]
        if not candidatos_por_angulo:
            raise ValueError(f"La pieza {p['etiqueta']} no entra en la hoja con ninguna rotación permitida.")

        colocada = False
        for h_idx in range(len(hojas_G)):
            G, sky = hojas_G[h_idx], hojas_sky[h_idx]
            mejor = None
            for ang, mr_col, mr_test in candidatos_por_angulo:
                hh, ww = mr_test.shape
                ylim = min(alto_c, sky + hh)
                if ylim < hh:
                    continue
                conv = fftconvolve(G[:ylim].astype(np.float32),
                                   mr_test[::-1, ::-1].astype(np.float32), mode="valid")
                valid = conv < 0.5
                if not valid.any():
                    continue
                y, x, score = _elegir_posicion(valid, hh, estrategia)
                if mejor is None or score < mejor[0]:
                    mejor = (score, ang, mr_col, mr_test, y, x)
            if mejor:
                _, ang, mr_col, mr_test, y, x = mejor
                hh, ww = mr_test.shape
                # estampar la ocupación real (contorno + borde propio, sin el espaciado)
                dy, dx = (hh - mr_col.shape[0]) // 2, (ww - mr_col.shape[1]) // 2
                G[y + dy:y + dy + mr_col.shape[0], x + dx:x + dx + mr_col.shape[1]] |= mr_col
                hojas_sky[h_idx] = max(hojas_sky[h_idx], y + hh)
                # bbox matemático exacto del vector rotado, centrado en la celda de la máscara
                th = math.radians(ang)
                bw = abs(p["w"] * math.cos(th)) + abs(p["h"] * math.sin(th))
                bh = abs(p["w"] * math.sin(th)) + abs(p["h"] * math.cos(th))
                cx = (x + ww / 2) * cell_pt
                cy = (y + hh / 2) * cell_pt
                colocaciones[h_idx].append({"pieza": p, "ang": ang, "cx": cx, "cy": cy,
                                            "bw": bw, "bh": bh})
                area_piezas_c2 += int(p["_mask"].sum())
                colocada = True
                break
        if not colocada:
            h_idx = nueva_hoja()
            # hoja vacía: elegir el ángulo de menor altura y colocar en el origen
            ang, mr_col, mr_test = min(candidatos_por_angulo, key=lambda c: c[2].shape[0])
            hh, ww = mr_test.shape
            y, x = 0, 0
            G = hojas_G[h_idx]
            dy, dx = (hh - mr_col.shape[0]) // 2, (ww - mr_col.shape[1]) // 2
            G[y + dy:y + dy + mr_col.shape[0], x + dx:x + dx + mr_col.shape[1]] |= mr_col
            hojas_sky[h_idx] = y + hh
            th = math.radians(ang)
            bw = abs(p["w"] * math.cos(th)) + abs(p["h"] * math.sin(th))
            bh = abs(p["w"] * math.sin(th)) + abs(p["h"] * math.cos(th))
            colocaciones[h_idx].append({"pieza": p, "ang": ang,
                                        "cx": (x + ww / 2) * cell_pt, "cy": (y + hh / 2) * cell_pt,
                                        "bw": bw, "bh": bh})
            area_piezas_c2 += int(p["_mask"].sum())

    area_piezas_cm2 = area_piezas_c2 * (cell_pt / CM) ** 2
    return colocaciones, area_piezas_cm2


def componer_pdf_contorno(colocaciones, cfg, path_salida, etiquetas=True):
    m = cfg["margenes_cm"]
    ancho_pag = cfg["ancho_cm"] * CM
    out = fitz.open()
    consumo_cm = 0.0
    alturas_cm = []   # alto de CADA página (cada página = una MESA física de tela)
    user_units = []   # /UserUnit de cada página (1 = mesa normal, sin truco)
    for hoja in colocaciones:
        if not hoja:
            continue
        alto_usado = max(c["cy"] + c["bh"] / 2 for c in hoja)
        alto_pag = alto_usado + (m["sup"] + m["inf"]) * CM
        # ── MESAS DE MÁS DE 5,08 m ────────────────────────────────────────────────────────────
        # Ninguna página PDF puede pasar de 14400 unidades por lado (200 pulgadas = 508 cm). Para
        # mesas más largas se usa **/UserUnit** (PDF 1.6): cada unidad vale `uu` puntos, así que se
        # dibuja TODO dividido por `uu` y el lector lo multiplica de vuelta. Verificado con el RIP
        # del usuario, que reporta el largo real. Con uu=1 (mesas normales) la salida es idéntica
        # a la de siempre: `s` vale 1 y no se toca nada.
        uu = max(1, ceil(max(ancho_pag, alto_pag) / 14400.0))
        s = 1.0 / uu
        page = out.new_page(width=ancho_pag * s, height=alto_pag * s)
        for c in hoja:
            x0 = (m["izq"] * CM + c["cx"] - c["bw"] / 2) * s
            y0 = (m["sup"] * CM + c["cy"] - c["bh"] / 2) * s
            page.show_pdf_page(fitz.Rect(x0, y0, x0 + c["bw"] * s, y0 + c["bh"] * s),
                               c["pieza"]["doc"], 0, rotate=c["ang"])
            if etiquetas:
                page.insert_text(fitz.Point(x0 + 2 * s, max(y0 - 3 * s, 6 * s)), c["pieza"]["etiqueta"],
                                 fontname="helvetica", fontsize=max(1, 6 * s), color=(0.4, 0.4, 0.4))
        user_units.append(uu)
        alturas_cm.append(round(alto_pag / CM, 1))
        consumo_cm += alto_pag / CM
    out.save(path_salida, deflate=True, garbage=3)
    out.close()
    # PyMuPDF no escribe /UserUnit → se agrega con pikepdf (ya es dependencia del proyecto). Si
    # fallara, la hoja quedaría a 1/uu de escala: se avisa fuerte en el log en vez de pasar callado.
    if any(u > 1 for u in user_units):
        try:
            import pikepdf
            with pikepdf.open(path_salida, allow_overwriting_input=True) as pdf:
                for pg, u in zip(pdf.pages, user_units):
                    if u > 1:
                        pg.UserUnit = int(u)
                pdf.save(path_salida)
        except Exception as e:
            print(f"  [!!] MESA LARGA SIN /UserUnit ({path_salida}): {e}\n"
                  f"       La hoja quedaría a 1/{max(user_units):g} de escala. NO IMPRIMIR.")
    return consumo_cm, alturas_cm
