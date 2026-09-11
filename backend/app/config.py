# -*- coding: utf-8 -*-
"""Configuracion leida del entorno. En Render se define en el panel de Environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Ajustes(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Base de datos (Neon) -------------------------------------------------
    # Cadena de Neon. Acepta el formato postgres:// que da el panel y lo normaliza.
    database_url: str = "postgresql+psycopg://usuario:clave@localhost:5432/nominas"

    # --- Seguridad ------------------------------------------------------------
    jwt_secreto: str = "cambia-esto-en-produccion"
    jwt_horas: int = 12
    cookie_segura: bool = True          # False solo para desarrollo en http://localhost
    cookie_samesite: str = "none"       # "none" si front y back estan en dominios distintos

    # Clave de un solo uso para crear el primer administrador. Vaciala tras usarla.
    clave_arranque: str = ""

    # --- CORS -----------------------------------------------------------------
    # Lista separada por comas con los origenes del frontend en Vercel.
    origenes_permitidos: str = "http://localhost:5173"

    # --- Limites --------------------------------------------------------------
    max_mb_subida: int = 25

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def origenes(self) -> list[str]:
        return [o.strip() for o in self.origenes_permitidos.split(",") if o.strip()]


@lru_cache
def ajustes() -> Ajustes:
    return Ajustes()
