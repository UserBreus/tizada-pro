# -*- coding: utf-8 -*-
"""
CONTRATO: MOLDE A MEDIDA — `py verificar_molde_a_medida.py` (MAPA 623).

Pedido del usuario (2026-10-06): un molde de UNA pieza rectangular (banderas). En Configuración se
crea sin archivo (nombre de la pieza + margen/dobladillo); en el pedido se escribe ancho y alto en
METROS; el visor muestra el margen punteado; si la pieza no entra en la tela, esa tela no se puede
elegir ni se puede avanzar.

Lo que se defiende:
  1. El PDF del rectángulo (motor del navegador) pasa por el alta del camino A y queda UNA pieza con
     su nombre, un talle que es la medida («1,50x0,90») y las medidas exactas.
  2. «¿Entra en la tela?»: gemelos py `_cabe_en_tela` ↔ js `cabeEnTela`, y `_talle_de_medida` ↔
     `talleDeMedida`.
  3. El servidor: la plantilla guarda `a_medida`; la COPIA del pedido copia la configuración (y la
     etiqueta pasa a la variable de la copia); la variable se crea sola después del alta.
  4. La fila de un molde a medida va con SU talle aunque la planilla tenga columna de talle.
  5. La API del otro sistema: `medida-falta`, `medida-invalida`, `tela-no-entra`; el plan frena una
     tela donde no entra.
  6. La plantilla de Illustrator lleva el margen PUNTEADO aparte (no en el SVG que se vuelve guía).

⚠️ No toca nada del usuario: `db` es un doble que explota ([[test-no-toca-mssql]]), DATOS a un tmp.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_TMP = tempfile.mkdtemp(prefix="verif_a_medida_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
import copy as _cp
_DOCS = {}
_falso_db.set_doc = lambda c, o: _DOCS.__setitem__(c, _cp.deepcopy(o))
_falso_db.get_doc = lambda c, default=None: _cp.deepcopy(_DOCS.get(c, default))
_falso_db.proyectar_catalogo = lambda cat: None
sys.modules["db"] = _falso_db
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S               # noqa: E402
import integracion_externa as IE   # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK   " if cond else "  FALLA") + " " + msg)


def node(js):
    r = subprocess.run(["node", "--input-type=module", "-e", js], cwd=os.path.join(_AQUI, "frontend"),
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


print("\n1 · 🔴 EL RECTÁNGULO ENTRA POR EL ALTA DE SIEMPRE (motor del navegador)")
_out = os.path.join(_TMP, "am.json")
r = subprocess.run(["node", "src/motor/pruebas/a_medida.mjs", "1.5", "0.9", "Bandera", os.path.join(_TMP, "am.pdf"), _out],
                   cwd=os.path.join(_AQUI, "frontend"), capture_output=True, text=True, timeout=120)
ok(r.returncode == 0, "el motor arma el PDF y corre el alta" + ("" if r.returncode == 0 else f" ({r.stderr[-300:]})"))
am = json.load(open(_out, encoding="utf-8")) if os.path.exists(_out) else {}
reg = am.get("registro") or {}
ok(list(reg) == ["Bandera"], f"una sola pieza, con su nombre ({list(reg)})")
ok(list((reg.get("Bandera") or {})) == ["1,50x0,90"], "su talle es la medida «1,50x0,90»")
_i = (reg.get("Bandera") or {}).get("1,50x0,90") or {}
ok(_i.get("w_cm") == 150 and _i.get("h_cm") == 90, f"mide 150 × 90 cm ({_i.get('w_cm')} × {_i.get('h_cm')})")
ok(_i.get("pieza_idx") == 0, "y queda con su índice (la variable se ata a ella)")
ok(not am.get("problemas"), f"sin problemas en el alta ({am.get('problemas')})")
ok(((am.get("dxf") or {}).get("nombres_aplicados") or []) == ["Bandera"], "el nombre lo puso el alta sola")

print("\n2 · GEMELOS py ↔ js: ¿entra en la tela? y el nombre del talle")
CASOS = [
    dict(anchoM=3, altoM=2, bordeMm=0, anchoCm=157, largoMaxCm=2000, margenNestingMm=0, rotacion="ninguna"),
    dict(anchoM=1.5, altoM=3, bordeMm=0, anchoCm=157, largoMaxCm=2000, margenNestingMm=10, rotacion="ninguna"),
    dict(anchoM=3, altoM=1.5, bordeMm=0, anchoCm=157, largoMaxCm=2000, margenNestingMm=10, rotacion="90"),
    dict(anchoM=1.57, altoM=1, bordeMm=1, anchoCm=157, largoMaxCm=2000, margenNestingMm=0, rotacion="ninguna"),
    dict(anchoM=1, altoM=25, bordeMm=0, anchoCm=157, largoMaxCm=2000, margenNestingMm=0, rotacion="libre"),
    dict(anchoM=1.5, altoM=0.9, bordeMm=2, anchoCm=157, largoMaxCm=500, margenNestingMm=10, rotacion="auto"),
    # el caso del usuario (2026-10-07): 3 × 1,57 en «Bandera (1,60)» (157 útiles), borde 2 mm, acomodo libre
    dict(anchoM=3, altoM=1.57, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre"),
    # LA MEDIDA ES LA DEL DISEÑO (2026-10-07): 3 × 1,50 con 1 cm de margen por lado = pieza 302 × 152
    dict(anchoM=3, altoM=1.5, margen={"todos": 1}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre"),
    # …y 3 × 1,57 con 3 cm de margen = 306 × 163: se pasa 6,3 cm (entra hasta 156,7); lo máximo, 1,50 de alto
    dict(anchoM=3, altoM=1.57, margen={"todos": 3}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre"),
    # sin giro: el máximo es de ANCHO
    dict(anchoM=1.6, altoM=1, margen={"izq": 2, "der": 2, "arriba": 0, "abajo": 0}, bordeMm=0, anchoCm=157, largoMaxCm=500, margenNestingMm=0, rotacion="ninguna"),
    # el reclamo del usuario (2026-10-07): 3 × 1,50 con 3 cm de margen = 306 × 156 en «Bandera (1,60)» (157) TIENE que entrar
    dict(anchoM=3, altoM=1.5, margen={"todos": 3}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre"),
]
js = node("import { cabeEnTela, talleDeMedida } from './src/motor/molde/aMedida.js';"
          f"const C = {json.dumps(CASOS)};"
          "console.log(JSON.stringify({c: C.map(x => cabeEnTela(x)), t: [talleDeMedida(1.5, 0.9), talleDeMedida(2, 1.005), talleDeMedida(0.333, 12)]}))")
for caso, rj in zip(CASOS, js["c"]):
    cabe, mot = S._cabe_en_tela(caso["anchoM"], caso["altoM"], caso["bordeMm"], caso["anchoCm"], caso["largoMaxCm"],
                                caso["margenNestingMm"], caso["rotacion"], margen=caso.get("margen"))
    ok(cabe == rj["cabe"] and (mot or None) == (rj["motivo"] or None),
       f"{caso['anchoM']}×{caso['altoM']} m en {caso['anchoCm']} cm ({caso['rotacion']}): py {cabe} = js {rj['cabe']}"
       + ("" if (mot or None) == (rj["motivo"] or None) else f" · py «{mot}» ≠ js «{rj['motivo']}»"))
ok(not js["c"][0]["cabe"] and "se pasa 143,3 cm" in js["c"][0]["motivo"], f"3 × 2 m NO entra en una tela de 1,57 y dice cuánto se pasa ({js['c'][0]['motivo']})")
ok(js["c"][2]["cabe"] and js["c"][2]["girada"], "3 × 1,5 m entra GIRADA si el nesting gira 90°")
# 🔴 la separación es ENTRE piezas (MAPA 633): en una mesa de 157 cm entra una pieza de hasta 156,7 (la grilla
# del armado es de 4 mm); justo 157 no
ok(not js["c"][3]["cabe"] and "entra hasta 156,7 cm de ancho" in js["c"][3]["motivo"] and js["c"][3]["maximoM"] == 1.56,
   f"1,57 m justo del ancho de la tela no entra (grilla de 4 mm): lo máximo, 1,56 ({js['c'][3]['motivo']})")
ok(not js["c"][6]["cabe"] and "se pasa 0,3 cm (ni girándola)" in js["c"][6]["motivo"],
   f"3 × 1,57 sin margen tampoco entra girada en 157 ({js['c'][6]['motivo']})")
ok(js["c"][7]["cabe"] and js["c"][7]["girada"], "3 × 1,50 con 1 cm de margen (pieza 302 × 152) entra girada en 157 (ejemplo del usuario)")
ok(not js["c"][8]["cabe"] and "se pasa 6,3 cm" in js["c"][8]["motivo"] and "lo máximo es 1,50 m de alto (sin contar el margen)" in js["c"][8]["motivo"]
   and js["c"][8]["maximoM"] == 1.5, f"3 × 1,57 con 3 cm de margen: dice cuánto se pasa y el máximo ({js['c'][8]['motivo']})")
ok(not js["c"][9]["cabe"] and "lo máximo es 1,52 m de ancho" in js["c"][9]["motivo"], f"sin giro, el máximo es de ancho ({js['c'][9]['motivo']})")
# 🔴 contra el ARMADO REAL (preparar de motor/nesting/contorno.js): lo que la regla dice que entra, entra; el
# máximo que informa entra y 1 cm más ya no; y una pieza 1 cm más angosta que la mesa ENTRA (MAPA 632-633).
_ARM = [dict(w=w, tela=t, mg=mg) for t, mg in ((157, 0), (160, 10), (150, 5)) for w in (t - 3.2, t - 2.6, t - 2, t - 1.9, t - 1, t)]
arm = node("import { preparar } from './src/motor/nesting/contorno.js';"
           "import { cabeEnTela } from './src/motor/molde/aMedida.js';"
           "const CM = 28.3465;"
           "const real = (w, t, mg) => { const B = 0.2 * CM, Wc = w * CM - 2 * B, Hc = 20 * CM - 2 * B;"
           " const p = { etiqueta: 'x', rotacion: 'ninguna', borde_cm: 0, base: { W: Wc, Hp: Hc + 2 * B, B, S: 1, x0: 0, y0: 0, cont: { segmentos: [['re', 0, 0, Wc, Hc]] } } };"
           " const m = mg / 10; preparar([p], { ancho_cm: t, altura_max_cm: 100, espaciado_cm: 0.5, margenes_cm: { sup: m, inf: m, izq: m, der: m }, resolucion_mm: 4 });"
           " return p._candidatos_angulo.length > 0 };"
           f"const A = {json.dumps(_ARM)};"
           "const out = A.map(a => { const r = cabeEnTela({ anchoM: a.w / 100, altoM: 0.2, anchoCm: a.tela, largoMaxCm: 100, margenNestingMm: a.mg });"
           " const mx = cabeEnTela({ anchoM: (a.tela + 1) / 100, altoM: 0.2, anchoCm: a.tela, largoMaxCm: 100, margenNestingMm: a.mg }).maximoM * 100;"
           " return { ...a, regla: r.cabe, armado: real(a.w, a.tela, a.mg), max: mx, maxEntra: real(mx, a.tela, a.mg), maxMas1: real(mx + 1, a.tela, a.mg) } });"
           "console.log(JSON.stringify(out))")
_prom = [a for a in arm if a["regla"] and not a["armado"]]
ok(not _prom, f"lo que la regla dice que ENTRA lo acepta el armado real ({len(arm)} casos al borde){'' if not _prom else ' · promete: ' + str(_prom)}")
_cons = [a for a in arm if a["armado"] and not a["regla"]]
ok(len(_cons) <= 3, f"y no rechaza de más (sólo justo en el borde de una celda: {[(a['tela'], a['w']) for a in _cons]})")
ok(all(a["armado"] for a in arm if a["w"] <= a["tela"] - 1 - 0.2 * a["mg"]), "una pieza 1 cm más angosta que la mesa (menos el margen) ENTRA en el armado real: la separación no se come el borde")
ok(all(a["maxEntra"] and not a["maxMas1"] for a in arm), f"el máximo que informa entra en el armado y 1 cm más ya no ({sorted({(a['tela'], a['mg'], a['max']) for a in arm})})")
ok(js["c"][10]["cabe"] and js["c"][10]["girada"], "3 × 1,50 con 3 cm de margen (pieza 306 × 156) ENTRA girada en la mesa de 157 (reclamo del usuario)")
pz = node("import { medidaPieza } from './src/motor/molde/aMedida.js';"
          "console.log(JSON.stringify(medidaPieza(3, 1.5, { todos: 1 })))")
ok(pz == {"anchoCm": 302, "altoCm": 152} and S._medida_pieza(3, 1.5, {"todos": 1}) == (302.0, 152.0),
   f"la pieza = la medida del diseño + el margen: 3 × 1,50 con 1 cm → 302 × 152 (py y js) ({pz})")
ok([S._talle_de_medida(1.5, 0.9), S._talle_de_medida(2, 1.005), S._talle_de_medida(0.333, 12)] == js["t"],
   f"el nombre del talle es el mismo en los dos ({js['t']})")

print("\n3 · EL SERVIDOR: plantilla, copia del pedido y variable")
CAT = {"productos": [], "plantillas_planillas": [{"id": "sin", "nombre": "Banderas", "columnas": [
    {"id": "nombre", "label": "Nombre", "role": "nombre"}]}],
    "telas": [{"id": "1", "nombre": "Tela 1,60", "ancho_cm": 157, "usable": True},
              {"id": "2", "nombre": "Tela 3,20", "ancho_cm": 317, "usable": True}],
    "nesting_presets": [{"id": "nesting_default", "nombre": "Estándar", "espaciado_mm": 5, "margen_mm": 10, "rotacion": "ninguna",
                         "alto_max_cm": 2000}]}
S._cargar_catalogo_para_editar = lambda *a, **k: CAT
S._cargar_catalogo = lambda *a, **k: CAT
S._guardar_catalogo = lambda *a, **k: None
extra, de, err = S._a_medida_crear({"a_medida": {"pieza": "Bandera", "margen": {"todos": 3}, "ancho_m": 1, "alto_m": 1}}, CAT, "prod_tpl")
ok(err is None and extra["a_medida"]["pieza"] == "Bandera" and extra["a_medida"]["margen"]["todos"] == 3.0,
   "la plantilla guarda la pieza y el margen")
ok(extra["a_medida"]["variable"] == S._clave_var_a_medida("prod_tpl"), "y la clave fija de su variable")
_, _, err2 = S._a_medida_crear({"a_medida": {"pieza": "Ban/dera"}}, CAT, "x")
ok(err2 is not None, "un nombre de pieza con «/» se rechaza")
tpl = {"id": "prod_tpl", "nombre": "Bandera a medida", "planilla_template_id": "sin", **extra,
       "etiqueta": {"activo": True, "posiciones": {extra["a_medida"]["variable"] + "§Bandera": {"rx": 0.1, "ry": 0.9}, "Bandera": {"rx": 0.5}}},
       "borde_corte": {"activo": True, "ancho_mm": 2}, "nesting_preset_id": "nesting_default", "telas_cfg": {"todas": ["1", "2"]},
       "variantes": [{"clave": "v_viejo"}], "creado_por": 7}
CAT["productos"].append(tpl)
ex2, de2, err3 = S._a_medida_crear({"a_medida_de": "prod_tpl", "efimero": True, "ancho_m": "1,5", "alto_m": 0.9}, CAT, "prod_copia")
ok(err3 is None and de2 == "prod_tpl", "la copia del pedido sale de la plantilla")
ok(ex2["a_medida"]["ancho_m"] == 1.5 and ex2["a_medida"]["de"] == "prod_tpl", "con su medida (acepta «1,5») y de dónde salió")
ok("variantes" not in ex2 and "creado_por" not in ex2 and ex2.get("telas_cfg") == {"todas": ["1", "2"]} and ex2.get("borde_corte", {}).get("ancho_mm") == 2,
   "copia la configuración (telas, borde) pero NO las variables ni el dueño")
_cl = S._clave_var_a_medida("prod_copia")
ok((_cl + "§Bandera") in ex2["etiqueta"]["posiciones"] and "Bandera" in ex2["etiqueta"]["posiciones"],
   "la posición de la etiqueta pasa a la variable de la copia")
_, _, err4 = S._a_medida_crear({"a_medida_de": "prod_tpl", "ancho_m": 1, "alto_m": 1}, CAT, "z")
ok(err4 is not None, "una copia que no es efímera (del pedido) se rechaza")
_, _, err5 = S._a_medida_crear({"a_medida_de": "prod_tpl", "efimero": True, "ancho_m": 60, "alto_m": 1}, CAT, "z")
ok(err5 is not None, "una medida de más de 50 m se rechaza")
copia = {"id": "prod_copia", "nombre": "Bandera 1,50x0,90", "efimero": True, **ex2}
CAT["productos"].append(copia)
REG = {"Bandera": {"1,50x0,90": {"mesa": 1, "pieza_idx": 0, "w_cm": 150, "h_cm": 90}}}
_cargar_real = S._cargar
S._cargar = lambda nombre, pid=None, *a, **k: (_cp.deepcopy(REG) if nombre == "registro_producto.json" and pid == "prod_copia"
                                              else _cargar_real(nombre, pid, *a, **k))
os.makedirs(os.path.join(_TMP, "productos", "prod_copia"), exist_ok=True)
S._a_medida_variable("prod_copia")
_v = (copia.get("variantes") or [{}])[0]
ok(_v.get("clave") == _cl and _v.get("label") == "Bandera a medida", f"la variable se crea sola, con la clave fija ({_v.get('clave')})")
ok((_v.get("valores") or [{}])[0].get("pieza_idx") == 0 and (_v.get("valores") or [{}])[0].get("talle_origen") == "1,50x0,90",
   "apunta a la única pieza, en su talle")
ok(copia.get("variante_guia") == "1,50x0,90", "y el talle guía es la medida")
pub = S._a_medida_publico(copia, CAT)
ok(pub["borde_mm"] == 2 and pub["nesting"]["alto_max_cm"] == 2000 and pub["nesting"]["margen_mm"] == 10,
   "la pantalla recibe el borde y el acomodo para decidir sola qué tela sirve")
# la medida es la del DISEÑO: la pieza lleva los 3 cm de margen por lado (1,50 → 156 cm, que no entra en
# los 153 útiles de la tela de 1,60); con 1,40 (146 cm) entra en las dos
# (MAPA 692) lo decide la computadora del usuario: `amEnTela` del motor del navegador, con lo que publica el servidor
def _no_entran(prod, ids):
    pub = S._a_medida_publico(prod, CAT)
    telas = [t for t in CAT["telas"] if str(t.get("id")) in ids]
    r = node("import { amEnTela } from './src/motor/molde/aMedida.js';"
             f"const am = {json.dumps(pub)}; const T = {json.dumps(telas)};"
             "console.log(JSON.stringify(T.map(t => [t.nombre, amEnTela(am, t.ancho_cm)]).filter(x => !x[1].cabe).map(x => [x[0], x[1].motivo])))")
    return r
# (MAPA 696) la bandera SIEMPRE puede girar: para que no entre, los DOS lados tienen que pasarse (alto 1,55 → 161 cm)
copia["a_medida"]["alto_m"] = 1.55
ok(len(_no_entran(copia, ["1", "2"])) == 1, "1,50 × 1,55 + 3 cm de margen por lado (156 × 161 cm) no entra en la de 1,60 ni girada")
copia["a_medida"]["ancho_m"] = 1.4
ok(_no_entran(copia, ["1", "2"]) == [], "1,40 × 1,55 + el margen (146 cm de un lado) entra en las dos telas")
copia["a_medida"]["ancho_m"] = 3
_no = _no_entran(copia, ["1", "2"])
ok(len(_no) == 1 and _no[0][0] == "Tela 1,60", f"3 × 1,55 m no entra en la de 1,60 ni girada ({_no})")
copia["a_medida"]["ancho_m"] = 1.5
copia["a_medida"]["alto_m"] = 0.9

print("\n3b · UN MOLDE YA CREADO, SIN ARCHIVO, SE PUEDE PASAR A MEDIDA (Moldería, 2026-10-06)")
# El catálogo y su guardado se reemplazan acá: lo que se prueba es la DECISIÓN de la ruta.
_cx = {"productos": [{"id": "pSin", "nombre": "Bandera nueva"}, {"id": "pCon", "nombre": "Camiseta"},
                     {"id": "pEf", "nombre": "Del pedido", "efimero": True}]}
_bk = (S._cargar_catalogo_para_editar, S._guardar_catalogo, S._guard_id)
S._cargar_catalogo_para_editar, S._guardar_catalogo, S._guard_id = (lambda: _cx), (lambda c: None), (lambda c: None)
try:
    os.makedirs(os.path.dirname(S._ruta_entrada("plantilla.ai", "pCon")), exist_ok=True)
    open(S._ruta_entrada("plantilla.ai", "pCon"), "wb").write(b"%PDF-1.4")

    def _conv(pid, **k):
        with S.app.test_request_context("/api/productos/a_medida", method="POST",
                                        json={"id": pid, "convertir": {"pieza": "Bandera", "margen": {"todos": 2}, **k}}):
            r = S.guardar_a_medida()
        r, c = (r if isinstance(r, tuple) else (r, r.status_code))
        return c, r.get_json()
    c, j = _conv("pSin", ancho_m=1.2, alto_m=0.8)
    _p = _cx["productos"][0]
    ok(c == 200 and _p.get("a_medida", {}).get("pieza") == "Bandera" and _p["a_medida"]["variable"] == S._clave_var_a_medida("pSin"),
       f"el molde sin archivo pasa a medida, con su pieza y la clave fija de su variable ({c})")
    ok(_p["a_medida"]["ancho_m"] == 1.2 and _p["a_medida"]["margen"]["todos"] == 2.0, "con la medida de muestra y el margen")
    c, j = _conv("pCon")
    ok(c == 409 and "a_medida" not in _cx["productos"][1], f"🔴 un molde que YA tiene su archivo no se pisa con un rectángulo ({c})")
    c, j = _conv("pEf")
    ok(c == 409 and "a_medida" not in _cx["productos"][2], f"un molde del pedido (efímero) tampoco ({c})")
    # 🔴 EL NOMBRE Y EL NÚMERO NO SALEN DEL MARGEN (regla del usuario, MAPA 624)
    _p["a_medida"]["margen"] = {"todos": 2, "der": 5}
    _p["limite_texto"] = {"numero": {"margen_cm": 1, "por_pieza": {"Bandera": None}}, "nombre": {"margen_cm": 8}}
    _lt = S._limite_texto_de(_p)
    # el margen se escribe desde el borde FINAL; el límite del texto se mide desde el contorno, que está
    # la reserva del borde de corte (2 mm) más adentro: 5 cm − 0,2 = 4,8 (2026-10-07)
    ok(_lt.get("*") == {"margen_cm": 4.8}, f"todo campo sin límite propio queda adentro del mayor borde del margen ({_lt.get('*')})")
    ok(_lt["numero"]["margen_cm"] == 4.8 and _lt["numero"]["por_pieza"]["Bandera"] == 4.8,
       "un límite menor que el margen sube al margen (y «sin límite» en la pieza también)")
    ok(_lt["nombre"]["margen_cm"] == 8.0, "uno mayor que el margen se respeta")
    ok(S._limite_texto_de({"limite_texto": {"nombre": {"margen_cm": 1}}}) == {"nombre": {"margen_cm": 1.0}},
       "un molde que no es a medida sigue igual")
    import motor_pedido as _MP
    _pers = {"1": {"Palabra": {"x": 1}, "Número": {"x": 2}}}
    _pc = _MP.pers_con_limite(_pers, _lt)
    ok(_pc["1"]["Palabra"].get("limite_cm") == 4.8 and _pc["1"]["Número"].get("limite_cm") == 4.8,
       "el motor aplica «*» a un campo que el molde no nombra (Palabra) y el suyo al Número")
    _cj = node("import { persConLimite } from './src/motor/pieza/estampar.js';"
               f"console.log(JSON.stringify(persConLimite({json.dumps(_pers)}, {json.dumps(_lt)})))")
    ok(_cj["1"]["Palabra"].get("limite_cm") == 4.8 and _cj["1"]["Número"].get("limite_cm") == 4.8,
       "…y el motor del navegador igual (gemelo `persConLimite`)")
    _camp = [c["clave"] for c in S._campos_de_molde("pSin", _p)]
    ok("*" not in _camp, f"«*» no aparece como un campo en la pantalla ({_camp})")

    # EL NOMBRE DE LA PIEZA se cambia desde «Variables»: lo guardado por pieza pasa al nombre nuevo
    _v = _p["a_medida"]["variable"]
    _p["etiqueta"] = {"posiciones": {_v + "§Bandera": {"rx": 0.2}}}
    _p["telas_cfg"] = {"todas": [], "por_pieza": {"Bandera": ["44"]}}

    def _post(cuerpo):
        with S.app.test_request_context("/api/productos/a_medida", method="POST", json=cuerpo):
            r = S.guardar_a_medida()
        r, c = (r if isinstance(r, tuple) else (r, r.status_code))
        return c, r.get_json()
    c, j = _post({"id": "pSin", "pieza": "Banderín"})
    ok(c == 200 and _p["a_medida"]["pieza"] == "Banderín", f"la pieza pasa a llamarse «Banderín» ({c})")
    ok(_p["etiqueta"]["posiciones"] == {_v + "§Banderín": {"rx": 0.2}} and _p["telas_cfg"]["por_pieza"] == {"Banderín": ["44"]}
       and "Banderín" in _p["limite_texto"]["numero"]["por_pieza"],
       "la etiqueta, las telas y el límite del texto de la pieza la siguen")
    c, j = _post({"id": "pSin", "pieza": "a/b"})
    ok(c == 400 and _p["a_medida"]["pieza"] == "Banderín", f"un nombre con «/» no entra ({c})")
finally:
    S._cargar_catalogo_para_editar, S._guardar_catalogo, S._guard_id = _bk

print("\n4 · LA FILA VA CON LA MEDIDA, aunque la planilla tenga columna de talle")
CAT["plantillas_planillas"].append({"id": "con", "nombre": "Estándar", "columnas": [{"id": "talle", "label": "Talle", "role": "talle"},
                                                                                     {"id": "nombre", "label": "Nombre", "role": "nombre"}]})
c2 = dict(copia, planilla_template_id="con", mapeo_columnas={"talle": "talle", "nombre": "nombre"})
out = S._traducir_prendas([{"nombre": "PEÑAROL", "talle": ""}], c2, CAT, reg=REG)
ok(len(out) == 1 and out[0]["talle"] == "1,50x0,90", f"la fila sale con «1,50x0,90» ({[x.get('talle') for x in out]})")

print("\n5 · LA API DEL OTRO SISTEMA")
for cod in ("medida-falta", "medida-invalida", "tela-no-entra"):
    ok(cod in IE.ALARMAS, f"existe la alarma `{cod}`")
telas = {"1": CAT["telas"][0], "2": CAT["telas"][1]}
A = []
r1 = IE._medida_del_pedido({}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(r1 is None and A and A[-1]["codigo"] == "medida-falta", "sin medida → `medida-falta`")
A = []
r2 = IE._medida_del_pedido({"medida": {"ancho_m": "x", "alto_m": 1}}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(r2 is None and A and A[-1]["codigo"] == "medida-invalida", "medida rara → `medida-invalida`")
A = []
r3 = IE._medida_del_pedido({"medida": {"ancho_m": 3, "alto_m": 2}}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(r3 is None and A and A[-1]["codigo"] == "tela-no-entra", "3 × 2 m en la tela de 1,60 → `tela-no-entra`")
A = []
r4 = IE._medida_del_pedido({"ancho_m": 1.4, "alto_m": 0.9}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(r4 == {"ancho_m": 1.4, "alto_m": 0.9, "forma": "rectangulo", "orientacion": "abajo", "terminacion": "dobladillo"} and not A,
   f"una medida buena pasa (también con los campos sueltos) ({r4} {A})")
pubx = IE._a_medida_publico_ext(tpl)
ok(pubx and pubx["pieza"] == "Bandera" and pubx["margen_cm"]["arriba"] == 3.0, "la API publica la pieza y el margen del molde a medida")
ok(IE._a_medida_publico_ext(copia) is None, "…y una copia de pedido no se publica")
# 🔴 TODO DESDE EL OTRO SISTEMA (MAPA 644): lo que publica alcanza para pedirlo completo y saber si entra
ok(pubx["medida_minima_m"] == 0.05 and pubx["medida_maxima_m"] == 50.0 and pubx["borde_corte_mm"] == 2.0
   and "tiras" in pubx and pubx["tiras"]["maximo_por_lado"] == 50 and "regla" in pubx["tiras"] and "largo_maximo_cm" in pubx,
   "publica los límites de la medida, el borde, el largo máximo y cómo se piden las tiras")
_t160 = next((x for x in pubx["telas"] if x["id"] == "1"), None)
_ok160, _mot160 = S._cabe_en_tela(3, 2, 0, 157, 2000, 10, "ninguna", margen={"todos": 3})
ok(_t160 and f"entra hasta {str(_t160['entra_hasta_cm']).replace('.', ',')} cm" in (_mot160 or ""),
   f"`entra_hasta_cm` de cada tela es el MISMO número que usa la regla de la pantalla ({_t160} · {_mot160})")
A = []
ok(IE._tiras_del_pedido(None, tpl, CAT, "m", A) is None and not A, "sin `tiras`: las del molde")
_tt = IE._tiras_del_pedido({"lleva": True, "lados": {"arriba": 5, "izquierda": "3"}}, tpl, CAT, "m", A)
ok(_tt == {"activo": True, "lados": {"arriba": 5, "abajo": 0, "izq": 3, "der": 0, "base": 0, "laterales": 0, "alrededor": 0}, "marcar": True} and not A,
   f"`tiras: {{lleva, lados}}` (con «izquierda» y números como texto); lo que no viene es 0 ({_tt})")
ok(IE._tiras_del_pedido(False, tpl, CAT, "m", A) == {"activo": False, "lados": {"arriba": 0, "abajo": 0, "izq": 0, "der": 0, "base": 0, "laterales": 0, "alrededor": 0}},
   "`tiras: false` = no lleva")
for _malo in ({"arriba": "x"}, {"norte": 2}, {"lados": {"abajo": 51}}, "cinco"):
    A = []
    IE._tiras_del_pedido(_malo, tpl, CAT, "m", A)
    ok(A and A[-1]["codigo"] == "tiras-invalidas" and A[-1]["frena"], f"`tiras: {_malo}` → `tiras-invalidas`")
A = []
IE._tiras_del_pedido({"arriba": 3}, {**tpl, "a_medida": {**tpl["a_medida"], "margen": {"todos": 0}}}, CAT, "m", A)
ok(A and A[-1]["codigo"] == "tiras-sin-margen", "tiras en un lado sin margen → `tiras-sin-margen`")
with S.app.test_request_context(json={"molde": "prod_tpl", "ancho_m": 1.5, "alto_m": 0.9, "tiras": {"arriba": 4, "abajo": 4}}):
    _rc = IE.v1_a_medida_calcular()
_rj, _rs = (_rc[0].get_json(), _rc[1]) if isinstance(_rc, tuple) else (_rc.get_json(), 200)
ok(_rs == 200 and _rj["total_cm"] == {"ancho": 156.0, "alto": 96.0} and _rj["entra_en_alguna"]
   and _rj["tiras"]["total_marcas"] == 2 + 2 and any(x["lado"] == "arriba" and x["cada_cm"] == 50.0 for x in _rj["tiras"]["por_lado"])
   and any(f["etiqueta"] == "Tiras" for f in _rj["ficha"]),
   f"`POST /a_medida/calcular`: total, en qué telas entra, las tiras (cuántas, cada cuánto) y la ficha ({_rj.get('total_cm')}, {_rj.get('tiras')})")
with S.app.test_request_context(json={"molde": "prod_tpl", "ancho_m": 3, "alto_m": 2, "tela": "1"}):
    _rc = IE.v1_a_medida_calcular()
_rj = (_rc[0] if isinstance(_rc, tuple) else _rc).get_json()
ok(len(_rj["telas"]) == 1 and not _rj["telas"][0]["entra"] and "lo máximo es" in (_rj["telas"][0]["motivo"] or ""),
   "con una tela donde no entra: dice que no, cuánto se pasa y lo máximo")
ok('_tp = (_m0 or {}).get("tiras")' in io.open(os.path.join(_AQUI, "integracion_externa.py"), encoding="utf-8").read(),
   "el robot le pone a la copia del pedido las tiras que mandó el otro sistema")
src = io.open(os.path.join(_AQUI, "integracion_externa.py"), encoding="utf-8").read()
ok("/api/externo/robot/a_medida/<ref>" in src and "/api/externo/robot/a_medida/<ref>/listo" in src,
   "el robot tiene por dónde pedir la copia a medida")
rob = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "robot", "robot.mjs"), encoding="utf-8").read()
ok("armarCopiaAMedida" in rob and rob.count("armarCopiaAMedida(") >= 3, "el robot arma la copia en el pedido y en la plantilla")
srv = io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
# MAPA 692 (regla del usuario 2026-10-13: «nada del uso depende del servidor»): el plan YA NO frena; lo decide
# la pantalla (`amEnTela`) y el pedido del otro sistema lo valida la API (`tela-no-entra`, arriba)
ok('"la pieza no entra en la tela"' not in srv and "_a_medida_telas_que_no_entran" not in srv,
   "el servidor ya no decide si la pieza entra: no hay freno 409 en el plan")

print("\n6 · LA PLANTILLA: el margen punteado aparte")
pl = node("import { planIllustrator } from './src/motor/molde/illustrator.js';"
          "const segs = [['m',0,0],['l',425.2,0],['l',425.2,255.1],['l',0,255.1],['h']];"
          "const cd = [{ talle: '1,50x0,90', items: [{ segs, nombre: 'Bandera', ccx: 212.6, ccy: 127.55, wC: 425.2, hC: 255.1 }] }];"
          "const r = planIllustrator(cd, { dobladillo: { arriba: 3, abajo: 3, izq: 3, der: 3 } });"
          "const p = r.plan.caminos.filter(k => k.punteado);"
          "console.log(JSON.stringify({ n: p.length, enSvg: (r.plan.svg.match(/<path /g) || []).length,"
          " total: r.plan.caminos.length }))")
# 🔴 LAS DOS GUÍAS (2026-10-07, «a la bandera le falta una guía en Illustrator y en Corel»): el contorno
# (tamaño completo) Y el margen (dónde queda el diseño) van IGUAL — caminos sin `punteado` y en el SVG —
# así la extensión vuelve guía a los dos con cualquier versión instalada (como `punteado` dependía del
# conector: Illustrator 1.27 lo dejaba como arte y Corel 1.4 no lo conocía).
ok(pl["total"] == 2 and pl["n"] == 0, f"la mesa lleva DOS caminos de guía (contorno + margen) y ninguno punteado ({pl})")
ok(pl["enSvg"] == pl["total"], "los dos van en el SVG que la extensión vuelve guía")
ga = node("import { aiGuiaMedidas } from './src/motor/molde/herramientas.js';"
          "const segs = [['m',0,0],['l',425.2,0],['l',425.2,255.1],['l',0,255.1],['h']];"
          "const cd = [{ talle: '1,50x0,90', items: [{ segs, nombre: 'Bandera', ccx: 212.6, ccy: 127.55, wC: 425.2, hC: 255.1, dobladillo: { arriba: 3, abajo: 3, izq: 3, der: 3 } }] }];"
          "import { cajaGuia } from './src/motor/molde/herramientas.js';"
          "const t = new TextDecoder('latin1').decode(aiGuiaMedidas(cd, {}));"
          "console.log(JSON.stringify({ caja: (t.match(/\\[8 6\\] 0 d/g) || []).length,"
          " r: cajaGuia(cd[0].items[0], cd[0].items[0].dobladillo).map(v => Math.round(v * 10) / 10),"
          " sin: cajaGuia({ ...cd[0].items[0] }, null).map(v => Math.round(v * 10) / 10) }))")
# 🔴 LA CAJA DEL DISEÑO = EL MARGEN (decisión del usuario 2026-10-07): la línea punteada de «Plantilla» y de
# la guía .ai es el margen (3 cm = 85 pt adentro de cada borde), no la bandera entera; una sola línea.
ok(ga["caja"] == 1 and ga["r"] == [85.0, 85.0, 340.2, 170.1],
   f"la guía .ai trae el contorno y UNA caja punteada que es el margen ({ga})")
ok(ga["sin"] == [0.0, 0.0, 425.2, 255.1], "un molde que no es a medida sigue con la caja de siempre")
app6 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("if (prodCfg?.a_medida && p.w_cm && p.h_cm) {" in app6 and "const mb = margenSobreContorno(_amP.margen, reservaAM(_amP), _amP.forma, _amP.orientacion, _amP.ancho_m, _amP.alto_m, _amP.terminacion);" in app6,
   "la vista «Plantilla» de Configuración dibuja la caja del diseño en el margen")
jsx = io.open(os.path.join(_AQUI, "extension_illustrator", "com.tizadapro.illustrator", "jsx", "tizada.jsx"), encoding="utf-8").read()
ok("strokeDashes" in jsx and "punteados" in jsx, "la extensión de Illustrator lo dibuja punteado y no como guía")
cs = io.open(os.path.join(_AQUI, "extension_corel", "puente", "ArmarCorel.cs"), encoding="utf-8").read()
ok("Punteado" in cs and "OutlineStyles" in cs, "el puente de CorelDRAW también")

app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
print("\n6b · MARCAS DE TIRAS (MAPA 639/641): por LADO, contando las puntas, del borde a la guía, a distancias iguales")
import motor_pedido as _MP   # noqa: E402
_mg = {"arriba": 3.0, "abajo": 3.0, "izq": 3.0, "der": 3.0}
# «si pongo 5 en un lado son 5 contando las 2 de la punta» (2026-10-08): sólo la izquierda con 5
_s5 = _MP._segmentos_tiras(306.0, 156.0, _mg, {"izq": 5})
ok(_s5 == [(0.0, 0.0, 3.0, 3.0), (0.0, 156.0, 3.0, 153.0), (0.0, 39.0, 3.0, 39.0), (0.0, 78.0, 3.0, 78.0), (0.0, 117.0, 3.0, 117.0)],
   f"5 en un lado = 5 marcas: las 2 de las puntas (en diagonal, a la esquina de la guía) + 3 en el medio, parejas ({_s5})")
ok(len(_MP._segmentos_tiras(306.0, 156.0, _mg, {})) == 0 and len(_MP._segmentos_tiras(306.0, 156.0, _mg, {"arriba": 0, "abajo": 0, "izq": 0, "der": 0})) == 0,
   "en ningún lado: ninguna marca")
_s1 = _MP._segmentos_tiras(306.0, 156.0, _mg, {"abajo": 1})
ok(_s1 == [(153.0, 0.0, 153.0, 3.0)], f"con 1, una sola en el medio del lado ({_s1})")
_s2 = _MP._segmentos_tiras(306.0, 156.0, _mg, {"arriba": 2})
ok(_s2 == [(306.0, 156.0, 303.0, 153.0), (0.0, 156.0, 3.0, 153.0)], f"con 2, sólo las dos puntas de ese lado ({_s2})")
_st = _MP._segmentos_tiras(306.0, 156.0, _mg, {"arriba": 4, "abajo": 4, "izq": 3, "der": 3})
ok(len(_st) == 4 + 2 * 2 + 2 * 1 and len(set(_st)) == len(_st),
   f"en todos: cada esquina UNA sola vez aunque la pidan los dos lados (4 + 2×2 + 2×1 = {len(_st)})")
ok(all((sg[0] == sg[2] or sg[1] == sg[3]) for sg in _st[4:]), "las del medio, perpendiculares al borde")
_sm = _MP._segmentos_tiras(100.0, 50.0, {"arriba": 2.0, "abajo": 0.0, "izq": 0.0, "der": 0.0}, {"arriba": 3, "abajo": 3, "izq": 3})
ok(_sm == [(100.0, 50.0, 100.0, 48.0), (0.0, 50.0, 0.0, 48.0), (50.0, 50.0, 50.0, 48.0)],
   f"un lado sin margen no lleva marcas ({_sm})")
_C = [({"lados": {"arriba": 4, "abajo": 6, "izq": 5, "der": 0}, "color": [0.1, 0.9, 0, 0.05], "grosor_mm": 1.2, "margen": _mg}, 867.4, 442.2),
      ({"lados": {"arriba": 1, "abajo": 0, "izq": 7, "der": 2}, "color": [0, 0, 0, 1], "grosor_mm": 0.5,
        "margen": {"arriba": 2, "abajo": 0, "izq": 1.5, "der": 4}}, 8674.0, 4422.7)]
_tj = node("import { opsTiras, componerBase, configBorde } from './src/motor/pieza/base.js';"
           f"const C = {json.dumps(_C)};"
           "const bc = configBorde({ activo: true, ancho_mm: 2, tiras: C[0][0] });"
           "const cb = componerBase(bc, {}, 1, 'CLIP', 100, 50, 'ARTE');"
           "console.log(JSON.stringify({ o: C.map(([t, W, H]) => opsTiras(t, W, H)), cb,"
           " fin: opsTiras(C[0][0], 100 + 2 * bc.B, 50 + 2 * bc.B) }))")
ok(_tj["o"] == [_MP._ops_tiras(t, W, H) for t, W, H in _C] and all(_tj["o"]),
   "gemelos: el navegador (`opsTiras`) escribe EXACTO el mismo trazo que el servidor (`_ops_tiras`)")
ok(_tj["cb"].endswith(_tj["fin"]) and "ARTE" in _tj["cb"] and _tj["cb"].index("ARTE") < len(_tj["cb"]) - len(_tj["fin"]),
   "el motor del navegador las pone ENCIMA del diseño y del borde, en la página entera (el total de la pieza)")
_mpsrc = io.open(os.path.join(_AQUI, "motor_pedido.py"), encoding="utf-8").read()
ok('_base_stream += _ops_tiras(_bc.get("tiras"), W, H, B)' in _mpsrc, "y el motor del servidor también")
_pt = {"id": "pt", "a_medida": {"margen": {"todos": 3}},
       "marcas_tiras": {"activo": True, "lados": {"izq": "5", "arriba": 99}, "color": [1, 0, 0, 0], "grosor_mm": "1,5"}}
_td = S._tiras_de(_pt)
ok(_td == {"lados": {"arriba": 50, "abajo": 0, "izq": 5, "der": 0, "base": 0, "laterales": 0, "alrededor": 0},
           "color": [0.0, 0.0, 0.0, 1.0], "grosor_mm": 1.5,   # el color guardado se ignora: negra con contorno blanco (MAPA 682)
           "margen": {"arriba": 3.0, "abajo": 3.0, "izq": 3.0, "der": 3.0}, "forma": "rectangulo", "orientacion": "abajo",
           "marcar": True, "terminacion": "dobladillo", "recorte": True, "diseno_cm": [100.0, 100.0]},
   f"el servidor arma lo que lee el motor (por lado, acotado, margen por lado) ({_td})")
ok(S._tiras_limpias({"activo": True, "verticales": 3, "horizontales": 0})["lados"] == {"arriba": 2, "abajo": 2, "izq": 5, "der": 5,
                                                                                    "base": 0, "laterales": 0, "alrededor": 0},
   "lo guardado con la forma vieja (sin las puntas, esquinas siempre) se traduce: N + 2")
ok(S._borde_de(_pt).get("tiras") == _td, "y viaja con el borde que rige (preview, tizada y robot leen lo mismo)")
ok(S._tiras_de({**_pt, "marcas_tiras": {"activo": False}}) is None and "tiras" not in S._borde_de({**_pt, "marcas_tiras": {"activo": False}}),
   "apagadas, no hay marcas")
ok(S._tiras_de({**_pt, "marcas_tiras": {"activo": True, "lados": {}}}) is None, "prendidas pero en ningún lado: no hay marcas")
ok(S._tiras_de({**_pt, "a_medida": {"margen": {"todos": 0}}}) is None, "sin margen no hay guía: no hay marcas")
ok(S._tiras_de({"id": "x", "marcas_tiras": {"activo": True, "lados": {"izq": 2}}}) is None, "un molde que no es a medida no lleva marcas")
# 🔴 GROSOR Y COLOR SON DEL MOLDE (MAPA 642): la copia del pedido elige si lleva y en qué lados, pero el grosor
# y el color los toma de la plantilla AHORA (cambiarlos en Ajustes llega a las copias ya armadas)
_ctpl = {"id": "tpl_t", "a_medida": {"margen": {"todos": 2}}, "marcas_tiras": {"activo": False, "grosor_mm": 2.5, "color": [0, 1, 0, 0]}}
_ccop = {"id": "cop_t", "a_medida": {"margen": {"todos": 2}, "de": "tpl_t"},
         "marcas_tiras": {"activo": True, "lados": {"abajo": 3}, "grosor_mm": 1, "color": [0, 0, 0, 1]}}
_tc = S._tiras_de(_ccop, {"productos": [_ctpl, _ccop]})
ok(_tc and _tc["grosor_mm"] == 2.5 and _tc["color"] == [0.0, 0.0, 0.0, 1.0] and _tc["lados"]["abajo"] == 3,
   f"la copia del pedido: lados propios, grosor del molde, la marca siempre negra ({_tc})")
# 🔴 LA FICHA TÉCNICA DEL MOLDE A MEDIDA (MAPA 643): medida, total, margen, borde y las tiras con cuántas y
# cada cuánto (sobre el borde, de punta a punta), de la MISMA geometría que imprime el motor
_cf = {"id": "cop_f", "a_medida": {"ancho_m": 3, "alto_m": 1.5, "margen": {"todos": 3}, "de": "tpl_t"},
       "borde_corte": {"activo": True, "ancho_mm": 2},
       "marcas_tiras": {"activo": True, "lados": {"arriba": 5, "abajo": 5, "izq": 1, "der": 0}}}
_fa = S._ficha_a_medida(_cf, {"productos": [_ctpl, _cf]})
_fv = {f["etiqueta"]: f["valor"] for f in (_fa or {}).get("filas", [])}
ok(_fv.get("Medida del diseño (guía)") == "300 × 150 cm" and _fv.get("Total del arte (con el margen)") == "306 × 156 cm"
   and _fv.get("Terminación") == "Dobladillo · 3 cm por lado · esquinas recortadas" and _fv.get("Borde de corte") == "2 mm, adentro de la medida total",
   f"la ficha dice la medida del diseño, el total con el margen, el margen y el borde ({_fv})")
# (MAPA 653) con dobladillo el rectángulo lleva las esquinas recortadas: la esquina no lleva marca y las
# distancias se miden sobre la guía (300 ÷ 4 = 75)
ok(_fv.get("Tiras", "").startswith("7 marcas en total · grosor 2,5 mm · negra con contorno blanco")
   and _fv.get("Arriba") == "5 marcas contando las 2 puntas, una cada 75 cm · marca de 3 cm"
   and _fv.get("Izquierda") == "1 marca, en el medio (a 75 cm de cada punta) · marca de 3 cm" and "Derecha" not in _fv,
   f"y las tiras: cuántas en total (sin las esquinas recortadas), por lado cuántas y cada cuánto se cosen ({_fv.get('Tiras')})")
ok(S._ficha_a_medida({"id": "n", "nombre": "Buzo"}) is None, "un molde que no es a medida no agrega la sección")
import ficha_tecnica as _FT   # noqa: E402
_fdir = os.path.join(_TMP, "ficha_am"); os.makedirs(_fdir, exist_ok=True)
_pz = fitz.open(); _pz.new_page(width=306 * 28.3465, height=156 * 28.3465); _pzb = _pz.tobytes(); _pz.close()
_rf = _FT.generar_ficha(_fdir, "Ficha técnica", "Bandera", {"columnas": [{"id": "c", "label": "Cantidad"}], "filas": [{"c": 1}]},
                        [{"nombre": "Bandera 3,00x1,50", "diseno": "Principal", "piezas": [{"nombre": "Bandera", "w_cm": 306, "h_cm": 156, "pdf": _pzb}],
                          "a_medida": _fa}])
_ftx = "".join(pg.get_text() for pg in fitz.open(_rf))
ok("MEDIDA Y TERMINACIÓN" in _ftx and "una cada 75 cm" in _ftx and "306 × 156 cm" in _ftx,
   "la ficha impresa trae la sección «MEDIDA Y TERMINACIÓN»")
_png = os.environ.get("FICHA_AM_PNG")
if _png:
    fitz.open(_rf)[0].get_pixmap(matrix=fitz.Matrix(1.6, 1.6)).save(_png)
_app_g = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok('data-tour="tiras-grosor">Grosor de la marca (mm)' in _app_g and "const fijarGrosor = (txt) =>" in _app_g
   and _app_g.index('data-tour="tiras-grosor"') < _app_g.index('data-tour="tiras-activo"'),
   "el grosor se elige en Ajustes › Marcas de tiras, siempre a la vista (antes sólo con las marcas prendidas) y se puede escribir 0,5")
ok("marcas_tiras" not in S._AM_NO_COPIAR, "la copia del pedido hereda las marcas de la plantilla")
_app_t = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("{ id: 'tiras', icon: 'tiras', label: 'Marcas de tiras'" in _app_t and "<TirasAMedida " in _app_t
   and "tirasAMedida={(_amIt && _amIt.de && _amTirasVer)" in _app_t and "<MarcasTirasSVG tiras={_tr}" in _app_t
   and "tiras={_amTirasVer}" in _app_t,
   "la herramienta «Marcas de tiras» (sólo a medida) y las marcas en los tres visores: Ajustes, el paso Arte y la medida escrita")
# 🔴 EN EL PEDIDO (MAPA 640): «Lleva tiras» y cuántas por lado en el panel de la medida; el visor las dibuja
# con lo elegido SIN esperar (sin el render viejo del motor mientras no vuelve guardado) y se guardan en la COPIA
ok('data-tour="arte-tiras-activo"' in _app_t and 'ancla="arte-tiras-lados"' in _app_t and 'ancla="tiras-lados"' in _app_t and "guardarTirasPedido(_id, _amKey, v)" in _app_t
   and "body: JSON.stringify({ id: mid, marcas_tiras: valor })" in _app_t and "(_amDesfase || _amTirasPend) ? null" in _app_t
   and "tirasAMedida={(_amIt && _amIt.de && _amTirasVer)" in _app_t,
   "en el pedido se elige si lleva tiras y cuántas; el visor las muestra al instante y se guardan en la copia del pedido")

print("\n7 · LA PANTALLA")
for ancla, que in (("molde-tipo", "«Con archivo / A medida» al crear el molde"), ("a-medida-panel", "el panel de Moldería del molde a medida"),
                   ("arte-medida", "la tarjeta de la medida en el paso Arte"), ("arte-dobladillo", "la línea punteada en el visor"),
                   ("arte-medida-tela", "la tela se elige con la medida (MAPA 634)"),
                   ("arte-medida-visor", "el visor en vivo de la medida: tela, total del arte y guía del diseño (MAPA 634)"),
                   ("a-medida-convertir", "«Pasar a medida» en Moldería, para un molde que todavía no tiene archivo"),
                   ("a-medida-margen-guardar", "el margen en su propia herramienta"),
                   ("texto-dobladillo", "«Nombre y número» dice que el texto no pasa el margen")):
    ok(f'data-tour="{ancla}"' in app, que)
ok("telasNoEntranDet" in app and "_amTelaNoEntra" in app, "la tela donde no entra no se ofrece y frena el paso")
# 🔴 ELEGIDO SIGUE ELEGIDO (MAPA 677, bug del usuario 2026-10-12: «lo selecciono y se deselecciona; lo toco de nuevo y
# queda dos veces»): la copia a medida reemplaza a la plantilla en el diseño; para mostrar y elegir cuenta como ella
ok("const varsVistasDe = (did) => [...new Set(varsDeDiseno(did).map(_claveOrigen))];" in app
   and "const enActivo = !!_dDest && varsVistasDe(_dDest).includes(v.clave);" in app
   and "if (_suyas.length) _suyas.forEach(c => s.delete(c)); else s.add(clave);" in app
   and "queda.push(cs.find(c => c !== o) || cs[0]);" in app,
   "la tarjeta del molde a medida sigue marcada con su copia; tocarla la saca (con sus copias) y lo doble se limpia")
# (MAPA 678) apagado, pero diciendo por qué: el botón de cargar el arte muestra el giro y «Armando la medida…»
ok("Armando la medida…" in app and "@keyframes spin" in open(os.path.join("frontend", "src", "index.css"), encoding="utf-8").read(),
   "mientras se arma la medida, «Cargar arte» dice «Armando la medida…» con el giro (no queda mudo)")
# (MAPA 679) EL NOMBRE DE LA COPIA LLEVA LA MEDIDA DE AHORA, no la primera con la que se armó
_cat679 = {"plantillas_planillas": [], "productos": [
    {"id": "pl", "nombre": "Bandera", "a_medida": {"pieza": "Bandera", "ancho_m": 1, "alto_m": 1}},
    {"id": "cp", "nombre": "Bandera 1,00x1,00", "efimero": True, "a_medida": {"de": "pl", "pieza": "Bandera", "ancho_m": 3, "alto_m": 1.45}},
    {"id": "otro", "nombre": "Camiseta"}]}
S._normalizar_catalogo(_cat679)
_n679 = {p["id"]: p["nombre"] for p in _cat679["productos"]}
ok(_n679 == {"pl": "Bandera", "cp": "Bandera 3,00x1,45", "otro": "Camiseta"} and not S._normalizar_catalogo(_cat679),
   f"la copia se llama con su medida actual («Bandera 3,00x1,45»), la plantilla y los demás no cambian ({_n679})")
ok("_normalizar_catalogo(cat)   # el nombre de la copia toma la medida nueva (MAPA 679)" in open("servidor.py", encoding="utf-8").read(),
   "cambiar la medida renombra la copia en el mismo guardado")
# (MAPA 682) LA MARCA DE TIRA: NEGRA CON CONTORNO BLANCO, sin elegir color (reemplaza a 680/681). Gemelos py/js: primero
# la línea BLANCA más ancha (`TIRA_CONTORNO_MM` de cada lado), encima la NEGRA con su grosor
_tir682 = {"lados": {"arriba": 3}, "grosor_mm": 1.0, "margen": {"arriba": 2, "abajo": 2, "izq": 2, "der": 2}, "forma": "rectangulo",
           "color": [0, 1, 1, 0], "recorte": True, "diseno_cm": [100.0, 100.0]}
_op682 = _MP._ops_tiras(_tir682, 104 * _MP.CM, 104 * _MP.CM, 0.0)
_wb682 = (1.0 + 2 * _MP.TIRA_CONTORNO_MM) * _MP.MM
ok(_op682.count("0 0 0 0 K") == 1 and _op682.count("0 0 0 1 K") == 1 and _op682.index("0 0 0 0 K") < _op682.index("0 0 0 1 K")
   and f"{_wb682:.3f} w" in _op682 and "0 1 1 0 K" not in _op682,
   "el motor dibuja la marca blanca (más ancha) y encima la negra; el color guardado no se usa")
_js682 = open(os.path.join("frontend", "src", "motor", "pieza", "base.js"), encoding="utf-8").read()
ok("export const TIRA_CONTORNO_MM = 0.4" in _js682 and _MP.TIRA_CONTORNO_MM == 0.4 and "0 0 0 0 K" in _js682 and "0 0 0 1 K" in _js682,
   "el gemelo del navegador dibuja igual (mismo contorno)")
ok('data-tour="arte-tiras-color' not in app and 'data-tour="tiras-color"' not in app and "color_propio" not in app
   and "onElegirColor" not in app and "sw('tira', '#000000')" in app and "const swb = sw + 2 * TIRA_CONTORNO_MM * k;" in app,
   "sin elegir color (ni en Ajustes ni en el pedido); el visor y la leyenda la muestran negra con contorno blanco")
import integracion_externa as _IE682
_A682 = []
_IE682._tiras_del_pedido({"lleva": True, "arriba": 2, "color_cmyk": [0, 1, 1, 0]}, {"a_medida": {}, "marcas_tiras": {}}, {"productos": []}, "m", _A682, "rectangulo", "sin")
ok(any((x.get("codigo") if isinstance(x, dict) else "") == "tiras-invalidas" for x in _A682),
   "por la API ya no se manda color: `color_cmyk` en las tiras → `tiras-invalidas`")
ok("panelIzquierdo={_amIt ? _panelMedida" in app,
   "la medida queda a la vista al lado del visor (en lugar de los talles de la plantilla), armado o no")
# 🔴 SIN ARMAR, LA MISMA PANTALLA (MAPA 676, reclamo del usuario 2026-10-12: «¿por qué volviste a romper este espacio?»):
# mientras la copia se arma de fondo se ve el paso de siempre —cabecera con sus botones, visor y panel de diseños—, con
# el dibujo de la forma en el visor; lo que necesita la copia espera apagado. Nunca una tarjeta aparte sin barra.
# (MAPA 695) y SIN ESPERAR al servidor: «Cargar arte» ya no se apaga por la copia — la copia se arma al cargar el arte
ok("{(_moldeListo || (_amIt && !_amIt.de)) ? (" in app and "visorReemplazo={_amSinArmar ? _visorMedida : null}" in app
   and "disabled={!!amArmando} title={amArmando ?" in app and "onCargarDiseno={() => fileInputArteRef.current.click()}" in app
   and "disabled={!!amArmando || _amSinArmar}" not in app and "{(_amIt && !_amIt.de) ? (" not in app,
   "sin armar todavía: la pantalla de siempre con sus botones, y «Cargar arte» se puede tocar ya (MAPA 695)")
# 🔴 UN SOLO LUGAR (pedido del usuario 2026-10-07: «usá la misma visual, no lo separes en 2 espacios»): el dibujo de la
# medida va EN el visor del paso, no en una pantalla aparte ni en un dibujito dentro del panel
ok("telaAMedida={_telaVisor}" in app
   and app.count("telaAlrededor(") >= 3 and "_tarjetaMedida" not in app,
   "la medida se dibuja EN el visor del paso: en vivo mientras se escribe y, armada, la misma tela alrededor del arte")
ok("[_claveTelaDis(did, d.id)]: v" in app, "la tela elegida antes de armar pasa a la copia del pedido")
# 🔴 SIN BOTÓN NI LISTA APARTE (pedido del usuario 2026-10-07: «no lo separes en 2; elegir la tela como siempre»): la
# medida se arma sola al dejar de escribir y la tela va por «Asignar telas»
ok("amTimerRef.current = null; amIntentoRef.current = firma;" in app and "armarAMedida(st.did, st.it, st.a, st.h, { forma: st.f, orientacion: st.o, terminacion: st.te, silencioso: true })" in app and "listaParaArmar" in app
   and "Armar a esta medida" not in app and "— Elegí la tela —" not in app,
   "la medida se arma sola (sin botón) y la tela se elige como siempre (sin lista propia en el panel)")
# 🔴 DE ENTRADA, EL PASO COMPLETO (MAPA 637): el visor muestra el molde a medida con la medida PREDETERMINADA de
# Ajustes; la medida se cambia en el panel del paso. (MAPA 695) Ya NO se arma en el servidor al entrar: se dibuja acá
ok("st.lista && st.esCopia && (!!amForm[st.clave] || st.vieja)" in app and "metrosTexto(_amIt.ancho_m || 1)" in app,
   "el molde a medida se ve con la medida predeterminada al entrar al paso Arte, sin armar nada en el servidor")
# 🔴 CAMBIAR LA MEDIDA ES INSTANTÁNEO (MAPA 638): el visor de siempre dibuja la medida escrita al toque
# (`_layoutVivo`) y el archivo se rehace de fondo, SIN el cartel que tapa todo
ok("canvasLayout={_amSinArmar ? null : (_layoutVivo || canvasLayout)}" in app and "previewPiezas={_pvMedida}" in app
   and "const avisar = silencioso ? () => {} : (t) => setProcesando(t);" in app and "!amArmando && !!st" in app,
   "cambiar la medida se ve al instante en el mismo visor y el molde se rehace de fondo, sin cartel")

print("\n8 · CÍRCULOS Y TRIÁNGULOS (MAPA 645): la forma se elige en cada pedido")
import math as _mt
# 8.1 el PDF de cada forma entra por el alta de siempre, con la medida que dice la regla
_FPDF = [("circulo", "abajo", 1.0, 1.0, {"todos": 2}, 2.0), ("triangulo", "abajo", 1.2, 0.8, {"todos": 2}, 2.0),
         ("triangulo", "der", 0.9, 1.4, {"todos": 1.5}, 2.0)]
for _f, _o, _a, _h, _mg, _res in _FPDF:
    _po, _jo = os.path.join(_TMP, f"am_{_f}_{_o}.pdf"), os.path.join(_TMP, f"am_{_f}_{_o}.json")
    r = subprocess.run(["node", "src/motor/pruebas/a_medida.mjs", str(_a), str(_h), "Banderín", _po, _jo, _f, _o, json.dumps(_mg), str(_res)],
                       cwd=os.path.join(_AQUI, "frontend"), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        ok(False, f"{_f} ({_o}): el motor arma el PDF y corre el alta ({r.stderr[-300:]})")
        continue
    _j = json.load(open(_jo, encoding="utf-8"))
    _W, _H = S._medida_pieza(_a, _h, _mg, _f, _o)
    _ii = next(iter(next(iter((_j.get("registro") or {}).values()), {}).values()), {})
    # el círculo se achica la reserva (borde «fuera»); el triángulo NO (su contorno es el total, borde por dentro)
    _ew, _eh = (_W - 2 * _res / 10, _H - 2 * _res / 10) if _f == "circulo" else (_W, _H)
    ok(abs((_ii.get("w_cm") or 0) - _ew) < 0.15 and abs((_ii.get("h_cm") or 0) - _eh) < 0.15 and not _j.get("problemas"),
       f"{_f} ({_o}) {_a}×{_h} m: una pieza de {_ii.get('w_cm')} × {_ii.get('h_cm')} cm (esperado {_ew:.1f} × {_eh:.1f}) por el alta de siempre")
    _pg = fitz.open(_po)[0]
    _pts = [(round(p.x, 1), round(p.y, 1)) for d in _pg.get_drawings() for it in d["items"] for p in it[1:] if hasattr(p, "x")]
    if _f == "circulo":
        _cv = sum(1 for d in _pg.get_drawings() for it in d["items"] if it[0] == "c")
        ok(_cv >= 4, f"el círculo va en CURVAS (vector), no en tramos rectos ({_cv} curvas)")
    else:
        _xs, _ys = [p[0] for p in _pts], [p[1] for p in _pts]
        if _o == "abajo":
            # fitz: y hacia abajo → la punta es lo de y mayor (con el recorte, las dos solapas a los lados de la punta)
            _ab = [p for p in _pts if p[1] > max(_ys) - 0.5]
            _pu = (sum(p[0] for p in _ab) / len(_ab), max(_ys))
            ok(abs(_pu[0] - (min(_xs) + max(_xs)) / 2) < 1, f"punta abajo: la punta queda abajo y al medio ({_pu})")
        else:
            _de = [p for p in _pts if p[0] > max(_xs) - 0.5]
            _pu = (max(_xs), sum(p[1] for p in _de) / len(_de))
            ok(abs(_pu[1] - (min(_ys) + max(_ys)) / 2) < 1, f"punta a la derecha: la punta queda a la derecha y al medio ({_pu})")

# 8.2 gemelos py ↔ js: la pieza, ¿entra?, y las marcas
_CF = [dict(anchoM=1.0, altoM=1.0, margen={"todos": 2}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre", forma="circulo"),
       dict(anchoM=1.6, altoM=1.6, margen={"todos": 1}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre", forma="circulo"),
       dict(anchoM=1.2, altoM=0.8, margen={"todos": 2}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="libre", forma="triangulo", orientacion="abajo"),
       dict(anchoM=1.5, altoM=1.0, margen={"todos": 3}, bordeMm=2, anchoCm=157, largoMaxCm=3000, margenNestingMm=0, rotacion="ninguna", forma="triangulo", orientacion="izq"),
       dict(anchoM=3.0, altoM=1.5, margen={"arriba": 1, "abajo": 4}, bordeMm=0, anchoCm=157, largoMaxCm=3000, margenNestingMm=10, rotacion="90", forma="triangulo", orientacion="arriba")]
_mgT = {"arriba": 3.0, "abajo": 3.0, "izq": 3.0, "der": 3.0}
# (el triángulo con las puntas en INGLETE, MAPA 649: sus marcas salen de la medida del DISEÑO)
_gT = {o: S.MP._geo_triangulo(120.0, 80.0, 3.0, o) for o in ("abajo", "arriba")}
_gV = {o: S.MP._geo_triangulo(80.0, 120.0, 3.0, o) for o in ("izq", "der")}
_TF = [("circulo", "abajo", 104.0, 104.0, {"alrededor": 8}, None), ("circulo", "abajo", 60.0, 60.0, {"alrededor": 1}, None),
       ("triangulo", "abajo", _gT["abajo"]["W"], _gT["abajo"]["H"], {"base": 5, "laterales": 4}, [120.0, 80.0]),
       ("triangulo", "arriba", _gT["arriba"]["W"], _gT["arriba"]["H"], {"base": 1}, [120.0, 80.0]),
       ("triangulo", "izq", _gV["izq"]["W"], _gV["izq"]["H"], {"laterales": 3}, [80.0, 120.0]),
       ("triangulo", "der", _gV["der"]["W"], _gV["der"]["H"], {"base": 1, "laterales": 50}, [80.0, 120.0])]
_jf = node("import { cabeEnTela, medidaPieza, margenSobreContorno } from './src/motor/molde/aMedida.js';"
           "import { segmentosTiras } from './src/motor/molde/tiras.js';"
           "import { opsTiras } from './src/motor/pieza/base.js';"
           "import { segsDobladillo, geoTriangulo } from './src/motor/molde/formas.js';"
           f"const C = {json.dumps(_CF)}; const T = {json.dumps(_TF)}; const M = {json.dumps(_mgT)};"
           "const tir = (f, o, l, d) => ({ lados: l, color: [0, 1, 0.5, 0], grosor_mm: 1.2, margen: M, forma: f, orientacion: o, diseno_cm: d });"
           "console.log(JSON.stringify({"
           " c: C.map(x => cabeEnTela(x)),"
           " p: C.map(x => medidaPieza(x.anchoM, x.altoM, x.margen, x.forma, x.orientacion)),"
           " s: T.map(([f, o, W, H, l, d]) => segmentosTiras(W, H, M, l, f, o, d)),"
           " o: T.map(([f, o, W, H, l, d]) => opsTiras(tir(f, o, l, d), W * 28.3465, H * 28.3465, f === 'triangulo' ? 5.67 : 0)),"
           " msc: [margenSobreContorno({ todos: 3 }, 2, 'circulo'), margenSobreContorno({ arriba: 1, izq: 4 }, 2, 'triangulo', 'der'), margenSobreContorno({ todos: 3 }, 2),"
           "       margenSobreContorno({ todos: 3 }, 2, 'triangulo', 'abajo', 1.2, 0.8)],"
           " dobC: segsDobladillo([0, 0, 100, 100], { arriba: 3, abajo: 3, izq: 3, der: 3, forma: 'circulo' }, 1),"
           " geo: [['abajo', 120, 80], ['arriba', 120, 80], ['izq', 80, 120], ['der', 80, 120]].map(([o, w, h]) => geoTriangulo(w, h, 3, o)),"
           f" dobT: segsDobladillo([0, 0, {_gT['abajo']['W']}, {_gT['abajo']['H']}], {{ arriba: 3, abajo: 3, izq: 3, der: 3, forma: 'triangulo', orientacion: 'abajo', diseno: {{ w: 120, h: 80 }} }}, 1),"
           "}))")
for caso, rj, pj in zip(_CF, _jf["c"], _jf["p"]):
    cabe, mot = S._cabe_en_tela(caso["anchoM"], caso["altoM"], caso["bordeMm"], caso["anchoCm"], caso["largoMaxCm"],
                                caso["margenNestingMm"], caso["rotacion"], margen=caso.get("margen"),
                                forma=caso["forma"], orientacion=caso.get("orientacion", "abajo"))
    Wp, Hp = S._medida_pieza(caso["anchoM"], caso["altoM"], caso["margen"], caso["forma"], caso.get("orientacion", "abajo"))
    ok(cabe == rj["cabe"] and (mot or None) == (rj["motivo"] or None) and abs(Wp - pj["anchoCm"]) < 1e-9 and abs(Hp - pj["altoCm"]) < 1e-9,
       f"{caso['forma']} {caso.get('orientacion', '')} {caso['anchoM']}×{caso['altoM']}: py ({Wp:.2f}×{Hp:.2f}, {cabe}) = js ({pj['anchoCm']:.2f}×{pj['altoCm']:.2f}, {rj['cabe']})"
       + ("" if (mot or None) == (rj["motivo"] or None) else f" · py «{mot}» ≠ js «{rj['motivo']}»"))
ok(_jf["p"][0] == {"anchoCm": 104, "altoCm": 104}, f"círculo de 1 m con 2 cm de margen = Ø 104 cm ({_jf['p'][0]})")
ok(not _jf["c"][1]["cabe"] and "diámetro" in (_jf["c"][1]["motivo"] or ""), f"el círculo que no entra lo dice por el DIÁMETRO ({_jf['c'][1]['motivo']})")
_igual = lambda A, B: len(A) == len(B) and all(abs(u - v) < 1e-9 for p, q in zip(A, B) for u, v in zip(p, q))
_okGeo = all(_igual(S.MP._geo_triangulo(w, h, 3.0, o)["pol"], g["pol"]) and _igual(S.MP._geo_triangulo(w, h, 3.0, o)["guia"], g["guia"])
             for (o, w, h), g in zip((("abajo", 120.0, 80.0), ("arriba", 120.0, 80.0), ("izq", 80.0, 120.0), ("der", 80.0, 120.0)), _jf["geo"]))
ok(_okGeo, "gemelos: el triángulo recortado (contorno y guía) es el mismo en el servidor y en el navegador")
_okSeg = all(_igual(a, b) for a, b in zip([S.MP._segmentos_tiras(W, H, _mgT, l, f, o, d) for f, o, W, H, l, d in _TF], _jf["s"]))
ok(_okSeg, "gemelos: las marcas del círculo y del triángulo son las mismas en el servidor y en el navegador")
_opsPy = [S.MP._ops_tiras({"lados": l, "color": [0, 1, 0.5, 0], "grosor_mm": 1.2, "margen": _mgT, "forma": f, "orientacion": o, "diseno_cm": d},
                          W * S.MP.CM, H * S.MP.CM, 5.67 if f == "triangulo" else 0) for f, o, W, H, l, d in _TF]
ok(_opsPy == _jf["o"] and all(_opsPy), "gemelos: el trazo impreso de las marcas (con la forma) es EXACTO el mismo en los dos motores")
_sc = S.MP._segmentos_tiras(104.0, 104.0, _mgT, {"alrededor": 8}, "circulo")
ok(len(_sc) == 8 and all(abs(_mt.hypot(x1 - 52, y1 - 52) - 52) < 1e-9 and abs(_mt.hypot(x2 - 52, y2 - 52) - 49) < 1e-9 for x1, y1, x2, y2 in _sc)
   and abs(_sc[0][0] - 52) < 1e-9 and _sc[0][1] > 100,
   "círculo: N marcas parejas, del borde hacia el centro el margen, la primera ARRIBA al medio")


# 🔺 EL DOBLEZ (MAPA 649-650, pedido del usuario: «que si lo doblan en la guía del dobladillo no quede sobrante
# hacia afuera» y «que las puntas se unan SUPERPONIÉNDOSE pero que no sobre, así como queda en el rectángulo»):
# cada solapa, reflejada sobre su lado de la guía, cae ADENTRO del triángulo de la guía y, en cada punta, llega
# justo hasta el OTRO lado (se superpone con la solapa vecina)
def _dentro(P, T, tol=1e-6):
    (ax, ay), (bx, by), (cx, cy) = T
    s = lambda x1, y1, x2, y2, x3, y3: (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)
    d1, d2, d3 = s(P[0], P[1], ax, ay, bx, by), s(P[0], P[1], bx, by, cx, cy), s(P[0], P[1], cx, cy, ax, ay)
    return not ((d1 < -tol or d2 < -tol or d3 < -tol) and (d1 > tol or d2 > tol or d3 > tol))


def _refl(P, A, B):
    ux, uy = B[0] - A[0], B[1] - A[1]
    s = ((P[0] - A[0]) * ux + (P[1] - A[1]) * uy) / (ux * ux + uy * uy)
    return (2 * (A[0] + ux * s) - P[0], 2 * (A[1] + uy * s) - P[1])


_dobla_ok, _junta_ok = True, True
for (w, h), o in (((120.0, 80.0), "abajo"), ((120.0, 80.0), "arriba"), ((80.0, 120.0), "izq"), ((80.0, 120.0), "der"),
                  ((300.0, 60.0), "abajo"), ((50.0, 150.0), "der")):
    g = S.MP._geo_triangulo(w, h, 3.0, o)
    G, pol = g["guia"], g["pol"]
    for i in range(3):
        a, b, c = G[i], G[(i + 1) % 3], G[(i + 2) % 3]
        qa, qb = pol[3 * i + 1], pol[3 * i + 2]
        ra, rb = _refl(qa, a, b), _refl(qb, a, b)
        _dobla_ok = _dobla_ok and _dentro(ra, G) and _dentro(rb, G)
        # doblada, la punta de la solapa cae justo sobre el OTRO lado de la guía (salvo una punta de más de
        # 120°, donde las solapas se cortan en el medio del hueco para no pisarse en la tela)
        for r_, v, w_ in ((ra, a, c), (rb, b, c)):
            _ux, _uy, _wx, _wy = w_[0] - v[0], w_[1] - v[1], (b if v is a else a)[0] - v[0], (b if v is a else a)[1] - v[1]
            _cos = (_ux * _wx + _uy * _wy) / (_mt.hypot(_ux, _uy) * _mt.hypot(_wx, _wy))
            if _cos >= -0.5:
                _junta_ok = _junta_ok and abs((r_[0] - v[0]) * _uy - (r_[1] - v[1]) * _ux) < 1e-6
ok(_dobla_ok, "doblado por la guía, el margen del triángulo cae ADENTRO: no sobra nada hacia afuera (6 triángulos, 4 puntas)")
ok(_junta_ok, "…y en cada punta la solapa doblada llega justo al otro lado: se SUPERPONE con la vecina (como la esquina del rectángulo)")
_g0 = S.MP._geo_triangulo(120.0, 80.0, 3.0, "abajo")
ok(len(_g0["pol"]) == 9 and any(abs(p[0] - q[0]) < 1e-9 and abs(p[1] - q[1]) < 1e-9 for p in _g0["pol"] for q in _g0["guia"][2:])
   and (round(_g0["W"], 1), round(_g0["H"], 1)) == (122.1, 84.1) and S._medida_pieza(1.2, 0.8, {"todos": 3}, "triangulo", "abajo") == (_g0["W"], _g0["H"]),
   f"el corte llega a la punta de la guía; 1,20 × 0,80 con 3 cm de margen ocupa {_g0['W']:.1f} × {_g0['H']:.1f} cm (con las puntas enteras eran 132 × 88)")
_st5 = S.MP._segmentos_tiras(_g0["W"], _g0["H"], _mgT, {"base": 5, "laterales": 4}, "triangulo", "abajo", [120.0, 80.0])
_Gp = _g0["guia"]
ok(len(_st5) == 3 + 2 * 2 and not any(abs(x1 - p[0]) < 1e-6 and abs(y1 - p[1]) < 1e-6 for x1, y1, _x2, _y2 in _st5 for p in _Gp),
   f"triángulo: SIN marca en las puntas (el corte ya la marca) y las del medio contando las puntas ({len(_st5)} = 3 + 2×2)")
ok(all(abs(_mt.hypot(x2 - x1, y2 - y1) - 3.0) < 1e-9 for x1, y1, x2, y2 in _st5),
   "las del medio, perpendiculares a la guía y del largo del margen")
ok(len(S.MP._segmentos_tiras(_g0["W"], _g0["H"], _mgT, {"base": 2}, "triangulo", "abajo", [120.0, 80.0])) == 0
   and len(S.MP._segmentos_tiras(_g0["W"], _g0["H"], _mgT, {"base": 1}, "triangulo", "abajo", [120.0, 80.0])) == 1,
   "base con 2 = sólo las puntas (ninguna marca); con 1, una en el medio")
_s50 = _jf["s"][5]
ok(len(_s50) > 50 and all(_mt.hypot(x2 - x1, y2 - y1) <= 3.0 + 1e-9 for x1, y1, x2, y2 in _s50),
   "con muchas marcas, las de cerca de la punta se acortan con el recorte (nunca pasan el corte)")
_c3 = {"arriba": 3, "abajo": 3, "izq": 3, "der": 3}
ok(_jf["msc"][0] == {"arriba": 2.8, "abajo": 2.8, "izq": 2.8, "der": 2.8, "forma": "circulo", "orientacion": "abajo", "costura": _c3}
   and _jf["msc"][1] == {"arriba": 4, "abajo": 4, "izq": 4, "der": 4, "forma": "triangulo", "orientacion": "der", "recorte": True,
                         "costura": {"arriba": 4, "abajo": 4, "izq": 4, "der": 4}}
   and "forma" not in _jf["msc"][2] and _jf["msc"][2].get("costura") == _c3 and _jf["msc"][3].get("diseno") == {"w": 120, "h": 80},
   f"la guía del margen: parejo (el mayor) desde el contorno; el triángulo sin reserva y con la medida del diseño ({_jf['msc']})")
_bxC = [min(s[i] for s in _jf["dobC"] if len(s) > 2 for i in (1, 3, 5) if i < len(s)), max(s[i] for s in _jf["dobC"] if len(s) > 2 for i in (1, 3, 5) if i < len(s))]
ok(_jf["dobC"][1][0] == "c" and abs(_bxC[0] - 3) < 1e-9 and abs(_bxC[1] - 97) < 1e-9,
   "la guía de la plantilla (.ai / PDF / Illustrator / Corel) del círculo es un CÍRCULO el margen adentro")
_ptsT = [(s[1], s[2]) for s in _jf["dobT"] if s[0] in ("m", "l")]
ok(_igual(_ptsT, _g0["guia"]), "…y la del triángulo es EXACTO el triángulo del diseño dentro del contorno recortado")

# 8.3 el servidor: la copia guarda la forma; el triángulo lleva el borde por DENTRO
_tri = {"id": "ptri", "a_medida": {"margen": {"todos": 2}, "ancho_m": 1.2, "alto_m": 0.8, "de": "x", "forma": "triangulo", "orientacion": "izq"}}
_cir = {"id": "pcir", "a_medida": {"margen": {"todos": 2}, "ancho_m": 1, "alto_m": 1, "de": "x", "forma": "circulo"}}
ok(S._reserva_borde_mm(_tri) == 0 and S._reserva_borde_mm(_cir) > 0, "el triángulo no se achica (reserva 0); el círculo sí, como el rectángulo")
ok(S._borde_de(_tri).get("alineacion") == "dentro" and S._borde_de(_cir).get("alineacion") != "dentro",
   "el borde de corte del triángulo va POR DENTRO (si no, la punta en inglete del borde se sale de la página)")
_pubT = S._a_medida_publico(_tri, {"productos": []}) or {}
ok(_pubT.get("reserva_mm") == 0 and (_pubT.get("reserva_borde_mm") or 0) > 0,
   "publica la reserva del borde sin mirar la forma (la pantalla cambia de forma antes de guardarla)")
_fT = S._ficha_a_medida(_tri) or {}
_fC = S._ficha_a_medida(_cir) or {}
ok(any(x["etiqueta"] == "Forma" and "Triángulo" in x["valor"] and "izquierda" in x["valor"] for x in _fT.get("filas", []))
   and any("Ø 100" in x["valor"] for x in _fC.get("filas", [])),
   "la ficha técnica dice la forma (y la punta) y el diámetro del círculo")
_extra, _de, _err = S._a_medida_crear({"a_medida_de": "tplF", "efimero": True, "ancho_m": 1, "alto_m": 1, "forma": "circulo"},
                                      {"productos": [{"id": "tplF", "a_medida": {"pieza": "Bandera", "margen": {"todos": 1}, "ancho_m": 1, "alto_m": 1}}]}, "pnew")
ok(not _err and _extra["a_medida"]["forma"] == "circulo" and _extra["a_medida"]["orientacion"] == "abajo",
   "la copia del pedido guarda la forma elegida (la plantilla no tiene forma: la elige cada pedido)")

# 8.4 la API del otro sistema
A = []
_rc = IE._medida_del_pedido({"forma": "círculo", "medida": {"diametro_m": 1.2}}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(_rc == {"ancho_m": 1.2, "alto_m": 1.2, "forma": "circulo", "orientacion": "abajo", "terminacion": "dobladillo"} and not A,
   f"`forma: círculo` + `diametro_m` (con tilde, como lo escriba) ({_rc} {A})")
A = []
_rt = IE._medida_del_pedido({"medida": {"ancho_m": 1, "alto_m": 0.6, "forma": "triangular", "orientacion": "derecha"}}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(_rt == {"ancho_m": 1.0, "alto_m": 0.6, "forma": "triangulo", "orientacion": "der", "terminacion": "dobladillo"} and not A, f"triángulo con la punta a la derecha, dentro de `medida` ({_rt})")
A = []
ok(IE._medida_del_pedido({"forma": "hexágono", "ancho_m": 1, "alto_m": 1}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A) is None
   and A and A[-1]["codigo"] == "forma-invalida", "una forma que no existe → `forma-invalida`")
A = []
ok(IE._medida_del_pedido({"forma": "triangulo", "orientacion": "costado", "ancho_m": 1, "alto_m": 1}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A) is None
   and A and A[-1]["codigo"] == "forma-invalida", "una punta que no existe → `forma-invalida`")
ok(set(pubx.get("formas") or []) == {"rectangulo", "circulo", "triangulo"} and set(pubx.get("orientaciones_triangulo") or []) == {"abajo", "arriba", "izq", "der"}
   and "lados_por_forma" in (pubx.get("tiras") or {}), "la API publica las formas, las puntas y qué lados de tiras lleva cada una")

# 8.5 la pantalla
app8 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok('data-tour="arte-medida-forma"' in app8 and 'data-tour="arte-medida-punta"' in app8 and "onForma={(fo, or_) =>" in app8
   and "title=\"Diámetro del diseño\"" in app8,
   "en el panel de la medida se elige la forma, la punta del triángulo y, en el círculo, el diámetro")
ok("forma: fo, orientacion: or_, terminacion: te, geo_v: versionGeo(fo) }) });" in app8 and "forma: fo, orientacion: or_, terminacion: te }, avisar);" in app8,
   "la forma viaja al servidor y al PDF que arma esta computadora")
ok("_amOtraForma" in app8 and "pathForma(contornoForma(_amFo, _amOr" in app8,
   "cambiar la forma se ve al instante en el visor (el contorno con la forma nueva), como la medida")
ok(app8.count("<GuiaMargenSVG") >= 2 and "tri: _amFo === 'triangulo'" in app8 and "formaD" in app8 and "_amEst.a, _amEst.h, _amTe) : null}" in app8,
   "la guía del margen, la tela y la caja de «Plantilla» se dibujan con la forma")
ok('forma="todas"' in app8 and "forma={f} ancla=\"arte-tiras-lados\"" in app8,
   "tiras: en el pedido, los lados de SU forma; en Ajustes, los de las tres")
_herr = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "molde", "herramientas.js"), encoding="utf-8").read()
_illu = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "molde", "illustrator.js"), encoding="utf-8").read()
ok("segsDobladillo" in _herr and "segsDobladillo(cajaSegs(segs), dobladillo, PT_POR_CM)" in _illu,
   "las plantillas (.ai, PDF de medidas, Illustrator y Corel) dibujan la guía con la forma")

# 8.6 🔴 LA COPIA ARMADA CON UNA GEOMETRÍA VIEJA SE REARMA SOLA (MAPA 651): un triángulo armado con el inglete
# (649) mostraba en Illustrator la guía de la 650 — el archivo no se rehace solo al cambiar el dibujo
_gv = node("import { versionGeo, geoVieja, GEO_VERSION } from './src/motor/molde/aMedida.js';"
           "console.log(JSON.stringify({ t: versionGeo('triangulo'), r: versionGeo('rectangulo'),"
           " vieja: geoVieja({ de: 'x', forma: 'triangulo', geo_v: 2 }), sinSello: geoVieja({ de: 'x', forma: 'triangulo' }),"
           " hoy: geoVieja({ de: 'x', forma: 'triangulo', geo_v: GEO_VERSION.triangulo }), rect: geoVieja({ de: 'x' }), rectHoy: geoVieja({ de: 'x', geo_v: GEO_VERSION.rectangulo }), tpl: geoVieja({ forma: 'triangulo' }) }))")
ok(_gv["t"] >= 3 and _gv["r"] >= 2 and _gv["vieja"] and _gv["sinSello"] and not _gv["hoy"] and _gv["rect"] and not _gv["rectHoy"] and not _gv["tpl"],
   f"una copia armada con una geometría vieja (o sin sello: el rectángulo de antes de las esquinas recortadas) se detecta; la de hoy y la plantilla no ({_gv})")
ok("(Number(am.geo_v) || 1) === versionGeo(f)" in app8 and "|| st.vieja)" in app8 and "vieja: geoVieja(_amIt)" in app8
   # (MAPA 664) la versión viaja en el mismo pedido que crea la copia o le cambia la medida (antes, un POST más)
   and app8.count("terminacion: te, geo_v: versionGeo(fo) }) });") == 2 and "anotarGeo" not in app8
   and 'extra["a_medida"]["geo_v"] = max(1, min(1000, int(cuerpo.get("geo_v"))))' in io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
   and "geoVieja(_amIt)) || normTerminacion(_amIt.terminacion) !== _amTe));" in app8,
   "el paso Arte la rearma solo (sin escribir nada), la dibuja ya con la geometría nueva y anota con cuál quedó")
_ps = io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
ok('am["geo_v"] = max(1, min(1000, int(cuerpo.get("geo_v"))))' in _ps, "el servidor guarda con qué geometría se armó (`geo_v`)")

print("\n9 · TERMINACIÓN DEL BORDE Y TIRAS SIN MARCAR (MAPA 652)")
# 9.1 gemelos py ↔ js: el triángulo con overlock (puntas enteras), la pieza y sus marcas
_mg9 = {"arriba": 1.0, "abajo": 1.0, "izq": 1.0, "der": 1.0}
_j9 = node("import { geoTriangulo, trianguloCorrido, verticesTriangulo } from './src/motor/molde/formas.js';"
           "import { medidaPieza, cabeEnTela, margenDeTerminacion, normTerminacion, margenSobreContorno } from './src/motor/molde/aMedida.js';"
           "import { segmentosTiras } from './src/motor/molde/tiras.js';"
           "const g = geoTriangulo(120, 80, 1, 'abajo', false);"
           "console.log(JSON.stringify({ g,"
           " p: [medidaPieza(1.2, 0.8, { todos: 1 }, 'triangulo', 'abajo', 'overlock'), medidaPieza(1.2, 0.8, { todos: 3 }, 'triangulo', 'abajo', 'dobladillo'),"
           "     medidaPieza(1.2, 0.8, { todos: 0 }, 'triangulo', 'abajo', 'sin'), medidaPieza(3, 1.5, { todos: 1 }, 'rectangulo', 'abajo', 'overlock')],"
           f" s: segmentosTiras(g.W, g.H, {json.dumps(_mg9)}, {{ base: 5, laterales: 4 }}, 'triangulo', 'abajo', [120, 80], false),"
           " c: cabeEnTela({ anchoM: 1.5, altoM: 1.5, margen: { todos: 1 }, bordeMm: 2, anchoCm: 157, largoMaxCm: 3000, rotacion: 'libre', forma: 'triangulo', terminacion: 'overlock' }),"
           " md: [margenDeTerminacion({ margen: { todos: 3 }, overlock_cm: 0.8 }, 'overlock'), margenDeTerminacion({ margen: { todos: 3 } }, 'sin'),"
           "      margenDeTerminacion({ margen: { todos: 1 }, margen_dobladillo: { todos: 3 }, terminacion: 'overlock' }, 'dobladillo'),"
           "      margenDeTerminacion({ margen: { todos: 3 } }, 'overlock')],"
           " nt: [normTerminacion('overlock'), normTerminacion('nada')],"
           " msc: margenSobreContorno({ todos: 1 }, 2, 'triangulo', 'abajo', 1.2, 0.8, 'overlock'),"
           "}))")
_g9 = S.MP._geo_triangulo(120.0, 80.0, 1.0, "abajo", False)
_P9 = S.MP._triangulo_corrido(S.MP._vertices_triangulo(0.0, 0.0, 120.0, 80.0, "abajo"), 1.0)
ok(_igual(_g9["pol"], _j9["g"]["pol"]) and len(_g9["pol"]) == 3
   and abs(_g9["W"] - (max(p[0] for p in _P9) - min(p[0] for p in _P9))) < 1e-9,
   "overlock: el triángulo ENTERO corrido el margen (sin recortes), igual en los dos motores")
_p9 = [S._medida_pieza(1.2, 0.8, {"todos": 1}, "triangulo", "abajo", "overlock"), S._medida_pieza(1.2, 0.8, {"todos": 3}, "triangulo", "abajo", "dobladillo"),
       S._medida_pieza(1.2, 0.8, {"todos": 0}, "triangulo", "abajo", "sin"), S._medida_pieza(3, 1.5, {"todos": 1}, "rectangulo", "abajo", "overlock")]
ok(all(abs(a[0] - b["anchoCm"]) < 1e-9 and abs(a[1] - b["altoCm"]) < 1e-9 for a, b in zip(_p9, _j9["p"]))
   and _p9[2] == (120.0, 80.0) and _p9[3] == (302.0, 152.0),
   f"la pieza con cada terminación es la misma en los dos (sin margen = el diseño; rectángulo overlock 1 cm = 302 × 152) ({_p9})")
_s9 = S.MP._segmentos_tiras(_g9["W"], _g9["H"], _mg9, {"base": 5, "laterales": 4}, "triangulo", "abajo", [120.0, 80.0], False)
ok(_igual(_s9, _j9["s"]) and len(_s9) == 3 + 3 + 2 * 2
   and all(abs(_s9[i][0] - _g9["pol"][i][0]) < 1e-9 for i in range(3)),
   f"overlock: el triángulo lleva marca en las 3 puntas (en diagonal) + las del medio ({len(_s9)} = 3 + 3 + 2×2), gemelas")
_c9 = S._cabe_en_tela(1.5, 1.5, 2, 157, 3000, 0, "libre", margen={"todos": 1}, forma="triangulo", terminacion="overlock")
ok(_c9[0] == _j9["c"]["cabe"] and (_c9[1] or None) == (_j9["c"]["motivo"] or None), "¿entra en la tela? con la terminación: gemelos")
ok(_j9["md"] == [{"todos": 0.8}, {"todos": 0}, {"todos": 3}, {"todos": 1}] and _j9["nt"] == ["overlock", "dobladillo"]
   and _j9["msc"].get("recorte") is False,
   f"el margen que rige con cada terminación (overlock del molde o 1 cm, sin = 0, dobladillo guardado en la copia) ({_j9['md']})")
ok(S._margen_de_terminacion({"margen": {"todos": 3}, "overlock_cm": 0.8}, "overlock") == {"todos": 0.8}
   and S._margen_de_terminacion({"margen": {"todos": 3}}, "sin") == {"todos": 0.0}
   and S._margen_de_terminacion({"margen": {"todos": 1}, "margen_dobladillo": {"todos": 3}}, "dobladillo")["todos"] == 3.0,
   "…y el servidor da lo mismo")
# 9.2 la copia guarda la terminación y los dos márgenes
_ex9, _de9, _er9 = S._a_medida_crear({"a_medida_de": "tplT", "efimero": True, "ancho_m": 1, "alto_m": 1, "terminacion": "overlock"},
                                     {"productos": [{"id": "tplT", "a_medida": {"pieza": "Bandera", "margen": {"todos": 3}, "overlock_cm": 0.7,
                                                                                "ancho_m": 1, "alto_m": 1, "terminacion": "dobladillo"}}]}, "pT")
ok(not _er9 and _ex9["a_medida"]["terminacion"] == "overlock" and _ex9["a_medida"]["margen"] == {"todos": 0.7}
   and _ex9["a_medida"]["margen_dobladillo"] == {"todos": 3} and _ex9["a_medida"]["overlock_cm"] == 0.7,
   f"la copia del pedido: la terminación elegida, el margen que rige y los dos guardados ({_ex9['a_medida']})")
_ex9b = S._a_medida_crear({"a_medida_de": "tplT", "efimero": True, "ancho_m": 1, "alto_m": 1},
                          {"productos": [{"id": "tplT", "a_medida": {"pieza": "B", "margen": {"todos": 3}, "terminacion": "sin"}}]}, "pT2")[0]
ok(_ex9b["a_medida"]["terminacion"] == "sin" and _ex9b["a_medida"]["margen"] == {"todos": 0.0},
   "sin elegir, arranca con la terminación por defecto del molde")
# 9.3 tiras que no se marcan en la tizada: la ficha las trae igual
_pm = {"id": "pm", "a_medida": {"margen": {"todos": 3}, "ancho_m": 1.5, "alto_m": 1, "de": "x", "terminacion": "dobladillo"},
       "marcas_tiras": {"activo": True, "lados": {"arriba": 5, "abajo": 5}, "marcar": False}}
ok(S._tiras_de(_pm) is None and (S._tiras_de(_pm, para_ficha=True) or {}).get("marcar") is False and "tiras" not in S._borde_de(_pm),
   "«Marcar en la tizada» apagado: el motor no las imprime (no viajan con el borde) pero la ficha las tiene")
_f9 = S._ficha_a_medida(_pm) or {}
ok(any(x["etiqueta"] == "Tiras" and "no se marcan en la tizada" in x["valor"] and x["valor"].startswith("6 tiras") for x in _f9.get("filas", []))
   and any(x["etiqueta"] == "Arriba" and "cada 37,5 cm" in x["valor"] for x in _f9.get("filas", [])),
   f"la ficha dice cuántas y cada cuánto, y que no se marcan ({[x['valor'] for x in _f9.get('filas', []) if x['etiqueta'] in ('Tiras', 'Arriba')]})")
_ps9 = {"id": "ps", "a_medida": {"margen": {"todos": 0}, "ancho_m": 1, "alto_m": 1, "de": "x", "forma": "circulo", "terminacion": "sin"},
        "marcas_tiras": {"activo": True, "lados": {"alrededor": 8}}}
_f9s = S._ficha_a_medida(_ps9) or {}
ok(S._tiras_de(_ps9) is None and any(x["etiqueta"] == "Tiras" and x["valor"].startswith("8 tiras") for x in _f9s.get("filas", []))
   and any(x["etiqueta"] == "Terminación" and x["valor"] == "Sin margen" for x in _f9s.get("filas", [])),
   "sin margen: las tiras van sólo en la ficha; la terminación dice «Sin margen»")
ok(any(x["etiqueta"] == "Terminación" and x["valor"].startswith("Overlock") for x in (S._ficha_a_medida(
       {"id": "po", "a_medida": {"margen": {"todos": 1}, "ancho_m": 1, "alto_m": 1, "de": "x", "terminacion": "overlock"}}) or {}).get("filas", [])),
   "la ficha dice la terminación (Overlock · 1 cm por lado)")
_tt9 = [((f, l, r), len(S.MP._segmentos_tiras(*((S.MP._geo_triangulo(120.0, 80.0, 3.0, "abajo", r)["W"], S.MP._geo_triangulo(120.0, 80.0, 3.0, "abajo", r)["H"]) if f == "triangulo" else (100.0, 100.0)),
                                               _mgT, l, f, "abajo", [120.0, 80.0], r)), S._total_tiras(f, l, r))
        for f, l, r in (("rectangulo", {"arriba": 5, "abajo": 3, "izq": 1}, True), ("rectangulo", {"arriba": 2, "der": 4}, True),
                        ("triangulo", {"base": 5, "laterales": 4}, True), ("triangulo", {"base": 1, "laterales": 3}, False),
                        ("circulo", {"alrededor": 9}, True))]
ok(all(a == b for _k, a, b in _tt9), f"la cuenta de la ficha sin dibujar (`_total_tiras`) = la del motor ({[(k[0], a, b) for k, a, b in _tt9]})")
# 9.4 la API del otro sistema
A = []
_r9 = IE._medida_del_pedido({"terminacion": "Overlock", "medida": {"ancho_m": 1.4, "alto_m": 0.9}}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(_r9 and _r9.get("terminacion") == "overlock" and not A, f"`terminacion: Overlock` (como lo escriba) ({_r9} {A})")
A = []
ok(IE._medida_del_pedido({"terminacion": "costura", "ancho_m": 1, "alto_m": 1}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A) is None
   and A and A[-1]["codigo"] == "terminacion-invalida", "una terminación que no existe → `terminacion-invalida`")
A = []
_r9s = IE._medida_del_pedido({"terminacion": "sin margen", "ancho_m": 1, "alto_m": 1}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(_r9s and _r9s["terminacion"] == "sin", "«sin margen» también se entiende")
A = []
_tp9 = IE._tiras_del_pedido({"lleva": True, "marcar": False, "lados": {"arriba": 3}}, tpl, CAT, "m", A)
_tp9s = IE._tiras_del_pedido({"lleva": True, "lados": {"arriba": 3}}, tpl, CAT, "m", A, "rectangulo", "sin")
ok(_tp9 and _tp9["marcar"] is False and _tp9s and _tp9s["activo"] and not A,
   f"tiras: `marcar: false` viaja, y sin margen no frena (van sólo en la ficha) ({_tp9} {_tp9s} {A})")
_pub9 = IE._a_medida_publico_ext(tpl)
ok(set(_pub9.get("terminaciones") or []) == {"dobladillo", "overlock", "sin"} and "overlock_cm" in _pub9
   and "terminacion_por_defecto" in _pub9 and "marcar_por_defecto" in (_pub9.get("tiras") or {}),
   "la API publica las terminaciones, el overlock, la de por defecto y si las tiras se marcan")
# 9.5 la pantalla
app9 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok('data-tour="arte-medida-terminacion"' in app9 and 'data-tour="arte-tiras-marcar"' in app9 and 'data-tour="a-medida-overlock"' in app9
   and 'data-tour="a-medida-terminacion"' in app9 and 'data-tour="tiras-marcar"' in app9,
   "en el pedido se elige la terminación y si las tiras se marcan; en Ajustes, el overlock, la de por defecto y el «marcar» de por defecto")
ok("terminacion: st.te" in app9 and "normTerminacion(am.terminacion) === te" in app9 and "if (tiras.marcar === false) {" in app9
   and "(!pv || tirasAMedida.marcar === false)" in app9 and "marcar: t.marcar !== false };" in app9
   and "terminacion: te }, avisar);" in app9,
   "la terminación arma el molde (se rearma solo al cambiarla) y unas tiras sin marcar se VEN en el visor como guía (MAPA 653)")

# 9.6 🔲 EL RECTÁNGULO CON DOBLADILLO, CON LAS ESQUINAS RECORTADAS (MAPA 653)
_j10 = node("import { pdfMoldeAMedida } from './src/motor/molde/aMedida.js';"
            "import { rectRecortado } from './src/motor/molde/formas.js';"
            "import { segmentosTiras } from './src/motor/molde/tiras.js';"
            "import * as mupdf from 'mupdf';"
            "const pz = (t) => { const r = pdfMoldeAMedida(mupdf, { anchoM: 3, altoM: 1.5, pieza: 'B', margen: { todos: 3 }, reservaMm: 2, terminacion: t });"
            " const d = mupdf.Document.openDocument(r.pdf, 'application/pdf'); const pg = d.loadPage(0); const b = pg.getBounds();"
            " return Buffer.from(r.pdf).toString('base64') };"
            "console.log(JSON.stringify({ dob: pz('dobladillo'), ovl: pz('overlock'), rr: rectRecortado(0, 0, 100, 50, 3, 3, 2, 0),"
            f" s: segmentosTiras(306, 156, {json.dumps(_mgT)}, {{ arriba: 5, abajo: 4, izq: 1, der: 2 }}, 'rectangulo', 'abajo', null, true) }}))")
import base64 as _b64
def _pts_pdf(b):
    _d = fitz.open(stream=_b64.b64decode(b), filetype="pdf")
    return [(round(q.x / 28.3465, 2), round(q.y / 28.3465, 2)) for dr in _d[0].get_drawings() for it in dr["items"] for q in it[1:] if hasattr(q, "x")]
_pd, _po = _pts_pdf(_j10["dob"]), _pts_pdf(_j10["ovl"])
ok(len(set(_pd)) == 12 and len(set(_po)) <= 4,
   f"dobladillo: el contorno del rectángulo sin el cuadradito de cada esquina (12 puntos); overlock: entero (4) ({len(set(_pd))}, {len(set(_po))})")
ok([0, 0] in _j10["rr"] and [100, 0] in _j10["rr"] and [97, 50] in _j10["rr"] and [3, 48] in _j10["rr"],
   f"un lado sin margen no recorta sus esquinas (abajo 0: las de abajo enteras, las de arriba recortadas) ({_j10['rr']})")
_s10 = S.MP._segmentos_tiras(306.0, 156.0, _mgT, {"arriba": 5, "abajo": 4, "izq": 1, "der": 2}, "rectangulo", "abajo", None, True)
ok(_igual(_s10, _j10["s"]) and len(_s10) == 3 + 2 + 1 + 0 and not any((x1, y1) in ((0.0, 0.0), (306.0, 0.0), (306.0, 156.0), (0.0, 156.0)) for x1, y1, _a, _b in _s10)
   and (78.0, 156.0, 78.0, 153.0) in [tuple(x) for x in _s10],
   f"tiras: sin marca en las esquinas, las del medio sobre la guía (arriba 5 → cada 75 desde x = 3), gemelas ({_s10})")
ok(S._total_tiras("rectangulo", {"arriba": 5, "abajo": 4, "izq": 1, "der": 2}, True) == len(_s10)
   and S._total_tiras("rectangulo", {"arriba": 5, "abajo": 4, "izq": 1, "der": 2}, False) == 4 + 6,
   "la cuenta de la ficha: sin esquinas con dobladillo, con esquinas con overlock")


print("\n10 · 🧵 LA COSTURA: la guía punteada adentro de la guía del diseño (MAPA 654)")
_j11 = node("import { segsCostura, segsDobladillo } from './src/motor/molde/formas.js';"
            "import { margenSobreContorno } from './src/motor/molde/aMedida.js';"
            "import { planIllustrator } from './src/motor/molde/illustrator.js';"
            "import { aiGuiaMedidas } from './src/motor/molde/herramientas.js';"
            "const dR = margenSobreContorno({ todos: 3 }, 2, 'rectangulo', 'abajo', 3, 1.5, 'dobladillo');"
            "const dO = margenSobreContorno({ todos: 3 }, 2, 'rectangulo', 'abajo', 3, 1.5, 'overlock');"
            "const dT = margenSobreContorno({ todos: 3 }, 2, 'triangulo', 'abajo', 1.2, 0.8, 'dobladillo');"
            "const dC = margenSobreContorno({ todos: 3 }, 2, 'circulo', 'abajo', 1, 1, 'dobladillo');"
            "console.log(JSON.stringify({ dR, dO,"
            " r: segsCostura([0, 0, 305.6, 155.6], dR, 1), o: segsCostura([0, 0, 305.6, 155.6], dO, 1),"
            " t: segsCostura([0, 0, 122.1, 84.1], dT, 1), tg: segsDobladillo([0, 0, 122.1, 84.1], dT, 1),"
            " c: segsCostura([0, 0, 105.6, 105.6], dC, 1) }))")
ok(_j11["dR"].get("costura") == {"arriba": 3, "abajo": 3, "izq": 3, "der": 3} and "costura" not in _j11["dO"],
   "sólo con dobladillo: la costura viaja con la guía del margen (el margen entero); con overlock no hay")
_r11 = [p for p in _j11["r"] if p[0] in ("m", "l")]
ok(_j11["o"] is None and abs(_r11[0][1] - 5.8) < 1e-9 and abs(_r11[1][1] - 299.8) < 1e-9,
   f"rectángulo 3 × 1,50 con 3 cm: la guía a 3 cm del total y la costura a 6 (el margen otra vez, adentro) ({_r11[:2]})")
_tg = [p for p in _j11["tg"] if p[0] in ("m", "l")]
_tc = [p for p in _j11["t"] if p[0] in ("m", "l")]
_I = S.MP._incentro([(p[1], p[2]) for p in _tg])
_dist = lambda P, A, B: abs((B[0] - A[0]) * (A[1] - P[1]) - (A[0] - P[0]) * (B[1] - A[1])) / _mt.hypot(B[0] - A[0], B[1] - A[1])
_tce = S.MP._triangulo_corrido([(p[1], p[2]) for p in _tg], -3.0)
ok(len(_tc) == 3 and _igual([(p[1], p[2]) for p in _tc], _tce),
   "triángulo: la costura es el triángulo de la guía corrido el margen hacia adentro")
ok(_j11["c"] and _j11["c"][1][0] == "c", "círculo: la costura es un círculo, el margen adentro de la guía")
_ilu = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "molde", "illustrator.js"), encoding="utf-8").read()
_jsx = io.open(os.path.join(_AQUI, "extension_illustrator", "com.tizadapro.illustrator", "jsx", "tizada.jsx"), encoding="utf-8").read()
_cs = io.open(os.path.join(_AQUI, "extension_corel", "puente", "ArmarCorel.cs"), encoding="utf-8").read()
_hr = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "molde", "herramientas.js"), encoding="utf-8").read()
# 🔴 (MAPA 656) como arte punteado quedaba TAPADA por el fondo de la mesa («falta la tercera guía»): va como
# RAYAS sueltas que entran por el SVG y se vuelven GUÍAS (guías en fila = guía punteada, siempre encima)
_j12 = node("import { segsRayas } from './src/motor/molde/formas.js';"
            "const r = segsRayas([['m', 0, 0], ['l', 100, 0], ['l', 100, 50], ['l', 0, 50], ['h']], 10, 6);"
            "console.log(JSON.stringify({ n: r.filter(s => s[0] === 'm').length, r0: r.slice(0, 3) }))")
ok(_j12["n"] == 19 and _j12["r0"] == [["m", 0, 0], ["l", 10, 0], ["m", 16, 0]],
   f"la línea en rayas: 1 cada 16 (10 + 6), sueltas, siguiendo el camino ({_j12})")
ok("const r = g ? segsRayas(g, 1 * PT_POR_CM, 0.6 * PT_POR_CM) : null" in _ilu and "if (cos) for (const k of cos) for (const sp of k.sub) svg.push(" in _ilu
   and "nombre: 'costura' })" in _ilu and _hr.count("segsCostura(bboxSegs(it.segs)") == 2,
   "Illustrator y Corel la reciben como GUÍA PUNTEADA (rayas por el SVG, como el contorno y el dobladillo), y la guía .ai y el PDF de medidas punteada")
# 🔴 (MAPA 657) los conectores aceptan hasta 500 sub-caminos por camino: una bandera de 3 × 1,50 tiene ~550 rayas
# de costura y el plan ENTERO se rechazaba («no funciona la conexión con Illustrator y Corel»)
_pj = io.open(os.path.join(_AQUI, "extension_illustrator", "com.tizadapro.illustrator", "js", "puente.js"), encoding="utf-8").read()
ok("lista(k.sub, 500, 'sub-caminos')" in _pj and 'Lista(Get(k, "sub"), 500, "sub-caminos")' in _cs
   and "const MAX_SUB_POR_CAMINO = 400" in _ilu and "sub.slice(i, i + MAX_SUB_POR_CAMINO)" in _ilu and "caminos.push(...cos)" in _ilu,
   "la costura se reparte en caminos de hasta 400 rayas (los conectores rechazan más de 500 por camino)")
_a11 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("pathCostura(m, x0, y0, w, h, 10 * kx)" in _a11 and "dCostura &&" in _a11,
   "el visor también la muestra (naranja punteada), antes y después de armar")
ok('data-tour="arte-medida-costura"' in _a11 and "strokeDasharray={tipo === 'guia' ? '9 6' : tipo === 'costura' ? '5 4' : undefined}" in _a11,
   "la leyenda del panel muestra cada línea como se ve (color, grosor y rayas), con la costura (MAPA 655)")

print("\n11 · EL ARTE ES DE OTRA MEDIDA: las guías del arte = las de la pieza (MAPA 658)")
# 🔴 pedido del usuario 2026-10-09 con captura: «las guías deben ser idénticas; el arte no llegó a cubrirlo todo».
# El arte se armó con la plantilla de 3,00 × 1,50 (mesa 300 × 153,4) y después la medida pasó a 1,45 (pieza
# 300 × 148,5): escalado por el alto, el diseño quedaba más angosto y dejaba tela sin cubrir.
_j13 = node("import { arteDeOtraMedida } from './src/motor/molde/aMedida.js';"
            "console.log(JSON.stringify([arteDeOtraMedida({ w_cm: 300, h_cm: 153.4 }, { w: 300, h: 148.5 }),"
            " arteDeOtraMedida({ w_cm: 300, h_cm: 148.6 }, { w: 300, h: 148.5 }), arteDeOtraMedida(null, { w: 1, h: 1 })]))")
ok(_j13[0] == {"arte": {"w": 300, "h": 153.4}, "molde": {"w": 300, "h": 148.5}} and _j13[1] is None and _j13[2] is None,
   f"navegador: 300 × 153,4 contra 300 × 148,5 avisa; ± 0,5 cm es la misma medida ({_j13})")
_pid13 = "prod_otra_medida"
_dir13 = os.path.dirname(S._ruta_entrada("arte.ai", _pid13, sub=S._diseno_sub("jugador")))
os.makedirs(_dir13, exist_ok=True)
with open(os.path.join(_dir13, ".deteccion_cache.json"), "w", encoding="utf-8") as _f:
    json.dump({"clave": "x", "det": {"mesas": [{"mesa": 1, "w_cm": 300, "h_cm": 153.4, "nombre_detectado": "Bandera"}]}}, _f)
_cargar_v = S._cargar
S._cargar = lambda n, pid=None, sub=None: ({"Bandera": {"3,00x1,45": {"w_cm": 300.0, "h_cm": 148.5}}}
                                          if n == "registro_producto.json" and pid == _pid13 else _cargar_v(n, pid, sub))
try:
    _o13 = S._arte_otra_medida({"id": _pid13, "a_medida": {"pieza": "Bandera", "de": "x"}}, "jugador")
    _s13 = S._arte_otra_medida({"id": _pid13}, "jugador")
finally:
    S._cargar = _cargar_v
ok(_o13 == {"arte": {"w": 300.0, "h": 153.4}, "molde": {"w": 300.0, "h": 148.5}} and _s13 is None,
   f"servidor (gemelo): lee la detección guardada del arte y la pieza del registro; un molde común no se mira ({_o13})")
_ie = io.open(os.path.join(_AQUI, "integracion_externa.py"), encoding="utf-8").read()
ok(IE.ALARMAS.get("arte-otra-medida", (None, None))[1] is True and 'alarma("arte-otra-medida"' in _ie
   and "S._arte_otra_medida(_prod, dis[\"slug\"])" in _ie,
   "la API frena con `arte-otra-medida` (el robot cuenta el arte y el servidor compara)")
_a13 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok('data-tour="arte-medida-otra"' in _a13 and "arteOtra={_amArteOtra}" in _a13
   and "arteDeOtraMedida(_me, { w: _amEst.pz.anchoCm - 2 * _amRes / 10, h: _amEst.pz.altoCm - 2 * _amRes / 10 })" in _a13,
   "el paso Arte lo muestra en el panel de la medida (sólo el dato: arte y pieza en cm)")
ok("setDets({}); detsPedidas.current = new Set();" in _a13 and "if (detsPedidas.current.has(pid)) continue;" in _a13,
   "«Crear plantilla» vuelve a leer el molde al abrirse (con la detección vieja salía la plantilla de la medida anterior)")
ok("useEffect(() => { _guiaIllu.current = new Map(); }, [moldeReload]);" in _a13,
   "«Crear en Illustrator» de Configuración tira sus datos cuando el molde cambia")

print("\n12 · LA FICHA CON DIBUJOS: plano, doblez paso a paso, la esquina/punta de cerca y los pasos (MAPA 659)")
# 🔴 pedido del usuario 2026-10-09: «que la ficha técnica de los moldes a medida sea más específica y visualmente
# detallista, mostrando y explicando los dobleces». El servidor calcula los trazos (`ficha_a_medida.py`) con la
# geometría del motor y las dos fichas sólo los dibujan (`_dibujar_ops` ↔ `dibujarOps`).
import ficha_a_medida as _FAM   # noqa: E402
_dib = (_fa or {}).get("dibujos") or []
_txt = lambda b: [o["s"] for o in b["ops"] if o["k"] == "t"]
ok(len(_dib) == 3 and all(b["alto"] > 0 and b["ops"] for b in _dib)
   and _txt(_dib[0])[0] == "PLANO DE LA PIEZA" and _txt(_dib[2])[0] == "CÓMO SE TERMINA",
   f"tres bloques: plano, terminación y pasos ({[(b['alto'], len(b['ops'])) for b in _dib]})")
_l0 = [o for o in _dib[0]["ops"] if o["k"] == "l"]
_cont = next((o for o in _l0 if o.get("f") == list(_FAM.TELA)), None)
_puntos = [o for o in _l0 if o.get("c") is None and o.get("f") == list(_FAM.NEGRO) and len(o["p"]) == 12]
ok(_cont is not None and len(_cont["p"]) == 12 and any(o.get("d") == _FAM.RAYAS_GUIA and o.get("c") == list(_FAM.AZUL) for o in _l0)
   and any(o.get("d") == _FAM.RAYAS_COSTURA for o in _l0) and len(_puntos) == 7 + 1,     # + el de la leyenda
   f"el plano: contorno con las esquinas recortadas (12 puntos), la guía (doblez), la costura y las 7 tiras ({len(_puntos)})")
ok(any("306 total" in t for t in _txt(_dib[0])) and any("300 diseño" in t for t in _txt(_dib[0]))
   and "156 total" in _txt(_dib[0]) and "150 diseño" in _txt(_dib[0]),
   "con cotas del total y del diseño, a lo ancho y a lo alto")
_t1 = _txt(_dib[1])
ok(all(x in _t1 for x in ("1 · Cortado", "2 · Doblado", "3 · Cosido", "La esquina de cerca", "Cortada", "Doblada"))
   and any("costura a 3 cm del doblez" in t for t in _t1),
   "el dobladillo en corte paso a paso (cortado → doblado → cosido) y la esquina cortada y doblada")
_pas = " ".join(_txt(_dib[2]))
ok("Doblar el margen de 3 cm hacia el revés" in _pas and "Coser a 3 cm del doblez" in _pas and "7 en total" in _pas
   and "vértices de los recortes de las esquinas" in _pas,
   "los pasos con las medidas de ESTE pedido (margen, costura, tiras)")
# las solapas dobladas caen ADENTRO de la guía (no sobra nada afuera) — en el rectángulo y en el triángulo
_gr = _FAM._geometria("rectangulo", "abajo", "dobladillo", 300, 150, {"arriba": 3, "abajo": 3, "izq": 3, "der": 3}, 306, 156)
_gx0, _gy0, _gx1, _gy1 = _gr["caja_diseno"]
_gt = _FAM._geometria("triangulo", "abajo", "dobladillo", 300, 145, {k: 2 for k in ("arriba", "abajo", "izq", "der")}, 300, 148.49)
def _dentro_tri(p, G, eps=1e-6):
    s = [(G[(i + 1) % 3][0] - G[i][0]) * (p[1] - G[i][1]) - (G[(i + 1) % 3][1] - G[i][1]) * (p[0] - G[i][0]) for i in range(3)]
    return all(x >= -eps for x in s) or all(x <= eps for x in s)
ok(len(_gr["solapas"]) == 4 and all(_gx0 - 1e-9 <= x <= _gx1 + 1e-9 and _gy0 - 1e-9 <= y <= _gy1 + 1e-9 for sol in _gr["solapas"] for x, y in sol)
   and len(_gt["solapas"]) == 3 and all(_dentro_tri(p, _gt["G"]) for sol in _gt["solapas"] for p in sol),
   "«Doblada»: cada solapa reflejada por la guía cae adentro de la pieza terminada (rectángulo y triángulo)")
def _fam(forma, term, an, al, m, tiras=None):
    W, H = S._medida_pieza(an / 100, al / 100, {"todos": m}, forma, "abajo", term)
    return _FAM.dibujos_a_medida(forma, "abajo", term, an, al, {k: m for k in ("arriba", "abajo", "izq", "der")}, W, H, tiras=tiras)
_dt, _dc, _do, _ds = _fam("triangulo", "dobladillo", 300, 145, 2), _fam("circulo", "dobladillo", 120, 120, 2.5), \
    _fam("rectangulo", "overlock", 150, 90, 1), _fam("triangulo", "sin", 120, 60, 0)
ok("La punta de cerca" in _txt(_dt[1]) and "El borde de cerca" in _txt(_dc[1])
   and "2 · Overlock" in _txt(_do[1]) and not any("de cerca" in t for t in _txt(_do[1]))
   and "Corte al ras" in _txt(_ds[1]) and any("Sin margen" in t for t in _txt(_ds[2])),
   "cada forma y terminación con lo suyo: la punta del triángulo, el borde del círculo, el overlock, sin margen")
ok(any(o["s"].startswith("Ø 120 diseño") for o in _dc[0]["ops"] if o["k"] == "t")
   and any(o["s"].startswith("Ø 125 total") for o in _dc[0]["ops"] if o["k"] == "t"),
   "el círculo acotado por el diámetro (diseño y total)")
# las dos fichas los dibujan (gemelos; el píxel a píxel lo mira `verificar_navegador_ficha.py`)
_ftp = io.open(os.path.join(_AQUI, "ficha_tecnica.py"), encoding="utf-8").read()
_fjs = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "ficha", "ficha.js"), encoding="utf-8").read()
ok("_dibujar_ops(pg, MARGEN, y, _b.get(\"ops\"))" in _ftp and "dibujarOps(ctx, pg, MARGEN, y, b.ops)" in _fjs
   and "drawCont = dashes + ' d\\n' + drawCont" in _fjs and "FAM.dibujos_a_medida(" in io.open(os.path.join(_AQUI, "verificar_navegador_ficha.py"), encoding="utf-8").read(),
   "servidor y navegador dibujan los mismos trazos (rayas incluidas); el contrato de gemelos los incluye")
_ftx2 = "".join(pg.get_text() for pg in fitz.open(_rf))
ok("PLANO DE LA PIEZA" in _ftx2 and "EL DOBLADILLO" in _ftx2 and "CÓMO SE TERMINA" in _ftx2,
   "la ficha impresa trae el plano, el dobladillo y los pasos")
# best-effort: si el dibujo falla, la ficha sale igual con las filas
_dv = _FAM.dibujos_a_medida
_FAM.dibujos_a_medida = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("prueba"))
try:
    _fx = S._ficha_a_medida(_cf, {"productos": [_ctpl, _cf]})
finally:
    _FAM.dibujos_a_medida = _dv
ok(_fx and _fx.get("filas") and _fx.get("dibujos") == [], "si el dibujo falla, la ficha sale igual con sus filas")

print(chr(10) + "13 · LA COPIA SE ARMA RECIÉN AL CARGAR EL ARTE; AUTOMÁTICO SÓLO EL RE-ARMADO DE UNA COPIA (MAPA 660 → 695)")
# MAPA 695 (el usuario: «dibujar esa mierda simple no necesita del servidor»): elegir la medida no toca el servidor.
_a13b = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
_arm = _a13b[_a13b.index("const armarAMedida = async"):_a13b.index("const amIntentoRef = useRef('');")]
ok(".then((bien) => { if (bien && amIntentoRef.current === firma) amIntentoRef.current = ''; });" in _a13b
   and "return mid;" in _arm and "return d.id;" in _arm and "showError(e.message);" + chr(10) + "      return false;" in _arm.replace(chr(13), ""),
   "armarAMedida devuelve el id de la copia (o false si falló); el «ya lo intenté» queda sólo si falló")
ok("st.lista && st.esCopia && (!!amForm[st.clave] || st.vieja)" in _a13b,
   "el armado automático es SÓLO re-armar una copia que ya existe (otra medida escrita o geometría vieja), nunca la plantilla")
ok("const asegurarCopiaAMedida = async" in _arm and "id = await asegurarCopiaAMedida(_etapa);" in _a13b
   and _a13b.count("await asegurarCopiaAMedida((x) => setProcesando(x))") == 1,
   "la copia se arma al cargar el arte (dentro del mismo cartel) o al tocar «Crear plantilla»; elegir la tela no la necesita")
ok("useEffect(() => { if (pedidoPaso !== 'arte') amIntentoRef.current = ''; }, [pedidoPaso]);" in _a13b,
   "y al salir del paso Arte se olvida también un intento fallido")

print(chr(10) + "14 · INSTANTÁNEO: UN SOLO HILO, LA MISMA MEDIDA UNA VEZ, PRECALENTADO Y «NUEVO PEDIDO» SIN ESPERA (MAPA 661)")
# 🔴 pedido del usuario 2026-10-09: «¿por qué demora tanto acá y en borrar un pedido? que sea instantáneo»
import zipfile as _zf
_zv, _zn = os.path.join(_TMP, "am_viejo.zip"), os.path.join(_TMP, "am_nuevo.zip")
_r14 = subprocess.run(["node", os.path.join("src", "motor", "pruebas", "a_medida_rapido.mjs")], cwd=os.path.join(_AQUI, "frontend"),
                      capture_output=True, text=True, encoding="utf-8", timeout=300, env=dict(os.environ, ZV=_zv, ZN=_zn))
try:
    _j14 = json.loads(_r14.stdout.strip().splitlines()[-1])
except Exception:
    _j14 = {}
def _zip_sin_fecha(ruta):
    z = _zf.ZipFile(ruta)
    out = {}
    for n in z.namelist():
        b = z.read(n)
        if n == "manifest.json":
            d = json.loads(b); d.pop("armado", None); b = json.dumps(d, sort_keys=True).encode()
        out[n] = b
    return out
ok(_j14.get("mismoArchivo") and _j14.get("mismoResumen") and os.path.exists(_zv) and _zip_sin_fecha(_zv) == _zip_sin_fecha(_zn),
   f"en UN hilo sale el MISMO molde que con los dos pools de antes (archivo, resumen y paquete; sólo cambia la fecha) — {_j14.get('ms')}")
ok(_j14.get("memoria") is True and _j14.get("otraMedidaEsOtra") is True,
   "la misma medida se prepara UNA vez (aunque el margen venga escrito distinto); otra medida es otro molde")
_a14 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
_pm14 = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "prepararMolde.js"), encoding="utf-8").read()
ok("return await prepararEnDosTiempos(archivo, { dxfResumen: r.resumen, pool: uno })" in _pm14 and "pool = poolAjeno || crearPool(" in _pm14
   and "precalentarMoldeAMedida({ anchoM: leerMetros(metrosTexto(am.ancho_m || 1))" in _a14,
   "un solo hilo (el del PDF lee el molde) y se precalienta apenas el molde a medida entra al pedido")
_rp = _a14[_a14.index("const _reiniciarPedido = () => {"):_a14.index("setPedidoPaso('diseno');          // el wizard arranca por el DISEÑO")]
ok("setBorrandoPedido(" not in _rp and "setProductosCat(c => ({ ...c, productos: (c.productos || []).filter(p => !_sacar.has(p.id)) }))" in _rp,
   "«Nuevo pedido» arranca YA: lo del servidor se borra de fondo (sin cartel que espere) y sus moldes salen de la lista en el acto")

print(chr(10) + "15 · CAMBIAR DE DISEÑO SIGUE SIENDO INSTANTÁNEO, SIN ARMAR NADA DE FONDO (MAPA 662 → 695)")
# MAPA 695: armar de fondo las copias de TODOS los diseños eran 5-7 pedidos al servidor por diseño (la cola de 43
# medida en el publicado). Pasar de diseño es instantáneo igual: el visor dibuja la medida ACÁ (`_visorMedida`).
_a15 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
_ef15 = _a15[_a15.index("const amIntentoRef = useRef('');"):_a15.index("// ⚡ PRECALENTAR (MAPA 661")]
ok("amFondoRef" not in _a15 and "for (const did of Object.keys(disenoMoldes || {}))" not in _ef15,
   "ya no se arman de fondo las copias de los otros diseños")

print(chr(10) + "16 · LA FICHA: LA MISMA CONFIGURACIÓN EN VARIOS DISEÑOS VA UNA VEZ; DISTINTA, UNA POR DISEÑO (MAPA 665)")
_cat16 = {"productos": [{"id": "c1", "a_medida": {"de": "tplA"}}, {"id": "c2", "a_medida": {"de": "tplA"}},
                        {"id": "c3", "a_medida": {"de": "tplA"}}, {"id": "c4", "a_medida": {"de": "tplB"}}]}
_sec = lambda v: {"filas": [{"etiqueta": "Medida del diseño (guía)", "valor": v}], "notas": [], "dibujos": [{"alto": 1, "ops": []}]}
_g16 = [{"pid": "c1", "diseno_nombre": "JUGADOR", "a_medida": _sec("300 × 150 cm")},
        {"pid": "c2", "diseno_nombre": "GOLERO", "a_medida": _sec("300 × 150 cm")},
        {"pid": "c3", "diseno_nombre": "ARQUERO", "a_medida": _sec("300 × 145 cm")},
        {"pid": "c4", "diseno_nombre": "SUPLENTE", "a_medida": _sec("300 × 150 cm")}]
S._agrupar_a_medida_ficha(_g16, _cat16)
ok(_g16[0]["a_medida"].get("titulo_disenos") == "JUGADOR y GOLERO" and _g16[1]["a_medida"] is None,
   "mismo molde y misma configuración en JUGADOR y GOLERO → una sola sección, con los dos diseños en el título")
# (MAPA 666) con la plantilla en varios diseños cada sección dice a cuál corresponde; un molde solo, no hace falta
ok(_g16[2]["a_medida"] and _g16[2]["a_medida"].get("titulo_disenos") == "ARQUERO"
   and _g16[3]["a_medida"] and not _g16[3]["a_medida"].get("titulo_disenos"),
   "otra medida (ARQUERO) u otro molde (SUPLENTE) → cada uno con la suya (ARQUERO dice su diseño: su plantilla está en tres)")
ok([g["diseno_nombre"] for g in _g16] == ["JUGADOR", "GOLERO", "ARQUERO", "SUPLENTE"]
   and [g["am"]["grupo"] for g in _g16] == ["tplA", "tplA", "tplA", "tplB"] and _g16[0]["am"]["sub"] == "1,00 × 1,00 m",
   "cada guía a medida lleva su bloque (`am`: la plantilla, su medida) y las de una plantilla quedan juntas")
print(chr(10) + "17 · LA FICHA: UN BLOQUE COMPACTO POR MOLDE A MEDIDA, UNA TARJETA POR DISEÑO (MAPA 666)")
_g17 = [{"pid": "c1", "diseno_nombre": "JUGADOR"}, {"pid": "x", "diseno_nombre": "OTRO"}, {"pid": "c2", "diseno_nombre": "GOLERO"}]
S._agrupar_a_medida_ficha(_g17, {"productos": _cat16["productos"] + [{"id": "tplA", "nombre": "Bandera", "a_medida": {}}]})
ok([g["diseno_nombre"] for g in _g17] == ["JUGADOR", "GOLERO", "OTRO"] and _g17[0]["am"]["molde"] == "Bandera",
   "las de la misma bandera se juntan aunque en el pedido estén separadas, con el nombre de la plantilla")
_cmp = _FT._compactar_a_medida([
    {"nombre": "Bandera 1,00x1,00", "diseno": "JUGADOR", "piezas": [{"nombre": "Bandera", "tela": "T", "pdf": b""}], "fuentes": [{"campo": "nombre", "fuente": "Anton"}],
     "procesos": [], "am": {"grupo": "t", "molde": "Bandera", "sub": "3,00 × 1,45 m · triángulo", "aspecto": 0.495}, "a_medida": {"filas": [1]}},
    {"nombre": "Bandera 1,00x1,00", "diseno": "GOLERO", "piezas": [{"nombre": "Bandera", "tela": "T", "pdf": b""}], "fuentes": [{"campo": "nombre", "fuente": "Anton"}],
     "procesos": [], "am": {"grupo": "t", "molde": "Bandera", "sub": "3,00 × 1,20 m · triángulo", "aspecto": 0.41}, "a_medida": None},
    {"nombre": "Buzo", "diseno": "JUGADOR", "piezas": []}])
ok(len(_cmp) == 2 and _cmp[0]["compacta"] and _cmp[0]["nombre"] == "Bandera"
   and [(p["nombre"], p["sub"]) for p in _cmp[0]["piezas"]] == [("JUGADOR", "3,00 × 1,45 m · triángulo"), ("GOLERO", "3,00 × 1,20 m · triángulo")]
   and len(_cmp[0]["fuentes"]) == 1 and len(_cmp[0]["a_medidas"]) == 1 and _cmp[0]["aspecto"] == 0.495 and not _cmp[1].get("compacta"),
   "un bloque: una tarjeta por diseño (nombre = el diseño, debajo su medida), tipografías sin repetir; el resto igual")
_hc = _FT._h_card_a_medida(0.495)
ok(70 < _hc < 95 and _FT._h_card_a_medida(None) is None and _FT._h_card_a_medida(5) == 170.0,
   f"la tarjeta toma el alto justo de la bandera ({_hc:.1f} pt; antes 106 fijos en 5 columnas)")
_fd17 = os.path.join(_TMP, "ficha_666"); os.makedirs(_fd17, exist_ok=True)
_pz17 = fitz.open(); _pz17.new_page(width=300 * 28.35, height=148.5 * 28.35); _b17 = _pz17.tobytes(); _pz17.close()
_r17 = _FT.generar_ficha(_fd17, "Ficha técnica", "Bandera", {"columnas": [{"id": "c", "label": "Cantidad"}], "filas": [{"c": 1}]},
                         [{"nombre": "Bandera 1,00x1,00", "diseno": d, "piezas": [{"nombre": "Bandera", "tela": "Bandera (1,60)", "pdf": _b17}],
                           "am": {"grupo": "t", "molde": "Bandera", "sub": "3,00 × 1,45 m · triángulo", "aspecto": 0.495},
                           "a_medida": ({**_fa, "titulo_disenos": "JUGADOR y GOLERO"} if d == "JUGADOR" else None)} for d in ("JUGADOR", "GOLERO")])
_t17 = "".join(pg.get_text() for pg in fitz.open(_r17))
ok("Bandera · a medida" in _t17 and "MOLDE GUÍA" not in _t17 and "1 pieza" not in _t17 and _t17.count("3,00 × 1,45 m · triángulo") == 2
   and "JUGADOR" in _t17 and "GOLERO" in _t17 and _t17.count("MEDIDA Y TERMINACIÓN") == 1,
   "la ficha impresa: «Bandera · a medida», sin «MOLDE GUÍA» ni «1 pieza», las dos tarjetas con su medida y una sola sección")
_fj17 = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "ficha", "ficha.js"), encoding="utf-8").read()
_gen17 = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "pedido", "generar.js"), encoding="utf-8").read()
ok("export function compactarAMedida(guias)" in _fj17 and "function hCardAMedida(aspecto)" in _fj17
   and "fichaAMedida(g.a_medida_datos)" in _gen17 and "agruparAMedidaFicha(guias)" in _gen17,
   "la ficha del navegador arma la sección y agrupa en ESTA computadora (MAPA 692; el píxel a píxel lo mira `verificar_navegador_ficha.py`)")
_ps16 = io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
ok("_agrupar_a_medida_ficha(guias, plan[\"cat\"])" not in _ps16 and '_g["a_medida_datos"] = _datos_ficha_a_medida(' in _ps16
   and "_agrupar_a_medida_ficha(_guias, cat)" in _ps16 and 'g["pid"] = _pf' in _ps16,
   "el plan manda sólo los datos guardados (MAPA 692); la ficha del servidor (API/contratos) sigue agrupando igual")
_fd16 = os.path.join(_TMP, "ficha_665"); os.makedirs(_fd16, exist_ok=True)
_r16 = _FT.generar_ficha(_fd16, "Ficha técnica", "Bandera", {"columnas": [{"id": "c", "label": "Cantidad"}], "filas": [{"c": 1}]},
                         [{"nombre": "Bandera", "diseno": "JUGADOR", "piezas": [], "a_medida": {**_fa, "titulo_disenos": "JUGADOR y GOLERO"}},
                          {"nombre": "Bandera", "diseno": "GOLERO", "piezas": [], "a_medida": None}])
_t16 = "".join(pg.get_text() for pg in fitz.open(_r16))
ok("MEDIDA Y TERMINACIÓN · JUGADOR y GOLERO" in _t16 and _t16.count("MEDIDA Y TERMINACIÓN") == 1,
   "la ficha impresa la trae UNA vez, titulada con los dos diseños")
_fj16 = io.open(os.path.join(_AQUI, "frontend", "src", "motor", "ficha", "ficha.js"), encoding="utf-8").read()
ok("(verdad(amF.titulo_disenos) ? ` · ${amF.titulo_disenos}` : '')" in _fj16, "la del navegador igual (gemelo)")

print("\n691 · 🔴 EL SERVIDOR MIDE LA MISMA PIEZA QUE EL VISOR (forma, punta, terminación)")
# El reclamo (2026-10-13): en el servidor publicado un triángulo de 3 × 1,50 que el visor mostraba de
# 300 × 153,4 cm se frenaba al enviar el pedido «mide 300,4 × 158,8»: `_a_medida_telas_que_no_entran` (el
# plan, 409) y `_amTelaNoEntra` (la pantalla) llamaban a la cuenta SIN forma/punta/terminación → un
# rectángulo con el margen guardado. (a) los gemelos dan lo mismo en TODAS las combinaciones; (b) el freno
# del servidor da lo mismo que la cuenta del visor sobre una copia real; (c) la pantalla le pasa todo.
import itertools as _it691
_C691 = []
for f, o, te, rot, mg, (an, al), tela in _it691.product(
        ("rectangulo", "circulo", "triangulo"), ("abajo", "arriba", "izquierda", "derecha"), ("dobladillo", "overlock", "sin"),
        ("ninguna", "90", "libre", "auto"), ({"todos": 0}, {"todos": 2}, {"izq": 1, "der": 3, "arriba": 4, "abajo": 0.5}),
        ((3, 1.5), (1.5, 3), (1.2, 0.8), (4, 1), (1.55, 1.55)), (157, 180, 100)):
    if f != "triangulo" and o != "abajo":
        continue                                    # la punta sólo cambia el triángulo
    _C691.append(dict(anchoM=an, altoM=al, margen=mg, bordeMm=2, anchoCm=tela, largoMaxCm=500, margenNestingMm=10,
                      rotacion=rot, resolucionMm=4, forma=f, orientacion=o, terminacion=te, overlock_cm=1.5))
_f691 = os.path.join(_TMP, "casos_691.json")          # por archivo: en la línea de comandos no entran (WinError 206)
with open(_f691, "w", encoding="utf-8") as _fh:
    json.dump(_C691, _fh)
_js691 = node("import { cabeEnTela, margenDeTerminacion } from './src/motor/molde/aMedida.js'; import { readFileSync } from 'fs';"
              f"const C = JSON.parse(readFileSync({json.dumps(_f691)}, 'utf8'));"
              "console.log(JSON.stringify(C.map(x => { const r = cabeEnTela({ ...x, margen: margenDeTerminacion({ margen: x.margen, overlock_cm: x.overlock_cm }, x.terminacion) });"
              " return [r.cabe, r.motivo || null] })))")
_dif691 = []
for c, (jc, jm) in zip(_C691, _js691):
    _mg = S._margen_de_terminacion({"margen": c["margen"], "overlock_cm": c["overlock_cm"]}, c["terminacion"])
    pc, pm = S._cabe_en_tela(c["anchoM"], c["altoM"], c["bordeMm"], c["anchoCm"], c["largoMaxCm"], c["margenNestingMm"], c["rotacion"],
                             margen=_mg, resolucion_mm=c["resolucionMm"], forma=c["forma"], orientacion=c["orientacion"],
                             terminacion=c["terminacion"])
    if pc != jc or (pm or None) != jm:
        _dif691.append(f"{c['forma']}/{c['orientacion']}/{c['terminacion']}/{c['rotacion']} {c['anchoM']}×{c['altoM']} en {c['anchoCm']}: py {pc} «{pm}» ≠ js {jc} «{jm}»")
ok(not _dif691, f"gemelos `_cabe_en_tela` ↔ `cabeEnTela`: {len(_C691)} combinaciones (forma × punta × terminación × giro × margen × medida × tela) iguales"
   + ("" if not _dif691 else f" — {len(_dif691)} distintas, p. ej. {_dif691[0]}"))

# (b) una COPIA real (triángulo con overlock, margen guardado de dobladillo 4 cm): lo que decide la pantalla
# (`amEnTela`, MAPA 692) = la cuenta que muestra el visor (`estadoMedida`) = lo que valida la API (Python, como
# `integracion_externa`: margen de la terminación + forma + punta)
_cat691 = {"telas": [{"id": "t157", "nombre": "Bandera (1,60)", "ancho_cm": 157}],
           "nesting_presets": [{"id": "np", "nombre": "x", "margen_mm": 10, "rotacion": "libre", "alto_max_cm": 3000}]}
for _f, _te, _an, _al in (("triangulo", "dobladillo", 3, 1.5), ("triangulo", "overlock", 3, 1.5), ("circulo", "sin", 1.55, 1.55),
                          ("rectangulo", "overlock", 3, 1.53), ("triangulo", "dobladillo", 3, 1.6)):
    _am = {"de": "plantilla", "ancho_m": _an, "alto_m": _al, "forma": _f, "orientacion": "abajo", "terminacion": _te,
           "margen": {"todos": 4}, "margen_dobladillo": {"todos": 2}, "overlock_cm": 1}
    _pr = {"id": "copia691", "nombre": "Bandera", "a_medida": _am, "nesting_preset_id": "np"}
    _pub = S._a_medida_publico(_pr, _cat691)
    _n = _pub["nesting"]; _term = S._norm_terminacion(_am["terminacion"])
    _api = S._cabe_en_tela(_an, _al, _pub["borde_mm"], 157, _n["alto_max_cm"], _n["margen_mm"], _n["rotacion"],
                           margen=S._margen_de_terminacion(_am, _term), resolucion_mm=_n["resolucion_mm"],
                           forma=_f, orientacion="abajo", terminacion=_term)
    _vis = node("import { cabeEnTela, amEnTela, margenDeTerminacion, normTerminacion } from './src/motor/molde/aMedida.js';"
                f"const am = {json.dumps(_pub)}; const te = normTerminacion(am.terminacion); const n = am.nesting;"
                "const v = cabeEnTela({ anchoM: am.ancho_m, altoM: am.alto_m, margen: margenDeTerminacion(am, te), bordeMm: am.borde_mm, anchoCm: 157,"
                " largoMaxCm: n.alto_max_cm, margenNestingMm: n.margen_mm, rotacion: n.rotacion, resolucionMm: n.resolucion_mm,"
                " forma: am.forma, orientacion: am.orientacion, terminacion: te });"
                "const p = amEnTela(am, 157);"
                "console.log(JSON.stringify([[v.cabe, v.motivo || null], [p.cabe, p.motivo || null]]))")
    ok(_vis[0] == _vis[1] and _vis[1] == [_api[0], _api[1] or None],
       f"{_f} {_an}×{_al} con {_te}: la pantalla ({'entra' if _vis[1][0] else _vis[1][1]}) = el visor = la API")

# (c) la pantalla frena la tela del pedido con `amEnTela` (la computadora del usuario decide, MAPA 692)
_app691 = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
_i691 = _app691.index("const _amTelaNoEntra = (am, telaId) =>")
_b691 = _app691[_i691:_i691 + 600]
ok("amEnTela(am, t.ancho_cm)" in _b691, "la pantalla (`_amTelaNoEntra`) decide con `amEnTela` (forma, punta, terminación y su margen)")

print("\n692 · 🔴 LA FICHA DEL MOLDE A MEDIDA LA ARMA LA COMPUTADORA DEL USUARIO (el servidor sólo da los datos)")
# Regla del usuario (2026-10-13): «nada del uso depende del servidor». El plan manda `a_medida_datos` (lo
# guardado) y el navegador arma filas, notas, dibujos y el agrupado: tiene que dar EXACTAMENTE lo mismo que
# la ficha del servidor (`_ficha_a_medida`, `_agrupar_a_medida_ficha`), que sigue para la API.
import itertools as _it692


def _igual692(a, b, ruta="$"):
    """Diferencia profunda (números con tolerancia 1e-6); None si son iguales."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return None if abs(float(a) - float(b)) <= 1e-6 else f"{ruta}: {a} ≠ {b}"
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return f"{ruta}: largo {len(a)} ≠ {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _igual692(x, y, f"{ruta}[{i}]")
            if d:
                return d
        return None
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return f"{ruta}: claves {sorted(set(a) ^ set(b))}"
        for k in a:
            d = _igual692(a[k], b[k], f"{ruta}.{k}")
            if d:
                return d
        return None
    return None if a == b else f"{ruta}: {a!r} ≠ {b!r}"


