"""
AGREGAR PIEZAS AL MOLDE — escribe geometría nueva en `plantilla.ai`.

Hasta acá el molde era de sólo lectura: entraba como lo exportó el patronista y el sistema apenas
lo leía. Esto agrega el primer camino que ESCRIBE geometría, y por eso lleva tres cuidados que no
son opcionales:

1. **Se escribe una VERSIÓN, no el archivo del usuario.** Igual que el arte (`objetos_agregados`):
   `plantilla.v<N>.ai` + el puntero `plantilla.ver`. El original nunca se toca, y en Windows se
   evita el `os.replace` sobre un PDF abierto (WinError 5).

2. **Los trazados van como OPERADORES DE TRAZADO, nunca como XObject.** `extraer_piezas_mesa` lee
   con `page.get_drawings()`, que reporta trazados sueltos; metido en un XObject el contenido se
   ve como UN objeto y no como una pieza. Verificado sobre el molde real: inyectando operadores,
   la pieza pasa a detectarse (138 → 139 contornos) sin que aparezca ningún talle nuevo.

3. **EL `pieza_idx` ES LA POSICIÓN, NO UN ID** — y por eso el orden importa. Desde que las piezas
   quedan en **orden de DIBUJO** (`molde_real.extraer_piezas_mesa`, regla del usuario 2026-08-18) y
   la pieza nueva se escribe **al final** del contenido de la capa (`page.contents_add`), la nueva
   es **la última** de cada talle y **no se renumera nada**: `indice_de_insercion` devuelve
   `len(conts)` y el mapa de remapeo queda en la identidad. Medido con el contrato sobre el molde
   real: **0 de 2760** entradas cambian de índice.
   ⚠️ El remapeo (`remapear_registro`, cruce por bbox de la detección de ANTES contra la de DESPUÉS)
   **se conserva igual**: es la red que sostiene la identidad si el orden volviera a depender de la
   posición, o si un archivo raro alterara el orden de dibujo. No se saca porque hoy dé 0.
   (Con el orden viejo —por bbox— insertar en el medio corría a **69 de 138** piezas: de ahí venía
   la mitad de la complejidad de esta operación.)

⚠️ Una capa nueva NO sirve para esto: en la plantilla, toda capa con dibujo que no esté en
`CAPAS_SISTEMA` se lee como un TALLE (`motor_pedido._talles_de_plantilla`). La pieza va DENTRO de
la capa del talle al que pertenece.
"""

import re

import pikepdf
from pikepdf import Dictionary, Name, Stream

import objetos_agregados as OA


def _ocg_por_nombre(pdf, nombre):
    """La OCG (capa) que se llama `nombre`, o None."""
    ocp = pdf.Root.get("/OCProperties")
    if ocp is None:
        return None
    for g in (ocp.get("/OCGs") or []):
        try:
            if str(g.get("/Name")) == str(nombre):
                return g
        except Exception:
            continue
    return None


def _nombre_en_recursos(page, pdf, ocg, sugerido):
    """Nombre con el que la página referencia a esa OCG en `/Resources/Properties`.

    Si la capa todavía no está declarada en la página, se la agrega: sin eso el `/OC /X BDC` del
    stream apuntaría a la nada y el contenido quedaría fuera de la capa (visible siempre)."""
    if "/Resources" not in page.obj:
        page.obj["/Resources"] = Dictionary()
    res = page.obj["/Resources"]
    if "/Properties" not in res:
        res["/Properties"] = Dictionary()
    props = res["/Properties"]
    for k, v in props.items():
        try:
            if v.objgen == ocg.objgen:
                return str(k)[1:]
        except Exception:
            continue
    n = sugerido
    i = 0
    while ("/" + n) in props:
        i += 1
        n = f"{sugerido}{i}"
    props[Name("/" + n)] = ocg
    return n


def ops_de_segmentos(segs, dx, dy, y1=None, u=1.0):
    """Segmentos crudos (como los devuelve `molde_real`) → operadores de trazado PDF.

    ⚠️ **NO se da vuelta la Y.** Las coordenadas «crudas» de `molde_real._contorno_de_drawing` ya
    son coordenadas PDF (y hacia arriba, medidas desde el borde inferior): se arman como
    `cb.y1 - r.y1/U`, que es exactamente eso. Voltearlas otra vez ponía la pieza reflejada respecto
    del lugar marcado — se vio midiendo: se pidieron 80 mm hacia abajo y daba 5297 mm. `y1` queda
    por compatibilidad y no se usa.

    `dx`/`dy` trasladan en las MISMAS unidades crudas (y con el mismo sentido: `dy` positivo = hacia
    ARRIBA en la hoja; quien llama desde el visor —donde la Y va para abajo— manda el signo dado
    vuelta)."""
    out = []

    def P(x, y):
        return ((x + dx) * u, (y + dy) * u)

    for s in segs:
        op = s[0]
        if op == "m":
            out.append("%.4f %.4f m" % P(s[1], s[2]))
        elif op == "l":
            out.append("%.4f %.4f l" % P(s[1], s[2]))
        elif op == "c":
            out.append("%.4f %.4f %.4f %.4f %.4f %.4f c" % (P(s[1], s[2]) + P(s[3], s[4]) + P(s[5], s[6])))
        elif op == "re":
            x, y = P(s[1], s[2])
            out.append("%.4f %.4f %.4f %.4f re" % (x, y, s[3] * u, s[4] * u))
        elif op == "h":
            out.append("h")
    return "\n".join(out)


