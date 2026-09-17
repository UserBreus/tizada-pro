// APLANAR LA HOJA PARA EL RIP, EN EL NAVEGADOR (PLAN_NAVEGADOR.md, etapa 4, punto 3).
//
// Traducción de `aplanar_rip.py` (`_aplanar_archivo`) sobre la API de objetos de mupdf.js. Deja la
// hoja como el PDF que exporta Illustrator, que es el que el RIP acepta:
//   1. DES-ANIDA los Form XObjects: lo de adentro pasa al stream que los usaba, envuelto en
//      `q [Matrix cm] [BBox re W n] … Q` (la misma receta, byte a byte, que el Python).
//   2. CONSOLIDA los perfiles ICC repetidos en uno solo (por hash de los bytes crudos).
//   3. DECLARA el estado gráfico (`/GSflat`: overprint apagado, stroke adjust) y saca de los
//      ExtGState las claves que un preflight lee como transparencia cuando ya valen lo opaco.
//   4. Saca las capas OCG (marcadores BDC/EMC, `/Properties`, `/OC`, `/OCProperties`) y los bloques
//      de texto fantasma (fuente inexistente o sin glifos).
//   5. Guarda con recolección de basura, comprimido, PDF 1.6.
// TODO preservando los valores CMYK EXACTOS: los operandos de color se copian tal cual (el lector y
// el escritor de `pdf/contenido.js` reescriben los mismos bytes que pikepdf).
//
// Dos modos, como el Python: UN NIVEL (default: la página conserva sus `Do` y se sanea el interior
// de cada Form una vez) y TOTAL (`total: true` = `TIZADA_APLANADO_TOTAL=1`: todo inline).
//
// 🔴 LO QUE HAY QUE SABER DE mupdf.js PARA LEER ESTO:
//   · Los reales de un objeto PDF se guardan en float32 (`asNumber()` de `48.00004` da
//     48.000038146972656). Para escribir `%.6f` como Python hay que recuperar el decimal original:
//     `num32` busca la representación más corta que vuelve al mismo float32.
//   · `get()` resuelve las referencias al leer, pero el valor que entrega `forEach` es la referencia
//     cruda: al copiarla a otro diccionario (`put`) se copia la referencia, no el objeto — igual que
//     `d[nm] = obj` en pikepdf. La identidad de un objeto es su número (`asIndirect()`); un objeto
//     directo vale 0, como el `(0, 0)` de pikepdf.
//   · `writeStream` deja el stream sin filtro (mupdf lo comprime al guardar con `compress`).
//   · El contrato `verificar_navegador_aplanar.py` compara la salida con la del servidor.

import { instrucciones as parsear, escribir } from '../pdf/contenido.js'
import { pyFixed } from '../py.js'
import { sha1HexBytes } from '../sha1.js'

const RES_KINDS = ['ColorSpace', 'XObject', 'Font', 'ExtGState', 'Shading', 'Pattern', 'Properties']
const OPKIND = { Do: 'XObject', gs: 'ExtGState', cs: 'ColorSpace', CS: 'ColorSpace', scn: 'ColorSpace',
  SCN: 'ColorSpace', sh: 'Shading', Tf: 'Font', BDC: 'Properties', DP: 'Properties' }
const OPS_CS = new Set(['cs', 'CS', 'scn', 'SCN'])
const OPS_MARCA = new Set(['BDC', 'BMC', 'EMC', 'MP', 'DP'])
const OPS_TEXTO = new Set(['Tj', 'TJ', "'", '"'])

const nulo = (o) => !o || o.isNull()
const esNombre = (o, n) => !nulo(o) && o.isName() && o.asName() === n
const idDe = (o) => (!nulo(o) && o.isIndirect()) ? o.asIndirect() : 0
const esForm = (o) => !nulo(o) && o.isStream() && esNombre(o.get('Subtype'), 'Form')

/** Las claves de un diccionario (una foto: se puede borrar mientras se recorre), EN EL ORDEN DE
 *  qpdf: pikepdf recorre `keys()` ordenadas por bytes («/CS0» < «/CS0_fl1»); mupdf guarda las
 *  entradas en el orden en que llegaron. Del orden dependen los nombres `_flN` y cuál de dos
 *  perfiles ICC iguales queda como canónico: con el mismo orden, la misma salida. */
