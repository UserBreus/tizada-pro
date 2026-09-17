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
