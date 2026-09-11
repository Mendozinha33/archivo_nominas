import { useEffect, useState } from 'react'

import { Aviso, Estado, Vacio } from '../componentes/Piezas'
import { api } from '../lib/api'
import { fechaCorta } from '../lib/util'

/** Traza de auditoría: quién archivó qué y cuándo. El equivalente al registro.csv. */
export default function Registro() {
  const [filas, setFilas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.registro()
      .then(setFilas)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false))
  }, [])

  return (
    <>
      <p className="pistas">
        Toda operación sobre el archivo queda registrada. Sirve como traza de qué se archivó,
        quién lo hizo y cuándo, que es lo que exige la política de protección de datos.
      </p>

      <div className="acciones">
        <button className="btn fantasma"
          onClick={() => api.descargarRegistroCsv().catch((e) => setError(e.message))}>
          Descargar CSV
        </button>
      </div>

      <Aviso onCerrar={() => setError('')}>{error}</Aviso>
      {cargando && <Estado texto="Cargando el registro…" />}

      <div className="rotulo">
        <h2>Registro</h2>
        <span className="cuenta">{filas.length} últimas operaciones</span>
      </div>

      {!cargando && filas.length === 0 ? (
        <Vacio titulo="Sin operaciones todavía" />
      ) : (
        <div className="envoltorio-tabla">
          <table className="listado">
            <thead>
              <tr>
                <th>Fecha</th><th>Usuario</th><th>Acción</th><th>Trabajador</th>
                <th>Periodo</th><th>Fichero</th><th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{fechaCorta(r.fecha)}</td>
                  <td className="mono">{r.usuario_email}</td>
                  <td>{r.accion}</td>
                  <td>{r.trabajador_nombre}</td>
                  <td className="mono">{r.periodo}</td>
                  <td className="mono">{r.fichero}</td>
                  <td>{r.detalle}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
