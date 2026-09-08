/* ============================================================================
   TIZADA PRO — Esquema MSSQL
   ----------------------------------------------------------------------------
   REGLAS DURAS (ver PLAN_MSSQL.md §4 y MAPA_DEL_SISTEMA.md §8):
   · La PIEZA se identifica por ID NUMÉRICO (IDENTITY, arranca en 1). NUNCA por
     nombre. El nombre queda como dato de uso (mostrar/agrupar/mapear).
   · Cada pieza NUEVA tiene su propio id: IDENTITY no reusa ni recicla.
   · Cada pieza se registra TAMBIÉN con un id dentro del MOLDE del que vino
     -> pieza.id (identidad global) + pieza.id_en_molde (posición en su molde).
   · El DISEÑO también pasa a id numérico (hoy se identifica por su nombre
     slugificado: 'dise-o', 'jugador' -> mismo mal que las piezas).
   · Sin multi-cliente (los clientes solo hacen pedidos) PERO con usuarios,
     roles y permisos.

   Idempotente: se puede correr varias veces (crea sólo lo que falta).
   ============================================================================ */

/* ---------- 1. USUARIOS / ROLES / PERMISOS ---------- */

IF OBJECT_ID('dbo.usuario') IS NULL
CREATE TABLE dbo.usuario (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    usuario         NVARCHAR(64)  NOT NULL UNIQUE,   -- con el que entra
    nombre          NVARCHAR(120) NOT NULL,          -- para mostrar
    email           NVARCHAR(160) NULL,
    password_hash   VARBINARY(256) NOT NULL,         -- PBKDF2 (NUNCA texto plano)
    password_salt   VARBINARY(64)  NOT NULL,
    activo          BIT NOT NULL CONSTRAINT DF_usuario_activo DEFAULT 1,
    creado_en       DATETIME2 NOT NULL CONSTRAINT DF_usuario_creado DEFAULT SYSUTCDATETIME(),
    creado_por      INT NULL,
    modificado_en   DATETIME2 NULL,
    modificado_por  INT NULL,
    ultimo_acceso   DATETIME2 NULL
);

IF OBJECT_ID('dbo.rol') IS NULL
CREATE TABLE dbo.rol (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    clave       NVARCHAR(48)  NOT NULL UNIQUE,   -- 'operario', 'disenador', 'admin'
    nombre      NVARCHAR(120) NOT NULL,
    descripcion NVARCHAR(400) NULL,
    -- de sistema = no se puede borrar desde la pantalla (evita quedarse sin admin)
    es_sistema  BIT NOT NULL CONSTRAINT DF_rol_sistema DEFAULT 0,
    creado_en   DATETIME2 NOT NULL CONSTRAINT DF_rol_creado DEFAULT SYSUTCDATETIME()
);

/* Permisos POR ACCIÓN, no por pantalla: las pantallas cambian, las acciones no. */
IF OBJECT_ID('dbo.permiso') IS NULL
CREATE TABLE dbo.permiso (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    clave       NVARCHAR(64)  NOT NULL UNIQUE,   -- 'pedido.crear', 'molde.editar'
    modulo      NVARCHAR(32)  NOT NULL,          -- 'pedido' | 'molde' | 'config' | 'usuario'
    nombre      NVARCHAR(120) NOT NULL,
    descripcion NVARCHAR(400) NULL
);

IF OBJECT_ID('dbo.usuario_rol') IS NULL
CREATE TABLE dbo.usuario_rol (
    usuario_id INT NOT NULL FOREIGN KEY REFERENCES dbo.usuario(id) ON DELETE CASCADE,
    rol_id     INT NOT NULL FOREIGN KEY REFERENCES dbo.rol(id)     ON DELETE CASCADE,
    CONSTRAINT PK_usuario_rol PRIMARY KEY (usuario_id, rol_id)
);

