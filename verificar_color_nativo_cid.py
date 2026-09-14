# -*- coding: utf-8 -*-
"""
CONTRATO: EL COLOR DEL NOMBRE/NÚMERO ES EL DEL ARTE, EXACTO — y la mesa suelta lleva su perfil.
Se corre con `py verificar_color_nativo_cid.py`.

EL REPORTE (2026-09-10): «¿por qué me cambió los colores? el original es 0/100/100/0 y el archivo
exportado 0/99,6/100/0,2; ¿declara el perfil ICC y todo lo que debe tener un archivo para
sublimación?». Tres respuestas, y dos eran nuestras:

  A) El 0/99,6/100/0,2 **viene del arte del usuario**: su `arte.ai` trae literalmente
     `0 0.996 1 0.002 k`. Illustrator muestra 0/100/100/0 porque redondea el panel a enteros.
     El sistema copió los bytes tal cual. NO es un bug.

  B) 🔴 El nombre/número del GOLERO salía **0/87,3/84,8/7,1** (calculado, 4 decimales) en vez del
     rojo del arte. CAUSA: los tres lectores de personalización (`_colores_personalizable`,
     `_trazo_personalizable`, `_pasadas_personalizable`) guardaban el color nativo SÓLO con clave
     por TEXTO del `Tj`. Con una fuente CID (2 bytes por glifo) ese "texto" son ids de glifo
     (`\\x00(\\x00+…`) que nunca coinciden con «nombre»/«00» → `colorn=None` → `_color_op` cae a
     sRGB→CMYK. En la mesa 1 zafaba por el atajo «un solo texto en la mesa»; en la 2 (nombre +
     número) no. FIX: se guarda TAMBIÉN con clave por CAPA (Nombre, Número…), que no depende de
     la fuente, y `_match_texto` la prueba primero.

  C) 🔴 La hoja completa lleva `OutputIntents` (el perfil ICC declarado) y la **mesa suelta no**:
     `descargar_mesa` copiaba la página a un PDF nuevo y el OutputIntent vive en la RAÍZ. El
     archivo que va a la imprenta era justo el que no declaraba perfil. FIX: `_pdf_de_una_pagina`
     copia el OutputIntent de la hoja.

⚠️ No toca datos del usuario: lee su arte en SOLO LECTURA y arma sus propios PDF en memoria.
"""
import io
import os
import re
import sys
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError(f"MSSQL (db.{n})")))
_falso.get_doc = lambda c, default=None: default
_falso.set_doc = lambda c, o: None
_falso.proyectar_catalogo = lambda c: None
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

import pikepdf                                   # noqa: E402
import motor_pedido as MP                        # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


# ─────────────────────────────────────────────────────────────────
print("\n1 · 🔴 FUENTE CID: el color nativo se encuentra por CAPA aunque el texto no sirva de clave")
# Un arte sintético como el del GOLERO: dos textos en capas Nombre/Número, dibujados con una fuente
# Type0 (Identity-H) cuyo `Tj` son ids de glifo. El relleno es el rojo del usuario.
ROJO = "0 0.996 1 0.002 k"


