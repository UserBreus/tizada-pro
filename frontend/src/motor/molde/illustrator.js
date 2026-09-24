// LA PLANTILLA ARMADA DIRECTO EN ILLUSTRATOR — 2026-09-23.
//
// Pedido del usuario: «en vez de descargar un archivo, que el sistema se conecte con una extensión
// de Illustrator y cree las mesas de trabajo, las capas, las guías y el acomodo». La extensión
// (`extension_illustrator/`, CEP) escucha en esta misma PC (`127.0.0.1:47850`); el navegador le
// pasa un PLAN ya calculado acá y ella sólo dibuja. Nada pasa por el servidor.
//
// 🔴 POR QUÉ UNA MESA POR PIEZA: el motor lee el arte MESA POR MESA (cada mesa de trabajo es una
// página del PDF) y la asigna a la pieza por el NOMBRE que tiene como texto vivo en la capa
// «guias» (`motor_pedido._texto_mesa` / `mapeo_por_nombre`); el tamaño de la mesa es la CAJA DEL
// DISEÑO (la medida que cubre todos los talles, `medidas_diseno`). La guía .ai de siempre traía
// todas las piezas en UNA sola mesa y el diseñador tenía que armar las mesas a mano: acá salen
// hechas, con el nombre exacto que el motor espera (`#talle` / `#rango` + el nombre de la pieza).
// 🔴 UNA MESA POR PIEZA, AUNQUE SE LLAMEN IGUAL (regla del usuario 2026-09-23: «por más que se
// llamen igual, una pieza no debe compartir mesa con otra»).
// 🔴 EL NOMBRE DE LA MESA ES EL QUE ENTIENDE EL SISTEMA: el GENÉRICO, sin el número («Frente», no
// «Frente 2»; regla del usuario 2026-09-23, y el motor lee siempre por genérico: `_match_piezas`),
// con `#talle` / `#rango` según el modo. Consecuencia del motor (`mapeo_por_nombre`): si varias
// mesas se llaman igual, la PRIMERA cubre a todas las piezas de ese nombre → se AVISA.
// ⚠️ NO agrandar las mesas del mismo nombre para que «sirvan para todas» (se probó en la 1.10.0):
// con todas las variables hay 11 «Cuello» de formas muy distintas (uno alto y angosto, otro de
// 66 × 3,6 cm) y la mesa del angosto quedaba de más de 3 m: todo gigante y el texto fuera del
// lienzo → Illustrator tiraba «PARM». Cada mesa = la caja de SU pieza (apta para los talles del
// modo: default = todos, rango = los del rango, talle = ese talle).
import { EDITABLES_GUIA, normNom } from './herramientas.js'

export const PUERTO_ILLUSTRATOR = 47850
/**
 * La versión de la extensión que corresponde a ESTE sistema (la del servidor: la sube sola
 * `extension_illustrator/construir.py` en cada cambio) → `{version, instalador}`. Una vez por página.
 */
let _versionServidor = null
export function versionDelServidor(rutaApi = (x) => x) {
  if (!_versionServidor) {
    _versionServidor = fetch(rutaApi('/api/illustrator/version')).then((r) => (r.ok ? r.json() : {})).catch(() => ({}))
  }
  return _versionServidor
}
const BASE = `http://127.0.0.1:${PUERTO_ILLUSTRATOR}`

// El tope del lienzo de Illustrator es 16383 pt (227"). Un molde entero a tamaño real ya mide eso
// (medido: el de la camiseta, 34 piezas, 15.935 × 13.869 pt = 5,6 × 4,9 m), así que el tope es el
// real menos un margen, y la extensión CENTRA el dibujo en el lienzo (ver `tizada.jsx`): armarlo
// desde una esquina lo sacaba del lienzo y Illustrator fallaba con «PARM».
const TOPE_LIENZO = 16200
const MARG = 36, GAP = 36
// alto (medida real, pt) que se deja arriba de cada talle para su título «TALLE S»: grande, que
// se lea de lejos (pedido del usuario 2026-09-23: «algo que diferencie cada talle»)
const TITULO_TALLE = 150
// entre un talle y otro (medida real, pt): bastante más que entre mesas, que no se amontonen
const GAP_BLOQUE = 200
// el RECUADRO de cada talle: cuánto se separa de sus mesas (menos que el margen y que medio
// `GAP_BLOQUE`: nunca toca una mesa ni el recuadro de otro talle ni se sale del lienzo)
const PAD_BLOQUE = 30
// el CARTEL DE ESCALA (sólo si el archivo no es a tamaño real): una franja ARRIBA de todo, sin
// mesas, con «ARCHIVO A ESCALA 40% (1:2,5)» GRANDE y en vector. La letra va en medidas del archivo
// (no se achica con la escala: tiene que leerse): ~5 % del ancho de lo armado, entre estos topes.
const LETRA_ESCALA_MIN = 40, LETRA_ESCALA_MAX = 220
// Illustrator no admite más de 1000 mesas de trabajo por documento
export const TOPE_MESAS = 1000
// los porcentajes que se ofrecen (100 % … 10 %, de 10 en 10; pedido del usuario 2026-09-23)
export const PORCENTAJES = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]
// el lado del lienzo de Illustrator en metros (lo que se muestra al recomendar)
export const LIENZO_M = +(TOPE_LIENZO / 72 * 2.54 / 100).toFixed(2)

/**
 * ¿Hay un Illustrator con la extensión de USER PRO abierto en esta PC? → `{version, illustrator}`
 * o `null`. La primera vez Chrome pregunta «permitir» (es esta misma PC) y la pregunta queda
 * esperando al usuario: por eso la espera por defecto es LARGA (alguien mayor tarda en leer el
 * cartel). Si no hay nada escuchando, la respuesta es inmediata igual (conexión rechazada).
 */
export async function buscarIllustrator(esperaMs = 60000) {
  const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const t = ctl ? setTimeout(() => ctl.abort(), esperaMs) : null
  try {
    const r = await fetch(`${BASE}/estado`, { signal: ctl ? ctl.signal : undefined, cache: 'no-store' })
    if (!r.ok) return null
    const d = await r.json().catch(() => null)
    return d && d.app === 'TIZADA PRO' ? d : null
  } catch {
    return null
  } finally {
    if (t) clearTimeout(t)
  }
}

