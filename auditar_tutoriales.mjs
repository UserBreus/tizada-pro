/**
 * AUDITOR DE LOS TUTORIALES REALES — `node auditar_tutoriales.mjs [url]`
 *
 * ── POR QUÉ EXISTE ─────────────────────────────────────────────────────────────────────────────
 * Los seis contratos del frontend pasaban con todo en verde y el sistema de tutoriales igual se
 * trababa en la app (auditoría 2026-08-31). El motivo: los contratos prueban el MOTOR con casos
 * de juguete, y lo que falla son los tutoriales GRABADOS con los datos del taller — un botón que
 * decía «Copiar a 1», una tela que se llama «Dry Polo (1,83)», una columna que en esta instalación
 * se llama `dise_o`. Esto agarra el guion REAL, el que la gente va a ver.
 *
 * ── CÓMO SE USA ────────────────────────────────────────────────────────────────────────────────
 *   py srv_visor.py                    (sandbox de sólo lectura con los datos reales, 8060)
 *   node auditar_tutoriales.mjs        → audita http://localhost:8060
 *   node auditar_tutoriales.mjs http://localhost:8050     (el server de verdad; pide sesión)
 *   node auditar_tutoriales.mjs archivo.json              (una exportación guardada)
 *
 * NO ESCRIBE NADA: sólo hace un GET y lee. Sale con código 1 si encuentra algo que va a romper el
 * tutorial (un paso sin ningún lugar que marcar), 0 si sólo hay avisos.
 *
 * Lo que mira, uno por uno, sobre el guion que arma `aGuion` (o sea, lo que se va a ver):
 *   · pasos SIN EXPLICACIÓN (el cartel saldría con el nombre crudo del control);
 *   · anclas ATADAS A LOS DATOS de este taller (números, nombres de moldes o telas);
 *   · anclas por texto SIN SECCIÓN a la que caer si ese control ya no está;
 *   · columnas de la planilla que ninguna regla sabe explicar;
 *   · pasos que quedaron sin ancla (ésos no se pueden mostrar: es un error, no un aviso).
 */
import { readFileSync, existsSync } from 'node:fs';
import { aGuion } from './frontend/src/guion.js';
import { DICCIONARIO } from './frontend/src/diccionario.js';

const arg = process.argv[2] || 'http://localhost:8060';

async function traerTutoriales() {
  if (existsSync(arg)) return JSON.parse(readFileSync(arg, 'utf8'));
  const r = await fetch(arg.replace(/\/$/, '') + '/api/tutoriales');
  if (!r.ok) throw new Error(`el servidor contestó ${r.status} (¿está levantado? ¿pide sesión?)`);
  const d = await r.json();
  return d.tutoriales || [];
}

const CON_DATOS = /\d|·|«|»/;                 // números, nombres de molde, comillas de un dato
const errores = [];
const avisos = [];

const tuts = await traerTutoriales().catch((e) => { console.error('  ✗ ' + e.message); process.exit(2); });
console.log(`\nAUDITORÍA DE ${tuts.length} TUTORIAL(ES) GRABADO(S) — ${arg}`);

for (const t of tuts) {
  const g = aGuion(t);
  if (!g) continue;
  console.log(`\n══ «${g.titulo}» — ${(t.pasos || []).length} grabados → ${g.pasos.length} que se ven`);
  g.pasos.forEach((p, i) => {
    const a = String(p.ancla || '');
    const sec = a.includes('#') ? a.split('#')[1] : a;
    const n = String(i + 1).padStart(2);
    const notas = [];
    if (!a && p.accion !== 'modalPaso') {
      errores.push(`«${g.titulo}» paso ${i + 1}: sin ancla, no hay nada que marcar`);
      notas.push('ERROR · sin ancla: ese paso no se puede mostrar');
    }
    if (a.startsWith('col:')) {
      // la columna se explica por su ROL en la pantalla; acá, sin DOM, sólo se ve si hay entrada
      if (!DICCIONARIO[a]) notas.push('la explicación depende del ROL de la columna en pantalla (sin él, el cartel es genérico)');
    } else if (a.startsWith('txt:')) {
      const nom = a.slice(4).split('#')[0].split('@')[0];
      if (CON_DATOS.test(nom)) notas.push(`atado a un dato de este taller: «${nom}» (si cambia, se busca ignorando los números)`);
      if (!a.includes('#') && !p.ventana) notas.push('sin sección a la que caer si ese control ya no está');
      if (nom.length >= 48) notas.push('el texto del ancla está cortado en 48 caracteres');
    } else if (a && !DICCIONARIO[a] && p.accion !== 'modalPaso') {
      notas.push('sin entrada en el diccionario: el cartel sale con el nombre del control');
    }
    if (!p.texto) notas.push('sin cartel');
    // 🔴 UN MOVIMIENTO SIN SUS PUNTOS no se puede mostrar con el cursor: se grabó con un servidor
    // que todavía no conocía el gesto (y los descartaba al guardar). Lo marca `aGuion` — no se
    // busca por índice, que en el guion no coincide con la grabación (se completan etapas y se
    // juntan repetidos).
    if (p._sinGesto) {
      notas.push('MOVIMIENTO SIN GESTO: se guardó el paso pero no el recorrido — regrabalo para que se vea el cursor');
    }
    for (const x of notas) if (!x.startsWith('ERROR')) avisos.push(`«${g.titulo}» paso ${i + 1}: ${x}`);
    const marca = notas.length ? '  ⚠️' : '   ';
    console.log(`${marca} ${n}. ${a || '(aviso)'}${p.cuantas ? ` [elegí ${p.cuantas}]` : ''}${p.ventana ? ` [en: ${p.ventana}]` : ''}`);
    console.log(`        → ${(p.texto || '').slice(0, 100)}`);
    for (const x of notas) console.log(`        ⚠️ ${x}`);
  });
}

console.log(`\n${errores.length} error(es) · ${avisos.length} aviso(s)`);
for (const e of errores) console.log('  ✗ ' + e);
if (errores.length) process.exit(1);
console.log('  Los avisos no rompen el tutorial: dicen qué se va a resolver por aproximación.');
