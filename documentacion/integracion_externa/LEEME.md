# Conectar otro sistema con TIZADA PRO

Todo lo que hace falta para que un sistema externo (ventas, ERP, tienda online) le mande pedidos a
TIZADA PRO y reciba los archivos de producción **asociados a SU pedido**, sin que nadie toque TIZADA.

📘 **La guía visual en PDF:** [`TIZADA_PRO_Conectar_otro_sistema.pdf`](TIZADA_PRO_Conectar_otro_sistema.pdf) (11 páginas, con
la puesta en marcha en el servidor de TIZADA y los diagramas de cómo se conectan los JSON).

## Qué viaja

| Dirección | Qué | Formato |
|---|---|---|
| otro sistema → TIZADA | El **pedido**: `pedido.json` + los **artes** (.ai/.pdf) + las **tipografías** que falten (.ttf/.otf) | un **.zip** (`POST /pedidos`) |
| otro sistema → TIZADA | Revisar un pedido antes de mandarlo | el mismo .zip o sólo el JSON (`POST /pedidos/validar`) |
| TIZADA → otro sistema | Qué se puede pedir: **variables**, prendas, talles, columnas de la planilla, telas, tipografías, alarmas | JSON (`GET`) |
| TIZADA → otro sistema | El **estado** y el **resultado**: cada PDF con su sha256, su enlace de Drive y la venta (`pedido_externo`) tal cual se mandó | JSON (`GET /pedidos/{ref}`) o **aviso** firmado (webhook) |
| TIZADA → otro sistema | Los **PDF**: una tizada por tela (cada página es una mesa) + la **ficha técnica** | PDF (`GET …/archivos/{nombre}` o Google Drive) |

## Por dónde empezar (10 minutos)

1. Pedir una **llave** al que administra TIZADA PRO (*Configuración › Integraciones › Crear llave*).
2. Leer [`API.md`](API.md): el recorrido y cada ruta.
3. Mirar [`pedido_ejemplo.json`](pedido_ejemplo.json) y [`resultado_ejemplo.json`](resultado_ejemplo.json).
   Campo por campo: [`FORMATO_PEDIDO.md`](FORMATO_PEDIDO.md).
4. Probar con el código listo de [`codigo/`](codigo/):
   ```bash
   set TIZADA_URL=http://127.0.0.1:8050
   set TIZADA_LLAVE=tzp_...
   python codigo/enviar_pedido.py una_carpeta_con_pedido_json_y_artes --solo-revisar
   ```
5. Para la pantalla del otro sistema: el **sistema de ventas de prueba** (repositorio aparte) hace todo
   esto con interfaz — elegir diseños y variables como en TIZADA, subir el arte, planilla con
   Importar/Exportar, revisar, mandar, ver el avance, recibir el aviso, ver los PDF y comprobar en Drive.

## Contenido

| | |
|---|---|
| [`API.md`](API.md) | La API entera: llave, recorrido, cada ruta con lo que manda y lo que vuelve, el aviso y su firma, errores |
| [`FORMATO_PEDIDO.md`](FORMATO_PEDIDO.md) | `pedido.json` campo por campo, cómo armar el arte, las alarmas y cómo evitarlas |
| [`openapi.yaml`](openapi.yaml) | La API en OpenAPI 3 (se importa en Postman / Insomnia o se genera un cliente) |
| [`esquemas/`](esquemas/) | JSON Schema del pedido y del estado/resultado/aviso |
| [`pedido_ejemplo.json`](pedido_ejemplo.json) | Un pedido completo (revisado contra el catálogo real) |
| [`resultado_ejemplo.json`](resultado_ejemplo.json) | Lo que vuelve cuando está listo (= el cuerpo del aviso) |
| [`respuestas/`](respuestas/) | La respuesta REAL de cada ruta (código HTTP + cuerpo; las listas largas recortadas) |
| [`codigo/`](codigo/) | Python sin dependencias (`enviar_pedido.py`, `recibir_aviso.py`) y Node 18+ (`cliente.mjs`) |

## Reglas que conviene saber de entrada

- **Se eligen VARIABLES, no moldes** (igual que en TIZADA): el pedido manda la `variable` (clave `v_…`
  de `GET /variables`); la prenda va de la mano.
- Las **telas por id**, las **piezas por nombre genérico** («Cuello», no «Cuello 2»), los **talles tal
  cual** los tiene la prenda.
- La `referencia` es única: con la misma referencia ya lista, se rechaza salvo `"reemplazar": true`.
- `pedido_externo` vuelve **tal cual** en el resultado: ahí va lo que el otro sistema necesite para
  reconocer su venta.
- Revisar con `POST /pedidos/validar` antes de mandar; las alarmas dicen qué y dónde (`donde.campo`).
- El aviso se cree **sólo si la firma coincide** (`X-Tizada-Firma`).
