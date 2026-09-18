// EL MOLDE SIN DISEÑO ADENTRO (camino A), EN EL NAVEGADOR — PLAN_NAVEGADOR.md etapa 1, paso 7.
//
// Traducción función por función de lo que hoy hace el servidor con un molde «pelado» (cada
// trazado es una pieza; los talles son capas): `molde_real._candidatos_mesa`,
// `extraer_contorno_mesa`, `extraer_piezas_mesa` y, de `motor_pedido.py`, `_talles_de_plantilla`,
// `_ordenar_por_archivo`, `_etiqueta_de_mesa`, `alta_plantilla`, `detectar_piezas`,
// `detectar_piezas_todas` y `alta_plantilla_manual` con todo su emparejado (exacto del DXF, por
// índice, por solape, por forma, fijos a mano, segunda pasada de «Pieza extra N»).
// El contrato `verificar_navegador_camino_a.py` compara la salida con la del servidor, número a
// número y clave por clave (también el ORDEN de los diccionarios).
//
// Lo que cambia respecto del Python se explica acá; el porqué de cada regla está en el Python.
//
// 🔴 ORDEN DE LOS DICCIONARIOS. Python conserva el orden de inserción y muchos de estos dicts
// llevan de clave el nombre del talle («0», «1», «2»…). Un objeto de JavaScript reordena las claves
// que parecen enteros (las pone primero y ascendentes): por eso todo dict con claves de talle o de
// pieza es un `Map`, y el JSON se escribe con `aTextoJSON` (que respeta el orden del Map).
//
// 🔴 `get_drawings()` (sin `extended`) ≠ `get_cdrawings(extended=True)`. El servidor lee el molde
// pelado con `get_drawings()`: sólo rellenos y trazos («f», «s», «fs»), sin recortes ni grupos,
// y con los rectángulos «re» NORMALIZADOS (`Rect(...).normalize()`). Acá se parte de
// `dibujosDePagina` (la lectura extendida, ya verificada contra PyMuPDF) y se filtra por tipo; se
// verificó con los moldes reales que los dos caminos dan la misma lista (mismos tipos, capas,
// rectángulos y tramos). Los «re» se normalizan antes de armar el contorno.
//
// 🔴 LAS CAPAS OCULTAS. `alta_plantilla` abre el archivo una vez POR TALLE y apaga las demás capas
// (`set_layer_ui_config(action=2)`) para leer el texto de la etiqueta de ese talle nada más. En
// mupdf.js el equivalente es `setLayerVisible(i, false)`, con `i` = índice de la capa en la lista
// interna de MuPDF, que NO es el orden de `/OCGs`: MuPDF la ordena por número de objeto
// DESCENDENTE (medido: en un molde `/OCGs` va 30…59 y `getLayerName(0)` es el objeto 59). Se
// resuelve por número de objeto y se verifica contra `getLayerName` (si no coincide, se corta).
// Las entradas de la interfaz que no se apagan (rótulos, bloqueadas) son las mismas que MuPDF
// ignora en `pdf_deselect_layer_config_ui`.
//
// ⚠️ `math.log` y `math.atan2` de CPython (la libm de MSVC) y los de V8 difieren en el último bit
// (medido: 2,3 % de los logaritmos, 17 % de los atan2, en 40 000 valores al azar). No hay port
// posible. `atan2` sólo alimenta un ángulo que después se redondea a 1 decimal; `log` alimenta el
// costo del emparejado por forma, que se ordena y se compara contra un umbral: un bit sólo cambia
// el resultado en un EMPATE exacto entre dos pares distintos (dos piezas con la misma geometría
// respecto de la guía). `math.hypot` sí se porta exacto (`pyHypot`).

import { pyRound, pyMax, compararTuplas, pyStrip, pyHypot, pySortedStr, pyRepr } from '../py.js'
import { dibujosDePagina } from '../pdf/dibujos.js'
import { CM, geometriaPagina, contornoDeDrawing, itemVisor, emparejarPorSolape } from './contornos.js'

export const MM = 2.83465                          // puntos por mm (molde_real.MM)
export const MARGEN_MESA_CM = 2.0                  // margen sugerido por lado (motor_pedido)
import { CAPAS_SISTEMA } from '../nombres.js'
export { CAPAS_SISTEMA }

// Las opciones de `get_text("dict")` de PyMuPDF (`TEXTFLAGS_DICT` = 199): ligaduras, espacios,
// imágenes, recorte al MediaBox y CID para los glifos sin unicode. Con otro juego de opciones
// MuPDF parte las líneas distinto y la etiqueta no se leería igual.
const OPCIONES_TEXTO = 'preserve-ligatures,preserve-whitespace,preserve-images,mediabox-clip,use-cid-for-unknown-unicode'

const ancho = (r) => Math.max(0, r[2] - r[0])
const alto = (r) => Math.max(0, r[3] - r[1])
const esDibujo = (d) => d.type === 'f' || d.type === 's' || d.type === 'fs'

// ─── el molde abierto: páginas, geometría y dibujos cacheados ─────────────────────────────────
/**
 * El molde como lo ve el servidor: `doc` es un `mupdf.PDFDocument`. Los dibujos de cada mesa se
 * leen UNA vez (el servidor los relee en cada función; acá se cachean, el resultado es el mismo).
 */
export class MoldeA {
  constructor(mupdf, doc) {
    this.mupdf = mupdf
    this.doc = doc
    this.n = doc.countPages()
    this._pag = new Map()
    this._ocultas = 0                              // > 0 mientras hay capas apagadas
  }

  pagina(mesa) {
    let p = this._pag.get(mesa)
    if (!p) {
      const page = this.doc.loadPage(mesa - 1)
      p = { page, geo: geometriaPagina(page), dibujos: null }
      this._pag.set(mesa, p)
    }
    return p
  }

  /** `page.get_drawings()`: rellenos y trazos de la mesa, con TODAS las capas visibles. */
  dibujos(mesa) {
    const p = this.pagina(mesa)
    if (!p.dibujos) {
      if (this._ocultas) throw new Error('los dibujos se leen con todas las capas visibles')
      p.dibujos = dibujosDePagina(this.mupdf, p.page).filter(esDibujo)
    }
    return p.dibujos
  }

  destroy() {
    for (const p of this._pag.values()) p.page.destroy()
    this._pag.clear()
  }
}

