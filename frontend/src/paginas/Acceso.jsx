import { useState } from 'react'

import { Aviso } from '../componentes/Piezas'
import { useSesion } from '../lib/sesion'

/** Pantalla de entrada. Si no hay ningún usuario todavía, pide crear el primer administrador. */
export default function Acceso() {
  const { instalado, entrar, arrancar, sinConexion } = useSesion()
  const [email, setEmail] = useState('')
  const [clave, setClave] = useState('')
  const [nombre, setNombre] = useState('')
  const [claveArranque, setClaveArranque] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      if (instalado) await entrar(email, clave)
      else await arrancar({ email, nombre, clave, clave_arranque: claveArranque })
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="lienzo">
      <div className="acceso">
        <form className="modal-cuerpo" onSubmit={enviar}>
          <p className="eyebrow">Gestión de nóminas y contratos</p>
          <h1>Archivo de <em>nóminas</em></h1>
          <p className="ayuda">
            {instalado
              ? 'Entra con tu cuenta para consultar y archivar documentos.'
              : 'Primer arranque: crea la cuenta de administrador del club.'}
          </p>

          {sinConexion && (
            <Aviso>
              No hay conexión con el servidor. En el plan gratuito de Render el servicio se
              duerme: vuelve a intentarlo en unos 30 segundos.
            </Aviso>
          )}

          {!instalado && (
            <div className="campo">
              <label htmlFor="nombre">Nombre y apellidos</label>
              <input id="nombre" type="text" required minLength={2} value={nombre}
                autoComplete="name" onChange={(e) => setNombre(e.target.value)} />
            </div>
          )}

          <div className="campo">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required value={email} autoComplete="username"
              onChange={(e) => setEmail(e.target.value)} />
          </div>

          <div className="campo">
            <label htmlFor="clave">Contraseña</label>
            <input id="clave" type="password" required value={clave}
              minLength={instalado ? 1 : 10}
              autoComplete={instalado ? 'current-password' : 'new-password'}
              onChange={(e) => setClave(e.target.value)} />
            {!instalado && <small>Mínimo 10 caracteres. Guárdala en un gestor de contraseñas.</small>}
          </div>

          {!instalado && (
            <div className="campo">
              <label htmlFor="arranque">Clave de arranque</label>
              <input id="arranque" type="password" required value={claveArranque}
                onChange={(e) => setClaveArranque(e.target.value)} />
              <small>La que pusiste en CLAVE_ARRANQUE en Render. Bórrala de allí después.</small>
            </div>
          )}

          <p className="error">{error}</p>

          <div className="modal-pie">
            <button className="btn primario" type="submit" disabled={enviando}>
              {enviando ? 'Un momento…' : instalado ? 'Entrar' : 'Crear administrador'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
