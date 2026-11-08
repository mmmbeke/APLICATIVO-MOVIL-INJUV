-- =====================================================================
-- INJUV App Móvil - Extensión NO destructiva de la base de datos Neon
-- =====================================================================
-- * Idempotente: se puede ejecutar varias veces.
-- * No elimina ni renombra tablas/columnas de la plataforma web.
-- * Las tablas que ya existen en la web (usuarios, oportunidades, postulaciones,
--   noticias) solo reciben columnas nuevas con ADD COLUMN IF NOT EXISTS.
--   Los campos del spec móvil que ya existen en la web con otro nombre se
--   reutilizan desde el ORM (ver README):
--     oportunidades.categoria      -> tipo_de_voluntariado
--     oportunidades.cupos_totales  -> cupo_maximo
--     oportunidades.creado_en      -> created_at
--     postulaciones.fecha_postulacion -> created_at
--     noticias.bajada / cuerpo / imagen_url -> resumen / contenido / imagen_noticia
-- * usuarios.rol se mantiene como VARCHAR con los valores de la web
--   ('user' | 'organizacion' | 'admin'); la API los expone como
--   VOLUNTARIO | TUTOR | ADMIN.
--
-- Ejecutar con:  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/001_mobile_extension.sql
--            o:  python -m scripts.init_db
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1) usuarios (tabla de la web)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    apellido VARCHAR(100),
    rut VARCHAR(20),
    email VARCHAR(150),
    telefono VARCHAR(20),
    region VARCHAR(100),
    ciudad VARCHAR(100),
    comuna VARCHAR(100),
    sexo VARCHAR(100),
    fecha_nacimiento DATE,
    password_hash VARCHAR(255),
    rol VARCHAR(100),
    hora_voluntariado INTEGER,
    organizacion_afiliada INTEGER,
    foto_perfil VARCHAR(255),
    created_at TIMESTAMP
);

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS rol VARCHAR(100) DEFAULT 'user';
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS region_id INTEGER;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS comuna_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_usuarios_region_id ON usuarios(region_id);
CREATE INDEX IF NOT EXISTS idx_usuarios_email_lower ON usuarios(LOWER(email));

-- ---------------------------------------------------------------------
-- 2) organizaciones (tabla de la web) - solo se asegura su existencia
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizaciones (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100),
    id_usuario_org INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP
);
ALTER TABLE organizaciones ADD COLUMN IF NOT EXISTS id_usuario_admin INTEGER REFERENCES usuarios(id);

-- ---------------------------------------------------------------------
-- 3) oportunidades (tabla de la web) + columnas móviles
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS oportunidades (
    id SERIAL PRIMARY KEY,
    organizacion_id INTEGER,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    cupo_maximo INTEGER,
    fecha_inicio_voluntariado DATE,
    fecha_fin_voluntariado DATE,
    horas_voluntariado INTEGER,
    estado VARCHAR(20),
    region_opor VARCHAR(255),
    comuna_opor VARCHAR(255),
    tipo_de_voluntariado VARCHAR(100),
    created_at TIMESTAMP
);

ALTER TABLE oportunidades ADD COLUMN IF NOT EXISTS tutor_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
ALTER TABLE oportunidades ADD COLUMN IF NOT EXISTS requisitos TEXT;
ALTER TABLE oportunidades ADD COLUMN IF NOT EXISTS region_id INTEGER;
ALTER TABLE oportunidades ADD COLUMN IF NOT EXISTS comuna_id INTEGER;
ALTER TABLE oportunidades ADD COLUMN IF NOT EXISTS whatsapp_grupo_url VARCHAR(500);

CREATE INDEX IF NOT EXISTS idx_oportunidades_tutor ON oportunidades(tutor_id);
CREATE INDEX IF NOT EXISTS idx_oportunidades_region_comuna ON oportunidades(region_id, comuna_id);
CREATE INDEX IF NOT EXISTS idx_oportunidades_estado ON oportunidades(estado);

-- ---------------------------------------------------------------------
-- 4) oportunidad_fechas (nueva) - múltiples fechas por oportunidad
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS oportunidad_fechas (
    id SERIAL PRIMARY KEY,
    oportunidad_id INTEGER NOT NULL REFERENCES oportunidades(id) ON DELETE CASCADE,
    fecha_inicio TIMESTAMPTZ NOT NULL,
    fecha_fin TIMESTAMPTZ,
    CONSTRAINT ck_oportunidad_fechas_rango CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);
CREATE INDEX IF NOT EXISTS idx_oportunidad_fechas_oportunidad ON oportunidad_fechas(oportunidad_id, fecha_inicio);

-- ---------------------------------------------------------------------
-- 5) postulaciones (tabla de la web)
--    estado conserva los textos de la web:
--    'Pendiente de revisión' (PENDIENTE) | 'Seleccionado' | 'No seleccionado' (RECHAZADO)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS postulaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    oportunidad_id INTEGER REFERENCES oportunidades(id),
    estado VARCHAR(50),
    estado_confirmacion VARCHAR(20),
    asistencia_capacitacion VARCHAR(20),
    asistencia_actividad VARCHAR(20),
    tiene_certificado BOOLEAN,
    resena_org_publica BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_postulaciones_oportunidad ON postulaciones(oportunidad_id);
CREATE INDEX IF NOT EXISTS idx_postulaciones_usuario ON postulaciones(usuario_id);

-- ---------------------------------------------------------------------
-- 6) asistencias_tutor (nueva) - marcaje manual por el tutor, sin QR
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS asistencias_tutor (
    id SERIAL PRIMARY KEY,
    postulacion_id INTEGER NOT NULL UNIQUE REFERENCES postulaciones(id) ON DELETE CASCADE,
    tutor_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    asistio BOOLEAN NOT NULL,
    fecha_marcaje TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 7) notificaciones (nueva)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notificaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(40) NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    mensaje TEXT NOT NULL,
    oportunidad_id INTEGER REFERENCES oportunidades(id) ON DELETE SET NULL,
    leido BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_envio TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_notificaciones_tipo CHECK (
        tipo IN ('FUISTE_SELECCIONADO', 'ACTIVIDAD_CREADA', 'CERTIFICADO_CARGADO', 'MENSAJE_TUTOR')
    )
);
CREATE INDEX IF NOT EXISTS idx_notificaciones_usuario ON notificaciones(usuario_id, fecha_envio DESC);

-- ---------------------------------------------------------------------
-- 8) certificados (nueva)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS certificados (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    oportunidad_id INTEGER NOT NULL REFERENCES oportunidades(id) ON DELETE CASCADE,
    url_pdf TEXT NOT NULL,
    horas_acreditadas NUMERIC(6, 1) NOT NULL CHECK (horas_acreditadas >= 0),
    fecha_carga TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_certificados_usuario_oportunidad UNIQUE (usuario_id, oportunidad_id)
);
CREATE INDEX IF NOT EXISTS idx_certificados_usuario ON certificados(usuario_id);

-- ---------------------------------------------------------------------
-- 9) noticias (tabla de la web)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS noticias (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL,
    contenido TEXT NOT NULL,
    resumen VARCHAR(500),
    autor_id INTEGER REFERENCES usuarios(id),
    estado VARCHAR(20) DEFAULT 'activa',
    imagen_noticia VARCHAR(500),
    fecha_publicacion TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMIT;
