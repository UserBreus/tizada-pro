/**
 * CONTRATO DE LA AYUDA GUIADA — se corre en cada `npm run build`.
 *
 * PARA QUÉ: el motor de la ayuda (`src/tutor.jsx`) ilumina elementos buscándolos por
 * `data-tour="…"`. Si alguien renombra, mueve o borra un control, la guía que lo usaba se rompe
 * EN SILENCIO: el usuario ve «No encuentro ese lugar en pantalla» recién a los 5 segundos, y nadie
 * se entera hasta que se queja. Este chequeo hace que eso NO PUEDA LLEGAR AL BUILD.
 *
 * QUÉ CHEQUEA:
 *   1. que TODA ancla que piden los guiones (`ancla` + `tambien`) y la tabla `RUTAS` exista en el JSX;
 *   2. que los pasos estén bien formados (acción conocida, texto, y que los 'gesto' sepan verificarse);
 *   3. que los predicados `hecho(E, E0)` no exploten y digan la verdad en los casos que importan
 *      —sobre todo: NO dar por hecho lo que el usuario todavía no hizo, y NO avanzar si el
 *      guardado falló—;
 *   4. que ninguna guía lleve al usuario a un paso del pedido al que no se pueda llegar.
 *
 * ⚠️ POR QUÉ NO ALCANZA CON BUSCAR `data-tour="x"`: hay anclas que NO son literales,
 *      · dinámicas    → `data-tour={'ajuste-' + item.id}`     (una por ítem del menú de ajustes)
 *      · condicionales→ `data-tour={i === 0 ? 'perfil-card' : undefined}`
 *    Un chequeo ingenuo las da por faltantes (probado: 9 falsos positivos). Por eso se leen las
 *    TRES formas: literal, cualquier string dentro de una expresión `{…}` y los PREFIJOS de
 *    concatenación (`'ajuste-' + …` habilita cualquier ancla que empiece con `ajuste-`).
 *
 * Correr suelto:  npm run guias
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const SRC = join(AQUI, 'src');

const leer = (f) => {
  try { return readFileSync(join(SRC, f), 'utf8'); }
  catch (e) { console.error(`✗ no se pudo leer src/${f}: ${e.message}`); process.exit(2); }
};

const guias = leer('guias.js');
const app = leer('App.jsx');
const tutor = leer('tutor.jsx');

// ── 1. Lo que PIDEN los guiones ────────────────────────────────────────────────────────────────
const pedidas = new Map();      // ancla -> cuántas veces se pide
const anota = (a) => pedidas.set(a, (pedidas.get(a) || 0) + 1);
for (const m of guias.matchAll(/\bancla:\s*'([^']+)'/g)) anota(m[1]);
for (const m of guias.matchAll(/\btambien:\s*\[([^\]]*)\]/g)) {
  for (const t of m[1].matchAll(/'([^']+)'/g)) anota(t[1]);
}
// Las anclas que el propio motor usa para llevar de una pantalla a otra (tabla RUTAS) también
// tienen que existir, si no el «te llevo hasta ahí» apunta a la nada.
const rutas = tutor.slice(tutor.indexOf('const RUTAS'), tutor.indexOf('/** La ruta puede depender'));
for (const m of rutas.matchAll(/\bancla:\s*'([^']+)'/g)) anota(m[1]);

// ── 2. Lo que EXISTE en la app ─────────────────────────────────────────────────────────────────
const existen = new Set();      // anclas literales
const prefijos = new Set();     // prefijos de concatenación: `data-tour={'ajuste-' + item.id}`
for (const m of app.matchAll(/data-tour=(?:"([^"]+)"|\{([^}]*)\})/g)) {
  if (m[1]) { existen.add(m[1]); continue; }
  const expr = m[2] || '';
  // cualquier string literal dentro de la expresión cuenta como ancla posible…
  for (const s of expr.matchAll(/'([^']*)'|"([^"]*)"/g)) {
    const v = s[1] ?? s[2];
    if (v) existen.add(v);
  }
  // …y si la expresión CONCATENA (`'ajuste-' + item.id`), el string es un PREFIJO.
  for (const s of expr.matchAll(/'([^']*)'\s*\+/g)) if (s[1]) prefijos.add(s[1]);
}
// El texto del prefijo (`ajuste-`) NO es un ancla real: se saca para no reportarlo como «sin usar».
for (const p of prefijos) existen.delete(p);

const cubre = (a) => existen.has(a) || [...prefijos].some(p => a.startsWith(p) && a.length > p.length);

// ── 3. Veredicto de las anclas ─────────────────────────────────────────────────────────────────
const faltan = [...pedidas.keys()].filter(a => !cubre(a)).sort();
const sinUsar = [...existen].filter(a => !pedidas.has(a)).sort();

console.log(`ayuda guiada · ${pedidas.size} anclas pedidas · ${existen.size} en App.jsx` +
  (prefijos.size ? ` (+${prefijos.size} prefijo/s dinámico/s: ${[...prefijos].join(', ')})` : ''));
if (sinUsar.length) {
  // No es error: hay controles marcados que ninguna guía usa hoy (quedaron de guías anteriores y
  // sirven si mañana se suma otra). Se listan para que la lista no crezca sin que nadie mire.
  console.log(`  · ${sinUsar.length} marcadas en la app que la guía no usa (no es error)`);
}

if (faltan.length) {
  console.error('\n✗ AYUDA ROTA — estas anclas las pide la guía y NO existen en src/App.jsx:\n');
  for (const a of faltan) console.error(`    data-tour="${a}"`);
  console.error('\n  Arreglo: o le ponés ese `data-tour` al control en App.jsx, o corregís el');
  console.error('  `ancla` en src/guias.js. Una guía que apunta a la nada deja al usuario esperando.\n');
  process.exit(1);
}
console.log('✓ todas las anclas de la ayuda existen');

// ══ 4. PASOS Y PREDICADOS ═════════════════════════════════════════════════════════════════════
const { GUIAS, GUIA_PRINCIPAL, RECORRIDOS, AREAS } = await import('./src/guias.js');

const errores = [];
const avisos = [];
const ok = (cond, msg) => { if (!cond) errores.push(msg); };

/** Estado de ayuda de juguete: un pedido completo. Se pisa lo que interese con `con()`. */
const E_BASE = () => ({
  cargado: true, tab: 'pedidos', sub: 'dashboard', paso: 'moldes', ajuste: 'menu',
  moldeAbierto: false, nMoldes: 1,
  pedido: { nDisenos: 1, sinVariable: 0, artesTotal: 1, artesCargadas: 1, telasFaltan: 0, nFilas: 3,
    hayResultados: true, editorAbierto: false, nEditables: 1 },
});
const con = (patch) => { const E = E_BASE(); Object.assign(E.pedido, patch.pedido || {}); return E; };
const E_VACIO = { pedido: {} };

