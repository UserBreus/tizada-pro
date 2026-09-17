// TEXTO A CURVAS EN EL NAVEGADOR — traducción de `texto_curvas.py` (`FuenteCurvas`).
//
// PLAN_NAVEGADOR.md, etapa 3, punto 2. El nombre/número que se estampa NO es texto vivo: son los
// contornos de la tipografía convertidos a operadores de trazado PDF (m / l / c / h). Este módulo
// tiene que emitir EXACTAMENTE los mismos operadores que el servidor para los mismos bytes de fuente,
// texto, tamaño y posición: lo vigila `verificar_navegador_curvas.py` (comparación de cadenas).
//
// Los comentarios que explican el PORQUÉ de cada regla están en el Python; acá se repiten sólo los
// que cambian cómo se escribe en JavaScript. Lo NO obvio que hubo que reproducir de fontTools:
//
//   · Las cuadráticas TrueType NO se toman del `path` de opentype.js (arranca cada contorno en otro
//     punto y ya parte los off-curve consecutivos): se leen los puntos crudos de `glyf` y se recorre
//     el contorno como `Glyph.draw` de fontTools (rotar hasta que termine en un on-curve, `moveTo`
//     al último, `qCurveTo` con TODOS los off-curve seguidos, `lineTo` final implícito en el `h`).
//     La elevación a cúbica (regla 2/3) es la de `texto_curvas._ops_glifo`, en el mismo orden.
//   · Los compuestos se descomponen como `DecomposingRecordingPen` + `TransformPen`: la matriz del
//     componente es (xx, xy, yx, yy, dx, dy) con `transformPoint` = (xx·x + yx·y + dx, xy·x + yy·y + dy),
//     los anidados componen la matriz (`Transform.transform`) y se dibujan con UNA sola transformación;
//     un componente por «punto emparejado» (sin ARGS_ARE_XY_VALUES) es un error en fontTools → acá también.
//   · fontTools corre el glifo de primer nivel `lsb − xMin` en x (`_TTGlyphGlyf._getGlyphAndOffset`);
//     en las fuentes bien hechas es 0, pero se reproduce.
//   · El `cmap` se elige con la prioridad de `getBestCmap` ((3,10), (0,6), (0,4), (3,1), (0,3), (0,2),
//     (0,1), (0,0)) leyendo la tabla cruda: opentype.js elige OTRA subtabla (la última que encuentra,
//     y acepta Mac Roman) y no sirve para esto. Los glifos 0 se descartan (`_make_map`).
//   · Las fuentes CFF (.otf) sí usan el `path` de opentype.js: sus comandos M/L/C/Z son los mismos
//     verbos que emite el `T2OutlineExtractor` de fontTools (moveTo/lineTo/curveTo/closePath).
//
// Formato de un «registro» (lo que en Python graba el pen): [verbo, args] con args = lista de
// puntos [x, y] (o `null` en el último de un `qCurveTo` sin on-curve, igual que fontTools).

import * as _ot from 'opentype.js'
// Vite toma el `module` (ESM, exporta `parse`); Node toma el `main` (CommonJS → todo en `default`)
const opentype = _ot.parse ? _ot : _ot.default
import { pyFixed, pyIsSpace, pyStrip, pySum } from '../py.js'

// ─── lectura cruda del sfnt (lo que opentype.js no expone tal cual) ──────────────────────────

/** Directorio de tablas del sfnt: tag → { offset, length }. Las colecciones (ttcf) no se admiten:
 *  `TTFont` tampoco las abre sin `fontNumber`, y el catálogo sube archivos de una sola fuente. */
function tablasSfnt(dv) {
  const tag = dv.getUint32(0)
  if (tag === 0x74746366) throw new Error('colección TrueType (ttcf): no se admite')   // 'ttcf'
  const n = dv.getUint16(4)
  const tablas = new Map()
  for (let i = 0; i < n; i++) {
    const o = 12 + i * 16
    const t = String.fromCharCode(dv.getUint8(o), dv.getUint8(o + 1), dv.getUint8(o + 2), dv.getUint8(o + 3))
    tablas.set(t, { offset: dv.getUint32(o + 8), length: dv.getUint32(o + 12) })
  }
  return tablas
}

// Python `bytes([b]).decode("mac_roman")` para b ≥ 128 (los de abajo son ASCII).
const MAC_ROMAN_ALTOS = [196, 197, 199, 201, 209, 214, 220, 225, 224, 226, 228, 227, 229, 231, 233, 232, 234, 235, 237, 236, 238, 239, 241, 243, 242, 244, 246, 245, 250, 249, 251, 252, 8224, 176, 162, 163, 167, 8226, 182, 223, 174, 169, 8482, 180, 168, 8800, 198, 216, 8734, 177, 8804, 8805, 165, 181, 8706, 8721, 8719, 960, 8747, 170, 186, 937, 230, 248, 191, 161, 172, 8730, 402, 8776, 8710, 171, 187, 8230, 160, 192, 195, 213, 338, 339, 8211, 8212, 8220, 8221, 8216, 8217, 247, 9674, 255, 376, 8260, 8364, 8249, 8250, 64257, 64258, 8225, 183, 8218, 8222, 8240, 194, 202, 193, 203, 200, 205, 206, 207, 204, 211, 212, 63743, 210, 218, 219, 217, 305, 710, 732, 175, 728, 729, 730, 184, 733, 731, 711]

