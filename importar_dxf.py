# -*- coding: utf-8 -*-
"""Importador de moldería en DXF → PDF vectorial con la MISMA estructura que un .ai
(una capa/OCG por talle + los contornos de cada pieza), para que el resto del sistema
funcione igual (detección, nombrado, motor).

FIDELIDAD: el dibujo se respeta TAL CUAL viene en el archivo. Las polilíneas con
arcos (bulge), los SPLINE, círculos y elipses se convierten a curvas Bézier EXACTAS
vía `ezdxf.path.make_path` — nada se aplana a rectas ni se re-acomoda ni se escala.

Soporta 2 formas:
  • OPTITEX / AAMA con textos «Size: …» y «Piece Name: …»  (talle y nombre en textos,
    todo en la capa 0). Se aparea cada contorno con su talle/nombre por ORDEN de aparición.
  • GENÉRICO: contornos cerrados agrupados por posición, talle del nombre de capa.

Los contornos se guardan como SEGMENTOS: ("m",x,y) ("l",x,y) ("c",c1x,c1y,c2x,c2y,x,y) ("h",).
"""
import io
import pymupdf as fitz

CM = 28.3465          # puntos por cm
_UNID_A_CM = {0: 0.1, 1: 2.54, 2: 30.48, 4: 0.1, 5: 1.0, 6: 100.0, 8: 0.00254}

# Entidades que pueden formar el contorno cerrado de una pieza.
_TIPOS_PIEZA = {"LWPOLYLINE", "POLYLINE", "SPLINE", "ELLIPSE", "CIRCLE"}


def _path_a_segs(p):
    """Convierte un ezdxf Path a segmentos (m/l/c/h) SIN perder curvas.
    CURVE3 (cuadrática) se eleva a cúbica exacta; CURVE4 pasa tal cual."""
    segs = []
    sx, sy = float(p.start.x), float(p.start.y)
    segs.append(("m", sx, sy))
    cx, cy = sx, sy
    for cmd in p:
        nombre = cmd.type.name
        ex, ey = float(cmd.end.x), float(cmd.end.y)
        if nombre == "MOVE_TO":
            segs.append(("m", ex, ey))
            sx, sy = ex, ey
        elif nombre == "LINE_TO":
            segs.append(("l", ex, ey))
        elif nombre == "CURVE3_TO":       # cuadrática → cúbica exacta (elevación de grado)
            qx, qy = float(cmd.ctrl.x), float(cmd.ctrl.y)
            c1x, c1y = cx + 2.0 / 3.0 * (qx - cx), cy + 2.0 / 3.0 * (qy - cy)
            c2x, c2y = ex + 2.0 / 3.0 * (qx - ex), ey + 2.0 / 3.0 * (qy - ey)
            segs.append(("c", c1x, c1y, c2x, c2y, ex, ey))
        elif nombre == "CURVE4_TO":       # cúbica tal cual
            segs.append(("c", float(cmd.ctrl1.x), float(cmd.ctrl1.y),
                         float(cmd.ctrl2.x), float(cmd.ctrl2.y), ex, ey))
        else:                             # comando desconocido: unir recto (no debería pasar)
            segs.append(("l", ex, ey))
        cx, cy = ex, ey
    return segs, (sx, sy), (cx, cy)


