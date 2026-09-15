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

import pikepdf
import pymupdf as fitz

# ⚡ NIVEL DE COMPRESIÓN al escribir PDFs (2026-09-07). qpdf deflatea con el nivel por defecto de
# zlib (6): guardar la hoja aplanada del pedido de 5 prendas costaba 6,9 s; con nivel 1 son 1,7 s
# y el archivo pasa de 18,0 a 20,4 MB. Es SIN PÉRDIDA (flate es flate: ni un byte del contenido
# cambia, sólo cuánto se empaqueta), así que el color y el vector siguen exactos. Vale para todo
# el proceso (es un ajuste global de pikepdf). `TIZADA_FLATE=6` vuelve al de siempre.
try:
    pikepdf.settings.set_flate_compression_level(int(os.environ.get("TIZADA_FLATE") or 1))
except Exception:
    pass


from molde_real import _contorno_de_drawing

CM = 28.3465          # puntos PDF por centímetro
_TOL_MARCO = 1.0      # pt de tolerancia para reconocer el marco de la mesa


# ─────────────────────────────────────────────────────────────────
# Lectura del archivo (cacheada: `get_drawings` es lo caro)
# ─────────────────────────────────────────────────────────────────
_CACHE = {}
# De qué HILO es cada entrada. Lo necesita `olvidar()` sin documento: un request que termina no
# puede llevarse el caché del hilo de fondo que está desplegando un molde (ahí el caché es lo que
# hace que los 20 talles de una mesa cuesten una sola lectura).
_CACHE_HILO = {}


def _dibujos(doc, mesa):
    """Todo lo que dibuja una mesa, recortes incluidos.

    `get_drawings(extended=True)` es lo único que devuelve los CLIP, y es caro (segundos por mesa
    en el archivo real). Se cachea por documento+mesa porque el alta lo pide una vez por cada uno
    de los 20 talles: sin caché serían 20 lecturas de la misma mesa.
    """
    clave = (id(doc), mesa)
    _CACHE_HILO[clave] = _hilo_actual()
    if clave not in _CACHE:
        if os.environ.get("TIZADA_DIBUJOS_LEGACY") == "1":
            _CACHE[clave] = doc[mesa - 1].get_drawings(extended=True)
        else:
            # ⚡ (2026-09-07) `get_cdrawings`: lo mismo que `get_drawings` pero CRUDO — tuplas en
            # vez de Point/Rect/Quad. Medido en el archivo real: la mesa 2 pasa de 9,0 s a 2,2 s,
            # porque los 7 s eran PyMuPDF envolviendo en objetos los miles de puntos del DISEÑO,
            # que acá no se miran (sólo se quieren los recortes del talle). Los pocos trazados
            # que sí se usan se convierten al vuelo (`_rect_de`, `_items_objetos`).
            _CACHE[clave] = doc[mesa - 1].get_cdrawings(extended=True)
    return _CACHE[clave]


def _hilo_actual():
    import threading
    return threading.get_ident()


def olvidar(doc=None):
    """Suelta la caché. Obligatorio antes de cerrar el documento: la clave es `id(doc)` y Python
    reusa los ids de los objetos liberados — sin esto, otro documento podría leer estos dibujos.

    🔴 SIN DOCUMENTO se lleva SÓLO lo de ESTE HILO. Lo llama el `teardown_request` al terminar cada
    request (si no, los dibujos de una mesa entera quedaban residentes para siempre); vaciarlo todo
    ahí le tiraría el caché al hilo de fondo que está desplegando un molde, y ese hilo pide la
    misma mesa una vez por talle: sin caché son 2,2 s por talle en vez de una sola lectura."""
    if doc is None:
        _yo = _hilo_actual()
        for k in [k for k, h in _CACHE_HILO.items() if h == _yo]:
            _CACHE.pop(k, None)
            _CACHE_HILO.pop(k, None)
        return
    for k in [k for k in _CACHE if k[0] == id(doc)]:
        del _CACHE[k]
        _CACHE_HILO.pop(k, None)


def _rect_de(d):
    """El rectángulo de un item. Un recorte NO trae `rect` (viene en None): trae `scissor`.
    Con `get_cdrawings` viene como tupla: se devuelve siempre un `fitz.Rect`."""
    r = d.get("scissor") or d.get("rect")
    if r is None or isinstance(r, fitz.Rect):
        return r
    return fitz.Rect(*r)


