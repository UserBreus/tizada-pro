# CorelDRAW en TIZADA PRO — archivo de referencia

> Estudio hecho el **2026-09-30** con **CorelDRAW Graphics Suite 2026 (v27.2.0.135)** instalado en la PC
> del taller. Todo lo que dice «medido» se probó de verdad: se armaron archivos en Corel por
> automatización (COM), se publicaron a PDF y se pasaron por las mismas funciones del motor que leen
> un arte o un molde. Lo que dice «según la documentación» no se pudo probar acá (no hay Corel 2022
> a 2025 instalado).
> Relacionado: `MAPA_DEL_SISTEMA.md` (changelog **597**), `MANUAL_HERRAMIENTAS.md` §2.2, y los
> scripts de prueba en `documentacion/corel/pruebas/`.

---

## 1. En una línea

**TIZADA PRO no lee el `.cdr`: lee el PDF que publica Corel**, igual que del `.ai` de Illustrator lee
su parte PDF. Corel guarda algunas cosas **distinto** que Illustrator. Desde el 2026-09-30 el sistema
entiende las dos formas, y con los artes y moldes de Illustrator da **exactamente lo mismo que antes**:
se comparó la lectura de 19 archivos reales antes y después.

---

## 2. Versiones de Corel (2022 en adelante)

| Nombre | Versión interna | Cómo se llama para automatizar (ProgID) |
|---|---|---|
| 2022 | 24.0 – 24.2 | `CorelDRAW.Application.24` |
| 2023 | 24.3 – 24.5 (mismo 24 que 2022) | `CorelDRAW.Application.24` |
| 2024 | 25 | `CorelDRAW.Application.25` |
| 2025 | 26 | `CorelDRAW.Application.26` |
| **2026** (la del taller) | **27** | `CorelDRAW.Application.27` |

- `CorelDRAW.Application` (sin número) abre la instalada más nueva. **Medido:** conecta con el Corel
  que ya está abierto y no abre otro.