function claves(d) {
  const out = []
  if (nulo(d)) return out
  d.resolve().forEach((v, k) => out.push([String(k), v]))
  return out.sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))
}

/** El valor float32 que guarda mupdf → el decimal que se escribió (el más corto que vuelve al mismo
 *  float32). Con hasta 7 cifras significativas lo recupera exacto; con más, lo mejor posible. */
export function num32(x) {
  if (!Number.isFinite(x) || Number.isInteger(x)) return x
  for (let p = 1; p <= 9; p++) {
    const s = x.toPrecision(p)
    if (Math.fround(Number(s)) === x) return Number(s)
  }
  return x
}
const num6 = (x) => ({ r: pyFixed(num32(x), 6) })          // `f"{float(v):.6f}"` como operando real

const latin1 = (s) => { const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255; return u }

/** Los bytes del contenido de una página (varios streams se unen con '\n', como qpdf) o de un XObject. */
function bytesContenido(obj, esPagina) {
  if (!esPagina) return obj.readStream().asUint8Array().slice()
  const c = obj.get('Contents')
  if (nulo(c)) return new Uint8Array(0)
  if (c.isArray()) {
    const partes = []
    for (let i = 0; i < c.length; i++) partes.push(c.get(i).readStream().asUint8Array().slice())
    const out = new Uint8Array(partes.reduce((a, x) => a + x.length, 0) + Math.max(0, partes.length - 1))
    let p = 0
    partes.forEach((x, k) => { if (k) out[p++] = 10; out.set(x, p); p += x.length })
    return out
  }
  return c.readStream().asUint8Array().slice()
}

// ─── `_merge_res`: los recursos del XObject pasan al contenedor; los que chocan se renombran ──
function mergeRes(doc, dst, src) {
  const remap = {}
  for (const kind of RES_KINDS) {
    const s = nulo(src) ? null : src.get(kind)
    if (nulo(s)) continue
    let d = dst.get(kind)
    if (nulo(d)) { d = doc.newDictionary(); dst.put(kind, d) }
    for (const [nm, obj] of claves(s)) {
      if (kind === 'XObject' && esForm(obj)) continue     // los Form ya se inlinearon → NO mergearlos (quedarían huérfanos)
      const ya = d.get(nm)
      if (!nulo(ya)) {
        if (idDe(ya) === idDe(obj)) continue              // el mismo objeto (o dos directos: pikepdf los ve iguales)
        let i = 1
        while (!nulo(d.get(`${nm}_fl${i}`))) i++
        const nuevo = `${nm}_fl${i}`
        d.put(nuevo, obj)
        ;(remap[kind] ||= {})[nm] = nuevo
      } else d.put(nm, obj)
    }
  }
  return remap
}

/** `_remap_ops`: renombra los recursos que `remap` dice; las demás instrucciones quedan TAL CUAL. */
function remapOps(ops, remap) {
  if (!Object.keys(remap).length) return ops
  const out = []
  for (let inst of ops) {
    const k = OPKIND[inst.op]
    if (k && remap[k]) {
      const r = remap[k]
      inst = { op: inst.op, args: inst.args.map((o) => (o && o.n !== undefined) ? { n: (r[o.n] ?? o.n) } : o) }
    }
    out.push(inst)
  }
  return out
}

// ─── `_flatten`: des-anida los Form XObjects del contenedor ──────────────────────────────────
/** Devuelve las instrucciones ya aplanadas. `hechos` (por objeto) evita aplanar dos veces el mismo
 *  XObject: cada `Do` de la misma pieza reusa sus instrucciones, como en el Python. */
