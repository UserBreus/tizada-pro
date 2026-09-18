// LECTOR MÍNIMO DE DXF (ASCII) — PLAN_NAVEGADOR.md, etapa 1, punto 7.
//
// Un DXF es una lista de pares (código, valor), uno por línea. Acá se leen las tres secciones que usa
// `importar_dxf.py`: HEADER (sólo `$INSUNITS`, `$ACADVER` y `$DWGCODEPAGE`), BLOCKS (para los INSERT
// del parser genérico) y ENTITIES (el modelspace). No se usa `dxf-parser`: no expone la tolerancia de
// nudos de la SPLINE ni el punto base del bloque, y se necesitaba controlar EXACTAMENTE qué códigos
// lee cada entidad para hacer lo mismo que ezdxf (por ejemplo: la elevación de un POLYLINE es la z de
// su código 10, y si no está, la z del primer vértice; los VERTEX cuelgan del POLYLINE hasta SEQEND).
//
// Lo que sale es lo que ezdxf le da a `importar_dxf.py`: entidades planas con los campos que usa
// (`type`, `layer`, `extrusion`, y por tipo: puntos, bulge, flags, centro, radio, ejes, nudos…). Los
// números se leen con `Number()`, que redondea igual que el `float()` de Python.
//
// Codificación: como ezdxf, las versiones anteriores a AC1021 (R2007) van con la página de códigos de
// `$DWGCODEPAGE` (ANSI_1252 → windows-1252, que es también la de omisión); de R2007 en adelante UTF-8.
// Sólo se ven en los nombres de pieza («Piece Name: Cuello Ñandú»).

const TAU = 6.283185307179586

function decodificar(bytes) {
  const latin = new TextDecoder('latin1').decode(bytes)
  // ezdxf mira $ACADVER y $DWGCODEPAGE antes de decodificar el archivo entero
  const ver = /\n\s*9\r?\n\$ACADVER\r?\n\s*1\r?\n([^\r\n]*)/.exec(latin)
  const version = ver ? ver[1].trim() : 'AC1009'
  if (version >= 'AC1021') return new TextDecoder('utf-8').decode(bytes)
  const cp = /\n\s*9\r?\n\$DWGCODEPAGE\r?\n\s*3\r?\n([^\r\n]*)/.exec(latin)
  const nombre = (cp ? cp[1].trim().toLowerCase() : 'ansi_1252')
  const m = /^ansi_(\d+)$/.exec(nombre)
  const codec = m ? 'windows-' + m[1] : (nombre === 'utf-8' || nombre === 'utf8' ? 'utf-8' : 'windows-1252')
  try { return new TextDecoder(codec).decode(bytes) } catch { return new TextDecoder('windows-1252').decode(bytes) }
}

/** Los pares (código, valor) del archivo, en orden. */
function* tags(texto) {
  const lineas = texto.split('\n')
  const n = lineas.length - (lineas[lineas.length - 1] === '' ? 1 : 0)
  for (let i = 0; i + 1 < n; i += 2) {
    const code = parseInt(lineas[i].trim(), 10)
    if (Number.isNaN(code)) continue
    let value = lineas[i + 1]
    if (value.endsWith('\r')) value = value.slice(0, -1)
    yield [code, value]
  }
}

const num = (v) => Number(v.trim())
const punto = (t, cx, cy, cz, def = [0, 0, 0]) => {
  const x = t.get(cx), y = t.get(cy), z = t.get(cz)
  if (x === undefined && y === undefined) return def === null ? undefined : def.slice()
  return [x !== undefined ? num(x) : 0, y !== undefined ? num(y) : 0, z !== undefined ? num(z) : 0]
}

