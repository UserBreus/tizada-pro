# Arma un harness que RENDERIZA el bloque de etiquetas del visor tal cual está en App.jsx.
# El JSX no se re-escribe: se recorta literalmente del archivo (desde `chipsVariante` hasta el
# cierre del map) y se le inyectan los estados como stubs. Así lo que se mide es el código real.
import io, os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "frontend", "src", "App.jsx")
SAL = os.path.join(RAIZ, "frontend", "__verif_visor.jsx")

src = io.open(APP, encoding="utf-8").read().split("\n")
i0 = next(i for i, l in enumerate(src) if "const bloquesVarPz = (() => {" in l)
i1 = next(i for i, l in enumerate(src) if l.strip() == "})}</>);")
bloque = "\n".join(src[i0:i1 + 1])
assert "LBL_MIN_PX" in bloque and "data-piece" in bloque, "el recorte no trajo el bloque esperado"

# El mismo cálculo de `sep`/`clusters` del memo `canvasLayout`, también recortado del archivo.
j0 = next(i for i, l in enumerate(src) if "const cen = layout.map(" in l)
j1 = next(i for i, l in enumerate(src) if "clusters = [...cajas.values()];" in l) + 1  # + el `}` del if
memo = "\n".join(src[j0:j1 + 1]).replace("let clusters = null;", "var clusters = null;")

# los umbrales también salen de App.jsx (si allá cambian, la verificación cambia con ellos)
consts = "\n".join(l.strip() for l in src if re.match(r"\s*const (LBL|TXT)_MIN_PX = ", l))
assert "LBL_MIN_PX" in consts and "TXT_MIN_PX" in consts, consts

harness = """
import React from 'react';

__CONSTS__

export function armarLayout(piezas, W, H) {
  const layout = piezas.map(p => ({ ...p, tx: 0, ty: 0, x_new: p.px, y_new: p.py }));
  let minX = 0, minY = 0, maxX = W, maxY = H;
  layout.forEach(p => { minX = Math.min(minX, p.px); minY = Math.min(minY, p.py); maxX = Math.max(maxX, p.px + p.pw); maxY = Math.max(maxY, p.py + p.ph); });
  const PAD = Math.max(6, Math.max(maxX - minX, maxY - minY) * 0.01);
  const vbW = maxX - minX + 2 * PAD, vbH = maxY - minY + 2 * PAD;
  const vb = `${(minX - PAD).toFixed(1)} ${(minY - PAD).toFixed(1)} ${vbW.toFixed(1)} ${vbH.toFixed(1)}`;
__MEMO__
  return { layout, width: W, height: H, vb, vbW, vbH, sep, clusters };
}

// Visor en modo «todas las variantes juntas» (el caso que reportó el usuario).
export default function VisorTest({ canvasLayout, k, empTodasInfo, varPz }) {
  const spx = (n) => n / k;
  const etqData = { nombres_existentes: {} };
  const etqNombres = {};
  const etqSeleccion = null;
  const tabAjustesMolde = 'moldes', varStep = null;
  const varPzModo = !!varPz, varPzAsig = varPz || {};
  const empModo = !varPz, empTalle = null, empVista = 'simple', empFijar = null, empData = {};
  const selNombrar = new Set(), juntasSel = new Set();
  const vinculandoJuntas = null, editandoNombre = null, comboVisor = null, asignandoTipo = null;
  const asignandoConjunto = null, asignandoGrupoPz = null, grupoPzAbierto = null, grupoAislado = null;
  const gruposPz = [], variantesEdit = [], resaltarNombre = null, modoAcomodar = false;
  const conjActivoSet = null, grupoPzActivoSet = null, activoSet = null, piezaTipoMap = {};
  const pzOffsets = {}, dragInfo = { current: {} };
  const startDrag = () => {};
  const nombreGenerico = (s) => s;
  const _juntaDeIdx = () => null;
  const colorGrupo = (n) => 'hsl(200, 70%, 60%)';
  const colorGrupoA = (n, a) => `hsla(200, 70%, 60%, ${a})`;
  const aisladoSet = null;
  return (
    <svg viewBox={canvasLayout.vb} width={canvasLayout.vbW * k} height={canvasLayout.vbH * k}>
      {(() => {
__BLOQUE__
      })()}
    </svg>
  );
}
"""

harness = harness.replace("__CONSTS__", consts).replace("__MEMO__", memo).replace("__BLOQUE__", bloque)
io.open(SAL, "w", encoding="utf-8").write(harness)
print("escrito", SAL, len(harness), "bytes")