- **Carpetas:** el programa va en `C:\Program Files\Corel\CorelDRAW Graphics Suite\27\`, pero los
  datos del usuario en `%APPDATA%\Corel\CorelDRAW Graphics Suite 2026\`. Una carpeta usa el número
  y la otra el año. **Nunca escribirlas a mano:** pedírselas a Corel (`app.SetupPath`,
  `app.AddonPath`, `app.GMSManager.UserGMSPath`).
- **Automatización (VBA, COM y JavaScript):**
  - Sólo en **CorelDRAW Graphics Suite**; *Standard* y *Essentials* no la traen (según la
    documentación).
  - Sólo en Windows (en Mac sólo hay JavaScript).
  - La instalación del taller trae VBA (x64) y un motor de JavaScript (`ScriptHost`).
  - Los paneles web de Corel son WebView2 (`browserEdge`).
- **Tamaño máximo de página: 45,72 m × 45,72 m** (1800").

---

## 3. Cómo guarda Corel el PDF, al lado de Illustrator (medido)

| Qué | Illustrator | CorelDRAW 2026 | ¿TIZADA PRO lo entiende? |
|---|---|---|---|
| **Capas** | Una capa PDF (OCG) por capa del documento | **Una por capa y por página**: con 9 mesas, «guias» aparece 9 veces | ✅ Desde hoy se toma **una vez cada nombre** (antes la barra de capas/talles las repetía) |
| **Orden de capas** | La de arriba primero | Igual (la de arriba primero) | ✅ Igual |
| **Marcas de capa en el dibujo** | `BDC /OC … EMC` | Igual (`/Pr12 BDC … EMC`) | ✅ Igual: aislar, recolorear y apagar capas funciona igual |
| **Capa por defecto** | «Capa 1» (se renombra) | «Capa 1» en **cada página**, y suele quedar **vacía** | ✅ En el molde base se ignora (no tiene dibujo). En el molde con diseño queda en la lista interna de capas, pero sin piezas no aparece en ningún lado (ver §6) |
| **Capas maestras** («Guías», «Escritorio», «Cuadrícula») | — | **No salen** en el PDF | ✅ Nada que hacer |
| **Mesa de trabajo** | Una página por mesa | Una página por mesa (el nombre de la página no viaja) | ✅ Igual. El nombre de la mesa se lee del **texto** en la capa guias, como siempre |
| **Nombre de la mesa** (`Frente#M`) | Texto vivo | Texto vivo | ✅ Igual (auto-mapeo por nombre) |
| **Colores CMYK** | `k` (DeviceCMYK); guarda decimales (0,996) | `cs`+`scn` sobre ICC CMYK; **siempre enteros** (12/34/56/7 → 0,12 0,34 0,56 0,07) | ✅ El motor ya leía los dos; **exacto** |
| **Tipografías** | TrueType simple | **Type0 (CID)** incrustada en subconjunto | ✅ Por nombre PostScript (`Arial-BoldMT`), igual que siempre |
| **Borde del nombre/número** («detrás del relleno») | Pila de apariencias: texto + **contornos del glifo trazados** (`S`) | El **mismo texto** en **modo trazo** (`1 Tr`) + ancho `w` + color de trazo | ✅ **Desde hoy.** Antes el borde de Corel se leía como un relleno del color que hubiera quedado de antes (salía cian) |
| **Copia invisible del texto** | No existe | Todo texto con borde lleva además una copia **invisible** (`3 Tr`, para poder seleccionarlo) | ✅ **Desde hoy.** MuPDF la seguía leyendo con la capa apagada: el número tomaba la posición y el tamaño del nombre |
| **Texto sobre una curva** | Letra por letra | Letra por letra | ✅ Sigue el arco (medido: 8 puntos de línea base) |
| **Máscara de recorte** (molde con diseño) | Máscara de recorte | **PowerClip** → sale como recorte (`W n`) | ✅ Detecta cada pieza en cada talle |
| **Grupo** dentro de «Editable …» | Objetos sueltos | Objetos sueltos | ✅ Igual (3 objetos en el mismo editable) |
| **Imagen** (logo PNG) | Imagen incrustada | Imagen incrustada | ✅ Igual (no recoloreable) |
| **Degradé** | Sombreado vectorial (`sh`) | Sombreado vectorial (`sh`) | ✅ Igual |
| **Transparencia** | `ca/CA` en ExtGState | `ca/CA 0,5` en ExtGState | ✅ Igual (vectorial) |
| **Sombra paralela** | Se rasteriza | **Se rasteriza** (imagen + máscara suave) | ⚠️ Igual que en Illustrator: es una imagen que hace el propio programa del diseñador, no TIZADA PRO |
| **Mesa muy larga** (30 m) | Usa `/UserUnit` (límite del PDF: 5,08 m sin él) | **Sin `/UserUnit`**: página de 85 039 pt | ✅ TIZADA PRO la lee bien. ⚠️ Acrobat y algunos RIP pueden mostrar en blanco una página de más de 5,08 m sin `/UserUnit`: problema sólo si el diseñador manda ese PDF de Corel directo al RIP |
| **Pantone / tinta plana** | `Separation` | No se pudo probar: Corel no da acceso a sus paletas Pantone por automatización | ⚠️ Según la documentación, Corel también escribe `Separation`, y el motor lee las dos igual |

---

## 4. Cómo tiene que exportar el diseñador desde Corel

**Archivo → Publicar como PDF** (en la pantalla: *Configuración* → pestañas):

1. **Compatibilidad: Acrobat 6.0 o más nuevo, o PDF/X-4.** Con las más viejas **se pierden las capas**
   (según la documentación). El valor por defecto de 2026 ya exporta las capas (medido).
2. **Color: Nativo o CMYK**, nunca RGB. Así el CMYK sale exacto (medido con el valor por defecto,
   que es Nativo).
3. **NO** tildar *Exportar texto como curvas*: los nombres de pieza y los textos que se personalizan
   (Nombre, Número…) tienen que llegar como texto.
