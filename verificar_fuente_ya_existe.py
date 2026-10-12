# -*- coding: utf-8 -*-
"""CONTRATO: UNA TIPOGRAFÍA SE GUARDA CON SU NOMBRE Y NO PISA OTRA SIN PREGUNTAR — `py verificar_fuente_ya_existe.py`

Pedido del usuario (2026-10-01):
  · «si yo subo una fuente es esa fuente»: se guarda con el nombre del archivo, sin `subida_`;
  · «si se llama igual a otra, que diga esa fuente ya existe: ¿reemplazarla o dejar la misma?»;
  · «obvio que también se pueden subir familias»: Regular, Bold, Black… de una familia conviven.

Se prueba contra `POST /api/fuente` con una carpeta de catálogo DESCARTABLE (copias de tipografías
del catálogo real): nunca se toca `catalogo_fuentes/`. También la migración de los `subida_*`.
"""
import os
import shutil
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")   # sin usuarios: import limpio
import registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(tempfile.mkdtemp(prefix="verif_logs_"))
import servidor as S          # noqa: E402
import motor_pedido as MP     # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


REAL = os.path.join(_AQUI, "catalogo_fuentes")


def real(nombre_parcial):
    """Una tipografía del catálogo real (sólo se LEE y se copia)."""
    for a in sorted(os.listdir(REAL)):
        if nombre_parcial.lower() in a.lower() and a.lower().endswith((".ttf", ".otf")):
            return os.path.join(REAL, a)
    raise SystemExit(f"no encontré «{nombre_parcial}» en catalogo_fuentes para la prueba")


TMP = tempfile.mkdtemp(prefix="verif_fuente_existe_")
S.FUENTES = TMP
S.app.config["TESTING"] = True
cli = S.app.test_client()


def subir(origen, nombre, reemplaza=None):
    datos = open(origen, "rb").read()
    import fitz
    nom = MP.nombres_fuente(datos)
    form = {"archivo": (__import__("io").BytesIO(datos), nombre), "interno": fitz.Font(fontbuffer=datos).name,
            "completo": nom["completo"], "ps": nom["ps"], "sin_contorno": "[]", "choca_con": "null"}
    if reemplaza:
        form["reemplaza"] = reemplaza
    r = cli.post("/api/fuente", data=form, content_type="multipart/form-data")
    return r.status_code, r.get_json(silent=True) or {}


