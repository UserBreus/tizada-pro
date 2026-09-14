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
import os
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


def poligonos_contorno(cont, S, x0, y0, B):
    """El contorno de una pieza como polilíneas en coordenadas de PÁGINA (pt, y hacia arriba),
    con la MISMA transformación que el clip y el borde del motor: (vx·S + B − x0·S, vy·S + B − y0·S).
    Las curvas se aplanan en 8 tramos (igual que el text-on-path de la etiqueta, `_eops_borde`)."""
    def _P(vx, vy):
        return (vx * S + B - x0 * S, vy * S + B - y0 * S)
    polis, pts, cur = [], [], None
    for sg in cont.get("segmentos") or []:
        op = sg[0]
        if op == "m":
            if len(pts) > 2:
                polis.append(pts)
            cur = _P(sg[1], sg[2]); pts = [cur]
        elif op == "l":
            cur = _P(sg[1], sg[2]); pts.append(cur)
        elif op == "c":
            p0 = cur or _P(sg[1], sg[2]); p1 = _P(sg[1], sg[2]); p2 = _P(sg[3], sg[4]); p3 = _P(sg[5], sg[6])
            for k in range(1, 9):
                u = k / 8.0; mu = 1 - u
                pts.append((mu*mu*mu*p0[0] + 3*mu*mu*u*p1[0] + 3*mu*u*u*p2[0] + u*u*u*p3[0],
                            mu*mu*mu*p0[1] + 3*mu*mu*u*p1[1] + 3*mu*u*u*p2[1] + u*u*u*p3[1]))
            cur = p3
        elif op == "re":
            X, Y, Wd, Ht = sg[1], sg[2], sg[3], sg[4]
            if len(pts) > 2:
                polis.append(pts)
            pts = [_P(X, Y), _P(X + Wd, Y), _P(X + Wd, Y + Ht), _P(X, Y + Ht)]
            cur = pts[0]
        elif op == "h":
            if len(pts) > 2:
                polis.append(pts)
            pts = []
    if len(pts) > 2:
        polis.append(pts)
    return polis


