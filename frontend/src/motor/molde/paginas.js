// LAS PÁGINAS POR TALLE DEL MOLDE DESPLEGADO, EN EL NAVEGADOR (PLAN_NAVEGADOR.md, etapa 1).
//
// Traducción de la etapa de PÁGINAS de `piezas_con_diseno.desplegar_mesa`: por cada talle, una
// página con SÓLO su capa (`cortar_capas` + `molde_real._raspar_instrucciones` con poda), sin los
// textos «00»/«NOMBRE» (que se guardan como placeholders), sin la etiqueta de corte que ya traía el
// diseño (decidida POR FAMILIA a nivel molde) y sin el trazo de la línea de corte del archivo; con
// sólo los recursos que usa, y con las capas saneadas en sus XObjects (`molde_real.sanear_oc`).
// Los porqués de cada regla están en el Python; el contrato `verificar_navegador_desplegado.py`
// compara el resultado con el del servidor.
//
// 🔴 REPARTO DEL TRABAJO (2026-09-17, velocidad). Lo que necesita el motor PDF (leer el contenido,
// los recursos, escribir el PDF de la mesa) queda acá; el trabajo de cada TALLE (quedarse con su
// capa, placeholders, etiqueta, línea de corte) está en `talle.js`, sobre bytes y datos simples, y
// sin crear un objeto por instrucción. Por eso los recursos de la página se extraen una vez a datos
// simples (`recursosLigeros`): así ese trabajo puede ir a otro hilo.

import { instrucciones as parsear, escribir } from '../pdf/contenido.js'
import { pyRound, compararTuplas } from '../py.js'
import { sha1Hex } from '../sha1.js'
import { normCapa, latin1, trabajarTalle, familiaDe, baseFuente } from './talle.js'

export { normCapa, mencionaTalle, familiaDe, piezaDeTexto } from './talle.js'

export const V_ETQ = 2
const ETQ_FRACCION = 2.0 / 3.0

// ─── objetos PDF (mupdf.js) → datos simples ──────────────────────────────────────────────────
const nulo = (o) => !o || o.isNull()
function claves(o) {
  const out = []
  if (nulo(o)) return out
  o.resolve().forEach((v, k) => out.push([String(k), v]))
  return out
}

function nombresDeProp(obj) {
  // `molde_real._nombres_oc` / `cortar_capas._nombres_de` para UNA entrada de /Properties
  try {
    if (nulo(obj)) return []
    const tipo = obj.get('Type')
    if (!nulo(tipo) && tipo.isName() && tipo.asName() === 'OCG') {
      const nm = obj.get('Name')
      if (nulo(nm)) return []
      return [nm.asString()]
    }
    if (!nulo(tipo) && tipo.isName() && tipo.asName() === 'OCMD') {
      const ocgs = obj.get('OCGs')
      if (nulo(ocgs)) return []
      if (ocgs.isArray()) {
        const out = []
        for (let i = 0; i < ocgs.length; i++) {
          const nm = ocgs.get(i).get('Name')
          if (nulo(nm)) return []
          out.push(nm.asString())
        }
        return out
      }
      const nm = ocgs.get('Name')
      if (nulo(nm)) return []
      return [nm.asString()]
    }
  } catch { return [] }
  return []
}

