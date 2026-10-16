// LOS DIBUJOS TÉCNICOS DEL MOLDE A MEDIDA EN LA FICHA, EN EL NAVEGADOR (MAPA 659).
//
// Gemelo EXACTO de `ficha_a_medida.dibujos_a_medida` (Python): el plano de la pieza con sus cotas, el
// borde en CORTE paso a paso (dobladillo / overlock / corte al ras), la esquina o la punta de cerca
// CORTADA y DOBLADA, y los pasos de «CÓMO SE TERMINA». Regla del usuario: «nada del uso depende del
// servidor; el servidor sólo guarda» → la ficha que arma el navegador tiene que poder calcular los
// dibujos sola, y tienen que salir IGUALES a los del servidor (mismas claves, mismos textos, mismos
// números). El contrato `verificar_ficha_a_medida_navegador.py` compara las dos salidas en miles de
// combinaciones (forma × punta × terminación × medidas × márgenes × tiras × borde).
//
// Salida: `[{alto, ops}]` (plano, terminación, pasos) con `ops` en puntos relativos al bloque:
//   · `{k: 'l', p: [[x, y], …], c: rgb|null, w, d: rayas|null, f: rgb|null, h: cerrar}` (polilínea);
//   · `{k: 't', x, y, s, z, c: rgb, b: negrita}` (texto, y = base).
//
// 🔴 POR QUÉ CADA DETALLE ESTÁ COMO ESTÁ (si se «simplifica», deja de dar lo mismo que Python):
//   · `round(x, 2)` de Python redondea el valor binario EXACTO y empata al par: `pyRound` (py.js), no
//     `toFixed`; `round(x)` sin decimales también empata al par (`redondearPar`), no `Math.round`;
//   · `f"{v:g}"` (las medidas en cm del texto) = 6 cifras significativas sin ceros de más (`formatoG`);
//   · `min/max(…, key=)` de Python devuelve el PRIMERO de los empatados (`primeroPor`);
//   · el ancho del texto es el de `pymupdf.get_text_length` (Base-14 de MuPDF), con su rareza: avanza
//     la cantidad de BYTES UTF-8 de cada carácter sobre un índice de CARACTERES, así que después de una
//     «ó» se saltea la letra siguiente al medir. Se copia tal cual (igual que `largoTexto` de ficha.js);
//     acá no hay mupdf a mano (la función es pura), así que los avances van en una tabla sacada de
//     `fz_advance_glyph` de MuPDF 1.26 (milésimas exactas: cada una es el float32 de k/1000);
//   · las operaciones aritméticas van en el MISMO orden que en Python (el double no es asociativo).
import { pyRound, pyStrip } from '../py.js'
import { geoTriangulo, incentro, trianguloCorrido, solapaTri, margenUniforme, normForma, normOrientacion } from '../molde/formas.js'
import { segmentosTiras } from '../molde/tiras.js'

const A4_W = 595.28
const MARGEN = 36
const CW = A4_W - 2 * MARGEN                  // el ancho útil de la ficha

const NEGRO = [0.1, 0.1, 0.1]
const GRIS = [0.45, 0.45, 0.45]
const GRIS_C = [0.75, 0.75, 0.75]
const AZUL = [0.0, 0.42, 0.82]                // la GUÍA del diseño = por dónde se dobla
const NARANJA = [0.93, 0.48, 0.08]            // la COSTURA (la misma naranja de la plantilla)
const TELA = [0.93, 0.95, 0.97]               // la pieza
const SOLAPA = [0.84, 0.87, 0.92]             // el margen doblado
const TELA_C = [0.55, 0.58, 0.62]             // la tela en corte
const TINTA = [0.85, 0.2, 0.55]               // la cara impresa

const RAYAS_GUIA = '[4 2] 0'
const RAYAS_COSTURA = '[1.5 1.5] 0'

// ─── lo que Python hace distinto con los números y los valores ─────────────────────────────────
/** `round(x)` de Python (sin decimales): al entero más cercano y, en el empate exacto, al PAR. */
function redondearPar(x) {
  const f = Math.floor(x)
  const d = x - f                             // exacto: restar el piso de un double no pierde bits
  const r = d < 0.5 ? f : d > 0.5 ? f + 1 : (f % 2 === 0 ? f : f + 1)
  return r === 0 ? 0 : r                      // un int de Python no tiene −0
}

/** `f"{x:g}"` de Python: 6 cifras significativas, sin ceros de más; exponente fuera de [1e-4, 1e6). */
function formatoG(x) {
  if (x === 0) return Object.is(x, -0) ? '-0' : '0'
  if (!Number.isFinite(x)) return x > 0 ? 'inf' : x < 0 ? '-inf' : 'nan'
  const [man, ex] = x.toExponential(5).split('e')
  const e = Number(ex)
  if (e < -4 || e >= 6) {
    const m = man.replace(/\.?0+$/, '')
    return `${m}e${e < 0 ? '-' : '+'}${String(Math.abs(e)).padStart(2, '0')}`
  }
  return x.toFixed(5 - e).replace(/\.?0+$/, '').replace(/^-0$/, '-0')
}

/** `_cm`: la medida en cm con un decimal y coma («12,5»; «12» si es entera). */
const cm = (v) => formatoG(redondearPar(Number(v) * 10) / 10).replace('.', ',')

/** La verdad de Python (`if x:`) para lo que llega acá: null, números, textos, listas y dicts. */
const verdad = (v) => !(v === null || v === undefined || v === false || v === 0 || v === '' || Number.isNaN(v) ||
  (Array.isArray(v) && v.length === 0) || (typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0))

