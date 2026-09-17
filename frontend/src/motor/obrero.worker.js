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
// ── PIEZAS (etapas 3 y 4): las mesas desplegadas abiertas y las tipografías listas ──────────
const mesas = new Map()        // mesa → PDFDocument de m{mesa}.pdf
let P = null                   // módulos de la pieza (base, estampar, svg, fuentes, curvas)
let abridor = null             // el que abre tipografías por nombre (`texto/fuentes.js`)

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
  // ¿Trae el diseño adentro? Se miran las dos primeras mesas, como el servidor
  // (`parece_molde_con_diseno`). Es lo que decide si este molde se prepara acá o lo lee el
  // servidor por el camino de siempre (molde pelado, camino A).
  async parece({ mesas = 2 } = {}) {
    const total = { clips: 0, pintados: 0 }
    for (let m = 0; m < Math.min(doc.countPages(), mesas); m++) {
      const page = doc.loadPage(m)
      const c = M.conteoConDiseno(M.dibujosDePagina(mupdf, page, { ligero: true }), M.geometriaPagina(page))
      page.destroy()
      total.clips += c.clips
      total.pintados += c.pintados
    }
    return M.decidirConDiseno(total)
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
    for (const d of mesas.values()) { try { d.destroy() } catch { /* nada */ } }
    mesas.clear()
    return true
  },

  // ── LAS PIEZAS EN EL NAVEGADOR (PLAN_NAVEGADOR.md, etapas 3 y 4) ─────────────────────────
  /** Abre una mesa desplegada (`m{mesa}.pdf`) para armar piezas de ella. */
  async mesa_abrir({ mesa, bytes }) {
    await cargar()
    if (mesas.has(mesa)) { try { mesas.get(mesa).destroy() } catch { /* nada */ } }
    mesas.set(mesa, mupdf.Document.openDocument(bytes, 'application/pdf'))
    return true
  },
  /** Las tipografías: el catálogo del servidor, los archivos ya bajados y los reemplazos. */
  async fuentes({ catalogo, archivos, alias }) {
    await cargar()
    if (!P) {
      P = {
        ...(await import('./pieza/base.js')), ...(await import('./pieza/estampar.js')),
        ...(await import('./pieza/svg.js')), ...(await import('./texto/fuentes.js')),
        FuenteCurvas: (await import('./texto/curvas.js')).FuenteCurvas,
      }
    }
    abridor = P.crearAbridor({
      catalogo, alias: alias || {}, FuenteCurvas: P.FuenteCurvas,
      traer: async (e) => { const b = archivos[e.archivo]; if (!b) throw new Error(`falta el archivo de «${e.interno}»`); return b },
    })
    await abridor.precargar(Object.keys(archivos).map((a) => (catalogo.find((c) => c.archivo === a) || {}).interno).filter(Boolean))
    return true
  },
  /** La BASE + el ESTAMPADO de una pieza (los operadores), y si se pide, su SVG o su PDF. */
  async pieza({ mesa, pagina, cont, borde, etiqueta, ph, persona, talle, pieza, nro, variante, grupo, info, alias, salida }) {
    await cargar()
    if (!P || !abridor) throw new Error('primero hay que cargar las tipografías (`fuentes`)')
    const d = mesas.get(mesa)
    if (!d) throw new Error(`la mesa ${mesa} no está abierta`)
    const pageObj = d.findPage(pagina)
    const uu = pageObj.get('UserUnit')
    const S = (uu && uu.isNumber && uu.isNumber()) ? Number(uu.asNumber()) : 1.0
    const base = P.armarBase(cont, S, borde)
    const estampado = P.estamparPieza({ base, ph, persona, talle, pieza, nro, variante, grupo, etiqueta,
                                        fuente: abridor.abrir, alias: alias || {}, info: info || {} })
    const r = { baseStream: base.baseStream, clip: base.clip, estampado, W: base.W, H: base.H, B: base.B, Hp: base.Hp, S,
                w: base.W + 2 * base.B, h: base.Hp }
    if (salida === 'svg' || salida === 'pdf') {
      const pdf = P.documentoPieza(mupdf, d, pagina, base, estampado)
      if (salida === 'pdf') return { valor: { ...r, pdf }, transfer: [pdf.buffer] }
      r.svg = P.svgDePdf(mupdf, pdf)
    }
    return r
  },
  /**
   * UNA HOJA DE TIZADA (etapa 4): acomoda las piezas de una tela (`nesting/contorno.js`), compone
   * la hoja con el sello (`hoja/componer.js`), la aplana para el RIP (`rip/aplanar.js`) y le
   * incrusta el perfil de salida. Es `_nestear_y_componer` + el final de `generar_multi`, para una
   * tela. `piezas` = las entradas del motor (`{w, h, base, estampado, pieza, talle, variante,
   * etiqueta, rotacion, borde_cm}`) con `base.fuentesXo` apuntando a las mesas ya abiertas acá.
   */
  /** La FICHA TÉCNICA (etapa 4): `ficha/ficha.js` sobre mupdf, acá para no cargar mupdf en la pantalla. */
  async ficha({ titulo, subtitulo, planilla, moldesGuia }) {
    await cargar()
    const F = await import('./ficha/ficha.js')
    const pdf = F.generarFicha(mupdf, { titulo, subtitulo, planilla, moldesGuia })
    return { valor: pdf, transfer: [pdf.buffer] }
  },
  async hoja({ piezas, cfg, perfil, avisar }) {
    await cargar()
    const N = await import('./nesting/contorno.js')
    const H = await import('./hoja/componer.js')
    let R = null
    try { R = await import('./rip/aplanar.js') } catch { R = null }
    const { colocaciones, area } = N.anidarContorno(piezas, cfg)
    const origenes = {}
    for (const [clave, d] of mesas) origenes[String(clave)] = d
    const hoja = H.componerHoja(mupdf, { hojas: colocaciones, cfg, origenes })
    let pdf = hoja.pdf
    if (R && R.aplanarParaRip) pdf = R.aplanarParaRip(mupdf, pdf)
    if (perfil && perfil.icc) {
      const out = mupdf.Document.openDocument(pdf, 'application/pdf')
      H.embeberPerfil(out, perfil)
      pdf = out.saveToBuffer('compress').asUint8Array().slice()
      out.destroy()
    }
    // `validar_salida`: la hoja final no puede tener recursos de fuente (todo el texto va en curvas)
    let tieneFuente = false
    {
      const d = mupdf.Document.openDocument(pdf, 'application/pdf')
      for (let i = 0; i < d.countPages(); i++) {
        const res = d.findPage(i).get('Resources')
        if (res && res.get && res.get('Font') && !res.get('Font').isNull()) { tieneFuente = true; break }
      }
      d.destroy()
    }
    const r = { pdf, consumoCm: hoja.consumoCm, alturasCm: hoja.alturasCm, area, tieneFuente,
                piezas: colocaciones.reduce((n, h) => n + h.length, 0) }
    return { valor: r, transfer: [pdf.buffer] }
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
