"""LOS DIBUJOS TÉCNICOS DEL MOLDE A MEDIDA EN LA FICHA (MAPA 659).

Pedido del usuario (2026-10-09): «para la ficha técnica de los moldes a medida, que sea más específica y
visualmente detallista, mostrando y explicando los dobleces, etc.». Antes la sección «MEDIDA Y
TERMINACIÓN» era sólo texto (`servidor._ficha_a_medida`: filas + notas). Ahora además lleva:

  · PLANO DE LA PIEZA: la pieza a escala con el contorno de corte, la guía del diseño (donde se dobla),
    la costura y las tiras, con cotas del total y del diseño;
  · LA TERMINACIÓN: el borde en CORTE, paso a paso (cortado → doblado hacia el revés → cosido; o el
    overlock), y la esquina (o la punta del triángulo) de cerca, CORTADA y DOBLADA: se ve el recorte y
    cómo se superponen las solapas sin que sobre nada;
  · CÓMO SE TERMINA: los pasos numerados, con las medidas de ESTE pedido.

🔴 LAS DOS FICHAS (servidor `ficha_tecnica.py` y navegador `motor/ficha/ficha.js`) SÓLO DIBUJAN. Toda la
geometría se calcula UNA vez acá y viaja como trazos listos —mismo criterio que las filas redactadas—:
`[{alto, ops}]` por bloque, con `ops` en puntos relativos al bloque (x desde el margen de la hoja):
  · `{"k": "l", "p": [[x, y], …], "c": rgb|None, "w": ancho, "d": rayas|None, "f": rgb|None, "h": cerrar}`
    = `page.draw_polyline(…)` de PyMuPDF (las rayas como el `dashes` de PyMuPDF: "[3 2] 0");
  · `{"k": "t", "x", "y", "s", "z": tamaño, "c": rgb, "b": negrita}` = `_texto` de la ficha (y = base).
Así no hay geometría gemela que mantener en JS: sólo dos primitivas (`dibujarPolilinea` + `texto`).

La geometría es la MISMA del motor (no un dibujo aproximado): `MP._geo_triangulo` (solapas y recortes),
`MP._segmentos_tiras` (las marcas que imprime la tizada), `MP._triangulo_corrido` (la costura) y el
rectángulo con las esquinas recortadas (MAPA 653, gemelo de `rectRecortado`).
"""
import math

import motor_pedido as MP

try:
    import pymupdf as _fitz
except Exception:                       # sin PyMuPDF se mide aproximado (no pasa en el servidor)
    _fitz = None

A4_W = 595.28
MARGEN = 36
CW = A4_W - 2 * MARGEN                  # el ancho útil de la ficha

NEGRO = (0.1, 0.1, 0.1)
GRIS = (0.45, 0.45, 0.45)
GRIS_C = (0.75, 0.75, 0.75)
AZUL = (0.0, 0.42, 0.82)                # la GUÍA del diseño = por dónde se dobla
NARANJA = (0.93, 0.48, 0.08)            # la COSTURA (la misma naranja de la plantilla)
TELA = (0.93, 0.95, 0.97)               # la pieza
SOLAPA = (0.84, 0.87, 0.92)             # el margen doblado
TELA_C = (0.55, 0.58, 0.62)             # la tela en corte
TINTA = (0.85, 0.2, 0.55)               # la cara impresa

RAYAS_GUIA = "[4 2] 0"
RAYAS_COSTURA = "[1.5 1.5] 0"


def _cm(v):
    return f"{round(float(v) * 10) / 10:g}".replace(".", ",")


def _ancho_texto(s, z, b=False):
    if _fitz is None:
        return len(s) * z * 0.5
    return _fitz.get_text_length(s, fontname="hebo" if b else "helv", fontsize=z)


