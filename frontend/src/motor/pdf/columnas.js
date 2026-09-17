// EL CONTENT-STREAM EN COLUMNAS (PLAN_NAVEGADOR.md, etapa 1 — velocidad).
//
// 🔴 POR QUÉ (2026-09-17). El usuario: «si un molde con diseño demora un minuto o más ya es
// muchísimo; debe ser muy pocos segundos». El perfil de la camiseta de 28 MB mostró que leer las
// instrucciones como OBJETOS (uno por instrucción, uno por número: 2,35 millones de instrucciones y
// unos 12 millones de números) era un tercio del tiempo, y el resto del armado de páginas era
// recorrer esos objetos. Acá el contenido se lee a arreglos numéricos: por instrucción, su
// operador (un código) y dónde están sus operandos; por operando, su tipo y dónde está en los bytes
// originales. Nada se decodifica hasta que alguien lo pide (casi ningún número del diseño hace falta).
//
// El RESULTADO es el mismo que el lector de `contenido.js` (que es el de pikepdf): mismos operadores,
// mismos operandos, y al escribir, los MISMOS bytes que `pikepdf.unparse_content_stream`. Lo prueba
// `verificar_navegador_columnas.py` contra pikepdf sobre los moldes reales.

import { instrucciones as leerObjetos, operandoTexto } from './contenido.js'

// ─── operadores: un código por nombre, para todo el programa ────────────────────────────────
export const OPS = []
const CODIGO = new Map()
export function codigo(nombre) {
  let c = CODIGO.get(nombre)
  if (c === undefined) { c = OPS.length; OPS.push(nombre); CODIGO.set(nombre, c) }
  return c
}
export const OP = {}
for (const n of ['q', 'Q', 'cm', 'BDC', 'BMC', 'EMC', 'MP', 'DP', 'BT', 'ET', 'Tf', 'Tm', 'Td', 'TD', 'TL', 'Tc', 'Tw', 'Tz',
  'T*', "'", '"', 'Tj', 'TJ', 'Tr', 'cs', 'CS', 'k', 'rg', 'g', 'K', 'RG', 'G', 'sc', 'scn', 'SC', 'SCN', 'w', 'M', 'J',
  'j', 'd', 'gs', 'ri', 'i', 'm', 'l', 'c', 'v', 'y', 're', 'h', 'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n',
  'W', 'W*', 'Do', 'sh', 'BI', 'ID', 'INLINE IMAGE']) OP[n] = codigo(n)

// tipos de operando
export const T = { INT: 1, REAL: 2, NOMBRE: 3, TEXTO: 4, HEX: 5, ARREGLO: 6, DICC: 7, TRUE: 8, FALSE: 9, NULL: 10 }

const ESP = new Uint8Array(256)       // 1 = espacio, 2 = delimitador
for (const c of [0, 9, 10, 12, 13, 32]) ESP[c] = 1
for (const c of '()<>[]{}/%') ESP[c.charCodeAt(0)] = 2
const HEXV = new Int8Array(256).fill(-1)
for (let c = 48; c <= 57; c++) HEXV[c] = c - 48
for (let c = 65; c <= 70; c++) HEXV[c] = c - 55
for (let c = 97; c <= 102; c++) HEXV[c] = c - 87

const OPCORTO = new Map()
function textoCorto(b, i, j) {
  let s = ''
  for (let k = i; k < j; k++) s += String.fromCharCode(b[k])
  return s
}
function codigoDeBytes(b, i, j) {
  const n = j - i
  if (n <= 3) {
    const clave = n | (b[i] << 2) | ((n > 1 ? b[i + 1] : 0) << 10) | ((n > 2 ? b[i + 2] : 0) << 18)
    let c = OPCORTO.get(clave)
    if (c === undefined) { c = codigo(textoCorto(b, i, j)); OPCORTO.set(clave, c) }
    return c
  }
  return codigo(textoCorto(b, i, j))
}

function crecerU32(a, n) { const x = new Uint32Array(n); x.set(a); return x }
function crecerU16(a, n) { const x = new Uint16Array(n); x.set(a); return x }
function crecerU8(a, n) { const x = new Uint8Array(n); x.set(a); return x }
function crecerF64(a, n) { const x = new Float64Array(n).fill(NaN); x.set(a); return x }