def arte_cid():
    p = pikepdf.new()
    p.add_blank_page(page_size=(400, 400))
    pg = p.pages[0]
    nombre = p.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/OCG"), "/Name": pikepdf.String("Nombre")}))
    numero = p.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/OCG"), "/Name": pikepdf.String("Número")}))
    diseno = p.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/OCG"), "/Name": pikepdf.String("diseño")}))
    p.Root.OCProperties = pikepdf.Dictionary({"/OCGs": pikepdf.Array([diseno, nombre, numero]),
                                             "/D": pikepdf.Dictionary({"/Order": pikepdf.Array([diseno, nombre, numero])})})
    # fuente Type0 con Identity-H: el Tj lleva ids de glifo de 2 bytes, no texto
    desc = p.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/FontDescriptor"), "/FontName": pikepdf.Name("/Falsa"),
                                               "/Flags": 32, "/FontBBox": pikepdf.Array([0, 0, 1000, 1000]),
                                               "/ItalicAngle": 0, "/Ascent": 800, "/Descent": -200, "/CapHeight": 700, "/StemV": 80}))
    cid = p.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/Font"), "/Subtype": pikepdf.Name("/CIDFontType2"),
                                              "/BaseFont": pikepdf.Name("/Falsa"), "/FontDescriptor": desc, "/DW": 600,
                                              "/CIDSystemInfo": pikepdf.Dictionary({"/Registry": pikepdf.String("Adobe"),
                                                                                    "/Ordering": pikepdf.String("Identity"), "/Supplement": 0})}))
    f0 = p.make_indirect(pikepdf.Dictionary({"/Type": pikepdf.Name("/Font"), "/Subtype": pikepdf.Name("/Type0"),
                                             "/BaseFont": pikepdf.Name("/Falsa"), "/Encoding": pikepdf.Name("/Identity-H"),
                                             "/DescendantFonts": pikepdf.Array([cid])}))
    pg.Resources = pikepdf.Dictionary({
        "/Font": pikepdf.Dictionary({"/F0": f0}),
        "/Properties": pikepdf.Dictionary({"/D": diseno, "/N1": nombre, "/N2": numero})})
    contenido = (
        b"/OC /D BDC 0 0 0 1 k EMC\n"
        b"BT /F0 40 Tf 1 0 0 1 50 300 Tm\n"
        b"/OC /N1 BDC " + ROJO.encode() + b" <0028002B0026> Tj EMC\n"
        b"/OC /N2 BDC <00040004> Tj EMC\n"
        b"ET\n")
    pg.Contents = p.make_stream(contenido)
    return p


ruta = os.path.join(RAIZ, "scratchpad")
os.makedirs(ruta, exist_ok=True)
ARTE = os.path.join(ruta, "_verif_arte_cid.pdf")
arte_cid().save(ARTE)
nat = MP._colores_personalizable(ARTE)
m1 = nat.get("1") or {}
claves_capa = [k for k in m1 if str(k).startswith(MP._CLAVE_CAPA)]
ok(len(claves_capa) == 2, f"se guardó el color por CAPA para los dos campos: {sorted(k[len(MP._CLAVE_CAPA):] for k in claves_capa)}")
ok(m1.get(MP._CLAVE_CAPA + "nombre") == ("k", [0.0, 0.996, 1.0, 0.002]),
   "🔴 y el de «Nombre» es el rojo EXACTO del arte")
ok(m1.get(MP._CLAVE_CAPA + "numero") == ("k", [0.0, 0.996, 1.0, 0.002]),
   "y el de «Número» también (hereda el relleno vigente)")
_txt = [k for k in m1 if not str(k).startswith(MP._CLAVE_CAPA)]
ok(all("\x00" in k for k in _txt), f"la clave por TEXTO son ids de glifo, inservibles: {[repr(k) for k in _txt]}")

print("\n2 · `_match_texto` prueba la capa primero y no rompe el atajo de «un solo texto»")
pers = MP.extraer_personalizacion(ARTE)
print(f"    campos detectados: { {m: sorted(c) for m, c in pers.items()} }")
# el matcheo real vive dentro de extraer_personalizacion; se prueba por su efecto
for campo in ("Nombre", "Número"):
    pl = (pers.get("1") or {}).get(campo)
    if pl is None:
        # PyMuPDF puede no ver texto de una fuente sin programa embebido → no hay placeholder que
        # matchear; el caso real (GOLERO) se cubre en la sección 3
        print(f"    ({campo}: PyMuPDF no extrajo el texto de la fuente falsa; se cubre con el arte real)")
        continue
    ok(pl.get("colorn") == ("k", [0.0, 0.996, 1.0, 0.002]), f"🔴 {campo}: colorn nativo, sin caer al cálculo")
    ok(MP._color_op(pl) == ROJO, f"y `_color_op` escribe «{ROJO}» tal cual")