function flatten(doc, cont, esPagina, hechos) {
  const id = idDe(cont) || null
  if (id !== null && hechos.has(id)) return hechos.get(id)
  const ops = [...parsear(bytesContenido(cont, esPagina))]
  const res = cont.get('Resources')
  const xobjs = nulo(res) ? null : res.get('XObject')
  if (nulo(xobjs) || !ops.length) {
    if (id !== null) hechos.set(id, ops)
    return ops
  }
  const nuevos = []
  for (const inst of ops) {
    if (inst.op === 'Do' && inst.args.length && inst.args[0] && inst.args[0].n !== undefined) {
      const xo = xobjs.get(inst.args[0].n)
      if (esForm(xo)) {
        let sub = flatten(doc, xo, false, hechos)
        const remap = mergeRes(doc, res, xo.get('Resources'))
        sub = remapOps(sub, remap)
        nuevos.push({ op: 'q', args: [] })
        const mtx = xo.get('Matrix')
        if (!nulo(mtx)) {
          const a = []
          for (let i = 0; i < mtx.length; i++) a.push(num6(mtx.get(i).asNumber()))
          nuevos.push({ op: 'cm', args: a })
        }
        const bbox = xo.get('BBox')
        if (!nulo(bbox)) {
          const [x0, y0, x1, y1] = [0, 1, 2, 3].map((i) => num32(bbox.get(i).asNumber()))
          nuevos.push({ op: 're', args: [Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)].map((v) => ({ r: pyFixed(v, 6) })) })
          nuevos.push({ op: 'W', args: [] })
          nuevos.push({ op: 'n', args: [] })
        }
        for (const s of sub) nuevos.push(s)
        nuevos.push({ op: 'Q', args: [] })
        continue
      }
    }
    nuevos.push(inst)
  }
  if (id !== null) hechos.set(id, nuevos)
  // (El Python escribe acá el contenido de la página y `_procesar_contenido` lo vuelve a escribir
  // enseguida con las mismas instrucciones saneadas: ese stream intermedio nunca llega al archivo,
  // así que acá no se escribe.)
  return nuevos
}

// ─── `_procesar_contenido`: UNA pasada que sanea el contenido y los recursos ─────────────────
/** (1) saca los bloques de texto fantasma, (2) saca los marcadores de capa, (3) remapea los
 *  ICCBased duplicados al canónico, (4) borra los XObjects que ya nadie usa; y limpia el residuo OCG. */
function procesarContenido(doc, cont, ops, esXObj) {
  const res = cont.get('Resources')
  const remap = {}
  const cs = nulo(res) ? null : res.get('ColorSpace')
  const entradasCs = claves(cs)                            // (`length` en mupdf.js es sólo de arreglos)
  if (entradasCs.length) {
    const porHash = {}
    for (const [nm, v] of entradasCs) {
      try {
        if (v.isArray() && esNombre(v.get(0), 'ICCBased')) {
          const h = sha1HexBytes(v.get(1).readRawStream().asUint8Array())
          if (h in porHash) { remap[nm] = porHash[h]; cs.delete(nm) } else porHash[h] = nm
        }
      } catch { /* como el Python: un ColorSpace raro se deja */ }
    }
  }
  const fuentes = new Set(nulo(res) ? [] : claves(res.get('Font')).map(([k]) => k))
  const hayRemap = Object.keys(remap).length > 0
  const rmp = (inst) => {
    if (hayRemap && OPS_CS.has(inst.op)) {
      return { op: inst.op, args: inst.args.map((o) => (o && o.n !== undefined) ? { n: (remap[o.n] ?? o.n) } : o) }
    }
    return inst                                            // sin cambio: la MISMA instrucción
  }
  const usados = new Set()
  if (ops !== null) {
    const out = []
    let bloque = [], enBT = false, faltaFuente = false, tieneTexto = false
    for (const inst of ops) {
      const o = inst.op
      if (OPS_MARCA.has(o)) continue                       // marcador de capa/estructura → fuera (no marca nada)
      if (o === 'BT') { enBT = true; bloque = [inst]; faltaFuente = tieneTexto = false; continue }
      if (enBT) {
        bloque.push(rmp(inst))
        if (o === 'Tf') {
          const a = inst.args
          if (a.length && a[0] && a[0].n !== undefined && !fuentes.has(a[0].n)) faltaFuente = true
        } else if (OPS_TEXTO.has(o)) tieneTexto = true
        if (o === 'ET') {
          enBT = false
          if (!(faltaFuente || !tieneTexto)) for (const b of bloque) out.push(b)   // bloque válido → se conserva
          bloque = []
        }
        continue
      }
      if (o === 'Do' && inst.args.length && inst.args[0] && inst.args[0].n !== undefined) usados.add(inst.args[0].n)
      out.push(rmp(inst))
    }
    const bytes = escribir(out)
    if (esXObj) cont.writeStream(bytes)
    else cont.put('Contents', doc.addStream(bytes, doc.newDictionary()))
  }
  const xo = nulo(res) ? null : res.get('XObject')
  if (!nulo(xo) && ops !== null) {
    for (const [nm] of claves(xo)) if (!usados.has(nm)) xo.delete(nm)
  }
  if (!nulo(res)) {
    if (!nulo(res.get('Properties'))) res.delete('Properties')
    for (const [, v] of claves(res.get('XObject'))) {
      try { if (!nulo(v.get('OC'))) v.delete('OC') } catch { /* nada */ }
    }
  }
  const root = doc.getTrailer().get('Root')
  if (!nulo(root.get('OCProperties'))) root.delete('OCProperties')
}