class _Lienzo:
    """Junta los trazos de UN bloque (coordenadas en puntos, y hacia ABAJO)."""

    def __init__(self):
        self.ops = []

    def linea(self, pts, color=NEGRO, ancho=1.0, rayas=None, relleno=None, cerrar=False):
        p = [[round(float(x), 2), round(float(y), 2)] for x, y in pts]
        if len(p) < 2:
            return
        self.ops.append({"k": "l", "p": p, "c": list(color) if color else None, "w": round(float(ancho), 2),
                         "d": rayas, "f": list(relleno) if relleno else None, "h": bool(cerrar)})

    def texto(self, x, y, s, z=8.0, color=NEGRO, b=False, alinear="izq"):
        s = str(s)
        if alinear != "izq":
            w = _ancho_texto(s, z, b)
            x = x - (w if alinear == "der" else w / 2)
        self.ops.append({"k": "t", "x": round(float(x), 2), "y": round(float(y), 2), "s": s, "z": z,
                         "c": list(color), "b": bool(b)})

    def flecha(self, x, y, dx, dy, color=GRIS, largo=4.0, medio=1.5):
        """Punta de flecha llena con la punta en (x, y), apuntando hacia (dx, dy)."""
        n = math.hypot(dx, dy) or 1
        ux, uy = dx / n, dy / n
        bx, by = x - ux * largo, y - uy * largo
        self.linea([(x, y), (bx - uy * medio, by + ux * medio), (bx + uy * medio, by - ux * medio)],
                   color=None, relleno=color, cerrar=True)

    def punto(self, x, y, r=1.7, color=NEGRO, lleno=True):
        pts = [(x + r * math.cos(2 * math.pi * k / 12), y + r * math.sin(2 * math.pi * k / 12)) for k in range(12)]
        if lleno:
            self.linea(pts, color=None, relleno=color, cerrar=True)
        else:
            self.linea(pts, color=color, ancho=0.6, cerrar=True)

    def cota_h(self, x0, x1, y, txt, arriba=True, color=GRIS):
        self.linea([(x0, y), (x1, y)], color=color, ancho=0.5)
        if x1 - x0 > 10:
            self.flecha(x0, y, -1, 0, color)
            self.flecha(x1, y, 1, 0, color)
        self.texto((x0 + x1) / 2, y - 3 if arriba else y + 9, txt, z=8, color=NEGRO, alinear="centro")

    def cota_v(self, x, y0, y1, txt, izquierda=True, color=GRIS):
        self.linea([(x, y0), (x, y1)], color=color, ancho=0.5)
        if y1 - y0 > 10:
            self.flecha(x, y0, 0, -1, color)
            self.flecha(x, y1, 0, 1, color)
        ym = (y0 + y1) / 2 + 3
        if izquierda:
            self.texto(x - 3, ym, txt, z=8, color=NEGRO, alinear="der")
        else:
            self.texto(x + 3, ym, txt, z=8, color=NEGRO)

    def caja(self, x0, y0, x1, y1, color=GRIS_C):
        self.linea([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], color=color, ancho=0.6, cerrar=True)


# ─── recortes (para los detalles de cerca) ──────────────────────────────────────────────────────
def _clip_seg(p, q, w):
    """Liang-Barsky: el tramo p-q dentro de la ventana w = (x0, y0, x1, y1), o None."""
    x0, y0, x1, y1 = w
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return None
            continue
        r = qq / pp
        if pp < 0:
            if r > t1:
                return None
            t0 = max(t0, r)
        else:
            if r < t0:
                return None
            t1 = min(t1, r)
    return (p[0] + t0 * dx, p[1] + t0 * dy), (p[0] + t1 * dx, p[1] + t1 * dy)


def _clip_polilinea(pts, w, cerrar=False):
    """Una polilínea recortada a la ventana: una lista de polilíneas (los tramos que quedan adentro)."""
    seq = list(pts) + ([pts[0]] if cerrar and pts else [])
    out, cur = [], None
    for a, b in zip(seq, seq[1:]):
        c = _clip_seg(a, b, w)
        if c is None:
            cur = None
            continue
        if cur is not None and abs(cur[-1][0] - c[0][0]) < 1e-9 and abs(cur[-1][1] - c[0][1]) < 1e-9:
            cur.append(c[1])
        else:
            cur = [c[0], c[1]]
            out.append(cur)
    return out


def _clip_poligono(pts, w):
    """Sutherland-Hodgman: el polígono recortado a la ventana (para los rellenos)."""
    x0, y0, x1, y1 = w
    bordes = ((lambda p: p[0] >= x0, lambda a, b: (x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0]))),
              (lambda p: p[0] <= x1, lambda a, b: (x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0]))),
              (lambda p: p[1] >= y0, lambda a, b: (a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0)),
              (lambda p: p[1] <= y1, lambda a, b: (a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1)))
    out = list(pts)
    for dentro, corte in bordes:
        if not out:
            break
        ent, out = out, []
        for i, b in enumerate(ent):
            a = ent[i - 1]
            if dentro(b):
                if not dentro(a):
                    out.append(corte(a, b))
                out.append(b)
            elif dentro(a):
                out.append(corte(a, b))
    return out