/**
 * Lee `b` (bytes descomprimidos) a columnas. Devuelve
 * `{b, ni, op, a0, na, no, t, v, s0, s1, imagenes: Map(instrucción → {pares, datos})}`.
 */
export function leerColumnas(b) {
  const n = b.length
  let capI = Math.max(1024, (n / 20) | 0), capO = Math.max(4096, (n / 5) | 0)
  let op = new Uint16Array(capI), a0 = new Uint32Array(capI), na = new Uint16Array(capI)
  let t = new Uint8Array(capO), s0 = new Uint32Array(capO), s1 = new Uint32Array(capO)
  let v = new Float64Array(capO).fill(NaN)
  let ni = 0, no = 0
  const imagenes = new Map()
  let p = 0

  // token actual
  let tipo = 0             // 0 fin, 1 valor, 2 op, 3 [, 4 ], 5 <<, 6 >>, 7 raro
  let vt = 0, vv = NaN, vs0 = 0, vs1 = 0, vop = 0

  function saltarLiteral() {
    let prof = 1
    while (p < n) {
      const c = b[p++]
      if (c === 92) { if (p < n) p++; continue }
      if (c === 40) prof++
      else if (c === 41) { prof--; if (prof === 0) break }
    }
  }
  function saltarHex() { while (p < n) { if (b[p++] === 62) break } }

  function regular() {
    const i = p
    while (p < n && ESP[b[p]] === 0) p++
    const j = p
    let k = i
    const c0 = b[k]
    if (c0 === 43 || c0 === 45) k++
    let digitos = 0, punto = 0, decimales = 0, raro = false, val = 0
    for (let q = k; q < j; q++) {
      const c = b[q]
      if (c >= 48 && c <= 57) { if (punto) decimales++; else { digitos++; val = val * 10 + (c - 48) } }
      else if (c === 46 && !punto) punto = 1
      else { raro = true; break }
    }
    vs0 = i; vs1 = j
    if (!raro && j > k) {
      if (!punto && digitos) {
        tipo = 1; vt = T.INT
        vv = digitos > 15 ? Number(textoCorto(b, i, j)) : (c0 === 45 ? -val : val)
        return
      }
      if (punto && (digitos || decimales)) { tipo = 1; vt = T.REAL; vv = NaN; return }
    }
    const len = j - i
    if (len === 4 && c0 === 116 && b[i + 1] === 114 && b[i + 2] === 117 && b[i + 3] === 101) { tipo = 1; vt = T.TRUE; return }
    if (len === 5 && c0 === 102 && b[i + 1] === 97 && b[i + 2] === 108 && b[i + 3] === 115 && b[i + 4] === 101) { tipo = 1; vt = T.FALSE; return }
    if (len === 4 && c0 === 110 && b[i + 1] === 117 && b[i + 2] === 108 && b[i + 3] === 108) { tipo = 1; vt = T.NULL; return }
    tipo = 2
    vop = codigoDeBytes(b, i, j)
  }

  function sig() {
    for (;;) {
      if (p >= n) { tipo = 0; return }
      const c = b[p]
      const e = ESP[c]
      if (e === 1) { p++; continue }
      if (c === 37) { while (p < n && b[p] !== 10 && b[p] !== 13) p++; continue }
      if (e === 0) { regular(); return }
      if (c === 40) { vs0 = p; p++; saltarLiteral(); vs1 = p; tipo = 1; vt = T.TEXTO; return }
      if (c === 60) {
        if (b[p + 1] === 60) { vs0 = p; p += 2; tipo = 5; return }
        vs0 = p; p++; saltarHex(); vs1 = p; tipo = 1; vt = T.HEX; return
      }
      if (c === 62 && b[p + 1] === 62) { p += 2; tipo = 6; return }
      if (c === 91) { vs0 = p; p++; tipo = 3; return }
      if (c === 93) { p++; tipo = 4; return }
      if (c === 47) {
        p++
        vs0 = p
        while (p < n && ESP[b[p]] === 0) {
          if (b[p] === 35 && p + 2 < n && HEXV[b[p + 1]] >= 0 && HEXV[b[p + 2]] >= 0) { p += 3; continue }
          p++
        }
        vs1 = p; tipo = 1; vt = T.NOMBRE; return
      }
      p++; tipo = 7; return
    }
  }

  // saltea un valor compuesto con el MISMO consumo que `valorCompuesto` de `contenido.js`
  function saltarCompuesto() {
    if (tipo === 1) return
    if (tipo === 3) {
      for (;;) {
        sig()
        if (tipo === 0 || tipo === 4) return
        if (tipo === 2) continue
        saltarCompuesto()
      }
    }
    if (tipo === 5) {
      for (;;) {
        sig()
        if (tipo === 0 || tipo === 6) return
        const esNombre = tipo === 1 && vt === T.NOMBRE
        sig()
        if (tipo === 0 || tipo === 6) return
        if (esNombre) saltarCompuesto()
      }
    }
  }

  function empujarOperando(tipoOp, s0v, s1v, val) {
    if (no >= capO) {
      capO *= 2
      t = crecerU8(t, capO); s0 = crecerU32(s0, capO); s1 = crecerU32(s1, capO); v = crecerF64(v, capO)
    }
    t[no] = tipoOp; s0[no] = s0v; s1[no] = s1v; v[no] = val
    no++
  }

  let pend = 0
  for (;;) {
    sig()
    if (tipo === 0) break
    if (tipo === 2) {
      if (vop === OP.BI) {
        // la imagen en línea (rarísima en un molde): mismo consumo que `imagenEnLinea` de contenido.js
        const pares = []
        let completa = false
        for (;;) {
          sig()
          if (tipo === 0) break
          if (tipo === 2 && OPS[vop] === 'ID') { completa = true; break }
          const esNombre = tipo === 1 && vt === T.NOMBRE, kIni = vs0, kFin = vs1
          sig()
          // (el tramo de un nombre empieza DESPUÉS de la «/»: para releerlo hay que incluirla)
          const vIni = (tipo === 1 && vt === T.NOMBRE) ? vs0 - 1 : ((tipo === 1 || tipo === 3 || tipo === 5) ? vs0 : p)
          saltarCompuesto()
          const vFin = tipo === 1 ? vs1 : p
          if (esNombre) pares.push([kIni, kFin, vIni, vFin])
        }
        if (completa) {
          if (ESP[b[p]] === 1) p++
          const ini = p
          while (p < n) {
            if (b[p] === 69 && b[p + 1] === 73 && ESP[b[p - 1]] === 1 && (p + 2 >= n || ESP[b[p + 2]] !== 0)) break
            p++
          }
          const datos = b.subarray(ini, p)
          p += 2
          const decod = pares.map(([ki, kf, vi, vf]) => {
            const clave = [...leerObjetos(concatenarOp(b.subarray(ki - 1, kf)))][0].args[0].n
            const r = [...leerObjetos(concatenarOp(b.subarray(vi, vf)))]
            return [clave, r.length ? r[0].args[0] : undefined]
          })
          if (ni >= capI) { capI *= 2; op = crecerU16(op, capI); a0 = crecerU32(a0, capI); na = crecerU16(na, capI) }
          op[ni] = OP['INLINE IMAGE']; a0[ni] = no; na[ni] = 0
          imagenes.set(ni, { pares: decod, dict: new Map(decod), datos })
          ni++
        }
        no = pend
        continue
      }
      if (ni >= capI) { capI *= 2; op = crecerU16(op, capI); a0 = crecerU32(a0, capI); na = crecerU16(na, capI) }
      op[ni] = vop; a0[ni] = pend; na[ni] = no - pend
      ni++
      pend = no
      continue
    }
    if (tipo === 7 || tipo === 4 || tipo === 6) continue
    if (tipo === 1) { empujarOperando(vt, vs0, vs1, vv); continue }
    const ini = vs0
    const t0 = tipo
    saltarCompuesto()
    empujarOperando(t0 === 3 ? T.ARREGLO : T.DICC, ini, p, NaN)
  }
  return { b, ni, op, a0, na, no, t, v, s0, s1, imagenes, cache: new Map() }
}

