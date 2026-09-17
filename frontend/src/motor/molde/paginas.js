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
// Las instrucciones son las de `pdf/contenido.js`. Donde el Python hace `float(v)`, `int(v)`,
// `bytes(v)` o `str(v)` sobre un operando y eso puede tirar una excepción (que el Python ataja y
// saltea la instrucción), acá las funciones `num`/`entero`/`bytesDe` tiran igual.

import { instrucciones as parsear, escribir } from '../pdf/contenido.js'
import { pyRound, pyG, compararTuplas } from '../py.js'
import { sha1Hex } from '../sha1.js'
import { CM } from './contornos.js'

// ─── Python en JavaScript ────────────────────────────────────────────────────────────────────
class NoEsNumero extends Error {}
const num = (v) => {
  if (v === true) return 1
  if (v === false) return 0
  if (v && v.i !== undefined) return Number(v.i)
  if (v && v.r !== undefined) return Number(v.r)
  throw new NoEsNumero()
}
const entero = (v) => {
  if (v === true) return 1
  if (v === false) return 0
  if (v && v.i !== undefined) return Number(v.i)
  if (v && v.r !== undefined) return Math.trunc(Number(v.r))
  throw new NoEsNumero()
}
const esNombre = (v) => !!v && typeof v === 'object' && !Array.isArray(v) && v.n !== undefined
const esTexto = (v) => !!v && typeof v === 'object' && !Array.isArray(v) && v.s !== undefined
const bytesDe = (v) => { if (esTexto(v)) return v.s; throw new NoEsNumero() }
const nombreStr = (v) => (esNombre(v) ? '/' + v.n : '\u0000otro')   // `str(Name)` = "/X"
const ESPACIOS_PY = '\t\n\u000b\u000c\r\u001c\u001d\u001e\u001f \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000'
const RX_ESPACIOS_PY = new RegExp('[' + ESPACIOS_PY + ']+', 'g')
const strip = (s) => s.replace(new RegExp('^[' + ESPACIOS_PY + ']+|[' + ESPACIOS_PY + ']+$', 'g'), '')
const splitPy = (s) => s.split(RX_ESPACIOS_PY).filter((x) => x)
const latin1 = (u8) => {
  let s = ''
  for (let i = 0; i < u8.length; i += 8192) s += String.fromCharCode.apply(null, u8.subarray(i, i + 8192))
  return s
}
const pow = Math.pow
const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
  a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
const round0 = (x) => pyRound(x, 0)        // `round(x)` de Python: al par en el empate

/** `molde_real._norm_capa`: NFKD, sin marcas combinantes, minúsculas, guiones → espacio. */
export function normCapa(s) {
  const t = String(s).normalize('NFKD').replace(/\p{Mn}/gu, '')
  return splitPy(t.toLowerCase().replace(/-/g, ' ')).join(' ')
}

// ─── objetos PDF (mupdf.js) ──────────────────────────────────────────────────────────────────
const nulo = (o) => !o || o.isNull()
const dictDe = (o) => (nulo(o) ? null : o.resolve())
function claves(o) {
  const out = []
  if (nulo(o)) return out
  o.resolve().forEach((v, k) => out.push([String(k), v]))
  return out
}

