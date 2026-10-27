# TIZADA PRO — guía para una IA que construye el sistema de ventas

> **Para quién es:** un asistente de IA (o un programador) que tiene que **construir desde cero** el
> sistema externo (ventas / ERP / tienda) que le manda pedidos a TIZADA PRO. Está escrito para que se
> pueda seguir paso a paso sin saber nada de indumentaria. Cuando algo no esté acá, la referencia
> exacta es [`API.md`](API.md) (cada ruta) y [`FORMATO_PEDIDO.md`](FORMATO_PEDIDO.md) (cada campo).
> Las respuestas reales de cada ruta están en [`respuestas/`](respuestas/) y los esquemas JSON en
> [`esquemas/`](esquemas/).
>
> 🔔 **Antes de tocar su sistema por una actualización, leé [`CAMBIOS.md`](CAMBIOS.md):** dice si hay que cambiar algo y qué nombre cambió (antes → ahora).
---

## 0. Reglas que no se negocian

1. **Se elige la VARIABLE, no el molde.** Lo que el cliente compra es una *variable* (`clave` `v_…`).
2. **Telas por `id`**, **piezas por nombre genérico** («Cuello», nunca «Cuello 2»), **talles tal cual** los publica la prenda.
3. **Medidas en METROS** (1.5 = un metro y medio). Nunca centímetros.
4. **Revisar antes de mandar:** `POST /pedidos/validar` cada vez que el vendedor cambia algo.
5. **El arte de una prenda a medida se dibuja sobre la plantilla de ESA medida.** Si cambia la medida, hay que pedir la plantilla de nuevo y rehacer el arte.
6. **Nunca inventar datos del catálogo:** formas, telas, talles, columnas y opciones salen de la API.
7. **La llave (`X-Api-Key`) vive en el servidor** del sistema externo, nunca en el navegador.
8. **Creer el aviso (webhook) sólo si la firma coincide.**

---

## 1. El dominio en 2 minutos

| Palabra del taller | Qué es, para un programador |
|---|---|
| **Sublimación** | El diseño se imprime en papel y se pasa a la tela con calor. TIZADA prepara lo que se imprime. |
| **Molde** | El «producto base» (Camiseta de fútbol, Bandera). Tiene piezas y talles. Código `prod_…`. |
| **Pieza** | Un pedazo de tela que se corta y se cose (Frente, Espalda, Manga). |
| **Variable** | **Lo que se vende**: un conjunto de piezas de un molde («Cuello redondo», «Cuello V»). Clave `v_…`. |
| **Talle** | Tamaño (S, M, L…). Cada pieza existe en cada talle. |
| **Molde a medida** | Una prenda de **una sola pieza sin talles** (bandera, banderín, círculo). El cliente dice cuánto mide. |
| **Diseño** | Un dibujo con nombre (JUGADOR, GOLERO). Un pedido puede tener varios; cada uno lleva sus variables. |
| **Arte** | El archivo del diseño (.ai / .pdf), dibujado sobre la **plantilla** que da TIZADA. |
| **Plantilla** | La base vacía para el diseñador: una mesa por pieza, con su nombre. |
| **Planilla** | La lista de prendas del pedido: una fila por prenda (talle, nombre, número, cantidad…). |
| **Tela** | El material. Tiene un ancho; las piezas tienen que entrar. Va por `id`. |
| **Tizada / mesa** | El resultado: las piezas acomodadas en la tela, listas para imprimir. Llega **un PDF por mesa** + la **ficha técnica**. |
| **Editable** | Un objeto del arte (escudo, logo) que puede no sublimarse (va en TPU, bordado o DTF). |

---

## 2. Arquitectura

```
[Sistema de ventas]  ── HTTPS + X-Api-Key ──►  [TIZADA PRO /api/externo/v1]
     │  catálogo (GET)                                │
     │  validar / mandar pedido (.zip)                ├─► robot: lee el arte, arma la tizada
     │  pedir plantillas (JSON)                       │
     ◄── estado (GET) o AVISO firmado (POST a su URL) ┘
     ◄── PDF (GET …/archivos/{nombre} o Google Drive)
```