/** Le pasa el plan a la extensión. Devuelve `{ok, mesas}` o tira el error que contestó Illustrator. */
export async function enviarAIllustrator(plan) {
  const r = await fetch(`${BASE}/plantilla`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(plan),
  })
  const d = await r.json().catch(() => ({}))
  if (!r.ok || !d.ok) throw new Error(d.error || `Illustrator contestó ${r.status}`)
  return d
}

const f2 = (v) => (Math.round(v * 100) / 100).toString()

/** Los tramos de `segs` como sub-caminos de Illustrator: `[[x, y, izqX, izqY, derX, derY], …]`. */
function subcaminos(segs, T) {
  const subs = []
  let cur = null
  const nuevo = () => { cur = { p: [], c: false }; subs.push(cur) }
  const punto = ([x, y]) => { cur.p.push([x, y, x, y, x, y]) }
  for (const s of segs || []) {
    const op = s[0]
    if (op === 'm') { nuevo(); punto(T(s[1], s[2])) }
    else if (op === 'l') { if (!cur) nuevo(); punto(T(s[1], s[2])) }
    else if (op === 'c') {
      if (!cur || !cur.p.length) { nuevo(); punto(T(s[5], s[6])); continue }
      const a = T(s[1], s[2]), b = T(s[3], s[4]), e = T(s[5], s[6])
      const u = cur.p[cur.p.length - 1]
      u[4] = a[0]; u[5] = a[1]                     // la manija de SALIDA del punto anterior
      cur.p.push([e[0], e[1], b[0], b[1], e[0], e[1]])   // y la de LLEGADA del nuevo
    } else if (op === 're') {
      const [x, y, w, h] = [s[1], s[2], s[3], s[4]]
      nuevo(); punto(T(x, y)); punto(T(x + w, y)); punto(T(x + w, y + h)); punto(T(x, y + h)); cur.c = true
    } else if (op === 'h') { if (cur) cur.c = true }
  }
  // un camino que termina donde empezó es CERRADO: el último punto se funde con el primero (si no,
  // Illustrator muestra dos puntos encimados en el cierre)
  for (const sp of subs) {
    const p = sp.p
    if (p.length > 2) {
      const a = p[0], z = p[p.length - 1]
      if (Math.abs(a[0] - z[0]) < 0.01 && Math.abs(a[1] - z[1]) < 0.01) {
        a[2] = z[2]; a[3] = z[3]; p.pop(); sp.c = true
      }
    }
  }
  return subs.filter((sp) => sp.p.length > 1)
}

function dSvg(subs) {
  const out = []
  for (const sp of subs) {
    const p = sp.p
    out.push(`M${f2(p[0][0])} ${f2(p[0][1])}`)
    const n = sp.c ? p.length + 1 : p.length
    for (let i = 1; i < n; i++) {
      const a = p[i - 1], b = p[i % p.length]
      const recta = a[4] === a[0] && a[5] === a[1] && b[2] === b[0] && b[3] === b[1]
      out.push(recta ? `L${f2(b[0])} ${f2(b[1])}`
        : `C${f2(a[4])} ${f2(a[5])} ${f2(b[2])} ${f2(b[3])} ${f2(b[0])} ${f2(b[1])}`)
    }
    if (sp.c) out.push('Z')
  }
  return out.join('')
}

/**
 * El PLAN que dibuja la extensión, con la MISMA geometría que la guía .ai (`aiGuiaMedidas`):
 * `capasData` = lo que devuelve `/api/plantilla/pdf_guia?datos=1&formato=ai`.
 *
 * Coordenadas en puntos, origen arriba a la izquierda y la «y» hacia ABAJO (la extensión las pasa
 * a las de Illustrator). Capas de abajo hacia arriba: diseño · editables · personalización · guias.
 *
 * `escala` = N para armar a 1:N (2026-09-23): TODO se achica igual —las mesas, el contorno, las
 * distancias entre mesas y los márgenes—, así un arte a escala entra con todos los talles en UN
 * archivo. Por talle, cada talle es un BLOQUE con su título («TALLE S») arriba, fuera de las mesas,
 * y los bloques se acomodan en grilla sin mezclarse.
 * → `{plan, avisos}`.
 */
