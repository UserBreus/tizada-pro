import './base.js'          // PRIMERO: deja el fetch listo para la sub-ruta antes de montar la app
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { prepararPestana } from './pestana.js'

// CADA PESTAÑA, SU PEDIDO (MAPA 762): antes de dibujar se decide de quién es el avance guardado (unos ms)
prepararPestana().catch(() => {}).finally(() => {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
})