IF OBJECT_ID('dbo.rol_permiso') IS NULL
CREATE TABLE dbo.rol_permiso (
    rol_id     INT NOT NULL FOREIGN KEY REFERENCES dbo.rol(id)     ON DELETE CASCADE,
    permiso_id INT NOT NULL FOREIGN KEY REFERENCES dbo.permiso(id) ON DELETE CASCADE,
    CONSTRAINT PK_rol_permiso PRIMARY KEY (rol_id, permiso_id)
);

/* ---------- 2. PRODUCTO (molde) ---------- */

IF OBJECT_ID('dbo.producto') IS NULL
CREATE TABLE dbo.producto (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    nombre         NVARCHAR(160) NOT NULL,
    -- id viejo del JSON ('prod_20260623_155145_76bc'): SOLO para migrar y poder
    -- rastrear el origen. No se usa como identidad.
    legacy_id      NVARCHAR(64) NULL UNIQUE,
    variante_guia  NVARCHAR(48) NULL,          -- talle guía
    activo         BIT NOT NULL CONSTRAINT DF_producto_activo DEFAULT 1,
    creado_en      DATETIME2 NOT NULL CONSTRAINT DF_producto_creado DEFAULT SYSUTCDATETIME(),
    creado_por     INT NULL FOREIGN KEY REFERENCES dbo.usuario(id),
    modificado_en  DATETIME2 NULL,
    modificado_por INT NULL FOREIGN KEY REFERENCES dbo.usuario(id)
);

/* Talles/variantes del molde (S, M, L…). Orden explícito: el alfabético miente. */
IF OBJECT_ID('dbo.talle') IS NULL
CREATE TABLE dbo.talle (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    producto_id INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id) ON DELETE CASCADE,
    nombre      NVARCHAR(48) NOT NULL,
    orden       INT NOT NULL CONSTRAINT DF_talle_orden DEFAULT 0,
    CONSTRAINT UQ_talle UNIQUE (producto_id, nombre)
);

/* ---------- 3. PIEZA (el corazón: id numérico, nombre sin rol de identidad) ---------- */

IF OBJECT_ID('dbo.pieza') IS NULL
CREATE TABLE dbo.pieza (
    -- IDENTIDAD GLOBAL. IDENTITY: secuencial, arranca en 1, no se reusa.
    id               INT IDENTITY(1,1) PRIMARY KEY,
    producto_id      INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id) ON DELETE CASCADE,
    -- id DENTRO del molde del que vino (regla del usuario 2026-07-17): 1..N por molde.
    id_en_molde      INT NOT NULL,
    -- El nombre es DATO, no identidad: puede repetirse y puede estar vacío.
    nombre           NVARCHAR(160) NULL,
    nombre_generico  NVARCHAR(160) NULL,   -- 'Manga 2' -> 'Manga' (para agrupar/mostrar)
    numero           INT NULL,             -- el 2 de 'Manga 2'
    legacy_id        NVARCHAR(32) NULL,    -- 'pz_0001' del JSON, sólo para migrar
    creado_en        DATETIME2 NOT NULL CONSTRAINT DF_pieza_creado DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_pieza_en_molde UNIQUE (producto_id, id_en_molde)
);
GO
/* Índice para buscar por nombre SIN que el nombre sea clave (puede repetirse). */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_pieza_nombre' AND object_id=OBJECT_ID('dbo.pieza'))
    CREATE INDEX IX_pieza_nombre ON dbo.pieza (producto_id, nombre_generico);
GO

/* Geometría/posición de la pieza EN CADA TALLE (era registro_producto.json).
   pieza_idx varía por talle -> por eso vive acá y NO en `pieza`. */
IF OBJECT_ID('dbo.pieza_talle') IS NULL
CREATE TABLE dbo.pieza_talle (
    pieza_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.pieza(id) ON DELETE CASCADE,
    talle_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.talle(id),
    mesa       INT NULL,
    pieza_idx  INT NULL,          -- índice dentro del .ai de ESE talle (varía por talle)
    ancla      NVARCHAR(32) NULL,
    bbox_mu    NVARCHAR(200) NULL, -- [x0,y0,x1,y1] serializado
    ancho_cm   DECIMAL(9,3) NULL,
    alto_cm    DECIMAL(9,3) NULL,
    CONSTRAINT PK_pieza_talle PRIMARY KEY (pieza_id, talle_id)
);

