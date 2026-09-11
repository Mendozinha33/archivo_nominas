import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import { Estado } from './componentes/Piezas'
import { useSesion } from './lib/sesion'
import Acceso from './paginas/Acceso'
import Archivo from './paginas/Archivo'
import Plantilla from './paginas/Plantilla'
import Procesar from './paginas/Procesar'
import Registro from './paginas/Registro'
import Revision from './paginas/Revision'
import Usuarios from './paginas/Usuarios'

export default function App() {
  const { usuario, cargando, esAdmin, salir } = useSesion()

  if (cargando) {
    return (
      <div className="lienzo">
        <Estado texto="Conectando con el servidor…" />
      </div>
    )
  }

  if (!usuario) return <Acceso />

  return (
    <div className="lienzo">
      <header className="club">
        <div className="cab-fila">
          <div>
            <p className="eyebrow">Gestión de nóminas y contratos</p>
            <h1>Archivo de <em>nóminas</em></h1>
          </div>
          <div className="quien-soy">
            <span><b>{usuario.nombre}</b><br />{usuario.rol}</span>
            <button className="btn mini fantasma" onClick={salir}>Salir</button>
          </div>
        </div>
        <p className="lead">
          Sube el PDF con todas las nóminas del mes. Cada hoja se separa, se nombra
          {' '}<span style={{ fontFamily: 'var(--mono)' }}>trabajador_mes.pdf</span> y se guarda
          en la carpeta de su trabajador, junto a su contrato y sus documentos.
        </p>
      </header>

      <nav className="pestanas">
        <Pestana a="/">Plantilla</Pestana>
        <Pestana a="/procesar">Procesar</Pestana>
        <Pestana a="/archivo">Archivo</Pestana>
        <Pestana a="/revision">Revisión</Pestana>
        <Pestana a="/registro">Registro</Pestana>
        {esAdmin && <Pestana a="/usuarios">Usuarios</Pestana>}
      </nav>

      <Routes>
        <Route path="/" element={<Plantilla />} />
        <Route path="/procesar" element={<Procesar />} />
        <Route path="/archivo" element={<Archivo />} />
        <Route path="/revision" element={<Revision />} />
        <Route path="/registro" element={<Registro />} />
        <Route path="/usuarios" element={esAdmin ? <Usuarios /> : <Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <p className="nota">
        Las nóminas son datos personales de categoría sensible. Aquí se guardan cifradas en
        tránsito y alojadas en Neon; el acceso queda limitado a las cuentas dadas de alta y toda
        operación queda anotada en el Registro. Revisa quién tiene cuenta con la misma frecuencia
        con la que revisas la plantilla.
      </p>
    </div>
  )
}

function Pestana({ a, children }) {
  return (
    <NavLink to={a} end={a === '/'}
      className={({ isActive }) => (isActive ? 'activa' : undefined)}>
      {children}
    </NavLink>
  )
}