_tpl692 = {"id": "tpl692", "nombre": "Bandera", "a_medida": {"pieza": "Bandera"}, "marcas_tiras": {"grosor_mm": 1.5}}
_LADOS692 = {"rectangulo": {"arriba": 4, "abajo": 1, "izq": 3, "der": 0}, "circulo": {"alrededor": 8},
             "triangulo": {"base": 5, "laterales": 3}}
_casos692, _prods692 = [], []
for (f, o), te, mg, (an, al), tir, borde in _it692.product(
        [("rectangulo", "abajo"), ("circulo", "abajo")] + [("triangulo", x) for x in ("abajo", "arriba", "izq", "der")],
        ("dobladillo", "overlock", "sin"), ({"todos": 2}, {"izq": 1, "der": 3, "arriba": 4, "abajo": 0.5}, {"todos": 0}),
        ((3, 1.5), (1.2, 0.8), (1.55, 1.55)), ("sin", "marca", "no_marca"), (True, False)):
    am = {"de": "tpl692", "pieza": "Bandera", "ancho_m": an, "alto_m": al, "forma": f, "orientacion": o, "terminacion": te,
          "margen_dobladillo": mg, "overlock_cm": 1.5}
    am["margen"] = S._margen_de_terminacion(am)
    pr = {"id": f"c692_{len(_prods692)}", "nombre": "Bandera", "a_medida": am, "borde_corte": {"activo": borde, "ancho_mm": 2}}
    if tir != "sin":
        pr["marcas_tiras"] = {"activo": True, "lados": _LADOS692[f], "marcar": tir == "marca"}
    _prods692.append(pr)
