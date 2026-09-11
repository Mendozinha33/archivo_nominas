import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Aviso, Estado, Modal, Vacio } from '../componentes/Piezas'
import { api } from '../lib/api'
import { useSesion } from '../lib/sesion'
import { iniciales } from '../lib/util'

export default function Plantilla() {
  const { esAdmin } = useSesion()
  const navegar = useNavigate()
  const [trabajadores, setTrabajadores] = useState([])
  const [incluirBajas, setIncluirBajas] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [editando, setEditando] = useState(null)   // null = cerrado, {} = nuevo

  const cargar = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      setTrabajadores(await api.trabajadores(incluirBajas))
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [incluirBajas])

  useEffect(() => { cargar() }, [cargar])

  async function darBaja(t) {
    const total = t.nominas + t.contratos + t.varios
    const aviso = total
      ? `${t.nombre} sale de la plantilla. Sus ${total} documento(s) se conservan en el archivo.`
      : `${t.nombre} sale de la plantilla.`
    if (!window.confirm(aviso)) return
    try {
      await api.bajaTrabajador(t.id, false)
      await cargar()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <>
      <div className="acciones">
        <button className="btn primario" onClick={() => setEditando({})}>Crear trabajador</button>
        <button className="btn fantasma" onClick={() => api.descargarZip().catch((e) => setError(e.message))}>
          Descargar archivo (ZIP)
        </button>
        <label className="ajuste" style={{ marginLeft: 'auto' }}>
          <input type="checkbox" checked={incluirBajas}
            onChange={(e) => setIncluirBajas(e.target.checked)} />
          Ver también las bajas
        </label>
      </div>

      <p className="pistas">
        El <b>DNI</b> hace la identificación exacta. Sin DNI se busca por nombre y apellidos, así que
        escríbelos <b>igual que aparecen en la nómina</b>. Lo que no encaje con nadie irá a
        <i> Sin identificar</i> en vez de asignarse a quien no es.
      </p>

      <Aviso onCerrar={() => setError('')}>{error}</Aviso>
      {cargando && <Estado texto="Cargando la plantilla…" />}

      <div className="rotulo">
        <h2>Plantilla</h2>
        <span className="cuenta">{trabajadores.length}</span>
      </div>

      {!cargando && trabajadores.length === 0 ? (
        <Vacio titulo="Todavía no hay nadie dado de alta">
          Crea a los trabajadores antes de subir el primer PDF de nóminas.
        </Vacio>
      ) : (
        trabajadores.map((t) => (
          <div key={t.id} className={`ficha${t.activo ? '' : ' baja'}`}
            onClick={() => navegar(`/archivo?trabajador=${t.id}`)}
            onKeyDown={(e) => { if (e.key === 'Enter') navegar(`/archivo?trabajador=${t.id}`) }}
            role="button" tabIndex={0}>
            <span className="iniciales">{iniciales(t.nombre)}</span>
            <span className="datos">
              <span className="nom">{t.nombre}{!t.activo && ' · baja'}</span>
              <span className="meta">
                {[t.dni || 'sin DNI', t.puesto || 'sin puesto'].join(' · ')}
                {' · '}{t.nominas} nómina(s) · {t.contratos ? 'contrato OK' : 'sin contrato'}
              </span>
            </span>
            <span className="iconos" onClick={(e) => e.stopPropagation()}>
              <button className="iconobtn" title="Editar" aria-label={`Editar ${t.nombre}`}
                onClick={() => setEditando(t)}>✎</button>
              {esAdmin && t.activo && (
                <button className="iconobtn borrar" title="Dar de baja"
                  aria-label={`Dar de baja a ${t.nombre}`} onClick={() => darBaja(t)}>✕</button>
              )}
            </span>
          </div>
        ))
      )}

      <Modal abierto={editando !== null} onCerrar={() => setEditando(null)}>
        <FormularioTrabajador
          trabajador={editando}
          onCancelar={() => setEditando(null)}
          onGuardado={async () => { setEditando(null); await cargar() }}
        />
      </Modal>
    </>
  )
}

function FormularioTrabajador({ trabajador, onCancelar, onGuardado }) {
  const esNuevo = !trabajador?.id
  const [nombre, setNombre] = useState(trabajador?.nombre || '')
  const [dni, setDni] = useState(trabajador?.dni || '')
  const [puesto, setPuesto] = useState(trabajador?.puesto || '')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setEnviando(true)
    try {
      const datos = { nombre, dni, puesto }
      if (esNuevo) await api.crearTrabajador(datos)
      else await api.editarTrabajador(trabajador.id, datos)
      await onGuardado()
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="modal-cuerpo" onSubmit={enviar}>
      <h3>{esNuevo ? 'Nuevo trabajador' : 'Editar trabajador'}</h3>
      <p className="ayuda">
        Estos datos sirven para reconocer sus hojas dentro del PDF y para nombrar su carpeta.
      </p>
      <div className="campo">
        <label htmlFor="fNombre">Nombre y apellidos</label>
        <input id="fNombre" type="text" required value={nombre} placeholder="Álvaro Ruiz Ferrán"
          onChange={(e) => setNombre(e.target.value)} />
        <small>Escríbelo igual que aparece en la nómina.</small>
      </div>
      <div className="campo">
        <label htmlFor="fDni">DNI / NIE</label>
        <input id="fDni" type="text" value={dni} placeholder="12345678Z"
          onChange={(e) => setDni(e.target.value)} />
        <small>Con el DNI la identificación es exacta.</small>
      </div>
      <div className="campo">
        <label htmlFor="fPuesto">Puesto</label>
        <input id="fPuesto" type="text" value={puesto} placeholder="Delantero · Primer equipo"
          onChange={(e) => setPuesto(e.target.value)} />
      </div>
      <p className="error">{error}</p>
      <div className="modal-pie">
        <button className="btn fantasma" type="button" onClick={onCancelar}>Cancelar</button>
        <button className="btn primario" type="submit" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Guardar trabajador'}
        </button>
      </div>
    </form>
  )
}
