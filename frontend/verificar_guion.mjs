/**
 * CONTRATO DEL GUION — `node verificar_guion.mjs` (corre solo en cada `npm run build`).
 *
 * Verifica lo que el usuario pidió con estas palabras: *«hay cosas que son obvias, como elegir el
 * diseño antes del molde. Cargué 2 diseños pero en el tutorial, como puse 1 solo, obvio que no
 * presioné en el diseño porque no era necesario; después en la ayuda no me mandó a eso. Leé los
 * pasos coherentes y hacé que se pongan automático.»*
 *
 * O sea: una grabación sólo tiene lo que la persona LLEGÓ A HACER. Lo que ya tenía resuelto no
 * quedó grabado, y el tutorial salía con agujeros. `aGuion` completa esas etapas con la SECUENCIA
 * del pedido, y cada una trae su `listo` para que a quien ya la tenga NO se le muestre.
 *
 * Se ejecuta el código de verdad (`src/guion.js` es JS puro, sin React, justamente para esto).
 */
import { readFileSync } from 'node:fs';
import { aGuion, pasoSuperado, queAtender } from './src/guion.js';
import { SECUENCIA } from './src/diccionario.js';

const fallas = [];
const ok = (c, m) => { console.log((c ? '  OK    ' : '  FALLA ') + m); if (!c) fallas.push(m); };
// el ancla de un paso puede venir AFINADA («txt:camiseta#pedido-variables» = ese botón, dentro de
// esa sección). Para medir la SECUENCIA importa la sección, que es la identidad semántica.
const anclas = (g) => g.pasos.map((p) => p.seccion || p.ancla);

// El estado que arma App.jsx. `VACIO` = pedido recién empezado.
const VACIO = { cargado: true, nMoldes: 3,
  pedido: { nDisenos: 0, sinVariable: 0, artesTotal: 0, artesCargadas: 0, telasFaltan: 0,
            nFilas: 0, hayResultados: false, editorAbierto: false, nEditables: 0, fuentesFaltan: 0 } };
const CON_DISENO = { ...VACIO, pedido: { ...VACIO.pedido, nDisenos: 2 } };

console.log('\n1 · EL CASO DEL USUARIO: grabó el paso del MOLDE, no el del diseño');
const grabado = { id: 't1', nombre: 'Cargar un pedido', pasos: [
  { ancla: 'pedido-variables', accion: 'click', etiqueta: 'Camiseta', donde: { tab: 'pedidos', paso: 'moldes' } },
] };
const g1 = aGuion(grabado);
ok(anclas(g1).includes('pedido-diseno-lista'),
   'el tutorial ahora SÍ manda a elegir el diseño, aunque no se haya grabado');
ok(anclas(g1).indexOf('pedido-diseno-lista') < anclas(g1).indexOf('pedido-variables'),
   '…y ANTES del molde, que es el orden real del trabajo');

console.log('\n2 · lo agregado se saltea solo a quien ya lo tiene hecho');
const pDiseno = g1.pasos.find((p) => p.ancla === 'pedido-diseno-lista');
ok(typeof pDiseno.hecho === 'function', 'el paso agregado trae su condición');
ok(pDiseno.hecho(VACIO) === false, 'con el pedido vacío, se pide');
ok(pDiseno.hecho(CON_DISENO) === true, 'con el diseño ya cargado, se saltea');

console.log('\n3 · no se duplica lo que la grabación YA tiene');
const g2 = aGuion({ id: 't2', nombre: 'x', pasos: [
  { ancla: 'pedido-diseno-lista', accion: 'click', donde: { tab: 'pedidos', paso: 'diseno' } },
  { ancla: 'pedido-variables', accion: 'click', donde: { tab: 'pedidos', paso: 'moldes' } },
] });
ok(anclas(g2).filter((a) => a === 'pedido-diseno-lista').length === 1,
   'el diseño aparece UNA sola vez');