- Base: `https://<servidor>/api/externo/v1` (prueba: `http://127.0.0.1:8050/api/externo/v1`).
- Encabezado en todo: `X-Api-Key: tzp_…` (salvo `GET /formato` y `GET /alarmas`).
- Todo UTF-8; respuestas JSON salvo los PDF.

---

## 3. Lo que el sistema externo tiene que guardar (modelo de datos sugerido)

| Tabla | Campos mínimos | De dónde sale |
|---|---|---|
| `catalogo_version` | `version` | `GET /variables` → `version` (refrescar todo cuando cambia) |
| `variable` | `clave`, `nombre`, `molde`, `molde_nombre`, `piezas[]`, `planilla`, `a_medida` (JSON o null) | `GET /variables` |
| `molde` | `codigo`, `talles[]`, `planilla.columnas[]`, `planilla.columna_talle`, `opciones_de_pieza`, `telas.todas[]`, `telas.por_pieza{}` | `GET /moldes/{codigo}` |
| `tela` | `id`, `nombre`, `ancho_mesa_cm`, `usable` | `GET /telas` |
| `tipografia` | `nombre` | `GET /tipografias` |
| `articulo` (del sistema externo) | su SKU + **`variable_clave`** | lo enlaza un humano una vez |
| `pedido` | `referencia` (única), `estado`, `etapa`, `alarmas`, `resultado` | lo que se manda / lo que vuelve |
| `archivo` | `nombre`, `tipo`, `sha256`, `descarga`, `drive_id`, `enlace` | `resultado.archivos[]` |

---

## 4. Los flujos, en orden

### 4.1 Sincronizar el catálogo (al arrancar y cuando cambie `version`)
1. `GET /variables` → guardar cada variable (y su bloque `a_medida` si lo tiene).
2. Por cada `molde` distinto: `GET /moldes/{codigo}` → talles, planilla, opciones, telas.
3. `GET /telas`, `GET /tipografias`, `GET /perfiles`, `GET /alarmas` (para mostrar mensajes).
   Todo lo que el operario puede hacer en el pedido de TIZADA también va en el JSON (MAPA 712): `moldes[].ajustes`
   (mover/rotar/escalar/espejar un editable), `moldes[].colores` (CMYK), `moldes[].mapeo_arte` (mesa del arte → pieza),
   `moldes[].reemplazos` / `moldes[].tipografia_por_campo` (tipografías), `editables: "no_imprimir"` y
   `planilla[].piezas` (Repo). Ver FORMATO_PEDIDO §3.
4. Siluetas para la pantalla: `GET /variables/{clave}/foto` (404 con `sin_calcular` → mostrar un ícono).

### 4.2 Armar un pedido (pantalla del vendedor)
1. Crear la `referencia` (letras, números, `.`, `-`, `_`; hasta 64; única).
2. Agregar **diseños** (nombre único: JUGADOR, GOLERO…).
3. A cada diseño, agregar **variables** (una por prenda). Todas las variables del pedido tienen que tener la **misma `planilla`** (si no: `planillas-distintas`).
4. Por variable: **tela principal** (id, sólo de `telas.todas` del molde y `usable`), excepciones por pieza (`telas_por_pieza`), piezas que no se hacen (`piezas_apagadas`), qué editable no se sublima (`editables`).
5. Si la variable es **a medida** → seguir §5 (medida, forma, terminación, tiras).
6. **Planilla:** una fila por prenda, con las columnas de `planilla.columnas` (ver §6).
7. **Arte:** pedir la plantilla (§4.3), que el diseñador dibuje, adjuntar el .ai/.pdf.
8. `POST /pedidos/validar` (JSON solo, en vivo) → mostrar alarmas → corregir.
9. Armar el `.zip` y `POST /pedidos` → 202 (en cola) o 422 (alarmas).

### 4.3 Plantilla para el diseñador
1. `POST /plantillas` con `{referencia, disenos: [{nombre, variables: [...]}], talles: {modo}, escala}`.
   Una variable **a medida** va con TODO lo que define su forma (la plantilla sale a esa medida, con su margen y su costura):
   `{"variable": "v_…", "forma": "triangulo", "orientacion": "abajo", "terminacion": "dobladillo", "medida": {"ancho_m": 1.0, "alto_m": 0.6}}`.