// 4.a — ESTRUCTURA
const ACCIONES = new Set(['click', 'input', 'ver', 'gesto']);
const ids = new Set();
ok(GUIAS.length >= 1 && !!GUIA_PRINCIPAL, 'no hay guía principal');
for (const g of GUIAS) {
  ok(!ids.has(g.id), `id de guía repetido: «${g.id}»`); ids.add(g.id);
  ok(g.pasos && g.pasos.length, `guía «${g.id}» sin pasos`);
  ok(!!g.titulo && !!g.desc, `guía «${g.id}» sin título o descripción (se muestran al arrancar)`);
  g.pasos.forEach((p, i) => {
    ok(ACCIONES.has(p.accion), `guía «${g.id}» paso ${i + 1}: acción desconocida «${p.accion}»`);
    ok(!!p.texto, `guía «${g.id}» paso ${i + 1}: sin texto`);
    // Un 'gesto' sin `hecho` cae al avance por TIEMPO, que es justo lo que se vino a arreglar:
    // el trabajo del visor tiene que verificarse, no cronometrarse.
    ok(!(p.accion === 'gesto' && typeof p.hecho !== 'function'),
      `guía «${g.id}» paso ${i + 1}: es 'gesto' pero no declara hecho() → avanzaría por tiempo`);
    // Robustez: un predicado que explota deja el tutorial colgado.
    if (typeof p.hecho === 'function') {
      try { p.hecho(E_BASE(), E_BASE()); p.hecho(E_VACIO, E_VACIO); }
      catch (e) { errores.push(`guía «${g.id}» paso ${i + 1}: hecho() explota (${e.message})`); }
    }
  });
}

