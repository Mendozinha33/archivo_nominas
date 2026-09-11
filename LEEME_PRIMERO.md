# Archivo de nóminas — proyecto completo

Herramientas para repartir un PDF con las nóminas de todo el equipo en la carpeta de cada
trabajador, con el nombre `trabajador_mes`.

Hay **tres versiones** que hacen lo mismo. Elige según el caso:

| | App de navegador | Script de escritorio | App web (nube) |
|---|---|---|---|
| Instalar algo | No | Sí (Python) | No |
| Dónde guarda | Descarga un ZIP | Carpetas en disco o red | Base de datos en Neon |
| Se acumula mes a mes | Solo durante la sesión | Sí, permanente | Sí, permanente |
| Varias personas a la vez | No | No | Sí, con usuarios y roles |
| Desde fuera del club | No | No | Sí, desde cualquier sitio |
| Quién ha tocado qué | No consta | `registro.csv` | Registro con usuario y hora |
| Los datos salen del equipo | No | No | **Sí** |
| Ideal para | Un mes suelto, revisar rápido | La rutina mensual en un solo equipo | Varias personas y archivo compartido |

Las dos primeras procesan todo en tu equipo y no envían nada a ningún servidor. La
tercera es la versión desplegada: más cómoda para trabajar en equipo, pero aloja
nóminas en servicios de terceros, con lo que eso implica en protección de datos
(ver el final de `DESPLIEGUE.md`).

---

## Contenido del paquete

    Archivo_de_nominas/
        LEEME_PRIMERO.md            este documento
        DESPLIEGUE.md               cómo publicar la app web (Neon + Render + Vercel)
        app_navegador/
            archivo_nominas.html    abrir con doble clic en Chrome, Edge o Firefox
        script_escritorio/
            archivo_nominas.py      el programa
            LEEME.md                instalación y todas las órdenes
        backend/                    API de la app web (FastAPI + pypdf), se despliega en Render
            app/                    código
            pruebas/prueba_api.py   prueba de extremo a extremo con el PDF de ejemplo
        frontend/                   interfaz de la app web (React + Vite), se despliega en Vercel
        render.yaml                 configuración del backend en Render
        ejemplo/
            nominas_ejemplo_enero.pdf   5 nóminas ficticias para practicar
            generar_ejemplo.py          por si quieres regenerarlo

---

## Estructura de carpetas que crean ambas versiones

    Álvaro Ruiz Ferrán/
        Contrato/
        Nóminas/
            Alvaro_Ruiz_Ferran_Enero_2025.pdf
            Alvaro_Ruiz_Ferran_Febrero_2025.pdf
        Documentos varios/
    _Sin identificar/          hojas que el programa no ha sabido asignar

---

## Cómo identifica a cada trabajador

1. **Por DNI/NIE**, si lo has puesto en su ficha. Es el método fiable: coincidencia exacta.
2. **Por nombre y apellidos**, si no hay DNI. Necesita que al menos dos palabras del nombre
   aparezcan en la hoja, así que escríbelo **igual que sale en la nómina**.

Lo que no encaja con nadie va a `_Sin identificar` en lugar de asignarse a quien no es.
El periodo se saca del texto de la hoja: reconoce «Enero 2025», «Periodo: 01/01/2025 a
31/01/2025», «01/2025» y formatos parecidos.

---

## Primeros pasos recomendados

1. Abre `app_navegador/archivo_nominas.html` y súbele `ejemplo/nominas_ejemplo_enero.pdf`
   para ver cómo funciona el reparto, sin tocar datos reales.
2. Prueba luego con **una** nómina real tuya y comprueba que detecta bien nombre y periodo.
3. Si algo falla, lo más probable es que el nombre de la ficha no coincida con el de la
   nómina, o que el PDF sea un escaneo sin texto (ver más abajo).
4. Cuando cuadre, instala el script siguiendo `script_escritorio/LEEME.md` y usa siempre
   `--simular` la primera vez de cada mes.

---

## Dos avisos importantes

**PDF escaneados.** Si las nóminas son imágenes sin capa de texto, ninguna de las dos
versiones puede leer los nombres. El script te avisa página por página. La solución es
pasarles antes un OCR, por ejemplo con `ocrmypdf`:

    pip install ocrmypdf
    ocrmypdf -l spa nominas_enero.pdf nominas_enero_ocr.pdf

**Protección de datos.** Las nóminas son datos personales de categoría sensible.

En las versiones **local y de navegador**, todo el procesado ocurre en tu equipo y no se
envía nada a ningún servidor; la carpeta del archivo debe estar en una ubicación con
acceso restringido y copia de seguridad, según la política del club. El `registro.csv`
que genera el script sirve como traza de qué se archivó y cuándo.

En la **app web**, los datos se alojan en Neon, Render y Vercel. Eso exige firmar los
contratos de encargado del tratamiento con los tres, anotar la app en el registro de
actividades y decidir plazos de conservación y copias. Está todo detallado al final de
`DESPLIEGUE.md`; léelo antes de subir la primera nómina real.

---

## Revisión mensual sugerida

    python archivo_nominas.py procesar nominas_marzo.pdf --simular
    python archivo_nominas.py procesar nominas_marzo.pdf
    python archivo_nominas.py revisar --periodo "Marzo 2025"

La última orden te dice a quién le falta la nómina de ese mes: es la comprobación que
conviene no saltarse antes de dar el mes por cerrado.