// ─── las capas como las lista PyMuPDF (`layer_ui_configs`) ───────────────────────────────────
function contieneRef(arr, o) {
  // pdf_array_contains: sólo el primer nivel del arreglo, por referencia
  if (!arr || arr.isNull() || !arr.isArray() || !o.isIndirect()) return false
  const n = o.asIndirect()
  for (let k = 0; k < arr.length; k++) {
    const x = arr.get(k)
    if (x.isIndirect() && x.asIndirect() === n) return true
  }
  return false
}

/**
 * `doc.layer_ui_configs()`: las entradas de la interfaz de capas, recorriendo `/OCProperties /D
 * /Order` como `populate_ui` de pdf-layer.c: un arreglo anidado se recorre (profundidad + 1), un
 * texto es un rótulo (bloqueado, sin OCG), un OCG que no está en `/OCGs` se ignora, y el mismo
 * OCG puede aparecer más de una vez. `[{text, ocg, tipo, locked, depth}]`.
 */
export function capasUI(doc) {
  let props
  try { props = doc.getTrailer().get('Root').get('OCProperties') } catch { props = null }
  if (!props || props.isNull()) return []
  const ocgs = props.get('OCGs')
  const nums = []
  if (ocgs && !ocgs.isNull() && ocgs.isArray()) {
    for (let i = 0; i < ocgs.length; i++) {
      const o = ocgs.get(i)
      nums.push(o.isIndirect() ? o.asIndirect() : 0)
    }
  }
  const D = props.get('D')
  const rb = D && !D.isNull() ? D.get('RBGroups') : null
  const locked = D && !D.isNull() ? D.get('Locked') : null
  const out = []
  const enCurso = new Set()                       // pdf_mark_obj: sólo contra ciclos
  const recorrer = (arr, depth) => {
    for (let i = 0; i < arr.length; i++) {
      const o = arr.get(i)
      if (o.isArray()) {
        const k = o.isIndirect() ? o.asIndirect() : null
        if (k !== null) { if (enCurso.has(k)) continue; enCurso.add(k) }
        try { recorrer(o, depth + 1) } finally { if (k !== null) enCurso.delete(k) }
        continue
      }
      if (o.isString()) {
        out.push({ text: o.asString(), ocg: -1, tipo: 'label', locked: true, depth })
        continue
      }
      if (!o.isIndirect() || !nums.includes(o.asIndirect())) continue
      const nombre = o.get('Name')
      out.push({
        text: nombre && !nombre.isNull() && nombre.isString() ? nombre.asString() : '',
        ocg: o.asIndirect(), depth,
        tipo: contieneRef(rb, o) ? 'radiobox' : 'checkbox',
        locked: contieneRef(locked, o),
      })
    }
  }
  try {
    const order = D && !D.isNull() ? D.get('Order') : null
    if (order && !order.isNull() && order.isArray()) recorrer(order, 0)
  } catch { /* sin /Order */ }
  return out
}

/** Map(número de objeto del OCG → índice de capa de mupdf.js), verificado contra `getLayerName`. */
function indicesDeCapa(doc) {
  const props = doc.getTrailer().get('Root').get('OCProperties')
  const ocgs = props.get('OCGs')
  const lista = []
  for (let i = 0; i < ocgs.length; i++) {
    const o = ocgs.get(i)
    if (!o.isIndirect()) continue
    const nombre = o.get('Name')
    lista.push([o.asIndirect(), nombre && !nombre.isNull() && nombre.isString() ? nombre.asString() : ''])
  }
  lista.sort((a, b) => b[0] - a[0])              // MuPDF ordena su lista interna por número, descendente
  const n = doc.countLayers()
  if (n !== lista.length) throw new Error(`capas: mupdf.js cuenta ${n} y /OCGs trae ${lista.length}`)
  const idx = new Map()
  lista.forEach(([num, nombre], i) => {
    if (doc.getLayerName(i) !== nombre) throw new Error(`capas: el índice ${i} no es el objeto ${num} («${nombre}» ≠ «${doc.getLayerName(i)}»)`)
    idx.set(num, i)
  })
  return idx
}

/**
 * `alta_plantilla`: «para cada capa de la interfaz cuyo texto no sea el talle, apagarla». Corre
 * `fn()` con las demás capas apagadas y las vuelve a dejar como estaban. Un rótulo o una capa
 * bloqueada no se tocan (MuPDF tampoco los toca).
 */
export function conSoloLaCapa(molde, talle, fn) {
  const ui = capasUI(molde.doc)
  const idx = indicesDeCapa(molde.doc)
  const antes = []
  for (const e of ui) {
    if (e.text === talle || e.tipo === 'label' || e.locked) continue
    const i = idx.get(e.ocg)
    if (i === undefined) continue
    antes.push([i, molde.doc.isLayerVisible(i)])
    molde.doc.setLayerVisible(i, false)
  }
  molde._ocultas += 1
  try {
    return fn()
  } finally {
    molde._ocultas -= 1
    for (const [i, v] of antes.reverse()) molde.doc.setLayerVisible(i, v)
  }
}

/** `_orden_capas_archivo`: los textos no vacíos de la interfaz de capas, repetidos incluidos. */
export function ordenCapasArchivo(molde) {
  try {
    return capasUI(molde.doc).map((c) => c.text).filter((t) => t)
  } catch {
    return []
  }
}

/** `_ordenar_por_archivo`: los del panel primero (en su orden), después los que no figuran. */
export function ordenarPorArchivo(molde, nombres) {
  nombres = [...nombres]
  const orden = ordenCapasArchivo(molde)
  const setNombres = new Set(nombres), setOrden = new Set(orden)
  return [...orden.filter((n) => setNombres.has(n)), ...nombres.filter((n) => !setOrden.has(n))]
}

// ─── los talles ──────────────────────────────────────────────────────────────────────────────
/**
 * `_talles_de_plantilla`. ⚠️ En Python la cola de `_ordenar_por_archivo` (las capas que no están
 * en el panel) itera un `set`: su orden depende del hash de cada texto, que cambia de un proceso a
 * otro (`PYTHONHASHSEED`). Acá van en el orden en que aparecen en el archivo; sólo importa cuando
 * una capa con dibujo no figura en `/Order`, cosa que Illustrator no produce.
 */
