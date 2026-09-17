// UN HILO DE TRABAJO DEL MOTOR (PLAN_NAVEGADOR.md, etapa 1 — velocidad).
//
// Varios de estos corren a la vez (`pool.js`). Cada uno abre el molde UNA vez con mupdf.js y
// después atiende tareas sueltas: las piezas de una mesa, el contenido de una mesa cortado por
// talle, el trabajo de un talle, el PDF de una mesa, el paquete. Las tareas usan exactamente las
// mismas funciones que el motor en un solo hilo (el contrato compara el resultado con el servidor).
//
// Corre igual en el navegador (Web Worker) y en Node (worker_threads), para poder probarlo.

const enNode = typeof self === 'undefined' || typeof self.postMessage !== 'function'
const canal = enNode ? (await import('node:worker_threads')).parentPort : self
const escuchar = (fn) => (enNode ? canal.on('message', fn) : (self.onmessage = (ev) => fn(ev.data)))
const responder = (msg, transfer) => canal.postMessage(msg, transfer || [])

let mupdf = null
let doc = null
let M = null           // módulos del motor

async function cargar() {
  if (M) return
  mupdf = await import('mupdf')
  const dib = await import('./pdf/dibujos.js')
  const cont = await import('./molde/contornos.js')
  const pag = await import('./molde/paginas.js')
  const tal = await import('./molde/talle.js')
  const paq = await import('./paquete/armar.js')
  M = { ...dib, ...cont, ...pag, ...tal, ...paq }
}

const TAREAS = {
  async abrir({ bytes }) {
    await cargar()
    if (doc) { try { doc.destroy() } catch { /* nada */ } }
    doc = mupdf.Document.openDocument(bytes, 'application/pdf')
    return { mesas: doc.countPages(), talles: M.tallesDelMolde(doc) }
  },
  async contornos({ mesa, talles }) {
    const page = doc.loadPage(mesa - 1)
    const geo = M.geometriaPagina(page)
    let completos = null
    const r = M.contornosDeMesa(M.dibujosDePagina(mupdf, page, { ligero: true }), geo, mesa, talles,
      () => (completos = completos || M.dibujosDePagina(mupdf, page)))
    page.destroy()
    return { mesa, geo, talles: r.talles, marco: r.marco, U: r.U }
  },
  async preparar({ mesa, talles }) {
    // el contenido de la mesa, leído y cortado UNA vez, repartido en los bytes de cada talle
    const prep = M.prepararMesa(doc, mesa)
    const porTalle = talles.map((t) => M.bytesDelTalle(prep, t))
    return { valor: { mesa, R: prep.R, porTalle }, transfer: porTalle.map((b) => b.buffer) }
  },
  async talle(datos) {
    await cargar()
    const r = M.trabajarTalle(datos)
    return r.contenido ? { valor: r, transfer: [r.contenido.buffer] } : r
  },
  async armar({ mesa, contenidos }) {
    const pdf = M.armarPdfMesa(mupdf, doc, mesa, contenidos)
    return { valor: pdf, transfer: [pdf.buffer] }
  },
  async paquete({ archivo, desplegado, motor, fase, sha1 }) {
    await cargar()
    const r = M.armarPaqueteMolde(archivo, desplegado, { motor, fase, sha1 })
    const { zip } = r
    sha1 = r.sha1
    return { valor: { zip, sha1 }, transfer: [zip.buffer] }
  },
  async cerrar() {
    if (doc) { try { doc.destroy() } catch { /* nada */ } doc = null }
    return true
  },
}

escuchar(async (msg) => {
  const { id, tipo, datos } = msg || {}
  try {
    const r = await TAREAS[tipo](datos || {})
    if (r && typeof r === 'object' && 'valor' in r && 'transfer' in r) responder({ id, valor: r.valor }, r.transfer)
    else responder({ id, valor: r })
  } catch (e) {
    responder({ id, error: String((e && e.message) || e), pila: e && e.stack })
  }
})
