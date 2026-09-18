// EL HILO QUE DIBUJA LAS MESAS EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 2.
//
// Abre un PDF (una hoja de tizada, la ficha técnica, un molde) y contesta pedidos de dibujo: la
// mesa entera o un recorte, al ancho que pida la pantalla. Es lo que antes hacía el pool del visor
// del servidor. La lista de dibujo de cada página queda guardada: el zoom pide muchos recortes de
// la misma mesa y rearmarla cada vez es lo caro.
//
// 🔴 mupdf SE CARGA CON `await import(...)`, NO con un import de arriba: mupdf.js usa `await` a
// nivel de módulo y, en un Web Worker, eso deja al hilo sin arrancar — el worker se queda mudo,
// sin error ni respuesta (medido 2026-09-17 en el laboratorio). Así lo hace `obrero.worker.js`.
const enNode = typeof self === 'undefined' || typeof self.postMessage !== 'function'
const canal = enNode ? (await import('node:worker_threads')).parentPort : self
const escuchar = (fn) => (enNode ? canal.on('message', fn) : (self.onmessage = (ev) => fn(ev.data)))
const responder = (msg, transfer) => canal.postMessage(msg, transfer || [])

let mupdf = null
let dibujarMesa = null
let replay = null                 // `vista/replay.js`: la hoja repetida con cada dibujo de origen interpretado UNA vez
let doc = null
const listas = new Map()          // página → lista de dibujo ya armada
const preps = new Map()           // página → preparado del replay (o null si esa página no se puede repetir)

async function cargar() {
  if (mupdf) return
  mupdf = await import('mupdf')
  dibujarMesa = (await import('./vista/dibujar.js')).dibujarMesa
  replay = await import('./vista/replay.js')
  mupdf.enableICC()               // es lo que hace PyMuPDF; apagada, los colores difieren
}

function cerrarTodo() {
  for (const dl of listas.values()) { try { dl.destroy() } catch { /* nada */ } }
  listas.clear()
  for (const p of preps.values()) { if (p) { try { p.destroy() } catch { /* nada */ } } }
  preps.clear()
  if (doc) { try { doc.destroy() } catch { /* nada */ } doc = null }
}

function listaDe(pagina) {
  if (!listas.has(pagina)) {
    const page = doc.loadPage(pagina)
    listas.set(pagina, page.toDisplayList(true))
    page.destroy()
  }
  return listas.get(pagina)
}

const TAREAS = {
  async abrir({ bytes }) {
    await cargar()
    cerrarTodo()
    doc = mupdf.Document.openDocument(bytes, 'application/pdf')
    const medidas = []
    for (let i = 0; i < doc.countPages(); i++) {
      const p = doc.loadPage(i)
      const b = p.getBounds()
      medidas.push({ ancho: b[2] - b[0], alto: b[3] - b[1] })
      p.destroy()
    }
    return { paginas: medidas.length, medidas }
  },
  async dibujar({ pagina, ancho, recorte, exacto = false }) {
    await cargar()
    // LO RÁPIDO PRIMERO (2026-09-18): la hoja de tizada se «repite» con cada dibujo de origen
    // interpretado una sola vez (`vista/replay.js`: 2-5 s en vez de 20-30 s por página). Si la
    // página no se puede repetir (algo fuera del repertorio) o se pide `exacto` (el contrato de la
    // vista compara bit a bit contra PyMuPDF), va por la lista de dibujo de siempre.
    if (!exacto) {
      if (!preps.has(pagina)) {
        let p = null
        try { p = replay.prepararReplay(mupdf, doc, pagina) } catch { p = null }
        preps.set(pagina, p)
      }
      const prep = preps.get(pagina)
      if (prep) {
        const r = replay.dibujarConReplay(mupdf, doc, pagina, prep, { ancho, recorte })
        return { valor: { png: r.png, w: r.w, h: r.h }, transfer: [r.png.buffer] }
      }
    }
    const r = dibujarMesa(mupdf, doc, pagina, { ancho, recorte, lista: listaDe(pagina) })
    return { valor: { png: r.png, w: r.w, h: r.h }, transfer: [r.png.buffer] }
  },
  async cerrar() {
    cerrarTodo()
    return true
  },
}

escuchar(async (msg) => {
  const { id, tipo, datos } = msg || {}
  try {
    const r = await TAREAS[tipo](datos || {})
    if (r && r.transfer) responder({ id, ok: true, valor: r.valor }, r.transfer)
    else responder({ id, ok: true, valor: r })
  } catch (err) {
    responder({ id, ok: false, error: String((err && err.message) || err) })
  }
})
