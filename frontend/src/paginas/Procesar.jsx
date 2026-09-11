import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { Aviso, Cifra, Estado, Vacio } from '../componentes/Piezas'
import { api } from '../lib/api'

const SITUACIONES = {
  nuevo: { clase: 'ok', texto: 'nuevo' },
  duplicado: { clase: '', texto: 'ya archivada' },
  sin_identificar: { clase: 'aviso', texto: 'sin identificar' },
}

export default function Procesar() {
  const entrada = useRef(null)
  const [fichero, setFichero] = useState(null)
  const [encima, setEncima] = useState(false)
  const [patron, setPatron] = useState('mes')
  const [periodo, setPeriodo] = useState('')
  const [trabajando, setTrabajando] = useState('')
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState('')
  const [hayPlantilla, setHayPlantilla] = useState(true)

  useEffect(() => {
    api.trabajadores().then((t) => setHayPlantilla(t.length > 0)).catch(() => {})
  }, [])

  function elegir(f) {
    if (!f) return
    if (f.type !== 'application/pdf' && !f.name.toLowerCase().endsWith('.pdf')) {
      setError('Solo se puede procesar un PDF.')
      return
    }
    setError('')
    setResultado(null)
    setFichero(f)
  }

  async function lanzar(simular) {
    if (!fichero) return
    setError('')
    setTrabajando(simular ? 'Simulando el reparto…' : 'Archivando las nóminas…')
    try {
      setResultado(await api.procesar(fichero, { simular, periodo, patron }))
    } catch (e) {
      setError(e.message)
      setResultado(null)
    } finally {
      setTrabajando('')
    }
  }

  return (
    <>
      <p className="pistas">
        Sube el PDF con todas las nóminas del mes: cada hoja se separa, se nombra
        <b> trabajador_mes.pdf</b> y se guarda en la carpeta de su trabajador. Haz siempre
        primero la <b>simulación</b>: enseña dónde iría cada hoja sin escribir nada.
      </p>

      {!hayPlantilla && (
        <Aviso>
          La plantilla está vacía. <Link to="/">Da de alta a los trabajadores</Link> antes
          de procesar un PDF.
        </Aviso>
      )}

      <Aviso onCerrar={() => setError('')}>{error}</Aviso>

      <div
        className={`zona-soltar${encima ? ' encima' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setEncima(true) }}
        onDragLeave={() => setEncima(false)}
        onDrop={(e) => { e.preventDefault(); setEncima(false); elegir(e.dataTransfer.files?.[0]) }}
        onClick={() => entrada.current?.click()}
        role="button" tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') entrada.current?.click() }}
      >
        <strong>{fichero ? fichero.name : 'Arrastra aquí el PDF de nóminas'}</strong>
        {fichero
          ? `${(fichero.size / 1024 / 1024).toFixed(2)} MB · pulsa para cambiarlo`
          : 'o pulsa para elegirlo'}
        <input ref={entrada} type="file" accept="application/pdf" hidden
          onChange={(e) => elegir(e.target.files?.[0])} />
      </div>

      <div className="ajustes">
        <label className="ajuste">
          Nombre del fichero
          <select value={patron} onChange={(e) => setPatron(e.target.value)}>
            <option value="mes">Trabajador_Enero_2025</option>
            <option value="num">Trabajador_2025-01</option>
          </select>
        </label>
        <label className="ajuste">
          Forzar periodo
          <input type="text" placeholder="Enero 2025 (opcional)" value={periodo}
            style={{ fontFamily: 'var(--mono)', fontSize: 12 }}
            onChange={(e) => setPeriodo(e.target.value)} />
        </label>
      </div>

      <div className="acciones">
        <button className="btn" disabled={!fichero || !!trabajando} onClick={() => lanzar(true)}>
          Simular reparto
        </button>
        <button className="btn primario" disabled={!fichero || !!trabajando}
          onClick={() => lanzar(false)}>
          Archivar de verdad
        </button>
      </div>

      <Estado texto={trabajando} />

      {resultado && <Resultado resultado={resultado} />}
    </>
  )
}

function Resultado({ resultado }) {
  return (
    <>
      <div className="rotulo">
        <h2>{resultado.simulado ? 'Simulación' : 'Resultado'}</h2>
        <span className="cuenta">{resultado.origen} · {resultado.paginas_totales} páginas</span>
      </div>

      {resultado.simulado && (
        <Aviso tipo="ok">No se ha escrito nada. Esto es solo lo que haría.</Aviso>
      )}

      <div className="resumen">
        <Cifra n={resultado.simulado ? resultado.hojas.length : resultado.nuevos}
          etiqueta={resultado.simulado ? 'hojas' : 'archivadas'} />
        <Cifra n={resultado.duplicados} etiqueta="ya estaban" />
        <Cifra n={resultado.sin_identificar} etiqueta="sin identificar" alerta />
        <Cifra n={resultado.sin_texto} etiqueta="sin texto" alerta />
      </div>

      {resultado.sin_texto > 0 && (
        <Aviso>
          Hay hojas sin capa de texto: parecen un escaneo. Pásales antes un OCR
          (por ejemplo <b>ocrmypdf -l spa entrada.pdf salida.pdf</b>) y vuelve a subirlo.
        </Aviso>
      )}

      {resultado.sin_identificar > 0 && (
        <Aviso>
          {resultado.sin_identificar} hoja(s) no han encajado con nadie.
          {resultado.simulado
            ? ' Revisa que el nombre de la ficha coincida con el de la nómina.'
            : <> Colócalas a mano desde <Link to="/archivo?sin_asignar=1">Sin identificar</Link>.</>}
        </Aviso>
      )}

      {resultado.hojas.length === 0 ? (
        <Vacio titulo="El PDF no tenía páginas que repartir" />
      ) : (
        <div className="envoltorio-tabla">
          <table className="listado">
            <thead>
              <tr>
                <th>Páginas</th><th>Trabajador</th><th>Periodo</th>
                <th>Nombre del fichero</th><th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {resultado.hojas.map((h, i) => {
                const s = SITUACIONES[h.situacion] || SITUACIONES.nuevo
                return (
                  <tr key={`${h.paginas}-${i}`}>
                    <td className="mono">{h.paginas}</td>
                    <td>{h.trabajador_nombre || <i>_Sin identificar</i>}</td>
                    <td className="mono">{h.periodo_txt || '—'}</td>
                    <td className="mono">{h.nombre_fichero}</td>
                    <td>
                      <span className={`sello ${s.clase}`}>{s.texto}</span>
                      {h.sin_texto && <span className="sello aviso"> sin texto</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
