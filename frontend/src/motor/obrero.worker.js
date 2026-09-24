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
  // los avisos de estructura de los archivos (miles) no se imprimen: ver `mupdfSilencio.js`
  ;(await import('./mupdfSilencio.js')).silenciarAvisosMupdf()
  mupdf = await import('mupdf')
  mupdf.enableICC()               // es lo que hace PyMuPDF; apagada, los colores de un dibujo difieren
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
    // las bases llevan el contorno del molde anterior: con otra plantilla quedarían con la forma vieja
    for (const k of [...basesA.keys()]) if (k.split('|').includes(clave)) basesA.delete(k)
    const m = moldesA.get(clave)
    const talles = CA.tallesDePlantilla(m)
    return { talles, ordenVar: CA.ordenarPorArchivo(m, [...talles].sort()) }
  },
  /** Un cálculo sobre el ARTE que pidió el servidor (ver `molde_calculo`): → JSON en texto. */
  async arte_calculo({ bytes, fn, args = {} }) {
    await cargar()
    const CA = await import('./molde/caminoA.js')
    let r
    try {
      if (fn === 'arte_personalizacion') r = (await import('./arte/personalizacion.js')).extraerPersonalizacion(mupdf, bytes)
      else if (fn === 'arte_editables') r = (await import('./arte/editables.js')).extraerEditables(mupdf, bytes)
      else if (fn === 'arte_mapeo_variantes') r = (await import('./arte/mapeo.js')).mapeoVariantesArte(mupdf, bytes, args.registro || {}, args.orden || [])
      else if (fn === 'arte_mapeo_nombre') r = (await import('./arte/mapeo.js')).mapeoPorNombre(mupdf, bytes, args.registro || {})
      else if (fn === 'arte_detectar') r = (await import('./arte/mapeo.js')).detectarArte(mupdf, bytes, args.registro || {}, 240)
      else if (fn === 'arte_perfil') r = (await import('./arte/perfil.js')).detectarPerfilIncrustado(mupdf, bytes)
      else throw new Error(`cálculo desconocido: ${fn}`)
    } catch (e) {
      return CA.aTextoJSON({ __error__: String((e && e.message) || e) })
    }
    return CA.aTextoJSON(r)
  },
  /**
   * El OBJETO QUE NO SE SUBLIMA (TPU/Bordado/DTF), aislado del arte y recortado a su lugar, como un
   * PDF de una página: la ficha lo pega en vector (antes el servidor mandaba una miniatura).
   */
  async arte_objeto_pdf({ bytes, mesa, capa, bbox }) {
    await cargar()
    const { leerPagina, reescribirPagina, resolutorXObjects } = await import('./pieza/caminoA.js')
    const { aislarCapaObjetos } = await import('./molde/capas.js')
    const { sanearOc } = await import('./molde/paginas.js')
    const { normNombre } = await import('./nombres.js')
    const doc = new mupdf.PDFDocument(bytes)
    const out = new mupdf.PDFDocument()
    try {
      const pageObj = doc.findPage(mesa - 1)
      let { inst, R } = leerPagina(pageObj)
      inst = aislarCapaObjetos(inst, R, normNombre(capa), {}, resolutorXObjects(pageObj))
      reescribirPagina(doc, pageObj, inst)
      sanearOc(pageObj, new Set())
      // el recuadro del objeto (coordenadas de la página, y hacia abajo) ±2 pt → caja del PDF
      const page = doc.loadPage(mesa - 1)
      const inv = mupdf.Matrix.invert(page.getTransform())
      page.destroy()
      const r = mupdf.Rect.transform([bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2], inv)
      const caja = doc.newArray()
      for (const v of r) caja.push(doc.newReal(v))
      pageObj.put('MediaBox', caja); pageObj.put('CropBox', caja)
      out.graftPage(0, doc, mesa - 1)
      const pdf = out.saveToBuffer('compress').asUint8Array().slice()
      return { valor: pdf, transfer: [pdf.buffer] }
    } finally {
      try { out.destroy() } catch { /* nada */ }
      try { doc.destroy() } catch { /* nada */ }
    }
  },
  /** La GUÍA de medidas (PDF o .ai) sobre la geometría que arma el servidor (`pdf_guia?datos=1`). */
  async guia_archivo({ capas_data, formato = 'pdf', opciones = {} }) {
    await cargar()
    const H = await import('./molde/herramientas.js')
    const bytes = formato === 'ai' ? H.aiGuiaMedidas(capas_data, opciones) : H.pdfGuiaMedidas(mupdf, capas_data, opciones)
    return { valor: bytes, transfer: [bytes.buffer] }
  },
  /** Los contornos de la pieza que sube el usuario (`piezas_molde.contornos_de_pdf`), en el hilo. */
  async contornos_de_pdf({ bytes }) {
    await cargar()
    const H = await import('./molde/herramientas.js')
    const CA = await import('./molde/caminoA.js')
    return CA.aTextoJSON(H.contornosDePdf(mupdf, bytes))
  },
  /**
   * UN CÁLCULO QUE PIDIÓ EL SERVIDOR (2026-09-22, `servidor._calcular` → 428): sobre el molde
   * abierto con `clave` (`molde_a_abrir`), la misma función que tenía el Python. Devuelve el
   * resultado como JSON en TEXTO (`aTextoJSON`: respeta el orden de las claves de los Map, como
   * los dict de Python). Si la función falla, `{"__error__": motivo}`: el servidor lo vuelve a
   * levantar como el error de siempre.
   */
  async molde_calculo({ clave, fn, args = {} }) {
    await cargar()
    const CA = await import('./molde/caminoA.js')
    const H = await import('./molde/herramientas.js')
    const m = moldesA.get(clave)
    if (!m) throw new Error('el molde no está abierto en este hilo')
    let r
    try {
      switch (fn) {
        case 'detectar_piezas': r = CA.detectarPiezas(m, args.talle_ref ?? null, !!args.capas_candidatas); break
        case 'detectar_piezas_todas': r = CA.detectarPiezasTodas(m); break
        case 'alta_plantilla_manual':
          r = CA.altaPlantillaManual(m, args.asign || [], args.mesa, args.talle_ref, args.indices ?? null, args.emparejado ?? null,
                                     (args.excluir_talles && args.excluir_talles.length) ? args.excluir_talles : null)
          break
        case 'alta_plantilla': r = CA.altaPlantilla(m); break
        case 'talles_de_plantilla': r = CA.tallesDePlantilla(m); break
        case 'analizar_variantes': r = H.analizarVariantes(m); break
        case 'detectar_por_talle': r = H.detectarPorTalle(m, args.mesa, args.talles || []); break
        case 'extraer_piezas_mesa': r = CA.extraerPiezasMesa(m, args.mesa, args.talle); break
        case 'anchos_mesas': r = Array.from({ length: m.n }, (_, i) => { const g = m.pagina(i + 1).geo; return g.rect[2] - g.rect[0] }); break
        case 'nido_piezas':
          r = H.nidoPiezas(m, args.registro || {}, { talleGuia: args.talle_guia ?? null, indices: args.indices ?? null, emparejado: args.emparejado ?? null })
          break
        default: throw new Error(`cálculo desconocido: ${fn}`)
      }
    } catch (e) {
      return CA.aTextoJSON({ __error__: String((e && e.message) || e) })
    }
    return CA.aTextoJSON(r)
  },
  /**
   * UNA OPERACIÓN QUE REESCRIBE EL MOLDE (2026-09-22): sobre `bytes` (la versión vigente, o el
   * original para partir en variantes) → `{bytes, resultado_json}` con el archivo nuevo y lo que el
   * servidor necesita saber. Si falla, `resultado_json` = `{"__error__": motivo}` y sin bytes.
   */
  async molde_editar({ bytes, fn, args = {} }) {
    await cargar()
    const CA = await import('./molde/caminoA.js')
    const H = await import('./molde/herramientas.js')
    const abrirTemp = (b) => new CA.MoldeA(mupdf, mupdf.Document.openDocument(b, 'application/pdf'))
    try {
      if (fn === 'agregar_pieza') {
        const r = H.agregarPieza(mupdf, bytes, args.colocaciones || {}, args.mesa || 1)
        return { valor: { bytes: r.bytes, resultado_json: CA.aTextoJSON({ puestos: r.puestos }) }, transfer: [r.bytes.buffer] }
      }
      if (fn === 'renombrar_y_alta') {
        const r = H.renombrarCapas(mupdf, bytes, args.mapa || {})
        const nuevo = abrirTemp(r.bytes.slice())
        let alta
        try { alta = CA.altaPlantilla(nuevo) } finally { nuevo.destroy() }
        return { valor: { bytes: r.bytes, resultado_json: CA.aTextoJSON({ n: r.n, alta }) }, transfer: [r.bytes.buffer] }
      }
      if (fn === 'separar_y_alta') {
        const orig = abrirTemp(bytes.slice())
        let r
        try { r = H.separarPorPiezas(mupdf, bytes, orig, args.asignaciones || {}) } finally { orig.destroy() }
        const nuevo = abrirTemp(r.bytes.slice())
        let ref, alta
        try {
          // la variante de referencia = la de más piezas (la PRIMERA si empatan, como `max`)
          let mejor = -1
          for (const t of r.orden) { const k = CA.extraerPiezasMesa(nuevo, r.mesa, t).length; if (k > mejor) { mejor = k; ref = t } }
          const pref = CA.extraerPiezasMesa(nuevo, r.mesa, ref)
          const porBbox = new Map((args.por_bbox || []).map(([k, v]) => [k.map((x) => Math.round(Number(x) * 10) / 10).join('|'), v]))
          const kb = (b) => b.map((x) => Math.round(Number(x) * 10) / 10).join('|')
          const asign = pref.map((p, i) => ({ idx: i, nombre: porBbox.get(kb(p.bbox_mu)) || `Pieza ${i + 1}` }))
          alta = CA.altaPlantillaManual(nuevo, asign, r.mesa, ref, null, args.emparejado ?? null)
        } finally { nuevo.destroy() }
        return { valor: { bytes: r.bytes, resultado_json: CA.aTextoJSON({ mesa: r.mesa, capa_origen: r.capa_origen, orden: r.orden, ref, alta }) },
                 transfer: [r.bytes.buffer] }
      }
      throw new Error(`operación desconocida: ${fn}`)
    } catch (e) {
      return { bytes: null, resultado_json: CA.aTextoJSON({ __error__: String((e && e.message) || e) }) }
    }
  },
  /**
   * Lo que `generar_pedido` prepara UNA vez para el arte separado: el mapeo por variante
   * (`mapeo_variantes_arte`), los editables (`extraer_editables`) y el contexto que arma bases.
   * `objetos` = los objetos agregados con sus bytes (`{...objeto, bytes}`).
   */
  async contexto_a({ clave, arte: arteBytes, registro, ordenVar, mapeoArte, editablesCfg, editablesTamano, editablesColor,
                     editablesMarca, editablesSinMarca, marcasComoCruz = true, referencia, borde, objetos = [], conPersonalizacion = false,
                     molde = null }) {
    await cargar()
    await cargarPieza()
    if (!abridor) throw new Error('primero hay que cargar las tipografías (`fuentes`)')
    const PA = await import('./pieza/caminoA.js')
    const MA = await import('./arte/mapeo.js')
    const ED = await import('./arte/editables.js')
    if (contextosA.has(clave)) { try { contextosA.get(clave).ctx.cerrar() } catch { /* nada */ } }
    // 🔴 Las bases armadas con el contexto anterior NOMBRAN sus documentos (el arte, los editables),
    // y `cerrar()` acaba de destruirlos. Si quedaban en `basesA`, la próxima pieza del mismo
    // talle/variable reusaba una base muerta y reventaba con «cannot find page tree» o «invalid
    // page number»: pasaba al cargar un arte nuevo con el visor ya mostrando el anterior, y la
    // pantalla le tiraba TODOS los talles al servidor (reporte 2026-09-18: «tarda en cargar un arte»).
    for (const k of [...basesA.keys()]) if (k.startsWith(clave + '|')) basesA.delete(k)
    let mapeoVar
    try { mapeoVar = MA.mapeoVariantesArte(mupdf, arteBytes, registro, ordenVar || []) } catch { mapeoVar = {} }
    let editables = []
    if (mapeoArte && editablesCfg !== null && editablesCfg !== undefined) {
      try { editables = ED.extraerEditables(mupdf, arteBytes) } catch { editables = [] }
    }
    const porArchivo = new Map(objetos.map((o) => [o.archivo, o.bytes]))
    // 🔴 EL ARTE CLÁSICO (2026-09-22): el diseño viene dibujado sobre la MISMA mesa del molde, sin
    // mapeo. Para limpiarlo hacen falta las capas del molde (`TODAS`) y los recuadros de su
    // moldería por talle (`geometrias_base`), que salen del molde abierto en este hilo. Antes el
    // navegador no lo sabía hacer y esos pedidos se generaban en el servidor.
    let capasMolde = null, geomsBase = null
    const esClasico = !Object.keys(PA.normalizarMapeo(mapeoArte).base || {}).length
    if (esClasico && molde && moldesA.has(molde)) {
      const m = moldesA.get(molde)
      capasMolde = PA.capasDelDocumento(m.doc)
      const geoms = new Map()
      geomsBase = (mesa, talle) => {
        const k = `${mesa}|${talle}`
        if (!geoms.has(k)) {
          // `molde_real.geometrias_base`: los recuadros de los dibujos de ESE talle, en crudas del lienzo
          const { geo } = m.pagina(mesa)
          const cb = geo.cb, U = geo.U || 1.0
          geoms.set(k, m.dibujos(mesa).filter((d) => d.layer === talle && d.rect).map((d) => {
            const r = d.rect
            return [r[0] / U + cb[0], cb[3] - r[3] / U, r[2] / U + cb[0], cb[3] - r[1] / U]
          }))
        }
        return geoms.get(k)
      }
    }
    const ctx = PA.contextoCaminoA(mupdf, {
      capasMolde, geomsBase,
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
    const clasico = !c.ctx.separado
    if (!base) {
      // el arte CLÁSICO está sobre la misma mesa del molde (sin mapeo): su propia base
      base = clasico ? c.ctx.armarBaseClasico({ cont, mesa, talle, pieza, variante: variante ?? null })
                     : c.ctx.armarBase({ cont, pieza, talle, variante: variante ?? null })
      // 🔴 EL ORIGEN DE CADA DIBUJO LLEVA SU ARTE. El contexto lo nombra por mesa (`arte|2`,
      // `editable|…`), y la hoja comparte un dibujo entre piezas por ese nombre: con JUGADOR y
      // GOLERO del mismo molde en la misma hoja, las del golero salían con el arte del jugador
      // (nombre y número bien: van aparte). Reporte 2026-09-18. Con la clave del arte adelante,
      // dos artes distintos nunca comparten dibujo; las piezas del MISMO arte lo siguen compartiendo.
      base.fuentesXo = (base.fuentesXo || []).map(([nom, ref]) => [nom, { ...ref, origen: `${claveArte}§${ref.origen}` }])
      basesA.set(kb, base)
    }
    // la personalización va por la mesa del ARTE (separado) o por la del MOLDE (clásico: `clave_pers = str(mesa)`)
    const phMesa = clasico ? ((ph || {})[String(mesa)] || {}) : (base.mesaA ? ((ph || {})[String(base.mesaA)] || {}) : {})
    const estampado = P.estamparPieza({ base, ph: phMesa, persona, talle, pieza, nro, variante: variante ?? null, grupo: grupo ?? null,
                                        etiqueta, fuente: abridor.abrir, alias: alias || {}, info: info || {},
                                        separado: !clasico, arteRect: clasico ? null : base.arteRect })
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
  /**
   * VALIDAR EL ARTE CON UN MAPEO NUEVO, ACÁ (2026-09-22, «el servidor sólo sostiene el sistema y la
   * base»). Es `MP.validar_arte_separado` de `POST /api/arte/mapeo`, que el servidor corría en el
   * request cada vez que se arrastraba un diseño sobre una pieza: `arte/mapeo.js
   * validarArteSeparado` es su traducción (la misma que usa el paquete del arte al subirlo).
   * `contexto` = `/api/productos/<pid>/arte_contexto`; `variante` acota a las piezas de esa variable
   * (`_piezas_de_variable`; sin piezas → todo el molde, igual que el servidor).
   */
  async arte_validar({ bytes, contexto, mapeo, variante = '' }) {
    await cargar()
    const { validarArteSeparado } = await import('./arte/mapeo.js')
    const scope = variante ? ((contexto.variantes || {})[variante] || null) : null
    const val = validarArteSeparado(mupdf, bytes, contexto.registro || {}, contexto.fuentes || { catalogo: [], alias: {} },
                                    mapeo || {}, contexto.orden_var || [], scope)
    val.campos_personalizacion = [...new Set(Object.values(val.personalizacion || {}).flatMap((m) => Object.keys(m || {})))]
      .sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
    return val
  },
  /** Los editables del arte para el editor (`arte/editablesVista.js`): lo que era
   *  `GET /api/productos/editables` en el pool del servidor. */
  async editables_vista({ bytes, datos }) {
    await cargar()
    const { editablesParaEditor } = await import('./arte/editablesVista.js')
    return editablesParaEditor(mupdf, bytes, datos)
  },
  /**
   * UNA TIPOGRAFÍA ANTES DE SUBIRLA (2026-09-22): lo que `MP.alta_fuente` hacía en el servidor.
   * `interno` = el nombre que le da MuPDF (el mismo `fz_font_name` que `fitz.Font(...).name`);
   * `sin_contorno` = los caracteres de prueba que no se pueden dibujar; `choca_con` = otra del
   * `catalogo` que normaliza al mismo nombre (el resolvedor no las podría distinguir). `destino` =
   * el nombre con el que se va a guardar (no choca consigo misma al reemplazarse).
   */
  async fuente_analizar({ bytes, catalogo = [], destino = '' }) {
    await cargar()
    const { FuenteCurvas } = await import('./texto/curvas.js')
    const { normFuente } = await import('./texto/fuentes.js')
    let interno
    const f = new mupdf.Font('subida', bytes)
    try { interno = f.getName() } finally { try { f.destroy() } catch { /* nada */ } }
    const fc = new FuenteCurvas(bytes, null)
    const prueba = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ0123456789#-'
    const sin = []
    for (const ch of prueba) {
      let ok = false
      try { const [regs] = fc._glifo(ch); ok = !!(regs && regs.length) } catch { ok = false }
      if (!ok) sin.push(ch)
    }
    const nuevo = normFuente(interno)
    const otra = (catalogo || []).find((c) => c.archivo !== destino && normFuente(c.interno || '') === nuevo)
    return { interno, sin_contorno: sin, choca_con: otra ? { interno: otra.interno, archivo: otra.archivo } : null }
  },
  /**
   * REVALIDAR EL ARTE después de sumar una tipografía (lo que `/api/fuente` hacía en el servidor):
   * separado → `validarArteSeparado` con el mapeo base; clásico → `validarArte` con la plantilla.
   */
  async arte_revalidar({ bytes, modo, contexto, mapeo, plantilla = null }) {
    await cargar()
    const M = await import('./arte/mapeo.js')
    const fuentes = contexto.fuentes || { catalogo: [], alias: {} }
    if (modo === 'separado') return M.validarArteSeparado(mupdf, bytes, contexto.registro || {}, fuentes, mapeo || {}, contexto.orden_var || [])
    if (!plantilla) throw new Error('para revalidar un arte clásico hace falta la plantilla')
    return M.validarArte(mupdf, bytes, plantilla, fuentes)
  },
  /**
   * UNA MESA SUELTA (la página `pi` de una hoja) como PDF propio, CON el perfil de color de la hoja:
   * lo que `GET /api/trabajos/<tid>/mesa/<archivo>` hacía con pikepdf (`_pdf_de_una_pagina`). La
   * página ya viene aplanada (lista para el RIP) y se copia tal cual; `OutputIntents` vive en la
   * raíz, así que se copia aparte. Una hoja de una sola página sale TAL CUAL. PDF 1.6 como la hoja.
   */
  async pagina_pdf({ bytes, pi = 0 }) {
    await cargar()
    const src = new mupdf.PDFDocument(bytes)
    try {
      const n = src.countPages()
      if (n <= 1) { const u = bytes.slice(); return { valor: u, transfer: [u.buffer] } }
      const p = pi >= 0 && pi < n ? pi : 0
      const dst = new mupdf.PDFDocument()
      try {
        dst.graftPage(0, src, p)
        const ois = src.getTrailer().get('Root').get('OutputIntents')
        if (ois && !ois.isNull()) dst.getTrailer().get('Root').put('OutputIntents', dst.graftObject(ois))
        try { dst.setMetaData('info:Creator', 'TIZADA PRO'); dst.setMetaData('info:Producer', 'TIZADA PRO') } catch { /* sin metadatos */ }
        const out = dst.saveToBuffer('garbage,compress').asUint8Array().slice()
        if (out[0] === 37 && out[1] === 80 && out[2] === 68 && out[3] === 70 && out[4] === 45) { out[5] = 49; out[6] = 46; out[7] = 54 }
        return { valor: out, transfer: [out.buffer] }
      } finally {
        try { dst.destroy() } catch { /* nada */ }
      }
    } finally {
      try { src.destroy() } catch { /* nada */ }
    }
  },
  // ── «EDITAR DISEÑO» (`arte/editarArte.js`): lo que hacía `objetos_agregados.py` en el servidor ──
  /** Un objeto subido → PDF de una página + su medida + su vista (SVG, texto). */
  async objeto_normalizar({ bytes, nombre }) {
    await cargar()
    const EA = await import('./arte/editarArte.js')
    const { svgDePdf } = await import('./pieza/svg.js')
    const r = EA.normalizarObjeto(mupdf, bytes, nombre)
    let svg = ''
    try { svg = svgDePdf(mupdf, r.pdf) } catch { svg = '' }
    return { valor: { ...r, svg }, transfer: [r.pdf.buffer] }
  },
  /** La vista (SVG, texto) de un PDF de una página (el objeto duplicado). */
  async svg_de_pdf({ bytes }) {
    await cargar()
    const { svgDePdf } = await import('./pieza/svg.js')
    return svgDePdf(mupdf, bytes)
  },
  /** COLOCAR: el objeto entra al arte como la capa «Editable <nombre>» en cada mesa de la pieza. */
  async arte_colocar({ arte, registro, mapeoBase, pieza, fx, fy, wCm, hCm, objPdf, nombre }) {
    await cargar()
    const EA = await import('./arte/editarArte.js')
    const col = EA.colocacionesObjeto(mupdf, arte, { registro, mapeoBase, pieza, fx, fy, wCm, hCm })
    const r = EA.inyectarEditable(mupdf, arte, col, objPdf, nombre)
    return { valor: r, transfer: [r.bytes.buffer] }
  },
  /** QUITAR: saca del arte una capa que agregó el usuario. */
  async arte_quitar({ arte, capa }) {
    await cargar()
    const EA = await import('./arte/editarArte.js')
    const r = EA.quitarEditable(mupdf, arte, capa)
    return { valor: r, transfer: [r.bytes.buffer] }
  },
  /** Las capas del arte como las lista el panel de capas (`layer_ui_configs`), para saber cuáles
   *  agregó el usuario comparando con el original (`capas_agregadas`). */
  async arte_capas({ bytes }) {
    await cargar()
    const CA = await import('./molde/caminoA.js')
    const d = new mupdf.PDFDocument(bytes)
    try { return CA.capasUI(d).map((c) => c.text) } finally { d.destroy() }
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
    const r = { baseStream: base.baseStream, clip: base.clip, estampado, W: base.W, H: base.H, B: base.B, Hp: base.Hp, S, nom: base.nom,
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
  /**
   * EL MOLDE GUÍA DE LA FICHA, SIN DIBUJAR NADA (2026-09-22, «ya tenemos el archivo, usá eso; no
   * puede tardar más de 1 s»). Un PDF con UNA página por pieza que NOMBRA el diseño original — la
   * mesa del talle guía (camino B) o las páginas del arte (camino A) — copiado UNA sola vez para todas
   * las piezas; cada página es el contorno de la pieza + «NOMBRE»/«00» encima, lo mismo que va a la
   * tizada. Nada se rasteriza: es el vector del archivo (LEY: siempre el vector original).
   * `piezas` = [{camino: 'a'|'b', datos}] con los datos de `pieza_a` / `pieza`. Devuelve el PDF y,
   * por pieza, su página (o el error si esa pieza no se pudo armar: su tarjeta queda vacía).
   */
  async guia_pdf({ piezas }) {
    await cargar()
    const PA = await import('./pieza/caminoA.js')
    const RC = await import('./ficha/recorte.js')
    const out = new mupdf.PDFDocument()
    const arboles = new Map()          // XObject → su contenido en árbol (se lee UNA vez)
    const xoMesa = new Map()           // `${mesa}|${pagina}` → la mesa del talle como XObject
    const mapas = new Map()            // documento del arte → graft map (sus recursos, una vez)
    const xoArte = new Map()           // documento del arte → (página → XObject)
    const enc = new TextEncoder()
    const res = []
    try {
      for (const p of piezas) {
        try {
          let r, xs
          if (p.camino === 'a') {
            r = await TAREAS.pieza_a({ ...p.datos, salida: null })
            const base = basesA.get(r.baseId)
            r = { ...r, baseStream: base.baseStream }   // la base del camino A queda en el hilo
            xs = []
            for (const [nom, ref] of base.fuentesXo || []) {
              if (!mapas.has(ref.doc)) { mapas.set(ref.doc, out.newGraftMap()); xoArte.set(ref.doc, new Map()) }
              const porPag = xoArte.get(ref.doc)
              if (!porPag.has(ref.pagina)) porPag.set(ref.pagina, PA.formDePagina(out, mapas.get(ref.doc), ref.doc, ref.pagina))
              xs.push([nom.slice(1), porPag.get(ref.pagina)])
            }
          } else {
            r = await TAREAS.pieza({ ...p.datos, salida: null })
            const k = `${p.datos.mesa}|${p.datos.pagina}`
            if (!xoMesa.has(k)) xoMesa.set(k, P.formDeMesa(mupdf, out, mesas.get(p.datos.mesa), p.datos.pagina).xo)
            xs = [[r.nom.slice(1), xoMesa.get(k)]]
          }
          const w = r.W + 2 * r.B, h = r.H + 2 * r.B
          const contenido = enc.encode((r.baseStream || '') + r.estampado)
          // 🔴 cada pieza se lleva SÓLO su parte del archivo (`ficha/recorte.js`): con la mesa entera
          // en cada tarjeta, quien mira la ficha tenía que leer la mesa completa por pieza y las
          // hojas del molde guía no aparecían. Mismo vector, sin lo que el recorte tapaba igual.
          try { xs = RC.xobjectsDePieza(out, contenido, xs, [0, 0, w, h], arboles) } catch { /* va la mesa entera */ }
          const rd = out.newDictionary(), xd = out.newDictionary()
          for (const [n, o] of xs) xd.put(n, o)
          rd.put('XObject', xd)
          out.insertPage(out.countPages(), out.addPage([0, 0, w, h], 0, rd, contenido))
          res.push({ pagina: out.countPages() - 1, w, h, wr: r.w, hr: r.h })   // wr/hr: la medida que se rotula
        } catch (e) {
          res.push({ error: String((e && e.message) || e) })
        }
      }
      // `garbage`: la mesa entera ya no la nombra nadie (cada pieza tiene su parte): no viaja
      const pdf = out.saveToBuffer('garbage,compress').asUint8Array().slice()
      return { valor: { pdf, piezas: res }, transfer: [pdf.buffer] }
    } finally {
      for (const m of mapas.values()) { try { m.destroy() } catch { /* nada */ } }
      try { out.destroy() } catch { /* nada */ }
    }
  },
  /** La FICHA TÉCNICA (etapa 4): `ficha/ficha.js` sobre mupdf, acá para no cargar mupdf en la pantalla. */
  async ficha({ titulo, subtitulo, planilla, moldesGuia }) {
    await cargar()
    const F = await import('./ficha/ficha.js')
    const pdf = F.generarFicha(mupdf, { titulo, subtitulo, planilla, moldesGuia })
    // cuántas hojas tiene (la pantalla lo muestra; antes el servidor abría la ficha para contarlas)
    let paginas = 1
    try { const d = new mupdf.PDFDocument(pdf.slice()); paginas = d.countPages(); d.destroy() } catch { paginas = 1 }
    return { valor: { pdf, paginas }, transfer: [pdf.buffer] }
  },
  async hoja({ piezas, cfg, perfil, tela }, { avance = () => {} } = {}) {
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
    avance(0.02, 'Acomodando las piezas en la tela')
    const _t = { t0: performance.now() }
    const { colocaciones, area } = N.anidarContorno(piezas, cfg)
    _t.acomodar = performance.now()
    avance(0.40, 'Armando la hoja')
    const origenes = {}
    for (const [clave, d] of mesas) origenes[String(clave)] = d
    Object.assign(origenes, origenesA)
    const hoja = H.componerHoja(mupdf, { hojas: colocaciones, cfg, origenes })
    _t.armar = performance.now()
    avance(0.65, 'Preparando la hoja para el RIP')
    let pdf = hoja.pdf
    if (R && R.aplanarParaRip) pdf = R.aplanarParaRip(mupdf, pdf)
    _t.rip = performance.now()
    avance(0.90, 'Incrustando el perfil de color y revisando la hoja')
    if (perfil && perfil.icc) {
      const out = mupdf.Document.openDocument(pdf, 'application/pdf')
      H.embeberPerfil(out, perfil)
      pdf = out.saveToBuffer('compress').asUint8Array().slice()
      out.destroy()
    }
    // `validar_salida`: las cuatro validaciones de la hoja, con los mismos textos que el servidor
    const V = await import('./hoja/validar.js')
    const _tv0 = performance.now()
    const validaciones = V.validarHoja(mupdf, pdf, tela, Number(cfg.espaciado_cm ?? 0.5) * 10.0)
    // la revisión para el RIP, ACÁ (antes el servidor volvía a abrir la hoja con pikepdf al guardar)
    let rip
    try { rip = (await import('./rip/verificar.js')).verificarRip(mupdf, pdf) }
    catch (e) { rip = { ok: false, fallas: [`no se pudo revisar la hoja: ${(e && e.message) || e}`] } }
    const _s = (a, b) => Math.round((b - a) / 100) / 10
    const r = { pdf, consumoCm: hoja.consumoCm, alturasCm: hoja.alturasCm, area, validaciones, rip,
                piezas: colocaciones.reduce((n, h) => n + h.length, 0),
                // cuánto tardó cada etapa de ESTA hoja, en segundos (queda en el pedido guardado)
                tiempos: { acomodar: _s(_t.t0, _t.acomodar), armar: _s(_t.acomodar, _t.armar), rip: _s(_t.armar, _t.rip),
                           perfil: _s(_t.rip, _tv0), validar: _s(_tv0, performance.now()) } }
    return { valor: r, transfer: [pdf.buffer] }
  },
}

// EL MONITOR pregunta cuánta memoria usa este hilo (`monitor.js medirHilos`): la del motor de PDF
// (la memoria de WebAssembly de mupdf, que es casi todo lo que gasta un hilo). Contesta por el
// canal que le mandan, así nadie más que escuche este hilo ve la respuesta.
// y cuánto tiempo lleva TRABAJANDO (con al menos una tarea en curso): con eso el monitor saca el %
// de procesador que usa TIZADA en esta PC (el navegador no deja medir el procesador de otra forma)
let _activos = 0, _desde = 0, _trabajadoMs = 0
function empiezaTarea() { if (_activos++ === 0) _desde = performance.now() }
function terminaTarea() { if (--_activos === 0) _trabajadoMs += performance.now() - _desde }
function contestarMemoria(puerto) {
  let bytes = 0
  try {
    const m = globalThis.$libmupdf_wasm_Module
    bytes = (m && m.HEAPU8 && m.HEAPU8.buffer && m.HEAPU8.buffer.byteLength) || 0
  } catch { /* nada */ }
  const trabajadoMs = _trabajadoMs + (_activos ? performance.now() - _desde : 0)
  try { puerto.postMessage({ bytes, trabajadoMs }) } catch { /* nada */ }
}

escuchar(async (msg) => {
  if (msg && msg.__memoria) { contestarMemoria(msg.__memoria); return }
  const { id, tipo, datos } = msg || {}
  // AVANCE de una tarea larga (la hoja): un mensaje aparte con el mismo id, que NO la termina. Sólo
  // cuenta etapas ya hechas: no agrega trabajo (pedido del usuario 2026-09-22: la barra real).
  const avance = (fraccion, texto) => { try { responder({ id, avance: fraccion, texto: texto || '' }) } catch { /* sin pantalla */ } }
  empiezaTarea()
  try {
    const r = await TAREAS[tipo](datos || {}, { avance })
    if (r && typeof r === 'object' && 'valor' in r && 'transfer' in r) responder({ id, valor: r.valor }, r.transfer)
    else responder({ id, valor: r })
  } catch (e) {
    responder({ id, error: String((e && e.message) || e), pila: e && e.stack })
  } finally {
    terminaTarea()
  }
})
