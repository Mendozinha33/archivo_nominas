# -*- coding: utf-8 -*-
"""Documentos: procesado del PDF de lote, consulta, reasignacion, descarga y ZIP."""

import io
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..config import ajustes
from ..deps import Actual, Admin, SesionBD, anotar
from ..models import Documento, Trabajador
from ..nominas import (
    CARPETA_TIPO, SIN_IDENTIFICAR, Candidato, nombre_documento, para_carpeta,
    periodo_legible, sha, texto_a_periodo, trocear,
)
from ..schemas import DocumentoCambio, DocumentoFuera, HojaProcesada, ResultadoProceso

router = APIRouter(prefix="/api/documentos", tags=["documentos"])

TIPOS_VALIDOS = set(CARPETA_TIPO)


def _a_salida(doc: Documento) -> DocumentoFuera:
    ficha = DocumentoFuera.model_validate(doc)
    ficha.trabajador_nombre = doc.trabajador.nombre if doc.trabajador else None
    ficha.periodo_txt = periodo_legible(doc.periodo_mes, doc.periodo_anio)
    return ficha


def _leer_subida(fichero: UploadFile) -> bytes:
    datos = fichero.file.read()
    tope = ajustes().max_mb_subida * 1024 * 1024
    if len(datos) > tope:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"El fichero pasa de {ajustes().max_mb_subida} MB.")
    if not datos:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El fichero está vacío.")
    return datos


def _ya_archivado(bd, trabajador_id: int | None, firma: str) -> Documento | None:
    """Reproduce la regla del script: mismo contenido para el mismo destino = duplicado."""
    return bd.scalar(select(Documento).where(
        Documento.sha256 == firma,
        Documento.trabajador_id.is_(None) if trabajador_id is None
        else Documento.trabajador_id == trabajador_id,
    ))


# --------------------------------------------------------------------------
# Procesar un PDF con varias nominas
# --------------------------------------------------------------------------


@router.post("/procesar", response_model=ResultadoProceso)
def procesar(
    bd: SesionBD,
    usuario: Actual,
    fichero: UploadFile = File(...),
    simular: bool = Form(False),
    periodo: str | None = Form(None),
    patron: str = Form("mes"),
) -> ResultadoProceso:
    """Trocea el PDF y reparte cada hoja. Con simular=true no escribe nada."""
    if patron not in ("mes", "num"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Patrón no válido.")

    plantilla = list(bd.scalars(select(Trabajador).where(Trabajador.activo.is_(True))))
    if not plantilla:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "La plantilla está vacía: da de alta a los trabajadores antes de procesar.")

    datos = _leer_subida(fichero)
    candidatos = [Candidato(id=t.id, nombre=t.nombre, dni=t.dni or "") for t in plantilla]
    try:
        grupos = trocear(datos, candidatos, periodo)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "No he podido leer el PDF. ¿Seguro que es un PDF válido?") from exc

    origen = fichero.filename or "lote.pdf"
    por_id = {t.id: t for t in plantilla}
    hojas: list[HojaProcesada] = []
    nuevos = duplicados = sin_identificar = sin_texto = 0

    for grupo in grupos:
        trabajador = por_id.get(grupo.candidato.id) if grupo.candidato else None
        nombre = nombre_documento(
            "nomina", trabajador.nombre if trabajador else None, grupo.periodo,
            patron=patron, origen=origen, primera_pagina=grupo.paginas[0] + 1)
        firma = sha(grupo.contenido)
        repetido = _ya_archivado(bd, trabajador.id if trabajador else None, firma) is not None

        if grupo.sin_texto:
            sin_texto += 1
        if not trabajador:
            sin_identificar += 1

        hoja = HojaProcesada(
            paginas=grupo.rango,
            trabajador_id=trabajador.id if trabajador else None,
            trabajador_nombre=trabajador.nombre if trabajador else None,
            periodo_txt=periodo_legible(*grupo.periodo) if grupo.periodo else "",
            nombre_fichero=nombre,
            situacion="duplicado" if repetido else ("nuevo" if trabajador else "sin_identificar"),
            sin_texto=grupo.sin_texto,
        )

        if simular or repetido:
            if repetido:
                duplicados += 1
            hojas.append(hoja)
            continue

        doc = Documento(
            trabajador_id=trabajador.id if trabajador else None,
            tipo="nomina",
            periodo_mes=grupo.periodo[0] if grupo.periodo else None,
            periodo_anio=grupo.periodo[1] if grupo.periodo else None,
            nombre_fichero=nombre,
            tamano=len(grupo.contenido),
            sha256=firma,
            contenido=grupo.contenido,
            paginas=grupo.rango,
            origen=origen,
            subido_por=usuario.id,
        )
        bd.add(doc)
        try:
            bd.flush()
        except IntegrityError:
            # Carrera con otra subida simultanea del mismo contenido: cuenta como duplicado.
            bd.rollback()
            duplicados += 1
            hoja.situacion = "duplicado"
            hojas.append(hoja)
            continue

        nuevos += 1
        hoja.documento_id = doc.id
        anotar(bd, usuario, "procesar", origen=origen, paginas=grupo.rango,
               trabajador_nombre=trabajador.nombre if trabajador else "Sin identificar",
               tipo="nomina", periodo=hoja.periodo_txt, fichero=nombre)
        hojas.append(hoja)

    return ResultadoProceso(
        simulado=simular, origen=origen,
        paginas_totales=sum(len(g.paginas) for g in grupos),
        nuevos=nuevos, duplicados=duplicados,
        sin_identificar=sin_identificar, sin_texto=sin_texto, hojas=hojas,
    )