def _mascara_contorno(b, cell_pt, sobre=4):
    """La máscara de ocupación de una pieza a partir de su CONTORNO (la base `b` del motor: `cont`,
    `S`, `x0`, `y0`, `B`, `W`, `Hp`), sin dibujar el arte.

    Hasta 2026-09-04 la máscara salía de rasterizar el documento de la pieza con el diseño adentro
    (`_mascara(doc)`): con el molde con diseño eso costaba 0,5-1 s por pieza distinta y obligaba a
    serializar un documento sólo para mirar su silueta. La silueta ES el contorno relleno más el
    borde de corte (B por fuera): se pinta el polígono a `sobre`× la resolución, se dilata el
    borde y se reduce a celdas con `any`, exactamente como la versión rasterizada. Mismo criterio
    de sobre-cobertura (una celda cuenta si CUALQUIER submuestra está adentro)."""
    from PIL import Image, ImageDraw
    zoom = float(sobre) / cell_pt
    Wp, Hp, B = float(b["W"]) + 2 * float(b["B"]), float(b["Hp"]), float(b["B"])
    w_px, h_px = max(1, ceil(Wp * zoom)), max(1, ceil(Hp * zoom))
    img = Image.new("1", (w_px, h_px), 0)
    dr = ImageDraw.Draw(img)
    for poli in poligonos_contorno(b["cont"], b["S"], b["x0"], b["y0"], B):
        pts = [(x * zoom, (Hp - y) * zoom) for x, y in poli]      # y hacia abajo, como el pixmap
        if len(pts) > 2:
            dr.polygon(pts, fill=1, outline=1)
    fino = np.array(img, dtype=bool)
    r = int(ceil(B * zoom))
    if r > 0:
        fino = ndimage.binary_dilation(fino, _disco(r))              # el borde de corte, por fuera
    H = (fino.shape[0] + sobre - 1) // sobre * sobre
    W = (fino.shape[1] + sobre - 1) // sobre * sobre
    rell = np.zeros((H, W), bool)
    rell[:fino.shape[0], :fino.shape[1]] = fino
    m = rell.reshape(H // sobre, sobre, W // sobre, sobre).any(axis=(1, 3))
    return m if m.any() else np.ones((H // sobre, W // sobre), bool)


_DEBUG = {}     # contadores del nesting (bloques vs FFT), para medir


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
        # 🔴 EL MOLDE VA EN LA CLAVE. Sin él, dos moldes distintos con una pieza del mismo nombre
        # («Frente 1», «Cuello 1»), mismo talle y las dos filas sin variable elegida compartían la
        # SILUETA: la segunda se colocaba con la forma de la primera y la hoja salía con las piezas
        # encimadas, perfectamente imprimible. Antes no podía pasar porque cada molde armaba su
        # propia tizada; desde el changelog 439 los moldes de la misma columna de talle se acomodan
        # JUNTOS, así que la clave tiene que distinguirlos.
        geo_key = (p.get("_molde"), p.get("pieza"), p.get("talle"), p.get("variante"), p["rotacion"],
                   p.get("borde_cm", 0), cell_pt, esp_c, paso)
        p["_geo_key"] = geo_key
        hit = _geo.get(geo_key)
        if hit is not None:                                # otra instancia con MISMA geometría
            p["_mask"] = hit["_mask"]; p["_borde_c"] = hit["_borde_c"]
            p["_cell_pt"] = hit["_cell_pt"]; p["_candidatos_angulo"] = hit["_candidatos_angulo"]
            p["_cache_key"] = cache_key
            continue
        # Con base (camino B, hoja compartida) la máscara sale del contorno, sin tocar el arte;
        # `TIZADA_MASCARA_LEGACY=1` vuelve a rasterizar el documento de la pieza.
        _b = p.get("base")
        if _b and _b.get("cont") is not None and not os.environ.get("TIZADA_MASCARA_LEGACY"):
            p["_mask"] = _mascara_contorno(_b, cell_pt)
        else:
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
    # BLOQUES DE PIEZAS IDÉNTICAS (2026-09-04, plan E7): un pedido grande repite la misma pieza del
    # mismo talle decenas de veces (100 camisetas = 900 piezas de 72 geometrías). Cada colocación
    # costaba una convolución FFT por ángulo candidato sobre la hoja entera (con rotación libre, 24
    # FFT por pieza): a 900 piezas, minutos. Para una pieza cuya geometría ya se colocó se prueba
    # PRIMERO, sin FFT, al lado de la última igual (a la derecha, debajo, o al inicio de la fila
    # siguiente) con una comprobación local de solapamiento; y si no entra, la FFT se hace sólo con
    # el ángulo que usó la anterior (las idénticas comparten el mejor ángulo) antes de barrer todos.
    # `TIZADA_NESTING_SIN_BLOQUES=1` vuelve al barrido completo (para comparar layouts).
    _bloques = not os.environ.get("TIZADA_NESTING_SIN_BLOQUES")
    ultimo = {}                     # geo_key → (h_idx, ang, y, x, mr_col, mr_test)
    _DEBUG.update({"bloque": 0, "fft": 0, "sin_geo": 0, "sin_ultimo": 0, "sin_lugar": 0})

    def _cabe(G, yy, xx, mr_test):
        hh, ww = mr_test.shape
        if yy < 0 or xx < 0 or yy + hh > alto_c or xx + ww > ancho_c:
            return False
        return not (G[yy:yy + hh, xx:xx + ww] & mr_test).any()

    def _x_en_fila(G, yy, mr_test, desde=0):
        """El menor x ≥ `desde` en el que la máscara entra en la fila `yy` (o None): la fila entera
        de una vez, con una ventana deslizante sobre la banda de la hoja (una prueba local de
        solapamiento por posición, sin FFT)."""
        hh, ww = mr_test.shape
        if yy < 0 or yy + hh > alto_c or ww > ancho_c:
            return None
        banda = G[yy:yy + hh, :]
        try:
            from numpy.lib.stride_tricks import sliding_window_view
            v = sliding_window_view(banda, (hh, ww))[0]          # (ancho_c-ww+1, hh, ww)
            choca = (v & mr_test).any(axis=(1, 2))
        except Exception:
            return None
        libres = np.flatnonzero(~choca[desde:])
        return int(libres[0]) + desde if libres.size else None

    for i in orden:
        p = piezas[i]
        candidatos_por_angulo = p["_candidatos_angulo"]
        if not candidatos_por_angulo:
            raise ValueError(f"La pieza {p['etiqueta']} no entra en la hoja con ninguna rotación permitida.")

        colocada = False
        _u = ultimo.get(p.get("_geo_key")) if _bloques else None
        if _u is not None:
            h_u, ang_u, y_u, x_u, mr_col_u, mr_test_u = _u
            G = hojas_G[h_u]
            hh, ww = mr_test_u.shape
            # candidatos: la misma fila (a la derecha de la última), la fila siguiente desde el
            # borde izquierdo, y una fila más abajo — el primer lugar libre de cada una
            _pos = []
            for yy, desde in ((y_u, x_u + ww), (y_u + hh, 0), (y_u + 2 * hh, 0)):
                xx = _x_en_fila(G, yy, mr_test_u, desde)
                if xx is not None:
                    _pos.append((yy, xx))
                    break
            for yy, xx in _pos:
                if _cabe(G, yy, xx, mr_test_u):
                    dy, dx = (hh - mr_col_u.shape[0]) // 2, (ww - mr_col_u.shape[1]) // 2
                    G[yy + dy:yy + dy + mr_col_u.shape[0], xx + dx:xx + dx + mr_col_u.shape[1]] |= mr_col_u
                    hojas_sky[h_u] = max(hojas_sky[h_u], yy + hh)
                    th = math.radians(ang_u)
                    bw = abs(p["w"] * math.cos(th)) + abs(p["h"] * math.sin(th))
                    bh = abs(p["w"] * math.sin(th)) + abs(p["h"] * math.cos(th))
                    colocaciones[h_u].append({"pieza": p, "ang": ang_u, "cx": (xx + ww / 2) * cell_pt,
                                              "cy": (yy + hh / 2) * cell_pt, "bw": bw, "bh": bh})
                    area_piezas_c2 += int(p["_mask"].sum())
                    ultimo[p["_geo_key"]] = (h_u, ang_u, yy, xx, mr_col_u, mr_test_u)
                    colocada = True
                    _DEBUG["bloque"] += 1
                    break
            if not colocada:
                _DEBUG["sin_lugar"] += 1
        elif p.get("_geo_key") is None:
            _DEBUG["sin_geo"] += 1
        else:
            _DEBUG["sin_ultimo"] += 1
        if colocada:
            continue
        _DEBUG["fft"] += 1
        # Qué ángulos se evalúan con FFT:
        #  · una geometría REPETIDA: sólo el ángulo de su anterior (las idénticas comparten el
        #    mejor ángulo; barrer los 24 en cada hoja llena era el 60 % de las FFT);
        #  · la PRIMERA de una geometría con rotación libre: de GRUESO a FINO — primero los
        #    múltiplos de 90°, después ±2 pasos alrededor del mejor (8 FFT en vez de 24, misma
        #    calidad en la práctica: los ángulos vecinos casi no cambian la altura resultante);
        #  · el resto: todos sus candidatos.
        if _u:
            _fases = [[c for c in candidatos_por_angulo if c[0] == _u[1]] or candidatos_por_angulo]
        elif p.get("rotacion") == "libre" and len(candidatos_por_angulo) > 8:
            _grueso = [c for c in candidatos_por_angulo if c[0] % 90 == 0] or candidatos_por_angulo[:4]
            _fases = [_grueso, None]                       # None = «los vecinos del mejor», se arma después
        else:
            _fases = [candidatos_por_angulo]
        # una repetida que no entró al lado de su anterior busca desde la hoja de esa anterior
        # en adelante (las de antes ya están llenas: probarlas era una FFT por hoja, 15 hojas a
        # 100 prendas, para no encontrar nada)
        for h_idx in range(_u[0] if _u else 0, len(hojas_G)):
            G, sky = hojas_G[h_idx], hojas_sky[h_idx]
            mejor = None
            for _cands in _fases:
              if _cands is None:
                  if mejor is None:
                      continue
                  _vistos = {c[0] for c in _fases[0]}
                  _ang0 = mejor[1]
                  _cands = [c for c in candidatos_por_angulo if c[0] not in _vistos
                            and min(abs(c[0] - _ang0), 360 - abs(c[0] - _ang0)) <= 2 * max(1, int(paso))]
              for ang, mr_col, mr_test in _cands:
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
                if p.get("_geo_key") is not None:
                    ultimo[p["_geo_key"]] = (h_idx, ang, y, x, mr_col, mr_test)
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
            if p.get("_geo_key") is not None:
                ultimo[p["_geo_key"]] = (h_idx, ang, y, x, mr_col, mr_test)
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