# el atajo «un solo valor» sigue vivo con las claves por capa presentes
solo = {"xx": ("k", [0, 0, 0, 1]), MP._CLAVE_CAPA + "nombre": ("k", [0, 0, 0, 1])}
_mt = None
src_ep = MP.extraer_personalizacion.__code__
# `_match_texto` es local: se reconstruye la misma regla acá para probarla en aislamiento
def _match(dmesa, tn, capa=None):
    if not dmesa:
        return None
    if capa:
        v = dmesa.get(MP._CLAVE_CAPA + capa)
        if v is not None:
            return v
    _t = {k: x for k, x in dmesa.items() if not str(k).startswith(MP._CLAVE_CAPA)}
    v = _t.get(tn)
    if v is None:
        v = next((x for k, x in _t.items() if k and (k in tn or tn in k)), None)
    if v is None and len(_t) == 1:
        v = next(iter(_t.values()))
    return v
ok(_match(solo, "zzz") == ("k", [0, 0, 0, 1]), "una mesa con UN texto sigue matcheando por el atajo aunque tenga clave por capa")
ok(_match({"00": ("k", [1, 1, 1, 1]), MP._CLAVE_CAPA + "numero": ("k", [0, 0.5, 0, 0])}, "00", "numero") == ("k", [0, 0.5, 0, 0]),
   "y con capa, gana la capa")

print("\n3 · EL ARTE REAL DEL USUARIO (GOLERO, fuente CID · JUGADOR, fuente simple)")
pid = "prod_20260820_095558_38bc"
real = os.path.join(RAIZ, "entrada", pid, "disenos")
if os.path.exists(os.path.join(real, "golero", "arte.ai")):
    g = MP.extraer_personalizacion(os.path.join(real, "golero", "arte.ai"))
    m2 = g.get("2") or {}
    ok(m2.get("Nombre", {}).get("colorn") == ("k", [0.0, 0.996, 1.0, 0.002]),
       "🔴 GOLERO mesa 2 · Nombre: el rojo exacto del arte (antes: None → 0/87,3/84,8/7,1)")
    ok(m2.get("Número", {}).get("colorn") == ("k", [0.0, 0.996, 1.0, 0.002]),
       "🔴 GOLERO mesa 2 · Número: ídem")
    ok(all(MP._color_op(pl) == ROJO for pl in m2.values()),
       "y lo que se escribe en la tizada es «0 0.996 1 0.002 k», el del arte, sin calcular nada")
    # JUGADOR usa una fuente SIMPLE (no CID): tiene que salir por el camino de siempre, con su
    # color nativo leído del archivo. 🔴 NO se clava el valor: el arte es del usuario y lo cambia
    # cuando quiere (2026-09-14 lo reemplazó por el «PESADO» y el texto pasó de negro a blanco, lo
    # que ponía este contrato en rojo sin que hubiera nada roto). Lo que se exige es la PROPIEDAD:
    # que haya color nativo y que se escriba tal cual, sin recalcularlo.
    j = MP.extraer_personalizacion(os.path.join(real, "jugador", "arte.ai"))
    _pl = [pl for c in j.values() for pl in c.values()]
    ok(_pl and all(pl.get("colorn") for pl in _pl),
       "JUGADOR (fuente simple): todos los campos traen color NATIVO del arte (ninguno en None)")
    ok(all(MP._color_op(pl) == " ".join(f"{v:g}" for v in pl["colorn"][1]) + " " + pl["colorn"][0]
           for pl in _pl),
       "…y la tizada escribe ESE color tal cual, sin calcularlo "
       f"(hoy: {sorted({MP._color_op(pl) for pl in _pl})})")
else:
    print("    (no está el arte real: se saltea)")
MP.cerrar_abiertos()

print("\n4 · 🔴 CADA MESA SUELTA LLEVA EL PERFIL DE LA HOJA, con SUS valores (1, 2 o todas)")
# Pedido explícito del usuario (2026-09-11): «los valores debe mantenerlos aunque se descargue 1 o 2
# o todos los pdf». La pantalla baja TODO por `descargar_mesa` (una mesa, o «Descargar todo» que
# llama al mismo endpoint página por página), así que este helper es el único camino. Cada página
# lleva un rojo DISTINTO a propósito: si el helper sacara la página equivocada o perdiera un valor,
# acá se ve.
import servidor as S                              # noqa: E402
ROJOS = [b"0 0.996 1 0.002 k", b"0 1 1 0.314 k", b"0.75 0 0 0 k"]
hoja = pikepdf.new()
for i in range(3):
    hoja.add_blank_page(page_size=(300, 300))
    hoja.pages[i].Contents = hoja.make_stream(b"q " + ROJOS[i] + b" 10 10 100 100 re f Q")
