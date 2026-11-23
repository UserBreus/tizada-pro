// CONTRATO DEL BUSCADOR de moldes y variables (`src/buscador.js`) — `node verificar_buscador.mjs`
//
// Los ejemplos son los que dio el usuario (2026-11-12, MAPA 815): «busco cortada y me aparecen moldes
// que no tienen cortada ni en la variable ni en el molde» · «si pongo cortada M filtra todo lo que
// contenga cortada M» · «cuando borrás queda trancado: debería volver a aparecer todo».
// Corre en el build: si alguien vuelve a aflojar la coincidencia, no compila.
import { readFileSync } from 'node:fs'
import { normBusq, puntajeBusqueda, filtrarBusqueda, clavesRepetidas } from './src/buscador.js'

let fallas = 0
const ok = (cond, que) => { if (!cond) { fallas++; console.error('  ✗ ' + que) } }
const igual = (a, b, que) => ok(JSON.stringify(a) === JSON.stringify(b), `${que}\n      esperado: ${JSON.stringify(b)}\n      salió:    ${JSON.stringify(a)}`)

// Lo mismo que arma la pantalla: una entrada por variable, con su molde detrás.
const V = (label, moldeNombre) => ({ label, moldeNombre, clave: `${moldeNombre}/${label}` })
const vars = [
  V('Cuello redondo', 'Camiseta de futbol'), V('cuello V', 'Camiseta de futbol'), V('Cortada', 'Camiseta de futbol'),
  V('Cortada M', 'Camiseta de futbol'), V('Cortada manga larga', 'Camiseta de futbol'), V('Recortada', 'Camiseta de futbol'),
  V('Manga corta', 'Camiseta de futbol'), V('Entera', 'Camiseta de futbol'),
  V('Cortada mujer', 'Musculosa'), V('Cortada M', 'Musculosa'), V('Lisa', 'Musculosa'),
  V('Clásica', 'Short cortada'), V('Con bolsillo', 'Short cortada'),
]
const textos = (v) => [v.label, v.moldeNombre]
const buscar = (q) => filtrarBusqueda(q, vars, textos).map(({ item }) => `${item.label} @ ${item.moldeNombre}`)

// 1) «cortada»: la que se llama así va PRIMERO, y siguen las que la contienen (no las esconde).
{
  const r = buscar('cortada')
  ok(r[0] === 'Cortada @ Camiseta de futbol', `«cortada»: la exacta va primero (salió «${r[0]}»)`)
  for (const n of ['Cortada M @ Camiseta de futbol', 'Cortada manga larga @ Camiseta de futbol', 'Recortada @ Camiseta de futbol',
    'Cortada mujer @ Musculosa', 'Cortada M @ Musculosa']) ok(r.includes(n), `«cortada» tiene que mostrar «${n}»`)
  // el molde se llama «Short cortada»: aparecen TODAS sus variables
  for (const n of ['Clásica @ Short cortada', 'Con bolsillo @ Short cortada']) ok(r.includes(n), `«cortada» es parte del nombre del molde: muestra «${n}»`)
  // y NADA que no tenga «cortada» ni en la variable ni en el molde
  for (const n of ['Cuello redondo @ Camiseta de futbol', 'cuello V @ Camiseta de futbol', 'Manga corta @ Camiseta de futbol',
    'Entera @ Camiseta de futbol', 'Lisa @ Musculosa']) ok(!r.includes(n), `«cortada» NO puede mostrar «${n}»`)
  ok(r.indexOf('Cortada M @ Camiseta de futbol') < r.indexOf('Recortada @ Camiseta de futbol'), '«cortada»: lo que EMPIEZA así va antes que lo que la tiene en el medio')
}

// 2) «cortada M»: sólo lo que contiene «cortada m» de corrido.
igual(buscar('cortada M'), ['Cortada M @ Camiseta de futbol', 'Cortada M @ Musculosa', 'Cortada manga larga @ Camiseta de futbol', 'Cortada mujer @ Musculosa'],
  '«cortada M»: las exactas primero y después las que siguen con «m…»; nada más')
igual(buscar('cortada ma'), ['Cortada manga larga @ Camiseta de futbol'], '«cortada ma»: cuanto más se escribe, menos queda')
// antes alcanzaba con que cada palabra estuviera en cualquier lado: «m» está en «Camiseta»
ok(!buscar('cortada m').includes('Cortada @ Camiseta de futbol'), '«cortada m» NO trae «Cortada» por la «m» de «Camiseta de futbol»')
ok(!buscar('cortada c').some((x) => x.endsWith('@ Short cortada')), '«cortada c» NO junta el final del molde con el principio de la variable')