export function tallesDePlantilla(molde) {
  const cnt = new Map()
  for (let i = 1; i <= molde.n; i++) {
    for (const d of molde.dibujos(i)) {
      const lay = d.layer
      if (lay) cnt.set(lay, (cnt.get(lay) || 0) + 1)
    }
  }
  const conDibujo = [...cnt.keys()].filter((n) => !CAPAS_SISTEMA.has(n))
  if (cnt.has('0') && conDibujo.length) {
    const formas = conDibujo.map((n) => cnt.get(n)).sort((a, b) => a - b)
    const mediana = formas[Math.floor(formas.length / 2)]
    if (cnt.get('0') >= mediana * 0.5) conDibujo.push('0')      // tiene contenido de talle, no basura de CAD
  }
  return ordenarPorArchivo(molde, conDibujo)
}

/** `_talles_con_molde`: Map(talle → Set(mesas)), en el orden en que cada talle aparece. */
export function tallesConMolde(molde) {
  const validos = new Set(tallesDePlantilla(molde))
  const talles = new Map()
  for (let i = 1; i <= molde.n; i++) {
    for (const d of molde.dibujos(i)) {
      const lay = d.layer
      if (lay && validos.has(lay)) {
        if (!talles.has(lay)) talles.set(lay, new Set())
        talles.get(lay).add(i)
      }
    }
  }
  return talles
}

/** `_capas_con_dibujo`: Map(capa → Set(mesas)) de TODA capa con trazados. */
export function capasConDibujo(molde) {
  const capas = new Map()
  for (let i = 1; i <= molde.n; i++) {
    for (const d of molde.dibujos(i)) {
      const lay = d.layer
      if (lay) {
        if (!capas.has(lay)) capas.set(lay, new Set())
        capas.get(lay).add(i)
      }
    }
  }
  return capas
}

// ─── las piezas de una mesa (molde_real) ─────────────────────────────────────────────────────
/** `_candidatos_mesa`: los trazados de la capa del talle que no sean más grandes que la mesa. */
export function candidatosMesa(molde, mesa, talle) {
  const { geo } = molde.pagina(mesa)
  const pw = ancho(geo.rect), ph = alto(geo.rect)
  return molde.dibujos(mesa).filter((d) => d.layer === talle && ancho(d.rect) < pw * 1.2 && alto(d.rect) < ph * 1.2)
}

function itemsComoGetDrawings(items) {
  // `get_drawings` entrega los «re» normalizados (`Rect(...).normalize()`)
  return (items || []).map((it) => {
    if (it[0] !== 're') return it
    const r = it[1]
    return ['re', [Math.min(r[0], r[2]), Math.min(r[1], r[3]), Math.max(r[0], r[2]), Math.max(r[1], r[3])], it[2]]
  })
}

function contornoDe(molde, d, mesa, talle) {
  const { geo } = molde.pagina(mesa)
  return contornoDeDrawing(itemsComoGetDrawings(d.items), d.rect, geo.cb, geo.U, mesa, talle)
}

/** `extraer_contorno_mesa`: el trazado de mayor área (el PRIMERO si empatan). */
export function extraerContornoMesa(molde, mesa, talle) {
  const candidatos = candidatosMesa(molde, mesa, talle)
  if (!candidatos.length) throw new Error(`Mesa ${mesa}: no hay trazados en la capa ${pyRepr(talle)}.`)
  const cont = pyMax(candidatos, (d) => ancho(d.rect) * alto(d.rect))
  return contornoDe(molde, cont, mesa, talle)
}

/** `extraer_piezas_mesa` (camino A): un trazado = una pieza, EN EL ORDEN DEL ARCHIVO. */
export function extraerPiezasMesa(molde, mesa, talle, areaMinCm2 = 0.25, ladoMinCm = 0.3) {
  const { geo } = molde.pagina(mesa)
  const piezas = []
  for (const d of candidatosMesa(molde, mesa, talle)) {
    const wCm = ancho(d.rect) / geo.U / CM, hCm = alto(d.rect) / geo.U / CM
    if (wCm * hCm < areaMinCm2 || Math.min(wCm, hCm) < ladoMinCm) continue
    piezas.push(contornoDe(molde, d, mesa, talle))
  }
  return piezas
}

// ─── el texto de la etiqueta «TALLE-Pieza-#» ─────────────────────────────────────────────────
const interseccionVacia = (a, b) =>
  Math.max(a[0], b[0]) >= Math.min(a[2], b[2]) || Math.max(a[1], b[1]) >= Math.min(a[3], b[3])

function rectDeQuad(q) {
  // fz_rect_from_quad: el mínimo y el máximo de las cuatro esquinas
  const xs = [q[0], q[2], q[4], q[6]], ys = [q[1], q[3], q[5], q[7]]
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
}

/**
 * `_etiqueta_de_mesa`: la primera línea con texto de la mesa, con las capas de los otros talles
 * apagadas (quien llama lo garantiza con `conSoloLaCapa`). Devuelve los fragmentos
 * `[texto, origen, dir, size, fuente]` de CADA línea con texto, como PyMuPDF: `texto` = todos los
 * caracteres de la línea, `origen`/`size`/`fuente` = los del primer span (= del primer carácter),
 * `dir` = la dirección de la línea; la fuente sin el prefijo de subconjunto (`split("+")[-1]`).
 * Se replican los descartes de `get_text("dict")`: un bloque o una línea cuyo rectángulo no toca
 * la página, y un carácter cuyo cuadrilátero no se solapa con ella.
 * (No se replica la corrección del cuadrilátero de `JM_char_quad` para fuentes con ascender y
 * descender degenerados: no cambia si el carácter toca o no la página en ningún caso real.)
 */
export function etiquetaDeMesa(molde, mesa) {
  const { page, geo } = molde.pagina(mesa)
  const tp = geo.rect                              // el MediaBox de la página de texto = page.rect
  const st = page.toStructuredText(OPCIONES_TEXTO)
  const frags = []
  let bloqueOk = false, linea = null
  try {
    st.walk({
      beginTextBlock(bbox) { bloqueOk = !interseccionVacia(tp, bbox) },
      endTextBlock() { bloqueOk = false },
      beginLine(bbox, wmode, dir) {
        linea = bloqueOk && !interseccionVacia(tp, bbox) ? { chars: [], dir: [dir[0], dir[1]], primero: null } : null
      },
      onChar(c, origin, font, size, quad) {
        if (!linea) return
        const r = rectDeQuad(quad)
        if (tp[0] >= r[2] || tp[1] >= r[3] || tp[2] <= r[0] || tp[3] <= r[1]) return   // JM_rects_overlap
        if (!linea.primero) linea.primero = { origin: [origin[0], origin[1]], size, fuente: font.getName() }
        linea.chars.push(c)
      },
      endLine() {
        if (!linea) return
        const t = linea.chars.join('')
        if (pyStrip(t)) {
          const p = linea.primero
          frags.push([t, p.origin, linea.dir, p.size, p.fuente.split('+').pop()])
        }
        linea = null
      },
    })
  } finally {
    st.destroy()
  }
  return frags
}