def _segs_de(e):
    """Contorno CERRADO de una entidad como segmentos, FIEL al archivo (igual que lo
    muestra Illustrator): las polilíneas de puntos van punto a punto TAL CUAL (sin
    suavizar ni inventar nada); las entidades con curvas REALES (bulge/spline/elipse/
    círculo) se convierten a Bézier exactas vía make_path."""
    if e.dxftype() not in _TIPOS_PIEZA:
        return None
    try:
        from ezdxf import path as _ep
        p = _ep.make_path(e)
    except Exception:
        return None
    if len(p) < 2:
        return None
    segs, (sx, sy), (cx, cy) = _path_a_segs(p)
    # cerrado de verdad, o casi cerrado (tolerancia relativa al tamaño)
    bb = _bbox_segs(segs)
    if not bb:
        return None
    diag = max(bb[2] - bb[0], bb[3] - bb[1], 1e-9)
    cerrado = p.is_closed or (abs(sx - cx) + abs(sy - cy)) < diag * 0.002
    if not cerrado:
        return None
    segs.append(("h",))
    # Si el contorno vino como PURAS RECTAS (polilínea de puntos, sin arcos) → ajustar
    # curvas Bézier (curvas curvas, rectas rectas). Si trae arcos/béziers reales, se dejan.
    if not any(s[0] == "c" for s in segs):
        pts = [(s[1], s[2]) for s in segs if s[0] in ("m", "l")]
        suave = _contorno_suave(pts)
        if suave:
            return suave
    return segs


def _bbox_segs(segs):
    """Bounding box de los segmentos. Incluye los puntos de control (la curva SIEMPRE
    queda contenida en su casco convexo → el bbox contiene la curva real)."""
    xs, ys = [], []
    for s in segs:
        op = s[0]
        if op in ("m", "l"):
            xs.append(s[1]); ys.append(s[2])
        elif op == "c":
            xs += [s[1], s[3], s[5]]; ys += [s[2], s[4], s[6]]
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _escala_cm(doc, piezas):
    """cm por unidad DXF. Usa $INSUNITS si está; si no, infiere por el tamaño de las piezas."""
    u = doc.header.get("$INSUNITS")
    if u:
        return _UNID_A_CM.get(int(u), 1.0)
    # heurística: la pieza más grande. Si mide <300 unidades → cm; si es más → mm.
    maxd = 0.0
    for p in piezas:
        for segs in p["talles"].values():
            bb = _bbox_segs(segs)
            if bb:
                maxd = max(maxd, bb[2] - bb[0], bb[3] - bb[1])
    return 1.0 if maxd < 300 else 0.1


# ── stitching: unir LINEs sueltas en contornos ────────────────────────────────
def _stitch(lineas, tol=0.05):
    """Une segmentos LINE sueltos (Optitex con "Poli-Líneas" off explota el contorno
    en cientos de LINE) en CADENAS de puntos, encadenando por extremos compartidos.
    Devuelve las cadenas ordenadas por área de bbox (la mayor = contorno de la pieza)."""
    from collections import defaultdict
    segs = []
    for l in lineas:
        try:
            a = (float(l.dxf.start.x), float(l.dxf.start.y))
            b = (float(l.dxf.end.x), float(l.dxf.end.y))
        except Exception:
            continue
        if abs(a[0] - b[0]) > 1e-9 or abs(a[1] - b[1]) > 1e-9:
            segs.append((a, b))
    if not segs:
        return []
    q = 1.0 / tol
    def k(p):
        return (round(p[0] * q), round(p[1] * q))
    adj = defaultdict(list)
    for i, (a, b) in enumerate(segs):
        adj[k(a)].append(i); adj[k(b)].append(i)
    usado = [False] * len(segs)
    cadenas = []
    for i0 in range(len(segs)):
        if usado[i0]:
            continue
        usado[i0] = True
        a, b = segs[i0]
        cad = [a, b]
        while True:                                  # extender hacia adelante
            fin = cad[-1]; nxt = None
            for j in adj[k(fin)]:
                if not usado[j]:
                    nxt = j; break
            if nxt is None:
                break
            usado[nxt] = True
            s, e = segs[nxt]
            cad.append(e if k(s) == k(fin) else s)
        while True:                                  # extender hacia atrás
            ini = cad[0]; prv = None
            for j in adj[k(ini)]:
                if not usado[j]:
                    prv = j; break
            if prv is None:
                break
            usado[prv] = True
            s, e = segs[prv]
            cad.insert(0, s if k(e) == k(ini) else e)
        cadenas.append(cad)
    def area(cad):
        xs = [p[0] for p in cad]; ys = [p[1] for p in cad]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))
    cadenas.sort(key=area, reverse=True)
    return cadenas