/** Una subtabla de `cmap` como la decodifica fontTools: lista ORDENADA de [código, gid] (gid ≠ 0). */
function decodificarSubtabla(dv, base) {
  const formato = dv.getUint16(base)
  const pares = []
  if (formato === 0) {
    for (let c = 0; c < 256; c++) {
      const gid = dv.getUint8(base + 6 + c)
      if (gid) pares.push([c, gid])
    }
  } else if (formato === 4) {
    const segX2 = dv.getUint16(base + 6)
    const seg = segX2 >> 1
    const endCode = base + 14, startCode = endCode + segX2 + 2, idDelta = startCode + segX2, idRange = idDelta + segX2
    const gia = idRange + segX2                                     // glyphIndexArray
    const lenGIA = (dv.getUint16(base + 2) - (gia - base)) >> 1     // lo que queda de la subtabla
    for (let i = 0; i < seg - 1; i++) {                             // fontTools salta el último (0xFFFF)
      const start = dv.getUint16(startCode + i * 2), end = dv.getUint16(endCode + i * 2)
      const delta = dv.getUint16(idDelta + i * 2), ro = dv.getUint16(idRange + i * 2)
      const partial = (ro >> 1) - start + i - seg
      for (let c = start; c <= end; c++) {
        let gid
        if (ro === 0) gid = (c + delta) & 0xFFFF
        else {
          const idx = c + partial
          if (idx >= lenGIA) throw new Error('cmap formato 4: índice fuera del glyphIndexArray')
          const g = dv.getUint16(gia + idx * 2)
          gid = g !== 0 ? (g + delta) & 0xFFFF : 0
        }
        if (gid) pares.push([c, gid])
      }
    }
  } else if (formato === 6) {
    const first = dv.getUint16(base + 6), cnt = dv.getUint16(base + 8)
    for (let k = 0; k < cnt; k++) {
      const gid = dv.getUint16(base + 10 + k * 2)
      if (gid) pares.push([first + k, gid])
    }
  } else if (formato === 12 || formato === 13) {
    const nGrupos = dv.getUint32(base + 12)
    for (let g = 0; g < nGrupos; g++) {
      const o = base + 16 + g * 12
      const s = dv.getUint32(o), e = dv.getUint32(o + 4), g0 = dv.getUint32(o + 8)
      for (let c = s; c <= e; c++) {
        const gid = formato === 12 ? g0 + (c - s) : g0
        if (gid) pares.push([c, gid])
      }
    }
  }
  // otros formatos (2, 8, 10, 14): no hay ninguno en el catálogo; se leen vacíos
  return pares
}

/** Las subtablas del `cmap` en el orden del archivo, con decodificación perezosa. */
function subtablasCmap(dv, tablas) {
  const t = tablas.get('cmap')
  if (!t) return []
  const n = dv.getUint16(t.offset + 2)
  const out = []
  for (let i = 0; i < n; i++) {
    const o = t.offset + 4 + i * 8
    const st = { platformID: dv.getUint16(o), platEncID: dv.getUint16(o + 2), _off: t.offset + dv.getUint32(o + 4), _pares: null }
    st.pares = () => (st._pares ??= decodificarSubtabla(dv, st._off))
    out.push(st)
  }
  return out
}

const PREFERENCIA_CMAP = [[3, 10], [0, 6], [0, 4], [3, 1], [0, 3], [0, 2], [0, 1], [0, 0]]

// ─── `glyf` crudo, dibujado como `Glyph.draw` de fontTools ───────────────────────────────────

const ON_CURVE = 0x01, X_SHORT = 0x02, Y_SHORT = 0x04, REPEAT = 0x08, X_SAME = 0x10, Y_SAME = 0x20, CUBIC = 0x80
const ARG_1_AND_2_ARE_WORDS = 0x0001, ARGS_ARE_XY_VALUES = 0x0002, WE_HAVE_A_SCALE = 0x0008, MORE_COMPONENTS = 0x0020,
  WE_HAVE_AN_X_AND_Y_SCALE = 0x0040, WE_HAVE_A_TWO_BY_TWO = 0x0080

const IDENTIDAD = [1, 0, 0, 1, 0, 0]
const esIdentidad = (t) => t.every((v, i) => v === IDENTIDAD[i])
const f2dot14 = (v) => v / 16384                                    // `fixedToFloat(v, 14)`
const maybeInt = (v) => v                                           // sólo cambia el TIPO en Python

