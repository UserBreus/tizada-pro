# -*- coding: utf-8 -*-
"""
PIEZAS DE UN MOLDE QUE YA TRAE EL DISEÑO ADENTRO — camino B
===========================================================

El camino de siempre (A) cruza un MOLDE (contornos) con un ARTE (el diseño) usando el mapeo. El
camino B es la alternativa: **un solo archivo donde cada pieza ya trae su diseño estampado**.

Eso rompe la detección de hoy. `molde_real.extraer_piezas_mesa` trata **cada trazado como una
pieza**: sirve para un molde pelado (donde cada trazado ES una pieza) pero con el diseño adentro
una sola prenda explota en decenas de "piezas" — el frente, cada franja, cada logo, cada letra.

**LA CLAVE: la forma de la pieza YA ESTÁ EN EL ARCHIVO.** Illustrator mete el dibujo de cada pieza
dentro de una MÁSCARA DE RECORTE cuyo trazado es la silueta de la pieza. Así que no hay que
reconstruir ningún contorno: hay que *leer el recorte*. Es la misma regla que usa el proyecto de
referencia (`Prueba para tizada`, `src/core/shape.js`): «si la pieza tiene máscara de recorte, su
forma ES el trazado de la máscara; lo que hay adentro nunca cuenta como objeto propio».

Medido sobre el archivo real (`CAMISETA JUGADOR.ai`, 123 MB, 9 mesas, 20 talles en capas), por cada
mesa y talle aparecen entre 3 y 7 recortes: **la misma silueta repetida** (Illustrator repite la
máscara por cada capa de dibujo que recorta) más el **marco de la mesa de trabajo**. De ahí sale el
algoritmo:

  1. Los recortes de ESA capa (talle). Aislar por capa **no es una optimización, es obligatorio**:
     los talles están apilados uno encima del otro (gradación) y sin aislar se funden en una mancha.
  2. Descartar el **marco de la mesa** — el rectángulo que Illustrator agrega al exportar.
  3. **Agrupar por solape**: dos recortes que se pisan son la misma pieza (union-find). Eso junta
     solo las repeticiones de la silueta y, de paso, se traga los recortes anidados del dibujo
     interno sin tener que mirar el nivel de anidamiento.
  4. De cada grupo, el contorno de la pieza es el recorte **de mayor área** — el que cubre a los
     demás. Con su trazado vectorial exacto: no se aproxima nada.

Si el archivo no trae recortes utilizables se cae al **respaldo**: agrupar los trazados pintados por
solape de sus bounding boxes. ⚠️ Ese camino **todavía no se verificó contra un archivo real** (no
hay uno sin máscaras a mano); está marcado como tal en `verificar_molde_con_diseno.py`.

La salida es **el mismo dict que `molde_real._contorno_de_drawing`** (`segmentos`, `bbox_raw`,
`bbox_mu`, `w`, `h`, `mesa`, `talle`, `user_unit`), a propósito: así el registro, el nido, el visor
y el motor siguen funcionando sin enterarse de que la pieza vino por otro camino.
"""

import os

import pymupdf as fitz

from molde_real import _contorno_de_drawing

CM = 28.3465          # puntos PDF por centímetro
_TOL_MARCO = 1.0      # pt de tolerancia para reconocer el marco de la mesa


# ─────────────────────────────────────────────────────────────────
# Lectura del archivo (cacheada: `get_drawings` es lo caro)
# ─────────────────────────────────────────────────────────────────
_CACHE = {}


def _dibujos(doc, mesa):
    """Todo lo que dibuja una mesa, recortes incluidos.

    `get_drawings(extended=True)` es lo único que devuelve los CLIP, y es caro (segundos por mesa
    en el archivo real). Se cachea por documento+mesa porque el alta lo pide una vez por cada uno
    de los 20 talles: sin caché serían 20 lecturas de la misma mesa.
    """
    clave = (id(doc), mesa)
    if clave not in _CACHE:
        _CACHE[clave] = doc[mesa - 1].get_drawings(extended=True)
    return _CACHE[clave]