// ─── `_declarar_estado_grafico` ──────────────────────────────────────────────────────────────
function declararEstadoGrafico(doc, page) {
  let res = page.get('Resources')
  if (nulo(res)) { res = doc.newDictionary(); page.put('Resources', res) }
  let eg = res.get('ExtGState')
  if (nulo(eg)) { eg = doc.newDictionary(); res.put('ExtGState', eg) }
  for (const [, v] of claves(eg)) {
    if (esNombre(v.get('SMask'), 'None')) v.delete('SMask')
    if (esNombre(v.get('BM'), 'Normal')) v.delete('BM')
    try {
      const ca = v.get('CA'), ca2 = v.get('ca')
      if (!nulo(ca) && ca.isNumber() && ca.asNumber() === 1) v.delete('CA')
      if (!nulo(ca2) && ca2.isNumber() && ca2.asNumber() === 1) v.delete('ca')
    } catch { /* nada */ }
    const ais = v.get('AIS')
    if (!nulo(ais) && ais.isBoolean() && ais.asBoolean() === false) v.delete('AIS')
  }
  const gs = doc.newDictionary()
  gs.put('Type', doc.newName('ExtGState'))
  gs.put('OP', doc.newBoolean(false))
  gs.put('op', doc.newBoolean(false))
  gs.put('OPM', doc.newInteger(1))
  gs.put('SA', doc.newBoolean(true))
  eg.put('GSflat', doc.addObject(gs))
  let cont = page.get('Contents')
  if (!nulo(cont) && cont.isArray()) cont = cont.get(0)
  const viejo = nulo(cont) ? new Uint8Array(0) : cont.readStream().asUint8Array().slice()
  const cab = latin1('/GSflat gs\n')
  const nuevo = new Uint8Array(cab.length + viejo.length)
  nuevo.set(cab); nuevo.set(viejo, cab.length)
  page.put('Contents', doc.addStream(nuevo, doc.newDictionary()))
}

// ─── `_aplanar_un_nivel` (default) ───────────────────────────────────────────────────────────
function aplanarUnNivel(doc, page, hechos) {
  const res = page.get('Resources')
  const xobjs = nulo(res) ? null : res.get('XObject')
  if (!nulo(xobjs)) {
    for (const [nm] of claves(xobjs)) {
      const xo = xobjs.get(nm)
      if (!esForm(xo)) continue
      const id = idDe(xo) || null
      if (id !== null && hechos.has(id)) continue
      const r = xo.get('Resources')
      if (!nulo(xo.get('TizadaBase')) && (nulo(r) || nulo(r.get('XObject')))) {
        // Base de la hoja compartida: nace de una página desplegada, sin marcadores de capa y con
        // las fuentes declaradas. No se parsea (el Python tampoco).
        if (id !== null) hechos.set(id, true)
        for (const k of ['OC', 'Group']) if (!nulo(xo.get(k))) xo.delete(k)
        continue
      }
      const sub = flatten(doc, xo, false, hechos)          // des-anida lo de ADENTRO
      procesarContenido(doc, xo, sub, true)                // y lo sanea, una vez
      if (id !== null) hechos.set(id, sub)
      if (!nulo(xo.get('OC'))) xo.delete('OC')
      if (!nulo(xo.get('Group'))) xo.delete('Group')       // sin grupos de transparencia
    }
  }
  const ops = [...parsear(bytesContenido(page, true))]
  procesarContenido(doc, page, ops, false)                 // la página: sus propios trazos + los Do
  declararEstadoGrafico(doc, page)
}

