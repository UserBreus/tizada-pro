// EL MOLDE DESPLEGADO ENTERO, EN EL NAVEGADOR (PLAN_NAVEGADOR.md, etapa 1).
//
// Es `piezas_con_diseno.alta_molde_con_diseno(paginas=True)` sin escribir en disco: el resultado
// queda en memoria para armar el PAQUETE que se manda al servidor con «Guardar». El orden es el del
// Python: 1) los contornos de todas las mesas; 2) la decisión de la etiqueta que trae el diseño
// (por familia, con los candidatos de TODAS las mesas); 3) las páginas por talle de cada mesa, con
// esa decisión aplicada; 4) el registro y el visor.

import { dibujosDePagina } from '../pdf/dibujos.js'
import { tallesDelMolde, geometriaPagina, contornosDeMesa, altaDesdeContornos } from './contornos.js'
import { buscarCandidatosMesa, decidirFamilias, familiasOcultas, hashOcultas, paginasDeTalles, V_ETQ } from './paginas.js'

export const V_CONTORNOS = 4
export const V_PAGINAS = 6

function contenidoDe(page) {
  const obj = page.getObject()
  const c = obj.get('Contents')
  if (!c || c.isNull()) return new Uint8Array(0)
  if (c.isArray()) {
    const partes = []
    for (let i = 0; i < c.length; i++) partes.push(c.get(i).readStream().asUint8Array().slice())
    const u8 = new Uint8Array(partes.reduce((a, x) => a + x.length, 0) + Math.max(0, partes.length - 1))
    let p = 0
    partes.forEach((x, k) => { if (k) u8[p++] = 10; u8.set(x, p); p += x.length })
    return u8
  }
  return c.readStream().asUint8Array().slice()
}

/**
 * `avisar(etapa, hecho, total, texto)` recibe el avance. `manual` = lo que el usuario fijó a mano
 * sobre las familias de la etiqueta (se conserva, como en el Python).
 * Devuelve `{talles, mesas: Map(mesa → {json, pdf}), etiqueta, alta}`.
 */
export function desplegarMolde(mupdf, doc, { avisar = null, manual = {} } = {}) {
  const talles = tallesDelMolde(doc)
  const n = doc.countPages()
  const mesas = new Map()
  const porMesa = new Map(), geos = new Map()

  // 1) contornos
  for (let m = 1; m <= n; m++) {
    const page = doc.loadPage(m - 1)
    const geo = geometriaPagina(page)
    geos.set(m, geo)
    if (talles.length) {
      // lectura LIGERA (sin recorrer los rellenos del diseño); la completa sólo si hace falta el respaldo
      let completos = null
      const r = contornosDeMesa(dibujosDePagina(mupdf, page, { ligero: true }), geo, m, talles,
        () => (completos = completos || dibujosDePagina(mupdf, page)))
      mesas.set(m, { json: { sello: null, orden: talles.slice(), talles: r.talles, v: V_CONTORNOS, paginas: false, marco: r.marco, U: r.U } })
      if (r.talles.size) porMesa.set(m, r.talles)
    }
    page.destroy()
    if (avisar) avisar('contornos', m, n, `mesa ${m} de ${n}`)
  }
  if (!talles.length) {
    return { talles, mesas, etiqueta: null, alta: altaDesdeContornos(porMesa, geos, talles, n) }
  }

  // 2) la etiqueta que trae el diseño
  const cands = []
  for (let m = 1; m <= n; m++) {
    const { json } = mesas.get(m)
    const page = doc.loadPage(m - 1)
    const recursos = page.getObject().get('Resources')
    cands.push(...buscarCandidatosMesa(contenidoDe(page), recursos, m, talles, json.talles, json.marco, json.U))
    page.destroy()
    if (avisar) avisar('etiquetas', m, n, `etiquetas · mesa ${m}`)
  }
  const total = new Set()
  for (let m = 1; m <= n; m++) {
    for (const lst of mesas.get(m).json.talles.values()) lst.forEach((_, i) => total.add(`${m}|${i}`))
  }
  const etiqueta = { sello: null, v: V_ETQ, piezas: total.size, familias: decidirFamilias(cands, total.size, manual), manual }
  const ocultar = familiasOcultas(etiqueta)
  const etq = hashOcultas(ocultar)

  // 3) las páginas por talle
  for (let m = 1; m <= n; m++) {
    const entrada = mesas.get(m)
    const j = entrada.json
    const r = paginasDeTalles(mupdf, doc, m, talles, j.talles, j.marco, j.U, ocultar)
    entrada.pdf = r.pdf
    entrada.json = { sello: null, orden: j.orden, talles: j.talles, paginas: true, v: V_CONTORNOS, vp: V_PAGINAS,
      marco: j.marco, U: j.U, placeholders: r.placeholders, linea_corte: r.lineas,
      etiqueta_archivo: r.etiqueta_archivo, etq }
    if (avisar) avisar('paginas', m, n, `páginas por talle · mesa ${m} de ${n}`)
  }

  // 4) el registro y el visor
  return { talles, mesas, etiqueta, alta: altaDesdeContornos(porMesa, geos, talles, n) }
}
