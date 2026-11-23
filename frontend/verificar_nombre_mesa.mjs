// CONTRATO: EL NOMBRE DE CADA MESA — `node verificar_nombre_mesa.mjs` (va en el build).
//
// El nombre de la mesa no es un adorno: es el nombre del ARCHIVO que se descarga, el que arma el robot y el que
// lee el otro sistema («REF__Mesa 3 - Tela - Fila 3 - x5.pdf», documentacion/integracion_externa). Un comentario
// mal puesto se tragó el « - x30» de Copia y ningún contrato lo vio (inspector, MAPA 799): éste lo mira.

import { nombreMesaDef } from './src/motor/pdf/mesaPorArchivo.js';

const fallos = [];
const igual = (dado, esperado, que) => {
  const ok = dado === esperado;
  console.log((ok ? '  OK    ' : '  FALLA ') + que + (ok ? '' : `\n          dio      «${dado}»\n          esperaba «${esperado}»`));
  if (!ok) fallos.push(que);
};

console.log('CONTRATO DEL NOMBRE DE LA MESA\n');
igual(nombreMesaDef(0, 'DRY RUN', null), 'Mesa 1 - DRY RUN', 'mesa común: número y tela');
igual(nombreMesaDef(2, 'Tela', { fila: 3, copias: 5 }), 'Mesa 3 - Tela - Fila 3 - x5', 'Copia: la fila y las copias (lo que promete la guía del otro sistema)');
igual(nombreMesaDef(0, 'DRY RUN (1,83 m)', { fila: 1, copias: 30 }), 'Mesa 1 - DRY RUN (1,83 m) - Fila 1 - x30', 'Copia ×30: no pierde el « - x30»');
igual(nombreMesaDef(0, 'T', { fila: 1, copias: 2, por_mesa: 4 }), 'Mesa 1 - T - Fila 1 - 4 por mesa - x2', 'Copia que llena el ancho: cuántas por mesa');
igual(nombreMesaDef(1, 'T', { filas: [{ fila: 1 }, { fila: 2 }], copias: 1 }), 'Mesa 2 - T - Filas 1+2 - x1', 'Copia mezclada: las filas');
igual(nombreMesaDef(1, 'T', { fila: 1, copias: 1, sueltas: 2 }), 'Mesa 2 - T - Fila 1 - piezas sueltas de 2 prendas - x1', 'piezas sueltas (plural) y las copias al final');
igual(nombreMesaDef(1, 'T', { fila: 1, copias: 1, sueltas: 1 }), 'Mesa 2 - T - Fila 1 - piezas sueltas de 1 prenda - x1', 'piezas sueltas (singular)');
igual(nombreMesaDef(0, 'T', { talles: ['M'] }), 'Mesa 1 - T - Talle M', 'Talles por mesa: uno solo en singular');
igual(nombreMesaDef(0, 'T', { talles: ['S', 'M'] }), 'Mesa 1 - T - Talles S-M', 'Talles por mesa: varios');
igual(nombreMesaDef(2, 'T', { fila: 3, copias: 5, talles: ['M'] }), 'Mesa 3 - T - Fila 3 - Talle M - x5', 'Copia: el talle de la mesa (MAPA 820) y las copias al final');
igual(nombreMesaDef(1, 'T', { filas: [{ fila: 1 }, { fila: 2 }], copias: 1, por_mesa: 2, sueltas: 1, talles: ['S', 'M'] }), 'Mesa 2 - T - Filas 1+2 - Talles S-M - 2 por mesa - piezas sueltas de 1 prenda - x1', 'Copia mezclada: los talles de sus filas');
igual(nombreMesaDef(0, 'T', { diseno: 'GOLERO', fila: 1, copias: 3 }),'Mesa 1 - T - GOLERO - Fila 1 - x3', 'Separar diseños: el diseño delante');

if (fallos.length) {
  console.log(`\nROJO: ${fallos.length} nombre(s) de mesa distintos de lo que se promete.`);
  process.exit(1);
}
console.log('\nVERDE: el nombre de cada mesa es el que se promete.');
