// Renderiza el bloque REAL del visor (recortado de App.jsx) con la geometría REAL del molde y
// cuenta rótulos encimados. Uso: node verif_visor.mjs <archivo_json_de_deteccion_todas> <k>
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import fs from 'fs';
import VisorTest, { armarLayout } from '../frontend/__verif_visor.jsx';

const det = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
const kIn = process.argv[3] ? Number(process.argv[3]) : null;
const cl = armarLayout(det.piezas, det.img_w, det.img_h);

// «Ver todo»: el molde entero dentro del panel del visor (≈ 570 × 520 px reales de la pantalla).
const k = kIn || Math.min(570 / cl.vbW, 520 / cl.vbH);

const info = { nom: {}, fijo: {} };
det.piezas.forEach(p => { info.nom[`${p.talle}|${p.t_idx}`] = ''; });

const html = renderToStaticMarkup(React.createElement(VisorTest, { canvasLayout: cl, k, empTodasInfo: info }));
fs.writeFileSync(process.argv[4] || 'salida_visor.svg', html);

// ── Medición: posiciones de TODO lo que se dibuja como texto/círculo de rótulo ──
// Se sacan del SVG generado (no de las estructuras de datos): es lo que se ve.
const textos = [...html.matchAll(/<text[^>]*?x="([-\d.]+)"[^>]*?y="([-\d.]+)"[^>]*>([^<]*)<\/text>/g)]
  .map(m => ({ x: +m[1], y: +m[2], t: m[3] }));
// los rótulos de pieza van dentro de un <g transform="translate(cx, cy)"> sin x/y propios
const grupos = [...html.matchAll(/<g transform="translate\(([-\d.]+), ([-\d.]+)\)">(.*?)<\/g>/gs)];
const badges = [];
for (const g of grupos) {
  const cx = +g[1], cy = +g[2];
  const txt = [...g[3].matchAll(/<text[^>]*>([^<]*)<\/text>/g)].map(m => m[1]);
  if (g[3].includes('<circle')) badges.push({ cx, cy, txt });
}
const puntos = (html.match(/<circle cx=/g) || []).length;   // piezas sin rótulo (punto chico)

function colisiones(pts, min) {
  let n = 0; const pares = [];
  for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
    const d = Math.hypot((pts[i].cx - pts[j].cx) * k, (pts[i].cy - pts[j].cy) * k);
    if (d < min) { n++; if (pares.length < 6) pares.push([pts[i].txt?.join('/'), pts[j].txt?.join('/'), d.toFixed(1)]); }
  }
  return { n, pares };
}

const c = colisiones(badges, 34);
console.log(JSON.stringify({
  piezas: det.piezas.length,
  k: +k.toFixed(4),
  rotulos_completos: badges.length,
  puntos_sin_rotulo: puntos,
  chips_de_variante: textos.filter(t => /^(XS|S|M|L|XL|2XL|3XL)$/.test(t.t)).length,
  textos_sueltos: textos.length,
  pares_encimados_menos_de_34px: c.n,
  ejemplos: c.pares,
}, null, 1));