def _circulo(cx, cy, r, n=144):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _reflejar(p, a, n):
    """El punto `p` reflejado sobre la recta que pasa por `a` con normal unitaria `n` (el doblez)."""
    d = (p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1]
    return (p[0] - 2 * d * n[0], p[1] - 2 * d * n[1])


# ─── la geometría de la pieza (cm, y hacia ARRIBA, origen en la esquina del total) ────────────────
def _geometria(forma, orient, term, an_cm, al_cm, mg, W, H):
    """{contorno, guia, costura, circulo?, solapas, rec}: los mismos contornos que arma el alta del molde."""
    mi, md, ma, mb = (float(mg.get(k) or 0) for k in ("izq", "der", "arriba", "abajo"))
    mu = MP._margen_uniforme(mg)
    g = {"forma": forma, "rec": False, "costura": None, "solapas": []}
    if forma == "circulo":
        R, rg = W / 2, an_cm / 2
        g.update(contorno=_circulo(R, R, R), guia=_circulo(R, R, rg), centro=(R, R), R=R, rg=rg)
        if term == "dobladillo" and mu > 0 and rg - mu > 0:
            g["costura"] = _circulo(R, R, rg - mu)
        g["caja_diseno"] = (R - rg, R - rg, R + rg, R + rg)
        return g
    if forma == "triangulo":
        rec = term != "overlock"
        t = mu if term != "sin" else 0.0
        geo = MP._geo_triangulo(an_cm, al_cm, t, orient, rec)
        G = [tuple(p) for p in geo["guia"]]
        g.update(contorno=[tuple(p) for p in geo["pol"]], guia=G, rec=rec and t > 0, G=G, t=t)
        if term == "dobladillo" and t > 0 and MP._incentro(G)[2] - t > 0:
            g["costura"] = MP._triangulo_corrido(G, -t)
        if term == "dobladillo" and t > 0:
            for i in range(3):          # cada solapa y su reflejo sobre el lado (= doblada)
                a, b = G[i], G[(i + 1) % 3]
                ux, uy, nx, ny, _L, ca, cb, tt = MP._solapa_tri(G, i, t)
                sol = [a, (a[0] + tt * ca * ux + tt * nx, a[1] + tt * ca * uy + tt * ny),
                       (b[0] - tt * cb * ux + tt * nx, b[1] - tt * cb * uy + tt * ny), b]
                g["solapas"].append([_reflejar(p, a, (nx, ny)) for p in sol])
        xs, ys = [p[0] for p in G], [p[1] for p in G]
        g["caja_diseno"] = (min(xs), min(ys), max(xs), max(ys))
        return g
    # RECTÁNGULO: con dobladillo, las esquinas recortadas del tamaño del margen (MAPA 653)
    rec = term == "dobladillo" and (mi > 0 or md > 0 or ma > 0 or mb > 0)
    if rec:
        g["contorno"] = [(mi, 0), (W - md, 0), (W - md, mb), (W, mb), (W, H - ma), (W - md, H - ma), (W - md, H),
                         (mi, H), (mi, H - ma), (0, H - ma), (0, mb), (mi, mb)]
    else:
        g["contorno"] = [(0, 0), (W, 0), (W, H), (0, H)]
    g["guia"] = [(mi, mb), (W - md, mb), (W - md, H - ma), (mi, H - ma)]
    g["rec"] = rec
    g["m"] = (mi, md, ma, mb)
    if term == "dobladillo" and W - 2 * (mi + md) > 0 and H - 2 * (ma + mb) > 0 and (mi or md or ma or mb):
        g["costura"] = [(2 * mi, 2 * mb), (W - 2 * md, 2 * mb), (W - 2 * md, H - 2 * ma), (2 * mi, H - 2 * ma)]
    if rec:                             # las solapas dobladas por la guía (abajo, derecha, arriba, izquierda)
        g["solapas"] = [s for s in (
            [(mi, mb), (W - md, mb), (W - md, 2 * mb), (mi, 2 * mb)] if mb > 0 else None,
            [(W - md, mb), (W - md, H - ma), (W - 2 * md, H - ma), (W - 2 * md, mb)] if md > 0 else None,
            [(mi, H - ma), (W - md, H - ma), (W - md, H - 2 * ma), (mi, H - 2 * ma)] if ma > 0 else None,
            [(mi, mb), (mi, H - ma), (2 * mi, H - ma), (2 * mi, mb)] if mi > 0 else None) if s]
    g["caja_diseno"] = (mi, mb, W - md, H - ma)
    return g