function infoFuente(f) {
  // lo que `_decodificador`, `_ancho_texto` y el nombre de la fuente leen de una fuente
  const info = { tipo0: false, tu: null, enc: null, fc: 0, widths: null, baseFont: '' }
  try {
    const st = f.get('Subtype')
    info.tipo0 = !nulo(st) && st.isName() && st.asName() === 'Type0'
  } catch { /* nada */ }
  if (info.tipo0) {
    try {
      const tu = f.get('ToUnicode')
      info.tu = nulo(tu) ? null : latin1(tu.readStream().asUint8Array().slice())
    } catch { info.tu = 'ERR' }
  } else {
    try {
      const enc = f.get('Encoding')
      if (!nulo(enc) && enc.isDictionary() && !nulo(enc.get('Differences'))) {
        const arr = enc.get('Differences')
        const items = []
        for (let i = 0; i < arr.length; i++) {
          const it = arr.get(i)
          if (it.isName()) items.push(it.asName())
          else if (it.isNumber()) items.push(Math.trunc(it.asNumber()))
          else throw new Error('Differences')
        }
        info.enc = items
      }
    } catch { info.enc = 'ERR' }
  }
  try {
    const x = f.get('FirstChar')
    info.fc = nulo(x) ? 0 : (x.isNumber() ? Math.trunc(x.asNumber()) : 'ERR')
  } catch { info.fc = 'ERR' }
  try {
    const ws = f.get('Widths')
    if (!nulo(ws) && ws.isArray()) {
      // ⚠️ MuPDF guarda los reales en `float`: un ancho no entero con muchos decimales puede diferir
      // en la sexta cifra del de pikepdf. Illustrator escribe anchos enteros.
      const w = []
      for (let i = 0; i < ws.length; i++) { const x = ws.get(i); w.push(x.isNumber() ? x.asNumber() : null) }
      info.widths = w
    }
  } catch { info.widths = null }
  try {
    const bf = f.get('BaseFont')
    info.baseFont = nulo(bf) ? '' : (bf.isName() ? '/' + bf.asName() : bf.asString())
  } catch { info.baseFont = '' }
  return info
}

function nDeColorSpace(o) {
  const def = { '/DeviceCMYK': 4, '/DeviceRGB': 3, '/DeviceGray': 1 }
  try {
    const r = o.resolve()
    if (r.isArray()) {
      const base = '/' + r.get(0).asName()
      if (base === '/ICCBased' && r.length > 1) {
        const nO = r.get(1).get('N')
        return (nulo(nO) ? 0 : Math.trunc(nO.asNumber())) || null
      }
      return { '/CalRGB': 3, '/CalGray': 1, '/Separation': 1, '/DeviceN': null }[base] ?? null
    }
    return def[r.isName() ? '/' + r.asName() : String(r)] ?? null
  } catch { return null }
}

/** Los recursos de una página como datos simples (se pueden mandar a otro hilo). */
export function recursosLigeros(res) {
  const R = { props: {}, fuentes: {}, cs: {} }
  if (nulo(res)) return R
  try { for (const [k, v] of claves(res.get('Properties'))) R.props[k] = nombresDeProp(v) } catch { /* nada */ }
  try { for (const [k, v] of claves(res.get('Font'))) R.fuentes['/' + k] = infoFuente(v.resolve()) } catch { /* nada */ }
  try { for (const [k, v] of claves(res.get('ColorSpace'))) R.cs['/' + k] = nDeColorSpace(v) } catch { /* nada */ }
  return R
}

// ─── cortar_capas: dónde empieza y termina cada capa, por bytes ──────────────────────────────
const W = (c) => (c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122) || c === 95 || c === 46   // [\w.]
const RX_MARCAS = /\/OC[ \t\n\r\f\v]*(\/[^ \t\n\r\f\v/[\]<>(){}%]+)[ \t\n\r\f\v]*(BDC)|(?<![A-Za-z0-9_.])(BDC|BMC|EMC)(?![A-Za-z0-9_.])/g

function marcasEn(s, desde, hasta) {
  const sub = (desde === 0 && hasta === s.length) ? s : s.slice(desde, hasta)
  const out = []
  RX_MARCAS.lastIndex = 0
  let m
  while ((m = RX_MARCAS.exec(sub)) !== null) out.push({ ini: m.index + desde, fin: m.index + m[0].length + desde, marca: m[1] || null, bdcOc: !!m[2], otra: m[3] || null })
  return out
}

function contarQQ(u8, desde, hasta) {
  let q = 0, Q = 0
  for (let i = desde; i < hasta; i++) {
    const c = u8[i]
    if (c !== 113 && c !== 81) continue
    if (i > desde && W(u8[i - 1])) continue
    if (i + 1 < hasta && W(u8[i + 1])) continue
    if (c === 113) q++; else Q++
  }
  return [q, Q]
}