/** `d.get(k, def)` */
const pyGet = (d, k, def) => (d && Object.prototype.hasOwnProperty.call(d, k) ? d[k] : def)

/** `float(d.get(k) or 0)` */
const num0 = (d, k) => { const v = d ? d[k] : undefined; return verdad(v) ? Number(v) : 0 }

/** `min(lista, key=f)` / `max(lista, key=f)` de Python: el PRIMERO de los empatados. */
function primeroPor(lista, clave, mayor) {
  let mejor = lista[0], mk = clave(lista[0])
  for (let i = 1; i < lista.length; i++) {
    const k = clave(lista[i])
    if (mayor ? k > mk : k < mk) { mejor = lista[i]; mk = k }
  }
  return mejor
}

/** `a == b` de Python entre listas de puntos (tuplas de números). */
function mismosPuntos(a, b) {
  if (!a || !b || a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (a[i].length !== b[i].length) return false
    for (let j = 0; j < a[i].length; j++) if (a[i][j] !== b[i][j]) return false
  }
  return true
}

// ─── el ancho del texto: `pymupdf.get_text_length` con la Base-14 de MuPDF ──────────────────────
// Avance de cada código cp1252 (0-255) en milésimas del cuerpo, tal como lo da `fz_advance_glyph` de
// MuPDF 1.26 para `fz_encode_character(font, código)` (los 128-159 caen en el glifo vacío de 278).
const AV_HELV = [278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
  278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556,
  1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556,
  333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 278,
  278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
  278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333, 400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611,
  667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278, 722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
  556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278, 556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500]
const AV_HEBO = [278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
  278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611,
  975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556,
  333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 278,
  278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278, 278,
  278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333, 400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611,
  722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278, 722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611,
  556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278, 611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556]
// el avance es un float32 (MuPDF guarda los anchos de la fuente en float): k/1000 llevado a float
const F_HELV = AV_HELV.map((k) => Math.fround(k / 1000))
const F_HEBO = AV_HEBO.map((k) => Math.fround(k / 1000))

// `fz_windows_1252_from_unicode`: ASCII y 160-255 tal cual, los 27 especiales de cp1252, -1 lo demás
const CP1252 = { 338: 140, 339: 156, 352: 138, 353: 154, 376: 159, 381: 142, 382: 158, 402: 131, 710: 136,
  732: 152, 8211: 150, 8212: 151, 8216: 145, 8217: 146, 8218: 130, 8220: 147, 8221: 148, 8222: 132,
  8224: 134, 8225: 135, 8226: 149, 8230: 133, 8240: 137, 8249: 139, 8250: 155, 8364: 128 }
const cp1252 = (u) => (u < 128 ? u : (u >= 160 && u < 256) ? u : (CP1252[u] ?? -1))

/** `_ancho_texto` = `pymupdf.get_text_length(s, "hebo" if b else "helv", z)` (`util_measure_string`). */
export function anchoTexto(s, z, b = false) {
  const tabla = b ? F_HEBO : F_HELV
  const cs = Array.from(s)
  let w = 0, pos = 0
  while (pos < cs.length) {
    const u = cs[pos].codePointAt(0)
    // `t, c = fz_chartorune(text[pos:]); pos += t`: t son BYTES UTF-8 sobre un índice de caracteres
    pos += u < 0x80 ? 1 : u < 0x800 ? 2 : u < 0x10000 ? 3 : 4
    let c = cp1252(u)
    if (c < 0) c = 0xB7
    w += tabla[c]
  }
  return w * z
}

// ─── el lienzo: junta los trazos de UN bloque (puntos, y hacia ABAJO) ───────────────────────────
class Lienzo {
  constructor() { this.ops = [] }

  linea(pts, { color = NEGRO, ancho = 1.0, rayas = null, relleno = null, cerrar = false } = {}) {
    const p = pts.map(([x, y]) => [pyRound(Number(x), 2), pyRound(Number(y), 2)])
    if (p.length < 2) return
    this.ops.push({ k: 'l', p, c: color ? [...color] : null, w: pyRound(Number(ancho), 2),
      d: rayas, f: relleno ? [...relleno] : null, h: !!cerrar })
  }

  texto(x, y, s, { z = 8.0, color = NEGRO, b = false, alinear = 'izq' } = {}) {
    s = String(s)
    if (alinear !== 'izq') {
      const w = anchoTexto(s, z, b)
      x = x - (alinear === 'der' ? w : w / 2)
    }
    this.ops.push({ k: 't', x: pyRound(Number(x), 2), y: pyRound(Number(y), 2), s, z, c: [...color], b: !!b })
  }

  /** Punta de flecha llena con la punta en (x, y), apuntando hacia (dx, dy). */
  flecha(x, y, dx, dy, color = GRIS, largo = 4.0, medio = 1.5) {
    const n = Math.hypot(dx, dy) || 1
    const ux = dx / n, uy = dy / n
    const bx = x - ux * largo, by = y - uy * largo
    this.linea([[x, y], [bx - uy * medio, by + ux * medio], [bx + uy * medio, by - ux * medio]],
      { color: null, relleno: color, cerrar: true })
  }

  punto(x, y, { r = 1.7, color = NEGRO, lleno = true } = {}) {
    const pts = []
    for (let k = 0; k < 12; k++) pts.push([x + r * Math.cos(2 * Math.PI * k / 12), y + r * Math.sin(2 * Math.PI * k / 12)])
    if (lleno) this.linea(pts, { color: null, relleno: color, cerrar: true })
    else this.linea(pts, { color, ancho: 0.6, cerrar: true })
  }