4. **NO** tildar *Representar rellenos complejos como mapas de bits*: el degradé tiene que seguir
   siendo vector.
5. **El texto del diseño** (lo que se imprime tal cual) va en curvas: *Objeto → Convertir en curvas*
   (Ctrl+Q).
6. **Capas con los mismos nombres que en Illustrator:** `diseño`, `guias`, `Editable …`, `Nombre`,
   `Número` / `00`, y una capa por talle en los moldes. La «Capa 1» vacía se puede dejar.
7. Subir el **.pdf**.

Esto mismo está en la app, en la guía «¿Cómo exportar el molde desde tu programa?», y en los avisos
del arte.

---

## 5. Qué cambió en el código (2026-09-30)

Todo va en **los dos motores**, servidor (Python) y navegador (JavaScript), con la regla de que den
lo mismo.

| Arreglo | Servidor | Navegador |
|---|---|---|
| Capas **una vez cada nombre** | `motor_pedido._orden_capas_archivo`, los campos de `_extraer_personalizacion_crudo`, `variantes_molde._orden_archivo` | `molde/caminoA.js` `ordenCapasArchivo`, `arte/personalizacion.js` (campos) |
| Borde en **modo trazo** (`Tr`) | `_TR_RELLENA` / `_TR_TRAZA` / `_tr_de`, en `_colores_personalizable`, `_trazo_personalizable` y `_pasadas_personalizable` | `TR_RELLENA` / `TR_TRAZA` / `trDe` en `arte/personalizacion.js` |
| **Fantasmas** (texto invisible) | `_extraer_personalizacion_crudo`, paso 1: lo que se lee con todas las capas apagadas se descuenta una vez al aislar cada capa | Igual en `extraerPersonalizacion` |
| **La capa manda** | `_match_texto`: si hay capas anotadas y la de ese campo no, no se toma la de otro por el atajo «un solo texto» | `matchTexto` |
| Avisos que nombran Corel | Aviso del texto vivo en `validar_arte` | `arte/mapeo.js`, `arte/svgPdf.js`, guía de exportación y ayuda de la capa `diseño` en `App.jsx` |

**Cómo se comprobó:**
- «Foto» de la lectura de **19 archivos reales de Illustrator** (11 artes, 5 moldes y 3 de prueba)
  antes y después: **19 de 19 idénticos**.
- Contratos en verde:
  - `verificar_navegador_arte.py` (con los 11 artes reales + los 2 de Corel);
  - `verificar_navegador_camino_a.py`;
  - `verificar_personalizacion_con_diseno.py`;
  - `verificar_color_nativo_cid.py`;
  - `verificar_navegador_curvas.py`.
- **Resultado del arte de Corel:**
  - El **nombre** queda a 48 pt, blanco, con borde negro de 1,5 mm detrás.
  - El **número** queda a 140 pt, negro, sin borde y en su lugar.
- **Molde base de Corel:** 2 piezas × 3 talles con las medidas exactas (45 × 65 cm en S), sin avisos.
- **Molde con diseño de Corel:** detecta 1 pieza por mesa y por talle.

---

## 6. Lo que salió mal (para no repetirlo)

- **Filtrar la «Capa 1» vacía en `talles_del_molde` (probado y REVERTIDO).** Parecía lo lógico, pero
  esa lista es la clave del molde desplegado (`orden` de `m{mesa}.json`). Además, el servidor la
  calcula sobre la **cáscara** (sin dibujo): no puede saber si la capa está vacía y daría otra lista
  que la PC. Cambiarla también invalidaba el desplegado de un molde de Illustrator ya cargado que
  tenía «Capa 1» vacía. Como una capa sin piezas no aparece en ningún lado, se dejó como estaba.
  Quedó escrito en el docstring.
- **El `alpha` del glifo no sirve para detectar el texto invisible:** PyMuPDF lo da, pero mupdf.js
  (el navegador) lo tira en `colorFromNumber`, y los dos motores tienen que leer igual. Por eso se
  usa la regla de los fantasmas, que sólo usa texto y posición.
