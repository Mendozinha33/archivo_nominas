# -*- coding: utf-8 -*-
"""Revision mensual y registro de auditoria."""

import csv
import io

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from ..deps import Actual, SesionBD
from ..models import Documento, Registro, Trabajador
from ..nominas import periodo_legible, texto_a_periodo
from ..schemas import RegistroFuera, Revision

router = APIRouter(prefix="/api", tags=["revision"])


@router.get("/revisar", response_model=Revision)
def revisar(bd: SesionBD, _: Actual, periodo: str = Query(...)) -> Revision:
    """Dice a quien le falta la nomina de un periodo."""
    p = texto_a_periodo(periodo)
    if not p:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            'No entiendo el periodo. Prueba con "Enero 2025" o "01/2025".')
    mes, anio = p

    plantilla = list(bd.scalars(
        select(Trabajador).where(Trabajador.activo.is_(True)).order_by(Trabajador.nombre)))
    if not plantilla:
        raise HTTPException(status.HTTP_409_CONFLICT, "La plantilla está vacía.")

    consulta = select(Documento.trabajador_id).where(
        Documento.tipo == "nomina", Documento.periodo_mes == mes)
    if anio:
        consulta = consulta.where(Documento.periodo_anio == anio)
    con_nomina = {i for (i,) in bd.execute(consulta.distinct()).all() if i is not None}

    return Revision(
        periodo_txt=periodo_legible(mes, anio),
        total=len(plantilla),
        con_nomina=[t.nombre for t in plantilla if t.id in con_nomina],
        sin_nomina=[t.nombre for t in plantilla if t.id not in con_nomina],
    )


@router.get("/registro", response_model=list[RegistroFuera])
def registro(bd: SesionBD, _: Actual, limite: int = Query(300, le=2000)) -> list[Registro]:
    return list(bd.scalars(select(Registro).order_by(Registro.id.desc()).limit(limite)))


@router.get("/registro/csv")
def registro_csv(bd: SesionBD, _: Actual) -> Response:
    """Mismo CSV que generaba el script de escritorio, listo para abrir con Excel."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(["fecha", "usuario", "accion", "origen", "paginas",
                       "trabajador", "tipo", "periodo", "fichero", "detalle"])
    for r in bd.scalars(select(Registro).order_by(Registro.id)):
        escritor.writerow([
            r.fecha.strftime("%Y-%m-%d %H:%M"), r.usuario_email, r.accion, r.origen,
            r.paginas, r.trabajador_nombre, r.tipo, r.periodo, r.fichero, r.detalle,
        ])
    # utf-8-sig para que Excel respete los acentos al abrirlo directamente.
    return Response(
        content=salida.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="registro.csv"'},
    )
