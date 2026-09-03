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


def alta_molde_con_diseno(path, avisar=None, procesos=None):
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
        por_mesa = desplegar_molde(path, talles, avisar=avisar, procesos=procesos) if talles else {}

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
        for talle in talles:
            _pm = [(mesa, i, cont)
                   for mesa in sorted(por_mesa)
                   for i, cont in enumerate(por_mesa[mesa].get(talle) or [])]
            if not _pm:
                continue
            try:
                visor[talle] = layout_visor(doc, _pm, talle, talles)
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
    piezas_mesa = []
    for mesa in range(1, doc.page_count + 1):
        for i, cont in enumerate(piezas_de_mesa(doc, mesa, talle_ref)):
            piezas_mesa.append((mesa, i, cont))
    if not piezas_mesa:
        raise ValueError(f"No se detectaron piezas en el talle {talle_ref!r}.")
    return layout_visor(doc, piezas_mesa, talle_ref, talles, sep_cm)


def layout_visor(doc, piezas_mesa, talle_ref, talles, sep_cm=2.0):
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

    sep = sep_cm * CM
    zoom = 10.0 / CM                                 # 1 unidad de salida = 1 mm (igual que hoy)
    items, cursor_x, cursor_y, alto_fila = [], sep, sep, 0.0
    ancho_max = 0.0

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
        out = {}
        for k, talle in enumerate(talles):
            _pm = []
            for mesa in range(1, doc.page_count + 1):
                for i, cont in enumerate(piezas_de_mesa(doc, mesa, talle)):
                    _pm.append((mesa, i, cont))
            if not _pm:
                continue
            try:
                out[talle] = layout_visor(doc, _pm, talle, talles)
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
    if hit is not None and hit["sello"] == sello:
        return hit
    fj = os.path.join(carpeta, f"m{mesa}.json")
    fp = os.path.join(carpeta, f"m{mesa}.pdf")
    if not (os.path.exists(fj) and os.path.exists(fp)):
        return None
    try:
        import json
        with open(fj, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:
        return None
    if d.get("sello") != sello:
        return None
    conts = {t: [_cont_de_json(c) for c in lst] for t, lst in (d.get("talles") or {}).items()}
    hit = {"sello": sello, "orden": list(d.get("orden") or []), "contornos": conts, "pdf": fp}
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


def desplegar_mesa(path_molde, mesa, talles, carpeta=None):
    """Despliega UNA mesa: escribe `m{mesa}.pdf` + `m{mesa}.json` y devuelve `{talle: [contornos]}`
    (sólo los talles con piezas). Es lo que corre en cada proceso del alta."""
    import json
    import molde_real as MR
    carpeta = carpeta or _carpeta_desplegado(path_molde)
    os.makedirs(carpeta, exist_ok=True)
    sello = _sello(path_molde)

    # 1) los contornos, como siempre (get_drawings de la mesa, una vez para los 20 talles)
    doc = fitz.open(path_molde)
    try:
        conts = {}
        for talle in talles:
            pzs = _piezas_de_mesa_cruda(doc, mesa, talle)
            if pzs:
                conts[talle] = pzs
    finally:
        olvidar(doc)
        doc.close()

    # 2) la página de cada talle. Se parsea la mesa UNA vez y se filtra veinte; el filtrado es,
    #    instrucción por instrucción, el mismo de `aislar_capa(..., podar=True)`.
    pdf = pikepdf.open(path_molde)
    try:
        pag = pdf.pages[mesa - 1]
        ins = list(pikepdf.parse_content_stream(pag))
        ops, oc = MR._mapa_oc(ins, pag)
        bloques = MR._bloques_oc(ops, oc)
        out = pikepdf.Pdf.new()
        for talle in talles:
            obj = {MR._norm_capa(talle)}
            fn = (lambda pila, _o=obj: not any(frame and (_o & frame) for frame in pila))
            saltar = MR._saltar_bloques(ops, oc, fn, bloques)
            salida = MR._raspar_instrucciones(ins, ops, oc, fn, True, saltar)
            npag = _pagina_desplegada(out, pag, salida)
            MR.sanear_oc(out, npag)
        fp = os.path.join(carpeta, f"m{mesa}.pdf")
        out.save(fp + ".tmp")
        out.close()
        os.replace(fp + ".tmp", fp)
    finally:
        pdf.close()

    fj = os.path.join(carpeta, f"m{mesa}.json")
    with open(fj + ".tmp", "w", encoding="utf-8") as fh:
        json.dump({"sello": sello, "orden": list(talles), "talles": conts}, fh)
    os.replace(fj + ".tmp", fj)
    _CONT_CACHE.pop((carpeta, mesa), None)
    return conts


def _desplegar_mesa_worker(args):
    """Worker de proceso (spawn-safe: recibe y devuelve tipos simples)."""
    path, mesa, talles = args
    return mesa, desplegar_mesa(path, mesa, list(talles))


def desplegar_molde(path_molde, talles, avisar=None, procesos=None):
    """Despliega TODAS las mesas y devuelve `{mesa: {talle: [contornos]}}`.

    Con `procesos` > 1 va una mesa por proceso (ProcessPool: PyMuPDF/pikepdf no son thread-safe).
    Si el pool no arranca o se cae, las mesas que falten se hacen acá, en serie: se pierde la
    velocidad, no el alta. `avisar(hecho, total, texto)` recibe el avance mesa a mesa."""
    _d = fitz.open(path_molde)
    n = _d.page_count
    _d.close()
    mesas = list(range(1, n + 1))
    por_mesa = {}
    hecho = 0

    def _listo(mesa, conts):
        nonlocal hecho
        if conts:
            por_mesa[mesa] = conts
        hecho += 1
        if avisar:
            avisar(hecho, n, f"mesa {mesa} de {n}")

    pendientes = list(mesas)
    if procesos and procesos > 1 and n > 1:
        try:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            with ProcessPoolExecutor(max_workers=min(n, procesos)) as ex:
                futs = {ex.submit(_desplegar_mesa_worker, (path_molde, m, list(talles))): m for m in mesas}
                for f in as_completed(futs):
                    mesa, conts = f.result()
                    _listo(mesa, conts)
                    pendientes.remove(mesa)
        except Exception as e:
            print(f"[camino B] el desplegado en paralelo falló ({type(e).__name__}: {e}); "
                  f"sigo en serie con {len(pendientes)} mesa(s)")
    for mesa in pendientes:
        _listo(mesa, desplegar_mesa(path_molde, mesa, list(talles)))
    return por_mesa


_PERS_JSON = "personalizacion.json"


def personalizacion_guardada(path_molde):
    """Los placeholders de nombre/número que `motor_pedido.extraer_personalizacion` ya calculó
    para ESTE archivo (por sello), o None. Vive en el desplegado porque depende sólo del archivo
    y costaba 100 s por proceso."""
    try:
        import json
        fj = os.path.join(_carpeta_desplegado(path_molde), _PERS_JSON)
        if not os.path.exists(fj):
            return None
        with open(fj, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("sello") != _sello(path_molde):
            return None
        return d.get("pers")
    except Exception:
        return None


def personalizacion_guardar(path_molde, pers):
    import json
    carpeta = _carpeta_desplegado(path_molde)
    os.makedirs(carpeta, exist_ok=True)
    fj = os.path.join(carpeta, _PERS_JSON)
    with open(fj + ".tmp", "w", encoding="utf-8") as fh:
        json.dump({"sello": _sello(path_molde), "pers": pers}, fh)
    os.replace(fj + ".tmp", fj)


def ruta_desplegada(path_molde, mesa, talle, armar=True):
    """`(ruta_pdf, índice_de_página)` de la mesa con sólo ese talle, o None si el talle no está.
    Si la mesa no está desplegada (molde viejo, archivo cambiado) y `armar`, la despliega ahora."""
    d = _leer_desplegado(path_molde, mesa)
    if d is None and armar:
        doc = fitz.open(path_molde)
        try:
            talles = talles_del_molde(doc)
        finally:
            doc.close()
        if not talles:
            return None
        desplegar_mesa(path_molde, mesa, talles)
        d = _leer_desplegado(path_molde, mesa)
    if d is None or talle not in d["orden"]:
        return None
    return d["pdf"], d["orden"].index(talle)
