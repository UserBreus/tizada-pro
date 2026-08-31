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