def _items_objetos(items):
    """Los items de un trazado crudo (`get_cdrawings`) con la forma de `get_drawings`: puntos
    como `fitz.Point`, rectángulos como `fitz.Rect`, cuadriláteros como `fitz.Quad`. Es lo que
    espera `molde_real._contorno_de_drawing` (`p.x`, `rr.x0`, `q.ul`). Se aplica SÓLO al trazado
    elegido de cada pieza: convertir todos era lo que costaba 7 s por mesa."""
    out = []
    for it in items or []:
        op = it[0]
        if op == "l":
            out.append(("l", fitz.Point(it[1]), fitz.Point(it[2])))
        elif op == "c":
            out.append(("c", fitz.Point(it[1]), fitz.Point(it[2]), fitz.Point(it[3]), fitz.Point(it[4])))
        elif op == "re":
            out.append(it if isinstance(it[1], fitz.Rect) else ("re", fitz.Rect(*it[1]), it[2]))
        elif op == "qu":
            out.append(it if isinstance(it[1], fitz.Quad) else ("qu", fitz.Quad(it[1])))
        else:
            out.append(it)
    return out


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

    🔴 Primero mira el MOLDE DESPLEGADO (ver más abajo): si el alta ya dejó escritos los contornos
    de esta mesa, se leen de ahí y no se abre el dibujo. Medido en el pedido real, `get_drawings`
    de las 9 mesas costaba 109 s **por tizada** — la misma lectura que el alta ya había hecho.
    Con los umbrales por defecto nada más: son los del alta, y son los que se guardaron.
    """
    if area_min_cm2 == 0.25 and lado_min_cm == 0.3:
        d = _leer_desplegado(getattr(doc, "name", None), mesa)
        if d is not None:
            import copy
            return copy.deepcopy(d["contornos"].get(talle) or [])
    return _piezas_de_mesa_cruda(doc, mesa, talle, area_min_cm2, lado_min_cm)


def _piezas_de_mesa_cruda(doc, mesa, talle, area_min_cm2=0.25, lado_min_cm=0.3):
    """`piezas_de_mesa` leyendo el archivo de verdad (`get_drawings`). Es lo que corre el alta,
    una vez por mesa, y lo que guarda el desplegado."""
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

    pintado = _pintado_por_clip(_dibujos(doc, mesa), talle)
    trazos = [_rect_de(x) for x in _dibujos(doc, mesa) if x.get("type") == "s" and x.get("layer") == talle]
    trazos = [t for t in trazos if t is not None and t.width > 0 and t.height > 0]
    piezas = []
    for grupo in _agrupar_por_solape(rects):
        # 🔴 El contorno es el recorte de mayor área ENTRE LOS QUE TIENEN EL DISEÑO ADENTRO
        # (rellenos). Antes era el mayor del grupo a secas, y en el archivo real el mayor es la
        # LÍNEA DE CORTE dibujada: un recorte 1 mm más alto (cuello, costadillo) o 3,5 mm más
        # ancho (cuello curvo) con sólo TRAZOS adentro. La pieza salía más grande que el diseño:
        # una franja blanca entre el estampado y el borde de corte, «borde de más de 3 mm» y
        # piezas «por fuera de lo que deberían ser» (reporte del usuario 2026-09-07). Si ningún
        # recorte del grupo tiene rellenos, vale el mayor, como siempre.
        con_diseno = [k for k in grupo if pintado.get(id(cands[k]), (0, 0))[0] > 0]
        i = max(con_diseno or grupo, key=lambda k: rects[k].width * rects[k].height)
        r = rects[i]
        # 🔴 LA LÍNEA DE CORTE DEL ARCHIVO (2026-09-07, pedido del usuario: «que los cambios los
        # haga en el borde que viene»). Si en el grupo hay un recorte con TRAZOS y sin rellenos
        # que envuelve al del diseño, es la línea de corte que dibujó el diseñador (medido: 0,5 a
        # 4 mm más grande que la máscara del diseño, con un trazo de 2 mm centrado en ella). ESA
        # es la pieza: su geometría es el contorno (nesting, clip, borde) y el trazo se saca del
        # dibujo en la etapa de páginas (`quitar_linea_de_corte`) para volver a trazarlo con la
        # configuración del borde. Sin línea en el archivo: la máscara del diseño, como siempre.
        linea = None
        if con_diseno:
            # el trazo puede estar ADENTRO del recorte (cuello recto, camiseta) o ser el dibujo
            # que le sigue, con su misma caja (cuello curvo: el grupo se cierra antes del trazo)
            def _es_linea(k):
                f, s = pintado.get(id(cands[k]), (0, 0))
                if f > 0 or not _envuelve(rects[k], r):
                    return False
                return s > 0 or any(_envuelve(rects[k], tr, 1.0) and _envuelve(tr, rects[k], 1.0) for tr in trazos)
            envol = [k for k in grupo if k != i and _es_linea(k)]
            if envol:
                linea = max(envol, key=lambda k: rects[k].width * rects[k].height)
        if linea is not None:
            i, r = linea, rects[linea]
        w_cm, h_cm = r.width / U / CM, r.height / U / CM
        if w_cm * h_cm < area_min_cm2 or min(w_cm, h_cm) < lado_min_cm:
            continue
        cont = _contorno_de_drawing({"items": _items_objetos(cands[i]["items"]), "rect": r}, cb, U, mesa, talle)
        if linea is not None:
            cont["linea_corte"] = True          # el estilo (ancho, color) lo agrega la etapa de páginas
        piezas.append((min(grupo), cont))

    # el orden del archivo = el orden en que aparece el PRIMER recorte de cada pieza
    piezas.sort(key=lambda p: p[0])
    return [p for _, p in piezas]


def _pintado_por_clip(dibujos, talle):
    """Cuántos RELLENOS y cuántos TRAZOS hay adentro de cada recorte de la capa `talle`:
    `{id(clip): (rellenos, trazos)}`. `get_drawings(extended=True)` devuelve los dibujos EN ORDEN
    con su `level`: lo que sigue a un recorte de nivel L con nivel mayor está adentro de él, hasta
    el próximo dibujo de nivel ≤ L. Se cuenta también lo de los recortes anidados."""
    seq = [d for d in dibujos if d.get("layer") == talle]
    out = {}
    for k, d in enumerate(seq):
        if d.get("type") != "clip":
            continue
        L = d.get("level") or 0
        f = s = 0
        for y in seq[k + 1:]:
            if (y.get("level") or 0) <= L:
                break
            t = y.get("type")
            if t in ("f", "fs"):
                f += 1
            elif t == "s":
                s += 1
        out[id(d)] = (f, s)
    return out


def _envuelve(a, b, tol=1.0):
    """¿El rectángulo `a` contiene al `b` (con `tol` puntos de tolerancia)?"""
    return (a.x0 <= b.x0 + tol and a.y0 <= b.y0 + tol and a.x1 >= b.x1 - tol and a.y1 >= b.y1 - tol)


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
        piezas.append((min(grupo), _contorno_de_drawing(
            {"items": _items_objetos(dibujos[idx[i]].get("items")), "rect": r}, cb, U, mesa, talle)))
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


def alta_molde_con_diseno(path, avisar=None, procesos=None, paginas=True):
    """Da de alta un molde del camino B: arma el registro de TODAS sus piezas, en todos los talles.

    `procesos` = cuántas mesas desplegar a la vez (None = de a una, en este proceso). El servidor
    pasa su tope; los scripts van serial, porque un ProcessPool en Windows re-importa el módulo
    principal y un script sin `if __name__ == "__main__"` se volvería a ejecutar entero.

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

        # 1) 🔴 DESPLEGAR cada mesa: sus contornos en todos los talles Y la página de cada talle
        #    ya aislada y podada, escritos al lado del archivo. El archivo se lee UNA vez, acá, y
        #    el motor no vuelve a abrir el dibujo nunca más (ver «EL MOLDE DESPLEGADO»). Con
        #    `procesos` va una mesa por proceso: PyMuPDF/pikepdf no son thread-safe.
        #    `paginas=False` (el servidor): la subida responde con los contornos y las páginas por
        #    talle se arman después, en segundo plano (`_prewarm_desplegado`).
        por_mesa = desplegar_molde(path, talles, avisar=avisar, procesos=procesos, paginas=paginas) if talles else {}

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

        # 3) 🔴 EL VISOR DE TODOS LOS TALLES, ACÁ MISMO — es lo que hace que «nombrar piezas» y
        #    «ubicar la etiqueta» anden al instante por pesado que sea el diseño.
        #    Leer los dibujos del archivo es lo único caro de esas pantallas: 52 s para UN talle
        #    (medido), y son enteros `get_drawings` de las 9 mesas. Pero acá esos contornos YA
        #    están leídos —es lo que acaba de hacer el bucle de arriba—, así que acomodarlos en la
        #    grilla de cada talle no cuesta nada. Se guardan y el visor no vuelve a abrir el PDF.
        visor = {}
        _aco = acomodo_mesas(por_mesa)          # UNA vez: el mismo lugar para la mesa en todos los talles
        for talle in talles:
            _pm = [(mesa, i, cont)
                   for mesa in sorted(por_mesa)
                   for i, cont in enumerate(por_mesa[mesa].get(talle) or [])]
            if not _pm:
                continue
            try:
                visor[talle] = layout_visor(doc, _pm, talle, talles, acomodo=_aco)
            except Exception as e:
                # Que falle el layout de UN talle no puede tumbar el alta: sin su entrada, el
                # visor de ese talle se calcula a demanda como antes (lento, pero anda).
                print(f"[camino B] no se pudo preparar el visor del talle {talle}: {e}")

        completos = [t for t in talles if all(t in registro.get(p, {}) for p in registro)]
        detalle = {}
        for pieza, por_talle in registro.items():
            mayor = max(por_talle.values(), key=lambda v: v["h_cm"])
            detalle[pieza] = {"mesas": sorted({v["mesa"] for v in por_talle.values()}),
                              "talles": [t for t in talles if t in por_talle],
                              "talle_mayor_cm": {"w": mayor["w_cm"], "h": mayor["h_cm"]}}
        return {"mesas": doc.page_count, "talles": talles, "piezas": sorted(registro),
                "completos": completos, "registro": registro, "problemas": problemas,
                "advertencias": [], "piezas_detalle": detalle, "origen": "con_diseno",
                # el visor ya armado, talle por talle (lo guarda el servidor: ver `_visor_guardar`)
                "visor": visor}
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
    talles = talles_del_molde(doc)
    if not talles:
        raise ValueError("El archivo no declara capas: no se pueden separar los talles.")
    # el talle de referencia por defecto: el del medio, que es el que mejor representa al molde
    talle_ref = talle_ref if talle_ref in talles else talles[len(talles) // 2]
    piezas_mesa, por_mesa = [], {}
    for mesa in range(1, doc.page_count + 1):
        # TODOS los talles: es lo que define dónde va cada mesa (ver `acomodo_mesas`), y no cuesta
        # nada — `_dibujos` cachea por mesa, así que leer los 20 talles es una sola lectura.
        for t in talles:
            pzs = piezas_de_mesa(doc, mesa, t)
            if pzs:
                por_mesa.setdefault(mesa, {})[t] = pzs
            if t == talle_ref:
                piezas_mesa.extend((mesa, i, c) for i, c in enumerate(pzs))
    if not piezas_mesa:
        raise ValueError(f"No se detectaron piezas en el talle {talle_ref!r}.")
    return layout_visor(doc, piezas_mesa, talle_ref, talles, sep_cm, acomodo_mesas(por_mesa, sep_cm))


def acomodo_mesas(por_mesa, sep_cm=2.0):
    """Dónde va cada MESA en el lienzo del visor: `{"mesas": {mesa: (x0, y0, dx, dy)}, "w", "h"}`.

    🔴 LA REGLA (usuario, 2026-09-04): **el molde se muestra tal cual viene en el archivo**. Los
    talles están dibujados UNO ENCIMA DEL OTRO (la gradación) y así tienen que quedar: no se
    separan, no se acomodan, no se reparten en bloques — ya se distinguen por su CAPA (el ojito
    de la columna de talles). Lo único que hay que acomodar son las MESAS, y sólo porque el PDF
    las guarda todas en el mismo lugar: medido, las 9 páginas del archivo real arrancan en (0,0),
    así que dibujadas tal cual caerían una encima de la otra.

    Por eso el acomodo se calcula **una sola vez con TODOS los talles**: la caja de cada mesa es
    la unión de todas sus piezas en todos sus talles. Si se calculara por talle, el mismo molde
    se movería al cambiar de talle en el visor.

    Las mesas van en filas tipo estante, **en el orden del archivo** (mesa 1, 2, 3…), con el
    ancho de fila que deja el lienzo más parecido a una pantalla.
    `por_mesa` = `{mesa: {talle: [contornos]}}`.
    """
    sep = sep_cm * CM
    cajas = {}
    for mesa, por_t in (por_mesa or {}).items():
        xs0, ys0, xs1, ys1 = [], [], [], []
        for conts in (por_t or {}).values():
            for c in conts or []:
                x0, y0, x1, y1 = c["bbox_mu"]
                xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
        if xs0:
            cajas[mesa] = (min(xs0), min(ys0), max(xs1), max(ys1))
    if not cajas:
        return {"mesas": {}, "w": 1.0, "h": 1.0}
    orden = sorted(cajas)
    sep = max(sep, max(c[3] - c[1] for c in cajas.values()) * 0.05)

    def _armar(ancho_objetivo):
        pos, x, y, alto_fila, ancho = {}, sep, sep, 0.0, 0.0
        for m in orden:
            x0, y0, x1, y1 = cajas[m]
            w, h = x1 - x0, y1 - y0
            if x > sep and x + w > ancho_objetivo:
                x, y, alto_fila = sep, y + alto_fila + sep, 0.0
            pos[m] = (x0, y0, x, y)
            x += w + sep
            alto_fila = max(alto_fila, h)
            ancho = max(ancho, x)
        return pos, ancho + sep - sep, y + alto_fila + sep

    anchos = [cajas[m][2] - cajas[m][0] for m in orden]
    total = sum(anchos) + sep * (len(anchos) + 1)
    mejor = None
    for k in range(1, len(orden) + 1):                # k = filas «objetivo»
        pos, w, h = _armar(max(max(anchos) + 2 * sep, total / k))
        r = abs((w / max(h, 1e-9)) - 16 / 9)
        if mejor is None or r < mejor[0]:
            mejor = (r, pos, w, h)
    _r, pos, w, h = mejor
    return {"mesas": pos, "w": w, "h": h}


def layout_visor(doc, piezas_mesa, talle_ref, talles, sep_cm=2.0, acomodo=None):
    """Acomoda en una grilla los contornos YA LEÍDOS y devuelve lo que dibuja el visor.

    🔴 Está separada de `detectar_para_visor` porque leer los dibujos del archivo es lo ÚNICO caro
    de esta pantalla: medido sobre el archivo real, armar el visor de un talle cuesta 52 s y **los
    52 son `get_drawings` de las 9 mesas** (1.516 items leídos para quedarse con 140 recortes);
    acomodarlos después es instantáneo. Como el ALTA ya recorre todas las mesas y todos los talles,
    puede llamar a esto con los contornos que ya tiene en la mano y dejar el visor de los 20 talles
    listo — y así nombrar piezas y ubicar la etiqueta no vuelven a abrir el PDF nunca más.
    `piezas_mesa` = [(mesa, idx_en_la_mesa, contorno), …].
    """
    from motor_pedido import _item_visor            # diferido: motor_pedido importa de molde_real

    zoom = 10.0 / CM                                 # 1 unidad de salida = 1 mm (igual que hoy)
    acomodo = acomodo or acomodo_mesas({m: {talle_ref: [c for mm, _i, c in piezas_mesa if mm == m]}
                                        for m, _i, _c in piezas_mesa}, sep_cm)
    items = []

    for idx, (mesa, i, cont) in enumerate(piezas_mesa):
        page = doc[mesa - 1]
        cb = page.cropbox
        U = page.rect.width / cb.width if cb.width else 1.0
        cx0, cy0, dx, dy = acomodo["mesas"].get(mesa) or (0.0, 0.0, 0.0, 0.0)
        # 🔴 EL RECORTE ES EL DE LA MESA, NO EL DE LA PIEZA: así cada pieza cae donde el archivo
        # la puso DENTRO de su mesa, y las de distintos talles quedan una encima de la otra —
        # que es como vienen (la gradación). Lo único que se mueve es la MESA entera.
        clip = fitz.Rect(cx0 - dx, cy0 - dy, cx0 - dx + 1, cy0 - dy + 1)
        it = _item_visor(cont, idx, clip, cb, U, zoom)
        it["mesa"] = mesa
        it["t_idx"] = i                              # su índice DENTRO de la mesa = el del registro
        items.append(it)

    return {"mesa": None, "talle_ref": talle_ref, "talles": talles, "unidad": "mm",
            "img_w": round(acomodo["w"] * zoom, 1),
            "img_h": round(acomodo["h"] * zoom, 1),
            "piezas": items, "sin_variantes": False, "origen": "con_diseno",
            # `anidado`: los talles están dibujados uno ENCIMA del otro, como en el archivo. El
            # visor lo usa para no rotular 20 bloques de talle en el mismo lugar.
            "formato": "anidado"}


def visor_junto(visor, registro=None, sep_cm=2.0):
    """TODOS los talles en UN lienzo, **uno encima del otro, como vienen en el archivo**.

    Regla del usuario (2026-09-04): «que respete cómo viene en el archivo… no hablo de las mesas
    sino de los objetos: que no separe los que están uno arriba del otro. Todos los frentes están
    juntos, que los deje así — ya están en diferente capa». Así que acá **no se acomoda nada**:
    los visores por talle ya comparten el mismo lienzo (ver `acomodo_mesas`, el acomodo de las
    mesas se calcula una sola vez para todos los talles), y esto sólo los junta. Los talles se
    distinguen por su CAPA (el ojito de la columna), no por su posición.

    Cada pieza lleva `talle`, `mesa`, `idx_mesa` (su índice dentro de la MESA, lo que usa
    `pieza_renombrar`), `t_idx`/`pieza_idx` (su índice dentro del TALLE, la clave del registro y
    lo que `grupo_pieza` recibe como `guia_idx`), un `idx` global para el visor y `name`.
    """
    import re
    nombres = {}
    for nom, por_t in (registro or {}).items():
        if re.match(r"^\s*Pieza\s+\d+\s*$", str(nom or ""), re.I):
            continue                    # provisorio del alta = sin nombre (la pantalla lo rotula por número)
        for t, inf in (por_t or {}).items():
            if (inf or {}).get("pieza_idx") is not None:
                nombres[(t, int(inf["pieza_idx"]))] = nom
    talles = [t for t in visor.keys() if (visor[t] or {}).get("piezas")]
    piezas, g, por_talle = [], 0, {}
    for t in talles:
        items = visor[t]["piezas"]
        for it in items:
            p = dict(it)
            p["talle"] = t
            p["idx_mesa"] = it.get("t_idx")
            p["pieza_idx"] = it["idx"]
            p["t_idx"] = it["idx"]
            p["idx"] = g
            p["name"] = nombres.get((t, it["idx"]))
            piezas.append(p)
            g += 1
        por_talle[t] = len(items)
    return {"mesa": None, "talles": talles, "unidad": "mm",
            "img_w": max((float((visor[t] or {}).get("img_w") or 0) for t in talles), default=1.0),
            "img_h": max((float((visor[t] or {}).get("img_h") or 0) for t in talles), default=1.0),
            "piezas": piezas, "por_talle": por_talle,
            # `anidado` = los talles van uno encima del otro: el visor NO rotula un bloque por
            # talle (caerían los 20 rótulos en el mismo lugar).
            "formato": "anidado", "origen": "con_diseno"}


def visor_todos(path, avisar=None):
    """El visor de TODOS los talles de un molde ya dado de alta: `{talle: layout}`.

    Existe para los moldes que se cargaron ANTES de que el alta empezara a dejarlo preparado. Sale
    más caro que hacerlo en el alta, pero **se paga una sola vez y para todos los talles**: leer
    los dibujos de las 9 mesas cuesta lo mismo se pida un talle o los veinte, porque los talles
    son capas del mismo archivo. Sin esto, un molde viejo pagaba ~50 s **por cada talle** que se
    mirara."""
    doc = fitz.open(path)
    try:
        talles = talles_del_molde(doc)
        if not talles:
            return {}
        por_mesa = {}
        for mesa in range(1, doc.page_count + 1):
            for t in talles:
                pzs = piezas_de_mesa(doc, mesa, t)
                if pzs:
                    por_mesa.setdefault(mesa, {})[t] = pzs
        _aco = acomodo_mesas(por_mesa)          # el mismo lugar para la mesa en todos los talles
        out = {}
        for k, talle in enumerate(talles):
            _pm = [(mesa, i, cont)
                   for mesa in sorted(por_mesa)
                   for i, cont in enumerate(por_mesa[mesa].get(talle) or [])]
            if not _pm:
                continue
            try:
                out[talle] = layout_visor(doc, _pm, talle, talles, acomodo=_aco)
            except Exception as e:
                print(f"[camino B] no se pudo armar el visor del talle {talle}: {e}")
            if avisar:
                avisar(k + 1, len(talles), talle)
        return out
    finally:
        olvidar(doc)
        doc.close()


def _ancla_por_defecto(cont):
    """La etiqueta de corte arranca centrada y pegada al borde de abajo, como en el camino A
    (`motor_pedido._ancla_sintetica`). Después el usuario la mueve pieza por pieza (E4)."""
    x0, _y0, x1, y1 = cont["bbox_mu"]
    size = 3.0 * (CM / 10.0)                        # 3 mm
    return {"x": round((x0 + x1) / 2, 1), "y": round(y1 - size * 0.25, 1),
            "angulo": 0.0, "size_pt": round(size, 2), "fuente": "Arial-BoldMT"}


# ─────────────────────────────────────────────────────────────────
#  NOMBRAR UNA PIEZA
# ─────────────────────────────────────────────────────────────────
# 🔴 EN EL CAMINO B, NOMBRAR NO ES AGRUPAR: ES RENOMBRAR.
#
# En el camino A el registro se RE-ARMA cada vez que se nombra (`alta_plantilla_manual`): hay que
# emparejar la pieza del talle que se está mirando con su homóloga en los demás, y eso se resuelve
# por forma y posición. Acá no hay nada que emparejar: los talles son CAPAS DE LA MISMA MESA, así
# que la correspondencia ya está resuelta desde el alta y volver a armar el registro sólo puede
# empeorarlo (de hecho lo rompe: `alta_plantilla_manual` asume UNA sola mesa).
#
# Nombrar es, literalmente, cambiar la clave de un dict.


def renombrar(reg, mesa, idx_mesa, nombre):
    """Le pone `nombre` a la pieza que ocupa (`mesa`, `idx_mesa`). Devuelve `(reg_nuevo, ren)`,
    con `ren = {nombre_viejo: nombre_nuevo}` para que el llamador arrastre lo que colgaba del
    nombre (etiqueta, telas, acomodos) con `_migrar_nombres_pieza`.

    La pieza se busca por el par (mesa, índice dentro de la mesa) porque es el único identificador
    que NO depende del talle: `pieza_idx` es la posición dentro del talle y podría no coincidir con
    la que muestra el visor si se está mirando otro talle.

    No toca `mesa`/`idx_mesa`/`pieza_idx`/`bbox_mu`/`ancla` de nadie, y conserva el ORDEN de las
    piezas: de ese orden salen los `id_en_molde` con los que se numeran las piezas en la base.
    """
    import motor_pedido as MP

    if not reg:
        raise ValueError("el molde todavía no tiene piezas registradas")
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("el nombre no puede estar vacío")

    # 1. Encontrar la pieza. Basta con que UN talle la ubique en ese (mesa, idx_mesa): la posición
    #    es la misma en todos los talles (son capas de la misma mesa).
    objetivo = None
    for clave, por_t in reg.items():
        for inf in (por_t or {}).values():
            if not isinstance(inf, dict):
                continue
            if inf.get("mesa") == mesa and inf.get("idx_mesa") == idx_mesa:
                objetivo = clave
                break
        if objetivo:
            break
    if objetivo is None:
        raise ValueError(f"no hay ninguna pieza en la mesa {mesa}, posición {idx_mesa}")
    if objetivo == nombre:
        return reg, {}

    # 2. El nombre final lo decide la MISMA regla del camino A (`nombres_normalizados`): lo que ya
    #    es único se respeta tal cual, y sólo los repetidos se desambiguan con el primer número
    #    libre. Si acá se usara otra regla, dos piezas podrían terminar con el mismo nombre y el
    #    registro —que es un dict POR NOMBRE— perdería una en silencio.
    orden = list(reg.keys())
    asign = [{"idx": i, "nombre": (nombre if c == objetivo else c)} for i, c in enumerate(orden)]
    finales = MP.nombres_normalizados(asign)

    # 3. Reconstruir conservando el orden de inserción.
    nuevo, ren = {}, {}
    for i, viejo in enumerate(orden):
        fin = finales.get(i, viejo)
        nuevo[fin] = reg[viejo]
        if fin != viejo:
            ren[viejo] = fin
    if len(nuevo) != len(reg):
        raise ValueError("el nombre elegido pisa a otra pieza; probá con otro")
    return nuevo, ren


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


# ─────────────────────────────────────────────────────────────────
# EL MOLDE DESPLEGADO — el archivo se lee UNA vez, al cargar
# ─────────────────────────────────────────────────────────────────
# Es la idea central del proyecto de referencia (`Prueba para tizada`): parsea el PDF una sola vez
# a una escena en memoria y después todo —detectar, acomodar, exportar— trabaja sobre eso. Acá el
# equivalente vive EN DISCO, al lado del archivo, en `desplegado/`:
#
#   m{mesa}.pdf   una página por talle, con SÓLO ese talle, aislado y podado (`aislar_capa` con
#                 `podar=True`, byte a byte lo mismo que hacía el motor en cada tizada) y con
#                 nada más que los recursos que usa (fuentes, estados gráficos, XObjects).
#   m{mesa}.json  el sello del archivo (tamaño + fecha), el orden de los talles (= el orden de
#                 las páginas del PDF) y los contornos de cada talle, tal como los devuelve
#                 `piezas_de_mesa`.
#
# 🔴 POR QUÉ. Medido en un pedido real de 5 prendas (27 piezas distintas): el motor tardaba 356 s
# y 328 eran RE-LEER EL ARCHIVO: 119 s aislando el talle de cada pieza (parsear 398 mil a 1,2
# millones de operadores por mesa, una vez por talle), 109 s de `get_drawings` de las 9 mesas y
# 100 s de `extraer_personalizacion` recorriendo todo el archivo. Todo eso depende SÓLO del
# archivo, no del pedido: se hace una vez, cuando se carga.
#
# El motor y el visor NO dependen de que exista: si falta o el sello no coincide (el archivo
# cambió), se arma esa mesa en el momento (`ruta_desplegada`) y sigue. Un molde viejo se vuelve
# rápido la primera vez que se usa. Se borra con el molde (vive en su carpeta de `entrada/`) y
# cuando se re-sube uno del camino A encima.
DESPLEGADO = "desplegado"
_CONT_CACHE = {}          # {(carpeta, mesa): índice ya leído}  — no releer el JSON en cada pieza
# Versión de la REGLA DE CONTORNOS. Un `m{mesa}.json` con otra versión tiene contornos viejos:
# se rehacen (5 s por mesa, en paralelo) y sus páginas por talle se conservan (no dependen de
# la regla). 2 = el recorte con el diseño adentro, no el mayor del grupo (2026-09-07).
_V_CONTORNOS = 3          # 3 = la línea de corte del archivo es el contorno (2026-09-07)
# Versión de la etapa de PÁGINAS. 3 = la línea de corte se saca del dibujo (`quitar_linea_de_corte`).
# 4 = también se saca la ETIQUETA DE CORTE que ya trae el diseño. 5 = se decide POR FAMILIA a nivel
# molde (`decidir_familias`), no por umbrales; el hash de la decisión (`etq`) también entra en la
# vigencia. 6 = se saca también el BORDE de la etiqueta (contornos de glifo trazados). Sin subir
# el número, un molde ya desplegado seguiría con su etiqueta vieja adentro.
_V_PAGINAS = 6
# Lo que se copia de la página original a la desplegada. Lista CERRADA a propósito: `/PieceInfo`
# (los datos privados de Illustrator), `/Metadata`, `/Annots` o `/Thumb` no dibujan nada y pesan.
_CLAVES_PAGINA = ("/MediaBox", "/CropBox", "/BleedBox", "/TrimBox", "/ArtBox", "/Rotate",
                  "/UserUnit", "/Group")


def _carpeta_desplegado(path_molde):
    return os.path.join(os.path.dirname(os.path.abspath(path_molde)), DESPLEGADO)


def _sello(path_molde):
    """Tamaño + fecha del archivo: si cambian, el desplegado es de OTRO archivo. `os.replace`
    conserva la fecha, así que el desplegado que el alta arma sobre el temporal sigue valiendo
    cuando el temporal pasa a ser el molde."""
    st = os.stat(path_molde)
    return [st.st_size, int(st.st_mtime)]


def _cont_de_json(c):
    """El contorno vuelve del JSON con listas; el sistema lo maneja con tuplas."""
    c = dict(c)
    c["segmentos"] = [tuple(s) for s in c["segmentos"]]
    c["bbox_raw"] = tuple(c["bbox_raw"])
    c["bbox_mu"] = tuple(c["bbox_mu"])
    return c


def _leer_desplegado(path_molde, mesa):
    """El índice de una mesa desplegada, o None si no está o es de otro archivo."""
    if not path_molde:
        return None
    try:
        sello = _sello(path_molde)
    except OSError:
        return None
    carpeta = _carpeta_desplegado(path_molde)
    clave = (carpeta, mesa)
    hit = _CONT_CACHE.get(clave)
    # 🔴 Una entrada SIN páginas no vale como caché: se guardó mientras el hilo de fondo las
    # armaba y, como el sello del archivo no cambia, el servidor seguía diciendo «preparando»
    # para siempre (2026-09-04: el chequeo de tipografía re-preguntaba cada 7 s sin fin).
    if hit is not None and hit["sello"] == sello and hit.get("pdf") is not None:
        return hit
    fj = os.path.join(carpeta, f"m{mesa}.json")
    fp = os.path.join(carpeta, f"m{mesa}.pdf")
    if not os.path.exists(fj):
        return None
    try:
        import json
        with open(fj, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    if d.get("sello") != sello or d.get("v") != _V_CONTORNOS:
        return None
    conts = {t: [_cont_de_json(c) for c in lst] for t, lst in (d.get("talles") or {}).items()}
    # el estilo de la línea de corte del archivo (ancho, color), leído en la etapa de páginas
    for t, por_idx in (d.get("linea_corte") or {}).items():
        for k, info in (por_idx or {}).items():
            try:
                conts[t][int(k)]["linea_corte"] = info
            except (KeyError, IndexError, ValueError, TypeError):
                pass
    # `pdf` sólo si las páginas por talle YA están (el JSON lo dice): el alta escribe primero los
    # contornos y las páginas llegan después, en segundo plano — ver `desplegar_mesa`.
    hit = {"sello": sello, "orden": list(d.get("orden") or []), "contornos": conts,
           "pdf": fp if (d.get("paginas") and os.path.exists(fp)) else None}
    _CONT_CACHE[clave] = hit
    return hit


def _traer(out, obj):
    """Copia un valor de la página original al PDF desplegado. Los objetos indirectos van con
    `copy_foreign` (que los copia una sola vez: las 20 páginas comparten la misma fuente); los
    directos se reconstruyen; los escalares van tal cual."""
    if isinstance(obj, (pikepdf.Dictionary, pikepdf.Array, pikepdf.Stream)):
        if obj.is_indirect:
            return out.copy_foreign(obj)
        if isinstance(obj, pikepdf.Dictionary):
            return pikepdf.Dictionary({str(k): _traer(out, v) for k, v in obj.items()})
        if isinstance(obj, pikepdf.Array):
            return pikepdf.Array([_traer(out, v) for v in obj])
    return obj


def _pagina_desplegada(out, pag, salida):
    """Agrega a `out` una página como `pag` pero con `salida` como contenido y SÓLO los recursos
    que ese contenido nombra. La mesa original arrastra 22 fuentes y los 20 OCG: aislado un
    talle quedan dos o tres nombres, y el resto sólo abultaría cada pieza de la tizada."""
    import re
    data = pikepdf.unparse_content_stream(salida)
    # Los nombres que el contenido usa, por regex sobre los bytes: mirar operando por operando
    # con pikepdf costaba 0,45 s por talle (9 s por mesa); esto, milisegundos. Sobra alguno que
    # aparezca dentro de un string: se conserva un recurso de más, nunca falta uno.
    usados = set()
    for tok in set(re.findall(rb"/([^\s/\[\]<>(){}%]+)", data)):
        tok = re.sub(rb"#([0-9A-Fa-f]{2})", lambda m: bytes([int(m.group(1), 16)]), tok)
        usados.add("/" + tok.decode("latin-1"))
    inline = re.search(rb"(?:^|\s)BI\s", data) is not None   # imagen inline: nombra su ColorSpace adentro
    src = pag.obj
    d = pikepdf.Dictionary(Type=pikepdf.Name.Page)
    for k in _CLAVES_PAGINA:
        if k in src:
            d[k] = _traer(out, src[k])
    res = pikepdf.Dictionary()
    for k, v in (src.get("/Resources") or pikepdf.Dictionary()).items():
        k = str(k)
        if k == "/ProcSet" or not isinstance(v, pikepdf.Dictionary):
            res[k] = _traer(out, v)
            continue
        sub = pikepdf.Dictionary()
        for nm, obj in v.items():
            if str(nm) in usados or (inline and k == "/ColorSpace"):
                sub[str(nm)] = _traer(out, obj)
        if len(sub):
            res[k] = sub
    d["/Resources"] = res
    d["/Contents"] = out.make_stream(data)
    out.pages.append(pikepdf.Page(d))
    return out.pages[-1]


# ─────────────────────────────────────────────────────────────────
# «00» Y «NOMBRE»: los placeholders del número y el nombre, POR TEXTO
# ─────────────────────────────────────────────────────────────────
# Regla del usuario (2026-09-04): el molde con diseño trae, dentro de cada talle, el texto «00»
# donde va el número y «NOMBRE» donde va el nombre; el sistema los detecta y pone el valor de la
# columna «numero» y el de la columna «nombre» de la planilla. Es por TEXTO, no por capa.
# Se hace acá, en la etapa de páginas del desplegado, porque ahí ya se está recorriendo el
# content-stream de cada talle: se decodifica cada `Tj`/`TJ`, y si dice «00» o «NOMBRE» se guarda
# dónde está, con qué tamaño, fuente y color NATIVO (CMYK exacto, con sus pasadas de apariencia)
# y se SACA del dibujo (si quedara, se imprimiría «NOMBRE» debajo del nombre estampado).
# ⚠️ PyMuPDF no sirve para leer el «00» de este archivo: viene con un `/Differences [31 /0]`
# (código 31 → glifo «0») y `get_text` lo descarta como carácter de control. Decodificar a mano
# con la codificación de la fuente es lo único que lo ve.
_PLACEHOLDERS = {"00": "numero", "NOMBRE": "nombre"}
_GLIFO_DIGITO = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                 "six": "6", "seven": "7", "eight": "8", "nine": "9", "space": " "}


def _decodificador(fuente):
    """Función bytes → texto para una fuente SIMPLE del PDF (WinAnsi/Standard + /Differences).
    Para Type0 se intenta el ToUnicode (bfchar/bfrange simples); si no se puede, None."""
    import re
    try:
        st = str(fuente.get("/Subtype", ""))
        if st == "/Type0":
            tu = fuente.get("/ToUnicode")
            if tu is None:
                return None
            data = tu.read_bytes().decode("latin-1", "replace")
            mapa = {}
            for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", data):
                if len(src) <= 4:
                    try:
                        mapa[int(src, 16)] = bytes.fromhex(dst).decode("utf-16-be", "replace")
                    except Exception:
                        pass
            for lo, hi, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", data):
                try:
                    a, b, d0 = int(lo, 16), int(hi, 16), int(dst, 16)
                    for k in range(a, min(b, a + 255) + 1):
                        mapa.setdefault(k, chr(d0 + (k - a)))
                except Exception:
                    pass
            def _dec0(b):
                return "".join(mapa.get(int.from_bytes(b[i:i + 2], "big"), "?") for i in range(0, len(b) - 1, 2))
            return _dec0
        dif = {}
        enc = fuente.get("/Encoding")
        if isinstance(enc, pikepdf.Dictionary) and "/Differences" in enc:
            code = 0
            for it in enc["/Differences"]:
                if isinstance(it, pikepdf.Name):
                    nm = str(it)[1:]
                    if nm in _GLIFO_DIGITO:
                        dif[code] = _GLIFO_DIGITO[nm]
                    elif len(nm) == 1:
                        dif[code] = nm
                    elif re.fullmatch(r"uni[0-9A-Fa-f]{4}", nm):
                        dif[code] = chr(int(nm[3:], 16))
                    else:
                        dif[code] = "?"
                    code += 1
                else:
                    code = int(it)
        def _dec(b):
            return "".join(dif.get(c, chr(c)) for c in b)
        return _dec
    except Exception:
        return None


def _texto_mostrado(op, operands, dec):
    """El texto de un operador de mostrar (`Tj`, `TJ`, `'`, `"`), decodificado."""
    try:
        if op in ("Tj", "'"):
            b = bytes(operands[-1])
        elif op == '"':
            b = bytes(operands[2])
        elif op == "TJ":
            b = b"".join(bytes(x) for x in operands[0] if isinstance(x, pikepdf.String))
        else:
            return ""
        return dec(b) if dec else b.decode("latin-1", "replace")
    except Exception:
        return ""


def _mul(a, b):
    """Producto de matrices PDF [a b c d e f] (a × b)."""
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
            a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]


