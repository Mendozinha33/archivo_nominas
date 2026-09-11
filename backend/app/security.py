# -*- coding: utf-8 -*-
"""Hash de contrasenas (Argon2) y emision/validacion de JWT."""

from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from .config import ajustes

_hasher = PasswordHasher()
ALGORITMO = "HS256"
COOKIE = "nominas_sesion"


def hashear(clave: str) -> str:
    return _hasher.hash(clave)


def comprobar(clave: str, clave_hash: str) -> bool:
    try:
        _hasher.verify(clave_hash, clave)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def necesita_rehash(clave_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(clave_hash)
    except InvalidHashError:
        return False


def crear_token(usuario_id: int, email: str, rol: str) -> str:
    cfg = ajustes()
    ahora = datetime.now(timezone.utc)
    carga = {
        "sub": str(usuario_id),
        "email": email,
        "rol": rol,
        "iat": ahora,
        "exp": ahora + timedelta(hours=cfg.jwt_horas),
    }
    return jwt.encode(carga, cfg.jwt_secreto, algorithm=ALGORITMO)


def leer_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, ajustes().jwt_secreto, algorithms=[ALGORITMO])
    except jwt.PyJWTError:
        return None
