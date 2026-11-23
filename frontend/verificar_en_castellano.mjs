/**
 * CONTRATO: LOS ERRORES SE LEEN EN CASTELLANO — `node verificar_en_castellano.mjs` (corre en `npm run build`).
 *
 * MAPA 782-789. El navegador, Python (urllib, Windows) y los servidores de afuera dan sus errores en inglés, y la pantalla
 * pegaba `e.message` tal cual. `enCastellano` (App.jsx) los cambia por una frase en castellano. Se rompió tres veces:
 * traducía palabra por palabra y dejaba frases mezcladas («The request is el navegador no dio permiso agent…»), tomaba
 * «Error al guardar» por inglés y lo convertía en «error del sistema», o dejaba pasar «<urlopen error …>» porque el
 * mensaje de Windows venía en castellano. Este contrato corre la función TAL CUAL está en App.jsx y exige:
 *   · lo nuestro, en castellano, queda IGUAL;
 *   · lo de afuera sale sin inglés (ningún tramo con más palabras de inglés que de castellano) y con su sentido.
 */
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const app = readFileSync(new URL('./src/App.jsx', import.meta.url), 'utf8')
const i = app.indexOf('const _EN_PAL'), j = app.indexOf('// decimales con COMA')
if (i < 0 || j < 0) { console.log('✗ CONTRATO ROTO — no se encontró `enCastellano` en App.jsx'); process.exit(1) }
// el catálogo de errores del navegador vive aparte (`src/erroresNavegador.js`, MAPA 818) y App.jsx lo importa
const { ERRORES_NAVEGADOR, PALABRAS_INGLES } = await import('./src/erroresNavegador.js')
const { enCastellano, _esTramoIngles, _ERR_SISTEMA } = new Function('ERRORES_NAVEGADOR', 'PALABRAS_INGLES', app.slice(i, j) + '\nreturn { enCastellano, _esTramoIngles, _ERR_SISTEMA }')(ERRORES_NAVEGADOR, PALABRAS_INGLES)
console.error = () => {}