  cotaH(x0, x1, y, txt, arriba = true, color = GRIS) {
    this.linea([[x0, y], [x1, y]], { color, ancho: 0.5 })
    if (x1 - x0 > 10) {
      this.flecha(x0, y, -1, 0, color)
      this.flecha(x1, y, 1, 0, color)
    }
    this.texto((x0 + x1) / 2, arriba ? y - 3 : y + 9, txt, { z: 8, color: NEGRO, alinear: 'centro' })
  }

  cotaV(x, y0, y1, txt, izquierda = true, color = GRIS) {
    this.linea([[x, y0], [x, y1]], { color, ancho: 0.5 })
    if (y1 - y0 > 10) {
      this.flecha(x, y0, 0, -1, color)
      this.flecha(x, y1, 0, 1, color)
    }
    const ym = (y0 + y1) / 2 + 3
    if (izquierda) this.texto(x - 3, ym, txt, { z: 8, color: NEGRO, alinear: 'der' })
    else this.texto(x + 3, ym, txt, { z: 8, color: NEGRO })
  }

  caja(x0, y0, x1, y1, color = GRIS_C) {
    this.linea([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], { color, ancho: 0.6, cerrar: true })
  }
}

// ─── recortes (para los detalles de cerca) ──────────────────────────────────────────────────────
/** Liang-Barsky: el tramo p-q dentro de la ventana w = [x0, y0, x1, y1], o null. Gemelo: `_clip_seg`. */
function clipSeg(p, q, w) {
  const [x0, y0, x1, y1] = w
  const dx = q[0] - p[0], dy = q[1] - p[1]
  let t0 = 0.0, t1 = 1.0
  for (const [pp, qq] of [[-dx, p[0] - x0], [dx, x1 - p[0]], [-dy, p[1] - y0], [dy, y1 - p[1]]]) {
    if (pp === 0) {
      if (qq < 0) return null
      continue
    }
    const r = qq / pp
    if (pp < 0) {
      if (r > t1) return null
      t0 = Math.max(t0, r)
    } else {
      if (r < t0) return null
      t1 = Math.min(t1, r)
    }
  }
  return [[p[0] + t0 * dx, p[1] + t0 * dy], [p[0] + t1 * dx, p[1] + t1 * dy]]
}

/** Una polilínea recortada a la ventana: los tramos que quedan adentro. Gemelo: `_clip_polilinea`. */
function clipPolilinea(pts, w, cerrar = false) {
  const seq = [...pts, ...(cerrar && pts.length ? [pts[0]] : [])]
  const out = []
  let cur = null
  for (let i = 0; i + 1 < seq.length; i++) {
    const c = clipSeg(seq[i], seq[i + 1], w)
    if (c === null) { cur = null; continue }
    if (cur !== null && Math.abs(cur[cur.length - 1][0] - c[0][0]) < 1e-9 && Math.abs(cur[cur.length - 1][1] - c[0][1]) < 1e-9) {
      cur.push(c[1])
    } else {
      cur = [c[0], c[1]]
      out.push(cur)
    }
  }
  return out
}

/** Sutherland-Hodgman: el polígono recortado a la ventana (para los rellenos). Gemelo: `_clip_poligono`. */
function clipPoligono(pts, w) {
  const [x0, y0, x1, y1] = w
  const bordes = [
    [(p) => p[0] >= x0, (a, b) => [x0, a[1] + (b[1] - a[1]) * (x0 - a[0]) / (b[0] - a[0])]],
    [(p) => p[0] <= x1, (a, b) => [x1, a[1] + (b[1] - a[1]) * (x1 - a[0]) / (b[0] - a[0])]],
    [(p) => p[1] >= y0, (a, b) => [a[0] + (b[0] - a[0]) * (y0 - a[1]) / (b[1] - a[1]), y0]],
    [(p) => p[1] <= y1, (a, b) => [a[0] + (b[0] - a[0]) * (y1 - a[1]) / (b[1] - a[1]), y1]],
  ]
  let out = [...pts]
  for (const [dentro, corte] of bordes) {
    if (!out.length) break
    const ent = out
    out = []
    for (let i = 0; i < ent.length; i++) {
      const b = ent[i], a = ent[i === 0 ? ent.length - 1 : i - 1]      // `ent[i - 1]` de Python
      if (dentro(b)) {
        if (!dentro(a)) out.push(corte(a, b))
        out.push(b)
      } else if (dentro(a)) {
        out.push(corte(a, b))
      }
    }
  }
  return out
}

function circulo(cx, cy, r, n = 144) {
  const out = []
  for (let k = 0; k < n; k++) out.push([cx + r * Math.cos(2 * Math.PI * k / n), cy + r * Math.sin(2 * Math.PI * k / n)])
  return out
}

/** El punto `p` reflejado sobre la recta que pasa por `a` con normal unitaria `n` (el doblez). */
function reflejar(p, a, n) {
  const d = (p[0] - a[0]) * n[0] + (p[1] - a[1]) * n[1]
  return [p[0] - 2 * d * n[0], p[1] - 2 * d * n[1]]
}