# --------------------------------------------------------------------------
# Archivar un fichero suelto
# --------------------------------------------------------------------------


@router.post("", response_model=DocumentoFuera, status_code=status.HTTP_201_CREATED)
def archivar(
    bd: SesionBD,
    usuario: Actual,
    fichero: UploadFile = File(...),
    trabajador_id: int = Form(...),
    tipo: str = Form("varios"),
    periodo: str | None = Form(None),
    patron: str = Form("mes"),
    nombre: str | None = Form(None),
) -> DocumentoFuera:
    """Guarda un contrato, una nomina suelta o cualquier documento de un trabajador."""
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tipo no válido.")
    trabajador = bd.get(Trabajador, trabajador_id)
    if not trabajador:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trabajador no encontrado.")

    datos = _leer_subida(fichero)
    original = fichero.filename or "documento.pdf"
    sufijo = "." + original.rsplit(".", 1)[-1] if "." in original else ".pdf"
    p = texto_a_periodo(periodo) if periodo else None

    nombre_final = nombre or nombre_documento(
        tipo, trabajador.nombre, p, patron=patron, origen=original, sufijo=sufijo)

    firma = sha(datos)
    if _ya_archivado(bd, trabajador.id, firma):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Ese fichero ya estaba archivado para este trabajador.")

    doc = Documento(
        trabajador_id=trabajador.id, tipo=tipo,
        periodo_mes=p[0] if p else None, periodo_anio=p[1] if p else None,
        nombre_fichero=nombre_final, mime=fichero.content_type or "application/pdf",
        tamano=len(datos), sha256=firma, contenido=datos, paginas="",
        origen=original, subido_por=usuario.id,
    )
    bd.add(doc)
    bd.flush()
    anotar(bd, usuario, "archivar", origen=original, trabajador_nombre=trabajador.nombre,
           tipo=tipo, periodo=periodo_legible(doc.periodo_mes, doc.periodo_anio),
           fichero=nombre_final)
    bd.refresh(doc)
    return _a_salida(doc)


# --------------------------------------------------------------------------
# Consulta
# --------------------------------------------------------------------------


@router.get("", response_model=list[DocumentoFuera])
def listar(
    bd: SesionBD,
    _: Actual,
    trabajador_id: int | None = None,
    sin_asignar: bool = False,
    tipo: str | None = None,
    anio: int | None = None,
    mes: int | None = None,
    limite: int = Query(500, le=2000),
) -> list[DocumentoFuera]:
    consulta = select(Documento).options(selectinload(Documento.trabajador))
    if sin_asignar:
        consulta = consulta.where(Documento.trabajador_id.is_(None))
    elif trabajador_id is not None:
        consulta = consulta.where(Documento.trabajador_id == trabajador_id)
    if tipo:
        consulta = consulta.where(Documento.tipo == tipo)
    if anio:
        consulta = consulta.where(Documento.periodo_anio == anio)
    if mes:
        consulta = consulta.where(Documento.periodo_mes == mes)
    consulta = consulta.order_by(
        Documento.periodo_anio.desc().nullslast(),
        Documento.periodo_mes.desc().nullslast(),
        Documento.id.desc(),
    ).limit(limite)
    return [_a_salida(d) for d in bd.scalars(consulta)]


