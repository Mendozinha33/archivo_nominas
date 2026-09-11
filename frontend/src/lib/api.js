// Cliente de la API. El token va en la cabecera Authorization porque el front (Vercel)
// y el back (Render) viven en dominios distintos y la cookie de terceros no siempre llega.

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const CLAVE_TOKEN = 'nominas:token'

export function leerToken() {
  try { return sessionStorage.getItem(CLAVE_TOKEN) } catch { return null }
}

export function guardarToken(token) {
  try {
    if (token) sessionStorage.setItem(CLAVE_TOKEN, token)
    else sessionStorage.removeItem(CLAVE_TOKEN)
  } catch { /* modo privado: la sesion dura solo lo que dure la pestana */ }
}

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje)
    this.estado = estado
  }
}

async function fallo(res) {
  let detalle = `Error ${res.status}`
  try {
    const cuerpo = await res.json()
    if (typeof cuerpo.detail === 'string') detalle = cuerpo.detail
    else if (Array.isArray(cuerpo.detail) && cuerpo.detail[0]?.msg) detalle = cuerpo.detail[0].msg
  } catch { /* la respuesta no traia JSON */ }
  return new ErrorApi(detalle, res.status)
}

async function pedir(ruta, { metodo = 'GET', cuerpo, formulario, crudo = false } = {}) {
  const cabeceras = {}
  const token = leerToken()
  if (token) cabeceras.Authorization = `Bearer ${token}`
  if (cuerpo) cabeceras['Content-Type'] = 'application/json'

  let res
  try {
    res = await fetch(`${BASE}${ruta}`, {
      method: metodo,
      headers: cabeceras,
      credentials: 'include',
      body: formulario || (cuerpo ? JSON.stringify(cuerpo) : undefined),
    })
  } catch {
    throw new ErrorApi(
      'No hay conexión con el servidor. Si acaba de despertar, puede tardar unos segundos.', 0)
  }

  if (res.status === 401) {
    guardarToken(null)
    throw await fallo(res)
  }
  if (!res.ok) throw await fallo(res)
  if (crudo) return res
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // --- autenticacion ---
  estado: () => pedir('/api/auth/estado'),
  arranque: (datos) => pedir('/api/auth/arranque', { metodo: 'POST', cuerpo: datos }),
  login: (email, clave) => pedir('/api/auth/login', { metodo: 'POST', cuerpo: { email, clave } }),
  logout: () => pedir('/api/auth/logout', { metodo: 'POST' }),
  yo: () => pedir('/api/auth/yo'),

  // --- usuarios ---
  usuarios: () => pedir('/api/usuarios'),
  crearUsuario: (datos) => pedir('/api/usuarios', { metodo: 'POST', cuerpo: datos }),
  editarUsuario: (id, datos) => pedir(`/api/usuarios/${id}`, { metodo: 'PATCH', cuerpo: datos }),
  borrarUsuario: (id) => pedir(`/api/usuarios/${id}`, { metodo: 'DELETE' }),

  // --- plantilla ---
  trabajadores: (incluirBajas = false) =>
    pedir(`/api/trabajadores?incluir_bajas=${incluirBajas}`),
  crearTrabajador: (datos) => pedir('/api/trabajadores', { metodo: 'POST', cuerpo: datos }),
  editarTrabajador: (id, datos) =>
    pedir(`/api/trabajadores/${id}`, { metodo: 'PATCH', cuerpo: datos }),
  bajaTrabajador: (id, borrarDocumentos = false) =>
    pedir(`/api/trabajadores/${id}?borrar_documentos=${borrarDocumentos}`, { metodo: 'DELETE' }),

  // --- documentos ---
  documentos: (filtros = {}) => {
    const q = new URLSearchParams()
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.set(k, v)
    })
    return pedir(`/api/documentos?${q}`)
  },
  procesar: (fichero, { simular = false, periodo = '', patron = 'mes' } = {}) => {
    const fd = new FormData()
    fd.append('fichero', fichero)
    fd.append('simular', String(simular))
    fd.append('patron', patron)
    if (periodo) fd.append('periodo', periodo)
    return pedir('/api/documentos/procesar', { metodo: 'POST', formulario: fd })
  },
  archivar: (fichero, { trabajadorId, tipo = 'varios', periodo = '', patron = 'mes' }) => {
    const fd = new FormData()
    fd.append('fichero', fichero)
    fd.append('trabajador_id', String(trabajadorId))
    fd.append('tipo', tipo)
    fd.append('patron', patron)
    if (periodo) fd.append('periodo', periodo)
    return pedir('/api/documentos', { metodo: 'POST', formulario: fd })
  },
  editarDocumento: (id, datos) => pedir(`/api/documentos/${id}`, { metodo: 'PATCH', cuerpo: datos }),
  borrarDocumento: (id) => pedir(`/api/documentos/${id}`, { metodo: 'DELETE' }),

  // --- revision y registro ---
  revisar: (periodo) => pedir(`/api/revisar?periodo=${encodeURIComponent(periodo)}`),
  registro: () => pedir('/api/registro'),

  // --- descargas ---
  descargarDocumento: (id, nombre) => descargar(`/api/documentos/${id}/descargar`, nombre),
  descargarZip: (filtros = {}) => {
    const q = new URLSearchParams()
    Object.entries(filtros).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.set(k, v)
    })
    return descargar(`/api/documentos/zip/descargar?${q}`, 'archivo_nominas.zip')
  },
  descargarRegistroCsv: () => descargar('/api/registro/csv', 'registro.csv'),
}

// Las descargas necesitan la cabecera de sesion, asi que no valen enlaces directos:
// se piden con fetch y se sirven al navegador como blob.
async function descargar(ruta, nombrePorDefecto) {
  const res = await pedir(ruta, { crudo: true })
  const blob = await res.blob()
  const cabecera = res.headers.get('Content-Disposition') || ''
  const marca = /filename\*=UTF-8''([^;]+)/.exec(cabecera)
  const nombre = marca ? decodeURIComponent(marca[1]) : nombrePorDefecto

  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 4000)
}