# ─── 1 · EL PLANO DE LA PIEZA ────────────────────────────────────────────────────────────────────
def _bloque_plano(g, W, H, an_cm, al_cm, tiras_segs, tiras, borde_txt):
    L = _Lienzo()
    L.texto(0, 10, "PLANO DE LA PIEZA", z=9.5, b=True)
    AX0, AX1, TOP, HMAX = 58.0, CW - 58.0, 40.0, 195.0
    s = min((AX1 - AX0) / W, HMAX / H)
    pw, ph = W * s, H * s
    px0 = AX0 + ((AX1 - AX0) - pw) / 2
    py0 = TOP
    P = lambda x, y: (px0 + x * s, py0 + (H - y) * s)
    L.texto(CW, 10, f"escala aprox. 1:{max(1, round(28.3465 / s))} · medidas en cm", z=7.5, color=GRIS, alinear="der")
    circ = g["forma"] == "circulo"
    # la pieza (relleno) y su contorno de corte
    L.linea([P(*p) for p in g["contorno"]], color=NEGRO, ancho=1.0, relleno=TELA, cerrar=True)
    if g["guia"] is not None and g["contorno"] != g["guia"]:
        L.linea([P(*p) for p in g["guia"]], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA, cerrar=True)
    if g["costura"]:
        L.linea([P(*p) for p in g["costura"]], color=NARANJA, ancho=0.8, rayas=RAYAS_COSTURA, cerrar=True)
    # las tiras: la marca real (del borde a la guía) + un punto afuera para encontrarla a esta escala
    marcar = bool(tiras and tiras.get("marcar", True))
    for x1, y1, x2, y2 in tiras_segs:
        a, b = P(x1, y1), P(x2, y2)
        dx, dy = a[0] - b[0], a[1] - b[1]
        n = math.hypot(dx, dy) or 1
        L.linea([a, b], color=NEGRO if marcar else GRIS, ancho=1.2, rayas=None if marcar else "[1 1] 0")
        L.punto(a[0] + dx / n * 4.5, a[1] + dy / n * 4.5, color=NEGRO if marcar else GRIS, lleno=marcar)
    # cotas: el DISEÑO arriba (y a la derecha), el TOTAL abajo (y a la izquierda)
    # las líneas de referencia salen de los puntos EXTREMOS de cada contorno (en el triángulo, la esquina
    # de la caja no es parte de la pieza)
    gx0, gy0, gx1, gy1 = g["caja_diseno"]
    cont, guia = g["contorno"], g["guia"]
    ext = lambda pts, k, f: f(pts, key=lambda p: p[k])
    ya = py0 - 16
    for p in (ext(guia, 0, min), ext(guia, 0, max)):
        L.linea([P(*p), (P(*p)[0], ya - 3)], color=GRIS_C, ancho=0.4)
    L.cota_h(P(gx0, 0)[0], P(gx1, 0)[0], ya, ("Ø " if circ else "") + f"{_cm(an_cm)} diseño (guía)", arriba=True)
    yb = py0 + ph + 14
    for p in (ext(cont, 0, min), ext(cont, 0, max)):
        L.linea([P(*p), (P(*p)[0], yb + 3)], color=GRIS_C, ancho=0.4)
    L.cota_h(px0, px0 + pw, yb, ("Ø " if circ else "") + f"{_cm(W)} total (con el margen)", arriba=False)
    if not circ:
        xl = px0 - 14
        for p in (ext(cont, 1, max), ext(cont, 1, min)):
            L.linea([P(*p), (xl - 3, P(*p)[1])], color=GRIS_C, ancho=0.4)
        L.cota_v(xl, py0, py0 + ph, f"{_cm(H)} total", izquierda=True)
        xr = px0 + pw + 14
        for p in (ext(guia, 1, max), ext(guia, 1, min)):
            L.linea([P(*p), (xr + 3, P(*p)[1])], color=GRIS_C, ancho=0.4)
        L.cota_v(xr, P(0, gy1)[1], P(0, gy0)[1], f"{_cm(al_cm)} diseño", izquierda=False)
    # la leyenda: cada línea como se ve en el plano
    yl = yb + 30
    items = [("corte", "Corte (contorno)")]
    if g["contorno"] != g["guia"]:
        items.append(("guia", "Guía del diseño = doblez" if g.get("doblez") else "Guía del diseño"))
    if g["costura"]:
        items.append(("costura", "Costura"))
    if tiras_segs:
        items.append(("tira", "Tira (marca de borde a guía)" if marcar else "Tira (no va marcada)"))
    x = 0.0
    for tipo, txt in items:
        if tipo == "corte":
            L.linea([(x, yl - 3), (x + 18, yl - 3)], color=NEGRO, ancho=1.0)
        elif tipo == "guia":
            L.linea([(x, yl - 3), (x + 18, yl - 3)], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA)
        elif tipo == "costura":
            L.linea([(x, yl - 3), (x + 18, yl - 3)], color=NARANJA, ancho=0.8, rayas=RAYAS_COSTURA)
        else:
            L.linea([(x + 6, yl - 3), (x + 14, yl - 3)], color=NEGRO if marcar else GRIS, ancho=1.2)
            L.punto(x + 2, yl - 3, color=NEGRO if marcar else GRIS, lleno=marcar)
        L.texto(x + 22, yl, txt, z=7.5, color=GRIS)
        x += 30 + _ancho_texto(txt, 7.5) + 10
    alto = yl + 6
    if borde_txt:
        L.texto(0, yl + 12, borde_txt, z=7.5, color=GRIS)
        alto = yl + 16
    return {"alto": round(alto, 2), "ops": L.ops}


