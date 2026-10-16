// EL MOLDE A MEDIDA EN LA FICHA TÉCNICA, CALCULADO EN ESTA COMPUTADORA (MAPA 692).
//
// Regla del usuario (2026-10-13): «no quiero que nada del uso dependa del servidor; el servidor sólo
// contiene el sistema y guarda». Hasta acá el PLAN traía la sección «MEDIDA Y TERMINACIÓN» ya redactada
// por el servidor (`_ficha_a_medida` + `_agrupar_a_medida_ficha`); ahora el servidor manda sólo los DATOS
// guardados del molde (`a_medida_datos`: la medida, la forma, la terminación, el borde y las tiras) y las
// filas, las notas, los dibujos y el agrupado se arman acá.
//
// Gemelos EXACTOS (mismos textos, mismos números): `_ficha_a_medida`, `_tiras_por_lado`, `_total_tiras`,
// `_margen_a_medida` y `_agrupar_a_medida_ficha` de servidor.py — siguen allá para la API del otro sistema
// y la ficha del servidor. El contrato `verificar_molde_a_medida.py` §692 compara los dos lados.
// Los números se formatean como Python (`py.js`): `round` al par en el empate y `:g` sin ceros de más.

import { medidaPieza, margenDeTerminacion, normTerminacion } from './aMedida.js'
import { segmentosTiras } from './tiras.js'
import { normForma, normOrientacion, margenUniforme, verticesTriangulo, NOMBRE_FORMA, NOMBRE_PUNTA } from './formas.js'
import { dibujosAMedida } from '../ficha/aMedidaDibujos.js'
import { pyRound, pyFixed, pyG } from '../py.js'

const LADOS = ['arriba', 'abajo', 'izq', 'der']

/** `cm = lambda x: f"{round(float(x) * 10) / 10:g}".replace(".", ",")` de la ficha del servidor. */
const cm = (x) => pyG(pyRound(Number(x) * 10) / 10).replace('.', ',')

/** El margen (dobladillo) en cm: `{todos}` o `{arriba, abajo, izq, der}`, todo entre 0 y 100. Gemelo: `_margen_a_medida`. */
export function margenGuardado(m) {
  m = m && typeof m === 'object' ? m : {}
  const out = {}
  for (const k of ['todos', ...LADOS]) {
    if (m[k] === undefined || m[k] === null || m[k] === '') continue
    const v = Number(String(m[k]).replace(',', '.'))
    if (Number.isFinite(v)) out[k] = Math.max(0, Math.min(100, v))
  }
  if (out.todos === undefined) out.todos = 0
  return out
}

const entero = (x) => Math.trunc(Number(x) || 0)

/** Cuántas tiras lleva la pieza sin dibujarlas (la ficha cuando NO se marcan). Gemelo: `_total_tiras`. */
export function totalTiras(forma, lados, recorte = true) {
  const n = (k) => Math.max(0, entero((lados || {})[k]))
  const medio = (c) => (c === 1 ? 1 : Math.max(0, c - 2))
  if (forma === 'circulo') return n('alrededor')
  if (forma === 'triangulo') {
    const nb = n('base'), nl = n('laterales')
    const puntas = recorte ? 0 : (nb >= 2 || nl >= 2 ? 2 : 0) + (nl >= 2 ? 1 : 0)
    return puntas + medio(nb) + 2 * medio(nl)
  }
  const a = n('arriba'), b = n('abajo'), i = n('izq'), d = n('der')
  const esquinas = recorte ? 0 : [[i, b], [d, b], [d, a], [i, a]].filter(([x, y]) => x >= 2 || y >= 2).length
  return esquinas + medio(a) + medio(b) + medio(i) + medio(d)
}