ok(anclas(g2).join() === 'pedido-diseno-lista,pedido-variables', 'y no se agregó nada de más');

console.log('\n4 · una grabación que arranca al final trae TODA la cadena');
const g3 = aGuion({ id: 't3', nombre: 'x', pasos: [
  { ancla: 'planilla-enviar', accion: 'click', donde: { tab: 'pedidos', paso: 'resultados' } },
] });
const esperado = SECUENCIA.map((e) => e.ancla);
ok(anclas(g3).join() === esperado.join(),
   `la cadena completa y en orden: ${anclas(g3).join(' → ')}`);

console.log('\n5 · un tutorial que no es del pedido no se toca');
const g4 = aGuion({ id: 't4', nombre: 'x', pasos: [
  { ancla: 'cfg-telas', accion: 'click', donde: { tab: 'config', sub: 'dashboard' } },
  { ancla: 'telas-lista', accion: 'click', donde: { tab: 'config', sub: 'telas' } },
] });
ok(anclas(g4).join() === 'cfg-telas,telas-lista',
   'nada de la secuencia del pedido se cuela en un tutorial de Configuración');

console.log('\n6 · cada paso sale con las palabras del diccionario');
ok(g1.pasos.every((p) => p.texto && p.texto.length > 3), 'todos los pasos tienen su cartel');
ok(g1.pasos.some((p) => p.nota), 'y la explicación de para qué es');

console.log('\n8 · ARRANCA DESDE DONDE ESTÁ: lo ya dado no se muestra ni arrastra para atrás');
// La persona abre el tutorial con el trabajo empezado. Un paso de una etapa ANTERIOR ya cumplida
// se saltea; uno de una etapa a medias NO (el tutorial la lleva a terminarla).
const HECHO_TODO = { cargado: true, nMoldes: 3, pedido: { nDisenos: 1, sinVariable: 0,
  artesTotal: 1, artesCargadas: 1, telasFaltan: 0, nFilas: 0, hayResultados: false,
  editorAbierto: false, nEditables: 0, fuentesFaltan: 0, activoConVariable: true, activoArteCargado: true } };
const pDis = { ancla: 'pedido-diseno-lista', accion: 'click', ir: { tab: 'pedidos', paso: 'diseno' } };
const pMol = { ancla: 'pedido-variables', accion: 'click', ir: { tab: 'pedidos', paso: 'moldes' } };
const pIrM = { ancla: 'pedido-ir-moldes', accion: 'click', ir: { tab: 'pedidos', paso: 'diseno' } };
const EN_PLANILLA = { tab: 'pedidos', paso: 'planilla' };
ok(pasoSuperado(pDis, HECHO_TODO, EN_PLANILLA) === true,
   '🔴 parado en la planilla con el diseño ya elegido, ese paso queda atrás');
ok(pasoSuperado(pIrM, HECHO_TODO, EN_PLANILLA) === true,
   'un CLIC grabado de una etapa anterior (ir a moldes) también queda atrás');
ok(pasoSuperado(pMol, HECHO_TODO, EN_PLANILLA) === true,
   'la prenda ya elegida queda atrás');
// la red: la etapa anterior A MEDIAS no se saltea — hay que volver a terminarla
const FALTAN_TELAS = { ...HECHO_TODO, pedido: { ...HECHO_TODO.pedido, telasFaltan: 3 } };
const pTel = { ancla: 'arte-telas', accion: 'click', ir: { tab: 'pedidos', paso: 'arte' } };
ok(pasoSuperado(pTel, FALTAN_TELAS, EN_PLANILLA) === false,
   '🔴 con telas faltando, el paso del arte NO se saltea aunque esté parado en la planilla');
const SIN_PRENDA = { ...HECHO_TODO, pedido: { ...HECHO_TODO.pedido, sinVariable: 1 } };
ok(pasoSuperado(pMol, SIN_PRENDA, EN_PLANILLA) === false,
   'con un diseño sin prenda, tampoco');