// ─── la geometría de la pieza (cm, y hacia ARRIBA, origen en la esquina del total) ────────────────
/** {contorno, guia, costura, solapas, rec, caja_diseno, …}: los mismos contornos del alta. Gemelo: `_geometria`. */
function geometria(forma, orient, term, anCm, alCm, mg, W, H) {
  const mi = num0(mg, 'izq'), md = num0(mg, 'der'), ma = num0(mg, 'arriba'), mb = num0(mg, 'abajo')
  const mu = margenUniforme(mg)
  const g = { forma, rec: false, costura: null, solapas: [] }
  if (forma === 'circulo') {
    const R = W / 2, rg = anCm / 2
    Object.assign(g, { contorno: circulo(R, R, R), guia: circulo(R, R, rg), centro: [R, R], R, rg })
    if (term === 'dobladillo' && mu > 0 && rg - mu > 0) g.costura = circulo(R, R, rg - mu)
    g.caja_diseno = [R - rg, R - rg, R + rg, R + rg]
    return g
  }
  if (forma === 'triangulo') {
    const rec = term !== 'overlock'
    const t = term !== 'sin' ? mu : 0.0
    const geo = geoTriangulo(anCm, alCm, t, orient, rec)
    const G = geo.guia.map((p) => [p[0], p[1]])
    Object.assign(g, { contorno: geo.pol.map((p) => [p[0], p[1]]), guia: G, rec: rec && t > 0, G, t })
    if (term === 'dobladillo' && t > 0 && incentro(G).r - t > 0) g.costura = trianguloCorrido(G, -t)
    if (term === 'dobladillo' && t > 0) {
      for (let i = 0; i < 3; i++) {          // cada solapa y su reflejo sobre el lado (= doblada)
        const a = G[i], b = G[(i + 1) % 3]
        const { ux, uy, nx, ny, ca, cb, tt } = solapaTri(G, i, t)
        const sol = [a, [a[0] + tt * ca * ux + tt * nx, a[1] + tt * ca * uy + tt * ny],
          [b[0] - tt * cb * ux + tt * nx, b[1] - tt * cb * uy + tt * ny], b]
        g.solapas.push(sol.map((p) => reflejar(p, a, [nx, ny])))
      }
    }
    const xs = G.map((p) => p[0]), ys = G.map((p) => p[1])
    g.caja_diseno = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
    return g
  }
  // RECTÁNGULO: con dobladillo, las esquinas recortadas del tamaño del margen (MAPA 653)
  const rec = term === 'dobladillo' && (mi > 0 || md > 0 || ma > 0 || mb > 0)
  if (rec) {
    g.contorno = [[mi, 0], [W - md, 0], [W - md, mb], [W, mb], [W, H - ma], [W - md, H - ma], [W - md, H],
      [mi, H], [mi, H - ma], [0, H - ma], [0, mb], [mi, mb]]
  } else {
    g.contorno = [[0, 0], [W, 0], [W, H], [0, H]]
  }
  g.guia = [[mi, mb], [W - md, mb], [W - md, H - ma], [mi, H - ma]]
  g.rec = rec
  g.m = [mi, md, ma, mb]
  if (term === 'dobladillo' && W - 2 * (mi + md) > 0 && H - 2 * (ma + mb) > 0 && (mi || md || ma || mb)) {
    g.costura = [[2 * mi, 2 * mb], [W - 2 * md, 2 * mb], [W - 2 * md, H - 2 * ma], [2 * mi, H - 2 * ma]]
  }
  if (rec) {                                  // las solapas dobladas por la guía (abajo, derecha, arriba, izquierda)
    g.solapas = [
      mb > 0 ? [[mi, mb], [W - md, mb], [W - md, 2 * mb], [mi, 2 * mb]] : null,
      md > 0 ? [[W - md, mb], [W - md, H - ma], [W - 2 * md, H - ma], [W - 2 * md, mb]] : null,
      ma > 0 ? [[mi, H - ma], [W - md, H - ma], [W - md, H - 2 * ma], [mi, H - 2 * ma]] : null,
      mi > 0 ? [[mi, mb], [mi, H - ma], [2 * mi, H - ma], [2 * mi, mb]] : null,
    ].filter((s) => s)
  }
  g.caja_diseno = [mi, mb, W - md, H - ma]
  return g
}