/** Arma la entidad a partir de su lista de pares. */
function armar(tipo, pares) {
  // el primer valor de cada código (lo que ezdxf guarda en `dxf.<attr>`); las listas se leen aparte
  const t = new Map()
  for (const [c, v] of pares) if (!t.has(c)) t.set(c, v)
  const e = {
    type: tipo,
    layer: t.has(8) ? t.get(8) : '0',
    paperspace: t.has(67) ? num(t.get(67)) : 0,
    extrusion: punto(t, 210, 220, 230, [0, 0, 1]),
  }
  if (tipo === 'LINE') {
    e.start = punto(t, 10, 20, 30); e.end = punto(t, 11, 21, 31)
  } else if (tipo === 'LWPOLYLINE') {
    e.flags = t.has(70) ? num(t.get(70)) : 0
    e.elevation = t.has(38) ? num(t.get(38)) : 0.0
    e.points = []
    let p = null
    for (const [c, v] of pares) {
      if (c === 10) { p = { x: num(v), y: 0, s: 0, e: 0, b: 0 }; e.points.push(p) }
      else if (p && c === 20) p.y = num(v)
      else if (p && c === 40) p.s = num(v)
      else if (p && c === 41) p.e = num(v)
      else if (p && c === 42) p.b = num(v)
    }
  } else if (tipo === 'POLYLINE') {
    e.flags = t.has(70) ? num(t.get(70)) : 0
    e.elevation = punto(t, 10, 20, 30, null)        // undefined si el POLYLINE no trae código 10
    e.vertices = []
  } else if (tipo === 'VERTEX') {
    const loc = punto(t, 10, 20, 30)
    e.x = loc[0]; e.y = loc[1]; e.z = loc[2]
    e.bulge = t.has(42) ? num(t.get(42)) : 0.0
    e.flags = t.has(70) ? num(t.get(70)) : 0
  } else if (tipo === 'CIRCLE' || tipo === 'ARC') {
    e.center = punto(t, 10, 20, 30); e.radius = t.has(40) ? num(t.get(40)) : 1.0
  } else if (tipo === 'ELLIPSE') {
    e.center = punto(t, 10, 20, 30); e.majorAxis = punto(t, 11, 21, 31, [1, 0, 0])
    e.ratio = t.has(40) ? num(t.get(40)) : 1.0
    e.startParam = t.has(41) ? num(t.get(41)) : 0.0
    e.endParam = t.has(42) ? num(t.get(42)) : TAU
  } else if (tipo === 'SPLINE') {
    e.flags = t.has(70) ? num(t.get(70)) : 0
    e.degree = t.has(71) ? num(t.get(71)) : 3
    e.knotTolerance = t.has(42) ? num(t.get(42)) : 1e-10
    e.knots = []; e.weights = []; e.controlPoints = []; e.fitPoints = []
    let cp = null, fp = null
    for (const [c, v] of pares) {
      if (c === 40) e.knots.push(num(v))
      else if (c === 41) e.weights.push(num(v))
      else if (c === 10) { cp = [num(v), 0, 0]; e.controlPoints.push(cp) }
      else if (c === 20 && cp) cp[1] = num(v)
      else if (c === 30 && cp) cp[2] = num(v)
      else if (c === 11) { fp = [num(v), 0, 0]; e.fitPoints.push(fp) }
      else if (c === 21 && fp) fp[1] = num(v)
      else if (c === 31 && fp) fp[2] = num(v)
    }
  } else if (tipo === 'TEXT' || tipo === 'ATTRIB' || tipo === 'ATTDEF') {
    e.text = t.has(1) ? t.get(1) : ''
    e.insert = punto(t, 10, 20, 30)
  } else if (tipo === 'MTEXT') {
    // ezdxf: los trozos (código 3) seguidos del final (código 1); \r fuera y \n → \P
    let cola = ''
    const partes = []
    for (const [c, v] of pares) { if (c === 1) cola = v; else if (c === 3) partes.push(v) }
    e.text = (partes.join('') + cola).replace(/\r/g, '').replace(/\n/g, '\\P')
    e.insert = punto(t, 10, 20, 30)
  } else if (tipo === 'INSERT') {
    e.name = t.has(2) ? t.get(2) : ''
    e.insert = punto(t, 10, 20, 30)
    e.xscale = t.has(41) ? num(t.get(41)) : 1.0
    e.yscale = t.has(42) ? num(t.get(42)) : 1.0
    e.zscale = t.has(43) ? num(t.get(43)) : 1.0
    e.rotation = t.has(50) ? num(t.get(50)) : 0.0
    e.attribs = t.has(66) ? num(t.get(66)) : 0
  }
  return e
}

/** Las entidades de una lista de pares (de ENTITIES o de un BLOCK), con los VERTEX colgados de su
 * POLYLINE y los ATTRIB del INSERT, como en ezdxf. */
function entidades(pares) {
  const crudas = []
  let actual = null
  for (const [c, v] of pares) {
    if (c === 0) { actual = { tipo: v.trim(), pares: [] }; crudas.push(actual) }
    else if (actual) actual.pares.push([c, v])
  }
  const out = []
  let dueno = null           // el POLYLINE/INSERT que está juntando VERTEX/ATTRIB
  for (const cr of crudas) {
    const e = armar(cr.tipo, cr.pares)
    if (dueno) {
      if (e.type === 'SEQEND') { dueno = null; continue }
      if (dueno.type === 'POLYLINE' && e.type === 'VERTEX') { dueno.vertices.push(e); continue }
      if (dueno.type === 'INSERT' && e.type === 'ATTRIB') continue
      dueno = null
    }
    if (e.type === 'VERTEX' || e.type === 'SEQEND') continue
    out.push(e)
    if (e.type === 'POLYLINE' || (e.type === 'INSERT' && e.attribs)) dueno = e
  }
  return out
}