def _ancho_texto(fuente, b, dec):
    """Ancho del texto en unidades de texto (1/1000 em), con los /Widths de la fuente simple."""
    try:
        fc = int(fuente.get("/FirstChar", 0))
        ws = fuente.get("/Widths")
        if ws is None:
            return None
        tot = 0.0
        for c in b:
            i = c - fc
            tot += float(ws[i]) if 0 <= i < len(ws) else 500.0
        return tot / 1000.0
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# LA ETIQUETA QUE YA TRAE EL DISEÑO — decidida POR FAMILIA, no por umbrales
# ─────────────────────────────────────────────────────────────────
# Un molde con el diseño adentro puede venir con la ETIQUETA DE CORTE ya puesta: un texto con el
# TALLE en cada pieza. Si se deja, la prenda sale con DOS (la del archivo y la del sistema).
#
# 🔴 LO QUE NO SIRVE: reconocerla por tamaño y posición («≤ 10 mm, pegada al borde»). Eso estaba
# calibrado con UN diseñador; otro la pone más grande, más adentro o con texto de más («TALLE M»),
# y la regla falla EN SILENCIO. El usuario lo dijo con todas las letras (2026-09-11): «no todos
# los diseñadores traen la etiqueta como debería; debe ser ajuste nuestro».
#
# LO QUE SÍ ES INDEPENDIENTE DEL DISEÑADOR: la etiqueta de corte **se repite igual en casi todas
# las piezas** del molde (la copian y pegan: misma fuente, mismo tamaño), mientras que un texto
# del diseño que también dice el talle —la TALLA TEJIDA de la piecita «TALLE», que dice «M» igual
# que la etiqueta— vive en UNA sola pieza. La firma es la CONSISTENCIA entre piezas.
#
# Entonces:
#   1. CANDIDATO = todo texto de la capa de un talle que nombre ESE talle como palabra entera
#      («M», «TALLE M», «M-FRENTE» sí; «2XL» no es «XL»; «00» no es «0»). Sin umbral de tamaño ni
#      de posición. Los placeholders «00»/«NOMBRE» van por su propio camino.
#   2. FAMILIA = (fuente, alto redondeado a 0,5 mm). Es lo que un copiar-pegar conserva.
#   3. DECISIÓN por molde: se oculta la familia que aparece en ≥ 2/3 de las piezas del molde
#      (y en al menos 2). El resto se deja y se INFORMA. El usuario puede dar vuelta cada familia
#      desde la pantalla (interruptor), y eso rehace las páginas.
# Vive en `etiqueta_archivo.json`, al lado del desplegado. Su hash entra en la vigencia de las
# páginas por talle: cambiar la decisión rehace SÓLO las páginas, no los contornos.
import re as _re

