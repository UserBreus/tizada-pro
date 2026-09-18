// LOS NOMBRES COMO PYTHON, EN UN SOLO LUGAR — `motor_pedido._norm_nombre` / `_norm_generico` /
// `_es_capa_guia` / `_es_capa_editable` / `_nombre_editable`, `molde_real._norm_capa`, y las listas
// de capas del sistema. Antes cada módulo (molde, pieza, arte) tenía su copia: la misma regla escrita
// tres veces era tres lugares para que una se desviara (MAPA 495, pendiente de unificar).
//
// Todo es exacto respecto de Python: los espacios son los de `str.split()` (incluye U+001C-U+001F,
// el separador de los idents de las figuras editables), `\d` es `\p{Nd}` y `strip()` es `pyStrip`.
import { pyIsSpace, pyStrip } from './py.js'

/** `str.split()` de Python (sin argumento): por corridas de espacios de Python, sin vacíos. */
export function splitPy(s) {
  const out = []
  let cur = ''
  for (const ch of String(s)) {
    if (pyIsSpace(ch)) { if (cur) { out.push(cur); cur = '' } } else cur += ch
  }
  if (cur) out.push(cur)
  return out
}

/** `_norm_nombre`: NFKD sin marcas combinantes, minúsculas, guión → espacio, espacios colapsados. */
export function normNombre(s) {
  if (!s) return ''
  const t = String(s).normalize('NFKD').replace(/\p{Mn}/gu, '')
  return splitPy(t.toLowerCase().replace(/-/g, ' ')).join(' ')
}

/** `molde_real._norm_capa`: la misma regla (sobre el texto tal cual, sin el atajo del vacío). */
export const normCapa = (s) => normNombre(String(s))

// los espacios de Python (`str.isspace`), como clase de expresión regular
export const WS_PY = '\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000'
const RX_GENERICO = new RegExp('[' + WS_PY + ']+\\p{Nd}+[' + WS_PY + ']*$', 'u')
const RX_WS = new RegExp('^[' + WS_PY + ']$')

/** `_norm_generico`: además sin el número final («Frente 8» → «frente»). */
export function normGenerico(s) {
  return pyStrip(normNombre(s).replace(RX_GENERICO, ''))
}

/** `_es_capa_guia`: la capa «guías» del arte (texto para el sistema; nunca se imprime). */
export const esCapaGuia = (nombre) => ['guias', 'guia', 'guides'].includes(normNombre(nombre || ''))
/** `_es_capa_editable`: una capa OCG «Editable …». */
export const esCapaEditable = (nombre) => normNombre(nombre || '').startsWith('editable')

/**
 * `_nombre_editable(capa)`: sin el prefijo «editable» (con o sin separador), como el Python
 * (`re.sub(r"^\s*editable\b[\s\-_]*", "", s.strip(), flags=re.I)`, con `\s`/`\b` de Python).
 */
export function nombreEditable(capa) {
  const s = pyStrip(String(capa))
  const chars = Array.from(s)
  let i = 0
  const esWs = (ch) => RX_WS.test(ch)
  while (i < chars.length && esWs(chars[i])) i++
  const pal = chars.slice(i, i + 8).join('')
  let fin = null
  if (pal.toLowerCase() === 'editable') {
    const sig = chars[i + 8]
    // `\b`: después de «editable» no puede seguir otro carácter de palabra
    if (sig === undefined || !/[\p{L}\p{N}_]/u.test(sig)) {
      let j = i + 8
      while (j < chars.length && (esWs(chars[j]) || chars[j] === '-' || chars[j] === '_')) j++
      fin = j
    }
  }
  const r = fin === null ? s : chars.slice(fin).join('')
  return pyStrip(r) || 'Editable'
}

/** Capas que no son talles ni piezas (`molde_real.CAPAS_SISTEMA`). */
export const CAPAS_SISTEMA = new Set(['Fondo', 'Capa 1', 'Personalizable', '0', 'referencia', 'Referencia'])
/** `CAPAS_NO_PERS` de motor_pedido: cualquier OTRA capa del arte es un campo de personalización. */
export const CAPAS_NO_PERS = new Set(['diseño', 'diseno', 'personalizable', 'guias', 'guías', 'guides',
  'guia', 'guía', 'fondo', 'capa 1', 'referencia', '0'])
/** Las capas gráficas (las de arriba menos «personalizable»). */
export const CAPAS_GRAFICAS = new Set([...CAPAS_NO_PERS].filter((x) => x !== 'personalizable'))