/**
 * Lee un DXF: `{version, header: {INSUNITS}, blocks: Map(nombre → {basePoint, entities}), modelspace}`.
 * `modelspace` son las entidades de ENTITIES que no van al paperspace (código 67 ≠ 1).
 */
export function leerDXF(bytes) {
  const texto = decodificar(bytes)
  const header = {}
  const blocks = new Map()
  let modelspace = []
  let seccion = null, esperaNombre = false
  let variable = null
  let bloque = null, paresBloque = null
  let paresEntidades = null
  let version = 'AC1009'
  for (const [c, v] of tags(texto)) {
    if (seccion === null) {
      if (c === 0 && v.trim() === 'SECTION') esperaNombre = true
      else if (esperaNombre && c === 2) { seccion = v.trim(); esperaNombre = false; if (seccion === 'ENTITIES') paresEntidades = [] }
      continue
    }
    if (c === 0 && v.trim() === 'ENDSEC') {
      if (seccion === 'ENTITIES') modelspace = entidades(paresEntidades)
      seccion = null; continue
    }
    if (seccion === 'HEADER') {
      if (c === 9) { variable = v.trim(); continue }
      if (variable === '$INSUNITS' && c === 70) header.INSUNITS = parseInt(v.trim(), 10)
      else if (variable === '$ACADVER' && c === 1) version = v.trim()
      else if (variable === '$DWGCODEPAGE' && c === 3) header.DWGCODEPAGE = v.trim()
    } else if (seccion === 'BLOCKS') {
      if (c === 0 && v.trim() === 'BLOCK') { bloque = { name: '', basePoint: [0, 0, 0], entities: [] }; paresBloque = null; continue }
      if (c === 0 && v.trim() === 'ENDBLK') {
        if (bloque) { bloque.entities = paresBloque ? entidades(paresBloque) : []; blocks.set(bloque.name, bloque) }
        bloque = null; paresBloque = null; continue
      }
      if (!bloque) continue
      if (paresBloque === null) {
        // la cabecera del BLOCK, hasta la primera entidad
        if (c === 0) { paresBloque = [[c, v]]; continue }
        if (c === 2 && !bloque.name) bloque.name = v.trim()
        else if (c === 10) bloque.basePoint[0] = num(v)
        else if (c === 20) bloque.basePoint[1] = num(v)
        else if (c === 30) bloque.basePoint[2] = num(v)
      } else paresBloque.push([c, v])
    } else if (seccion === 'ENTITIES') {
      paresEntidades.push([c, v])
    }
  }
  if (seccion === 'ENTITIES' && paresEntidades) modelspace = entidades(paresEntidades)
  return { version, header, blocks, modelspace: modelspace.filter((e) => e.paperspace !== 1) }
}

/** `fast_plain_mtext(text)` de ezdxf: el texto del MTEXT sin códigos de formato (`\P` → salto). */
export function plainMtext(text) {
  const chars = []
  // caret_decode: ^X → chr((ord(X) - 64) % 126)
  const dec = text.replace(/\^(.)/g, (_, ch) => String.fromCharCode(((ch.charCodeAt(0) - 64) % 126 + 126) % 126))
  let raw = Array.from(dec).reverse()
  const ONE_CHAR = 'PNLlOoKkX'
  const SPECIAL = { c: 'Ø', d: '°', p: '±' }
  while (raw.length) {
    let char = raw.pop()
    if (char === '\\') {
      if (!raw.length) break
      char = raw.pop()
      if ('\\{}'.includes(char)) chars.push(char)
      else if (ONE_CHAR.includes(char)) {
        if (char === 'P') chars.push('\n')
        else if (char === 'N') chars.push(' ')
      } else {
        const stacking = char === 'S'
        const first = char
        const search = raw.slice()
        let ok = true
        while (char !== ';') {
          if (!search.length) { ok = false; break }
          char = search.pop()
          if (stacking && char !== ';') chars.push(char)
        }
        if (ok) raw = search
        else { chars.push('\\'); chars.push(first) }
      }
    } else if (char === '{' || char === '}') {
      // marcas de grupo: fuera
    } else if (char === '%') {
      if (raw.length && raw[raw.length - 1] === '%') {
        raw.pop()
        if (raw.length) {
          const code = raw.pop()
          const letter = SPECIAL[code.toLowerCase()]
          if (letter) chars.push(letter)
          else chars.push('%', '%', code)
        }
      } else chars.push(char)
    } else chars.push(char)
  }
  return chars.join('')
}
