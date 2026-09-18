// LA BASE DE UNA PIEZA DEL CAMINO B — PLAN_NAVEGADOR.md, etapa 3 (y la reusa la 4).
//
// Traducción de `motor_pedido._armar_base` (ramal `_camino_b`): la página de la pieza mide el
// contorno más el margen `B`, el dibujo es la mesa del molde desplegada (sólo la capa del talle)
// como Form XObject, recortada al contorno, y encima el borde de corte y la línea de corte que
// traía el archivo. Todo son OPERADORES de texto: acá se arman las mismas cadenas que arma
// Python (mismos `:.3f`, mismo orden), y el contrato las compara letra por letra.
//
// Coordenadas: el contorno viene en «crudas» del lienzo (y hacia arriba, `bbox_raw`); `S` es la
// escala del XObject (= `/UserUnit` de la mesa, `cont.user_unit`), `x0/y0` la esquina del contorno
// en crudas y `x0m/y0m` en coordenadas de dispositivo (`bbox_mu`, y hacia abajo), que es lo que
// usan los placeholders y las etiquetas.
import { pyFixed, pyG } from '../py.js'

export const MM = 2.83465            // puntos por mm (molde_real.MM)
export const CM = 28.3465            // puntos por cm (motor_pedido.CM)

/** `ops_cont`: el contorno como operadores de trazado, escalado por `S` y desplazado (dx, dy). */
export function opsCont(cont, S, dx = 0.0, dy = 0.0) {
  const fseg = (s) => {
    if (s[0] === 're') {
      // `re` es (x, y, ANCHO, ALTO): el desplazamiento va SÓLO a x e y (changelog 2026-09-07)
      const [x, y, w, h] = s.slice(1, 5)
      return `${pyFixed(x * S + dx, 3)} ${pyFixed(y * S + dy, 3)} ${pyFixed(w * S, 3)} ${pyFixed(h * S, 3)} re`
    }
    const nums = s.slice(1).map((v, i) => pyFixed(v * S + (i % 2 === 0 ? dx : dy), 3))
    return (nums.join(' ') + ' ' + s[0]).trim()
  }
  return cont.segmentos.map(fseg).join('\n')
}

/** `" ".join(f"{v:g}" for v in color) + " K"` */
const colorOp = (vals, op) => vals.map((v) => pyG(Number(v))).join(' ') + ' ' + op

/**
 * Arma la base: `{baseStream, clip, W, H, Hp, x0, y0, x0m, y0m, S, B, nom}`.
 *   · `cont`   — el contorno (`piezas_de_mesa`, con `segmentos`, `bbox_raw`, `bbox_mu`, `w`, `h`,
 *                `user_unit` y, si el archivo la traía, `linea_corte`);
 *   · `S`      — la escala del XObject de la mesa (el `/UserUnit` de la página desplegada);
 *   · `borde`  — `{activo, ancho_mm, color: [c,m,y,k], alineacion: 'fuera'|'centro'|'dentro'}`;
 *   · `nom`    — el nombre del XObject en la página de la pieza (`/A0`, como `add_resource(prefix="A")`).
 * `B` = margen y mitad del ancho del borde: `(ancho_mm si activo, si no 2.0) * MM`.
 */
export function armarBase(cont, S, borde, nom = '/A0') {
  const bc = configBorde(borde)
  const { B } = bc
  const [x0, y0] = cont.bbox_raw
  const W = cont.w, H = cont.h
  const [x0m, y0m] = cont.bbox_mu
  const Hp = H + 2 * B
  const ops = opsCont(cont, S)
  const clip = opsCont(cont, S, B - x0 * S, B - y0 * S)
  const arteDraw = `q\n1 0 0 1 ${pyFixed(B - x0 * S, 3)} ${pyFixed(B - y0 * S, 3)} cm\n` +
                   `q\n${ops}\nW n\n${nom} Do\nQ\nQ\n`
  const baseStream = componerBase(bc, cont, S, clip, W, H, arteDraw)
  return { baseStream, clip, W, H, Hp, x0, y0, x0m, y0m, S, B, nom,
           bcActivo: bc.bcActivo, bcColor: bc.bcColor, bcAlin: bc.bcAlin, cont }
}