function gruposQQ(u8, s, ini, fin) {
  const marcas = []
  for (const m of marcasEn(s, ini, fin)) marcas.push([m.ini, m.fin, m.otra === 'EMC' ? -1 : 1])
  const sub = s.slice(ini, fin)
  const RX_BTET = /(?<![A-Za-z0-9_.])(BT|ET)(?![A-Za-z0-9_.])/g
  let mm
  while ((mm = RX_BTET.exec(sub)) !== null) marcas.push([mm.index + ini, mm.index + mm[0].length + ini, mm[1] === 'ET' ? -1 : 1])
  marcas.sort((a, b) => compararTuplas(a, b))
  const out = []
  const pila = []
  let prof = 0, im = 0, saldo = 0
  for (let i = ini; i < fin; i++) {
    const c = u8[i]
    if (c !== 113 && c !== 81) continue
    if (i > ini && W(u8[i - 1])) continue
    if (i + 1 < fin && W(u8[i + 1])) continue
    while (im < marcas.length && marcas[im][0] < i) { saldo += marcas[im][2]; im++ }
    if (c === 113) { pila.push([i, saldo]); prof++ } else {
      prof--
      if (prof < 0) return []
      const [pi, s0] = pila.length ? pila.pop() : [null, 0]
      if (pi !== null && !pila.length && s0 === saldo) out.push([pi, i + 1])
    }
  }
  return out
}

/** `cortar_capas.cortar`: `{u8, trozos: [{nombres, ini, fin, sobras, balanceado}]}` o null. */
export function cortar(u8, R) {
  if (!u8.length) return null
  const s = latin1(u8)
  const raiz = [], pila = []
  for (const m of marcasEn(s, 0, s.length)) {
    if (m.bdcOc) pila.push([m.ini, m.marca])
    else if (m.otra === 'BDC' || m.otra === 'BMC') pila.push([m.ini, null])
    else {
      if (!pila.length) return null
      const [ini, marca] = pila.pop()
      if (!pila.length) raiz.push([ini, m.fin, marca])
    }
  }
  if (pila.length) return null
  const oc = raiz.filter((e) => e[2] !== null)
  if (oc.length < 2) return null
  const trozos = []
  let pos = 0
  for (const [ini, fin, marca] of oc) {
    if (ini > pos) trozos.push({ nombres: null, ini: pos, fin: ini, sobras: [], balanceado: true })
    const [q, Q] = contarQQ(u8, ini, fin)
    const balanceado = q === Q
    const nombres = new Set((R.props[marca.slice(1)] || []).map(normCapa))
    trozos.push({ nombres, ini, fin, sobras: balanceado ? [] : gruposQQ(u8, s, ini, fin), balanceado })
    pos = fin
  }
  if (pos < u8.length) trozos.push({ nombres: null, ini: pos, fin: u8.length, sobras: [], balanceado: true })
  if (trozos.reduce((a, t) => a + (t.fin - t.ini), 0) !== u8.length) return null
  return { u8, trozos }
}

/** `cortar_capas.solo(corte, objetivo)`: los bytes del talle (`objetivo` = nombre normalizado). */
export function solo(corte, objetivo) {
  const partes = []
  const { u8 } = corte
  for (const t of corte.trozos) {
    const esMio = t.nombres !== null && t.nombres.has(objetivo)
    if (t.nombres !== null && t.balanceado && !esMio) continue
    if (t.sobras.length && !esMio) {
      let pos = t.ini
      for (const [a, z] of t.sobras) {
        if (a > pos) partes.push(u8.subarray(pos, a))
        pos = z
      }
      partes.push(u8.subarray(pos, t.fin))
      continue
    }
    partes.push(u8.subarray(t.ini, t.fin))
  }
  const total = partes.reduce((a, p) => a + p.length, 0)
  const out = new Uint8Array(total)
  let p = 0
  for (const x of partes) { out.set(x, p); p += x.length }
  return out
}