_cat692 = {"productos": [_tpl692] + _prods692}
for pr in _prods692:
    _casos692.append({"py": S._ficha_a_medida(pr, _cat692), "datos": S._datos_ficha_a_medida(pr, _cat692)})
_f692 = os.path.join(_TMP, "casos_692.json")
with open(_f692, "w", encoding="utf-8") as _fh:
    json.dump([c["datos"] for c in _casos692], _fh)
_salida692 = os.path.join(_TMP, "salida_692.json")
node("import { fichaAMedida } from './src/motor/molde/aMedidaFicha.js'; import { readFileSync, writeFileSync } from 'fs';"
     f"const C = JSON.parse(readFileSync({json.dumps(_f692)}, 'utf8'));"
     f"writeFileSync({json.dumps(_salida692)}, JSON.stringify(C.map(d => fichaAMedida(d))));"
     "console.log('1')")
_js692 = json.load(open(_salida692, encoding="utf-8"))
_dif692 = [(i, d) for i, (c, j) in enumerate(zip(_casos692, _js692)) for d in [_igual692(c["py"], j)] if d]
_conDib = sum(1 for c in _casos692 if (c["py"] or {}).get("dibujos"))
ok(not _dif692 and _conDib == len(_casos692),
   f"`fichaAMedida` (navegador) = `_ficha_a_medida` (servidor) en {len(_casos692)} moldes (forma × punta × terminación × margen × "
   f"medida × tiras × borde), filas, notas y dibujos ({_conDib} con dibujos)"
   + ("" if not _dif692 else f" — {len(_dif692)} distintos, p. ej. caso {_dif692[0][0]} "
      f"({_prods692[_dif692[0][0]]['a_medida']['forma']}/{_prods692[_dif692[0][0]]['a_medida']['terminacion']}): {_dif692[0][1]}"))

