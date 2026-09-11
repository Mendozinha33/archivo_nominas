# -*- coding: utf-8 -*-
"""
Logica de reparto de nominas, portada desde script_escritorio/archivo_nominas.py.

Aqui no se toca ni disco ni base de datos: son funciones puras sobre texto y bytes,
para que se puedan probar sueltas y reutilizar desde la API.
"""

import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
MESES_BONITO = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "Y", "DA", "DOS", "VAN", "VON"}

CARPETA_TIPO = {"contrato": "Contrato", "nomina": "Nóminas", "varios": "Documentos varios"}
SIN_IDENTIFICAR = "_Sin identificar"


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------


def sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", sin_acentos(texto).upper()).strip()


def para_fichero(texto: str) -> str:
    limpio = re.sub(r'[\\/:*?"<>|]', "", sin_acentos(texto))
    return re.sub(r"_+", "_", re.sub(r"\s+", "_", limpio)).strip("_")


def para_carpeta(texto: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", texto or "").strip() or "Sin nombre"


def tokens_nombre(nombre: str) -> list[str]:
    return [t for t in normalizar(nombre).split(" ") if len(t) >= 3 and t not in PARTICULAS]


def sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


# ---------------------------------------------------------------------------
# Identificacion de trabajador y periodo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidato:
    """Trabajador reducido a lo que hace falta para identificarlo."""

    id: int
    nombre: str
    dni: str = ""


def identificar(texto_pagina: str, candidatos: list[Candidato]) -> Candidato | None:
    """Devuelve el trabajador de la hoja, o None si no hay confianza suficiente."""
    texto = normalizar(texto_pagina)
    plano = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9ÑÇ ]", " ", texto))
    compacto = re.sub(r"[^A-Z0-9]", "", texto)

    mejor, mejor_punt = None, 0
    for cand in candidatos:
        punt = 0
        dni = re.sub(r"[^A-Z0-9]", "", (cand.dni or "").upper())
        if len(dni) >= 8 and dni in compacto:
            punt = 100
        else:
            tks = tokens_nombre(cand.nombre)
            aciertos = sum(1 for t in tks if t in plano)
            if aciertos >= 2 or (len(tks) == 1 and aciertos == 1):
                punt = 10 * aciertos + (15 if aciertos == len(tks) else 0)
        if punt > mejor_punt:
            mejor, mejor_punt = cand, punt
    return mejor if mejor_punt >= 20 else None


def detectar_periodo(texto_pagina: str):
    """Devuelve (mes, anio) o None."""
    texto = normalizar(texto_pagina)

    m = re.search(r"PERIODO[^0-9]{0,25}(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", texto)
    if m:
        anio = int(m.group(3))
        return int(m.group(2)), anio if anio > 99 else 2000 + anio

    for i, mes in enumerate(MESES):
        m = re.search(r"\b" + mes + r"\b(?:\s+(?:DE|DEL)\s*)?\s*(\d{4})?", texto)
        if m:
            if m.group(1):
                return i + 1, int(m.group(1))
            suelto = re.search(r"\b(20\d{2})\b", texto)
            return i + 1, int(suelto.group(1)) if suelto else None

    m = re.search(r"\b(0[1-9]|1[0-2])[/\-](20\d{2})\b", texto)
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](20\d{2})\b", texto)
    if m:
        return int(m.group(2)), int(m.group(3))
    return None


def texto_a_periodo(texto):
    return detectar_periodo(texto) if texto else None


def etiqueta_periodo(periodo, patron: str = "mes") -> str:
    if not periodo:
        return "Sin_periodo"
    mes, anio = periodo
    if patron == "num":
        return f"{anio}-{mes:02d}" if anio else f"{mes:02d}"
    return MESES_BONITO[mes - 1] + (f"_{anio}" if anio else "")


def periodo_legible(mes, anio) -> str:
    if not mes:
        return ""
    return MESES_BONITO[mes - 1] + (f" {anio}" if anio else "")


# ---------------------------------------------------------------------------
# Troceo del PDF
# ---------------------------------------------------------------------------


@dataclass
class Grupo:
    """Paginas consecutivas que pertenecen al mismo trabajador y periodo."""

    paginas: list
    candidato: Candidato | None
    periodo: tuple | None
    contenido: bytes
    sin_texto: bool

    @property
    def rango(self) -> str:
        if len(self.paginas) == 1:
            return str(self.paginas[0] + 1)
        return f"{self.paginas[0] + 1}-{self.paginas[-1] + 1}"


def trocear(datos_pdf: bytes, candidatos: list, periodo_forzado: str | None = None) -> list:
    """Lee el PDF, identifica cada hoja y devuelve los grupos ya extraidos a bytes."""
    lector = PdfReader(io.BytesIO(datos_pdf))
    if lector.is_encrypted:
        try:
            lector.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise ValueError("El PDF está protegido con contraseña.") from exc

    forzado = texto_a_periodo(periodo_forzado) if periodo_forzado else None

    paginas = []
    for i, pagina in enumerate(lector.pages):
        try:
            texto = pagina.extract_text() or ""
        except Exception:  # noqa: BLE001
            texto = ""
        paginas.append({
            "i": i,
            "cand": identificar(texto, candidatos),
            "periodo": forzado or detectar_periodo(texto),
            "sin_texto": not texto.strip(),
        })

    # agrupa paginas consecutivas del mismo trabajador y periodo
    crudos = []
    for p in paginas:
        clave = (p["cand"].id if p["cand"] else None, p["periodo"])
        if crudos and crudos[-1]["clave"] == clave and p["cand"]:
            crudos[-1]["paginas"].append(p["i"])
            crudos[-1]["sin_texto"] = crudos[-1]["sin_texto"] and p["sin_texto"]
        else:
            crudos.append({"clave": clave, "cand": p["cand"], "periodo": p["periodo"],
                           "paginas": [p["i"]], "sin_texto": p["sin_texto"]})

    grupos = []
    for crudo in crudos:
        escritor = PdfWriter()
        for i in crudo["paginas"]:
            escritor.add_page(lector.pages[i])
        buffer = io.BytesIO()
        escritor.write(buffer)
        grupos.append(Grupo(paginas=crudo["paginas"], candidato=crudo["cand"],
                            periodo=crudo["periodo"], contenido=buffer.getvalue(),
                            sin_texto=crudo["sin_texto"]))
    return grupos


def nombre_documento(tipo: str, nombre_trabajador, periodo, patron: str = "mes",
                     origen: str = "documento.pdf", primera_pagina: int = 1,
                     sufijo: str = ".pdf") -> str:
    """Nombre de fichero con el mismo criterio que el script de escritorio."""
    if not nombre_trabajador:
        raiz = para_fichero(origen.rsplit(".", 1)[0]) or "hoja"
        return f"{raiz}_pag{primera_pagina}.pdf"
    base = para_fichero(nombre_trabajador)
    if tipo == "nomina":
        return f"{base}_{etiqueta_periodo(periodo, patron)}.pdf"
    if tipo == "contrato":
        return f"{base}_Contrato{sufijo}"
    return f"{base}_{para_fichero(origen)}" if origen else f"{base}{sufijo}"
