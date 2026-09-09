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
ok(/aplicarCfgMolde\(cfgSugeridas\[_id\], _id/.test(APP),
   'y aplicar recibe el molde por argumento (no por estado, que React no tiene actualizado)');
// El aviso aplica con lo que trae LA RECETA (`null`), no con lo que haya quedado tildado en
// una pantalla que ni siquiera está abierta.
ok(/aplicarCfgMolde\(cfgSugeridas\[_id\], _id, 0, null\)/.test(APP),
   'y desde el aviso entra lo que la receta tiene guardado');

console.log('\n6) Aplicada una vez, el cartel NO vuelve; y una receta se puede EDITAR');
// 🔴 Aplicar recarga el molde (`moldeReload`) y eso vuelve a disparar la búsqueda: sin recordar
// cuál ya se aplicó, el cartel reaparecía solo como si no hubieras hecho nada.
ok(APP.includes('const cfgAplicada = useRef({})'), 'se recuerda qué receta ya se aplicó en cada molde');
ok(/cfgAplicada\.current\[_pidAp\] = c\.id/.test(APP), 'se anota al aplicar bien');
ok(/_sirve = c => c\.id !== cfgAplicada\.current\[pid\]/.test(APP),
   'y la búsqueda ya no la ofrece (pero sí ofrecería OTRA que calce)');
// Editar la que ya está, en vez de juntar copias casi iguales.
ok(APP.includes('data-tour="molde-cfg-actualizar"'), 'cada receta guardada se puede actualizar');
ok(APP.includes('const actualizarCfgMolde'), 'con su confirmación (pisa lo que tenía)');
ok(/id: existente \? existente\.id : undefined/.test(APP), 'y el guardado manda el id de esa receta');
// ⚠️ El botón del pie pasa el EVENTO como argumento: sin envolverlo, `existente` sería el evento
// y creería que hay que pisar una receta que no existe.
ok(APP.includes('onClick={() => guardarCfgMolde()}'),
   '🔴 el botón de guardar nuevo NO le pasa el evento como si fuera una receta');

console.log('\n7) Los «aplicar ademas» quedan guardados con la receta, y se dice cuando falta guardar');
// Reporte del usuario 2026-09-09: tildo «Talle de guia» y las tarjetas no lo mostraban. Eran dos
// cosas: el servidor corria codigo viejo (no se habia reiniciado) y, ademas, la pantalla no decia
// que tildar no alcanza — queda guardado recien con «Guardar» o «Actualizar».
ok(/partes: cfgPartes/.test(APP), 'guardar manda lo que esta tildado');
ok(APP.includes('const _partesSinGuardar'), 'la pantalla sabe si eso todavia no esta en ninguna receta');
ok(APP.includes('no está guardado'), 'y lo dice con todas las letras');
ok(/c\.partes \|\| \[\]/.test(APP), 'y cada tarjeta muestra lo que se lleva');

console.log('\n8) El TALLE DE GUIA se asigna en el acto (y no miente si el guardado falla)');
// Reporte del usuario 2026-09-09: se esperaba a que el servidor devolviera el molde DIBUJADO en
// ese talle (medido: ~1 s en un molde comun, varios segundos en uno grande la primera vez) y hasta
// entonces la pantalla no cambiaba: el clic parecia no hacer nada.
const cg = APP.slice(APP.indexOf('const cambiarTalleGuia'), APP.indexOf('const guardarReferencia'));
ok(/setGuiaPend\(talleRef\)/.test(cg), 'el talle elegido manda enseguida, antes de cualquier respuesta');
ok(cg.indexOf('setGuiaPend(talleRef)') < cg.indexOf('/api/plantilla/deteccion'),
   'se marca ANTES de pedir el dibujo, no despues');
ok(!/await fetch\('\/api\/productos\/variante_guia'/.test(cg),
   'el guardado sale en paralelo: no se espera para mostrar el cambio');
ok(/_n !== guiaSeq\.current/.test(cg),
   'y si se toca otro talle, la respuesta vieja se descarta (manda el ultimo clic)');
// 🔴 La deteccion devuelve como guia la GUARDADA: si el guardado fallo y no dijeramos nada, la
// pantalla volveria sola al talle anterior y pareceria que el clic no funciono.
ok(/No se pudo guardar el/.test(cg), 'si el guardado falla, se DICE');
ok(/guiaFallo\.current === _n \? _antes : talleRef/.test(cg),
   'y el dibujo, que llega despues, no vuelve a poner un talle que no se guardo');
ok(APP.includes('dibujando'), 'mientras llega el dibujo se avisa, para que no parezca colgado');

console.log('\n9) Aplicada la configuracion, el VISOR muestra lo que entro');
// Pedido del usuario 2026-09-09. Los nombres y la etiqueta no salen de un solo lado: la deteccion
// (CACHEADA por molde y talle), `/api/productos/etiqueta`, y el lienzo con todos los talles.
// Refrescar solo uno dejaba la pantalla como estaba, como si no hubiera pasado nada.
const rv = APP.slice(APP.indexOf('const refrescarVisorMolde'), APP.indexOf('const aplicarCfgMolde'));
ok(rv.length > 100, 'hay un solo lugar que deja el visor al dia (`refrescarVisorMolde`)');
ok(/delete _talleDetCache\.current\[k\]/.test(rv), 'tira el cache de la deteccion de ESE molde');
ok(/setEmpTodasData\(null\)/.test(rv), 'y el lienzo con todos los talles se vuelve a pedir');
ok(/cargarMoldeOperario\(pid\)/.test(rv), 'relee los nombres');
ok(/api\/productos\/etiqueta/.test(rv) && /setEtiquetaConfig/.test(rv), 'y la etiqueta');
const ap = APP.slice(APP.indexOf('const aplicarCfgMolde'), APP.indexOf('const cancelarEsperaCfg'));
ok(/refrescarVisorMolde\(_pidAp\)/.test(ap), 'y aplicar lo llama con el molde que toco');

console.log('\n10) La planilla ofrece los talles de TODOS los moldes del pedido');
// Reporte del usuario 2026-09-09: con dos moldes cargados la columna Talle mostraba los de UNO
// solo (`estado.talles`, que son los del molde ACTIVO del servidor) y faltaba la mitad.
ok(APP.includes('const tallesDelPedido'), 'hay una lista con los talles de todos los moldes');
ok(/moldesUnion\.forEach\(mid => _tallesDeMolde\(mid\)/.test(APP),
   'se juntan molde por molde, sin repetir y respetando el orden de cada uno');
ok(!/c\.role === 'talle' \? \(estado\?\.talles \|\| \[\]\)/.test(APP),
   'y la columna Talle ya NO usa los del molde activo');
ok(/c\.role === 'talle'.{0,80}tallesDeColumna\(c\.id\)/s.test(APP),
   'sino los de los moldes que leen ESA columna de talle');
// …y el DISENO de una fila solo puede ser uno que tenga ESE talle en alguno de sus moldes.
ok(APP.includes('const _disenosParaFila'), 'los diseños se filtran por la fila entera');
ok(/_disenosParaFila\(fila\)/.test(APP), 'el desplegable de Diseño usa ESA FILA');
ok(/_opcionesDeCol\(c, f\)/.test(APP), 'y la validación mira la fila, no la columna sola');

console.log();
if (fallos.length) {
  console.log(`✗ CONTRATO ROTO — ${fallos.length} falla(s):`);
  fallos.forEach(f => console.log('   ·', f));
  process.exit(1);
}
console.log('✓ CONTRATO VERDE — el pedido muestra lo que falta y no te saca de la pantalla');