# el agrupado (MAPA 665-666): mismo orden, mismos bloques, mismas secciones y títulos que el servidor
_g692 = [(0, "JUGADOR"), (len(_prods692) - 1, "OTRO"), (0, "GOLERO"), (5, "ARQUERO"), (None, "BUZO")]
_lista_py, _lista_js = [], []
for idx, dis in _g692:
    if idx is None:
        _lista_py.append({"pid": "buzo", "nombre": "Buzo", "diseno_nombre": dis})
        _lista_js.append({"pid": "buzo", "nombre": "Buzo", "diseno_nombre": dis, "a_medida": None, "a_medida_datos": None})
        continue
    pr = _prods692[idx]
    _lista_py.append({"pid": pr["id"], "nombre": "Bandera", "diseno_nombre": dis, "a_medida": S._ficha_a_medida(pr, _cat692)})
    _lista_js.append({"pid": pr["id"], "nombre": "Bandera", "diseno_nombre": dis, "a_medida_datos": S._datos_ficha_a_medida(pr, _cat692)})
S._agrupar_a_medida_ficha(_lista_py, _cat692)
_f692b = os.path.join(_TMP, "agrupar_692.json")
with open(_f692b, "w", encoding="utf-8") as _fh:
    json.dump(_lista_js, _fh)