/* ---------- 4. DISEÑO (también con id numérico: hoy es el nombre slugificado) ---------- */

IF OBJECT_ID('dbo.diseno') IS NULL
CREATE TABLE dbo.diseno (
    id             INT IDENTITY(1,1) PRIMARY KEY,
    producto_id    INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id) ON DELETE CASCADE,
    nombre         NVARCHAR(160) NOT NULL,
    slug           NVARCHAR(160) NULL,   -- 'dise-o': SOLO compat de rutas viejas, NO es identidad
    es_principal   BIT NOT NULL CONSTRAINT DF_diseno_principal DEFAULT 0,
    arte_path      NVARCHAR(400) NULL,   -- el .ai/.pdf sigue en disco (binario), acá su ruta
    creado_en      DATETIME2 NOT NULL CONSTRAINT DF_diseno_creado DEFAULT SYSUTCDATETIME(),
    creado_por     INT NULL FOREIGN KEY REFERENCES dbo.usuario(id),
    CONSTRAINT UQ_diseno_nombre UNIQUE (producto_id, nombre)
);

/* ---------- 5. VARIABLES (grupos de piezas) ---------- */

IF OBJECT_ID('dbo.variable') IS NULL
CREATE TABLE dbo.variable (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    producto_id INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id) ON DELETE CASCADE,
    clave       NVARCHAR(48)  NOT NULL,   -- 'v_0' legacy; se conserva por compat de datos
    label       NVARCHAR(160) NOT NULL,
    acomodo     NVARCHAR(MAX) NULL,       -- JSON: posiciones del acomodo
    orden       NVARCHAR(MAX) NULL,       -- JSON: orden en cm
    CONSTRAINT UQ_variable UNIQUE (producto_id, clave)
);

/* Qué piezas entran en la variable. POR ID: acá muere el "un solo slot por nombre"
   (dedupePorNombre) que impedía elegir 2 piezas del mismo nombre genérico. */
IF OBJECT_ID('dbo.variable_pieza') IS NULL
CREATE TABLE dbo.variable_pieza (
    variable_id INT NOT NULL FOREIGN KEY REFERENCES dbo.variable(id) ON DELETE CASCADE,
    pieza_id    INT NOT NULL FOREIGN KEY REFERENCES dbo.pieza(id),
    CONSTRAINT PK_variable_pieza PRIMARY KEY (variable_id, pieza_id)
);

/* Vínculo "van juntas" (manga + su vivo): un grupo de piezas que entra/sale junto. */
IF OBJECT_ID('dbo.junta') IS NULL
CREATE TABLE dbo.junta (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    variable_id INT NOT NULL FOREIGN KEY REFERENCES dbo.variable(id) ON DELETE CASCADE,
    nombre      NVARCHAR(160) NULL
);
IF OBJECT_ID('dbo.junta_pieza') IS NULL
CREATE TABLE dbo.junta_pieza (
    junta_id INT NOT NULL FOREIGN KEY REFERENCES dbo.junta(id) ON DELETE CASCADE,
    pieza_id INT NOT NULL FOREIGN KEY REFERENCES dbo.pieza(id),
    CONSTRAINT PK_junta_pieza PRIMARY KEY (junta_id, pieza_id)
);

/* ---------- 6. TELAS ---------- */