// parado EN la misma etapa, el paso se muestra (capaz quiere agregar otro diseño)
ok(pasoSuperado(pDis, HECHO_TODO, { tab: 'pedidos', paso: 'diseno' }) === false,
   'parado EN esa etapa, el paso se muestra (no es anterior)');
// fuera del pedido, nada se saltea por posición
ok(pasoSuperado({ ancla: 'cfg-telas', accion: 'click', ir: { tab: 'config', sub: 'telas' } },
                HECHO_TODO, EN_PLANILLA) === false,
   'un paso de Configuración no entra en esta regla');
ok(pasoSuperado(pDis, HECHO_TODO, { tab: 'config', sub: 'dashboard' }) === false,
   'parado fuera de Pedidos, tampoco se saltea nada');

console.log('\n10 · EL ORDEN: lo completado entra ANTES del botón «siguiente», nunca después');
// El bug real (2026-08-28): grabó sin tocar las telas (ya estaban). Al completar, la etapa de
// telas se insertaba DESPUÉS de «A la planilla» — y su `ir` te arrastraba de la planilla al arte:
// «me manda a hacer un paso después que era antes».
const go = aGuion({ id: 'to', nombre: 'x', pasos: [
  { ancla: 'pedido-diseno-lista', accion: 'click', donde: { tab: 'pedidos', paso: 'diseno' } },
  { ancla: 'pedido-variables', accion: 'click', donde: { tab: 'pedidos', paso: 'moldes' } },
  { ancla: 'arte-cargar', accion: 'click', donde: { tab: 'pedidos', paso: 'arte' } },
  { ancla: 'arte-siguiente', accion: 'click', donde: { tab: 'pedidos', paso: 'arte' } },
  { ancla: 'planilla-tabla', accion: 'input', donde: { tab: 'pedidos', paso: 'planilla' } },
] });
const AO = anclas(go);
ok(AO.includes('arte-telas'), 'la etapa de telas (no grabada) se completa igual');
ok(AO.indexOf('arte-telas') < AO.indexOf('arte-siguiente'),
   '🔴 y queda ANTES de «A la planilla», no después (era el bug del arrastre para atrás)');
ok(AO.indexOf('arte-cargar') < AO.indexOf('arte-telas'),
   'el orden interno del arte se respeta: cargar y después telas');

console.log('\n11 · LOS CAMPOS DEL EDITOR llegan al guion');
const ge = aGuion({ id: 'te', nombre: 'x', pasos: [
  { ancla: 'pedido-diseno-lista', accion: 'click', donde: { tab: 'pedidos', paso: 'diseno' },
    texto: 'Cartel corregido a mano' },
  { accion: 'modal', modal: 'Perfil de color del diseño', donde: { tab: 'pedidos', paso: 'arte' } },
] });
const e1 = ge.pasos.find((p) => p.ancla === 'pedido-diseno-lista');
ok(e1.texto === 'Cartel corregido a mano', 'el cartel corregido a mano le gana al diccionario');
const e2 = ge.pasos.find((p) => p.accion === 'modalPaso');
ok(!!e2 && e2.modal === 'Perfil de color del diseño',
   'el paso «esperar aviso» se convierte en una espera con su título');
ok(!!e2.texto && e2.texto.includes('Perfil de color'),
   '…y su cartel dice qué aviso va a aparecer');

// ── una VENTANA DE TRABAJO puesta en la línea («Se está armando la tizada») no se responde: se
// espera. Decirle «respondé lo que pide» manda al usuario a buscar un botón que no existe.
ok((() => {
  const gt = aGuion({ id: 'tt', nombre: 'x', pasos: [
    { accion: 'modal', modal: 'Se está poniendo el diseño sobre el molde.', donde: {} },
    { accion: 'modal', modal: 'Perfil de color del diseño', donde: {} },
  ] });
  const trabajo = gt.pasos.find((p) => p.modal === 'Se está poniendo el diseño sobre el molde.');
  const aviso = gt.pasos.find((p) => p.modal === 'Perfil de color del diseño');
  return !!trabajo && trabajo.esTrabajo === true && /esper/i.test(trabajo.texto)
    && !/respond/i.test(trabajo.texto)
    && !!aviso && !aviso.esTrabajo && /respond/i.test(aviso.texto);
})(), '🔴 la ventana de TRABAJO pide ESPERAR; la de aviso, responder');