def firma_contornos(conts):
    """Firma posicional de cada contorno: su bbox redondeado. Es lo que permite reconocer, tras
    escribir el archivo, cuál era cuál — la geometría de las piezas que ya estaban no cambia."""
    return [tuple(round(float(v), 1) for v in c["bbox_raw"]) for c in conts]


def mapa_idx(firmas_antes, firmas_despues):
    """{idx_viejo: idx_nuevo} cruzando por bbox. Los que no aparecen (no debería pasar) se omiten."""
    pos = {}
    for j, f in enumerate(firmas_despues):
        pos.setdefault(f, []).append(j)
    out = {}
    for i, f in enumerate(firmas_antes):
        libres = pos.get(f)
        if libres:
            out[i] = libres.pop(0)
    return out


def remapear_registro(registro, mapas):
    """Reescribe los `pieza_idx` del registro con `{talle: {idx_viejo: idx_nuevo}}`.

    Devuelve `(registro_nuevo, cuántos cambiaron, [avisos])`. Una entrada cuyo idx no está en el
    mapa se deja como estaba y se avisa: preferible dejarla igual y decirlo, a moverla a ciegas."""
    nuevo, cambios, avisos = {}, 0, []
    for nom, por_t in (registro or {}).items():
        nuevo[nom] = {}
        for t, info in (por_t or {}).items():
            if not isinstance(info, dict) or info.get("pieza_idx") is None:
                nuevo[nom][t] = info
                continue
            m = mapas.get(t) or {}
            viejo = int(info["pieza_idx"])
            if viejo in m:
                if m[viejo] != viejo:
                    cambios += 1
                nuevo[nom][t] = {**info, "pieza_idx": m[viejo]}
            else:
                nuevo[nom][t] = info
                avisos.append(f"«{nom}» en el talle {t}: no se pudo reubicar (índice {viejo})")
    return nuevo, cambios, avisos


def contornos_de_pdf(path):
    """Trazados de la página 1 de un PDF suelto, en coords crudas (y-arriba), con la MISMA lectura
    que usa el molde. Sirve para tomar la pieza de un archivo que sube el usuario.

    Se devuelven ordenados de mayor a menor área: el contorno más grande suele ser la pieza y el
    resto, marcas internas (piquetes, línea de hilo)."""
    import motor_pedido as MP
    from molde_real import _contorno_de_drawing
    doc = MP._abrir(path)
    try:
        pagina = doc[0]
        cb = pagina.cropbox
        u = float(pagina.parent.metadata.get("user_unit", 1) or 1) if hasattr(pagina, "parent") else 1.0
        conts = []
        for d in pagina.get_drawings():
            try:
                c = _contorno_de_drawing(d, cb, u or 1.0, 1, None)
            except Exception:
                continue
            if c and c.get("segmentos") and any(s[0] != "h" for s in c["segmentos"]):
                # LA CAPA de donde salió: con ella cada forma va a SU talle (`formas_por_talle`)
                c["capa"] = d.get("layer") or ""
                conts.append(c)
        conts.sort(key=lambda c: c["w"] * c["h"], reverse=True)
        return conts
    finally:
        doc.close()


