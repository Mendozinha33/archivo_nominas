#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archivo de nóminas — reparto automático de un PDF con varias nóminas.

Crea y mantiene esta estructura de carpetas:

    Archivo/
        plantilla.json                  <- los trabajadores dados de alta
        registro.csv                    <- histórico de todo lo archivado
        Alvaro Ruiz Ferran/
            Contrato/
            Nóminas/
                Alvaro_Ruiz_Ferran_Enero_2025.pdf
            Documentos varios/
        _Sin identificar/               <- hojas que no ha sabido asignar

Uso rápido
----------
    python archivo_nominas.py alta "Álvaro Ruiz Ferrán" --dni 12345678Z --puesto Delantero
    python archivo_nominas.py procesar nominas_enero.pdf --simular
    python archivo_nominas.py procesar nominas_enero.pdf
    python archivo_nominas.py archivar contrato_alvaro.pdf --trabajador "Álvaro Ruiz" --tipo contrato
    python archivo_nominas.py revisar --periodo "Enero 2025"

Requisitos:  pip install pypdf
"""

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("Falta la librería pypdf.  Instálala con:  pip install pypdf")

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------

BASE_POR_DEFECTO = Path("Archivo")
SUBCARPETAS = ("Contrato", "Nóminas", "Documentos varios")
CARPETA_TIPO = {"contrato": "Contrato", "nomina": "Nóminas", "varios": "Documentos varios"}
SIN_IDENTIFICAR = "_Sin identificar"

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
MESES_BONITO = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "Y", "DA", "DOS", "VAN", "VON"}

# --------------------------------------------------------------------------
# Utilidades de texto
# --------------------------------------------------------------------------


def sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "")
                   if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", sin_acentos(texto).upper()).strip()


def para_fichero(texto: str) -> str:
    limpio = re.sub(r'[\\/:*?"<>|]', "", sin_acentos(texto))
    return re.sub(r"_+", "_", re.sub(r"\s+", "_", limpio)).strip("_")


def para_carpeta(texto: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", texto).strip() or "Sin nombre"


def tokens_nombre(nombre: str) -> list:
    return [t for t in normalizar(nombre).split(" ") if len(t) >= 3 and t not in PARTICULAS]


# --------------------------------------------------------------------------
# Plantilla de trabajadores
# --------------------------------------------------------------------------


def ruta_plantilla(base: Path) -> Path:
    return base / "plantilla.json"


def cargar_plantilla(base: Path) -> list:
    fichero = ruta_plantilla(base)
    if not fichero.exists():
        return []
    return json.loads(fichero.read_text(encoding="utf-8"))


def guardar_plantilla(base: Path, plantilla: list) -> None:
    base.mkdir(parents=True, exist_ok=True)
    plantilla.sort(key=lambda t: t["nombre"])
    ruta_plantilla(base).write_text(
        json.dumps(plantilla, ensure_ascii=False, indent=2), encoding="utf-8")


def buscar_trabajador(plantilla: list, texto_busqueda: str):
    """Busca por nombre parcial o DNI. Devuelve el trabajador o None."""
    aguja = normalizar(texto_busqueda)
    exactos = [t for t in plantilla if normalizar(t["nombre"]) == aguja
               or normalizar(t.get("dni", "")) == aguja]
    if exactos:
        return exactos[0]
    parciales = [t for t in plantilla if aguja in normalizar(t["nombre"])]
    if len(parciales) == 1:
        return parciales[0]
    if len(parciales) > 1:
        nombres = ", ".join(t["nombre"] for t in parciales)
        raise SystemExit(f"«{texto_busqueda}» encaja con varios trabajadores: {nombres}")
    return None


def crear_carpetas(base: Path, nombre: str) -> Path:
    carpeta = base / para_carpeta(nombre)
    for sub in SUBCARPETAS:
        (carpeta / sub).mkdir(parents=True, exist_ok=True)
    return carpeta


# --------------------------------------------------------------------------
# Reconocimiento de trabajador y periodo
# --------------------------------------------------------------------------


def identificar(texto_pagina: str, plantilla: list):
    texto = normalizar(texto_pagina)
    plano = re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9ÑÇ ]", " ", texto))
    compacto = re.sub(r"[^A-Z0-9]", "", texto)

    mejor, mejor_punt = None, 0
    for trabajador in plantilla:
        punt = 0
        dni = re.sub(r"[^A-Z0-9]", "", (trabajador.get("dni") or "").upper())
        if len(dni) >= 8 and dni in compacto:
            punt = 100
        else:
            tks = tokens_nombre(trabajador["nombre"])
            aciertos = sum(1 for t in tks if t in plano)
            if aciertos >= 2 or (len(tks) == 1 and aciertos == 1):
                punt = 10 * aciertos + (15 if aciertos == len(tks) else 0)
        if punt > mejor_punt:
            mejor, mejor_punt = trabajador, punt
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


def etiqueta_periodo(periodo, patron="mes") -> str:
    if not periodo:
        return "Sin_periodo"
    mes, anio = periodo
    if patron == "num":
        return f"{anio}-{mes:02d}" if anio else f"{mes:02d}"
    return MESES_BONITO[mes - 1] + (f"_{anio}" if anio else "")


def texto_a_periodo(texto: str):
    """Convierte lo que escriba el usuario ('Enero 2025', '01/2025') en (mes, anio)."""
    return detectar_periodo(texto) if texto else None


# --------------------------------------------------------------------------
# Registro y escritura
# --------------------------------------------------------------------------


def sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


def destino_libre(carpeta: Path, nombre: str, contenido: bytes):
    """Devuelve (ruta, 'nuevo'|'duplicado'). Nunca sobrescribe."""
    ruta = carpeta / nombre
    if not ruta.exists():
        return ruta, "nuevo"
    if sha(ruta.read_bytes()) == sha(contenido):
        return ruta, "duplicado"
    raiz, ext = ruta.stem, ruta.suffix
    n = 2
    while True:
        alterna = carpeta / f"{raiz}_({n}){ext}"
        if not alterna.exists():
            return alterna, "nuevo"
        if sha(alterna.read_bytes()) == sha(contenido):
            return alterna, "duplicado"
        n += 1


def anotar_registro(base: Path, filas: list) -> None:
    if not filas:
        return
    fichero = base / "registro.csv"
    nuevo = not fichero.exists()
    with fichero.open("a", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        if nuevo:
            escritor.writerow(["fecha", "origen", "paginas", "trabajador",
                               "tipo", "periodo", "fichero", "ruta"])
        escritor.writerows(filas)


# --------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------


def cmd_init(args):
    base = args.base
    base.mkdir(parents=True, exist_ok=True)
    if not ruta_plantilla(base).exists():
        guardar_plantilla(base, [])
    for t in cargar_plantilla(base):
        crear_carpetas(base, t["nombre"])
    print(f"Archivo preparado en: {base.resolve()}")


def cmd_alta(args):
    base = args.base
    plantilla = cargar_plantilla(base)
    if len(args.nombre.split()) < 2:
        raise SystemExit("Escribe nombre y al menos un apellido.")
    if any(normalizar(t["nombre"]) == normalizar(args.nombre) for t in plantilla):
        raise SystemExit(f"{args.nombre} ya está en la plantilla.")
    plantilla.append({
        "nombre": args.nombre.strip(),
        "dni": (args.dni or "").strip().upper(),
        "puesto": (args.puesto or "").strip(),
    })
    guardar_plantilla(base, plantilla)
    carpeta = crear_carpetas(base, args.nombre)
    print(f"Alta de {args.nombre}.  Carpeta: {carpeta}")


def cmd_editar(args):
    base = args.base
    plantilla = cargar_plantilla(base)
    trabajador = buscar_trabajador(plantilla, args.trabajador)
    if not trabajador:
        raise SystemExit(f"No encuentro a «{args.trabajador}» en la plantilla.")
    antiguo = trabajador["nombre"]
    if args.nombre:
        trabajador["nombre"] = args.nombre.strip()
    if args.dni is not None:
        trabajador["dni"] = args.dni.strip().upper()
    if args.puesto is not None:
        trabajador["puesto"] = args.puesto.strip()
    guardar_plantilla(base, plantilla)

    if args.nombre and para_carpeta(args.nombre) != para_carpeta(antiguo):
        vieja, nueva = base / para_carpeta(antiguo), base / para_carpeta(args.nombre)
        if vieja.exists() and not nueva.exists():
            vieja.rename(nueva)
            print(f"Carpeta renombrada: {vieja.name} -> {nueva.name}")
    crear_carpetas(base, trabajador["nombre"])
    print(f"Actualizado: {trabajador['nombre']}"
          f" · {trabajador.get('dni') or 'sin DNI'} · {trabajador.get('puesto') or 'sin puesto'}")


def cmd_baja(args):
    base = args.base
    plantilla = cargar_plantilla(base)
    trabajador = buscar_trabajador(plantilla, args.trabajador)
    if not trabajador:
        raise SystemExit(f"No encuentro a «{args.trabajador}» en la plantilla.")
    plantilla = [t for t in plantilla if t is not trabajador]
    guardar_plantilla(base, plantilla)
    print(f"{trabajador['nombre']} sale de la plantilla. "
          f"Su carpeta se conserva en {base / para_carpeta(trabajador['nombre'])}")


def cmd_plantilla(args):
    base = args.base
    plantilla = cargar_plantilla(base)
    if not plantilla:
        print("Plantilla vacía. Da de alta con:  alta \"Nombre Apellidos\" --dni 12345678Z")
        return
    print(f"{len(plantilla)} trabajador(es) en {base.resolve()}\n")
    for t in plantilla:
        carpeta = base / para_carpeta(t["nombre"])
        nominas = len(list((carpeta / "Nóminas").glob("*.pdf"))) if carpeta.exists() else 0
        contrato = any((carpeta / "Contrato").iterdir()) if (carpeta / "Contrato").exists() else False
        print(f"  {t['nombre']:<34} {t.get('dni',''):<11} {t.get('puesto',''):<26} "
              f"{nominas:>3} nómina(s)  {'contrato OK' if contrato else 'sin contrato'}")


def cmd_procesar(args):
    base, pdf = args.base, args.pdf
    if not pdf.exists():
        raise SystemExit(f"No existe el fichero {pdf}")
    plantilla = cargar_plantilla(base)
    if not plantilla:
        raise SystemExit("La plantilla está vacía: da de alta a los trabajadores antes de procesar.")

    lector = PdfReader(str(pdf))
    if lector.is_encrypted:
        try:
            lector.decrypt("")
        except Exception:
            raise SystemExit("El PDF está protegido con contraseña.")

    print(f"Leyendo {pdf.name} · {len(lector.pages)} páginas")
    paginas = []
    for i, pagina in enumerate(lector.pages):
        try:
            texto = pagina.extract_text() or ""
        except Exception:
            texto = ""
        if not texto.strip():
            print(f"  aviso: la página {i+1} no tiene texto (¿es un escaneo?)")
        periodo = texto_a_periodo(args.periodo) if args.periodo else detectar_periodo(texto)
        paginas.append({"i": i, "trab": identificar(texto, plantilla), "periodo": periodo})

    # agrupa páginas consecutivas del mismo trabajador y periodo
    grupos = []
    for p in paginas:
        clave = (p["trab"]["nombre"] if p["trab"] else None, p["periodo"])
        if grupos and grupos[-1]["clave"] == clave and p["trab"]:
            grupos[-1]["paginas"].append(p["i"])
        else:
            grupos.append({"clave": clave, "trab": p["trab"],
                           "periodo": p["periodo"], "paginas": [p["i"]]})

    filas, nuevos, repetidos, sin_asignar = [], 0, 0, 0
    for grupo in grupos:
        escritor = PdfWriter()
        for i in grupo["paginas"]:
            escritor.add_page(lector.pages[i])
        import io
        buffer = io.BytesIO()
        escritor.write(buffer)
        contenido = buffer.getvalue()

        trabajador = grupo["trab"]
        etiqueta = etiqueta_periodo(grupo["periodo"], args.patron)
        if trabajador:
            carpeta = crear_carpetas(base, trabajador["nombre"]) / "Nóminas"
            nombre = f"{para_fichero(trabajador['nombre'])}_{etiqueta}.pdf"
        else:
            carpeta = base / SIN_IDENTIFICAR
            carpeta.mkdir(parents=True, exist_ok=True)
            nombre = f"{pdf.stem}_pag{grupo['paginas'][0]+1}.pdf"
            sin_asignar += 1

        destino, situacion = destino_libre(carpeta, nombre, contenido)
        rango = (f"{grupo['paginas'][0]+1}" if len(grupo["paginas"]) == 1
                 else f"{grupo['paginas'][0]+1}-{grupo['paginas'][-1]+1}")

        if args.simular:
            print(f"  [simulación] pág. {rango:<7} -> {destino.relative_to(base)}"
                  f"{'   (ya archivada)' if situacion == 'duplicado' else ''}")
            continue

        if situacion == "duplicado":
            repetidos += 1
            print(f"  pág. {rango:<7} ya estaba archivada en {destino.relative_to(base)}")
            continue

        destino.write_bytes(contenido)
        nuevos += 1
        print(f"  pág. {rango:<7} -> {destino.relative_to(base)}")
        filas.append([datetime.now().strftime("%Y-%m-%d %H:%M"), pdf.name, rango,
                      trabajador["nombre"] if trabajador else "Sin identificar",
                      "nomina", etiqueta.replace("_", " "), destino.name,
                      str(destino.relative_to(base))])

    anotar_registro(base, filas)
    if args.simular:
        print("\nSimulación terminada: no se ha escrito nada.")
        return
    print(f"\n{nuevos} nómina(s) archivadas · {repetidos} repetida(s) · "
          f"{sin_asignar} sin identificar")
    if sin_asignar:
        print(f"Revisa {base / SIN_IDENTIFICAR} y usa «archivar» para colocarlas a mano.")

    if args.mover_origen:
        entradas = base / "_PDF procesados"
        entradas.mkdir(exist_ok=True)
        shutil.move(str(pdf), str(entradas / pdf.name))
        print(f"Original movido a {entradas / pdf.name}")


def cmd_archivar(args):
    base = args.base
    plantilla = cargar_plantilla(base)
    trabajador = buscar_trabajador(plantilla, args.trabajador)
    if not trabajador:
        raise SystemExit(f"No encuentro a «{args.trabajador}» en la plantilla.")
    if not args.fichero.exists():
        raise SystemExit(f"No existe el fichero {args.fichero}")

    carpeta = crear_carpetas(base, trabajador["nombre"]) / CARPETA_TIPO[args.tipo]
    contenido = args.fichero.read_bytes()

    if args.nombre:
        nombre = args.nombre
    elif args.tipo == "nomina":
        periodo = texto_a_periodo(args.periodo) if args.periodo else None
        nombre = f"{para_fichero(trabajador['nombre'])}_{etiqueta_periodo(periodo, args.patron)}.pdf"
    elif args.tipo == "contrato":
        nombre = f"{para_fichero(trabajador['nombre'])}_Contrato{args.fichero.suffix}"
    else:
        nombre = args.fichero.name

    destino, situacion = destino_libre(carpeta, nombre, contenido)
    if situacion == "duplicado":
        print(f"Ese fichero ya estaba en {destino.relative_to(base)}")
        return
    destino.write_bytes(contenido)
    anotar_registro(base, [[datetime.now().strftime("%Y-%m-%d %H:%M"), args.fichero.name, "",
                            trabajador["nombre"], args.tipo, args.periodo or "",
                            destino.name, str(destino.relative_to(base))]])
    print(f"Archivado en {destino.relative_to(base)}")


def cmd_revisar(args):
    base = args.base
    plantilla = cargar_plantilla(base)
    if not plantilla:
        raise SystemExit("La plantilla está vacía.")
    periodo = texto_a_periodo(args.periodo)
    if not periodo:
        raise SystemExit('No entiendo el periodo. Prueba con "Enero 2025" o "01/2025".')

    marca_mes = para_fichero(etiqueta_periodo(periodo, "mes")).upper()
    marca_num = etiqueta_periodo(periodo, "num")
    con, sin = [], []
    for t in plantilla:
        carpeta = base / para_carpeta(t["nombre"]) / "Nóminas"
        ficheros = [f.name.upper() for f in carpeta.glob("*.pdf")] if carpeta.exists() else []
        if any(marca_mes in f or marca_num in f for f in ficheros):
            con.append(t["nombre"])
        else:
            sin.append(t["nombre"])

    etiqueta = etiqueta_periodo(periodo, "mes").replace("_", " ")
    print(f"Periodo {etiqueta}: {len(con)} de {len(plantilla)} con nómina archivada")
    if sin:
        print("\nFalta la nómina de:")
        for nombre in sin:
            print(f"  · {nombre}")
    else:
        print("\nNo falta ninguna.")


# --------------------------------------------------------------------------
# Línea de comandos
# --------------------------------------------------------------------------


def construir_parser():
    p = argparse.ArgumentParser(
        description="Reparte un PDF con varias nóminas en la carpeta de cada trabajador.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplo:  python archivo_nominas.py procesar nominas_enero.pdf --simular")
    p.add_argument("--base", type=Path, default=BASE_POR_DEFECTO,
                   help="carpeta raíz del archivo (por defecto: ./Archivo)")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("init", help="crea la carpeta del archivo")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("alta", help="da de alta a un trabajador y crea sus carpetas")
    s.add_argument("nombre")
    s.add_argument("--dni", default="")
    s.add_argument("--puesto", default="")
    s.set_defaults(func=cmd_alta)

    s = sub.add_parser("editar", help="cambia los datos de un trabajador")
    s.add_argument("trabajador", help="nombre parcial o DNI")
    s.add_argument("--nombre", help="nombre nuevo (renombra también su carpeta)")
    s.add_argument("--dni")
    s.add_argument("--puesto")
    s.set_defaults(func=cmd_editar)

    s = sub.add_parser("baja", help="quita a un trabajador de la plantilla (conserva su carpeta)")
    s.add_argument("trabajador")
    s.set_defaults(func=cmd_baja)

    s = sub.add_parser("plantilla", help="lista la plantilla y lo archivado de cada uno")
    s.set_defaults(func=cmd_plantilla)

    s = sub.add_parser("procesar", help="trocea un PDF de nóminas y lo reparte")
    s.add_argument("pdf", type=Path)
    s.add_argument("--periodo", help='fuerza el periodo, p. ej. "Enero 2025"')
    s.add_argument("--patron", choices=["mes", "num"], default="mes",
                   help="mes: Nombre_Enero_2025 · num: Nombre_2025-01")
    s.add_argument("--simular", action="store_true", help="enseña qué haría sin escribir nada")
    s.add_argument("--mover-origen", action="store_true",
                   help="mueve el PDF original a _PDF procesados al terminar")
    s.set_defaults(func=cmd_procesar)

    s = sub.add_parser("archivar", help="guarda un fichero suelto en la carpeta de un trabajador")
    s.add_argument("fichero", type=Path)
    s.add_argument("--trabajador", required=True)
    s.add_argument("--tipo", choices=["contrato", "nomina", "varios"], default="varios")
    s.add_argument("--periodo", help='para --tipo nomina, p. ej. "Enero 2025"')
    s.add_argument("--nombre", help="nombre de fichero a medida")
    s.add_argument("--patron", choices=["mes", "num"], default="mes")
    s.set_defaults(func=cmd_archivar)

    s = sub.add_parser("revisar", help="dice a quién le falta la nómina de un periodo")
    s.add_argument("--periodo", required=True)
    s.set_defaults(func=cmd_revisar)

    return p


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = construir_parser().parse_args()
    args.base.mkdir(parents=True, exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
