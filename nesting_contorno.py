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
from scipy.special import cosdg, sindg

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


def _perfil_inferior(m):
    """Por columna de la máscara: la fila siguiente a la última ocupada (0 si la columna está vacía)."""
    tiene = m.any(axis=0)
    ult = m.shape[0] - np.argmax(m[::-1, :], axis=0)
    return np.where(tiene, ult, 0).astype(np.int64), np.nonzero(tiene)[0]


# 🔴 EL CONTACTO (MAPA 719): cuánto vale cada celda de largo de más frente a una celda de borde que toca.
# Medido en camisetas, mangas, banderines, círculos, rectángulos y mezclas: 2 es el que más acorta en
# promedio. Compite con «bl» y «hueco»: donde no sirve, gana otro (nunca empeora). Gemelo: CONTACTO_PESO.
CONTACTO_PESO = 2
_ANILLOS = {}


def _anillo(mt):
    """Las celdas que RODEAN a la máscara (vecinas de lado, no de esquina), con un margen de 1: donde la
    pieza «toca». Una vez por máscara. Gemelo: `anillo` (contorno.js)."""
    r = _ANILLOS.get(id(mt))
    if r is None or r[0] is not mt:
        big = np.pad(mt, 1)
        r = (mt, ndimage.binary_dilation(big) & ~big)
        _ANILLOS[id(mt)] = r
    return r[1]


def _contacto(Gs, mt):
    """Para cada lugar de la máscara: cuántas celdas de su anillo están ocupadas o son pared (arriba,
    izquierda y derecha; abajo NO: es la tela que sigue). Mismo tamaño que el mapa de lugares válidos."""
    Gp = np.pad(Gs, 1, constant_values=True)
    Gp[-1, :] = False
    ring = _anillo(mt)
    return fftconvolve(Gp.astype(np.float32), ring[::-1, ::-1].astype(np.float32), mode="valid")


def _elegir_posicion(valid, hh, estrategia, hueco=None):
    """Devuelve (y, x, score) de la mejor posición válida según la estrategia. `hueco` (sólo para la
    estrategia «hueco») = (prof, b, cols, dy, dx): el perfil de la hoja y el de la pieza."""
    ys, xs = np.where(valid)
    if estrategia == "bl":            # bottom-left estricto: menor altura resultante
        k = np.lexsort((xs, ys + hh))
        y, x = int(ys[k[0]]), int(xs[k[0]])
        return y, x, (y + hh, x)
    if estrategia == "contacto":
        # 🔴 EL MAYOR CONTACTO (MAPA 719): la pieza va donde MÁS borde toca de las otras piezas y de la mesa
        # (así una manga se mete en el hueco que le queda a un cuerpo y dos piezas giradas encastran), menos
        # `CONTACTO_PESO` por cada celda que alarga la mesa. Sale del contorno: vale para cualquier forma.
        # Empate: el fondo más alto, después más a la izquierda. `hueco` = (mapa de contacto, sky).
        # Sólo los lugares donde la pieza queda APOYADA arriba (no puede subir una fila más: toca algo o la
        # pared de arriba) — medido: el mismo acomodo y ~100 veces menos lugares que contar en el navegador.
        cmap, sky = hueco
        apoyada = valid.copy()
        apoyada[1:] &= ~valid[:-1]
        ys, xs = np.where(apoyada)
        c = np.rint(cmap[ys, xs]).astype(np.int64)
        fondo = ys + hh
        val = c - CONTACTO_PESO * (np.maximum(fondo, sky) - sky)
        k = np.lexsort((xs, fondo, -val))
        y, x = int(ys[k[0]]), int(xs[k[0]])
        return y, x, (-int(val[k[0]]), int(fondo[k[0]]), x)
    if estrategia == "hueco":
        # 🔴 EL MENOR HUECO (MAPA 714): la misma altura que «bl» (lo más arriba posible), pero entre los
        # lugares de esa fila gana el que menos hueco deja ATRAPADO: por cada columna, lo que el frente
        # de la hoja (`prof`, la última celda ocupada) avanza al poner la pieza — la pieza más el vacío
        # que queda encerrado entre ella y lo de arriba. Nada de formas: sale de las máscaras. Con
        # piezas que encastran (banderines, triángulos, talles mezclados) elige el lugar que encaja.
        prof, b, cols, dy, dx = hueco
        y = int(ys.min())
        xs0 = xs[ys == y]
        nueva = (y + dy) + b[cols][None, :]
        actual = prof[xs0[:, None] + dx + cols[None, :]]
        inc = np.maximum(0, nueva - actual).sum(axis=1)
        k = np.lexsort((xs0, inc))
        x = int(xs0[k[0]])
        return y, x, (y + hh, int(inc[k[0]]), x)
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
    # 🔴 LA SEPARACIÓN ES ENTRE PIEZAS, NO CONTRA EL BORDE DE LA MESA (MAPA 633): cada máscara de prueba
    # lleva `esp_c` de aire alrededor, y con la grilla del tamaño justo de la mesa ese aire también quedaba
    # contra el borde (8 mm por lado con 5 mm de espaciado): una bandera de 156 cm no entraba en una mesa
    # de 157. La grilla se agranda `esp_c` de cada lado para que el aire pueda colgar afuera, y las
    # posiciones se corren `esp_c` al devolverlas (las tres `colocaciones` de `_anidar_estrategia`): la PIEZA nunca sale de la mesa y el
    # borde lo decide sólo el margen configurado. Gemelo: `preparar` de motor/nesting/contorno.js.
    ancho_c += 2 * esp_c
    alto_c += 2 * esp_c
    paso = cfg.get("paso_libre_grados", 15)
    # DEDUP por GEOMETRÍA: muchas piezas comparten silueta (mismo (pieza,talle,variante,
    # rotación,borde,grilla)). La máscara sale SOLO del contorno de corte exterior
    # (umbral + fill_holes; el estampado interior no la cambia) → misma clave = máscara y
    # candidatos IDÉNTICOS. Se computan UNA vez y se comparten (solo lectura en la colocación),
    # evitando N rasterizaciones/dilataciones. No afecta la salida (solo posiciona; se dibuja
    # el `doc` propio de cada pieza). Base cacheada por (pieza,talle,variante) en el motor.
    _geo = {}
    for p in piezas:
        # 🔴 EL TAMAÑO DE LA MESA VA EN LA CLAVE (MAPA 703): los giros que se guardan son los que
        # ENTRAN en esta mesa; una pieza ya preparada para una mesa grande, acomodada después en una
        # más chica (la franja de la Copia), reusaba giros que no entraban → hoja rota.
        cache_key = (cell_pt, esp_c, paso, p["rotacion"], p.get("borde_cm", 0), alto_c, ancho_c)
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
            # 🔴 UN GIRO QUE DA LA MISMA SILUETA QUE OTRO YA ANOTADO NO SE VUELVE A PROBAR (MAPA 708):
            # un círculo girado, un hexágono cada 60°… se acomodan igual (en empate ya ganaba el primer
            # giro), así que el resultado es idéntico y con giro libre se ahorra hasta 24 búsquedas.
            if any(c[2].shape == mr_test.shape and c[1].shape == mr_col.shape and np.array_equal(c[2], mr_test)
                   and np.array_equal(c[1], mr_col) for c in candidatos_angulo):
                continue
            candidatos_angulo.append((ang, mr_col, mr_test))

        p["_candidatos_angulo"] = candidatos_angulo
        p["_cache_key"] = cache_key
        _geo[geo_key] = {"_mask": p["_mask"], "_borde_c": p["_borde_c"],
                         "_cell_pt": p["_cell_pt"], "_candidatos_angulo": p["_candidatos_angulo"]}

    return cell_pt, ancho_c, alto_c, esp_c, paso


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 🔴 EL OPTIMIZADOR (MAPA 728) — gemelo EXACTO de `anidarContorno` (frontend/src/motor/nesting/contorno.js)
#
# El acomodo de siempre es CODICIOSO: pone cada pieza, en el orden dado, donde mejor queda AHORA. Con un
# orden fijo (las grandes primero) las chicas quedan para el final y se apilan al pie (los cuellos de 20
# camisetas: 14 en filas al final de la última mesa). La tizada mejor sale de OTRO orden — piezas chicas
# intercaladas que caen en los huecos entre las grandes — y ese orden no se adivina: se BUSCA. Por eso:
#   1. la búsqueda de siempre (órdenes × criterios × giros, `_candidatos_busqueda`) da el punto de partida;
#   2. CARRILES independientes buscan cada uno con su semilla (en el navegador, a la vez en varios hilos;
#      acá, en orden: el resultado es el mismo): el carril 0 es lo de siempre, el 1 mejora el orden de la
#      búsqueda, los demás arrancan de órdenes mezclados; cada intento cambia el orden o el criterio y queda
#      si usa menos tela;
#   3. cada carril termina PULIDO: la última mesa se re-acomoda sola (MAPA 726) y cada pieza sube al lugar
#      libre más alto que tenga (`_compactar_hoja`): nunca alarga;
#   4. gana el carril de menos tela (empate: el de número más bajo).
# Todo REPETIBLE (semillas fijas, la misma cuenta en los dos motores). El carril 0 es exactamente lo de
# antes + compactar: nunca da peor que antes. Nada de formas ni reglas fijas: todo sale de las máscaras.
# ─────────────────────────────────────────────────────────────────────────────────────────────
CARRILES = 16
CARRILES_HASTA = 120          # piezas: con más, sin carriles (MAPA 732)
PRESUPUESTO_CARRIL = 800      # colocaciones de pieza por carril: intentos = esto // piezas (2 a 40)
COMPACTAR_HASTA = 120         # piezas por mesa: con más, la grilla tarda minutos (Copia de 593 banderines); queda el contorno (MAPA 732)


