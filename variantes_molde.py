"""
NOMBRAR VARIANTES (talles) de un molde — TIZADA PRO.

Un molde puede llegar con las capas SIN nombrar (`Layer 1`, `Capa 3`, `A`), como sale de muchos
CAD. El sistema arma el registro leyendo el NOMBRE de cada capa como talle, así que sin nombres no
hay molde utilizable: detecta 20 "talles" llamados `Layer N` y 0 piezas.

Esta herramienta deja que el usuario les ponga nombre. Dos caminos, porque hay dos formatos reales:

- **Molde ANIDADO** (el más común, gradación de Optitex): todos los talles están dibujados uno
  ENCIMA del otro, en la misma posición. Ahí no se puede "seleccionar con el mouse" un talle:
  se nombra POR CAPA.
- **Molde EXTENDIDO** (size-run): cada talle ocupa su propio bloque. Ahí sí se puede seleccionar
  las piezas de un bloque y ponerle el nombre.

En los dos casos el sistema PROPONE la curva ordenando por área (verificado contra un molde real de
20 talles: reproduce el orden exacto), y el usuario confirma o corrige los nombres — porque el
tamaño dice cuál es más chico, pero no si el más chico se llama `0` o `XS`.

El renombrado NO reescribe el archivo del usuario: escribe una VERSIÓN nueva
(`plantilla.v1.ai` + puntero `plantilla.ver`) igual que el arte. Así el original queda de respaldo,
el cambio es reversible, y —clave— el resto del motor no necesita saber nada: lee la versión
vigente y ahí las capas YA se llaman como corresponde. Traducir el nombre "al vuelo" en cada lectura
era la alternativa, y siempre quedaba un punto sin traducir (p. ej. `molde_real._candidatos_mesa`,
que compara la capa por nombre exacto y dejaría al motor sin piezas al generar la tizada).
"""
import os

import fitz

from objetos_agregados import _ver_actual, _ver_path, fijar_version, ruta_vigente

CM = 28.3465
# Capas que NUNCA son un talle (las mismas que descarta el motor).
CAPAS_SISTEMA = {"Fondo", "Capa 1", "Personalizable", "0", "referencia", "Referencia"}


def _capas_con_dibujo(doc):
    """{capa: [rects]} de todo lo dibujado, por capa, en todas las mesas."""
    out = {}
    for i in range(len(doc)):
        for d in doc[i].get_drawings():
            lay = d.get("layer")
            r = d.get("rect")
            if lay and r:
                out.setdefault(lay, []).append(r)
    return out


def _orden_archivo(doc):
    try:
        return [c.get("text") for c in doc.layer_ui_configs() if c.get("text")]
    except Exception:
        return []


