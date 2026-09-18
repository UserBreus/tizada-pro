// LA HOJA CON EL SELLO, EN EL NAVEGADOR — PLAN_NAVEGADOR.md, etapa 4, punto 2.
//
// Traducción de `hoja_pike.componer_hoja_sello` (+ `matriz_colocacion`, `_remapear`, `_num`,
// `altos_de_hojas`) sobre mupdf.js. La tizada de una tela es UNA hoja PDF con una página por mesa
// física; el dibujo de cada mesa desplegada entra a la hoja UNA sola vez como Form XObject de
// página (`/S0`, `/S1`, …) y cada pieza colocada queda como
//
//     q <matriz de colocación> 0 0 W H re W n <base_stream remapeado> <estampado> Q
//
// o sea la matriz que la lleva a su lugar (con el giro del nesting), el recorte a la caja de la
// pieza, el `base_stream` de la base (su recorte al contorno + `/S0 Do` + el borde de corte) y los
// trazos chicos por prenda (nombre, número, etiqueta). Estructura final: UN solo nivel de XObject,
// la que ya deja `aplanar_rip` y la que el RIP del usuario procesó bien (changelog 456 del MAPA).
// El contrato `verificar_navegador_hoja.py` compara esta hoja con la de Python: páginas, tamaños,
// `/UserUnit`, XObjects, content-streams byte a byte y píxeles.
//
// ⚠️ Lo que NO está acá, a propósito:
//   · `componer_hoja_pike` (una copia de la mesa ADENTRO de cada base): es el compositor anterior
//     al sello, y hoy sólo corre con `TIZADA_SIN_SELLO=1`. El sello es el camino de verdad.
//   · `preview_svg` / `svgs_de_bases` (las previas en SVG): nadie las abre desde 2026-09-15.
//
// ─── CONTRATO DE ENTRADA de `componerHoja(mupdf, entrada)` ──────────────────────────────────
//
//   entrada.hojas      — lo que devuelve el nesting (`anidar_contorno` → `nesting/contorno.js`):
//                        una lista por PÁGINA (mesa física) de colocaciones. Las páginas vacías se
//                        saltean, como en Python. Cada colocación:
//       { cx, cy, bw, bh, ang, pieza }
//         cx, cy   — centro de la caja del contorno ROTADO, en puntos, en coordenadas de la hoja
//                    SIN márgenes (origen arriba a la izquierda, y hacia abajo: el nesting trabaja así)
//         bw, bh   — ancho y alto de esa caja rotada (pt)
//         ang      — giro en grados (el nesting da enteros: 0/90/180/270 o cada 15°)
//         pieza    — { base, estampado }
//           estampado — string (latin-1, un carácter por byte) con los operadores POR PRENDA que
//                       arma `pieza/estampar.js` (nombre y número en curvas + etiqueta), o ''.
//                       Ya viene envuelto en `q <clip> W n … Q\n` (así lo deja `generar_pieza`).
//           base      — la base de (pieza, talle[, variable]), UNA por combinación: el MISMO
//                       objeto JS en todas las prendas que la compartan (se deduplica por
//                       identidad, como `id(b)` en Python). Lo que arma `pieza/base.js`:
//               baseStream — string latin-1: `<borde> q cm q <contorno> W n /A0 Do Q Q <línea>` (el
//                            orden depende de la alineación del borde; ver `armarBase`)
//               B          — margen de la pieza = mitad del ancho del borde, en pt
//               W, Hp      — ancho del contorno (pt) y alto de la página de la pieza (H + 2B).
//                            La caja de la pieza en la hoja mide (W + 2B) × Hp.
//               fuentesXo  — qué dibujo de origen nombra el `baseStream` y con qué nombre local:
//                            `[[ '/A0', { origen: 'm1', pagina: 3 } ], …]` (o un objeto
//                            `{ '/A0': {origen, pagina} }`; el ORDEN de primera aparición decide
//                            los nombres globales `/S0`, `/S1`… como en Python). En el camino B
//                            hay UNA entrada: la mesa desplegada, página del talle. Dos bases que
//                            apunten al mismo (origen, pagina) comparten el XObject en la hoja.
//               delMolde   — true si el dibujo viene de un molde desplegado (camino B): entonces
//                            el XObject se marca `/TizadaBase true` (si no anida otros dibujos)
//                            para que el aplanado no lo vuelva a parsear. Default: true.
//   entrada.cfg        — la config del nesting de esa tela: { ancho_cm, margenes_cm: {sup, inf, izq, der} }
//   entrada.origenes   — { [id]: Uint8Array | mupdf.PDFDocument } — los PDF de las mesas
//                        desplegadas (`desplegado/m{mesa}.pdf`), por el id que usan las bases.
//                        Un Uint8Array se abre y se cierra acá; un PDFDocument queda del que llama.
//   entrada.signoRotacion — +1 (default; calibrado contra `show_pdf_page`, ver `matrizColocacion`)
//   entrada.progreso   — opcional: `(etapa, detalle, null) => void`, una llamada por página
//   entrada.perfil     — opcional: `{ icc: Uint8Array, nombre, n }` → OutputIntent /GTS_PDFX
//                        (`servidor._embeber_perfil_pdf`). ⚠️ En el servidor el perfil se pone
//                        DESPUÉS del aplanado para el RIP (que lo borraría); acá se ofrece para
//                        cuando la hoja no pasa por él.
//
//   Devuelve `{ pdf: Uint8Array, consumoCm, alturasCm }` — la hoja sin comprimir (es intermedia:
//   el aplanado para el RIP la vuelve a escribir y ahí sí comprime), el consumo de tela en cm y el
//   alto de cada página (cm, redondeado a 1 decimal como `round(x, 1)` de Python).