def olvidar(doc=None):
    """Suelta la caché. Obligatorio antes de cerrar el documento: la clave es `id(doc)` y Python
    reusa los ids de los objetos liberados — sin esto, otro documento podría leer estos dibujos."""
    if doc is None:
        _CACHE.clear()
        return
    for k in [k for k in _CACHE if k[0] == id(doc)]:
        del _CACHE[k]


def _rect_de(d):
    """El rectángulo de un item. Un recorte NO trae `rect` (viene en None): trae `scissor`."""
    return d.get("scissor") or d.get("rect")


# ─────────────────────────────────────────────────────────────────
# LA MARCA: qué molde es del camino B
# ─────────────────────────────────────────────────────────────────
# Un molde del camino B se detecta al SUBIRLO y queda MARCADO EN DISCO, al lado del archivo. No se
# vuelve a adivinar en cada lectura, y eso es a propósito:
#   · **explícito**: el camino se decide una vez, cuando el usuario sube el archivo y el sistema le
#     avisa qué entendió. Un molde del camino A que algún día exporte con una máscara no se cambia
#     de camino solo, en silencio, a mitad de un pedido.
#   · **en disco y no en memoria**: el nesting paraleliza con PROCESOS (PyMuPDF no es thread-safe),
#     y una marca en una variable global no existiría del otro lado. Un archivito sí.
MARCA = "molde.origen"


def _ruta_marca(path_molde):
    return os.path.join(os.path.dirname(os.path.abspath(path_molde)), MARCA)


def marcar(path_molde, con_diseno=True):
    """Deja escrito de qué camino es este molde. Se llama UNA vez, al darlo de alta."""
    ruta = _ruta_marca(path_molde)
    try:
        if con_diseno:
            tmp = ruta + ".tmp"
            with open(tmp, "w", encoding="utf-8") as g:
                g.write("con_diseno\n")
            os.replace(tmp, ruta)          # atómica, como todo lo que se escribe acá
        elif os.path.exists(ruta):
            os.remove(ruta)
        return True
    except OSError:
        return False


def es_camino_b(path_molde):
    """¿Este archivo de molde ya trae el diseño adentro? Lo dice la marca que dejó el alta."""
    if not path_molde:
        return False
    try:
        return os.path.exists(_ruta_marca(path_molde))
    except (OSError, TypeError):
        return False


# ─────────────────────────────────────────────────────────────────
# Descartes y agrupamiento
# ─────────────────────────────────────────────────────────────────
def _es_marco_de_mesa(rect, page):
    """¿Este recorte es el marco de la mesa de trabajo?

    Illustrator agrega al exportar un recorte rectangular del tamaño de la página. Si no se
    descarta, aparece como una "pieza" que es toda la mesa.

    ⚠️ Se compara contra el rectángulo de la página **con tolerancia de 1 pt**, NO por porcentaje
    de área. Probado por las malas: con la regla «ocupa más del 95 % de la mesa» se comía piezas
    reales — en el archivo del usuario, la tira del talle 0 mide 28,7 cm en una mesa de 29,0 cm.
    """
    p = page.rect
    return (abs(rect.x0 - p.x0) < _TOL_MARCO and abs(rect.y0 - p.y0) < _TOL_MARCO
            and abs(rect.x1 - p.x1) < _TOL_MARCO and abs(rect.y1 - p.y1) < _TOL_MARCO)


def _se_pisan(a, b):
    """¿Dos rectángulos comparten superficie de verdad?

    Se mide contra el MÁS CHICO: un recorte del dibujo interno cae entero adentro de la pieza y
    tiene que quedar en su grupo, aunque en área sea una migaja al lado de ella.
    """
    ancho = min(a.x1, b.x1) - max(a.x0, b.x0)
    alto = min(a.y1, b.y1) - max(a.y0, b.y0)
    if ancho <= 0 or alto <= 0:
        return False
    comun = ancho * alto
    menor = min(a.width * a.height, b.width * b.height)
    return menor <= 0 or comun / menor > 0.5


