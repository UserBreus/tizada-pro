// CREAR LA PLANTILLA EN ILLUSTRATOR O CORELDRAW DESDE LA PÁGINA DEL SISTEMA EXTERNO
// Navegador (módulo ES), sin dependencias. Hace LO MISMO que el botón «Crear en Illustrator / CorelDRAW» de
// TIZADA PRO: busca el conector en la computadora del diseñador, compara su versión con la que dice TIZADA,
// le manda cada archivo del plan EN ORDEN y junta lo que contestó (mesas armadas, archivos .ai guardados).
//
// TIZADA PRO dice CÓMO se crea: el plan (cada archivo «… - Illustrator.json» / «… - CorelDRAW.json") trae las
// mesas con su nombre, las capas, los contornos y las guías; el conector lo arma tal cual en el programa. Esta
// página no calcula nada: sólo lleva el plan de TIZADA al conector.
//
// EL CAMINO
//   1. SU SERVIDOR pide la plantilla y espera a que esté (la llave X-Api-Key vive en su servidor, NUNCA en el
//      navegador; ver `cliente.mjs plantilla …`):
//        POST /api/externo/v1/plantillas            → 202
//        GET  /api/externo/v1/plantillas/{ref}      → hasta «listo» (trae `archivos` y `conectores`)
//   2. SU PÁGINA, abierta en la computadora del diseñador (donde está instalado el conector y el programa):
//
//        import { crearEnPrograma } from './crear_en_programa.js'
//        const estado = await (await fetch('/su-servidor/plantillas/PL-0001')).json()   // lo de GET /plantillas/PL-0001
//        const r = await crearEnPrograma({
//          programa: 'illustrator',                 // o 'corel'
//          estado,
//          diseno: 'JUGADOR',                       // un diseño de la plantilla (sin esto, todos)
//          traer: (archivo) => fetch('/su-servidor/plantillas/PL-0001/archivos/' + encodeURIComponent(archivo.nombre))
//                                .then((x) => x.text()),  // su servidor lo baja de TIZADA con la llave
//          alAvanzar: (texto) => mostrarCartel(texto),
//        })
//        // r = { ok: true, programa: 'illustrator', mesas: 15, archivos: ['JUGADOR.ai'],
//        //       carpeta: 'Documentos › USER PRO › Plantillas', avisos: [] }
//
//   Si falla, tira un Error con `codigo`:
//     'no-lista'      la plantilla todavía no está «listo» en TIZADA
//     'sin-archivos'  no hay archivos de ese programa (o de ese diseño) en la plantilla
//     'sin-conector'  el conector no está instalado en esta computadora o el programa no está abierto
//                     (`error.instalador` = de dónde bajarlo en la API de TIZADA)
//     'programa'      el programa contestó un error al armar (el mensaje es el suyo)
//
// LO QUE HAY QUE SABER
//   · El conector escucha SÓLO en la computadora del diseñador (127.0.0.1) y acepta pedidos de cualquier página
//     (contesta el pedido previo de CORS y el de red local que pide Chrome). La primera vez el navegador puede
//     preguntar si la página puede acceder a dispositivos de la red local: hay que permitirlo.
//   · No agregar cabeceras propias al pedido al conector: sólo `Content-Type: application/json`.
//   · Illustrator tiene que estar ABIERTO. CorelDRAW (2022 o más nuevo) se abre solo si está cerrado.
//   · Un diseño grande puede venir en varios archivos de Illustrator (`parte` «1 de 2»…): se mandan todos, en
//     orden; cada uno queda como un .ai aparte en Documentos › USER PRO › Plantillas.

export const PUERTOS = { illustrator: 47850, corel: 47851 }
const NOMBRE = { illustrator: 'Illustrator', corel: 'CorelDRAW' }

const fallo = (codigo, mensaje, extra = {}) => Object.assign(new Error(mensaje), { codigo, ...extra })
// «2 de 3» → 2 (sin parte = 1): los archivos de un programa se mandan en ese orden
const numeroDeParte = (a) => { const m = /^(\d+)/.exec(String(a.parte || '')); return m ? Number(m[1]) : 1 }

/**
 * ¿Está el conector en esta computadora? → lo que contesta su `/estado` ({app, version, …}) o null.
 * `direccion` sólo para pruebas (por defecto http://127.0.0.1:<puerto del programa>).
 */