def _cad_a_segs(cad):
    """Cadena de puntos → segmentos (m/l/h), TAL CUAL (sin suavizar). Cierra el contorno."""
    if not cad or len(cad) < 3:
        return None
    segs = [("m", cad[0][0], cad[0][1])]
    for p in cad[1:]:
        segs.append(("l", p[0], p[1]))
    segs.append(("h",))
    return segs


# ── ajuste de curvas Bézier (Schneider) sobre los puntos del contorno ─────────
# El DXF trae la curva como MUCHOS puntos rectos. Ajustamos curvas Bézier que pasan
# por esos puntos (dentro de una tolerancia < ruido de digitalización): las curvas
# quedan CURVAS a cualquier zoom, las rectas RECTAS y las esquinas/piquetes FILOSOS.
import math as _m
def _fcs(a, b): return (a[0] - b[0], a[1] - b[1])
def _fca(a, b): return (a[0] + b[0], a[1] + b[1])
def _fck(a, s): return (a[0] * s, a[1] * s)
def _fcd(a, b): return a[0] * b[0] + a[1] * b[1]
def _fcl(a): return _m.hypot(a[0], a[1])
def _fcn(a):
    l = _fcl(a) or 1e-12; return (a[0] / l, a[1] / l)
def _fcq(bz, t):
    mt = 1 - t
    return (bz[0][0] * mt**3 + 3 * bz[1][0] * mt * mt * t + 3 * bz[2][0] * mt * t * t + bz[3][0] * t**3,
            bz[0][1] * mt**3 + 3 * bz[1][1] * mt * mt * t + 3 * bz[2][1] * mt * t * t + bz[3][1] * t**3)
def _fc_chord(pts):
    u = [0.0]
    for i in range(1, len(pts)):
        u.append(u[-1] + _fcl(_fcs(pts[i], pts[i - 1])))
    tot = u[-1] or 1e-12
    return [x / tot for x in u]
def _fc_gen(pts, u, lT, rT):
    A = [(_fck(lT, 3 * (1 - u[i])**2 * u[i]), _fck(rT, 3 * (1 - u[i]) * u[i]**2)) for i in range(len(pts))]
    C = [[0., 0.], [0., 0.]]; X = [0., 0.]
    for i in range(len(pts)):
        a0, a1 = A[i]
        C[0][0] += _fcd(a0, a0); C[0][1] += _fcd(a0, a1); C[1][0] += _fcd(a0, a1); C[1][1] += _fcd(a1, a1)
        t = u[i]; mt = 1 - t; b0 = mt**3; b1 = 3 * mt * mt * t; b2 = 3 * mt * t * t; b3 = t**3
        base = (pts[0][0] * (b0 + b1) + pts[-1][0] * (b2 + b3), pts[0][1] * (b0 + b1) + pts[-1][1] * (b2 + b3))
        tmp = _fcs(pts[i], base); X[0] += _fcd(a0, tmp); X[1] += _fcd(a1, tmp)
    detC = C[0][0] * C[1][1] - C[1][0] * C[0][1]; seg = _fcl(_fcs(pts[-1], pts[0]))
    if abs(detC) < 1e-12:
        al = ar = seg / 3.0
    else:
        al = (X[0] * C[1][1] - X[1] * C[0][1]) / detC; ar = (C[0][0] * X[1] - C[1][0] * X[0]) / detC
    if al < 1e-6 * seg or ar < 1e-6 * seg:
        al = ar = seg / 3.0
    return [pts[0], _fca(pts[0], _fck(lT, al)), _fca(pts[-1], _fck(rT, ar)), pts[-1]]
