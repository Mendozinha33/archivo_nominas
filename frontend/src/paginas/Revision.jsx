import { useEffect, useState } from 'react'

import { Aviso, Cifra, Estado, Vacio } from '../componentes/Piezas'
import { api } from '../lib/api'
import { periodoAnterior } from '../lib/util'

/** La comprobación de fin de mes: a quién le falta la nómina del periodo. */
export default function Revision() {
  const [periodo, setPeriodo] = useState(periodoAnterior())
  const [revision, setRevision] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  async function revisar(e) {
    e?.preventDefault()
    setCargando(true)
    setError('')
    try {
      setRevision(await api.revisar(periodo))
    } catch (err) {
      setError(err.message)
      setRevision(null)
    } finally {
      setCargando(false)
    }
  }

  // Al abrir la pestaña se revisa directamente el mes que toca cerrar.
  useEffect(() => { revisar() }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <p className="pistas">
        Antes de dar el mes por cerrado, comprueba que no falta ninguna nómina. Acepta
        <b> Enero 2025</b>, <b>01/2025</b> y formatos parecidos.
      </p>

      <form className="acciones" onSubmit={revisar}>
        <input type="text" value={periodo} onChange={(e) => setPeriodo(e.target.value)}
          style={{ fontFamily: 'var(--mono)', minWidth: 180 }} aria-label="Periodo a revisar" />
        <button className="btn primario" type="submit" disabled={cargando}>Revisar periodo</button>
      </form>

      <Aviso onCerrar={() => setError('')}>{error}</Aviso>
      {cargando && <Estado texto="Revisando…" />}

      {revision && (
        <>
          <div className="rotulo">
            <h2>{revision.periodo_txt}</h2>
            <span className="cuenta">
              {revision.con_nomina.length} de {revision.total} con nómina archivada
            </span>
          </div>

          <div className="resumen">
            <Cifra n={revision.con_nomina.length} etiqueta="archivadas" />
            <Cifra n={revision.sin_nomina.length} etiqueta="faltan" alerta />
          </div>

          {revision.sin_nomina.length === 0 ? (
            <Aviso tipo="ok">No falta ninguna. El periodo está completo.</Aviso>
          ) : (
            <div className="envoltorio-tabla">
              <table className="listado">
                <thead><tr><th>Falta la nómina de</th></tr></thead>
                <tbody>
                  {revision.sin_nomina.map((n) => <tr key={n}><td>{n}</td></tr>)}
                </tbody>
              </table>
            </div>
          )}

          {revision.con_nomina.length === 0 && <Vacio titulo="Todavía no hay nada de este periodo" />}
        </>
      )}
    </>
  )
}
