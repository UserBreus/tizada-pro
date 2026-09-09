// CONTRATO DE LOS PASOS DEL PEDIDO — `node verificar_pasos_pedido.mjs` (corre en el build).
//
// La barra de abajo del pedido es la que dice QUÉ FALTA para poder fabricar. Lo que no figura ahí
// no existe para el usuario: se entera cuando la tela ya está cortada.
//
// 🔴 EL MOLDE CON EL DISEÑO ADENTRO (camino B) no lleva arte: sus dos tareas son **nombrar las
// piezas** y **ubicar la etiqueta**. Antes iban escondidas adentro del paso «Asignar arte» —que
// para el camino B decía «faltan nombrar las piezas»— y la etiqueta no figuraba en ningún lado
// (pedido del usuario 2026-09-09). Acá se cuida que sigan siendo pasos propios.
//
// Y que al pasar del diseño al paso Arte **no** se entre solo a la herramienta de nombrar: eso te
// sacaba del pedido sin pedirte permiso y perdías de vista el visor y los talles.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const APP = fs.readFileSync(path.join(AQUI, 'src', 'App.jsx'), 'utf8');
const fallos = [];
const ok = (cond, que) => {
  console.log((cond ? '  OK    ' : '  FALLA ') + que);
  if (!cond) fallos.push(que);
};

console.log('CONTRATO DE LOS PASOS DEL PEDIDO\n');

console.log('1) El molde con diseño tiene SUS pasos en la barra de abajo');
const memo = APP.slice(APP.indexOf('const pasoItems = React.useMemo'),
                       APP.indexOf('const removeFila'));
ok(memo.includes("corto: 'Nombrar piezas'"), '«Nombrar piezas» es un paso propio');
ok(memo.includes("corto: 'Ubicar etiqueta'"), '«Ubicar etiqueta» es un paso propio');
ok(/id: 'nombresB'[\s\S]{0,400}hecho: _sinNomB\.length === 0/.test(memo),
   'nombrar TRABA mientras falte alguna pieza por nombrar');
// ⚠️ Ubicar la etiqueta NO puede trabar: una pieza sin marcar NO sale sin etiqueta, sale con la
// etiqueta CENTRADA ABAJO. Exigir el 100 % frenaría pedidos que están perfectos.
ok(/id: 'etiquetaB'[\s\S]{0,400}aviso: true/.test(memo),
   '🔴 ubicar la etiqueta AVISA pero NO traba (sin marcar sale centrada abajo)');
ok(memo.includes('_etiquetasSinUbicar('), 'y dice cuántas piezas faltan, no sólo que falta algo');

console.log('\n2) El arte sigue siendo un paso, pero sólo para los moldes que lo llevan');
ok(memo.includes('const _itB = itemsPedido.filter(x => _esConDiseno(x.moldeId))')
   && memo.includes('const _itA = itemsPedido.filter(x => !_esConDiseno(x.moldeId))'),
   'los moldes con diseño y los de arte se cuentan por separado');
ok(!/faltan: itemsSinArte\.map\(x => _esConDiseno/.test(memo),
   'el paso del arte ya no habla de nombrar piezas (eso es su propio paso)');

console.log('\n3) 🔴 Del diseño NO se entra solo a nombrar');
const ir = APP.slice(APP.indexOf('const irANombrarB'), APP.indexOf('const irANombrarB') + 1600);
ok(ir.includes("setPedidoPaso('arte')"), 'el botón lleva al paso Arte');
ok(!ir.includes('abrirNombrarB('),
   'y NO abre solo la herramienta de nombrar (se entra con su botón)');
ok(APP.includes('texto="Al arte"'), 'el botón dice a dónde lleva de verdad');

console.log('\n4) Los contadores que miran los pasos hacen recalcular la barra');
// Sin esto, nombrabas todas las piezas y el paso seguía en rojo hasta cambiar de pantalla: los
// contadores cambian sin que cambie ningún id, y la firma vieja eran sólo los ids.
ok(APP.includes('const _avanceCat = React.useMemo'), 'hay una firma con el AVANCE de cada molde');
ok(/\}, \[pedidoPaso[^\]]*_avanceCat/.test(APP), 'y la barra depende de ella');

console.log('\n5) 🔴 El aviso de «ya configuraste este molde» sale DONDE se trabaja el molde');
// Pedido del usuario 2026-09-09: el aviso vivía sólo en Moldería y el panel del pedido apenas
// decía «hay una» en un botón. Tiene que salir acá, y desde acá elegirse.
ok(APP.includes('data-tour="pieza-b-sugerida"'), 'el cartel está en el panel del visor del pedido');
ok(APP.includes('data-tour="pieza-b-sugerida-aplicar"'), 'y se aplica desde ahí');
ok(/pieza-b-sugerida[\s\S]{0,1800}Elegir otra/.test(APP), 'y se puede elegir OTRA de las guardadas');
// 🔴 POR MOLDE: el panel del pedido y Moldería miran moldes DISTINTOS. Con una sola sugerencia,
// la del pedido mostraba la del molde abierto en Configuración (o ninguna).
ok(APP.includes('const [cfgSugeridas, setCfgSugeridas]'), 'la sugerencia se guarda POR MOLDE');
ok(APP.includes('cfgSugeridas[_id]') && APP.includes('cfgSugeridas[pidCfg]'),
   'cada pantalla mira la de SU molde');
ok(/aplicarCfgMolde\(cfgSugeridas\[_id\], _id\)/.test(APP),
   'y aplicar recibe el molde por argumento (no por estado, que React no tiene actualizado)');

console.log();
if (fallos.length) {
  console.log(`✗ CONTRATO ROTO — ${fallos.length} falla(s):`);
  fallos.forEach(f => console.log('   ·', f));
  process.exit(1);
}
console.log('✓ CONTRATO VERDE — el pedido muestra lo que falta y no te saca de la pantalla');
