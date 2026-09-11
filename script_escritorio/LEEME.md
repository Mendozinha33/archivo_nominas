# Archivo de nóminas — script de escritorio

Reparte un PDF con varias nóminas en la carpeta de cada trabajador, en tu disco o en una
unidad de red. A diferencia de la versión web, aquí el archivo queda guardado de verdad y
se acumula mes a mes.

## Instalación (una sola vez)

1. Instala Python 3.9 o superior desde https://www.python.org (en Windows marca la casilla
   **Add Python to PATH** durante la instalación).
2. Abre la consola (Windows: *Símbolo del sistema*; Mac: *Terminal*) y ejecuta:

       pip install pypdf

3. Guarda `archivo_nominas.py` en la carpeta donde quieras tener el archivo y sitúate en ella:

       cd C:\Nominas

## Estructura que crea

    Archivo/
        plantilla.json              los trabajadores dados de alta
        registro.csv                histórico de todo lo archivado (se abre con Excel)
        Álvaro Ruiz Ferrán/
            Contrato/
            Nóminas/
                Alvaro_Ruiz_Ferran_Enero_2025.pdf
            Documentos varios/
        _Sin identificar/           hojas que no ha sabido asignar

Para guardar en una unidad de red, añade `--base` a cualquier orden:

    python archivo_nominas.py --base "\\servidor\rrhh\Archivo" plantilla

## Órdenes

| Orden | Para qué sirve |
|---|---|
| `init` | Prepara la carpeta del archivo. |
| `alta "Nombre Apellidos" --dni 12345678Z --puesto Delantero` | Da de alta y crea sus tres subcarpetas. |
| `editar "Ruiz" --nombre "..." --dni ... --puesto ...` | Cambia sus datos; si cambia el nombre, renombra la carpeta. |
| `baja "Ruiz"` | Lo saca de la plantilla. La carpeta y sus documentos se conservan. |
| `plantilla` | Lista a todos con cuántas nóminas y si tienen contrato. |
| `procesar nominas_enero.pdf` | Trocea el PDF y reparte cada nómina. |
| `archivar contrato.pdf --trabajador "Ruiz" --tipo contrato` | Guarda un fichero suelto (`contrato`, `nomina` o `varios`). |
| `revisar --periodo "Enero 2025"` | Dice a quién le falta la nómina de ese mes. |

### Opciones útiles de `procesar`

- `--simular` — enseña dónde iría cada hoja **sin escribir nada**. Úsalo siempre la primera vez.
- `--periodo "Enero 2025"` — fuerza el periodo si el PDF no lo trae claro.
- `--patron num` — nombra `Nombre_2025-01.pdf` en vez de `Nombre_Enero_2025.pdf`.
- `--mover-origen` — mueve el PDF original a `_PDF procesados` al terminar.

## Rutina de cada mes

    python archivo_nominas.py procesar nominas_febrero.pdf --simular
    python archivo_nominas.py procesar nominas_febrero.pdf
    python archivo_nominas.py revisar --periodo "Febrero 2025"

Lo que caiga en `_Sin identificar` se coloca a mano:

    python archivo_nominas.py archivar "Archivo\_Sin identificar\nominas_febrero_pag5.pdf" ^
        --trabajador "López" --tipo nomina --periodo "Febrero 2025"

## Notas

- **Nunca sobrescribe.** Si el fichero ya existe y es idéntico, avisa de que ya estaba
  archivado; si es distinto, guarda una copia con sufijo `_(2)`.
- **Puedes repetir el mismo PDF** sin miedo a duplicar.
- Con **DNI** en la plantilla la identificación es exacta; sin él se hace por nombre y
  apellidos, así que escríbelos igual que aparecen en la nómina.
- Si el PDF es un **escaneo sin texto**, el script avisa página por página: en ese caso hace
  falta pasarle antes un OCR (por ejemplo `ocrmypdf`).