_ETQ_JSON = "etiqueta_archivo.json"
_V_ETQ = 1                  # versión de la REGLA de decisión (subir si cambia el criterio)
_ETQ_FRACCION = 2.0 / 3.0   # una familia es etiqueta de corte si está en ≥ 2/3 de las piezas
_ETQ_RADIO_MM = 40.0        # a qué pieza pertenece un texto: la más cercana, hasta 40 mm


def _tokens(txt):
    return [t for t in _re.split(r"[^0-9A-Za-zÁÉÍÓÚÑÜáéíóúñü]+", str(txt or "").upper()) if t]


def _norm_talle(s):
    return " ".join(str(s or "").strip().upper().replace("-", " ").split())


def menciona_talle(txt, talle):
    """¿El texto nombra ESE talle como palabra entera? «TALLE M» y «M-FRENTE» sí; «2XL» no es «XL»."""
    t = _norm_talle(talle)
    if not t:
        return False
    if _norm_talle(txt) == t:
        return True
    return t in _tokens(txt)


def familia_de(fuente, alto_mm):
    """La clave de familia: fuente (sin subset) + alto a 0,5 mm. Lo que conserva un copiar-pegar."""
    f = str(fuente or "?").lstrip("/").split("+")[-1]
    return f"{f}|{round(float(alto_mm) * 2) / 2:g}"


def pieza_de_texto(dx, dy, contornos):
    """`(idx_pieza, borde_mm)` de la pieza a la que pertenece un texto: la que lo contiene o, si
    quedó apenas afuera (la base del texto alineada con el ruedo), la más cercana hasta
    `_ETQ_RADIO_MM`. `borde_mm` = distancia al borde de esa pieza (informativo)."""
    CM10 = CM / 10.0
    mejor = None
    for i, c in enumerate(contornos or []):
        try:
            x0, y0, x1, y1 = c["bbox_mu"]
        except Exception:
            continue
        fx = max(x0 - dx, 0.0, dx - x1)
        fy = max(y0 - dy, 0.0, dy - y1)
        if fx or fy:
            d = (fx * fx + fy * fy) ** 0.5
        else:
            d = min(dx - x0, x1 - dx, dy - y0, y1 - dy)
        d /= CM10
        if (fx or fy) and d > _ETQ_RADIO_MM:
            continue
        if mejor is None or d < mejor[1]:
            mejor = (i, round(d, 2))
    return mejor


def decidir_familias(candidatos, total_piezas, manual=None):
    """La decisión por molde, PURA (se prueba sola).

    `candidatos` = [{mesa, talle, idx, fuente, alto_mm, texto, borde_mm}, …] de TODAS las mesas.
    `total_piezas` = cuántas piezas tiene el molde (mesa+índice). `manual` = {clave: bool} que
    el usuario fijó desde la pantalla (gana siempre). Devuelve la lista de familias, cada una con
    `ocultar` y su `motivo`, ordenadas de la más presente a la menos.
    """
    fams = {}
    for c in candidatos:
        k = familia_de(c.get("fuente"), c.get("alto_mm", 0))
        f = fams.setdefault(k, {"clave": k, "fuente": str(c.get("fuente") or "?").lstrip("/").split("+")[-1],
                                "alto_mm": round(float(c.get("alto_mm", 0)), 1), "piezas": set(),
                                "talles": set(), "ejemplo": c.get("texto", ""), "borde_mm": None})
        f["piezas"].add((c.get("mesa"), c.get("idx")))
        f["talles"].add(c.get("talle"))
        if c.get("borde_mm") is not None and (f["borde_mm"] is None or c["borde_mm"] < f["borde_mm"]):
            f["borde_mm"] = c["borde_mm"]
    # 🔴 UN TEXTO QUE ESCALA CON EL TALLE ES UN SOLO TEXTO. La talla tejida mide 10 mm en el talle 0
    # y 13,5 en el 6XL: por clave (fuente + alto) salían SIETE familias de una pieza cada una. Es
    # el mismo elemento en la misma pieza, así que se fusionan las familias de la misma fuente que
    # caen exactamente en las mismas piezas; el alto queda como rango. Una etiqueta de corte no
    # escala (5,3 mm en los 20 talles) y no la toca.
    por_huella = {}
    for f in list(fams.values()):
        h = (f["fuente"], tuple(sorted(f["piezas"])))
        g = por_huella.get(h)
        if g is None:
            por_huella[h] = f
            f["altos"] = {f["alto_mm"]}
            f["claves"] = [f["clave"]]
            continue
        del fams[f["clave"]]
        g["altos"].add(f["alto_mm"])
        g["claves"].append(f["clave"])       # la etapa de páginas oculta por clave: van TODAS
        g["talles"] |= f["talles"]
        if f["borde_mm"] is not None and (g["borde_mm"] is None or f["borde_mm"] < g["borde_mm"]):
            g["borde_mm"] = f["borde_mm"]
    for f in fams.values():
        altos = sorted(f.pop("altos", {f["alto_mm"]}))
        if len(altos) > 1:
            f["alto_mm"] = altos[0]
            f["alto_hasta_mm"] = altos[-1]
    salida = []
    for f in fams.values():
        n = len(f["piezas"])
        auto = n >= 2 and total_piezas > 0 and n >= _ETQ_FRACCION * total_piezas
        fijado = (manual or {}).get(f["clave"])
        ocultar = bool(fijado) if fijado is not None else auto
        if fijado is not None:
            motivo = "lo fijaste vos"
        elif auto:
            motivo = f"se repite en {n} de {total_piezas} piezas: es la etiqueta de corte"
        elif n == 1:
            motivo = "está en una sola pieza: parece parte del diseño (la talla tejida, por ejemplo)"
        else:
            motivo = f"está en {n} de {total_piezas} piezas, menos de dos tercios: se deja"
        salida.append({"clave": f["clave"], "claves": sorted(f.get("claves") or [f["clave"]]),
                       "piezas_lista": sorted([list(x) for x in f["piezas"]]),   # (mesa, idx): para apagar la etiqueta del sistema ahí
                       "fuente": f["fuente"], "alto_mm": f["alto_mm"],
                       **({"alto_hasta_mm": f["alto_hasta_mm"]} if f.get("alto_hasta_mm") else {}),
                       "piezas": n, "de": total_piezas, "talles": len(f["talles"]),
                       "ejemplo": f["ejemplo"], "borde_mm": f["borde_mm"],
                       "ocultar": ocultar, "automatico": auto, "motivo": motivo})
    salida.sort(key=lambda x: (-x["piezas"], x["clave"]))
    return salida


def piezas_con_talle_en_diseno(decision):
    """Las piezas `[mesa, idx]` donde quedó una familia de talle SIN ocultar: el talle es parte
    del diseño (la talla tejida de la solapa). Ahí la etiqueta de corte del sistema sobra —el
    usuario lo pidió (2026-09-11): «la solapa ya viene con una etiqueta diseñada para la visual».
    Sale de la decisión guardada; el servidor lo traduce a nombres y apaga la etiqueta ahí."""
    out = set()
    for f in ((decision or {}).get("familias") or []):
        if not f.get("ocultar"):
            out |= {tuple(x) for x in (f.get("piezas_lista") or [])}
    return sorted([list(x) for x in out])


def _ruta_etq(path_molde):
    return os.path.join(_carpeta_desplegado(path_molde), _ETQ_JSON)


