# Despliegue: Neon + Render + Vercel

Tres servicios, en este orden. La base de datos primero porque el backend la necesita,
y el backend antes que el frontend porque hay que saber su URL.

Calcula 30-40 minutos la primera vez.

---

## Antes de empezar: subir el repositorio

Vercel y Render despliegan desde un repositorio git. Ya está inicializado; solo falta
crearlo en GitHub y subirlo.

```bash
gh repo create archivo-nominas --private --source=. --push
```

O a mano en github.com, y luego:

```bash
git remote add origin https://github.com/TU_USUARIO/archivo-nominas.git
git push -u origin main
```

**Que el repositorio sea privado.** Aunque no contiene datos, describe cómo se
almacenan las nóminas del club.

---

## 1. Neon (base de datos)

1. Entra en <https://console.neon.tech> y crea un proyecto.
2. **Region: `Europe (Frankfurt)` o `Europe (Ireland)`.** Son datos personales de
   trabajadores: si salen de la UE necesitas cubrir la transferencia internacional.
   Esto no se puede cambiar después sin recrear el proyecto.
3. Nombre de la base de datos: `nominas`.
4. En **Connection Details**, copia la cadena marcada **Pooled connection**. Tiene esta
   pinta y es la que usa el backend:

       postgresql://usuario:clave@ep-algo-pooler.eu-central-1.aws.neon.tech/nominas?sslmode=require

   Usa la *pooled*, no la directa: Render abre y cierra conexiones y el pooler lo absorbe.

Las tablas se crean solas la primera vez que arranca el backend. No hay que ejecutar
ningún SQL.

> **Plan gratuito: 0,5 GB.** Los PDF se guardan dentro de la base de datos. Una hoja de
> nómina ocupa unos 100 KB, así que una plantilla de 30 personas gasta del orden de
> 35 MB al año. Da de sobra durante años, pero si algún día se queda corto, el cambio
> es mover los PDF a almacenamiento de objetos (R2 o S3) dejando en Neon solo los datos.

---

## 2. Render (backend)

1. Entra en <https://dashboard.render.com> → **New** → **Blueprint**.
2. Conecta el repositorio. Render lee `render.yaml` y propone el servicio
   `archivo-nominas-api` solo.
3. Te pedirá las variables marcadas como secretas. Rellena:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | La cadena *pooled* de Neon del paso 1. |
| `CLAVE_ARRANQUE` | Una frase larga que te inventes. Sirve **una sola vez**. |
| `ORIGENES_PERMITIDOS` | Déjala vacía de momento: la rellenas en el paso 3. |

`JWT_SECRETO` lo genera Render solo. No lo toques.

4. **Create**. El primer despliegue tarda unos 3 minutos.
5. Comprueba que vive, cambiando por tu URL:

```bash
curl https://archivo-nominas-api.onrender.com/api/salud
```

Debe responder `{"ok":true,"bd":"conectada"}`. Si dice `"sin conexión"`, la
`DATABASE_URL` está mal.

> **Plan gratuito: el servicio se duerme** tras 15 minutos sin uso, y la primera
> petición después tarda unos 30 segundos. La app lo avisa en pantalla en lugar de
> parecer rota. Para la rutina mensual del club es asumible; si molesta, el plan
> Starter (7 $/mes) lo mantiene despierto.

---

## 3. Vercel (frontend)

1. Entra en <https://vercel.com/new> e importa el mismo repositorio.
2. **Root Directory: `frontend`.** Esto es lo único que hay que cambiar; el resto lo
   detecta solo desde `vercel.json` (framework Vite, `npm run build`, salida `dist`).
3. En **Environment Variables**, añade:

| Variable | Valor |
|---|---|
| `VITE_API_URL` | `https://archivo-nominas-api.onrender.com` (tu URL de Render, **sin barra final**) |

4. **Deploy**. Tarda un minuto.
5. Copia la URL que te da Vercel, por ejemplo `https://archivo-nominas.vercel.app`.

### Cerrar el círculo (importante)

Vuelve a Render → tu servicio → **Environment** y pon ahora:

    ORIGENES_PERMITIDOS = https://archivo-nominas.vercel.app

Sin barra final y sin espacios. Guarda: Render reinicia el servicio solo.

**Si te saltas este paso**, el navegador bloqueará todas las peticiones por CORS y la
app parecerá colgada sin dar ningún error claro.

