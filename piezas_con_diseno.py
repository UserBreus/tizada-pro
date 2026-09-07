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


def _dibujos(doc, mesa):
    """Todo lo que dibuja una mesa, recortes incluidos.

    `get_drawings(extended=True)` es lo único que devuelve los CLIP, y es caro (segundos por mesa
    en el archivo real). Se cachea por documento+mesa porque el alta lo pide una vez por cada uno
    de los 20 talles: sin caché serían 20 lecturas de la misma mesa.
    """
    clave = (id(doc), mesa)
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


def olvidar(doc=None):
    """Suelta la caché. Obligatorio antes de cerrar el documento: la clave es `id(doc)` y Python
    reusa los ids de los objetos liberados — sin esto, otro documento podría leer estos dibujos."""
    if doc is None:
        _CACHE.clear()
        return
    for k in [k for k in _CACHE if k[0] == id(doc)]:
        del _CACHE[k]


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

    piezas = []
    for grupo in _agrupar_por_solape(rects):
        # el recorte de MAYOR ÁREA es el borde externo: el que cubre a todos los del grupo
        i = max(grupo, key=lambda k: rects[k].width * rects[k].height)
        r = rects[i]
        w_cm, h_cm = r.width / U / CM, r.height / U / CM
        if w_cm * h_cm < area_min_cm2 or min(w_cm, h_cm) < lado_min_cm:
            continue
        piezas.append((min(grupo), _contorno_de_drawing(
            {"items": _items_objetos(cands[i]["items"]), "rect": r}, cb, U, mesa, talle)))

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
    if d.get("sello") != sello:
        return None
    conts = {t: [_cont_de_json(c) for c in lst] for t, lst in (d.get("talles") or {}).items()}
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


def quitar_placeholders(salida, page, marco, U):
    """Saca de `salida` (instrucciones de UN talle) los textos «00»/«NOMBRE» y devuelve
    `(salida_sin_ellos, {campo: placeholder})`.

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
    quitar = set()
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
                if campo is None or tm is None:
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
                ancho = an * esc * th
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
        except Exception:
            continue
    if not quitar:
        return salida, {}
    return [inst for i, inst in enumerate(salida) if i not in quitar], encontrados


def desplegar_mesa(path_molde, mesa, talles, carpeta=None, contornos=True, paginas=True):
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
    import molde_real as MR
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
        _escribir_json({"sello": sello, "orden": list(talles), "talles": conts, "paginas": False,
                        "marco": marco, "U": U})
        if not paginas:
            return conts
    elif conts is None:
        # sólo las páginas: los contornos ya están (o no hacen falta acá)
        _prev = _json_vigente(fj, sello, talles)
        if _prev is None:
            return desplegar_mesa(path_molde, mesa, talles, carpeta, contornos=True, paginas=True)
        conts = _prev.get("talles") or {}
        marco, U = _prev.get("marco"), _prev.get("U")

    # 2) la página de cada talle. Se parsea la mesa UNA vez y se filtra veinte; el filtrado es,
    #    instrucción por instrucción, el mismo de `aislar_capa(..., podar=True)`.
    pdf = pikepdf.open(path_molde)
    try:
        pag = pdf.pages[mesa - 1]
        ins = list(pikepdf.parse_content_stream(pag))
        ops, oc = MR._mapa_oc(ins, pag)
        bloques = MR._bloques_oc(ops, oc)
        out = pikepdf.Pdf.new()
        placeholders = {}
        for talle in talles:
            obj = {MR._norm_capa(talle)}
            fn = (lambda pila, _o=obj: not any(frame and (_o & frame) for frame in pila))
            saltar = MR._saltar_bloques(ops, oc, fn, bloques)
            salida = MR._raspar_instrucciones(ins, ops, oc, fn, True, saltar)
            # «00» y «NOMBRE»: se leen y se SACAN del dibujo de este talle (ver arriba)
            salida, ph = quitar_placeholders(salida, pag, marco, U)
            if ph:
                placeholders[talle] = ph
            npag = _pagina_desplegada(out, pag, salida)
            MR.sanear_oc(out, npag)
        out.save(fp + ".tmp")
        out.close()
        _reemplazar(fp + ".tmp", fp)
    finally:
        pdf.close()

    _escribir_json({"sello": sello, "orden": list(talles), "talles": conts, "paginas": True,
                    "marco": marco, "U": U, "placeholders": placeholders})
    return conts


def _reemplazar(origen, destino, intentos=8):
    """`os.replace` con reintento. En Windows falla con «Acceso denegado» si OTRO proceso tiene
    el destino abierto en ese instante (el servidor leyendo `m{mesa}.json` mientras un worker lo
    reescribe): visto 2026-09-07 — el pool «fallaba» por eso y las 9 mesas seguían EN SERIE, tres
    veces más lento, sin que nadie se enterara. Esperar unas décimas y volver a probar alcanza."""
    import time
    for i in range(intentos):
        try:
            os.replace(origen, destino)
            return
        except PermissionError:
            if i == intentos - 1:
                raise
            time.sleep(0.25 * (i + 1))


def _json_vigente(fj, sello, talles):
    """El índice `m{mesa}.json` si es de ESTE archivo (sello) y de este orden de talles; si no,
    None. Un JSON viejo, de otro archivo o con otro orden, no vale: las páginas no corresponderían."""
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


def _desplegar_mesa_worker(args):
    """Worker de proceso (spawn-safe: recibe y devuelve tipos simples)."""
    path, mesa, talles, contornos, paginas = args
    return mesa, desplegar_mesa(path, mesa, list(talles), contornos=contornos, paginas=paginas)


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
        return _desplegar_molde_sin_candado(path_molde, talles, avisar, procesos, contornos, paginas, n, mesas, por_mesa)
    finally:
        _cand.release()


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
    if procesos and procesos > 1 and n > 1:
        try:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            with ProcessPoolExecutor(max_workers=min(n, procesos)) as ex:
                futs = {ex.submit(_desplegar_mesa_worker, (path_molde, m, list(talles), contornos, paginas)): m for m in mesas}
                for f in as_completed(futs):
                    mesa, conts = f.result()
                    _listo(mesa, conts)
                    pendientes.remove(mesa)
        except Exception as e:
            print(f"[camino B] el desplegado en paralelo falló ({type(e).__name__}: {e}); "
                  f"sigo en serie con {len(pendientes)} mesa(s)")
    for mesa in pendientes:
        _listo(mesa, desplegar_mesa(path_molde, mesa, list(talles), contornos=contornos, paginas=paginas))
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
        desplegar_molde(path_molde, talles, procesos=procesos or max(2, (os.cpu_count() or 2) - 1),
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
        desplegar_molde(path_molde, talles, procesos=max(2, (os.cpu_count() or 2) - 1),
                        contornos=(d is None), paginas=True)
        d = _leer_desplegado(path_molde, mesa)
    if d is None or d["pdf"] is None or talle not in d["orden"]:
        return None
    return d["pdf"], d["orden"].index(talle)