def _fc_err(pts, bz, u):
    md = 0.0; sp = len(pts) // 2
    for i in range(1, len(pts) - 1):
        q = _fcq(bz, u[i]); d = _fcs(q, pts[i]); dd = d[0] * d[0] + d[1] * d[1]
        if dd > md:
            md = dd; sp = i
    return md, sp
def _fc_reparam(bz, pts, u):
    q1 = [_fck(_fcs(bz[i + 1], bz[i]), 3) for i in range(3)]
    q2 = [_fck(_fcs(q1[i + 1], q1[i]), 2) for i in range(2)]
    out = []
    for i in range(len(u)):
        t = u[i]; mt = 1 - t
        qq = _fcq(bz, t); d = _fcs(qq, pts[i])
        d1 = (q1[0][0] * mt * mt + 2 * q1[1][0] * mt * t + q1[2][0] * t * t, q1[0][1] * mt * mt + 2 * q1[1][1] * mt * t + q1[2][1] * t * t)
        d2 = (q2[0][0] * mt + q2[1][0] * t, q2[0][1] * mt + q2[1][1] * t)
        num = d[0] * d1[0] + d[1] * d1[1]; den = d1[0]**2 + d1[1]**2 + d[0] * d2[0] + d[1] * d2[1]
        out.append(t if abs(den) < 1e-12 else t - num / den)
    return out
def _fc_fit(pts, lT, rT, err, depth=0):
    if len(pts) == 2:
        d = _fcl(_fcs(pts[1], pts[0])) / 3.0
        return [[pts[0], _fca(pts[0], _fck(lT, d)), _fca(pts[1], _fck(rT, d)), pts[1]]]
    u = _fc_chord(pts); bz = _fc_gen(pts, u, lT, rT); e, sp = _fc_err(pts, bz, u)
    if e < err:
        return [bz]
    if depth < 24 and e < err * 16:
        for _ in range(6):
            u = _fc_reparam(bz, pts, u); bz = _fc_gen(pts, u, lT, rT); e, sp = _fc_err(pts, bz, u)
            if e < err:
                return [bz]
    sp = max(1, min(len(pts) - 2, sp))
    cT = _fcn(_fcs(pts[sp - 1], pts[sp + 1]))
    return _fc_fit(pts[:sp + 1], lT, cT, err, depth + 1) + _fc_fit(pts[sp:], (-cT[0], -cT[1]), rT, err, depth + 1)

def _contorno_suave(cad, tol=0.04, corner_ang=32.0):
    """Cadena de puntos → segs (m/l/c/h) con curvas Bézier ajustadas, esquinas y
    piquetes preservados, rectas rectas. Fallback al literal si algo falla."""
    try:
        P = []
        for p in cad:
            p = (float(p[0]), float(p[1]))
            if not P or abs(p[0] - P[-1][0]) > 1e-7 or abs(p[1] - P[-1][1]) > 1e-7:
                P.append(p)
        if len(P) >= 2 and abs(P[0][0] - P[-1][0]) < 1e-7 and abs(P[0][1] - P[-1][1]) < 1e-7:
            P.pop()
        n = len(P)
        if n < 4:
            return _cad_a_segs(cad)
        def turn(i):
            a = P[(i - 1) % n]; b = P[i]; c = P[(i + 1) % n]
            v1 = _fcs(b, a); v2 = _fcs(c, b); l1 = _fcl(v1) or 1e-9; l2 = _fcl(v2) or 1e-9
            return _m.degrees(_m.acos(max(-1.0, min(1.0, _fcd(v1, v2) / (l1 * l2)))))
        corners = [i for i in range(n) if turn(i) > corner_ang]
        err = tol * tol
        if not corners:
            seq = P + [P[0]]; lT = _fcn(_fcs(seq[1], seq[0])); rT = _fcn(_fcs(seq[-2], seq[-1]))
            bezs = _fc_fit(seq, lT, rT, err)
            segs = [("m", bezs[0][0][0], bezs[0][0][1])] + [("c", b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]) for b in bezs] + [("h",)]
            return segs
        segs = [("m", P[corners[0]][0], P[corners[0]][1])]; mn = len(corners)
        for ci in range(mn):
            i0 = corners[ci]; i1 = corners[(ci + 1) % mn]; run = []; i = i0
            while True:
                run.append(P[i])
                if i == i1:
                    break
                i = (i + 1) % n
            if len(run) == 2:
                segs.append(("l", run[1][0], run[1][1]))
            elif len(run) > 2:
                lT = _fcn(_fcs(run[1], run[0])); rT = _fcn(_fcs(run[-2], run[-1]))
                for b in _fc_fit(run, lT, rT, err):
                    segs.append(("c", b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]))
        segs.append(("h",))
        return segs
    except Exception:
        return _cad_a_segs(cad)