export function planIllustrator(capasData, { config = 'default', rango = [], titulo = 'Molde', capas = null, editables = null, archivo = null, referencia = 'alto', posiciones = null, talleVisor = null, escala = 1, soloMedir = false, acomodoGuia = null, soloGuia = false } = {}) {
  if (!capasData || !capasData.length) throw new Error('no se detectaron piezas en la plantilla')
  const avisos = []
  const esc = Number(escala) > 0 ? Number(escala) : 1
  const s = 1 / esc                                   // de medida real a la del archivo

  // ── las capas (mismos nombres y colores que la guía .ai) ──
  const RESERVADAS = new Set(['molde', 'guia', 'guias'])
  const pers = []
  let diseno = null
  for (let nc of (capas || [])) {
    nc = String(nc).trim()
    if (!nc || RESERVADAS.has(nc.toLowerCase())) continue
    if (normNom(nc) === 'diseno') diseno = nc
    else if (normNom(nc).includes('editable')) continue          // «editable» en cualquier parte (`esCapaEditable`)
    else pers.push(nc)
  }
  const eds = (editables !== null && editables !== undefined ? editables : EDITABLES_GUIA).map((e) => String(e).trim()).filter(Boolean)
  const listaCapas = [{ nombre: diseno || 'diseño', color: [128, 128, 128], bloqueada: false }]
  for (const ed of eds) listaCapas.push({ nombre: ed, color: [255, 170, 60], bloqueada: false })
  for (const nc of pers) listaCapas.push({ nombre: nc, color: [190, 120, 255], bloqueada: false })
  const iGuias = listaCapas.length
  listaCapas.push({ nombre: 'guias', color: [52, 211, 153], bloqueada: true })

  // ── UNA MESA POR PIEZA: su caja del diseño, en el lugar de la pieza en el molde ──
  // VARIOS RANGOS (pedido del usuario 2026-09-23: «crear varios rangos antes de crear el Illustrator
  // para que cree el archivo con todos»): cada bloque de `capasData` trae SU `rango` (la pantalla
  // pide uno por rango y los junta); sin eso, el rango de siempre (`rango`).
  const multiRango = config === 'rango' && capasData.some((b) => Array.isArray(b.rango) && b.rango.length)
  const nombreMesa = (pieza, talle, rangoB) => {
    // el número del final es de la PIEZA, no del arte: el sistema no lo usa para asignar
    const gen = String(pieza).replace(/\s+\d+\s*$/, '').trim() || String(pieza).trim()
    const rr = rangoB && rangoB.length ? rangoB : rango
    if (config === 'talle' && talle) return `#${talle} ${gen}`
    if (config === 'rango' && rr && rr.length) return `#${rr[0]}-${rr[rr.length - 1]} ${gen}`
    return gen
  }
  const grupos = []                    // por talle: [{nombre, w, h, items:[la pieza], cx, cy}]
  const tallesGrupos = []              // el talle de cada grupo (mismo orden)
  const rangosGrupos = []              // con varios rangos: el rango de cada grupo
  let sinNombre = 0
  // sin «por talle» sólo cuenta el primer bloque (igual que la guía .ai); por talle —y con varios
  // rangos—, todos
  const bloques = config === 'talle' || multiRango ? capasData : [capasData[0]]
  for (const cd of bloques) {
    const g = []
    for (const it of cd.items || []) {
      // una pieza SIN nombre también tiene su mesa (se arma todo, como se ve en el sistema), pero el
      // sistema no la va a reconocer hasta que se nombre: se avisa
      let nm
      if (it.nombre) nm = nombreMesa(it.nombre, cd.talle, cd.rango)
      else { sinNombre++; nm = `Sin nombre ${sinNombre}` }
      g.push({ nombre: nm, w: it.wC || 0, h: it.hC || 0, items: [it], cx: it.ccx, cy: it.ccy })
    }
    if (g.length) { grupos.push(g); tallesGrupos.push(cd.talle); rangosGrupos.push(cd.rango && cd.rango.length ? cd.rango : rango) }
  }
  // cada mesa donde el VISOR dibuja su pieza (si la pantalla lo mandó)
  void referencia
  aplicarPosicionesDelVisor(grupos, tallesGrupos, posiciones, talleVisor)
  // cada mesa con su `ref` (a qué mesa del GUÍA corresponde): la del visor si la hay; si no, el
  // nombre + su número entre las del mismo nombre en orden de lectura (igual en todos los talles)
  for (const g of grupos) {
    const vistos = new Map()
    const orden = g.filter((m) => !m.ref).sort((a, b) => (b.cy - a.cy) || (a.cx - b.cx))
    for (const m of orden) {
      const n = m.items[0].nombre || m.nombre      // el de la PIEZA (sin el #talle)
      const k = vistos.get(n) || 0
      vistos.set(n, k + 1)
      m.ref = `${n}@${k}`
    }
  }
  const repetidos = mismoNombre(grupos)
  if (repetidos.length) {
    const ej = repetidos.slice(0, 3).map(([n, c]) => `«${n}» ×${c}`).join(', ')
    avisos.push(`Hay mesas con el mismo nombre (${ej}${repetidos.length > 3 ? '…' : ''}): al subir el arte, el sistema usa la PRIMERA de cada nombre para todas esas piezas. Para un diseño distinto en cada una, mandá de a una variable.`)
  }
  if (sinNombre) avisos.push(`${sinNombre} pieza${sinNombre === 1 ? '' : 's'} sin nombre («Sin nombre N»): el sistema no ${sinNombre === 1 ? 'la' : 'las'} va a reconocer en el arte hasta que ${sinNombre === 1 ? 'la' : 'las'} nombres.`)
  if (!grupos.length) throw new Error('no se detectaron piezas en la plantilla')

  // ── el acomodo: COMO ESTÁ EN EL MOLDE (pedido del usuario 2026-09-23: «que TIZADA le diga la
  // ubicación de cada mesa como está acomodada una con otra») ──
  // El acomodo se calcula en medida REAL y después se achica entero por la escala: así las
  // distancias entre mesas y entre talles quedan en la misma proporción que las piezas. El tope del
  // lienzo, visto en medida real, crece con la escala (a 1:5 entra 5 veces más).
  const porTalle = config === 'talle'
  // por talle y por rango cada bloque lleva su TÍTULO y su RECUADRO (default no: es uno solo)
  const conBloques = porTalle || (config === 'rango' && rango && rango.length > 0)
  const tit = conBloques ? TITULO_TALLE : 0           // lugar para el título de cada talle
  const tope = TOPE_LIENZO / s
  // 🔴 El acomodo del molde se mide SIN tope: antes, si a tamaño real pasaba el lienzo, se caía
  // directo a «en filas» —un talle por fila— y 31 talles quedaban en una columna de 38 m (la
  // escala recomendada daba 10 % cuando la grilla entraba mucho más grande). Las filas sólo si el
  // del molde no entra Y las filas quedan más chicas.
  const giGuia = Math.max(0, talleVisor != null ? tallesGrupos.indexOf(talleVisor) : 0)
  // `soloGuia`: las mesas del talle GUÍA como quedan (a mano si se acomodaron, si no automático),
  // en medida real — lo que muestra el editor «Acomodar mesas» para acomodarlas a mano
  if (soloGuia) {
    const r = acomodoDelMolde([grupos[giGuia]], Infinity, 0, 0, acomodoGuia)
    if (!r) return []
    return r.mesas.map((m) => ({ ref: m.ref, nombre: m.nombre, x: m.x, y: m.y, w: m.w, h: m.h }))
  }
  let acomodo = acomodoDelMolde(grupos, Infinity, tit, giGuia, acomodoGuia)
  if (!acomodo || Math.max(acomodo.W, acomodo.H) > tope) {
    const filas = acomodoEnFilas(grupos, tope, tit)
    if (!acomodo || Math.max(filas.W, filas.H) < Math.max(acomodo.W, acomodo.H)) {
      acomodo = filas
      avisos.push('Con el acomodo del molde las mesas no entraban en Illustrator: se acomodaron en filas.')
    }
  }
  const nTotal = grupos.reduce((n, g) => n + g.length, 0)
  // 🔴 A ESCALA, EL ARCHIVO LO DICE (pedido del usuario 2026-09-24: «un texto pasado a curvas cuando
  // es a escala, en un espacio que no tenga mesa de trabajo, que diga a qué escala es el archivo»
  // y después: «debe aparecer GRANDE en la parte SUPERIOR»): una franja ARRIBA de todo, fuera de
  // toda mesa, con el cartel en vector; todo lo demás baja lo que mide la franja (`dyCartel`).
  // Cuenta para el tamaño del lienzo (también al medir/recomendar).
  const conCartel = esc > 1.0001
  const pctCartel = Math.round(100 / esc)
  const txtCartel = `ARCHIVO A ESCALA ${pctCartel}% (1:${String(Math.round(esc * 100) / 100).replace('.', ',')})`
  let letraCartel = 0
  if (conCartel) {
    const anchoArmado = acomodo.W * s - 2 * MARG * s
    // grande (5 % del ancho) pero que entre a lo ancho de lo armado; nunca menos que el mínimo
    letraCartel = Math.max(LETRA_ESCALA_MIN, Math.min(LETRA_ESCALA_MAX, acomodo.W * s * 0.05,
      anchoArmado / (0.62 * txtCartel.length)))
  }
  const dyCartel = conCartel ? letraCartel * 1.8 : 0
  const anchoCartel = conCartel ? letraCartel * 0.62 * txtCartel.length + 2 * MARG * s : 0
  const W0 = Math.max(acomodo.W * s, anchoCartel)
  const H0 = acomodo.H * s + dyCartel
  // `soloMedir`: ¿entra en UN documento de Illustrator? (para recomendar; ver `recomendarIllustrator`)
  if (soloMedir) {
    const entra = Math.max(W0, H0) <= TOPE_LIENZO     // entra en el ESPACIO
    return { cabe: entra && nTotal <= TOPE_MESAS, entra, W: W0, H: H0, nMesas: nTotal }
  }
  if (Math.max(W0, H0) > TOPE_LIENZO) {
    throw new Error(`las mesas no entran en el lienzo de Illustrator (227"). ${porTalle ? 'Elegí menos talles o una escala más chica' : 'Elegí una VARIABLE para armar solo sus piezas, o una escala más chica'}.`)
  }
  if (nTotal > TOPE_MESAS) {
    throw new Error('son más de 1000 mesas y Illustrator no admite más en un archivo. Elegí menos talles o una variable.')
  }
  const mesas = acomodo.mesas.map((m) => ({ ...m, x: m.x * s, y: m.y * s + dyCartel, w: m.w * s, h: m.h * s }))
  const W = W0, H = H0

  // ── lo que se dibuja: el contorno de cada pieza centrado en su mesa (como GUÍA de Illustrator),
  // su nombre como TEXTO arriba a la izquierda, y el FONDO rojo clarito de cada mesa en «diseño» ──
  const caminos = []
  const textos = []
  const fondos = []
  const svg = []
  for (const m of mesas) {
    const mx = m.x + m.w / 2, my = m.y + m.h / 2
    for (const it of m.items) {
      // canvas (y hacia arriba, centro de la caja en ccx/ccy) → lienzo (y hacia abajo, centro en la mesa)
      const T = (cx, cy) => [mx + (cx - it.ccx) * s, my - (cy - it.ccy) * s]
      const subs = subcaminos(it.segs, T)
      if (!subs.length) continue
      caminos.push({ capa: iGuias, sub: subs, ancho: 1, color: [0, 0, 0, 100] })
      // un <path> por sub-camino: así cada uno entra a Illustrator como un trazado suelto que se
      // puede volver GUÍA (un trazado compuesto no puede)
      for (const sp of subs) svg.push(`<path d="${dSvg([sp])}"/>`)
    }
    // el nombre de la mesa como TEXTO VIVO en «guias», arriba a la izquierda DENTRO de la mesa: es
    // lo que lee el motor para saber de qué pieza es (tiene que quedar adentro de la mesa)
    // (a escala el mínimo baja con ella: un texto de 8 pt no entra en una mesa de 1:10)
    const tam = Math.max(Math.max(3, 8 * s), Math.min(28, Math.min(m.w, m.h) / 12))
    const pad = Math.max(4 * s, tam * 0.5)
    textos.push({ capa: iGuias, t: m.nombre, x: m.x + pad, y: m.y + pad + tam * 0.8, tam })
    // el fondo de la mesa, ROJO CLARITO (pedido del usuario 2026-09-23; antes gris 0/0/0/10), en
    // «diseño» (la capa de abajo de todo). CMYK 0/25/15/0.
    fondos.push({ capa: 0, rect: [m.x, m.y, m.x + m.w, m.y + m.h], color: [0, 25, 15, 0] })
  }
  // 🔴 CADA TALLE SE DISTINGUE (pedido del usuario 2026-09-23: «cuando es talle por talle o rango
  // debe haber algo que diferencie cada talle y no esté todo amontonado»): su TÍTULO grande
  // («TALLE S» / «RANGO XS–L») y un RECUADRO alrededor de sus mesas, los dos en «guias» y FUERA de
  // toda mesa (lo que está fuera de una mesa el motor no lo lee: no se confunde con una pieza).
  // El recuadro va como guía, igual que los contornos.
  if (conBloques) {
    (acomodo.titulos || []).forEach((p, i) => {
      if (porTalle && tallesGrupos[i] == null) return
      const rr = rangosGrupos[i] || rango || []
      const rot = porTalle ? `TALLE ${tallesGrupos[i]}` : `RANGO ${rr[0]}${rr.length > 1 ? '–' + rr[rr.length - 1] : ''}`
      const tamT = Math.max(4, TITULO_TALLE * 0.55 * s)
      // `vector`: la extensión lo pasa a CONTORNOS (pedido del usuario 2026-09-23): texto vivo sólo
      // son los nombres de las mesas, lo que lee el sistema al subir el arte
      textos.push({ capa: iGuias, t: rot, x: p.x * s, y: (p.y - TITULO_TALLE * 0.3) * s + dyCartel, tam: tamT, vector: true })
      const c = acomodo.cajas && acomodo.cajas[i]
      if (!c) return
      const x0 = (c.x - PAD_BLOQUE) * s, y0 = (c.y - TITULO_TALLE * 0.9) * s + dyCartel
      const x1 = (c.x + c.w + PAD_BLOQUE) * s, y1 = (c.y + c.h + PAD_BLOQUE) * s + dyCartel
      const sub = [{ p: [[x0, y0, x0, y0, x0, y0], [x1, y0, x1, y0, x1, y0], [x1, y1, x1, y1, x1, y1], [x0, y1, x0, y1, x0, y1]], c: true }]
      caminos.push({ capa: iGuias, sub, ancho: 1, color: [0, 0, 0, 100] })
      svg.push(`<path d="${dSvg(sub)}"/>`)
    })
  }
  if (conCartel) {
    // arriba de todo: la línea base en el 75 % de la franja (las mayúsculas quedan adentro)
    textos.push({ capa: iGuias, t: txtCartel, x: MARG * s, y: dyCartel * 0.75, tam: letraCartel, vector: true })
  }
  const aW = Math.ceil(W), aH = Math.ceil(H)
  const plan = {
    version: 1,
    titulo: String(titulo || 'Molde'),
    // con qué nombre se GUARDA el documento (molde + variable); la extensión le pone la carpeta
    archivo: String(archivo || titulo || 'Plantilla'),
    escala: esc,                                 // 1:N (sólo informativo: todo ya viene achicado)
    ancho: aW, alto: aH,
    capas: listaCapas,
    activa: 0,                                   // se termina parado en «diseño»
    mesas: mesas.map((m) => ({ nombre: m.nombre, rect: [m.x, m.y, m.x + m.w, m.y + m.h] })),
    caminos,
    textos,
    fondos,
    guias: true,                                 // los contornos, como GUÍAS de Illustrator
    // los contornos también como UN SVG: la extensión lo importa de una vez (mucho más rápido que
    // dibujar punto por punto en Illustrator); si esa importación falla, dibuja `caminos`.
    // `tizada_ref` = un rectángulo SIN relleno ni trazo del tamaño exacto del lienzo: con él la
    // extensión sabe dónde quedó lo importado y a qué escala (la caja de una curva no es la de sus
    // puntos, así que alinear por los contornos solos correría todo), y después lo borra.
    svg: caminos.length
      ? `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="${aW}" height="${aH}" viewBox="0 0 ${aW} ${aH}">` +
        `<rect id="tizada_ref" x="0" y="0" width="${aW}" height="${aH}" fill="none" stroke="none"/>` +
        `<g fill="none" stroke="#000000" stroke-width="1">${svg.join('')}</g></svg>`
      : null,
  }
  return { plan, avisos, nMesas: mesas.length }
}