IF OBJECT_ID('dbo.tela') IS NULL
CREATE TABLE dbo.tela (
    id        INT IDENTITY(1,1) PRIMARY KEY,
    nombre    NVARCHAR(120) NOT NULL UNIQUE,
    ancho_cm  DECIMAL(9,2) NOT NULL,
    legacy_id NVARCHAR(48) NULL
);
IF OBJECT_ID('dbo.grupo_tela') IS NULL
CREATE TABLE dbo.grupo_tela (
    id     INT IDENTITY(1,1) PRIMARY KEY,
    nombre NVARCHAR(120) NOT NULL
);
IF OBJECT_ID('dbo.grupo_tela_item') IS NULL
CREATE TABLE dbo.grupo_tela_item (
    grupo_id INT NOT NULL FOREIGN KEY REFERENCES dbo.grupo_tela(id) ON DELETE CASCADE,
    tela_id  INT NOT NULL FOREIGN KEY REFERENCES dbo.tela(id)       ON DELETE CASCADE,
    CONSTRAINT PK_grupo_tela_item PRIMARY KEY (grupo_id, tela_id)
);
/* Telas habilitadas para un molde */
IF OBJECT_ID('dbo.producto_tela') IS NULL
CREATE TABLE dbo.producto_tela (
    producto_id INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id) ON DELETE CASCADE,
    tela_id     INT NOT NULL FOREIGN KEY REFERENCES dbo.tela(id)     ON DELETE CASCADE,
    CONSTRAINT PK_producto_tela PRIMARY KEY (producto_id, tela_id)
);
/* Tela por PIEZA (por id, no por nombre) */
IF OBJECT_ID('dbo.pieza_tela') IS NULL
CREATE TABLE dbo.pieza_tela (
    pieza_id INT NOT NULL PRIMARY KEY FOREIGN KEY REFERENCES dbo.pieza(id) ON DELETE CASCADE,
    tela_id  INT NOT NULL FOREIGN KEY REFERENCES dbo.tela(id)
);

/* ---------- 7. MAPEO DEL ARTE (pieza -> mesa), POR VARIABLE ---------- */
/* REGLA DURA (MAPA §5): el mapeo se maneja POR VARIABLE, nunca por molde entero. */
IF OBJECT_ID('dbo.mapeo_arte') IS NULL
CREATE TABLE dbo.mapeo_arte (
    diseno_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.diseno(id) ON DELETE CASCADE,
    variable_id INT NOT NULL FOREIGN KEY REFERENCES dbo.variable(id),
    pieza_id    INT NOT NULL FOREIGN KEY REFERENCES dbo.pieza(id),
    mesa        INT NOT NULL,
    CONSTRAINT PK_mapeo_arte PRIMARY KEY (diseno_id, variable_id, pieza_id)
);

/* ---------- 8. EDITABLES (transform por objeto / variable / talle) ---------- */
IF OBJECT_ID('dbo.editable') IS NULL
CREATE TABLE dbo.editable (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    diseno_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.diseno(id) ON DELETE CASCADE,
    variable_id INT NULL FOREIGN KEY REFERENCES dbo.variable(id),
    objeto      NVARCHAR(160) NOT NULL,   -- nombre de la capa "Editable …"
    talle_id    INT NULL FOREIGN KEY REFERENCES dbo.talle(id),
    dx          DECIMAL(12,6) NOT NULL CONSTRAINT DF_ed_dx DEFAULT 0,
    dy          DECIMAL(12,6) NOT NULL CONSTRAINT DF_ed_dy DEFAULT 0,
    rot         DECIMAL(9,3)  NOT NULL CONSTRAINT DF_ed_rot DEFAULT 0,
    sx          DECIMAL(12,6) NOT NULL CONSTRAINT DF_ed_sx DEFAULT 1,   -- negativo = espejo
    sy          DECIMAL(12,6) NOT NULL CONSTRAINT DF_ed_sy DEFAULT 1,
    CONSTRAINT UQ_editable UNIQUE (diseno_id, variable_id, objeto, talle_id)
);

