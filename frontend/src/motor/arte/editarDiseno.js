// «EDITAR DISEÑO»: LO QUE PIDE LA PANTALLA, ARMADO EN ESTA COMPUTADORA — 2026-09-22.
//
// Agregar un objeto, colocarlo en una pieza, quitarlo del diseño y duplicarlo. El trabajo sobre
// los archivos lo hace un hilo (`obrero.worker.js` → `objeto_normalizar`, `arte_colocar`,
// `arte_quitar`, `arte_capas`, `svg_de_pdf`; ver `arte/editarArte.js`) y el servidor sólo guarda
// (el objeto normalizado, o la versión nueva del arte). El SVG se convierte acá (`svgPdf.js`).
import { enHiloSuelto } from '../hiloSuelto.js'
import { traerConCache } from '../cache.js'
import { svgAPdf } from './svgPdf.js'

async function json(url, opts) {
  const r = await fetch(url, opts)
  const d = await r.json().catch(() => ({}))
  if (!r.ok) { const e = new Error(d.error || `${url}: ${r.status}`); e.datos = d; throw e }
  return d
}
const qDis = (diseno, sep = '?') => (diseno && diseno !== 'principal' ? `${sep}diseno=${encodeURIComponent(diseno)}` : '')

/** Los datos del diseño que se edita (`/motor_b`: registro, mapeo, objetos, sello y versión). */
async function disenoDe(pid, diseno, rutaApi) {
  const info = await json(rutaApi(`/api/productos/${encodeURIComponent(pid)}/motor_b`))
  if (!info.camino_a) throw new Error('este molde no tiene un arte aparte para editar')
  const d = (info.disenos || []).find((x) => x.id === (diseno || 'principal'))
  if (!d) throw new Error('este diseño no tiene el arte cargado')
  return { info, d }
}
async function arteDe(pid, d, rutaApi) {
  return (await traerConCache(`arte|${pid}|${d.id}|${(d.sello || []).join(',')}`,
    rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_archivo${qDis(d.id)}`))).slice()
}

/**
 * AGREGAR: el archivo se normaliza acá a un PDF de una página (un SVG se convierte primero) y se
 * sube ya hecho. Devuelve el objeto como lo devolvía el servidor (`{…, svg: texto}`).
 */
export async function agregarObjeto(file, { pid, diseno, rutaApi }) {
  let bytes = new Uint8Array(await file.arrayBuffer())
  let nombreArchivo = file.name || 'objeto'
  if (/\.svg$/i.test(nombreArchivo)) {
    const conv = svgAPdf(new TextDecoder('utf-8').decode(bytes))
    bytes = conv.pdf
  }
  const r = await enHiloSuelto('objeto_normalizar', { bytes, nombre: nombreArchivo }, [bytes.buffer], 'objeto')
  const fd = new FormData()
  fd.append('pdf', new Blob([r.pdf], { type: 'application/pdf' }), 'objeto.pdf')
  fd.append('normalizado', '1')
  fd.append('pid', pid); fd.append('diseno', diseno || 'principal')
  fd.append('nombre', (nombreArchivo || 'Objeto').replace(/\.[^.]+$/, ''))
  fd.append('w_cm', String(r.w_cm)); fd.append('h_cm', String(r.h_cm)); fd.append('tipo', r.tipo)
  const d = await json(rutaApi('/api/productos/objeto_agregar'), { method: 'POST', body: fd })
  return { ...d.objeto, svg: r.svg || '' }
}

/**
 * COLOCAR: el objeto entra al arte como la capa «Editable <nombre>» en la mesa de la pieza (en
 * cada rango que use) y el arte nuevo se sube como versión nueva. `fx/fy` = el punto tocado, en
 * fracciones de la pieza.
 */
export async function colocarObjeto({ pid, diseno, oid, pieza, fx, fy, rutaApi }) {
  const { info, d } = await disenoDe(pid, diseno, rutaApi)
  const obj = (d.objetos || []).find((o) => String(o.id) === String(oid))
  if (!obj) throw new Error('el objeto ya no está')
  if (!(info.registro || {})[pieza]) throw new Error('falta la pieza en el molde')
  const arte = await arteDe(pid, d, rutaApi)
  const objPdf = (await traerConCache(`oa|${pid}|${d.id}|${obj.id}|${obj.archivo}`,
    rutaApi(`/api/productos/${encodeURIComponent(pid)}/objeto_agregado/${encodeURIComponent(obj.id)}${qDis(d.id)}`))).slice()
  const r = await enHiloSuelto('arte_colocar', {
    arte, registro: info.registro, mapeoBase: ((d.mapeo || {}).mapeo) || {}, pieza, fx, fy,
    wCm: Number(obj.w_cm || 0), hCm: Number(obj.h_cm || 0), objPdf, nombre: obj.nombre || obj.id,
  }, [arte.buffer, objPdf.buffer], 'arte')
  const fd = new FormData()
  fd.append('arte', new Blob([r.bytes], { type: 'application/pdf' }), 'arte.pdf')
  fd.append('pid', pid); fd.append('diseno', diseno || 'principal'); fd.append('pieza', pieza)
  fd.append('capa', r.capa); fd.append('mesas', JSON.stringify(r.mesas)); fd.append('version_base', String(d.version ?? ''))
  return json(rutaApi(`/api/productos/objeto_agregado/${encodeURIComponent(oid)}/colocar`), { method: 'POST', body: fd })
}

/**
 * QUITAR DEL DISEÑO una capa que agregó el usuario. Se comprueba acá que NO venga en el arte
 * original (`capas_agregadas`: la vigente menos la original, por posición) y el arte sin la capa
 * se sube como versión nueva.
 */
export async function quitarDelDiseno({ pid, diseno, capa, rutaApi }) {
  const { d } = await disenoDe(pid, diseno, rutaApi)
  const arte = await arteDe(pid, d, rutaApi)
  const orig = new Uint8Array(await (await fetch(rutaApi(`/api/productos/${encodeURIComponent(pid)}/arte_archivo?original=1${qDis(d.id, '&')}`))).arrayBuffer())
  const [vig, ori] = await Promise.all([
    enHiloSuelto('arte_capas', { bytes: arte.slice() }, [], 'arte'),
    enHiloSuelto('arte_capas', { bytes: orig }, [orig.buffer], 'arte'),
  ])
  const quedan = [...ori], agregadas = new Set()
  for (const n of vig) { const i = quedan.indexOf(n); if (i >= 0) quedan.splice(i, 1); else agregadas.add(n) }
  const r = await enHiloSuelto('arte_quitar', { arte, capa }, [arte.buffer], 'arte')
  const fd = new FormData()
  fd.append('arte', new Blob([r.bytes], { type: 'application/pdf' }), 'arte.pdf')
  fd.append('pid', pid); fd.append('diseno', diseno || 'principal'); fd.append('capa', capa)
  fd.append('borrados', String(r.borrados)); fd.append('version_base', String(d.version ?? ''))
  if (agregadas.has(capa)) fd.append('agregada_segun_original', '1')
  return json(rutaApi('/api/productos/editable_quitar'), { method: 'POST', body: fd })
}

/** DUPLICAR: el servidor copia el archivo; la vista (SVG) de la copia se dibuja acá. */
export async function duplicarObjeto({ pid, diseno, oid, rutaApi }) {
  const d = await json(rutaApi(`/api/productos/objeto_agregado/${encodeURIComponent(oid)}/duplicar`), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid, diseno }),
  })
  const o = d.objeto || {}
  if (!o.svg && o.archivo) {
    try {
      const b = new Uint8Array(await (await fetch(rutaApi(`/api/productos/${encodeURIComponent(pid)}/objeto_agregado/${encodeURIComponent(o.id)}${qDis(diseno)}`))).arrayBuffer())
      o.svg = await enHiloSuelto('svg_de_pdf', { bytes: b }, [b.buffer], 'objeto')
    } catch { o.svg = '' }
  }
  return o
}