// ── el paso que vive DENTRO de una ventana emergente (2026-08-28: «este paso se hace en una
// ventana emergente y no la veo a la ventana»): `ventana` tiene que VIAJAR al guion — sin eso
// ni el editor la dibuja ni la reproducción sabe explicarla.
ok((() => {
  const gv2 = aGuion({ id: 'tw', nombre: 'x', pasos: [
    { ancla: 'txt:entendido', accion: 'click', ventana: 'Perfil de color del diseño',
      donde: { tab: 'pedidos', paso: 'arte' } },
  ] });
  const pw = gv2.pasos.find((p) => p.ancla === 'txt:entendido');
  return !!pw && pw.ventana === 'Perfil de color del diseño';
})(), '🔴 el paso grabado dentro de una ventana conserva `ventana` en el guion');

// 🔴 Lo que es del GRABADOR no es un paso del trabajo (2026-08-31: «el botón de parar y guardar
// para terminar el tutorial no saldrá en el tutorial: eso es del grabador»).
{
  const ga = aGuion({ id: 'ta', nombre: 'x', pasos: [
    { ancla: 'pedido-diseno-lista', accion: 'click', etiqueta: 'JUGADOR', donde: { tab: 'pedidos', paso: 'diseno' } },
    { ancla: 'txt:parar y guardar', accion: 'click', etiqueta: 'Parar y guardar', donde: { tab: 'pedidos', paso: 'diseno' } },
  ] });
  ok(!ga.pasos.some((p) => /parar y guardar/i.test(p.ancla || '')),
     '🔴 el «Parar y guardar» del grabador NO queda como paso del tutorial');
  ok(ga.pasos.some((p) => (p.seccion || p.ancla) === 'pedido-diseno-lista'), 'y lo demás del tutorial queda');
}

