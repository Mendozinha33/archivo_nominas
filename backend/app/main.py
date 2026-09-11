# -*- coding: utf-8 -*-
"""Punto de entrada de la API del archivo de nominas."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import ajustes
from .db import Base, motor
from .routers import auth, documentos, revision, trabajadores

log = logging.getLogger("nominas")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@asynccontextmanager
async def ciclo(_: FastAPI):
    # Para un esquema de este tamano create_all basta y evita arrastrar Alembic.
    # Si algun dia cambian las tablas en produccion, hay que migrar a mano.
    Base.metadata.create_all(bind=motor)
    log.info("Esquema comprobado. Origenes permitidos: %s", ajustes().origenes)
    yield


app = FastAPI(
    title="Archivo de nóminas",
    description="Reparte un PDF con las nóminas del equipo en el archivo de cada trabajador.",
    version="1.0.0",
    lifespan=ciclo,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ajustes().origenes,
    allow_credentials=True,          # necesario para la cookie de sesion
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router)
app.include_router(auth.usuarios_router)
app.include_router(trabajadores.router)
app.include_router(documentos.router)
app.include_router(revision.router)


@app.get("/api/salud", tags=["salud"])
def salud() -> dict:
    """Health check de Render. Comprueba tambien que Neon responde."""
    try:
        with motor.connect() as conexion:
            conexion.execute(text("select 1"))
        return {"ok": True, "bd": "conectada"}
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo de conexion con la base de datos")
        return {"ok": False, "bd": "sin conexión", "error": str(exc)[:200]}


@app.get("/", include_in_schema=False)
def raiz() -> dict:
    return {"servicio": "Archivo de nóminas", "documentacion": "/docs"}
