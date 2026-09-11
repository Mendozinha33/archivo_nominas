import { useCallback, useEffect, useState } from 'react'

import { Aviso, Estado, Modal } from '../componentes/Piezas'
import { api } from '../lib/api'
import { useSesion } from '../lib/sesion'
import { fechaCorta } from '../lib/util'

/** Solo para administradores: quién puede entrar y con qué permisos. */
export default function Usuarios() {
  const { usuario: yo } = useSesion()
  const [usuarios, setUsuarios] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [creando, setCreando] = useState(false)

  const cargar = useCallback(async () => {
    setCargando(true)
    try {
      setUsuarios(await api.usuarios())
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function cambiar(u, datos) {
    try {
      await api.editarUsuario(u.id, datos)
      await cargar()
    } catch (e) {
      setError(e.message)
    }
  }

  async function borrar(u) {
    if (!window.confirm(`Borrar la cuenta de ${u.email}.`)) return
    try {
      await api.borrarUsuario(u.id)
      await cargar()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <>
      <p className="pistas">
        El <b>administrador</b> gestiona plantilla, usuarios y puede borrar documentos. El
        <b> gestor</b> archiva y consulta, pero no borra nada del archivo.
      </p>

      <div className="acciones">
        <button className="btn primario" onClick={() => setCreando(true)}>Crear usuario</button>
      </div>

      <Aviso onCerrar={() => setError('')}>{error}</Aviso>
      {cargando && <Estado texto="Cargando usuarios…" />}

      <div className="rotulo">
        <h2>Usuarios</h2>
        <span className="cuenta">{usuarios.length}</span>
      </div>

      <div className="envoltorio-tabla">
        <table className="listado">
          <thead>
            <tr>
              <th>Nombre</th><th>Email</th><th>Rol</th><th>Estado</th>
              <th>Último acceso</th><th></th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id}>
                <td>{u.nombre}{u.id === yo?.id && ' · tú'}</td>
                <td className="mono">{u.email}</td>
                <td>
                  <select value={u.rol} disabled={u.id === yo?.id}
                    onChange={(e) => cambiar(u, { rol: e.target.value })} aria-label="Rol">
                    <option value="admin">Administrador</option>
                    <option value="gestor">Gestor</option>
                  </select>
                </td>
                <td>
                  <span className={`sello ${u.activo ? 'ok' : 'aviso'}`}>
                    {u.activo ? 'activo' : 'bloqueado'}
                  </span>
                </td>
                <td className="mono">{fechaCorta(u.ultimo_acceso) || '—'}</td>
                <td>
                  {u.id !== yo?.id && (
                    <>
                      <button className="btn mini fantasma"
                        onClick={() => cambiar(u, { activo: !u.activo })}>
                        {u.activo ? 'Bloquear' : 'Reactivar'}
                      </button>{' '}
                      <button className="btn mini peligro" onClick={() => borrar(u)}>Borrar</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal abierto={creando} onCerrar={() => setCreando(false)}>
        <FormularioUsuario
          onCancelar={() => setCreando(false)}
          onCreado={async () => { setCreando(false); await cargar() }}
        />
      </Modal>
    </>
  )
}

function FormularioUsuario({ onCancelar, onCreado }) {
  const [datos, setDatos] = useState({ nombre: '', email: '', clave: '', rol: 'gestor' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  const cambia = (campo) => (e) => setDatos((d) => ({ ...d, [campo]: e.target.value }))

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await api.crearUsuario(datos)
      await onCreado()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="modal-cuerpo" onSubmit={enviar}>
      <h3>Nuevo usuario</h3>
      <p className="ayuda">Tendrá acceso a datos personales sensibles: da de alta solo a quien lo necesite.</p>
      <div className="campo">
        <label htmlFor="uNombre">Nombre y apellidos</label>
        <input id="uNombre" type="text" required value={datos.nombre} onChange={cambia('nombre')} />
      </div>
      <div className="campo">
        <label htmlFor="uEmail">Email</label>
        <input id="uEmail" type="email" required value={datos.email} onChange={cambia('email')} />
      </div>
      <div className="campo">
        <label htmlFor="uClave">Contraseña</label>
        <input id="uClave" type="password" required minLength={10} value={datos.clave}
          autoComplete="new-password" onChange={cambia('clave')} />
        <small>Mínimo 10 caracteres. Pásasela por un canal seguro.</small>
      </div>
      <div className="campo">
        <label htmlFor="uRol">Rol</label>
        <select id="uRol" value={datos.rol} onChange={cambia('rol')}>
          <option value="gestor">Gestor · archiva y consulta</option>
          <option value="admin">Administrador · además gestiona y borra</option>
        </select>
      </div>
      <p className="error">{error}</p>
      <div className="modal-pie">
        <button className="btn fantasma" type="button" onClick={onCancelar}>Cancelar</button>
        <button className="btn primario" type="submit" disabled={enviando}>
          {enviando ? 'Creando…' : 'Crear usuario'}
        </button>
      </div>
    </form>
  )
}
