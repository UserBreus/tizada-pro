// LO QUE PYTHON HACE DISTINTO QUE JAVASCRIPT CON LOS NÚMEROS (PLAN_NAVEGADOR.md, regla 2: la
// salida del navegador tiene que ser IDÉNTICA a la del servidor).
//
// `round(x, n)` y `f"{x:.1f}"` de Python redondean el valor BINARIO exacto al decimal más cercano
// y, en un empate exacto, al PAR (0.125 → 0.12). `Number.prototype.toFixed` también mira el valor
// exacto pero en el empate va para ARRIBA (0.125 → "0.13"). Pasa poco (sólo con valores que en
// binario son exactamente ...5), pero pasa: acá se hace como Python.

function digitosExactos(ax) {
  // |x| con 100 decimales: para los valores de este sistema (medidas en puntos, de 1e-6 a 1e6) es
  // la expansión decimal EXACTA del double (tiene a lo sumo ~60 decimales)
  return ax.toFixed(100)
}

function redondearTexto(x, n) {
  if (!Number.isFinite(x)) return String(x)
  const neg = x < 0 || Object.is(x, -0)
  const s = digitosExactos(Math.abs(x))
  const punto = s.indexOf('.')
  const ent = s.slice(0, punto)
  const dec = s.slice(punto + 1)
  let cuerpo = ent + dec.slice(0, n)              // dígitos que quedan, sin punto
  const resto = dec.slice(n)
  const primero = resto.charCodeAt(0) - 48
  const masAlla = /[1-9]/.test(resto.slice(1))
  let subir = false
  if (primero > 5 || (primero === 5 && masAlla)) subir = true
  else if (primero === 5 && !masAlla) subir = ((cuerpo.charCodeAt(cuerpo.length - 1) - 48) % 2) === 1   // empate: al par
  if (subir) {
    const d = cuerpo.split('')
    let i = d.length - 1
    while (i >= 0) {
      if (d[i] === '9') { d[i] = '0'; i-- } else { d[i] = String.fromCharCode(d[i].charCodeAt(0) + 1); break }
    }
    cuerpo = (i < 0 ? '1' : '') + d.join('')
  }
  const e = cuerpo.length - n
  let txt = n > 0 ? cuerpo.slice(0, e) + '.' + cuerpo.slice(e) : cuerpo
  txt = txt.replace(/^0+(?=\d)/, '')
  return (neg ? '-' : '') + txt
}

/** `round(x, n)` de Python (float → float). */
export function pyRound(x, n = 0) {
  if (!Number.isFinite(x)) return x
  return Number(redondearTexto(x, n))
}

/** `f"{x:.Nf}"` de Python. */
export function pyFixed(x, n) {
  return redondearTexto(x, n)
}

/** `f"{x:g}"` de Python para los casos de este sistema (altos en mm con .5): sin ceros de más. */
export function pyG(x) {
  if (Number.isInteger(x)) return String(x)
  let s = x.toPrecision(6)
  if (s.includes('e')) return s
  s = s.replace(/0+$/, '').replace(/\.$/, '')
  return s
}

/** `max(lista, key=f)` de Python: el PRIMERO de los máximos. */
export function pyMax(lista, clave) {
  let mejor, mk
  for (const x of lista) {
    const k = clave(x)
    if (mejor === undefined || compararTuplas(k, mk) > 0) { mejor = x; mk = k }
  }
  return mejor
}

/** Comparación de tuplas como Python (números y textos, elemento por elemento). */
export function compararTuplas(a, b) {
  if (!Array.isArray(a)) a = [a]
  if (!Array.isArray(b)) b = [b]
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    if (a[i] < b[i]) return -1
    if (a[i] > b[i]) return 1
  }
  return a.length - b.length
}

// `str.isspace()` de Python: los espacios de Python NO son los de `\s` de JavaScript (Python cuenta
// \x1c-\x1f y no cuenta ﻿). Importa porque un espacio sin glifo se estampa con un avance en
// vez de reventar, y tiene que ser el MISMO conjunto de caracteres en las dos puntas.
const ESPACIO_PY = /^[\t\n\v\f\r\x1c-\x1f \x85\xa0  - \u2028\u2029  　]$/
export function pyIsSpace(ch) {
  return ESPACIO_PY.test(ch)
}

/** `str.strip()` de Python (sin argumentos): saca los espacios de Python en las dos puntas. */
export function pyStrip(s) {
  const c = Array.from(s)
  let i = 0, j = c.length
  while (i < j && pyIsSpace(c[i])) i++
  while (j > i && pyIsSpace(c[j - 1])) j--
  return c.slice(i, j).join('')
}

// `sum(lista)` de Python 3.12 para números. NO es una suma simple: mientras los ítems son enteros
// acumula exacto; con el primer float pasa a double y de ahí en más los floats se suman con la
// compensación de Neumaier (Kahan–Babuška) y los enteros se suman a secas; al final agrega la
// compensación si es finita. Se notó en `ancho_texto` con glifos prestados (anchos float mezclados
// con enteros): un bit distinto en el ancho corre el nombre entero en la pieza.
export function pySum(valores, esEntero) {
  const n = valores.length
  let i = 0, iResult = 0
  while (i < n && esEntero(i)) { iResult += valores[i]; i++ }
  if (i === n) return iResult
  let fResult = iResult + valores[i]
  i++
  let c = 0.0
  for (; i < n; i++) {
    const x = valores[i]
    if (esEntero(i)) { fResult += x; continue }
    const t = fResult + x
    if (Math.abs(fResult) >= Math.abs(x)) c += (fResult - t) + x
    else c += (x - t) + fResult
    fResult = t
  }
  if (c !== 0 && Number.isFinite(c)) fResult += c
  return fResult
}
