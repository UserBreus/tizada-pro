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
]
js = node("import { cabeEnTela, talleDeMedida } from './src/motor/molde/aMedida.js';"
          f"const C = {json.dumps(CASOS)};"
          "console.log(JSON.stringify({c: C.map(x => cabeEnTela(x)), t: [talleDeMedida(1.5, 0.9), talleDeMedida(2, 1.005), talleDeMedida(0.333, 12)]}))")
for caso, rj in zip(CASOS, js["c"]):
    cabe, mot = S._cabe_en_tela(caso["anchoM"], caso["altoM"], caso["bordeMm"], caso["anchoCm"], caso["largoMaxCm"],
                                caso["margenNestingMm"], caso["rotacion"])
    ok(cabe == rj["cabe"] and (mot or None) == (rj["motivo"] or None),
       f"{caso['anchoM']}×{caso['altoM']} m en {caso['anchoCm']} cm ({caso['rotacion']}): py {cabe} = js {rj['cabe']}"
       + ("" if (mot or None) == (rj["motivo"] or None) else f" · py «{mot}» ≠ js «{rj['motivo']}»"))
ok(not js["c"][0]["cabe"] and "300 cm" in js["c"][0]["motivo"], "3 × 2 m NO entra en una tela de 1,57 (ejemplo del usuario)")
ok(js["c"][2]["cabe"] and js["c"][2]["girada"], "3 × 1,5 m entra GIRADA si el nesting gira 90°")
ok(not js["c"][3]["cabe"], "el borde de corte suma: 1,57 m + 2 × 1 mm no entra en 157 cm")
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
ok(S._a_medida_telas_que_no_entran(copia, CAT, ["1", "2"]) == [], "1,50 × 0,90 entra en las dos telas")
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
    ok(_lt.get("*") == {"margen_cm": 5.0}, f"todo campo sin límite propio queda adentro del mayor borde del margen ({_lt.get('*')})")
    ok(_lt["numero"]["margen_cm"] == 5.0 and _lt["numero"]["por_pieza"]["Bandera"] == 5.0,
       "un límite menor que el margen sube al margen (y «sin límite» en la pieza también)")
    ok(_lt["nombre"]["margen_cm"] == 8.0, "uno mayor que el margen se respeta")
    ok(S._limite_texto_de({"limite_texto": {"nombre": {"margen_cm": 1}}}) == {"nombre": {"margen_cm": 1.0}},
       "un molde que no es a medida sigue igual")
    import motor_pedido as _MP
    _pers = {"1": {"Palabra": {"x": 1}, "Número": {"x": 2}}}
    _pc = _MP.pers_con_limite(_pers, _lt)
    ok(_pc["1"]["Palabra"].get("limite_cm") == 5.0 and _pc["1"]["Número"].get("limite_cm") == 5.0,
       "el motor aplica «*» a un campo que el molde no nombra (Palabra) y el suyo al Número")
    _cj = node("import { persConLimite } from './src/motor/pieza/estampar.js';"
               f"console.log(JSON.stringify(persConLimite({json.dumps(_pers)}, {json.dumps(_lt)})))")
    ok(_cj["1"]["Palabra"].get("limite_cm") == 5.0 and _cj["1"]["Número"].get("limite_cm") == 5.0,
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
r4 = IE._medida_del_pedido({"ancho_m": 1.5, "alto_m": 0.9}, copia, CAT, telas["1"], {}, telas, "m", "JUGADOR", A)
ok(r4 == {"ancho_m": 1.5, "alto_m": 0.9} and not A, "una medida buena pasa (también con los campos sueltos)")
pubx = IE._a_medida_publico_ext(tpl)
ok(pubx and pubx["pieza"] == "Bandera" and pubx["margen_cm"]["arriba"] == 3.0, "la API publica la pieza y el margen del molde a medida")
ok(IE._a_medida_publico_ext(copia) is None, "…y una copia de pedido no se publica")
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
          "console.log(JSON.stringify({ n: p.length, dash: p[0] && p[0].punteado, enSvg: (r.plan.svg.match(/<path /g) || []).length,"
          " total: r.plan.caminos.length }))")
ok(pl["n"] == 1 and pl["dash"] == [9, 6], f"un camino punteado [9, 6] ({pl})")
ok(pl["enSvg"] == pl["total"] - pl["n"], "el punteado NO va en el SVG (ése se vuelve guía de Illustrator)")
jsx = io.open(os.path.join(_AQUI, "extension_illustrator", "com.tizadapro.illustrator", "jsx", "tizada.jsx"), encoding="utf-8").read()
ok("strokeDashes" in jsx and "punteados" in jsx, "la extensión de Illustrator lo dibuja punteado y no como guía")
cs = io.open(os.path.join(_AQUI, "extension_corel", "puente", "ArmarCorel.cs"), encoding="utf-8").read()
ok("Punteado" in cs and "OutlineStyles" in cs, "el puente de CorelDRAW también")

app = io.open(os.path.join(_AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
print("\n7 · LA PANTALLA")
for ancla, que in (("molde-tipo", "«Con archivo / A medida» al crear el molde"), ("a-medida-panel", "el panel de Moldería del molde a medida"),
                   ("arte-medida", "la tarjeta de la medida en el paso Arte"), ("arte-dobladillo", "la línea punteada en el visor"),
                   ("arte-medida-cambiar", "cambiar la medida"),
                   ("a-medida-convertir", "«Pasar a medida» en Moldería, para un molde que todavía no tiene archivo"),
                   ("a-medida-margen-guardar", "el margen en su propia herramienta"),
                   ("texto-dobladillo", "«Nombre y número» dice que el texto no pasa el margen")):
    ok(f'data-tour="{ancla}"' in app, que)
ok("telasNoEntranDet" in app and "_amTelaNoEntra" in app, "la tela donde no entra no se ofrece y frena el paso")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✓ CONTRATO VERDE — el molde a medida se arma, entra (o no) en la tela y se ve con su margen")
