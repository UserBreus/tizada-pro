// EL PERFIL DE COLOR QUE TRAE EL ARTE, LEÍDO EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». `GET /api/arte/perfil`
// abría el arte con pikepdf y recorría todos sus recursos buscando un perfil ICC, y le leía el
// nombre con LittleCMS (`ImageCms.getProfileName`). Es la traducción de
// `servidor._detectar_perfil_incrustado`: OutputIntent → ICCBased en cualquier recurso → el
// modelo de color del encabezado de Illustrator. Devuelve `{tiene, nombre, espacio}`; la
// comparación con el perfil predeterminado sigue en el servidor (son datos de configuración).

const u32 = (b, o) => ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0
const u16 = (b, o) => (b[o] << 8) | b[o + 1]
const sig = (b, o) => String.fromCharCode(b[o], b[o + 1], b[o + 2], b[o + 3])

/** El texto de una etiqueta ICC (`desc`/`dmnd`/`dmdd`) como lo da LittleCMS (inglés si hay). */
function textoEtiqueta(b, nombre) {
  if (b.length < 132) return ''
  const n = u32(b, 128)
  for (let i = 0; i < n; i++) {
    const e = 132 + i * 12
    if (e + 12 > b.length) break
    if (sig(b, e) !== nombre) continue
    const o = u32(b, e + 4)
    if (o + 12 > b.length) return ''
    const tipo = sig(b, o)
    if (tipo === 'desc') {
      const cnt = u32(b, o + 8)
      let s = ''
      for (let k = 0; k < cnt && o + 12 + k < b.length; k++) { const c = b[o + 12 + k]; if (!c) break; s += String.fromCharCode(c) }
      return s
    }
    if (tipo === 'text') {
      let s = ''
      for (let k = o + 8; k < b.length; k++) { const c = b[k]; if (!c) break; s += String.fromCharCode(c) }
      return s
    }
    if (tipo === 'mluc') {
      const nr = u32(b, o + 8), tam = u32(b, o + 12)
      let elegido = null
      for (let r = 0; r < nr; r++) {
        const p = o + 16 + r * tam
        const lang = String.fromCharCode(b[p], b[p + 1]), pais = String.fromCharCode(b[p + 2], b[p + 3])
        const reg = { largo: u32(b, p + 4), ofs: u32(b, p + 8) }
        if (elegido === null) elegido = reg                           // lo primero, si no hay inglés
        if (lang === 'en' && (pais === 'US' || !elegido.en)) { elegido = { ...reg, en: true }; if (pais === 'US') break }
      }
      if (!elegido) return ''
      let s = ''
      for (let k = 0; k + 1 < elegido.largo; k += 2) {
        const c = u16(b, o + elegido.ofs + k)
        if (!c) break
        s += String.fromCharCode(c)
      }
      return s
    }
    return ''
  }
  return ''
}

/** `ImageCms.getProfileName(...).strip()`: «modelo - fabricante», el modelo, o la descripción. */
export function nombreDePerfil(icc) {
  try {
    const model = textoEtiqueta(icc, 'dmdd'), manufacturer = textoEtiqueta(icc, 'dmnd')
    let s
    if (!(model || manufacturer)) s = textoEtiqueta(icc, 'desc') || ''
    else if (!manufacturer || (model && model.length > 30)) s = model
    else s = `${model} - ${manufacturer}`
    return s.trim() || null
  } catch { return null }
}

const nulo = (o) => !o || (o.isNull && o.isNull())

/** `_detectar_perfil_incrustado` sobre los bytes del arte. */
export function detectarPerfilIncrustado(mupdf, bytes) {
  let nombre = null, espacio = null
  let doc = null
  try {
    doc = new mupdf.PDFDocument(bytes)
    const root = doc.getTrailer().get('Root')
    const ois = root.get('OutputIntents')
    if (!nulo(ois) && ois.isArray()) {
      for (let i = 0; i < ois.length && !nombre; i++) {
        const oi = ois.get(i)
        const dop = oi.get('DestOutputProfile')
        if (!nulo(dop)) { const n = nombreDePerfil(dop.readStream().asUint8Array()); if (n) { nombre = n; break } }
        let info = oi.get('Info')
        if (nulo(info)) info = oi.get('OutputConditionIdentifier')
        if (!nulo(info) && !nombre) { try { nombre = info.isString() ? info.asString() : String(info) } catch { /* nada */ } }
      }
    }
    if (!nombre) {
      const vistos = new Set()
      const recorrer = (obj, d = 0) => {
        if (d > 8 || nombre || nulo(obj)) return
        try {
          if (obj.isIndirect()) { const k = obj.asIndirect(); if (vistos.has(k)) return; vistos.add(k) }
          if (obj.isArray() && obj.length >= 2 && obj.get(0).isName() && obj.get(0).asName() === 'ICCBased') {
            const st = obj.get(1)
            const n = nombreDePerfil(st.readStream().asUint8Array())
            if (n) nombre = n
            const nn = st.get('N')
            if (!nulo(nn)) espacio = { 1: 'GRAY', 3: 'RGB', 4: 'CMYK' }[Number(nn.asNumber())] || espacio
          }
        } catch { /* como el Python: sigue */ }
        // como el Python: sólo se entra por las claves de los diccionarios (un arreglo se mira a
        // ver si ES un ICCBased, pero no se recorre)
        try { if (obj.isDictionary()) obj.forEach((v) => recorrer(v, d + 1)) } catch { /* nada */ }
      }
      for (let p = 0; p < doc.countPages() && !nombre; p++) recorrer(doc.findPage(p))
    }
  } catch { /* sin PDF legible: sólo el encabezado */ }
  finally { if (doc) { try { doc.destroy() } catch { /* nada */ } } }
  if (espacio === null) {
    let t = ''
    for (let i = 0; i < Math.min(60000, bytes.length); i++) t += String.fromCharCode(bytes[i])
    const m = t.match(/AI9_ColorModel:\s*(\d+)/)
    if (m) espacio = { 0: 'GRAY', 1: 'RGB', 2: 'CMYK' }[Number(m[1])] || 'CMYK'
  }
  return { tiene: !!nombre, nombre, espacio: espacio || 'CMYK' }
}
