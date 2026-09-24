// LA HOJA LISTA PARA EL RIP, REVISADA EN ESTA COMPUTADORA — 2026-09-22.
//
// 🔴 POR QUÉ: «el servidor será sólo para sostener el sistema y la base». Al guardar un pedido, el
// servidor volvía a abrir cada hoja con pikepdf para revisar que cualquier RIP la lea
// (`verificar_rip_compatible.verificar(balance=False, dibujar=False)`). Es la misma revisión,
// sobre la hoja que acaba de armar el hilo, antes de mandarla:
//   1. PDF 1.6 o anterior;
//   2. sin capas (ni /OCProperties ni /OC en los XObjects);
//   3. sin transparencia (/Group /Transparency, /SMask, opacidad < 1, fusión que no sea Normal);
//   4. XObjects de un solo nivel;
//   5. toda fuente con su archivo embebido;
//   6. sólo CMYK, Gray, ICC de 4 canales, Separation/DeviceN, Indexed y Pattern;
//   7. un solo perfil ICC por contenido (sin copias repetidas);
//   8. OutputIntent /GTS_PDFX con perfil CMYK (N=4).
// Devuelve `{ok, fallas}` con los mismos textos que el Python.
import { sha1HexBytes } from '../sha1.js'

const nulo = (o) => !o || (o.isNull && o.isNull())
const nombre = (o) => { try { return !nulo(o) && o.isName() ? o.asName() : null } catch { return null } }
const numero = (o, d = 0) => { try { return !nulo(o) && o.isNumber() ? Number(o.asNumber()) : d } catch { return d } }
const idDe = (o) => { try { return o.isIndirect() ? o.asIndirect() : null } catch { return null } }
const claves = (dict) => { const out = []; try { if (!nulo(dict)) dict.forEach((v, k) => out.push([String(k), v])) } catch { /* nada */ } return out }

function* xobjects(res, vistos, nivel = 0) {
  const xs = nulo(res) ? null : res.get('XObject')
  if (nulo(xs)) return
  for (const [, xo] of claves(xs)) {
    const og = idDe(xo)
    if (og !== null) { if (vistos.has(og)) continue; vistos.add(og) }
    yield [xo, nivel]
    if (nombre(xo.get('Subtype')) === 'Form') yield* xobjects(xo.get('Resources'), vistos, nivel + 1)
  }
}

function fuenteEmbebida(f) {
  try {
    if (nombre(f.get('Subtype')) === 'Type0') f = f.get('DescendantFonts').get(0)
    const fd = f.get('FontDescriptor')
    if (nulo(fd)) return nombre(f.get('Subtype')) === 'Type3'
    return ['FontFile', 'FontFile2', 'FontFile3'].some((k) => !nulo(fd.get(k)))
  } catch { return false }
}

function csOk(cs, iccHashes) {
  try {
    if (cs.isName()) return ['DeviceCMYK', 'DeviceGray', 'Pattern'].includes(cs.asName())
    if (cs.isArray() && cs.length) {
      const fam = nombre(cs.get(0))
      if (fam === 'ICCBased') {
        const st = cs.get(1)
        if (numero(st.get('N')) !== 4) return false
        const h = sha1HexBytes(st.readRawStream().asUint8Array())
        if (!iccHashes.has(h)) iccHashes.set(h, new Set())
        iccHashes.get(h).add(idDe(st))
        return true
      }
      if (fam === 'Separation' || fam === 'DeviceN') return csOk(cs.get(2), iccHashes)
      if (fam === 'Indexed') return csOk(cs.get(1), iccHashes)
      if (fam === 'Pattern') return true
      return fam === 'DeviceCMYK' || fam === 'DeviceGray'
    }
  } catch { return false }
  return false
}