const QUEDAN = [
  'Error al guardar: no hay conexión con el servidor', 'Error al eliminar: el servidor contestó algo que no se entiende',
  'Error al leer', 'Error interno', 'Error', 'Error leyendo PDF', 'Faltan 2 piezas sin tela', 'No se encontró el molde', 'Esa tela no existe',
  'la fila 3: tiene talle XL que el molde no tiene', 'Elegí al menos una talla.', 'el archivo trae 2 contornos y el molde tiene 30 tallas',
  'No se pudo leer los usuarios: no hay conexión con el servidor', 'PDF inválido', 'el molde no tiene piezas', 'Hay 1 pieza sin tela asignada.',
  // nombres del usuario en inglés entre «» (vuelta 26): no son un error
  '«The Best Shirt.ai»: el archivo no tiene piezas', 'La tipografía «Open Sans Default Font» no está en el catálogo',
]
const CAMBIAN = [   // [entrada, algo que la salida tiene que decir]
  ['No se pudo hablar con el servidor publicado: <urlopen error [WinError 10061] No se puede establecer una conexión ya que el equipo de destino denegó expresamente dicha conexión>', 'conectar'],
  ['<urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>', 'conectar'],
  ['Expecting value: line 1 column 1 (char 0)', 'no se entiende'], ["[Errno 2] No such file or directory: 'x'", 'no se encontró'],
  ['[Errno 28] No space left on device', 'lugar'], ["'NoneType' object has no attribute 'get'", 'falla interna'],
  ['net::ERR_CONNECTION_REFUSED', 'conexión'], ['JSON.parse: unexpected character at line 1 column 1 of the JSON data', 'no se entiende'],
  ['[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed', 'segura'], ['code=2: cannot open document', 'PDF'],
  ['PermissionError: [WinError 32] The process cannot access the file because it is being used by another process', 'archivo'],
  ["InvalidStateError: Failed to execute 'transaction' on 'IDBDatabase': The database connection is closing.", 'recargá'],
  ['aviso: HTTP Error 401: UNAUTHORIZED', 'llave'], ['Not Found: el molde x', 'no se encontró: el molde x'],
  ['NotAllowedError: The request is not allowed by the user agent or the platform in the current context.', 'permiso'],
  ['504 Gateway Timeout', 'tardó'], ['The read operation timed out', 'tardó'], ['NetworkError: A network error occurred.', 'conexión'],
  ["Lock broken by another request with the 'steal' option.", 'pestaña'], ['409 Conflict', 'cambió'], ['413 Payload Too Large', 'grande'],
  ['Failed to fetch', 'conexión'], ["No se pudo armar: TypeError: Failed to execute 'json' on 'Response': body stream already read", 'No se pudo armar: falla interna'],
  [`Unexpected token '<', "<!doctype "... is not valid JSON`, 'no se entiende'], ["Cannot read properties of undefined (reading 'mesas')", 'falla interna'],
  ['No se pudo leer el servidor: HTTP 503', 'problema'], ['Maximum call stack size exceeded', 'falla interna'],
  // vuelta 26
  ["No se pudo actualizar las telas del sistema: No se pudo consultar la API de telas: 'utf-8' codec can't decode byte 0xe2 in position 10: invalid continuation byte", 'No se pudo actualizar las telas del sistema: No se pudo consultar la API de telas: la respuesta trae caracteres'],
  ["Failed to execute 'transaction' on 'IDBDatabase': The database connection is closing.", 'recargá'],
  ["No se pudo guardar en esta computadora: Failed to execute 'transaction' on 'IDBDatabase': The database connection is closing.", 'No se pudo guardar en esta computadora: se cerró'],
  ["error interno del servidor: unsupported operand type(s) for +: 'int' and 'str'", 'error interno del servidor: falla interna'],
  ['code=2: syntax error in array', 'PDF'], ['Uncaught RangeError: Invalid array length', 'falla interna'],
  ['RuntimeError: unreachable', 'recargá'], ['HTTP 409', 'cambió'], ['HTTP 422', 'no aceptó'], ['HTTP 429', 'demasiados'],
  ['MemoryError', 'memoria'], ['Login timeout expired', 'base de datos'], ['zlib error: incorrect header check', 'comprimido'],
  ['Worker terminated', 'se cortó'], ['float division by zero', 'falla interna'], ['socket.timeout: timed out', 'tardó'],
  // vuelta 27
  ['math domain error', 'falla interna'], ['dictionary changed size during iteration', 'falla interna'],
  ["error interno del servidor: 'width'", 'error interno del servidor: falla interna'], ['Extra data: line 1 column 5 (char 4)', 'no se entiende'],
  ['pikepdf._core.PdfError: x.pdf: unable to find trailer', 'PDF'], ['pymupdf.FileDataError: cannot open broken document', 'PDF'],
  ['FzErrorFormat: no objects found', 'PDF'], ['MuPDF error: format error: cannot find startxref', 'PDF'],
  ['OTS parsing error: invalid sfntVersion: 1008821359', 'tipografía'], ['Unsupported OpenType signature wOF2', 'tipografía'],
  ['JSZip: Corrupted zip or bug: unexpected signature', 'comprimido'], ['Mixed Content: The page was loaded over HTTPS', 'insegura'],
  ['WebAssembly.instantiate(): Out of memory', 'memoria'], ['Uncaught (in promise) TypeError: Failed to fetch', 'conexión'],
  ['Something went wrong', 'falla interna'], ['canvas size exceeds maximum', 'memoria'], ['ERR_INSUFFICIENT_RESOURCES', 'memoria'],
  ['Corrupted zip: missing 22 bytes.', 'comprimido'], ['No password given', 'PDF'], ['undefined', 'falla interna'], ['null', 'falla interna'],
  ['RuntimeError: Aborted(OOM)', 'memoria'], ['ImportError: DLL load failed while importing _fitz', 'componente'], ['405 Method Not Allowed', 'operación'],
  ["pyodbc.IntegrityError: ('23000', \"Violation of UNIQUE KEY constraint 'UQ_x'. Cannot insert duplicate key\")", 'ya existe'],
  ['NotAllowedError: Failed to execute showSaveFilePicker: Must be handling a user gesture to show a file picker.', 'permiso'],
  ["error del sistema: 'x'", 'falla interna'],
  // vuelta 28
  ['AssertionError', 'falla interna'], ['CancelledError', 'se canceló'], ['NotImplementedError', 'falla interna'],
  ['BadZipFile: File is not a zip file', 'comprimido'], ['BrokenProcessPool: A process in the process pool was terminated abruptly', 'procesos'],
  ['Script error.', 'falla interna'], ['URI malformed', 'falla interna'], ['Unauthenticated.', 'llave'],
  ["Invalid URL 'x': No scheme supplied. Perhaps you meant https://x?", 'dirección'],
  // vuelta 29: clases detrás de algo nuestro, con módulo, con siglas, entre paréntesis
  ['No se pudo guardar: CancelledError', 'No se pudo guardar: se canceló'], ['No se pudo guardar: ValueError', 'No se pudo guardar: falla interna'],
  ['No se pudo guardar: Error', 'No se pudo guardar: falla interna'], ['OSError', 'falla interna'], ['EOFError', 'falla interna'],
  ['DOMException', 'falla interna'], ['TTLibError', 'falla interna'], ['KeyboardInterrupt', 'falla interna'],
  ['concurrent.futures._base.CancelledError', 'se canceló'], ['sqlite3.OperationalError: database is locked', 'falla interna'],
  ['requests.exceptions.ConnectionError: HTTPSConnectionPool(host=\'x\', port=443): Max retries exceeded', 'conexión'],
  ['fontTools.ttLib.TTLibError: Not a TrueType or OpenType font', 'tipografía'], ['http.client.RemoteDisconnected: Remote end closed connection', 'conexión'],
  ['la mesa 3 falló dos veces (OSError: [Errno 28] No space left on device)', 'la mesa 3 falló dos veces (no queda lugar en el disco del servidor)'],
  ['el aplanado en paralelo no terminó (CancelledError: )', 'el aplanado en paralelo no terminó'],
  ['Token expired', 'venció'], ['jwt expired', 'venció'], ['Communication link failure', 'base de datos'],
  ['Temporary failure in name resolution', 'dirección'], ['Error: timeout', 'tardó'], ['Uncaught Error: Worker error', 'falla interna'],
  ['SystemError: error return without exception set', 'falla interna'], ['NaN', 'falla interna'],
  ['The user has exceeded their Drive storage quota', 'Google Drive'], ['The method is not allowed for the requested URL.', 'operación'],
  ['Access is denied.', 'archivo'], ['Error: PDF header not found', 'PDF'], ['font not found', 'tipografía'],
  ['<HttpError 404 when requesting https://x returned "File not found: x.">', 'Google Drive'],
]
CAMBIAN.push(
  ["el aplanado en paralelo no terminó (ValueError: invalid literal for int() with base 10: 'abc')", 'el aplanado en paralelo no terminó (falla interna'],
  ['la mesa 2 falló (RangeError: toFixed() digits argument must be between 0 and 100)', 'la mesa 2 falló (falla interna'],
  ['No se pudo (NetworkError when attempting to fetch resource.)', 'No se pudo (no hay conexión'],
)
const QUEDAN_2 = [['No se pudo armar la tizada: (TimeoutError)', 'No se pudo armar la tizada'], ['Hay 1 molde (WhatsApp) sin nombre', 'Hay 1 molde (WhatsApp) sin nombre']]
const QUEDAN_EXTRA = ['Los procesos de dibujo no respondieron (TimeoutError). Volvé a intentarlo en unos segundos.']
// 2026-11-23 (MAPA 817): la pantalla vieja tras un build ya no dice «no hay conexión», y la memoria de MuPDF se nombra
CAMBIAN.push(['Failed to fetch dynamically imported module: http://localhost:8050/assets/x-abc.js', 'recargá'],
  ['TypeError: Importing a module script failed.', 'recargá'], ['realloc (163443015 bytes) failed', 'memoria'])