// 4.a-bis — LOS RECORRIDOS SON EXPLICATIVOS: no piden hacer nada.
//   Es la decisión del usuario: un solo paso a paso (armar la tizada) y, para el resto de las
//   pantallas, recorridos que sólo cuentan «para qué sirve cada cosa». Si a uno se le escapa un
//   paso de acción, la persona queda esperando a que le pidan algo que el recorrido no explica.
for (const g of RECORRIDOS) {
  ok(g.explica === true, `el recorrido «${g.id}» no está marcado como explicativo (explica: true)`);
  ok(AREAS.some(a => a.id === g.area), `el recorrido «${g.id}» tiene un área desconocida («${g.area}»)`);
  g.pasos.forEach((p, i) => {
    ok(p.accion === 'ver', `recorrido «${g.id}» paso ${i + 1}: es explicativo, la acción tiene que ser 'ver' (es «${p.accion}»)`);
    ok(typeof p.hecho !== 'function', `recorrido «${g.id}» paso ${i + 1}: un recorrido explicativo no puede exigir que la acción se haga (hecho)`);
  });
}
ok(!GUIA_PRINCIPAL.explica, 'la guía principal quedó marcada como explicativa: dejaría de pedir las acciones');
ok(GUIA_PRINCIPAL.pasos.some(p => p.accion === 'click' || p.accion === 'input' || p.accion === 'gesto'),
  'la guía principal se quedó sin pasos de acción');

