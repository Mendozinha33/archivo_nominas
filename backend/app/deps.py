# -*- coding: utf-8 -*-
"""Dependencias compartidas: usuario autenticado, control de rol y utilidades."""

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import obtener_sesion
from .models import Registro, Usuario
from .security import COOKIE, leer_token

SesionBD = Annotated[Session, Depends(obtener_sesion)]


def usuario_actual(
    bd: SesionBD,
    authorization: Annotated[str | None, Header()] = None,
    nominas_sesion: Annotated[str | None, Cookie(alias=COOKIE)] = None,
) -> Usuario:
    """Acepta el token por cabecera Authorization: Bearer o por cookie httpOnly.

    La cabecera es la via principal: front y back viven en dominios distintos
    (vercel.app y onrender.com) y muchos navegadores bloquean la cookie de
    terceros. La cookie sigue funcionando si sirves ambos bajo un mismo dominio.
    """
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    elif nominas_sesion:
        token = nominas_sesion

    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No has iniciado sesión.")

    carga = leer_token(token)
    if not carga:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "La sesión ha caducado.")

    usuario = bd.get(Usuario, int(carga["sub"]))
    if not usuario or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no válido.")
    return usuario


Actual = Annotated[Usuario, Depends(usuario_actual)]


def solo_admin(usuario: Actual) -> Usuario:
    if usuario.rol != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Hace falta ser administrador para esta acción.")
    return usuario


Admin = Annotated[Usuario, Depends(solo_admin)]


def anotar(bd: Session, usuario: Usuario | None, accion: str, **campos) -> None:
    """Escribe una linea en el registro de auditoria."""
    bd.add(Registro(
        usuario_email=usuario.email if usuario else "",
        accion=accion,
        origen=campos.get("origen", "")[:255],
        paginas=campos.get("paginas", "")[:60],
        trabajador_nombre=campos.get("trabajador_nombre", "")[:180],
        tipo=campos.get("tipo", "")[:20],
        periodo=campos.get("periodo", "")[:40],
        fichero=campos.get("fichero", "")[:255],
        detalle=campos.get("detalle", ""),
    ))