import { pyFixed, pyRound } from '../py.js'

export const CM = 72 / 2.54

/** `hoja_pike._num`: `f"{v:.6f}"` sin ceros de más, y «-0» → «0». */
export function num(v) {
  let t = pyFixed(Number(v), 6).replace(/0+$/, '').replace(/\.$/, '')
  if (t === '' || t === '-0') t = '0'
  return t
}

/**
 * `hoja_pike.matriz_colocacion`: la `cm` que deja la base (BBox 0 0 W H, y hacia arriba) donde el
 * compositor de siempre la ponía con `show_pdf_page(rect, doc, 0, rotate=ang)`: el rect es la caja
 * del contorno ROTADO (bw × bh) centrada en (cx, cy) con el origen arriba a la izquierda; en PDF
 * (origen abajo) el centro es (x, alto − y). `signo` = sentido de giro que reproduce a PyMuPDF: +1
 * (con −1 las piezas giradas salían para el otro lado). `s` = 1/UserUnit de la página.
 * Seis decimales también en la traslación: con tres, las piezas giradas caían hasta medio punto
 * más allá y el render difería en los bordes.
 */
export function matrizColocacion(c, m, s, altoPag, W, H, signo = 1) {
  const cx = (m.izq * CM + c.cx) * s
  const cy = altoPag * s - (m.sup * CM + c.cy) * s
  const th = (signo * c.ang) * (Math.PI / 180)          // math.radians
  const ca = Math.cos(th), sa = Math.sin(th)
  const a = s * ca, b = s * sa, c_ = -s * sa, d = s * ca
  // trasladar el centro de la base (W/2, H/2) al centro de la colocación
  const e = cx - (a * W / 2 + c_ * H / 2)
  const f = cy - (b * W / 2 + d * H / 2)
  return `${pyFixed(a, 6)} ${pyFixed(b, 6)} ${pyFixed(c_, 6)} ${pyFixed(d, 6)} ${pyFixed(e, 6)} ${pyFixed(f, 6)} cm`
}

// 🔴 EL JUEGO DE CARACTERES COMPLETO DE UN NOMBRE PDF (`hoja_pike._RX_NOM`). Los nombres locales
// pueden ser al azar del estilo `/Ax_-73ZjlLXUbUuqaylXI2g`: con letras y dígitos solos el remapeo no
// acertaba ninguno y la hoja salía con «cannot find XObject resource».
const RX_NOM = /\/([^\s/[\]<>(){}%]+)(?=\s+Do(?![A-Za-z0-9]))/g

/** `hoja_pike._remapear`: los nombres de XObject del `baseStream` → los globales de la hoja. */
export function remapear(stream, ren) {
  if (!ren || !Object.keys(ren).length) return stream
  return stream.replace(RX_NOM, (_todo, nombre) => ren['/' + nombre] ?? '/' + nombre)
}