// ─── la mesa: su contenido, cortado una sola vez ─────────────────────────────────────────────
/** El contenido de la mesa, sus recursos ligeros y el corte por capas (una vez por mesa). */
export function prepararMesa(doc, mesa) {
  const page = doc.loadPage(mesa - 1)
  const obj = page.getObject()
  const c = obj.get('Contents')
  let u8
  if (nulo(c)) u8 = new Uint8Array(0)
  else if (c.isArray()) {
    const partes = []
    for (let i = 0; i < c.length; i++) partes.push(c.get(i).readStream().asUint8Array().slice())
    u8 = new Uint8Array(partes.reduce((a, x) => a + x.length, 0) + Math.max(0, partes.length - 1))
    let p = 0
    partes.forEach((x, k) => { if (k) u8[p++] = 10; u8.set(x, p); p += x.length })
  } else u8 = c.readStream().asUint8Array().slice()
  const R = recursosLigeros(obj.get('Resources'))
  let corte = null
  try { corte = cortar(u8, R) } catch { corte = null }
  page.destroy()
  return { mesa, u8, R, corte }
}

/** Los bytes de un talle de la mesa preparada (con el corte; sin corte, la mesa entera). */
export function bytesDelTalle(prep, talle) {
  return prep.corte ? solo(prep.corte, normCapa(talle)) : prep.u8
}

// ─── la etiqueta: candidatos y decisión por familia ─────────────────────────────────────────
/** `buscar_candidatos_mesa` (con el corte por bytes; el contrato verifica que da lo mismo). */
export function buscarCandidatosMesa(prep, talles, conts, marco, U) {
  const out = []
  for (const talle of talles) {
    if (!(conts.get(talle) || []).length) continue
    const r = trabajarTalle({ bytes: bytesDelTalle(prep, talle), R: prep.R, marco, U, talle,
      contornos: conts.get(talle), modo: 'candidatos' })
    for (const c of r.candidatos) { c.mesa = prep.mesa; out.push(c) }
  }
  return out
}

/** `decidir_familias`. */
export function decidirFamilias(candidatos, totalPiezas, manual = {}) {
  const fams = new Map()
  for (const c of candidatos) {
    const k = familiaDe(c.fuente, c.alto_mm || 0)
    if (!fams.has(k)) {
      fams.set(k, { clave: k, fuente: baseFuente(c.fuente || '?'), alto_mm: pyRound(Number(c.alto_mm || 0), 1),
        piezas: new Map(), talles: new Set(), ejemplo: c.texto || '', borde_mm: null })
    }
    const f = fams.get(k)
    f.piezas.set(`${c.mesa}|${c.idx}`, [c.mesa, c.idx])
    f.talles.add(c.talle)
    if (c.borde_mm !== null && c.borde_mm !== undefined && (f.borde_mm === null || c.borde_mm < f.borde_mm)) f.borde_mm = c.borde_mm
  }
  const huella = (f) => f.fuente + ' ' + JSON.stringify([...f.piezas.values()].sort(compararTuplas))
  const porHuella = new Map()
  for (const f of [...fams.values()]) {
    const h = huella(f)
    const g = porHuella.get(h)
    if (!g) { porHuella.set(h, f); f.altos = new Set([f.alto_mm]); f.claves = [f.clave]; continue }
    fams.delete(f.clave)
    g.altos.add(f.alto_mm)
    g.claves.push(f.clave)
    for (const t of f.talles) g.talles.add(t)
    if (f.borde_mm !== null && (g.borde_mm === null || f.borde_mm < g.borde_mm)) g.borde_mm = f.borde_mm
  }
  for (const f of fams.values()) {
    const altos = [...(f.altos || new Set([f.alto_mm]))].sort((a, b) => a - b)
    delete f.altos
    if (altos.length > 1) { f.alto_mm = altos[0]; f.alto_hasta_mm = altos[altos.length - 1] }
  }
  const salida = []
  for (const f of fams.values()) {
    const n = f.piezas.size
    const auto = n >= 2 && totalPiezas > 0 && n >= ETQ_FRACCION * totalPiezas
    const fijado = (manual || {})[f.clave]
    const ocultar = fijado !== undefined && fijado !== null ? !!fijado : auto
    let motivo
    if (fijado !== undefined && fijado !== null) motivo = 'lo fijaste vos'
    else if (auto) motivo = `se repite en ${n} de ${totalPiezas} piezas: es la etiqueta de corte`
    else if (n === 1) motivo = 'está en una sola pieza: parece parte del diseño (la talla tejida, por ejemplo)'
    else motivo = `está en ${n} de ${totalPiezas} piezas, menos de dos tercios: se deja`
    salida.push({ clave: f.clave, claves: [...(f.claves || [f.clave])].sort(),
      piezas_lista: [...f.piezas.values()].sort(compararTuplas),
      fuente: f.fuente, alto_mm: f.alto_mm, ...(f.alto_hasta_mm ? { alto_hasta_mm: f.alto_hasta_mm } : {}),
      piezas: n, de: totalPiezas, talles: f.talles.size, ejemplo: f.ejemplo, borde_mm: f.borde_mm,
      ocultar, automatico: auto, motivo })
  }
  salida.sort((a, b) => compararTuplas([-a.piezas, a.clave], [-b.piezas, b.clave]))
  return salida
}

