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
const TOPE_APP = 321;
const resApp = await eslint.lintFiles(['src/App.jsx']);
const nApp = resApp.reduce((n, r) => n + r.messages.filter(
  (m) => m.ruleId === 'no-use-before-define' || m.ruleId === 'no-undef').length, 0);
if (nApp > TOPE_APP) {
  const nuevos = nApp - TOPE_APP;
  console.log(`\n  ${nuevos} caso(s) NUEVO(S) en App.jsx (tope congelado: ${TOPE_APP}, ahora ${nApp}):`);
  for (const r of resApp) {
    for (const m of r.messages.slice(-nuevos - 3)) {
      if (m.ruleId === 'no-use-before-define' || m.ruleId === 'no-undef') {
        console.log(`   · App.jsx:${m.line} — ${m.message}`);
      }
    }
  }
  console.log('\n  Movelo DEBAJO de lo que usa. En App.jsx esto deja la app en «No se pudo cargar».');
  process.exit(1);
}
console.log(`  App.jsx: ${nApp} caso(s) previos (tope ${TOPE_APP}, ninguno nuevo)`);

console.log(`  archivos revisados: ${ARCHIVOS.length}`);
if (casos.length) {
  console.log(`\n  ${casos.length} USO(S) ANTES DE DECLARAR — riesgo de pantalla negra:`);
  for (const c of casos) console.log('   · ' + c);
  console.log('\n  Mové la declaración ARRIBA del primer uso. No alcanza con que «hoy no rompa»:');
  console.log('  basta que alguien lea esa variable durante el render para que se caiga todo.');
  process.exit(1);
}
console.log('  OK: nada se lee antes de declararse ni usa algo que no existe');