/** `molde_real._nombres_oc`: los nombres de capa de un `BDC /OC <operando>`. */
function nombresOc(operando, recursos) {
  try {
    if (!esNombre(operando)) return []
    if (nulo(recursos)) return []
    const props = recursos.get('Properties')
    if (nulo(props)) return []
    const obj = props.get(operando.n)
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

// ─── cortar_capas: dónde empieza y termina cada capa, por bytes ──────────────────────────────
const W = (c) => (c >= 48 && c <= 57) || (c >= 65 && c <= 90) || (c >= 97 && c <= 122) || c === 95 || c === 46   // [\w.]
const RX_MARCAS = /\/OC[ \t\n\r\f\v]*(\/[^ \t\n\r\f\v/[\]<>(){}%]+)[ \t\n\r\f\v]*(BDC)|(?<![A-Za-z0-9_.])(BDC|BMC|EMC)(?![A-Za-z0-9_.])/g

function marcasEn(s, desde, hasta) {
  // _RX_MARCAS.finditer sobre s[desde:hasta] (con los bordes del trozo como bordes del texto)
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

function nombresDe(marca, recursos) {
  // cortar_capas._nombres_de
  try {
    if (nulo(recursos)) return new Set()
    const props = recursos.get('Properties')
    if (nulo(props)) return new Set()
    const obj = props.get(marca.slice(1))
    if (nulo(obj)) return new Set()
    const t = obj.get('Type')
    if (!nulo(t) && t.isName() && t.asName() === 'OCG') return new Set([normCapa(obj.get('Name').asString())])
    if (!nulo(t) && t.isName() && t.asName() === 'OCMD') {
      const ocgs = obj.get('OCGs')
      if (ocgs.isArray()) {
        const s = new Set()
        for (let i = 0; i < ocgs.length; i++) s.add(normCapa(ocgs.get(i).get('Name').asString()))
        return s
      }
      if (!nulo(ocgs)) return new Set([normCapa(ocgs.get('Name').asString())])
    }
  } catch { /* como el Python */ }
  return new Set()
}

function gruposQQ(u8, s, ini, fin) {
  // cortar_capas._grupos_qq sobre b = data[ini:fin]; devuelve tramos absolutos
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
export function cortar(u8, recursos) {
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
    trozos.push({ nombres: nombresDe(marca, recursos), ini, fin, sobras: balanceado ? [] : gruposQQ(u8, s, ini, fin), balanceado })
    pos = fin
  }
  if (pos < u8.length) trozos.push({ nombres: null, ini: pos, fin: u8.length, sobras: [], balanceado: true })
  if (trozos.reduce((a, t) => a + (t.fin - t.ini), 0) !== u8.length) return null
  return { u8, trozos }
}

/** `cortar_capas.solo(corte, objetivo)`: los bytes del talle. */
export function solo(corte, objetivo) {
  const partes = []
  const { u8 } = corte
  for (const t of corte.trozos) {
    const esMio = t.nombres !== null && [...objetivo].some((x) => t.nombres.has(x))
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

// ─── molde_real: quedarse con un talle ───────────────────────────────────────────────────────
const PAINT_PATH = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'])
const PAINT_TEXT = new Set(['Tj', 'TJ', "'", '"'])
const PAINT_DROP = new Set(['Do', 'sh'])
const CLIP_OPS = new Set(['W', 'W*'])
const PATH_BUILD = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const ins = (op, args = []) => ({ op, args })

function mapaOc(inst, recursos) {
  const ops = inst.map((i) => i.op)
  const oc = new Map()
  ops.forEach((o, i) => {
    if (o !== 'BDC') return
    const a = inst[i].args
    if (a.length === 2 && nombreStr(a[0]) === '/OC') oc.set(i, new Set(nombresOc(a[1], recursos).map(normCapa)))
  })
  return [ops, oc]
}

function bloquesOc(ops, oc) {
  const raiz = [], abiertos = []
  ops.forEach((o, i) => {
    if (o === 'BDC' || o === 'BMC') abiertos.push([i, o === 'BDC' ? (oc.get(i) || null) : null, 0, []])
    else if (o === 'EMC') {
      if (abiertos.length) {
        const [ini, nombres, bal, hijos] = abiertos.pop()
        ;(abiertos.length ? abiertos[abiertos.length - 1][3] : raiz).push([ini, i, nombres, bal === 0, hijos])
      }
    } else if (o === 'q') { for (const b of abiertos) b[2] += 1 } else if (o === 'Q') { for (const b of abiertos) b[2] -= 1 }
  })
  return raiz
}

function saltarBloques(bloques, suprimir) {
  const saltar = new Set()
  const caminar = (lista) => {
    for (const [ini, fin, nombres, balanceado, hijos] of lista) {
      if (nombres && nombres.size && suprimir([nombres])) {
        if (balanceado) for (let k = ini; k <= fin; k++) saltar.add(k)
        continue
      }
      caminar(hijos)
    }
  }
  caminar(bloques)
  return saltar
}

function rasparInstrucciones(inst, ops, oc, suprimir, saltar) {
  // podar=True
  const salida = [], pila = []
  for (let idx = 0; idx < inst.length; idx++) {
    if (saltar.has(idx)) continue
    const it = inst[idx]
    const op = ops[idx]
    if (op === 'BDC' || op === 'BMC') { pila.push(oc.get(idx) || new Set()); continue }
    if (op === 'EMC') { if (pila.length) pila.pop(); continue }
    if (op === 'MP' || op === 'DP') continue
    if (suprimir(pila)) {
      if (PATH_BUILD.has(op)) continue
      if (PAINT_PATH.has(op)) continue
      if (PAINT_TEXT.has(op)) {
        if (op === "'") salida.push(ins('T*'))
        else if (op === '"' && it.args.length === 3) {
          salida.push(ins('Tw', [it.args[0]]))
          salida.push(ins('Tc', [it.args[1]]))
          salida.push(ins('T*'))
        }
        continue
      }
      if (PAINT_DROP.has(op) || op.toUpperCase().replace(/_/g, ' ') === 'INLINE IMAGE') continue
      if (CLIP_OPS.has(op)) continue
    }
    salida.push(it)
  }
  return salida
}

const suprimirFuera = (obj) => (pila) => !pila.some((frame) => frame && frame.size && [...obj].some((x) => frame.has(x)))

// ─── «00», «NOMBRE» y la etiqueta que trae el diseño ─────────────────────────────────────────
const PLACEHOLDERS = { '00': 'numero', NOMBRE: 'nombre' }
const GLIFO_DIGITO = { zero: '0', one: '1', two: '2', three: '3', four: '4', five: '5', six: '6', seven: '7', eight: '8', nine: '9', space: ' ' }
const ETQ_FRACCION = 2.0 / 3.0
const ETQ_RADIO_MM = 40.0
export const V_ETQ = 2

function decodificador(fuente) {
  try {
    const st = fuente.get('Subtype')
    if (!nulo(st) && st.isName() && st.asName() === 'Type0') {
      const tu = fuente.get('ToUnicode')
      if (nulo(tu)) return null
      const data = latin1(tu.readStream().asUint8Array().slice())
      const mapa = new Map()
      const WS = '[\\s\\u001c-\\u001f\\u0085]*'
      const rxPar = new RegExp('<([0-9A-Fa-f]+)>' + WS + '<([0-9A-Fa-f]+)>', 'g')
      let m
      while ((m = rxPar.exec(data)) !== null) {
        const [, src, dst] = m
        if (src.length <= 4) {
          if (dst.length % 2) continue                  // bytes.fromhex con largo impar: error → se saltea
          const b = new Uint8Array(dst.length / 2)
          for (let i = 0; i < b.length; i++) b[i] = parseInt(dst.substr(i * 2, 2), 16)
          mapa.set(parseInt(src, 16), new TextDecoder('utf-16be').decode(b))
        }
      }
      const rxRango = new RegExp('<([0-9A-Fa-f]+)>' + WS + '<([0-9A-Fa-f]+)>' + WS + '<([0-9A-Fa-f]+)>', 'g')
      while ((m = rxRango.exec(data)) !== null) {
        const a = parseInt(m[1], 16), b = parseInt(m[2], 16), d0 = parseInt(m[3], 16)
        for (let k = a; k <= Math.min(b, a + 255); k++) {
          if (!mapa.has(k)) {
            const cp = d0 + (k - a)
            if (cp > 0x10ffff) break
            mapa.set(k, String.fromCodePoint(cp))
          }
        }
      }
      return (b) => {
        let s = ''
        for (let i = 0; i < b.length - 1; i += 2) s += mapa.has((b[i] << 8) | b[i + 1]) ? mapa.get((b[i] << 8) | b[i + 1]) : '?'
        return s
      }
    }
    const dif = new Map()
    const enc = fuente.get('Encoding')
    if (!nulo(enc) && enc.isDictionary() && !nulo(enc.get('Differences'))) {
      const arr = enc.get('Differences')
      let code = 0
      for (let i = 0; i < arr.length; i++) {
        const it = arr.get(i)
        if (it.isName()) {
          const nm = it.asName()
          if (GLIFO_DIGITO[nm] !== undefined) dif.set(code, GLIFO_DIGITO[nm])
          else if ([...nm].length === 1) dif.set(code, nm)
          else if (/^uni[0-9A-Fa-f]{4}$/.test(nm)) dif.set(code, String.fromCharCode(parseInt(nm.slice(3), 16)))
          else dif.set(code, '?')
          code += 1
        } else code = Math.trunc(it.asNumber())
      }
    }
    return (b) => {
      let s = ''
      for (const c of b) s += dif.has(c) ? dif.get(c) : String.fromCharCode(c)
      return s
    }
  } catch { return null }
}

function textoMostrado(op, args, dec) {
  try {
    let b
    if (op === 'Tj' || op === "'") b = bytesDe(args[args.length - 1])
    else if (op === '"') b = bytesDe(args[2])
    else if (op === 'TJ') b = concatenar((Array.isArray(args[0]) ? args[0] : (() => { throw new NoEsNumero() })()).filter(esTexto).map((x) => x.s))
    else return ''
    return dec ? dec(b) : latin1(b)
  } catch { return '' }
}

function concatenar(lista) {
  const out = new Uint8Array(lista.reduce((a, x) => a + x.length, 0))
  let p = 0
  for (const x of lista) { out.set(x, p); p += x.length }
  return out
}

function anchoTexto(fuente, b) {
  try {
    const fcO = fuente.get('FirstChar')
    const fc = nulo(fcO) ? 0 : Math.trunc(fcO.asNumber())
    const ws = fuente.get('Widths')
    if (nulo(ws)) return null
    let tot = 0.0
    const n = ws.length
    for (const c of b) {
      const i = c - fc
      tot += (i >= 0 && i < n) ? ws.get(i).asNumber() : 500.0
    }
    return tot / 1000.0
  } catch { return null }
}

const tokens = (txt) => String(txt || '').toUpperCase().split(/[^0-9A-Za-zÁÉÍÓÚÑÜáéíóúñü]+/).filter((t) => t)
const normTalle = (s) => splitPy(strip(String(s || '')).toUpperCase().replace(/-/g, ' ')).join(' ')

export function mencionaTalle(txt, talle) {
  const t = normTalle(talle)
  if (!t) return false
  if (normTalle(txt) === t) return true
  return tokens(txt).includes(t)
}

// `str(x).lstrip("/").split("+")[-1]` (sin reemplazar el vacío) y la versión con «?» de `familia_de`
const ultimoTramo = (s) => { const x = String(s).replace(/^\/+/, '').split('+'); return x[x.length - 1] }
const baseFuente = (s) => ultimoTramo(s || '?')

export function familiaDe(fuente, altoMm) {
  return `${baseFuente(fuente || '?')}|${pyG(round0(Number(altoMm) * 2) / 2)}`
}

export function piezaDeTexto(dx, dy, contornos) {
  const CM10 = CM / 10.0
  let mejor = null
  ;(contornos || []).forEach((c, i) => {
    const bb = c && c.bbox_mu
    if (!bb) return
    const [x0, y0, x1, y1] = bb
    const fx = Math.max(x0 - dx, 0.0, dx - x1)
    const fy = Math.max(y0 - dy, 0.0, dy - y1)
    let d
    if (fx || fy) d = pow(fx * fx + fy * fy, 0.5)
    else d = Math.min(dx - x0, x1 - dx, dy - y0, y1 - dy)
    d /= CM10
    if ((fx || fy) && d > ETQ_RADIO_MM) return
    if (mejor === null || d < mejor[1]) mejor = [i, pyRound(d, 2)]
  })
  return mejor
}

function colorSpaceN(csRecursos, name) {
  const def = { '/DeviceCMYK': 4, '/DeviceRGB': 3, '/DeviceGray': 1 }
  try {
    const o = csRecursos.get(name)
    if (o === undefined) return def[name] ?? null
    if (o.isArray()) {
      const base = '/' + o.get(0).asName()
      if (base === '/ICCBased' && o.length > 1) {
        const nO = o.get(1).get('N')
        const n = nulo(nO) ? 0 : Math.trunc(nO.asNumber())
        return n || null
      }
      return { '/CalRGB': 3, '/CalGray': 1, '/Separation': 1, '/DeviceN': null }[base] ?? null
    }
    return def[o.isName() ? '/' + o.asName() : String(o)] ?? null
  } catch { return null }
}

function recursosPorNombre(recursos, clave) {
  const m = new Map()
  try {
    if (nulo(recursos)) return m
    for (const [k, v] of claves(recursos.get(clave))) m.set('/' + k, v)
  } catch { /* nada */ }
  return m
}

/** `quitar_placeholders`: `[salida, encontrados(Map campo→ph), etiquetas(Map idx→etq)]`. */
export function quitarPlaceholders(salida, recursos, marco, U, talle, contornos, ocultar, candidatos) {
  const fuentes = recursosPorNombre(recursos, 'Font')
  const cs = recursosPorNombre(recursos, 'ColorSpace')
  const opN = { 4: 'k', 3: 'rg', 1: 'g' }
  const [x0c, , , y1c] = marco
  const dev = (x, y) => [(x - x0c) * U, (y1c - y) * U]
  let ctm = [1, 0, 0, 1, 0, 0]
  const pila = []
  let fcol = null, scol = null, fcsN = null, scsN = null, sw = 1.0, tr = 0, tf = null, tfs = 1.0
  let tm = null, tlm = null, tl = 0.0, th = 1.0
  const encontrados = new Map(), etiquetas = new Map(), quitar = new Set(), cajas = []
  const r4 = (v) => pyRound(num(v), 4)
  for (let i = 0; i < salida.length; i++) {
    const op = salida[i].op
    const ops = salida[i].args || []
    try {
      if (op === 'q') pila.push([ctm, fcol, fcsN, scol, scsN, sw, tr, tf, tfs])
      else if (op === 'Q') { if (pila.length) [ctm, fcol, fcsN, scol, scsN, sw, tr, tf, tfs] = pila.pop() }
      else if (op === 'cm') ctm = mul(ops.map(num), ctm)
      else if (op === 'cs') fcsN = colorSpaceN(cs, nombreStr(ops[0]))
      else if (op === 'CS') scsN = colorSpaceN(cs, nombreStr(ops[0]))
      else if (op === 'k' || op === 'rg' || op === 'g') fcol = [op, ops.map(r4)]
      else if (op === 'K' || op === 'RG' || op === 'G') scol = [op.toLowerCase(), ops.map(r4)]
      else if (op === 'sc' || op === 'scn') {
        const nums = ops.filter((v) => !esNombre(v)).map(r4)
        const o2 = opN[fcsN] || opN[nums.length]
        if (o2) fcol = [o2, nums]
      } else if (op === 'SC' || op === 'SCN') {
        const nums = ops.filter((v) => !esNombre(v)).map(r4)
        const o2 = opN[scsN] || opN[nums.length]
        if (o2) scol = [o2, nums]
      } else if (op === 'w') sw = num(ops[0])
      else if (op === 'Tr') tr = entero(ops[0])
      else if (op === 'BT') { tm = tlm = [1, 0, 0, 1, 0, 0] }
      else if (op === 'ET') { tm = tlm = null }
      else if (op === 'Tf') { const a = nombreStr(ops[0]); const b = num(ops[1]); tf = a; tfs = b }
      else if (op === 'Tm') { tm = tlm = ops.map(num) }
      else if (op === 'Td' || op === 'TD') {
        tlm = mul([1, 0, 0, 1, num(ops[0]), num(ops[1])], tlm || [1, 0, 0, 1, 0, 0])
        tm = tlm.slice()
        if (op === 'TD') tl = -num(ops[1])
      } else if (op === 'TL') tl = num(ops[0])
      else if (op === 'Tc' || op === 'Tw') { /* no entra al ancho */ }
      else if (op === 'Tz') th = num(ops[0]) / 100.0
      else if (op === 'T*' || op === "'" || op === '"' || op === 'Tj' || op === 'TJ') {
        if (op === 'T*' || op === "'" || op === '"') {
          tlm = mul([1, 0, 0, 1, 0, -tl], tlm || [1, 0, 0, 1, 0, 0])
          tm = tlm.slice()
        }
        if (op === 'T*') continue
        const f = fuentes.get(tf)
        const dec = f !== undefined ? decodificador(f) : null
        const txt = textoMostrado(op, ops, dec)
        const campo = PLACEHOLDERS[strip(txt).toUpperCase().replace(/ /g, '')]
        if (tm === null) continue
        const m = mul(mul([tfs, 0, 0, tfs, 0, 0], tm), ctm)
        const esc = pow(pow(m[0], 2) + pow(m[1], 2), 0.5)
        const ox = m[4], oy = m[5]
        let b
        if (op === 'Tj' || op === "'") b = bytesDe(ops[ops.length - 1])
        else if (op === '"') b = bytesDe(ops[2])
        else b = concatenar((Array.isArray(ops[0]) ? ops[0] : (() => { throw new NoEsNumero() })()).filter(esTexto).map((x) => x.s))
        let an = f !== undefined ? anchoTexto(f, b) : null
        if (an === null) an = 0.6 * [...strip(txt)].length
        const ancho = an * esc * th
        if (campo === undefined) {
          if (talle && (candidatos || (ocultar && ocultar.size)) && mencionaTalle(txt, talle)) {
            const [dx, dy] = dev(ox, oy)
            const altoMm = esc * U / (CM / 10.0)
            const fn = f !== undefined ? ultimoTramo(nombreDeObjeto(f.get('BaseFont'))) : '?'
            const pz = piezaDeTexto(dx, dy, contornos)
            if (pz !== null) {
              const [ip, borde] = pz
              if (candidatos) {
                candidatos.push({ talle, idx: ip, texto: strip(txt), fuente: fn, alto_mm: pyRound(altoMm, 2),
                  borde_mm: borde, x: pyRound(dx, 2), y: pyRound(dy, 2) })
              } else if (ocultar.has(familiaDe(fn, altoMm))) {
                if (!etiquetas.has(ip)) {
                  etiquetas.set(ip, { texto: strip(txt), x: pyRound(dx, 2), y: pyRound(dy, 2), alto_mm: pyRound(altoMm, 2),
                    borde_mm: borde, familia: familiaDe(fn, altoMm), copias: 0 })
                }
                etiquetas.get(ip).copias += 1
                quitar.add(i)
                cajas.push([ip, dx, dy, ancho * U, esc * U])
              }
            }
          }
          continue
        }
        const [dx, dy] = dev(ox, oy)
        let ph = encontrados.get(campo)
        if (ph === undefined) {
          ph = { cx: pyRound(dx + ancho * U / 2.0, 2), baseline_y: pyRound(dy, 2), size: pyRound(esc * U, 3),
            fuente: f !== undefined ? ultimoTramo(nombreDeObjeto(f.get('BaseFont'))) : '',
            ancho: pyRound(ancho * U, 2), color: 0, colorn: null, trazo: null, pasadas: [], baseline_pts: [], texto: strip(txt) }
          encontrados.set(campo, ph)
        }
        const add = (p) => {
          if (!ph.pasadas.length || JSON.stringify(ph.pasadas[ph.pasadas.length - 1]) !== JSON.stringify(p)) ph.pasadas.push(p)
        }
        if ([0, 2, 4, 6].includes(tr) && fcol) {
          add({ t: 'f', color: [fcol[0], fcol[1].slice()] })
          if (ph.colorn === null) ph.colorn = [fcol[0], fcol[1].slice()]
        }
        if ([1, 2, 5, 6].includes(tr) && scol) {
          const w = sw * pow(pow(ctm[0], 2) + pow(ctm[1], 2), 0.5) * U
          add({ t: 'S', color: [scol[0], scol[1].slice()], w: pyRound(w, 4) })
          if (ph.trazo === null) ph.trazo = [scol[0], scol[1].slice(), pyRound(w, 4)]
        }
        quitar.add(i)
        cajas.push([null, dx, dy, ancho * U, esc * U])
      }
    } catch { continue }
  }
  if (!quitar.size) return [salida, new Map(), new Map()]
  for (const [iq, iQ, ip] of bloquesDeContorno(salida, cajas, marco, U)) {
    for (let k = iq; k <= iQ; k++) quitar.add(k)
    if (ip !== null && etiquetas.has(ip)) etiquetas.get(ip).contornos = (etiquetas.get(ip).contornos || 0) + 1
  }
  return [salida.filter((_, i) => !quitar.has(i)), encontrados, etiquetas]
}

function nombreDeObjeto(o) {
  // `str(f.get("/BaseFont", ""))`: un nombre da "/X"; nada da ""
  if (nulo(o)) return ''
  if (o.isName()) return '/' + o.asName()
  if (o.isString()) return o.asString()
  return String(o)
}

const OPS_TRAZADO = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const OPS_ESTADO = new Set(['w', 'M', 'J', 'j', 'd', 'CS', 'SCN', 'SC', 'K', 'RG', 'G', 'gs', 'ri', 'i'])

function bloquesDeContorno(salida, cajas, marco, U) {
  if (!cajas.length) return []
  const [x0c, , , y1c] = marco
  const mm2 = 2.0 * (CM / 10.0) * U
  const dev = (x, y) => [(x - x0c) * U, (y1c - y) * U]
  const cs = cajas.map(([ip, dx, dy, ancho, alto]) => [dx - mm2, dx + ancho + mm2, dy - 1.1 * alto - mm2, dy + 0.3 * alto + mm2, ip])
  const adentro = (bx0, by0, bx1, by1) => {
    for (const [X0, X1, Y0, Y1, ip] of cs) if (bx0 >= X0 && bx1 <= X1 && by0 >= Y0 && by1 <= Y1) return ip
    return 'sin'
  }
  const toca = (px, py) => cs.some(([X0, X1, Y0, Y1]) => X0 <= px && px <= X1 && Y0 <= py && py <= Y1)
  let ctm = [1, 0, 0, 1, 0, 0]
  const pila = [], hallados = []
  let i = 0
  const n = salida.length
  while (i < n) {
    const op = salida[i].op
    const ops = salida[i].args || []
    if (op === 'cm') {
      try { ctm = mul(ops.map(num), ctm) } catch { /* como el Python */ }
    } else if (op === 'Q') {
      if (pila.length) ctm = pila.pop()
    } else if (op === 'q') {
      pila.push(ctm.slice())
      let j = i + 1, prof = 1, pintado = null, otro = false, ctmB = ctm.slice()
      const pts = []
      while (j < n && prof) {
        const o2 = salida[j].op, a2 = salida[j].args || []
        if (o2 === 'q') { prof += 1; otro = true }
        else if (o2 === 'Q') { prof -= 1; if (prof === 0) break }
        else if (o2 === 'cm') {
          try { ctmB = mul(a2.map(num), ctmB) } catch { otro = true }
        } else if (OPS_TRAZADO.has(o2)) {
          try {
            const nums = a2.map(num)
            let cand
            if (o2 === 're') {
              if (nums.length !== 4) throw new NoEsNumero()
              const [x, y, w, h] = nums
              cand = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]
            } else {
              cand = []
              for (let k = 0; k < nums.length - 1; k += 2) cand.push([nums[k], nums[k + 1]])
            }
            for (const [x, y] of cand) {
              const X = ctmB[0] * x + ctmB[2] * y + ctmB[4]
              const Y = ctmB[1] * x + ctmB[3] * y + ctmB[5]
              const p = dev(X, Y)
              if (!toca(p[0], p[1])) { otro = true; break }
              pts.push(p)
            }
          } catch { otro = true }
        } else if (o2 === 'S' || o2 === 's') pintado = pintado === null ? 'S' : 'varios'
        else if (['f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n', 'W', 'W*'].includes(o2)) otro = true
        else if (OPS_ESTADO.has(o2)) { /* estado */ }
        else otro = true
        if (otro) break
        j += 1
      }
      if (prof === 0 && pintado === 'S' && !otro && pts.length) {
        const bx0 = Math.min(...pts.map((p) => p[0])), bx1 = Math.max(...pts.map((p) => p[0]))
        const by0 = Math.min(...pts.map((p) => p[1])), by1 = Math.max(...pts.map((p) => p[1]))
        const ip = adentro(bx0, by0, bx1, by1)
        if (ip !== 'sin') {
          hallados.push([i, j, ip])
          ctm = pila.pop()
          i = j + 1
          continue
        }
      }
    }
    i += 1
  }
  return hallados
}

/** `quitar_linea_de_corte`: `[salida, encontrados(Map idx→{w,color})]`. */
export function quitarLineaDeCorte(salida, recursos, contornos, marco, U) {
  const objetivos = []
  ;(contornos || []).forEach((c, i) => { if (c.linea_corte) objetivos.push([i, c.bbox_raw.map(Number)]) })
  if (!objetivos.length) return [salida, new Map()]
  const cs = recursosPorNombre(recursos, 'ColorSpace')
  const opN = { 4: 'k', 3: 'rg', 1: 'g' }
  const nDeCs = (name) => {
    const def = { '/DeviceCMYK': 4, '/DeviceRGB': 3, '/DeviceGray': 1 }
    try {
      const o = cs.get(name)
      if (o === undefined) return def[name] ?? null
      if (o.isArray()) {
        const base = '/' + o.get(0).asName()
        if (base === '/ICCBased' && o.length > 1) {
          const nO = o.get(1).get('N')
          return (nulo(nO) ? 0 : Math.trunc(nO.asNumber())) || null
        }
        return { '/CalRGB': 3, '/CalGray': 1, '/Separation': 1 }[base] ?? null
      }
      return def[o.isName() ? '/' + o.asName() : String(o)] ?? null
    } catch { return null }
  }
  let ctm = [1, 0, 0, 1, 0, 0]
  const pila = []
  let scol = null, scsN = null, sw = 1.0
  let pts = []
  const encontrados = new Map(), reemplazar = new Map(), candidatos = []
  const tol = 1.5
  const P = (x, y) => [ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5]]
  const r4 = (v) => pyRound(num(v), 4)
  for (let i = 0; i < salida.length; i++) {
    const op = salida[i].op
    const o = salida[i].args || []
    try {
      if (op === 'q') pila.push([ctm, scol, scsN, sw])
      else if (op === 'Q') { if (pila.length) [ctm, scol, scsN, sw] = pila.pop() }
      else if (op === 'cm') ctm = mul(o.map(num), ctm)
      else if (op === 'CS') scsN = nDeCs(nombreStr(o[0]))
      else if (op === 'K' || op === 'RG' || op === 'G') scol = [op.toLowerCase(), o.map(r4)]
      else if (op === 'SC' || op === 'SCN') {
        const nums = o.filter((v) => !esNombre(v)).map(r4)
        const o2 = opN[scsN] || opN[nums.length]
        if (o2) scol = [o2, nums]
      } else if (op === 'w') sw = num(o[0])
      else if (op === 're') {
        if (o.length !== 4) throw new NoEsNumero()
        const [x, y, w, h] = o.map(num)
        pts.push(P(x, y), P(x + w, y), P(x + w, y + h), P(x, y + h))
      } else if (op === 'm' || op === 'l') {
        if (o.length < 2) throw new NoEsNumero()
        pts.push(P(num(o[0]), num(o[1])))
      } else if (op === 'c') {
        if (o.length < 6) throw new NoEsNumero()
        const v = [0, 1, 2, 3, 4, 5].map((k) => num(o[k]))
        pts.push(P(v[0], v[1]), P(v[2], v[3]), P(v[4], v[5]))
      } else if (op === 'v' || op === 'y') {
        if (o.length < 4) throw new NoEsNumero()
        const v = [0, 1, 2, 3].map((k) => num(o[k]))
        pts.push(P(v[0], v[1]), P(v[2], v[3]))
      } else if (['S', 's', 'n', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'].includes(op)) {
        if ((op === 'S' || op === 's') && pts.length) {
          const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
          const caja = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
          const esc = pow(pow(ctm[0], 2) + pow(ctm[1], 2), 0.5)
          candidatos.push([i, caja, pyRound(sw * esc, 4), scol ? [scol[0], scol[1].slice()] : ['k', [0, 0, 0, 1]]])
        }
        pts = []
      }
    } catch { continue }
  }
  const exceso = 60.0
  for (const [idx, bb] of objetivos) {
    let mejor = null
    for (const [i, caja, w, color] of candidatos) {
      if (reemplazar.has(i)) continue
      if (caja[0] <= bb[0] + tol && caja[1] <= bb[1] + tol && caja[2] >= bb[2] - tol && caja[3] >= bb[3] - tol) {
        const ex = (bb[0] - caja[0]) + (bb[1] - caja[1]) + (caja[2] - bb[2]) + (caja[3] - bb[3])
        if (ex <= 4 * exceso && (mejor === null || ex < mejor[0])) mejor = [ex, i, w, color]
      }
    }
    if (mejor !== null) {
      const [, i, w, color] = mejor
      encontrados.set(idx, { w, color })
      reemplazar.set(i, ins('n'))
    }
  }
  if (!reemplazar.size) return [salida, new Map()]
  return [salida.map((it, i) => reemplazar.get(i) || it), encontrados]
}

// ─── la etiqueta: candidatos y decisión por familia ─────────────────────────────────────────
function instruccionesDelTalle(u8, corte, recursos, talle) {
  const obj = new Set([normCapa(talle)])
  const bytes = corte ? solo(corte, obj) : u8
  const inst = [...parsear(bytes)]
  const [ops, oc] = mapaOc(inst, recursos)
  const suprimir = suprimirFuera(obj)
  const saltar = saltarBloques(bloquesOc(ops, oc), suprimir)
  return rasparInstrucciones(inst, ops, oc, suprimir, saltar)
}

/** `buscar_candidatos_mesa` (con el corte por bytes; el contrato verifica que da lo mismo). */
export function buscarCandidatosMesa(u8, recursos, mesa, talles, conts, marco, U) {
  const out = []
  const corte = cortar(u8, recursos)
  for (const talle of talles) {
    if (!(conts.get(talle) || []).length) continue
    const salida = instruccionesDelTalle(u8, corte, recursos, talle)
    const cands = []
    quitarPlaceholders(salida, recursos, marco, U, talle, conts.get(talle), null, cands)
    for (const c of cands) { c.mesa = mesa; out.push(c) }
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
  const huella = (f) => f.fuente + '\u0000' + JSON.stringify([...f.piezas.values()].sort(compararTuplas))
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

function nombresUsados(data) {
  // re.findall(rb"/([^\s/\[\]<>(){}%]+)", data) con #xx decodificado
  const usados = new Set()
  const n = data.length
  const DEL = new Set([47, 91, 93, 60, 62, 40, 41, 123, 125, 37])
  for (let i = 0; i < n; i++) {
    if (data[i] !== 47) continue
    let j = i + 1
    while (j < n && !ESPACIO_B[data[j]] && !DEL.has(data[j])) j++
    if (j > i + 1) {
      const tok = latin1(data.subarray(i + 1, j)).replace(/#([0-9A-Fa-f]{2})/g, (_, h) => String.fromCharCode(parseInt(h, 16)))
      usados.add(tok)
      i = j - 1
    }
  }
  return usados
}

function hayInline(data) {
  // re.search(rb"(?:^|\s)BI\s", data)
  for (let i = 0; i + 2 < data.length + 0; i++) {
    if (data[i] === 66 && data[i + 1] === 73 && (i + 2 < data.length) && ESPACIO_B[data[i + 2]] && (i === 0 || ESPACIO_B[data[i - 1]])) return true
  }
  return false
}

/** `_pagina_desplegada` + `sanear_oc`: agrega a `out` la página del talle. */
function paginaDesplegada(mupdf, out, mapa, srcPage, salida) {
  const data = escribir(salida)
  const usados = nombresUsados(data)
  const inline = hayInline(data)
  const src = srcPage.getObject()
  const d = out.newDictionary()
  d.put('Type', out.newName('Page'))
  for (const k of CLAVES_PAGINA) {
    const v = src.get(k)
    if (!nulo(v)) d.put(k, mapa.graftObject(v))
  }
  const res = out.newDictionary()
  for (const [k, v] of claves(src.get('Resources'))) {
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
      if (['BDC', 'BMC', 'EMC', 'MP', 'DP'].includes(op)) { cambio = true; continue }
      if (op === 'q') prof += 1
      else if (op === 'Q') {
        if (prof === 0) { cambio = true; continue }
        prof -= 1
      }
      fuera.push(it)
    }
    for (let k = 0; k < prof; k++) { fuera.push(ins('Q')); cambio = true }
    if (cambio) stream.writeStream(escribir(fuera))
  } catch { /* como el Python */ }
}

function sanearOc(pagina, vistos) {
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
 * `_paginas_de_talles`: el PDF de la mesa (una página por talle, en el orden dado) y lo que se
 * guarda en `m{mesa}.json`. `doc` = el molde (mupdf.PDFDocument), `conts` = Map(talle → piezas).
 */
export function paginasDeTalles(mupdf, doc, mesa, talles, conts, marco, U, ocultar) {
  const page = doc.loadPage(mesa - 1)
  const recursos = page.getObject().get('Resources')
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
  let corte = null
  try { corte = cortar(u8, recursos) } catch { corte = null }
  let instTodas = null
  const out = new mupdf.PDFDocument()
  const mapa = out.newGraftMap()
  const placeholders = new Map(), lineas = new Map(), etqArchivo = new Map()
  for (const talle of talles) {
    const objT = new Set([normCapa(talle)])
    const suprimir = suprimirFuera(objT)
    let inst, ops, oc
    if (corte) {
      inst = [...parsear(solo(corte, objT))]
      ;[ops, oc] = mapaOc(inst, recursos)
    } else {
      if (!instTodas) { const i2 = [...parsear(u8)]; const [o2, c2] = mapaOc(i2, recursos); instTodas = [i2, o2, c2] }
      ;[inst, ops, oc] = instTodas
    }
    const saltar = saltarBloques(bloquesOc(ops, oc), suprimir)
    let salida = rasparInstrucciones(inst, ops, oc, suprimir, saltar)
    const contT = conts.get(talle) || []
    let ph, etq, lc
    ;[salida, ph, etq] = quitarPlaceholders(salida, recursos, marco, U, talle, contT, new Set(ocultar || []), null)
    if (ph.size) placeholders.set(talle, ph)
    if (etq.size) etqArchivo.set(talle, new Map([...etq].map(([k, v]) => [String(k), v])))
    ;[salida, lc] = quitarLineaDeCorte(salida, recursos, contT, marco, U)
    if (lc.size) lineas.set(talle, new Map([...lc].map(([k, v]) => [String(k), v])))
    paginaDesplegada(mupdf, out, mapa, page, salida)
  }
  // compresión RÁPIDA (nivel ~1, lo mismo que usa el servidor con pikepdf): sin pérdida, 5 veces más
  // rápida que la normal y ~15 % más pesada — medido con 20 MB de contenido real: 0,4 s contra 2 s
  const pdf = out.saveToBuffer('compress,compression-effort=15').asUint8Array().slice()
  // Soltar YA la memoria de WebAssembly de esta mesa: el recolector de JavaScript no sabe cuánto
  // pesa del otro lado y, con 9 mesas de 50 MB, la pestaña llegaba al tope de 4 GB.
  try { mapa.destroy() } catch { /* nada */ }
  try { out.destroy() } catch { /* nada */ }
  page.destroy()
  return { pdf, placeholders, lineas, etiqueta_archivo: etqArchivo }
}
