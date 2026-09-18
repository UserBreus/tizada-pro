// LAS CAPAS DEL ARTE, EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 3 (camino A: el arte SEPARADO).
//
// Traducción de la parte de `molde_real.py` que el motor usa para preparar la mesa del arte de
// una pieza: quitar capas SIN romper el estado gráfico (`suprimir_capas`, `_raspar_pintado`),
// dejar UNA capa sola (`aislar_capa`), cambiarle el color (`recolorar_capa`), y partir una capa
// «Editable …» en sus figuras para aislar/recolorear una por una (`_analizar_capa`,
// `aislar_objeto`, `aislar_capa_objetos`); más `limpiar_capas_conservando_talle` (el arte CLÁSICO,
// sobre la misma mesa del molde). Los porqués de cada regla están en el Python; acá se copian
// las decisiones instrucción por instrucción para que el content-stream resultante sea el MISMO
// (`pdf/contenido.js` lo escribe byte a byte como pikepdf).
//
// Todo trabaja sobre la lista de instrucciones de `pdf/contenido.js` y los recursos ligeros de
// la página (`molde/paginas.js:recursosLigeros` → `R.props[nombre] = [capas]`), así que corre en
// cualquier hilo y no toca el PDF hasta que alguien escribe el resultado.

import { normCapa } from '../nombres.js'
import { reprPy } from '../arte/texto.js'
import { pyRound, pyFixed } from '../py.js'
import { sha1Hex } from '../sha1.js'

// Operadores de PINTADO (lo único que se suprime para el contenido que NO es del objeto).
export const PAINT_PATH = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'])   // → `n`
export const PAINT_TEXT = new Set(['Tj', 'TJ', "'", '"'])                              // → se eliminan
export const PAINT_DROP = new Set(['Do', 'sh'])                                        // XObject / sombreado
export const CLIP_OPS = new Set(['W', 'W*'])
export const PATH_BUILD = new Set(['m', 'l', 'c', 'v', 'y', 're', 'h'])
const FILL_PATH = new Set(['f', 'F', 'f*', 'b', 'b*', 'B', 'B*'])
const STROKE_PATH = new Set(['S', 's', 'b', 'b*', 'B', 'B*'])
const TERMINADORES = new Set([...PAINT_PATH, 'n'])

const esImagenEnLinea = (op) => op.toUpperCase().replace(/_/g, ' ') === 'INLINE IMAGE'
const numero = (v) => {
  // `float(operando)` de Python: sólo números; lo demás levanta (el llamador decide)
  if (v && typeof v === 'object' && (v.i !== undefined || v.r !== undefined)) return Number(v.i !== undefined ? v.i : v.r)
  throw new TypeError('no es un número')
}
const latin1 = (u8) => { let s = ''; for (const c of u8) s += String.fromCharCode(c); return s }

/** `molde_real._nombres_oc`: los nombres de capa (SIN normalizar) del operando de un `BDC /OC`. */
export function nombresOc(operando, R) {
  try {
    if (!operando) return []
    if (operando.n !== undefined) return (R.props || {})[operando.n] || []
    if (operando.d !== undefined) {
      // un diccionario en línea (raro): /Type /OCG con su /Name
      const d = operando.d
      const t = d.get('Type')
      if (t && t.n === 'OCG') { const nm = d.get('Name'); return nm && nm.s ? [latin1(nm.s)] : [] }
    }
  } catch { /* como el Python */ }
  return []
}

const esBdcOc = (ins) => ins.op === 'BDC' && ins.args.length === 2 && ins.args[0] && ins.args[0].n === 'OC'

/** `_mapa_oc`: `{ops, oc}` — el operador de cada instrucción y, por `BDC /OC`, el set de capas normalizadas. */
export function mapaOc(inst, R) {
  const ops = inst.map((i) => i.op)
  const oc = new Map()
  for (let i = 0; i < inst.length; i++) {
    if (ops[i] === 'BDC' && esBdcOc(inst[i])) oc.set(i, new Set(nombresOc(inst[i].args[1], R).map(normCapa)))
  }
  return { ops, oc }
}