/** `Transform.transform(other)` de fontTools: `self` (t2) transformada por `other` (t1). */
function componer(t2, t1) {
  const [xx1, xy1, yx1, yy1, dx1, dy1] = t1
  const [xx2, xy2, yx2, yy2, dx2, dy2] = t2
  return [xx1 * xx2 + xy1 * yx2, xx1 * xy2 + xy1 * yy2, yx1 * xx2 + yy1 * yx2, yx1 * xy2 + yy1 * yy2,
    xx2 * dx1 + yx2 * dy1 + dx2, xy2 * dx1 + yy2 * dy1 + dy2]
}
/** `Transform.transformPoint`. */
function transformar(t, p) {
  const [xx, xy, yx, yy, dx, dy] = t
  return [xx * p[0] + yx * p[1] + dx, xy * p[0] + yy * p[1] + dy]
}

/** Un glifo de `glyf` leído tal cual: { xMin, contornos: [{puntos:[[x,y]], flags:[]}] } o
 *  { xMin, componentes: [{gid, trans}] } o null si no tiene datos (glifo vacío). */
function leerGlyf(dv, base, largo) {
  if (!largo) return null
  const nContornos = dv.getInt16(base)
  const xMin = dv.getInt16(base + 2)
  let p = base + 10
  if (nContornos === 0) return { xMin, contornos: [] }
  if (nContornos < 0) {
    const componentes = []
    let mas = true
    while (mas) {
      const flags = dv.getUint16(p); const gid = dv.getUint16(p + 2); p += 4
      let x = null, y = null
      if (flags & ARG_1_AND_2_ARE_WORDS) {
        if (flags & ARGS_ARE_XY_VALUES) { x = dv.getInt16(p); y = dv.getInt16(p + 2) }
        p += 4
      } else {
        if (flags & ARGS_ARE_XY_VALUES) { x = dv.getInt8(p); y = dv.getInt8(p + 1) }
        p += 2
      }
      let m = [1, 0, 0, 1]
      if (flags & WE_HAVE_A_SCALE) { const s = f2dot14(dv.getInt16(p)); m = [s, 0, 0, s]; p += 2 }
      else if (flags & WE_HAVE_AN_X_AND_Y_SCALE) { m = [f2dot14(dv.getInt16(p)), 0, 0, f2dot14(dv.getInt16(p + 2))]; p += 4 }
      else if (flags & WE_HAVE_A_TWO_BY_TWO) {
        m = [f2dot14(dv.getInt16(p)), f2dot14(dv.getInt16(p + 2)), f2dot14(dv.getInt16(p + 4)), f2dot14(dv.getInt16(p + 6))]; p += 8
      }
      // (xx, xy, yx, yy, x, y) como `getComponentInfo`; sin ARGS_ARE_XY_VALUES fontTools revienta
      // con AttributeError al dibujar → acá el `trans` queda null y se revienta en el mismo momento
      componentes.push({ gid, trans: x === null ? null : [m[0], m[1], m[2], m[3], x, y] })
      mas = (flags & MORE_COMPONENTS) !== 0
    }
    return { xMin, componentes }
  }
  const fines = []
  for (let i = 0; i < nContornos; i++) { fines.push(dv.getUint16(p)); p += 2 }
  const nInstr = dv.getUint16(p); p += 2 + nInstr
  const nPuntos = fines[fines.length - 1] + 1
  const flags = []
  while (flags.length < nPuntos) {
    const f = dv.getUint8(p++)
    flags.push(f)
    if (f & REPEAT) { const r = dv.getUint8(p++); for (let k = 0; k < r; k++) flags.push(f) }
  }
  if (flags.length !== nPuntos) throw new Error('glyf: flags de más')
  const xs = new Array(nPuntos), ys = new Array(nPuntos)
  let v = 0
  for (let i = 0; i < nPuntos; i++) {
    const f = flags[i]
    if (f & X_SHORT) { const d = dv.getUint8(p++); v += (f & X_SAME) ? d : -d }
    else if (!(f & X_SAME)) { v += dv.getInt16(p); p += 2 }
    xs[i] = v
  }
  v = 0
  for (let i = 0; i < nPuntos; i++) {
    const f = flags[i]
    if (f & Y_SHORT) { const d = dv.getUint8(p++); v += (f & Y_SAME) ? d : -d }
    else if (!(f & Y_SAME)) { v += dv.getInt16(p); p += 2 }
    ys[i] = v
  }
  const contornos = []
  let ini = 0
  for (const fin of fines) {
    const puntos = [], fl = []
    for (let i = ini; i <= fin; i++) { puntos.push([xs[i], ys[i]]); fl.push(flags[i]) }
    contornos.push({ puntos, flags: fl })
    ini = fin + 1
  }
  return { xMin, contornos }
}

