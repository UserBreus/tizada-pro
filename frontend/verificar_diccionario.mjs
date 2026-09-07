/**
 * CONTRATO DEL DICCIONARIO — `node verificar_diccionario.mjs` (corre solo en cada `npm run build`).
 *
 * Reemplaza a `verificar_guias.mjs`, que verificaba los guiones fijos de `guias.js` (eliminados
 * 2026-08-27: ahora los tutoriales los GRABA el usuario).
 *
 * La regla que protege: **el sistema escribe los carteles del tutorial**, así que cada elemento
 * que se pueda grabar tiene que tener su explicación. Lo que se verifica:
 *
 *   1. Cada `data-tour` de App.jsx tiene entrada en `diccionario.js`. Sin eso el cartel sale
 *      pobre (cae al texto del botón) y el tutorial pierde el sentido.
 *   2. Ninguna entrada del diccionario sobra (ancla que ya no existe → texto muerto que nadie ve).
 *   3. Cada entrada está COMPLETA: `nombre`, `que` y `como`.
 *   4. El `como` está en imperativo y en criollo (arranca con un verbo de acción, no con «Se…»):
 *      el cartel le habla a la persona.
 *   5. `explicar()` existe y tiene fallback: un elemento sin entrada igual se puede grabar.
 *
 * Falla con código 1 y NO deja compilar: un tutorial con carteles vacíos es peor que no tenerlo.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const leer = (p) => readFileSync(join(AQUI, p), 'utf8');

const fallas = [];
const avisos = [];
const falla = (m) => fallas.push(m);

let app, dic;
try {
  app = leer('src/App.jsx');
  dic = leer('src/diccionario.js');
} catch (e) {
  console.error('✗ no se pudo leer:', e.message);
  process.exit(1);
}

// ── las anclas que hay en la app ────────────────────────────────────────────────────────────
// 🔴 DOS FORMAS de marcar un control, y las dos cuentan: el `data-tour` directo y el que se pasa
// POR PROP a un componente (`<BtnSiguiente ancla="pedido-ir-moldes" …>`, que adentro lo convierte
// en data-tour). Mirar sólo la primera dejaba fuera los 8 botones que mueven el pedido de un paso
// al otro — los mas importantes de cualquier tutorial. Ya habia pasado con el verificador viejo.
const anclas = new Set([
  ...[...app.matchAll(/data-tour=["']([\w:.-]+)["']/g)].map((m) => m[1]),
  ...[...app.matchAll(/\sancla=["']([\w:.-]+)["']/g)].map((m) => m[1]),
]);

// 🔴 TERCERA FORMA: las anclas que se ARMAN (`data-tour={'ajuste-' + item.id}`). Se le escapaban
// enteras al contrato: los 10 ajustes de una moldería —la puerta a TODA la configuración de un
// molde— no tenían explicación y nadie lo cantaba. El tutorial terminaba diciendo «Tocá "Aa"» (el
// ícono del botón) y después «Tocá acá.» (auditoría de Configuración, 2026-09-01).
// Cada familia dinámica se declara acá con DÓNDE están sus ids; si aparece una familia nueva sin
// declarar, el contrato corta.
const FAMILIAS = [
  { prefijo: 'ajuste-', desde: 'Ajustes de la moldería', hasta: '].map(_lock)' },
  { prefijo: 'edit-marca-', desde: 'const MARCAS_PROC = [', hasta: '];', clave: 'k' },
  { prefijo: 'perfil-esp-', desde: 'const ESPACIOS = [', hasta: '];', clave: 'k' },
];
for (const f of FAMILIAS) {
  const i = app.indexOf(f.desde);
  const j = i >= 0 ? app.indexOf(f.hasta, i) : -1;
  if (i < 0 || j < 0) {
    falla(`no encuentro la lista de la familia «${f.prefijo}» en App.jsx (buscaba entre ` +
          `«${f.desde}» y «${f.hasta}»): si cambió de forma, actualizá FAMILIAS acá.`);
    continue;
  }
  const campo = f.clave || 'id';
  const rx = new RegExp('\\{\\s*' + campo + ":\\s*'([\\w-]+)'", 'g');
  for (const m of app.slice(i, j).matchAll(rx)) anclas.add(f.prefijo + m[1]);
}
const familiasEnApp = [...new Set([...app.matchAll(/data-tour=\{'([\w:-]+)'\s*\+/g)].map((m) => m[1]))];
const sinDeclarar = familiasEnApp.filter((p2) => !FAMILIAS.some((f) => f.prefijo === p2));
if (sinDeclarar.length) {
  falla(`familia(s) de anclas dinámicas sin declarar en el contrato: ${sinDeclarar.join(', ')} — ` +
        `agregalas a FAMILIAS o sus explicaciones nunca se van a verificar.`);
}

// ── las entradas del diccionario (con su contenido) ─────────────────────────────────────────
const entradas = new Map();
const re = /^ {2}'([\w:.-]+)':\s*\{([\s\S]*?)^ {2}\},$/gm;
for (const m of dic.matchAll(re)) entradas.set(m[1], m[2]);

console.log(`  anclas en la app: ${anclas.size} · entradas en el diccionario: ${entradas.size}`);

// 1 · nada sin explicación
const sinExplicar = [...anclas].filter((a) => !entradas.has(a)).sort();
if (sinExplicar.length) {
  falla(`${sinExplicar.length} elemento(s) SIN explicación en diccionario.js — el tutorial les ` +
        `pondría un cartel pobre:\n     ${sinExplicar.join(', ')}`);
}

// 2 · nada de sobra
// Las claves `txt:…` (controles sin data-tour, por su texto) y `modal:…` (explicaciones de
// modales) no son anclas del JSX, así que acá no cuentan como sobrantes.
const sobran = [...entradas.keys()].filter((a) => !a.startsWith('txt:') && !a.startsWith('modal:')
  && !a.startsWith('col:') && !anclas.has(a)).sort();
if (sobran.length) {
  falla(`${sobran.length} entrada(s) del diccionario ya no existen en la app (texto muerto):\n` +
        `     ${sobran.join(', ')}`);
}

// 3 y 4 · cada entrada, completa y hablándole a la persona
const ARRANQUE_PASIVO = /^(se |el |la |los |las |acá |aca |es |son )/i;
for (const [clave, cuerpo] of entradas) {
  const campo = (n) => {
    const m = cuerpo.match(new RegExp(`${n}:\\s*'((?:[^'\\\\]|\\\\.)*)'`));
    return m ? m[1].trim() : '';
  };
  const nombre = campo('nombre');
  const que = campo('que');
  const como = campo('como');
  if (!nombre) falla(`«${clave}» no dice cómo se llama en pantalla (nombre)`);
  if (!que) falla(`«${clave}» no explica PARA QUÉ es (que)`);
  if (!como) falla(`«${clave}» no dice QUÉ HAY QUE HACER (como)`);
  if (como && ARRANQUE_PASIVO.test(como)) {
    avisos.push(`«${clave}» → el cartel arranca pasivo («${como.slice(0, 40)}…»); tiene que ` +
                `decirle a la persona qué hacer`);
  }
  if (que && que.length < 25) {
    avisos.push(`«${clave}» → la explicación es muy corta para servir de ayuda: «${que}»`);
  }
}

// 5 · el fallback, que es lo que permite grabar sobre un elemento todavía sin explicar
if (!/export function explicar\(/.test(dic)) {
  falla('falta `explicar()` en diccionario.js: sin ella, un elemento sin entrada rompería el tutorial');
}
if (!/DICCIONARIO\[ancla\]/.test(dic) || !/if \(d\) return d;/.test(dic)) {
  falla('`explicar()` no cae al texto del botón cuando el ancla no está en el diccionario');
}

// ── 6 · LOS PASOS INTELIGENTES, EJECUTADOS DE VERDAD ────────────────────────────────────────
// `diccionario.js` es JS plano (sin React), asi que se puede IMPORTAR y CORRER cada regla. Esto
// vale mucho mas que leerlas: una regla que mira un campo que no existe no explota, devuelve
// `undefined` y el paso se saltea (o no) SIN QUE NADIE SE ENTERE.
const { DICCIONARIO: D } = await import('./src/diccionario.js');

// El estado que arma App.jsx (`ayudaEstado`). Dos fotos: pedido recién empezado y pedido listo.
const VACIO = { cargado: true, nMoldes: 0,
  pedido: { nDisenos: 0, sinVariable: 0, artesTotal: 0, artesCargadas: 0, telasFaltan: 0,
            nFilas: 0, hayResultados: false, editorAbierto: false, nEditables: 0, fuentesFaltan: 1 } };
const LISTO = { cargado: true, nMoldes: 3,
  pedido: { nDisenos: 2, sinVariable: 0, artesTotal: 2, artesCargadas: 2, telasFaltan: 0,
            nFilas: 12, hayResultados: true, editorAbierto: false, nEditables: 4, fuentesFaltan: 0 } };
const campos = new Set(Object.keys(LISTO.pedido));
let nListo = 0, nCuantos = 0;
for (const [clave, e] of Object.entries(D)) {
  if (typeof e.listo === 'function') {
    nListo++;
    for (const [tag, E] of [['vacio', VACIO], ['listo', LISTO]]) {
      let r;
      try { r = e.listo(E); } catch (err) { falla(`«${clave}».listo explota con el pedido ${tag}: ${err.message}`); continue; }
      if (typeof r !== 'boolean') falla(`«${clave}».listo no devuelve true/false con el pedido ${tag} (dio ${r})`);
    }
    // una regla que da lo mismo en los dos extremos no está mirando nada util
    try {
      if (e.listo(VACIO) === e.listo(LISTO)) {
        avisos.push(`«${clave}».listo da lo mismo con el pedido vacio y con el terminado: revisar que mire lo que cree`);
      }
    } catch { /* ya se reporto arriba */ }
  }
  if (e.cuantos) {
    nCuantos++;
    if (!e.cuantos.pregunta) falla(`«${clave}».cuantos no tiene la pregunta para la persona`);
    if (typeof e.cuantos.mide !== 'function') falla(`«${clave}».cuantos no dice de donde sale la cuenta (mide)`);
    else {
      try {
        const a = e.cuantos.mide(VACIO), b = e.cuantos.mide(LISTO);
        if (typeof a !== 'number' || typeof b !== 'number') falla(`«${clave}».cuantos.mide no devuelve un numero`);
      } catch (err) { falla(`«${clave}».cuantos.mide explota: ${err.message}`); }
    }
  }
}