export async function buscarConector(programa, { esperaMs = 5000, direccion } = {}) {
  const base = direccion || `http://127.0.0.1:${PUERTOS[programa]}`
  const ctl = new AbortController()
  const t = setTimeout(() => ctl.abort(), esperaMs)
  try {
    const r = await fetch(`${base}/estado`, { signal: ctl.signal, cache: 'no-store' })
    if (!r.ok) return null
    const d = await r.json().catch(() => null)
    if (!d || d.app !== 'TIZADA PRO') return null
    if (programa === 'corel' && d.programa !== 'corel') return null       // el de Illustrator no sirve para Corel
    if (programa === 'illustrator' && d.programa === 'corel') return null
    return d
  } catch {
    return null
  } finally {
    clearTimeout(t)
  }
}

/** Crea la plantilla en el programa (ver el encabezado). */
export async function crearEnPrograma({ programa, estado, diseno = null, traer, alAvanzar = () => {}, direccion } = {}) {
  if (!PUERTOS[programa]) throw fallo('programa', 'programa: tiene que ser «illustrator» o «corel»')
  if (typeof traer !== 'function') throw fallo('programa', 'falta `traer(archivo)`: devuelve el contenido del archivo (texto)')
  if (!estado || estado.estado !== 'listo') {
    throw fallo('no-lista', `la plantilla todavía no está lista en TIZADA PRO (estado: ${(estado && estado.estado) || 'desconocido'})`)
  }
  const info = (estado.conectores || {})[programa] || {}
  const tipo = info.tipo_archivo || programa
  const archivos = (estado.archivos || [])
    .filter((a) => a.tipo === tipo && (!diseno || a.diseno === diseno))
    .sort((a, b) => numeroDeParte(a) - numeroDeParte(b))
  if (!archivos.length) {
    throw fallo('sin-archivos', `la plantilla no trae archivos de ${NOMBRE[programa]}${diseno ? ` para «${diseno}»` : ''}`)
  }

  alAvanzar(`Buscando ${NOMBRE[programa]} en esta computadora…`)
  const con = await buscarConector(programa, { direccion })
  if (!con) {
    throw fallo('sin-conector', `No se encontró el conector de ${NOMBRE[programa]} en esta computadora` +
      (programa === 'illustrator' ? ' (o Illustrator no está abierto)' : '') + '. Hay que instalarlo una vez.',
      { instalador: info.instalador || '/api/externo/v1/conectores' })
  }
  const avisos = []
  // la misma comparación que hace TIZADA para avisar que hay una versión nueva del conector
  if (info.version && con.version && con.version !== info.version) {
    avisos.push(`Hay una versión nueva del conector de ${NOMBRE[programa]} (tiene la ${con.version}, la nueva es la ${info.version}): conviene volver a instalarlo.`)
  }

  const base = direccion || `http://127.0.0.1:${PUERTOS[programa]}`
  let mesas = 0, fallidos = 0
  const guardados = []
  for (let i = 0; i < archivos.length; i++) {
    const a = archivos[i]
    const n = archivos.length > 1 ? `Archivo ${i + 1} de ${archivos.length}: ` : ''
    alAvanzar(`${n}trayendo el plan de TIZADA PRO…`)
    const plan = await traer(a)
    alAvanzar(`${n}armando en ${NOMBRE[programa]}…`)
    // el plan VA TAL CUAL lo dio TIZADA (no se toca ni se vuelve a armar); sólo esta cabecera
    const r = await fetch(`${base}/plantilla`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: typeof plan === 'string' ? plan : JSON.stringify(plan),
    })
    const d = await r.json().catch(() => ({}))
    if (!r.ok || !d.ok) throw fallo('programa', d.error || `${NOMBRE[programa]} contestó ${r.status}`)
    mesas += d.mesas || 0
    fallidos += d.textosFallidos || 0
    if (d.archivo) guardados.push(d.archivo)
  }
  if (fallidos) avisos.push(`${fallidos} mesa${fallidos === 1 ? '' : 's'} quedó sin su nombre escrito: ${NOMBRE[programa]} no lo aceptó.`)
  return { ok: true, programa, mesas, archivos: guardados, carpeta: 'Documentos › USER PRO › Plantillas', avisos }
}