2. `GET /plantillas/{referencia}` hasta `listo` → `archivos[]`: por diseño un `illustrator` (.json), un `corel` (.json) y una `guia` (.ai).
3. En la PC del diseñador, la página del sistema externo hace `POST http://127.0.0.1:47850/plantilla` (Illustrator) o `:47851` (CorelDRAW) con el contenido del .json tal cual. Para saber si el conector está: `GET http://127.0.0.1:47850/estado`. Sin conector: bajar la `guia` .ai. Instaladores: `GET /conectores`.
   **Código listo:** [`codigo/crear_en_programa.js`](codigo/crear_en_programa.js) (`crearEnPrograma`) hace todo eso como el botón de TIZADA; el estado trae `conectores.{illustrator|corel}` con a dónde mandar (`crear`), la `version` que corresponde y el `instalador`. La llave queda en su servidor ([`codigo/cliente.mjs`](codigo/cliente.mjs): `esperarPlantilla`, `archivoPlantilla`).

### 4.4 Seguir y recibir
1. `GET /pedidos/{ref}` cada 5–10 s hasta `listo` / `rechazado` / `error` / `cancelado`. Mostrar `etapa` (si trae `(NN %)`, es el avance).
2. O recibir el **aviso**: `POST` a su URL con el mismo JSON. Validar firma:
   `HMAC_SHA256(clave = sha256_hex(llave), mensaje = cuerpo crudo)` en hex == `X-Tizada-Firma`. Contestar 2xx.
3. Con `listo`: guardar `resultado.archivos[]` y bajar cada PDF de `descarga` (verificar `sha256`) o usar `drive_id`/`enlace`. **La copia del servidor se borra a los 30 días.**
4. Cancelar: `DELETE /pedidos/{ref}` (409 si ya está listo).

---

## 5. Prendas a medida (banderas) — lo más importante

Una variable es a medida si trae `a_medida` (no null). Ese bloque dice qué se puede pedir:
`formas`, `forma_por_defecto`, `orientaciones_triangulo`, `orientacion_por_defecto`, `terminaciones`,
`terminacion_por_defecto`, `margen_cm`, `overlock_cm`, `medida_minima_m` (0.05), `medida_maxima_m` (50),
`telas[]` (con `entra_hasta_cm`), `largo_maximo_cm`, `gira`, `tiras` (`lleva_por_defecto`, `lados_por_defecto`,
`lados_por_forma`, `maximo_por_lado`, `grosor_mm`, `color`).

### 5.1 La medida
- La medida que se manda es la **del diseño** (lo que se ve). TIZADA le agrega el margen para coser y eso es el **total** impreso. Ejemplo: 3,00 × 1,50 con 3 cm de margen → total 3,06 × 1,56.
- Nunca restar ni sumar el margen del lado del sistema externo: mandar lo que pide el cliente.

### 5.2 Las 3 formas

| Forma | Qué pedir | JSON |
|---|---|---|
| `rectangulo` (por defecto) | ancho y alto | `"medida": {"ancho_m": 1.5, "alto_m": 0.9}` |
| `circulo` | **sólo** el diámetro | `"forma": "circulo", "medida": {"diametro_m": 1.2}` |
| `triangulo` | ancho y alto **de la caja** + hacia dónde va la punta | `"forma": "triangulo", "orientacion": "abajo", "medida": {"ancho_m": 1.0, "alto_m": 0.6}` |

### 5.3 El triángulo, sin ambigüedad
- Siempre isósceles: los dos lados largos iguales, la punta centrada.
- Imaginar la **caja** que lo encierra **con la bandera ya colgada como se va a ver**:
  **`ancho_m` = la caja de izquierda a derecha · `alto_m` = la caja de arriba a abajo.**
- `orientacion` = hacia dónde mira la punta:

| `orientacion` | La base está… | `ancho_m` es… | `alto_m` es… |
|---|---|---|---|
| `abajo` (por defecto, banderín) | arriba | el largo de la base | de la base a la punta |
| `arriba` | abajo | el largo de la base | de la base a la punta |
| `izq` | a la derecha (vertical) | de la base a la punta | **el largo de la base** |
| `der` | a la izquierda (vertical) | de la base a la punta | **el largo de la base** |

