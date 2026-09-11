# -*- coding: utf-8 -*-
"""Inicio de sesion, alta del primer administrador y gestion de usuarios."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select

from ..config import ajustes
from ..deps import Actual, Admin, SesionBD, anotar
from ..models import Usuario
from ..schemas import (
    Arranque, Credenciales, Sesion, UsuarioCambio, UsuarioFuera, UsuarioNuevo,
)
from ..security import COOKIE, comprobar, crear_token, hashear, necesita_rehash

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _poner_cookie(respuesta: Response, token: str) -> None:
    cfg = ajustes()
    respuesta.set_cookie(
        COOKIE, token,
        max_age=cfg.jwt_horas * 3600,
        httponly=True,
        secure=cfg.cookie_segura,
        samesite=cfg.cookie_samesite,
        path="/",
    )


@router.get("/estado")
def estado(bd: SesionBD) -> dict:
    """Dice si ya hay algun usuario, para que el front sepa si toca el alta inicial."""
    total = bd.scalar(select(func.count()).select_from(Usuario)) or 0
    return {"instalado": total > 0, "usuarios": total}


@router.post("/arranque", response_model=Sesion, status_code=status.HTTP_201_CREATED)
def arranque(datos: Arranque, respuesta: Response, bd: SesionBD) -> Sesion:
    """Crea el primer administrador. Solo funciona si no hay ningun usuario todavia."""
    cfg = ajustes()
    if not cfg.clave_arranque:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "El alta inicial está desactivada (falta CLAVE_ARRANQUE).")
    if datos.clave_arranque != cfg.clave_arranque:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clave de arranque incorrecta.")
    if bd.scalar(select(func.count()).select_from(Usuario)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe al menos un usuario.")

    usuario = Usuario(email=str(datos.email).lower(), nombre=datos.nombre.strip(),
                      clave_hash=hashear(datos.clave), rol="admin", activo=True,
                      ultimo_acceso=datetime.now(timezone.utc))
    bd.add(usuario)
    bd.flush()
    anotar(bd, usuario, "arranque", detalle="Alta del primer administrador")

    token = crear_token(usuario.id, usuario.email, usuario.rol)
    _poner_cookie(respuesta, token)
    return Sesion(token=token, usuario=UsuarioFuera.model_validate(usuario))


@router.post("/login", response_model=Sesion)
def login(datos: Credenciales, respuesta: Response, bd: SesionBD) -> Sesion:
    usuario = bd.scalar(select(Usuario).where(Usuario.email == str(datos.email).lower()))
    # Mismo mensaje para usuario inexistente y clave mala: no filtramos quien existe.
    if not usuario or not usuario.activo or not comprobar(datos.clave, usuario.clave_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos.")

    if necesita_rehash(usuario.clave_hash):
        usuario.clave_hash = hashear(datos.clave)
    usuario.ultimo_acceso = datetime.now(timezone.utc)

    token = crear_token(usuario.id, usuario.email, usuario.rol)
    _poner_cookie(respuesta, token)
    return Sesion(token=token, usuario=UsuarioFuera.model_validate(usuario))


@router.post("/logout")
def logout(respuesta: Response) -> dict:
    respuesta.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/yo", response_model=UsuarioFuera)
def yo(usuario: Actual) -> Usuario:
    return usuario


# --------------------------------------------------------------------------
# Usuarios (solo administradores)
# --------------------------------------------------------------------------

usuarios_router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@usuarios_router.get("", response_model=list[UsuarioFuera])
def listar(bd: SesionBD, _: Admin) -> list[Usuario]:
    return list(bd.scalars(select(Usuario).order_by(Usuario.nombre)))


@usuarios_router.post("", response_model=UsuarioFuera, status_code=status.HTTP_201_CREATED)
def crear(datos: UsuarioNuevo, bd: SesionBD, admin: Admin) -> Usuario:
    email = str(datos.email).lower()
    if bd.scalar(select(Usuario).where(Usuario.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya hay un usuario con ese email.")
    usuario = Usuario(email=email, nombre=datos.nombre.strip(),
                      clave_hash=hashear(datos.clave), rol=datos.rol, activo=True)
    bd.add(usuario)
    bd.flush()
    anotar(bd, admin, "usuario_alta", detalle=f"{email} como {datos.rol}")
    return usuario


@usuarios_router.patch("/{usuario_id}", response_model=UsuarioFuera)
def editar(usuario_id: int, datos: UsuarioCambio, bd: SesionBD, admin: Admin) -> Usuario:
    usuario = bd.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")

    # Un administrador no puede dejarse a si mismo sin acceso ni quedarse el sistema sin admin.
    quitando_admin = (datos.rol and datos.rol != "admin") or datos.activo is False
    if usuario.rol == "admin" and quitando_admin:
        otros = bd.scalar(select(func.count()).select_from(Usuario).where(
            Usuario.rol == "admin", Usuario.activo.is_(True), Usuario.id != usuario.id)) or 0
        if otros == 0:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "Debe quedar al menos un administrador activo.")

    if datos.nombre is not None:
        usuario.nombre = datos.nombre.strip()
    if datos.rol is not None:
        usuario.rol = datos.rol
    if datos.activo is not None:
        usuario.activo = datos.activo
    if datos.clave:
        usuario.clave_hash = hashear(datos.clave)

    anotar(bd, admin, "usuario_edita", detalle=usuario.email)
    return usuario


@usuarios_router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(usuario_id: int, bd: SesionBD, admin: Admin) -> None:
    usuario = bd.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    if usuario.id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "No puedes borrar tu propia cuenta.")
    if usuario.rol == "admin":
        otros = bd.scalar(select(func.count()).select_from(Usuario).where(
            Usuario.rol == "admin", Usuario.activo.is_(True), Usuario.id != usuario.id)) or 0
        if otros == 0:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "Debe quedar al menos un administrador activo.")
    anotar(bd, admin, "usuario_baja", detalle=usuario.email)
    bd.delete(usuario)