/**
 * La configuración del borde de corte como la lee `generar_pedido` (`_bc_*`, `B`): `{bcActivo,
 * bcMm, bcColor, bcAlin, B}`. `B` = margen de la pieza y mitad del ancho del borde.
 */
export function configBorde(borde) {
  const bc = borde || {}
  // `_bc.get("activo", True)`: sin la clave, prendido; con ella, su verdad (0/None/false apagan)
  const bcActivo = bc.activo === undefined ? true : !!bc.activo
  const bcMm = Math.max(0.2, Number(bc.ancho_mm ?? 2.0) || 2.0)
  const bcColor = (bc.color || [0.75, 0.68, 0.67, 0.90]).slice(0, 4)
  let bcAlin = bc.alineacion || 'fuera'
  if (!['fuera', 'centro', 'dentro'].includes(bcAlin)) bcAlin = 'fuera'
  const B = (bcActivo ? bcMm : 2.0) * MM
  return { bcActivo, bcMm, bcColor, bcAlin, B }
}

/**
 * El borde de corte y la línea de corte del archivo, como en `_armar_base` (compartido por los
 * dos caminos): `{bordeOps, bordePost}`. `bc` = `configBorde(...)`.
 */
export function bloqueBorde(bc, cont, S, clip, W, H) {
  const { bcActivo, bcColor, bcAlin, B } = bc
  let bordeOps = ''
  const bcol = colorOp(bcColor, 'K')
  if (bcActivo) {
    if (bcAlin === 'centro') {
      bordeOps = `q\n${clip}\n${pyFixed(B, 3)} w 0 j 0 J 10 M ${bcol}\nS\nQ\n`
    } else if (bcAlin === 'dentro') {
      bordeOps = `q\n${clip}\nW n\n${clip}\n${pyFixed(2 * B, 3)} w 0 j 0 J 10 M ${bcol}\nS\nQ\n`
    } else {
      // hacia afuera (default): trazo 2B recortado al EXTERIOR (par-impar) → queda B visible afuera
      bordeOps = `q\n${pyFixed(-3 * B, 3)} ${pyFixed(-3 * B, 3)} ${pyFixed(W + 8 * B, 3)} ${pyFixed(H + 8 * B, 3)} re\n${clip}\nW* n\n${clip}\n` +
                 `${pyFixed(2 * B, 3)} w 0 j 0 J 10 M ${bcol}\nS\nQ\n`
    }
  }
  // La línea de corte que traía el archivo (`cont.linea_corte = {w, color}`), como en Python.
  const lc = (cont.linea_corte && typeof cont.linea_corte === 'object') ? cont.linea_corte : null
  let bordePost = ''
  if (lc && lc.w) {
    const wl = Number(lc.w) * S
    if (!bcActivo) {
      const [lop, lv] = lc.color || ['k', [0, 0, 0, 1]]
      const lcol = lv.map((v) => pyG(Number(v))).join(' ') + ' ' + ({ k: 'K', rg: 'RG', g: 'G' }[String(lop)] || 'K')
      bordePost = `q\n${clip}\n${pyFixed(wl, 3)} w 0 j 0 J 10 M ${lcol}\nS\nQ\n`
    } else if (bcAlin === 'fuera') {
      bordePost = `q\n${clip}\nW n\n${clip}\n${pyFixed(wl, 3)} w 0 j 0 J 10 M ${bcol}\nS\nQ\n`
    }
  }
  return { bordeOps, bordePost }
}