// ─── utilidades chicas de Python ─────────────────────────────────────────────────────────────
const listaPy = (arr) => `[${arr.join(', ')}]`                         // str(lista de enteros)
const stripGuiones = (s) => s.replace(/^-+/, '').replace(/-+$/, '')   // str.strip("-")
const grados = (x) => x * (180.0 / Math.PI)                            // math.degrees

function entradaRegistro(cont, mesa, ancla, piezaIdx) {
  const e = { mesa }
  if (piezaIdx !== undefined) e.pieza_idx = piezaIdx
  e.w_cm = pyRound(cont.w / CM, 1)
  e.h_cm = pyRound(cont.h / CM, 1)
  e.bbox_mu = cont.bbox_mu.map((v) => pyRound(v, 2))
  e.ancla = ancla
  return e
}

// ─── alta por etiquetas de texto ─────────────────────────────────────────────────────────────
/** `alta_plantilla`: la moldería con la convención «una mesa por pieza, talles en capas». */
export function altaPlantilla(molde) {
  const talles = tallesDePlantilla(molde)          // deja leídos los dibujos de todas las mesas
  const registro = new Map(), problemas = [], advertencias = []
  const mesasPorPieza = new Map()                  // pieza → Set(mesas)
  if (!talles.length) {
    problemas.push('No se encontró ninguna capa de talle. Cada talle debe ser una capa con su ' +
      'nombre exacto (M, 3XL, 16, …).')
  }
  for (const talle of talles) {
    conSoloLaCapa(molde, talle, () => {
      for (let mesa = 1; mesa <= molde.n; mesa++) {
        const { page } = molde.pagina(mesa)
        // `d2[mesa-1].get_drawings()` con las otras capas apagadas: sólo importa si hay algo del talle
        const tieneMolde = dibujosDePagina(molde.mupdf, page, { ligero: true })
          .some((d) => esDibujo(d) && d.layer === talle)
        const frags = etiquetaDeMesa(molde, mesa)
        const texto = pyStrip(frags.map((f) => f[0]).join(''))
        if (!frags.length) {
          if (tieneMolde) {
            problemas.push(`Mesa ${mesa}, talle «${talle}»: hay molde dibujado pero falta la etiqueta de texto «${talle}-Pieza-#».`)
          }
          continue
        }
        if (!texto.startsWith(talle + '-') || !texto.endsWith('#')) {
          problemas.push(`Mesa ${mesa}, talle «${talle}»: etiqueta «${texto}» mal escrita. Debe empezar con «${talle}-» y terminar en «-#» (ej. «${talle}-Frente-#»).`)
          continue
        }
        // texto[len(talle) + 1:-2] — por puntos de código, como Python
        const cps = Array.from(texto)
        const pieza0 = pyStrip(stripGuiones(cps.slice(Array.from(talle).length + 1, -2).join('')))
        let pieza = pieza0
        if (!pieza) {
          problemas.push(`Mesa ${mesa}, talle «${talle}»: la etiqueta no nombra la pieza. Formato: «${talle}-NombreDePieza-#».`)
          continue
        }
        let cont
        try {
          cont = extraerContornoMesa(molde, mesa, talle)
        } catch (e) {
          problemas.push(`Mesa ${mesa}, talle «${talle}», pieza «${pieza}»: no se pudo leer el contorno (${e.message}).`)
          continue
        }
        if (pieza.startsWith('Manga') && !pieza.toLowerCase().includes('corta') && !pieza.toLowerCase().includes('larga')) {
          pieza += cont.h / CM < 45 ? ' (corta)' : ' (larga)'
        }
        if (!mesasPorPieza.has(pieza)) mesasPorPieza.set(pieza, new Set())
        mesasPorPieza.get(pieza).add(mesa)
        if (registro.has(pieza) && registro.get(pieza).has(talle)) {
          const mesas = [...mesasPorPieza.get(pieza)].sort((a, b) => a - b)
          advertencias.push(`Pieza «${pieza}», talle «${talle}»: etiqueta repetida (mesas ${listaPy(mesas)}). Se usa la última.`)
        }
        const [, origen, [dx, dy], size, fuente] = frags[0]
        const ancla = {
          x: pyRound(origen[0], 1), y: pyRound(origen[1], 1),
          angulo: pyRound(grados(Math.atan2(-dy, dx)), 1),
          size_pt: pyRound(size, 1), fuente,
        }
        if (!registro.has(pieza)) registro.set(pieza, new Map())
        registro.get(pieza).set(talle, entradaRegistro(cont, mesa, ancla))
      }
    })
  }
  // cada pieza debe vivir en UNA sola mesa
  for (const pieza of pySortedStr([...mesasPorPieza.keys()])) {
    const mesas = mesasPorPieza.get(pieza)
    if (mesas.size > 1) {
      advertencias.push(`La pieza «${pieza}» está repartida en las mesas ${listaPy([...mesas].sort((a, b) => a - b))}. ` +
        'La convención nueva pide UNA sola mesa por pieza, con todos los talles como capas.')
    }
  }
  const piezasDetalle = new Map()
  for (const [pieza, porTalle] of registro) {
    const mayor = pyMax([...porTalle.values()], (v) => v.h_cm)
    piezasDetalle.set(pieza, {
      mesas: [...(mesasPorPieza.get(pieza) || [])].sort((a, b) => a - b),
      talles: ordenarPorArchivo(molde, porTalle.keys()),
      talle_mayor_cm: { w: mayor.w_cm, h: mayor.h_cm },
      mesa_sugerida_cm: { w: pyRound(mayor.w_cm + 2 * MARGEN_MESA_CM, 1), h: pyRound(mayor.h_cm + 2 * MARGEN_MESA_CM, 1) },
    })
  }
  const completos = talles.filter((t) => [...registro.values()].every((p) => p.has(t)))
  return { mesas: molde.n, talles, piezas: pySortedStr([...registro.keys()]), completos, registro, problemas,
    advertencias, piezas_detalle: piezasDetalle }
}