_ag692 = node("import { fichaAMedida, agruparAMedidaFicha } from './src/motor/molde/aMedidaFicha.js'; import { readFileSync } from 'fs';"
              f"const G = JSON.parse(readFileSync({json.dumps(_f692b)}, 'utf8'));"
              "for (const g of G) g.a_medida = g.a_medida_datos ? fichaAMedida(g.a_medida_datos) : null;"
              "agruparAMedidaFicha(G);"
              "console.log(JSON.stringify(G.map(g => ({ pid: g.pid, d: g.diseno_nombre, am: g.am || null, sec: g.a_medida ? (g.a_medida.titulo_disenos || '·') : null }))))")
_ag692py = [{"pid": g["pid"], "d": g["diseno_nombre"], "am": g.get("am"), "sec": (g["a_medida"].get("titulo_disenos") or "·") if g.get("a_medida") else None}
            for g in _lista_py]
_dag = _igual692(_ag692py, _ag692)
ok(not _dag, "`agruparAMedidaFicha` = `_agrupar_a_medida_ficha`: mismo orden, mismos bloques compactos y una sección por configuración"
   + ("" if not _dag else f" — {_dag}"))
# (las cuatro banderas salen de la MISMA plantilla: quedan en su orden; el buzo, que no es a medida, al final)
_sec692 = {x["d"]: x["sec"] for x in _ag692}
ok([x["d"] for x in _ag692] == ["JUGADOR", "OTRO", "GOLERO", "ARQUERO", "BUZO"] and _sec692["JUGADOR"] == "JUGADOR y GOLERO"
   and _sec692["GOLERO"] is None and _sec692["OTRO"] == "OTRO" and _sec692["BUZO"] is None,
   f"JUGADOR y GOLERO con la misma bandera: una sola sección titulada con los dos; otra configuración, la suya ({list(_sec692.items())})")

