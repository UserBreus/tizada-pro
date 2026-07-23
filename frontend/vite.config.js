import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// La app puede vivir en la RAÍZ del dominio (el taller: http://localhost:8050/) o colgada de una
// SUB-RUTA (el servidor publicado: https://…/Tizadapro/). El prefijo se elige al COMPILAR:
//     npm run build                         → "/"           (taller, como siempre)
//     TIZADA_BASE=/Tizadapro/ npm run build → "/Tizadapro/" (publicado)
// Vite reescribe con eso las rutas de los assets del index.html y lo expone en
// `import.meta.env.BASE_URL`, que es lo que lee el envoltorio de `fetch` (src/base.js).
const BASE = process.env.TIZADA_BASE || '/'

// https://vite.dev/config/
export default defineConfig({
  base: BASE,
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8050',
        changeOrigin: true,
      },
      '/trabajos': {
        target: 'http://127.0.0.1:8050',
        changeOrigin: true,
      }
    }
  }
})