- Ejemplo: «base de 1 m, 60 cm hasta la punta»:
  - punta abajo → `{"ancho_m": 1.0, "alto_m": 0.6}`;
  - punta a la derecha → `{"ancho_m": 0.6, "alto_m": 1.0}`.
- Se aceptan con o sin tilde y `izquierda`/`derecha`.

### 5.4 Terminación del borde (`terminacion`)
| Valor | Qué es | Efecto |
|---|---|---|
| `dobladillo` | se dobla el margen y se cose; esquinas/puntas recortadas | usa `margen_cm` |
| `overlock` | costura sobre el borde | usa `overlock_cm` (parejo, chico) |
| `sin` | no se cose el borde | la pieza es exactamente el diseño; las tiras no se marcan (sólo van en la ficha) |

Si no viene: `terminacion_por_defecto`. En círculo y triángulo el margen es parejo (el mayor de `margen_cm`).

### 5.5 Tiras (`tiras`)
- Cintas que se cosen para atar la bandera; TIZADA imprime marcas **negras con contorno blanco** donde van. **El color no se elige** (mandar `color_cmyk` → `tiras-invalidas`). El grosor es el del molde.
- Cuántas **por lado, contando las 2 puntas** (5 = una en cada esquina + 3 en el medio, parejas · 1 = una en el centro · 0 = sin tiras).
- Lados según la forma: rectángulo `arriba`/`abajo`/`izq`/`der` (0–50) · triángulo `base`/`laterales` · círculo `alrededor` (0–200).
- Formatos válidos: `{"lleva": true, "lados": {"arriba": 5, "abajo": 5}}`, o lados sueltos `{"arriba": 5}`, o `true`/`false` (las del molde / ninguna). `"marcar": false` = no se imprimen pero salen en la ficha.
- Con dobladillo la marca de la esquina no se imprime (el corte ya la marca) pero cuenta. Un lado sin margen no puede llevar tiras (`tiras-sin-margen`).

### 5.6 Tela: ¿entra?
- El total tiene que entrar en la tela (`entra_hasta_cm`) y en el largo máximo. Si no: `tela-no-entra` (dice cuánto se pasa y lo máximo).
- **`POST /a_medida/calcular`** (no guarda nada) responde: `total_cm`, `telas[]` con `entra`/`motivo`, `entra_en_alguna`, `tiras` (por lado, cada cuánto, total), la `ficha`. Usarla en vivo mientras el cliente escribe.
  ```json
  POST /a_medida/calcular
  { "variable": "v_…", "forma": "triangulo", "orientacion": "abajo", "ancho_m": 1.0, "alto_m": 0.6,
    "tela": "44", "tiras": { "base": 3 } }
  ```

### 5.7 El orden de las preguntas al cliente (y por qué)

| # | Preguntar | Por qué en este orden | ¿Se puede automatizar? |
|---|---|---|---|
| 1 | Producto (variable a medida) | De su `a_medida` sale todo lo demás | No (lo elige el cliente) |
| 2 | Forma | Define qué medidas pedir | Sí, si el producto ya es de una forma (banderín → triángulo) |
| 3 | Punta (sólo triángulo) | Define cuál es el ancho y cuál el alto | Sí: `abajo` |
| 4 | Medida del diseño (m) | Base de todo el cálculo | No |
| 5 | Terminación | Cambia cuánta tela lleva → decide la tela | Sí: `terminacion_por_defecto` |
| 6 | Tela | Tiene que entrar el total | Sí: la primera con `entra: true` de `calcular` |
| 7 | Tiras | Dependen de la forma (lados) y de la terminación (sin borde no se marcan) | Sí: `lleva_por_defecto` / `lados_por_defecto` |
| 8 | Arte | Tiene que ser de ESTA medida | Pedir la plantilla con la medida (§4.3) |

### 5.8 La fila de la planilla
Una prenda a medida **no lleva talle** en la fila. Sólo `diseno` (si hay varios), `cantidad` y lo que tenga la planilla.

---

