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

/** `_norm_generico`: además sin el número final («Frente 8» → «frente»). */
export function normGenerico(s) {
  return pyStrip(normNombre(s).replace(RX_GENERICO, ''))
}

/** `_es_capa_guia`: la capa «guías» del arte (texto para el sistema; nunca se imprime). */
export const esCapaGuia = (nombre) => ['guias', 'guia', 'guides'].includes(normNombre(nombre || ''))
/**
 * `_es_capa_editable`: la palabra «editable» EN CUALQUIER PARTE del nombre de la capa, en
 * mayúsculas o minúsculas (regla del usuario 2026-09-23: «Editablecosopere», «Editable_coso. pere»,
 * «Logo editable» también son editables). Antes tenía que EMPEZAR con «editable».
 */
export const esCapaEditable = (nombre) => normNombre(nombre || '').includes('editable')

// la palabra «editable» con los separadores que la rodean — `_RX_EDITABLE` del Python
const RX_EDITABLE = new RegExp('[' + WS_PY + '\\-_.]*editable(?:s(?=[' + WS_PY + '\\-_.]|$))?[' + WS_PY + '\\-_.]*', 'giu')

/**
 * `_nombre_editable(capa)`: la capa SIN la palabra «editable» (esté donde esté) ni los separadores
 * que la rodean: «Editable TPU» y «Editable_TPU» → «TPU» (el MISMO objeto), «Editablecosopere» →
 * «cosopere», «Logo editable» → «Logo». Igual que el Python (`" ".join(sub(...).split())` y
 * `strip(" -_.")`).
 */
export function nombreEditable(capa) {
  const s = splitPy(String(capa).replace(RX_EDITABLE, ' ')).join(' ')
  return s.replace(/^[ \-_.]+|[ \-_.]+$/g, '') || 'Editable'
}

/** Capas que no son talles ni piezas (`molde_real.CAPAS_SISTEMA`). */
export const CAPAS_SISTEMA = new Set(['Fondo', 'Capa 1', 'Personalizable', '0', 'referencia', 'Referencia'])
/** `CAPAS_NO_PERS` de motor_pedido: cualquier OTRA capa del arte es un campo de personalización. */
export const CAPAS_NO_PERS = new Set(['diseño', 'diseno', 'personalizable', 'guias', 'guías', 'guides',
  'guia', 'guía', 'fondo', 'capa 1', 'referencia', '0'])
/** Las capas gráficas (las de arriba menos «personalizable»). */
export const CAPAS_GRAFICAS = new Set([...CAPAS_NO_PERS].filter((x) => x !== 'personalizable'))