print("\n696 · 🔴 UN MOLDE A MEDIDA SIEMPRE PUEDE GIRAR 90° (en la pantalla, la API y el armado)")
# El reclamo (2026-10-13): en el publicado la Bandera tenía la regla «Estándar» (no gira) y una de 3 × 1,50 no
# entraba en la tela de 1,60; en el taller (regla «Productos simples», giro libre) sí. Una bandera es plana.
_cat696 = {"telas": [{"id": "t157", "nombre": "Bandera (1,60)", "ancho_cm": 157}],
           "nesting_presets": [{"id": "np0", "nombre": "Estándar", "margen_mm": 10, "rotacion": "ninguna", "alto_max_cm": 3000},
                               {"id": "npL", "nombre": "Libre", "margen_mm": 10, "rotacion": "libre", "alto_max_cm": 3000}]}
_am696 = {"de": "tpl", "ancho_m": 3, "alto_m": 1.5, "forma": "triangulo", "orientacion": "abajo", "terminacion": "dobladillo",
          "margen": {"todos": 2}, "margen_dobladillo": {"todos": 2}}
_pr696 = {"id": "c696", "nombre": "Bandera", "a_medida": _am696, "nesting_preset_id": "np0"}
_pub696 = S._a_medida_publico(_pr696, _cat696)
_r696 = node("import { amEnTela, rotacionAMedida } from './src/motor/molde/aMedida.js';"
             f"const am = {json.dumps(_pub696)};"
             "console.log(JSON.stringify([amEnTela(am, 157), ['ninguna','auto','180','90','libre'].map(rotacionAMedida)]))")
