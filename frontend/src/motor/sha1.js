// SHA-1 sincrónico (el `crypto.subtle` del navegador es asincrónico y el motor necesita el hash en
// medio de un cálculo: `hash_ocultas` de piezas_con_diseno.py). Implementación directa de FIPS 180-1.

export function sha1Hex(texto) {
  const datos = new TextEncoder().encode(texto)
  return sha1HexBytes(datos)
}

export function sha1HexBytes(datos) {
  const n = datos.length
  const bloques = ((n + 9 + 63) >> 6) << 6
  const m = new Uint8Array(bloques)
  m.set(datos)
  m[n] = 0x80
  const bits = n * 8
  const dv = new DataView(m.buffer)
  dv.setUint32(bloques - 4, bits >>> 0)
  dv.setUint32(bloques - 8, Math.floor(bits / 4294967296))
  let h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0
  const w = new Uint32Array(80)
  for (let off = 0; off < bloques; off += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(off + i * 4)
    for (let i = 16; i < 80; i++) {
      const x = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]
      w[i] = (x << 1) | (x >>> 31)
    }
    let a = h0, b = h1, c = h2, d = h3, e = h4
    for (let i = 0; i < 80; i++) {
      let f, k
      if (i < 20) { f = (b & c) | (~b & d); k = 0x5A827999 }
      else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1 }
      else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC }
      else { f = b ^ c ^ d; k = 0xCA62C1D6 }
      const t = (((a << 5) | (a >>> 27)) + f + e + k + w[i]) >>> 0
      e = d; d = c; c = (b << 30) | (b >>> 2); b = a; a = t
    }
    h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0; h4 = (h4 + e) >>> 0
  }
  return [h0, h1, h2, h3, h4].map((v) => v.toString(16).padStart(8, '0')).join('')
}