def analizar(path_plantilla):
    """Radiografía del molde para la herramienta de nombrar variantes.

    Devuelve `{formato, capas:[…], sugerencia:[…]}`:
    - `formato`: 'anidado' (talles superpuestos → nombrar por capa) o 'extendido' (cada talle en su
      bloque → además se puede seleccionar).
    - `capas`: por capa → nombre actual, nº de piezas, área total, bbox y si parece un talle.
    - `sugerencia`: las capas de talle ordenadas de MENOR a MAYOR (la curva propuesta).
    """
    import motor_pedido as MP
    doc = fitz.open(ruta_vigente(path_plantilla))
    try:
        porcapa = _capas_con_dibujo(doc)
        orden = _orden_archivo(doc)
        # QUÉ ES UN TALLE lo decide el motor, no esta herramienta: una sola regla para todo el
        # sistema (si acá dijera otra cosa, el usuario nombraría capas que después el motor ignora).
        es_talle = set(MP._talles_de_plantilla(doc))
        capas = []
        for nom, rects in porcapa.items():
            area = sum(r.width * r.height for r in rects)
            x0 = min(r.x0 for r in rects); y0 = min(r.y0 for r in rects)
            x1 = max(r.x1 for r in rects); y1 = max(r.y1 for r in rects)
            capas.append({
                "capa": nom,
                "piezas": len(rects),
                "area": round(area, 1),
                "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                "es_talle": nom in es_talle,
                # CANDIDATA a variante: tiene molde dibujado, aunque el sistema todavía no la
                # cuente como talle. Son justamente las que hay que nombrar — si sólo se
                # ofrecieran las que YA son talle, un molde con todo en «Capa 1» (que es capa de
                # sistema) no tendría ninguna capa para nombrar y quedaría inusable para siempre.
                "candidata": len(rects) > 1,
            })
        capas.sort(key=lambda c: orden.index(c["capa"]) if c["capa"] in orden else 9999)

        # Se trabaja sobre las CANDIDATAS (no sólo las que ya son talle): incluye las capas de
        # sistema con molde dibujado, que son el caso típico del molde que hay que nombrar.
        talles = [c for c in capas if c["candidata"]]
        # ¿anidado o extendido? Si los bloques de dos talles se pisan casi por completo, están
        # dibujados uno sobre otro y NO se pueden separar con el mouse.
        formato = "extendido"
        if len(talles) >= 2:
            a, b = talles[0]["bbox"], talles[1]["bbox"]
            solapa_x = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            solapa_y = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            ancho = min(a[2] - a[0], b[2] - b[0]) or 1
            alto = min(a[3] - a[1], b[3] - b[1]) or 1
            if solapa_x / ancho > 0.7 and solapa_y / alto > 0.7:
                formato = "anidado"

        # La CURVA propuesta: de menor a mayor por área. El área distingue talles que por ancho
        # empatan (en un molde real, «16» y «XS» tienen el mismo ancho medio y distinta área).
        sugerencia = [c["capa"] for c in sorted(talles, key=lambda c: c["area"])]
        return {"formato": formato, "capas": capas, "sugerencia": sugerencia,
                "total_talles": len(talles),
                # el molde NO tiene ni un talle reconocido: sin nombrar las variantes no se puede
                # usar (es lo que hacía que después de subirlo no se mostrara nada)
                "sin_talles": not any(c["es_talle"] for c in capas),
                "una_sola_capa": len(talles) == 1}
    finally:
        doc.close()


def renombrar_capas(path_plantilla, mapa):
    """Escribe una VERSIÓN nueva de la plantilla con las capas renombradas.

    `mapa` = {nombre_actual: nombre_nuevo}. Devuelve (ruta_nueva, cuántas se renombraron).
    El archivo original del usuario no se toca (queda como respaldo y se puede volver a él).
    """
    import pikepdf

    mapa = {str(k): str(v).strip() for k, v in (mapa or {}).items() if str(v or "").strip()}
    if not mapa:
        raise ValueError("no hay nombres para aplicar")
    nuevos = [v for v in mapa.values()]
    if len(set(nuevos)) != len(nuevos):
        raise ValueError("hay dos variantes con el mismo nombre: cada talle tiene que ser único")

    vigente = ruta_vigente(path_plantilla)
    destino = _ver_path(path_plantilla, _ver_actual(path_plantilla) + 1)
    n = 0
    pdf = pikepdf.open(vigente)
    try:
        ocp = pdf.Root.get("/OCProperties")
        if ocp is None:
            raise ValueError("el molde no tiene capas: no se pueden nombrar las variantes")
        for o in (ocp.get("/OCGs") or []):
            nom = str(o.get("/Name") or "")
            if nom in mapa:
                o["/Name"] = pikepdf.String(mapa[nom])
                n += 1
        if not n:
            raise ValueError("ninguna de esas capas existe en el molde")
        pdf.save(destino)
    finally:
        pdf.close()
    fijar_version(path_plantilla, _ver_actual(path_plantilla) + 1)
    return destino, n


