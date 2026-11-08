# INJUV Mobile API (FastAPI)

Backend REST para la app móvil INJUV (Android/Kotlin). Comparte la base de datos Neon PostgreSQL
con la [plataforma web](https://github.com/mmmbeke/PLATAFORMA-WEB-INJUV) sin romper sus tablas.

Stack: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2.0, psycopg2 (SSL), PyJWT, Passlib/bcrypt + Werkzeug, Uvicorn.

## Estructura

```
main.py                  # app FastAPI, CORS, manejadores de error JSON
app/api/deps.py          # get_current_user, require_tutor, require_voluntario
app/api/v1/endpoints/    # auth, oportunidades, postulaciones, asistencia, notificaciones, certificados, noticias
app/core/                # config, seguridad (JWT/hash), roles y estados (traducción web <-> móvil)
app/db/                  # engine (pool_pre_ping, sslmode) y sesión
app/models/              # modelos SQLAlchemy (tablas web existentes + tablas móviles)
app/schemas/             # esquemas Pydantic de entrada/salida
app/services/            # lógica de negocio y notificaciones
sql/001_mobile_extension.sql  # migración idempotente y no destructiva
scripts/init_db.py       # aplica los .sql de sql/
```

## Compatibilidad con la plataforma web

La API no renombra ni elimina columnas web; traduce valores en la capa de modelos:

| Concepto | Valor en BD (web) | Valor en API móvil |
|---|---|---|
| `usuarios.rol` | `user` / `organizacion` / `admin` | `VOLUNTARIO` / `TUTOR` / `ADMIN` |
| `postulaciones.estado` | `Pendiente de revisión` / `Seleccionado` / `No seleccionado` | `PENDIENTE` / `SELECCIONADO` / `RECHAZADO` |
| `oportunidades.tipo_de_voluntariado` | | `categoria` |
| `oportunidades.cupo_maximo` | | `cupos_totales` |
| `noticias.resumen` / `contenido` | | `bajada` / `cuerpo` |

- Contraseñas: por defecto se generan hashes Werkzeug (`pbkdf2:sha256`) para que el login de la web
  (Flask `check_password_hash`) siga funcionando con usuarios registrados desde la app. Se verifican
  hashes Werkzeug y bcrypt. `PASSWORD_HASH_SCHEME=bcrypt` genera bcrypt (la web **no** podrá validarlos).
- El marcaje de asistencia también actualiza `postulaciones.asistencia_actividad` (`Sí`/`No`).

### Migración (`sql/001_mobile_extension.sql`)

Solo `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, índices y constraints. Se puede correr varias veces.

- Columnas nuevas: `usuarios.region_id`, `usuarios.comuna_id`, y columnas móviles en `oportunidades`
  (`region_id`, `comuna_id`, `requisitos`, `whatsapp_link`, `tutor_id`, ...).
- Tablas nuevas: `oportunidad_fechas`, `asistencias_tutor`, `notificaciones`, `certificados`.

## Ejecución local

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # completa DATABASE_URL y JWT_SECRET_KEY
python -m scripts.init_db     # aplica la migración (idempotente)
uvicorn main:app --reload
```

Swagger: http://localhost:8000/docs · ReDoc: `/redoc` · Health: `/health`

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | — | URL de Neon (`postgresql://...`) |
| `DB_SSLMODE` | `require` | Usa `disable` solo en local |
| `JWT_SECRET_KEY` | — | Secreto para firmar tokens |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | 7 días |
| `CORS_ORIGINS` | `*` | Lista separada por comas |
| `PASSWORD_HASH_SCHEME` | `werkzeug` | `werkzeug` o `bcrypt` |
| `NOTICIAS_IMAGEN_BASE_URL` | web en Render | Prefijo para `imagen_noticia` |
| `TIMEZONE` | `America/Santiago` | |

### Tests

Requieren un PostgreSQL local (`TEST_DATABASE_ADMIN_URL`, por defecto `postgresql://postgres:postgres@localhost:5432/postgres`).
Si existe la BD `injuv_web_template` (esquema web), se clona para probar la migración sobre tablas existentes.

```bash
pytest -q
```

## Despliegue en Render

- **Docker**: `docker build -t injuv-api . && docker run -p 8000:8000 --env-file .env injuv-api`
- **Blueprint**: `render.yaml` (raíz del repo) crea el servicio web (`healthCheckPath: /health`). Configura `DATABASE_URL`
  en el dashboard (no se versiona). Ejecuta `python -m scripts.init_db` una vez (Shell de Render) o
  habilita `preDeployCommand` en planes de pago.

## Endpoints (`/api/v1`)

Autenticación: `Authorization: Bearer <token>`. El JWT incluye `sub` (user_id) y `rol`.

| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/auth/login` | público | `{"identificador": "email o RUT", "password": "..."}` |
| POST | `/auth/token` | público | Form OAuth2 (botón *Authorize* de Swagger) |
| POST | `/auth/register` | público | Registro de voluntario |
| GET/PUT | `/auth/me` | autenticado | Ver / editar perfil |
| POST | `/oportunidades` | TUTOR/ADMIN | Crea oportunidad con `fechas[]`; notifica `ACTIVIDAD_CREADA` a voluntarios de la región |
| GET | `/oportunidades` | autenticado | Filtros `region_id`, `comuna_id`, `categoria`; orden por próxima fecha |
| GET | `/oportunidades/{id}` | autenticado | `whatsapp_link` solo para seleccionados o gestores |
| POST | `/postulaciones/{oportunidad_id}` | VOLUNTARIO | Postular |
| GET | `/postulaciones/mias` | VOLUNTARIO | Mis postulaciones |
| GET | `/postulaciones/oportunidad/{id}` | TUTOR/ADMIN | Postulantes |
| PUT | `/postulaciones/{id}/estado` | TUTOR/ADMIN | `SELECCIONADO` notifica `FUISTE_SELECCIONADO` (valida cupos) |
| POST | `/asistencia/marcar-masivo` | TUTOR/ADMIN | Marcaje manual (sin QR) |
| GET | `/notificaciones` | autenticado | `?solo_no_leidas=true` |
| PATCH | `/notificaciones/{id}/leer` | autenticado | |
| POST | `/notificaciones/mensaje-masivo` | TUTOR/ADMIN | A los seleccionados de una oportunidad |
| POST | `/certificados/cargar` | TUTOR/ADMIN | Crea/reemplaza; notifica `CERTIFICADO_CARGADO` |
| GET | `/certificados` | autenticado | Certificados propios + total de horas |
| GET | `/noticias` | autenticado | Noticias publicadas de la web |

Errores: siempre JSON `{"detail": "...", ...}` (422 incluye `errors` de validación).

> Push: `app/services/notificaciones.py::enviar_push` es un hook (hoy solo registra en log).
> Las notificaciones quedan persistidas en BD; para push real integrar Firebase Cloud Messaging ahí.