/**
 * Cuánto hay que AGRANDAR el acomodo (cada eje por su lado) para que ninguna caja de `g` toque a
 * otra. Los pares que se pisan se resuelven separando en X (kx ≥ nx/dx) O en Y (ky ≥ ny/dy); se
 * elige la combinación (kx, ky) que deja el lienzo más chico: agrandar parejo en las dos
 * direcciones llevaba un molde de 34 piezas a 15.935 × 13.869 pt, pegado al tope de Illustrator
 * (16.383), y ahí Illustrator falla («PARM») con lo que cae en el borde. → `{kx, ky}` o `null` si
 * dos piezas están en el mismo lugar exacto (no hay agrandado que las separe).
 */
function agrandado(g) {
  const pares = []
  for (let i = 0; i < g.length; i++) {
    for (let j = i + 1; j < g.length; j++) {
      const a = g[i], b = g[j]
      const dx = Math.abs(a.cx - b.cx), dy = Math.abs(a.cy - b.cy)
      const nx = (a.w + b.w) / 2 + GAP, ny = (a.h + b.h) / 2 + GAP
      if (dx >= nx || dy >= ny) continue                 // ya no se tocan
      const rx = dx > 0.5 ? nx / dx : Infinity, ry = dy > 0.5 ? ny / dy : Infinity
      if (!isFinite(rx) && !isFinite(ry)) return null    // mismo lugar exacto
      pares.push([rx, ry])
    }
  }
  const spanX = Math.max(...g.map((m) => m.cx)) - Math.min(...g.map((m) => m.cx))
  const spanY = Math.max(...g.map((m) => m.cy)) - Math.min(...g.map((m) => m.cy))
  const maxW = Math.max(...g.map((m) => m.w)), maxH = Math.max(...g.map((m) => m.h))
  let kx = 1, ky = 1, mejor = Infinity
  const candidatos = [1, ...pares.map((q) => q[0]).filter((v) => isFinite(v))]
  for (const cx of candidatos) {
    let cy = 1
    for (const [rx, ry] of pares) if (rx > cx + 1e-9) cy = Math.max(cy, ry)
    if (!isFinite(cy)) continue
    const area = (spanX * cx + maxW) * (spanY * cy + maxH)
    if (area < mejor) { mejor = area; kx = cx; ky = cy }
  }
  return isFinite(mejor) ? { kx, ky } : null
}