> Si quieres que también funcionen las *preview deployments* de Vercel (las de cada
> rama), añade su URL separada por comas. Piensa si te compensa: son URLs públicas
> apuntando a la misma base de datos real.

---

## 4. Crear el administrador y cerrar la puerta

1. Abre la URL de Vercel. Como no hay ningún usuario, sale la pantalla de
   **primer arranque**.
2. Rellena tu nombre, tu email, una contraseña de 10 caracteres o más, y la
   `CLAVE_ARRANQUE` que pusiste en Render.
3. Entras directamente como administrador.
4. **Vuelve a Render y deja `CLAVE_ARRANQUE` vacía.** Guarda.

Ese endpoint ya no se puede volver a usar (comprueba que no exista ningún usuario),
pero dejar la clave puesta no aporta nada y es una llave suelta.

A partir de aquí los usuarios se crean desde la pestaña **Usuarios**.

---

## 5. Comprobación final

Con el PDF de `ejemplo/nominas_ejemplo_enero.pdf`:

1. **Plantilla** → crea `Álvaro Ruiz Ferrán` con DNI `12345678Z`.
2. **Procesar** → sube el PDF → **Simular reparto**. Debe reconocerlo y agrupar las
   páginas 1-2, que son su nómina de dos hojas.
3. **Archivar de verdad** → vuelve a subir el mismo PDF: debe decir *ya estaban*, no
   duplicar.
4. **Archivo** → **Descargar ZIP**: dentro va la carpeta del trabajador con
   `Contrato`, `Nóminas` y `Documentos varios`.
5. **Registro** → están todas las operaciones con tu email y la hora.

Si los cinco pasos salen, el despliegue está bien.

---

## Qué hacer cuando algo falla

| Síntoma | Causa casi siempre |
|---|---|
| La app carga pero nada responde | `ORIGENES_PERMITIDOS` no coincide **exacto** con la URL de Vercel (sobra la barra final, o falta `https://`). |
| «No hay conexión con el servidor» | Render dormido. Espera 30 segundos y reintenta. Si persiste, mira los logs en Render. |
| `/api/salud` dice `sin conexión` | `DATABASE_URL` mal, o has usado la conexión directa de Neon en vez de la *pooled*. |
| «El alta inicial está desactivada» | `CLAVE_ARRANQUE` vacía en Render. Ponla, crea el admin, vacíala otra vez. |
| Sale la pantalla de login y no la de arranque | Ya existe un usuario. Si no sabes cuál, bórralo en Neon: `delete from usuarios;` |
| El PDF no identifica a nadie | El nombre de la ficha no coincide con el de la nómina, o el PDF es un escaneo sin texto (la app lo avisa: cuenta *sin texto*). |

Logs: en Render, pestaña **Logs** del servicio. En Vercel, pestaña **Deployments** →
el despliegue → **Runtime Logs**.

---

## Actualizar la app

Cualquier `git push` a `main` despliega solo en los dos servicios. No hay más pasos.

Una salvedad: el esquema de la base de datos se crea al arrancar, pero **no se migra**.
Si algún día cambian las tablas, hay que aplicar el cambio a mano en Neon o añadir
Alembic al backend.

---

## Antes de meter nóminas reales

Esto ya no es la herramienta local de antes: los datos salen del equipo del club.

- **Contrato de encargado del tratamiento** con Neon, Render y Vercel. Los tres lo
  ofrecen (DPA) y hay que firmarlos, no basta con aceptar los términos.
- **Registro de actividades de tratamiento**: hay que anotar esta app.
- **Copias de seguridad**: Neon guarda historial de 7 días en el plan gratuito. Para
  nóminas es poco. Descarga el ZIP completo cada cierto tiempo, o sube el plan.
- **Conservación**: la ley obliga a guardar nóminas 4 años, pero no a guardarlas para
  siempre. Decide cuándo se borran.
- **Altas y bajas**: cuando alguien deja el club, quítale la cuenta en **Usuarios** el
  mismo día. La pestaña **Registro** dice quién ha visto y archivado qué.

Las herramientas locales (`app_navegador/` y `script_escritorio/`) siguen funcionando y
no envían nada a ningún servidor. Si solo necesitas repartir el PDF de un mes, siguen
siendo la opción con menos exposición.
