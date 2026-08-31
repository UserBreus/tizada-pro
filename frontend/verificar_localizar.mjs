/**
 * CONTRATO DEL LOCALIZADOR — se corre en `npm run build` (y con `node verificar_localizar.mjs`).
 *
 * `localizar.js` decide QUÉ LUGAR de la pantalla es cada paso de un tutorial: lo que se graba y
 * lo que después se ilumina. Se prueba con un DOM mínimo hecho a mano (no hay navegador acá), que
 * imita la planilla real: una `<table data-tour="planilla-tabla">` con encabezados y celdas que
 * marcan su columna con `data-col`.
 *
 * 🔴 EL CASO QUE LO MOTIVÓ (2026-08-28): «ese paso marcado en realidad debe de marcar la columna
 * que estamos trabajando, no la planilla completa». Tocar Talle, Nombre o Número grababa siempre
 * el mismo paso —el `data-tour` de la tabla— y el tutorial iluminaba la planilla entera.
 */
import { readFileSync } from 'node:fs';

const fallos = [];
function ok(cond, msg) {
  if (!cond) fallos.push(msg);
  console.log((cond ? '  OK   ' : '  FALLA') + ' ' + msg);
}

// ── un DOM de juguete: lo justo para que corra el localizador ───────────────────────────────
class El {
  constructor(tag, attrs = {}, rect = { left: 0, top: 0, right: 10, bottom: 10 }) {
    this.tagName = tag.toUpperCase();
    this.attrs = attrs;
    this.children = [];
    this.parentNode = null;
    this._rect = rect;
  }
  add(hijo) { hijo.parentNode = this; this.children.push(hijo); return hijo; }
  getAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n) ? this.attrs[n] : null; }
  // soporta lo que usa el localizador: varias alternativas con coma, `[attr]`, `[attr="v"]`,
  // `tag[attr]` y nombres de etiqueta sueltos
  matches(sel) {
    return sel.split(',').map((x) => x.trim()).filter(Boolean).some((alt) => {
      const tag = (alt.match(/^([a-zA-Z]+)/) || [])[1];
      if (tag && this.tagName !== tag.toUpperCase()) return false;
      const attrs = [...alt.matchAll(/\[([^=\]]+)(?:="([^"]*)")?\]/g)];
      if (!tag && !attrs.length) return false;
      return attrs.every((m) => (m[2] === undefined
        ? this.getAttribute(m[1]) != null
        : this.getAttribute(m[1]) === m[2]));
    });
  }
  closest(sel) {
    for (let n = this; n; n = n.parentNode) if (n.matches && n.matches(sel)) return n;
    return null;
  }
  get parentElement() { return this.parentNode; }
  // el texto que se VE: el propio y el de los hijos, en líneas (como innerText)
  get innerText() {
    const mio = this.attrs._texto || '';
    const hijos = this.children.map((c) => c.innerText).filter(Boolean);
    return [mio, ...hijos].filter(Boolean).join('\n');
  }
  querySelectorAll(sel) { return this.todos([]).slice(1).filter((e) => e.matches(sel)); }
  contains(o) { for (let n = o; n; n = n.parentNode) if (n === this) return true; return false; }
  getBoundingClientRect() {
    const r = this._rect;
    return { ...r, width: r.right - r.left, height: r.bottom - r.top, x: r.left, y: r.top };
  }
  get textContent() { return this.innerText; }
  todos(out = []) { out.push(this); for (const c of this.children) c.todos(out); return out; }
}

// planilla: encabezados arriba (y=0..20) y dos filas de celdas (y=20..50)
const raiz = new El('div');
const tabla = raiz.add(new El('table', { 'data-tour': 'planilla-tabla' }));
const COLS = [['talle', 'Talle'], ['nombre', 'Nombre'], ['numero', 'Número']];
const thead = tabla.add(new El('thead'));
COLS.forEach(([id, label], i) => thead.add(new El('th',
  { 'data-col': id, 'data-col-label': label }, { left: i * 100, top: 0, right: i * 100 + 100, bottom: 20 })));