/** `_base_stream`: el orden del borde respecto del dibujo depende de la alineación. */
export function componerBase(bc, cont, S, clip, W, H, arteDraw) {
  const { bordeOps, bordePost } = bloqueBorde(bc, cont, S, clip, W, H)
  return bc.bcAlin === 'fuera' ? `${bordeOps}${arteDraw}${bordePost}` : `${arteDraw}${bordeOps}${bordePost}`
}

// ─── el documento de UNA pieza (para la vista previa y los contratos) ────────────────────────
function leerCaja(pageObj, clave) {
  const v = pageObj.get(clave)
  if (!v || !v.isArray || !v.isArray()) return null
  const out = []
  for (let i = 0; i < 4; i++) out.push(Number(v.get(i).asNumber()))
  return out
}

/**
 * La mesa desplegada (página `pagina` de `mesaDoc`, un `PDFDocument`) como Form XObject dentro
 * de `out`, igual que `pikepdf.Page.as_form_xobject()` (qpdf `getFormXObjectForPage` con
 * transformaciones): `/BBox` = TrimBox → CropBox → MediaBox, `/Matrix` = la escala de `/UserUnit`
 * (los moldes no traen `/Rotate`), `/Resources` los de la página, y sin `/OC`.
 * Devuelve el objeto del XObject (ya agregado a `out`).
 */
export function formDeMesa(mupdf, out, mesaDoc, pagina) {
  const pageObj = mesaDoc.findPage(pagina)
  const caja = leerCaja(pageObj, 'TrimBox') || leerCaja(pageObj, 'CropBox') || leerCaja(pageObj, 'MediaBox') || [0, 0, 612, 792]
  const uu = pageObj.get('UserUnit')
  const U = (uu && uu.isNumber && uu.isNumber()) ? Number(uu.asNumber()) : 1.0
  // el contenido de la página: uno o varios streams, concatenados con un salto de línea
  const cont = pageObj.get('Contents')
  let bytes
  if (cont && cont.isArray && cont.isArray()) {
    const partes = []
    for (let i = 0; i < cont.length; i++) partes.push(cont.get(i).readStream())
    let n = 0
    for (const p of partes) n += p.length + 1
    bytes = new Uint8Array(n)
    let k = 0
    for (const p of partes) { bytes.set(p, k); k += p.length; bytes[k++] = 10 }
  } else {
    bytes = cont ? cont.readStream() : new Uint8Array(0)
  }
  const dict = out.newDictionary()
  dict.put('Type', out.newName('XObject'))
  dict.put('Subtype', out.newName('Form'))
  const bbox = out.newArray()
  for (const v of caja) bbox.push(out.newReal(v))
  dict.put('BBox', bbox)
  if (U !== 1.0) {
    const m = out.newArray()
    for (const v of [U, 0, 0, U, 0, 0]) m.push(out.newReal(v))
    dict.put('Matrix', m)
  }
  const res = pageObj.get('Resources')
  if (res) dict.put('Resources', out.graftObject(res))
  const grupo = pageObj.get('Group')
  if (grupo) dict.put('Group', out.graftObject(grupo))
  const xo = out.addStream(bytes, dict)
  return { xo, U }
}

/**
 * El PDF de una pieza: una página de `(W+2B) × (H+2B)` con el XObject de la mesa como `/A0` y
 * el contenido `baseStream + estampado`. Devuelve los bytes.
 */
export function documentoPieza(mupdf, mesaDoc, pagina, base, estampado = '') {
  const out = new mupdf.PDFDocument()
  const { xo } = formDeMesa(mupdf, out, mesaDoc, pagina)
  const res = out.newDictionary()
  const xos = out.newDictionary()
  xos.put(base.nom.slice(1), xo)
  res.put('XObject', xos)
  const contenido = new TextEncoder().encode(base.baseStream + estampado)
  const page = out.addPage([0, 0, base.W + 2 * base.B, base.H + 2 * base.B], 0, res, contenido)
  out.insertPage(out.countPages(), page)
  return out.saveToBuffer('compress').asUint8Array().slice()
}