/** `Glyph.draw` de fontTools para un glifo simple: graba en `pen` (una función (verbo, args)). */
function dibujarSimple(g, offset, pen) {
  for (const c of g.contornos) {
    let contour = offset ? c.puntos.map(([x, y]) => [x + offset, y]) : c.puntos.slice()
    let cFlags = c.flags.map((f) => f & ON_CURVE)
    let cuFlags = c.flags.map((f) => f & CUBIC)
    if (!cFlags.includes(1)) {
      const cubic = cuFlags.every((f) => f)
      if (cubic) {
        const count = contour.length
        if (count % 2) throw new Error('Odd number of cubic off-curves undefined')
        const l = contour[count - 1], f = contour[0]
        pen('moveTo', [[maybeInt((l[0] + f[0]) * 0.5), maybeInt((l[1] + f[1]) * 0.5)]])
        for (let i = 0; i < count; i += 2) {
          const p1 = contour[i], p2 = contour[i + 1], p4 = contour[i + 2 < count ? i + 2 : 0]
          pen('curveTo', [p1, p2, [maybeInt((p2[0] + p4[0]) * 0.5), maybeInt((p2[1] + p4[1]) * 0.5)]])
        }
      } else {
        pen('qCurveTo', [...contour, null])        // sin ningún on-curve: el caso especial de fontTools
      }
    } else {
      const firstOnCurve = cFlags.indexOf(1) + 1
      contour = contour.slice(firstOnCurve).concat(contour.slice(0, firstOnCurve))
      cFlags = cFlags.slice(firstOnCurve).concat(cFlags.slice(0, firstOnCurve))
      cuFlags = cuFlags.slice(firstOnCurve).concat(cuFlags.slice(0, firstOnCurve))
      pen('moveTo', [contour[contour.length - 1]])
      while (contour.length) {
        const nextOnCurve = cFlags.indexOf(1) + 1
        if (nextOnCurve === 1) {
          if (contour.length > 1) pen('lineTo', [contour[0]])   // el último lineTo lo implica el closePath
        } else {
          const cubicFlags = cuFlags.slice(0, nextOnCurve - 1)
          const cubic = cubicFlags.some((f) => f)
          if (cubic) {
            if (!cubicFlags.every((f) => f)) throw new Error('Mixed cubic and quadratic segment undefined')
            const count = nextOnCurve
            if (count < 3) throw new Error('At least two cubic off-curve points required')
            if ((count - 1) % 2) throw new Error('Odd number of cubic off-curves undefined')
            for (let i = 0; i < count - 3; i += 2) {
              const p1 = contour[i], p2 = contour[i + 1], p4 = contour[i + 2]
              pen('curveTo', [p1, p2, [maybeInt((p2[0] + p4[0]) * 0.5), maybeInt((p2[1] + p4[1]) * 0.5)]])
            }
            pen('curveTo', contour.slice(count - 3, count))
          } else {
            pen('qCurveTo', contour.slice(0, nextOnCurve))
          }
        }
        contour = contour.slice(nextOnCurve)
        cFlags = cFlags.slice(nextOnCurve)
        cuFlags = cuFlags.slice(nextOnCurve)
      }
      pen('closePath', [])
    }
  }
}

// ─── la fuente ───────────────────────────────────────────────────────────────────────────────

