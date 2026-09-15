// ── QUÉ SE ESTÁ DESCARGANDO, Y CUÁNTO VA ─────────────────────────────────────────────────────
// Pedido del usuario (2026-09-14): «si estoy descargando un archivo y no va a usar el descargar
// del navegador, hacé un espacio que nos vaya mostrando cuánto va la descarga de cada archivo,
// porque a veces quiero abrir el archivo y aún no se descargó todo».
//
// POR QUÉ HACE FALTA: desde que la descarga pasa por el «Guardar como» nativo (`descargar.js`),
// el navegador YA NO muestra su barra. El archivo aparece en la carpeta apenas se elige el
// nombre, pero se termina de escribir recién al final: abrirlo antes da un archivo incompleto,
// y hasta ahora no había NINGUNA forma de saberlo. Esto es esa forma.
//
// Es un estado global chiquito y sin dependencias a propósito: `descargar.js` es un módulo suelto
// que se llama desde media docena de lugares de App.jsx, así que no puede depender de React.
// La pantalla se suscribe; el módulo de descarga sólo avisa.

let _items = [];          // {id, nombre, bytes, total, estado, error, t0, tFin}
let _proximoId = 1;
const _subs = new Set();

function _emitir() {
  const copia = _items.slice();
  _subs.forEach((fn) => { try { fn(copia); } catch { /* un suscriptor roto no frena a los demás */ } });
}

/** La pantalla se engancha acá. Devuelve la función para desengancharse. */
export function suscribir(fn) {
  _subs.add(fn);
  fn(_items.slice());               // estado actual de entrada, sin esperar al próximo cambio
  return () => _subs.delete(fn);
}

/** Empieza una descarga; devuelve su id para los avisos siguientes. */
export function abrir(nombre) {
  const id = _proximoId++;
  _items = [..._items, { id, nombre, bytes: 0, total: 0, estado: 'descargando', error: '', t0: Date.now(), tFin: 0 }];
  _emitir();
  return id;
}

function _cambiar(id, campos) {
  let tocado = false;
  _items = _items.map((d) => (d.id === id ? (tocado = true, { ...d, ...campos }) : d));
  if (tocado) _emitir();
}

/** Cuántos bytes van. `total` puede ser 0 si el servidor no dijo el tamaño. */
export function avance(id, bytes, total) {
  _cambiar(id, { bytes, total: total || 0 });
}

export function terminar(id) {
  _cambiar(id, { estado: 'listo', tFin: Date.now() });
}

export function fallar(id, error) {
  _cambiar(id, { estado: 'error', error: String(error || 'falló'), tFin: Date.now() });
}

/** Canceló el usuario (o se cerró el diálogo): no es un error, no hay que alarmar. */
export function cancelar(id) {
  _cambiar(id, { estado: 'cancelado', tFin: Date.now() });
}

export function quitar(id) {
  _items = _items.filter((d) => d.id !== id);
  _emitir();
}

/** Saca de la lista todo lo que ya no está en curso. Lo que sigue bajando NO se toca. */
export function limpiarTerminadas() {
  _items = _items.filter((d) => d.estado === 'descargando');
  _emitir();
}

/** ¿Hay algo bajando ahora? Lo usa el aviso de «no cierres la pestaña». */
export function hayEnCurso() {
  return _items.some((d) => d.estado === 'descargando');
}