/** `_bloques_oc`: el árbol de bloques marcados `(ini, fin, nombres|null, balanceado, hijos)`. */
export function bloquesOc(ops, oc) {
  const raiz = [], abiertos = []
  for (let i = 0; i < ops.length; i++) {
    const o = ops[i]
    if (o === 'BDC' || o === 'BMC') abiertos.push([i, o === 'BDC' ? (oc.get(i) ?? null) : null, 0, []])
    else if (o === 'EMC') {
      if (abiertos.length) {
        const [ini, nombres, bal, hijos] = abiertos.pop()
        ;(abiertos.length ? abiertos[abiertos.length - 1][3] : raiz).push([ini, i, nombres, bal === 0, hijos])
      }
    } else if (o === 'q') { for (const b of abiertos) b[2] += 1 } else if (o === 'Q') { for (const b of abiertos) b[2] -= 1 }
  }
  return raiz
}

/** `_saltar_bloques`: los índices de los bloques enteros que se borran (poda fuerte). */
export function saltarBloques(ops, oc, suprimirFn, bloques = null) {
  if (bloques === null) bloques = bloquesOc(ops, oc)
  const saltar = new Set()
  const caminar = (lista) => {
    for (const [ini, fin, nombres, balanceado, hijos] of lista) {
      if (nombres && nombres.size && suprimirFn([nombres])) {
        if (balanceado) for (let k = ini; k <= fin; k++) saltar.add(k)
        continue
      }
      caminar(hijos)
    }
  }
  caminar(bloques)
  return saltar
}

/** `_raspar_instrucciones`: la pasada que decide instrucción por instrucción. */
export function rasparInstrucciones(inst, ops, oc, suprimirFn, podar, saltar) {
  const salida = [], pila = []
  for (let i = 0; i < inst.length; i++) {
    if (saltar.has(i)) continue
    const ins = inst[i], op = ops[i]
    if (op === 'BDC' || op === 'BMC') { pila.push(oc.get(i) || new Set()); continue }
    if (op === 'EMC') { if (pila.length) pila.pop(); continue }
    if (op === 'MP' || op === 'DP') continue
    if (suprimirFn(pila)) {
      if (podar && PATH_BUILD.has(op)) continue
      if (PAINT_PATH.has(op)) {
        if (!podar) salida.push({ op: 'n', args: [] })
        continue
      }
      if (PAINT_TEXT.has(op)) {
        if (op === "'") salida.push({ op: 'T*', args: [] })
        else if (op === '"' && ins.args.length === 3) {
          salida.push({ op: 'Tw', args: [ins.args[0]] })
          salida.push({ op: 'Tc', args: [ins.args[1]] })
          salida.push({ op: 'T*', args: [] })
        }
        continue
      }
      if (PAINT_DROP.has(op) || esImagenEnLinea(op)) continue
      if (CLIP_OPS.has(op)) continue
    }
    salida.push(ins)
  }
  return salida
}

/** `_raspar_pintado`: conserva TODO el estado gráfico y suprime sólo el pintado de lo que `suprimirFn(pila)` marca. */
export function rasparPintado(inst, R, suprimirFn, podar = false) {
  const { ops, oc } = mapaOc(inst, R)
  const saltar = podar ? saltarBloques(ops, oc, suprimirFn) : new Set()
  return rasparInstrucciones(inst, ops, oc, suprimirFn, podar, saltar)
}

const conjunto = (objetivo) => (typeof objetivo === 'string' ? new Set([normCapa(objetivo)]) : new Set([...objetivo].map(normCapa)))
const interseca = (a, b) => { for (const x of a) if (b.has(x)) return true; return false }

/** `aislar_capa`: deja SOLO el pintado de la(s) capa(s) `objetivo`. */
export function aislarCapa(inst, R, objetivo, podar = false) {
  const obj = conjunto(objetivo)
  return rasparPintado(inst, R, (pila) => !pila.some((f) => f && f.size && interseca(obj, f)), podar)
}

/** `suprimir_capas`: quita esas capas sin romper el estado gráfico. */
export function suprimirCapas(inst, R, capas) {
  const sup = conjunto(capas)
  if (!sup.size) return inst
  return rasparPintado(inst, R, (pila) => pila.some((f) => f && f.size && interseca(sup, f)))
}

/** `{v:.6f}` parseado por pikepdf: el real conserva su texto, y así se escribe. */
const opColor = (vals, letra) => ({ op: letra, args: vals.map((v) => ({ r: pyFixed(Number(v), 6) })) })