// 4.a-ter — TODO DESTINO `ir` TIENE QUE SER ALCANZABLE (si no, el puente apunta a la nada).
//   Se comprueba contra las claves de RUTAS del propio motor.
{
  const rutas = new Set([...tutor.matchAll(/'(tab|sub|paso|molde|ajuste):([a-zA-Z]+)'\s*:/g)].map(m => `${m[1]}:${m[2]}`));
  // las de los ajustes se generan en bloque (`ajuste:${id}`): se leen de esa lista
  for (const m of tutor.matchAll(/\['([a-z]+)', '[^']+'\]/g)) rutas.add(`ajuste:${m[1]}`);
  const CONOCIDAS = new Set(['tab', 'sub', 'paso', 'molde', 'ajuste']);
  for (const g of GUIAS) {
    for (const p of g.pasos) {
      for (const [k, v] of Object.entries(p.ir || {})) {
        ok(CONOCIDAS.has(k), `guía «${g.id}»: el paso pide ir a «${k}», que el motor no sabe qué es`);
        // 'paso:resultados' y el punto de partida no tienen ruta a propósito (ver RUTAS)
        if (k === 'paso' && (v === 'resultados' || v === 'moldes')) continue;
        ok(rutas.has(`${k}:${v}`),
          `guía «${g.id}»: pide ir a «${k}:${v}» y el motor no tiene ruta para llegar → el puente apuntaría a la nada`);
      }
    }
  }
}

// 4.b — NO SACAR AL USUARIO DE SU PEDIDO.
//   El pedido es un wizard EN FILA: a «arte» se llega con la prenda elegida, a «planilla» con el
//   arte cargado y a «resultados» SÓLO generando (no hay botón). Una guía que hace `ir` a esos
//   pasos sin comprobar nada teletransporta a la persona a una pantalla vacía y le arruina el
//   pedido en curso. Por eso: si un paso lleva a un paso del pedido que no sea 'moldes', la guía
//   TIENE que declarar `requiere(E)` (y el motor no la arranca hasta que se cumpla).
const rutasPaso = new Set([...tutor.matchAll(/'paso:([a-z]+)'\s*:/g)].map(m => m[1]));
for (const g of GUIAS) {
  for (const p of g.pasos) {
    const dest = p.ir && p.ir.paso;
    if (!dest || dest === 'moldes') continue;         // 'moldes' es el arranque: siempre se puede
    ok(typeof g.requiere === 'function',
      `guía «${g.id}»: lleva al paso «${dest}» del pedido y no declara requiere() → puede dejar al usuario en una pantalla vacía`);
    if (!rutasPaso.has(dest))
      avisos.push(`guía «${g.id}»: al paso «${dest}» no hay ruta en RUTAS (se llega sólo por el flujo)`);
  }
}

// 4.c — LO QUE TIENEN QUE DECIR LOS `hecho` DE LA GUÍA (el corazón del asunto).
const paso = (ancla) => GUIA_PRINCIPAL.pasos.find(p => p.ancla === ancla && typeof p.hecho === 'function');

{ // agregar el DISEÑO: cuenta que se haya agregado uno NUEVO, no que ya hubiera alguno
  const p = paso('pedido-diseno-agregar');
  ok(!!p, 'el paso de agregar el diseño perdió su hecho()');
  const E0 = con({ pedido: { nDisenos: 1 } });
  ok(p && !p.hecho(E0, E0), 'agregar el diseño se da por hecho sin agregar nada');
  ok(p && p.hecho(con({ pedido: { nDisenos: 2 } }), E0), 'agregar un diseño NO avanza el paso');
}
{ // elegir la PRENDA: es un gesto en la grilla, no hay clic que escuchar
  const p = paso('pedido-variables');
  ok(!!p, 'el paso de elegir la prenda perdió su hecho()');
  ok(p && !p.hecho(con({ pedido: { nDisenos: 1, sinVariable: 1 } }), E_BASE()),
    'se da por elegida la prenda con un diseño sin prenda');
  ok(p && p.hecho(con({ pedido: { nDisenos: 1, sinVariable: 0 } }), E_BASE()),
    'elegir la prenda NO cumple el paso');
}
{ // cargar el ARTE: lo que cuenta es el archivo PROCESADO, no que se abra el explorador
  const p = paso('arte-cargar');
  ok(!!p, 'el paso de cargar el arte perdió su hecho()');
  const E0 = con({ pedido: { artesCargadas: 0 } });
  ok(p && !p.hecho(E0, E0), 'el arte se da por cargado sin haberse procesado');
  ok(p && p.hecho(con({ pedido: { artesCargadas: 1 } }), E0), 'cargar el arte NO avanza el paso');
}
{ // TELAS: no se sigue hasta que TODAS las piezas tengan tela (el sistema tampoco deja)
  const p = paso('telas-panel');
  ok(!!p, 'el paso de asignar telas perdió su hecho()');
  ok(p && !p.hecho(con({ pedido: { telasFaltan: 3 } }), E_BASE()), 'se sigue con piezas sin tela');
  ok(p && p.hecho(con({ pedido: { telasFaltan: 0 } }), E_BASE()), 'con todas las telas puestas NO avanza');
}

// 4.d — EL ORDEN DE LA GUÍA ES EL DEL VIDEO: diseño → prenda → arte → telas → planilla → tizadas.
{
  const orden = GUIA_PRINCIPAL.pasos.map(p => p.ancla);
  const pos = (a) => orden.indexOf(a);
  const secuencia = ['pedido-diseno-input', 'pedido-variables', 'pedido-ir-arte', 'arte-cargar',
    'arte-telas', 'arte-siguiente', 'planilla-tabla', 'planilla-enviar', 'resultados-mesas'];
  for (const a of secuencia) ok(pos(a) >= 0, `la guía perdió el paso «${a}»`);
  for (let i = 1; i < secuencia.length; i++)
    ok(pos(secuencia[i - 1]) < pos(secuencia[i]),
      `la guía quedó desordenada: «${secuencia[i]}» va antes que «${secuencia[i - 1]}»`);
}

// ══ 5. EL GLOBO NO PUEDE TAPAR EL BOTÓN QUE HAY QUE TOCAR ═════════════════════════════════════
// El usuario lo reportó así: «los botones los oculta detrás del resaltado en vez de resaltar».
// La ubicación del globo es una función pura (`tutor_pos.js`) justamente para poder barrer acá
// TODAS las combinaciones: botón en cualquier parte de la pantalla × globos de distinto alto.
{
  const { ubicarGlobo, seSolapan } = await import('./src/tutor_pos.js');
  const pantallas = [[1920, 1080], [1366, 768], [1280, 720], [1024, 600]];
  const globos = [{ w: 374, h: 120 }, { w: 374, h: 190 }, { w: 374, h: 260 }, { w: 374, h: 340 }];
  let casos = 0, tapa = 0, afuera = 0, peor = null;
  for (const [vw, vh] of pantallas) {
    for (const g of globos) {
      // el botón recorre toda la pantalla, incluidas las esquinas y la barra inferior
      for (let x = 0; x <= vw - 160; x += 97) {
        for (let y = 0; y <= vh - 46; y += 61) {
          for (const [w, h] of [[160, 44], [420, 44], [160, 300]]) {
            const rect = { x, y, w, h };
            const p = ubicarGlobo(rect, g, vw, vh, 22, 12);
            // si no entraba, el globo se achica al hueco (`maxAlto`) — se mide con ESE alto
            const caja = { x: p.left, y: p.top, w: g.w, h: p.maxAlto || g.h };
            casos++;
            if (seSolapan(rect, caja)) { tapa++; if (!peor) peor = { vw, vh, g, rect, p }; }
            if (caja.x < 0 || caja.y < 0 || caja.x + caja.w > vw || caja.y + caja.h > vh) afuera++;
          }
        }
      }
    }
  }
  ok(tapa === 0, `el globo tapa el elemento resaltado en ${tapa} de ${casos} casos (ej: ${JSON.stringify(peor)})`);
  ok(afuera === 0, `el globo se sale de la pantalla en ${afuera} de ${casos} casos`);
  // Y con lugar de sobra tiene que ir DEBAJO (es lo natural: leo y después toco).
  const p1 = ubicarGlobo({ x: 500, y: 100, w: 160, h: 44 }, { w: 374, h: 190 }, 1280, 720, 22, 12);
  ok(p1.flecha === 'arriba' && p1.top > 100, 'con lugar abajo el globo no se pone debajo del elemento');
  // Botón en la barra inferior (el caso del pedido): tiene que irse ARRIBA, no taparlo.
  const rb = { x: 1100, y: 660, w: 160, h: 44 };
  const p2 = ubicarGlobo(rb, { w: 374, h: 190 }, 1280, 720, 22, 12);
  ok(!seSolapan(rb, { x: p2.left, y: p2.top, w: 374, h: 190 }), 'el globo tapa el botón de la barra inferior');
  // ── EL LAZO INFINITO (React #185) — que no vuelva ────────────────────────────────────────────
  // Cuando el globo no entra se le pone `maxHeight`. Con `box-sizing: border-box` (regla global de
  // la app) el alto RENDERIZADO pasa a ser exactamente el hueco → si el componente midiera ESE
  // alto, la próxima vuelta «ya entra», se le saca el tope, vuelve a no entrar… y React corta con
  // «Maximum update depth exceeded». Por eso se mide el alto NATURAL (`scrollHeight`).
  // 1) la ubicación tiene que ser un PUNTO FIJO si se la realimenta con el alto natural:
  {
    const g = { w: 374, h: 340 }, vw = 1024, vh = 600, rect = { x: 60, y: 150, w: 900, h: 300 };
    let p = ubicarGlobo(rect, g, vw, vh, 22, 12);
    for (let k = 0; k < 5; k++) {
      const q = ubicarGlobo(rect, g, vw, vh, 22, 12);   // mismo alto natural → misma respuesta
      ok(q.top === p.top && q.left === p.left && q.maxAlto === p.maxAlto,
        'la ubicación del globo no es estable: se movería sola en cada render (lazo infinito)');
      p = q;
    }
    ok(p.maxAlto != null, 'el caso sin lugar dejó de achicar el globo (volvería a taparlo)');
  }
  // 2) y el componente NO puede volver a medir el alto RENDERIZADO. Se mira el CÓDIGO, no los
  //    comentarios (un grep flojo daba OK con sólo mencionar `scrollHeight` en una explicación).
  const codigo = tutor.split('\n')
    .filter(l => !/^\s*(\/\/|\*|\/\*)/.test(l))          // fuera comentarios de línea y de bloque
    .join('\n');
  const medicion = (codigo.match(/const h = [^\n;]+;/) || [''])[0];
  ok(/el\.scrollHeight/.test(medicion),
    `el globo dejó de medirse por su alto NATURAL (scrollHeight) → vuelve el lazo React #185. Línea actual: «${medicion.trim()}»`);
  ok(!/getBoundingClientRect\(\)\.height/.test(medicion),
    'el globo se está midiendo con getBoundingClientRect().height → lazo React #185');
  console.log(`✓ ubicación del globo: ${casos} combinaciones, nunca tapa el elemento ni se sale de la pantalla`);
}

// ── LA VISTA DE TODOS LOS TALLES (el «nido») NO PUEDE QUEDAR APAGADA ──────────────────────────
// El nido es la geometría de las piezas del registro. Se rompió dos veces del mismo modo y el
// síntoma siempre fue el mismo: «tengo que recargar la página para ver todas las variantes».
{
  const app = readFileSync(new URL('./src/App.jsx', import.meta.url), 'utf8');
  const codigo = app.split('\n')
    .filter(l => !/^\s*(\/\/|\*|\/\*)/.test(l))          // sin comentarios: ya pasó que un grep floje
    .join('\n');

  // 1) El efecto que pide el nido TIENE que mirar `nidoData`. Sin eso, `invalidarNido()` lo deja
  //    en null y nadie lo vuelve a pedir mientras no cambie otra dependencia — o sea, nunca si ya
  //    estás adentro de la variable.
  const efecto = (codigo.match(/const necesita = tabAjustesMolde[\s\S]*?\}, \[[^\]]*\]\);/) || [''])[0];
  const deps = (efecto.match(/\}, \[([^\]]*)\]\);/) || ['', ''])[1];
  if (!/\bnidoData\b/.test(deps)) {
    errores.push('el efecto que carga el nido no depende de `nidoData`: al invalidarlo no se vuelve a pedir '
      + `y la vista de todos los talles desaparece hasta recargar la página. Deps actuales: [${deps.trim()}]`);
  }

  // 1.b) Las variables que se pueden elegir en el Pedido NO se filtran por `_moldePropio`.
  //      `propio` lo calcula el server según QUIÉN MIRA (true sólo para el dueño), así que
  //      filtrar por él dejaba al dueño sin poder usar SU PROPIA variable mientras el resto sí.
  //      Reproducido: el dueño veía 0 variables y otro usuario veía 1.
  const catalogo = (codigo.match(/const varsCatalogo = [^\n;]*/) || [''])[0];
  if (/_moldePropio/.test(catalogo)) {
    errores.push('`varsCatalogo` filtra por `_moldePropio`: el DUEÑO de un molde propio se queda sin '
      + `sus propias variables (a los demás sí les aparecen). Línea: «${catalogo.trim()}»`);
  }

  // 1.c) La grilla de Configuración se filtra por `personal`, NUNCA por `propio`. `propio` es
  //      «es MÍO» y lo calcula el server según quién mira: el artículo privado de OTRO llega con
  //      `propio: false` y se cuela en el espacio del taller (pasa con un admin, que por
  //      `molde.ver_todos` ve los ajenos). `personal` no depende del espectador.
  const grilla = (codigo.match(/productosCat\.productos\.filter\([^)]*\)\.map\(\(p, _i\)/) || [''])[0];
  if (grilla && !/\.personal/.test(grilla)) {
    errores.push('la grilla de molderías de Configuración no filtra por `personal`: el artículo '
      + `privado de OTRO usuario se cuela en el espacio del taller. Línea: «${grilla.trim()}»`);
  }

  // 2) Guardar una VARIABLE no puede invalidar el nido: cambia qué piezas se muestran, no su
  //    geometría. `nidoVarPiezas` ya recalcula solo. Invalidarlo acá fue exactamente el bug.
  const guardar = (codigo.match(/const guardarGruposCon = async[\s\S]*?\n  \};/) || [''])[0];
  if (/invalidarNido\(/.test(guardar)) {
    errores.push('`guardarGruposCon` invalida el nido: asignar una pieza a una variable NO cambia su '
      + 'geometría, y tirarlo hace desaparecer la vista de todos los talles hasta recargar');
  }
}

for (const a of avisos) console.log(`  ⚠ ${a}`);
if (errores.length) {
  console.error(`\n✗ LÓGICA DE LA AYUDA ROTA (${errores.length}):\n`);
  for (const e of errores) console.error(`    · ${e}`);
  console.error('');
  process.exit(1);
}
console.log(`✓ la guía «${GUIA_PRINCIPAL.titulo}»: ${GUIA_PRINCIPAL.pasos.length} pasos, en el orden del video`);