/**
 * LAS MESAS DE UN TALLE CON LAS SEPARACIONES DEL GUÍA. `G` = la caja de cada mesa en el acomodo
 * del talle guía (x, y, w, h; «y» hacia abajo); `W`/`H` = el tamaño de cada mesa en ESTE talle.
 * Entre dos mesas vecinas del guía (una a la izquierda de la otra —o arriba— y enfrentadas) queda
 * la MISMA distancia de borde a borde que en el guía: si una crece, empuja a las que siguen, y si
 * achica, se acercan. Con los tamaños del guía reproduce el guía exacto. Si dos que en el guía no
 * eran vecinas (en diagonal) llegaran a tocarse por crecer, se separan en el eje en que el guía
 * las tenía más lejos. → `{X, Y}` (la esquina de cada mesa).
 */
function copiarSeparaciones(G, W, H) {
  const n = G.length
  const extra = { x: [], y: [] }
  const resolver = (eje, S) => {
    const st = (i) => (eje === 'x' ? G[i].x : G[i].y)
    const en = (i) => st(i) + (eje === 'x' ? G[i].w : G[i].h)
    const o0 = (i) => (eje === 'x' ? G[i].y : G[i].x)
    const o1 = (i) => o0(i) + (eje === 'x' ? G[i].h : G[i].w)
    const enfrentadas = (a, b) => Math.min(o1(a), o1(b)) - Math.max(o0(a), o0(b)) > 0.5
    const orden = [...Array(n).keys()].sort((a, b) => st(a) - st(b))
    const antes = (a, b) => a !== b && en(a) <= st(b) + 0.5 && enfrentadas(a, b)
    // 🔴 sólo la VECINA DIRECTA: si entre «a» y «b» hay otra mesa «c» enfrentada con las dos, la
    // distancia de «a» a «b» ya la dan a→c→b. Contarla también empujaba a «b» con la distancia
    // del guía entre a y b aunque «c» se hubiera achicado (medido: 13,05 cm donde el guía tiene
    // 7,76 en el talle más chico).
    const directa = (a, b) => antes(a, b) && !orden.some((c) => antes(a, c) && antes(c, b))
    const pos = new Array(n)
    const hecho = new Array(n).fill(false)
    for (const b of orden) {
      let mx = -Infinity
      for (let a = 0; a < n; a++) {
        if (a === b || !hecho[a]) continue
        const vecina = directa(a, b)
        const forzada = extra[eje].some(([p, q]) => p === a && q === b)
        if (!vecina && !forzada) continue
        const gap = st(b) - en(a)
        mx = Math.max(mx, pos[a] + S[a] + (gap >= 0 ? gap : GAP))
      }
      // sin vecina antes: se queda donde está en el guía
      pos[b] = mx > -Infinity ? mx : st(b)
      hecho[b] = true
    }
    return pos
  }
  let X = resolver('x', W), Y = resolver('y', H)
  for (let vuelta = 0; vuelta < 8; vuelta++) {
    let choque = false
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        if (!(X[i] < X[j] + W[j] - 0.01 && X[j] < X[i] + W[i] - 0.01 && Y[i] < Y[j] + H[j] - 0.01 && Y[j] < Y[i] + H[i] - 0.01)) continue
        choque = true
        const sx = Math.max(G[j].x - (G[i].x + G[i].w), G[i].x - (G[j].x + G[j].w))
        const sy = Math.max(G[j].y - (G[i].y + G[i].h), G[i].y - (G[j].y + G[j].h))
        if (sx >= sy) extra.x.push(G[i].x <= G[j].x ? [i, j] : [j, i])
        else extra.y.push(G[i].y <= G[j].y ? [i, j] : [j, i])
      }
    }
    if (!choque) break
    X = resolver('x', W); Y = resolver('y', H)
  }
  return { X, Y }
}