/** `recolorar_capa`: inyecta el color CMYK antes de cada pintado DENTRO de la capa. */
export function recolorarCapa(inst, R, objetivo, cmykFill = null, cmykStroke = null) {
  const obj = conjunto(objetivo)
  const dentro = (pila) => pila.some((f) => f && f.size && interseca(obj, f))
  const salida = [], pila = []
  for (const ins of inst) {
    const op = ins.op
    if (op === 'BDC' || op === 'BMC') {
      let nombres = new Set()
      if (op === 'BDC' && esBdcOc(ins)) nombres = new Set(nombresOc(ins.args[1], R).map(normCapa))
      pila.push(nombres); salida.push(ins); continue
    }
    if (op === 'EMC') { if (pila.length) pila.pop(); salida.push(ins); continue }
    if (dentro(pila)) {
      if (cmykFill !== null && cmykFill !== undefined && FILL_PATH.has(op)) salida.push(opColor(cmykFill, 'k'))
      if (cmykStroke !== null && cmykStroke !== undefined && STROKE_PATH.has(op)) salida.push(opColor(cmykStroke, 'K'))
    }
    salida.push(ins)
  }
  return salida
}

// ─── objetos dentro de una capa (`_analizar_capa`) ───────────────────────────────────────────
const mmul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3],
  a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3],
  a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]
const mpt = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]

/** `repr()` de un float de Python (los de este sistema: redondeados a 1-3 decimales). */
/** `repr()` de un float de Python: el de `arte/texto.js` (un solo lugar). */
export const pyReprFloat = (x) => reprPy(x)

/** `repr()` de un str de Python (comillas simples salvo que el texto las tenga y no tenga dobles). */
function pyReprStr(s) {
  const q = (s.includes("'") && !s.includes('"')) ? '"' : "'"
  let out = q
  for (const ch of s) {
    const c = ch.codePointAt(0)
    if (ch === '\\') out += '\\\\'
    else if (ch === q) out += '\\' + q
    else if (ch === '\n') out += '\\n'
    else if (ch === '\r') out += '\\r'
    else if (ch === '\t') out += '\\t'
    else if (c < 32 || c === 127) out += '\\x' + c.toString(16).padStart(2, '0')
    else out += ch
  }
  return out + q
}

/** `repr()` de una tupla de Python con str/float/int/tuplas adentro (la FIRMA de un objeto). */
function pyReprTupla(t) {
  const partes = t.map((v) => {
    if (Array.isArray(v)) return pyReprTupla(v)
    if (typeof v === 'string') return pyReprStr(v)
    if (v && typeof v === 'object' && v.int !== undefined) return String(v.int)
    return pyReprFloat(v)
  })
  return partes.length === 1 ? '(' + partes[0] + ',)' : '(' + partes.join(', ') + ')'
}

/**
 * `_analizar_capa`: los objetos de la capa `objetivo` (por firma de geometría), sus clips y todos
 * los índices de pintado. `xobjInfo(nombre)` → `{bbox:[x0,y0,x1,y1], matrix|null}` del Form XObject
 * de la página, o null (`_bbox_xobject`).
 */
