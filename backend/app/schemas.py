# -*- coding: utf-8 -*-
"""Contratos de entrada y salida de la API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --------------------------------------------------------------------------
# Autenticacion y usuarios
# --------------------------------------------------------------------------


class Credenciales(BaseModel):
    email: EmailStr
    clave: str = Field(min_length=1)


class UsuarioFuera(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre: str
    rol: str
    activo: bool
    creado: datetime
    ultimo_acceso: datetime | None = None


class Sesion(BaseModel):
    token: str
    usuario: UsuarioFuera


class UsuarioNuevo(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=160)
    clave: str = Field(min_length=10, max_length=200)
    rol: str = Field(default="gestor", pattern="^(admin|gestor)$")


class UsuarioCambio(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=160)
    rol: str | None = Field(default=None, pattern="^(admin|gestor)$")
    activo: bool | None = None
    clave: str | None = Field(default=None, min_length=10, max_length=200)


class Arranque(BaseModel):
    """Alta del primer administrador, protegida por CLAVE_ARRANQUE."""

    email: EmailStr
    nombre: str = Field(min_length=2, max_length=160)
    clave: str = Field(min_length=10, max_length=200)
    clave_arranque: str


# --------------------------------------------------------------------------
# Trabajadores
# --------------------------------------------------------------------------


class TrabajadorNuevo(BaseModel):
    nombre: str = Field(min_length=3, max_length=180)
    dni: str = Field(default="", max_length=20)
    puesto: str = Field(default="", max_length=120)


class TrabajadorCambio(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=180)
    dni: str | None = Field(default=None, max_length=20)
    puesto: str | None = Field(default=None, max_length=120)
    activo: bool | None = None


class TrabajadorFuera(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    dni: str
    puesto: str
    activo: bool
    creado: datetime
    nominas: int = 0
    contratos: int = 0
    varios: int = 0


# --------------------------------------------------------------------------
# Documentos
# --------------------------------------------------------------------------


class DocumentoFuera(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trabajador_id: int | None
    trabajador_nombre: str | None = None
    tipo: str
    periodo_mes: int | None
    periodo_anio: int | None
    periodo_txt: str = ""
    nombre_fichero: str
    tamano: int
    paginas: str
    origen: str
    subido: datetime


class DocumentoCambio(BaseModel):
    trabajador_id: int | None = None
    tipo: str | None = Field(default=None, pattern="^(contrato|nomina|varios)$")
    periodo: str | None = None           # texto libre: "Enero 2025", "01/2025"
    nombre_fichero: str | None = Field(default=None, min_length=1, max_length=255)
    quitar_trabajador: bool = False      # mandar la hoja a _Sin identificar


# --------------------------------------------------------------------------
# Procesado de un PDF de lote
# --------------------------------------------------------------------------


class HojaProcesada(BaseModel):
    paginas: str
    trabajador_id: int | None
    trabajador_nombre: str | None
    periodo_txt: str
    nombre_fichero: str
    situacion: str                       # nuevo | duplicado | sin_identificar
    sin_texto: bool
    documento_id: int | None = None


class ResultadoProceso(BaseModel):
    simulado: bool
    origen: str
    paginas_totales: int
    nuevos: int
    duplicados: int
    sin_identificar: int
    sin_texto: int
    hojas: list[HojaProcesada]


# --------------------------------------------------------------------------
# Revision mensual
# --------------------------------------------------------------------------


class Revision(BaseModel):
    periodo_txt: str
    total: int
    con_nomina: list[str]
    sin_nomina: list[str]


class RegistroFuera(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    usuario_email: str
    accion: str
    origen: str
    paginas: str
    trabajador_nombre: str
    tipo: str
    periodo: str
    fichero: str
    detalle: str
