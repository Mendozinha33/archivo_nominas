import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
import './estilos.css'
import { ProveedorSesion } from './lib/sesion'

createRoot(document.getElementById('raiz')).render(
  <React.StrictMode>
    {/* Los future flags evitan los avisos de React Router y ya dejan el comportamiento de v7. */}
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ProveedorSesion>
        <App />
      </ProveedorSesion>
    </BrowserRouter>
  </React.StrictMode>,
)