// ─── 1 · EL PLANO DE LA PIEZA ────────────────────────────────────────────────────────────────────
function bloquePlano(g, W, H, anCm, alCm, tirasSegs, tiras, bordeTxt) {
  const L = new Lienzo()
  L.texto(0, 10, 'PLANO DE LA PIEZA', { z: 9.5, b: true })
  const AX0 = 58.0, AX1 = CW - 58.0, TOP = 40.0, HMAX = 195.0
  const s = Math.min((AX1 - AX0) / W, HMAX / H)
  const pw = W * s, ph = H * s
  const px0 = AX0 + ((AX1 - AX0) - pw) / 2
  const py0 = TOP
  const P = (x, y) => [px0 + x * s, py0 + (H - y) * s]
  L.texto(CW, 10, `escala aprox. 1:${Math.max(1, redondearPar(28.3465 / s))} · medidas en cm`, { z: 7.5, color: GRIS, alinear: 'der' })
  const circ = g.forma === 'circulo'
  // la pieza (relleno) y su contorno de corte
  L.linea(g.contorno.map((p) => P(...p)), { color: NEGRO, ancho: 1.0, relleno: TELA, cerrar: true })
  if (g.guia !== null && !mismosPuntos(g.contorno, g.guia)) {
    L.linea(g.guia.map((p) => P(...p)), { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA, cerrar: true })
  }
  if (verdad(g.costura)) {
    L.linea(g.costura.map((p) => P(...p)), { color: NARANJA, ancho: 0.8, rayas: RAYAS_COSTURA, cerrar: true })
  }
  // las tiras: la marca real (del borde a la guía) + un punto afuera para encontrarla a esta escala
  const marcar = verdad(tiras) && verdad(pyGet(tiras, 'marcar', true))
  for (const [x1, y1, x2, y2] of tirasSegs) {
    const a = P(x1, y1), b = P(x2, y2)
    const dx = a[0] - b[0], dy = a[1] - b[1]
    const n = Math.hypot(dx, dy) || 1
    L.linea([a, b], { color: marcar ? NEGRO : GRIS, ancho: 1.2, rayas: marcar ? null : '[1 1] 0' })
    L.punto(a[0] + dx / n * 4.5, a[1] + dy / n * 4.5, { color: marcar ? NEGRO : GRIS, lleno: marcar })
  }
  // cotas: el DISEÑO arriba (y a la derecha), el TOTAL abajo (y a la izquierda); las líneas de referencia
  // salen de los puntos EXTREMOS de cada contorno (en el triángulo la esquina de la caja no es de la pieza)
  const [gx0, gy0, gx1, gy1] = g.caja_diseno
  const cont = g.contorno, guia = g.guia
  const ext = (pts, k, mayor) => primeroPor(pts, (p) => p[k], mayor)
  const ya = py0 - 16
  for (const p of [ext(guia, 0, false), ext(guia, 0, true)]) {
    L.linea([P(...p), [P(...p)[0], ya - 3]], { color: GRIS_C, ancho: 0.4 })
  }
  L.cotaH(P(gx0, 0)[0], P(gx1, 0)[0], ya, (circ ? 'Ø ' : '') + `${cm(anCm)} diseño (guía)`, true)
  const yb = py0 + ph + 14
  for (const p of [ext(cont, 0, false), ext(cont, 0, true)]) {
    L.linea([P(...p), [P(...p)[0], yb + 3]], { color: GRIS_C, ancho: 0.4 })
  }
  L.cotaH(px0, px0 + pw, yb, (circ ? 'Ø ' : '') + `${cm(W)} total (con el margen)`, false)
  if (!circ) {
    const xl = px0 - 14
    for (const p of [ext(cont, 1, true), ext(cont, 1, false)]) {
      L.linea([P(...p), [xl - 3, P(...p)[1]]], { color: GRIS_C, ancho: 0.4 })
    }
    L.cotaV(xl, py0, py0 + ph, `${cm(H)} total`, true)
    const xr = px0 + pw + 14
    for (const p of [ext(guia, 1, true), ext(guia, 1, false)]) {
      L.linea([P(...p), [xr + 3, P(...p)[1]]], { color: GRIS_C, ancho: 0.4 })
    }
    L.cotaV(xr, P(0, gy1)[1], P(0, gy0)[1], `${cm(alCm)} diseño`, false)
  }
  // la leyenda: cada línea como se ve en el plano
  const yl = yb + 30
  const items = [['corte', 'Corte (contorno)']]
  if (!mismosPuntos(g.contorno, g.guia)) items.push(['guia', verdad(g.doblez) ? 'Guía del diseño = doblez' : 'Guía del diseño'])
  if (verdad(g.costura)) items.push(['costura', 'Costura'])
  if (tirasSegs.length) items.push(['tira', marcar ? 'Tira (marca de borde a guía)' : 'Tira (no va marcada)'])
  let x = 0.0
  for (const [tipo, txt] of items) {
    if (tipo === 'corte') {
      L.linea([[x, yl - 3], [x + 18, yl - 3]], { color: NEGRO, ancho: 1.0 })
    } else if (tipo === 'guia') {
      L.linea([[x, yl - 3], [x + 18, yl - 3]], { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA })
    } else if (tipo === 'costura') {
      L.linea([[x, yl - 3], [x + 18, yl - 3]], { color: NARANJA, ancho: 0.8, rayas: RAYAS_COSTURA })
    } else {
      L.linea([[x + 6, yl - 3], [x + 14, yl - 3]], { color: marcar ? NEGRO : GRIS, ancho: 1.2 })
      L.punto(x + 2, yl - 3, { color: marcar ? NEGRO : GRIS, lleno: marcar })
    }
    L.texto(x + 22, yl, txt, { z: 7.5, color: GRIS })
    x += 30 + anchoTexto(txt, 7.5) + 10
  }
  let alto = yl + 6
  if (bordeTxt) {
    L.texto(0, yl + 12, bordeTxt, { z: 7.5, color: GRIS })
    alto = yl + 16
  }
  return { alto: pyRound(alto, 2), ops: L.ops }
}

// ─── 2 · LA TERMINACIÓN: el borde en corte y la esquina/punta de cerca ─────────────────────────────
function telaCorte(L, x0, x1, y, impresa = true) {
  L.linea([[x0, y], [x1, y]], { color: TELA_C, ancho: 2.4 })
  if (impresa) L.linea([[x0, y - 1.9], [x1, y - 1.9]], { color: TINTA, ancho: 1.0 })
}

/** El arco del doblez (el margen dando la vuelta hacia el revés) en el borde `xa + m`, a la altura `y`. */
function arcoDoblez(xa, m, y) {
  const out = []
  for (let k = 0; k < 11; k++) out.push([xa + m - 3.2 * Math.sin(Math.PI * k / 10), y + 3.2 - 3.2 * Math.cos(Math.PI * k / 10)])
  return out
}