export function analizarCapa(inst, R, objetivo, xobjInfo = null) {
  const obj = normCapa(objetivo)
  let ctm = [1, 0, 0, 1, 0, 0]
  const pilaCtm = [], pilaOc = []
  let ini = null, pts = [], clip = false, fill = null
  const unidades = []
  const paintIdxTodos = new Set()
  const frameCapas = () => { const s = new Set(); for (const f of pilaOc) for (const x of f) s.add(x); return s }
  const bboxXObject = (nom) => {
    try {
      const info = xobjInfo ? xobjInfo(nom) : null
      if (!info) return null
      const bx = info.bbox.map(Number)
      const M = info.matrix ? info.matrix.map(Number) : [1, 0, 0, 1, 0, 0]
      const m = mmul(M, ctm)
      const xs = [], ys = []
      for (const [px, py] of [[bx[0], bx[1]], [bx[2], bx[1]], [bx[2], bx[3]], [bx[0], bx[3]]]) {
        const [qx, qy] = mpt(m, px, py); xs.push(qx); ys.push(qy)
      }
      return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
    } catch { return null }
  }
  for (let i = 0; i < inst.length; i++) {
    const it = inst[i], op = it.op
    if (op === 'q') pilaCtm.push(ctm)
    else if (op === 'Q') ctm = pilaCtm.length ? pilaCtm.pop() : ctm
    else if (op === 'cm') {
      // `_mmul` con menos de 6 números levanta en Python y la CTM queda como estaba
      try { const v = it.args.map(numero); if (v.length < 6) throw new TypeError('cm'); ctm = mmul(v, ctm) } catch { /* nada */ }
    } else if (op === 'k') {
      try { fill = it.args.map(numero).slice(0, 4) } catch { fill = null }
    } else if (op === 'scn' || op === 'sc') {
      try { const vals = it.args.map(numero); fill = vals.length === 4 ? vals : fill } catch { /* nada */ }
    } else if (op === 'BDC' || op === 'BMC') {
      let nombres = new Set()
      if (op === 'BDC' && esBdcOc(it)) nombres = new Set(nombresOc(it.args[1], R).map(normCapa))
      pilaOc.push(nombres)
    } else if (op === 'EMC') { if (pilaOc.length) pilaOc.pop() } else if (PATH_BUILD.has(op)) {
      if (ini === null) { ini = i; pts = []; clip = false }
      let f
      try { f = it.args.map(numero) } catch { f = [] }
      if (op === 're' && f.length === 4) {
        const [x, y, w, h] = f
        for (const [px, py] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]]) pts.push(mpt(ctm, px, py))
      } else {
        for (let k = 0; k < f.length - 1; k += 2) pts.push(mpt(ctm, f[k], f[k + 1]))
      }
    } else if (op === 'W' || op === 'W*') clip = true
    else if (TERMINADORES.has(op)) {
      if (pts.length) {
        const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
        const bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]
        const esClip = clip || op === 'n'
        const fillOp = FILL_PATH.has(op), strokeOp = STROKE_PATH.has(op)
        if (!esClip) paintIdxTodos.add(i)
        const sig = ['v', ...pts.map(([px, py]) => [pyRound(px, 1), pyRound(py, 1)])]
        unidades.push({ i, bbox, esClip, capas: frameCapas(), kind: 'vector', fillOp, strokeOp,
          fill: fillOp ? fill : null, sig })
      }
      ini = null; pts = []; clip = false
    } else if (op === 'Do') {
      const nom = it.args.length && it.args[0] && it.args[0].n !== undefined ? '/' + it.args[0].n : (it.args.length ? String(it.args[0]) : '')
      let bbox = bboxXObject(nom)
      if (bbox === null) bbox = [ctm[4], ctm[5], ctm[4], ctm[5]]
      paintIdxTodos.add(i)
      const sig = ['do', nom, pyRound(ctm[0], 3), pyRound(ctm[3], 3), pyRound(ctm[4], 1), pyRound(ctm[5], 1)]
      unidades.push({ i, bbox, esClip: false, capas: frameCapas(), kind: 'xobject', fillOp: false, strokeOp: false, fill: null, sig })
    } else if (PAINT_TEXT.has(op)) {
      const bbox = [ctm[4], ctm[5], ctm[4], ctm[5]]
      paintIdxTodos.add(i)
      unidades.push({ i, bbox, esClip: false, capas: frameCapas(), kind: 'texto', fillOp: false, strokeOp: false, fill: null, sig: ['tx', { int: i }] })
    } else if (op === 'sh') {
      const bbox = [ctm[4], ctm[5], ctm[4], ctm[5]]
      paintIdxTodos.add(i)
      unidades.push({ i, bbox, esClip: false, capas: frameCapas(), kind: 'shading', fillOp: false, strokeOp: false, fill: null, sig: ['sh', pyRound(ctm[4], 1), pyRound(ctm[5], 1), { int: i }] })
    }
  }
  const deCapa = unidades.filter((u) => u.capas.has(obj))
  const clipsCapaIdx = new Set(deCapa.filter((u) => u.esClip).map((u) => u.i))
  const pintadas = deCapa.filter((u) => !u.esClip)
  const porSig = new Map(), ordenSig = []
  for (const u of pintadas) {
    const s = pyReprTupla(u.sig)
    if (!porSig.has(s)) { porSig.set(s, []); ordenSig.push(s) }
    porSig.get(s).push(u)
  }
  const objetos = []
  for (const s of ordenSig) {
    const us = porSig.get(s)
    const b = [Math.min(...us.map((u) => u.bbox[0])), Math.min(...us.map((u) => u.bbox[1])),
      Math.max(...us.map((u) => u.bbox[2])), Math.max(...us.map((u) => u.bbox[3]))]
    const oid = sha1Hex(s).slice(0, 8)                    // id ESTABLE por la geometría (= sha1(repr(sig)))
    const iPaints = new Set(us.map((u) => u.i))
    const fillOp = us.some((u) => u.fillOp), strokeOp = us.some((u) => u.strokeOp)
    const conFill = us.find((u) => u.fill !== null)
    objetos.push({ obj_id: oid, kind: us[0].kind, bbox: b, fill: conFill ? conFill.fill.slice() : null,
      recolorable: !!(fillOp || strokeOp), fillOp, strokeOp, iPaints })
  }
  objetos.sort((a, b) => Math.min(...a.iPaints) - Math.min(...b.iPaints))
  return { objetos, clipsCapaIdx, paintIdxTodos }
}