function acomodoDelMolde(grupos, tope = TOPE_LIENZO, tit = 0, gi = 0, aMano = null) {
  // 🔴 CADA TALLE ES UNA COPIA DEL TALLE GUÍA, CON SUS MISMAS SEPARACIONES (pedido del usuario
  // 2026-09-23: «si el talle guía es M y entre 2 mesas tiene una separación de 1 cm, en todos los
  // talles tendrá esa separación»). Primero se arma el GUÍA (las posiciones del visor, agrandadas
  // lo justo para que no se toquen); después cada talle pone SUS mesas —de otro tamaño— con las
  // distancias de BORDE A BORDE del guía (`copiarSeparaciones`). Copiar los centros no alcanzaba:
  // con mesas más grandes o más chicas, la separación entre bordes cambiaba.
  const guia = grupos[gi] || grupos[0]
  const kG = agrandado(guia)
  if (!kG) return null
  // las mesas que no están en el guía (otro talle con otra pieza) usan su propio lugar, agrandado
  // con el mayor de todos los talles para que no caigan encima de nada
  let kT = { ...kG }
  for (const g of grupos) {
    if (g === guia) continue
    const k = agrandado(g)
    if (!k) return null
    kT = { kx: Math.max(kT.kx, k.kx), ky: Math.max(kT.ky, k.ky) }
  }
  const cajaGuia = new Map()
  for (const m of guia) {
    // ACOMODADA A MANO (el editor «Acomodar mesas»): manda sobre la automática; su separación con
    // las vecinas es la que copian todos los talles
    const q = aMano && m.ref && aMano[m.ref]
    if (q && q.length === 4) cajaGuia.set(m.ref, { x: q[0], y: q[1], w: q[2], h: q[3] })
    else if (m.ref) cajaGuia.set(m.ref, { x: m.cx * kG.kx - m.w / 2, y: -m.cy * kG.ky - m.h / 2, w: m.w, h: m.h })
  }
  const bloques = []
  for (const g of grupos) {
    const G = g.map((m) => cajaGuia.get(m.ref) ||
      { x: m.cx * kT.kx - m.w / 2, y: -m.cy * kT.ky - m.h / 2, w: m.w, h: m.h })
    const { X, Y } = copiarSeparaciones(G, g.map((m) => m.w), g.map((m) => m.h))
    // el ORDEN de las mesas de trabajo = el de lectura del GUÍA (de arriba abajo, de izquierda a
    // derecha, por el centro de su caja en el guía): el mismo en todos los talles
    const idx = [...g.keys()]
    const fila = (i) => Math.round((G[i].y + G[i].h / 2) / (GAP * 2))
    idx.sort((a, b) => fila(a) - fila(b) || (G[a].x + G[a].w / 2) - (G[b].x + G[b].w / 2))
    const minX = Math.min(...X), minY = Math.min(...Y)
    const maxX = Math.max(...g.map((m, i) => X[i] + m.w)), maxY = Math.max(...g.map((m, i) => Y[i] + m.h))
    bloques.push({
      mesas: idx.map((i) => ({ ...g[i], x: X[i] - minX, y: Y[i] - minY })),
      w: maxX - minX, h: maxY - minY,
    })
  }
  return empaquetar(bloques, tope, tit)
}