/** Las tiras de cada lado de la pieza TOTAL (`W` × `H` cm). Gemelo: `_tiras_por_lado`. */
export function tirasPorLado(forma, orientacion, W, H, t) {
  const out = []
  const lados = t.lados || {}, mg = t.margen || {}
  const mu = margenUniforme(mg)
  const todas = !(t.marcar ?? true)          // no se marcan: la ficha las lista igual, sin largo de marca
  if (forma === 'circulo') {
    const n = entero(lados.alrededor)
    if (n > 0 && (mu > 0 || todas)) {
      const per = Math.PI * W
      out.push({ lado: 'alrededor', nombre: 'Alrededor', marcas: n, largo_del_lado_cm: pyRound(per, 1),
                 cada_cm: pyRound(per / n, 2), en_el_medio: false, largo_marca_cm: mu })
    }
    return out
  }
  if (forma === 'triangulo') {
    // recortado (MAPA 649) las marcas se reparten sobre la GUÍA (el borde terminado), de punta a punta
    const dc = t.diseno_cm || [W, H]
    const P = verticesTriangulo(0, 0, Number(dc[0]), Number(dc[1]), orientacion)
    const d = (u, v) => Math.sqrt((u[0] - v[0]) ** 2 + (u[1] - v[1]) ** 2)
    for (const [k, nombre, L] of [['base', 'Base', d(P[0], P[1])], ['laterales', 'Laterales (cada uno)', d(P[1], P[2])]]) {
      const n = entero(lados[k])
      if (n > 0 && (mu > 0 || todas)) {
        out.push({ lado: k, nombre, marcas: n, largo_del_lado_cm: pyRound(L, 1),
                   cada_cm: n >= 2 ? pyRound(L / (n - 1), 2) : null, en_el_medio: n === 1, largo_marca_cm: mu })
      }
    }
    return out
  }
  const f = (k) => Number(mg[k]) || 0
  const ladosR = t.recorte     // esquinas recortadas (MAPA 653): sobre la GUÍA, de esquina a esquina
    ? [['arriba', 'Arriba', W - f('izq') - f('der')], ['abajo', 'Abajo', W - f('izq') - f('der')],
       ['izq', 'Izquierda', H - f('arriba') - f('abajo')], ['der', 'Derecha', H - f('arriba') - f('abajo')]]
    : [['arriba', 'Arriba', W], ['abajo', 'Abajo', W], ['izq', 'Izquierda', H], ['der', 'Derecha', H]]
  for (const [k, nombre, L] of ladosR) {
    const n = entero(lados[k])
    if (n > 0 && (f(k) > 0 || todas)) {
      out.push({ lado: k, nombre, marcas: n, largo_del_lado_cm: pyRound(L, 1),
                 cada_cm: n >= 2 ? pyRound(L / (n - 1), 2) : null, en_el_medio: n === 1, largo_marca_cm: f(k) })
    }
  }
  return out
}

/**
 * La sección «MEDIDA Y TERMINACIÓN» de la ficha: `{filas, notas, dibujos}` o null si no es a medida.
 * `datos` = `a_medida_datos` del plan: `{am, borde: {activo, ancho_mm}, tiras}` (lo GUARDADO; las tiras como
 * `_tiras_de(..., para_ficha=True)`, las mismas que dibuja el motor). Gemelo: `_ficha_a_medida`.
 */
