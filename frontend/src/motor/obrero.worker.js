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
let arte = null                // el arte separado abierto (camino A), para dibujar sus mesas
// ── LA TIZADA DEL CAMINO A: el molde pelado, el contexto del arte y las bases armadas ─────────
const moldesA = new Map()      // clave → MoldeA (la plantilla abierta con `molde/caminoA.js`)
const contornosA = new Map()   // `${clave}|${mesa}|${talle}` → contornos de esa mesa/talle
const contextosA = new Map()   // clave del arte → contexto (`pieza/caminoA.js`)
const basesA = new Map()       // id → base armada (queda acá: nombra documentos abiertos acá)

async function cargarPieza() {
  if (P) return
  P = {
    ...(await import('./pieza/base.js')), ...(await import('./pieza/estampar.js')),
    ...(await import('./pieza/svg.js')), ...(await import('./texto/fuentes.js')),
    FuenteCurvas: (await import('./texto/curvas.js')).FuenteCurvas,
  }
}

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
  // ── EL MOLDE SIN DISEÑO (camino A) y el DXF (PLAN_NAVEGADOR.md, 1b) ────────────────────────
  /** Un DXF de moldería → el PDF con una capa por talle (`dxf/importar.js`) + su resumen. */
  async dxf_convertir({ bytes }) {
    await cargar()
    const { dxfAPdf } = await import('./dxf/importar.js')
    const r = dxfAPdf(mupdf, bytes)
    return { valor: { pdf: r.pdf, resumen: r.resumen, omitidas: r.omitidas || null }, transfer: [r.pdf.buffer] }
  },
  /**
   * El alta del molde abierto (`abrir`) SIN diseño adentro: registro por etiquetas (o manual con
   * los nombres del DXF), la detección del visor por talle y el lienzo de todas, y el paquete
   * `alta_a` que el servidor valida y guarda (`_paquete_molde_aplicar`).
   */
  async alta_a({ sha1, motor, dxf = null, dxfBytes = null, indices = null, emparejado = null }) {
    await cargar()
    if (!doc) throw new Error('el molde no está abierto')
    const CA = await import('./molde/caminoA.js')
    const molde = new CA.MoldeA(mupdf, doc)
    const preparado = CA.prepararCaminoA(molde, { indices, emparejado, dxf })
    const { zip } = M.armarPaqueteCaminoA(null, preparado, { motor, sha1, dxfBytes })
    const alta = preparado.alta
    return { valor: { zip, resumen: { mesas: alta.mesas, talles: alta.talles, piezas: alta.registro.size,
                                      dxf: preparado.dxf || null } }, transfer: [zip.buffer] }
  },
  // ── LA TIZADA DEL CAMINO A (PLAN_NAVEGADOR.md, 1b): pieza = molde pelado + arte separado ───
  /** Abre la plantilla (molde sin diseño) para leer los contornos de sus piezas. */
  async molde_a_abrir({ clave, bytes }) {
    await cargar()
    const CA = await import('./molde/caminoA.js')
    if (moldesA.has(clave)) { try { moldesA.get(clave).destroy() } catch { /* nada */ } }
    moldesA.set(clave, new CA.MoldeA(mupdf, mupdf.Document.openDocument(bytes, 'application/pdf')))
    for (const k of [...contornosA.keys()]) if (k.startsWith(clave + '|')) contornosA.delete(k)
    const m = moldesA.get(clave)
    const talles = CA.tallesDePlantilla(m)
    return { talles, ordenVar: CA.ordenarPorArchivo(m, [...talles].sort()) }
  },
  /**
   * Lo que `generar_pedido` prepara UNA vez para el arte separado: el mapeo por variante
   * (`mapeo_variantes_arte`), los editables (`extraer_editables`) y el contexto que arma bases.
   * `objetos` = los objetos agregados con sus bytes (`{...objeto, bytes}`).
   */
  async contexto_a({ clave, arte: arteBytes, registro, ordenVar, mapeoArte, editablesCfg, editablesTamano, editablesColor,
                     editablesMarca, editablesSinMarca, marcasComoCruz = true, referencia, borde, objetos = [], conPersonalizacion = false }) {
    await cargar()
    await cargarPieza()
    if (!abridor) throw new Error('primero hay que cargar las tipografías (`fuentes`)')
    const PA = await import('./pieza/caminoA.js')
    const MA = await import('./arte/mapeo.js')
    const ED = await import('./arte/editables.js')
    if (contextosA.has(clave)) { try { contextosA.get(clave).ctx.cerrar() } catch { /* nada */ } }
    let mapeoVar
    try { mapeoVar = MA.mapeoVariantesArte(mupdf, arteBytes, registro, ordenVar || []) } catch { mapeoVar = {} }
    let editables = []
    if (mapeoArte && editablesCfg !== null && editablesCfg !== undefined) {
      try { editables = ED.extraerEditables(mupdf, arteBytes) } catch { editables = [] }
    }
    const porArchivo = new Map(objetos.map((o) => [o.archivo, o.bytes]))
    const ctx = PA.contextoCaminoA(mupdf, {
      arte: arteBytes, mapeoArte, mapeoVar, editables, editablesCfg, editablesTamano, editablesColor,
      editablesMarca, editablesSinMarca, marcasComoCruz, referencia: referencia || 'alto', borde,
      objetosAgregados: objetos.length ? { objetos: objetos.map(({ bytes: _b, ...o }) => o), abrir: (a) => porArchivo.get(a) } : null,
      fuente: abridor.abrir,
    })
    let pers = null
    if (conPersonalizacion) {
      const PE = await import('./arte/personalizacion.js')
      try { pers = PE.extraerPersonalizacion(mupdf, arteBytes) } catch { pers = {} }
    }
    contextosA.set(clave, { ctx, arteRect: ctx.arteRect })
    return { pers }
  },
  /**
   * Una pieza del camino A: el contorno sale de la plantilla (`extraer_piezas_mesa` por
   * `idx_mesa`/`pieza_idx`, o el contorno mayor), la base del contexto del arte y el estampado
   * como en el camino B (con `separado`). La base queda ACÁ (`basesA`) y se devuelve su `baseId`.
   */
  async pieza_a({ molde, arte: claveArte, mesa, talle, pieza, info, persona, nro, variante, grupo, ph, etiqueta, alias, salida }) {
    await cargar()
    if (!P || !abridor) throw new Error('primero hay que cargar las tipografías (`fuentes`)')
    const m = moldesA.get(molde)
    if (!m) throw new Error(`el molde «${molde}» no está abierto`)
    const c = contextosA.get(claveArte)
    if (!c) throw new Error(`el arte «${claveArte}» no está preparado`)
    const CA = await import('./molde/caminoA.js')
    const PA = await import('./pieza/caminoA.js')
    const kc = `${molde}|${mesa}|${talle}`
    let cont
    if (info && info.pieza_idx !== undefined && info.pieza_idx !== null) {
      if (!contornosA.has(kc)) contornosA.set(kc, CA.extraerPiezasMesa(m, mesa, talle))
      cont = contornosA.get(kc)[info.idx_mesa ?? info.pieza_idx]
    } else {
      cont = CA.extraerContornoMesa(m, mesa, talle)
    }
    if (!cont) throw new Error(`la pieza «${pieza}» (talle ${talle}) no está en la mesa ${mesa}`)
    const kb = `${claveArte}|${molde}|${pieza}|${talle}|${variante ?? ''}`
    let base = basesA.get(kb)
    if (!base) {
      base = c.ctx.armarBase({ cont, pieza, talle, variante: variante ?? null })
      basesA.set(kb, base)
    }
    const phMesa = base.mesaA ? ((ph || {})[String(base.mesaA)] || {}) : {}
    const estampado = P.estamparPieza({ base, ph: phMesa, persona, talle, pieza, nro, variante: variante ?? null, grupo: grupo ?? null,
                                        etiqueta, fuente: abridor.abrir, alias: alias || {}, info: info || {},
                                        separado: true, arteRect: base.arteRect })
    const r = { baseId: kb, estampado, W: base.W, H: base.H, B: base.B, Hp: base.Hp, S: base.S, mesaA: base.mesaA,
                w: base.W + 2 * base.B, h: base.Hp }
    if (salida === 'svg' || salida === 'pdf') {
      const pdf = PA.documentoPiezaCaminoA(mupdf, base, estampado)
      if (salida === 'pdf') return { valor: { ...r, pdf }, transfer: [pdf.buffer] }
      r.svg = P.svgDePdf(mupdf, pdf)
    }
    return r
  },
  /** Cierra lo del camino A de un pedido (moldes, contextos y bases). */
  async cerrar_a() {
    for (const m of moldesA.values()) { try { m.destroy() } catch { /* nada */ } }
    for (const c of contextosA.values()) { try { c.ctx.cerrar() } catch { /* nada */ } }
    moldesA.clear(); contextosA.clear(); contornosA.clear(); basesA.clear()
    return true
  },
  /** El arte separado analizado acá (`arte/preparar.js`): el paquete que `POST /api/arte` guarda. */
  async arte_preparar({ bytes, contexto }) {
    await cargar()
    const { prepararArte } = await import('./arte/preparar.js')
    const r = prepararArte(mupdf, bytes, contexto)
    return { valor: { zip: r.zip, sha1: r.sha1, modo: r.modo, validacion: r.validacion, mapeo: r.mapeo }, transfer: [r.zip.buffer] }
  },
  // ── EL ARTE SEPARADO (camino A): sus mesas como SVG para el paso Arte ─────────────────────
  /** Abre el arte y apaga las capas que no se imprimen (guías y editables), como `/api/arte/mesa_img`. */
  async arte_abrir({ bytes }) {
    await cargar()
    await cargarPieza()
    if (arte) { try { arte.destroy() } catch { /* nada */ } arte = null }
    arte = mupdf.Document.openDocument(bytes, 'application/pdf')
    const { apagarCapasNoImpresas } = await import('./arte/capas.js')
    apagarCapasNoImpresas(arte)
    return arte.countPages()
  },
  async arte_svg({ pagina }) {
    if (!arte) throw new Error('el arte no está abierto')
    return P.svgDePagina(mupdf, arte, pagina)
  },
  async cerrar() {
    if (doc) { try { doc.destroy() } catch { /* nada */ } doc = null }
    if (arte) { try { arte.destroy() } catch { /* nada */ } arte = null }
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
    await cargarPieza()
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
  async hoja({ piezas, cfg, perfil, tela }) {
    await cargar()
    const N = await import('./nesting/contorno.js')
    const H = await import('./hoja/componer.js')
    let R = null
    try { R = await import('./rip/aplanar.js') } catch { R = null }
    // camino A: `base` llegó como `{id}`; la de verdad (con su contorno y sus documentos de
    // origen) está acá. Va ANTES del nesting, que lee `base.cont`.
    const origenesA = {}
    for (const p of piezas) {
      if (p.base && p.base.id !== undefined && !p.base.baseStream) {
        const b = basesA.get(p.base.id)
        if (!b) throw new Error(`la base «${p.base.id}» no está armada en este hilo`)
        p.base = b
        for (const [, ref] of (b.fuentesXo || [])) if (ref && ref.doc && !(ref.origen in origenesA)) origenesA[ref.origen] = ref.doc
      }
    }
    const { colocaciones, area } = N.anidarContorno(piezas, cfg)
    const origenes = {}
    for (const [clave, d] of mesas) origenes[String(clave)] = d
    Object.assign(origenes, origenesA)
    const hoja = H.componerHoja(mupdf, { hojas: colocaciones, cfg, origenes })
    let pdf = hoja.pdf
    if (R && R.aplanarParaRip) pdf = R.aplanarParaRip(mupdf, pdf)
    if (perfil && perfil.icc) {
      const out = mupdf.Document.openDocument(pdf, 'application/pdf')
      H.embeberPerfil(out, perfil)
      pdf = out.saveToBuffer('compress').asUint8Array().slice()
      out.destroy()
    }
    // `validar_salida`: las cuatro validaciones de la hoja, con los mismos textos que el servidor
    const V = await import('./hoja/validar.js')
    const validaciones = V.validarHoja(mupdf, pdf, tela, Number(cfg.espaciado_cm ?? 0.5) * 10.0)
    const r = { pdf, consumoCm: hoja.consumoCm, alturasCm: hoja.alturasCm, area, validaciones,
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
