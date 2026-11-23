// LOS DATOS DEL MOLDE (`/api/productos/<pid>/motor_b`), UNA SOLA VEZ AUNQUE LOS PIDAN VARIOS A LA VEZ (MAPA 770).
//
// Al elegir una tipografía, la vista previa, el estado de fuentes y el editor pedían el MISMO `/motor_b` a la vez
// (el inspector vio tres seguidos). Mientras uno está en viaje, los demás esperan ESE; cuando llega, cada uno recibe
// su propia copia (los que llaman la modifican). Nada se guarda después: el siguiente pedido va al servidor (si no,
// se vería la lista de objetos o la config de antes de un cambio).
const enViaje = new Map()

/** Un GET de JSON que, si ya está en viaje el mismo, espera ése (también lo usa la plantilla `pdf_guia`, MAPA 772:
 *  al abrirla salían 3 iguales). `msjError` = lo que se dice si el servidor no explica. */
export function pedirJsonUnaVez(url, msjError = null) {
  let p = enViaje.get(url)
  if (!p) {
    p = fetch(url).then(async (r) => {
      const d = await r.json().catch(() => ({}))
      if (!r.ok) { const e = new Error(d.error || msjError || `${url}: ${r.status}`); e.datos = d; throw e }
      return d
    })
    enViaje.set(url, p)
    const soltar = () => { if (enViaje.get(url) === p) enViaje.delete(url) }
    p.then(soltar, soltar)
  }
  return p.then((d) => structuredClone(d))
}

export const pedirMotorB = (url) => pedirJsonUnaVez(url)