- **PowerShell y COM:** los métodos de Corel con parámetros opcionales (`SaveAs`, `Import`,
  `AddToPowerClip`, `Outline.SetProperties`) fallan con «no se puede convertir string a string».
  Hay que pasarlos todos: `SaveAs(ruta, app.CreateStructSaveAsOptions())`,
  `Import(ruta, 0, app.CreateStructImportOptions())`, `AddToPowerClip(cont, 0)`, o usar la
  propiedad (`Outline.Width`).
- **PowerShell 5.1 lee un `.ps1` sin BOM como ANSI:** «diseño» llega roto. Los scripts se guardan
  en UTF-8 **con BOM**.
- **`GetActiveObject('CorelDRAW.Application')` falla (MK_E_UNAVAILABLE)** aunque Corel esté
  abierto: Corel no se anota en la tabla de objetos activos. `New-Object -ComObject` (o `Dispatch`)
  sí se engancha con la instancia abierta.
- **Contratos que estaban rotos antes y se arreglaron de paso:**
  - `verificar_navegador_camino_a.py` no esperaba el campo `formato`.
  - El doble de `db` de `verificar_navegador_tizada.py` no tenía `filas`.
  - **Queda roto y anotado aparte:** la ficha técnica sale distinta entre navegador y servidor en
    `verificar_navegador_tizada_a.py`. Ya fallaba antes de estos cambios.

---

## 7. Conectar Corel como se conecta Illustrator («Crear en CorelDRAW»)

### 7.1 Cómo funciona hoy con Illustrator