// 2026-11-23 (MAPA 818): los del navegador que se ven de verdad, cada uno con la explicación que le toca
CAMBIAN.push(
  ["TypeError: Cannot read properties of undefined (reading 'mesas')", 'todavía no estaba cargado'],
  ['NotReadableError: The requested file could not be read, typically due to permission problems that have occurred after a reference to a file was acquired.', 'volvé a elegirlo'],
  ['NoModificationAllowedError: An attempt was made to modify an object where modifications are not allowed.', 'otro programa'],
  ["NotFoundError: Failed to execute 'removeChild' on 'Node': The node to be removed is not a child of this node.", 'traductor'],
  ['net::ERR_INTERNET_DISCONNECTED', 'sin internet'], ['net::ERR_BLOCKED_BY_CLIENT', 'bloqueador'], ['net::ERR_CERT_DATE_INVALID', 'fecha y la hora'],
  ['net::ERR_UPLOAD_FILE_CHANGED', 'volvé a elegirlo'], ['net::ERR_CONNECTION_RESET', 'se cortó la conexión'],
  ['QuotaExceededError: The quota has been exceeded.', 'no queda lugar'],
  ['VersionError: The requested version (3) is less than the existing version (4).', 'otra pestaña'],
  ['UnknownError: Internal error opening backing store for indexedDB.open.', 'guardado del navegador'],
  ['The string did not match the expected pattern.', 'no se entiende'], ['JSON Parse error: Unrecognized token \'<\'', 'una página en vez de datos'],
  ["SecurityError: Failed to read the 'localStorage' property from 'Window': Access is denied for this document.", 'ventana privada'],
  ['NotAllowedError: Document is not focused.', 'clic en la página'], ['Maximum call stack size exceeded', 'vuelta sin fin'],
  ['too much recursion', 'vuelta sin fin'], ['TypeError: x is not iterable', 'esperaba una lista'], ['TypeError: Load failed', 'conexión'],
  ['TypeError: window.queryLocalFonts is not a function', 'Chrome o Edge'], ["Cannot read properties of undefined (reading 'digest')", 'https'],
  ["undefined is not an object (evaluating 'a.b')", 'todavía no estaba cargado'], ["can't access property \"x\", y is undefined", 'todavía no estaba cargado'],
  ["ReferenceError: Cannot access 'x' before initialization", 'antes de que estuviera listo'], ['Assignment to constant variable.', 'protegido'],
  ['EncodingError: The source image cannot be decoded.', 'imagen'], ['RuntimeError: memory access out of bounds', 'lector de PDF'],
  ['WebAssembly.instantiate(): Out of memory: Cannot allocate Wasm memory for new instance', 'memoria'],
  ['Extension context invalidated.', 'extensión'], ['TypeError: NetworkError when attempting to fetch resource.', 'conexión'],
)
const SIN_PARENTESIS = 'Los procesos de dibujo no respondieron. Volvé a intentarlo en unos segundos.'
// 🔴 TODO lo NUESTRO en castellano, sacado del código (lo que pasa por showError / new Error / "error": … / raise):
// tiene que salir IGUAL. La vuelta 27 del inspector probó 540 a mano; esto lo hace en cada build.
// (TODO el código: `frontend/src` entero y todos los .py de la raíz — la vuelta 28 encontró 652, no 377)
const _todo = (dir, ext) => readdirSync(dir, { withFileTypes: true }).flatMap((d) => d.isDirectory()
  ? (['node_modules', 'pruebas', 'laboratorio'].includes(d.name) ? [] : _todo(join(dir, d.name), ext))
  : (ext.test(d.name) ? [join(dir, d.name)] : []))
