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
ok(len(S._a_medida_telas_que_no_entran(copia, CAT, ["1", "2"])) == 1, "1,50 × 0,90 + 3 cm de margen por lado (156 cm) ya no entra en la de 1,60")
copia["a_medida"]["ancho_m"] = 1.4
ok(S._a_medida_telas_que_no_entran(copia, CAT, ["1", "2"]) == [], "1,40 × 0,90 + el margen (146 cm) entra en las dos telas")
copia["a_medida"]["ancho_m"] = 3
_no = S._a_medida_telas_que_no_entran(copia, CAT, ["1", "2"])
ok(len(_no) == 1 and _no[0][0] == "Tela 1,60", f"3 m de ancho no entra en la de 1,60 ({_no})")
copia["a_medida"]["ancho_m"] = 1.5

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
ok(r4 == {"ancho_m": 1.4, "alto_m": 0.9} and not A, f"una medida buena pasa (también con los campos sueltos) ({A})")
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
ok(_tt == {"activo": True, "lados": {"arriba": 5, "abajo": 0, "izq": 3, "der": 0}} and not A,
   f"`tiras: {{lleva, lados}}` (con «izquierda» y números como texto); lo que no viene es 0 ({_tt})")
ok(IE._tiras_del_pedido(False, tpl, CAT, "m", A) == {"activo": False, "lados": {"arriba": 0, "abajo": 0, "izq": 0, "der": 0}},
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
   and _rj["tiras"]["total_marcas"] == 4 + 2 + 2 and any(x["lado"] == "arriba" and x["cada_cm"] == 52.0 for x in _rj["tiras"]["por_lado"])
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
ok('"la pieza no entra en la tela"' in srv, "el plan del pedido frena una tela donde la pieza no entra (cinturón)")

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
ok("if (prodCfg?.a_medida && p.w_cm && p.h_cm) {" in app6 and "const mb = margenSobreContorno(prodCfg.a_medida.margen, prodCfg.a_medida.reserva_mm);" in app6,
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
ok('_base_stream += _ops_tiras(_bc.get("tiras"), W + 2*B, H + 2*B)' in _mpsrc, "y el motor del servidor también")
_pt = {"id": "pt", "a_medida": {"margen": {"todos": 3}},
       "marcas_tiras": {"activo": True, "lados": {"izq": "5", "arriba": 99}, "color": [1, 0, 0, 0], "grosor_mm": "1,5"}}
_td = S._tiras_de(_pt)
ok(_td == {"lados": {"arriba": 50, "abajo": 0, "izq": 5, "der": 0}, "color": [1.0, 0.0, 0.0, 0.0], "grosor_mm": 1.5,
           "margen": {"arriba": 3.0, "abajo": 3.0, "izq": 3.0, "der": 3.0}},
   f"el servidor arma lo que lee el motor (por lado, acotado, margen por lado) ({_td})")
ok(S._tiras_limpias({"activo": True, "verticales": 3, "horizontales": 0})["lados"] == {"arriba": 2, "abajo": 2, "izq": 5, "der": 5},
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
ok(_tc and _tc["grosor_mm"] == 2.5 and _tc["color"] == [0.0, 1.0, 0.0, 0.0] and _tc["lados"]["abajo"] == 3,
   f"la copia del pedido: lados propios, grosor y color del molde ({_tc})")
# 🔴 LA FICHA TÉCNICA DEL MOLDE A MEDIDA (MAPA 643): medida, total, margen, borde y las tiras con cuántas y
# cada cuánto (sobre el borde, de punta a punta), de la MISMA geometría que imprime el motor
_cf = {"id": "cop_f", "a_medida": {"ancho_m": 3, "alto_m": 1.5, "margen": {"todos": 3}, "de": "tpl_t"},
       "borde_corte": {"activo": True, "ancho_mm": 2},
       "marcas_tiras": {"activo": True, "lados": {"arriba": 5, "abajo": 5, "izq": 1, "der": 0}}}
_fa = S._ficha_a_medida(_cf, {"productos": [_ctpl, _cf]})
_fv = {f["etiqueta"]: f["valor"] for f in (_fa or {}).get("filas", [])}
ok(_fv.get("Medida del diseño (guía)") == "300 × 150 cm" and _fv.get("Total del arte (con el margen)") == "306 × 156 cm"
   and _fv.get("Margen (dobladillo)") == "3 cm por lado" and _fv.get("Borde de corte") == "2 mm, adentro de la medida total",
   f"la ficha dice la medida del diseño, el total con el margen, el margen y el borde ({_fv})")
ok(_fv.get("Tiras", "").startswith("11 marcas en total · grosor 2,5 mm · color C0 M100 Y0 K0")
   and _fv.get("Arriba") == "5 marcas contando las 2 puntas, una cada 76,5 cm · marca de 3 cm"
   and _fv.get("Izquierda") == "1 marca, en el medio (a 78 cm de cada punta) · marca de 3 cm" and "Derecha" not in _fv,
   f"y las tiras: cuántas en total (las esquinas una vez), por lado cuántas y cada cuánto se cosen ({_fv.get('Tiras')})")
ok(S._ficha_a_medida({"id": "n", "nombre": "Buzo"}) is None, "un molde que no es a medida no agrega la sección")
import ficha_tecnica as _FT   # noqa: E402
_fdir = os.path.join(_TMP, "ficha_am"); os.makedirs(_fdir, exist_ok=True)
_pz = fitz.open(); _pz.new_page(width=306 * 28.3465, height=156 * 28.3465); _pzb = _pz.tobytes(); _pz.close()
_rf = _FT.generar_ficha(_fdir, "Ficha técnica", "Bandera", {"columnas": [{"id": "c", "label": "Cantidad"}], "filas": [{"c": 1}]},
                        [{"nombre": "Bandera 3,00x1,50", "diseno": "Principal", "piezas": [{"nombre": "Bandera", "w_cm": 306, "h_cm": 156, "pdf": _pzb}],
                          "a_medida": _fa}])
_ftx = "".join(pg.get_text() for pg in fitz.open(_rf))
ok("MEDIDA Y TERMINACIÓN" in _ftx and "una cada 76,5 cm" in _ftx and "306 × 156 cm" in _ftx,
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
ok("panelIzquierdo={(_amIt && _amIt.de) ? _panelMedida" in app,
   "con el molde armado, la medida queda a la vista al lado del visor (en lugar de los talles de la plantilla)")
# 🔴 UN SOLO LUGAR (pedido del usuario 2026-10-07: «usá la misma visual, no lo separes en 2 espacios»): el dibujo de la
# medida va EN el visor del paso, no en una pantalla aparte ni en un dibujito dentro del panel
ok("telaAMedida={_telaVisor}" in app
   and app.count("telaAlrededor(") >= 3 and "_tarjetaMedida" not in app,
   "la medida se dibuja EN el visor del paso: en vivo mientras se escribe y, armada, la misma tela alrededor del arte")
ok("[_claveTelaDis(did, d.id)]: v" in app, "la tela elegida antes de armar pasa a la copia del pedido")
# 🔴 SIN BOTÓN NI LISTA APARTE (pedido del usuario 2026-10-07: «no lo separes en 2; elegir la tela como siempre»): la
# medida se arma sola al dejar de escribir y la tela va por «Asignar telas»
ok("amIntentoRef.current = firma; armarAMedida(st.did, st.it, st.a, st.h)" in app and "listaParaArmar" in app
   and "Armar a esta medida" not in app and "— Elegí la tela —" not in app,
   "la medida se arma sola (sin botón) y la tela se elige como siempre (sin lista propia en el panel)")
# 🔴 DE ENTRADA, EL PASO COMPLETO (MAPA 637): el molde a medida recién elegido se arma solo con la medida
# PREDETERMINADA de Ajustes; la medida se cambia en el panel del paso, no en otra pantalla
ok("(st.esCopia && !amForm[st.clave])" in app and "metrosTexto(_amIt.ancho_m || 1)" in app,
   "el molde a medida se arma solo con la medida predeterminada al entrar al paso Arte")
# 🔴 CAMBIAR LA MEDIDA ES INSTANTÁNEO (MAPA 638): el visor de siempre dibuja la medida escrita al toque
# (`_layoutVivo`) y el archivo se rehace de fondo, SIN el cartel que tapa todo
ok("canvasLayout={_layoutVivo || canvasLayout}" in app and "previewPiezas={_pvMedida}" in app
   and "const avisar = silencioso ? () => {} : (t) => setProcesando(t);" in app and "!amArmando && !!st" in app,
   "cambiar la medida se ve al instante en el mismo visor y el molde se rehace de fondo, sin cartel")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✓ CONTRATO VERDE — el molde a medida se arma, entra (o no) en la tela y se ve con su margen")