try:
    m54 = real("Superstar M54")
    arial_bold = real("Arial-Bold")
    arial_black = real("ariblk")
    anton = real("Anton-Regular")

    print("1. se guarda con su nombre real")
    st, d = subir(m54, "Superstar M54.ttf")
    ok(st == 200 and os.path.exists(os.path.join(TMP, "Superstar M54.ttf")), f"queda «Superstar M54.ttf» (status {st})")
    ok(not any(a.startswith("subida_") for a in os.listdir(TMP)), "ningún archivo lleva «subida_»")

    print("2. el mismo nombre de archivo: pregunta (409) y no pisa")
    antes = open(os.path.join(TMP, "Superstar M54.ttf"), "rb").read()
    st, d = subir(anton, "Superstar M54.ttf")
    ok(st == 409 and (d.get("existe") or {}).get("archivo") == "Superstar M54.ttf", f"contesta «ya existe» (status {st})")
    ok(open(os.path.join(TMP, "Superstar M54.ttf"), "rb").read() == antes, "la que estaba sigue intacta")
    st, d = subir(anton, "SUPERSTAR m54.TTF")
    ok(st == 409, f"mismo nombre con otras mayúsculas también pregunta (status {st})")

    print("3. la misma fuente con otro nombre de archivo: también pregunta")
    st, d = subir(m54, "copia de la m54.ttf")
    ok(st == 409 and (d.get("existe") or {}).get("archivo") == "Superstar M54.ttf", f"la reconoce por adentro (status {st})")
    ok(not os.path.exists(os.path.join(TMP, "copia de la m54.ttf")), "no quedó guardada sin permiso")

    print("4. «Reemplazarla»")
    st, d = subir(m54, "copia de la m54.ttf", reemplaza="Superstar M54.ttf")
    ok(st == 200, f"entra con reemplaza (status {st})")
    ok(os.path.exists(os.path.join(TMP, "copia de la m54.ttf")) and not os.path.exists(os.path.join(TMP, "Superstar M54.ttf")),
       "queda la nueva y se saca la vieja (no la misma fuente dos veces)")
    st, d = subir(anton, "copia de la m54.ttf", reemplaza="copia de la m54.ttf")
    ok(st == 200 and open(os.path.join(TMP, "copia de la m54.ttf"), "rb").read() == open(anton, "rb").read(),
       "mismo nombre + reemplaza: queda el archivo nuevo")

    print("5. familias: estilos distintos conviven")
    st1, _ = subir(arial_bold, "Arial-Bold.ttf")
    st2, d2 = subir(arial_black, "ariblk.ttf")
    ok(st1 == 200 and st2 == 200, f"Arial Bold y Arial Black entran las dos ({st1}, {st2})")

    print("6. el resolvedor distingue por PostScript")
    _cat = {"carpetas": [TMP], "alias": {}}
    ok(os.path.basename(MP.resolver_fuente("Arial-Black", _cat) or "") == "ariblk.ttf", "«Arial-Black» → ariblk.ttf")
    ok(os.path.basename(MP.resolver_fuente("Arial-BoldMT", _cat) or "") == "Arial-Bold.ttf", "«Arial-BoldMT» → Arial-Bold.ttf")

    print("7. las cargadas antes como subida_* pasan a su nombre (sin perder nada)")
    MIG = tempfile.mkdtemp(prefix="verif_fuente_mig_")
    S.FUENTES = MIG
    shutil.copy(m54, os.path.join(MIG, "subida_Superstar M54.ttf"))          # sólo con prefijo → se renombra
    shutil.copy(anton, os.path.join(MIG, "Anton-Regular.ttf"))
    shutil.copy(anton, os.path.join(MIG, "subida_Anton-Regular.ttf"))         # copia idéntica → se saca
    shutil.copy(arial_bold, os.path.join(MIG, "Impacto.ttf"))
    shutil.copy(arial_black, os.path.join(MIG, "subida_Impacto.ttf"))        # distinta con el mismo nombre → no se toca
    S._quitar_prefijo_fuentes()
    quedan = sorted(os.listdir(MIG))
    ok("Superstar M54.ttf" in quedan and "subida_Superstar M54.ttf" not in quedan, "subida_Superstar M54.ttf → Superstar M54.ttf")
    ok("subida_Anton-Regular.ttf" not in quedan and "Anton-Regular.ttf" in quedan, "la copia idéntica se saca, la buena queda")
    ok("subida_Impacto.ttf" in quedan and "Impacto.ttf" in quedan, "si hay otra DISTINTA con ese nombre no se toca ninguna")
    shutil.rmtree(MIG, ignore_errors=True)

    # 🔴 (MAPA 669) EL NOMBRE INTERNO QUE MANDA EL NAVEGADOR. Arriba se simula el navegador con el nombre de
    # PyMuPDF; el navegador de verdad hacía `new mupdf.Font('subida', bytes).getName()` → «subida» para TODA
    # tipografía (mupdf.js devuelve el nombre que se le pasa). Ahora se calcula de los bytes y tiene que dar
    # EXACTO lo mismo que `fitz.Font(...).name`.
    print("8. el nombre interno que calcula el navegador = el de PyMuPDF (y nunca «subida»)")
    import json as _json, subprocess as _sp, glob as _glob, fitz
    _AQ = os.path.dirname(os.path.abspath(__file__))
    _fs = sorted(_glob.glob(os.path.join(_AQ, "catalogo_fuentes", "*.[oOtT][tT][fF]")))
    _ref = {p: fitz.Font(fontfile=p).name for p in _fs}
    _js = ("import fs from 'node:fs'; import { nombreInternoMupdf } from './src/motor/texto/fuentes.js';"
           "const r = JSON.parse(fs.readFileSync(0, 'utf8')); const o = {};"
           "for (const p of Object.keys(r)) o[p] = nombreInternoMupdf(new Uint8Array(fs.readFileSync(p)));"
           "console.log(JSON.stringify(o))")
    _r = _sp.run(["node", "--input-type=module", "-e", _js], cwd=os.path.join(_AQ, "frontend"), input=_json.dumps(_ref),
                 capture_output=True, text=True, encoding="utf-8", timeout=120)
    _got = _json.loads(_r.stdout.strip().splitlines()[-1]) if _r.returncode == 0 and _r.stdout.strip() else {}
    _mal = [(os.path.basename(p), _ref[p], _got.get(p)) for p in _ref if _got.get(p) != _ref[p]]
    ok(len(_ref) > 0 and not _mal, f"{len(_ref) - len(_mal)} de {len(_ref)} tipografías del catálogo con el mismo nombre interno"
       + (f" — distintas: {_mal[:3]}" if _mal else ""))
    _w = open(os.path.join(_AQ, "frontend", "src", "motor", "obrero.worker.js"), encoding="utf-8").read()
    ok("const interno = nombreInternoMupdf(bytes)" in _w and "new mupdf.Font('subida'" not in _w,
       "el análisis del navegador usa ese nombre (ya no `new mupdf.Font('subida', …)`)")
    _dir8 = tempfile.mkdtemp(prefix="verif_fuente_8_")
    _ar = os.path.join(_dir8, "Anton-Regular.ttf")
    shutil.copy(os.path.join(_AQ, "catalogo_fuentes", "Anton-Regular.ttf"), _ar)     # una copia: el catálogo no se toca
    if os.path.exists(_ar):
        MP._FUENTE_INFO.clear()
        MP.registrar_fuente(_ar, "subida")
        ok(MP._info_fuente(_ar)["interno"] == "Anton Regular", "si una pestaña vieja manda «subida», el servidor lo ignora y lee el archivo")

    # (MAPA 670) LAS TIPOGRAFÍAS DE ESTA PC conviven con las cargadas: con un navegador simulado (`queryLocalFonts`
    # devuelve tipografías REALES del catálogo) y el permiso dado o no
    print("9. las fuentes de esta PC: sin permiso nada cambia; con permiso se reconocen y las cargadas ganan")
    _r9 = _sp.run(["node", os.path.join("src", "motor", "pruebas", "fuentes_pc.mjs"), os.path.join(_AQ, "catalogo_fuentes")],
                  cwd=os.path.join(_AQ, "frontend"), capture_output=True, text=True, encoding="utf-8", timeout=120)
    try:
        _j9 = _json.loads(_r9.stdout.strip().splitlines()[-1])
    except Exception:
        _j9 = {}
    _sp9, _cp9, _es9 = _j9.get("sinPermiso") or {}, _j9.get("conPermiso") or {}, _j9.get("estampar") or {}
    ok(_sp9.get("lista") == 0 and _sp9.get("catalogo") == 1 and _sp9.get("preguntas") == 0,
       f"sin el permiso no se pregunta solo y el catálogo queda igual ({_sp9})")
    ok(_cp9.get("antonGanaLaSubida") and _cp9.get("graduateDeLaPc"),
       "con el permiso: la cargada (Anton) le gana a la de la PC, y la que sólo está en la PC (Graduate) se reconoce")
    ok(_es9.get("suma") == 1 and _es9.get("interno") == _es9.get("internoEsperado") and _es9.get("bytesIguales") and _es9.get("sinNecesidadNoSuma"),
       f"para estampar se suma SÓLO la que falta, con su nombre interno exacto y sus bytes ({_es9.get('interno')})")
    _fr = lambda *r: open(os.path.join(_AQ, "frontend", "src", "motor", *r), encoding="utf-8").read()
    _g9, _pv9, _fe9, _pa9, _fs9 = _fr("pedido", "generar.js"), _fr("arte", "previa.js"), _fr("arte", "fuentesEstado.js"), _fr("prepararArte.js"), _fr("arte", "fuentesSubir.js")
    ok(_g9.count("await sumarFuentesPc(plan, rutaApi)") == 2 and _g9.count("bajarFuentes(md.fuentes, md.pid, rutaApi, md._pc)") == 3
       and "fuentesConPc(m.info.fuentes, nombres)" in _pv9 and "const todas = await catalogoConPc(subidas)" in _fe9
       and "de_pc" in _fe9 and "catalogoConPc(" in _pa9 and "catalogoConPc(" in _fs9,
       "la usan la tizada (y el aviso «se achicará»), la vista previa, el estado de fuentes, la planilla y la revisión del arte")
    _app9 = open(os.path.join(_AQ, "frontend", "src", "App.jsx"), encoding="utf-8").read()
    ok('data-tour="arte-fuente-pc"' in _app9 and "listarPc({ pedir: true })" in _app9 and "fuentesEstado.de_pc.join" in _app9,
       "la ventana de Fuentes: «Usar las de esta PC» (pide el permiso con un clic) y cuáles se toman de la PC")

    # (MAPA 672) «no veo las fuentes de mi PC en Configuración y el arte dice que no encuentra la fuente»: el permiso
    # quedaba escondido en un botón del modal. Ahora se pide solo al primer clic, se ven en Configuración → Fuentes
    # (y se cargan al sistema de a una) y las colecciones .ttc de Windows se leen
    print("10. fuentes de la PC: permiso al primer clic, lista en Configuración y colecciones .ttc")
    _co10, _pc10 = _j9.get("coleccion"), _j9.get("primerClic") or {}
    if _co10 is not None:
        ok(_co10.get("ps") == "CambriaMath" and _co10.get("interno") == "Cambria Math Regular" and _co10.get("glifos", 0) > 0
           and _co10.get("ext") == "ttf" and _co10.get("sueltaIgual"),
           f"de una colección .ttc sale la cara pedida como archivo suelto y el estampado la lee ({_co10})")
    ok(_pc10.get("sinClic") == 0 and (_pc10.get("tras1") or {}).get("pedidas") == 1 and (_pc10.get("tras1") or {}).get("oyentes") == 1
       and _pc10.get("concedido") and _pc10.get("quedanOyentes") == 0 and _pc10.get("lista", 0) > 0 and _pc10.get("cerroNoInsiste"),
       f"el permiso se pide al primer clic y nunca sin un clic; si ese intento falla (pestaña no visible) vuelve en el próximo; "
       f"si la persona cierra el cartel, no insiste ({_pc10})")
    ok("pcPermiso === 'prompt' && (" in _app9 and _app9.count('data-tour="arte-fuente-pc" onClick={pedirFuentesPc}') == 1,
       "el cartel amarillo «Tipografía no encontrada» del paso Arte trae «Usar las de esta PC» a la vista (MAPA 673)")
    ok("pedirAlPrimerClic();" in _app9 and 'data-tour="fuentes-pc"' in _app9 and "archivoPc(f.ps)" in _app9
       and "nombresPc().then(setPcLista)" in _app9 and _app9.count("{botonFuentesPc()}") >= 2
       and "cargarFuentesTodas(); _pvLimpiar()" in _app9,
       "Configuración → Fuentes lista las de la PC con «Cargar al sistema»; el botón está también en «Tipografía no encontrada»; al dar el permiso se revisan TODOS los artes")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("FALLAS:" if FALLOS else "TODO OK", *FALLOS, sep="\n  · ")
sys.exit(1 if FALLOS else 0)