# ─── 2 · LA TERMINACIÓN: el borde en corte y la esquina/punta de cerca ─────────────────────────────
def _tela_corte(L, x0, x1, y, impresa=True):
    L.linea([(x0, y), (x1, y)], color=TELA_C, ancho=2.4)
    if impresa:
        L.linea([(x0, y - 1.9), (x1, y - 1.9)], color=TINTA, ancho=1.0)


def _panel_corte(L, X, term, M, costura_cm):
    """El borde en CORTE (de costado), paso a paso. `X` = dónde empieza el panel; M en cm (el texto)."""
    xa, xe, m = X + 64, X + 250, 34.0
    if term == "dobladillo":
        y1, y2, y3 = 44.0, 88.0, 132.0
        # 1 · cortado: el margen plano, con dónde va el doblez y dónde la costura
        L.texto(X, y1 + 3, "1 · Cortado", z=8, b=True)
        _tela_corte(L, xa, xe, y1)
        L.linea([(xa + m, y1 - 10), (xa + m, y1 + 7)], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA)
        L.linea([(xa + 2 * m, y1 - 10), (xa + 2 * m, y1 + 7)], color=NARANJA, ancho=0.8, rayas=RAYAS_COSTURA)
        L.cota_h(xa, xa + m, y1 - 13, f"{_cm(M)} cm")
        L.texto(xa, y1 + 15, "borde", z=7, color=GRIS, alinear="centro")
        L.texto(xa + m, y1 + 15, "doblez", z=7, color=AZUL, alinear="centro")
        L.texto(xa + 2 * m, y1 + 15, "costura", z=7, color=NARANJA, alinear="centro")
        L.texto(xe, y1 + 15, "cara impresa arriba", z=7, color=TINTA, alinear="der")
        # 2 · doblado: el margen va hacia el revés, por la guía
        L.texto(X, y2 + 3, "2 · Doblado", z=8, b=True)
        _tela_corte(L, xa + m, xe, y2)
        arco = [(xa + m - 3.2 * math.sin(math.pi * k / 10), y2 + 3.2 - 3.2 * math.cos(math.pi * k / 10)) for k in range(11)]
        L.linea(arco, color=TELA_C, ancho=2.4)
        L.linea([(xa + m, y2 + 6.4), (xa + 2 * m, y2 + 6.4)], color=TELA_C, ancho=2.4)
        L.linea([(xa + m, y2 - 10), (xa + m, y2 + 12)], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA)
        L.texto(xa - 2, y2 + 19, f"el margen de {_cm(M)} cm va hacia el revés, doblado justo por la guía", z=7, color=GRIS)
        # 3 · cosido: la costura a M del doblez agarra el borde del margen
        L.texto(X, y3 + 3, "3 · Cosido", z=8, b=True)
        _tela_corte(L, xa + m, xe, y3)
        arco = [(xa + m - 3.2 * math.sin(math.pi * k / 10), y3 + 3.2 - 3.2 * math.cos(math.pi * k / 10)) for k in range(11)]
        L.linea(arco, color=TELA_C, ancho=2.4)
        L.linea([(xa + m, y3 + 6.4), (xa + 2 * m, y3 + 6.4)], color=TELA_C, ancho=2.4)
        L.linea([(xa + 2 * m - 1.5, y3 - 6), (xa + 2 * m - 1.5, y3 + 12)], color=NARANJA, ancho=1.1, rayas="[1.6 1.2] 0")
        L.cota_h(xa + m, xa + 2 * m - 1.5, y3 - 9, f"{_cm(costura_cm)} cm")
        L.texto(xa - 2, y3 + 21, f"costura a {_cm(costura_cm)} cm del doblez: toma el borde del margen", z=7, color=GRIS)
        return 160.0
    if term == "overlock":
        y1, y2 = 44.0, 92.0
        L.texto(X, y1 + 3, "1 · Cortado", z=8, b=True)
        _tela_corte(L, xa, xe, y1)
        L.linea([(xa + m, y1 - 10), (xa + m, y1 + 7)], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA)
        L.cota_h(xa, xa + m, y1 - 13, f"{_cm(M)} cm")
        L.texto(xa, y1 + 15, "borde", z=7, color=GRIS, alinear="centro")
        L.texto(xa + m, y1 + 15, "guía del diseño", z=7, color=AZUL, alinear="centro")
        L.texto(X, y2 + 3, "2 · Overlock", z=8, b=True)
        _tela_corte(L, xa, xe, y2)
        # el hilo ENVUELVE el borde: lazos que pasan por arriba, dan la vuelta al canto y vuelven por abajo
        for k in range(4):
            xx = xa + 3 + k * 4.2
            L.linea([(xx, y2 - 4.2), (xa - 1.6, y2 - 4.2), (xa - 3.4, y2 - 2.4), (xa - 3.4, y2 + 1.4),
                     (xa - 1.6, y2 + 3.2), (xx, y2 + 3.2)], color=NARANJA, ancho=0.6)
        L.texto(xa - 2, y2 + 19, f"overlock en todo el borde: envuelve el canto (la pieza lleva {_cm(M)} cm de más)", z=7, color=GRIS)
        return 110.0
    y1 = 44.0
    L.texto(X, y1 + 3, "Corte al ras", z=8, b=True)
    _tela_corte(L, xa, xe, y1)
    L.linea([(xa, y1 - 10), (xa, y1 + 7)], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA)
    L.texto(xa, y1 + 15, "el borde es la guía del diseño: sin margen ni costura", z=7, color=GRIS)
    return 62.0