/**
 * Los bloques (uno por talle) en GRILLA, en el orden de los talles: se prueba de 1 a N bloques por
 * fila y se queda la que deja el lienzo más cuadrado (el lado mayor más chico). Antes iban todos en
 * UNA fila: con varios talles el lienzo se iba de ancho mucho antes de llenarse. Cada bloque deja
 * arriba `tit` para su título; entre bloques, `GAP_BLOQUE` (que no parezcan del mismo talle).
 * → `{mesas, W, H, titulos: [{x, y}], cajas: [{x, y, w, h}]}` (dónde arranca cada bloque y lo que
 * ocupan sus mesas), o `null` si ni así entra en `tope`.
 */
function empaquetar(bloques, tope, tit) {
  const sep = tit ? GAP_BLOQUE : GAP * 3
  let mejor = null
  for (let k = 1; k <= bloques.length; k++) {
    let W = 0, y = MARG
    const lugares = []
    for (let i = 0; i < bloques.length; i += k) {
      let x = MARG, altoFila = 0
      for (const b of bloques.slice(i, i + k)) {
        lugares.push([x, y + tit])
        x += b.w + sep
        altoFila = Math.max(altoFila, b.h)
      }
      W = Math.max(W, x - sep + MARG)
      y += tit + altoFila + sep
    }
    const H = y - sep + MARG
    if (!mejor || Math.max(W, H) < Math.max(mejor.W, mejor.H)) mejor = { W, H, lugares }
  }
  if (!mejor || Math.max(mejor.W, mejor.H) > tope) return null
  const mesas = [], titulos = [], cajas = []
  bloques.forEach((b, i) => {
    const [x, y] = mejor.lugares[i]
    titulos.push({ x, y })
    cajas.push({ x, y, w: b.w, h: b.h })
    for (const m of b.mesas) mesas.push({ ...m, x: x + m.x, y: y + m.y })
  })
  return { mesas, W: mejor.W, H: mejor.H, titulos, cajas }
}

/**
 * Respaldo: en filas (cada talle arranca una fila nueva, con su título arriba). Sólo si el acomodo
 * del molde no entra. Se prueban varios anchos de fila y se queda el que deja el lienzo más
 * CUADRADO (el lado mayor más chico): un ancho fijo dejaba el mismo molde de 9.760 × 16.261 pt,
 * fuera del tope.
 */
function acomodoEnFilas(grupos, tope = TOPE_LIENZO, tit = 0) {
  const todas = grupos.flat()
  const maxW = Math.max(...todas.map((m) => m.w))
  let mejor = null
  // a escala el tope (en medida real) crece: el paso crece con él para no probar miles de anchos
  const paso = Math.max(50, maxW / 8, (tope - 2 * MARG) / 400)
  for (let lim = maxW; lim <= tope - 2 * MARG + 1; lim += paso) {
    const r = enFilas(grupos, lim, tit)
    if (!mejor || Math.max(r.W, r.H) < Math.max(mejor.W, mejor.H)) mejor = r
  }
  return mejor || enFilas(grupos, maxW, tit)
}

function enFilas(grupos, limiteFila, tit = 0) {
  const sep = tit ? GAP_BLOQUE : GAP
  let y = MARG, ancho = MARG
  const mesas = [], titulos = [], cajas = []
  for (const g of grupos) {
    y += tit
    titulos.push({ x: MARG, y })
    const y0 = y
    let x = MARG, altoFila = 0, anchoBloque = 0
    for (const m of g) {
      if (x > MARG && x + m.w > MARG + limiteFila) { x = MARG; y += altoFila + GAP; altoFila = 0 }
      mesas.push({ ...m, x, y })
      x += m.w + GAP; altoFila = Math.max(altoFila, m.h)
      ancho = Math.max(ancho, x - GAP)
      anchoBloque = Math.max(anchoBloque, x - GAP - MARG)
    }
    cajas.push({ x: MARG, y: y0, w: anchoBloque, h: y + altoFila - y0 })
    y += altoFila + sep
  }
  return { mesas, W: ancho + MARG, H: y - sep + MARG, titulos, cajas }
}

/** Los nombres de mesa que se repiten dentro de cada bloque (talle): [[nombre, cuántas]]. */
function mismoNombre(grupos) {
  const out = []
  for (const g of grupos) {
    const n = new Map()
    for (const m of g) if (!m.nombre.startsWith('Sin nombre ')) n.set(m.nombre, (n.get(m.nombre) || 0) + 1)
    for (const [nombre, c] of n) if (c > 1) out.push([nombre, c])
  }
  return out
}

/**
 * EL ACOMODO DEL VISOR. `posiciones` = {nombre de pieza: [{x, y}]} con el centro de cada pieza tal
 * como la dibuja el visor de la Plantilla (puntos reales, «y» hacia abajo), del talle que se está
 * viendo (`talleVisor`). Cada mesa de ese talle se pone EXACTAMENTE ahí —mismas ubicaciones y
 * distancias que en el sistema—. Las que el visor no tiene (otro talle en «por talle», una pieza
 * sin nombre) usan su posición del molde corrida lo mismo que las demás (la mediana de la
 * diferencia entre las dos posiciones de las piezas que están en ambos lados).
 * Las posiciones del molde (`ccx/ccy`) no alcanzaban: medido 2026-09-23, el visor y la geometría
 * de la guía no dan el mismo acomodo (el Cuello abajo en vez de arriba, el bloque del Frente más
 * lejos).
 */