// ─── detección por geometría (etiquetado visual) ─────────────────────────────────────────────
/** `_union_bbox`. */
export function unionBbox(piezas) {
  if (!piezas.length) throw new Error('min() arg is an empty sequence')
  return [Math.min(...piezas.map((c) => c.bbox_mu[0])), Math.min(...piezas.map((c) => c.bbox_mu[1])),
    Math.max(...piezas.map((c) => c.bbox_mu[2])), Math.max(...piezas.map((c) => c.bbox_mu[3]))]
}

function conteoPorCapa(molde, mesa) {
  // collections.Counter(str(d["layer"]) for d in get_drawings() if d.get("layer"))
  const cnt = new Map()
  for (const d of molde.dibujos(mesa)) if (d.layer) cnt.set(d.layer, (cnt.get(d.layer) || 0) + 1)
  return cnt
}

/** `_mesa_principal`: la mesa con más trazos de talle (a igual cantidad, la de mayor número). */
export function mesaPrincipal(molde, talles) {
  const ranking = []
  for (let m = 1; m <= molde.n; m++) {
    const cnt = conteoPorCapa(molde, m)
    let n = 0
    for (const t of talles) n += cnt.get(t) || 0
    if (n) ranking.push([n, m])
  }
  if (!ranking.length) return null
  ranking.sort((a, b) => -compararTuplas(a, b))
  return ranking[0][1]
}

function clipDe(piezas) {
  const union = unionBbox(piezas)
  const mx = Math.max(20.0, (union[2] - union[0]) * 0.04)
  return [union[0] - mx, union[1] - mx, union[2] + mx, union[3] + mx]
}

/**
 * `detectar_piezas` (sin su caché). `{mesa, talle_ref, talles, unidad, img_w, img_h, piezas,
 * sin_variantes}`. ⚠️ Cada item mezcla dos sistemas: `px/py/pw/ph` salen de `bbox_mu` (coords
 * MuPDF, sin pasar por el cropbox ni el /UserUnit) y `path_svg` de los segmentos crudos del lienzo
 * (con cropbox y U): `_item_visor` es así en el servidor y se copia tal cual.
 */
export function detectarPiezas(molde, talleRef = null, capasCandidatas = false) {
  let tallesMesas = tallesConMolde(molde)
  let sinVariantes = false
  if (capasCandidatas && !tallesMesas.size) {
    sinVariantes = true
    tallesMesas = capasConDibujo(molde)
  }
  // ¿existe una capa de referencia? (sin distinguir mayúsculas; si hay varias, la última)
  const capasDoc = new Map()
  for (const c of capasUI(molde.doc)) if (c.text) capasDoc.set(c.text.toLowerCase(), c.text)
  const capaRef = capasDoc.get('referencia')
  let mesa = null
  if (capaRef) {
    talleRef = capaRef
    mesa = 1
    for (let i = 0; i < molde.n; i++) {
      if (extraerPiezasMesa(molde, i + 1, capaRef).length) { mesa = i + 1; break }
    }
  } else {
    if (!tallesMesas.size) throw new Error('La plantilla no tiene capas de talle con molde dibujado.')
    const tallesSet = [...tallesMesas.keys()]
    const ranking = []                             // (n_trazos, mesa, talle)
    for (let m = 1; m <= molde.n; m++) {
      const cnt = conteoPorCapa(molde, m)
      for (const t of tallesSet) if (cnt.get(t)) ranking.push([cnt.get(t), m, t])
    }
    ranking.sort((a, b) => -compararTuplas(a, b))
    let talleAuto = null
    for (const [, m, t] of ranking) {              // el talle con más trazos que dé piezas
      if (extraerPiezasMesa(molde, m, t).length) { mesa = m; talleAuto = t; break }
    }
    if (mesa === null) throw new Error('La plantilla no tiene capas de talle con molde dibujado.')
    talleRef = talleRef || talleAuto
  }
  const piezas = extraerPiezasMesa(molde, mesa, talleRef)
  if (!piezas.length) throw new Error(`No se detectaron piezas en la mesa ${mesa}, talle ${pyRepr(talleRef)}.`)
  const clip = clipDe(piezas)
  const zoom = 1.0 / MM
  const { geo } = molde.pagina(mesa)
  const items = piezas.map((cont, i) => itemVisor(cont, i, clip, geo.cb, geo.U, zoom))
  return { mesa, talle_ref: talleRef, talles: ordenarPorArchivo(molde, tallesMesas.keys()), unidad: 'mm',
    img_w: pyRound(ancho(clip) * zoom, 1), img_h: pyRound(alto(clip) * zoom, 1),
    piezas: items, sin_variantes: sinVariantes }
}

/** `detectar_piezas_todas`: todas las piezas de todos los talles en un solo lienzo. */
export function detectarPiezasTodas(molde) {
  const tallesMesas = tallesConMolde(molde)
  if (!tallesMesas.size) throw new Error('La plantilla no tiene capas de talle con molde dibujado.')
  let talles = ordenarPorArchivo(molde, tallesMesas.keys())
  const mesa = mesaPrincipal(molde, talles)
  if (mesa === null) throw new Error('La plantilla no tiene capas de talle con molde dibujado.')
  const porTalle = new Map()
  for (const t of talles) {
    const pzs = extraerPiezasMesa(molde, mesa, t)
    if (pzs.length) porTalle.set(t, pzs)
  }
  if (!porTalle.size) throw new Error(`No se detectaron piezas en la mesa ${mesa}.`)
  talles = talles.filter((t) => porTalle.has(t))
  const todas = []
  for (const t of talles) todas.push(...porTalle.get(t))
  const clip = clipDe(todas)
  const zoom = 1.0 / MM
  const { geo } = molde.pagina(mesa)
  const items = []
  let g = 0
  for (const t of talles) {
    porTalle.get(t).forEach((cont, i) => {
      const it = itemVisor(cont, g, clip, geo.cb, geo.U, zoom)
      it.talle = t
      it.t_idx = i
      items.push(it)
      g += 1
    })
  }
  const conteo = new Map()
  for (const t of talles) conteo.set(t, porTalle.get(t).length)
  return { mesa, talles, unidad: 'mm', img_w: pyRound(ancho(clip) * zoom, 1), img_h: pyRound(alto(clip) * zoom, 1),
    piezas: items, por_talle: conteo }
}