export function fichaAMedida(datos) {
  const am = datos && datos.am
  if (!am || typeof am !== 'object') return null
  const an = Number(am.ancho_m) || 1, al = Number(am.alto_m) || 1
  const m = margenGuardado(am.margen)
  const t0 = Number(m.todos) || 0
  const mg = {}
  for (const k of LADOS) mg[k] = Number(m[k] ?? t0) || 0
  const f = normForma(am.forma), o = normOrientacion(am.orientacion)
  const term = normTerminacion(am.terminacion)
  const { anchoCm: W, altoCm: H } = medidaPieza(an, al, margenDeTerminacion(am, term), f, o, term)   // el margen que RIGE
  const mu = margenUniforme(mg)
  let mtxt
  if (f !== 'rectangulo') mtxt = mu > 0 ? `${cm(mu)} cm parejo en todo el borde` : ''
  else if (new Set(LADOS.map((k) => mg[k])).size === 1) mtxt = mg.arriba > 0 ? `${cm(mg.arriba)} cm por lado` : ''
  else mtxt = `arriba ${cm(mg.arriba)} · abajo ${cm(mg.abajo)} · izquierda ${cm(mg.izq)} · derecha ${cm(mg.der)} cm`
  // LA TERMINACIÓN (MAPA 652): dobladillo (con las puntas del triángulo recortadas), overlock o sin margen
  const ttxt = (term === 'sin' || mu <= 0) ? 'Sin margen'
    : term === 'overlock' ? `Overlock · ${mtxt}`
      : `Dobladillo · ${mtxt}` + (f === 'triangulo' ? ' · puntas recortadas' : f === 'rectangulo' ? ' · esquinas recortadas' : '')
  const b = (datos && datos.borde) || {}
  const bordeMm = Number(b.ancho_mm) || 0
  const btxt = b.activo ? `${cm(bordeMm)} mm, adentro de la medida total` : 'sin borde de corte'
  const [md, tt] = f === 'circulo' ? [`Ø ${cm(an * 100)} cm`, `Ø ${cm(W)} cm`]
    : [`${cm(an * 100)} × ${cm(al * 100)} cm`, `${cm(W)} × ${cm(H)} cm`]
  const filas = [
    { etiqueta: 'Forma', valor: NOMBRE_FORMA[f] + (f === 'triangulo' ? `, ${NOMBRE_PUNTA[o]}` : '') },
    { etiqueta: 'Medida del diseño (guía)', valor: md },
    { etiqueta: 'Total del arte (con el margen)', valor: tt },
    { etiqueta: 'Terminación', valor: ttxt },
    { etiqueta: 'Borde de corte', valor: btxt },
  ]
  let notas = []
  const t = datos.tiras || null
  let total = null
  if (t) {
    const rec = t.recorte ?? true
    const marcar = t.marcar ?? true
    total = marcar ? segmentosTiras(W, H, t.margen, t.lados, f, o, t.diseno_cm ?? null, rec).length : totalTiras(f, t.lados, rec)
    filas.push({ etiqueta: 'Tiras', valor: !marcar
      ? `${total} tira${total !== 1 ? 's' : ''} en total · no se marcan en la tizada`
      : `${total} marca${total !== 1 ? 's' : ''} en total · grosor ${cm(t.grosor_mm)} mm · negra con contorno blanco` })
    for (const x of tirasPorLado(f, o, W, H, t)) {
      let v
      if (x.marcas === 1 && x.lado !== 'alrededor') v = `1 marca, en el medio (a ${cm(x.largo_del_lado_cm / 2)} cm de cada punta)`
      else if (x.lado === 'alrededor') v = `${x.marcas} marca${x.marcas !== 1 ? 's' : ''} parejas, una cada ${cm(x.cada_cm)} cm sobre el borde`
      else v = `${x.marcas} marcas contando las 2 puntas, una cada ${cm(x.cada_cm)} cm`
      filas.push({ etiqueta: x.nombre, valor: v + (marcar ? ` · marca de ${cm(x.largo_marca_cm)} cm` : ''), sub: true })
    }
    // una frase por renglón: la ficha no parte el texto y una sola larga se cortaba al borde de la hoja
    notas = f === 'circulo'
      ? ['Cada marca va del borde de la pieza hacia el centro, hasta la guía del diseño.',
         'Las distancias se miden sobre el borde, empezando arriba.']
      : f === 'triangulo' && rec
        ? ['Cada marca va del borde de la pieza hasta la guía; en las puntas no lleva (el corte ya la marca).',
           'Las distancias se miden sobre la guía, de punta a punta.']
        : f === 'triangulo'
          ? ['Cada marca va del borde de la pieza hasta la guía; las de las puntas, en diagonal.',
             'Las distancias se miden sobre la guía, de punta a punta.']
          : rec
            ? ['Cada marca va del borde de la pieza hasta la guía; en las esquinas no lleva (el corte ya la marca).',
               'Las distancias se miden sobre la guía, de esquina a esquina.']
            : ['Cada marca va del borde de la pieza hasta la guía del diseño; las de las esquinas, en diagonal.',
               'Las distancias se miden sobre el borde, de punta a punta.']
    if (!marcar) notas = ['No van marcadas en la tela: se cosen a estas distancias.', ...notas.slice(1)]   // no van impresas (MAPA 652)
  } else {
    filas.push({ etiqueta: 'Tiras', valor: 'no lleva' })
  }
  // LOS DIBUJOS (MAPA 659): best-effort, como en el servidor: si algo falla, la ficha sale igual con las filas
  let dibujos = []
  try {
    dibujos = dibujosAMedida(f, o, term, an * 100, al * 100, term !== 'sin' ? mg : {}, W, H, t, b.activo ? bordeMm : 0, t ? total : null)
  } catch (e) {
    console.warn('[ficha] dibujos del molde a medida:', e)
    dibujos = []
  }
  return { filas, notas, dibujos }
}

