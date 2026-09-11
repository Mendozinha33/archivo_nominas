# Archivo de nóminas — app web

Reparte un PDF con las nóminas de todo el equipo en el archivo de cada trabajador.

Para el uso diario, empieza por [`LEEME_PRIMERO.md`](LEEME_PRIMERO.md).
Para publicarla, por [`DESPLIEGUE.md`](DESPLIEGUE.md).
Este documento es solo para trabajar en el código.

## Cómo está montado

    frontend/   React + Vite          -> Vercel
    backend/    FastAPI + pypdf       -> Render
                                      -> Neon (PostgreSQL)

La lógica de identificación (`backend/app/nominas.py`) está portada tal cual del script
de escritorio: mismo criterio de DNI, nombres y detección de periodo, así que las tres
versiones reparten igual.

Los PDF se guardan en Neon como `bytea`. A escala de club son unas decenas de MB al año.

## Levantar el entorno local

Hacen falta Python 3.12+ y Node 20+.

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # en Linux o Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crea `backend/.env` (ya está en `.gitignore`):

```
DATABASE_URL=sqlite:///./local.db
JWT_SECRETO=cualquier-cosa-para-desarrollo
CLAVE_ARRANQUE=arranque-local
COOKIE_SEGURA=false
COOKIE_SAMESITE=lax
ORIGENES_PERMITIDOS=http://localhost:5173
```

SQLite vale para desarrollar. En producción siempre es PostgreSQL.

```bash
python -m uvicorn app.main:app --reload
```

API en <http://127.0.0.1:8000>, documentación interactiva en `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

En <http://localhost:5173>. Apunta al backend local a través de
`frontend/.env.development`.

Si Vite arranca en otro puerto porque el 5173 está ocupado, añade ese puerto a
`ORIGENES_PERMITIDOS` o la API rechazará las peticiones por CORS.

## Pruebas

```bash
cd backend
.venv/Scripts/python pruebas/prueba_api.py
```

Levanta la API entera contra una SQLite desechable y recorre el flujo completo con
`ejemplo/nominas_ejemplo_enero.pdf`: arranque, login, plantilla, troceo del PDF,
detección de duplicados, reasignación, ZIP, permisos por rol y auditoría. Sale con
código 1 si algo falla, así que sirve tal cual en CI.

## Autenticación

Token JWT firmado con HS256, contraseñas con Argon2. El token viaja en la cabecera
`Authorization: Bearer` porque el front (vercel.app) y el back (onrender.com) están en
dominios distintos y muchos navegadores bloquean la cookie de terceros. La cookie
`httpOnly` también se emite y el backend la acepta, así que si algún día sirves ambos
bajo el mismo dominio, funciona sin tocar nada.

Dos roles: `admin` (todo, incluido borrar documentos y gestionar usuarios) y `gestor`
(archiva y consulta). El primer administrador se crea una sola vez con `CLAVE_ARRANQUE`.

## Notas del modelo de datos

- `documentos` tiene un índice único sobre `(trabajador_id, sha256)` con
  `NULLS NOT DISTINCT`, que es lo que impide archivar dos veces el mismo contenido —
  también entre las hojas sin asignar.
- `trabajador_id` nulo es el equivalente a la carpeta `_Sin identificar`.
- Las bajas de trabajador no borran nada: marcan `activo = false` y conservan el
  historial, igual que el script de escritorio conservaba la carpeta.
- El esquema se crea con `create_all` al arrancar. No hay migraciones: si cambian las
  tablas en producción, hay que aplicarlo a mano o añadir Alembic.