const tbody = tabla.add(new El('tbody'));
[0, 1].forEach((f) => COLS.forEach(([id, label], i) => tbody.add(new El('td',
  { 'data-col': id, 'data-col-label': label },
  { left: i * 100, top: 20 + f * 15, right: i * 100 + 100, bottom: 35 + f * 15 }))));
// un control con marca propia DENTRO de una celda: ese gana (es más específico que la columna)
const celdaConBoton = tbody.children.find((c) => c.getAttribute('data-col') === 'nombre');
const botonPropio = celdaConBoton.add(new El('button', { 'data-tour': 'planilla-borrar-fila' }));

const todos = raiz.todos();
// el selector soporta lo que usa el localizador: varias alternativas con coma (OR) y atributos
// pegados dentro de cada una (AND)
global.document = {
  querySelectorAll: (sel) => todos.filter((e) => sel.split(',').map((s) => s.trim()).filter(Boolean)
    .some((alt) => alt.split(/(?<=\])(?=\[)/).every((s) => e.matches(s)))),
  querySelector: (sel) => global.document.querySelectorAll(sel)[0] || null,
};
global.window = { getComputedStyle: () => ({ visibility: 'visible', display: 'block', opacity: '1' }) };
global.CSS = { escape: (s) => s };

const { identificar, buscar, rectDeColumna, rectDeAncla, esDelAncla, etiquetaColumna } = await import('./src/localizar.js');

console.log('\n1 · Un paso de la planilla es SU COLUMNA, no la tabla entera');
for (const [id, label] of COLS) {
  const celda = tbody.children.find((c) => c.getAttribute('data-col') === id);
  ok(identificar(celda) === 'col:' + id, `tocar una celda de ${label} graba «col:${id}» (no «planilla-tabla»)`);
}
ok(new Set(COLS.map(([id]) => identificar(tbody.children.find((c) => c.getAttribute('data-col') === id)))).size === 3,
   '🔴 tres columnas distintas dan TRES pasos distintos (antes eran tres veces el mismo)');
ok(identificar(botonPropio) === 'planilla-borrar-fila',
   'un control con marca propia adentro de una celda le gana a la columna');
ok(identificar(tabla) === 'planilla-tabla', 'tocar la tabla misma (fuera de toda columna) sigue siendo la tabla');

console.log('\n2 · Iluminar una columna la abarca entera (encabezado + celdas)');
const r = rectDeColumna('nombre');
ok(!!r, 'la columna tiene recuadro');
ok(r && r.y === 0 && r.h === 50, 'va desde el encabezado hasta la última celda (alto 50)');
ok(r && r.x === 100 && r.w === 100, 'y ocupa el ancho de ESA columna, no el de la tabla');
const rT = rectDeColumna('talle');
ok(rT && rT.x === 0, 'otra columna cae en otro lugar (Talle arranca en 0)');
ok(rectDeColumna('no-existe') === null, 'una columna que no está en pantalla no inventa recuadro');

// 🔴 EL DESPLEGABLE DE LA CELDA (2026-08-28: «debe de seleccionar toda la columna y el
// desplegable también»). La lista de opciones se monta en el body (portal, `position: fixed`), no
// dentro de la tabla: sin sumarla, el hueco del tutorial la dejaba afuera —bajo el velo— justo
// cuando hay que elegir en ella.
const lista = raiz.add(new El('div', { 'data-col-lista': 'talle' },
  { left: 0, top: 50, right: 100, bottom: 130 }));
todos.push(lista);
const rConLista = rectDeColumna('talle');
ok(rConLista && rConLista.h === 130, 'con la lista abierta, el recuadro la incluye (alto 50 → 130)');
ok(rConLista && rConLista.y === 0, 'y sigue arrancando en el encabezado');
ok((rectDeColumna('nombre') || {}).h === 50, 'la lista de una columna no agranda a las demás');
todos.splice(todos.indexOf(lista), 1);   // se cierra la lista
ok((rectDeColumna('talle') || {}).h === 50, 'al cerrarse la lista, el recuadro vuelve a la columna sola');

