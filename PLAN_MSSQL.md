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

**Fase 0 — lo único que hace falta preguntar antes de codear:**
1. Instancia MSSQL: ¿cuál/dónde y con qué credenciales? (o ¿levanto una local para desarrollar?)
2. Driver: `pyodbc` (ODBC Driver 18) o `pymssql`.
3. **Multi-cliente:** si va a ser app web con clientes, ¿los datos se separan por cliente? Eso mete
   `cliente_id` en TODAS las tablas → **definir ANTES** de diseñar el esquema, no después. Es la
   pregunta más cara de contestar tarde.

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

- 2026-07-17: plan creado. **Nada codeado.** Próximo paso: **Fase 0** (las 3 preguntas de arriba).
