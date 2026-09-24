/**
 * CONTRATO: TODA DESCARGA ABRE EL «GUARDAR COMO» — se corre en `npm run build` (y con
 * `node verificar_descarga_elegir_carpeta.mjs`).
 *
 * Pedido del usuario (2026-09-11): «cuando descargás el PDF, que te abra la carpeta de elegir dónde
 * guardarlo». Vive en `src/descargar.js` (File System Access API de Chrome/Edge) y TODAS las
 * descargas de la app pasan por ahí: si alguien vuelve a poner un `<a download>` pelado o un
 * `a.click()` a mano, el botón nuevo guarda solo en "Descargas" y nadie se entera. Por eso se cuenta
 * acá, sobre el código, no sobre un click que no se puede simular (el diálogo es nativo).
 *
 * Reglas que se vigilan:
 *   1. Cada `download=` de App.jsx tiene un `onClick` que llama a `descargarArchivo`.
 *   2. No queda ningún `a.download = …` + `a.click()` a mano en App.jsx (van por `descargarBlob`).
 *   3. «Descargar todo» usa `descargarVarios` (UNA carpeta), no 30 diálogos.
 *   4. En `descargar.js`: cancelar NO descarga (AbortError → return sin respaldo); sin API hay
 *      respaldo clásico; el archivo se pide con fetch (misma origen: viaja la sesión); ningún
 *      alert/confirm.
 */
import fs from 'node:fs';

const app = fs.readFileSync(new URL('./src/App.jsx', import.meta.url), 'utf8');
const mod = fs.readFileSync(new URL('./src/descargar.js', import.meta.url), 'utf8');
const est = fs.readFileSync(new URL('./src/descargas.js', import.meta.url), 'utf8');
const fallos = [];

function ok(cond, msg) {
  if (!cond) fallos.push(msg);
  console.log((cond ? '  OK   ' : '  FALLA') + ' ' + msg);
}