1. **La extensión (CEP):** `extension_illustrator\com.tizadapro.illustrator\` se instala en
   `%APPDATA%\Adobe\CEP\extensions\` y prende `PlayerDebugMode`. El instalador
   (`extension_illustrator\instalador\Instalador.cs`) hace las dos cosas.
2. **El puente:** es un servidor HTTP chico que corre **dentro de Illustrator** (Node de CEP) en
   **`127.0.0.1:47850`** (`js/puente.js`). Tiene `GET /estado` y `POST /plantilla` (el plan en
   JSON).
3. **La web:** manda el plan (`frontend/src/motor/molde/illustrator.js` → `planIllustrator` /
   `enviarAIllustrator`).
4. **Illustrator lo arma** con ExtendScript (`jsx/tizada.jsx` → `tizadaArmar`):
   - documento CMYK;
   - capas de abajo hacia arriba;
   - una mesa de trabajo por pieza con su nombre;
   - contornos importados de un SVG y convertidos en guías;
   - nombre de cada mesa como texto;
   - capas bloqueadas;
   - guardado en `Documentos\USER PRO\Plantillas\<nombre>.ai`.

### 7.2 Qué hace Corel de todo eso (medido por COM en la 2026)

| Paso de Illustrator | En Corel | Medido |
|---|---|---|
| Documento CMYK en mm | `CreateDocument()` + `doc.Unit = 3` | ✅ |
| Mesa de trabajo por pieza, con nombre | Una **página** por mesa: `AddPages` + `page.Name` + `page.SetSize(w, h)` | ✅ |
| Mesa larga | **Hasta 100 m** (Illustrator topa en ~5,8 m) | ✅ 30 m y 100 m |
| Capas con nombre, de abajo hacia arriba | `page.CreateLayer(nombre)` (la última creada queda arriba) | ✅ |
| Importar el SVG de contornos en su lugar | `layer.Import(svg, 0, opciones)` + `SetPosition` | ✅ 200 × 300 mm exactos, en la posición pedida |
| Contornos como guías | `MasterPage.GuidesLayer.CreateGuide…`, o una capa no imprimible | ✅ Guías creadas |
| Nombre de mesa como texto / en curvas | `CreateArtisticText` / `ConvertToCurves` | ✅ |
| Bloquear capas | `layer.Editable = false` | ✅ |
| Guardar para que abra desde 2022 | `SaveAs(ruta, opciones)` con `opciones.Version = 24` | ✅ `.cdr` versión 2022 |

### 7.3 Cómo conectarlo: tres caminos

| Camino | Qué es | A favor | En contra |
|---|---|---|---|
| **A. Puente propio + COM** (recomendado) | Un programita nuestro en la PC del taller escucha en `127.0.0.1` (otro puerto, p. ej. 47851) con el mismo protocolo que el de Illustrator, y maneja Corel por COM | Un solo código para 2022–2026 (`CorelDRAW.Application` + `VersionMajor`). No se instala nada dentro de Corel. La web casi no cambia: el mismo plan, otro destino | Sólo Windows y sólo Graphics Suite. El programita tiene que estar corriendo (se instala una vez, como la extensión). No hay panel dentro de Corel |
| B. Macro VBA (.gms) | Un botón dentro de Corel que pide el plan a la web | Se instala sin permisos de administrador | VBA no puede escuchar pedidos, sólo preguntar. Depende del nivel de seguridad de macros |
| C. Panel dentro de Corel (add-on HTML o C#) | Lo más parecido al panel de Illustrator | Interfaz dentro de Corel | Instalar pide administrador (`Programs64\Addons`). Sin verificar que el panel web de 2026 pueda manejar Corel y hablar con 127.0.0.1. Hay que probarlo versión por versión |

### 7.4 ✅ HECHO (2026-09-30, MAPA 598): «Crear en CorelDRAW»

Se hizo el **camino A**. Todo en `extension_corel/`, se arma con `py extension_corel/construir.py`
(la versión sube sola por huella, como la de Illustrator).

- **Un solo programa, `Instalar-USER-PRO-Corel-<versión>.exe`**, con tres modos:
  - **sin nada:** la ventana de instalar (la misma del instalador de Illustrator, adaptada).
  - **`/puente`:** el puente en segundo plano, con un ícono junto al reloj.
  - **`/desinstalar`:** la ventana de quitar.
- **Qué hace al instalar** (sin pedir administrador):
  - se copia a `%LOCALAPPDATA%\USER PRO\Corel\USER-PRO-Corel.exe`;
  - queda arrancando con Windows (`HKCU\...\Run` «USERPRO-Corel»);
  - se anota en «Aplicaciones instaladas»;
  - deja el puente corriendo.
  Para actualizar o quitar, cierra el puente **por su PID** (sólo el que corre desde esa carpeta).
- **`puente/Puente.cs`, el servidor local:**
  - Escucha en `127.0.0.1:47851` con un servidor HTTP propio sobre `TcpListener`. No usa
    `HttpListener`, que en muchas PC pide administrador.
  - Tiene `GET /estado` (con `programa:'corel'`, `corel`, `corel_version`, `corel_abierto` y
    `sistema`) y `POST /plantilla`.
  - CORS igual que el puente de Illustrator.
  - Arma una plantilla por vez.
- **`puente/ArmarCorel.cs`, el armado:**
  - **Validación:** el plan se valida campo por campo con topes (`Plan.Sanear`).
  - **COM:** en un solo hilo STA, con filtro de mensajes (si Corel está ocupado, reintenta 2 min).
    Usa `dynamic`, sin biblioteca de tipos: el mismo código sirve para las versiones 24 a 27.
  - **Qué arma, por mesa:** una página con su nombre y su tamaño. En cada página, las capas de abajo
    hacia arriba; la «Capa 1» con que nace la página se renombra a `diseño`, así no queda vacía.
    En `diseño` va el fondo rojo clarito. En `guias` (bloqueada) van el contorno, importado de un
    SVG por página con `tizada_ref` (y punto por punto si eso falla), y el nombre de la mesa como
    texto vivo.
  - **Guardado:** como `.cdr` versión 24 en `Documentos\USER PRO\Plantillas`, sin pisar uno
    existente.
- **Web:**
  - `frontend/src/motor/molde/corel.js`: `buscarCorel`, `enviarACorel`, `versionCorelDelServidor`
    y `planCorel`. Este último es el mismo `planIllustrator` con `sinTope`, repartido en páginas por
    el campo `mesa` que ahora marca `planIllustrator`.
  - **Pantalla del molde:** en Plantilla, la tarjeta única `PlantillaProgramas` («Crear la base en
    tu programa») pone los dos botones lado a lado: Illustrator en naranja y CorelDRAW en verde.
    Cada uno conecta la primera vez y después crea. Debajo están los instaladores de los dos a la
    vista, los avisos de versión nueva y la ventana «No encontré CorelDRAW».
  - El cartel «Creando en…» sirve para los dos programas.
  - Servidor: `/api/corel/version` y `/api/corel/instalador` (el publicado no los tiene, igual que
    Illustrator).
- **Todas las mesas en UN espacio de trabajo (desde la 1.1.0).** Cada mesa sigue siendo una página
  (así la lee el sistema: mesa = página del PDF), pero el conector prende la **vista de varias
  páginas** de Corel en **acomodo libre** (`UseMultipageView`, `MultipageLayout = 1` Freeform) y pone
  cada página en el lugar de su pieza en el molde (`SetPageOrigin` = el CENTRO de la página, «y»
  hacia arriba), igual que las mesas de trabajo de Illustrator. Se guarda con el archivo (medido:
  al reabrir sigue en varias páginas y con las mismas posiciones). El PDF no cambia. Probado con el
  molde de 34 piezas: 34 de 34 en su lugar, ninguna se pisa, y el sistema lee las 34 páginas con
  su nombre y su tamaño. La vista de varias páginas existe desde CorelDRAW 2021: sirve en todas las
  versiones soportadas (2022 en adelante).
- **Botón «Exportar para TIZADA PRO» (desde la 1.2.0).** El conector dibuja un botón pegado a la
  ventana de Corel (abajo a la derecha; se corre arrastrando la manija y el lugar se recuerda):
  - Es una ventanita **hija** de la de Corel: queda encima de Corel y debajo de los demás
    programas, lo sigue cuando se mueve y se esconde si Corel se minimiza o se cierra.
  - Al tocarlo (`ExportarCorel`), primero **revisa** el documento abierto sin tocarlo: avisa si
    hay texto en «diseño» sin pasar a curvas o páginas sin el nombre de la mesa en «guias», y
    pregunta si exporta igual.
  - Después publica el PDF con los ajustes fijos de §4: Acrobat 9 (capas), color nativo, todas
    las páginas, texto como texto, sin rellenos a mapa de bits, fuentes incrustadas, imágenes
    SIN pérdida (ZIP, sin reducir), tintas planas como tintas. Deja los ajustes de PDF del
    documento como estaban y nunca guarda el .cdr.
  - El PDF va al lado del .cdr como «<nombre> - para TIZADA.pdf» (nombre propio: nunca pisa otro
    PDF). Si el documento nunca se guardó, va a Documentos › USER PRO › Para subir. Al terminar
    abre la carpeta con el PDF marcado.
  - También está en el menú del ícono junto al reloj, que tiene «Mostrar el botón en CorelDRAW»
    para apagarlo.
  - **Por qué no es un botón de la barra de Corel** (probado): Corel no expone el editor de VBA por
    COM, `RunMacro` no ve proyectos nuevos sin reiniciar Corel, el truco de VBA para agregar
    botones dejó de andar en la 2022 (foro de Corel) y un add-on propio va en Program Files
    (pide administrador).
  - **Probado:** con el documento real abierto (7 mesas) sale PDF 1.7 con las capas en orden, los
    7 nombres de mesa legibles y CMYK por `scn`. El botón quedó visible, hijo de Corel y adentro
    de su ventana.
- **Siempre a tamaño real y en UN archivo.** En Corel cada mesa es una página de hasta 45 m, así que
  el % y el reparto en varios archivos (cosas del lienzo de Illustrator) no aplican.
  - Lo que en Illustrator va **fuera** de las mesas no va en Corel: el título «TALLE S», el recuadro
    del talle y el cartel de escala.
  - Cada página ya se llama como su mesa («#S Frente»).
- **Probado con un molde real** (camiseta, 34 piezas, copia):
  - 34 páginas en 19 s;
  - cada página del tamaño exacto, con el contorno en su lugar (0 pt de diferencia) y el nombre
    leído bien por `_texto_mesa`;
  - capas en orden;
  - el dibujo punto por punto da el mismo contorno que el SVG.
  Mirado en imagen. El archivo de prueba y el puente de prueba se borraron y cerraron.
- **Sin probar:**
  - Corel **2022–2025** (no hay acá).
  - El **instalador** de punta a punta en otra PC.
  - El botón desde el **navegador**: lo prueba el usuario.

- **Ajuste 4 (conector 1.3.0): el botón es PARTE DE COREL y pregunta la carpeta.** Pedido del
  usuario: «que sea parte de Corel y que pregunte en qué carpeta queremos guardarlo».
  - **Complemento** `extension_corel/complemento/` → `<Corel>\Programs64\Addons\TizadaPro\`:
    `CorelDrw.addon` (vacío: marca la carpeta), `AppUI.xslt` (define el botón
    `712d37ec-…` tipo `dropDownDlgBtn` que despliega un ítem `browser` `a14e264b-…` con
    `href="http://127.0.0.1:47851/panel"`, y la barra `commandBarData` `bc3f54ed-…` «TIZADA PRO»
    ubicada después de la Estándar) y `UserUI.xslt` (la suma al espacio de trabajo).
  - Por qué así: es lo que Corel carga SIN macros ni VBA; el control web de Corel llama al puente
    (`/panel` es una página ES5 que al abrirse hace `POST /exportar-corel`) y el puente hace todo
    lo demás por COM. Así el botón funciona igual de la 2022 a la 2026.
  - Escribir en `Programs64\Addons` pide **administrador**: el instalador se relanza con
    `/complemento` (`Verb=runas`, `Complemento.cs`) UNA vez; el error 1223 = tocaron «No». Todo lo
    demás sigue sin permisos. `/desinstalar` lo quita con `/quitar-complemento`.
  - **Pregunta la carpeta:** `FlujoExportar.Correr()` (el mismo desde la barra, el botón flotante y
    el menú del ícono): analiza → avisos → `SaveFileDialog` encima de Corel (carpeta del .cdr,
    nombre sugerido, avisa antes de reemplazar) → exporta → abre la carpeta → devuelve el foco a
    Corel.
  - El botón flotante (`BotonCorel`) se esconde solo si el Corel abierto tiene el complemento
    (`FlujoExportar.HayComplemento`, mirado cada 10 s).
  - **Probado:** compila, `/panel` responde HTML con el conector 1.3.0 (se cerró SÓLO el instalado
    por PID y se volvió a arrancar). Los XSLT validados con lxml contra el `DrawUI.xml` de la 2026
    (botón, ítem web y barra definidos una vez). **Sin probar (lo prueba el usuario):** la barra
    adentro de Corel tras reiniciarlo, el permiso de administrador y el diálogo real de guardar.

- **Ajuste 5 (conector 1.4.0): botón con ícono y texto.** La 1.3.0 mostraba sólo la flecha del
  `dropDownDlgBtn`: un botón de Corel sin DLL sólo usa íconos internos (`guid://` resuelve contra
  recursos de Corel; no hay íconos por archivo). Ahora el ítem (mismo guid `712d37ec-…`) es
  `type="wpfhost"` → `TizadaPro.dll` (`complemento/BotonTizada.cs`, WPF .NET 4, Corel 2022–2026
  corren CLR v4): ícono de TIZADA PRO en verde + «Exportar para TIZADA PRO», llama a
  `POST /exportar-corel` en un hilo aparte y, si el conector está cerrado, lo arranca. Con Corel
  abierto la DLL está en uso: el instalador la renombra (`*.viejo-…`) y pone la nueva.
  - `UserUI.xslt` corre UNA vez por espacio de trabajo (queda anotado en `<Addons>` del `.cdws`):
    por eso se conservó el guid del botón.
  - Íconos de los instaladores: el isotipo con los colores de cada programa (Illustrator naranja,
    Corel verde): `tenir()` en `extension_illustrator/construir.py`.