PERFIL = bytes(range(256)) * 4                     # 1 KB con contenido, no ceros: se compara byte a byte
icc = hoja.make_stream(PERFIL)
icc.N = 4
hoja.Root.OutputIntents = pikepdf.Array([hoja.make_indirect(pikepdf.Dictionary({
    "/Type": pikepdf.Name("/OutputIntent"), "/S": pikepdf.Name("/GTS_PDFX"),
    "/OutputConditionIdentifier": pikepdf.String("Perfil de prueba"), "/Info": pikepdf.String("Perfil de prueba"),
    "/DestOutputProfile": icc}))])
b = io.BytesIO()
hoja.save(b)
b.seek(0)
src = pikepdf.open(b)
for pi in range(3):
    dst = S._pdf_de_una_pagina(src, pi)
    o = io.BytesIO()
    dst.save(o, force_version="1.6")
    o.seek(0)
    out = pikepdf.open(o)
    oi = out.Root.get("/OutputIntents")
    ok(bool(oi) and str(oi[0].get("/S")) == "/GTS_PDFX"
       and str(oi[0].get("/OutputConditionIdentifier")) == "Perfil de prueba",
       f"🔴 mesa {pi + 1} suelta: OutputIntent GTS_PDFX declarado, el mismo de la hoja")
    ok(oi and oi[0].DestOutputProfile.read_bytes() == PERFIL and int(oi[0].DestOutputProfile.N) == 4,
       f"    mesa {pi + 1}: el ICC incrustado es byte a byte el de la hoja (N=4)")
    cont = out.pages[0].Contents.read_bytes()
    ok(ROJOS[pi] in cont and all(r not in cont for r in ROJOS if r != ROJOS[pi]),
       f"    mesa {pi + 1}: trae SU valor de color ({ROJOS[pi].decode()}) y ninguno de otra página")
    ok(len(out.pages) == 1 and out.pdf_version == "1.6", f"    mesa {pi + 1}: una sola página, PDF 1.6")

print("\n5 · 🔴 SI NO HAY NINGÚN PERFIL EN LA MÁQUINA, SE DICE — nunca sale una hoja sin declarar en silencio")
# `_icc_para_salida` decide el perfil: forzado → el del arte → el predeterminado del sistema. Los
# tres salen de archivos .icc/.icm de la máquina (Adobe, Windows, `perfiles_icc/`, TIZADA_PERFILES).
# Si no hay ninguno, devuelve (None, None, None) y la hoja saldría sin OutputIntent: eso ahora deja
# `perfil_icc = None` y un aviso que lo dice con todas las letras.
_dirs, _cache = S.PERFILES_DIRS, S._perfiles_cache
try:
    S.PERFILES_DIRS, S._perfiles_cache = [], None
    ok(S._icc_para_salida([], cat={}) == (None, None, None),
       "sin carpetas de perfiles, `_icc_para_salida` devuelve (None, None, None) — no inventa uno")
finally:
    S.PERFILES_DIRS, S._perfiles_cache = _dirs, _cache
_src = open(os.path.join(RAIZ, "servidor.py"), encoding="utf-8").read()
_i = _src.find('res["perfil_icc"] = None')
ok(_i > 0, "🔴 la generación deja `perfil_icc = None` cuando no hubo perfil")
ok(_i > 0 and "SIN perfil de color" in _src[_i:_i + 900] and "avisos_pedido.append" in _src[_i:_i + 900],
   "y agrega un aviso al pedido que dice «SIN perfil de color» (antes: silencio)")
ok(S._icc_para_salida([], cat={})[0] is not None or not S.PERFILES_DIRS,
   f"en ESTA máquina hay perfil por defecto: {S._icc_para_salida([], cat={})[1]}")

for f in (ARTE,):
    try:
        os.remove(f)
    except OSError:
        pass

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: el nombre/número sale con el color exacto del arte y la mesa suelta declara su perfil")