// ─── `_unificar_icc`: un solo stream por perfil en TODO el archivo ──────────────────────────
function unificarIcc(doc) {
  const canon = new Map(), vistos = new Set()
  const recorrer = (d) => {
    if (nulo(d)) return
    for (const [, v] of claves(d.get('ColorSpace'))) {
      {
        try {
          if (v.isArray() && esNombre(v.get(0), 'ICCBased')) {
            const st = v.get(1)
            const h = sha1HexBytes(st.readRawStream().asUint8Array())
            if (canon.has(h)) { if (idDe(st) !== idDe(canon.get(h))) v.put(1, canon.get(h)) } else canon.set(h, st)
          }
        } catch { /* nada */ }
      }
    }
    for (const [, xo] of claves(d.get('XObject'))) {
      const og = idDe(xo)
      if (vistos.has(og)) continue
      vistos.add(og)
      recorrer(xo.get('Resources'))
    }
  }
  for (let i = 0; i < doc.countPages(); i++) recorrer(doc.findPage(i).get('Resources'))
}

// ─── `pdf.remove_unreferenced_resources()` de pikepdf (QPDFPageObjectHelper) ────────────────
// qpdf sólo filtra `/Font` y `/XObject`. Un recurso «se usa» si su nombre es el ÚLTIMO nombre
// que apareció antes de un operador de recurso (cs/CS/gs/Tf/scn/SCN/sh/Do): el nombre queda
// pegado hasta que aparece otro, así que `/CS0 cs 0 0 0 1 scn` cuenta CS0 también como patrón.
// El conjunto de nombres es UNO para todos los tipos: una fuente que se llame como un XObject
// usado se conserva. Los Form anidados se procesan primero; lo que usan y no declaran queda
// «sin resolver» y la página no lo borra (los Form viejos heredaban recursos de la página).
const QPDF_OPS = { CS: 'ColorSpace', cs: 'ColorSpace', gs: 'ExtGState', Tf: 'Font', SCN: 'Pattern', scn: 'Pattern', sh: 'Shading', Do: 'XObject' }

function quitarNoReferenciados(cont, esPagina, sinResolver) {
  let ops
  try { ops = parsear(bytesContenido(cont, esPagina)) } catch { return }
  const nombres = new Set(), porTipo = {}
  let ultimo = ''
  for (const inst of ops) {
    if (inst.op === 'INLINE IMAGE') continue
    for (const a of inst.args) if (a && a.n !== undefined) ultimo = a.n
    const t = QPDF_OPS[inst.op]
    if (t && ultimo !== '') { nombres.add(ultimo); (porTipo[t] ||= new Set()).add(ultimo) }
  }
  const res = cont.get('Resources')
  if (nulo(res) || !res.isDictionary()) return
  const dicts = [], conocidos = new Set()
  for (const kind of ['Font', 'XObject']) {
    const d = res.get(kind)
    if (!nulo(d) && d.isDictionary()) { dicts.push(d); for (const [k] of claves(d)) conocidos.add(k) }
  }
  for (const kind of ['Font', 'XObject']) for (const n of porTipo[kind] || []) if (!conocidos.has(n)) sinResolver.add(n)
  for (const d of dicts) {
    for (const [k] of claves(d)) {
      if (esPagina && sinResolver.has(k)) continue         // lo usa un Form anidado que no lo declara
      if (!nombres.has(k)) d.delete(k)
    }
  }
}

function removerRecursosNoReferenciados(page) {
  const sinResolver = new Set()
  const vistos = new Set(), cola = [page]
  while (cola.length) {                                    // `forEachFormXObject(recursive)`: a lo ancho
    const ph = cola.shift()
    const id = idDe(ph)
    if (!id || vistos.has(id)) continue
    vistos.add(id)
    const res = ph.get('Resources')
    const xd = nulo(res) ? null : res.get('XObject')
    if (nulo(xd)) continue
    for (const [, v] of claves(xd)) {
      if (!esForm(v)) continue
      quitarNoReferenciados(v, false, sinResolver)
      cola.push(v)
    }
  }
  quitarNoReferenciados(page, true, sinResolver)
}