function aplicarPosicionesDelVisor(grupos, talles, pos, talleVisor) {
  if (!pos || !Object.keys(pos).length || !grupos.length) return false
  const mediana = (a) => { const s = a.slice().sort((x, y) => x - y); return s[Math.floor(s.length / 2)] }
  // la corrida entre el molde y el visor de UN bloque, con las piezas que aparecen UNA sola vez en los dos
  const corrida = (g) => {
    const cuenta = new Map()
    for (const m of g) { const n = m.items[0].nombre; if (n) cuenta.set(n, (cuenta.get(n) || 0) + 1) }
    const dx = [], dy = []
    for (const m of g) {
      const n = m.items[0].nombre
      if (n && cuenta.get(n) === 1 && pos[n] && pos[n].length === 1) { dx.push(pos[n][0].x - m.cx); dy.push(pos[n][0].y + m.cy) }
    }
    return dx.length ? [mediana(dx), mediana(dy)] : null
  }
  let gi = talleVisor != null ? talles.indexOf(talleVisor) : -1
  if (gi < 0) gi = 0
  const base = corrida(grupos[gi]) || grupos.map(corrida).find(Boolean)
  if (!base) return false
  // 🔴 TODOS LOS TALLES CON EL ACOMODO DEL VISOR (pedido del usuario 2026-09-23: «no debe acomodar
  // como se ve el molde completo: debe acomodar como la variante elegida»). Antes sólo el talle del
  // visor tomaba esas posiciones y los demás quedaban donde están en el ARCHIVO del molde —con los
  // huecos de las piezas de otras variantes—. Ahora cada bloque (talle) usa la plantilla del visor
  // (mismo nombre = mismo lugar); cada uno con SU corrida, porque cada talle está en otro lugar del
  // archivo y el «más cercano» se busca desde ahí.
  grupos.forEach((gg) => {
    const [tx, ty] = corrida(gg) || base
    const usados = new Set()
    for (const m of gg) {
      const n = m.items[0].nombre
      let X = m.cx + tx, Y = -m.cy + ty
      if (n && pos[n]) {
        // si hay varias con ese nombre, la del visor más cercana que no se haya usado
        let mejor = -1, dist = Infinity
        pos[n].forEach((q, i) => {
          if (usados.has(n + '#' + i)) return
          const d = (q.x - X) ** 2 + (q.y - Y) ** 2
          if (d < dist) { dist = d; mejor = i }
        })
        if (mejor >= 0) { usados.add(n + '#' + mejor); X = pos[n][mejor].x; Y = pos[n][mejor].y; m.ref = n + '#' + mejor }
      }
      m.cx = X; m.cy = -Y                  // `acomodoDelMolde` trabaja con «y» hacia arriba
    }
  })
  return true
}

/**
 * ¿ENTRA EN ILLUSTRATOR? Y SI NO, QUÉ HACER (pedido del usuario 2026-09-23: «esto no puede pasar
 * más, así sean miles de mesas; en base al tamaño del espacio de Illustrator debe darte una
 * recomendación»). Un documento de Illustrator tiene un lienzo de ~5,7 m de lado y hasta 1000
 * mesas de trabajo. Con `porc` (el % elegido):
 *   · `cabe`: entra todo en UN archivo a ese % → se crea directo;
 *   · si no, `unArchivo` = el % MÁS GRANDE al que entra todo en un solo archivo (null si no hay:
 *     más de 1000 mesas no entran a ningún %), y `archivos` = cómo repartirlo al % elegido en
 *     varios archivos (por talles, en orden; un talle que solo no entra se parte en pedazos).
 * No decide nada: la pantalla muestra las opciones y el usuario elige.
 */
export function recomendarIllustrator(capasData, opts, porc) {
  const med = medir(capasData, opts, porc)
  if (med.cabe) return { cabe: true, med }
  // el % recomendado por ESPACIO (todo dentro del lienzo); si además son ≤ 1000 mesas, es UN archivo
  const reco = escalaRecomendada(capasData, opts)
  const unArchivo = reco.porc && reco.porc < porc && reco.med.cabe ? reco.porc : null
  // más de 1000 mesas: aunque entren en el espacio, van en varios archivos — al % recomendado
  const porEspacio = !unArchivo && reco.porc && reco.porc !== porc ? reco.porc : null
  return { cabe: false, med, unArchivo, reco,
           archivos: repartirEnArchivos(capasData, opts, porc),
           archivosEspacio: porEspacio ? repartirEnArchivos(capasData, opts, porEspacio) : null, porEspacio }
}

/**
 * LA ESCALA RECOMENDADA (pedido del usuario 2026-09-23: «que me recomiende en qué escala hacerlo:
 * todo debe entrar en el espacio de Illustrator»): el % MÁS GRANDE de `PORCENTAJES` al que todas
 * las mesas entran en el lienzo (`TOPE_LIENZO`). → `{porc, med, med100}`; `porc` null si ni al
 * 10 % entra. `med.cabe` falso con `porc` = entra en el espacio pero son más de 1000 mesas.
 */
export function escalaRecomendada(capasData, opts) {
  const med100 = medir(capasData, opts, 100)
  if (med100.entra) return { porc: 100, med: med100, med100 }
  // el tamaño es proporcional al %: se arranca por el que da la cuenta y se confirma midiendo
  // (el acomodo en filas de respaldo puede cambiar con la escala)
  for (const p of PORCENTAJES) {
    if (p === 100) continue
    if (Math.max(med100.W, med100.H) * p / 100 > TOPE_LIENZO * 1.05) continue
    const m = medir(capasData, opts, p)
    if (m.entra) return { porc: p, med: m, med100 }
  }
  return { porc: null, med: null, med100 }
}

function medir(capasData, opts, porc) {
  return planIllustrator(capasData, { ...opts, escala: 100 / porc, soloMedir: true })
}

/** Los `capasData` de cada archivo: talles enteros mientras entren; un talle solo que no entra, en pedazos. */
export function repartirEnArchivos(capasData, opts, porc) {
  // varios rangos se reparten igual que los talles: un bloque por rango
  const porTalle = opts.config === 'talle' || (opts.config === 'rango' && capasData.some((b) => Array.isArray(b.rango) && b.rango.length))
  const bloques = porTalle ? capasData : [capasData[0]]
  // sin «por talle» el plan sólo mira el PRIMER bloque: dos pedazos se juntan sumando sus piezas
  const juntar = (cur, u) => (porTalle ? [...cur, u] : [{ ...cur[0], items: [...cur[0].items, ...u.items] }])
  const partir = (b) => {
    const its = b.items || []
    if (its.length <= 1 || medir([b], opts, porc).cabe) return [b]
    const m = Math.ceil(its.length / 2)
    return [...partir({ ...b, items: its.slice(0, m) }), ...partir({ ...b, items: its.slice(m) })]
  }
  const archivos = []
  let cur = []
  for (const u of bloques.flatMap(partir)) {
    if (!cur.length) { cur = [u]; continue }
    const junto = juntar(cur, u)
    if (medir(junto, opts, porc).cabe) cur = junto
    else { archivos.push(cur); cur = [u] }
  }
  if (cur.length) archivos.push(cur)
  return archivos
}
