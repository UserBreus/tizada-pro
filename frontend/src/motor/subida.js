// NO VOLVER A SUBIR UN ARCHIVO QUE EL SERVIDOR YA TIENE — PLAN_NAVEGADOR.md, etapa 1 (pendiente).
//
// El navegador ya calcula el SHA-1 del molde y del arte para armar sus paquetes. Antes de mandar
// los bytes pregunta `GET /api/archivos/tengo?sha1=`: si el servidor lo tiene (mismo molde en otro
// artículo, un reintento, otro pedido), manda `archivo_sha1` + `archivo_nombre` y el servidor lo
// copia de donde está (`servidor._archivo_subido`). Un molde de 120 MB no viaja dos veces.

/** Agrega a `fd` el archivo (o su sha1, si el servidor ya lo tiene). Devuelve `true` si no viajó. */
export async function adjuntarArchivo(fd, archivo, sha1, rutaApi = (x) => x, campo = 'archivo') {
  fd.delete(campo)
  if (sha1) {
    try {
      const r = await fetch(rutaApi(`/api/archivos/tengo?sha1=${encodeURIComponent(sha1)}`))
      const d = r.ok ? await r.json() : null
      if (d && d.tengo) {
        fd.append(campo + '_sha1', sha1)
        fd.append(campo + '_nombre', archivo.name || 'archivo')
        return true
      }
    } catch { /* sin respuesta: viaja el archivo, como siempre */ }
  }
  fd.append(campo, archivo, archivo.name || undefined)
  return false
}