// ─── el emparejado entre talles ──────────────────────────────────────────────────────────────
/** `_bboxes_acomodadas`: las cajas con el acomodo a mano (`offsets` = Map(idx → [dx_mm, dy_mm])). */
export function bboxesAcomodadas(conts, offsets = null) {
  return conts.map((c, i) => {
    let [x0, y0, x1, y1] = c.bbox_mu
    const d = offsets ? offsets.get(i) : undefined
    if (d) {
      const dx = d[0] * MM, dy = d[1] * MM
      x0 += dx; x1 += dx; y0 += dy; y1 += dy
    }
    return [x0, y0, x1, y1]
  })
}

/** `_feats_conts`: centroide normalizado a la unión del talle, log-aspecto y log-área relativa. */
export function featsConts(conts, offsets = null) {
  const cajas = bboxesAcomodadas(conts, offsets)
  if (!cajas.length) throw new Error('min() arg is an empty sequence')
  const ux0 = Math.min(...cajas.map((b) => b[0])), uy0 = Math.min(...cajas.map((b) => b[1]))
  const ux1 = Math.max(...cajas.map((b) => b[2])), uy1 = Math.max(...cajas.map((b) => b[3]))
  const uw = Math.max(1e-6, ux1 - ux0), uh = Math.max(1e-6, uy1 - uy0)
  return cajas.map(([x0, y0, x1, y1]) => {
    const w = Math.max(1e-6, x1 - x0), h = Math.max(1e-6, y1 - y0)
    return { cx: ((x0 + x1) / 2 - ux0) / uw, cy: ((y0 + y1) / 2 - uy0) / uh,
      lar: Math.log(w / h), larea: Math.log((w * h) / (uw * uh)) }
  })
}

// `int(x)` de Python sobre lo que viene de un JSON: un entero, un float (se trunca) o un texto
// con un entero (espacios alrededor permitidos). Cualquier otra cosa lanza, como en Python.
function intPy(v) {
  if (typeof v === 'boolean') return v ? 1 : 0
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) throw new Error('int() de un float no finito')
    return Math.trunc(v)
  }
  if (typeof v === 'string' && /^\s*[+-]?\d+\s*$/.test(v)) return parseInt(v.trim(), 10)
  throw new Error(`int() inválido: ${v}`)
}
function floatPy(v) {
  if (typeof v === 'boolean') return v ? 1 : 0
  if (typeof v === 'number') return v
  if (typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v))) return Number(v)
  throw new Error(`float() inválido: ${v}`)
}
const propio = (o, k) => o !== null && typeof o === 'object' && Object.prototype.hasOwnProperty.call(o, k)

/** `emp_offsets`: el acomodo a mano de un talle → Map(idx → [dx_mm, dy_mm]) o null. */
export function empOffsets(emparejado, talle) {
  const d = (((emparejado || {}).acomodo) || {})
  const v = propio(d, talle) ? (d[talle] || {}) : {}
  const out = new Map()
  for (const [k, x] of Object.entries(v)) {
    try { out.set(intPy(k), [floatPy(x[0]), floatPy(x[1])]) } catch { continue }
  }
  return out.size ? out : null
}

/** `emp_fijos`: las correcciones manuales de un talle → Map(nombre → idx) o null. */
export function empFijos(emparejado, talle) {
  const d = (((emparejado || {}).manual) || {})
  const v = propio(d, talle) ? (d[talle] || {}) : {}
  const out = new Map()
  for (const [nom, idx] of Object.entries(v)) {
    try { out.set(String(nom), intPy(idx)) } catch { continue }
  }
  return out.size ? out : null
}

/** `_aplicar_fijos`: lo manual pisa lo automático y libera el índice que tuviera otro nombre. */
export function aplicarFijos(eleccion, fijos, nPiezas) {
  if (!fijos) return eleccion
  for (const [nom, j] of fijos) {
    if (j === null || j < 0 || j >= nPiezas) continue
    for (const [otro, [jj]] of [...eleccion]) {
      if (jj === j && otro !== nom) eleccion.delete(otro)
    }
    eleccion.set(nom, [j, false])                 // una clave que ya existía conserva su lugar (como en Python)
  }
  return eleccion
}

/** `_emparejar_por_forma`: Map(nombre → [idx, rotada90]), greedy global por costo. */
export function emparejarPorForma(fRef, nombresRef, fCand, umbral = 1.6) {
  const pares = []
  for (const [nom, ir] of nombresRef) {
    if (ir >= fRef.length) continue
    const fr = fRef[ir]
    fCand.forEach((fc, j) => {
      const dpos = pyHypot(fc.cx - fr.cx, fc.cy - fr.cy)
      const daRecta = Math.abs(fc.lar - fr.lar)
      const daGirada = Math.abs(-fc.lar - fr.lar) + 0.25
      const rot = daGirada < daRecta
      const daspect = Math.min(daRecta, daGirada)
      const darea = Math.abs(fc.larea - fr.larea)
      pares.push([dpos + 0.9 * daspect + 0.6 * darea, nom, j, rot])
    })
  }
  pares.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))   // sort(key=costo): estable
  const eleccion = new Map(), usados = new Set()
  for (const [costo, nom, j, rot] of pares) {
    if (costo > umbral) break
    if (eleccion.has(nom) || usados.has(j)) continue
    eleccion.set(nom, [j, rot])
    usados.add(j)
  }
  return eleccion
}

/** `_mapa_indices`: la correspondencia del DXF → Map(talle → Map(idx_ref → idx_talle)) o null. */
export function mapaIndices(indices, talleRef) {
  if (!indices || !propio(indices, talleRef)) return null
  const posiciones = (lst) => {
    const d = new Map()
    lst.forEach((nm, i) => { if (!d.has(nm)) d.set(nm, []); d.get(nm).push(i) })
    return d
  }
  const posRef = posiciones(indices[talleRef])
  const out = new Map()
  for (const [t, lst] of Object.entries(indices)) {
    const posT = posiciones(lst)
    const m = new Map()
    for (const [nm, refs] of posRef) {
      const ts = posT.get(nm) || []
      refs.forEach((gi, k) => { if (k < ts.length) m.set(gi, ts[k]) })
    }
    out.set(t, m)
  }
  return out
}