def optimizar_de_entorno():
    """`TIZADA_NESTING_OPTIMIZAR`: «0» = sin carriles (sólo la búsqueda de siempre, pulida); «CxI» = C carriles ×
    I intentos; sin poner, None (los de siempre). SÓLO para los contratos, que generan pedidos enteros en Python
    (16 carriles en Python tardan minutos): el servidor lo pone en el plan (`cfg_nesting.optimizar`) y así el
    navegador acomoda con lo mismo. El servidor de verdad no lo tiene puesto."""
    v = str(os.environ.get("TIZADA_NESTING_OPTIMIZAR") or "").strip().lower()
    if not v:
        return None
    if v in ("0", "no", "false"):
        return False
    try:
        c, i = (int(x) for x in v.split("x"))
        return {"carriles": max(1, c), "intentos": max(0, i)}
    except ValueError:
        return None


def parametros_optimizar(n, cfg):
    """(carriles, intentos por carril). `cfg["optimizar"]` = `{"carriles", "intentos"}` o `False`; sin la clave,
    la del entorno de los contratos (`optimizar_de_entorno`) o los de siempre."""
    o = (cfg or {}).get("optimizar")
    if o is None:
        o = optimizar_de_entorno()
    # 🔴 CON MÁS DE 120 PIEZAS, SIN CARRILES (MAPA 732): la Copia de 593 banderines tardaba minutos (gemelo de JS)
    if o is False or n < 3 or (n > CARRILES_HASTA and not (isinstance(o, dict) and o.get("carriles"))):
        return 1, 0
    ent = lambda v, mn: type(v) is int and v >= mn
    d = o if isinstance(o, dict) else {}
    carriles = d["carriles"] if ent(d.get("carriles"), 1) else CARRILES
    intentos = d["intentos"] if ent(d.get("intentos"), 0) else min(40, max(2, PRESUPUESTO_CARRIL // n))
    return carriles, intentos


def _alto_hoja(h):
    return max(c["cy"] + c["bh"] / 2 for c in h)


def _consumo(coloc):
    """La suma del largo de cada mesa (pt), en el orden de las mesas."""
    return sum(_alto_hoja(h) for h in coloc if h)


def _criterios(piezas, cfg):
    """Los criterios de colocación que compiten (los mismos en la búsqueda y en los carriles)."""
    estrategias = list(cfg.get("estrategias", ["bl", "bandas"]))
    if len(piezas) > 12:
        estrategias = ["bl"]
    # 🔴 EL MENOR HUECO COMPITE SIEMPRE (MAPA 714): es un criterio de colocación general (sale de las
    # máscaras, no de la forma) y gana sólo si deja la mesa más corta — nunca empeora lo de antes.
    if "hueco" not in estrategias:
        estrategias.append("hueco")
    # 🔴 Y EL MAYOR CONTACTO (MAPA 719): el que usa la FORMA para encastrar (mangas en los huecos, piezas
    # giradas que se meten una en otra). Hasta 200 piezas (el mismo límite que los órdenes): con cientos de
    # piezas chicas arma escaleras que dejan zonas enormes por revisar (689 banderines: 3 → 26 s).
    if "contacto" not in estrategias and len(piezas) <= 200:
        estrategias.append("contacto")
    return estrategias


def _variantes_giro(piezas):
    """🔴 GIRAR NO SIEMPRE ACORTA (MAPA 579): el acomodo es codicioso y con giros de costado puede dejar la
    mesa más larga que sin girar. Si alguna pieza puede ir de costado, se prueba TAMBIÉN sólo con 0° y 180°."""
    v = [None]
    if any(c[0] % 180 != 0 for p in piezas for c in p["_candidatos_angulo"]):
        v.append({0, 180})
    return v


def _candidatos_busqueda(piezas, cfg):
    """Los puntos de partida de la búsqueda, EN ORDEN (giros × órdenes × criterios): gana el primero de
    menos tela. Los ÓRDENES (MAPA 708): hasta 200 piezas, los cuatro (por área, alto, ancho y lado mayor);
    con más, sólo por área."""
    idx = list(range(len(piezas)))
    A = [int(piezas[i]["_mask"].sum()) for i in idx]
    Hh = [piezas[i]["_mask"].shape[0] for i in idx]
    Ww = [piezas[i]["_mask"].shape[1] for i in idx]
    if len(piezas) > 200:
        base = [sorted(idx, key=lambda i: A[i], reverse=True)]
    else:
        base = [sorted(idx, key=lambda i: A[i], reverse=True),
                sorted(idx, key=lambda i: Hh[i], reverse=True),
                sorted(idx, key=lambda i: Ww[i], reverse=True),
                sorted(idx, key=lambda i: max(Hh[i], Ww[i]), reverse=True)]
    ordenes, vistos = [], set()
    for o in base:
        if tuple(o) not in vistos:
            vistos.add(tuple(o))
            ordenes.append(o)
    return [{"orden": orden, "est": est, "solo_ang": solo_ang}
            for solo_ang in _variantes_giro(piezas) for orden in ordenes for est in _criterios(piezas, cfg)]


def _anidar_busqueda(piezas, cfg):
    """La búsqueda de siempre (MAPA 708 + 714 + 719): cada pieza en TODOS los giros que permite su regla y en
    TODAS las posiciones de la mesa; varios órdenes × criterios × giros, y gana el acomodo de MENOR consumo
    (el primero, en empate). → dict con `coloc`, `area`, `consumo` y el punto que ganó (`orden`, `est`,
    `solo_ang`). Gemelo: `anidarBusqueda` (contorno.js)."""
    if not piezas:
        return {"coloc": [], "area": 0.0, "consumo": 0, "orden": [], "est": "bl", "solo_ang": None}
    prep = _preparar(piezas, cfg)
    mejor = None
    for c in _candidatos_busqueda(piezas, cfg):
        coloc, area = _anidar_estrategia(piezas, cfg, c["est"], c["orden"], prep, c["solo_ang"])
        consumo = _consumo(coloc)
        if mejor is None or consumo < mejor["consumo"]:
            mejor = dict(c, coloc=coloc, area=area, consumo=consumo)
    return mejor


def _compactar_hoja(hoja, prep):
    """COMPACTAR una mesa (MAPA 728): cada pieza, de la que llega más abajo a la que llega más arriba, prueba
    subir al lugar libre más alto que tenga (con cualquiera de los giros que permite su regla), con las demás
    quietas; si lo hay, se muda. Se repite hasta que ninguna se mueve. Cada mudanza deja la pieza más arriba:
    la mesa nunca se alarga y el lugar que deja puede servirle a otra. Gemelo: `compactarHoja` (contorno.js)."""
    cell_pt, ancho_c, alto_c, esp_c, paso = prep
    h = []
    for c in hoja:
        k = next(t for t in c["pieza"]["_candidatos_angulo"] if t[0] == c["ang"])
        mt = k[2]
        h.append([c, k, math.floor(c["cx"] / cell_pt + esp_c - mt.shape[1] / 2 + 0.5),
                  math.floor(c["cy"] / cell_pt + esp_c - mt.shape[0] / 2 + 0.5)])
    # 🔴 COMO MUCHO 2 PASADAS (MAPA 732): sin tope, una Copia de 593 banderines pasaba minutos acá (gemelo de JS)
    cambio, pasadas = True, 0
    while cambio and pasadas < 2:
        pasadas += 1
        cambio = False
        orden = sorted(range(len(h)), key=lambda i: (-(h[i][3] + h[i][1][2].shape[0]), -i))
        for i in orden:
            c, k, x, y = h[i]
            fondo0 = y + k[2].shape[0]
            G = np.zeros((alto_c, ancho_c), bool)
            sky = 0
            for j, (_cj, kj, xj, yj) in enumerate(h):
                if j == i:
                    continue
                mt, mc = kj[2], kj[1]
                dy, dx = (mt.shape[0] - mc.shape[0]) // 2, (mt.shape[1] - mc.shape[1]) // 2
                G[yj + dy:yj + dy + mc.shape[0], xj + dx:xj + dx + mc.shape[1]] |= mc
                sky = max(sky, yj + mt.shape[0])
            ylim = min(alto_c, max(sky, fondo0))
            mejor = None
            for cand in c["pieza"]["_candidatos_angulo"]:
                mr_test = cand[2]
                hh = mr_test.shape[0]
                if ylim < hh or mr_test.shape[1] > ancho_c:
                    continue
                conv = fftconvolve(G[:ylim].astype(np.float32), mr_test[::-1, ::-1].astype(np.float32), mode="valid")
                valid = conv < 0.5
                if not valid.any():
                    continue
                yy, xx, score = _elegir_posicion(valid, hh, "bl")
                if mejor is None or score < mejor[0]:
                    mejor = (score, cand, yy, xx)
            if mejor is not None and mejor[2] + mejor[1][2].shape[0] < fondo0:
                _, cand, yy, xx = mejor
                ang, mr_test = cand[0], cand[2]
                hh, ww = mr_test.shape
                p = c["pieza"]
                th = math.radians(ang)
                bw = abs(p["w"] * math.cos(th)) + abs(p["h"] * math.sin(th))
                bh = abs(p["w"] * math.sin(th)) + abs(p["h"] * math.cos(th))
                h[i] = [dict(c, ang=ang, cx=(xx - esp_c + ww / 2) * cell_pt, cy=(yy - esp_c + hh / 2) * cell_pt, bw=bw, bh=bh),
                        cand, xx, yy]
                cambio = True
    return [e[0] for e in h]


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 🔴 COMPACTAR CON EL CONTORNO REAL (MAPA 731) — gemelo EXACTO de `compactarVector` (contorno.js)
#
# El acomodo trabaja sobre una grilla de 4 mm: cada pieza queda un poco más grande que su contorno y el aire
# entre piezas se redondea para arriba (pedido 11 mm = 5 de espaciado + los dos bordes; medido en la tizada del
# usuario: 16,8 mm de mediana). Al final cada pieza se DESLIZA con su contorno de verdad hacia arriba y hacia la
# izquierda hasta quedar EXACTAMENTE a la distancia pedida de sus vecinas (+ 0,3 mm de holgura). Sólo traslada;
# nunca alarga. El primer contacto al deslizar es un vértice de una pieza contra un borde de la otra (en los dos
# sentidos): dónde entra el vértice en la «cápsula» del borde (el segmento engordado), cerrado, sin iterar.
# ─────────────────────────────────────────────────────────────────────────────────────────────
HOLGURA_VECTOR_MM = 0.3
PASADAS_VECTOR = 6


def _capsula(v, ax, ay, bx, by, R, eje):
    """Dónde la recta (x = v con `eje` 0; y = v con 1) queda a distancia <= R del segmento ab → (lo, hi) o None."""
    if eje == 1:
        ax, ay = ay, ax
        bx, by = by, bx
    lo, hi = math.inf, -math.inf
    d = v - ax
    if -R <= d <= R:
        h = math.sqrt(R * R - d * d)
        lo = min(lo, ay - h); hi = max(hi, ay + h)
    d = v - bx
    if -R <= d <= R:
        h = math.sqrt(R * R - d * d)
        lo = min(lo, by - h); hi = max(hi, by + h)
    sx, sy = bx - ax, by - ay
    L = math.sqrt(sx * sx + sy * sy)
    if L > 0:
        nx, ny, dx, dy = -sy / L, sx / L, sx / L, sy / L
        a0, a1 = -math.inf, math.inf
        c1 = nx * (v - ax)
        if abs(ny) > 1e-12:
            u, w = ay + (-R - c1) / ny, ay + (R - c1) / ny
            if u > w:
                u, w = w, u
            a0 = max(a0, u); a1 = min(a1, w)
        elif abs(c1) > R:
            a1 = -math.inf
        c2 = dx * (v - ax)
        if abs(dy) > 1e-12:
            u, w = ay + (0 - c2) / dy, ay + (L - c2) / dy
            if u > w:
                u, w = w, u
            a0 = max(a0, u); a1 = min(a1, w)
        elif c2 < 0 or c2 > L:
            a1 = -math.inf
        if a0 <= a1:
            lo = min(lo, a0); hi = max(hi, a1)
    return (lo, hi) if lo <= hi else None


def _compactar_vector(hoja, cfg):
    """COMPACTAR UNA MESA CON EL CONTORNO REAL (ver arriba) → la mesa con las piezas deslizadas."""
    if not hoja:
        return hoja
    esp = float(cfg.get("espaciado_cm", 0.5)) * CM
    holg = HOLGURA_VECTOR_MM / 10 * CM
    P = []
    for c in hoja:
        b = c["pieza"]["base"]
        B = float(b.get("B") or 0)
        P.append({"c": dict(c), "loc": poligonos_contorno(b["cont"], b["S"], b["x0"], b["y0"], B),
                  "Wp": float(b["W"]) + 2 * B, "Hp": float(b["Hp"]), "B": B, "W": None, "bb": None})

    def ubicar(e):
        co, si = float(cosdg(e["c"]["ang"])), float(sindg(e["c"]["ang"]))
        cx, cy, w2, h2 = e["c"]["cx"], e["c"]["cy"], e["Wp"] / 2, e["Hp"] / 2
        x0 = y0 = math.inf
        x1 = y1 = -math.inf
        W = []
        for pl in e["loc"]:
            out = []
            for px, py in pl:
                u, v = px - w2, py - h2
                X, Y = cx + u * co - v * si, cy - (u * si + v * co)
                out.append((X, Y))
                x0 = min(x0, X); x1 = max(x1, X); y0 = min(y0, Y); y1 = max(y1, Y)
            W.append(out)
        e["W"], e["bb"] = W, (x0, y0, x1, y1)

    for e in P:
        ubicar(e)
    Bmax = max(e["B"] for e in P)
    Rmax = esp + 2 * Bmax + holg

    def contra(A, Bw, R, eje, t, signo):
        o, q = eje, 1 - eje
        for ra in A:
            for pt in ra:
                v, pos = pt[o], pt[q]
                for rb in Bw:
                    n = len(rb)
                    for s in range(n):
                        ax, ay = rb[s]
                        bx, by = rb[(s + 1) % n]
                        ea, eb = (ax, bx) if eje == 0 else (ay, by)
                        if v < min(ea, eb) - R or v > max(ea, eb) + R:
                            continue
                        iv = _capsula(v, ax, ay, bx, by, R, eje)
                        if iv is None:
                            continue
                        if signo > 0:
                            if iv[1] <= pos + 1e-9:
                                t = min(t, pos - iv[1])
                            elif iv[0] < pos:
                                return 0
                        else:
                            if iv[0] >= pos - 1e-9:
                                t = min(t, iv[0] - pos)
                            elif iv[1] > pos:
                                return 0
                        if t <= 0:
                            return 0
        return t

    def deslizar(i, eje):
        e = P[i]
        bi = e["bb"]
        t = e["c"]["cy"] - e["c"]["bh"] / 2 if eje == 0 else e["c"]["cx"] - e["c"]["bw"] / 2
        if t <= 1e-9:
            return 0
        lo, hi, a0, a1 = (0, 2, 1, 3) if eje == 0 else (1, 3, 0, 2)
        cands = [j for j in range(len(P)) if j != i and not (P[j]["bb"][lo] > bi[hi] + Rmax or P[j]["bb"][hi] < bi[lo] - Rmax
                                                                or P[j]["bb"][a0] >= bi[a1])]
        cands.sort(key=lambda j: (-P[j]["bb"][a1], j))
        for j in cands:
            ej = P[j]
            R = esp + e["B"] + ej["B"] + holg
            if ej["bb"][a1] < bi[a0] - t - R:
                break
            t = contra(e["W"], ej["W"], R, eje, t, 1)
            if t <= 0:
                return 0
            t = contra(ej["W"], e["W"], R, eje, t, -1)
            if t <= 0:
                return 0
        return t

    for _ in range(PASADAS_VECTOR):
        movio = False
        for eje in (0, 1, 0):
            k = 1 if eje == 0 else 0
            orden = sorted(range(len(P)), key=lambda i: (P[i]["bb"][k], i))
            for i in orden:
                t = deslizar(i, eje)
                if t > 1e-6:
                    if eje == 0:
                        P[i]["c"]["cy"] -= t
                    else:
                        P[i]["c"]["cx"] -= t
                    ubicar(P[i])
                    movio = True
        if not movio:
            break
    return [e["c"] for e in P]


def _pulir(cfg, coloc, prep):
    """El final de cada carril: la última mesa sola (MAPA 726) y compactar cada mesa. Nunca alarga."""
    col = list(coloc)
    llenas = [i for i, h in enumerate(col) if h]
    if len(llenas) >= 2:
        # 🔴 LA ÚLTIMA MESA SE VUELVE A ACOMODAR SOLA (MAPA 726): sus piezas son las que quedaron al final; con
        # la búsqueda completa entre ellas suelen ocupar menos. Sólo si queda en UNA mesa y más corta.
        ult = llenas[-1]
        h2 = [h for h in _anidar_busqueda([c["pieza"] for c in col[ult]], cfg)["coloc"] if h]
        if len(h2) == 1 and _alto_hoja(h2[0]) < _alto_hoja(col[ult]) - 1e-6:
            col[ult] = h2[0]
    return [(_compactar_hoja(h, prep) if h and len(h) <= COMPACTAR_HASTA else h) for h in col]


def _carril(piezas, cfg, k, inicio):
    """UN CARRIL del optimizador (MAPA 728) — gemelo EXACTO de `carril` (contorno.js). `inicio` = el mejor
    punto de la búsqueda (`orden`, `est`, `solo_ang`). Carril 0: ese mismo acomodo, pulido (lo de antes).
    Carril 1: busca desde ahí. Los demás: desde un orden MEZCLADO (el área de cada pieza con ruido, por la
    semilla del carril). Cada intento: un orden nuevo mezclado (1 de 4) o el mejor con 1 a 3 cambios (dos
    piezas de lugar o una movida), a veces otro criterio; queda si usa menos tela (o igual y deja menos pieza
    en la última mesa). → (coloc, consumo)."""
    prep = _preparar(piezas, cfg)
    sa_ini = set(inicio["solo_ang"]) if inicio["solo_ang"] is not None else None
    if k == 0:
        coloc, _ = _anidar_estrategia(piezas, cfg, inicio["est"], inicio["orden"], prep, sa_ini)
        col = _pulir(cfg, coloc, prep)
        return col, _consumo(col)

    def evaluar(orden, est, sa):
        coloc, _ = _anidar_estrategia(piezas, cfg, est, orden, prep, sa)
        return {"c": _consumo(coloc), "a": _area_ultima(coloc), "coloc": coloc}

    mejor = _buscar_carril(piezas, cfg, k, inicio, evaluar)
    col = _pulir(cfg, mejor["coloc"], prep)
    return col, _consumo(col)


def _area_ultima(col):
    """Cuánta pieza (celdas) quedó en la última mesa (0 con una sola mesa). Gemelo: `areaUltima`."""
    ll = [h for h in col if h]
    if len(ll) < 2:
        return 0
    return sum(int(c["pieza"]["_mask"].sum()) for c in ll[-1])


def _clave_combinacion(est, sa):
    """La clave de una combinación de criterio y giros. Gemelo: `claveCombinacion`."""
    return f"{est}|{','.join(str(a) for a in sorted(sa))}" if sa is not None else f"{est}|"


def _buscar_carril(piezas, cfg, k, inicio, evaluar):
    """LA BÚSQUEDA DE UN CARRIL (k ≥ 1), sin pulir: `evaluar(orden, est, sa)` → dict con `c` y `a` (acomoda o,
    con piezas todas iguales, trae la cuenta ya hecha). → el mejor intento. Gemelo: `buscarCarril`."""
    n = len(piezas)
    sa_ini = set(inicio["solo_ang"]) if inicio["solo_ang"] is not None else None
    _, intentos = parametros_optimizar(n, cfg)
    A = [int(p["_mask"].sum()) for p in piezas]
    ests, vars_ = _criterios(piezas, cfg), _variantes_giro(piezas)
    st = k * 7919 + 17                       # la semilla del carril: fija, el resultado se repite

    def u():
        nonlocal st
        st = (st * 1103515245 + 12345) & 0x7fffffff
        return st / 2147483648

    def mezclado():
        r = 0.2 + 0.6 * u()
        clave = [a * (1 + r * (u() - 0.5)) for a in A]
        return sorted(range(n), key=lambda i: clave[i], reverse=True)

    mejor = None

    def probar(orden, est, sa):
        nonlocal mejor
        r = evaluar(orden, est, sa)
        if mejor is None or r["c"] < mejor["c"] - 1e-9 or (abs(r["c"] - mejor["c"]) <= 1e-9 and r["a"] <= mejor["a"]):
            mejor = dict(r, orden=orden, est=est, sa=sa)

    if k == 1:
        probar(inicio["orden"], inicio["est"], sa_ini)
    else:
        probar(mezclado(), ests[k % len(ests)], vars_[k % len(vars_)])
    for _ in range(intentos):
        est = mejor["est"]
        if u() < 0.25:
            o = mezclado()
            est = ests[math.floor(u() * len(ests))]
        else:
            o = list(mejor["orden"])
            m = 1 + math.floor(u() * 3)
            for _q in range(m):
                i = math.floor(u() * n)
                j = math.floor(u() * n)
                if u() < 0.5:
                    o[i], o[j] = o[j], o[i]
                else:
                    o.insert(j, o.pop(i))
            if u() < 0.15:
                est = ests[math.floor(u() * len(ests))]
        probar(o, est, mejor["sa"])
    return mejor


# ─────────────────────────────────────────────────────────────────────────────────────────────
# 🔴 EL PATRÓN (MAPA 736) — gemelo EXACTO de `anidarPatron` (frontend/src/motor/nesting/contorno.js)
#
# El usuario, con 102 banderas iguales que salieron unas derechas y otras inclinadas sin orden: «el sistema no
# tiene que buscar bandera por bandera el mejor espacio: tiene que ver todas las que tenemos y qué espacio van a
# ocupar; hacer los cálculos —las rotaciones y todo— con todo junto, y ahí decir cómo irá acomodado». El acomodo
# de siempre es pieza por pieza (cada una donde mejor queda AHORA): con piezas iguales nunca «ve» el dibujo que se
# repite. Acá se calcula ese dibujo: con TODAS las piezas en la cuenta, la UNIDAD que se repite (las formas en
# proporción) y el PERÍODO a lo largo de la mesa en el que entran más unidades por metro, probando cada giro que
# permite la regla en cada lugar de una franja que se repite (lo que sale por abajo vuelve a entrar por arriba: la
# franja se calcula con sus copias de arriba y de abajo). Ese dibujo se repite a lo largo de la mesa con todas las
# piezas. NADA de formas fijas: todo sale de las máscaras; compite con el acomodo de siempre y gana el que gasta
# menos tela. Acá los lugares salen de la FFT (como `_anidar_estrategia`); en el navegador, de los bits.
# ─────────────────────────────────────────────────────────────────────────────────────────────
PATRON_MIN_PIEZAS = 2          # desde 2 piezas iguales (gemelo: con 5 banderines no se probaba)
# 🔴 SIN TOPE DE PIEZAS POR UNIDAD (2026-10-20): con unidades grandes la franja lleva al menos 2 unidades, se busca
# con menos largos y sin forzar giros. Gemelo: `PATRON_UNIDAD_CHICA` (contorno.js)
PATRON_UNIDAD_CHICA = 6        # hasta acá: los giros forzados y el barrido fino
PATRON_MAX_POR_PERIODO = 12    # piezas por período como mucho
PATRON_PASOS = 32              # el barrido grueso del período (medido: 48 da los mismos dibujos con 25 % más de cuenta)

_FIRMAS = {}


def _huella(m):
    """Alto, ancho, celdas y la suma de las posiciones (1…) de las celdas prendidas. Gemelo: `huella`."""
    idx = np.flatnonzero(m.ravel())
    return f"{m.shape[0]}x{m.shape[1]}:{len(idx)}:{int((idx + 1).sum())}"


def _firma_cands(cands):
    """La firma de los giros de una pieza, una vez por lista de giros. Gemelo: `firmaCands`."""
    r = _FIRMAS.get(id(cands))
    if r is None or r[0] is not cands:
        r = (cands, "|".join(f"{a}/{_huella(mc)}/{_huella(mt)}" for a, mc, mt in cands))
        _FIRMAS[id(cands)] = r
    return r[1]


def _cands_iguales(a, b):
    """¿Los mismos giros con las mismas máscaras, celda por celda? Gemelo: `candsIguales`."""
    if a is b:
        return True
    if len(a) != len(b):
        return False
    for ka, kb in zip(a, b):
        if ka[0] != kb[0] or ka[1].shape != kb[1].shape or ka[2].shape != kb[2].shape:
            return False
        if not (np.array_equal(ka[1], kb[1]) and np.array_equal(ka[2], kb[2])):
            return False
    return True


def _siluetas_distintas(cands):
    """Los giros que prueba el patrón: uno por silueta (mismo tamaño y no más del 1 % de celdas distintas; queda el
    primero). Gemelo: `siluetasDistintas`."""
    out = []
    for k in cands:
        a = k[2]
        igual = False
        for o in out:
            b = o[2]
            if a.shape == b.shape and int(np.count_nonzero(a != b)) * 100 <= max(int(a.sum()), int(b.sum())):
                igual = True
                break
        if not igual:
            out.append(k)
    return out


def _todas_iguales(piezas):
    """¿Todas las piezas tienen la MISMA forma? Gemelo: `todasIguales`."""
    if len(piezas) < 2:
        return False
    c0 = piezas[0]["_candidatos_angulo"]
    ok = {id(c0)}
    for p in piezas:
        c = p["_candidatos_angulo"]
        if id(c) in ok:
            continue
        if _firma_cands(c) != _firma_cands(c0) or not _cands_iguales(c, c0):
            return False
        ok.add(id(c))
    return True


def _unidad_patron(piezas):
    """La UNIDAD que se repite: las formas en proporción. Gemelo: `unidadPatron`."""
    if len(piezas) < PATRON_MIN_PIEZAS:
        return None
    formas, de_firma = [], {}
    for p in piezas:
        fk = _firma_cands(p["_candidatos_angulo"])
        f = de_firma.get(fk)
        if f is not None and not _cands_iguales(f["cands"], p["_candidatos_angulo"]):
            f = None
        if f is None:
            f = {"cands": p["_candidatos_angulo"], "piezas": []}
            if fk not in de_firma:
                de_firma[fk] = f
            formas.append(f)
        f["piezas"].append(p)
    for f in formas:
        f["candsP"] = _siluetas_distintas(f["cands"])
    g = 0
    for f in formas:
        g = math.gcd(g, len(f["piezas"]))
    if g < 2:
        return None
    U = sum(len(f["piezas"]) // g for f in formas)
    orden = sorted(range(len(formas)), key=lambda i: (-int(formas[i]["piezas"][0]["_mask"].sum()), i))
    unidad = []
    for i in orden:
        unidad.extend([i] * (len(formas[i]["piezas"]) // g))
    return {"formas": formas, "unidad": unidad, "veces": g, "total": len(piezas)}


def _estampar_recorte(G, yy, xx, mc):
    """`G[...] |= mc` con las filas que caen fuera de la grilla recortadas."""
    R = G.shape[0]
    y0, y1 = max(0, yy), min(R, yy + mc.shape[0])
    if y0 < y1:
        G[y0:y1, xx:xx + mc.shape[1]] |= mc[y0 - yy:y1 - yy]


_PROPIAS = {}


def _choca_consigo(k, p):
    """¿La pieza choca con SUS PROPIAS copias de la franja (una cada `p` filas)? Gemelo: `chocaConsigo`."""
    clave = (id(k[2]), p)
    r = _PROPIAS.get(clave)
    if r is not None and r[0] is k[2]:
        return r[1]
    mt, mc = k[2], k[1]
    dy, dx = (mt.shape[0] - mc.shape[0]) // 2, (mt.shape[1] - mc.shape[1]) // 2
    choca = False
    j = 1
    while not choca and j * p < mt.shape[0] + mc.shape[0]:
        for sg in (1, -1):
            oy = dy + sg * j * p
            y0, y1 = max(0, oy), min(mt.shape[0], oy + mc.shape[0])
            if y0 < y1 and (mt[y0:y1, dx:dx + mc.shape[1]] & mc[y0 - oy:y1 - oy]).any():
                choca = True
                break
        j += 1
    _PROPIAS[clave] = (k[2], choca)
    return choca


def _lugar_franja(G, mt, desde, hasta, orden):
    """El mejor lugar de la franja (tops en las filas `desde` a `hasta`) según `orden`: «arriba» (más arriba, más
    a la izquierda), «arriba-der» (más arriba, más a la derecha) o «columna» (más a la izquierda, más arriba).
    Gemelo: `lugarFranja` (allá se poda con el mejor de otro giro; el resultado es el mismo)."""
    hh, ww = mt.shape
    if G.shape[1] - ww < 0 or hasta < desde:
        return None
    conv = fftconvolve(G[desde:hasta + hh].astype(np.float32), mt[::-1, ::-1].astype(np.float32), mode="valid")
    ys, xs = np.nonzero(conv < 0.5)
    if not len(ys):
        return None
    if orden == "columna":
        x = int(xs.min())
        return [desde + int(ys[xs == x].min()), x]
    y = int(ys[0])
    if orden == "arriba-der":
        return [desde + y, int(xs[ys == y].max())]
    return [desde + y, int(xs[0])]


def _gana_lugar(a, b, orden):
    if orden == "columna":
        return a[1] < b[1] or (a[1] == b[1] and a[0] < b[0])
    if orden == "arriba-der":
        return a[0] < b[0] or (a[0] == b[0] and a[1] > b[1])
    return a[0] < b[0] or (a[0] == b[0] and a[1] < b[1])


def _franja_patron(U, p, Hm, ancho_c, modo, forzar, paso):
    """UNA FRANJA DE LARGO `p`: se llenan lugares en el orden de la unidad, cada pieza con el giro y el lugar que
    gana según el modo, hasta que no entra la que sigue. Gemelo: `franjaPatron`."""
    R = p + 2 * Hm
    G = np.zeros((R, ancho_c), bool)
    col = []
    unidad = U["unidad"]
    for i in range(min(U["total"], max(PATRON_MAX_POR_PERIODO, min(2 * len(unidad), 24)))):   # gemelo de `maxPeriodo`
        fi = unidad[i % len(unidad)]
        orden = "columna" if modo == "columna" else ("arriba-der" if modo == "alterna" and i % 2 == 1 else "arriba")
        cands = U["formas"][fi]["candsP"]
        if forzar and i < len(forzar):
            f = [k for k in cands if k[0] == forzar[i]]
            if f:
                cands = f
        fases = [cands]
        if len(cands) > 8:
            g = [k for k in cands if k[0] % 90 == 0]
            if g and len(g) < len(cands):
                fases = [g, None]
        mejor = None

        def probar(lista):
            nonlocal mejor
            for k in lista:
                if _choca_consigo(k, p):
                    continue
                hasta = min(Hm + p - 1, R - k[2].shape[0])
                r = _lugar_franja(G, k[2], Hm, hasta, orden)
                if r is None:
                    continue
                if mejor is None or _gana_lugar(r, [mejor[1], mejor[2]], orden):
                    mejor = (k, r[0], r[1])

        probar(fases[0])
        if len(fases) > 1:
            vistos = {id(k) for k in fases[0]}
            if mejor is None:
                resto = [k for k in cands if id(k) not in vistos]
            else:
                a0 = mejor[0][0]
                resto = [k for k in cands if id(k) not in vistos
                         and min(abs(k[0] - a0), 360 - abs(k[0] - a0)) <= 2 * max(1, int(paso))]
            probar(resto)
        if mejor is None:
            break
        k, y, x = mejor
        mt, mc = k[2], k[1]
        dy, dx = (mt.shape[0] - mc.shape[0]) // 2, (mt.shape[1] - mc.shape[1]) // 2
        # la pieza y sus copias de arriba y de abajo (las que asoman a la grilla)
        j = -(-(y + mt.shape[0]) // p)
        j = -j
        while y + dy + j * p < R:
            _estampar_recorte(G, y + dy + j * p, x + dx, mc)
            j += 1
        col.append({"forma": fi, "k": k, "y": y - Hm, "x": x})
    unidades = len(col) // len(unidad)
    return {"p": p, "colocadas": col[:unidades * len(unidad)], "unidades": unidades}


def _franja_mejor(a, b):
    """Densidad de a (unidades / largo) contra b, sin dividir; empate: el más corto. Gemelo: `franjaMejor`."""
    da, db = a["unidades"] * b["p"], b["unidades"] * a["p"]
    return da > db if da != db else a["p"] < b["p"]


def _modos_patron(U):
    """Los MODOS de la franja que compiten (en este orden; empate: el primero). Gemelo: `modosPatron`."""
    vistas, clases = set(), []
    for a, mc, mt in U["formas"][U["unidad"][0]]["candsP"]:
        s = f"{mt.shape[0]},{mt.shape[1]}"   # el TAMAÑO girado, no las celdas (ver `modosPatron`)
        if s not in vistas:
            vistas.add(s)
            clases.append(a)
    cl = clases
    if len(cl) > 4:
        r = [a for a in cl if a % 90 == 0]
        cl = r or cl[:4]
    out = []
    nU = len(U["unidad"])   # gemelo de `modosPatron`: con unidades grandes, menos modos
    lista = ("arriba", "alterna", "columna") if nU <= PATRON_UNIDAD_CHICA else (("alterna", "columna") if nU <= 2 * PATRON_UNIDAD_CHICA + 2 else ("alterna",))
    for modo in lista:
        out.append({"modo": modo, "forzar": None})
        # las tres primeras con el mismo giro (medido: arranca el dibujo que la de a una no ve)
        if len(cl) > 1 and len(U["unidad"]) <= PATRON_UNIDAD_CHICA:
            for a in cl:
                out.append({"modo": modo, "forzar": [a, a, a]})
    return out


def _largos_patron(U, ancho_c):
    h_min = min(k[2].shape[0] for f in U["formas"] for k in f["cands"])
    h_max = max(k[2].shape[0] for f in U["formas"] for k in f["cands"])
    # con una unidad grande la franja tiene que poder llevar su área: el largo máximo crece (gemelo: `largosPatron`)
    au = sum(int(U["formas"][fi]["cands"][0][1].sum()) for fi in U["unidad"])
    p_lo, p_hi = max(1, math.floor(h_min * 0.4)), math.ceil(max(h_max, 1.3 * au / ancho_c) * 2.5)
    pasos = 10 if len(U["unidad"]) > PATRON_UNIDAD_CHICA else PATRON_PASOS
    # `Math.round` de JS (no el redondeo bancario de Python)
    return h_max, p_lo, p_hi, max(1, math.floor((p_hi - p_lo) / pasos + 0.5))


def _mejor_franja_modo(U, prep, m):
    """EL MEJOR LARGO DE UN MODO: barrido grueso y, alrededor de los 3 mejores, el largo más corto en el que
    todavía entran las mismas unidades (bisección). Gemelo: `mejorFranjaModo`."""
    from functools import cmp_to_key
    Hm, p_lo, p_hi, paso = _largos_patron(U, prep[1])
    de_largo = {}
    mejor = None

    def probar(p):
        nonlocal mejor
        if p not in de_largo:
            f = _franja_patron(U, p, Hm, prep[1], m["modo"], m["forzar"], prep[4])
            de_largo[p] = f if f["unidades"] else None
            if f["unidades"] and (mejor is None or _franja_mejor(f, mejor)):
                mejor = f
        return de_largo[p]

    gruesos = list(range(p_lo, p_hi + 1, paso))
    for p in gruesos:
        probar(p)
    if mejor is None:
        return None

    def cmp(a, b):
        fa, fb = de_largo[a], de_largo[b]
        if _franja_mejor(fa, fb):
            return -1
        if _franja_mejor(fb, fa):
            return 1
        return a - b

    top = sorted([p for p in gruesos if de_largo.get(p)], key=cmp_to_key(cmp))
    for p0 in top[:3]:
        u0 = de_largo[p0]["unidades"]
        lo, hi = max(p_lo, p0 - paso + 1), p0
        while lo < hi:
            mid = (lo + hi) >> 1
            f = probar(mid)
            if f and f["unidades"] >= u0:
                hi = mid
            else:
                lo = mid + 1
    return dict(mejor, modo=m["modo"], forzar=m["forzar"])


def _anidar_patron(piezas, cfg, prep=None):
    """EL PATRÓN REPETIDO EN LA MESA → (coloc, consumo, info) o None. Gemelo: `anidarPatron`."""
    prep = prep or _preparar(piezas, cfg)
    U = _unidad_patron(piezas)
    if U is None:
        return None
    F = None
    for m in _modos_patron(U):
        f = _mejor_franja_modo(U, prep, m)
        if f and (F is None or _franja_mejor(f, F)):
            F = f
    if F is None:
        return None
    cell_pt, _, alto_c, esp_c, _ = prep
    el = sorted([dict(c, i=i) for i, c in enumerate(F["colocadas"])], key=lambda e: (e["y"], e["i"]))
    k, p = len(el), F["p"]
    por_forma = [len(f["piezas"]) for f in U["formas"]]

    def armar(s):
        fila = sorted([dict(e, y=(e["y"] - el[s]["y"] if j >= s else e["y"] - el[s]["y"] + p)) for j, e in enumerate(el)],
                      key=lambda e: (e["y"], e["i"]))
        falta, out = list(por_forma), []
        t = 0
        while len(out) < len(piezas):
            puso = False
            for e in fila:
                if not falta[e["forma"]]:
                    continue
                falta[e["forma"]] -= 1
                out.append(dict(e, y=t * p + e["y"]))
                puso = True
            if not puso:
                break
            t += 1
        return out

    mejor = None
    for s in range(k):
        out = armar(s)
        largo = 0
        for e in out:
            largo = max(largo, e["y"] + e["k"][2].shape[0])
        if mejor is None or largo < mejor[0]:
            mejor = (largo, out, s)
    usadas = [0] * len(U["formas"])
    coloc = [[]]
    base = 0
    for e in mejor[1]:
        mt = e["k"][2]
        hh, ww = mt.shape
        if e["y"] - base + hh > alto_c:
            if not coloc[-1]:
                return None
            coloc.append([])
            base = e["y"]
        pz = U["formas"][e["forma"]]["piezas"][usadas[e["forma"]]]
        usadas[e["forma"]] += 1
        ang = e["k"][0]
        th = math.radians(ang)
        bw = abs(pz["w"] * math.cos(th)) + abs(pz["h"] * math.sin(th))
        bh = abs(pz["w"] * math.sin(th)) + abs(pz["h"] * math.cos(th))
        coloc[-1].append({"pieza": pz, "ang": ang, "cx": (e["x"] - esp_c + ww / 2) * cell_pt,
                          "cy": (e["y"] - base - esp_c + hh / 2) * cell_pt, "bw": bw, "bh": bh})
    return coloc, _consumo(coloc), {"periodo": p, "por_periodo": k, "modo": F["modo"], "arranque": mejor[2]}


def anidar_contorno(piezas, cfg):
    """LA TIZADA MÁS EFICIENTE (MAPA 708 + 714 + 719 + 726 + 728) → (colocaciones, área de las piezas cm²).
    La búsqueda de siempre da el punto de partida y los CARRILES del optimizador buscan uno mejor; gana el
    de menos tela. Lo usan TODOS los modos (normal, Copia, talles por mesa o separados, diseños separados).
    Trabaja sólo con el CONTORNO del molde (la máscara). Gemelo EXACTO: `anidarContorno` (contorno.js), que
    corre los carriles en varios hilos con el mismo resultado."""
    if not piezas:
        return [], 0.0
    prep = _preparar(piezas, cfg)
    area = sum(int(p["_mask"].sum()) for p in piezas) * (prep[0] / CM) ** 2
    carriles, _ = parametros_optimizar(len(piezas), cfg)
    # 🔴 PIEZAS TODAS IGUALES (MAPA 736): cambiar el orden de piezas idénticas no cambia el acomodo —sólo el
    # criterio y los giros—, así que cada carril repetía las MISMAS cuentas. Con piezas iguales cada combinación
    # se acomoda UNA vez (la búsqueda ya las prueba todas), los carriles se recorren con esas cuentas (mismas
    # semillas: terminan en la misma combinación que antes) y se pule sólo cada combinación distinta en la que
    # terminan. El MISMO largo que los carriles, sin repetir nada. Gemelo: `anidarContorno`.
    iguales = carriles > 1 and _todas_iguales(piezas)
    cands = _candidatos_busqueda(piezas, cfg)
    rs_b = []
    for c in cands:
        coloc, _ = _anidar_estrategia(piezas, cfg, c["est"], c["orden"], prep, c["solo_ang"])
        rs_b.append((_consumo(coloc), _area_ultima(coloc)))
    ib = 0
    for i in range(1, len(rs_b)):
        if rs_b[i][0] < rs_b[ib][0]:
            ib = i
    b = cands[ib]
    inicio = {"orden": b["orden"], "est": b["est"],
              "solo_ang": sorted(b["solo_ang"]) if b["solo_ang"] is not None else None}
    if iguales:
        cuenta = {}
        for c, (cons, ult) in zip(cands, rs_b):
            cuenta.setdefault(_clave_combinacion(c["est"], c["solo_ang"]), dict(c, c=cons, a=ult))
        finales = [_clave_combinacion(inicio["est"], inicio["solo_ang"])]
        for k in range(1, carriles):
            m = _buscar_carril(piezas, cfg, k, inicio, lambda orden, est, sa: cuenta[_clave_combinacion(est, sa)])
            finales.append(_clave_combinacion(m["est"], m["sa"]))
        pulidos, resultados = {}, []
        for kc in finales:
            if kc not in pulidos:
                c = cuenta[kc]
                coloc, _ = _anidar_estrategia(piezas, cfg, c["est"], c["orden"], prep, c["solo_ang"])
                col = _pulir(cfg, coloc, prep)
                pulidos[kc] = (col, _consumo(col))
            resultados.append(pulidos[kc])
    else:
        resultados = [_carril(piezas, cfg, k, inicio) for k in range(carriles)]
    mejor = None
    for col, cons in resultados:
        if mejor is None or cons < mejor[1]:
            mejor = (col, cons)
    # 🔴 y al final, con el CONTORNO REAL (MAPA 731): cada pieza a la distancia exacta de sus vecinas
    coloc = [(_compactar_vector(h, cfg) if h else h) for h in mejor[0]]
    # 🔴 EL PATRÓN (MAPA 736): con piezas iguales, el dibujo que se repite calculado con TODAS juntas compite con
    # el acomodo pieza por pieza, YA con el contorno real; gana sólo si gasta menos tela (en empate, el de siempre)
    pat = _anidar_patron(piezas, cfg, prep)
    _DEBUG["patron"] = None
    if pat:
        cp = [(_compactar_vector(h, cfg) if h else h) for h in pat[0]]
        gano = _consumo(cp) < _consumo(coloc) - 1e-9
        _DEBUG["patron"] = dict(pat[2], consumo=_consumo(cp), gano=gano)
        if gano:
            coloc = cp
    return coloc, area


def _copias_de(fila, k):
    """`k` copias de las piezas de una fila (objetos aparte: comparten la máscara ya calculada). Cada copia
    sabe qué número de copia es y qué pieza de la fila (`_copia_i`, `_pieza_i`): con eso la Copia mezclada
    pone en cada lugar la pieza de la fila que le toca (MAPA 717)."""
    return [dict(p, _copia_i=i, _pieza_i=j) for i in range(k) for j, p in enumerate(fila)]


def _area_hoja(hoja, cell_pt):
    """El área de las piezas de una hoja (cm²), con la misma cuenta que el acomodo (celdas × celda²)."""
    return sum(int(c["pieza"]["_mask"].sum()) for c in hoja) * (cell_pt / CM) ** 2


def repartir_copias(fila, copias, cfg, hoja1=None, area1=None):
    """COPIA: LA MESA LLENA QUE SE REPITE (MAPA 720, reemplaza a la franja de la 703). El usuario: «cuando
    pongo copias no reducir la mesa a una sola fila del tamaño del objeto: acomodar en el tamaño máximo de la
    mesa y, si la cantidad concuerda con que esa mesa se debe repetir varias veces, en vez de crear la mesa
    varias veces se pone esa mesa varias copias». Se acomodan juntas las copias que hacen falta para LLENAR
    una mesa del largo máximo (`altura_max_cm`: el del nesting o el del botón «Largo»), con el acomodo de
    siempre: la primera mesa trae `n` copias COMPLETAS (una copia partida entre dos mesas se saca de la
    primera) y se imprime `copias // n` veces; el resto (`copias % n`) va en su mesa con el largo que
    necesite. Si todas entran en una mesa: una sola, con todas. Para no acomodar de más se acomodan como
    mucho las que entran por superficie + 1 (más no pueden entrar en una mesa; la primera queda llena
    igual). Devuelve `[(colocaciones, {"copias", "por_mesa"}, area)]` o None (una sola copia, o ni una
    copia entera entra en la mesa). `hoja1`/`area1` ya no se usan (quedan por compatibilidad).
    Gemelo EXACTO: `repartirCopias` (frontend/src/motor/nesting/contorno.js)."""
    if not fila or copias < 2:
        return None
    cell_pt, ancho_c, alto_c, _, _ = _preparar(fila, cfg)
    celdas = sum(int(p["_mask"].sum()) for p in fila) or 1
    k = min(copias, (alto_c * ancho_c) // celdas + 1)
    coloc, _ = anidar_contorno(_copias_de(fila, k), cfg)
    hojas = [h for h in coloc if h]
    if not hojas:
        return None
    if len(hojas) == 1 and k == copias:
        return [(hojas[0], {"copias": 1, "por_mesa": copias}, _area_hoja(hojas[0], cell_pt))]
    per = len(fila)
    cuenta = {}
    for c in hojas[0]:
        ci = c["pieza"].get("_copia_i", 0)
        cuenta[ci] = cuenta.get(ci, 0) + 1
    enteras = sorted(ci for ci, v in cuenta.items() if v == per)
    n = len(enteras)
    if n == 0:
        return None
    nuevo = {ci: i for i, ci in enumerate(enteras)}
    # la mesa llena con sus copias numeradas 0…n-1 (la Copia mezclada reparte esos lugares, MAPA 717)
    lleno = [dict(c, pieza=dict(c["pieza"], _copia_i=nuevo[c["pieza"].get("_copia_i", 0)]))
             for c in hojas[0] if c["pieza"].get("_copia_i", 0) in nuevo]
    llenas, resto = divmod(copias, n)
    res = [(lleno, {"copias": llenas, "por_mesa": n}, _area_hoja(lleno, cell_pt))]
    if resto:
        cr, _ = anidar_contorno(_copias_de(fila, resto), cfg)
        for h in cr:
            if h:
                res.append((h, {"copias": 1, "por_mesa": max(1, len(h) // per)}, _area_hoja(h, cell_pt)))
    return res


# LA BANDA ENTRE TALLES SEPARADOS (MAPA 711): el rótulo de arriba (7 mm de letra) + 3 mm + la línea
# (1,2 mm) + 3 mm + el rótulo de abajo, además del espaciado de siempre. ~2,6 cm: se nota sin gastar tela de
# más. Gemelo: `SEP_BANDA_MM` (contorno.js); el dibujo, `hoja_pike.ops_cortes`.
SEP_TEXTO_MM, SEP_AIRE_MM, SEP_LINEA_MM = 7.0, 3.0, 1.2
SEP_BANDA_MM = 2 * (SEP_TEXTO_MM + SEP_AIRE_MM) + SEP_LINEA_MM


def _firma_geo(p):
    """La GEOMETRÍA EXACTA de una pieza (MAPA 717): medida, giro permitido, borde y el contorno con el que
    se arma su máscara. Dos piezas con la misma firma ocupan lo mismo en la mesa, así que una puede ir en el
    lugar de la otra (el mismo molde con OTRO diseño). None = sin contorno: no se mezcla. Gemelo: `firmaGeo`."""
    b = p.get("base") if isinstance(p.get("base"), dict) else None
    c = b.get("cont") if b else None
    if not isinstance(c, dict) or not c.get("segmentos"):
        return None
    return (float(p["w"]), float(p["h"]), str(p.get("rotacion") or ""), float(p.get("borde_cm") or 0),
            tuple(float(b.get(k) or 0) for k in ("S", "x0", "y0", "B", "W", "Hp")),
            tuple(tuple(x if isinstance(x, str) else float(x) for x in s) for s in c["segmentos"]))


def _patron(resto, n):
    """Cuántas de cada fila van en una mesa de `n` lugares (MAPA 717): en PROPORCIÓN a lo que le falta a
    cada una (la parte entera; los lugares que quedan, a las de mayor resto — en empate, la primera). Nunca
    más de lo que le falta a una fila. Gemelo: `patronCopia`."""
    tot = sum(resto)
    p = [n * r // tot for r in resto]
    falta = n - sum(p)
    for i in sorted(range(len(resto)), key=lambda i: (-(n * resto[i] % tot), i)):
        if falta <= 0:
            break
        if p[i] < resto[i]:
            p[i] += 1
            falta -= 1
    return p


def _info_copia(filas, cuenta, copias):
    """`{fila…, copias, por_mesa}` de una mesa de Copia. `cuenta` = {índice en `filas`: {copias de esa fila
    en la mesa}}; con más de una fila: `fila: None` + `filas: [{fila, por_mesa}]` (MAPA 717)."""
    nro = lambda i: filas[i][0] + 1 if filas[i][0] >= 0 else None
    fs = sorted(cuenta)
    n_mesa = sum(len(cuenta[i]) for i in fs)
    if len(fs) == 1:
        return {"fila": nro(fs[0]), "copias": copias, "por_mesa": n_mesa}
    return {"fila": None, "filas": [{"fila": nro(i), "por_mesa": len(cuenta[i])} for i in fs], "copias": copias, "por_mesa": n_mesa}


def _copia_llenas(filas, cfg):
    """COPIA: LAS MESAS LLENAS QUE SE REPITEN (MAPA 720 + 725). `filas` = [(k, piezas, copias)] con la MISMA
    pieza (`_firma_geo`: el mismo molde Y el mismo talle; el diseño o el texto pueden cambiar). Con
    `repartir_copias` se sabe cuántas entran en una mesa del largo máximo (`n`); sus lugares se reparten entre
    las filas en PROPORCIÓN (`_patron`) y cada patrón se imprime `k` veces mientras quede para llenar una mesa
    entera (33 + 34 con lugar para 7 → 3+4 ×8 y 6+1 ×1). Cada lugar lleva la pieza DE VERDAD de su fila.
    Devuelve `(mesas, sobra)`: `mesas` = [(hoja, info, area)] y `sobra` = cuántas copias de cada fila NO
    llenan una mesa — esas van con todo lo demás, JUNTAS (`_copia_por_filas`). Si todas entran en una mesa
    no hay nada que repetir: todo sobra. Gemelo: `copiaLlenas`."""
    resto = [c for _, _, c in filas]
    total = sum(resto)
    if total < 2:
        return [], resto
    # si todas juntas no ocupan ni MEDIA mesa (por la CAJA de cada pieza, que es más que la pieza), no llenan
    # una: no hace falta acomodarlas para saberlo. Nada se pierde: igual van al pozo, juntas. Por la caja y no
    # por la máscara: preparar las máscaras acá costaba 1,4 s y dejaba esas piezas armadas distinto que las
    # demás del pozo (el navegador acomodaba ese pozo 1,5 s más lento).
    m = cfg["margenes_cm"]
    sup_mesa = (float(cfg["ancho_cm"]) - m["izq"] - m["der"]) * (float(cfg.get("altura_max_cm") or 500) - m["sup"] - m["inf"]) * CM * CM
    if 2 * total * sum(float(p["w"]) * float(p["h"]) for p in filas[0][1]) <= sup_mesa:
        return [], resto
    rep = repartir_copias(filas[0][1], total, cfg)
    if not rep or (len(rep) == 1 and rep[0][1]["copias"] == 1 and rep[0][1]["por_mesa"] == total):
        return [], resto
    n = rep[0][1]["por_mesa"]            # `repartir_copias` pone primero la mesa llena (n <= total)
    lleno, a_lleno = rep[0][0], rep[0][2]
    res = []
    while sum(resto) >= n:
        p = _patron(resto, n)
        k = min(resto[i] // p[i] for i in range(len(p)) if p[i] > 0)
        fila_de_copia = [i for i in range(len(p)) for _ in range(p[i])]
        out, cuenta = [], {}
        for c in lleno:
            ci = c["pieza"].get("_copia_i", 0)
            fi = fila_de_copia[ci]
            out.append(dict(c, pieza=dict(filas[fi][1][c["pieza"].get("_pieza_i", 0)])))
            cuenta.setdefault(fi, set()).add(ci)
        res.append((out, _info_copia(filas, cuenta, k), a_lleno))
        resto = [resto[i] - k * p[i] for i in range(len(p))]
    return res, resto


def _copia_por_filas(piezas, cfg, sep_dis, nombre_dis):
    """COPIA (MAPA 581 → 703 → 720 → 725). La cantidad de cada fila son COPIAS. Las filas con la misma pieza
    (mismo molde y talle; `_firma_geo`) forman una familia y, si alcanza, salen en MESAS LLENAS que se
    imprimen ×N (`_copia_llenas`). 🔴 TODO LO QUE NO LLENA UNA MESA VA JUNTO, con el acomodo de siempre y los
    talles MEZCLADOS — el usuario: «¿por qué me separó por talle si no apreté la opción Mesas?» (la 717 hacía
    una mesa por familia = una por talle: 19,7 m contra 15,5 m sin Copia). Separar talles es SÓLO el botón
    «Mesas»; separar diseños, SÓLO «Separar» (`sep_dis`: un pozo por diseño). Las mesas del pozo se imprimen
    ×1 y dicen qué filas llevan (`filas`). Gemelo EXACTO: `copiaPorFilas` (contorno.js)."""
    grupos = {}
    for p in piezas:
        k = p.get("_fila")
        k = k if isinstance(k, int) else -1
        grupos.setdefault(k, []).append(p)
    familias = []
    for k in sorted(grupos):
        g = grupos[k]
        dk = str(g[0].get("_diseno") or "") if sep_dis else ""
        fg = [_firma_geo(x) for x in g]
        if k >= 0 and None not in fg:
            fam = next((f for f in familias if f["firma"] == fg and f["dis"] == dk), None)
            if fam is not None:
                fam["filas"].append(k)
                continue
            familias.append({"firma": fg, "dis": dk, "filas": [k]})
        else:
            familias.append({"firma": None, "dis": dk, "filas": [k]})
    colocaciones, mesas, area = [], [], 0.0
    sobra_de, dis_de = {}, {}                # fila → copias que no llenan una mesa · fila → su pozo
    for fam in familias:
        filas = []
        for k in fam["filas"]:
            g = grupos[k]
            try:
                c = max(1, int(float(g[0].get("_copias") or 1))) if k >= 0 else 1
            except (TypeError, ValueError):
                c = 1
            filas.append((k, g, c))
        llenas, sobra = _copia_llenas(filas, cfg) if fam["filas"][0] >= 0 else ([], [c for _, _, c in filas])
        dis = {"diseno": nombre_dis.get(fam["dis"])} if sep_dis else {}
        for h, info, a in llenas:
            colocaciones.append(h)
            mesas.append({**info, **dis})
            area += a
        for (k, _, _), r in zip(filas, sobra):
            sobra_de[k] = r
            dis_de[k] = fam["dis"]
    # el pozo en el ORDEN DE LAS FILAS (como sin Copia: mismo acomodo y mismo tiempo); uno por diseño con «Separar»
    pozo, orden_pozo = {}, []
    for k in sorted(grupos):
        dk = dis_de.get(k, "")
        if dk not in pozo:
            pozo[dk] = []
            orden_pozo.append(dk)
        for inst in range(sobra_de.get(k, 0)):
            pozo[dk].extend(dict(p, _copia_i=inst, _pieza_i=j) for j, p in enumerate(grupos[k]))
    for dk in orden_pozo:
        pz = pozo[dk]
        if not pz:
            continue
        coloc, _ = anidar_contorno(pz, cfg)
        cell_pt = _preparar(pz, cfg)[0]
        dis = {"diseno": nombre_dis.get(dk)} if sep_dis else {}
        for h in coloc:
            if not h:
                continue
            cuenta = {}
            for c in h:
                f = c["pieza"].get("_fila")
                f = f if isinstance(f, int) else -1
                cuenta.setdefault(f, set()).add(c["pieza"].get("_copia_i", 0))
            fs = sorted(cuenta)
            nro = lambda f: f + 1 if f >= 0 else None
            n_mesa = sum(len(cuenta[f]) for f in fs)
            info = ({"fila": nro(fs[0]), "copias": 1, "por_mesa": n_mesa} if len(fs) == 1 else
                    {"fila": None, "filas": [{"fila": nro(f), "por_mesa": len(cuenta[f])} for f in fs], "copias": 1, "por_mesa": n_mesa})
            colocaciones.append(h)
            mesas.append({**info, **dis})
            area += _area_hoja(h, cell_pt)
    return colocaciones, area, mesas


def anidar_por_fila(piezas, cfg):
    """COPIA (MAPA 581): con `cfg['por_fila']`, cada FILA de la planilla (`pieza['_fila']`) se
    acomoda SOLA y sale en su(s) propia(s) mesa(s), en el orden de las filas. Devuelve
    `(colocaciones, area, mesas)`; `mesas` = una entrada por mesa `{fila (1…), copias}` (la cantidad
    de la fila como DATO, ya no multiplica prendas).
    COPIA (MAPA 725): `_copia_por_filas` — las mesas LLENAS que se repiten aparte y TODO lo demás junto
    (talles mezclados); las mesas con varias filas traen `fila: None` y `filas: [{fila, por_mesa}]`.
    TALLES POR MESA (MAPA 593): con `cfg['por_talles_mesa']`, cada GRUPO de talles que eligió la
    persona (`pieza['_grupo_mesa']` = 1, 2, …) se acomoda SOLO y sale en su(s) propia(s) mesa(s), en
    el orden de los grupos; los talles que no están en ningún grupo van juntos al final, como siempre.
    `mesas` = `{grupo (1… o None = el resto), talles: [...]}`. Copia manda sobre los grupos (cada
    fila ya es su mesa). Sin ninguna de las dos: `mesas` = None y lo de siempre.
    TALLES SEPARADOS EN LA MISMA MESA (MAPA 710): con `cfg['talles_mesa_modo'] == 'separados'` cada
    grupo se acomoda SOLO (el mejor acomodo de siempre) y los bloques se APILAN uno debajo del otro en
    la misma mesa, con una línea punteada entre bloque y bloque; si el que sigue no entra en el largo
    máximo, arranca otra mesa. Así salen menos mesas sin mezclar talles. `mesas` = `{grupo: None,
    talles: [...], separados: True, cortes: [y de cada línea, pt]}` (los compositores dibujan las líneas).
    SEPARAR DISEÑOS (MAPA 717): sin `cfg['separar_disenos']` el mismo molde se mezcla aunque cambie el
    diseño (regla del usuario); con él, cada diseño (`pieza['_diseno']`, en el orden en que aparece) va
    en su(s) propia(s) mesa(s) en cualquier modo, y cada mesa dice su `diseno` (`_diseno_nombre`).
    Mismo algoritmo que `anidarPorFila` del navegador."""
    cfg = cfg or {}
    por_fila = bool(cfg.get("por_fila"))
    por_talles = (not por_fila) and bool(cfg.get("por_talles_mesa"))
    sep_dis = bool(cfg.get("separar_disenos"))
    if not por_fila and not por_talles and not sep_dis:
        coloc, area = anidar_contorno(piezas, cfg)
        return coloc, area, None
    _RESTO = 10 ** 9                      # los talles sin grupo: juntos y AL FINAL
    _DIS = 10 ** 10                       # el diseño va primero en la clave (separar diseños)
    orden_dis, nombre_dis = {}, {}
    for p in piezas:
        d = str(p.get("_diseno") or "")
        if d not in orden_dis:
            orden_dis[d] = len(orden_dis)
            nombre_dis[d] = str(p.get("_diseno_nombre") or p.get("_diseno") or "") or None
    if por_fila:
        return _copia_por_filas(piezas, cfg, sep_dis, nombre_dis)
    grupos = {}
    for p in piezas:
        if por_talles:
            k = p.get("_grupo_mesa")
            k = k if isinstance(k, int) and not isinstance(k, bool) and k >= 1 else _RESTO
        else:
            k = 0
        if sep_dis:
            k = orden_dis[str(p.get("_diseno") or "")] * _DIS + k
        grupos.setdefault(k, []).append(p)
    colocaciones, mesas, area = [], [], 0.0
    separados = por_talles and cfg.get("talles_mesa_modo") == "separados"
    bloques = []                          # (hoja, talles, diseño) — sólo con «separados»
    _dis_de = lambda g: nombre_dis.get(str(g[0].get("_diseno") or "")) if sep_dis else None
    for k in sorted(grupos):
        g = grupos[k]
        coloc, a = anidar_contorno(g, cfg)
        if por_talles:
            # los talles de la mesa, en el orden en que llegan las piezas (el de la planilla)
            _tl = list(dict.fromkeys(str(x.get("talle")) for x in g if x.get("talle") not in (None, "")))
        _no_vacias = [h for h in coloc if h]
        _dx = {"diseno": _dis_de(g)} if sep_dis else {}
        for h in _no_vacias:
            if separados:
                bloques.append((h, list(_tl), _dis_de(g)))
                continue
            colocaciones.append(h)
            if por_talles:
                _gk = k % _DIS if sep_dis else k
                mesas.append({"grupo": _gk if _gk != _RESTO else None, "talles": list(_tl), **_dx})
            else:
                mesas.append(dict(_dx))
        area += a
    if separados:
        m = cfg["margenes_cm"]
        alto_max = (float(cfg.get("altura_max_cm") or 500) - m["sup"] - m["inf"]) * CM
        esp = float(cfg["espaciado_cm"] if cfg.get("espaciado_cm") is not None else 0.5) * CM
        banda = SEP_BANDA_MM * CM / 10
        actual = None
        previos = []                                   # los talles del bloque de arriba
        for h, tl, dis in bloques:
            hh = max(c["cy"] + c["bh"] / 2 for c in h)
            # entre bloque y bloque: el espaciado + la banda de la línea con sus rótulos; separando
            # diseños, otro diseño arranca otra mesa (MAPA 717)
            if actual is None or (actual["h"] and actual["y"] + banda + hh > alto_max + 1e-6) or actual["dis"] != dis:
                actual = {"h": [], "y": 0.0, "talles": [], "cortes": [], "dis": dis}
                colocaciones.append(actual["h"])
                mesas.append(actual)
            elif actual["h"]:
                actual["cortes"].append({"y": actual["y"] - esp / 2 + banda / 2, "arriba": list(previos), "abajo": list(tl)})
                actual["y"] += banda
            actual["h"].extend(dict(c, cy=c["cy"] + actual["y"]) for c in h)
            actual["talles"].extend(t for t in tl if t not in actual["talles"])
            actual["y"] += hh + esp
            previos = tl
        for i, x in enumerate(mesas):
            mesas[i] = {"grupo": None, "talles": x["talles"], "separados": True, "cortes": x["cortes"],
                        **({"diseno": x["dis"]} if sep_dis else {})}
    return colocaciones, area, mesas


def _anidar_estrategia(piezas, cfg, estrategia, orden, prep, solo_ang=None):
    """Coloca las piezas en el `orden` dado con la `estrategia`. Devuelve
    (hojas, area_piezas_cm2). hoja = [colocacion, ...]. `solo_ang`: sólo esos ángulos (si a una
    pieza no le queda ninguno, los suyos)."""
    cell_pt, ancho_c, alto_c, esp_c, paso = prep
    hojas_G, hojas_sky, colocaciones = [], [], []
    hojas_prof = []        # por hoja y columna: la fila siguiente a la última ocupada (estrategia «hueco»)
    _perf = {}             # el perfil inferior de cada máscara, una vez por máscara

    def perfil(mr_col):
        r = _perf.get(id(mr_col))
        if r is None:
            r = _perf[id(mr_col)] = (mr_col, *_perfil_inferior(mr_col))
        return r[1], r[2]

    def marcar_prof(h_idx, y0, x0, mr_col):
        b, cols = perfil(mr_col)
        pr = hojas_prof[h_idx]
        np.maximum.at(pr, x0 + cols, y0 + b[cols])

    def nueva_hoja():
        hojas_G.append(np.zeros((alto_c, ancho_c), bool))
        hojas_sky.append(0)
        hojas_prof.append(np.zeros(ancho_c, np.int64))
        colocaciones.append([])
        return len(hojas_G) - 1

    nueva_hoja()
    area_piezas_c2 = 0
    _DEBUG.update({"bloque": 0, "fft": 0, "sin_geo": 0, "sin_ultimo": 0, "sin_lugar": 0})

    for i in orden:
        p = piezas[i]
        candidatos_por_angulo = p["_candidatos_angulo"]
        if solo_ang is not None:
            candidatos_por_angulo = [c for c in candidatos_por_angulo if c[0] in solo_ang] or candidatos_por_angulo
        if not candidatos_por_angulo:
            # con el largo de mesa del pedido (MAPA 716) esto pasa cuando el largo elegido es más corto que la pieza
            _an = f"{float(cfg['ancho_cm']):g}".replace(".", ",")          # coma decimal, como en la pantalla
            _la = f"{float(cfg['altura_max_cm']) / 100:g}".replace(".", ",")
            raise ValueError(f"«{p.get('pieza') or p['etiqueta']}» (talle {p.get('talle') or '-'}) no entra en una mesa de "
                             f"{_an} cm de ancho × {_la} m de largo con el giro "
                             "que tiene permitido: hace falta una tela más ancha o un largo de mesa mayor.")

        colocada = False
        _DEBUG["fft"] += 1
        # 🔴 LOS GIROS QUE PERMITE SU REGLA, EN TODAS LAS POSICIONES (MAPA 708): nada de copiar el giro o
        # el lugar de la pieza anterior igual. Gana el lugar más abajo y más a la izquierda; cada pieza
        # con SU mejor giro. Con giro LIBRE (24 giros) se busca en dos pasos: los múltiplos de 90° y
        # después los vecinos del mejor (±2 pasos) — medido igual tela que probar los 24, 4× más rápido.
        if p.get("rotacion") == "libre" and len(candidatos_por_angulo) > 8:
            _fases = [[c for c in candidatos_por_angulo if c[0] % 90 == 0] or candidatos_por_angulo[:4], None]
        else:
            _fases = [candidatos_por_angulo]
        for h_idx in range(len(hojas_G)):
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
                hueco = None
                if estrategia == "hueco":
                    b, cols = perfil(mr_col)
                    hueco = (hojas_prof[h_idx], b, cols, (hh - mr_col.shape[0]) // 2, (ww - mr_col.shape[1]) // 2)
                elif estrategia == "contacto":
                    hueco = (_contacto(G[:ylim], mr_test), sky)
                y, x, score = _elegir_posicion(valid, hh, estrategia, hueco)
                if mejor is None or score < mejor[0]:
                    mejor = (score, ang, mr_col, mr_test, y, x)
            if mejor:
                _, ang, mr_col, mr_test, y, x = mejor
                hh, ww = mr_test.shape
                # estampar la ocupación real (contorno + borde propio, sin el espaciado)
                dy, dx = (hh - mr_col.shape[0]) // 2, (ww - mr_col.shape[1]) // 2
                G[y + dy:y + dy + mr_col.shape[0], x + dx:x + dx + mr_col.shape[1]] |= mr_col
                marcar_prof(h_idx, y + dy, x + dx, mr_col)
                hojas_sky[h_idx] = max(hojas_sky[h_idx], y + hh)
                # bbox matemático exacto del vector rotado, centrado en la celda de la máscara
                th = math.radians(ang)
                bw = abs(p["w"] * math.cos(th)) + abs(p["h"] * math.sin(th))
                bh = abs(p["w"] * math.sin(th)) + abs(p["h"] * math.cos(th))
                cx = (x - esp_c + ww / 2) * cell_pt      # la grilla empieza `esp_c` antes de la mesa
                cy = (y - esp_c + hh / 2) * cell_pt
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
            marcar_prof(h_idx, y + dy, x + dx, mr_col)
            hojas_sky[h_idx] = y + hh
            th = math.radians(ang)
            bw = abs(p["w"] * math.cos(th)) + abs(p["h"] * math.sin(th))
            bh = abs(p["w"] * math.sin(th)) + abs(p["h"] * math.cos(th))
            colocaciones[h_idx].append({"pieza": p, "ang": ang,
                                        "cx": (x - esp_c + ww / 2) * cell_pt, "cy": (y - esp_c + hh / 2) * cell_pt,
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