def leer_decision(path_molde):
    """La decisión guardada, si es de ESTE archivo y de esta regla; si no, None."""
    import json
    try:
        with open(_ruta_etq(path_molde), encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    if d.get("sello") != _sello(path_molde) or d.get("v") != _V_ETQ:
        return None
    return d


def familias_ocultas(decision):
    """Las claves (fuente + alto) que hay que sacar del dibujo, según la decisión. Una familia
    fusionada (el mismo texto escalando con el talle) aporta TODAS sus claves."""
    out = set()
    for f in ((decision or {}).get("familias") or []):
        if f.get("ocultar"):
            out |= set(f.get("claves") or [f["clave"]])
    return sorted(out)


def hash_ocultas(claves):
    """El hash que entra en la vigencia de las páginas: cambia la decisión → se rehacen."""
    import hashlib
    return hashlib.sha1("|".join(sorted(claves or [])).encode("utf-8")).hexdigest()[:12]


def buscar_candidatos_mesa(path_molde, mesa, talles, orden=None):
    """Los candidatos a etiqueta de UNA mesa, en los talles pedidos (worker de proceso).

    Parsea la mesa una vez y filtra por talle como la etapa de páginas, pero SIN escribir nada:
    sólo lee los textos. Medido: 1-5 s por mesa, en paralelo con las demás.

    🔴 `orden` = los talles del MOLDE, para reconocer el índice del desplegado; `talles` = los que
    le tocan a este worker. Son distintos desde que el trabajo se reparte por talle (2026-09-14):
    pasarle el trozo a `_json_mismo_archivo` lo hacía fallar —el orden no coincidía—, devolvía
    cero candidatos y el molde entero quedaba SIN etiqueta detectada, en silencio."""
    import molde_real as MR
    fj = os.path.join(_carpeta_desplegado(path_molde), f"m{mesa}.json")
    idx = _json_mismo_archivo(fj, _sello(path_molde), list(orden if orden is not None else talles))
    if idx is None:
        return mesa, []                      # sin contornos no hay a qué pieza asignar: se saltea
    conts = {t: [_cont_de_json(c) for c in lst] for t, lst in (idx.get("talles") or {}).items()}
    marco, U = idx.get("marco"), idx.get("U")
    out = []
    pdf = pikepdf.open(path_molde)
    try:
        pag = pdf.pages[mesa - 1]
        ins = list(pikepdf.parse_content_stream(pag))
        ops, oc = MR._mapa_oc(ins, pag)
        bloques = MR._bloques_oc(ops, oc)
        for talle in talles:
            if not conts.get(talle):
                continue
            obj = {MR._norm_capa(talle)}
            fn = (lambda pila, _o=obj: not any(frame and (_o & frame) for frame in pila))
            saltar = MR._saltar_bloques(ops, oc, fn, bloques)
            salida = MR._raspar_instrucciones(ins, ops, oc, fn, True, saltar)
            cands = []
            quitar_placeholders(salida, pag, marco, U, talle, conts[talle], candidatos=cands)
            for c in cands:
                c["mesa"] = mesa
                out.append(c)
    finally:
        pdf.close()
    return mesa, out


def decidir_etiqueta_archivo(path_molde, talles, procesos=None, avisar=None):
    """Junta los candidatos de TODAS las mesas, decide por familia y escribe
    `etiqueta_archivo.json`. Conserva lo que el usuario fijó a mano (`manual`). Devuelve la
    decisión. Se llama antes de la etapa de páginas; si ya está y es vigente, no se recalcula."""
    import json
    previa = leer_decision(path_molde)
    if previa is not None:
        return previa
    manual = {}
    try:                                     # lo fijado a mano sobrevive a una decisión rehecha
        with open(_ruta_etq(path_molde), encoding="utf-8") as fh:
            manual = (json.load(fh).get("manual") or {})
    except Exception:
        pass
    d = fitz.open(path_molde)
    try:
        n = d.page_count
    finally:
        d.close()
    mesas = list(range(1, n + 1))
    cands = []
    # El trozo de trabajo es (mesa, unos talles). Con varias mesas, una mesa entera por proceso
    # —parsearla cuesta y así se parsea una sola vez—; con pocas mesas y muchos talles se parte
    # por TALLE, o un molde de una sola mesa no repartiría nada (2026-09-14, ver `_armar_paginas`).
    if procesos and procesos > 1 and n < procesos and len(talles) > 1:
        tareas = [(m, tr) for m in mesas for tr in _trozos_de_talles(talles, max(1, procesos // n))]
    else:
        tareas = [(m, list(talles)) for m in mesas]
    pendientes = list(range(len(tareas)))
    if procesos and procesos > 1 and len(tareas) > 1:
        try:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            with ProcessPoolExecutor(max_workers=min(len(tareas), procesos)) as ex:
                futs = {ex.submit(buscar_candidatos_mesa, path_molde, m, list(tr), list(talles)): i
                        for i, (m, tr) in enumerate(tareas)}
                for f in as_completed(futs):
                    i = futs[f]
                    _m, cs = f.result()
                    cands.extend(cs)
                    pendientes.remove(i)
                    if avisar:
                        avisar(len(tareas) - len(pendientes), len(tareas), f"etiquetas · mesa {_m}")
        except Exception as e:
            print(f"[camino B] la búsqueda de etiquetas en paralelo falló ({type(e).__name__}: {e}); sigo en serie")
    for i in pendientes:
        m, tr = tareas[i]
        _m, cs = buscar_candidatos_mesa(path_molde, m, list(tr), list(talles))
        cands.extend(cs)
    # cuántas piezas tiene el molde (mesa + índice), de los contornos ya desplegados
    total = set()
    sello = _sello(path_molde)
    for m in mesas:
        idx = _json_mismo_archivo(os.path.join(_carpeta_desplegado(path_molde), f"m{m}.json"), sello, list(talles))
        for lst in ((idx or {}).get("talles") or {}).values():
            for i in range(len(lst)):
                total.add((m, i))
    familias = decidir_familias(cands, len(total), manual)
    dec = {"sello": sello, "v": _V_ETQ, "piezas": len(total), "familias": familias,
           "manual": manual}
    escribir_decision(path_molde, dec)
    return dec


def escribir_decision(path_molde, dec):
    import json
    ruta = _ruta_etq(path_molde)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(dec, fh, ensure_ascii=False, indent=1)
    _reemplazar(ruta + ".tmp", ruta)


def fijar_familia(path_molde, clave, ocultar):
    """El interruptor de la pantalla: fija una familia a mano y re-decide. Devuelve la decisión
    nueva; las páginas se rehacen por el hash (ver `desplegar_mesa`)."""
    dec = leer_decision(path_molde)
    if dec is None:
        return None
    manual = dict(dec.get("manual") or {})
    if ocultar is None:
        manual.pop(clave, None)
    else:
        manual[clave] = bool(ocultar)
    # re-decidir con los mismos conteos: cada familia guarda sus números
    for f in dec.get("familias") or []:
        fijado = manual.get(f["clave"])
        f["ocultar"] = bool(fijado) if fijado is not None else bool(f.get("automatico"))
        f["motivo"] = ("lo fijaste vos" if fijado is not None else
                       (f"se repite en {f['piezas']} de {f['de']} piezas: es la etiqueta de corte" if f.get("automatico")
                        else ("está en una sola pieza: parece parte del diseño (la talla tejida, por ejemplo)" if f["piezas"] == 1
                              else f"está en {f['piezas']} de {f['de']} piezas, menos de dos tercios: se deja")))
    dec["manual"] = manual
    escribir_decision(path_molde, dec)
    return dec


def quitar_placeholders(salida, page, marco, U, talle=None, contornos=None, ocultar=None, candidatos=None):
    """Saca de `salida` (instrucciones de UN talle) los textos «00»/«NOMBRE» y —si el diseño la
    trae— la ETIQUETA DE CORTE del talle. Devuelve
    `(salida_sin_ellos, {campo: placeholder}, {idx_pieza: etiqueta})`.

    `talle` y `contornos` son los de ESTE talle. Dos modos para la etiqueta que trae el diseño:
      · `candidatos=[]` → MODO BÚSQUEDA: no saca ningún texto del talle; agrega a esa lista cada
        texto que nombre el talle (con fuente, alto, pieza, distancia al borde). Es lo que usa
        `decidir_etiqueta_archivo` para armar las familias de TODO el molde.
      · `ocultar={claves}` → MODO PÁGINAS: saca los textos que nombren el talle y sean de una de
        esas familias (las que la decisión marcó). Sin `ocultar`, no se saca ninguna.

    El placeholder tiene la forma que espera `motor_pedido.generar_pieza` (la misma de
    `extraer_personalizacion`): `cx`/`baseline_y` en coordenadas de dispositivo de la mesa (las
    de `bbox_mu`, y hacia abajo, escaladas por `U`), `size` en puntos, `fuente` (nombre PostScript
    sin el prefijo de subset), `pasadas` (relleno/trazo nativos, en orden) y `colorn`.
    `marco` = [x0, y0, x1, y1] del CropBox (unidades crudas), `U` = escala de dispositivo."""
    fuentes = {}
    try:
        for k, v in (page.obj.get("/Resources") or {}).get("/Font", {}).items():
            fuentes[str(k)] = v
    except Exception:
        pass
    _cs = {}
    try:
        for k, v in (page.obj.get("/Resources") or {}).get("/ColorSpace", {}).items():
            _cs[str(k)] = v
    except Exception:
        pass

    def _n_de_cs(name):
        o = _cs.get(name)
        try:
            if o is None:
                return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(name)
            if isinstance(o, pikepdf.Array):
                base = str(o[0])
                if base == "/ICCBased" and len(o) > 1:
                    return int(o[1].get("/N", 0)) or None
                return {"/CalRGB": 3, "/CalGray": 1, "/Separation": 1, "/DeviceN": None}.get(base)
            return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(str(o))
        except Exception:
            return None
    _op_n = {4: "k", 3: "rg", 1: "g"}

    x0c, y0c, x1c, y1c = marco
    def _dev(x, y):                       # crudas (y arriba) → dispositivo (y abajo), como `_contorno_de_drawing.pt` al revés
        return ((x - x0c) * U, (y1c - y) * U)

    ctm = [1, 0, 0, 1, 0, 0]
    pila = []
    fcol = scol = None
    fcs_n = scs_n = None
    sw = 1.0
    tr = 0
    tf, tfs = None, 1.0
    tm = tlm = None
    tl, tc, tw, th = 0.0, 0.0, 0.0, 1.0
    encontrados = {}                      # campo → placeholder
    etiquetas = {}                        # idx_pieza → la etiqueta de corte que traía el archivo
    quitar = set()
    cajas_sacadas = []                    # (idx_pieza|None, x, baseline, ancho, alto) de cada texto sacado
    for i, inst in enumerate(salida):
        op = str(inst.operator)
        ops = inst.operands
        try:
            if op == "q":
                pila.append((ctm, fcol, fcs_n, scol, scs_n, sw, tr, tf, tfs))
            elif op == "Q":
                if pila:
                    ctm, fcol, fcs_n, scol, scs_n, sw, tr, tf, tfs = pila.pop()
            elif op == "cm":
                ctm = _mul([float(v) for v in ops], ctm)
            elif op == "cs":
                fcs_n = _n_de_cs(str(ops[0]))
            elif op == "CS":
                scs_n = _n_de_cs(str(ops[0]))
            elif op in ("k", "rg", "g"):
                fcol = (op, [round(float(v), 4) for v in ops])
            elif op in ("K", "RG", "G"):
                scol = (op.lower(), [round(float(v), 4) for v in ops])
            elif op in ("sc", "scn"):
                nums = [round(float(v), 4) for v in ops if not isinstance(v, pikepdf.Name)]
                o2 = _op_n.get(fcs_n) or _op_n.get(len(nums))
                if o2:
                    fcol = (o2, nums)
            elif op in ("SC", "SCN"):
                nums = [round(float(v), 4) for v in ops if not isinstance(v, pikepdf.Name)]
                o2 = _op_n.get(scs_n) or _op_n.get(len(nums))
                if o2:
                    scol = (o2, nums)
            elif op == "w":
                sw = float(ops[0])
            elif op == "Tr":
                tr = int(ops[0])
            elif op == "BT":
                tm = tlm = [1, 0, 0, 1, 0, 0]
            elif op == "ET":
                tm = tlm = None
            elif op == "Tf":
                tf, tfs = str(ops[0]), float(ops[1])
            elif op == "Tm":
                tm = tlm = [float(v) for v in ops]
            elif op in ("Td", "TD"):
                tlm = _mul([1, 0, 0, 1, float(ops[0]), float(ops[1])], tlm or [1, 0, 0, 1, 0, 0])
                tm = list(tlm)
                if op == "TD":
                    tl = -float(ops[1])
            elif op == "TL":
                tl = float(ops[0])
            elif op == "Tc":
                tc = float(ops[0])
            elif op == "Tw":
                tw = float(ops[0])
            elif op == "Tz":
                th = float(ops[0]) / 100.0
            elif op in ("T*", "'", '"') or op in ("Tj", "TJ"):
                if op in ("T*", "'", '"'):
                    if op == '"':
                        tw, tc = float(ops[0]), float(ops[1])
                    tlm = _mul([1, 0, 0, 1, 0, -tl], tlm or [1, 0, 0, 1, 0, 0])
                    tm = list(tlm)
                if op == "T*":
                    continue
                f = fuentes.get(tf)
                dec = _decodificador(f) if f is not None else None
                txt = _texto_mostrado(op, ops, dec)
                campo = _PLACEHOLDERS.get(txt.strip().upper().replace(" ", ""))
                if tm is None:
                    continue
                # posición y tamaño en el espacio de usuario → dispositivo
                m = _mul(_mul([tfs, 0, 0, tfs, 0, 0], tm), ctm)
                esc = (m[0] ** 2 + m[1] ** 2) ** 0.5           # tamaño del texto en puntos (crudos)
                ox, oy = m[4], m[5]
                if op in ("Tj", "'"):
                    b = bytes(ops[-1])
                elif op == '"':
                    b = bytes(ops[2])
                else:
                    b = b"".join(bytes(x) for x in ops[0] if isinstance(x, pikepdf.String))
                an = _ancho_texto(f, b, dec) if f is not None else None
                if an is None:
                    an = 0.6 * len(txt.strip())
                ancho = an * esc * th                          # en puntos crudos, como `esc`
                if campo is None:
                    # ¿nombra el talle? Entonces es candidato a ETIQUETA DE CORTE del diseño. Se
                    # mide con la MISMA posición que los placeholders (una sola matemática) y se
                    # decide POR FAMILIA a nivel molde (ver arriba): acá sólo se junta o se aplica.
                    if talle and (candidatos is not None or ocultar) and menciona_talle(txt, talle):
                        _dx, _dy = _dev(ox, oy)
                        _alto = esc * U / (CM / 10.0)
                        _fn = str(f.get("/BaseFont", "")).lstrip("/").split("+")[-1] if f is not None else "?"
                        _pz = pieza_de_texto(_dx, _dy, contornos)
                        if _pz is not None:
                            _ip, _borde = _pz
                            if candidatos is not None:
                                candidatos.append({"talle": talle, "idx": _ip, "texto": txt.strip(),
                                                   "fuente": _fn, "alto_mm": round(_alto, 2),
                                                   "borde_mm": _borde, "x": round(_dx, 2), "y": round(_dy, 2)})
                            elif familia_de(_fn, _alto) in ocultar:
                                etiquetas.setdefault(_ip, {"texto": txt.strip(), "x": round(_dx, 2),
                                                           "y": round(_dy, 2), "alto_mm": round(_alto, 2),
                                                           "borde_mm": _borde, "familia": familia_de(_fn, _alto),
                                                           "copias": 0})
                                etiquetas[_ip]["copias"] += 1
                                quitar.add(i)
                                cajas_sacadas.append((_ip, _dx, _dy, ancho * U, esc * U))
                    continue
                dx, dy = _dev(ox, oy)
                ph = encontrados.get(campo)
                if ph is None:
                    ph = {"cx": round(dx + ancho * U / 2.0, 2), "baseline_y": round(dy, 2),
                          "size": round(esc * U, 3), "fuente": str(f.get("/BaseFont", "")).lstrip("/").split("+")[-1] if f is not None else "",
                          "ancho": round(ancho * U, 2), "color": 0, "colorn": None, "trazo": None,
                          "pasadas": [], "baseline_pts": [], "texto": txt.strip()}
                    encontrados[campo] = ph
                # pasadas de apariencia, en orden: relleno y/o trazo según el modo de texto
                def _add(p):
                    if not ph["pasadas"] or ph["pasadas"][-1] != p:
                        ph["pasadas"].append(p)
                if tr in (0, 2, 4, 6) and fcol:
                    _add({"t": "f", "color": [fcol[0], list(fcol[1])]})
                    if ph["colorn"] is None:
                        ph["colorn"] = [fcol[0], list(fcol[1])]
                if tr in (1, 2, 5, 6) and scol:
                    _w = sw * ((ctm[0] ** 2 + ctm[1] ** 2) ** 0.5) * U     # ancho real del trazo, en dispositivo
                    _add({"t": "S", "color": [scol[0], list(scol[1])], "w": round(_w, 4)})
                    if ph["trazo"] is None:
                        ph["trazo"] = [scol[0], list(scol[1]), round(_w, 4)]
                quitar.add(i)
                cajas_sacadas.append((None, dx, dy, ancho * U, esc * U))
        except Exception:
            continue
    if not quitar:
        return salida, {}, {}
    # 🔴 EL BORDE TAMBIÉN SE VA. Illustrator exporta la apariencia «borde detrás» de un texto como
    # los CONTORNOS DEL GLIFO trazados (`q cm m/l… h S Q`), no como texto: sacando sólo el `Tj`
    # quedaba el borde blanco de la etiqueta flotando (reporte del usuario 2026-09-11: «me ocultó
    # la etiqueta pero me dejó su contorno»). Se reconocen por GEOMETRÍA —un bloque solo-trazo
    # cuya caja cae dentro de la caja del texto sacado—, que vale para cualquier fuente.
    for i_q, i_Q, ip in _bloques_de_contorno(salida, cajas_sacadas, marco, U):
        quitar.update(range(i_q, i_Q + 1))
        if ip is not None and ip in etiquetas:
            etiquetas[ip]["contornos"] = etiquetas[ip].get("contornos", 0) + 1
    return [inst for i, inst in enumerate(salida) if i not in quitar], encontrados, etiquetas


_OPS_TRAZADO = {"m", "l", "c", "v", "y", "re", "h"}
_OPS_ESTADO = {"w", "M", "J", "j", "d", "CS", "SCN", "SC", "K", "RG", "G", "gs", "ri", "i"}


def _bloques_de_contorno(salida, cajas, marco, U):
    """Los bloques `q … Q` que son SÓLO un trazado pintado con `S`/`s` (contornos de glifo) y caen
    dentro de la caja de un texto sacado. Devuelve `[(i_q, i_Q, idx_pieza)]`.

    La caja del texto es (x, baseline, ancho, alto) en dispositivo; se toma desde 0,3 alturas
    debajo de la línea base hasta 1,1 arriba (descendentes y ascendentes), con 2 mm de margen. El
    bloque tiene que caer ENTERO adentro: un dibujo del diseño que pase por ahí sobresale y no se
    toca."""
    if not cajas:
        return []
    x0c, y0c, x1c, y1c = marco
    mm2 = 2.0 * (CM / 10.0) * U

    def _dev(x, y):
        return ((x - x0c) * U, (y1c - y) * U)

    # Cada caja ya resuelta a (x0, x1, y0, y1, idx_pieza): se consultan una vez por punto.
    _cajas = [(dx - mm2, dx + ancho + mm2, dy - 1.1 * alto - mm2, dy + 0.3 * alto + mm2, ip)
              for ip, dx, dy, ancho, alto in cajas]

    def _adentro(bx0, by0, bx1, by1):
        for X0, X1, Y0, Y1, ip in _cajas:
            if bx0 >= X0 and bx1 <= X1 and by0 >= Y0 and by1 <= Y1:
                return ip
        return "sin"

    # 🔴 EL DESCARTE TEMPRANO. Un bloque que pisa un punto que no cae en NINGUNA caja no puede
    # estar entero adentro de una, así que se abandona ahí mismo, sin terminar de recorrerlo. Las
    # etiquetas ocupan milímetros en una mesa de metros: casi todos los bloques del diseño mueren
    # en su primer punto y cuestan unas comparaciones en vez de cientos de instrucciones.
    # ⚠️ Contra CADA caja, nunca contra la que las envuelve a todas: con las etiquetas repartidas
    # por la mesa esa envolvente ES la mesa entera y no descarta nada (medido 2026-09-14).
    def _toca(px, py):
        for X0, X1, Y0, Y1, _ip in _cajas:
            if X0 <= px <= X1 and Y0 <= py <= Y1:
                return True
        return False

    ctm, pila = [1, 0, 0, 1, 0, 0], []
    hallados = []
    i = 0
    n = len(salida)
    while i < n:
        op = str(salida[i].operator)
        ops = salida[i].operands
        if op == "cm":
            try:
                ctm = _mul([float(v) for v in ops], ctm)
            except Exception:
                pass
        elif op == "Q":
            if pila:
                ctm = pila.pop()
        elif op == "q":
            pila.append(list(ctm))
            # ¿es un bloque solo-trazo? se mira hasta su Q (sin anidar)
            j, prof, pts, pintado, otro, ctm_b = i + 1, 1, [], None, False, list(ctm)
            while j < n and prof:
                o2, a2 = str(salida[j].operator), salida[j].operands
                if o2 == "q":
                    prof += 1; otro = True
                elif o2 == "Q":
                    prof -= 1
                    if prof == 0:
                        break
                elif o2 == "cm":
                    try:
                        ctm_b = _mul([float(v) for v in a2], ctm_b)
                    except Exception:
                        otro = True
                elif o2 in _OPS_TRAZADO:
                    try:
                        nums = [float(v) for v in a2]
                        if o2 == "re":
                            x, y, w, h = nums
                            cand = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                        else:
                            cand = [(nums[k], nums[k + 1]) for k in range(0, len(nums) - 1, 2)]
                        for x, y in cand:
                            X = ctm_b[0] * x + ctm_b[2] * y + ctm_b[4]
                            Y = ctm_b[1] * x + ctm_b[3] * y + ctm_b[5]
                            _p = _dev(X, Y)
                            if not _toca(_p[0], _p[1]):
                                otro = True          # pisa fuera de toda etiqueta: no es un borde
                                break
                            pts.append(_p)
                    except Exception:
                        otro = True
                elif o2 in ("S", "s"):
                    pintado = "S" if pintado is None else "varios"
                elif o2 in ("f", "F", "f*", "B", "B*", "b", "b*", "n", "W", "W*"):
                    otro = True                      # relleno o recorte: no es un borde de glifo
                elif o2 in _OPS_ESTADO:
                    pass
                else:
                    otro = True                      # texto, imágenes, XObjects…: no es esto
                if otro:
                    # 🔴 YA NO PUEDE SER: no hace falta recorrer el resto del bloque. El `i += 1`
                    # de afuera sigue instrucción por instrucción como siempre, así que el `ctm`
                    # se mantiene bien y los bloques ANIDADOS se miran igual (cada `q` abre su
                    # propio intento). Cortar acá no cambia qué se encuentra, sólo cuánto cuesta.
                    break
                j += 1
            if prof == 0 and pintado == "S" and not otro and pts:
                bx0 = min(p[0] for p in pts); bx1 = max(p[0] for p in pts)
                by0 = min(p[1] for p in pts); by1 = max(p[1] for p in pts)
                ip = _adentro(bx0, by0, bx1, by1)
                if ip != "sin":
                    hallados.append((i, j, ip))
                    ctm = pila.pop()             # el Q del bloque cierra este q
                    i = j + 1
                    continue
        i += 1
    return hallados


def quitar_linea_de_corte(salida, page, contornos, marco, U):
    """Saca de `salida` (instrucciones de UN talle) el TRAZO de la línea de corte de cada pieza que
    la trae (`cont["linea_corte"]`) y devuelve `(salida_sin_el, {idx_pieza: {"w", "color"}})`.

    La línea se reconoce por geometría: un trazado que se PINTA sólo con trazo (`S`/`s`) y cuya
    caja, siguiendo la CTM, coincide con `bbox_raw` del contorno (la línea ES el contorno: el
    recorte del grupo de trazos es su propio trazado). El operador de pintura se cambia por `n`
    (fin de trazado sin pintar): la construcción queda, no dibuja nada. El ancho (`w`, en unidades
    crudas, con la escala de la CTM) y el color de trazo se guardan tal cual vienen: el borde
    apagado en la configuración los reproduce; el borde prendido los reemplaza."""
    objetivos = [(i, tuple(float(v) for v in c["bbox_raw"])) for i, c in enumerate(contornos)
                 if c.get("linea_corte")]
    if not objetivos:
        return salida, {}
    _cs = {}
    try:
        for k, v in (page.obj.get("/Resources") or {}).get("/ColorSpace", {}).items():
            _cs[str(k)] = v
    except Exception:
        pass

    def _n_de_cs(name):
        o = _cs.get(name)
        try:
            if o is None:
                return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(name)
            if isinstance(o, pikepdf.Array):
                base = str(o[0])
                if base == "/ICCBased" and len(o) > 1:
                    return int(o[1].get("/N", 0)) or None
                return {"/CalRGB": 3, "/CalGray": 1, "/Separation": 1}.get(base)
            return {"/DeviceCMYK": 4, "/DeviceRGB": 3, "/DeviceGray": 1}.get(str(o))
        except Exception:
            return None
    _op_n = {4: "k", 3: "rg", 1: "g"}

    ctm = [1, 0, 0, 1, 0, 0]
    pila = []
    scol, scs_n, sw = None, None, 1.0
    pts = []                                     # puntos del trazado en curso, en crudas de la página
    encontrados, reemplazar, candidatos = {}, {}, []
    tol = 1.5

    def _p(x, y):
        return (ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5])

    for i, inst in enumerate(salida):
        op = str(inst.operator)
        o = inst.operands
        try:
            if op == "q":
                pila.append((ctm, scol, scs_n, sw))
            elif op == "Q":
                if pila:
                    ctm, scol, scs_n, sw = pila.pop()
            elif op == "cm":
                ctm = _mul([float(v) for v in o], ctm)
            elif op == "CS":
                scs_n = _n_de_cs(str(o[0]))
            elif op in ("K", "RG", "G"):
                scol = (op.lower(), [round(float(v), 4) for v in o])
            elif op in ("SC", "SCN"):
                nums = [round(float(v), 4) for v in o if not isinstance(v, pikepdf.Name)]
                o2 = _op_n.get(scs_n) or _op_n.get(len(nums))
                if o2:
                    scol = (o2, nums)
            elif op == "w":
                sw = float(o[0])
            elif op == "re":
                x, y, w, h = (float(v) for v in o)
                pts += [_p(x, y), _p(x + w, y), _p(x + w, y + h), _p(x, y + h)]
            elif op in ("m", "l"):
                pts.append(_p(float(o[0]), float(o[1])))
            elif op == "c":
                pts += [_p(float(o[0]), float(o[1])), _p(float(o[2]), float(o[3])), _p(float(o[4]), float(o[5]))]
            elif op in ("v", "y"):
                pts += [_p(float(o[0]), float(o[1])), _p(float(o[2]), float(o[3]))]
            elif op in ("S", "s", "n", "f", "F", "f*", "B", "B*", "b", "b*"):
                if op in ("S", "s") and pts:
                    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                    caja = (min(xs), min(ys), max(xs), max(ys))
                    esc = (ctm[0] ** 2 + ctm[1] ** 2) ** 0.5
                    candidatos.append((i, caja, round(sw * esc, 4),
                                       [scol[0], list(scol[1])] if scol else ["k", [0, 0, 0, 1]]))
                pts = []
        except Exception:
            continue
    # El trazado de la línea puede pasarse del recorte (el recorte lo corta contra el marco de
    # la mesa: medido, hasta 37 pt en un costadillo que sale por arriba). Vale el trazo que
    # CONTIENE la caja del contorno sin pasarse más de `exceso` por lado; entre varios (el marco
    # de la mesa también la contiene), el más ajustado.
    exceso = 60.0
    for idx, bb in objetivos:
        mejor = None
        for i, caja, w, color in candidatos:
            if i in reemplazar:
                continue
            if (caja[0] <= bb[0] + tol and caja[1] <= bb[1] + tol and caja[2] >= bb[2] - tol and caja[3] >= bb[3] - tol):
                ex = (bb[0] - caja[0]) + (bb[1] - caja[1]) + (caja[2] - bb[2]) + (caja[3] - bb[3])
                if ex <= 4 * exceso and (mejor is None or ex < mejor[0]):
                    mejor = (ex, i, w, color)
        if mejor is not None:
            _, i, w, color = mejor
            encontrados[idx] = {"w": w, "color": color}
            reemplazar[i] = pikepdf.ContentStreamInstruction([], pikepdf.Operator("n"))
    if not reemplazar:
        return salida, {}
    return [reemplazar.get(i, inst) for i, inst in enumerate(salida)], encontrados


def desplegar_mesa(path_molde, mesa, talles, carpeta=None, contornos=True, paginas=True,
                   procesos=None, avisar=None):
    """Despliega UNA mesa y devuelve `{talle: [contornos]}` (sólo los talles con piezas). Es lo que
    corre en cada proceso del alta.

    Son DOS etapas, y por eso los dos flags:
      · `contornos` — `get_drawings` de la mesa (2-10 s) → `m{mesa}.json`. Es lo que necesitan
        el registro y el visor: sin esto la subida no puede responder.
      · `paginas`   — parsear el content-stream y filtrar los 20 talles (1-20 s) → `m{mesa}.pdf`.
        Lo usa SÓLO el motor, en la tizada, y hasta ahí el usuario tiene minutos (nombrar las
        piezas, ubicar la etiqueta). Medido: 107 s en serie contra 54 de los contornos, y la mesa
        más pesada 20 s contra 10 — con las dos etapas en la subida, el usuario esperaba el
        doble. El servidor pide los contornos al subir y las páginas en segundo plano, después
        de responder; si la tizada llega antes, `ruta_desplegada` arma esa mesa en el momento.
    El JSON lleva `paginas: true` sólo cuando el PDF ya está: con contornos nuevos y un PDF viejo
    del archivo anterior, el motor no lo puede tomar por bueno."""
    import json
    carpeta = carpeta or _carpeta_desplegado(path_molde)
    os.makedirs(carpeta, exist_ok=True)
    sello = _sello(path_molde)
    fj = os.path.join(carpeta, f"m{mesa}.json")
    fp = os.path.join(carpeta, f"m{mesa}.pdf")

    def _escribir_json(d):
        with open(fj + ".tmp", "w", encoding="utf-8") as fh:
            json.dump(d, fh)
        _reemplazar(fj + ".tmp", fj)
        _CONT_CACHE.pop((carpeta, mesa), None)

    conts = None
    if contornos:
        # (2026-09-07) Si el desplegado de ESTE archivo ya tiene los contornos (mismo sello,
        # mismo orden de talles), no se relee el dibujo: el alta repetida sobre el mismo archivo
        # (la caché por hash del servidor, `medir_tizada_b`, un re-alta) costaba 16 s por nada.
        _prev = _json_vigente(fj, sello, talles)
        if _prev is not None:
            conts = {t: [_cont_de_json(c) for c in lst] for t, lst in (_prev.get("talles") or {}).items()}
            marco, U = _prev.get("marco"), _prev.get("U")
            if not paginas or (_prev.get("paginas") and os.path.exists(fp)):
                return conts
            contornos = False              # los contornos están: siguen sólo las páginas
    # Un índice de ESTE archivo pero con contornos de otra versión: las páginas por talle siguen
    # valiendo (no dependen de la regla de contornos) y se conservan al reescribir el JSON.
    _viejo = _json_mismo_archivo(fj, sello, talles) if contornos else None
    if _viejo is not None and not (_viejo.get("paginas") and os.path.exists(fp)
                                   and _viejo.get("vp") == _V_PAGINAS):
        _viejo = None
    if contornos:
        # 1) los contornos, como siempre (get_drawings de la mesa, una vez para los 20 talles)
        doc = fitz.open(path_molde)
        try:
            conts = {}
            for talle in talles:
                pzs = _piezas_de_mesa_cruda(doc, mesa, talle)
                if pzs:
                    conts[talle] = pzs
            # el marco de la mesa (CropBox) y la escala de dispositivo: lo necesitan los
            # placeholders «00»/«NOMBRE» para expresar su posición como la de `bbox_mu`
            _pg = doc[mesa - 1]
            _cb = _pg.cropbox
            marco = [_cb.x0, _cb.y0, _cb.x1, _cb.y1]
            U = _pg.rect.width / _cb.width if _cb.width else 1.0
        finally:
            olvidar(doc)
            doc.close()
        _escribir_json({"sello": sello, "orden": list(talles), "talles": conts, "v": _V_CONTORNOS,
                        "paginas": bool(_viejo), "marco": marco, "U": U,
                        **({"placeholders": _viejo.get("placeholders") or {}, "vp": _V_PAGINAS,
                            "linea_corte": _viejo.get("linea_corte") or {},
                            "etiqueta_archivo": _viejo.get("etiqueta_archivo") or {},
                            "etq": _viejo.get("etq")} if _viejo else {})})
        if not paginas or _viejo:
            return conts
    elif conts is None:
        # sólo las páginas: los contornos ya están (o no hacen falta acá)
        _prev = _json_vigente(fj, sello, talles)
        if _prev is None:
            return desplegar_mesa(path_molde, mesa, talles, carpeta, contornos=True, paginas=True)
        conts = _prev.get("talles") or {}
        marco, U = _prev.get("marco"), _prev.get("U")
        _etq_dec = leer_decision(path_molde)
        _etq_hash = hash_ocultas(familias_ocultas(_etq_dec))
        if (_prev.get("paginas") and _prev.get("vp") == _V_PAGINAS and os.path.exists(fp)
                and _prev.get("etq") == _etq_hash):
            # las páginas de ESTE archivo ya están (y con la regla actual): no se rehacen. Sin
            # esto, un segundo `desplegar_molde(paginas=True)` sobre un molde listo (el hilo de
            # fondo que arrancó un endpoint mientras corría el de la subida) las reescribía
            # enteras: 44 s de CPU por nada, con la pantalla de nombrar esperando (2026-09-07).
            return {t: [_cont_de_json(c) for c in lst] for t, lst in conts.items()}

    # 2) la página de cada talle. Se parsea la mesa UNA vez y se filtra veinte; el filtrado es,
    #    instrucción por instrucción, el mismo de `aislar_capa(..., podar=True)`.
    # la decisión sobre la etiqueta del diseño (por familia, a nivel molde) — puede no existir
    # todavía (contornos recién hechos): entonces no se oculta nada, y `desplegar_molde` la arma
    # antes de pedir las páginas
    _etq_dec = leer_decision(path_molde)
    _ocultar = set(familias_ocultas(_etq_dec))
    _etq_hash = hash_ocultas(_ocultar)
    placeholders, lineas, etq_archivo = _armar_paginas(path_molde, mesa, talles, conts, marco, U,
                                                       _ocultar, fp + ".tmp", procesos, avisar)
    _reemplazar(fp + ".tmp", fp)

    _escribir_json({"sello": sello, "orden": list(talles), "talles": conts, "paginas": True,
                    "v": _V_CONTORNOS, "vp": _V_PAGINAS, "marco": marco, "U": U,
                    "placeholders": placeholders, "linea_corte": lineas,
                    "etiqueta_archivo": etq_archivo, "etq": _etq_hash})
    return conts


def _reemplazar(origen, destino, intentos=40):
    """`os.replace` con reintento. En Windows falla con «Acceso denegado» si OTRO proceso tiene
    el destino abierto en ese instante (el servidor leyendo `m{mesa}.json` mientras un worker lo
    reescribe): visto 2026-09-07 — el pool «fallaba» por eso y las 9 mesas seguían EN SERIE, tres
    veces más lento, sin que nadie se enterara.
    🔴 Y el que lee puede tardar lo que dura un RENDER, no unas décimas (2026-09-11): el motor
    tiene abierta `m3.pdf` mientras arma las piezas (15 s) y la ficha; con 8 intentos (7 s) el
    worker se rendía, el pool se abandonaba y las mesas restantes se armaban en serie DENTRO del
    servidor, 3 minutos con el GIL tomado — justo cuando el paso Tizada pedía las previas.
    Ahora espera hasta ~40 s (0,25 s → 1 s por intento)."""
    import time
    for i in range(intentos):
        try:
            os.replace(origen, destino)
            return
        except PermissionError:
            if i == intentos - 1:
                raise
            time.sleep(min(1.0, 0.25 * (i + 1)))


def _json_mismo_archivo(fj, sello, talles):
    """El índice `m{mesa}.json` si es de ESTE archivo (sello) y de este orden de talles, SEA CUAL
    SEA su versión de contornos; si no, None."""
    import json
    try:
        with open(fj, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    if d.get("sello") != sello or not d.get("marco"):
        return None
    if list(d.get("orden") or []) != list(talles):
        return None
    return d


def _json_vigente(fj, sello, talles):
    """Como `_json_mismo_archivo`, pero además con la regla de contornos ACTUAL (`_V_CONTORNOS`).
    Un JSON viejo, de otro archivo, con otro orden u otra versión no vale."""
    d = _json_mismo_archivo(fj, sello, talles)
    if d is None or d.get("v") != _V_CONTORNOS:
        return None
    return d


def _desplegar_mesa_worker(args):
    """Worker de proceso (spawn-safe: recibe y devuelve tipos simples)."""
    path, mesa, talles, contornos, paginas = args
    return mesa, desplegar_mesa(path, mesa, list(talles), contornos=contornos, paginas=paginas)


_TALLES_POR_PROCESO = 3        # menos que esto no paga el parseo de la mesa (ver `_trozos_de_talles`)


def _trozos_de_talles(talles, procesos):
    """En cuántos trozos conviene partir los talles de UNA mesa.

    🔴 CADA PROCESO VUELVE A PARSEAR LA MESA. En el molde de una sola mesa eso son 5 s antes de
    empezar, así que darle menos de `_TALLES_POR_PROCESO` talles a un proceso es regalar tiempo.
    Medido 2026-09-14 con 20 talles: 4 procesos 62 s · 6 procesos 61 s · 11 procesos **73 s** (la
    máquina tiene 6 núcleos y cada worker se queda con la mesa parseada en memoria). Con el tope,
    20 talles piden 6 trozos aunque el servidor ofrezca 11 procesos."""
    tope = max(1, len(talles) // _TALLES_POR_PROCESO)
    return _trozos(talles, min(int(procesos or 1), tope))


def _trozos(lista, k):
    """`lista` partida en a lo sumo `k` trozos parejos, SIN cambiar el orden."""
    lista = list(lista)
    k = max(1, min(int(k), len(lista)))
    n, sobra = divmod(len(lista), k)
    out, i = [], 0
    for j in range(k):
        largo = n + (1 if j < sobra else 0)
        out.append(lista[i:i + largo])
        i += largo
    return [t for t in out if t]


def _paginas_de_talles(path_molde, mesa, talles, conts, marco, U, ocultar, destino):
    """UNA página por talle (en el orden dado) escrita en `destino`. Devuelve
    `(placeholders, lineas, etiqueta_archivo)`.

    🔴 EL TROZO DEL TALLE SE CORTA POR BYTES ANTES DE PARSEAR (2026-09-15, `cortar_capas.py`).
    La mesa del usuario son 2.350.680 operadores y **un talle es el 5 %**: parsear la mesa entera
    y recorrerla veinte veces costaba ~197 s. Ahora se ubica por bytes dónde empieza y termina
    cada capa (1,5 s para las veinte) y se parsea **sólo el trozo de cada talle**. Lo que decide
    qué se conserva sigue siendo el MISMO código de `molde_real` — cambia la entrada, no la
    regla —, así que el resultado es operador por operador el de siempre. Si el corte no se
    puede garantizar (`cortar` devuelve None), se sigue por el camino de siempre."""
    import molde_real as MR
    import cortar_capas as CC
    ocultar = set(ocultar or ())
    pdf = pikepdf.open(path_molde)
    try:
        pag = pdf.pages[mesa - 1]
        try:
            corte = CC.cortar(pag)
        except Exception as e:
            print(f"  [camino B] no se pudo cortar la mesa {mesa} por bytes ({type(e).__name__}: {e});"
                  f" sigo por el camino de siempre")
            corte = None
        ins = ops = oc = bloques = None
        if corte is None:
            ins = list(pikepdf.parse_content_stream(pag))
            ops, oc = MR._mapa_oc(ins, pag)
            bloques = MR._bloques_oc(ops, oc)
        out = pikepdf.Pdf.new()
        placeholders = {}
        lineas = {}
        etq_archivo = {}      # talle → {idx_pieza: la etiqueta de corte que traía el diseño}
        for talle in talles:
            obj = {MR._norm_capa(talle)}
            fn = (lambda pila, _o=obj: not any(frame and (_o & frame) for frame in pila))
            if corte is not None:
                _ins = CC.instrucciones(CC.solo(corte, obj))
                _ops, _oc = MR._mapa_oc(_ins, pag)
                _bloques = MR._bloques_oc(_ops, _oc)
            else:
                _ins, _ops, _oc, _bloques = ins, ops, oc, bloques
            saltar = MR._saltar_bloques(_ops, _oc, fn, _bloques)
            salida = MR._raspar_instrucciones(_ins, _ops, _oc, fn, True, saltar)
            # «00» y «NOMBRE» se leen y se SACAN del dibujo de este talle (ver arriba); y si el
            # diseño ya trae la ETIQUETA DE CORTE del talle, también se saca — si no, la prenda
            # sale con dos (la del archivo y la del sistema).
            salida, ph, etq = quitar_placeholders(salida, pag, marco, U, talle, (conts or {}).get(talle) or [],
                                                  ocultar=ocultar)
            if ph:
                placeholders[talle] = ph
            if etq:
                etq_archivo[talle] = {str(k): v for k, v in etq.items()}
            # la línea de corte del archivo se saca del dibujo: la base la vuelve a trazar con
            # la configuración del borde (o tal cual, si el borde está apagado)
            salida, lc = quitar_linea_de_corte(salida, pag, (conts or {}).get(talle) or [], marco, U)
            if lc:
                lineas[talle] = {str(k): v for k, v in lc.items()}
            npag = _pagina_desplegada(out, pag, salida)
            MR.sanear_oc(out, npag)
        out.save(destino)
        out.close()
    finally:
        pdf.close()
    return placeholders, lineas, etq_archivo


def _paginas_worker(args):
    """Worker de proceso para UN trozo de talles. Los contornos y la decisión de la etiqueta se
    releen del desplegado ya escrito: así por el pipe viajan sólo textos y números."""
    path_molde, mesa, orden, mis_talles, destino = args
    idx = _json_mismo_archivo(os.path.join(_carpeta_desplegado(path_molde), f"m{mesa}.json"),
                              _sello(path_molde), list(orden)) or {}
    conts = {t: [_cont_de_json(c) for c in lst] for t, lst in (idx.get("talles") or {}).items()}
    ocultar = familias_ocultas(leer_decision(path_molde))
    ph, lc, etq = _paginas_de_talles(path_molde, mesa, list(mis_talles), conts,
                                     idx.get("marco"), idx.get("U"), ocultar, destino)
    return list(mis_talles), ph, lc, etq


def _armar_paginas(path_molde, mesa, talles, conts, marco, U, ocultar, destino, procesos, avisar):
    """Las páginas de una mesa, repartidas por TALLE si hay procesos de sobra.

    🔴 POR QUÉ POR TALLE. El reparto del camino B es por MESA, y con un molde de UNA sola mesa
    —todas las piezas juntas en una mesa de metros, como los arma otro diseñador— no repartía
    nada: 20 talles en fila en un proceso, 197 s (medido 2026-09-14). Cada talle es una página
    independiente, así que se arman en trozos y se pegan EN ORDEN. Cada proceso vuelve a parsear
    la mesa (5 s en ese archivo); recién vale la pena con varios talles por trozo, por eso el
    corte de `_trozos`. Si el pool no arranca o un trozo falla, se hace todo acá: se pierde la
    velocidad, no el desplegado."""
    trozos = (_trozos_de_talles(talles, procesos)
              if (procesos and procesos > 1 and len(talles) > 1) else [list(talles)])
    if len(trozos) > 1:
        partes = [destino + f".p{i}" for i in range(len(trozos))]
        try:
            from concurrent.futures import as_completed
            ph_t, lc_t, etq_t, hechos = {}, {}, {}, 0
            with _POOL_FACTORY(max_workers=len(trozos)) as ex:
                futs = [ex.submit(_paginas_worker, (path_molde, mesa, list(talles), tr, pa))
                        for tr, pa in zip(trozos, partes)]
                for f in as_completed(futs):
                    mis, ph, lc, etq = f.result()
                    ph_t.update(ph); lc_t.update(lc); etq_t.update(etq)
                    hechos += len(mis)
                    if avisar:
                        avisar(hechos, len(talles), f"talle {hechos} de {len(talles)}")
            # pegar los trozos EN ORDEN (el pool los devuelve como terminan, no como van)
            abiertos = []
            try:
                out = pikepdf.Pdf.new()
                for pa in partes:
                    p = pikepdf.open(pa)
                    abiertos.append(p)
                    out.pages.extend(p.pages)      # los originales quedan abiertos hasta el save
                out.save(destino)
                out.close()
            finally:
                for p in abiertos:
                    try:
                        p.close()
                    except Exception:
                        pass
                for pa in partes:
                    try:
                        os.remove(pa)
                    except Exception:
                        pass
            return ph_t, lc_t, etq_t
        except Exception as e:
            print(f"[camino B] el reparto por talle falló ({type(e).__name__}: {e}); "
                  f"armo la mesa {mesa} entera acá")
            for pa in partes:
                try:
                    os.remove(pa)
                except Exception:
                    pass
    return _paginas_de_talles(path_molde, mesa, list(talles), conts, marco, U, ocultar, destino)


import threading as _threading
_ARMANDO = {}                      # path → Lock: un solo constructor por molde a la vez
_ARMANDO_GUARD = _threading.Lock()


def _candado(path_molde):
    """El candado de ESTE molde (el mismo objeto para todos los hilos del proceso)."""
    k = os.path.normcase(os.path.abspath(path_molde))
    with _ARMANDO_GUARD:
        c = _ARMANDO.get(k)
        if c is None:
            c = _ARMANDO[k] = _threading.Lock()
        return c


def desplegar_molde(path_molde, talles, avisar=None, procesos=None, contornos=True, paginas=True):
    """Despliega TODAS las mesas y devuelve `{mesa: {talle: [contornos]}}`.

    Con `procesos` > 1 va una mesa por proceso (ProcessPool: PyMuPDF/pikepdf no son thread-safe).
    Si el pool no arranca o se cae, las mesas que falten se hacen acá, en serie: se pierde la
    velocidad, no el alta. `avisar(hecho, total, texto)` recibe el avance mesa a mesa.
    `contornos` / `paginas`: las dos etapas de `desplegar_mesa` (el servidor las separa)."""
    _d = fitz.open(path_molde)
    n = _d.page_count
    _d.close()
    mesas = list(range(1, n + 1))
    por_mesa = {}
    hecho = 0
    # 🔴 UN CONSTRUCTOR POR MOLDE. Medido 2026-09-04: el hilo de fondo de la subida armaba las
    # páginas por proceso mientras un request, al ver que faltaban, las armaba de nuevo en su
    # hilo — el doble de trabajo y el servidor congelado. El segundo ahora ESPERA al primero
    # (el candado se suelta al terminar) y, al re-mirar, encuentra todo hecho.
    _cand = _candado(path_molde)
    _cand.acquire()
    try:
        if paginas:
            # 🔴 LA DECISIÓN VA ANTES QUE LAS PÁGINAS: necesita los candidatos de TODAS las mesas
            # (la familia se decide por cuántas piezas la traen), y las páginas la aplican. Si los
            # contornos no están todavía, se hacen primero.
            if contornos:
                _desplegar_molde_sin_candado(path_molde, talles, avisar, procesos, True, False, n, mesas, por_mesa)
                contornos = False
            try:
                decidir_etiqueta_archivo(path_molde, talles, procesos=procesos, avisar=avisar)
            except Exception as e:
                print(f"[camino B] no se pudo decidir la etiqueta del diseño de {path_molde}: {e}")
        return _desplegar_molde_sin_candado(path_molde, talles, avisar, procesos, contornos, paginas, n, mesas, por_mesa)
    finally:
        _cand.release()


def _procesos_por_defecto():
    """Cuántos procesos para armar páginas cuando el que llama no lo dice (el motor, una página
    que falta). 🔴 `TIZADA_PROCESOS` MANDA: es la variable que acota la memoria del servidor
    publicado (cada worker abre el molde entero: con un .ai de 123 MB pesa ~1 GB). Sin ella,
    los núcleos de la máquina menos uno, como siempre."""
    try:
        n = int(os.environ.get("TIZADA_PROCESOS") or 0)
    except ValueError:
        n = 0
    return max(1, n) if n else max(2, (os.cpu_count() or 2) - 1)


def _pool_por_defecto(max_workers):
    from concurrent.futures import ProcessPoolExecutor
    return ProcessPoolExecutor(max_workers=max_workers)


# Ganchos para el contrato (`verificar_desplegado_pool.py`): un pool de mentira que hace fallar una
# mesa, y contar qué se armó en serie. En producción son el ProcessPool y `desplegar_mesa`.
_POOL_FACTORY = _pool_por_defecto
_MESA_EN_SERIE = None          # se fija abajo, después de definir `desplegar_mesa`


def _desplegar_molde_sin_candado(path_molde, talles, avisar, procesos, contornos, paginas, n, mesas, por_mesa):
    hecho = 0

    def _listo(mesa, conts):
        nonlocal hecho
        if conts:
            por_mesa[mesa] = conts
        hecho += 1
        if avisar:
            avisar(hecho, n, f"mesa {mesa} de {n}")

    pendientes = list(mesas)
    if procesos and procesos > 1 and n == 1 and len(talles) > 1:
        # 🔴 UNA SOLA MESA: no hay nada que repartir por mesa, así que se reparte por TALLE
        # (ver `_armar_paginas`). Se llama a `desplegar_mesa` y no a `_MESA_EN_SERIE` porque esto
        # NO es el camino en serie: adentro abre su propio pool, y el gancho de pruebas cuenta
        # justamente lo que se hizo sin repartir.
        _listo(mesas[0], desplegar_mesa(path_molde, mesas[0], list(talles), contornos=contornos,
                                        paginas=paginas, procesos=procesos, avisar=avisar))
        return por_mesa
    if procesos and procesos > 1 and n > 1:
        # 🔴 UNA MESA QUE FALLA NO TIRA EL POOL. Antes el `except` envolvía al pool entero: la
        # primera mesa que reventaba (un «Acceso denegado» porque el motor tenía abierta su
        # página) abandonaba el pool y TODAS las que faltaban se armaban en serie dentro del
        # servidor, con el GIL tomado — medido 2026-09-11: 3 minutos de servidor a los tumbos
        # justo en el paso Tizada. Ahora cada mesa se recoge por separado: la que falla se
        # reintenta UNA vez en el pool y, si vuelve a fallar, sólo ESA va en serie al final.
        try:
            from concurrent.futures import as_completed
            with _POOL_FACTORY(max_workers=min(n, procesos)) as ex:
                futs = {ex.submit(_desplegar_mesa_worker, (path_molde, m, list(talles), contornos, paginas)): m for m in mesas}
                reintentadas = set()
                while futs:
                    for f in as_completed(list(futs)):
                        mesa = futs.pop(f)
                        try:
                            mesa, conts = f.result()
                        except Exception as e:
                            if mesa not in reintentadas:
                                reintentadas.add(mesa)
                                print(f"[camino B] la mesa {mesa} falló en el pool ({type(e).__name__}: {e}); la reintento")
                                futs[ex.submit(_desplegar_mesa_worker, (path_molde, mesa, list(talles), contornos, paginas))] = mesa
                            else:
                                print(f"[camino B] la mesa {mesa} falló dos veces en el pool ({type(e).__name__}: {e}); "
                                      f"va en serie al final")
                            continue
                        _listo(mesa, conts)
                        pendientes.remove(mesa)
        except Exception as e:
            print(f"[camino B] el pool del desplegado no arrancó ({type(e).__name__}: {e}); "
                  f"sigo en serie con {len(pendientes)} mesa(s)")
    for mesa in pendientes:
        _listo(mesa, _MESA_EN_SERIE(path_molde, mesa, list(talles), contornos=contornos, paginas=paginas))
    return por_mesa


_PERS_JSON = "personalizacion.json"


def desplegado_listo(path_molde):
    """¿Todas las mesas tienen sus páginas por talle (y del archivo actual)? Es lo que dice si
    los placeholders ya se pueden leer sin construir nada."""
    try:
        doc = fitz.open(path_molde)
        try:
            n = doc.page_count
        finally:
            doc.close()
    except Exception:
        return False
    for mesa in range(1, n + 1):
        d = _leer_desplegado(path_molde, mesa)
        if d is None or d["pdf"] is None:
            return False
    return True


def personalizacion_con_diseno(path_molde, armar=True, procesos=None):
    """Los placeholders «00» / «NOMBRE» del molde con diseño, en la forma que consume
    `motor_pedido` (`{mesa: {campo: placeholder}}`), con `por_talle` adentro de cada campo: en
    este camino cada talle tiene el suyo, a su tamaño y en su lugar. Salen del desplegado
    (`m{mesa}.json["placeholders"]`, que deja la etapa de páginas). Sin placeholders → `{}` (no
    se estampa nada, la tizada sigue).

    🔴 `armar`: si a alguna mesa le faltan las páginas, con `armar=True` se arman ACÁ — pero
    **por procesos** (`desplegar_molde`), nunca en este hilo: `pikepdf.save` retiene el GIL y
    congelaba el servidor ENTERO (medido con py-spy, 2026-09-04: `fuentes_estado` armaba las 9
    mesas en serie en el hilo del request, en paralelo con el hilo de fondo que hacía lo mismo, y
    `/api/productos` tardaba 9 s y nombrar una pieza un minuto). Con `armar=False` (lo que usa
    cualquier request) las mesas sin páginas se saltan y el que llama decide qué hacer
    (ver `desplegado_listo`)."""
    import json
    doc = fitz.open(path_molde)
    try:
        n = doc.page_count
        talles = talles_del_molde(doc)
    finally:
        doc.close()
    if armar and talles and not desplegado_listo(path_molde):
        # una sola pasada por todas las mesas, una mesa por proceso (las que ya están se saltan
        # por sello adentro de `desplegar_mesa`)
        desplegar_molde(path_molde, talles, procesos=procesos or _procesos_por_defecto(),
                        contornos=False, paginas=True)
    pers = {}
    for mesa in range(1, n + 1):
        d = _leer_desplegado(path_molde, mesa)
        if d is None or d["pdf"] is None:
            continue
        try:
            with open(os.path.join(_carpeta_desplegado(path_molde), f"m{mesa}.json"), encoding="utf-8") as fh:
                por_talle = json.load(fh).get("placeholders") or {}
        except Exception:
            por_talle = {}
        if not por_talle:
            continue
        campos = {}
        for talle, ph_t in por_talle.items():
            for campo, ph in (ph_t or {}).items():
                c = campos.setdefault(campo, {"por_talle": {}})
                c["por_talle"][talle] = ph
        for campo, c in campos.items():
            # los valores «de arriba» son los del talle del medio (o el primero que lo tenga):
            # son los que se usan si a un talle no le encontraron el placeholder
            _ts = [t for t in (d["orden"] or []) if t in c["por_talle"]] or list(c["por_talle"])
            base = c["por_talle"][_ts[len(_ts) // 2]]
            pers.setdefault(str(mesa), {})[campo] = {**base, "por_talle": c["por_talle"]}
    return pers


def piezas_con_etiqueta_propia(path_molde):
    """`(piezas_ocultadas, familias)` según la decisión guardada. NO abre el molde ni despliega:
    si la decisión no está todavía, `(0, [])` — el aviso aparece cuando el dato existe."""
    dec = leer_decision(path_molde)
    if not dec:
        return 0, []
    fams = dec.get("familias") or []
    return sum(f.get("piezas", 0) for f in fams if f.get("ocultar")), fams


def personalizacion_guardada(path_molde, armar=True):
    """Lo que `motor_pedido.extraer_personalizacion` usa para un molde con diseño: los
    placeholders por texto (ver `personalizacion_con_diseno`). Nunca None: sin placeholders es
    `{}`, y eso también es una respuesta (no hay nada que estampar)."""
    try:
        return personalizacion_con_diseno(path_molde, armar=armar)
    except Exception as e:
        print(f"[camino B] no se pudieron leer los placeholders de {path_molde}: {e}")
        return {}


def personalizacion_guardar(path_molde, pers):
    """Ya no hace falta: los placeholders viven en el desplegado, por sello. Se deja por
    compatibilidad con el motor."""
    return None


def ruta_desplegada(path_molde, mesa, talle, armar=True):
    """`(ruta_pdf, índice_de_página)` de la mesa con sólo ese talle, o None si el talle no está.
    Si la mesa no está desplegada (molde viejo, archivo cambiado) y `armar`, la despliega ahora."""
    d = _leer_desplegado(path_molde, mesa)
    if (d is None or d["pdf"] is None) and armar:
        # Por PROCESOS y con el candado del molde (ver `desplegar_molde`): armar acá, en el hilo
        # que pide la página, retenía el GIL y congelaba el servidor.
        doc = fitz.open(path_molde)
        try:
            talles = talles_del_molde(doc)
        finally:
            doc.close()
        if not talles:
            return None
        desplegar_molde(path_molde, talles, procesos=_procesos_por_defecto(),
                        contornos=(d is None), paginas=True)
        d = _leer_desplegado(path_molde, mesa)
    if d is None or d["pdf"] is None or talle not in d["orden"]:
        return None
    return d["pdf"], d["orden"].index(talle)


_MESA_EN_SERIE = desplegar_mesa   # el armado en serie de verdad (el contrato lo reemplaza para contar)