/** `_ancla_sintetica`: etiqueta de 3 mm, centrada y pegada al borde inferior. */
export function anclaSintetica(cont) {
  const [x0, , x1, y1] = cont.bbox_mu
  const size = 3.0 * MM
  return { x: pyRound((x0 + x1) / 2, 1), y: pyRound(y1 - size * 0.25, 1), angulo: 0.0,
    size_pt: pyRound(size, 2), fuente: 'Arial-BoldMT' }
}

// `\s+\d+\s*$` de Python: `\s` son los espacios de Python y `\d` cualquier dígito decimal Unicode
const ESPACIOS = '[\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]'
const RE_NUMERO_FINAL = new RegExp(`${ESPACIOS}+\\p{Nd}+${ESPACIOS}*$`, 'u')

/**
 * `nombres_normalizados`: `[{idx, nombre}]` → Map(idx → nombre final), en el orden de Python
 * (por genérico, según el menor índice que lo usa; adentro por índice). Lo único se respeta;
 * los repetidos de un genérico reciben el primer número libre.
 */
export function nombresNormalizados(asignaciones) {
  const raw = new Map()
  for (const a of asignaciones || []) {
    const n = pyStrip(String(a.nombre || ''))
    if (n) raw.set(a.idx, n)
  }
  const genPz = (n) => pyStrip(n.replace(RE_NUMERO_FINAL, ''))
  const porGen = new Map()
  for (const i of [...raw.keys()].sort((a, b) => a - b)) {
    const g = genPz(raw.get(i))
    if (!porGen.has(g)) porGen.set(g, [])
    porGen.get(g).push(i)
  }
  const nombres = new Map()
  for (const [, idxs] of porGen) {
    const vals = idxs.map((i) => raw.get(i))
    if (new Set(vals).size === vals.length) {
      for (const i of idxs) nombres.set(i, raw.get(i))
      continue
    }
    const libres = new Set(vals.filter((v) => vals.filter((x) => x === v).length === 1))
    const usados = new Set(libres)
    for (const i of idxs) {
      const v = raw.get(i)
      if (libres.has(v)) { nombres.set(i, v); continue }
      const base = genPz(v) || v
      let n = 1
      while (usados.has(`${base} ${n}`)) n += 1
      nombres.set(i, `${base} ${n}`)
      usados.add(`${base} ${n}`)
    }
  }
  return nombres
}

/**
 * `alta_plantilla_manual`: el registro a partir de los nombres puestos en el talle de referencia.
 * `indices` = la correspondencia del DXF ({talle: [nombre por índice]}), `emparejado` =
 * {acomodo: {talle: {idx: [dx, dy]}}, manual: {talle: {nombre: idx}}}, `excluirTalles` = lista.
 */
export function altaPlantillaManual(molde, asignaciones, mesa, talleRef, indices = null, emparejado = null, excluirTalles = null) {
  const nombres = nombresNormalizados(asignaciones)
  if (!nombres.size) {
    return { mesas: molde.n, registro: new Map(), piezas: [], talles: [], completos: [],
      problemas: ['No se asignó ningún nombre de pieza.'], advertencias: [], piezas_detalle: new Map() }
  }
  const piezasRef = extraerPiezasMesa(molde, mesa, talleRef)
  const fRef = featsConts(piezasRef, empOffsets(emparejado, talleRef))
  const nombresRef = new Map()
  for (const [i, nom] of nombres) if (i < piezasRef.length) nombresRef.set(nom, i)
  // se cargan TODAS las piezas: las sin nombre, con uno provisorio «Pieza N»
  const usadosRef = new Set(nombresRef.values())
  for (let i = 0; i < piezasRef.length; i++) {
    if (usadosRef.has(i)) continue
    let prov = `Pieza ${i + 1}`
    while (nombresRef.has(prov)) prov += "'"
    nombresRef.set(prov, i)
  }
  const mapaExacto = mapaIndices(indices, talleRef)

  const tallesMesas = tallesConMolde(molde)
  const registro = new Map(), problemas = [], advertencias = []
  let sobrantesPorTalle = new Map()
  const pzsTalle = new Map(), sobraTalle = new Map()
  const excl = new Set((excluirTalles || []).map((t) => String(t)))
  const anotar = (nom, talle, cont, j) => {
    if (!registro.has(nom)) registro.set(nom, new Map())
    registro.get(nom).set(talle, entradaRegistro(cont, mesa, anclaSintetica(cont), j))
  }
  for (const [talle, mesas] of tallesMesas) {
    if (!mesas.has(mesa) || excl.has(talle)) continue
    const piezas = extraerPiezasMesa(molde, mesa, talle)
    if (!piezas.length) continue
    let eleccion
    if (talle === talleRef) {
      eleccion = new Map([...nombresRef].map(([nom, i]) => [nom, [i, false]]))
    } else if (mapaExacto && mapaExacto.has(talle)) {
      const mt = mapaExacto.get(talle)
      eleccion = new Map()
      for (const [nom, ir] of nombresRef) if (mt.has(ir) && mt.get(ir) < piezas.length) eleccion.set(nom, [mt.get(ir), false])
    } else if (piezas.length === piezasRef.length) {
      // misma cantidad → el índice ES la correspondencia
      eleccion = new Map()
      for (const [nom, i] of nombresRef) if (i < piezas.length) eleccion.set(nom, [i, false])
    } else {
      eleccion = emparejarPorSolape(piezasRef, nombresRef, piezas)
      if (!eleccion.size) {                        // sin solape (talles lado a lado) → forma
        eleccion = emparejarPorForma(fRef, nombresRef, featsConts(piezas, empOffsets(emparejado, talle)))
      }
    }
    if (talle !== talleRef) eleccion = aplicarFijos(eleccion, empFijos(emparejado, talle), piezas.length)
    const usados = new Set([...eleccion.values()].map(([j]) => j))
    const sobra = []
    for (let i = 0; i < piezas.length; i++) if (!usados.has(i)) sobra.push(i)
    pzsTalle.set(talle, piezas)
    sobraTalle.set(talle, sobra)
    if (sobra.length) {
      sobrantesPorTalle.set(talle, sobra.map((i) => ({ idx: i, w_cm: pyRound(piezas[i].w / CM, 1), h_cm: pyRound(piezas[i].h / CM, 1) })))
    }
    for (const [nom, [j]] of eleccion) anotar(nom, talle, piezas[j], j)
  }

  // 2ª pasada: las piezas que existen en otros talles pero no en el de referencia
  const conSobra = new Map()
  for (const [t, idxs] of sobraTalle) if (idxs.length) conSobra.set(t, idxs)
  if (conSobra.size) {
    const t0 = pyMax([...conSobra.keys()], (t) => conSobra.get(t).length)
    const extras = new Map()
    conSobra.get(t0).forEach((i, k) => {
      let nom = `Pieza extra ${k + 1}`
      while (registro.has(nom) || extras.has(nom)) nom += "'"
      extras.set(nom, i)
    })
    for (const [nom, i] of extras) anotar(nom, t0, pzsTalle.get(t0)[i], i)
    const f0 = featsConts(conSobra.get(t0).map((i) => pzsTalle.get(t0)[i]), empOffsets(emparejado, t0))
    const pos0 = new Map([...extras.keys()].map((nom, k) => [nom, k]))
    for (const [t, idxs] of conSobra) {
      if (t === t0) continue
      const ft = featsConts(idxs.map((i) => pzsTalle.get(t)[i]), empOffsets(emparejado, t))
      let el
      try { el = emparejarPorForma(f0, pos0, ft) } catch { el = new Map() }
      for (const [nom, [j]] of el) {
        if (j >= idxs.length) continue
        anotar(nom, t, pzsTalle.get(t)[idxs[j]], idxs[j])
      }
    }
    sobrantesPorTalle = new Map()                  // ya no queda nada sin cargar
  }

  const talles = ordenarPorArchivo(molde, tallesMesas.keys())
  const completos = talles.filter((t) => [...registro.values()].every((p) => p.has(t)))
  const piezasDetalle = new Map()
  for (const [pieza, porTalle] of registro) {
    const mayor = pyMax([...porTalle.values()], (v) => v.h_cm)
    piezasDetalle.set(pieza, { mesas: [mesa], talles: ordenarPorArchivo(molde, porTalle.keys()),
      talle_mayor_cm: { w: mayor.w_cm, h: mayor.h_cm } })
  }
  const faltantes = new Map()
  for (const t of talles) {
    if (excl.has(t)) continue
    const f = pySortedStr([...registro.keys()].filter((p) => !registro.get(p).has(t)))
    if (f.length) faltantes.set(t, f)
  }
  return { mesas: molde.n, talles, piezas: pySortedStr([...registro.keys()]), completos, registro, problemas,
    advertencias, piezas_detalle: piezasDetalle, faltantes_por_talle: faltantes,
    sobrantes_por_talle: sobrantesPorTalle, excluidos: pySortedStr([...excl]) }
}