console.log('\n3 · UN SOLO resolutor del recuadro (el tutorial y el editor marcan lo MISMO)');
// 🔴 El editor medía por su cuenta (`buscar(ancla).getBoundingClientRect()`) y con un paso de
// columna marcaba SÓLO EL TÍTULO, mientras el tutorial marcaba la columna entera. Misma clase de
// bug que en el motor con `_encaje()`: dos lugares decidiendo lo mismo con reglas distintas.
const thNombre = thead.children.find((e) => e.getAttribute('data-col') === 'nombre');
const rCol = rectDeAncla('col:nombre', thNombre);
ok(rCol && rCol.h === 50, 'un paso de columna es el TÍTULO MÁS TODAS LAS CASILLAS (no sólo el título)');
ok(rCol && rCol.h !== thNombre.getBoundingClientRect().height,
   '🔴 y NO es el recuadro del encabezado solo (que es lo que marcaba el editor)');
const botonSuelto = raiz.add(new El('button', { 'data-tour': 'x' }, { left: 5, top: 5, right: 45, bottom: 25 }));
todos.push(botonSuelto);
const rBoton = rectDeAncla('x', botonSuelto);
ok(rBoton && rBoton.w === 40 && rBoton.h === 20, 'un paso normal sigue siendo su propio control');
ok(rectDeAncla('col:no-existe', botonSuelto) !== null,
   'si la columna no está en pantalla, cae al elemento en vez de no marcar nada');
ok(rectDeAncla('col:nombre', null) !== null, 'una columna se mide aunque no haya elemento de referencia');
ok(rectDeAncla('x', null) === null, 'sin columna y sin elemento, no se inventa recuadro');

