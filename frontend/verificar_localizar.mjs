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
  hasAttribute(n) { return Object.prototype.hasOwnProperty.call(this.attrs, n); }
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
  // el hermano de arriba: `rotuloDe` lo usa para encontrar el rótulo de un campo
  get previousElementSibling() {
    const h = this.parentNode ? this.parentNode.children : [];
    const i = h.indexOf(this);
    return i > 0 ? h[i - 1] : null;
  }
  // el texto que se VE: el propio y el de los hijos, en líneas (como innerText)
  get innerText() {
    const mio = this.attrs._texto || '';
    const hijos = this.children.map((c) => c.innerText).filter(Boolean);
    return [mio, ...hijos].filter(Boolean).join('\n');
  }
  querySelectorAll(sel) { return this.todos([]).slice(1).filter((e) => e.matches(sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
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
global.window = { getComputedStyle: () => ({ visibility: 'visible', display: 'block', opacity: '1' }),
                  innerWidth: 1280, innerHeight: 900 };
global.CSS = { escape: (s) => s };

const { identificar, buscar, rectDeColumna, rectDeAncla, esDelAncla, etiquetaColumna,
        elegidasEn, estaApagado, motivoApagado, sinNumeros, anclaEfectiva, esCampo,
        partirAncla, gestoGenerico, esArrastre } = await import('./src/localizar.js');

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

console.log('\n6 · «ELEGÍ N DE ESTA LISTA» SE MIDE, NO SE CUENTAN CLICS (auditoría 2026-08-31)');
// 🔴 EL CASO REAL, verificado en pantalla: dos clics en el AIRE de la lista daban el paso por
// cumplido, y tocar dos opciones YA elegidas —que las DESMARCA— también: el tutorial avanzaba
// dejando el pedido con MENOS diseños que antes.
const listaOpc = raiz.add(new El('div', { 'data-tour': 'pedido-diseno-lista', 'data-opciones': '1' },
  { left: 0, top: 700, right: 300, bottom: 800 }));
const opA = listaOpc.add(new El('button', { _texto: 'JUGADOR', 'data-elegida': '1' }, { left: 0, top: 700, right: 100, bottom: 740 }));
const opB = listaOpc.add(new El('button', { _texto: 'GOLERO', 'data-elegida': '0' }, { left: 100, top: 700, right: 200, bottom: 740 }));
const opC = listaOpc.add(new El('button', { _texto: 'CUERPO TECNICO', 'data-elegida': '0' }, { left: 200, top: 700, right: 300, bottom: 740 }));
todos.push(listaOpc, opA, opB, opC);
ok(elegidasEn('pedido-diseno-lista') === 1, 'se cuenta lo que está ELEGIDO (1 de 3), no los toques');
opB.attrs['data-elegida'] = '1';
ok(elegidasEn('pedido-diseno-lista') === 2, 'al elegir otra, son 2');
opA.attrs['data-elegida'] = '0';
ok(elegidasEn('pedido-diseno-lista') === 1, '🔴 y al DESMARCAR una, vuelve a 1 (antes esto sumaba)');
ok(elegidasEn('planilla-tabla') === null, 'una lista que no declara sus elegidas devuelve null (ahí manda el clic)');

console.log('\n7 · LO QUE DESHACE NO CUMPLE EL PASO');
const quitar = listaOpc.add(new El('button', { _texto: '✕', 'data-no-avanza': '1' }, { left: 90, top: 700, right: 100, bottom: 710 }));
todos.push(quitar);
ok(!esDelAncla(quitar, 'pedido-diseno-lista'),
   '🔴 tocar la ✕ que QUITA un diseño no cuenta como elegir una opción');
ok(esDelAncla(opC, 'pedido-diseno-lista'), 'pero tocar una opción de verdad, sí');

console.log('\n8 · EL MISMO BOTÓN CON OTRO NÚMERO ADENTRO');
// «Copiar a 1» pasa a decir «Copiar a 3» con tres moldes marcados: el ancla grabada no encontraba
// nada y el tutorial quedaba en «No encuentro ese lugar» (tutorial «2 colores» del usuario).
const copiar = raiz.add(new El('button', { _texto: 'Copiar a 3' }, { left: 0, top: 900, right: 120, bottom: 930 }));
todos.push(copiar);
ok(sinNumeros('copiar a 1') === sinNumeros('copiar a 3'), 'los números son comodín');
ok(buscar('txt:copiar a 1') === copiar, '🔴 el paso grabado con «Copiar a 1» encuentra «Copiar a 3»');
const otroExacto = raiz.add(new El('button', { _texto: 'Copiar a 1' }, { left: 0, top: 940, right: 120, bottom: 970 }));
todos.push(otroExacto);
ok(buscar('txt:copiar a 1') === otroExacto, '…pero si existe el exacto, gana el exacto');

console.log('\n9 · EN UNA LISTA DE OPCIONES, EL PASO ES LA LISTA (también para lo ya grabado)');
ok(buscar('txt:cuerpo tecnico') === listaOpc,
   '🔴 un paso atado a UNA tarjeta se marca sobre la lista entera');
ok(anclaEfectiva('txt:cuerpo tecnico') === 'pedido-diseno-lista',
   '…y el cartel que se muestra es el de la lista, no el de esa tarjeta');
ok(esDelAncla(opB, 'txt:cuerpo tecnico'),
   'por eso vale elegir OTRA opción: quien sigue el tutorial no tiene por qué tener la misma');

console.log('\n10 · UN BOTÓN APAGADO SE EXPLICA, NO SE MANDA A TOCAR');
const barra = raiz.add(new El('div', {}, { left: 0, top: 1000, right: 600, bottom: 1100 }));
const avisoBarra = barra.add(new El('div', { 'data-aviso-paso': '1', _texto: 'Falta elegir la prenda de «GOLERO».' },
  { left: 0, top: 1000, right: 600, bottom: 1020 }));
const btnOff = barra.add(new El('button', { 'data-tour': 'pedido-ir-arte', _texto: 'Cargar el arte', disabled: true },
  { left: 480, top: 1040, right: 600, bottom: 1080 }));
btnOff.disabled = true;
todos.push(barra, avisoBarra, btnOff);
ok(estaApagado(btnOff), 'se detecta que el botón del paso está apagado');
ok(!estaApagado(opB), 'y que uno normal no lo está');
ok((motivoApagado(btnOff) || {}).texto === 'Falta elegir la prenda de «GOLERO».',
   '🔴 el motivo sale de la propia pantalla (el aviso del paso), con sus palabras');
ok((motivoApagado(btnOff) || {}).el === avisoBarra,
   '…y se sabe cuál es ese cartel, para iluminarlo junto al botón en vez de taparlo con el velo');

console.log('');
console.log('11 · CONFIGURACIÓN: LO QUE NO ES UN BOTÓN (auditoría 2026-09-01)');
// 🔴 EL CASO REAL: las tarjetas de moldería son `<div>` clickeables. El grabador las graba (cae al
// elemento tocado), pero `buscar` sólo miraba botones y campos: al reproducir, el tutorial decía
// «No encuentro ese lugar en pantalla» con la tarjeta delante de los ojos.
const tarjCfg = raiz.add(new El('div', { class: 'product-card' }, { left: 0, top: 1200, right: 300, bottom: 1360 }));
const tarjTitulo = tarjCfg.add(new El('div', { _texto: 'Camiseta de futbol' }, { left: 10, top: 1210, right: 200, bottom: 1240 }));
const tarjEstado = tarjCfg.add(new El('div', { _texto: 'MOLDE OK' }, { left: 10, top: 1250, right: 120, bottom: 1270 }));
todos.push(tarjCfg, tarjTitulo, tarjEstado);
ok(identificar(tarjCfg) === 'txt:camiseta de futbol', 'una tarjeta sin botón se puede grabar por su texto');
ok(buscar('txt:camiseta de futbol') === tarjCfg,
   '🔴 …y al reproducir se encuentra LA TARJETA, no su título (el clic cae en cualquier parte de ella)');
ok(esDelAncla(tarjEstado, 'txt:camiseta de futbol'),
   'tocar cualquier parte de la tarjeta cuenta como hacer ese paso');

console.log('');
console.log('12 · SI LA SECCIÓN **ES** EL CONTROL, EL PASO ES LA SECCIÓN');
// 🔴 Los ajustes de una moldería son botones ÍCONO + título con su propio `data-tour`. Al tocarlos
// por el ícono, el ancla quedaba afinada («txt:aa#ajuste-terminologia») y el cartel decía
// **«Tocá "Aa"»** en vez de «Entrá a "Nombres"».
const botonAjuste = raiz.add(new El('button', { 'data-tour': 'ajuste-terminologia' }, { left: 0, top: 1400, right: 300, bottom: 1470 }));
const iconoAjuste = botonAjuste.add(new El('span', { _texto: 'Aa' }, { left: 5, top: 1405, right: 35, bottom: 1435 }));
todos.push(botonAjuste, iconoAjuste);
ok(anclaEfectiva('txt:aa#ajuste-terminologia') === 'ajuste-terminologia',
   '🔴 el paso vuelve a ser el botón marcado (y usa SU explicación, no el nombre del ícono)');
// …pero un PANEL con varios botones adentro sigue afinado: ahí sí importa cuál se tocó (358)
const panel = raiz.add(new El('div', { 'data-tour': 'resultados-mesas' }, { left: 0, top: 1500, right: 400, bottom: 1600 }));
panel.add(new El('button', { _texto: 'Descargar sólo la hoja 1' }, { left: 5, top: 1505, right: 200, bottom: 1535 }));
panel.add(new El('button', { _texto: 'Descargar la ficha técnica completa' }, { left: 5, top: 1545, right: 200, bottom: 1575 }));
todos.push(panel, ...panel.children);
ok(anclaEfectiva('txt:descargar solo la hoja 1#resultados-mesas') === 'txt:descargar solo la hoja 1#resultados-mesas',
   'en un panel con varios botones, el paso sigue siendo EL BOTÓN que se tocó');

console.log('');
console.log('13 · UN CAMPO SE ESCRIBE: NO AVANZA SOLO (pedido del usuario 2026-09-01)');
// «cuando son campos de escribir no saltará automático, debe presionar Siguiente así puede
// escribir. El automático solo es en botones y ventanas emergentes que no tenés que presionar nada»
const campoTxt = raiz.add(new El('input', { placeholder: 'Nombre del diseño' }, { left: 0, top: 1700, right: 200, bottom: 1730 }));
const areaTxt = raiz.add(new El('textarea', { placeholder: 'Notas' }, { left: 0, top: 1740, right: 200, bottom: 1800 }));
const listaSel = raiz.add(new El('select', {}, { left: 0, top: 1810, right: 200, bottom: 1840 }));
const botonComun = raiz.add(new El('button', { _texto: 'Guardar' }, { left: 0, top: 1850, right: 100, bottom: 1880 }));
todos.push(campoTxt, areaTxt, listaSel, botonComun);
ok(esCampo(campoTxt) && esCampo(areaTxt), 'un input y un textarea son campos de escritura');
ok(!esCampo(listaSel), 'un desplegable NO: ahí se elige, no se escribe');
ok(!esCampo(botonComun), 'y un botón tampoco (ésos sí avanzan solos)');
// tocar el ícono/hijo de un campo también cuenta como campo
const envoltorio = raiz.add(new El('div', {}, { left: 0, top: 1900, right: 200, bottom: 1930 }));
const campoDentro = envoltorio.add(new El('input', {}, { left: 0, top: 1900, right: 200, bottom: 1930 }));
todos.push(envoltorio, campoDentro);
ok(esCampo(envoltorio), 'lo que CONTIENE un campo también se trata como campo');
ok(!esCampo(null), 'sin elemento, no explota');

// y en el motor: el clic sobre un campo NO cumple el paso (si no, se salta antes de escribir)
{
  const src = readFileSync(new URL('./src/tutor.jsx', import.meta.url), 'utf8');
  const desde = src.indexOf('AVANCE POR ACCIÓN EN EL DOM');
  const bloque = src.slice(desde, desde + 6000);
  ok(desde > 0 && bloque.includes('if (esCampo(e.target)) return;'),
     '🔴 el motor NO da por hecho el paso cuando el clic cae en un campo');
  ok(bloque.includes('if (paso.manual) return;'),
     '…y sigue sin escuchar los pasos que se terminan a mano (columna o campo)');
}

console.log('');
console.log('14 · EL «?» DE AYUDA NO ES EL NOMBRE DE UN CAMPO (tutorial «Cargar molde», 2026-09-01)');
// 🔴 EL CASO REAL: los rótulos de esta app llevan al lado el botón «?» del popover. El campo tomaba
// ESE texto como su identidad y el paso quedaba guardado como «txt:?» — imposible de reencontrar.
const filaCampo = raiz.add(new El('div', {}, { left: 0, top: 2000, right: 300, bottom: 2060 }));
const rotulo = filaCampo.add(new El('div', { _texto: '?' }, { left: 0, top: 2000, right: 20, bottom: 2016 }));
const campoConAyuda = filaCampo.add(new El('input', {}, { left: 0, top: 2020, right: 300, bottom: 2050 }));
todos.push(filaCampo, rotulo, campoConAyuda);
ok(identificar(campoConAyuda) !== 'txt:?',
   '🔴 un campo cuyo vecino es el «?» ya NO se graba como «txt:?»');
// y con un rótulo de verdad, ése manda
const fila2 = raiz.add(new El('div', {}, { left: 0, top: 2100, right: 300, bottom: 2160 }));
fila2.add(new El('div', { _texto: 'Nombre del molde ?' }, { left: 0, top: 2100, right: 200, bottom: 2116 }));
const campo2 = fila2.add(new El('input', {}, { left: 0, top: 2120, right: 300, bottom: 2150 }));
todos.push(fila2, campo2, ...fila2.children);
ok(String(identificar(campo2)).startsWith('txt:nombre del molde'),
   '…y el rótulo de verdad se usa SIN el «?» pegado');

console.log('');
console.log('15 · EL TUTORIAL NUNCA DICE QUE NO ENCUENTRA (regla del usuario 2026-09-01)');
// «este tipo de cartel no quiero más. no me puede decir mas no encuentro. si me esta guiando y el
//  tutorial esta grabado en el sistema debe de saber todo como va a salir»
{
  const src = readFileSync(new URL('./src/tutor.jsx', import.meta.url), 'utf8');
  // el código VIVO: sin comentarios de bloque (`/* … */`, también los `{/* … */}` del JSX) ni de
  // línea — lo que se prohíbe es que la frase vuelva a la PANTALLA, no que se cuente la historia
  const vivo = src.replace(/\/\*[\s\S]*?\*\//g, '').split('\n')
    .filter((l) => !l.trim().startsWith('//')).join('\n');
  ok(!/No encuentro ese lugar/i.test(vivo),
     '🔴 el cartel «No encuentro ese lugar en pantalla» no existe más en el motor');
  ok(!/Buscando ese lugar/i.test(vivo),
     '…ni el «Buscando ese lugar en pantalla» (el sistema sabe a dónde va: dice «Preparando este paso…»)');
  ok(/noAplicaron/.test(src),
     'en su lugar: los pasos que no están en la pantalla se pasan solos y se cuentan para el final');
  ok(/paso\.elige/.test(src),
     'y un puente que exige ELEGIR (abrir una moldería) ofrece saltear, no un «llevame» que no lleva');
}

console.log('');
console.log('16 · EL `#` DEL NOMBRE NO ROMPE EL ANCLA (paso 16/37 de «Cargar molde»)');
// «6XL · pieza #1 — Espalda…» adentro de `visor-molde`: partir por el PRIMER `#` daba una sección
// inventada («1 — espalda…») y el paso no se podía encontrar NUNCA.
{
  const a = 'txt:6xl · pieza #1 — espalda 16xl · pieza #2 — frent#visor-molde';
  const r = partirAncla(a);
  ok(r.seccion === 'visor-molde', '🔴 la sección es lo que va después del ÚLTIMO «#»');
  ok(r.nombre === '6xl · pieza #1 — espalda 16xl · pieza #2 — frent',
     '…y el nombre conserva su propio «#» adentro');
  const s = partirAncla('txt:editar@manga larga#panel-reglas');
  ok(s.nombre === 'editar' && s.ctx === 'manga larga' && s.seccion === 'panel-reglas',
     'con fila y sección a la vez, cada parte en su lugar');
  const u = partirAncla('txt:guardar');
  ok(u.nombre === 'guardar' && !u.seccion && !u.ctx, 'y un ancla simple sigue igual');
}

console.log('');
console.log('');
console.log('17 · EL GESTO QUE SE MUESTRA ES GENÉRICO (decisión del usuario 2026-09-01)');
// «que no muestre el arrastrado real que hacemos cuando grabamos; debe ser un arrastrado genérico
//  que siempre se muestra en la misma parte del campo» — quien sigue el tutorial tiene otro molde y
//  otras piezas: lo que hay que enseñar es EL GESTO, no el recorrido de quien grabó.
const lienzo = raiz.add(new El('div', { 'data-tour': 'visor-molde', 'data-lienzo': '1' },
  { left: 100, top: 200, right: 500, bottom: 400 }));   // 400 × 200
todos.push(lienzo);
{
  const g = gestoGenerico(lienzo);
  ok(!!g, 'hay gesto para mostrar aunque nadie haya grabado un recorrido');
  // 0,22 · 0,28  →  0,75 · 0,78 sobre un elemento de 400×200 que empieza en (100,200)
  ok(Math.abs(g.desde.x - 188) < 1 && Math.abs(g.desde.y - 256) < 1,
     'arranca siempre en el mismo punto del elemento');
  ok(Math.abs(g.hasta.x - 400) < 1 && Math.abs(g.hasta.y - 356) < 1,
     '…y termina siempre en el mismo, cruzando el área en diagonal');
  ok(g.desde.x < g.hasta.x && g.desde.y < g.hasta.y,
     'de arriba-izquierda a abajo-derecha, como se abarca un recuadro');
  // 🔴 LO QUE IMPORTA: en OTRA pantalla el gesto se ve en el MISMO lugar relativo
  const otro = new El('div', {}, { left: 0, top: 0, right: 800, bottom: 600 });
  const g2 = gestoGenerico(otro);
  ok(Math.abs(g2.desde.x / 800 - 0.22) < 0.01 && Math.abs(g2.desde.y / 600 - 0.28) < 0.01
     && Math.abs(g2.hasta.x / 800 - 0.75) < 0.01 && Math.abs(g2.hasta.y / 600 - 0.78) < 0.01,
     '🔴 en un visor más grande cae en la misma proporción (no en los mismos píxeles)');
  ok(gestoGenerico(null) === null, 'sin elemento no se dibuja ningún gesto');
}
{
  ok(esArrastre(10, 10, 60, 10) && esArrastre(10, 10, 10, 60), 'mover 50 px es un arrastre');
  ok(!esArrastre(10, 10, 13, 12), '…y el temblor de un clic NO lo es (no se graba un gesto falso)');
}

console.log();
if (fallos.length) {
  console.log(`  ${fallos.length} FALLO(S) — el localizador no marca lo que hay que marcar`);
  fallos.forEach((f) => console.log('   · ' + f));
  process.exit(1);
}
console.log('  OK: cada columna de la planilla es su propio paso y se ilumina entera');