/** El borde en CORTE (de costado), paso a paso. `X` = dónde empieza el panel; M en cm (el texto). */
function panelCorte(L, X, term, M, costuraCm) {
  const xa = X + 64, xe = X + 250, m = 34.0
  if (term === 'dobladillo') {
    const y1 = 44.0, y2 = 88.0, y3 = 132.0
    // 1 · cortado: el margen plano, con dónde va el doblez y dónde la costura
    L.texto(X, y1 + 3, '1 · Cortado', { z: 8, b: true })
    telaCorte(L, xa, xe, y1)
    L.linea([[xa + m, y1 - 10], [xa + m, y1 + 7]], { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA })
    L.linea([[xa + 2 * m, y1 - 10], [xa + 2 * m, y1 + 7]], { color: NARANJA, ancho: 0.8, rayas: RAYAS_COSTURA })
    L.cotaH(xa, xa + m, y1 - 13, `${cm(M)} cm`)
    L.texto(xa, y1 + 15, 'borde', { z: 7, color: GRIS, alinear: 'centro' })
    L.texto(xa + m, y1 + 15, 'doblez', { z: 7, color: AZUL, alinear: 'centro' })
    L.texto(xa + 2 * m, y1 + 15, 'costura', { z: 7, color: NARANJA, alinear: 'centro' })
    L.texto(xe, y1 + 15, 'cara impresa arriba', { z: 7, color: TINTA, alinear: 'der' })
    // 2 · doblado: el margen va hacia el revés, por la guía
    L.texto(X, y2 + 3, '2 · Doblado', { z: 8, b: true })
    telaCorte(L, xa + m, xe, y2)
    L.linea(arcoDoblez(xa, m, y2), { color: TELA_C, ancho: 2.4 })
    L.linea([[xa + m, y2 + 6.4], [xa + 2 * m, y2 + 6.4]], { color: TELA_C, ancho: 2.4 })
    L.linea([[xa + m, y2 - 10], [xa + m, y2 + 12]], { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA })
    L.texto(xa - 2, y2 + 19, `el margen de ${cm(M)} cm va hacia el revés, doblado justo por la guía`, { z: 7, color: GRIS })
    // 3 · cosido: la costura a M del doblez agarra el borde del margen
    L.texto(X, y3 + 3, '3 · Cosido', { z: 8, b: true })
    telaCorte(L, xa + m, xe, y3)
    L.linea(arcoDoblez(xa, m, y3), { color: TELA_C, ancho: 2.4 })
    L.linea([[xa + m, y3 + 6.4], [xa + 2 * m, y3 + 6.4]], { color: TELA_C, ancho: 2.4 })
    L.linea([[xa + 2 * m - 1.5, y3 - 6], [xa + 2 * m - 1.5, y3 + 12]], { color: NARANJA, ancho: 1.1, rayas: '[1.6 1.2] 0' })
    L.cotaH(xa + m, xa + 2 * m - 1.5, y3 - 9, `${cm(costuraCm)} cm`)
    L.texto(xa - 2, y3 + 21, `costura a ${cm(costuraCm)} cm del doblez: toma el borde del margen`, { z: 7, color: GRIS })
    return 160.0
  }
  if (term === 'overlock') {
    const y1 = 44.0, y2 = 92.0
    L.texto(X, y1 + 3, '1 · Cortado', { z: 8, b: true })
    telaCorte(L, xa, xe, y1)
    L.linea([[xa + m, y1 - 10], [xa + m, y1 + 7]], { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA })
    L.cotaH(xa, xa + m, y1 - 13, `${cm(M)} cm`)
    L.texto(xa, y1 + 15, 'borde', { z: 7, color: GRIS, alinear: 'centro' })
    L.texto(xa + m, y1 + 15, 'guía del diseño', { z: 7, color: AZUL, alinear: 'centro' })
    L.texto(X, y2 + 3, '2 · Overlock', { z: 8, b: true })
    telaCorte(L, xa, xe, y2)
    // el hilo ENVUELVE el borde: lazos que pasan por arriba, dan la vuelta al canto y vuelven por abajo
    for (let k = 0; k < 4; k++) {
      const xx = xa + 3 + k * 4.2
      L.linea([[xx, y2 - 4.2], [xa - 1.6, y2 - 4.2], [xa - 3.4, y2 - 2.4], [xa - 3.4, y2 + 1.4],
        [xa - 1.6, y2 + 3.2], [xx, y2 + 3.2]], { color: NARANJA, ancho: 0.6 })
    }
    L.texto(xa - 2, y2 + 19, `overlock en todo el borde: envuelve el canto (la pieza lleva ${cm(M)} cm de más)`, { z: 7, color: GRIS })
    return 110.0
  }
  const y1 = 44.0
  L.texto(X, y1 + 3, 'Corte al ras', { z: 8, b: true })
  telaCorte(L, xa, xe, y1)
  L.linea([[xa, y1 - 10], [xa, y1 + 7]], { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA })
  L.texto(xa, y1 + 15, 'el borde es la guía del diseño: sin margen ni costura', { z: 7, color: GRIS })
  return 62.0
}

/** [ventana en cm [x0, y0, x1, y1], nombre] del detalle de cerca: una esquina del rectángulo, la punta del
 *  triángulo o un tramo del borde del círculo. Gemelo: `_ventana_detalle`. */