const tutorSrc = readFileSync(new URL('./src/tutor.jsx', import.meta.url), 'utf8');
ok((tutorSrc.match(/rectDeAncla\(/g) || []).length >= 2,
   '🔴 el tutorial Y el editor lo usan (si uno mide por su cuenta, vuelven a mostrar cosas distintas)');

console.log('\n4 · TOCAR EL CONTROL DEL PASO CUENTA (si no, el tutorial queda clavado)');
// 🔴 EL CASO DEL USUARIO (2026-08-31, la tarjeta «Cuello redondo»): «presionás y no salta al
// siguiente paso». El detector del clic sólo miraba `data-tour`, y la MAYORÍA de los controles no
// tiene esa marca —se identifican por su texto—, así que el clic no contaba nunca. Sólo se veía
// en los pasos que se resuelven tocando: los que cambian de pantalla avanzaban igual, por otro lado.
const tarjeta = raiz.add(new El('button', { title: 'camiseta asque · 6 pzas' },
  { left: 0, top: 200, right: 120, bottom: 300 }));
const dibujito = tarjeta.add(new El('span'));       // el clic suele caer en un hijo, no en el botón
const otroBoton = raiz.add(new El('button', { title: 'Otra cosa' }, { left: 200, top: 200, right: 300, bottom: 300 }));
todos.push(tarjeta, dibujito, otroBoton);

const anclaTarjeta = identificar(tarjeta);
ok(anclaTarjeta === 'txt:camiseta asque · 6 pzas', `la tarjeta se graba por su texto (${anclaTarjeta})`);
ok(esDelAncla(tarjeta, anclaTarjeta), '🔴 tocar la tarjeta CUENTA como hacer ese paso');
ok(esDelAncla(dibujito, anclaTarjeta), 'y tocar el dibujito de adentro también');
ok(!esDelAncla(otroBoton, anclaTarjeta), 'tocar otro botón no lo da por hecho');
ok(esDelAncla(botonSuelto, 'x'), 'un control con data-tour sigue andando igual que antes');
ok(esDelAncla(tbody.children[1], 'col:nombre'), 'tocar una celda cuenta como el paso de su columna');
ok(!esDelAncla(tbody.children[0], 'col:nombre'), 'pero una celda de OTRA columna no');
ok(!esDelAncla(null, 'txt:lo que sea') && !esDelAncla(tarjeta, null), 'sin elemento o sin ancla, no explota');

// 🔴 Y EL CLIC MANDA AUNQUE EL PASO TENGA CONDICIÓN (2026-08-31, «Asignar telas»): antes, con una
// regla `listo` el motor «esperaba el estado» y ni escuchaba el clic — el paso quedaba clavado
// mientras el panel se abría atrás. Se vigila en el código, que es donde vive la decisión.
{
  const src = readFileSync(new URL('./src/tutor.jsx', import.meta.url), 'utf8');
  const desde = src.indexOf('AVANCE POR ACCIÓN EN EL DOM');
  const bloque = src.slice(desde, desde + 1400);
  ok(desde > 0 && !bloque.includes('|| esperaEstado) return;'),
     '🔴 el avance por clic NO se apaga cuando el paso tiene regla `listo`');
  ok(bloque.includes('if (fin || carga || bloqueoModal) return;'),
     'pero sigue sin escuchar mientras hay una carga o un modal encima');
}

console.log('\n4b · TODO LO MANIPULABLE ES GRABABLE (auditoría 2026-08-31: 969 controles reales)');
// 🔴 (a) El clic cae en el ÍCONO de adentro del botón, que no tiene nombre: antes `identificar`
// devolvía null y ese paso NO SE PODÍA GRABAR. Ahora se sube al control.
const btnIcono = raiz.add(new El('button', { title: 'Borrar la fila' }, { left: 0, top: 400, right: 30, bottom: 430 }));
const icono = btnIcono.add(new El('svg'));
const tracito = icono.add(new El('path'));
todos.push(btnIcono, icono, tracito);
ok(identificar(icono) === 'txt:borrar la fila', '🔴 tocar el ícono de un botón se graba como el botón');
ok(identificar(tracito) === 'txt:borrar la fila', 'y tocar un trazo del ícono, también');

// 🔴 (b) HOMÓNIMOS: 7 «Editar» en la misma pantalla. Sin contexto todos daban el mismo ancla y el
// tutorial marcaba el primero, no el que se tocó.
const filaA = raiz.add(new El('div', { _texto: 'Manga larga' }, { left: 0, top: 500, right: 200, bottom: 540 }));
filaA.add(new El('span', { _texto: 'Manga larga' }));
const editarA = filaA.add(new El('button', { _texto: 'Editar' }, { left: 150, top: 500, right: 200, bottom: 540 }));
const filaB = raiz.add(new El('div', { _texto: 'Con capucha' }, { left: 0, top: 560, right: 200, bottom: 600 }));
filaB.add(new El('span', { _texto: 'Con capucha' }));
const editarB = filaB.add(new El('button', { _texto: 'Editar' }, { left: 150, top: 560, right: 200, bottom: 600 }));
todos.push(filaA, editarA, filaB, editarB, ...filaA.children, ...filaB.children);

const aA = identificar(editarA);
const aB = identificar(editarB);
ok(aA !== aB, `🔴 dos «Editar» de filas distintas dan anclas DISTINTAS (${aA} ≠ ${aB})`);
ok(aA.startsWith('txt:editar@'), 'el ancla lleva el nombre de su fila');
ok(buscar(aA) === editarA, 'y al reproducir se encuentra EL de esa fila');
ok(buscar(aB) === editarB, 'cada uno el suyo');
ok(esDelAncla(editarA, aA) && !esDelAncla(editarB, aA),
   'tocar el «Editar» de otra fila NO da el paso por hecho');

console.log('\n5 · Lo que se busca y cómo se llama');
ok((buscar('col:nombre') || {}).tagName === 'TH', 'buscar una columna devuelve su encabezado (para el scroll)');
ok(etiquetaColumna('numero') === 'Número', 'el nombre de la columna sale del molde, con su acento');
ok(etiquetaColumna('inventada') === 'inventada', 'una columna desconocida cae a su id, sin explotar');

console.log();
if (fallos.length) {
  console.log(`  ${fallos.length} FALLO(S) — el localizador no marca lo que hay que marcar`);
  fallos.forEach((f) => console.log('   · ' + f));
  process.exit(1);
}
console.log('  OK: cada columna de la planilla es su propio paso y se ilumina entera');