export class FuenteCurvas {
  /** @param {ArrayBuffer|Uint8Array} fuenteBytes  @param {FuenteCurvas|null} respaldo */
  constructor(fuenteBytes, respaldo = null) {
    const u8 = fuenteBytes instanceof Uint8Array ? fuenteBytes : new Uint8Array(fuenteBytes)
    const ab = u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength)
    this._dv = new DataView(ab)
    this._tablas = tablasSfnt(this._dv)
    this.font = opentype.parse(ab)
    this.esCFF = !!(this.font.tables.cff || this.font.tables.cff2)
    this.numGlyphs = this.font.numGlyphs
    this._subtablas = subtablasCmap(this._dv, this._tablas)
    this.cmap = this._mejorCmap() || this._cmapDeRespaldo()
    this.upem = this.font.tables.head.unitsPerEm
    this._cache = new Map()
    this._cap = null
    this._capCalculando = false
    this.respaldo = respaldo
    this.sustituidos = []
    this._nombres = null
    this._loca = null
  }

  /** `getBestCmap()`: la primera subtabla que exista en el orden de preferencia; null si no hay. */
  _mejorCmap() {
    for (const [pl, en] of PREFERENCIA_CMAP) {
      const st = this._subtablas.find((s) => s.platformID === pl && s.platEncID === en)
      if (st) {
        const m = new Map()
        for (const [c, gid] of st.pares()) m.set(c, gid)      // el último gana, como el dict
        return m
      }
    }
    return null
  }

  /** `_cmap_de_respaldo`: Mac Roman (1,0) y símbolo (3,0) pasados a unicode; nunca null. */
  _cmapDeRespaldo() {
    const mapa = new Map()
    const util = (gid) => !['.notdef', '.null', 'nonmarkingreturn'].includes(this._nombreGlifo(gid))
    for (const t of this._subtablas) {                            // 1) Mac Roman, un byte → unicode
      if (t.platformID === 1 && t.platEncID === 0) {
        for (const [code, gid] of t.pares()) {
          const cp = code >= 0 && code < 256 ? (code < 128 ? code : MAC_ROMAN_ALTOS[code - 128]) : null
          if (cp !== null && util(gid) && !mapa.has(cp)) mapa.set(cp, gid)
        }
      }
    }
    for (const t of this._subtablas) {                            // 2) símbolo: 0xF000 + código (pisa)
      if (t.platformID === 3 && t.platEncID === 0) {
        for (const [code, gid] of t.pares()) {
          const cp = code >= 0xF000 && code <= 0xF0FF ? code - 0xF000 : code
          if (util(gid)) mapa.set(cp, gid)
        }
      }
    }
    if (!mapa.size) {                                             // 3) lo que sea, tal cual
      for (const t of this._subtablas) for (const [code, gid] of t.pares()) if (!mapa.has(code)) mapa.set(code, gid)
    }
    return mapa
  }

  /** El nombre PostScript del glifo como lo vería `TTFont.getGlyphOrder()`. Sólo se usa para dos
   *  cosas: saber si hay un glifo llamado «space» y descartar «.notdef/.null/nonmarkingreturn».
   *  CFF: el charset. `post` 1.0/2.0: los nombres de la tabla (recortados a `numGlyphs`). Sin
   *  nombres (`post` 3.0): fontTools los inventa desde el cmap unicode (AGL, el menor código de cada
   *  glifo) — acá basta con «space» para el glifo al que apunte U+0020 en alguna subtabla unicode. */
  _nombreGlifo(gid) {
    if (gid === 0) return '.notdef'
    if (!this._nombres) {
      const nombres = new Map()
      if (this.esCFF) {
        for (let i = 0; i < this.numGlyphs; i++) nombres.set(i, this.font.glyphs.get(i).name || null)
      } else {
        const gn = this.font.glyphNames
        const post = this.font.tables.post
        if (gn && gn.names && gn.names.length && post && (post.version === 1 || post.version === 2)) {
          for (let i = 0; i < this.numGlyphs; i++) nombres.set(i, gn.names[i] ?? null)
        } else {
          for (const t of this._subtablas) {
            if (!(t.platformID === 0 || (t.platformID === 3 && [0, 1, 10].includes(t.platEncID)))) continue
            for (const [c, g] of t.pares()) if (g && (!nombres.has(g) || c < nombres.get(g))) nombres.set(g, c)
          }
          for (const [g, c] of nombres) nombres.set(g, c === 0x20 ? 'space' : `uni${c.toString(16).toUpperCase().padStart(4, '0')}`)
        }
      }
      this._nombres = nombres
    }
    return this._nombres.get(gid) ?? null
  }

  _gidPorNombre(nombre) {
    for (let i = 0; i < this.numGlyphs; i++) if (this._nombreGlifo(i) === nombre) return i
    return null
  }

  get capRatio() {
    if (this._cap === null) {
      if (this._capCalculando) return 0.72          // re-entrada (medir la H prestada): lo que Python termina usando
      this._capCalculando = true
      let r = null
      try {
        const os2 = this.font.tables.os2
        if (!os2) throw new Error('sin OS/2')
        const cap = os2.sCapHeight
        if (cap && cap > 0) r = cap / this.upem
      } catch (e) { /* como el `except: pass` */ }
      if (!r) {
        try {                                        // medir la H real (su bbox vertical)
          const [ops] = this._glifo('H')
          const ys = []
          for (const [, args] of ops) for (const a of (args || [])) if (Array.isArray(a) && a.length === 2) ys.push(a[1])
          if (ys.length) r = (Math.max(...ys) - Math.min(...ys)) / this.upem
        } catch (e) { /* pass */ }
      }
      this._cap = r || 0.72
      this._capCalculando = false
    }
    return this._cap
  }

  sizeParaAlto(altoPt) {
    return Number(altoPt) / (this.capRatio || 0.72)
  }

  /** hmtx: [avance, lsb] del gid. */
  _metricas(gid) {
    const g = this.font.glyphs.get(gid)
    return [g.advanceWidth, g.leftSideBearing]
  }

  _loca_(gid) {
    if (!this._loca) {
      const t = this._tablas.get('loca')
      const largo = this.font.tables.head.indexToLocFormat
      const n = this.numGlyphs + 1
      const loca = new Array(n)
      for (let i = 0; i < n; i++) loca[i] = largo ? this._dv.getUint32(t.offset + i * 4) : this._dv.getUint16(t.offset + i * 2) * 2
      this._loca = loca
    }
    return [this._loca[gid], this._loca[gid + 1] - this._loca[gid]]
  }

  _glyf(gid) {
    const [o, largo] = this._loca_(gid)
    return leerGlyf(this._dv, this._tablas.get('glyf').offset + o, largo)
  }

  /** Los registros del glifo `gid` como los graba `DecomposingRecordingPen`. */
  _registros(gid) {
    const registros = []
    if (this.esCFF) {
      const path = this.font.glyphs.get(gid).path
      for (const c of path.commands) {
        if (c.type === 'M') registros.push(['moveTo', [[c.x, c.y]]])
        else if (c.type === 'L') registros.push(['lineTo', [[c.x, c.y]]])
        else if (c.type === 'C') registros.push(['curveTo', [[c.x1, c.y1], [c.x2, c.y2], [c.x, c.y]]])
        else if (c.type === 'Q') registros.push(['qCurveTo', [[c.x1, c.y1], [c.x, c.y]]])
        else if (c.type === 'Z') registros.push(['closePath', []])
      }
      return registros
    }
    const g = this._glyf(gid)
    if (!g) return registros                                  // glifo vacío: nada que grabar
    const pen = (verbo, args) => registros.push([verbo, args])
    if (g.componentes) {
      const dibujarComponente = (c, tExterna) => {
        if (!c.trans) throw new Error("'GlyphComponent' object has no attribute 'x'")
        const t = tExterna ? componer(tExterna, c.trans) : c.trans
        if (c.gid >= this.numGlyphs) return                    // `skipMissingComponents`
        const sub = this._glyf(c.gid)
        if (!sub) return
        if (sub.componentes) { for (const cc of sub.componentes) dibujarComponente(cc, t); return }
        const penT = esIdentidad(t) ? pen
          : (verbo, args) => pen(verbo, args.map((p) => (p === null ? null : transformar(t, p))))
        dibujarSimple(sub, 0, penT)                            // «Offset should only apply at top-level»
      }
      for (const c of g.componentes) dibujarComponente(c, null)
      return registros
    }
    const [, lsb] = this._metricas(gid)
    dibujarSimple(g, lsb - g.xMin, pen)
    return registros
  }

  _glifo(ch) {
    if (this._cache.has(ch)) return this._cache.get(ch)
    let gid = this.cmap.get(ch.codePointAt(0)) ?? null
    if (gid === null && pyIsSpace(ch)) {
      gid = this._gidPorNombre('space')
      if (gid === null) {
        const r = [[], Math.floor(this.upem / 3), true]      // el 3º: el ancho es ENTERO en Python
        this._cache.set(ch, r)
        return r
      }
    }
    if (gid === null) {
      const prestado = this._delRespaldo(ch)
      if (prestado !== null) return prestado
      throw new Error(`glifo faltante: ${JSON.stringify(ch)}`)
    }
    let registros
    try {
      registros = this._registros(gid)
    } catch (e) {
      const prestado = this._delRespaldo(ch)
      if (prestado !== null) return prestado
      throw new Error(`glifo corrupto: ${JSON.stringify(ch)} (${gid}): ${e.message}`)
    }
    const r = [registros, this._metricas(gid)[0], true]
    this._cache.set(ch, r)
    return r
  }

  _delRespaldo(ch) {
    if (this.respaldo === null) return null
    let registros, ancho
    try {
      [registros, ancho] = this.respaldo._glifo(ch)
    } catch (e) {
      return null
    }
    let k = this.upem / (this.respaldo.upem || this.upem)
    const cr = this.respaldo.capRatio
    if (cr) k *= (this.capRatio / cr)
    const pt = (p) => (p === null ? null : [p[0] * k, p[1] * k])
    const escalados = registros.map(([verbo, args]) => [verbo, (args || []).map(pt)])
    if (!this.sustituidos.includes(ch)) this.sustituidos.push(ch)
    const r = [escalados, ancho * k, false]                 // `ancho * k` es float en Python
    this._cache.set(ch, r)
    return r
  }

  prestados(texto) {
    const out = []
    for (const ch of String(texto ?? '')) {
      if (out.includes(ch) || pyIsSpace(ch) || this.cmap.has(ch.codePointAt(0))) continue
      if (this._delRespaldo(ch) !== null) out.push(ch)
    }
    return out
  }

  faltantes(texto) {
    const out = []
    for (const ch of String(texto ?? '')) {
      if (out.includes(ch)) continue
      try { this._glifo(ch) } catch (e) { out.push(ch) }
    }
    return out
  }

  anchoTexto(texto, size) {
    // `sum(...)` de Python: los anchos nativos son enteros y los prestados float → ver `pySum`
    const g = Array.from(texto).map((ch) => this._glifo(ch))
    return pySum(g.map((x) => x[1]), (i) => g[i][2]) * size / this.upem
  }

  _opsGlifo(registros, size, x, y, avance, ca, sa) {
    const e = size / this.upem
    const ops = []
    const M = (px, py) => {
      const ux = (px + avance) * e, uy = py * e
      return [x + ux * ca - uy * sa, y + ux * sa + uy * ca]
    }
    const f = (v) => pyFixed(v, 2)
    let actual = null, inicio = null
    for (const [verbo, args] of registros) {
      if (verbo === 'moveTo') {
        const p = M(...args[0]); ops.push(`${f(p[0])} ${f(p[1])} m`); actual = args[0]; inicio = args[0]
      } else if (verbo === 'lineTo') {
        const p = M(...args[0]); ops.push(`${f(p[0])} ${f(p[1])} l`); actual = args[0]
      } else if (verbo === 'curveTo') {
        const pts = args.map((pt) => M(...pt))
        ops.push(`${f(pts[0][0])} ${f(pts[0][1])} ${f(pts[1][0])} ${f(pts[1][1])} ${f(pts[2][0])} ${f(pts[2][1])} c`)
        actual = args[args.length - 1]
      } else if (verbo === 'qCurveTo') {
        const puntos = args.slice()
        if (puntos[puntos.length - 1] === null) puntos[puntos.length - 1] = inicio
        let p0 = actual
        const ctrls = puntos.slice(0, -1), fin = puntos[puntos.length - 1], segs = []
        ctrls.forEach((c0, i) => {
          const mid = i < ctrls.length - 1 ? [(c0[0] + ctrls[i + 1][0]) / 2, (c0[1] + ctrls[i + 1][1]) / 2] : fin
          segs.push([p0, c0, mid]); p0 = mid
        })
        for (const [q0, qc, q1] of segs) {
          if (!q0 || !q1) throw new TypeError("'NoneType' object is not subscriptable")   // como Python
          const c1 = [q0[0] + 2 / 3 * (qc[0] - q0[0]), q0[1] + 2 / 3 * (qc[1] - q0[1])]
          const c2 = [q1[0] + 2 / 3 * (qc[0] - q1[0]), q1[1] + 2 / 3 * (qc[1] - q1[1])]
          const P1 = M(...c1), P2 = M(...c2), P3 = M(...q1)
          ops.push(`${f(P1[0])} ${f(P1[1])} ${f(P2[0])} ${f(P2[1])} ${f(P3[0])} ${f(P3[1])} c`)
        }
        actual = fin
      } else if (verbo === 'closePath') {
        ops.push('h')
      }
    }
    return ops
  }

  opsTexto(texto, size, x, y, anguloDeg = 0.0) {
    const a = anguloDeg * (Math.PI / 180)                       // `math.radians`: x · (π/180)
    const ca = Math.cos(a), sa = Math.sin(a)
    const ops = []
    let avance = 0.0
    for (const ch of texto) {
      const [registros, ancho] = this._glifo(ch)
      ops.push(...this._opsGlifo(registros, size, x, y, avance, ca, sa))
      avance += ancho
    }
    return ops.join('\n')
  }

  opsTextoCurva(texto, size, puntos, x0 = null, x1 = null, align = 'centro') {
    let pts = puntos.filter(([px, py]) => px !== null && px !== undefined && py !== null && py !== undefined).map(([px, py]) => [Number(px), Number(py)])
    if (pts.length < 2) {
      const [x, y] = pts.length ? pts[0] : [0.0, 0.0]
      return this.opsTexto(texto, size, x, y)
    }
    pts.sort((p, q) => p[0] - q[0])                             // estable, como `list.sort`
    const xs = pts.map((p) => p[0])
    if (pts.length >= 3 && xs.every((v, i) => i === 0 || v > xs[i - 1])) {
      const [a, b, c] = polyfit2(xs, pts.map((p) => p[1]))
      const xa = x0 !== null && x0 !== undefined ? Math.min(xs[0], x0) : xs[0]
      const xb = x1 !== null && x1 !== undefined ? Math.max(xs[xs.length - 1], x1) : xs[xs.length - 1]
      const N = 60
      pts = []
      for (let k = 0; k <= N; k++) {
        const X = xa + (xb - xa) * k / N
        pts.push([X, a * X ** 2 + b * X + c])
      }
    }
    const lens = [0.0]
    for (let i = 1; i < pts.length; i++) lens.push(lens[lens.length - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    const CL = lens[lens.length - 1]

    const puntoEn = (s) => {
      s = Math.max(0.0, Math.min(CL, s))
      let i = 1
      while (i < lens.length && lens[i] < s) i++
      i = Math.min(i, pts.length - 1)
      const L0 = lens[i - 1], L1 = lens[i]
      const t = L1 === L0 ? 0.0 : (s - L0) / (L1 - L0)
      const x = pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0])
      const y = pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])
      const ang = Math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])
      return [x, y, ang]
    }
    const arclenEnX = (qx) => {
      for (let i = 1; i < pts.length; i++) {
        const a = pts[i - 1][0], b = pts[i][0]
        if ((a <= qx && qx <= b) || (b <= qx && qx <= a)) {
          const t = b === a ? 0.0 : (qx - a) / (b - a)
          return lens[i - 1] + t * (lens[i] - lens[i - 1])
        }
      }
      return qx <= pts[0][0] ? 0.0 : CL
    }

    const e = size / this.upem
    const letras = Array.from(texto)
    const anchos = letras.map((ch) => this._glifo(ch)[1] * e)
    const TW = pySum(anchos, () => false)                       // `sum(anchos)`: todos float
    if (x0 === null || x0 === undefined || x1 === null || x1 === undefined) { x0 = pts[0][0]; x1 = pts[pts.length - 1][0] }
    let s
    if (align === 'izquierda') s = arclenEnX(x0)
    else if (align === 'derecha') s = arclenEnX(x1) - TW
    else s = arclenEnX((x0 + x1) / 2.0) - TW / 2.0

    const build = (s0) => {
      const ops = []
      let ss = s0, xmin = null, xmax = null
      letras.forEach((ch, i) => {
        const w = anchos[i]
        const [registros] = this._glifo(ch)
        const [x, y, ang] = puntoEn(ss + w / 2.0)
        const ca = Math.cos(ang), sa = Math.sin(ang)
        const gx = x - (w / 2.0) * ca, gy = y - (w / 2.0) * sa
        const og = this._opsGlifo(registros, size, gx, gy, 0.0, ca, sa)
        for (const op of og) {
          const c0 = op[0]
          if ((c0 >= '0' && c0 <= '9') || c0 === '-') {
            const px = parseFloat(op.split(' ', 1)[0])
            xmin = xmin === null ? px : Math.min(xmin, px)
            xmax = xmax === null ? px : Math.max(xmax, px)
          }
        }
        ops.push(...og); ss += w
      })
      return [ops.join('\n'), xmin, xmax]
    }

    let [o, xmn, xmx] = build(s)
    if (xmn !== null) {
      if (align === 'izquierda') s += x0 - xmn
      else if (align === 'derecha') s += x1 - xmx
      else s += (x0 + x1) / 2.0 - (xmn + xmx) / 2.0
      ;[o] = build(s)
    }
    return o
  }

  opsTextoFiel(texto, size, glifos) {
    const g = glifos.map(([a, b, c, d]) => [Number(a), Number(b), Number(c), Number(d)])
    if (!g.length) return ''
    const lineas = []
    let cur = [g[0]]
    for (let i = 1; i < g.length; i++) {
      const dx = g[i][0] - g[i - 1][0], dy = g[i][1] - g[i - 1][1]
      if (Math.abs(dy) > 0.6 * size || dx < -0.4 * size) { lineas.push(cur); cur = [g[i]] }
      else cur.push(g[i])
    }
    lineas.push(cur)
    const exts = lineas.map((ln) => [Math.min(...ln.map((e) => e[2])), Math.max(...ln.map((e) => e[3]))])
    let align = 'centro'
    if (lineas.length >= 2) {
      const lefts = exts.map((e) => e[0]), rights = exts.map((e) => e[1]), cents = exts.map(([a, b]) => (a + b) / 2)
      const sl = Math.max(...lefts) - Math.min(...lefts), sr = Math.max(...rights) - Math.min(...rights), sc = Math.max(...cents) - Math.min(...cents)
      const m = Math.min(sl, sc, sr)
      align = m === sl ? 'izquierda' : (m === sr ? 'derecha' : 'centro')
    }
    const partes = texto.split('\n')
    const ops = []
    lineas.forEach((ln, i) => {
      const txt = lineas.length === 1 ? texto : (i < partes.length ? partes[i] : '')
      if (!pyStrip(txt)) return
      const [X0, X1] = exts[i]
      const base = ln.length >= 2 ? ln.map((e) => [e[0], e[1]]) : [[X0, ln[0][1]], [X1, ln[0][1]]]
      ops.push(this.opsTextoCurva(txt, size, base, X0, X1, align))
    })
    return ops.filter((o) => o).join('\n')
  }
}