// ─── metadatos: Creator/Producer en el Info y en XMP (como `open_metadata` de pikepdf) ──────
function ponerMetadatos(doc) {
  const xmp = '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>\n' +
    '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="TIZADA PRO">\n' +
    ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n' +
    ' <rdf:Description rdf:about=""><dc:creator xmlns:dc="http://purl.org/dc/elements/1.1/"><rdf:Seq><rdf:li>TIZADA PRO</rdf:li></rdf:Seq></dc:creator>' +
    '<xmp:CreatorTool xmlns:xmp="http://ns.adobe.com/xap/1.0/">TIZADA PRO</xmp:CreatorTool>' +
    '<pdf:Producer xmlns:pdf="http://ns.adobe.com/pdf/1.3/">TIZADA PRO</pdf:Producer></rdf:Description></rdf:RDF>\n' +
    '</x:xmpmeta>\n\n<?xpacket end="w"?>\n'
  const d = doc.newDictionary()
  d.put('Type', doc.newName('Metadata'))
  d.put('Subtype', doc.newName('XML'))
  doc.getTrailer().get('Root').put('Metadata', doc.addStream(new TextEncoder().encode(xmp), d))
  // pikepdf vuelca el XMP al Info al cerrarlo: dc:creator → /Author, xmp:CreatorTool → /Creator
  doc.setMetaData('info:Author', 'TIZADA PRO')
  doc.setMetaData('info:Creator', 'TIZADA PRO')
  doc.setMetaData('info:Producer', 'TIZADA PRO')
}

/**
 * `aplanar_rip._aplanar_archivo`: aplana TODAS las páginas y devuelve los bytes del PDF nuevo.
 * `opciones.total` = todo inline (`TIZADA_APLANADO_TOTAL=1`); default: un nivel.
 * Lanza si algo falla (el que llama decide: la hoja queda como estaba, como en el servidor).
 */
export function aplanarParaRip(mupdf, bytes, opciones = {}) {
  const doc = new mupdf.PDFDocument(bytes)
  try {
    const n = doc.countPages()
    for (let i = 0; i < n; i++) {
      const page = doc.findPage(i)
      // 🔴 el memo es POR PÁGINA: en la hoja cada página es una mesa independiente y así las
      // instrucciones de las piezas de una mesa no quedan vivas hasta el final.
      const hechos = new Map()
      if (opciones.total) {
        const ops = flatten(doc, page, true, hechos)      // des-anida los Form XObjects (inline)
        procesarContenido(doc, page, ops, false)           // 1 pasada, sobre las instrucciones en memoria
        declararEstadoGrafico(doc, page)
      } else aplanarUnNivel(doc, page, hechos)
    }
    unificarIcc(doc)
    // El OutputIntent (perfil de salida) se CONSERVA: le dice al RIP con qué perfil se armó.
    ponerMetadatos(doc)
    for (let i = 0; i < doc.countPages(); i++) removerRecursosNoReferenciados(doc.findPage(i))
    // recolección de basura (los OCG y los Form ya inlineados quedan sin referencia y se van),
    // compresión rápida sin pérdida (la misma que usa el servidor con pikepdf, nivel ~1)
    const out = doc.saveToBuffer('garbage,compress,compression-effort=15').asUint8Array().slice()
    // PDF 1.6 como Illustrator (máxima compatibilidad con el RIP): mupdf escribe la cabecera con la
    // versión del archivo original; `%PDF-d.d` mide lo mismo, así que se cambia en el lugar y los
    // desplazamientos de la tabla xref siguen valiendo (es lo que hace `force_version` de qpdf:
    // sólo la cabecera, el `/Version` del catálogo —si lo hay— queda como estaba).
    if (out[0] === 37 && out[1] === 80 && out[2] === 68 && out[3] === 70 && out[4] === 45) { out[5] = 49; out[6] = 46; out[7] = 54 }
    return out
  } finally {
    try { doc.destroy() } catch { /* nada */ }
  }
}
