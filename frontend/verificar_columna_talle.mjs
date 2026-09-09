// CONTRATO: CADA MOLDE LEE SU COLUMNA DE TALLE — `node verificar_columna_talle.mjs` (va en el build).
//
// Un pedido puede llevar UN diseño con DOS moldes —camiseta y short— y una planilla con DOS
// columnas de talle («Talle» y «Talle short»). Cada molde toma el suyo de una. Equivocarse acá NO
// da error: da una prenda del tamaño que no es, ya impresa y cortada.
//
// 🔴 Y lo pone EL CLIENTE, de un toque, en la tarjeta del molde (pedido del usuario 2026-09-09:
// «que lo ponga el cliente pero de una forma fácil, sin ir a un espacio extra»). El sistema NO
// adivina: nada de deducir por el nombre del archivo ni por los talles. Este contrato también
// cuida eso, porque una heurística metida después convertiría una decisión de la persona en una
// suposición del programa, y una suposición mal hecha sale impresa.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = fs.readFileSync(path.join(AQUI, 'src', 'App.jsx'), 'utf8');
const DIC = fs.readFileSync(path.join(AQUI, 'src', 'diccionario.js'), 'utf8');
const fallos = [];
const ok = (cond, que) => {
  console.log((cond ? '  OK    ' : '  FALLA ') + que);
  if (!cond) fallos.push(que);
};

console.log('CONTRATO DE LA COLUMNA DE TALLE POR MOLDE\n');

console.log('1) Un solo lugar decide de qué columna toma el talle cada molde');
ok(APP.includes('const colDeMolde'), 'hay un resolutor único (`colDeMolde`)');
ok(/mapeo_columnas \|\| \{\}\)\.talle/.test(APP), 'y sale del `mapeo_columnas` del molde');
ok(APP.includes('const colsTalle = React.useMemo'),
   'las columnas de talle salen de la planilla del pedido, no del molde activo');
ok(/plantillaComun/.test(APP.slice(APP.indexOf('const colsTalle = React.useMemo'),
                                   APP.indexOf('const colsTalle = React.useMemo') + 400)),
   'las toma de `plantillaComun` (en el espacio de carga todavía no hay molde activo)');

console.log('\n2) Cada columna de talle ofrece SOLO los talles de sus moldes');
// Antes las dos columnas ofrecían la unión de todos: se podía cargar un short en un talle que no
// existe, y el error recién aparecía con la tizada armada.
ok(APP.includes('const tallesDeColumna'), 'hay una lista de talles POR COLUMNA');
const tdc = APP.slice(APP.indexOf('const tallesDeColumna'), APP.indexOf('const _disenosParaFila'));
ok(/colDeMolde\(mid\) !== colId/.test(tdc), 'junta sólo los moldes que leen esa columna');
ok(/colsTalle\.length <= 1/.test(tdc), 'y con UNA sola columna no cambia nada de lo de antes');
ok(!/c\.role === 'talle'.{0,80}\btallesDelPedido\b/s.test(APP),
   '🔴 ninguna columna de talle ofrece ya la unión de todos los moldes');

console.log('\n3) El diseño de una fila se juzga con la columna de CADA molde');
const dpf = APP.slice(APP.indexOf('const _disenosParaFila'), APP.indexOf('const _disenosParaFila') + 900);
ok(/fila \|\| \{\}\)\[colDeMolde\(mid\)\]/.test(dpf),
   'cada molde se mira con SU columna, no con la primera de la planilla');
ok(/if \(!v\) return true;/.test(dpf), 'una celda vacía no descarta ningún diseño');

console.log('\n4) El gesto: un toque en la tarjeta del molde, sin ir a otra pantalla');
ok(APP.includes('function SelectorColumnaTalle'), 'hay un control único (`SelectorColumnaTalle`)');
const sel = APP.slice(APP.indexOf('function SelectorColumnaTalle'),
                      APP.indexOf('// APOYAR LA ETIQUETA EN EL CONTORNO'));
ok(/colsTalle\.length <= 1\) return null/.test(sel),
   'con una sola columna no se dibuja (cero ruido en el pedido normal)');
ok(/e\.stopPropagation\(\)/.test(sel), 'tocar una pastilla no tilda ni destilda la tarjeta');
ok((APP.match(/<SelectorColumnaTalle/g) || []).length >= 2,
   'está montado en las DOS tarjetas: el espacio de carga y «Mis artículos»');
ok(APP.includes("ancla=\"cargar-b-columna\"") && APP.includes("ancla=\"molde-columna-talle\""),
   'y cada una con su ancla de ayuda');
ok(/'molde-columna-talle':/.test(DIC), 'el ancla nueva tiene su ficha en el diccionario');

console.log('\n5) No se puede seguir sin decirlo (el default del alta no es una decisión)');
// Todo molde nace con `talle: "talle"`: sin una marca explícita no hay forma de distinguir «eligió
// Talle» de «nadie tocó nada», y era eso lo que sacaba el short con el talle de la camiseta.
ok(/talle_elegido: true/.test(APP), 'al elegir se deja la marca `talle_elegido`');
ok(/const _faltaCol = colsTalle\.length > 1|_colsTalle\.length > 1\s*\n?\s*&& _mios\.some/.test(APP),
   'la pantalla sabe a qué molde le falta');
ok(/Falta decir de qué columna toma el talle cada molde/.test(APP),
   'la barra de abajo lo dice con todas las letras');
ok(/disabled=\{!_mios\.length \|\| _faltaDis \|\| _faltaCol\}/.test(APP),
   '🔴 y «Al arte» queda apagado hasta que estén todos');

console.log('\n6) El sistema NO adivina: lo pone el cliente');
// Pedido explícito del usuario. Una heurística por nombre de archivo o por los talles convertiría
// su decisión en una suposición del programa — y las suposiciones acá salen impresas.
const _icdm = APP.indexOf('const colDeMolde');
const cdm = APP.slice(_icdm, APP.indexOf('};', _icdm) + 2);
ok(!/nombre|talles|includes\('/.test(cdm),
   '`colDeMolde` sólo lee lo que el cliente eligió (ni el nombre del archivo ni los talles)');
ok(!/nombre|\.talles/.test(sel),
   'el control tampoco mira el nombre del molde para pre-elegir una columna');
ok(!/_deducirColumnaTalle|_sugerirColumnaTalle/.test(APP),
   'y no hay ninguna función que la deduzca sola');

console.log();
if (fallos.length) {
  console.log(`✗ CONTRATO ROTO — ${fallos.length} falla(s):`);
  fallos.forEach(f => console.log('   ·', f));
  process.exit(1);
}
console.log('✓ CONTRATO VERDE — cada molde toma el talle de la columna que le dijo el cliente');