/** `numpy.polyfit(x, y, 2)` → [a, b, c]. numpy escala las columnas de la Vandermonde y resuelve por
 *  SVD (LAPACK): eso no se reproduce bit a bit. Acá: mismas columnas escaladas, mínimos cuadrados
 *  por QR de Householder (estable); la diferencia con numpy es ~1e-15 relativa, invisible en los
 *  operadores salvo que un valor caiga JUSTO en un borde de redondeo del `.2f` (el contrato lo
 *  tolera y lo cuenta). */
function polyfit2(xs, ys) {
  const n = xs.length
  const A = xs.map((x) => [x * x, x, 1])
  const scale = [0, 1, 2].map((j) => Math.sqrt(A.reduce((s, r) => s + r[j] * r[j], 0)))
  for (const r of A) for (let j = 0; j < 3; j++) r[j] /= scale[j]
  const b = ys.slice()
  for (let j = 0; j < 3; j++) {                                  // Householder
    let norma = 0
    for (let i = j; i < n; i++) norma += A[i][j] * A[i][j]
    norma = Math.sqrt(norma)
    if (norma === 0) continue
    const alfa = A[j][j] > 0 ? -norma : norma
    const v = new Array(n).fill(0)
    for (let i = j; i < n; i++) v[i] = A[i][j]
    v[j] -= alfa
    let vv = 0
    for (let i = j; i < n; i++) vv += v[i] * v[i]
    if (vv === 0) continue
    for (let k = j; k < 3; k++) {
      let d = 0
      for (let i = j; i < n; i++) d += v[i] * A[i][k]
      const f = 2 * d / vv
      for (let i = j; i < n; i++) A[i][k] -= f * v[i]
    }
    let d = 0
    for (let i = j; i < n; i++) d += v[i] * b[i]
    const f = 2 * d / vv
    for (let i = j; i < n; i++) b[i] -= f * v[i]
  }
  const c = [0, 0, 0]
  for (let j = 2; j >= 0; j--) {
    let s = b[j]
    for (let k = j + 1; k < 3; k++) s -= A[j][k] * c[k]
    c[j] = s / A[j][j]
  }
  return c.map((v, j) => v / scale[j])
}
