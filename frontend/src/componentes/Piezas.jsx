import { useEffect, useRef } from 'react'

/** Franja oscura de progreso, igual que la del HTML original. */
export function Estado({ texto, porcentaje }) {
  if (!texto) return null
  const indefinido = porcentaje === undefined || porcentaje === null
  return (
    <div className="estado" role="status" aria-live="polite">
      <span className="txt">{texto}</span>
      <span className={`barra${indefinido ? ' indef' : ''}`}>
        <i style={indefinido ? undefined : { width: `${porcentaje}%` }} />
      </span>
    </div>
  )
}

/** Aviso en rojo (error) o verde (confirmación). */
export function Aviso({ children, tipo = 'error', onCerrar }) {
  if (!children) return null
  return (
    <p className={`aviso${tipo === 'ok' ? ' ok' : ''}`} role={tipo === 'ok' ? 'status' : 'alert'}>
      {children}
      {onCerrar && (
        <button type="button" className="iconobtn" style={{ float: 'right' }}
          onClick={onCerrar} aria-label="Cerrar aviso">✕</button>
      )}
    </p>
  )
}

export function Vacio({ titulo, children, chico = false }) {
  return (
    <div className={`vacio${chico ? ' chico' : ''}`}>
      {titulo && <strong>{titulo}</strong>}
      {children}
    </div>
  )
}

export function Cifra({ n, etiqueta, alerta = false }) {
  return (
    <div className={`cifra${alerta && n > 0 ? ' alerta' : ''}`}>
      <b>{n}</b>
      <span>{etiqueta}</span>
    </div>
  )
}

/** Diálogo nativo: se abre y cierra según `abierto`, y avisa al cerrarse con Esc. */
export function Modal({ abierto, onCerrar, children }) {
  const ref = useRef(null)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (abierto && !d.open) d.showModal()
    if (!abierto && d.open) d.close()
  }, [abierto])

  useEffect(() => {
    const d = ref.current
    if (!d) return undefined
    const alCerrar = () => onCerrar?.()
    d.addEventListener('close', alCerrar)
    return () => d.removeEventListener('close', alCerrar)
  }, [onCerrar])

  return <dialog ref={ref}>{abierto && children}</dialog>
}
