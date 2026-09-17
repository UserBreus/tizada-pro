// EL TRABAJO PESADO, EN UN HILO APARTE DEL NAVEGADOR (PLAN_NAVEGADOR.md, §3).
//
// La pantalla nunca se congela: esto corre en un Web Worker. Mensajes:
//   ← { tipo: 'preparar_molde', archivo: File }
//   → { avance: { etapa, hecho, total, texto } }   (muchos)
//   → { listo: { zip: Uint8Array, sha1, resumen } } | { error: 'mensaje para la pantalla', codigo }
// Cancelar = `worker.terminate()`: se lleva la memoria de WebAssembly con él.

self.onmessage = async (ev) => {
  const { tipo, archivo } = ev.data || {}
  if (tipo !== 'preparar_molde') {
    self.postMessage({ error: `trabajo desconocido: ${tipo}` })
    return
  }
  const avisar = (etapa, hecho, total, texto) => self.postMessage({ avance: { etapa, hecho, total, texto } })
  try {
    avisar('abrir', 0, 1, 'Abriendo el archivo en tu computadora…')
    const bytes = new Uint8Array(await archivo.arrayBuffer())
    const mupdf = await import('mupdf')
    const { desplegarMolde } = await import('./molde/desplegar.js')
    const { armarPaqueteMolde } = await import('./paquete/armar.js')
    const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
    const TEXTO = { contornos: 'Detectando las piezas', etiquetas: 'Buscando la etiqueta del diseño', paginas: 'Separando los talles' }
    const r = desplegarMolde(mupdf, doc, {
      avisar: (etapa, hecho, total) => avisar(etapa, hecho, total, `${TEXTO[etapa] || etapa} · mesa ${hecho} de ${total}`),
    })
    doc.destroy()
    avisar('paquete', 0, 1, 'Armando el paquete para guardar…')
    const { zip, sha1 } = armarPaqueteMolde(bytes, r, { motor: 'mupdf.js · navegador' })
    const resumen = { mesas: r.alta.mesas, talles: r.alta.talles, piezas: r.alta.registro.size }
    self.postMessage({ listo: { zip, sha1, resumen } }, [zip.buffer])
  } catch (e) {
    const msg = String((e && e.message) || e)
    // Sin memoria: WebAssembly de 32 bits tiene 4 GB por pestaña, y la computadora puede tener menos.
    const sinMemoria = /memory|out of bounds|allocation|RangeError|Array buffer allocation/i.test(msg)
    self.postMessage({
      error: sinMemoria
        ? 'Esta computadora no tiene memoria suficiente para preparar este molde. Cerrá otras pestañas o programas y volvé a intentarlo, o usá una computadora con más memoria.'
        : `No se pudo preparar el molde en tu computadora: ${msg}`,
      codigo: sinMemoria ? 'sin_memoria' : 'error',
    })
  }
}
