// Utilidades de texto compartidas, con el mismo criterio que usa el backend.

export const PARTICULAS = new Set(['DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL', 'Y', 'DA', 'DOS', 'VAN', 'VON'])

export const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

export const TIPOS = {
  contrato: { orden: 0, carpeta: 'Contrato', label: 'Contrato' },
  nomina: { orden: 1, carpeta: 'Nóminas', label: 'Nómina' },
  varios: { orden: 2, carpeta: 'Documentos varios', label: 'Documento' },
}

export const norm = (s) => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .toUpperCase().replace(/\s+/g, ' ').trim()

export const limpiaCarp = (s) => (s || '').replace(/[\\/:*?"<>|]/g, '').trim() || 'Sin nombre'

export const iniciales = (n) => norm(n).split(' ').filter((x) => !PARTICULAS.has(x))
  .slice(0, 2).map((x) => x[0]).join('') || '–'

export function fechaCorta(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function tamanoLegible(bytes) {
  if (!bytes) return '0 KB'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** El periodo por defecto de la caja de revisión: el mes pasado, que es el que se cierra. */
export function periodoAnterior() {
  const hoy = new Date()
  const d = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)
  return `${MESES[d.getMonth()]} ${d.getFullYear()}`
}
