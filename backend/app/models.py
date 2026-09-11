# -*- coding: utf-8 -*-
"""Modelo de datos del archivo de nominas."""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(160))
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="gestor")  # admin | gestor
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Trabajador(Base):
    __tablename__ = "trabajadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(180))
    dni: Mapped[str] = mapped_column(String(20), default="")
    puesto: Mapped[str] = mapped_column(String(120), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documentos: Mapped[list["Documento"]] = relationship(back_populates="trabajador")

    __table_args__ = (
        UniqueConstraint("nombre", name="uq_trabajador_nombre"),
        Index("ix_trabajador_dni", "dni"),
    )


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL = hoja sin identificar, el equivalente a la carpeta _Sin identificar
    trabajador_id: Mapped[int | None] = mapped_column(
        ForeignKey("trabajadores.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo: Mapped[str] = mapped_column(String(20), default="nomina")  # contrato|nomina|varios
    periodo_mes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    periodo_anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nombre_fichero: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100), default="application/pdf")
    tamano: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    contenido: Mapped[bytes] = mapped_column(LargeBinary)
    paginas: Mapped[str] = mapped_column(String(60), default="")
    origen: Mapped[str] = mapped_column(String(255), default="")
    subido_por: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    subido: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trabajador: Mapped["Trabajador | None"] = relationship(back_populates="documentos")

    __table_args__ = (
        # Nunca se duplica el mismo contenido para el mismo trabajador.
        # postgresql_nulls_not_distinct hace que tambien aplique a las hojas sin asignar.
        Index("uq_doc_trab_sha", "trabajador_id", "sha256",
              unique=True, postgresql_nulls_not_distinct=True),
        Index("ix_doc_periodo", "periodo_anio", "periodo_mes"),
    )


class Registro(Base):
    """Traza de auditoria: el equivalente al registro.csv del script de escritorio."""

    __tablename__ = "registro"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    usuario_email: Mapped[str] = mapped_column(String(180), default="")
    accion: Mapped[str] = mapped_column(String(40), default="")
    origen: Mapped[str] = mapped_column(String(255), default="")
    paginas: Mapped[str] = mapped_column(String(60), default="")
    trabajador_nombre: Mapped[str] = mapped_column(String(180), default="")
    tipo: Mapped[str] = mapped_column(String(20), default="")
    periodo: Mapped[str] = mapped_column(String(40), default="")
    fichero: Mapped[str] = mapped_column(String(255), default="")
    detalle: Mapped[str] = mapped_column(Text, default="")
