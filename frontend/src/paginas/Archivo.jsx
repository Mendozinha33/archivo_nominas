import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Aviso, Estado, Vacio } from '../componentes/Piezas'
import { api } from '../lib/api'
import { useSesion } from '../lib/sesion'
import { TIPOS, fechaCorta, iniciales, limpiaCarp, tamanoLegible } from '../lib/util'

export default function Archivo() {
  const { esAdmin } = useSesion()
  const [params, setParams] = useSearchParams()
  const trabajadorId = params.get('trabajador')
  const soloSinAsignar = params.get('sin_asignar') === '1'

  const [trabajadores, setTrabajadores] = useState([])
  const [documentos, setDocumentos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [orden, setOrden] = useState('periodo-desc')

  const cargar = useCallback(async () => {
    setCargando(true)
    setError('')
    try {
      const [ts, ds] = await Promise.all([
        api.trabajadores(true),
        api.documentos(soloSinAsignar
          ? { sin_asignar: true }
          : trabajadorId ? { trabajador_id: trabajadorId } : {}),
      ])
      setTrabajadores(ts)
      setDocumentos(ds)
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }, [trabajadorId, soloSinAsignar])

  useEffect(() => { cargar() }, [cargar])

  const ordenar = useCallback((lista) => {
    const clave = (d) => (d.periodo_anio || 0) * 100 + (d.periodo_mes || 0)
    const c = [...lista]
    if (orden === 'nombre') return c.sort((a, b) => a.nombre_fichero.localeCompare(b.nombre_fichero, 'es'))
    if (orden === 'subida') return c.sort((a, b) => a.subido.localeCompare(b.subido))
    const dir = orden === 'periodo-asc' ? 1 : -1
    return c.sort((a, b) => (clave(a) - clave(b)) * dir || a.subido.localeCompare(b.subido))
  }, [orden])

  // Agrupa por trabajador, dejando _Sin identificar siempre al final.
  const grupos = useMemo(() => {
    const porTrabajador = new Map()
    documentos.forEach((d) => {
      const k = d.trabajador_id ?? '__sin__'
      if (!porTrabajador.has(k)) porTrabajador.set(k, [])
      porTrabajador.get(k).push(d)
    })
    const claves = [...porTrabajador.keys()].sort((a, b) => {
      if (a === '__sin__') return 1
      if (b === '__sin__') return -1
      const na = trabajadores.find((t) => t.id === a)?.nombre || ''
      const nb = trabajadores.find((t) => t.id === b)?.nombre || ''
      return na.localeCompare(nb, 'es')
    })
    return claves.map((k) => ({
      clave: k,
      trabajador: k === '__sin__' ? null : trabajadores.find((t) => t.id === k),
      docs: porTrabajador.get(k),
    }))
  }, [documentos, trabajadores])

  const enfocado = trabajadorId ? trabajadores.find((t) => t.id === Number(trabajadorId)) : null

  async function cambiar(doc, datos) {
    try {
      const actualizado = await api.editarDocumento(doc.id, datos)
      setDocumentos((ds) => ds.map((d) => (d.id === doc.id ? actualizado : d)))
    } catch (e) {
      setError(e.message)
      await cargar()
    }
  }

  async function borrar(doc) {
    if (!window.confirm(`Borrar ${doc.nombre_fichero} del archivo. Esto no se puede deshacer.`)) return
    try {
      await api.borrarDocumento(doc.id)
      setDocumentos((ds) => ds.filter((d) => d.id !== doc.id))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <>
      <div className="acciones">
        {(trabajadorId || soloSinAsignar) && (
          <button className="btn fantasma" onClick={() => setParams({})}>← Todo el archivo</button>
        )}
        <button className="btn fantasma" onClick={() => setParams({ sin_asignar: '1' })}>
          Ver sin identificar
        </button>
        <button className="btn"
          onClick={() => api.descargarZip(trabajadorId ? { trabajador_id: trabajadorId } : {})
            .catch((e) => setError(e.message))}>
          Descargar ZIP
        </button>
        <label className="ajuste" style={{ marginLeft: 'auto' }}>
          Ordenar por
          <select value={orden} onChange={(e) => setOrden(e.target.value)}>
            <option value="periodo-desc">Periodo · más reciente antes</option>
            <option value="periodo-asc">Periodo · más antiguo antes</option>
            <option value="nombre">Nombre del fichero (A–Z)</option>
            <option value="subida">Orden de subida</option>
          </select>
        </label>
      </div>

      <Aviso onCerrar={() => setError('')}>{error}</Aviso>
      {cargando && <Estado texto="Cargando el archivo…" />}

      {enfocado && (
        <Expediente trabajador={enfocado} onSubido={cargar} onError={setError} />
      )}

      <div className="rotulo">
        <h2>{soloSinAsignar ? 'Sin identificar' : enfocado ? 'Su archivo' : 'Archivo'}</h2>
        <span className="cuenta">{documentos.length} documento(s)</span>
      </div>

      {!cargando && documentos.length === 0 ? (
        <Vacio titulo="Aquí no hay nada todavía">
          {soloSinAsignar
            ? 'Ninguna hoja ha quedado sin asignar. Buena señal.'
            : 'Sube un PDF de nóminas desde la pestaña Procesar.'}
        </Vacio>
      ) : (
        grupos.map((g) => (
          <Carpeta key={g.clave} grupo={g} trabajadores={trabajadores} ordenar={ordenar}
            esAdmin={esAdmin} onCambiar={cambiar} onBorrar={borrar} onError={setError} />
        ))
      )}
    </>
  )
}

function Carpeta({ grupo, trabajadores, ordenar, esAdmin, onCambiar, onBorrar, onError }) {
  const sin = !grupo.trabajador
  const nombre = sin ? '_Sin identificar' : limpiaCarp(grupo.trabajador.nombre)
  const porTipo = Object.keys(TIPOS).map((tipo) => ({
    tipo, docs: ordenar(grupo.docs.filter((d) => d.tipo === tipo)),
  }))

  return (
    <div className={`carpeta${sin ? ' sin' : ''}`}>
      <div className="cab">
        <span className="icono" />
        <span className="ruta">{nombre}/</span>
        <span className="n">{grupo.docs.length} documento(s)</span>
      </div>
      {sin ? (
        <div className="sub nomina">
          <div className="cuerpo">
            {ordenar(grupo.docs).map((d) => (
              <Documento key={d.id} doc={d} trabajadores={trabajadores} esAdmin={esAdmin}
                onCambiar={onCambiar} onBorrar={onBorrar} onError={onError} />
            ))}
          </div>
        </div>
      ) : (
        porTipo.filter((s) => s.docs.length).map(({ tipo, docs }) => (
          <div key={tipo} className={`sub ${tipo}`}>
            <div className="subcab">
              <span className="pestana" />
              <span className="subruta">{TIPOS[tipo].carpeta}/</span>
              <span className="subn">{docs.length}</span>
            </div>
            <div className="cuerpo">
              {docs.map((d) => (
                <Documento key={d.id} doc={d} trabajadores={trabajadores} esAdmin={esAdmin}
                  onCambiar={onCambiar} onBorrar={onBorrar} onError={onError} />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

function Documento({ doc, trabajadores, esAdmin, onCambiar, onBorrar, onError }) {
  const [nombre, setNombre] = useState(doc.nombre_fichero)
  const [periodo, setPeriodo] = useState(doc.periodo_txt)

  useEffect(() => { setNombre(doc.nombre_fichero) }, [doc.nombre_fichero])
  useEffect(() => { setPeriodo(doc.periodo_txt) }, [doc.periodo_txt])

  return (
    <div className="doc">
      <div className="fila">
        <input className="nombre" value={nombre} onChange={(e) => setNombre(e.target.value)}
          onBlur={() => nombre !== doc.nombre_fichero && nombre.trim()
            && onCambiar(doc, { nombre_fichero: nombre.trim() })}
          aria-label="Nombre del fichero" />
        <span className="sello">{tamanoLegible(doc.tamano)}</span>
        {doc.paginas && <span className="sello">pág. {doc.paginas}</span>}
        {!doc.periodo_txt && doc.tipo === 'nomina' && <span className="sello aviso">sin periodo</span>}
      </div>
      <div className="fila">
        <select value={doc.trabajador_id ?? ''}
          onChange={(e) => onCambiar(doc, e.target.value
            ? { trabajador_id: Number(e.target.value) }
            : { quitar_trabajador: true })}
          aria-label="Trabajador">
          <option value="">— Sin identificar —</option>
          {trabajadores.map((t) => (
            <option key={t.id} value={t.id}>{t.nombre}</option>
          ))}
        </select>
        <select value={doc.tipo} onChange={(e) => onCambiar(doc, { tipo: e.target.value })}
          aria-label="Tipo de documento">
          {Object.entries(TIPOS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <input className="periodo" value={periodo} placeholder="Enero 2025"
          onChange={(e) => setPeriodo(e.target.value)}
          onBlur={() => periodo !== doc.periodo_txt && onCambiar(doc, { periodo })}
          aria-label="Periodo" />
        <button className="btn mini fantasma"
          onClick={() => api.descargarDocumento(doc.id, doc.nombre_fichero)
            .catch((e) => onError(e.message))}>
          Descargar
        </button>
        {esAdmin && (
          <button className="btn mini peligro" onClick={() => onBorrar(doc)}>Borrar</button>
        )}
        <span className="sello">{fechaCorta(doc.subido)}</span>
      </div>
    </div>
  )
}

/** Cabecera del trabajador enfocado, con la subida de contratos y documentos sueltos. */
function Expediente({ trabajador, onSubido, onError }) {
  const entrada = useRef(null)
  const [tipo, setTipo] = useState('contrato')
  const [subiendo, setSubiendo] = useState(false)

  async function subir(ficheros) {
    if (!ficheros?.length) return
    setSubiendo(true)
    try {
      for (const f of ficheros) {
        await api.archivar(f, { trabajadorId: trabajador.id, tipo })
      }
      await onSubido()
    } catch (e) {
      onError(e.message)
    } finally {
      setSubiendo(false)
      if (entrada.current) entrada.current.value = ''
    }
  }

  return (
    <div className="expediente">
      <span className="iniciales">{iniciales(trabajador.nombre)}</span>
      <span className="quien">
        <h3>{trabajador.nombre}</h3>
        <span className="dato">
          {[trabajador.dni || 'sin DNI', trabajador.puesto || 'sin puesto'].join(' · ')}
          {!trabajador.activo && ' · DE BAJA'}
        </span>
      </span>
      <span className="mandos">
        <select value={tipo} onChange={(e) => setTipo(e.target.value)} aria-label="Tipo a archivar">
          {Object.entries(TIPOS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <button className="btn mini" disabled={subiendo} onClick={() => entrada.current?.click()}>
          {subiendo ? 'Subiendo…' : 'Archivar fichero'}
        </button>
        <input ref={entrada} type="file" multiple hidden
          onChange={(e) => subir([...(e.target.files || [])])} />
      </span>
    </div>
  )
}
