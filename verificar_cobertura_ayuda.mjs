/**
 * MEDIDOR DE COBERTURA DE LA AYUDA — `node verificar_cobertura_ayuda.mjs`
 *
 * Genera `frontend/dist/_medir.js`, que se pega en la consola del navegador (o se carga con
 * `fetch`) para MEDIR SOBRE LA PANTALLA REAL cuántos controles el tutorial sabe identificar y
 * cuántos tienen explicación.
 *
 * Por qué existe: contar `<button>` en el código miente. Un mismo botón se dibuja 12 veces (una
 * por diseño) y muchos no están en pantalla nunca a la vez. Lo único que vale es medir lo que
 * se ve.
 *
 * CÓMO SE USA
 *   1. `py srv_visor.py`            → la UI real, sin login y sin poder escribir (puerto 8060)
 *   2. `node verificar_cobertura_ayuda.mjs`
 *   3. En el navegador, sobre la pantalla que quieras medir:
 *        await (async()=>{eval(await (await fetch('/_medir.js')).text()); return __medir()})()
 *   4. Lo que salga en `sinExplicacion` es lo que falta escribir en `diccionario.js`.
 *
 * ⚠️ En el sandbox no se dibuja la barra lateral (sin usuario no hay navegación), así que para
 * medir las pantallas de Configuración hay que hacerlo con sesión iniciada, en el 8050.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(AQUI, 'frontend/src/localizar.js'), 'utf8')
  // el `export default {...}` puede ocupar VARIAS líneas: sacar sólo la primera dejaba el resto
  // del objeto suelto y el medidor no compilaba («Unexpected token }»)
  .replace(/^export default [\s\S]*?;\s*$/m, '')
  .replace(/export function /g, 'function ');
const dic = readFileSync(join(AQUI, 'frontend/src/diccionario.js'), 'utf8');
const claves = [...new Set([...dic.matchAll(/^ {2}'([\w:.-]+)':/gm)].map((m) => m[1]))].sort();

const medidor = `
window.__medir = function () {
  const CON = new Set(${JSON.stringify(claves)});
  // 🔴 NO SÓLO LOS BOTONES. Media Configuración se toca en DIVS clickeables (las tarjetas de
  // moldería, filas de listas): el grabador SÍ los graba, así que hay que medir si después se
  // pueden volver a encontrar. Contarlos de menos fue lo que dejó pasar el bug de 2026-09-01
  // («No encuentro ese lugar» con la tarjeta a la vista).
  const _clickeable = (el) => {
    try { return window.getComputedStyle(el).cursor === 'pointer'; } catch (e) { return false; }
  };
  const _base = [...document.querySelectorAll('button, [role="button"], a[href], input, select, textarea')];
  const _divs = [...document.querySelectorAll('div, li, tr, td')]
    .filter((el) => _clickeable(el) && !el.closest('button, [role="button"], a[href]')
                    && !_base.includes(el)
                    // sólo el clickeable MÁS EXTERNO: si el padre ya cuenta, el hijo hereda el cursor
                    && !(el.parentElement && _clickeable(el.parentElement)));
  const ctrls = [..._base, ..._divs]
    .filter((el) => { const r = el.getBoundingClientRect(); return (r.width || r.height); });
  const r = { visibles: ctrls.length, botones: _base.length, clickeables: _divs.length, identificados: 0, recuperados: 0, sinId: [], sinExplicacion: [] };
  for (const el of ctrls) {
    const id = identificar(el);
    if (!id) { r.sinId.push(el.tagName + ' «' + (el.innerText || '').trim().slice(0, 18) + '»'); continue; }
    r.identificados++;
    if (buscar(id)) r.recuperados++;
    if (!CON.has(id)) r.sinExplicacion.push(id);
  }
  r.sinExplicacion = [...new Set(r.sinExplicacion)].sort();
  return r;
};
'medidor listo: __medir()';
`;
writeFileSync(join(AQUI, 'frontend/dist/_medir.js'), src + medidor, 'utf8');
console.log(`  medidor escrito en frontend/dist/_medir.js (${claves.length} explicaciones cargadas)`);
console.log('  en el navegador:  await (async()=>{eval(await (await fetch("/_medir.js")).text()); return __medir()})()');