// ⚠ OJO con el `\b`: dentro de una PLANTILLA de JS es un BACKSPACE, no un limite de
// palabra. Por eso el regex se arma con comillas y concatenacion. Ya paso dos veces.
// 🔴 que los campos que miran las reglas EXISTAN en `ayudaEstado`. Si no, la regla lee `undefined`
// y el paso se saltea o insiste sin motivo, en silencio.
const usados = new Set([...dic.matchAll(/E\.pedido\.(\w+)/g)].map((m) => m[1]));
const inventados = [...usados].filter((c) => !campos.has(c)).sort();
if (inventados.length) {
  falla(`las reglas miran campos que no existen en el estado: ${inventados.join(', ')}`);
}
const enApp = leer('src/App.jsx');
for (const c of usados) {
  if (!new RegExp('\\b' + c + ':').test(enApp)) {
    falla(`«${c}» lo miran las reglas pero App.jsx no lo pone en \`ayudaEstado\``);
  }
}
console.log(`  reglas: ${nListo} «saltear si ya esta» · ${nCuantos} «preguntar cuantas»`);

// ── 7 · LA BARRA LATERAL NO APARECE EN LOS TUTORIALES ───────────────────────────────────────
// Pedido del usuario. Son DOS candados y hacen falta los dos: si se cae uno, la barra vuelve a
// salir por ese lado y nadie se entera hasta ver un tutorial que arranca con «tocá Pedidos».
const tut = leer('src/tutor.jsx');
// 🔴 El filtro vive en `sePuedeGrabar` (localizar.js) — UN solo criterio para el grabador y para
// el «⏺ Agregar pasos» del editor. Antes cada uno tenía el suyo y el editor anotaba pasos que el
// grabador descarta (se vio 2026-08-31: agregó un «tocá Configuración» de la barra).
const loc = leer('src/localizar.js');
if (!/export function sePuedeGrabar/.test(loc) || !/closest\('aside\.sidebar'\)/.test(loc)) {
  falla('`sePuedeGrabar` ya no ignora la barra lateral: los tutoriales van a arrancar con «tocá Pedidos»');
}
for (const [archivo, src] of [['App.jsx (grabador)', app], ['tutor.jsx (editor)', tut]]) {
  if (!/sePuedeGrabar\(/.test(src)) {
    falla(`${archivo} no usa \`sePuedeGrabar\`: va a grabar cosas que el otro descarta`);
  }
}
if (!/startsWith\('nav-'\)/.test(tut) || !/llevarSolo/.test(tut)) {
  falla('el motor volvió a MARCAR la barra lateral en vez de cambiar de sección solo');
}

// ── 8 · EL TUTORIAL RESPETA LOS CARTELES DE CARGA ───────────────────────────────────────────
// Mientras hay una carga en pantalla no se avanza: se marca el cartel y se pide esperar.
if ((app.match(/data-cargando=/g) || []).length < 3) {
  falla('quedan menos de 2 superficies de carga marcadas con data-cargando (el overlay de ' +
        'Procesando, Armando la tizada y Poniendo el diseño): el tutorial va a avanzar por encima de una carga');
}
if (!/useCargando/.test(tut) || !/esEspera/.test(tut)) {
  falla('el motor ya no respeta los carteles de carga (useCargando / esEspera)');
}
// …y los MODALES: todos pasan por el componente Modal, que los marca; el motor frena ante uno
// ajeno al paso y lo explica. Si se cae cualquiera de las dos mitades, el tutorial les pasa por
// encima (paso: saltó al siguiente diseño con el aviso del perfil de color abierto).
if (!/data-modal=\{titulo/.test(app)) {
  falla('el componente Modal ya no marca los modales con data-modal: el tutorial les va a pasar por encima');
}
if (!/useModalAbierto/.test(tut) || !/bloqueoModal/.test(tut)) {
  falla('el motor ya no frena ante los modales (useModalAbierto / bloqueoModal)');
}

// ── 9 · LOS AVISOS CONOCIDOS EXISTEN DE VERDAD ──────────────────────────────────────────────
// El editor ofrece estos títulos para el paso «esperar aviso»: si alguien renombra un modal en
// App.jsx y no toca la lista, el paso esperaría un aviso que ya no existe — para siempre.
const { AVISOS_CONOCIDOS } = await import('./src/diccionario.js');
for (const tt of [...AVISOS_CONOCIDOS.modales, ...AVISOS_CONOCIDOS.cargas]) {
  if (!app.includes(tt)) falla(`el aviso «${tt}» de AVISOS_CONOCIDOS ya no existe en App.jsx`);
}
console.log(`  avisos conocidos: ${AVISOS_CONOCIDOS.modales.length} modales · ${AVISOS_CONOCIDOS.cargas.length} cargas`);

// ── 8b · NINGÚN CONTROL SIN NOMBRE (si no tiene nombre, no se puede grabar) ─────────────────
// 🔴 Pedido del usuario (2026-08-31): «que todo mini botón, espacio de trabajo, espacio de
// rellenar, todo lo manipulable sea grabable». El localizador identifica un control por su
// `data-tour` o por su NOMBRE (aria-label, title, texto, placeholder). Un botón que sólo tiene un
// ícono no tiene ninguno: no se puede grabar ni volver a encontrar. La auditoría sobre la app
// encontró 3 (el lápiz de renombrar una moldería, el tacho de borrar una planilla y el
// interruptor `Switch`); acá se vigila que no vuelvan a aparecer.
{
  const mudos = [];
  let i = 0;
  while ((i = app.indexOf('<button', i)) >= 0) {
    const fin = app.indexOf('</button>', i);
    if (fin < 0) break;
    const bloque = app.slice(i, fin);
    // el tag de apertura termina en el primer '>' que NO esté dentro de llaves (`style={{…}}`)
    let d = 0, cierre = -1;
    for (let k = 0; k < bloque.length; k++) {
      const ch = bloque[k];
      if (ch === '{') d++; else if (ch === '}') d--; else if (ch === '>' && d === 0) { cierre = k; break; }
    }
    if (cierre < 0) { i = fin + 9; continue; }
    const apertura = bloque.slice(0, cierre);
    const cuerpo = bloque.slice(cierre + 1);
    const tieneNombre = /title=|aria-label=|data-tour=/.test(apertura);
    // sacando el ícono, ¿queda algún texto (literal o dinámico)?
    const resto = cuerpo.replace(/<Icon[^>]*\/>/g, '').replace(/<svg[\s\S]*?<\/svg>/g, '')
      .replace(/<[^>]*>/g, '').replace(/[\s{}()]/g, '').trim();
    if (!tieneNombre && !resto) mudos.push(app.slice(0, i).split('\n').length);
    i = fin + 9;
  }
  if (mudos.length) {
    falla(`${mudos.length} botón(es) de sólo ícono SIN nombre (línea ${mudos.join(', ')}): `
      + 'ponerles `title` — sin nombre no se pueden grabar en un tutorial ni volver a encontrar');
  }
  console.log(`  controles sin nombre: ${mudos.length}`);
}

// ── 9a · LOS CARTELES NOMBRAN BOTONES QUE EXISTEN ───────────────────────────────────────────
// 🔴 «Tocá «Ver telas de pieza»» mientras el botón decía «Asignar telas» (reporte del usuario
// 2026-08-31): la persona busca en la pantalla algo que no está y el tutorial se vuelve inútil.
// Un nombre entre comillas en un cartel tiene que aparecer TAL CUAL en App.jsx. Los que no son
// botones sino EJEMPLOS de datos van exentos, con nombre y apellido: si la lista crece sin
// control, el candado deja de servir.
const EJEMPLOS = new Set([
  'con capucha',        // ejemplo de nombre de variable
  'sin giro',           // ejemplo de regla de nesting
  'capucha = sí',       // ejemplo de regla de planilla
]);
// El texto de un botón puede estar partido en el JSX (`← {texto}`), así que también se acepta
// que exista sin su flecha inicial.
const enLaApp = (t) => app.includes(t) || (t.startsWith('← ') && app.includes(t.slice(2)));
let citados = 0;
for (const [clave, cuerpo] of entradas) {
  for (const m of cuerpo.matchAll(/«([^»]{2,40})»/g)) {
    const nombre = m[1];
    if (EJEMPLOS.has(nombre)) continue;
    citados++;
    if (!enLaApp(nombre)) {
      falla(`«${clave}» manda a tocar «${nombre}», que NO existe en la app — ¿le cambiaron el nombre al botón?`);
    }
  }
}
// …y lo mismo con los carteles de NAVEGACIÓN («Volvé a la planilla con «← Planilla»»), que no
// están en el diccionario sino en las RUTAS de tutor.jsx. Ahí apareció otro nombre viejo.
const tutor = leer('src/tutor.jsx');
for (const m of tutor.matchAll(/texto: '([^']*«[^»]{2,40}»[^']*)'/g)) {
  for (const c of m[1].matchAll(/«([^»]{2,40})»/g)) {
    const nombre = c[1];
    if (EJEMPLOS.has(nombre) || nombre === 'Siguiente →') continue;   // el «Siguiente» es del globo
    citados++;
    if (!enLaApp(nombre)) {
      falla(`un cartel de navegación manda a tocar «${nombre}», que NO existe en la app`);
    }
  }
}
console.log(`  nombres de controles citados en los carteles: ${citados}`);

// ── 9c · LAS ANCLAS DE LAS RUTAS EXISTEN, Y SE SABEN EXPLICAR ───────────────────────────────
// Las RUTAS de `tutor.jsx` son el CAMINO: lo que el tutorial marca para llevarte de una pantalla a
// otra («Abrí una moldería», «Volvé a los moldes»). Si una de esas anclas no existe en la app, el
// puente no encuentra nada que marcar y el tutorial MUERE ahí: no hay forma de avanzar. Pasó en
// Configuración (2026-09-01): no había ninguna ruta para volver a la lista de molderías, así que
// quien quedaba dentro de una se quedaba sin tutorial.
let rutas = 0;
for (const m of tutor.matchAll(/ancla:\s*'([\w:.-]+)'/g)) {
  const a = m[1];
  if (a.includes('${') || a.startsWith('ajuste-')) continue;   // las de los ajustes se arman solas
  rutas++;
  if (!anclas.has(a)) {
    falla(`la RUTA usa el ancla «${a}», que NO está en la app: ese puente no marcaría nada y el ` +
          `tutorial se quedaría trabado sin salida.`);
  } else if (!entradas.has(a)) {
    falla(`la RUTA usa el ancla «${a}», que no tiene explicación en el diccionario.`);
  }
}
console.log(`  anclas de los caminos (RUTAS) verificadas: ${rutas}`);

// ── 9b · LAS COLUMNAS EXPLICADAS EXISTEN EN LA PLANILLA ─────────────────────────────────────
// Un paso de la planilla se ancla a `col:<id de la columna>` para iluminar LA COLUMNA y no la
// tabla entera. Las columnas son configurables por molde: las conocidas se explican acá, y una
// propia del molde (una sisa, una capucha) cae al label. Pero explicar una columna que NO existe
// es texto muerto que nadie va a ver — ya pasó al escribir esto (`variable` y `tela` no son
// columnas de la planilla: la variable se elige por fila y la tela por pieza).
let cols = 0;
for (const clave of [...entradas.keys()].filter((a) => a.startsWith('col:'))) {
  const id = clave.slice(4);
  if (!new RegExp(`id: *'${id}'`).test(app)) falla(`el diccionario explica la columna «${id}», que no existe en la planilla`);
  else cols++;
}
// tienen que marcarla el ENCABEZADO y la CELDA: con uno solo, o no se ilumina la columna
// entera o el clic en una celda vuelve a caer en la tabla (ya pasó al probarlo).
const marcasCol = (app.match(/data-col=\{c\.id\}/g) || []).length;
// y la LISTA de opciones (portal fuera de la tabla) tiene que decir de qué columna es, o el
// tutorial ilumina la columna y deja el desplegable bajo el velo.
if (!/data-col-lista=\{colId/.test(app)) falla("la lista desplegable de una celda ya no marca su columna (data-col-lista): al abrirla queda fuera del resaltado");
if (marcasCol < 2) falla(`la planilla marca su columna en ${marcasCol} lugar(es): hacen falta el <th> y el <td>, `
  + 'si no el paso ilumina la tabla entera en vez de la columna');
console.log(`  columnas de la planilla explicadas: ${cols}`);

// ── 10 · CADA VENTANA TIENE SU FICHA (se puede DIBUJAR, no sólo nombrar) ────────────────────
// El usuario no reconoce una ventana por su nombre: el editor la dibuja con lo que tiene adentro
// y sus botones (`ventana: {contenido, botones, cuando, paso}`), y el tutorial la explica con
// `que`/`como` cuando se abre sola. Sin ficha, la ventana vuelve a ser un nombre suelto.
const { fichaVentana } = await import('./src/diccionario.js');
const PASOS_VALIDOS = ['diseno', 'moldes', 'arte', 'planilla', 'resultados', 'config', 'otro'];
let conFicha = 0;
for (const tt of [...AVISOS_CONOCIDOS.modales, ...AVISOS_CONOCIDOS.cargas]) {
  const f = fichaVentana(tt);
  const esCarga = AVISOS_CONOCIDOS.cargas.includes(tt);
  if (!f.que || !f.como) falla(`la ventana «${tt}» no tiene explicación (que/como) en el diccionario`);
  else if (!f.contenido) falla(`la ventana «${tt}» no se puede DIBUJAR: le falta \`ventana.contenido\``);
  else if (!f.cuando) falla(`la ventana «${tt}» no dice CUÁNDO aparece (\`ventana.cuando\`)`);
  else if (!PASOS_VALIDOS.includes(f.paso)) falla(`la ventana «${tt}» tiene un paso raro: «${f.paso}»`);
  else if (esCarga !== f.trabajo) falla(`la ventana «${tt}»: `
    + (esCarga ? 'es una carga y no está marcada como de trabajo' : 'no es carga pero figura como de trabajo'));
  else conFicha++;
}
console.log(`  ventanas con ficha dibujable: ${conFicha}/${AVISOS_CONOCIDOS.modales.length + AVISOS_CONOCIDOS.cargas.length}`);

// ── resultado ───────────────────────────────────────────────────────────────────────────────
if (avisos.length) {
  console.log('');
  for (const a of avisos) console.log('  ⚠ ' + a);
}
if (fallas.length) {
  console.error('\n✗ DICCIONARIO INCOMPLETO:');
  for (const f of fallas) console.error('   · ' + f);
  process.exit(1);
}
console.log(`  OK: los ${anclas.size} elementos del sistema tienen su explicación` +
            (avisos.length ? ` (${avisos.length} aviso/s arriba)` : ''));
