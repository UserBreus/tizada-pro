// WORKER del laboratorio (PLAN_NAVEGADOR.md, etapa 0). Abre el molde con mupdf.js y, mesa por
// mesa, corre lo mismo que los contratos: los dibujos (`dibujosDePagina`, = get_cdrawings) y las
// instrucciones del contenido (`instrucciones`, = pikepdf). Mide tiempo y la memoria de
// WebAssembly (lo que de verdad limita: 4 GB por pestaña).

// Emscripten cuelga HEAPU8 del objeto «Module» que se le pasa: dejándolo en el global ANTES de
// importar mupdf.js se puede leer cuánta memoria de WebAssembly ocupa.
const MODULO = (globalThis.$libmupdf_wasm_Module = globalThis.$libmupdf_wasm_Module || {})
const memoriaWasm = () => {
  try { return MODULO.HEAPU8 ? MODULO.HEAPU8.buffer.byteLength : null } catch { return null }
}

async function sha1(u8) {
  const h = await crypto.subtle.digest('SHA-1', u8)
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

self.onmessage = async (ev) => {
  const { bytes } = ev.data
  const mupdf = await import('mupdf')
  const { dibujosDePagina } = await import('../motor/pdf/dibujos.js')
  const { instrucciones, contenidoCrudo } = await import('../motor/pdf/contenido.js')
  const t0 = performance.now()
  let doc
  try {
    doc = mupdf.Document.openDocument(bytes, 'application/pdf')
  } catch (e) {
    self.postMessage({ error: 'no se pudo abrir el archivo: ' + (e && e.message) })
    return
  }
  const n = doc.countPages()
  const mesas = []
  let pico = memoriaWasm() || 0
  for (let i = 0; i < n; i++) {
    const page = doc.loadPage(i)
    let t = performance.now()
    const nDib = dibujosDePagina(mupdf, page).length
    const segDib = (performance.now() - t) / 1000
    pico = Math.max(pico, memoriaWasm() || 0)
    t = performance.now()
    const crudo = contenidoCrudo(page)
    let nIns = 0
    for (const _ of instrucciones(crudo)) nIns++          // eslint-disable-line no-unused-vars
    const segIns = (performance.now() - t) / 1000
    const h = await sha1(crudo)
    pico = Math.max(pico, memoriaWasm() || 0)
    mesas.push({ mesa: i + 1, dibujos: nDib, segundos_dibujos: segDib, bytes: crudo.length, sha1: h,
      instrucciones: nIns, segundos_instrucciones: segIns })
    self.postMessage({ avance: `mesa ${i + 1} de ${n}: ${nDib} dibujos (${segDib.toFixed(2)} s) · ${nIns} instrucciones (${segIns.toFixed(2)} s)` })
    page.destroy()
  }
  doc.destroy()
  self.postMessage({ listo: { mesas, segundos: (performance.now() - t0) / 1000, memoria_wasm: pico,
    nucleos: navigator.hardwareConcurrency || null, memoria_equipo_gb: navigator.deviceMemory || null,
    navegador: navigator.userAgent, bytes: bytes.byteLength } })
}