/** `verificar(path, balance=False, dibujar=False)` sobre los bytes de la hoja. */
export function verificarRip(mupdf, bytes) {
  const fallas = []
  const mal = (cond, msg) => { if (!cond) fallas.push(msg) }
  // 1. la cabecera `%PDF-d.d`
  const ver = String.fromCharCode(...bytes.slice(5, 8))
  mal(ver <= '1.6', `versión PDF ${ver} (> 1.6)`)
  const pdf = new mupdf.PDFDocument(bytes)
  try {
    const root = pdf.getTrailer().get('Root')
    mal(nulo(root.get('OCProperties')), 'el catálogo tiene /OCProperties (capas)')
    const oi = root.get('OutputIntents')
    let okOi = false
    if (!nulo(oi) && oi.isArray() && oi.length) {
      const o = oi.get(0)
      const dp = o.get('DestOutputProfile')
      okOi = nombre(o.get('S')) === 'GTS_PDFX' && !nulo(dp) && numero(dp.get('N')) === 4
    }
    mal(okOi, 'sin OutputIntent /GTS_PDFX con perfil CMYK (/DestOutputProfile N=4)')
    const vistos = new Set(), iccHashes = new Map(), sinArchivo = [], csMalos = []
    for (let p = 0; p < pdf.countPages(); p++) {
      const pg = pdf.findPage(p)
      const contenedores = [pg]
      for (const [xo, nivel] of xobjects(pg.getInheritable('Resources'), vistos)) {
        if (nombre(xo.get('Subtype')) === 'Form') {
          contenedores.push(xo)
          mal(nivel === 0, `XObject anidado a profundidad ${nivel + 1}`)
          mal(nulo(xo.get('OC')), 'un XObject lleva /OC (capa)')
          const g = xo.get('Group')
          mal(!(!nulo(g) && nombre(g.get('S')) === 'Transparency'), 'un XObject tiene /Group /Transparency')
        } else {
          mal(nulo(xo.get('SMask')), 'una imagen lleva /SMask (transparencia)')
          const cs = xo.get('ColorSpace')
          if (!nulo(cs) && !csOk(cs, iccHashes)) csMalos.push(String(cs).slice(0, 40))
        }
      }
      for (const cont of contenedores) {
        const res = cont === pg ? pg.getInheritable('Resources') : cont.get('Resources')
        if (nulo(res)) continue
        const g = cont.get('Group')
        mal(!(!nulo(g) && nombre(g.get('S')) === 'Transparency'), 'la página tiene /Group /Transparency')
        for (const [k, gs] of claves(res.get('ExtGState'))) {
          try {
            if (!nulo(gs.get('SMask')) && nombre(gs.get('SMask')) !== 'None') fallas.push(`ExtGState /${k} con SMask`)
            if ((!nulo(gs.get('CA')) && numero(gs.get('CA'), 1) < 1) || (!nulo(gs.get('ca')) && numero(gs.get('ca'), 1) < 1)) fallas.push(`ExtGState /${k} con opacidad < 1`)
            const bm = gs.get('BM')
            if (!nulo(bm) && !['Normal', 'Compatible'].includes(nombre(bm))) fallas.push(`ExtGState /${k} con modo de fusión ${String(bm)}`)
          } catch { /* como el Python */ }
        }
        for (const [k, f] of claves(res.get('Font'))) {
          if (!fuenteEmbebida(f)) { let bf = k; try { bf = nombre(f.get('BaseFont')) || k } catch { /* nada */ } sinArchivo.push(bf) }
        }
        for (const [k, cs] of claves(res.get('ColorSpace'))) {
          if (!csOk(cs, iccHashes)) csMalos.push(`/${k}=${String(cs).slice(0, 40)}`)
        }
      }
    }
    mal(!sinArchivo.length, `fuentes sin archivo embebido: ${JSON.stringify([...new Set(sinArchivo)].sort().slice(0, 5))}`)
    mal(!csMalos.length, `espacios de color fuera de CMYK/Gray/ICC-4/Separation: ${JSON.stringify(csMalos.slice(0, 5))}`)
    const dup = [...iccHashes.values()].filter((ogs) => ogs.size > 1)
    mal(!dup.length, `${dup.length} perfil(es) ICC repetidos (${dup.reduce((a, s) => a + s.size, 0)} copias)`)
  } finally {
    try { pdf.destroy() } catch { /* nada */ }
  }
  return { ok: !fallas.length, fallas }
}
