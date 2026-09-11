import { createContext, useCallback, useContext, useEffect, useState } from 'react'

import { api, guardarToken, leerToken } from './api'

const Contexto = createContext(null)

export function ProveedorSesion({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [instalado, setInstalado] = useState(true)
  const [cargando, setCargando] = useState(true)
  const [sinConexion, setSinConexion] = useState(false)

  const refrescar = useCallback(async () => {
    setCargando(true)
    try {
      const est = await api.estado()
      setInstalado(est.instalado)
      setSinConexion(false)
      if (est.instalado && leerToken()) {
        try {
          setUsuario(await api.yo())
        } catch {
          // El token ha caducado o ya no vale: se descarta y se pide login otra vez.
          guardarToken(null)
          setUsuario(null)
        }
      } else {
        setUsuario(null)
      }
    } catch (e) {
      setSinConexion(e.estado === 0)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { refrescar() }, [refrescar])

  const entrar = useCallback(async (email, clave) => {
    const sesion = await api.login(email, clave)
    guardarToken(sesion.token)
    setUsuario(sesion.usuario)
    setInstalado(true)
    return sesion.usuario
  }, [])

  const arrancar = useCallback(async (datos) => {
    const sesion = await api.arranque(datos)
    guardarToken(sesion.token)
    setUsuario(sesion.usuario)
    setInstalado(true)
    return sesion.usuario
  }, [])

  const salir = useCallback(async () => {
    try { await api.logout() } catch { /* da igual si el servidor no responde */ }
    guardarToken(null)
    setUsuario(null)
  }, [])

  const valor = {
    usuario, instalado, cargando, sinConexion,
    esAdmin: usuario?.rol === 'admin',
    entrar, arrancar, salir, refrescar,
  }
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>
}

export function useSesion() {
  const valor = useContext(Contexto)
  if (!valor) throw new Error('useSesion se usa dentro de ProveedorSesion')
  return valor
}