# El conversor :int evita que "/zip/descargar" quede capturado por esta ruta.
@router.get("/{documento_id:int}/descargar")
def descargar(documento_id: int, bd: SesionBD, _: Actual) -> Response:
    doc = bd.get(Documento, documento_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    return Response(
        content=doc.contenido,
        media_type=doc.mime or "application/pdf",
        headers={"Content-Disposition":
                 f"attachment; filename*=UTF-8''{quote(doc.nombre_fichero)}"},
    )


# --------------------------------------------------------------------------
# Reasignacion y borrado
# --------------------------------------------------------------------------


@router.patch("/{documento_id:int}", response_model=DocumentoFuera)
def editar(documento_id: int, datos: DocumentoCambio,
           bd: SesionBD, usuario: Actual) -> DocumentoFuera:
    doc = bd.get(Documento, documento_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")

    if datos.quitar_trabajador:
        doc.trabajador_id = None
    elif datos.trabajador_id is not None:
        if not bd.get(Trabajador, datos.trabajador_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Trabajador no encontrado.")
        doc.trabajador_id = datos.trabajador_id

    if datos.tipo is not None:
        doc.tipo = datos.tipo
    if datos.periodo is not None:
        p = texto_a_periodo(datos.periodo)
        doc.periodo_mes = p[0] if p else None
        doc.periodo_anio = p[1] if p else None
    if datos.nombre_fichero is not None:
        doc.nombre_fichero = datos.nombre_fichero.strip()

    try:
        bd.flush()
    except IntegrityError as exc:
        bd.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Ese trabajador ya tiene archivado un documento idéntico.") from exc

    bd.refresh(doc)
    anotar(bd, usuario, "documento_edita", fichero=doc.nombre_fichero,
           trabajador_nombre=doc.trabajador.nombre if doc.trabajador else "Sin identificar",
           tipo=doc.tipo, periodo=periodo_legible(doc.periodo_mes, doc.periodo_anio))
    return _a_salida(doc)


@router.delete("/{documento_id:int}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(documento_id: int, bd: SesionBD, admin: Admin) -> None:
    doc = bd.get(Documento, documento_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado.")
    anotar(bd, admin, "documento_borra", fichero=doc.nombre_fichero,
           trabajador_nombre=doc.trabajador.nombre if doc.trabajador else "Sin identificar",
           tipo=doc.tipo, periodo=periodo_legible(doc.periodo_mes, doc.periodo_anio))
    bd.delete(doc)


# --------------------------------------------------------------------------
# Descarga masiva en ZIP con la estructura de carpetas de siempre
# --------------------------------------------------------------------------


@router.get("/zip/descargar")
def zip_descargar(
    bd: SesionBD,
    _: Actual,
    trabajador_id: int | None = None,
    anio: int | None = None,
    mes: int | None = None,
) -> StreamingResponse:
    consulta = select(Documento).options(selectinload(Documento.trabajador))
    if trabajador_id is not None:
        consulta = consulta.where(Documento.trabajador_id == trabajador_id)
    if anio:
        consulta = consulta.where(Documento.periodo_anio == anio)
    if mes:
        consulta = consulta.where(Documento.periodo_mes == mes)
    documentos = list(bd.scalars(consulta))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        # La estructura completa se crea siempre, aunque una subcarpeta quede vacia.
        trabajadores = bd.scalars(
            select(Trabajador).where(Trabajador.id == trabajador_id) if trabajador_id
            else select(Trabajador).where(Trabajador.activo.is_(True))
        ).all()
        for t in trabajadores:
            for carpeta in CARPETA_TIPO.values():
                z.writestr(f"{para_carpeta(t.nombre)}/{carpeta}/", "")

        usados: set[str] = set()
        for doc in documentos:
            if doc.trabajador:
                ruta = f"{para_carpeta(doc.trabajador.nombre)}/{CARPETA_TIPO[doc.tipo]}"
            else:
                ruta = SIN_IDENTIFICAR
            destino = f"{ruta}/{doc.nombre_fichero}"
            # Dos documentos distintos no pueden compartir nombre dentro del ZIP.
            if destino in usados:
                raiz, _, ext = doc.nombre_fichero.rpartition(".")
                n = 2
                while destino in usados:
                    destino = f"{ruta}/{raiz}_({n}).{ext}" if raiz else f"{ruta}/{doc.nombre_fichero}_({n})"
                    n += 1
            usados.add(destino)
            z.writestr(destino, doc.contenido)

    buffer.seek(0)
    nombre = "archivo_nominas.zip"
    return StreamingResponse(
        buffer, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