# ════════════════════════════════════════════════════════════════════════════════
# MODO «POR PIEZAS» — el molde trae TODAS las piezas en UNA sola capa
# ════════════════════════════════════════════════════════════════════════════════
# Caso real (molde «Molde short»): 36 piezas en «Capa 1», sin ninguna capa de talle. Ahí no hay
# capas que nombrar: el usuario selecciona las piezas de cada talle en el visor y les escribe el
# nombre de la variante.
#
# ⚠️ NO alcanza con guardar «la pieza 3 es del talle S» en el registro. En TODO el sistema el talle
# de una pieza sale del NOMBRE DE LA CAPA (`molde_real._candidatos_mesa` compara `d["layer"] ==
# talle`): un registro con talles que no existen como capa deja al motor SIN piezas al generar la
# tizada. Por eso, igual que `renombrar_capas`, acá se ESCRIBE EL ARCHIVO: se parte la capa única en
# capas (OCG) reales, una por variante, y el resto del sistema no se entera de nada.
#
# Cómo se parte: el content stream se recorre instrucción por instrucción y se agrupa en «unidades
# de trazado» (construcción m/l/c/v/y/re/h + el operador de pintado). Cada unidad se ubica por su
# bbox en coordenadas del lienzo y se empareja con la pieza que detectó `extraer_piezas_mesa`
# (mismo trazado → misma bbox: en el molde real la distancia dio 0.00). Después cada unidad se
# envuelve en su propio `/OC /MCx BDC … EMC`.
#
# Dos detalles que importan:
# - El BDC se mete PEGADO al trazado (después del `q … cm`, antes del `Q`), así el marcado nunca se
#   cruza con el anidado q/Q y el estado gráfico compartido (clip, ancho de línea, /GS) queda FUERA
#   de toda capa → se aplica siempre, aunque el usuario apague una variante.
# - Las piezas SIN asignar se vuelven a marcar con la capa ORIGINAL: no se pierde nada del archivo.

_CONSTRUCCION = {"m", "l", "c", "v", "y", "re", "h"}
_PINTADO = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"}


def _mul(a, b):
    """Composición de matrices PDF (a aplicada ANTES que b, que es lo que hace `cm`)."""
    return (a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
            a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
            a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5])


def _aplicar(m, x, y):
    return (m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])


def _unidades_de_trazado(instrucciones):
    """[(i_ini, i_fin, bbox_lienzo, es_clip)] — un ítem por trazado pintado del content stream.

    `bbox` sale de los puntos del trazado transformados por la CTM vigente (incluye los puntos de
    control de las curvas: sobra un poco, pero alcanza y sobra para emparejar por centro).
    `es_clip` marca los trazados que sólo definen un recorte (`W n`): esos NO son piezas y no se
    tocan (si se los metiera en una capa, apagar esa variante rompería el clip de todo el resto).
    """
    ctm, pila = (1, 0, 0, 1, 0, 0), []
    unidades, ini, pts, clip = [], None, [], False
    for i, it in enumerate(instrucciones):
        op = str(it.operator)
        if op == "q":
            pila.append(ctm)
        elif op == "Q":
            ctm = pila.pop() if pila else ctm
        elif op == "cm":
            try:
                ctm = _mul(tuple(float(v) for v in it.operands), ctm)
            except Exception:
                pass
        elif op in _CONSTRUCCION:
            if ini is None:
                ini, pts, clip = i, [], False
            try:
                f = [float(v) for v in it.operands]
            except Exception:
                f = []
            if op == "re" and len(f) == 4:
                x, y, w, h = f
                for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
                    pts.append(_aplicar(ctm, px, py))
            else:
                for k in range(0, len(f) - 1, 2):
                    pts.append(_aplicar(ctm, f[k], f[k + 1]))
        elif op in ("W", "W*"):
            clip = True
        elif op in _PINTADO:
            if ini is not None and pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                unidades.append((ini, i, (min(xs), min(ys), max(xs), max(ys)), clip))
            ini, pts, clip = None, [], False
    return unidades