// ─── JSON con el orden de Python ─────────────────────────────────────────────────────────────
/** El JSON de un resultado respetando el orden de inserción de los `Map` (ver el encabezado). */
export function aTextoJSON(v) {
  if (v === null || v === undefined) return 'null'
  if (typeof v === 'number') return Number.isFinite(v) ? JSON.stringify(v) : 'null'
  if (typeof v === 'string' || typeof v === 'boolean') return JSON.stringify(v)
  if (v instanceof Map) return '{' + [...v].map(([k, x]) => JSON.stringify(String(k)) + ':' + aTextoJSON(x)).join(',') + '}'
  if (v instanceof Set) return aTextoJSON([...v])
  if (Array.isArray(v)) return '[' + v.map(aTextoJSON).join(',') + ']'
  return '{' + Object.entries(v).map(([k, x]) => JSON.stringify(k) + ':' + aTextoJSON(x)).join(',') + '}'
}

// ─── todo lo que el paquete necesita, en un gesto ────────────────────────────────────────────
/**
 * Lo que hoy hace `servidor._procesar_molde_subido` con un molde sin diseño, para armar el paquete
 * `alta_a` (`paquete/armar.js: armarPaqueteCaminoA`): el alta por etiquetas, la detección del visor
 * (automática, por talle y el lienzo TODAS) y, si el molde vino de un DXF con nombres de pieza,
 * el alta manual con esos nombres — sólo para moldes chicos (≤ 25 nombres), como el servidor.
 * `dxf` = el resumen del DXF (`{archivo, talles, nombres, indices…}`) o null.
 * Devuelve `{alta, deteccion: {auto, porTalle: Map, todas}, dxf, talles}`. Las detecciones que
 * fallan (un talle sin piezas) se omiten: el servidor las calcula cuando se las pidan.
 */
export function prepararCaminoA(molde, { nombresDxf = null, indices = null, emparejado = null, dxf = null } = {}) {
  let alta = altaPlantilla(molde)
  const deteccion = { auto: null, porTalle: new Map(), todas: null }
  try { deteccion.auto = detectarPiezas(molde) } catch { deteccion.auto = null }
  const talles = deteccion.auto ? deteccion.auto.talles : alta.talles
  for (const t of talles) {
    try { deteccion.porTalle.set(t, detectarPiezas(molde, t)) } catch { /* ese talle no da piezas */ }
  }
  try { deteccion.todas = detectarPiezasTodas(molde) } catch { deteccion.todas = null }
  const dxfMan = dxf ? { ...dxf } : null
  const lista = nombresDxf || (dxf && dxf.nombres) || []
  const conNombre = lista.filter((n) => pyStrip(String(n)))
  if (conNombre.length && conNombre.length <= 25 && deteccion.auto) {
    const det = deteccion.auto
    const asign = []
    for (let i = 0; i < Math.min(det.piezas.length, lista.length); i++) {
      if (pyStrip(String(lista[i]))) asign.push({ idx: i, nombre: lista[i] })
    }
    try {
      const manual = asign.length ? altaPlantillaManual(molde, asign, det.mesa, det.talle_ref, indices, emparejado) : null
      if (manual && manual.registro.size) {
        alta = manual
        if (dxfMan) dxfMan.nombres_aplicados = pySortedStr([...manual.registro.keys()])
      }
    } catch { /* como el servidor: si el auto-nombrado falla, el alta queda por etiquetas */ }
  } else if (conNombre.length && dxfMan) {
    dxfMan.nombres_pendientes = conNombre.length      // molde grande: se nombra en Modelos
  }
  return { alta, deteccion, dxf: dxfMan, talles }
}