ok(_pub696["nesting"]["rotacion"] == "90" and _r696[0]["cabe"] and _r696[0]["girada"],
   f"con la regla «Estándar» (no gira) la bandera 3 × 1,50 entra GIRADA en la tela de 1,60 ({_r696[0].get('motivo')})")
ok(_r696[1] == ["90", "90", "90", "90", "libre"] and [S._rotacion_a_medida(x) for x in ("ninguna", "auto", "180", "90", "libre")] == _r696[1],
   "gemelos `rotacionAMedida` ↔ `_rotacion_a_medida`: «libre» queda libre, lo demás gira 90°")
ok(S._nesting_de({**_pr696, "nesting_preset_id": "npL"}, _cat696)["rotacion"] == "libre"
   and S._nesting_de({"id": "buzo", "nesting_preset_id": "np0"}, _cat696)["rotacion"] == "ninguna",
   "con regla libre sigue libre; un molde que NO es a medida sigue con su regla")
_src696 = io.open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
_cp696 = _src696[_src696.index("def _config_produccion("):_src696.index("def _con_cantidad(")]
ok("rot = _rotacion_a_medida(rot)" in _cp696, "el armado (`_config_produccion` → rotaciones del plan) gira igual que lo que dijo «entra»")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✓ CONTRATO VERDE — el molde a medida se arma, entra (o no) en la tela y se ve con su margen")