## 6. La planilla (`planilla[]`)
- Claves = los `id` de `planilla.columnas` del molde. Valores siempre como texto (`"07"` conserva el cero).
- Talle: en la columna que dice `planilla.columna_talle` (cada molde lee la suya; `null` = sin talles). El valor tal cual está en `talles[]`.
- Columnas con `opciones` (p. ej. manga): un valor de `opciones`, y la prenda tiene que **tenerlo** (`opciones_de_pieza`). Varias: `"Corta + Larga"`.
- `cantidad`: entero ≥ 1 (vacía = 1). `obligatoria: true` → no puede ir vacía.
- `diseno`: obligatoria si el pedido trae más de un diseño.

---

## 7. El paquete que se manda

```
<referencia>.zip
├── pedido.json                    (en la raíz)
├── artes/<archivo>.ai | .pdf      (las rutas que nombra pedido.json)
└── tipografias/<archivo>.ttf      (sólo las que no estén en GET /tipografias)
```
Límites: 600 MB, 400 archivos. `POST /pedidos` como multipart `paquete` o cuerpo `application/zip`.

### 7.1 `pedido.json` de ejemplo: un banderín triangular
```json
{
  "formato": "tizadapro.pedido/1",
  "referencia": "OV-2026-00123",
  "pedido_externo": { "id": 48211, "vendedor": "mgarcia" },
  "cliente": "Club Ejemplo",
  "disenos": [
    { "nombre": "BANDERIN",
      "moldes": [
        { "variable": "v_cb7fd79", "arte": "artes/banderin.ai", "tela": "44",
          "forma": "triangulo", "orientacion": "abajo",
          "medida": { "ancho_m": 1.0, "alto_m": 0.6 },
          "terminacion": "dobladillo",
          "tiras": { "base": 3 } } ] }
  ],
  "planilla": [
    { "cantidad": 2 }
  ]
}
```
- La fila no lleva talle (prenda a medida). `diseno` sólo hace falta si el pedido trae más de un diseño.
- Una camiseta y una bandera **no van en el mismo pedido** si sus variables tienen distinta `planilla` (`planillas-distintas`): mandar dos pedidos.
- Las claves, telas y columnas son ilustrativas: usar las del catálogo real. Un pedido de camisetas revisado contra el catálogo: [`pedido_ejemplo.json`](pedido_ejemplo.json).

### 7.2 Opcionales útiles
- `opciones.si_falta_tipografia`: `rechazar` (defecto) | `predeterminada`.
- `opciones.si_texto_no_entra`: `achicar` (defecto, avisa) | `rechazar`.
- `opciones.si_piezas_en_blanco`: `rechazar` (defecto) | `seguir`.
- `mesas.modo`: `normal` | `una_por_fila` | `por_talles` (`grupos`) | `talles_separados` (misma mesa, cada talle aparte con línea punteada; `grupos` opcional). Con `normal` la cantidad son PRENDAS (se repite la fila y se mezcla todo); con `una_por_fila` la fila sale UNA vez en su mesa y la cantidad son COPIAS: las copias se acomodan juntas en una mesa del largo máximo y, si alcanza para llenarla, esa mesa sale UNA vez marcada ×N; todo lo que no llena una mesa (de cualquier fila y talle) va JUNTO como en `normal`, ×1 (19 con lugar para 5 → archivo de 5 ×3 + las 4 que sobran con el resto; MAPA 725); vuelven `fila`, `copias` (veces que se imprime ese archivo) y `por_mesa` (unidades que trae) en cada archivo; unidades = `por_mesa × copias`. Detalle: `COMO_USAR_CADA_OPCION.md` §1.
- `mesas.separar_disenos` (opcional, booleano): sin él el MISMO MOLDE se mezcla aunque cambie el diseño — también con `una_por_fila`, en mesas mezcladas que se repiten (`fila: null` + `filas: [{fila, por_mesa}]` en el archivo); con `true` cada diseño va en sus propias mesas y el archivo trae `diseno` (MAPA 717).
- `mesas.largo_max_m` (opcional, metros, 0,10 a 50): el largo máximo de cada mesa del pedido; sin él rige el del nesting del molde. Mal → `largo-mesa-invalido`; un molde a medida más largo que eso → `tela-no-entra` (MAPA 716).
- `reemplazar: true` para rehacer una referencia ya `listo`.
- `aviso_url` (mismo sitio que la URL configurada en TIZADA).