/** `hoja_pike.altos_de_hojas`: el alto (pt) de cada página, con la misma cuenta que la hoja. */
export function altosDeHojas(hojas, cfg) {
  const m = cfg.margenes_cm
  const out = []
  for (const hoja of hojas) {
    if (!hoja || !hoja.length) continue
    out.push(altoUsado(hoja) + (m.sup + m.inf) * CM)
  }
  return out
}

function altoUsado(hoja) {
  // max(c["cy"] + c["bh"] / 2 for c in hoja)
  let mx = -Infinity
  for (const c of hoja) { const v = c.cy + c.bh / 2; if (v > mx) mx = v }
  return mx
}

const nulo = (o) => !o || o.isNull()

/** Un string latin-1 (un carácter = un byte) → bytes. */
function bytesLatin1(s) {
  const u = new Uint8Array(s.length)
  for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255
  return u
}

function concatenar(partes) {
  let n = 0
  for (const p of partes) n += p.length
  const out = new Uint8Array(n)
  let k = 0
  for (const p of partes) { out.set(p, k); k += p.length }
  return out
}

/** El contenido de una página de origen: uno o varios streams unidos por '\n' (qpdf). */
function contenidoDePagina(pageObj) {
  const c = pageObj.get('Contents')
  if (nulo(c)) return new Uint8Array(0)
  if (c.isArray()) {
    const partes = []
    for (let i = 0; i < c.length; i++) {
      if (i) partes.push(new Uint8Array([10]))
      partes.push(c.get(i).readStream().asUint8Array().slice())
    }
    return concatenar(partes)
  }
  return c.readStream().asUint8Array().slice()
}

// Los atributos de página se leen como qpdf (`getAttribute`): HEREDABLES desde el árbol /Pages.
function leerCaja(pageObj, clave) {
  const v = pageObj.getInheritable(clave)
  if (nulo(v) || !v.isArray() || v.length !== 4) return null
  const out = []
  // `toString()` y no `asNumber()`: los reales de mupdf son float32 (2214.33 → 2214.330078)
  for (let i = 0; i < 4; i++) { const x = v.get(i); if (!x.isNumber()) return null; out.push(x.isInteger() ? x.asNumber() : Number(x.toString())) }
  return out
}

/**
 * El dibujo de una página de origen como Form XObject de la hoja: lo que en Python hace
 * `pag.as_form_xobject()` (qpdf `getFormXObjectForPage`: `/BBox` = TrimBox → CropBox → MediaBox,
 * `/Matrix` sólo si la página trae `/Rotate` o `/UserUnit`, `/Resources` los de la página, y el
 * contenido concatenado) seguido de `copy_foreign` + lo que `componer_hoja_sello._global` le saca
 * (`/OC`, `/Group`) y le pone (`/TizadaBase true` si es del molde y no anida otros dibujos).
 */
function formDeOrigen(out, mapa, srcDoc, pagina, delMolde) {
  const pageObj = srcDoc.findPage(pagina)
  const caja = leerCaja(pageObj, 'TrimBox') || leerCaja(pageObj, 'CropBox') || leerCaja(pageObj, 'MediaBox')
  const dict = out.newDictionary()
  dict.put('Type', out.newName('XObject'))
  dict.put('Subtype', out.newName('Form'))
  const bbox = out.newArray()
  for (const v of (caja || [0, 0, 612, 792])) bbox.push(out.newReal(v))
  dict.put('BBox', bbox)
  const rotO = pageObj.getInheritable('Rotate'), uuO = pageObj.getInheritable('UserUnit')
  const hayRot = !nulo(rotO), hayUU = !nulo(uuO)
  if (caja && (hayRot || hayUU)) {
    // qpdf `getMatrixForTransformations(invert=false)`: la escala de /UserUnit y el giro de /Rotate
    const [llx, lly, urx, ury] = caja
    const width = urx - llx, height = ury - lly
    const scale = hayUU && uuO.isNumber() ? (uuO.isInteger() ? uuO.asNumber() : Number(uuO.toString())) : 1.0
    const rotate = hayRot && rotO.isNumber() ? Math.trunc(rotO.asNumber()) : 0
    let mtx
    switch (rotate) {
      case 90: mtx = [0, -scale, scale, 0, 0, width * scale]; break
      case 180: mtx = [-scale, 0, 0, -scale, width * scale, height * scale]; break
      case 270: mtx = [0, scale, -scale, 0, height * scale, 0]; break
      default: mtx = [scale, 0, 0, scale, 0, 0]
    }
    const arr = out.newArray()
    for (const v of mtx) arr.push(out.newReal(v))
    dict.put('Matrix', arr)
  }
  const res = pageObj.get('Resources')
  let anida = false
  if (!nulo(res)) {
    dict.put('Resources', mapa.graftObject(res))
    try { anida = !nulo(res.resolve().get('XObject')) } catch { anida = false }
  }
  // 🔴 LA MESA DEL MOLDE DESPLEGADO YA VIENE LIMPIA (sin marcadores de capa, con sus fuentes
  // declaradas, balanceada): marcarla le ahorra al aplanado volver a parsear sus operadores. Sólo
  // si no anida otros dibujos adentro. Una clave privada en un XObject es PDF válido.
  if (delMolde && !anida) dict.put('TizadaBase', true)
  return out.addStream(contenidoDePagina(pageObj), dict)
}