/** `objetos_de_capa`. */
export function objetosDeCapa(inst, R, objetivo, xobjInfo = null) {
  return analizarCapa(inst, R, objetivo, xobjInfo).objetos
}

/** `_reescribir_por_indice`. `recolorIdx` = Map(idx → [fill|null, stroke|null]). */
export function reescribirPorIndice(inst, suprimirIdx, recolorIdx = null, conservarMarcadores = false) {
  const salida = []
  for (let i = 0; i < inst.length; i++) {
    const ins = inst[i], op = ins.op
    if (op === 'BDC' || op === 'BMC' || op === 'EMC' || op === 'MP' || op === 'DP') {
      if (conservarMarcadores) salida.push(ins)
      continue
    }
    if (suprimirIdx.has(i)) {
      if (PAINT_PATH.has(op)) { salida.push({ op: 'n', args: [] }); continue }
      if (PAINT_TEXT.has(op)) {
        if (op === "'") salida.push({ op: 'T*', args: [] })
        else if (op === '"' && ins.args.length === 3) {
          salida.push({ op: 'Tw', args: [ins.args[0]] })
          salida.push({ op: 'Tc', args: [ins.args[1]] })
          salida.push({ op: 'T*', args: [] })
        }
        continue
      }
      if (PAINT_DROP.has(op) || esImagenEnLinea(op)) continue
      if (CLIP_OPS.has(op)) continue
    }
    const cr = recolorIdx ? recolorIdx.get(i) : null
    if (cr) {
      if (cr[0] !== null && cr[0] !== undefined && FILL_PATH.has(op)) salida.push(opColor(cr[0], 'k'))
      if (cr[1] !== null && cr[1] !== undefined && STROKE_PATH.has(op)) salida.push(opColor(cr[1], 'K'))
    }
    salida.push(ins)
  }
  return salida
}

/** `aislar_objeto`: deja SOLO la figura `objId` de la capa (y los clips de la capa), opcionalmente recoloreada. */
export function aislarObjeto(inst, R, objetivo, objId, cmykFill = null, cmykStroke = null, xobjInfo = null) {
  const a = analizarCapa(inst, R, objetivo, xobjInfo)
  const tgt = a.objetos.find((o) => o.obj_id === objId) || null
  const keep = new Set(tgt ? tgt.iPaints : [])
  for (const i of a.clipsCapaIdx) keep.add(i)
  const suprimir = new Set([...a.paintIdxTodos].filter((i) => !keep.has(i)))
  const recolor = new Map()
  if (tgt && ((cmykFill !== null && cmykFill !== undefined) || (cmykStroke !== null && cmykStroke !== undefined))) {
    for (const i of tgt.iPaints) recolor.set(i, [cmykFill ?? null, cmykStroke ?? null])
  }
  return reescribirPorIndice(inst, suprimir, recolor)
}

/** `aislar_capa_objetos`: la capa ENTERA, recoloreando cada figura (`colores` = {obj_id: [fill, stroke]}). */
export function aislarCapaObjetos(inst, R, objetivo, colores = null, xobjInfo = null) {
  const a = analizarCapa(inst, R, objetivo, xobjInfo)
  const keep = new Set(a.clipsCapaIdx)
  const recolor = new Map()
  for (const o of a.objetos) {
    for (const i of o.iPaints) keep.add(i)
    const c = (colores || {})[o.obj_id]
    if (c && ((c[0] !== null && c[0] !== undefined) || (c[1] !== null && c[1] !== undefined))) {
      for (const i of o.iPaints) recolor.set(i, [c[0] ?? null, c[1] ?? null])
    }
  }
  const suprimir = new Set([...a.paintIdxTodos].filter((i) => !keep.has(i)))
  return reescribirPorIndice(inst, suprimir, recolor)
}