// ─── leer un operando ────────────────────────────────────────────────────────────────────────
export class NoEsNumero extends Error {}

export function numero(C, o) {
  const tt = C.t[o]
  if (tt === T.INT) return C.v[o]
  if (tt === T.REAL) {
    let x = C.v[o]
    if (x !== x) { x = Number(textoCorto(C.b, C.s0[o], C.s1[o])); C.v[o] = x }
    return x
  }
  if (tt === T.TRUE) return 1
  if (tt === T.FALSE) return 0
  throw new NoEsNumero()
}

export function entero(C, o) {
  const tt = C.t[o]
  if (tt === T.REAL) return Math.trunc(numero(C, o))
  return numero(C, o)
}

/** El nombre decodificado (sin «/»), o null si el operando no es un nombre. */
export function nombre(C, o) {
  if (C.t[o] !== T.NOMBRE) return null
  let s = C.cache.get(o)
  if (s === undefined) {
    const b = C.b
    s = ''
    for (let p = C.s0[o]; p < C.s1[o];) {
      const c = b[p]
      if (c === 35 && p + 2 < C.s1[o] + 0 && HEXV[b[p + 1]] >= 0 && HEXV[b[p + 2]] >= 0) {
        s += String.fromCharCode(HEXV[b[p + 1]] * 16 + HEXV[b[p + 2]]); p += 3; continue
      }
      s += String.fromCharCode(c); p++
    }
    C.cache.set(o, s)
  }
  return s
}