---

## 8. Alarmas: qué hacer con cada una
Forma: `{codigo, frena, etapa, mensaje, donde: {campo, fila}}`. `frena: true` rechaza; `false` avisa. Etapas: `datos` (en el acto), `arte` y `tizada` (por el estado o el aviso). Catálogo vivo: `GET /alarmas`.

| Grupo | Códigos | Acción del sistema externo |
|---|---|---|
| Catálogo | `variable-desconocida`, `variable-ambigua`, `molde-no-disponible`, `molde-archivado`, `planillas-distintas` | Re-sincronizar el catálogo; mandar la `clave` (`molde-archivado`: esa prenda ya no se ofrece) |
| Tela | `tela-falta`, `tela-desconocida`, `tela-no-usable`, `tela-no-permitida`, `tela-no-entra` | Ofrecer sólo telas del molde, usables y donde entra (`calcular`) |
| Planilla | `talle-inexistente`, `opcion-inexistente`, `opcion-sin-piezas`, `columna-obligatoria-vacia`, `cantidad-invalida`, `fila-diseno-desconocido` | Validar los campos contra `GET /moldes/{codigo}` |
| A medida | `medida-falta`, `medida-invalida`, `forma-invalida`, `terminacion-invalida`, `tiras-invalidas`, `tiras-sin-margen`, `tiras-no-a-medida` | Seguir §5; probar con `calcular` |
| Arte | `arte-falta`, `arte-sin-mesas-de-pieza`, `arte-pieza-sin-mesa`, `arte-texto-vivo`, `arte-otra-medida`, `arte-mesa-vacia`, `editable-desconocido` | Mostrar al diseñador; rehacer sobre la plantilla correcta |
| Tipografías | `tipografia-falta`, `tipografia-invalida` | Adjuntar el .ttf/.otf o usar `tipografia_por_campo` |
| Avisos | `texto-se-achica`, `piezas-en-blanco` (con `seguir`), `tipografia-reemplazada` | Mostrar, no frenar |
| Referencia | `referencia-invalida`, `referencia-ya-generada`, `referencia-en-proceso` | Generar otra o usar `reemplazar` |

---

## 9. Checklist de aceptación (lo que tiene que hacer el sistema construido)
- [ ] Sincroniza el catálogo y lo refresca al cambiar `version`.
- [ ] Cada artículo está enlazado a una `variable_clave`.
- [ ] La pantalla de bandera pide en el orden de §5.7, completa lo automático y muestra el total y las telas con `calcular`.
- [ ] El triángulo pide la punta **antes** de las medidas y explica ancho/alto con un dibujo de la caja.
- [ ] Medidas siempre en metros; nunca suma el margen.
- [ ] Pide la plantilla con la medida final y no deja mandar un arte de otra medida.
- [ ] Valida con `POST /pedidos/validar` antes de mandar y muestra `donde.campo` de cada alarma.
- [ ] Manda el `.zip` con `pedido.json` en la raíz.
- [ ] Sigue el estado o recibe el aviso **verificando la firma**.
- [ ] Baja los PDF verificando `sha256` antes de 30 días.
- [ ] Guarda `pedido_externo` para reconocer la venta cuando vuelve.

## 10. Pruebas sugeridas
1. `POST /a_medida/calcular` con las 3 formas y las 4 puntas del triángulo: comparar `total_cm` y `telas[].entra`.
2. Validar un pedido con un talle inexistente → `talle-inexistente` con `donde.campo`.
3. Mandar `color_cmyk` en las tiras → `tiras-invalidas`.
4. Mandar un pedido completo y recibir el aviso con firma correcta; luego uno con la firma alterada → rechazarlo.
5. Bajar cada PDF y comparar `sha256`.

Código de referencia (sin dependencias): [`codigo/enviar_pedido.py`](codigo/enviar_pedido.py),
[`codigo/recibir_aviso.py`](codigo/recibir_aviso.py), [`codigo/cliente.mjs`](codigo/cliente.mjs),
[`codigo/crear_en_programa.js`](codigo/crear_en_programa.js) (página del diseñador → Illustrator / CorelDRAW).