/** `capa_admite_color`: ¿la capa tiene relleno/trazo DIRECTO en su frame? */
export function capaAdmiteColor(inst, R, objetivo) {
  const obj = conjunto(objetivo)
  const pila = []
  for (const ins of inst) {
    const op = ins.op
    if (op === 'BDC' || op === 'BMC') {
      let nombres = new Set()
      if (op === 'BDC' && esBdcOc(ins)) nombres = new Set(nombresOc(ins.args[1], R).map(normCapa))
      pila.push(nombres); continue
    }
    if (op === 'EMC') { if (pila.length) pila.pop(); continue }
    if (pila.some((f) => f && f.size && interseca(obj, f)) && (FILL_PATH.has(op) || STROKE_PATH.has(op))) return true
  }
  return false
}

// ─── el arte CLÁSICO: el diseño sobre la misma mesa del molde ───────────────────────────────
const PINTURA_CLASICO = new Set(['S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*', 'n'])

/**
 * `limpiar_capas_conservando_talle`: borra las capas `capasABorrar` (nombres SIN normalizar, como
 * en el Python) y, dentro de la capa `talle`, saca la moldería base (`geomsBase` = bboxes en crudas)
 * y todo el texto; el resto queda tal cual. Termina cerrando los `q` abiertos.
 */
export function limpiarCapasConservandoTalle(inst, R, capasABorrar, talle, geomsBase, tol = 0.8) {
  const borrar = new Set(capasABorrar)
  const salida = []
  let profQ = 0, oculto = 0, enTalle = false, profMc = 0, enTexto = false
  let camino = [], pts = []
  const coincideBase = (bb) => {
    if (bb === null) return false
    for (const g of geomsBase) {
      if (Math.abs(bb[0] - g[0]) < tol && Math.abs(bb[1] - g[1]) < tol && Math.abs(bb[2] - g[2]) < tol && Math.abs(bb[3] - g[3]) < tol) return true
    }
    return false
  }
  for (const ins of inst) {
    const op = ins.op
    if (oculto > 0) {
      if (op === 'BDC' || op === 'BMC') oculto += 1
      else if (op === 'EMC') oculto -= 1
      continue
    }
    if (op === 'BDC' && esBdcOc(ins)) {
      const nombres = nombresOc(ins.args[1], R)
      if (nombres.includes(talle)) { enTalle = true; profMc = 1; continue }
      if (nombres.some((n) => borrar.has(n))) { oculto = 1; continue }
    }
    if (enTalle) {
      if (op === 'BDC' || op === 'BMC') { profMc += 1; continue }
      if (op === 'EMC') { profMc -= 1; if (profMc === 0) enTalle = false; continue }
      if (op === 'BT') { enTexto = true; continue }
      if (op === 'ET') { enTexto = false; continue }
      if (enTexto) continue
      if (PATH_BUILD.has(op) || op === 'W' || op === 'W*') {
        camino.push(ins)
        for (let k = 0; k < ins.args.length - 1; k += 2) {
          try { pts.push([numero(ins.args[k]), numero(ins.args[k + 1])]) } catch { /* como el Python */ }
        }
        if (op === 're' && ins.args.length === 4) {
          try {
            const [x, y, w, h] = ins.args.map(numero)
            pts.push([x, y], [x + w, y + h])
          } catch { /* el Python levantaría: se ignora igual que un operando raro */ }
        }
        continue
      }
      if (PINTURA_CLASICO.has(op)) {
        const bb = pts.length ? [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])),
          Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))] : null
        if (!coincideBase(bb)) { salida.push(...camino); salida.push(ins) }
        camino = []; pts = []
        continue
      }
    }
    if (op === 'BDC' || op === 'BMC' || op === 'EMC' || op === 'MP' || op === 'DP') continue
    if (op === 'q') profQ += 1
    else if (op === 'Q') { if (profQ === 0) continue; profQ -= 1 }
    salida.push(ins)
  }
  for (let k = 0; k < profQ; k++) salida.push({ op: 'Q', args: [] })
  return salida
}