def _agrupar_por_solape(rects):
    """Union-find: los que se pisan quedan en el mismo grupo. Devuelve listas de índices.

    Es la idea de `assembly.js` del proyecto de referencia, pero sobre RECORTES en vez de sobre
    trazados: como son un puñado por mesa y talle (3 a 7 en el archivo real), alcanza con los
    bounding boxes y no hace falta rasterizar nada.
    """
    padre = list(range(len(rects)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if _se_pisan(rects[i], rects[j]):
                ri, rj = raiz(i), raiz(j)
                if ri != rj:
                    padre[rj] = ri

    grupos = {}
    for i in range(len(rects)):
        grupos.setdefault(raiz(i), []).append(i)
    return list(grupos.values())


# ─────────────────────────────────────────────────────────────────
# La detección
# ─────────────────────────────────────────────────────────────────
def piezas_de_mesa(doc, mesa, talle, area_min_cm2=0.25, lado_min_cm=0.3):
    """Las piezas de una mesa en un talle, para un molde que ya trae el diseño adentro.

    Devuelve dicts con la MISMA forma que `molde_real.extraer_piezas_mesa`, en el orden del
    archivo (regla del usuario 2026-08-18: no se reordenan por posición).
    """
    page = doc[mesa - 1]
    cb = page.cropbox
    U = page.rect.width / cb.width if cb.width else 1.0

    cands, rects = [], []
    for d in _dibujos(doc, mesa):
        if d.get("type") != "clip" or d.get("layer") != talle:
            continue
        r = _rect_de(d)
        if r is None or r.width <= 0 or r.height <= 0:
            continue                                   # recortes degenerados (una línea)
        if _es_marco_de_mesa(r, page):
            continue                                   # el marco de la mesa de trabajo
        if not (d.get("items") or []):
            continue
        cands.append(d)
        rects.append(r)

    if not cands:
        return _respaldo_por_trazados(doc, mesa, talle, page, cb, U, area_min_cm2, lado_min_cm)

    piezas = []
    for grupo in _agrupar_por_solape(rects):
        # el recorte de MAYOR ÁREA es el borde externo: el que cubre a todos los del grupo
        i = max(grupo, key=lambda k: rects[k].width * rects[k].height)
        r = rects[i]
        w_cm, h_cm = r.width / U / CM, r.height / U / CM
        if w_cm * h_cm < area_min_cm2 or min(w_cm, h_cm) < lado_min_cm:
            continue
        piezas.append((min(grupo), _contorno_de_drawing(
            {"items": cands[i]["items"], "rect": r}, cb, U, mesa, talle)))

    # el orden del archivo = el orden en que aparece el PRIMER recorte de cada pieza
    piezas.sort(key=lambda p: p[0])
    return [p for _, p in piezas]


def _respaldo_por_trazados(doc, mesa, talle, page, cb, U, area_min_cm2, lado_min_cm):
    """RESPALDO: el archivo no trae recortes utilizables → se agrupan los trazados PINTADOS.

    ⚠️ **Sin verificar contra un archivo real**: todos los moldes con diseño que hay a mano traen
    máscaras. Agrupa por solape de bounding boxes, que es más grosero que la silueta real: si dos
    piezas quedan pegadas en una sola, el archivo no tiene máscaras y hay que mirarlo en serio,
    no aflojar este umbral.
    """
    idx, rects = [], []
    for k, d in enumerate(_dibujos(doc, mesa)):
        if d.get("type") not in ("f", "s", "fs") or d.get("layer") != talle:
            continue
        r = _rect_de(d)
        if r is None or r.width <= 0 or r.height <= 0:
            continue
        idx.append(k)
        rects.append(r)
    if not rects:
        return []

    dibujos = _dibujos(doc, mesa)
    piezas = []
    for grupo in _agrupar_por_solape(rects):
        i = max(grupo, key=lambda k: rects[k].width * rects[k].height)
        r = rects[i]
        w_cm, h_cm = r.width / U / CM, r.height / U / CM
        if w_cm * h_cm < area_min_cm2 or min(w_cm, h_cm) < lado_min_cm:
            continue
        piezas.append((min(grupo), _contorno_de_drawing(dibujos[idx[i]], cb, U, mesa, talle)))
    piezas.sort(key=lambda p: p[0])
    return [p for _, p in piezas]


# ─────────────────────────────────────────────────────────────────
# El molde entero
# ─────────────────────────────────────────────────────────────────
def talles_del_molde(doc):
    """Los talles del molde = las capas (OCG) que el archivo declara, en el orden del archivo."""
    ocgs = doc.get_ocgs() or {}
    orden = []
    try:
        for x in (doc.layer_ui_configs() or []):
            n = x.get("text")
            if n and n not in orden:
                orden.append(n)
    except Exception:
        pass
    for v in ocgs.values():
        n = (v or {}).get("name")
        if n and n not in orden:
            orden.append(n)
    return orden


def registro_del_molde(doc, talles=None, avisar=None):
    """Recorre TODO el molde y devuelve `{(mesa, talle): [piezas]}`.

    `avisar(hecho, total, texto)` recibe el avance: leer 9 mesas del archivo real lleva ~45 s y el
    alta tiene que poder mostrar un cartel honesto en vez de quedarse muda.
    """
    talles = talles or talles_del_molde(doc)
    salida = {}
    total = doc.page_count * max(1, len(talles))
    hecho = 0
    for mesa in range(1, doc.page_count + 1):
        for talle in talles:
            piezas = piezas_de_mesa(doc, mesa, talle)
            if piezas:
                salida[(mesa, talle)] = piezas
            hecho += 1
            if avisar:
                avisar(hecho, total, f"mesa {mesa} · talle {talle}")
    return salida


def alta_molde_con_diseno(path, avisar=None):
    """Da de alta un molde del camino B: arma el registro de TODAS sus piezas, en todos los talles.

    🔴 **Acá no se empareja nada, y esa es la gran diferencia con el camino A.** `alta_plantilla`
    necesita etiquetas de texto «Talle-Pieza-#» en el archivo, y `alta_plantilla_manual` empareja
    las piezas entre talles por centroide, forma y solape — heurísticas que a veces cruzan piezas
    parecidas (de ahí salieron varios bugs del sistema). En el camino B **la correspondencia es
    exacta por construcción**: los talles son CAPAS de la misma mesa, así que la pieza *i* de la
    mesa *m* en el talle T es la misma que la pieza *i* de la mesa *m* en el talle T'. No hay nada
    que adivinar.

    Las piezas salen con nombre PROVISORIO («Pieza 1», «Pieza 2»…) porque el usuario todavía no las
    nombró: se cargan TODAS igual (regla del 2026-08-18 — una pieza sin nombre tiene que entrar al
    molde o no hay forma de nombrarla después) y él las renombra en el visor.
    """
    doc = fitz.open(path)
    try:
        talles = talles_del_molde(doc)
        registro, problemas = {}, []
        if not talles:
            problemas.append("El archivo no declara ninguna capa: no se pueden separar los talles. "
                             "Cada talle tiene que ser una capa con su nombre (M, 3XL, 16…).")

        # 1) las piezas de cada mesa en cada talle
        por_mesa = {}
        total = doc.page_count * max(1, len(talles))
        hecho = 0
        for mesa in range(1, doc.page_count + 1):
            for talle in talles:
                pzs = piezas_de_mesa(doc, mesa, talle)
                if pzs:
                    por_mesa.setdefault(mesa, {})[talle] = pzs
                hecho += 1
                if avisar:
                    avisar(hecho, total, f"mesa {mesa} · talle {talle}")

        # 2) 🔴 LOS DOS ÍNDICES, Y POR QUÉ SON DOS
        #    `pieza_idx` es, por invariante del sistema (MAPA §8.9), **la posición dentro de un
        #    TALLE**. En el camino A eso coincide con la posición dentro de la mesa porque el molde
        #    tiene UNA sola mesa. Acá hay 9, y si se guardara la posición dentro de la mesa las
        #    nueve piezas tendrían `pieza_idx = 0`: el mapa `pieza_idx → nombre` que resuelve las
        #    VARIABLES (`motor_pedido`, `_idx_a_nombre`) las colapsaría en una sola y ocho piezas
        #    quedarían invisibles — en silencio, que es la peor forma.
        #    Pero el motor SÍ necesita la posición dentro de la mesa para agarrar el contorno
        #    (`_armar_base` hace `extraer_piezas_mesa(mesa, talle)[idx]`). Así que se guardan los
        #    dos, cada uno con un significado: `pieza_idx` (dentro del talle, ÚNICO) e `idx_mesa`
        #    (dentro de la mesa). Un molde del camino A no trae `idx_mesa` y sigue como estaba.
        antes = {}                                   # cuántas piezas van antes, en ese talle
        acum = {}
        for mesa in sorted(por_mesa):
            for talle in talles:
                antes[(talle, mesa)] = acum.get(talle, 0)
                acum[talle] = acum.get(talle, 0) + len(por_mesa[mesa].get(talle, []))

        n = 0
        for mesa in sorted(por_mesa):
            cuantas = max(len(v) for v in por_mesa[mesa].values())
            for i in range(cuantas):
                n += 1
                nombre = f"Pieza {n}"
                for talle, pzs in por_mesa[mesa].items():
                    if i >= len(pzs):
                        continue                     # este talle no tiene esa pieza: no se inventa
                    cont = pzs[i]
                    registro.setdefault(nombre, {})[talle] = {
                        "mesa": mesa,
                        "pieza_idx": antes[(talle, mesa)] + i,   # dentro del TALLE (único)
                        "idx_mesa": i,                           # dentro de la MESA (para el motor)
                        "w_cm": round(cont["w"] / cont["user_unit"] / CM, 1),
                        "h_cm": round(cont["h"] / cont["user_unit"] / CM, 1),
                        "bbox_mu": [round(v, 2) for v in cont["bbox_mu"]],
                        "ancla": _ancla_por_defecto(cont)}

        if not registro and not problemas:
            problemas.append("No se detectó ninguna pieza. ¿El archivo trae el diseño adentro de "
                             "cada pieza, con su máscara de recorte?")

        completos = [t for t in talles if all(t in registro.get(p, {}) for p in registro)]
        detalle = {}
        for pieza, por_talle in registro.items():
            mayor = max(por_talle.values(), key=lambda v: v["h_cm"])
            detalle[pieza] = {"mesas": sorted({v["mesa"] for v in por_talle.values()}),
                              "talles": [t for t in talles if t in por_talle],
                              "talle_mayor_cm": {"w": mayor["w_cm"], "h": mayor["h_cm"]}}
        return {"mesas": doc.page_count, "talles": talles, "piezas": sorted(registro),
                "completos": completos, "registro": registro, "problemas": problemas,
                "advertencias": [], "piezas_detalle": detalle, "origen": "con_diseno"}
    finally:
        olvidar(doc)
        doc.close()


def detectar_para_visor(doc, talle_ref=None, sep_cm=2.0):
    """Lo que dibuja el visor de «Nombrar piezas» para un molde del camino B.

    🔴 **Muestra TODAS LAS MESAS JUNTAS.** El visor de hoy elige UNA mesa (la de más trazos) porque
    en el camino A una mesa trae muchas piezas. Acá es al revés: **cada mesa es una pieza**, así que
    mostrar una sola mesa mostraría una sola pieza y no habría nada que nombrar. Se acomodan en una
    grilla, cada una en su tamaño REAL (mm), que es lo mismo que hace el proyecto de referencia
    («las mesas se cargan todas juntas en un solo espacio de trabajo, no de a una»).

    Y va **sólo con los contornos**: ni un trazo del diseño. Es el pedido del usuario — el archivo
    real pesa 123 MB y mandarle el dibujo al navegador es exactamente lo que hace lento el sistema.

    Devuelve la misma estructura que `motor_pedido.detectar_piezas`, así el visor no cambia.
    """
    from motor_pedido import _item_visor            # diferido: motor_pedido importa de molde_real

    talles = talles_del_molde(doc)
    if not talles:
        raise ValueError("El archivo no declara capas: no se pueden separar los talles.")
    # el talle de referencia por defecto: el del medio, que es el que mejor representa al molde
    talle_ref = talle_ref if talle_ref in talles else talles[len(talles) // 2]

    sep = sep_cm * CM
    zoom = 10.0 / CM                                 # 1 unidad de salida = 1 mm (igual que hoy)

    # 1) las piezas de cada mesa, en el talle elegido
    items, cursor_x, cursor_y, alto_fila = [], sep, sep, 0.0
    ancho_max = 0.0
    piezas_mesa = []
    for mesa in range(1, doc.page_count + 1):
        for i, cont in enumerate(piezas_de_mesa(doc, mesa, talle_ref)):
            piezas_mesa.append((mesa, i, cont))
    if not piezas_mesa:
        raise ValueError(f"No se detectaron piezas en el talle {talle_ref!r}.")

    # 2) ancho de la grilla: la raíz del área total da filas y columnas parejas, y nunca menos que
    #    la pieza más ancha (si no, esa pieza se saldría de la grilla)
    area = sum(c["w"] * c["h"] for _, _, c in piezas_mesa)
    objetivo = max(max(c["w"] for _, _, c in piezas_mesa), (area ** 0.5) * 1.4)

    for idx, (mesa, i, cont) in enumerate(piezas_mesa):
        page = doc[mesa - 1]
        cb = page.cropbox
        U = page.rect.width / cb.width if cb.width else 1.0
        x0, y0, x1, y1 = cont["bbox_mu"]
        w, h = x1 - x0, y1 - y0
        if cursor_x > sep and cursor_x + w > objetivo:      # no entra en la fila: renglón nuevo
            cursor_x = sep
            cursor_y += alto_fila + sep
            alto_fila = 0.0
        # `_item_visor` ubica la pieza restándole el origen del recorte: se le pasa un recorte
        # sintético para que la pieza caiga justo en su casillero de la grilla.
        clip = fitz.Rect(x0 - cursor_x, y0 - cursor_y, x0 - cursor_x + 1, y0 - cursor_y + 1)
        it = _item_visor(cont, idx, clip, cb, U, zoom)
        it["mesa"] = mesa
        it["t_idx"] = i                              # su índice DENTRO de la mesa = el del registro
        items.append(it)
        cursor_x += w + sep
        alto_fila = max(alto_fila, h)
        ancho_max = max(ancho_max, cursor_x)

    return {"mesa": None, "talle_ref": talle_ref, "talles": talles, "unidad": "mm",
            "img_w": round((ancho_max + sep) * zoom, 1),
            "img_h": round((cursor_y + alto_fila + sep) * zoom, 1),
            "piezas": items, "sin_variantes": False, "origen": "con_diseno"}


def _ancla_por_defecto(cont):
    """La etiqueta de corte arranca centrada y pegada al borde de abajo, como en el camino A
    (`motor_pedido._ancla_sintetica`). Después el usuario la mueve pieza por pieza (E4)."""
    x0, _y0, x1, y1 = cont["bbox_mu"]
    size = 3.0 * (CM / 10.0)                        # 3 mm
    return {"x": round((x0 + x1) / 2, 1), "y": round(y1 - size * 0.25, 1),
            "angulo": 0.0, "size_pt": round(size, 2), "fuente": "Arial-BoldMT"}


def parece_molde_con_diseno(doc, mesas_a_mirar=2):
    """¿Este archivo es del camino B? Devuelve `(sí/no, motivo)`.

    Sirve para avisarle al usuario que subió el archivo equivocado ANTES de procesarlo, no después.
    El criterio es directo: un molde con el diseño adentro trae **máscaras de recorte** y **mucho
    relleno**; un molde pelado son trazos sueltos y casi ningún recorte.
    """
    clips = pintados = 0
    for mesa in range(1, min(doc.page_count, mesas_a_mirar) + 1):
        page = doc[mesa - 1]
        for d in _dibujos(doc, mesa):
            if d.get("type") == "clip":
                r = _rect_de(d)
                if r is not None and r.width > 0 and r.height > 0 and not _es_marco_de_mesa(r, page):
                    clips += 1
            elif d.get("type") in ("f", "fs"):
                pintados += 1
    if clips == 0:
        return False, "el archivo no trae máscaras de recorte: parece un molde sin diseño"
    if pintados == 0:
        return False, "el archivo trae recortes pero nada pintado adentro"
    return True, f"{clips} máscaras de recorte con dibujo adentro"