console.log('\n10a · OPCIONES INTERCAMBIABLES: «elegí 2», no «tocá estos 2»');
// 🔴 EL CASO DEL USUARIO (2026-08-31): «cuando tengo un modal con varias opciones —ejemplo,
// diseño— yo grabo presionando 2 botones random, pero quien pide ayuda puede elegir otros 2».
{
  const go2 = aGuion({ id: 'to2', nombre: 'x', pasos: [
    { ancla: 'pedido-diseno-lista', accion: 'click', etiqueta: 'JUGADOR', donde: { tab: 'pedidos', paso: 'diseno' } },
    { ancla: 'pedido-diseno-lista', accion: 'click', etiqueta: 'GOLERO', donde: { tab: 'pedidos', paso: 'diseno' } },
    { ancla: 'pedido-ir-moldes', accion: 'click', donde: { tab: 'pedidos', paso: 'diseno' } },
  ] });
  const pOpc = go2.pasos.filter((p) => p.ancla === 'pedido-diseno-lista');
  ok(pOpc.length === 1, `🔴 los dos clics en la lista son UN paso (son ${pOpc.length})`);
  ok(pOpc[0] && pOpc[0].cuantas === 2, 'que pide DOS opciones');
  ok(pOpc[0] && /elegí 2/i.test(pOpc[0].texto), `y lo dice así: «${pOpc[0] && pOpc[0].texto}»`);
  ok(pOpc[0] && !pOpc[0].ancla.includes('#'),
     'marca LA LISTA, no el botón que tocó quien grabó (JUGADOR)');
  ok(go2.pasos.some((p) => p.ancla === 'pedido-ir-moldes'), 'el resto del tutorial sigue igual');

  // 🔴 UN SOLO CLIC EN UNA LISTA TAMPOCO ATA AL TUTORIAL A ESA TARJETA (2026-08-31: «en el paso de
  // elegir molde también es multiopción; no debe ir a uno directo»).
  const g1c = aGuion({ id: 't1c', nombre: 'x', pasos: [
    { ancla: 'pedido-variables', accion: 'click', etiqueta: 'Cuello redondo',
      donde: { tab: 'pedidos', paso: 'moldes' } },
  ] });
  const pM = g1c.pasos.find((p) => (p.seccion || p.ancla) === 'pedido-variables');
  ok(pM && pM.ancla === 'pedido-variables',
     `🔴 marca LA LISTA de prendas, no «Cuello redondo» (${pM && pM.ancla})`);
  ok(pM && !/cuello redondo/i.test(pM.texto || ''),
     `y el cartel no nombra la prenda que tocó quien grabó: «${pM && pM.texto}»`);

  // 🔴 Y dos clics seguidos EN EL MISMO LUGAR no son dos pasos (se vio en «2 colores»: escribió en
  // dos filas de la misma columna y el tutorial repetía el cartel).
  const grep = aGuion({ id: 'trep', nombre: 'x', pasos: [
    { ancla: 'col:nombre', accion: 'click', donde: { tab: 'pedidos', paso: 'planilla' } },
    { ancla: 'col:nombre', accion: 'click', donde: { tab: 'pedidos', paso: 'planilla' } },
    { ancla: 'col:numero', accion: 'click', donde: { tab: 'pedidos', paso: 'planilla' } },
  ] });
  ok(grep.pasos.filter((p) => p.ancla === 'col:nombre').length === 1,
     '🔴 dos clics seguidos en la misma columna son UN paso');
  ok(grep.pasos.some((p) => p.ancla === 'col:numero'), 'y la columna siguiente sigue estando');
  // dos «esperar aviso» seguidos NO son duplicados: son dos ventanas distintas
  const gav = aGuion({ id: 'tav', nombre: 'x', pasos: [
    { accion: 'modal', modal: 'Perfil de color del diseño', donde: {} },
    { accion: 'modal', modal: 'Tipografía no encontrada', donde: {} },
  ] });
  ok(gav.pasos.filter((p) => p.accion === 'modalPaso').length === 2,
     'dos ventanas distintas seguidas siguen siendo dos pasos');

  // …pero dos botones que NO son opciones equivalentes siguen siendo dos pasos (entrada 358)
  const gn = aGuion({ id: 'tn', nombre: 'x', pasos: [
    { ancla: 'resultados-mesas', accion: 'click', etiqueta: 'Descargar sólo la hoja 1', donde: { tab: 'pedidos', paso: 'resultados' } },
    { ancla: 'resultados-mesas', accion: 'click', etiqueta: 'Descargar la ficha técnica', donde: { tab: 'pedidos', paso: 'resultados' } },
  ] });
  ok(gn.pasos.filter((p) => (p.seccion || p.ancla) === 'resultados-mesas').length === 2,
     '🔴 dos botones de acciones DISTINTAS no se juntan (no son intercambiables)');
}