/* ---------- 9. PEDIDOS Y TRABAJOS ---------- */
IF OBJECT_ID('dbo.pedido') IS NULL
CREATE TABLE dbo.pedido (
    id           INT IDENTITY(1,1) PRIMARY KEY,
    producto_id  INT NOT NULL FOREIGN KEY REFERENCES dbo.producto(id),
    nombre       NVARCHAR(160) NULL,
    estado       NVARCHAR(24) NOT NULL CONSTRAINT DF_pedido_estado DEFAULT 'borrador',
    creado_en    DATETIME2 NOT NULL CONSTRAINT DF_pedido_creado DEFAULT SYSUTCDATETIME(),
    creado_por   INT NULL FOREIGN KEY REFERENCES dbo.usuario(id)
);
/* Cada fila de la planilla */
IF OBJECT_ID('dbo.pedido_fila') IS NULL
CREATE TABLE dbo.pedido_fila (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    pedido_id   INT NOT NULL FOREIGN KEY REFERENCES dbo.pedido(id) ON DELETE CASCADE,
    orden       INT NOT NULL,
    diseno_id   INT NULL FOREIGN KEY REFERENCES dbo.diseno(id),
    variable_id INT NULL FOREIGN KEY REFERENCES dbo.variable(id),
    talle_id    INT NULL FOREIGN KEY REFERENCES dbo.talle(id),
    cantidad    INT NOT NULL CONSTRAINT DF_fila_cant DEFAULT 1,
    -- los campos que se estampan (nombre, número, palabra…) son configurables por
    -- molde -> van como JSON: el esquema no puede tener una columna por campo.
    campos      NVARCHAR(MAX) NULL
);
IF OBJECT_ID('dbo.trabajo') IS NULL
CREATE TABLE dbo.trabajo (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    pedido_id   INT NULL FOREIGN KEY REFERENCES dbo.pedido(id),
    legacy_id   NVARCHAR(64) NULL UNIQUE,   -- carpeta trabajos/<tid>
    estado      NVARCHAR(24) NOT NULL CONSTRAINT DF_trabajo_estado DEFAULT 'en_curso',
    salida_path NVARCHAR(400) NULL,
    creado_en   DATETIME2 NOT NULL CONSTRAINT DF_trabajo_creado DEFAULT SYSUTCDATETIME(),
    creado_por  INT NULL FOREIGN KEY REFERENCES dbo.usuario(id)
);

/* ---------- 10. FUENTES ---------- */
IF OBJECT_ID('dbo.fuente') IS NULL
CREATE TABLE dbo.fuente (
    id       INT IDENTITY(1,1) PRIMARY KEY,
    archivo  NVARCHAR(240) NOT NULL UNIQUE,   -- el .ttf/.otf sigue en catalogo_fuentes/
    interno  NVARCHAR(240) NULL,              -- nombre PostScript (el que matchea el arte)
    hash     NVARCHAR(32)  NULL
);

/* ---------- 11. CONFIG (clave-valor por molde; lo que hoy es config_produccion.json) ---------- */
IF OBJECT_ID('dbo.config') IS NULL
CREATE TABLE dbo.config (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    producto_id INT NULL FOREIGN KEY REFERENCES dbo.producto(id) ON DELETE CASCADE,  -- NULL = global
    clave       NVARCHAR(64) NOT NULL,
    valor       NVARCHAR(MAX) NULL,   -- JSON
    CONSTRAINT UQ_config UNIQUE (producto_id, clave)
);

GO
/* 2026-08-19: el `ancla` real es un dict JSON (~120 chars) — NVARCHAR(32) lo truncaba. (ancla_ancha) */
IF COL_LENGTH('dbo.pieza_talle','ancla') IS NOT NULL AND COL_LENGTH('dbo.pieza_talle','ancla') <= 64
    ALTER TABLE dbo.pieza_talle ALTER COLUMN ancla NVARCHAR(MAX) NULL;
GO

GO
/* 2026-08-19: version del REGISTRO por producto — reemplaza al mtime del JSON como señal de
   invalidacion de caches (sin espejo en disco ya no hay mtime que mirar). */
IF COL_LENGTH('dbo.producto','registro_rev') IS NULL
    ALTER TABLE dbo.producto ADD registro_rev INT NOT NULL CONSTRAINT DF_producto_regrev DEFAULT 0;
GO