def _norm_capa(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


def formas_por_talle(conts, talles, objetivo):
    """`(asig, modo, faltan)`: qué forma del archivo subido va en cada talle de `objetivo`.

    🔴 POR CAPA primero (pedido del usuario 2026-10-26: «no está leyendo realmente las capas»): si el
    archivo trae capas con el nombre de los talles, cada talle toma la forma MÁS GRANDE de SU capa (lo
    demás de esa capa son marcas internas). Repartirlas por tamaño ponía en un talle la forma de otro
    cuando los tamaños no crecen parejo (o el archivo trae de más).
    Sin capas con esos nombres: por tamaño, de la más chica a la más grande en el orden de los talles
    (si trae las de todo el molde se toma la de cada talle elegido; si trae justo las elegidas, en orden).
    `modo` = "capas" | "tamaño"; `faltan` = talles de `objetivo` sin forma. Gemelo: `_formasPorTalle` (App.jsx)."""
    por_capa = {}
    for c in conts:                                # vienen de mayor a menor área: la primera es la pieza
        k = _norm_capa(c.get("capa"))
        if k and k not in por_capa:
            por_capa[k] = c
    if any(_norm_capa(t) in por_capa for t in objetivo):
        asig = {t: por_capa[_norm_capa(t)] for t in objetivo if _norm_capa(t) in por_capa}
        return asig, "capas", [t for t in objetivo if t not in asig]
    area = lambda x: x["w"] * x["h"]
    if len(conts) >= len(talles):
        o = sorted(conts[:len(talles)], key=area)
        asig = {t: o[k] for k, t in enumerate(talles) if t in objetivo}
    elif len(conts) >= len(objetivo):
        o = sorted(conts[:len(objetivo)], key=area)
        asig = {t: o[k] for k, t in enumerate(objetivo)}
    else:
        return {}, "tamaño", list(objetivo)
    return asig, "tamaño", []


def agregar_pieza(plantilla, colocaciones, mesa=1, etiqueta="Pieza nueva"):
    """Escribe piezas nuevas en `plantilla.ai` y devuelve la ruta de la VERSIÓN nueva.

    `colocaciones` = `{talle: colocacion | [colocacion, …]}` con
    `colocacion = {"segmentos": [...], "dx": float, "dy": float}` — la geometría que va en cada
    capa y su traslado, en unidades crudas del lienzo. Se escriben TODOS los talles en UNA sola
    pasada = una sola versión nueva del archivo, **aunque se agreguen varias piezas de un saque**
    (regla del usuario: lo preparado se guarda junto, y una versión por pieza era además una copia
    entera del molde en disco por cada una).

    ⚠️ La pieza tiene que entrar en TODOS los talles del molde. Si sólo entrara en algunos, el
    registro quedaría con una pieza que no existe en el resto y **la generación de la tizada
    explota** (`registro[pieza][talle]` → KeyError, sin guarda en el motor).
    """
    if not colocaciones:
        raise ValueError("no hay nada que agregar")
    vigente = OA.ruta_vigente(plantilla)
    destino = OA._ver_path(plantilla, OA._ver_actual(plantilla) + 1)
    pdf = pikepdf.open(vigente)
    try:
        page = pdf.pages[mesa - 1]
        cb = page.obj.get("/CropBox") or page.obj.get("/MediaBox")
        y1 = float(cb[3])
        puestos = []
        for talle, cols in colocaciones.items():
            ocg = _ocg_por_nombre(pdf, talle)
            if ocg is None:
                continue                      # ese talle no existe como capa: se salta y se informa
            pname = _nombre_en_recursos(page, pdf, ocg, "OCpz")
            escrito = False
            for col in (cols if isinstance(cols, (list, tuple)) else [cols]):
                ops = ops_de_segmentos(col["segmentos"], col.get("dx", 0.0), col.get("dy", 0.0), y1)
                if not ops.strip():
                    continue
                # Trazo fino y negro, como el resto del molde: lo que importa es el CONTORNO.
                # Va al FINAL del contenido → la pieza nueva es la última de su capa y no renumera.
                page.contents_add(Stream(pdf, f"q\n/OC /{pname} BDC\n0 0 0 RG 1 w\n{ops}\nS\nEMC\nQ\n".encode()))
                escrito = True
            if escrito:
                puestos.append(talle)
        if not puestos:
            raise ValueError("ninguno de los talles pedidos existe como capa en el molde")
        pdf.save(destino)
    finally:
        pdf.close()
    OA.fijar_version(plantilla, OA._ver_actual(plantilla) + 1)
    return destino, puestos


def detectar_por_talle(path, mesa, talles):
    """`{talle: [contornos]}` leyendo la página UNA SOLA VEZ.

    ⚠️ Tiene que dar EXACTAMENTE lo mismo que `extraer_piezas_mesa` talle por talle (mismo filtro,
    mismo orden): de ese orden sale el `pieza_idx`. La prueba lo compara contra el camino lento.

    Por qué existe: los 20 talles son CAPAS DE LA MISMA PÁGINA, y `_candidatos_mesa` llama a
    `page.get_drawings()` **una vez por talle** → barría la página entera 20 veces. Acá se barre una
    y se agrupa por capa: es la diferencia entre que agregar una pieza tarde minutos o segundos."""
    import motor_pedido as MP
    from molde_real import _contorno_de_drawing
    CM = 28.3465
    doc = MP._abrir(path)
    try:
        page = doc[mesa - 1]
        cb = page.cropbox
        pr = page.rect
        U = pr.width / cb.width if cb.width else 1.0
        out = {t: [] for t in talles}
        for d in page.get_drawings():
            t = d.get("layer")
            if t not in out:
                continue
            r = d["rect"]
            if not (r.width < pr.width * 1.2 and r.height < pr.height * 1.2):
                continue
            w_cm, h_cm = r.width / U / CM, r.height / U / CM
            # MISMO filtro que `extraer_piezas_mesa` (0.25 cm² / 0.3 cm — regla del usuario:
            # cargar todas aunque midan menos de 1 cm). Divergir acá cambia el pieza_idx.
            if w_cm * h_cm < 0.25 or min(w_cm, h_cm) < 0.3:
                continue
            out[t].append(_contorno_de_drawing(d, cb, U, mesa, t))
        # ⛔ SIN reordenar (entrada 182): el orden es el de DIBUJO del archivo, igual que
        # `extraer_piezas_mesa`. El sort viejo por posición divergía en moldes anidados y el
        # pieza_idx apuntaba a otra pieza según qué camino lo leyera.
        return out
    finally:
        doc.close()


def bbox_desplazado(segs, dx, dy, conts_ref):
    """`bbox_mu` que va a tener una pieza al colocarla con ese desplazamiento.

    Los segmentos vienen en coords CRUDAS y el orden de las piezas se decide con `bbox_mu` (las de
    MuPDF, y-abajo). La relación entre las dos la da cualquier contorno ya detectado del mismo
    archivo: `bbox_mu.x = bbox_raw.x - off_x` y la Y va al revés. Se saca de `conts_ref[0]` en vez
    de recalcular la geometría de la página."""
    xs, ys = [], []
    for s in segs:
        op = s[0]
        if op in ("m", "l"):
            xs.append(s[1]); ys.append(s[2])
        elif op == "c":
            xs += [s[1], s[3], s[5]]; ys += [s[2], s[4], s[6]]
        elif op == "re":
            xs += [s[1], s[1] + s[3]]; ys += [s[2], s[2] + s[4]]
    if not xs or not conts_ref:
        return (0.0, 0.0, 0.0, 0.0)
    x0, y0, x1, y1 = min(xs) + dx, min(ys) + dy, max(xs) + dx, max(ys) + dy
    r = conts_ref[0]
    off_x = r["bbox_raw"][0] - r["bbox_mu"][0]          # crudo → mu en X (traslación)
    suma_y = r["bbox_raw"][1] + r["bbox_mu"][3]         # crudo + mu = cte (la Y va al revés)
    return (x0 - off_x, suma_y - y1, x1 - off_x, suma_y - y0)


def indice_de_insercion(conts, bbox_mu_nueva):
    """Qué `pieza_idx` le toca a una pieza nueva, SIN volver a leer el archivo.

    El orden es por `(x0, y0)` del bbox, así que la posición de la pieza nueva se calcula contando
    cuántas van antes. Todo lo que está de ahí en adelante corre un lugar: `mapa_insercion`.

    Sirve para dos cosas: evitar la segunda detección completa (era la mitad del tiempo) y poder
    DECIRLE al usuario, antes de escribir nada, qué número le va a tocar y a cuántas piezas les
    mueve el suyo."""
    # ⛔ ORDEN DE DIBUJO (entrada 182): la pieza nueva se AGREGA al final del contenido de la
    # capa, así que su índice es SIEMPRE el último — nadie se renumera. (Con el orden viejo por
    # posición había que predecir dónde caía y correr a todas las de después; ese renumerado
    # era la mitad de la complejidad de agregar una pieza, y ya no existe.)
    return len(conts)


def mapa_insercion(n_antes, k):
    """`{idx_viejo: idx_nuevo}` al insertar UNA pieza en la posición `k`."""
    return {i: (i if i < k else i + 1) for i in range(n_antes)}


# ─── EDITAR PIEZAS: REEMPLAZAR SU FORMA o MOVERLAS, EN SU LUGAR (MAPA 746) ──────────────────────────
# Gemelo de `frontend/src/motor/molde/editarPiezas.js` (ahí está el porqué completo). Resumen: el número
# de una pieza ES su posición en el orden de dibujo de su capa, así que la pieza se toca DONDE ESTÁ en el
# content stream (mover = `q … cm … Q`; reemplazar = sus operadores de trazado por los de la forma nueva,
# con su mismo operador de pintado) y nadie se renumera. Se escribe una VERSIÓN; el archivo del usuario no
# se toca. Y nada se da por bueno sin `verificar_edicion`.
_TEXTO_OPS = {"Tj", "TJ", "'", '"'}


def _capas_de_recursos(pg):
    out = {}
    try:
        props = pg.obj.Resources.get("/Properties") or {}
    except Exception:
        props = {}
    for k, v in (props.items() if hasattr(props, "items") else []):
        try:
            out[str(k)[1:]] = str(v.get("/Name"))
        except Exception:
            continue
    return out


def _unidades_con_capa(inst, capas):
    """Gemelo de `unidadesConCapa`: trazados pintados y bloques de texto con su capa, su CTM y su caja."""
    from variantes_molde import _mul, _aplicar, _CONSTRUCCION, _PINTADO
    ctm, pila, pila_mc, out = (1, 0, 0, 1, 0, 0), [], [], []
    ini, pts, clip = None, [], False
    # TEXTO POR TRAMOS (como el gemelo): un bloque BT…ET puede llevar las etiquetas de VARIAS piezas; la
    # unidad es el tramo que arranca en un posicionamiento (Tm/Td/TD/T*/'/") y llega hasta el próximo
    I = (1, 0, 0, 1, 0, 0)
    bt, tlm, tl, tramo = None, I, 0.0, None

    def lin(m, tx, ty):
        return (m[0], m[1], m[2], m[3], m[4] + tx * m[0] + ty * m[2], m[5] + tx * m[1] + ty * m[3])

    def cerrar_tramo(fin):
        if tramo and tramo["muestra"]:
            out.append(dict(tramo, fin=fin, tipo="texto", capa=capa_actual(), ctm=ctm))

    def capa_actual():
        for c in reversed(pila_mc):
            if c:
                return c
        return None

    def nums(it):
        try:
            return [float(v) for v in it.operands]
        except Exception:
            return []

    for i, it in enumerate(inst):
        op = str(it.operator)
        if op == "q":
            pila.append(ctm)
        elif op == "Q":
            ctm = pila.pop() if pila else ctm
        elif op == "cm":
            a = nums(it)
            if len(a) == 6:
                ctm = _mul(tuple(a), ctm)
        elif op in ("BDC", "BMC"):
            c = None
            ops_ = list(it.operands)
            if op == "BDC" and len(ops_) >= 2 and str(ops_[0]) == "/OC" and isinstance(ops_[1], pikepdf.Name):
                c = capas.get(str(ops_[1])[1:])
            pila_mc.append(c)
        elif op == "EMC":
            if pila_mc:
                pila_mc.pop()
        elif op == "TL":
            a = nums(it)
            if len(a) == 1:
                tl = a[0]
        elif op == "BT":
            bt, tlm = i, I
            tramo = {"bt": i, "pos": None, "op": None, "ini": i + 1, "antes": I, "tlm": I, "muestra": False}
        elif bt is not None and op in ("Tm", "Td", "TD", "T*", "'", '"'):
            cerrar_tramo(i - 1)
            a = nums(it) if op in ("Tm", "Td", "TD") else []
            antes_m = tlm                                   # la matriz de línea JUSTO antes de posicionar
            if op == "Tm":
                if len(a) == 6:
                    tlm = tuple(a)
            elif op in ("Td", "TD"):
                if len(a) == 2:
                    if op == "TD":
                        tl = -a[1]
                    tlm = lin(tlm, a[0], a[1])
            else:
                tlm = lin(tlm, 0, -tl)                      # T*, ' y ": a la línea siguiente (interlineado)
            tramo = {"bt": bt, "pos": i, "op": op, "ini": i, "antes": antes_m, "tlm": tlm,
                     "muestra": op in ("'", '"')}
            if tramo["muestra"]:
                tramo["pt"] = _aplicar(ctm, tlm[4], tlm[5])
        elif op in _TEXTO_OPS:
            if tramo is not None:
                tramo["muestra"] = True
                if "pt" not in tramo:
                    tramo["pt"] = _aplicar(ctm, tramo["tlm"][4], tramo["tlm"][5])
        elif op == "ET":
            cerrar_tramo(i - 1)
            bt, tramo = None, None
        elif op in _CONSTRUCCION:
            if ini is None:
                ini, pts, clip = i, [], False
            a = nums(it)
            if op == "re" and len(a) == 4:
                x, y, w, h = a
                for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
                    pts.append(_aplicar(ctm, px, py))
            else:
                for k in range(0, len(a) - 1, 2):
                    pts.append(_aplicar(ctm, a[k], a[k + 1]))
        elif op in ("W", "W*"):
            clip = True
        elif op in _PINTADO:
            if ini is not None and pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                out.append({"ini": ini, "fin": i, "tipo": "trazado", "capa": capa_actual(), "ctm": ctm,
                            "clip": clip, "pinta": op, "bbox": [min(xs), min(ys), max(xs), max(ys)]})
            ini, pts, clip = None, [], False
    return out


def _centro(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


def _dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _tol(b):
    return max(1.0, 0.15 * min(abs(b[2] - b[0]), abs(b[3] - b[1])))


def _iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    un = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / un if un > 0 else 0.0


def _emparejar_trazos(trazos, cajas):
    """Gemelo de `emparejarTrazos`: cada pieza detectada ↔ el trazo que más se le superpone (las grandes
    eligen primero; vale con la mitad de superposición o centros cerca). → lista (unidad o None) por pieza."""
    usados, out = set(), [None] * len(cajas)
    orden = sorted(range(len(cajas)), key=lambda i: (-(cajas[i][2] - cajas[i][0]) * (cajas[i][3] - cajas[i][1]), i))
    for i in orden:
        b, mejor = cajas[i], None
        for k, u in enumerate(trazos):
            if k in usados:
                continue
            s, d = _iou(u["bbox"], b), _dist(_centro(u["bbox"]), _centro(b))
            if s < 0.5 and d > _tol(b):
                continue
            p = s - d * 1e-6
            if mejor is None or p > mejor[0]:
                mejor = (p, k)
        if mejor:
            usados.add(mejor[1])
            out[i] = trazos[mejor[1]]
    return out


def _num(v):
    from decimal import Decimal
    return Decimal("%.4f" % v)


def _traslado_usuario(m, dx, dy):
    det = m[0] * m[3] - m[1] * m[2]
    if not det:
        raise ValueError("una pieza del molde se dibuja con una transformación que no se puede invertir")
    return ((m[3] * dx - m[2] * dy) / det, (-m[1] * dx + m[0] * dy) / det)


def _trazado_en_usuario(segs, m):
    from pikepdf import ContentStreamInstruction as CSI, Operator
    det = m[0] * m[3] - m[1] * m[2]
    if not det:
        raise ValueError("una pieza del molde se dibuja con una transformación que no se puede invertir")

    def inv(X, Y):
        return ((m[3] * (X - m[4]) - m[2] * (Y - m[5])) / det, (-m[1] * (X - m[4]) + m[0] * (Y - m[5])) / det)
    out = []
    for s in segs or []:
        op = s[0]
        if op in ("m", "l"):
            p = inv(s[1], s[2])
            out.append(CSI([_num(p[0]), _num(p[1])], Operator(op)))
        elif op == "c":
            a, b, c = inv(s[1], s[2]), inv(s[3], s[4]), inv(s[5], s[6])
            out.append(CSI([_num(a[0]), _num(a[1]), _num(b[0]), _num(b[1]), _num(c[0]), _num(c[1])], Operator("c")))
        elif op == "re":
            x, y, w, h = s[1], s[2], s[3], s[4]
            q = [inv(X, Y) for X, Y in ((x, y), (x + w, y), (x + w, y + h), (x, y + h))]
            out.append(CSI([_num(q[0][0]), _num(q[0][1])], Operator("m")))
            for p in q[1:]:
                out.append(CSI([_num(p[0]), _num(p[1])], Operator("l")))
            out.append(CSI([], Operator("h")))
        elif op == "h":
            out.append(CSI([], Operator("h")))
    return out


def trasladar_segs(segs, dx, dy):
    """Segmentos crudos corridos (dx, dy). Gemelo: `trasladarSegs`."""
    out = []
    for s in segs or []:
        if s[0] in ("m", "l"):
            out.append([s[0], s[1] + dx, s[2] + dy])
        elif s[0] == "c":
            out.append(["c", s[1] + dx, s[2] + dy, s[3] + dx, s[4] + dy, s[5] + dx, s[6] + dy])
        elif s[0] == "re":
            out.append(["re", s[1] + dx, s[2] + dy, s[3], s[4]])
        else:
            out.append(list(s))
    return out


def resolver_ediciones(antes, pedidos):
    """Gemelo de `resolverEdiciones`: lo pedido (pieza por su número en cada talle, o una pieza de
    referencia al agregar, + corrimiento + forma centrada en (0, 0) con su `caja`) → `(ediciones, esperado)`
    con las cajas de la detección del molde de AHORA."""
    ediciones, esperado, nuevas = [], [], {}
    for p in pedidos or []:
        cs = antes.get(p["talle"]) or []
        dx, dy = float(p.get("dx") or 0), float(p.get("dy") or 0)
        otras = [c["bbox_raw"] for c in cs]
        if p["tipo"] == "agregar":
            ref = p.get("ref")
            if ref is None or not (0 <= int(ref) < len(cs)):
                raise ValueError(f"no está la pieza de referencia en el talle {p['talle']}")
            c = _centro(cs[int(ref)]["bbox_raw"])
            x, y = c[0] + dx, c[1] + dy
            if p["talle"] not in nuevas:
                nuevas[p["talle"]] = len(cs)
            ediciones.append({"talle": p["talle"], "tipo": "agregar", "segmentos": trasladar_segs(p["forma"], x, y)})
            k = p["caja"]
            esperado.append({"talle": p["talle"], "idx": nuevas[p["talle"]], "nueva": True, "bbox": [k[0] + x, k[1] + y, k[2] + x, k[3] + y]})
            nuevas[p["talle"]] += 1
            continue
        i = int(p["idx"])
        if not (0 <= i < len(cs)):
            raise ValueError(f"la pieza {i + 1} no está en el talle {p['talle']}")
        b = cs[i]["bbox_raw"]
        if p["tipo"] == "mover":
            ediciones.append({"talle": p["talle"], "tipo": "mover", "idx": i, "bbox": b, "dx": dx, "dy": dy, "otras": otras})
            esperado.append({"talle": p["talle"], "idx": i, "bbox": [b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy]})
        elif p["tipo"] == "reemplazar":
            c = _centro(b)
            x, y = c[0] + dx, c[1] + dy
            ediciones.append({"talle": p["talle"], "tipo": "reemplazar", "idx": i, "bbox": b, "dx": dx, "dy": dy, "otras": otras,
                              "segmentos": trasladar_segs(p["forma"], x, y)})
            k = p["caja"]
            esperado.append({"talle": p["talle"], "idx": i, "bbox": [k[0] + x, k[1] + y, k[2] + x, k[3] + y]})
        else:
            raise ValueError(f"cambio desconocido: {p['tipo']}")
    return ediciones, esperado


def editar_piezas(plantilla, ediciones, mesa=1, destino=None):
    """Gemelo de `editarPiezas`: escribe la VERSIÓN nueva y devuelve su ruta. `ediciones` como allá.
    Con `destino`, escribe AHÍ y no toca el puntero de versión (el servidor lo verifica antes de
    convertirlo en la versión vigente: si la edición no dio, no queda nada a medias)."""
    from pikepdf import ContentStreamInstruction as CSI, Operator, parse_content_stream, unparse_content_stream
    if not ediciones:
        raise ValueError("no hay nada que cambiar")
    vigente = OA.ruta_vigente(plantilla)
    _version = destino is None
    destino = destino or OA._ver_path(plantilla, OA._ver_actual(plantilla) + 1)
    pdf = pikepdf.open(vigente)
    try:
        pg = pdf.pages[mesa - 1]
        inst = list(parse_content_stream(pg))
        unidades = _unidades_con_capa(inst, _capas_de_recursos(pg))
        usadas = set()
        antes, despues, reemplazo, borrar = {}, {}, {}, set()

        tramos_movidos = {}                                 # id(tramo) → (tu, tv) en el espacio del usuario

        def envolver(u, dx, dy):
            tu, tv = _traslado_usuario(u["ctm"], dx, dy)
            if u["tipo"] == "texto":
                tramos_movidos[id(u)] = (tu, tv)
                return
            antes.setdefault(u["ini"], []).extend([CSI([], Operator("q")),
                                                   CSI([1, 0, 0, 1, _num(tu), _num(tv)], Operator("cm"))])
            despues.setdefault(u["fin"], []).append(CSI([], Operator("Q")))

        agregadas = []
        por_talle = {}                       # talle → (trazos, pares): el emparejado de TODAS sus piezas

        def igual(a, b):
            return all(abs(v - b[k]) < 0.5 for k, v in enumerate(a))
        for e in ediciones:
            if e["tipo"] == "agregar":
                agregadas.append(e)
                continue
            cajas = e.get("otras") or [e["bbox"]]
            if e["talle"] not in por_talle:
                tt = [u for u in unidades if u["capa"] == e["talle"] and u["tipo"] == "trazado" and not u["clip"] and u["pinta"] != "n"]
                por_talle[e["talle"]] = (tt, _emparejar_trazos(tt, cajas))
            trazos_t, pares = por_talle[e["talle"]]
            k_ = e.get("idx")
            if k_ is None:
                k_ = next((j for j, b in enumerate(cajas) if igual(b, e["bbox"])), -1)
            pieza = pares[k_] if 0 <= k_ < len(pares) else None
            ids_usadas = {id(unidades[j]) for j in usadas}
            if pieza is None or id(pieza) in ids_usadas:
                raise ValueError(f"no se encontró la pieza dentro del molde (talle {e['talle']}): este molde no se puede editar así")
            de_capa = [u for k, u in enumerate(unidades) if u["capa"] == e["talle"] and k not in usadas]
            trazos = [u for u in trazos_t if id(u) not in ids_usadas]
            ids_pares = {id(u) for u in pares if u is not None}
            iguales = [u for u in trazos if u is not pieza and igual(u["bbox"], pieza["bbox"]) and id(u) not in ids_pares]
            de_otras = [u for j, u in enumerate(pares) if u is not None and j != k_]
            pb = pieza["bbox"]
            m = 0.01 * max(pb[2] - pb[0], pb[3] - pb[1])

            def es_otra(u):
                return any(u is o or igual(o["bbox"], u["bbox"]) for o in de_otras)
            marcas = [u for u in trazos if u is not pieza and u not in iguales and not es_otra(u)
                      and u["bbox"][0] >= pb[0] - m and u["bbox"][2] <= pb[2] + m
                      and u["bbox"][1] >= pb[1] - m and u["bbox"][3] <= pb[3] + m]
            textos = [u for u in de_capa if u["tipo"] == "texto" and u.get("pt")
                      and pb[0] - m <= u["pt"][0] <= pb[2] + m and pb[1] - m <= u["pt"][1] <= pb[3] + m]
            for u in [pieza] + iguales + marcas + textos:
                usadas.add(next(k for k, x in enumerate(unidades) if x is u))
            dx, dy = float(e.get("dx") or 0), float(e.get("dy") or 0)
            if e["tipo"] == "mover":
                for u in [pieza] + iguales + marcas + textos:
                    envolver(u, dx, dy)
            elif e["tipo"] == "reemplazar":
                if not e.get("segmentos"):
                    raise ValueError("falta la forma nueva de la pieza")
                for u in [pieza] + iguales:
                    reemplazo[u["ini"]] = (u["fin"], _trazado_en_usuario(e["segmentos"], u["ctm"])
                                           + [CSI([], Operator(str(inst[u["fin"]].operator)))])
                for u in marcas:
                    borrar.update(range(u["ini"], u["fin"] + 1))
                if dx or dy:
                    for u in textos:
                        envolver(u, dx, dy)
            else:
                raise ValueError(f"cambio desconocido: {e['tipo']}")
        # TEXTO (como el gemelo): antes de cada tramo movido, un Tm ABSOLUTO con su lugar corrido (si se
        # posicionaba con Tm, se corre ése); antes del tramo SIGUIENTE que no se mueve y se posicionaba
        # relativo, un Tm con la matriz de línea que tenía. Los operadores originales quedan.
        def tm_de(m, t=(0.0, 0.0)):
            return CSI([_num(m[0]), _num(m[1]), _num(m[2]), _num(m[3]), _num(m[4] + t[0]), _num(m[5] + t[1])], Operator("Tm"))
        sust, meter, por_bloque = {}, {}, {}
        for u in unidades:
            if u["tipo"] == "texto":
                por_bloque.setdefault(u["bt"], []).append(u)
        for tramos in por_bloque.values():
            for k, u in enumerate(tramos):
                prev = tramos[k - 1] if k else None
                if id(u) in tramos_movidos:
                    t = tramos_movidos[id(u)]
                    if u["op"] == "Tm":
                        sust[u["pos"]] = [tm_de(u["tlm"], t)]
                    else:
                        meter[u["ini"] if u["pos"] is None else u["pos"]] = [tm_de(u["antes"], t)]
                elif prev is not None and id(prev) in tramos_movidos and u["op"] and u["op"] != "Tm":
                    meter[u["pos"]] = [tm_de(u["antes"])]
        nuevo, i = [], 0
        while i < len(inst):
            nuevo.extend(meter.get(i, []))
            if i in sust:
                nuevo.extend(sust[i])
                i += 1
                continue
            nuevo.extend(antes.get(i, []))
            if i in reemplazo:
                fin, ins = reemplazo[i]
                nuevo.extend(ins)
                nuevo.extend(despues.get(fin, []))
                i = fin + 1
                continue
            if i not in borrar:
                nuevo.append(inst[i])
            nuevo.extend(despues.get(i, []))
            i += 1
        # AGREGAR (como el gemelo): al final del contenido, ADENTRO de la capa de su talle (la OCG que ya
        # existe: ni capas nuevas ni otro orden), así es la última de su talle y nadie se renumera.
        for e in agregadas:
            ocg = _ocg_por_nombre(pdf, e["talle"])
            if ocg is None:
                raise ValueError(f"el talle {e['talle']} no existe como capa en el molde")
            nom = _nombre_en_recursos(pg, pdf, ocg, "OCpz")
            nuevo.extend([CSI([], Operator("q")), CSI([pikepdf.Name("/OC"), pikepdf.Name("/" + nom)], Operator("BDC")),
                          CSI([0, 0, 0], Operator("RG")), CSI([1], Operator("w"))]
                         + _trazado_en_usuario(e["segmentos"], (1, 0, 0, 1, 0, 0))
                         + [CSI([], Operator("S")), CSI([], Operator("EMC")), CSI([], Operator("Q"))])
        pg.obj.Contents = pdf.make_stream(unparse_content_stream(nuevo))
        pdf.save(destino)
    finally:
        pdf.close()
    if _version:
        OA.fijar_version(plantilla, OA._ver_actual(plantilla) + 1)
    return destino


def verificar_edicion(antes, despues, esperado):
    """Gemelo de `verificarEdicion`: lista de problemas en palabras (vacía = la edición hizo sólo lo pedido)."""
    mal = []
    tocadas = {f"{x['talle']}|{x['idx']}": x["bbox"] for x in esperado}
    mas_de = {}
    for x in esperado:
        if x.get("nueva"):
            mas_de[x["talle"]] = mas_de.get(x["talle"], 0) + 1

    def caja_ok(nb, esp):
        tol = max(2.0, 0.03 * max(esp[2] - esp[0], esp[3] - esp[1]))
        return (_dist(_centro(nb), _centro(esp)) <= tol and abs((nb[2] - nb[0]) - (esp[2] - esp[0])) <= tol
                and abs((nb[3] - nb[1]) - (esp[3] - esp[1])) <= tol)
    for t, a in antes.items():
        d = despues.get(t) or []
        debe = len(a) + mas_de.get(t, 0)
        if len(d) != debe:
            mal.append(f"en el talle {t} quedaron {len(d)} piezas y tenían que ser {debe}")
            continue
        for i in range(len(a), len(d)):
            esp = tocadas.get(f"{t}|{i}")
            if not esp or not caja_ok(d[i]["bbox_raw"], esp):
                mal.append(f"la pieza nueva {i + 1} del talle {t} no quedó donde tenía que quedar")
        for i, c in enumerate(a):
            nb = d[i]["bbox_raw"]
            esp = tocadas.get(f"{t}|{i}")
            if esp:
                tol = max(2.0, 0.03 * max(esp[2] - esp[0], esp[3] - esp[1]))
                if (_dist(_centro(nb), _centro(esp)) > tol or abs((nb[2] - nb[0]) - (esp[2] - esp[0])) > tol
                        or abs((nb[3] - nb[1]) - (esp[3] - esp[1])) > tol):
                    mal.append(f"la pieza {i + 1} del talle {t} no quedó donde tenía que quedar")
            elif any(abs(v - nb[k]) > 0.6 for k, v in enumerate(c["bbox_raw"])):
                mal.append(f"la pieza {i + 1} del talle {t} cambió sin que se la tocara")
    return mal