**Pendiente, anotado (ya casi no hace falta con el botón «Exportar para TIZADA PRO»):** subir el **.cdr directo**. El mismo puente lo abriría en Corel y devolvería
el PDF publicado con los ajustes de §4. Se le propuso al usuario; todavía no se hizo.

### 7.5 Qué tiene un .cdr por dentro (estudiado con uno armado por nosotros)

- **El contenedor:** es un **ZIP** con `mimetype` = `application/x-vnd.corel.zcf.draw.document+zip`.
- **Adentro:**
  - `content/root.dat`: RIFF con firma `CDRU` en la 2026. Tiene los bloques `doc`, `page`, `layr`,
    `obj `, `outl`, `fild`, `font`, `txsm`…
  - `content/data/page1.dat` … `pageN.dat`, `masterPage.dat` y `data1.dat`: binario propio de Corel,
    que no empieza con RIFF.
  - `content/dataFileList.dat`: la lista de los `.dat`.
  - `color/color.xml`: el modelo de color (`Cmyk`) y si hay objetos RGB o CMYK.
  - `font/fontTable.dat`.
  - `embed/embeddingN`: ~1 MB cada uno; aparentemente son las tipografías incrustadas.
  - `styles/document.cdss`.
  - `META-INF/` (XMP).
  - `previews/thumbnail.png` y `pageN.png`: imágenes chicas.