console.log('\n10b · DOS BOTONES DE LA MISMA VENTANA SON DOS PASOS DISTINTOS');
// 🔴 EL CASO DEL USUARIO (2026-08-31): «si en un modal presiono 2 botones, el tutorial tiene que
// esperar a que presione los 2». En su tutorial los pasos 21 y 22 eran los DOS `resultados-mesas`
// —«Descargar sólo la hoja 1» y «Descargar la ficha técnica»—: el grabador se quedaba con el
// `data-tour` del PANEL y perdía cuál botón era, así que el tutorial marcaba el panel entero y no
// podía distinguirlos. Ahora el ancla lleva el botón Y su sección.
{
  const gd = aGuion({ id: 'td', nombre: 'x', pasos: [
    { ancla: 'resultados-mesas', accion: 'click', etiqueta: 'Descargar sólo la hoja 1',
      donde: { tab: 'pedidos', paso: 'resultados' } },
    { ancla: 'resultados-mesas', accion: 'click', etiqueta: 'Descargar la ficha técnica completa',
      donde: { tab: 'pedidos', paso: 'resultados' } },
  ] });
  const dos = gd.pasos.filter((p) => (p.seccion || p.ancla) === 'resultados-mesas');
  ok(dos.length === 2, 'los dos pasos siguen siendo dos');
  ok(dos[0].ancla !== dos[1].ancla,
     `🔴 y ahora son DISTINTOS (${dos[0].ancla} ≠ ${dos[1].ancla})`);
  ok(dos.every((p) => p.ancla.startsWith('txt:') && p.ancla.endsWith('#resultados-mesas')),
     'cada uno es «ese botón, dentro de esa sección»');
  ok(dos.every((p) => p.seccion === 'resultados-mesas'),
     'y se recuerda de qué sección salieron (para la secuencia y para el fallback)');
  // un paso cuyo texto ES el del elemento marcado no se afina (sería redundante)
  const gs = aGuion({ id: 'ts2', nombre: 'x', pasos: [
    { ancla: 'planilla-enviar', accion: 'click', etiqueta: 'Enviar el pedido',
      donde: { tab: 'pedidos', paso: 'planilla' } },
  ] });
  ok(gs.pasos.some((p) => p.ancla === 'planilla-enviar'),
     'un botón que YA está marcado a mano se queda con su marca');
}

console.log('\n11a · CON DOS COSAS ENCIMA, MANDA LA DE ADELANTE');
// 🔴 EL CASO DEL USUARIO (2026-08-31): el modal «Perfil de color del diseño» abierto ENCIMA de la
// carga «Se está poniendo el diseño sobre el molde». El tutorial pedía esperar la carga —que está
// tapada— en vez de mandar a cerrar la ventana de adelante, que se cierra con «Entendido» y ya es
// un paso del tutorial.
ok(queAtender({ modalTapando: true, hayCarga: true, cargaEsDelPaso: false }) === 'modal',
   '🔴 modal ENCIMA de una carga → primero el modal');
ok(queAtender({ modalTapando: false, hayCarga: true, cargaEsDelPaso: false }) === 'carga',
   'cerrado el modal, si la carga sigue → la espera');
ok(queAtender({ modalTapando: false, hayCarga: false, cargaEsDelPaso: false }) === 'paso',
   'sin nada encima → el paso normal');
ok(queAtender({ modalTapando: false, hayCarga: true, cargaEsDelPaso: true }) === 'paso',
   'un paso que ESPERA esa carga la muestra él mismo (no la tapa una espera genérica)');
ok(queAtender({ modalTapando: true, hayCarga: true, cargaEsDelPaso: true }) === 'modal',
   'pero si además hay un modal tapando, ése va primero igual');
// 🔴 SEGUNDA VUELTA (2026-08-31): «esa ventana tiene un botón de Entendido pero la ayuda lee un
// modal que está por detrás». El paso ES el «Entendido» de la ventana de adelante: la carga de
// atrás no puede taparlo.
ok(queAtender({ modalTapando: false, modalDelPasoAbierto: true, hayCarga: true, cargaEsDelPaso: false }) === 'paso',
   '🔴 si el modal de adelante ES donde va el paso, se atiende EL PASO (no la carga de atrás)');
ok(queAtender({ modalTapando: false, modalDelPasoAbierto: true, hayCarga: false, cargaEsDelPaso: false }) === 'paso',
   'y sin carga, igual');
ok(queAtender({ modalTapando: true, modalDelPasoAbierto: false, hayCarga: false, cargaEsDelPaso: false }) === 'modal',
   'un modal AJENO sigue frenando el tutorial');