GO
/* ════════════════════════════════════════════════════════════════════════════════════════════
   2026-09-07 — ÍNDICES DE LAS CLAVES FORÁNEAS QUE SE RECORREN DENTRO DE UNA ESCRITURA.

   Sin estos, cada uno de estos SELECT/DELETE/UPDATE recorre la TABLA ENTERA **con los locks de
   escritura tomados**: cuanto más crece la base, más tiempo se queda esperando todo el resto.
   SQL Server indexa solo la PK y los UNIQUE — una FK NO trae índice, y en varias de estas tablas
   la columna que se busca es la SEGUNDA de una clave compuesta, o sea inservible para buscar.

   Todos van guardados por `IF NOT EXISTS` (igual que IX_pieza_nombre): correr esto de nuevo no
   hace nada. Se aplica solo al arrancar el servidor (`_poner_base_al_dia_al_arrancar`).
   ════════════════════════════════════════════════════════════════════════════════════════════ */

/* `guardar_registro` y `borrar_piezas_molde` borran por acá, y la FK de `talle` se comprueba
   contra esta tabla (es la más grande: ~1000 filas por molde). */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_pieza_talle_talle' AND object_id=OBJECT_ID('dbo.pieza_talle'))
    CREATE INDEX IX_pieza_talle_talle ON dbo.pieza_talle (talle_id);
GO
/* La PK es (variable_id, pieza_id): buscar por pieza no la puede usar. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_variable_pieza_pieza' AND object_id=OBJECT_ID('dbo.variable_pieza'))
    CREATE INDEX IX_variable_pieza_pieza ON dbo.variable_pieza (pieza_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_junta_pieza_pieza' AND object_id=OBJECT_ID('dbo.junta_pieza'))
    CREATE INDEX IX_junta_pieza_pieza ON dbo.junta_pieza (pieza_id);
GO
/* UQ_editable es (diseno_id, variable_id, objeto, talle_id): ni `variable_id` ni `talle_id`
   quedan primeros, así que ninguna de las dos búsquedas la aprovecha. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_editable_variable' AND object_id=OBJECT_ID('dbo.editable'))
    CREATE INDEX IX_editable_variable ON dbo.editable (variable_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_editable_talle' AND object_id=OBJECT_ID('dbo.editable'))
    CREATE INDEX IX_editable_talle ON dbo.editable (talle_id);
GO
/* Ídem: la PK de mapeo_arte es (diseno_id, variable_id, pieza_id). */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_mapeo_arte_variable' AND object_id=OBJECT_ID('dbo.mapeo_arte'))
    CREATE INDEX IX_mapeo_arte_variable ON dbo.mapeo_arte (variable_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_mapeo_arte_pieza' AND object_id=OBJECT_ID('dbo.mapeo_arte'))
    CREATE INDEX IX_mapeo_arte_pieza ON dbo.mapeo_arte (pieza_id);
GO
/* `pedido_fila` no tenía NINGÚN índice por estas tres, y al borrar un molde se le hace
   `UPDATE ... SET x=NULL WHERE x=?`: eso recorría la tabla entera tomando locks. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_pedido_fila_talle' AND object_id=OBJECT_ID('dbo.pedido_fila'))
    CREATE INDEX IX_pedido_fila_talle ON dbo.pedido_fila (talle_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_pedido_fila_variable' AND object_id=OBJECT_ID('dbo.pedido_fila'))
    CREATE INDEX IX_pedido_fila_variable ON dbo.pedido_fila (variable_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_pedido_fila_diseno' AND object_id=OBJECT_ID('dbo.pedido_fila'))
    CREATE INDEX IX_pedido_fila_diseno ON dbo.pedido_fila (diseno_id);
GO
/* Estas dos se recorren en CADA request (`usuario_actual` pide roles y permisos), y en las dos
   la columna que se busca es la segunda de la PK. */
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_usuario_rol_rol' AND object_id=OBJECT_ID('dbo.usuario_rol'))
    CREATE INDEX IX_usuario_rol_rol ON dbo.usuario_rol (rol_id);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_rol_permiso_permiso' AND object_id=OBJECT_ID('dbo.rol_permiso'))
    CREATE INDEX IX_rol_permiso_permiso ON dbo.rol_permiso (permiso_id);
GO