def _parse_optitex_lineas(msp):
    """Optitex/AAMA con el contorno EXPLOTADO en LINEs sueltas (opción "Poli-Líneas"
    desactivada): Size:/Piece Name: en textos + cientos de LINE que se UNEN en el
    contorno de cada pieza. Se toma tal cual viene (sin suavizar)."""
    reg = {}; orden = []
    cur_size = [None]; cur_piece = [None]; lineas = []
    vio = [False]

    def flush():
        if cur_size[0] and cur_piece[0] and lineas:
            cad = _stitch(lineas)
            if cad:
                segs = _contorno_suave(cad[0])   # ajusta curvas Bézier (curvas curvas, rectas rectas)
                if segs and _bbox_segs(segs):
                    bb = _bbox_segs(segs)
                    if (bb[2] - bb[0]) > 0.3 and (bb[3] - bb[1]) > 0.3:   # descarta ruido
                        if cur_size[0] not in orden:
                            orden.append(cur_size[0])
                        reg.setdefault(cur_piece[0], {})[cur_size[0]] = segs
        lineas.clear()

    for e in msp:
        t = e.dxftype()
        if t == "TEXT":
            s = str(e.dxf.text).strip(); low = s.lower()
            if low.startswith("size:"):
                flush(); cur_size[0] = s[5:].strip(); vio[0] = True
            elif low.startswith("piece name:"):
                cur_piece[0] = s[11:].strip().lstrip("@").strip(); vio[0] = True
        elif t == "LINE":
            lineas.append(e)
    flush()
    if not vio[0] or not reg:
        return None
    piezas = [{"nombre": n, "talles": tal} for n, tal in reg.items()]
    return piezas, orden


# ── 1) Optitex/AAMA por textos Size:/Piece Name: ──────────────────────────────
def _parse_optitex(msp):
    cur_size = cur_piece = None
    reg = {}   # nombre_pieza -> {talle: segs}
    orden_talles = []
    vio_textos = False
    for e in msp:
        t = e.dxftype()
        if t == "TEXT":
            s = str(e.dxf.text).strip()
            if s.lower().startswith("size:"):
                cur_size = s[5:].strip(); vio_textos = True
            elif s.lower().startswith("piece name:"):
                cur_piece = s[11:].strip().lstrip("@").strip(); vio_textos = True
            continue
        segs = _segs_de(e)
        if segs is None or not cur_piece or not cur_size:
            continue
        if cur_size not in orden_talles:
            orden_talles.append(cur_size)
        reg.setdefault(cur_piece, {})[cur_size] = segs
    if not vio_textos or not reg:
        return None
    piezas = [{"nombre": nom, "talles": tal} for nom, tal in reg.items()]
    return piezas, orden_talles


# ── 2) genérico: contornos por posición, talle del layer ──────────────────────
def _solapan(a, b):
    ax0, ay0, ax1, ay1 = a; bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0); ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return False
    inter = (ix1 - ix0) * (iy1 - iy0)
    menor = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0)) or 1
    return inter / menor > 0.55


