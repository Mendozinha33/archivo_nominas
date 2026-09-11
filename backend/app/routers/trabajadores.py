# -*- coding: utf-8 -*-
"""Plantilla: alta, edicion y baja de trabajadores."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from ..deps import Actual, Admin, SesionBD, anotar
from ..models import Documento, Trabajador
from ..nominas import normalizar
from ..schemas import TrabajadorCambio, TrabajadorFuera, TrabajadorNuevo

router = APIRouter(prefix="/api/trabajadores", tags=["trabajadores"])


def _con_recuento(bd, trabajadores: list[Trabajador]) -> list[TrabajadorFuera]:
    """Anade a cada trabajador cuantos documentos tiene de cada tipo, en una sola consulta."""
    if not trabajadores:
        return []
    ids = [t.id for t in trabajadores]
    filas = bd.execute(
        select(Documento.trabajador_id, Documento.tipo, func.count())
        .where(Documento.trabajador_id.in_(ids))
        .group_by(Documento.trabajador_id, Documento.tipo)
    ).all()
    conteo: dict[int, dict[str, int]] = {}
    for trab_id, tipo, n in filas:
        conteo.setdefault(trab_id, {})[tipo] = n

    salida = []
    for t in trabajadores:
        c = conteo.get(t.id, {})
        ficha = TrabajadorFuera.model_validate(t)
        ficha.nominas = c.get("nomina", 0)
        ficha.contratos = c.get("contrato", 0)
        ficha.varios = c.get("varios", 0)
        salida.append(ficha)
    return salida


@router.get("", response_model=list[TrabajadorFuera])
def listar(bd: SesionBD, _: Actual, incluir_bajas: bool = False) -> list[TrabajadorFuera]:
    consulta = select(Trabajador).order_by(Trabajador.nombre)
    if not incluir_bajas:
        consulta = consulta.where(Trabajador.activo.is_(True))
    return _con_recuento(bd, list(bd.scalars(consulta)))


@router.post("", response_model=TrabajadorFuera, status_code=status.HTTP_201_CREATED)
def alta(datos: TrabajadorNuevo, bd: SesionBD, usuario: Actual) -> TrabajadorFuera:
    if len(datos.nombre.split()) < 2:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Escribe nombre y al menos un apellido.")
    existentes = bd.scalars(select(Trabajador)).all()
    if any(normalizar(t.nombre) == normalizar(datos.nombre) for t in existentes):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"{datos.nombre} ya está en la plantilla.")

    trabajador = Trabajador(nombre=datos.nombre.strip(), dni=datos.dni.strip().upper(),
                            puesto=datos.puesto.strip(), activo=True)
    bd.add(trabajador)
    bd.flush()
    anotar(bd, usuario, "trabajador_alta", trabajador_nombre=trabajador.nombre)
    return _con_recuento(bd, [trabajador])[0]


@router.patch("/{trabajador_id}", response_model=TrabajadorFuera)
def editar(trabajador_id: int, datos: TrabajadorCambio,
           bd: SesionBD, usuario: Actual) -> TrabajadorFuera:
    trabajador = bd.get(Trabajador, trabajador_id)
    if not trabajador:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trabajador no encontrado.")

    if datos.nombre is not None:
        otros = bd.scalars(select(Trabajador).where(Trabajador.id != trabajador_id)).all()
        if any(normalizar(t.nombre) == normalizar(datos.nombre) for t in otros):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"Ya hay otro trabajador llamado {datos.nombre}.")
        trabajador.nombre = datos.nombre.strip()
    if datos.dni is not None:
        trabajador.dni = datos.dni.strip().upper()
    if datos.puesto is not None:
        trabajador.puesto = datos.puesto.strip()
    if datos.activo is not None:
        trabajador.activo = datos.activo

    anotar(bd, usuario, "trabajador_edita", trabajador_nombre=trabajador.nombre)
    return _con_recuento(bd, [trabajador])[0]


@router.delete("/{trabajador_id}", status_code=status.HTTP_204_NO_CONTENT)
def baja(trabajador_id: int, bd: SesionBD, admin: Admin, borrar_documentos: bool = False) -> None:
    """Baja del trabajador. Por defecto conserva sus documentos, como el script de escritorio."""
    trabajador = bd.get(Trabajador, trabajador_id)
    if not trabajador:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trabajador no encontrado.")

    n = bd.scalar(select(func.count()).select_from(Documento)
                  .where(Documento.trabajador_id == trabajador_id)) or 0
    if borrar_documentos:
        for doc in bd.scalars(select(Documento).where(Documento.trabajador_id == trabajador_id)):
            bd.delete(doc)
        anotar(bd, admin, "trabajador_borra", trabajador_nombre=trabajador.nombre,
               detalle=f"Baja con borrado de {n} documento(s)")
        bd.delete(trabajador)
    else:
        # Se conserva el historico: el trabajador queda inactivo y sus documentos intactos.
        trabajador.activo = False
        anotar(bd, admin, "trabajador_baja", trabajador_nombre=trabajador.nombre,
               detalle=f"Baja conservando {n} documento(s)")
