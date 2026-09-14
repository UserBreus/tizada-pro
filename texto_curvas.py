"""
TEXTO A CURVAS — convierte texto en operadores de trazado PDF (contornos
vectoriales reales de la fuente). El archivo final no contiene texto vivo:
ninguna sustitución de tipografía es posible en el RIP ni en ningún visor.
"""
import io
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen


class FuenteCurvas:
    def __init__(self, fuente_bytes, respaldo=None):
        self.tt = TTFont(io.BytesIO(fuente_bytes))
        self.glyphset = self.tt.getGlyphSet()
        self.cmap = self.tt.getBestCmap() or self._cmap_de_respaldo()
        self.upem = self.tt["head"].unitsPerEm
        self._cache = {}
        self._cap = None
        # 🔴 EL CARÁCTER QUE ESTA FUENTE NO TIENE LO PRESTA LA DE RESPALDO (regla del usuario
        # 2026-09-14: «si la fuente no tiene algunos caracteres que le ponga unos genéricos
        # solamente en ese carácter»). Las tipografías de camiseta traen letras y números y nada
        # más: un «J. PEREZ» tumbaba la tizada entera. Ahora el nombre sale COMPLETO y sólo ese
        # carácter viene de otra tipografía, escalado para que se vea del mismo tamaño.
        self.respaldo = respaldo
        self.sustituidos = []          # los caracteres que hubo que pedirle al respaldo

    def _cmap_de_respaldo(self):
        """Un `cmap` unicode para fuentes que NO traen tabla unicode. `getBestCmap` sólo mira las
        tablas (3,1)/(0,x)/(3,10) y devuelve None si no hay: pasó con una fuente que el usuario
        subió al catálogo («MoreggiTFont4-Camiseta»: sólo Mac Roman (1,0) y símbolo (3,0)) y la
        tizada se caía con `'NoneType' object has no attribute 'get'` (2026-09-07). Acá se arma
        el mapa con lo que hay: la tabla símbolo guarda los caracteres en 0xF000 + código, la
        Mac Roman en su propia codificación de un byte; se pasan los dos a unicode. Nunca
        devuelve None: sin nada, un dict vacío (= todos los glifos «faltantes», que es lo que el
        resto del sistema ya sabe manejar)."""
        mapa = {}
        try:
            tablas = list(self.tt["cmap"].tables) if "cmap" in self.tt else []
        except Exception:
            tablas = []
        for t in tablas:                                   # 1) Mac Roman, un byte → unicode
            if (t.platformID, t.platEncID) == (1, 0):
                for code, gname in t.cmap.items():
                    try:
                        cp = ord(bytes([code]).decode("mac_roman")) if 0 <= code < 256 else None
                    except Exception:
                        cp = None
                    if cp is not None and gname not in (".notdef", ".null", "nonmarkingreturn"):
                        mapa.setdefault(cp, gname)
        for t in tablas:                                   # 2) símbolo: 0xF000 + código (pisa al anterior)
            if (t.platformID, t.platEncID) == (3, 0):
                for code, gname in t.cmap.items():
                    cp = code - 0xF000 if 0xF000 <= code <= 0xF0FF else code
                    if gname not in (".notdef", ".null", "nonmarkingreturn"):
                        mapa[cp] = gname
        if not mapa:                                       # 3) lo que sea, tal cual
            for t in tablas:
                for code, gname in t.cmap.items():
                    mapa.setdefault(code, gname)
        return mapa

    @property
    def cap_ratio(self):
        """Qué proporción del tamaño de fuente ocupa una MAYÚSCULA (altura de caja, «cap height»).

        Hace falta porque el «tamaño de letra» de una fuente es el **em**, que reserva lugar para
        ascendentes y descendentes: pedir 3 mm dibujaba una M de **2,15 mm** en Arial Bold (28 %
        menos). Quien configura una etiqueta en milímetros habla de la ALTURA DE LA LETRA, no del
        em — así que se convierte con esta proporción. Se usa `sCapHeight` de la tabla OS/2 y, si la
        fuente no la trae, se mide la «H» de verdad."""
        if self._cap is None:
            r = None
            try:
                cap = getattr(self.tt["OS/2"], "sCapHeight", None)
                if cap and cap > 0:
                    r = cap / self.upem
            except Exception:
                pass
            if not r:
                try:                                   # medir la H real (su bbox vertical)
                    ops, _ = self._glifo("H")
                    ys = []
                    for _op, args in ops:
                        for a in (args or ()):
                            if isinstance(a, (tuple, list)) and len(a) == 2:
                                ys.append(a[1])
                    if ys:
                        r = (max(ys) - min(ys)) / self.upem
                except Exception:
                    pass
            self._cap = r or 0.72                      # típico si la fuente no dice nada
        return self._cap

    def size_para_alto(self, alto_pt):
        """Tamaño de fuente que hace que una MAYÚSCULA mida exactamente `alto_pt`."""
        return float(alto_pt) / (self.cap_ratio or 0.72)

    def _glifo(self, ch):
        if ch in self._cache:
            return self._cache[ch]
        gname = self.cmap.get(ord(ch))
        if gname is None and ch.isspace():
            # Un espacio sin glifo (fuentes decorativas de camiseta que sólo traen letras y
            # números) no puede tumbar «MESSI 10»: no tiene contorno, así que sólo hace falta
            # un avance. Se usa el del glifo `space` si existe por nombre; si no, un tercio del em.
            gname = "space" if "space" in self.glyphset else None
            if gname is None:
                self._cache[ch] = ([], self.upem // 3)
                return self._cache[ch]
        if gname is None:
            prestado = self._del_respaldo(ch)
            if prestado is not None:
                return prestado
            raise ValueError(f"glifo faltante: {ch!r}")
        pen = DecomposingRecordingPen(self.glyphset)
        # Un glifo puede estar en el cmap pero tener los datos CORRUPTOS (p. ej. `loca` con un
        # offset imposible → fontTools lee fuera del buffer: "bytearray index out of range").
        # Se normaliza a ValueError, igual que el glifo faltante: para quien llama el resultado
        # es el mismo (ese carácter no se puede dibujar) y un solo glifo roto no tumba la fuente.
        try:
            self.glyphset[gname].draw(pen)
        except Exception as e:
            prestado = self._del_respaldo(ch)      # está en el cmap pero los datos no sirven
            if prestado is not None:
                return prestado
            raise ValueError(f"glifo corrupto: {ch!r} ({gname}): {e}") from e
        ancho = self.glyphset[gname].width
        self._cache[ch] = (pen.value, ancho)
        return self._cache[ch]

    def _del_respaldo(self, ch):
        """El glifo `ch` de la tipografía de respaldo, traído a las unidades de ÉSTA.

        Se escala por dos cosas a la vez: los `upem` (cada fuente mide en su propia grilla) y la
        **altura de mayúscula**, que es lo que hace que se vea del mismo tamaño — sin eso, un
        punto prestado a una fuente de camiseta puede salir notoriamente más chico o más grande.
        Devuelve None si el respaldo tampoco lo tiene: ahí no hay con qué dibujarlo."""
        if self.respaldo is None:
            return None
        try:
            registros, ancho = self.respaldo._glifo(ch)
        except Exception:
            return None
        k = self.upem / (self.respaldo.upem or self.upem)
        _cr = self.respaldo.cap_ratio
        if _cr:
            k *= (self.cap_ratio / _cr)

        def _pt(p):
            return None if p is None else (p[0] * k, p[1] * k)   # `qCurveTo` puede traer None

        escalados = [(verbo, tuple(_pt(p) for p in (args or ()))) for verbo, args in registros]
        if ch not in self.sustituidos:
            self.sustituidos.append(ch)
        self._cache[ch] = (escalados, ancho * k)
        return self._cache[ch]

    def prestados(self, texto):
        """Los caracteres de `texto` que esta tipografía no tiene y le va a dibujar el respaldo.

        Es lo que hay que AVISAR: salen, pero con otra tipografía. Lo que no puede dibujar ni el
        respaldo va en `faltantes`."""
        out = []
        for ch in str(texto or ""):
            if ch in out or ch.isspace() or self.cmap.get(ord(ch)) is not None:
                continue
            if self._del_respaldo(ch) is not None:
                out.append(ch)
        return out

    def faltantes(self, texto):
        """Los caracteres de `texto` que esta tipografía NO puede dibujar, sin repetir y en orden.

        Con tipografía de respaldo, un carácter que ELLA sí puede dibujar NO figura acá: se
        estampa prestado (ver `prestados`). Queda sólo lo que no puede dibujar nadie.

        Preguntar es mejor que reventar: el que va a estampar lo consulta y arma un aviso que
        dice qué carácter y en qué texto, en vez de un `glifo faltante: '.'` a mitad de la tizada
        (reporte del usuario 2026-09-14: un nombre con punto y una fuente de camiseta que sólo
        trae letras y números)."""
        out = []
        for ch in str(texto or ""):
            if ch in out:
                continue
            try:
                self._glifo(ch)
            except Exception:
                out.append(ch)
        return out

    def ancho_texto(self, texto, size):
        return sum(self._glifo(ch)[1] for ch in texto) * size / self.upem

    def _ops_glifo(self, registros, size, x, y, avance, ca, sa):
        """Operadores de trazado PDF de UN glifo (sus `registros`), con línea base en
        (x, y), desplazado `avance` en em y rotado (ca, sa = cos/sin del ángulo)."""
        e = size / self.upem
        ops = []

        def M(px, py):
            ux, uy = (px + avance) * e, py * e
            return (x + ux * ca - uy * sa, y + ux * sa + uy * ca)

        actual = inicio = None
        for verbo, args in registros:
            if verbo == "moveTo":
                p = M(*args[0]); ops.append(f"{p[0]:.2f} {p[1]:.2f} m"); actual = args[0]; inicio = args[0]
            elif verbo == "lineTo":
                p = M(*args[0]); ops.append(f"{p[0]:.2f} {p[1]:.2f} l"); actual = args[0]
            elif verbo == "curveTo":
                pts = [M(*pt) for pt in args]
                ops.append(f"{pts[0][0]:.2f} {pts[0][1]:.2f} {pts[1][0]:.2f} {pts[1][1]:.2f} {pts[2][0]:.2f} {pts[2][1]:.2f} c")
                actual = args[-1]
            elif verbo == "qCurveTo":
                puntos = list(args)
                if puntos[-1] is None:
                    puntos[-1] = inicio
                p0 = actual; ctrls = puntos[:-1]; fin = puntos[-1]; segs = []
                for i, c0 in enumerate(ctrls):
                    mid = ((c0[0] + ctrls[i+1][0]) / 2, (c0[1] + ctrls[i+1][1]) / 2) if i < len(ctrls) - 1 else fin
                    segs.append((p0, c0, mid)); p0 = mid
                for (q0, qc, q1) in segs:
                    c1 = (q0[0] + 2/3*(qc[0]-q0[0]), q0[1] + 2/3*(qc[1]-q0[1]))
                    c2 = (q1[0] + 2/3*(qc[0]-q1[0]), q1[1] + 2/3*(qc[1]-q1[1]))
                    P1, P2, P3 = M(*c1), M(*c2), M(*q1)
                    ops.append(f"{P1[0]:.2f} {P1[1]:.2f} {P2[0]:.2f} {P2[1]:.2f} {P3[0]:.2f} {P3[1]:.2f} c")
                actual = fin
            elif verbo == "closePath":
                ops.append("h")
        return ops

    def ops_texto(self, texto, size, x, y, angulo_deg=0.0):
        """Operadores de trazado PDF del texto, con origen en (x, y) = punto de
        línea base izquierda, en coordenadas PDF (y hacia arriba), rotado
        `angulo_deg` alrededor del origen. Devuelve solo construcción de path
        (sin operador de pintura): el llamador decide f / S / B."""
        import math
        a = math.radians(angulo_deg); ca, sa = math.cos(a), math.sin(a)
        ops, avance = [], 0.0
        for ch in texto:
            registros, ancho = self._glifo(ch)
            ops.extend(self._ops_glifo(registros, size, x, y, avance, ca, sa))
            avance += ancho
        return "\n".join(ops)

    def ops_texto_curva(self, texto, size, puntos, x0=None, x1=None, align="centro"):
        """Texto cuyos glifos siguen una CURVA (línea base = polilínea de `puntos` (x, y) en
        coords PDF, y-arriba). Cada glifo se ubica en su posición de arco con el ángulo de la
        tangente local. La ALINEACIÓN se calcula sobre el EXTENT VISUAL `[x0, x1]` del placeholder
        original (NO sobre los orígenes de los glifos, que están corridos respecto al texto real
        → si no, el texto queda descentrado)."""
        import math
        pts = [(float(px), float(py)) for px, py in puntos if px is not None and py is not None]
        if len(pts) < 2:
            x, y = pts[0] if pts else (0.0, 0.0)
            return self.ops_texto(texto, size, x, y)
        pts.sort(key=lambda p: p[0])
        # Recuperar el ARCO SUAVE del diseño: los orígenes de los glifos MUESTREAN una curva suave
        # (el arco/warp del diseño). Ajustamos una PARÁBOLA (y = a·x² + b·x + c) por mínimos
        # cuadrados y la usamos densa sobre el EXTENT [x0,x1] → el arco queda suave y se extiende
        # CURVO (no recto), igual que el original. Sin esto, la polilínea + extensión recta aplana
        # las puntas y el arco de la tizada no coincide con el del diseño.
        _xs = [p[0] for p in pts]
        if len(pts) >= 3 and all(_xs[i] > _xs[i-1] for i in range(1, len(_xs))):
            import numpy as _np
            _a, _b, _c = _np.polyfit(_xs, [p[1] for p in pts], 2)
            _xa = min(_xs[0], x0) if x0 is not None else _xs[0]
            _xb = max(_xs[-1], x1) if x1 is not None else _xs[-1]
            _N = 60
            pts = [( _xa + (_xb - _xa) * k / _N,
                     float(_a * (_xa + (_xb - _xa) * k / _N) ** 2 + _b * (_xa + (_xb - _xa) * k / _N) + _c) )
                   for k in range(_N + 1)]
        # longitudes acumuladas de la polilínea
        lens = [0.0]
        for i in range(1, len(pts)):
            lens.append(lens[-1] + math.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]))
        CL = lens[-1]

        def punto_en(s):
            s = max(0.0, min(CL, s))
            i = 1
            while i < len(lens) and lens[i] < s:
                i += 1
            i = min(i, len(pts) - 1)
            L0, L1 = lens[i-1], lens[i]
            t = 0.0 if L1 == L0 else (s - L0) / (L1 - L0)
            x = pts[i-1][0] + t*(pts[i][0]-pts[i-1][0])
            y = pts[i-1][1] + t*(pts[i][1]-pts[i-1][1])
            ang = math.atan2(pts[i][1]-pts[i-1][1], pts[i][0]-pts[i-1][0])
            return x, y, ang

        def arclen_en_x(qx):
            """Arc-length del punto de la curva cuya x == qx (x monótona en el arco de un texto)."""
            for i in range(1, len(pts)):
                a, b = pts[i-1][0], pts[i][0]
                if (a <= qx <= b) or (b <= qx <= a):
                    t = 0.0 if b == a else (qx - a) / (b - a)
                    return lens[i-1] + t * (lens[i] - lens[i-1])
            return 0.0 if qx <= pts[0][0] else CL     # fuera del rango → extremo

        e = size / self.upem
        anchos = [self._glifo(ch)[1] * e for ch in texto]
        TW = sum(anchos)
        # ALINEACIÓN por el EXTENT VISUAL [x0, x1] (centro = centro del extent = centro de la mesa
        # si el diseño lo centró). Se ubica el texto sobre el arco en la x que corresponda.
        if x0 is None or x1 is None:
            x0, x1 = pts[0][0], pts[-1][0]
        if align == "izquierda":
            s = arclen_en_x(x0)
        elif align == "derecha":
            s = arclen_en_x(x1) - TW
        else:                                          # centro: el CENTRO del texto cae en el centro del extent
            s = arclen_en_x((x0 + x1) / 2.0) - TW / 2.0

        def _build(s0):
            ops, ss, xmin, xmax = [], s0, None, None
            for ch, w in zip(texto, anchos):
                registros, _a = self._glifo(ch)
                x, y, ang = punto_en(ss + w / 2.0)        # tangente en el CENTRO del glifo
                ca, sa = math.cos(ang), math.sin(ang)
                gx = x - (w / 2.0) * ca; gy = y - (w / 2.0) * sa   # línea base IZQUIERDA del glifo
                og = self._ops_glifo(registros, size, gx, gy, 0.0, ca, sa)
                for op in og:
                    c0 = op[0]
                    if c0.isdigit() or c0 == "-":      # línea con coords (m/l/c); saltar 'h'
                        px = float(op.split(" ", 1)[0])
                        xmin = px if xmin is None else min(xmin, px)
                        xmax = px if xmax is None else max(xmax, px)
                ops.extend(og); ss += w
            return "\n".join(ops), xmin, xmax

        # 1er trazado y CORRECCIÓN por el extent VISUAL real (los glifos rotados de las puntas
        # corren el centro respecto al punto medio del arco → se mide y se ajusta a [x0, x1]).
        _o, xmn, xmx = _build(s)
        if xmn is not None:
            if align == "izquierda":
                s += x0 - xmn
            elif align == "derecha":
                s += x1 - xmx
            else:
                s += (x0 + x1) / 2.0 - (xmn + xmx) / 2.0
            _o, _, _ = _build(s)
        return _o

    def ops_texto_fiel(self, texto, size, glifos):
        """Reproduce `texto` sobre el layout COMPLETO del placeholder (respeta el PÁRRAFO).
        `glifos` = [(x, y, x0, x1)] por glifo/renglón en coords destino y ORDEN DE LECTURA
        (x,y = línea base; x0,x1 = bordes del renglón, para la alineación). Respeta:
          • VARIAS LÍNEAS + INTERLINEADO (agrupa renglones por salto de y / reset de x);
          • ALINEACIÓN izquierda/centro/derecha (detectada por los bordes de los renglones);
          • CURVA/ARCO e inclinación por letra (cada renglón sigue su línea base).
        Una sola línea → se centra (idéntico a ops_texto_curva)."""
        g = [(float(a), float(b), float(c), float(d)) for (a, b, c, d) in glifos]
        if not g:
            return ""
        lineas, cur = [], [g[0]]
        for i in range(1, len(g)):
            dx = g[i][0] - g[i-1][0]; dy = g[i][1] - g[i-1][1]
            if abs(dy) > 0.6 * size or dx < -0.4 * size:   # salto de renglón
                lineas.append(cur); cur = [g[i]]
            else:
                cur.append(g[i])
        lineas.append(cur)
        exts = [(min(e[2] for e in ln), max(e[3] for e in ln)) for ln in lineas]   # (x0, x1) por renglón
        # ALINEACIÓN: qué borde comparten los renglones (solo detectable con ≥2 renglones).
        align = "centro"
        if len(lineas) >= 2:
            lefts = [x0 for x0, _ in exts]; rights = [x1 for _, x1 in exts]
            cents = [(x0 + x1) / 2 for x0, x1 in exts]
            sl = max(lefts) - min(lefts); sr = max(rights) - min(rights); sc = max(cents) - min(cents)
            m = min(sl, sc, sr)
            align = "izquierda" if m == sl else ("derecha" if m == sr else "centro")
        partes = texto.split("\n")
        ops = []
        for i, ln in enumerate(lineas):
            txt = texto if len(lineas) == 1 else (partes[i] if i < len(partes) else "")
            if not txt.strip():
                continue
            X0, X1 = exts[i]
            if len(ln) >= 2:
                base = [(e[0], e[1]) for e in ln]                 # arco / varios puntos
            else:
                base = [(X0, ln[0][1]), (X1, ln[0][1])]           # renglón plano de x0 a x1
            ops.append(self.ops_texto_curva(txt, size, base, X0, X1, align))
        return "\n".join(o for o in ops if o)