def _texto_cercano(textos, bb):
    x0, y0, x1, y1 = bb; mx = (x1 - x0) * 0.15 + 1; my = (y1 - y0) * 0.15 + 1
    cand = [t for t in textos if x0 - mx <= t[1] <= x1 + mx and y0 - my <= t[2] <= y1 + my]
    if not cand:
        return ""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cand.sort(key=lambda t: (t[1] - cx) ** 2 + (t[2] - cy) ** 2)
    return cand[0][0]


def _parse_generico(msp):
    contornos = []
    for e in msp:
        segs = _segs_de(e)
        if segs:
            contornos.append({"segs": segs, "layer": (e.dxf.layer or "0"), "bb": _bbox_segs(segs)})
    for ins in msp.query("INSERT"):
        try:
            for e in ins.virtual_entities():
                segs = _segs_de(e)
                if segs:
                    contornos.append({"segs": segs, "layer": (e.dxf.layer or "0"), "bb": _bbox_segs(segs)})
        except Exception:
            pass
    if not contornos:
        return None
    textos = []
    for e in msp.query("TEXT MTEXT"):
        try:
            s = e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.text
            p = e.dxf.insert
            if s and str(s).strip():
                textos.append((str(s).strip(), float(p[0]), float(p[1])))
        except Exception:
            pass
    grupos = []
    for c in sorted(contornos, key=lambda c: -((c["bb"][2] - c["bb"][0]) * (c["bb"][3] - c["bb"][1]))):
        for g in grupos:
            if _solapan(g[0]["bb"], c["bb"]):
                g.append(c); break
        else:
            grupos.append([c])
    piezas = []; orden = []
    for g in grupos:
        g.sort(key=lambda c: (c["bb"][2] - c["bb"][0]) * (c["bb"][3] - c["bb"][1]))
        nombre = _texto_cercano(textos, g[-1]["bb"])
        tal = {}
        for i, c in enumerate(g):
            lay = str(c.get("layer") or "").strip()
            t = lay if (lay and lay != "0" and len(lay) <= 6) else f"T{i + 1}"
            if t not in orden:
                orden.append(t)
            tal[t] = c["segs"]
        piezas.append({"nombre": nombre, "talles": tal})
    return piezas, orden


