// node frontend/src/motor/pruebas/capacidad.mjs <mb_del_trabajo> [tipo] [memoria_gb_declarada]
// La puerta de la etapa 5 en Node: con una máquina que declara poca memoria tiene que CERRAR; con
// memoria de sobra tiene que ABRIR. Lo corre `verificar_navegador_capacidad.py`.
// (Los ArrayBuffer viven fuera del heap de V8: `--max-old-space-size` no sirve para simular poca
//  memoria; se simula lo que el navegador DECLARA, que es lo primero que mira la puerta.)
import { puedeHacer, memoriaParaMolde, puntosDePotencia } from '../capacidad.js'

const mb = Number(process.argv[2] || 100)
const tipo = process.argv[3] || 'molde'
const memGb = process.argv[4] ? Number(process.argv[4]) : undefined
// En Node no hay `navigator`: se simula lo que diría un navegador de escritorio
Object.defineProperty(globalThis, 'navigator', { value: { hardwareConcurrency: 4, deviceMemory: memGb, userAgent: 'node' }, configurable: true })
globalThis.Worker = class {}
const r = puedeHacer({ tipo, mb, hilos: 2 })
console.log(JSON.stringify({ puede: r.puede, motivo: r.motivo, necesita: memoriaParaMolde(mb, 2), puntos: r.detalle && r.detalle.puntos, benchmark: puntosDePotencia(300) }))