def piezas_para_asignar(path_plantilla):
    """(mesa, capa, piezas) del bloque de molde a repartir en variantes: la mesa+capa con MÁS
    piezas dibujadas. En el caso que motiva esto hay una sola capa y una sola mesa; si hubiera
    varias, se trabaja sobre la que concentra el molde (y el llamador lo informa)."""
    import motor_pedido as MP
    from molde_real import extraer_piezas_mesa
    doc = fitz.open(ruta_vigente(path_plantilla))
    try:
        mejor = (0, None, None)
        for m in range(1, len(doc) + 1):
            capas = {d.get("layer") for d in doc[m - 1].get_drawings() if d.get("layer")}
            for c in capas:
                n = len(extraer_piezas_mesa(doc, m, c))
                if n > mejor[0]:
                    mejor = (n, m, c)
        if not mejor[1]:
            raise ValueError("el molde no tiene piezas dibujadas en ninguna capa")
        return mejor[1], mejor[2], extraer_piezas_mesa(doc, mejor[1], mejor[2])
    finally:
        doc.close()


def separar_por_piezas(path_plantilla, asignaciones):
    """Parte la capa única del molde en una capa (OCG) REAL por variante.

    `asignaciones` = {pieza_idx: "nombre_variante"} sobre las piezas que devuelve
    `piezas_para_asignar` (los mismos índices que `/api/plantilla/deteccion`).
    Devuelve (ruta_nueva, mesa, capa_origen, orden_de_variantes).

    El orden de las variantes es de MENOR a MAYOR ÁREA total — el mismo criterio que ya usa
    `analizar` para proponer la curva (verificado contra un molde real de 20 talles). Ese orden es
    el que queda en el panel de capas y el que después lee `_ordenar_por_archivo`.
    """
    import pikepdf
    from pikepdf import Array, Dictionary, Name, String, parse_content_stream, unparse_content_stream

    asig = {int(k): str(v).strip() for k, v in (asignaciones or {}).items() if str(v or "").strip()}
    if not asig:
        raise ValueError("no hay ninguna pieza asignada a una variante")
    mesa, capa_origen, piezas = piezas_para_asignar(path_plantilla)
    fuera = [i for i in asig if i < 0 or i >= len(piezas)]
    if fuera:
        raise ValueError(f"hay piezas que no existen en el molde: {sorted(fuera)}")
    for nom in set(asig.values()):
        if nom in CAPAS_SISTEMA and nom != "0":
            raise ValueError(f"«{nom}» es un nombre reservado del sistema: elegí otro")

    # Orden de la curva: por área total de las piezas de cada variante (menor → mayor).
    area = {}
    for i, nom in asig.items():
        b = piezas[i]["bbox_mu"]
        area[nom] = area.get(nom, 0.0) + abs(b[2] - b[0]) * abs(b[3] - b[1])
    orden = sorted(area, key=lambda n: area[n])

    vigente = ruta_vigente(path_plantilla)
    destino = _ver_path(path_plantilla, _ver_actual(path_plantilla) + 1)
    pdf = pikepdf.open(vigente)
    try:
        pg = pdf.pages[mesa - 1]
        instrucciones = list(parse_content_stream(pg))
        unidades = [u for u in _unidades_de_trazado(instrucciones) if not u[3]]

        # Emparejar cada trazado del content stream con la pieza detectada (por centro). Las
        # coordenadas de `bbox_raw` son las del lienzo PDF (y arriba), las mismas que la CTM.
        libres = list(range(len(unidades)))
        de_pieza = {}
        for k, pz in enumerate(piezas):
            x0, y0, x1, y1 = pz["bbox_raw"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            tol = 0.15 * min(abs(x1 - x0), abs(y1 - y0)) or 1.0
            mejor = None
            for u in libres:
                b = unidades[u][2]
                d = ((b[0] + b[2]) / 2 - cx) ** 2 + ((b[1] + b[3]) / 2 - cy) ** 2
                if mejor is None or d < mejor[0]:
                    mejor = (d, u)
            if mejor is None or mejor[0] ** 0.5 > tol:
                raise ValueError(f"no se pudo ubicar la pieza {k + 1} dentro del molde: "
                                 f"este molde no se puede separar por piezas")
            de_pieza[k] = unidades[mejor[1]]
            libres.remove(mejor[1])

        # OCG por variante + su nombre de recurso en la página
        ocp = pdf.Root.get("/OCProperties")
        if ocp is None:
            ocp = pdf.Root["/OCProperties"] = Dictionary(OCGs=Array(), D=Dictionary(Order=Array(), ON=Array()))
        props = pg.Resources.get("/Properties")
        if props is None:
            props = pg.Resources["/Properties"] = Dictionary()
        ocg_origen = None
        for nom_res in props.keys():
            try:
                if str(props[nom_res].get("/Name")) == capa_origen:
                    ocg_origen = Name(nom_res)
            except Exception:
                pass
        usados = {str(k) for k in props.keys()}
        res_de = {}
        for j, nom in enumerate(orden):
            ocg = pdf.make_indirect(Dictionary(
                Type=Name.OCG, Name=String(nom), Intent=Array([Name("/View"), Name("/Design")])))
            ocp["/OCGs"].append(ocg)
            d = ocp.get("/D")
            if d is None:
                d = ocp["/D"] = Dictionary(Order=Array(), ON=Array())
            for clave in ("/Order", "/ON"):
                if clave not in d:
                    d[clave] = Array()
                d[clave].append(ocg)
            k = f"/MCv{j}"
            while k in usados:
                k += "x"
            usados.add(k)
            props[k] = ocg
            res_de[nom] = Name(k)

        # Reconstruir el stream: fuera el marcado /OC viejo, y cada trazado en su capa.
        abre = {}          # índice de instrucción → nombre de recurso de la capa que la envuelve
        cierra = set()
        for k, u in de_pieza.items():
            nom = asig.get(k)
            destino_res = res_de.get(nom) if nom else ocg_origen
            if destino_res is None:
                continue   # pieza sin asignar y sin capa original que preservar: se deja suelta
            abre[u[0]] = destino_res
            cierra.add(u[1])

        # El marcado /OC que traía el archivo se saca (si no, todo quedaría además dentro de la
        # capa vieja y las variantes serían inútiles). Se respeta cualquier OTRO marcado (texto,
        # accesibilidad): sólo se descartan los BDC de /OC y su EMC pareja.
        nivel, quitar = [], set()
        for i, it in enumerate(instrucciones):
            op = str(it.operator)
            if op in ("BDC", "BMC"):
                es_oc = bool(it.operands) and str(it.operands[0]) == "/OC"
                nivel.append(es_oc)
                if es_oc:
                    quitar.add(i)
            elif op == "EMC":
                if nivel and nivel.pop():
                    quitar.add(i)

        nuevo = []
        for i, it in enumerate(instrucciones):
            if i in quitar:
                continue
            if i in abre:
                nuevo.append(([Name("/OC"), abre[i]], pikepdf.Operator("BDC")))
            nuevo.append((it.operands, it.operator))
            if i in cierra:
                nuevo.append(([], pikepdf.Operator("EMC")))
        pg.Contents = pdf.make_stream(unparse_content_stream(nuevo))
        pdf.save(destino)
    finally:
        pdf.close()
    fijar_version(path_plantilla, _ver_actual(path_plantilla) + 1)
    return destino, mesa, capa_origen, orden


def curva_sugerida(nombres_capas, estilo="letras"):
    """Nombres propuestos para una curva de N talles, del más chico al más grande. Es sólo una
    ayuda de tipeo: el usuario los edita."""
    n = len(nombres_capas)
    if n == 1:
        # molde de un solo talle: proponer una letra del medio de la curva no tiene sentido
        return ["Único"]
    letras = ["XXS", "XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL", "7XL"]
    if estilo == "numeros":
        return [str(i) for i in range(1, n + 1)]
    if estilo == "ninos":
        base = ["0", "1", "2", "4", "6", "8", "10", "12", "14", "16"]
        return (base + [f"{i}" for i in range(18, 18 + max(0, n - len(base)) * 2, 2)])[:n]
    if n <= len(letras):
        # centrar la curva alrededor de M cuando son pocos talles (3 talles → S, M, L)
        i = max(0, (len(letras) - n) // 2 - 1)
        return letras[i:i + n]
    return letras + [f"{k}XL" for k in range(7, 7 + n - len(letras))]