/** El valor como lo da el lector de objetos (`{s}`, `{n}`, `[…]`, `{d}`, número…). */
export function valor(C, o) {
  const tt = C.t[o]
  if (tt === T.INT) return { i: C.v[o] }
  if (tt === T.REAL) return { r: textoCorto(C.b, C.s0[o], C.s1[o]) }
  if (tt === T.NOMBRE) return { n: nombre(C, o) }
  if (tt === T.TRUE) return true
  if (tt === T.FALSE) return false
  if (tt === T.NULL) return null
  let x = C.cache.get(o)
  if (x === undefined) {
    // textos, arreglos y diccionarios: se decodifican con el lector de objetos sobre su tramo
    const r = [...leerObjetos(concatenarOp(C.b.subarray(C.s0[o], C.s1[o])))]
    x = r.length ? r[0].args[0] : undefined
    C.cache.set(o, x)
  }
  return x
}
const _OPFALSO = new Uint8Array([32, 110])          // « n»: un operador para cerrar el tramo
function concatenarOp(u8) {
  const out = new Uint8Array(u8.length + 2)
  out.set(u8)
  out.set(_OPFALSO, u8.length)
  return out
}

/** Los bytes de un texto (`Tj`), o tira `NoEsNumero` si no es un texto (como `bytes(v)` en Python). */
export function bytesTexto(C, o) {
  const tt = C.t[o]
  if (tt !== T.TEXTO && tt !== T.HEX) throw new NoEsNumero()
  return valor(C, o).s
}

// ─── escribir ────────────────────────────────────────────────────────────────────────────────
const BYTES_OP = []
function bytesOp(c) {
  let x = BYTES_OP[c]
  if (x === undefined) {
    const s = OPS[c]
    x = new Uint8Array(s.length)
    for (let i = 0; i < s.length; i++) x[i] = s.charCodeAt(i) & 255
    BYTES_OP[c] = x
  }
  return x
}

function nombreCanonico(b, i, j) {
  for (let k = i; k < j; k++) {
    const c = b[k]
    if (c < 33 || c > 126 || c === 35 || ESP[c] === 2) return false
  }
  return true
}
function enteroCanonico(b, i, j) {
  if (b[i] === 43) return false
  if (b[i] === 45) {
    if (j - i < 2 || b[i + 1] === 48) return false            // «-0…»
    return true
  }
  if (b[i] === 48 && j - i > 1) return false                    // ceros a la izquierda
  return true
}

