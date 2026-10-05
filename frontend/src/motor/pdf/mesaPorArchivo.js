// UNA MESA = UN ARCHIVO (2026-10-05, MAPA 620).
//
// La hoja de una tela trae una PÁGINA por mesa. Al descargar, TIZADA guarda cada mesa como un PDF
// aparte con su nombre («Mesa 1 - Bandera», «Mesa 2 - Bandera - Fila 3 - x2»…). El pedido que llega
// de OTRO SISTEMA tiene que recibir exactamente lo mismo (pedido del usuario: «cada mesa es un
// archivo, así como hace al descargar»). Lo usan los dos lados:
//   · la pantalla: `obrero.worker.js` → `pagina_pdf` (el botón de cada mesa y «Descargar todo»);
//   · el robot de la integración (`robot/robot.mjs`), al guardar los PDF del pedido.

/**
 * El PDF de la página `pi` de una hoja (`bytes`): la página tal cual (con su `/UserUnit` si es una
 * mesa larga), el perfil de salida (OutputIntent) y PDF 1.6, como la hoja. Si la hoja tiene una
 * sola página, devuelve los mismos bytes.
 */
export function paginaComoPdf(mupdf, bytes, pi = 0) {
  const src = new mupdf.PDFDocument(bytes)
  try {
    const n = src.countPages()
    if (n <= 1) return bytes.slice()
    const p = pi >= 0 && pi < n ? pi : 0
    const dst = new mupdf.PDFDocument()
    try {
      dst.graftPage(0, src, p)
      const ois = src.getTrailer().get('Root').get('OutputIntents')
      if (ois && !ois.isNull()) dst.getTrailer().get('Root').put('OutputIntents', dst.graftObject(ois))
      try { dst.setMetaData('info:Creator', 'TIZADA PRO'); dst.setMetaData('info:Producer', 'TIZADA PRO') } catch { /* sin metadatos */ }
      const out = dst.saveToBuffer('garbage,compress').asUint8Array().slice()
      if (out[0] === 37 && out[1] === 80 && out[2] === 68 && out[3] === 70 && out[4] === 45) { out[5] = 49; out[6] = 46; out[7] = 54 }
      return out
    } finally {
      try { dst.destroy() } catch { /* nada */ }
    }
  } finally {
    try { src.destroy() } catch { /* nada */ }
  }
}

/**
 * El nombre de una mesa, el de la pantalla: «Mesa N - tela» y, si la hoja lo dice, la fila y las
 * copias (Copia, MAPA 581) o los talles (Talles por mesa, MAPA 593). `gi` = el número de mesa
 * DENTRO de su tela, desde 0.
 */
export function nombreMesaDef(gi, tela, mf) {
  let suf = ''
  if (mf && mf.copias != null) suf = (mf.fila ? ' - Fila ' + mf.fila : '') + ' - x' + mf.copias
  else if (mf && Array.isArray(mf.talles) && mf.talles.length) suf = ' - Talles ' + mf.talles.join('-')
  return 'Mesa ' + (gi + 1) + (tela ? ' - ' + tela : '') + suf
}

/** Un nombre de archivo sin los caracteres que Windows no admite (el mismo `sanit` de la pantalla). */
export const nombreArchivoSeguro = (s) => ((s || 'mesa').replace(/[\\/:*?"<>|\n\r\t]+/g, '_').trim() || 'mesa')

/**
 * Las mesas de un pedido en el ORDEN de «Descargar todo»: tela por tela (en el orden en que
 * aparecen), y dentro de cada tela sus hojas y sus páginas; el número de mesa vuelve a 1 en cada
 * tela. `hojas` = las del resultado (`{archivo, tela, paginas, mesas, alturas_cm, ancho_cm…}`).
 * → `[{hoja, pi, numero (1…), deLaTela (total de esa tela), nombre}]`.
 */
export function mesasEnOrden(hojas) {
  const out = []
  for (const tela of [...new Set((hojas || []).map((h) => h.tela))]) {
    const deTela = hojas.filter((h) => h.tela === tela)
    const total = deTela.reduce((n, h) => n + (h.paginas || 1), 0)
    let gi = 0
    for (const h of deTela) {
      for (let pi = 0; pi < (h.paginas || 1); pi++) {
        out.push({ hoja: h, pi, numero: gi + 1, deLaTela: total, nombre: nombreMesaDef(gi, tela, (h.mesas && h.mesas[pi]) || null) })
        gi++
      }
    }
  }
  return out
}