console.log('\n1 · Cada ancla con download= abre el «Guardar como»');
// Cada `<a … download=…>` entera. No sirve una regex hasta el primer `>`: los `onClick={(e) => …}`
// llevan un `=>` adentro y la cortarían a la mitad. Se recorre contando llaves: el `>` que cierra
// la etiqueta es el primero que aparece con las llaves de JSX cerradas.
function etiquetasA(src) {
  const out = [];
  let i = 0;
  while ((i = src.indexOf('<a', i)) !== -1) {
    if (!/[\s>]/.test(src[i + 2] || '')) { i += 2; continue; }   // <abbr>, <article>… no son <a>
    let j = i, prof = 0;
    for (; j < src.length; j++) {
      const c = src[j];
      if (c === '{') prof++;
      else if (c === '}') prof--;
      else if (c === '>' && prof === 0) break;
    }
    const tag = src.slice(i, j + 1);
    if (/\bdownload=/.test(tag)) out.push([tag]);
    i = j + 1;
  }
  return out;
}
const anclas = etiquetasA(app);
ok(anclas.length >= 3, `hay anclas de descarga (${anclas.length})`);
const sinClick = anclas.filter((m) => !/onClick=\{[^}]*descargarArchivo\(/s.test(m[0]));
ok(sinClick.length === 0,
   `🔴 todas llaman a descargarArchivo en su onClick (sin: ${sinClick.length}${sinClick.length ? ' → ' + sinClick.map((m) => m[0].slice(0, 60).replace(/\s+/g, ' ')).join(' | ') : ''})`);
ok(anclas.every((m) => /e\.preventDefault\(\)/.test(m[0])),
   'y frenan la descarga clásica del ancla (preventDefault) — si no, se guardaría dos veces');

console.log('\n2 · No queda ninguna descarga a mano');
const aMano = [...app.matchAll(/a\.download\s*=/g)];
ok(aMano.length === 0, `🔴 ningún \`a.download = …\` suelto en App.jsx (hay ${aMano.length})`);
ok(/import \{[^}]*descargarBlob[^}]*\} from '\.\/descargar\.js'/.test(app), 'se importa `descargarBlob` para los archivos armados en memoria (CSV, guía .ai)');
ok(/descargarBlob\(blob,\s*`planilla_/.test(app), 'el CSV de la planilla va por descargarBlob');
// (desde 2026-09-22 el .ai se arma en esta computadora: el Blob sale del hilo, no del servidor)
ok(/descargarBlob\(new Blob\(\[bytes\], \{ type: 'application\/postscript' \}\),\s*`guia_/.test(app), 'la guía .ai va por descargarBlob');

console.log('\n3 · «Descargar todo» elige UNA carpeta');
ok(/descargarVarios\(items,\s*\{\s*avisar/.test(app), '🔴 «Descargar todo» llama a descargarVarios con la lista de mesas');
ok(!/for \(let pi = 0; pi < pvs\.length; pi\+\+\) \{[^}]*a\.click\(\)/s.test(app),
   'y ya no dispara un a.click() por mesa dentro del bucle');

console.log('\n4 · El módulo se porta bien');
ok(/showSaveFilePicker\(/.test(mod) && /showDirectoryPicker\(/.test(mod), 'usa la File System Access API (archivo y carpeta)');
ok(/isSecureContext/.test(mod), 'sólo en contexto seguro (https o localhost), que es donde la API existe');
ok(/function esCancelacion[\s\S]*AbortError/.test(mod), 'reconoce la cancelación del diálogo (AbortError)');
// cancelar → return sin descargar: en descargarArchivo el catch del picker devuelve antes del respaldo
ok(/if \(esCancelacion\(e\)\) return false\s*\/\/ canceló/.test(mod),
   '🔴 cancelar NO descarga nada (ni al respaldo)');
ok(/if \(esCancelacion\(e\)\) return -1/.test(mod), 'cancelar la carpeta tampoco');
ok(/function descargaClasica/.test(mod) && /if \(!puedeElegirDonde\(\)\) \{\s*(?:try \{ await )?descargaClasica/.test(mod),
   'sin la API cae al <a download> de siempre: la descarga nunca deja de funcionar');
ok(/await fetch\(url\)/.test(mod) || /fetch\(url\)/.test(mod), 'el archivo se pide con fetch de la misma origen (viaja la sesión)');
ok(!/\balert\(|\bconfirm\(/.test(mod), 'sin diálogos nativos: los errores van por `avisar`');
ok(/suggestedName: nombre/.test(mod), 'el diálogo sugiere el nombre de la mesa/ficha');

console.log('\n5 · 🔴 SE VE CUÁNTO VA CADA DESCARGA (el navegador ya no muestra SU barra)');
// El usuario (2026-09-14): «hacé un espacio que nos vaya mostrando cuánto va la descarga de cada
// archivo, porque a veces quiero abrir el archivo y aún no se descargó todo». Con el «Guardar
// como» nativo el archivo se crea al principio y se llena al final: sin esto no había forma de
// saber si ya estaba entero.
ok(/r\.body[\s\S]{0,200}getReader\(\)/.test(mod), 'se lee `response.body` de a pedazos');
ok(/Content-Length/.test(mod), 'el total sale del Content-Length que manda el servidor');
ok(/DESC\.avance\(id, bytes, total\)/.test(mod), 'informa el avance por BYTES en cada pedazo');
ok(/descargarArchivo[\s\S]{0,1800}bajarA\(url, handle, nombre\)/.test(mod),
   'un archivo suelto pasa por el streaming');
ok(/descargarVarios[\s\S]{0,1600}bajarA\(it\.url, fh, it\.nombre\)/.test(mod),
   '«Descargar todo» también');
ok(/export function suscribir/.test(est) && /export function avance/.test(est),
   'el estado compartido expone suscribir/avance');
ok(/function PanelDescargas\(\)/.test(app), 'existe el panel en pantalla');
ok(/<PanelDescargas \/>/.test(app), 'y está montado (una sola vez, global)');
ok(/DESCARGAS\.suscribir\(setItems\)/.test(app), 'el panel se suscribe al estado');
ok(/beforeunload/.test(app), 'avisa si se cierra la pestaña con una descarga a medias');
ok(!/async function alCortarse[\s\S]{0,120}TODO\(human\)/.test(mod),
   'está decidido qué pasa con el archivo si la descarga se corta (no quedó el TODO)');

console.log('');
if (fallos.length) {
  console.log(`  ${fallos.length} FALLO(S)`);
  process.exit(1);
}
console.log('  OK: toda descarga abre el «Guardar como» (o elige una carpeta para todas)');