/** `json.dumps(x, sort_keys=True)`: para comparar dos secciones sin importar el orden de las claves. */
function claveOrdenada(x) {
  if (Array.isArray(x)) return '[' + x.map(claveOrdenada).join(',') + ']'
  if (x && typeof x === 'object') return '{' + Object.keys(x).sort().map((k) => JSON.stringify(k) + ':' + claveOrdenada(x[k])).join(',') + '}'
  return JSON.stringify(x === undefined ? null : x)
}

/**
 * LOS MOLDES A MEDIDA EN LA FICHA (MAPA 665-666), sobre la lista de guías que arma ESTA computadora. Cambia la
 * lista en el lugar. Cada guía trae `pid`, `nombre`, `diseno_nombre` y `a_medida_datos` (del plan) y
 * `a_medida` (ya calculada con `fichaAMedida`): (1) una sección por CONFIGURACIÓN — las demás quedan con
 * `a_medida: null` y la primera lleva `titulo_disenos`; (2) `am` = el bloque compacto de cada guía, y las de
 * una misma plantilla, juntas. Gemelo: `_agrupar_a_medida_ficha`.
 */
export function agruparAMedidaFicha(guias) {
  const miembros = new Map()
  for (const g of guias) {
    const amc = g.a_medida_datos && g.a_medida_datos.am
    if (!amc || typeof amc !== 'object') continue
    const origen = amc.de || g.pid
    miembros.set(origen, (miembros.get(origen) || 0) + 1)
    const f = normForma(amc.forma), o = normOrientacion(amc.orientacion)
    const an = Number(amc.ancho_m) || 1, al = Number(amc.alto_m) || 1
    let W, H
    try {
      ({ anchoCm: W, altoCm: H } = medidaPieza(an, al, margenDeTerminacion(amc), f, o, amc.terminacion))
    } catch { W = an * 100; H = al * 100 }
    const m2 = (v) => pyFixed(Number(v), 2).replace('.', ',')
    const sub = f === 'circulo' ? `Ø ${m2(an)} m · círculo` : `${m2(an)} × ${m2(al)} m` + (f === 'triangulo' ? ' · triángulo' : '')
    g.am = { grupo: origen, molde: String(g.a_medida_datos.plantilla_nombre || g.molde || g.nombre || ''),
             sub, aspecto: W ? pyRound(H / W, 4) : 1.0 }
  }
  // las de una misma plantilla, juntas (en el lugar de la primera; el resto no cambia de orden)
  const orden = [], hechos = new Set()
  for (const g of guias) {
    const k = g.am && g.am.grupo
    if (!k) orden.push(g)
    else if (!hechos.has(k)) {
      hechos.add(k)
      orden.push(...guias.filter((x) => (x.am && x.am.grupo) === k))
    }
  }
  guias.splice(0, guias.length, ...orden)
  const vistos = new Map()
  for (const g of guias) {
    const am = g.a_medida
    if (!am || typeof am !== 'object' || !(am.filas && am.filas.length)) continue
    const origen = (g.am && g.am.grupo) || g.pid
    const clave = claveOrdenada([origen, am.filas, am.notas, am.dibujos])
    const dis = String(g.diseno_nombre || g._diseno_slug || '').trim()
    if (vistos.has(clave)) {
      const ds = vistos.get(clave).a_medida._disenos
      if (dis && !ds.includes(dis)) ds.push(dis)
      g.a_medida = null                    // ya está en la primera
      continue
    }
    g.a_medida = { ...am, _disenos: dis ? [dis] : [] }
    vistos.set(clave, g)
  }
  for (const g of vistos.values()) {
    const ds = g.a_medida._disenos
    delete g.a_medida._disenos
    const origen = (g.am && g.am.grupo) || g.pid
    if (ds.length && (ds.length > 1 || (miembros.get(origen) || 0) > 1)) {
      g.a_medida.titulo_disenos = ds.length === 1 ? ds[0] : ds.slice(0, -1).join(', ') + ' y ' + ds[ds.length - 1]
    }
  }
  return guias
}