def _ventana_detalle(g):
    """(ventana en cm (x0, y0, x1, y1), nombre) del detalle de cerca: una esquina del rectángulo, la punta
    del triángulo o un tramo del borde del círculo."""
    if g["forma"] == "rectangulo":
        mi, md, ma, mb = g["m"]
        k = max(mi, mb, 0.1)
        return (-0.7 * k, -0.7 * k, 3.1 * k, 3.1 * k), "esquina"
    if g["forma"] == "triangulo":
        G, t = g["G"], g["t"]
        V = G[2]                                     # la PUNTA (la que se orienta)
        cerca = [p for p in g["contorno"] if math.hypot(p[0] - V[0], p[1] - V[1]) > 1e-9]
        r = max(2.6 * t, min(math.hypot(p[0] - V[0], p[1] - V[1]) for p in cerca) * 1.3 if cerca else 0)
        ix, iy, _ri = MP._incentro(G)
        d = math.hypot(ix - V[0], iy - V[1]) or 1
        cx, cy = V[0] + (ix - V[0]) / d * r * 0.45, V[1] + (iy - V[1]) / d * r * 0.45
        return (cx - r, cy - r, cx + r, cy + r), "punta"
    R, rg = g["R"], g["rg"]
    t = R - rg
    r = max(2.4 * t, 1.0)
    return (R - r, 2 * R - 1.2 * r, R + r, 2 * R + 0.8 * r), "borde"


