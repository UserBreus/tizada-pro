/**
 * CONTRATO: NADA SE USA ANTES DE DECLARARSE NI SIN EXISTIR — se corre en `npm run build` (y con
 * `node verificar_tdz.mjs`).
 *
 * 🔴 EL CASO QUE LO MOTIVÓ (2026-08-28, reporte del usuario con la pantalla NEGRA al cargar el
 * arte con la ayuda abierta): `const paso = (carga && !modalDelPaso) ? …` leía `modalDelPaso`, que
 * se declaraba 19 líneas más abajo. Leer una `const` antes de su declaración no da `undefined`:
 * tira `ReferenceError: Cannot access 'X' before initialization`, y en React eso NO es un aviso en
 * la consola — se cae el árbol entero y la pantalla queda negra.
 *
 * POR QUÉ NO SALTÓ HASTA QUE LO VIO EL USUARIO: el `&&` corta. Sin ventana de carga a la vista,
 * `modalDelPaso` no se evaluaba nunca y todo andaba. Reventaba SÓLO con una carga en pantalla —
 * justo el momento en que el tutorial tiene que frenar y explicar la espera. Un bug así no lo
 * agarra ningún contrato que no ejecute el componente, pero el linter lo ve leyendo el código.
 *
 * Cubre los archivos del sistema de ayuda, que es donde se editó. `App.jsx` queda afuera a
 * propósito: arrastra usos previos que no son de esta tanda y taparían lo nuevo (pendiente
 * limpiarlo aparte).
 *
 * 🔴 EL AGUJERO QUE TUVO ESTE CANDADO (2026-09-18). Para `App.jsx` contaba JUNTAS dos reglas muy
 * distintas contra un tope congelado (321): «usado antes de declarar» (casi siempre inofensivo: 300
 * y pico heredados) y «NO EXISTE» (`no-undef`, que SIEMPRE es un bug). En una tanda se borró código
 * de `App.jsx`, la cuenta de los inofensivos bajó a 304 y un `_esB` que no existía en ese lugar
 * (`asignarTodasLasVariantes`) entró por debajo del tope sin que nada saltara: el build compiló,
 * se publicó, y al cargar un diseño salía «_esB is not defined». Un tope sobre una SUMA no distingue
 * «saqué uno inofensivo y metí un bug». Ahora:
 *   · `no-undef` es TOLERANCIA CERO y se mira en TODO `src` (antes: 4 archivos + la suma de App.jsx);
 *   · el tope de `App.jsx` cuenta SÓLO «usado antes de declarar», y se bajó a lo que hay hoy.
 *
 * ⚠️ Usa `eslint.tdz.config.mjs`, no el `eslint.config.js` del proyecto: ese hoy NO ARRANCA
 * (`reactHooks.configs.flat.recommended` es undefined con la versión instalada del plugin), o sea
 * `npm run lint` está roto — otra cosa para arreglar, pero este candado no puede depender de eso.
 */
import { ESLint } from 'eslint';

const ARCHIVOS = ['src/tutor.jsx', 'src/guion.js', 'src/localizar.js', 'src/diccionario.js'];

const eslint = new ESLint({ overrideConfigFile: 'eslint.tdz.config.mjs' });
const res = await eslint.lintFiles(ARCHIVOS);

const casos = [];
for (const r of res) {
  for (const m of r.messages) {
    if (m.ruleId === 'no-use-before-define' || m.ruleId === 'no-undef') {
      casos.push(`${r.filePath.split(/[\\/]/).pop()}:${m.line} — ${m.message}`);
    }
  }
}

// ── App.jsx: TOPE CONGELADO ─────────────────────────────────────────────────────────────────
// 🔴 Es el archivo donde más caro sale este error (2026-08-31: un `useMemo` que usaba
// `cantidadVisible`, declarado 20 líneas más abajo → «No se pudo cargar la aplicación»). Pero
// arrastra 321 casos previos, casi todos inofensivos (handlers que se leen dentro de callbacks,
// no durante el render). Arreglarlos todos de una es otra tarea; mientras tanto se congela la
// cuenta: uno nuevo CORTA EL BUILD.
// ⚠️ Si limpiás alguno, BAJÁ el tope. Nunca subirlo para «que pase».
// 🔴 SÓLO cuenta «usado antes de declarar». Lo que NO EXISTE (`no-undef`) va aparte, más abajo, con
// tolerancia cero: mezclarlos en una suma dejó pasar un bug (ver el encabezado).
const TOPE_APP = 301;
const resApp = await eslint.lintFiles(['src/App.jsx']);
const nApp = resApp.reduce((n, r) => n + r.messages.filter(
  (m) => m.ruleId === 'no-use-before-define').length, 0);
if (nApp > TOPE_APP) {
  const nuevos = nApp - TOPE_APP;
  console.log(`\n  ${nuevos} caso(s) NUEVO(S) en App.jsx (tope congelado: ${TOPE_APP}, ahora ${nApp}):`);
  for (const r of resApp) {
    for (const m of r.messages.slice(-nuevos - 3)) {
      if (m.ruleId === 'no-use-before-define') {
        console.log(`   · App.jsx:${m.line} — ${m.message}`);
      }
    }
  }
  console.log('\n  Movelo DEBAJO de lo que usa. En App.jsx esto deja la app en «No se pudo cargar».');
  process.exit(1);
}
console.log(`  App.jsx: ${nApp} caso(s) previos de «usado antes de declarar» (tope ${TOPE_APP}, ninguno nuevo)`);

// ── LO QUE NO EXISTE: TOLERANCIA CERO, EN TODO `src` ───────────────────────────────────────
// Un nombre que no existe no es «deuda»: es un `ReferenceError` esperando a que alguien pase por
// esa línea (un handler, un `catch`, un camino poco usado). No hay tope que valga.
const resTodo = await eslint.lintFiles(['src']);
const inexistentes = [];
for (const r of resTodo) {
  const f = r.filePath.split(/[\\/]src[\\/]/).pop();
  for (const m of r.messages) if (m.ruleId === 'no-undef') inexistentes.push(`${f}:${m.line} — ${m.message}`);
}
if (inexistentes.length) {
  console.log(`\n  ${inexistentes.length} NOMBRE(S) QUE NO EXISTEN — revienta con «X is not defined» cuando se pase por ahí:`);
  for (const c of inexistentes) console.log('   · ' + c);
  console.log('\n  No es un aviso: declaralo, importalo o usá el que sí existe en ese lugar.');
  process.exit(1);
}
console.log(`  nada usa un nombre que no existe (${resTodo.length} archivos de src)`);

console.log(`  archivos revisados: ${ARCHIVOS.length}`);
if (casos.length) {
  console.log(`\n  ${casos.length} USO(S) ANTES DE DECLARAR — riesgo de pantalla negra:`);
  for (const c of casos) console.log('   · ' + c);
  console.log('\n  Mové la declaración ARRIBA del primer uso. No alcanza con que «hoy no rompa»:');
  console.log('  basta que alguien lea esa variable durante el render para que se caiga todo.');
  process.exit(1);
}
console.log('  OK: nada se lee antes de declararse ni usa algo que no existe');