// 3) El nombre del molde muestra todas sus variables.
igual(buscar('musculosa'), ['Cortada mujer @ Musculosa', 'Cortada M @ Musculosa', 'Lisa @ Musculosa'], '«musculosa»: todas las variables de ese molde, en su orden')
igual(buscar('camiseta de futbol').length, 8, '«camiseta de futbol»: sus 8 variables')

// 4) Sin tildes ni mayúsculas, y con espacios de más.
igual(buscar('  CLASICA '), ['Clásica @ Short cortada'], 'sin tildes, sin mayúsculas, sin espacios de más')
igual(normBusq('  Ñandú   Único '), 'nandu unico', 'normBusq')

// 5) Borrar la búsqueda devuelve TODO, en el orden de siempre.
for (const q of ['', '   ', null, undefined]) {
  igual(filtrarBusqueda(q, vars, textos).map(({ item }) => item.clave), vars.map((v) => v.clave), `búsqueda vacía (${JSON.stringify(q)}): aparece todo`)
}
igual(buscar('zzz'), [], 'lo que no existe no trae nada')

// 6) El puntaje.
igual([puntajeBusqueda('cortada', 'Cortada'), puntajeBusqueda('cortada', 'Cortada M'), puntajeBusqueda('cortada', 'Short cortada'),
  puntajeBusqueda('cortada', 'Recortada'), puntajeBusqueda('cortada', 'Entera')], [100, 80, 60, 40, 0], 'puntajes: exacto, empieza, arranca una palabra, adentro, nada')

// 7) Configuración › Moldería busca por el molde o por sus variables (`cual` dice cuál coincidió).
{
  const moldes = [{ nombre: 'Camiseta de futbol', variables: ['Cuello redondo', 'Cortada'] }, { nombre: 'Musculosa', variables: ['Lisa'] }, { nombre: 'Cortada', variables: ['Única'] }]
  const r = filtrarBusqueda('cortada', moldes, (m) => [m.nombre, ...m.variables])
  igual(r.map((x) => [x.item.nombre, x.cual]), [['Cortada', 0], ['Camiseta de futbol', 2]], 'Moldería: primero el molde que se llama así, después el que tiene esa variable')
}

// 8) Códigos de variable repetidos entre moldes (lo que dejaba tarjetas pegadas).
igual(clavesRepetidas([
  { clave: 'v_a', moldeId: 'm1', moldeNombre: 'Uno', label: 'Entera' }, { clave: 'v_b', moldeId: 'm1', moldeNombre: 'Uno', label: 'Otra' },
  { clave: 'v_a', moldeId: 'm2', moldeNombre: 'Dos', label: 'Lisa' }, { clave: 'v_c', moldeId: 'm2', moldeNombre: 'Dos', label: 'Más' },
]).map((x) => [x.clave, x.variables.map((v) => v.moldeNombre)]), [['v_a', ['Uno', 'Dos']]], 'clavesRepetidas: sólo el código que está en dos moldes')

// 9) La pantalla: cada tarjeta de variable tiene una `key` que no se repite entre moldes, y el buscador
//    del pedido mira variable y molde por separado.
{
  const app = readFileSync(new URL('./src/App.jsx', import.meta.url), 'utf8')
  ok(!/key=\{v\.clave\} type="button"/.test(app), 'App.jsx: ninguna tarjeta de variable del pedido usa `key={v.clave}` (dos moldes con el mismo código dejan tarjetas pegadas)')
  ok(/_k: `\$\{p\.id\}\|\$\{i\}`/.test(app), 'App.jsx: `variablesDisponibles` le pone `_k` (molde + lugar) a cada variable')
  ok(app.includes('filtrarBusqueda(buscarVariable, varsCatalogo, v => [v.label, v.moldeNombre])'), 'App.jsx: el buscador del pedido mira [variable, molde], sin el texto pegado «molde variable»')
  ok(!/function (puntajeBusqueda|filtrarBusqueda)\(/.test(app), 'App.jsx: las reglas del buscador viven sólo en buscador.js')
}

if (fallas) { console.error(`\nverificar_buscador: ${fallas} falla(s)`); process.exit(1) }
console.log('verificar_buscador: OK')
