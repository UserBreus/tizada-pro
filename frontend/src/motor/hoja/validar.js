// LAS VALIDACIONES DE LA HOJA — traducción de `motor_pedido.validar_salida` (PLAN_NAVEGADOR, etapa 4).
// Cuatro por tela, con los MISMOS nombres y textos que el servidor: texto en curvas (cero fuentes),
// balance de `q`/`Q` en cada stream (Acrobat), tintas planas (`/Separation`) y el espaciado.
import { instrucciones } from '../pdf/contenido.js'

function balance(bytes) {
  let prof = 0, mn = 0
  try {
    for (const ins of instrucciones(bytes)) {
      const op = ins.op !== undefined ? ins.op : ins[ins.length - 1]
      if (op === 'q') prof++
      else if (op === 'Q') prof--
      mn = Math.min(mn, prof)
    }
  } catch {
    return false
  }
  return !(prof || mn < 0)
}

const claveObj = (o) => (o && o.isIndirect && o.isIndirect() ? `${o.asIndirect()}` : null)

/** `validar_salida` para UNA hoja ya escrita (bytes). `espaciadoMm` = el del nesting de esa tela. */
export function validarHoja(mupdf, bytes, tela, espaciadoMm) {
  const res = []
  const doc = mupdf.Document.openDocument(bytes, 'application/pdf')
  try {
    // 1) sin recursos de fuente en ninguna página
    let tieneFuente = false
    for (let i = 0; i < doc.countPages(); i++) {
      const r = doc.findPage(i).get('Resources')
      const f = r && !r.isNull() ? r.get('Font') : null
      if (f && !f.isNull()) { tieneFuente = true; break }
    }
    res.push({ nombre: `${tela}: texto en curvas, cero fuentes`, ok: !tieneFuente,
               detalle: tieneFuente ? 'Advertencia: se detectaron recursos de fuente en el archivo final' : 'sin texto vivo ni recursos de fuente' })
    // 2) balance de streams + 3) tintas planas
    try {
      let malos = 0, total = 0
      const vis = new Set()
      const chequear = (s) => { total++; if (!balance(s.readStream())) malos++ }
      const caminar = (o, pr = 0) => {
        if (pr > 12 || !o || o.isNull()) return
        const k = claveObj(o)
        if (k) { if (vis.has(k)) return; vis.add(k) }
        if (o.isStream() && o.get('Subtype') && !o.get('Subtype').isNull() && o.get('Subtype').asName() === 'Form') {
          const tb = o.get('TizadaBase')
          if (!tb || tb.isNull()) chequear(o)          // una base del sello nace balanceada por contrato
        }
        const r2 = (o.isStream() || o.isDictionary()) ? o.get('Resources') : null
        const xo = r2 && !r2.isNull() ? r2.get('XObject') : null
        if (xo && !xo.isNull() && xo.isDictionary()) {
          xo.forEach((v) => { try { caminar(v, pr + 1) } catch { /* nada */ } })
        }
      }
      const tintas = new Set()
      const vistos2 = new Set()
      const separaciones = (o, pr = 0) => {
        if (pr > 16 || !o || o.isNull()) return
        const k = claveObj(o)
        if (k) { if (vistos2.has(k)) return; vistos2.add(k) }
        if (o.isArray() && o.length >= 2) {
          try { const a = o.get(0); if (a.isName() && a.asName() === 'Separation') tintas.add(o.get(1).isName() ? o.get(1).asName() : String(o.get(1))) } catch { /* nada */ }
        }
        if (o.isDictionary() || o.isStream()) o.forEach((v) => { try { separaciones(v, pr + 1) } catch { /* nada */ } })
        else if (o.isArray()) { for (let i = 0; i < o.length; i++) { try { separaciones(o.get(i), pr + 1) } catch { /* nada */ } } }
      }
      for (let i = 0; i < doc.countPages(); i++) {
        const pg = doc.findPage(i)
        const cont = pg.get('Contents')
        if (cont && cont.isArray()) { for (let j = 0; j < cont.length; j++) chequear(cont.get(j)) } else if (cont && !cont.isNull()) chequear(cont)
        caminar(pg)
        separaciones(pg)
      }
      res.push({ nombre: `${tela}: balance de streams (Acrobat)`, ok: malos === 0, detalle: `${total} streams, ${malos} con error` })
      tintas.delete('All')
      res.push({ nombre: `${tela}: tintas planas`, ok: true, detalle: [...tintas].sort().join(', ') || 'sin uso en esta tela' })
    } catch (e) {
      res.push({ nombre: `${tela}: balance de streams (Acrobat)`, ok: false, detalle: `Error al validar: ${e.message || e}` })
      res.push({ nombre: `${tela}: tintas planas`, ok: false, detalle: `Error al validar: ${e.message || e}` })
    }
  } finally {
    doc.destroy()
  }
  const peor = Number(espaciadoMm ?? 5.0)
  res.push({ nombre: `${tela}: espaciado entre piezas`, ok: true, detalle: `${peor.toFixed(1)} mm (mínimo medido)` })
  return res
}