def _detalle(L, g, ventana, X, Y, lado, doblada):
    """Un recuadro de `lado` × `lado` con la pieza de cerca (cortada o doblada)."""
    x0, y0, x1, y1 = ventana
    z = lado / (x1 - x0)
    P = lambda p: (X + (p[0] - x0) * z, Y + (y1 - p[1]) * z)
    if not doblada:
        pol = _clip_poligono(g["contorno"], ventana)
        if len(pol) >= 3:
            L.linea([P(p) for p in pol], color=None, relleno=TELA, cerrar=True)
        for tr in _clip_polilinea(g["contorno"], ventana, cerrar=True):
            L.linea([P(p) for p in tr], color=NEGRO, ancho=1.0)
        for tr in _clip_polilinea(g["guia"], ventana, cerrar=True):
            L.linea([P(p) for p in tr], color=AZUL, ancho=0.8, rayas=RAYAS_GUIA)
    else:
        pol = _clip_poligono(g["guia"], ventana)
        if len(pol) >= 3:
            L.linea([P(p) for p in pol], color=None, relleno=TELA, cerrar=True)
        for sol in g["solapas"]:                     # el margen doblado, del lado del revés
            ps = _clip_poligono(sol, ventana)
            if len(ps) >= 3:
                L.linea([P(p) for p in ps], color=None, relleno=SOLAPA, cerrar=True)
        for sol in g["solapas"]:                     # sus bordes: donde se cruzan, se superponen
            for tr in _clip_polilinea(sol, ventana, cerrar=True):
                L.linea([P(p) for p in tr], color=GRIS, ancho=0.6, rayas="[2 1.5] 0")
        for tr in _clip_polilinea(g["guia"], ventana, cerrar=True):
            L.linea([P(p) for p in tr], color=NEGRO, ancho=1.0)
    if g["costura"]:
        for tr in _clip_polilinea(g["costura"], ventana, cerrar=True):
            L.linea([P(p) for p in tr], color=NARANJA, ancho=0.8, rayas=RAYAS_COSTURA)
    L.caja(X, Y, X + lado, Y + lado)


def _bloque_terminacion(g, term, M, nombre_term):
    L = _Lienzo()
    titulo = {"dobladillo": "EL DOBLADILLO", "overlock": "EL OVERLOCK", "sin": "SIN MARGEN"}.get(term, "LA TERMINACIÓN")
    L.texto(0, 10, titulo + " · el borde de costado", z=9.5, b=True)
    alto_a = _panel_corte(L, 0.0, term, M, M)
    alto = alto_a
    if term == "dobladillo" and g["solapas"] and g["forma"] != "circulo":
        ventana, que = _ventana_detalle(g)
        X, lado = 292.0, 104.0
        L.texto(X, 10, ("La esquina" if que == "esquina" else "La punta") + " de cerca", z=9.5, b=True)
        L.texto(X, 28, "Cortada", z=8, b=True)
        L.texto(X + lado + 19, 28, "Doblada", z=8, b=True)
        _detalle(L, g, ventana, X, 34.0, lado, doblada=False)
        _detalle(L, g, ventana, X + lado + 19, 34.0, lado, doblada=True)
        ny = 34.0 + lado + 11
        L.linea([(X, ny - 2.5), (X + 9, ny - 2.5), (X + 9, ny + 1.5), (X, ny + 1.5)], color=None, relleno=SOLAPA, cerrar=True)
        L.texto(X + 13, ny + 1, f"el margen ({_cm(M)} cm) doblado hacia el revés", z=7, color=GRIS)
        L.texto(X, ny + 11, ("El recorte de la esquina llega justo a la guía: al doblar," if que == "esquina" else
                             "El recorte de la punta llega justo a la guía: al doblar,"), z=7, color=GRIS)
        L.texto(X, ny + 20, "las solapas se superponen y no sobra tela hacia afuera.", z=7, color=GRIS)
        alto = max(alto, ny + 25)
    elif term == "dobladillo" and g["forma"] == "circulo" and g["costura"]:
        ventana, _que = _ventana_detalle(g)
        X, lado = 292.0, 104.0
        L.texto(X, 10, "El borde de cerca", z=9.5, b=True)
        _detalle(L, g, ventana, X, 34.0, lado, doblada=False)
        ny = 34.0 + lado + 11
        L.texto(X, ny, f"Margen {_cm(M)} cm · costura a {_cm(M)} cm de la guía.", z=7, color=GRIS)
        L.texto(X, ny + 9, "En la curva el margen doblado es más largo que la línea", z=7, color=GRIS)
        L.texto(X, ny + 18, "donde se apoya: repartir la tela de más pareja al coser.", z=7, color=GRIS)
        alto = max(alto, ny + 23)
    return {"alto": round(alto + 4, 2), "ops": L.ops}