function ventanaDetalle(g) {
  if (g.forma === 'rectangulo') {
    const [mi, , , mb] = g.m
    const k = Math.max(mi, mb, 0.1)
    return [[-0.7 * k, -0.7 * k, 3.1 * k, 3.1 * k], 'esquina']
  }
  if (g.forma === 'triangulo') {
    const G = g.G, t = g.t
    const V = G[2]                                     // la PUNTA (la que se orienta)
    const cerca = g.contorno.filter((p) => Math.hypot(p[0] - V[0], p[1] - V[1]) > 1e-9)
    const r = Math.max(2.6 * t, cerca.length ? Math.min(...cerca.map((p) => Math.hypot(p[0] - V[0], p[1] - V[1]))) * 1.3 : 0)
    const I = incentro(G)
    const ix = I.x, iy = I.y
    const d = Math.hypot(ix - V[0], iy - V[1]) || 1
    const cx = V[0] + (ix - V[0]) / d * r * 0.45, cy = V[1] + (iy - V[1]) / d * r * 0.45
    return [[cx - r, cy - r, cx + r, cy + r], 'punta']
  }
  const R = g.R, rg = g.rg
  const t = R - rg
  const r = Math.max(2.4 * t, 1.0)
  return [[R - r, 2 * R - 1.2 * r, R + r, 2 * R + 0.8 * r], 'borde']
}

/** Un recuadro de `lado` × `lado` con la pieza de cerca (cortada o doblada). Gemelo: `_detalle`. */
function detalle(L, g, ventana, X, Y, lado, doblada) {
  const [x0, , x1, y1] = ventana
  const z = lado / (x1 - x0)
  const P = (p) => [X + (p[0] - x0) * z, Y + (y1 - p[1]) * z]
  if (!doblada) {
    const pol = clipPoligono(g.contorno, ventana)
    if (pol.length >= 3) L.linea(pol.map(P), { color: null, relleno: TELA, cerrar: true })
    for (const tr of clipPolilinea(g.contorno, ventana, true)) L.linea(tr.map(P), { color: NEGRO, ancho: 1.0 })
    for (const tr of clipPolilinea(g.guia, ventana, true)) L.linea(tr.map(P), { color: AZUL, ancho: 0.8, rayas: RAYAS_GUIA })
  } else {
    const pol = clipPoligono(g.guia, ventana)
    if (pol.length >= 3) L.linea(pol.map(P), { color: null, relleno: TELA, cerrar: true })
    for (const sol of g.solapas) {                     // el margen doblado, del lado del revés
      const ps = clipPoligono(sol, ventana)
      if (ps.length >= 3) L.linea(ps.map(P), { color: null, relleno: SOLAPA, cerrar: true })
    }
    for (const sol of g.solapas) {                     // sus bordes: donde se cruzan, se superponen
      for (const tr of clipPolilinea(sol, ventana, true)) L.linea(tr.map(P), { color: GRIS, ancho: 0.6, rayas: '[2 1.5] 0' })
    }
    for (const tr of clipPolilinea(g.guia, ventana, true)) L.linea(tr.map(P), { color: NEGRO, ancho: 1.0 })
  }
  if (verdad(g.costura)) {
    for (const tr of clipPolilinea(g.costura, ventana, true)) L.linea(tr.map(P), { color: NARANJA, ancho: 0.8, rayas: RAYAS_COSTURA })
  }
  L.caja(X, Y, X + lado, Y + lado)
}

const TITULO_TERM = { dobladillo: 'EL DOBLADILLO', overlock: 'EL OVERLOCK', sin: 'SIN MARGEN' }

function bloqueTerminacion(g, term, M) {
  const L = new Lienzo()
  const titulo = Object.prototype.hasOwnProperty.call(TITULO_TERM, term) ? TITULO_TERM[term] : 'LA TERMINACIÓN'
  L.texto(0, 10, titulo + ' · el borde de costado', { z: 9.5, b: true })
  const altoA = panelCorte(L, 0.0, term, M, M)
  let alto = altoA
  if (term === 'dobladillo' && g.solapas.length && g.forma !== 'circulo') {
    const [ventana, que] = ventanaDetalle(g)
    const X = 292.0, lado = 104.0
    L.texto(X, 10, (que === 'esquina' ? 'La esquina' : 'La punta') + ' de cerca', { z: 9.5, b: true })
    L.texto(X, 28, 'Cortada', { z: 8, b: true })
    L.texto(X + lado + 19, 28, 'Doblada', { z: 8, b: true })
    detalle(L, g, ventana, X, 34.0, lado, false)
    detalle(L, g, ventana, X + lado + 19, 34.0, lado, true)
    const ny = 34.0 + lado + 11
    L.linea([[X, ny - 2.5], [X + 9, ny - 2.5], [X + 9, ny + 1.5], [X, ny + 1.5]], { color: null, relleno: SOLAPA, cerrar: true })
    L.texto(X + 13, ny + 1, `el margen (${cm(M)} cm) doblado hacia el revés`, { z: 7, color: GRIS })
    L.texto(X, ny + 11, (que === 'esquina' ? 'El recorte de la esquina llega justo a la guía: al doblar,'
      : 'El recorte de la punta llega justo a la guía: al doblar,'), { z: 7, color: GRIS })
    L.texto(X, ny + 20, 'las solapas se superponen y no sobra tela hacia afuera.', { z: 7, color: GRIS })
    alto = Math.max(alto, ny + 25)
  } else if (term === 'dobladillo' && g.forma === 'circulo' && verdad(g.costura)) {
    const [ventana] = ventanaDetalle(g)
    const X = 292.0, lado = 104.0
    L.texto(X, 10, 'El borde de cerca', { z: 9.5, b: true })
    detalle(L, g, ventana, X, 34.0, lado, false)
    const ny = 34.0 + lado + 11
    L.texto(X, ny, `Margen ${cm(M)} cm · costura a ${cm(M)} cm de la guía.`, { z: 7, color: GRIS })
    L.texto(X, ny + 9, 'En la curva el margen doblado es más largo que la línea', { z: 7, color: GRIS })
    L.texto(X, ny + 18, 'donde se apoya: repartir la tela de más pareja al coser.', { z: 7, color: GRIS })
    alto = Math.max(alto, ny + 23)
  }
  return { alto: pyRound(alto + 4, 2), ops: L.ops }
}

