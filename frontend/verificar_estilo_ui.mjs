/**
 * CONTRATO DE ESTILO DE LA INTERFAZ — se corre solo en `npm run build` (y con `node
 * verificar_estilo_ui.mjs`). Vigila las reglas de CSS que, cuando se caen, rompen la pantalla EN
 * SILENCIO: nada explota, simplemente algo se vuelve ilegible y nadie se entera hasta que un
 * usuario manda una captura.
 *
 * 🔴 LOS DESPLEGABLES (2026-08-28). La lista que se abre al tocar un `<select>` la dibuja el
 * SISTEMA OPERATIVO, no la app. Sin `color-scheme: dark` en la página, Windows la pinta con el
 * tema CLARO (fondo blanco) mientras las `option` heredan el `color` casi blanco del tema oscuro
 * → texto blanco sobre blanco: la lista se veía VACÍA y sólo se leía la opción bajo el mouse.
 * Afectaba a TODOS los desplegables del sistema a la vez, por eso el arreglo (y este candado)
 * viven en el CSS global y no en un componente.
 */
import fs from 'node:fs';

const css = fs.readFileSync(new URL('./src/index.css', import.meta.url), 'utf8');
const fallos = [];

function ok(cond, msg) {
  if (!cond) fallos.push(msg);
  console.log((cond ? '  OK   ' : '  FALLA') + ' ' + msg);
}

// sin comentarios, para no dar por buena una regla que quedó comentada
const vivo = css.replace(/\/\*[\s\S]*?\*\//g, '');

console.log('\n1 · Los desplegables nativos se ven sobre fondo oscuro');
ok(/:root\s*\{[^}]*color-scheme\s*:\s*dark/.test(vivo),
   '🔴 la página declara `color-scheme: dark` (si no, el popup del <select> sale BLANCO)');
ok(/select\s+option\s*\{[^}]*background-color\s*:/.test(vivo),
   '🔴 las `option` tienen fondo propio (respaldo si el navegador ignora color-scheme)');
ok(/select\s+option\s*\{[^}]*[^-]color\s*:/.test(vivo),
   '🔴 las `option` tienen color de texto propio');
ok(/select\s+optgroup\s*\{[^}]*background-color\s*:/.test(vivo),
   'los grupos (`optgroup`) también, que se usan en el editor de tutoriales');

// el tema es oscuro fijo: si algún día hay tema claro, `color-scheme` tiene que acompañarlo
console.log('\n2 · Coherencia con el tema');
ok(/--bg-primary\s*:\s*#000/.test(vivo),
   'el tema sigue siendo oscuro (si cambia, revisar `color-scheme`)');

console.log();
if (fallos.length) {
  console.log(`  ${fallos.length} FALLO(S) — el estilo de la interfaz se rompió`);
  fallos.forEach((f) => console.log('   · ' + f));
  process.exit(1);
}
console.log('  OK: los desplegables del sistema se abren legibles');
