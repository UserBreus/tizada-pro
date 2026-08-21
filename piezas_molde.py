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

3. 🔴 **AGREGAR UNA PIEZA RENUMERA A LAS DEMÁS.** El `pieza_idx` no es un id: es la POSICIÓN de la
   pieza en el orden por bbox dentro de su capa (`molde_real.extraer_piezas_mesa`). Al insertar una
   pieza en el medio, todas las que siguen corren un lugar — medido en el molde real: **69 de 138**.
   Si no se remapea, el registro queda apuntando a la pieza vecina y el nombrado se reasigna en
   masa. Por eso `remapear_registro` cruza la detección de ANTES con la de DESPUÉS por bbox (la
   geometría de las que ya estaban no cambia, así que el cruce es exacto, no una heurística) y
   reescribe los `pieza_idx`. No es un extra: es parte de agregar.

⚠️ Una capa nueva NO sirve para esto: en la plantilla, toda capa con dibujo que no esté en
`CAPAS_SISTEMA` se lee como un TALLE (`motor_pedido._talles_de_plantilla`). La pieza va DENTRO de
la capa del talle al que pertenece.
"""
import os

import pikepdf
from pikepdf import Dictionary, Name, Stream

import objetos_agregados as OA
from molde_real import extraer_piezas_mesa


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
                conts.append(c)
        conts.sort(key=lambda c: c["w"] * c["h"], reverse=True)
        return conts
    finally:
        doc.close()


def agregar_pieza(plantilla, colocaciones, mesa=1, etiqueta="Pieza nueva"):
    """Escribe una pieza nueva en `plantilla.ai` y devuelve la ruta de la VERSIÓN nueva.

    `colocaciones` = `{talle: {"segmentos": [...], "dx": float, "dy": float}}` — la geometría que
    va en cada capa y su traslado, en unidades crudas del lienzo. Se escriben TODOS los talles en
    UNA sola pasada = una sola versión nueva del archivo.

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
        for talle, col in colocaciones.items():
            ocg = _ocg_por_nombre(pdf, talle)
            if ocg is None:
                continue                      # ese talle no existe como capa: se salta y se informa
            pname = _nombre_en_recursos(page, pdf, ocg, "OCpz")
            ops = ops_de_segmentos(col["segmentos"], col.get("dx", 0.0), col.get("dy", 0.0), y1)
            if not ops.strip():
                continue
            # Trazo fino y negro, como el resto del molde: lo que importa es el CONTORNO.
            page.contents_add(Stream(pdf, f"q\n/OC /{pname} BDC\n0 0 0 RG 1 w\n{ops}\nS\nEMC\nQ\n".encode()))
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