# ─── 3 · CÓMO SE TERMINA: los pasos, con las medidas de este pedido ─────────────────────────────────
def _pasos(g, term, M, tiras, total_tiras, borde_mm):
    f = g["forma"]
    rinc = "esquinas" if f == "rectangulo" else "puntas"
    corte = ("Cortar la pieza por el contorno" + (f" (el borde de corte impreso, de {_cm(borde_mm)} mm, queda por dentro)" if borde_mm else "") + ".")
    p = []
    if term == "dobladillo":
        p.append(corte + (f" Las {rinc} ya vienen recortadas." if g["rec"] else ""))
        p.append(f"Doblar el margen de {_cm(M)} cm hacia el revés, por la guía del diseño"
                 + (f": la línea que une los vértices de los recortes de las {rinc}." if g["rec"] else "."))
        p.append(f"Coser a {_cm(M)} cm del doblez (la línea naranja): la costura toma el borde del margen doblado.")
        if g["rec"]:
            p.append(f"En las {rinc} las solapas quedan una sobre la otra: no sobra tela hacia afuera.")
        if f == "circulo":
            p.append("En la curva, repartir parejo la tela de más del margen al coser.")
    elif term == "overlock":
        p.append(corte)
        p.append(f"Pasar overlock por todo el borde: la pieza lleva {_cm(M)} cm de más alrededor para la máquina.")
    else:
        p.append(corte + " Sin margen: la pieza es el diseño, no se dobla ni se cose el borde.")
    if tiras:
        if tiras.get("marcar", True):
            p.append(f"Coser una tira en cada marca ({total_tiras} en total): cada marca va del borde hasta la guía.")
        else:
            p.append(f"Coser las tiras ({total_tiras} en total) a las distancias de la tabla: no van marcadas en la tela.")
    L = _Lienzo()
    L.texto(0, 10, "CÓMO SE TERMINA", z=9.5, b=True)
    y = 24.0
    for i, txt in enumerate(p, 1):
        lineas, cur = [], ""
        for pal in txt.split(" "):
            prueba = (cur + " " + pal).strip()
            if _ancho_texto(prueba, 8.5) > CW - 16 and cur:
                lineas.append(cur)
                cur = pal
            else:
                cur = prueba
        lineas.append(cur)
        L.texto(0, y, f"{i}.", z=8.5, b=True)
        for ln in lineas:
            L.texto(16, y, ln, z=8.5)
            y += 11.5
        y += 1.5
    return {"alto": round(y - 6, 2), "ops": L.ops}


def dibujos_a_medida(forma, orient, term, an_cm, al_cm, mg, W, H, tiras=None, borde_mm=0.0, total_tiras=None):
    """Los bloques de dibujo de la ficha `[{alto, ops}]` (ver el encabezado). `mg` = el margen que rige
    por lado (cm); `W` × `H` = el total (`servidor._medida_pieza`); `tiras` = `servidor._tiras_de(...,
    para_ficha=True)` o None; `borde_mm` = el borde de corte impreso (0 si no lleva); `total_tiras` = las
    que cuenta la fila «Tiras» (cuando no se marcan no hay segmentos que contar)."""
    forma = MP._norm_forma(forma)
    orient = MP._norm_orientacion(orient)
    if term == "sin":
        mg = {k: 0.0 for k in ("arriba", "abajo", "izq", "der")}
    g = _geometria(forma, orient, term, float(an_cm), float(al_cm), mg, float(W), float(H))
    g["doblez"] = term == "dobladillo"
    M = MP._margen_uniforme(mg) if forma != "rectangulo" else max(float(mg.get(k) or 0) for k in ("arriba", "abajo", "izq", "der"))
    segs = []
    if tiras:
        try:
            segs = MP._segmentos_tiras(W, H, tiras["margen"], tiras["lados"], forma, orient, tiras.get("diseno_cm"), tiras.get("recorte", True))
        except Exception:
            segs = []
    total = total_tiras if total_tiras is not None else len(segs)
    borde_txt = (f"El borde de corte ({_cm(borde_mm)} mm) se imprime sobre el contorno, por dentro de la medida total."
                 if borde_mm else "")
    return [_bloque_plano(g, float(W), float(H), float(an_cm), float(al_cm), segs, tiras, borde_txt),
            _bloque_terminacion(g, term, M, term),
            _pasos(g, term, M, tiras, total, borde_mm)]
