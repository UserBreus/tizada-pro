# PLAN — Migración a MSSQL (decidido 2026-07-17)

> Retomar con: **"seguimos con la migración a MSSQL"**. Este archivo existe para NO re-investigar
> nada: leelo y arrancá a codear. Actualizalo al final de cada sesión (§6 Estado).

## 1. CONTEXTO DEL PROYECTO (lo que yo asumí mal — NO volver a asumir)

- **TIZADA PRO es un proyecto GRANDE que va a ser una APP WEB usada por CLIENTES.** No es una
  herramienta local de un solo usuario. Que hoy corra con `py servidor.py` en localhost es el
  **estado actual**, NO el objetivo.
- **Se va a ASOCIAR a un sistema que ya usa MSSQL** → la base es **MSSQL**, decidido. No proponer
  SQLite/Postgres: compartir motor con el sistema con el que se integra es el requisito.
- Regla general: **NO inferir el alcance del proyecto de cómo se ejecuta hoy. Preguntar.**

## 2. POR QUÉ (el dolor real que esto resuelve)

Hoy NO hay base de datos: **860 archivos `.json` sueltos** en `datos/`, escritos a mano. Sin claves
primarias, sin UNIQUE, sin integridad referencial. Consecuencia concreta y ya diagnosticada: el
registro se guarda como **dict POR NOMBRE** → dos piezas homónimas colisionan y **se pierde una en
silencio**. De ahí salen los parches que rompen cosas (`_renumerar`, `dedupePorNombre`).

## 3. IDs QUE EXISTEN HOY (inventario real, verificado)

| id | ejemplo | identifica | problema |
|---|---|---|---|
| `pz_N` | `pz_0001` | pieza | string con prefijo; viola la regla |
| `v_N` | `v_0` | variable | string |
| `prod_<fecha>_<hash>` | `prod_20260623_155145_76bc` | producto/molde | string |
| `tl_n<timestamp>` | `tl_n1720…` | tela | string |
| **el NOMBRE crudo** | `jugador`, `dise-o` | **diseño** | **identidad por NOMBRE** (mismo mal que las piezas; `dise-o` = "diseño" slugificado) |

Basura acumulada por identificar-por-nombre: `juggador`, `hjn`, `fbfdhbfd`, `jtyjt` (pruebas que
quedaron como ids permanentes).

## 4. REGLAS DURAS DEL USUARIO (no negociables)

- **NADA A MEDIAS. Si una feature entra, entra COMPLETA** (regla explícita del usuario 2026-07-17:
  *"no me des nada por la mitad, debe de hacer todo"*). Concretamente para USUARIOS/ROLES: no
  alcanza con las tablas — va **todo el circuito**: esquema + endpoints + **PANTALLA de gestión**
  para crear/editar/borrar **usuarios**, **roles** y **permisos**, asignar roles a usuarios y
  permisos a roles, y que esos permisos **se apliquen de verdad** (backend Y frontend). Login y
  contraseñas **hasheadas** (nunca en claro). Si no entra completo en una sesión, se parte en
  entregas que **funcionen** cada una, y el estado queda en §6 — pero NO se entrega a medio hacer.

- **La pieza se identifica por ID NUMÉRICO, NUNCA por nombre.** Número pelado y secuencial
  (`1`, `2`, `3`…), arranca en 1. Sin prefijo `pz_`, sin ceros a la izquierda, sin strings.
- **Cada pieza NUEVA tiene su propio id.** No se reusa ni se recicla.
- **Cada pieza se registra TAMBIÉN con un id dentro del MOLDE del que vino** → 2 ids: el suyo
  (identidad global) y el que ocupa en su molde de origen.
- El **nombre** se sigue usando para TODO lo de hoy (mostrar, agrupar, mapear, renombrar). Solo
  deja de ser **identidad**.
- **NUNCA borrar ni sobrescribir datos del usuario** (`datos/`, `entrada/`) al probar/migrar.
  La migración se hace a una copia y se compara; el original no se toca hasta validar.

## 5. PLAN

**ALCANCE (aclarado por el usuario 2026-07-17):** **NO diseñar para el otro sistema.** La asociación
se ve DESPUÉS. Ahora: una base **propia, limpia y robusta**, bien normalizada, pensada para que
encima se puedan exponer **APIs** y compartir los datos. Motor: **MSSQL** (decidido). El esquema se
diseña por las necesidades de TIZADA PRO, sin condicionarlo a tablas ajenas.

**Fase 0 — RESPONDIDA por el usuario (2026-07-17). Ya se puede codear:**
1. **Instancia:** levantar una **MSSQL LOCAL para desarrollo**. (Preferir **Docker**
   `mcr.microsoft.com/mssql/server:2022-latest`; si no hay Docker, SQL Server **Developer Edition**.
   Guardar la cadena de conexión en **env** — `TIZADA_DB_*` —, NUNCA credenciales en el código.)
2. **Driver: `pyodbc`** (decidido por mí; el usuario no tenía preferencia). Es el estándar que
   Microsoft documenta/soporta y el que se usa en producción; `pymssql` está más relegado.
   Necesita **ODBC Driver 18 for SQL Server** instalado.
3. **Multi-cliente: NO.** "Los clientes van a hacer pedidos nomás" → **NO hay `cliente_id`/tenant**
   en el esquema. **PERO SÍ hay USUARIOS Y PERMISOS**: quién usa el sistema y qué puede hacer.
   → Agregar al esquema: `usuario`, `rol`, `permiso` (+ `usuario_rol`, `rol_permiso`), y auditoría
   mínima (`creado_por` / `creado_en` / `modificado_por` / `modificado_en`) en las tablas que se
   editan. Diseñar los permisos por ACCIÓN (ej. `pedido.crear`, `molde.editar`, `config.editar`),
   no por pantalla: las pantallas cambian, las acciones no. **NO inventar roles**: proponerlos y
   que el usuario los apruebe (candidatos observados en el sistema: **operario** = Pedidos, y
   **diseñador/admin** = Configuración — hoy la app ya separa esas dos vistas).

**Fase 1 — esquema.** Entidades del sistema (ver MAPA §4 "Modelo de datos"): producto/molde,
pieza, diseño, variable, grupo, tela, pedido, trabajo, fuente. Claves numéricas `IDENTITY`,
FKs reales, `UNIQUE` donde corresponda. El **diseño también** pasa a id numérico (hoy es el nombre).

**Fase 2 — capa de acceso.** Un módulo `db.py` que aísle el acceso; `servidor.py` y
`motor_pedido.py` NO deben hablar SQL directo. Hoy el patrón es `_cargar`/`_guardar` de JSON →
mantener esa firma y cambiar la implementación reduce el blast radius.

**Fase 3 — migración de datos.** Script que lee los 860 JSON y puebla MSSQL. Mapear los ids viejos
(`pz_0001` → `1`, etc.) y **guardar la equivalencia** para no romper referencias cruzadas
(variables, mapeos, editables apuntan a los ids viejos). Correr sobre COPIA y comparar.

**Fase 4 — verificación.** Generar la MISMA tizada antes y después y comparar **pixel a pixel**
(harness: `scratchpad/verif_tizada.py`). La LEY sigue siendo: arte = tizada.

## 6. ESTADO

- 2026-07-17: plan creado. **Nada codeado.** **Fase 0 YA RESPONDIDA** (MSSQL local en Docker, driver `pyodbc`, sin multi-cliente pero CON usuarios+permisos).
- **PRÓXIMO PASO: Fase 1 — el esquema.** Arrancar por ahí; incluir `usuario`/`rol`/`permiso` y proponer los roles al usuario antes de fijarlos.