export function familiasOcultas(decision) {
  const out = new Set()
  for (const f of (decision && decision.familias) || []) if (f.ocultar) for (const c of (f.claves || [f.clave])) out.add(c)
  return [...out].sort()
}

export function hashOcultas(claves) {
  return sha1Hex([...(claves || [])].sort().join('|')).slice(0, 12)
}

// ─── escribir la página del talle ────────────────────────────────────────────────────────────
const CLAVES_PAGINA = ['MediaBox', 'CropBox', 'BleedBox', 'TrimBox', 'ArtBox', 'Rotate', 'UserUnit', 'Group']
const ESPACIO_B = new Uint8Array(256)
for (const c of [9, 10, 11, 12, 13, 32]) ESPACIO_B[c] = 1
const DELIM_B = new Uint8Array(256)
for (const c of [47, 91, 93, 60, 62, 40, 41, 123, 125, 37]) DELIM_B[c] = 1

function nombresUsados(data) {
  // re.findall(rb"/([^\s/\[\]<>(){}%]+)", data) con #xx decodificado
  const usados = new Set()
  const n = data.length
  for (let i = 0; i < n; i++) {
    if (data[i] !== 47) continue
    let j = i + 1
    while (j < n && !ESPACIO_B[data[j]] && !DELIM_B[data[j]]) j++
    if (j > i + 1) {
      let tok = ''
      for (let k = i + 1; k < j; k++) tok += String.fromCharCode(data[k])
      if (tok.includes('#')) tok = tok.replace(/#([0-9A-Fa-f]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16)))
      usados.add(tok)
      i = j - 1
    }
  }
  return usados
}

function hayInline(data) {
  // re.search(rb"(?:^|\s)BI\s", data)
  for (let i = 0; i + 2 < data.length; i++) {
    if (data[i] === 66 && data[i + 1] === 73 && ESPACIO_B[data[i + 2]] && (i === 0 || ESPACIO_B[data[i - 1]])) return true
  }
  return false
}

/** `_pagina_desplegada` + `sanear_oc`: agrega a `out` la página del talle con este contenido. */
function paginaDesplegada(out, mapa, srcObj, data) {
  const usados = nombresUsados(data)
  const inline = hayInline(data)
  const d = out.newDictionary()
  d.put('Type', out.newName('Page'))
  for (const k of CLAVES_PAGINA) {
    const v = srcObj.get(k)
    if (!nulo(v)) d.put(k, mapa.graftObject(v))
  }
  const res = out.newDictionary()
  for (const [k, v] of claves(srcObj.get('Resources'))) {
    if (k === 'ProcSet' || !v.resolve().isDictionary()) { res.put(k, mapa.graftObject(v)); continue }
    const sub = out.newDictionary()
    let alguno = false
    for (const [nm, obj] of claves(v)) {
      if (usados.has(nm) || (inline && k === 'ColorSpace')) { sub.put(nm, mapa.graftObject(obj)); alguno = true }
    }
    if (alguno) res.put(k, sub)
  }
  d.put('Resources', res)
  d.put('Contents', out.addStream(data, out.newDictionary()))
  const ref = out.addObject(d)
  out.insertPage(out.countPages(), ref)
  sanearOc(ref, new Set())
  return ref
}

function quitarMarcadores(stream) {
  try {
    const inst = [...parsear(stream.readStream().asUint8Array().slice())]
    const fuera = []
    let prof = 0, cambio = false
    for (const it of inst) {
      const op = it.op
      if (op === 'BDC' || op === 'BMC' || op === 'EMC' || op === 'MP' || op === 'DP') { cambio = true; continue }
      if (op === 'q') prof += 1
      else if (op === 'Q') {
        if (prof === 0) { cambio = true; continue }
        prof -= 1
      }
      fuera.push(it)
    }
    for (let k = 0; k < prof; k++) { fuera.push({ op: 'Q', args: [] }); cambio = true }
    if (cambio) stream.writeStream(escribir(fuera))
  } catch { /* como el Python */ }
}

/** `molde_real.sanear_oc`: borra /OC y los marcadores de contenido opcional en los XObjects de la página. */
export function sanearOc(pagina, vistos) {
  const caminar = (res) => {
    if (nulo(res)) return
    const xo = res.get('XObject')
    if (nulo(xo)) return
    for (const [, x] of claves(xo)) {
      try {
        // `objgen`: un XObject directo es (0, 0) — el primero se mira y los demás directos no, como en el Python
        const clave = x.isIndirect() ? x.asIndirect() : 0
        if (vistos.has(clave)) continue
        vistos.add(clave)
        const obj = x.resolve()
        if (!nulo(obj.get('OC'))) obj.delete('OC')
        const st = obj.get('Subtype')
        if (!nulo(st) && st.isName() && st.asName() === 'Form') {
          quitarMarcadores(obj)
          caminar(obj.get('Resources'))
        }
      } catch { /* como el Python */ }
    }
  }
  caminar(pagina.resolve().get('Resources'))
}

/**
 * Arma el PDF de la mesa con el contenido de cada talle ya trabajado (`trabajarTalle`, en el mismo
 * orden que `talles`). `doc` = el molde (mupdf.PDFDocument).
 */
export function armarPdfMesa(mupdf, doc, mesa, contenidos) {
  const page = doc.loadPage(mesa - 1)
  const srcObj = page.getObject()
  const out = new mupdf.PDFDocument()
  const mapa = out.newGraftMap()
  for (const data of contenidos) paginaDesplegada(out, mapa, srcObj, data)
  // compresión RÁPIDA (nivel ~1, lo mismo que usa el servidor con pikepdf): sin pérdida, 5 veces más
  // rápida que la normal y ~15 % más pesada — medido con 20 MB de contenido real: 0,4 s contra 2 s
  const pdf = out.saveToBuffer('compress,compression-effort=15').asUint8Array().slice()
  // soltar YA la memoria de WebAssembly de esta mesa
  try { mapa.destroy() } catch { /* nada */ }
  try { out.destroy() } catch { /* nada */ }
  page.destroy()
  return pdf
}

/**
 * `_paginas_de_talles` en un solo hilo: `{pdf, placeholders, lineas, etiqueta_archivo}`.
 * (El reparto en varios hilos arma lo mismo con `trabajarTalle` + `armarPdfMesa`.)
 */
export function paginasDeTalles(mupdf, doc, prep, talles, conts, marco, U, ocultar) {
  const placeholders = new Map(), lineas = new Map(), etqArchivo = new Map()
  const contenidos = []
  for (const talle of talles) {
    const r = trabajarTalle({ bytes: bytesDelTalle(prep, talle), R: prep.R, marco, U, talle,
      contornos: conts.get(talle) || [], modo: 'pagina', ocultar })
    juntarTalle(r, talle, placeholders, lineas, etqArchivo)
    contenidos.push(r.contenido)
  }
  return { pdf: armarPdfMesa(mupdf, doc, prep.mesa, contenidos), placeholders, lineas, etiqueta_archivo: etqArchivo }
}

export function juntarTalle(r, talle, placeholders, lineas, etqArchivo) {
  if (r.placeholders.length) placeholders.set(talle, new Map(r.placeholders))
  if (r.etiquetas.length) etqArchivo.set(talle, new Map(r.etiquetas))
  if (r.lineas.length) lineas.set(talle, new Map(r.lineas))
}