const _raiz = fileURLToPath(new URL('..', import.meta.url))
const _js = _todo(fileURLToPath(new URL('./src', import.meta.url)), /\.(jsx?|mjs)$/).map((f) => readFileSync(f, 'utf8')).join('\n')
const _srv = readdirSync(_raiz).filter((f) => f.endsWith('.py') && !f.startsWith('verificar_')).map((f) => readFileSync(join(_raiz, f), 'utf8')).join('\n')
const _lim = (x) => x.replace(/\$\{[^}]*\}/g, '«x»').replace(/\{[a-z_][^{}]*\}/gi, '«x»').trim()   // también «{i.filename[:80]}» (f-string con recorte, MAPA 818)
const NUESTROS = new Set()
for (const re of [/showError\(\s*(['`])((?:\\.|(?!\1).)*)\1/g, /new Error\(\s*(['`])((?:\\.|(?!\1).)*)\1/g, /showWarn\(\s*(['`])((?:\\.|(?!\1).)*)\1/g])
  for (const m of _js.matchAll(re)) { const x = _lim(m[2]); if (x.length > 3 && /[áéíóúñ]|\b(?:el|la|no|se|de|que|con|para|hay)\b/i.test(x)) NUESTROS.add(x) }
for (const re of [/"error":\s*f?"((?:\\.|[^"])*)"/g, /raise \w+\(\s*f?"((?:\\.|[^"])*)"/g])
  for (const m of _srv.matchAll(re)) { const x = _lim(m[1]); if (x.length > 3 && /[áéíóúñ]|\b(?:el|la|no|se|de|que|con|para|hay)\b/i.test(x)) NUESTROS.add(x) }
const fallas = []
for (const [t, debe] of QUEDAN_2) { const o = enCastellano(t); if (o !== debe) fallas.push(`«${t}» → «${o}» (tenía que quedar «${debe}»)`) }
for (const t of QUEDAN_EXTRA) { const o = enCastellano(t); if (o !== SIN_PARENTESIS) fallas.push(`«${t}» → «${o}» (tenía que quedar la frase sin el nombre técnico)`) }
for (const t of NUESTROS) { const o = enCastellano(t); if (o !== t) fallas.push(`cambió un texto NUESTRO del código: «${t}» → «${o}»`) }
for (const t of QUEDAN) { const o = enCastellano(t); if (o !== t) fallas.push(`cambió lo que estaba en castellano: «${t}» → «${o}»`) }
for (const [t, debe] of CAMBIAN) {
  const o = enCastellano(t)
  if (!o.includes(debe)) fallas.push(`«${t}» → «${o}» (tenía que decir «${debe}»)`)
  if (o.split(': ').some(_esTramoIngles) || /urlopen|WinError|Errno|Error:|Exception/.test(o)) fallas.push(`quedó inglés: «${t}» → «${o}»`)
}
// 🔴 TODOS los mensajes oficiales de los navegadores (MAPA 818): ninguno puede salir en inglés ni quedar sin tocar
const { muestras: _muestras } = JSON.parse(readFileSync(new URL('./errores_navegador_muestras.json', import.meta.url), 'utf8'))
if (_muestras.length < 2000) fallas.push(`errores_navegador_muestras.json tiene ${_muestras.length} mensajes (eran 2.279): ¿se pisó la lista?`)
let _explicados = 0
for (const [, nombre, t] of _muestras) {
  if (t === 'x') continue                               // el mensaje de V8 que es sólo «%» (lo arma otro)
  const o = enCastellano(t)
  if (o === t) fallas.push(`mensaje del navegador sin traducir (${nombre}): «${t}»`)
  else if (o.split(': ').some(_esTramoIngles)) fallas.push(`quedó inglés (${nombre}): «${t}» → «${o}»`)
  if (o.trim() !== _ERR_SISTEMA) _explicados++
}
// los AVISOS pasan por explicarError (código + registro), la pantalla del Registro por enCastellano (no se registra a sí misma)
if (!app.includes('const txt = explicarError(txt0)')) fallas.push('showError ya no usa explicarError: la falla interna sale sin código ni registro (MAPA 817)')
if (!/api\/registro\/navegador[\s\S]{0,400}codigo: cod/.test(app)) fallas.push('explicarError ya no deja el código en el Registro del sistema (MAPA 817)')
if (fallas.length) {
  console.log(`\n✗ CONTRATO ROTO — ${fallas.length} falla(s) en enCastellano:`)
  for (const f of fallas) console.log('   · ' + f)
  process.exit(1)
}
console.log(`✓ CONTRATO VERDE — errores en castellano (${QUEDAN.length} frases + ${NUESTROS.size} textos del código intactos, ${CAMBIAN.length} de afuera traducidos; ${_muestras.length} mensajes oficiales de los navegadores en castellano, ${_explicados} con su explicación propia y el resto «falla interna» con código)`)
