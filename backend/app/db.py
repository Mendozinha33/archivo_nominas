# -*- coding: utf-8 -*-
"""Conexion a Neon (PostgreSQL) y sesion de SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import ajustes


class Base(DeclarativeBase):
    pass


_url = ajustes().sqlalchemy_url

if _url.startswith("sqlite"):
    # Solo para pruebas en local; en Vercel/Render/Neon siempre se usa PostgreSQL.
    motor = create_engine(_url, connect_args={"check_same_thread": False})
else:
    # Neon cierra las conexiones ociosas: pool_pre_ping evita servir una conexion muerta
    # y pool_recycle las renueva antes de que el proxy las corte.
    motor = create_engine(
        _url,
        pool_pre_ping=True,
        pool_recycle=280,
        pool_size=5,
        max_overflow=5,
        connect_args={} if "localhost" in _url else {"sslmode": "require"},
    )

SesionLocal = sessionmaker(bind=motor, autoflush=False, autocommit=False, expire_on_commit=False)


def obtener_sesion() -> Iterator[Session]:
    sesion = SesionLocal()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