// ─── 3 · CÓMO SE TERMINA: los pasos, con las medidas de este pedido ─────────────────────────────────
function pasos(g, term, M, tiras, totalTiras, bordeMm) {
  const f = g.forma
  const rinc = f === 'rectangulo' ? 'esquinas' : 'puntas'
  const corte = 'Cortar la pieza por el contorno' + (verdad(bordeMm) ? ` (el borde de corte impreso, de ${cm(bordeMm)} mm, queda por dentro)` : '') + '.'
  const p = []
  if (term === 'dobladillo') {
    p.push(corte + (g.rec ? ` Las ${rinc} ya vienen recortadas.` : ''))
    p.push(`Doblar el margen de ${cm(M)} cm hacia el revés, por la guía del diseño`
      + (g.rec ? `: la línea que une los vértices de los recortes de las ${rinc}.` : '.'))
    p.push(`Coser a ${cm(M)} cm del doblez (la línea naranja): la costura toma el borde del margen doblado.`)
    if (g.rec) p.push(`En las ${rinc} las solapas quedan una sobre la otra: no sobra tela hacia afuera.`)
    if (f === 'circulo') p.push('En la curva, repartir parejo la tela de más del margen al coser.')
  } else if (term === 'overlock') {
    p.push(corte)
    p.push(`Pasar overlock por todo el borde: la pieza lleva ${cm(M)} cm de más alrededor para la máquina.`)
  } else {
    p.push(corte + ' Sin margen: la pieza es el diseño, no se dobla ni se cose el borde.')
  }
  if (verdad(tiras)) {
    // `{total_tiras}` de un f-string: llega entero (len o la cuenta del servidor)
    if (verdad(pyGet(tiras, 'marcar', true))) {
      p.push(`Coser una tira en cada marca (${totalTiras} en total): cada marca va del borde hasta la guía.`)
    } else {
      p.push(`Coser las tiras (${totalTiras} en total) a las distancias de la tabla: no van marcadas en la tela.`)
    }
  }
  const L = new Lienzo()
  L.texto(0, 10, 'CÓMO SE TERMINA', { z: 9.5, b: true })
  let y = 24.0
  p.forEach((txt, idx) => {
    const lineas = []
    let cur = ''
    for (const pal of txt.split(' ')) {
      const prueba = pyStrip(cur + ' ' + pal)
      if (anchoTexto(prueba, 8.5) > CW - 16 && cur) {
        lineas.push(cur)
        cur = pal
      } else {
        cur = prueba
      }
    }
    lineas.push(cur)
    L.texto(0, y, `${idx + 1}.`, { z: 8.5, b: true })
    for (const ln of lineas) {
      L.texto(16, y, ln, { z: 8.5 })
      y += 11.5
    }
    y += 1.5
  })
  return { alto: pyRound(y - 6, 2), ops: L.ops }
}

/**
 * Los bloques de dibujo de la ficha `[{alto, ops}]` del molde a medida. Gemelo EXACTO de
 * `ficha_a_medida.dibujos_a_medida`. `mg` = el margen que rige por lado (cm); `W` × `H` = el total
 * (`medidaPieza`); `tiras` = lo de `_tiras_de(…, para_ficha=True)` o null; `bordeMm` = el borde de corte
 * impreso (0 si no lleva); `totalTiras` = las que cuenta la fila «Tiras» (cuando no se marcan no hay
 * segmentos que contar).
 */
export function dibujosAMedida(forma, orient, term, anCm, alCm, mg, W, H, tiras = null, bordeMm = 0, totalTiras = null) {
  forma = normForma(forma)
  orient = normOrientacion(orient)
  if (term === 'sin') mg = { arriba: 0.0, abajo: 0.0, izq: 0.0, der: 0.0 }
  mg = mg || {}
  const g = geometria(forma, orient, term, Number(anCm), Number(alCm), mg, Number(W), Number(H))
  g.doblez = term === 'dobladillo'
  const M = forma !== 'rectangulo' ? margenUniforme(mg) : Math.max(...['arriba', 'abajo', 'izq', 'der'].map((k) => num0(mg, k)))
  let segs = []
  if (verdad(tiras)) {
    try {
      // `tiras["margen"]` / `tiras["lados"]` de Python: si falta alguno, KeyError → sin marcas
      if (!('margen' in tiras) || !('lados' in tiras)) throw new Error('faltan margen o lados')
      segs = segmentosTiras(W, H, tiras.margen, tiras.lados, forma, orient, pyGet(tiras, 'diseno_cm', null), pyGet(tiras, 'recorte', true))
    } catch {
      segs = []
    }
  }
  const total = totalTiras !== null && totalTiras !== undefined ? totalTiras : segs.length
  const bordeTxt = verdad(bordeMm) ? `El borde de corte (${cm(bordeMm)} mm) se imprime sobre el contorno, por dentro de la medida total.` : ''
  return [bloquePlano(g, Number(W), Number(H), Number(anCm), Number(alCm), segs, tiras, bordeTxt),
    bloqueTerminacion(g, term, M),
    pasos(g, term, M, tiras, total, bordeMm)]
}