- **Se puede sacar:** los **nombres de capas y los textos**. Están en UTF-16 dentro de
  `pageN.dat`: «guias», «Nombre», «Editable escudo», «Frente#M».
- **No se puede sacar sin descifrar el formato:** los **colores exactos** (los CMYK 12/34/56/7 no
  aparecen como bytes sueltos) y las **formas**. Además cambia entre versiones (U = 2026).
- **Conclusión:** sirve para leer nombres, no para imprimir. Para imprimir hace falta el PDF que
  publica Corel, o que Corel mismo lo convierta (pendiente de arriba). Si el usuario manda un `.cdr`
  real suyo, se estudia igual para confirmarlo.

---

## 8. Cómo repetir las pruebas

En `documentacion/corel/pruebas/` (necesitan Corel abierto o instalado; arman documentos **nuevos** y
los cierran sin guardar; no tocan nada del usuario):

| Script | Qué arma |
|---|---|
| `arte_prueba.ps1` | Arte con capas `diseño`, `Editable escudo`, `Nombre` (con borde detrás), `00` y `guias`, en 2 mesas |
| `arte_efectos.ps1` | Degradé, transparencia, texto en curvas, sombra, grupo, logo PNG, nombre sobre curva, PowerClip |
| `molde_a_prueba.ps1` | Molde base: 2 piezas × 3 talles con «TALLE-Pieza-#» |
| `molde_b_prueba.ps1` | Molde con diseño adentro (PowerClip) en 2 talles |
| `plantilla_prueba.ps1` | Lo que haría «Crear en Corel»: página larga, capas, SVG importado, guías, bloqueo, guardar v24 |
| `pagina_larga.ps1` | Mesa de 1,6 × 30 m publicada a PDF |
| `analizar_pdf.py <pdf>` | Radiografía del PDF: capas, `/Order`, marcas `BDC`, textos por capa, colores, fuentes |
| `comparar_motor.py <pdf…>` | Pasa el archivo por las funciones del motor que leen el arte |
| `foto_lectura.py <salida.json> [extras]` | «Foto» de cómo el motor lee todos los artes y moldes reales, para comparar antes y después de un cambio |

Los `.ps1` se corren desde PowerShell y tienen que estar guardados en **UTF-8 con BOM**.