function entradasFuentes(fx) {
  if (!fx) return []
  if (Array.isArray(fx)) return fx
  return Object.keys(fx).map((k) => [k, fx[k]])
}

/**
 * `servidor._embeber_perfil_pdf`: el perfil ICC como OutputIntent (PDF/X). TAGEA el destino de
 * color sin convertir ni tocar un valor.
 */
export function embeberPerfil(out, perfil) {
  if (!perfil || !perfil.icc || !perfil.icc.length) return false
  const iccDict = out.newDictionary()
  iccDict.put('N', out.newInteger(Number(perfil.n || 4)))
  const icc = out.addStream(perfil.icc, iccDict)
  const oi = out.newDictionary()
  oi.put('Type', out.newName('OutputIntent'))
  oi.put('S', out.newName('GTS_PDFX'))
  oi.put('OutputConditionIdentifier', out.newString(perfil.nombre || 'Custom'))
  oi.put('Info', out.newString(perfil.nombre || 'Custom'))
  oi.put('DestOutputProfile', icc)
  const arr = out.newArray()
  arr.push(out.addObject(oi))
  out.getTrailer().get('Root').put('OutputIntents', arr)
  return true
}

/**
 * `hoja_pike.componer_hoja_sello`. Ver el contrato de entrada en el encabezado del archivo.
 * Devuelve `{ pdf, consumoCm, alturasCm }`.
 */