/**
 * Escribe una lista de instrucciones: `refs[k] >= 0` = la instrucción `refs[k]` de `C`;
 * `refs[k] < 0` = `sinteticas[-refs[k] - 1]` = `{op: código, args: [{o} (operando de C) …]}`.
 * Mismos bytes que `pikepdf.unparse_content_stream`.
 */
export function escribirColumnas(C, refs, nRefs, sinteticas = []) {
  const b = C.b
  let cap = 1 << 16
  for (let k = 0; k < nRefs; k++) {
    const r = refs[k]
    if (r >= 0) {
      const o0 = C.a0[r], o1 = o0 + C.na[r]
      cap += (C.na[r] ? (C.s1[o1 - 1] - C.s0[o0]) : 0) + 16 + C.na[r] * 4
    } else cap += 64
  }
  let out = new Uint8Array(cap)
  let p = 0
  const asegurar = (n) => { if (p + n > out.length) { const x = new Uint8Array((out.length + n) * 2); x.set(out.subarray(0, p)); out = x } }
  const txt = (s) => { asegurar(s.length); for (let i = 0; i < s.length; i++) out[p++] = s.charCodeAt(i) & 255 }
  // byte a byte: los tokens son de pocos bytes y `out.set(b.subarray(…))` crea un objeto por token
  const copiar = (i, j) => {
    if (p + (j - i) > out.length) asegurar(j - i)
    for (let k = i; k < j; k++) out[p++] = b[k]
  }
  const operando = (o) => {
    const tt = C.t[o]
    const i = C.s0[o], j = C.s1[o]
    if (tt === T.REAL) return copiar(i, j)
    if (tt === T.INT) {
      if (j - i <= 15 && enteroCanonico(b, i, j)) return copiar(i, j)
      return txt(String(C.v[o]).replace(/^-0$/, '0'))
    }
    if (tt === T.NOMBRE) {
      if (nombreCanonico(b, i, j)) { asegurar(1); out[p++] = 47; return copiar(i, j) }
      return txt(operandoTexto({ n: nombre(C, o) }))
    }
    if (tt === T.TRUE) return txt('true')
    if (tt === T.FALSE) return txt('false')
    if (tt === T.NULL) return txt('null')
    return txt(operandoTexto(valor(C, o)))
  }
  for (let k = 0; k < nRefs; k++) {
    if (k) { asegurar(1); out[p++] = 10 }
    const r = refs[k]
    if (r >= 0) {
      const c = C.op[r]
      if (c === OP['INLINE IMAGE']) {
        const im = C.imagenes.get(r)
        const partes = []
        const ABREV = { Width: 'W', Height: 'H', BitsPerComponent: 'BPC', ImageMask: 'IM', ColorSpace: 'CS', Filter: 'F', DecodeParms: 'DP', DeviceGray: 'G', DeviceRGB: 'RGB', DeviceCMYK: 'CMYK', Indexed: 'I', ASCIIHexDecode: 'AHx', ASCII85Decode: 'A85', LZWDecode: 'LZW', RunLengthDecode: 'RL', CCITTFaxDecode: 'CCF', DCTDecode: 'DCT' }
        for (const [kk, vv] of im.pares) {
          const k2 = ABREV[kk] || kk
          const v2 = (vv && vv.n !== undefined && ABREV[vv.n]) ? { n: ABREV[vv.n] } : vv
          partes.push(operandoTexto({ n: k2 }), operandoTexto(v2))
        }
        txt('BI\n' + partes.join(' ') + '\nID\n')
        asegurar(im.datos.length); out.set(im.datos, p); p += im.datos.length
        txt('EI')
        continue
      }
      const o0 = C.a0[r], o1 = o0 + C.na[r]
      for (let o = o0; o < o1; o++) { operando(o); asegurar(1); out[p++] = 32 }
      const ob = bytesOp(c)
      asegurar(ob.length); out.set(ob, p); p += ob.length
    } else {
      const s = sinteticas[-r - 1]
      for (const a of s.args) { operando(a); asegurar(1); out[p++] = 32 }
      const ob = bytesOp(s.op)
      asegurar(ob.length); out.set(ob, p); p += ob.length
    }
  }
  return out.slice(0, p)
}
