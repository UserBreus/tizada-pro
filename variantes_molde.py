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