export function componerHoja(mupdf, entrada) {
  const { hojas, cfg, origenes = {}, signoRotacion = 1, progreso = null, perfil = null } = entrada
  const m = cfg.margenes_cm
  const anchoPag = cfg.ancho_cm * CM
  const out = new mupdf.PDFDocument()
  const abiertos = []                    // documentos de origen abiertos acá (se cierran al final)
  const docs = new Map()                 // id de origen → PDFDocument
  const mapas = new Map()                // id de origen → graft map (uno por documento de origen)
  const porFuente = new Map()            // 'origen|pagina' → nombre global (/S0…)
  const xobjs = new Map()                // nombre global → XObject de la hoja
  const renPorBase = new Map()           // base → { nombre local: nombre global }

  const docDe = (id) => {
    let d = docs.get(id)
    if (d) return d
    const src = origenes[id]
    if (src === undefined || src === null) throw new Error(`la hoja necesita el origen «${id}» y no vino`)
    if (src instanceof Uint8Array || src instanceof ArrayBuffer) {
      d = new mupdf.PDFDocument(src)
      abiertos.push(d)
    } else d = src
    docs.set(id, d)
    mapas.set(id, out.newGraftMap())
    return d
  }

  // El nombre global de un dibujo de origen; lo copia a la hoja la primera vez.
  const global = (ref, delMolde) => {
    const k = `${ref.origen}|${ref.pagina}`
    let nm = porFuente.get(k)
    if (nm === undefined) {
      const doc = docDe(ref.origen)
      const xo = formDeOrigen(out, mapas.get(ref.origen), doc, Number(ref.pagina), delMolde)
      nm = `/S${porFuente.size}`
      porFuente.set(k, nm)
      xobjs.set(nm, xo)
    }
    return nm
  }

  const ren = (b) => {
    let r = renPorBase.get(b)
    if (r === undefined) {
      const dm = b.delMolde !== false
      r = {}
      for (const [nom, ref] of entradasFuentes(b.fuentesXo)) r[nom] = global(ref, dm)
      renPorBase.set(b, r)
    }
    return r
  }

  let consumoCm = 0.0
  const alturasCm = []
  const porPagina = []                   // [objeto de página, nombres de dibujo que usa]
  for (const hoja of hojas) {
    if (!hoja || !hoja.length) continue
    const altoPag = altoUsado(hoja) + (m.sup + m.inf) * CM
    // ── MESAS DE MÁS DE 5,08 m: /UserUnit ─────────────────────────────────────────────────
    // Ninguna página PDF puede pasar de 14400 unidades por lado (508 cm). Cada unidad vale `uu`
    // puntos: se dibuja TODO dividido por `uu` y el lector lo multiplica de vuelta (verificado con
    // el RIP del usuario). Con uu = 1 no cambia nada.
    const uu = Math.max(1, Math.ceil(Math.max(anchoPag, altoPag) / 14400.0))
    const s = 1.0 / uu
    const partes = []
    const usados = new Set()
    for (const c of hoja) {
      const pz = c.pieza
      const b = pz.base
      const W = Number(b.W) + 2 * Number(b.B)
      const H = Number(b.Hp)
      const mtx = matrizColocacion(c, m, s, altoPag, W, H, signoRotacion)
      const r = ren(b)
      for (const nm of Object.values(r)) usados.add(nm)
      // 🔴 EL RECORTE A LA CAJA DE LA PIEZA. El compositor de siempre mostraba cada pieza como una
      // PÁGINA (recortada a su MediaBox); acá el contenido se pega inline, así que el recorte hay
      // que ponerlo, o lo que la pieza dibujara un pelo afuera de su caja saldría en la hoja.
      partes.push(bytesLatin1(`q\n${mtx}\n0 0 ${num(W)} ${num(H)} re\nW\nn\n`))
      partes.push(bytesLatin1(remapear(b.baseStream, r)))
      const est = pz.estampado || ''
      if (est) partes.push(bytesLatin1(est))
      partes.push(bytesLatin1('Q\n'))
    }
    const pg = out.newDictionary()
    pg.put('Type', out.newName('Page'))
    const mb = out.newArray()
    for (const v of [0, 0, anchoPag * s, altoPag * s]) mb.push(out.newReal(v))
    pg.put('MediaBox', mb)
    if (uu > 1) pg.put('UserUnit', out.newInteger(uu))
    pg.put('Contents', out.addStream(concatenar(partes), out.newDictionary()))
    const ref = out.addObject(pg)
    out.insertPage(out.countPages(), ref)
    porPagina.push([ref, usados])
    alturasCm.push(pyRound(altoPag / CM, 1))
    consumoCm += altoPag / CM
    if (progreso) progreso('escribir el PDF', `mesa ${alturasCm.length}`, null)
  }
  // Cada página con SU PROPIA tabla de recursos (los streams se comparten; lo que se repite es la
  // lista de nombres): el aplanado limpia los huérfanos página por página, y con una tabla
  // compartida la limpieza de la primera se llevaría los dibujos que usan las otras.
  for (const [ref, usados] of porPagina) {
    const tabla = out.newDictionary()
    for (const nm of [...usados].sort()) tabla.put(nm.slice(1), xobjs.get(nm))
    const res = out.newDictionary()
    res.put('XObject', tabla)
    ref.put('Resources', res)
  }
  if (perfil) embeberPerfil(out, perfil)
  // Sin comprimir: el aplanado para el RIP la vuelve a escribir (y ahí sí comprime).
  const pdf = out.saveToBuffer('').asUint8Array().slice()
  for (const mp of mapas.values()) { try { mp.destroy() } catch { /* nada */ } }
  try { out.destroy() } catch { /* nada */ }
  for (const d of abiertos) { try { d.destroy() } catch { /* nada */ } }
  return { pdf, consumoCm, alturasCm }
}