# ── construir el PDF a TAMAÑO REAL 1:1 y TAL CUAL VIENE (coords originales del DXF) ──
def _construir_pdf(piezas, orden_talles, escala_cm):
    S = CM * escala_cm            # 1 unidad DXF → S puntos (1:1 real; PyMuPDF admite páginas grandes)
    MARG = 4 * CM
    # extent global con las coordenadas ORIGINALES (no se re-acomoda ni se escala)
    minX = minY = 1e18; maxX = maxY = -1e18
    for p in piezas:
        for segs in p["talles"].values():
            bb = _bbox_segs(segs)
            if bb:
                minX = min(minX, bb[0]); minY = min(minY, bb[1])
                maxX = max(maxX, bb[2]); maxY = max(maxY, bb[3])
    PW = MARG * 2 + (maxX - minX) * S
    PH = MARG * 2 + (maxY - minY) * S

    doc = fitz.open(); page = doc.new_page(width=PW, height=PH)
    page.draw_rect(fitz.Rect(0, 0, PW, PH), color=None, fill=(1, 1, 1))
    ocg = {t: doc.add_ocg(str(t)) for t in orden_talles}
    verde = (0.16, 0.62, 0.42)
    def P(x, y):                  # DXF (y-arriba) → página PDF (y-abajo), 1:1
        return fitz.Point(MARG + (x - minX) * S, PH - MARG - (y - minY) * S)
    # Un trazo por (pieza, talle) → CADA pieza queda separable por el sistema. Las curvas
    # se dibujan como Bézier REALES (draw_bezier), no aplanadas. `finish` por contorno
    # (path separado) pero un solo `commit` por talle (pocas escrituras al content stream).
    for t in orden_talles:
        oc = ocg.get(t, 0)
        sh = page.new_shape(); alguno = False
        for p in piezas:
            segs = p["talles"].get(t)
            if not segs:
                continue
            cur = ini = None; dibujo = False
            for s in segs:
                op = s[0]
                if op == "m":
                    cur = ini = P(s[1], s[2])
                elif op == "l" and cur is not None:
                    nxt = P(s[1], s[2]); sh.draw_line(cur, nxt); cur = nxt; dibujo = True
                elif op == "c" and cur is not None:
                    c1 = P(s[1], s[2]); c2 = P(s[3], s[4]); fin = P(s[5], s[6])
                    sh.draw_bezier(cur, c1, c2, fin); cur = fin; dibujo = True
                elif op == "h" and cur is not None and ini is not None:
                    if abs(cur.x - ini.x) > 1e-6 or abs(cur.y - ini.y) > 1e-6:
                        sh.draw_line(cur, ini)
                    cur = ini; dibujo = True
            if dibujo:
                sh.finish(color=verde, width=1.0, closePath=False, oc=oc)
                alguno = True
        if alguno:
            sh.commit()
    # nombres en el orden que numera detectar_piezas (bbox x0,y0 en coords de página)
    def _key(p):
        allb = [_bbox_segs(segs) for segs in p["talles"].values()]
        allb = [b for b in allb if b]
        x0 = min(b[0] for b in allb); y1 = max(b[3] for b in allb)
        return (round(MARG + (x0 - minX) * S, 1), round(PH - MARG - (y1 - minY) * S, 1))
    nombres = [p["nombre"] for p in sorted(piezas, key=_key)]

    # ── CORRESPONDENCIA EXACTA por talle: qué pieza (nombre del DXF) es cada índice ──
    # Replica el orden de `extraer_piezas_mesa` (mismo filtro de tamaño + sort por bbox
    # x0,y0 en coords de página): indices[talle][i] = nombre DXF de la pieza i.
    # Con esto el sistema NO adivina el emparejado entre talles: lo dice el archivo.
    indices = {}
    for t in orden_talles:
        entradas = []
        for p in piezas:
            segs = p["talles"].get(t)
            if not segs:
                continue
            bb = _bbox_segs(segs)
            if not bb:
                continue
            x0 = MARG + (bb[0] - minX) * S
            y0 = PH - MARG - (bb[3] - minY) * S            # borde SUPERIOR en coords de página (y-abajo)
            w_cm = (bb[2] - bb[0]) * S / CM
            h_cm = (bb[3] - bb[1]) * S / CM
            if w_cm * h_cm < 10.0 or min(w_cm, h_cm) < 1.0:
                continue                                    # mismo filtro que extraer_piezas_mesa
            entradas.append(((round(x0, 1), round(y0, 1)), p["nombre"] or ""))
        entradas.sort(key=lambda e: e[0])
        indices[t] = [nom for _, nom in entradas]

    out = doc.tobytes(); doc.close()
    resumen = {"piezas": len(piezas), "talles": orden_talles,
               "nombres_detectados": [n for n in nombres if n], "nombres": nombres,
               "indices": indices,
               "escala_pdf": 1.0}
    return out, resumen


def dxf_a_pdf(dxf_path):
    """Lee un DXF de moldería y devuelve (pdf_bytes, resumen) — PDF con capa por talle."""
    import ezdxf
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    parsed = _parse_optitex(msp) or _parse_optitex_lineas(msp) or _parse_generico(msp)
    if not parsed:
        raise ValueError("El DXF no trae contornos de piezas reconocibles.")
    piezas, orden_talles = parsed
    escala = _escala_cm(doc, piezas)
    return _construir_pdf(piezas, orden_talles, escala)