console.log('\n11b · LA PLANILLA SE TERMINA A MANO (no la cumple el primer clic)');
// 🔴 Reporte del usuario 2026-08-31: «no me deja escribir ni elegir sobre un desplegable porque
// salta a la otra columna». Cada columna es un paso y abarca TODAS las filas: darlo por hecho con
// el primer clic hace imposible cargarla. Se termina con «Siguiente →».
{
  const gp = aGuion({ id: 'tpl', nombre: 'x', pasos: [
    { ancla: 'col:nombre', accion: 'click', donde: { tab: 'pedidos', paso: 'planilla' } },
    { ancla: 'planilla-tabla', accion: 'click', donde: { tab: 'pedidos', paso: 'planilla' } },
    { ancla: 'planilla-enviar', accion: 'click', donde: { tab: 'pedidos', paso: 'planilla' } },
    { ancla: 'arte-telas', accion: 'click', donde: { tab: 'pedidos', paso: 'arte' } },
  ] });
  const de = (a) => gp.pasos.find((p) => p.ancla === a) || {};
  ok(de('col:nombre').manual === true, '🔴 un paso de COLUMNA se termina a mano');
  ok(de('planilla-tabla').manual === true, 'y el de la planilla entera también');
  ok(!de('planilla-enviar').manual, 'pero «Enviar el pedido» es un botón: ése sí avanza al tocarlo');
  ok(!de('arte-telas').manual, 'y un paso de otra pantalla no queda manual por error');
}

console.log('\n12 · NO HAY LÓGICA DE «VARIOS DISEÑOS» (y no puede volver)');
// 🔴 DECISIÓN DEL USUARIO (2026-08-28): «si se quiere para 2 diseños se debe de grabar para 2
// diseños y listo». Se probó lo contrario durante un día —ciclo automático, marcas «↻», pasos
// pintados, condiciones por cantidad— y el resultado era impredecible para quien seguía el
// tutorial. Un tutorial es lo que se grabó, en el orden en que se grabó.
{
  const src = readFileSync(new URL('./src/guion.js', import.meta.url), 'utf8');
  const PROHIBIDO = ['vistaReal', 'bloquesPorDiseno', 'etapaIncompleta', 'conAntes',
                     'vuelta2', '.bucle', 'p.repite', 'minDisenos'];
  for (const t of PROHIBIDO) ok(!src.includes(t), `guion.js no vuelve a tener «${t}»`);

  // y en los hechos: un tutorial grabado con marcas viejas se reproduce PLANO, sin repetir nada
  const viejo = aGuion({ id: 'tv', nombre: 'x', pasos: [
    { ancla: 'pedido-diseno-lista', accion: 'click', donde: { tab: 'pedidos', paso: 'diseno' } },
    { ancla: 'pedido-variables', accion: 'click', repite: ['mX'], solo: { minDisenos: 2 },
      donde: { tab: 'pedidos', paso: 'moldes' } },
    { accion: 'vuelta', mid: 'mX', donde: { tab: 'pedidos', paso: 'moldes' } },
  ] });
  ok(!viejo.pasos.some((p) => p.accion === 'vuelta'), 'una marca «↻» vieja ya no genera un paso');
  ok(!viejo.pasos.some((p) => p.repite || p.solo || p.bucle || p.etapas),
     '🔴 los campos del ciclo no sobreviven: el tutorial viejo se reproduce plano');
  ok(viejo.pasos.some((p) => p.ancla === 'pedido-variables'),
     'pero sus pasos reales siguen ahí (no se pierde la grabación)');
}

console.log('\n13 · lo que no rompe');
ok(aGuion(null) === null, 'sin tutorial, null (no explota)');
ok(aGuion({ id: 'z', nombre: 'z', pasos: [] }).pasos.length === 0, 'sin pasos, guion vacío');

console.log('');
if (fallas.length) {
  console.error('✗ EL GUION NO COMPLETA LO QUE DEBE:');
  for (const f of fallas) console.error('   · ' + f);
  process.exit(1);
}
console.log('  OK: el guion completa etapas, arranca desde donde estás y no repite lo hecho');
