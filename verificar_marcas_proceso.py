# -*- coding: utf-8 -*-
"""CONTRATO DE LAS MARCAS DE PROCESO (TPU · Bordado · DTF) — `py verificar_marcas_proceso.py`

La regla (pedido del usuario 2026-08-26): un objeto editable marcado **no se imprime**. En la
tizada, en su lugar, va una **cruz de 3 cm** (punta a punta, línea fina, negro puro) con la letra
del proceso, centrada donde estaba el objeto. En el **visor** el objeto se sigue viendo entero.

Lo que se verifica:
  1. La cruz mide 3 cm exactos, es negro puro y lleva su letra (T · B · D).
  2. La marca se lee de las TRES formas en que puede estar guardada (formato viejo plano, capa de
     un objeto, capa multi-objeto) y respeta la variable.
  3. Una marca desconocida se ignora (no dibuja nada).
  4. `marcas_como_cruz=False` (el preview del arte) NO cambia lo que se generaba antes.
  5. Sin marcas, el motor genera exactamente lo mismo que antes de la feature (no-regresión).

⚠️ Sólo LEE: usa objetos en memoria y, para la no-regresión, el molde del usuario en una copia
temporal con el módulo `db` reemplazado por un doble.
"""
import os
import re
import sys
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules.setdefault("api_usuarios", types.ModuleType("api_usuarios"))

import motor_pedido as MP    # noqa: E402
# 🔴 El registro de la prueba va a un temporal, y se engancha ANTES de importar `servidor`
# (que espeja la consola al importarse): un test no puede ensuciar el registro del sistema
# de verdad — si no, mañana alguien investiga una falla que provocó una prueba.
import tempfile as _tmp_log, registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(_tmp_log.mkdtemp(prefix="verif_logs_"))
import servidor as S         # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


# ── 1. LA CRUZ ──────────────────────────────────────────────────────────────────────────────
ops = MP._ops_cruz_proceso(100.0, 200.0, "tpu")
_xs = [float(x) for x in re.findall(r"([\d.]+) 200\.000 [ml]", ops)]
_ys = [float(y) for y in re.findall(r"100\.000 ([\d.]+) [ml]", ops)]
_largo_h = (max(_xs) - min(_xs)) / MP.MM if _xs else 0
_largo_v = (max(_ys) - min(_ys)) / MP.MM if _ys else 0
ok(abs(_largo_h - 30.0) < 0.01, f"el brazo horizontal mide 3 cm ({_largo_h:.2f} mm)")
ok(abs(_largo_v - 30.0) < 0.01, f"el brazo vertical mide 3 cm ({_largo_v:.2f} mm)")
ok("0 0 0 1 K" in ops, "va en negro puro (0 0 0 1 K), sin depender del perfil de color")
ok(f"{MP.CRUZ_TRAZO_MM * MP.MM:.3f} w" in ops, f"la línea es GRUESA ({MP.CRUZ_TRAZO_MM} mm)")
ok(MP.CRUZ_TRAZO_MM >= 1.2, f"…y se ve de lejos: {MP.CRUZ_TRAZO_MM} mm de trazo")
ok(MP._ops_cruz_proceso(0, 0, "no_existe") == "", "una marca desconocida no dibuja nada")
ok(sorted(MP.MARCAS_PROCESO) == ["bordado", "dtf", "tpu"], "las tres opciones son TPU, Bordado y DTF")
ok([v["letra"] for v in MP.MARCAS_PROCESO.values()] == ["T", "B", "D"], "cada una con su letra")

# …y con fuente, la letra va DENTRO DE UN CUADRANTE (no al costado de la cruz)
_f = None
try:
    from texto_curvas import FuenteCurvas
    for _c in ("Arial-Bold.ttf", "Anton-Regular.ttf"):
        _p = os.path.join(_AQUI, "catalogo_fuentes", _c)
        if os.path.exists(_p):
            _f = FuenteCurvas(open(_p, "rb").read()); break
except Exception:
    _f = None
if _f:
    CX, CY = 100.0, 200.0
    _r = (MP.CRUZ_MM * MP.MM) / 2.0
    _con = MP._ops_cruz_proceso(CX, CY, "bordado", _f)
    ok(len(_con) > len(ops) and _con.rstrip().endswith("Q"), "con fuente, la letra se dibuja")
    # todos los puntos del trazado de la letra tienen que caer en el cuadrante ARRIBA-DERECHA
    _pts = [(float(a), float(b)) for a, b in re.findall(r"([\d.]+) ([\d.]+) [ml]", _con)]
    _letra = [(x, y) for x, y in _pts if not (abs(y - CY) < 0.01 or abs(x - CX) < 0.01)]
    ok(bool(_letra), "la letra deja su propio trazado (no es sólo la cruz)")
    ok(all(CX < x < CX + _r and CY < y < CY + _r for x, y in _letra),
       f"la letra entra ENTERA en el cuadrante de la cruz ({len(_letra)} puntos)")
    ok(max(y for _x, y in _letra) <= CY + _r and max(x for x, _y in _letra) <= CX + _r,
       "…y no se sale de los 3 cm")

# ── 2. CÓMO SE LEE LA MARCA GUARDADA ────────────────────────────────────────────────────────
prod = {"editables": {"principal": {
    "v_1": {"Editable escudo": {"transforms": {}, "marca": "tpu"},
            "Editable logo": {"objetos": {"o7": {"transforms": {}, "marca": "bordado"},
                                          "o8": {"transforms": {}}}}},
    "v_2": {"Editable escudo": {"transforms": {}}},
}}}
mk = S._editables_marca(prod, "principal")
ok(mk.get("v_1", {}).get("Editable escudo") == "tpu", f"capa de 1 objeto: {mk.get('v_1')}")
ok(any(k.startswith("Editable logo") and v == "bordado" for k, v in mk.get("v_1", {}).items()),
   "capa multi-objeto: la marca es de la FIGURA, no de la capa")
ok("Editable escudo" not in mk.get("v_2", {}), "una variable sin marca no inventa ninguna")
ok(not any("o8" in k for k in mk.get("v_1", {})), "una figura sin marca no aparece")

# formato VIEJO (plano, sin variable) → cae en "*"
_viejo = {"editables": {"principal": {"Editable escudo": {"transforms": {}, "marca": "dtf"}}}}
ok(S._editables_marca(_viejo, "principal").get("*", {}).get("Editable escudo") == "dtf",
   "el formato viejo (sin variable) se lee como «*»")

# ── 2.b SIN MARCA: el objeto lleva proceso pero NO deja nada en la tizada ───────────────────
# (pedido del usuario 2026-08-27). Es un flag APARTE de la marca: «no se sublima» y «no deja
# rastro» son dos decisiones distintas.
_psm = {"editables": {"principal": {
    "v_1": {"Editable escudo": {"transforms": {}, "marca": "tpu", "sin_marca": True},
            "Editable numero": {"transforms": {}, "marca": "dtf"},
            "Editable logo": {"objetos": {"o7": {"transforms": {}, "marca": "bordado", "sin_marca": True},
                                          "o8": {"transforms": {}, "sin_marca": True}}}},
}}}
_sm = S._editables_sin_marca(_psm, "principal")
ok(_sm.get("v_1", {}).get("Editable escudo") is True, f"se lee el flag por capa: {_sm.get('v_1')}")
ok("Editable numero" not in _sm.get("v_1", {}),
   "un objeto con proceso y SIN el flag sigue dejando su cruz")
ok(any(k.startswith("Editable logo") and v is True for k, v in _sm.get("v_1", {}).items()),
   "capa multi-objeto: el flag es de la FIGURA")
ok(any("o8" in k for k in _sm.get("v_1", {})),
   "🔴 «sin marca» es AUTONOMO: vale aunque el objeto NO tenga proceso. Exigir el proceso "
   "primero fue un error mio: la orden del usuario se descartaba en silencio (2026-08-27)")
# el flag NO toca la marca: el objeto se sigue sacando del diseño (no se sublima)
_mk2 = S._editables_marca(_psm, "principal")
ok(_mk2.get("v_1", {}).get("Editable escudo") == "tpu",
   "el objeto sin marca CONSERVA su proceso (se sigue sin sublimar)")
# formato viejo
_v2 = {"editables": {"principal": {"Editable escudo": {"transforms": {}, "marca": "dtf", "sin_marca": True}}}}
ok(S._editables_sin_marca(_v2, "principal").get("*", {}).get("Editable escudo") is True,
   "el formato viejo (sin variable) también se lee como «*»")

# el objeto SIN proceso pero con el flag tiene que salir igual del diseño base
_sm_o8 = [k for k in _sm.get("v_1", {}) if "o8" in k]
ok(bool(_sm_o8), "la figura sin proceso y con el flag llega al motor")

# ── 2.c EL MOTOR NO DIBUJA NADA CUANDO EL FLAG ESTÁ PUESTO ──────────────────────────────────
_src = open(os.path.join(_AQUI, "motor_pedido.py"), encoding="utf-8").read()
ok("editables_sin_marca" in _src and "_sin_marca_de" in _src,
   "el motor recibe y usa `editables_sin_marca`")
ok(re.search(r"_c\s*=\s*_centro_editable\([^)]*\) if \(_mk and not _sin\) else None", _src) is not None,
   "la cruz se dibuja SOLO con proceso y sin el flag")
ok("if (_mk or _sin) and marcas_como_cruz:" in _src,
   "🔴 el flag SOLO (sin proceso) tambien saca el objeto del dibujo")
# …y de la base: si no, el objeto se imprime igual (fue el sintoma reportado)
ok("for _objs in _esinmarca.values():" in _src,
   "🔴 el flag SOLO tambien saca el objeto del DISEÑO BASE (si no, se imprime igual)")
# …y el objeto se sigue sacando del diseño: el `continue` está FUERA del if del centro
_frag = _src[_src.index("if (_mk or _sin) and marcas_como_cruz:"):]
# Se busca el `continue` como SENTENCIA (una linea que sea solo eso), no como palabra suelta: la
# primera version de esta comprobacion daba FALLA por culpa de un comentario que lo nombraba.
_m_cont = re.search(r"^(\s*)continue\s*$", _frag, re.M)
_m_cruz = re.search(r"^\s*arte_draw \+=.*_ops_cruz_proceso", _frag, re.M)
ok(_m_cont is not None and _m_cruz is not None and _m_cont.start() > _m_cruz.start()
   and len(_m_cont.group(1)) < len(_m_cruz.group(0)) - len(_m_cruz.group(0).lstrip()),
   "🔴 el objeto NO se imprime igual: el `continue` esta FUERA del if de la cruz "
   "(si quedara adentro, un objeto sin marca volveria a sublimarse)")
# y la ficha lo tiene que decir
_fsrc = open(os.path.join(_AQUI, "ficha_tecnica.py"), encoding="utf-8").read()
ok("sin_marca" in _fsrc and "SIN MARCA" in _fsrc,
   "la ficha avisa cuáles no dejan marca (si no, el operario busca una cruz que no existe)")

# ── 2.d LA FILA SIN VARIABLE ELEGIDA (bug real del 2026-08-27) ──────────────────────────────
# La config del editable se guarda POR VARIABLE, pero una fila del pedido puede venir sin
# variable (`variante_clave=None`). Antes eso perdía TODA la config en silencio: las marcas no
# se aplicaban y el objeto salía IMPRESO en la tizada. Se reprodujo con el molde del usuario.
_msrc = open(os.path.join(_AQUI, "motor_pedido.py"), encoding="utf-8").read()
ok("def _cfg_var(" in _msrc, "existe el resolutor único de config por variable")
# el patrón a mano puede existir UNA sola vez: dentro del propio resolutor
_pat = ".get(variante) or "
_i_res = _msrc.index("def _cfg_var(")
_i_fin = _msrc.index("def _cmyk4(", _i_res)
ok(_msrc.count(_pat) == 1 and _i_res < _msrc.index(_pat) < _i_fin,
   "🔴 nadie resuelve la variable a mano fuera del resolutor: si vuelve ese patrón, "
   "vuelve el bug de las filas sin variable")
for _q in ("_ecolor", "_emarca", "_esinmarca", "_ecfg"):
    ok(f"_cfg_var({_q}," in _msrc, f"{_q} (config del editable) usa el resolutor")

# la regla, tal cual la implementa el motor
def _cfg_var(mapa, variante):
    if not mapa:
        return {}
    if variante:
        return mapa.get(variante) or mapa.get("*") or {}
    if mapa.get("*"):
        return mapa["*"]
    _cs = [k for k in mapa if (mapa.get(k) or {})]
    return (mapa[_cs[0]] or {}) if len(_cs) == 1 else {}

_una = {"v_bu8p7gy": {"escudo": "tpu"}}
ok(_cfg_var(_una, "v_bu8p7gy").get("escudo") == "tpu", "la fila que elige su variable, la usa")
ok(_cfg_var(_una, None).get("escudo") == "tpu",
   "🔴 fila SIN variable + UNA sola configurada -> se usa esa (era el bug: se perdía)")
_dos = {"v_a": {"escudo": "tpu"}, "v_b": {"escudo": "dtf"}}
ok(_cfg_var(_dos, None).get("escudo") is None,
   "🔴 con VARIAS variables y la fila sin elegir NO se adivina (una prenda mal sale igual de bien impresa)")
ok(_cfg_var(_dos, "v_c").get("escudo") is None,
   "una variable sin config no hereda la de otra")
ok(_cfg_var({"*": {"escudo": "tpu"}, "v_a": {"escudo": "dtf"}}, None).get("escudo") == "tpu",
   "el «*» legacy sigue mandando cuando no hay variable")
ok(_cfg_var({}, None) == {} and _cfg_var(None, "v_a") == {}, "sin config, vacío (no explota)")
# y el servidor tiene que AVISAR el caso ambiguo
_ssrc = open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read()
ok("sin variable elegida y el diseño tiene editables" in _ssrc,
   "el pedido avisa cuando es ambiguo (si no, las marcas no salen y nadie se entera)")

# ── 2.e QUÉ ES «SIN MARCA» (definición del usuario, 2026-08-27) ─────────────────────────────
# «en la tizada no saldrá ninguna marca ni el diseño, pero en el VISOR y en la FICHA TÉCNICA sí lo
# mostrará y dirá la información de qué va, en qué material y qué tamaño».
_pf = {"editables": {"principal": {"v_1": {
    "escudo":   {"transforms": {}, "marca": "tpu", "sin_marca": True},
    "estrella": {"transforms": {}, "sin_marca": True},      # SOLO sin marca, sin proceso
    "numero":   {"transforms": {}, "marca": "dtf"},
    "logo":     {"transforms": {}},
}}}}
_ext_bk = MP.extraer_editables
MP.extraer_editables = lambda *a, **k: [
    {"ident": _n, "nombre": _n, "capa": f"Editable {_n}", "pieza": "Frente", "mesa": 1,
     "w_cm": 7.5, "h_cm": 7.5, "svg": None, "thumb": None}
    for _n in ("escudo", "estrella", "numero", "logo")]
try:
    # 🔴 Desde 2026-09-10 (changelog 423) la marca es DEL PEDIDO, no del molde: la ficha la recibe
    # por parámetro. Los casos son los mismos; lo que cambia es de dónde salen.
    _mk = S._editables_marca(_pf, "principal")
    _sm = S._editables_sin_marca(_pf, "principal")
    _por = {i["nombre"]: i for i in S._procesos_ficha("pid", _pf, "principal", "v_1", "a.ai",
                                                      talle_guia="M", marcas=_mk, sin_marca=_sm)}
    ok("escudo" in _por and _por["escudo"]["sin_marca"] and _por["escudo"]["proceso"] == "TPU",
       "ficha: proceso + sin marca aparece, con su material")
    ok("estrella" in _por and _por["estrella"]["sin_marca"] and not _por["estrella"]["proceso"],
       "🔴 ficha: SOLO «sin marca» (sin proceso) APARECE igual — si no, el objeto desaparece del "
       "sistema y nadie sabe que hay que hacerlo aparte")
    ok(bool(_por["estrella"].get("medidas")), "…y con su TAMAÑO")
    ok("logo" not in _por, "un objeto sin nada no ensucia la ficha")
finally:
    MP.extraer_editables = _ext_bk
_fsrc2 = open(os.path.join(_AQUI, "ficha_tecnica.py"), encoding="utf-8").read()
ok("Falta indicar en qué material se hace" in _fsrc2,
   "sin material elegido la ficha lo PIDE, no inventa uno")
# el VISOR lo sigue mostrando: es `marcas_como_cruz=False`, que ya se verifica más abajo
ok("marcas_como_cruz=False" in open(os.path.join(_AQUI, "servidor.py"), encoding="utf-8").read(),
   "el visor/preview muestra el objeto entero (marcas_como_cruz=False)")

# ── 3. EL MOTOR ACEPTA EL PARÁMETRO SIN CAMBIAR NADA MÁS ────────────────────────────────────
import inspect   # noqa: E402
_sig = inspect.signature(MP.generar_pedido).parameters
ok("editables_marca" in _sig and "marcas_como_cruz" in _sig, "`generar_pedido` recibe las marcas")
ok(_sig["marcas_como_cruz"].default is True,
   "por defecto se dibuja la CRUZ (la tizada); el preview pasa False a propósito")
ok(_sig["editables_marca"].default is None, "sin marcas, el motor se comporta como antes")

# ── 4. EL CENTRO DE LA CRUZ ES EL DEL OBJETO ────────────────────────────────────────────────
# `_centro_editable` tiene que dar el MISMO punto que usa `_matriz_editable` como pivote: si no,
# la cruz caería en otro lado que el objeto.
_obj = {"mesa_rect": (0, 0, 100, 100), "bbox_mu": (40, 40, 60, 60)}
_cont = {"bbox_mu": (0, 0, 100, 100)}
W = H = 200.0; B = 10.0
_c0 = MP._centro_editable({}, _obj, _cont, W, H, B)
ok(_c0 is not None and abs(_c0[0] - (B + 0.5 * W)) < 0.01,
   f"sin mover, la cruz cae en el centro del objeto ({_c0})")
_c1 = MP._centro_editable({"dx": 0.25, "dy": 0}, _obj, _cont, W, H, B)
ok(_c1 and _c1[0] > _c0[0], "si el objeto se movió a la derecha, la cruz lo sigue")
_c2 = MP._centro_editable({"dx": 0, "dy": 0.25}, _obj, _cont, W, H, B)
ok(_c2 and _c2[1] < _c0[1], "y si se movió hacia abajo, también (y-abajo del editor → y-arriba del PDF)")

# ── 5. LA FICHA: UN RENGLÓN POR OBJETO, CON LA MEDIDA DE CADA RANGO ─────────────────────────
# El arte puede venir POR RANGO (una mesa por tramo de talles) y el objeto medir distinto en cada
# uno: la ficha tiene que mostrar TODOS los tramos, no repetir el objeto ni quedarse con uno solo.
_TALLES = ["XS", "S", "M", "L", "XL", "2XL"]
_REG = {"Frente": {t: {} for t in _TALLES}}
_orden_orig, _map_orig, _ext_orig = S._orden_var, MP.mapeo_variantes_arte, MP.extraer_editables
try:
    S._orden_var = lambda reg: _TALLES
    MP.mapeo_variantes_arte = lambda arte, reg, orden: {
        "Frente": {"XS": 1, "S": 1, "M": 2, "L": 2, "XL": 3, "2XL": 3}}
    MP.extraer_editables = lambda arte: [
        {"nombre": "escudo", "ident": "escudo", "capa": "Editable escudo", "pieza": "Frente",
         "w_cm": w, "h_cm": w, "mesa": m, "svg": None, "thumb": None}
        for m, w in ((1, 6.5), (2, 7.5), (3, 8.5))]
    _prodm = {"editables": {"principal": {"v_1": {"escudo": {"transforms": {}, "marca": "tpu"}}}}}
    _r = S._procesos_ficha("pid", _prodm, "principal", "v_1", "arte.ai", talle_guia="M", reg=_REG,
                          marcas=S._editables_marca(_prodm, "principal"),
                          sin_marca=S._editables_sin_marca(_prodm, "principal"))
    ok(len(_r) == 1, f"el objeto se lista UNA sola vez, aunque esté en 3 mesas (salieron {len(_r)})")
    _md = _r[0]["medidas"] if _r else []
    ok(len(_md) == 3, f"una línea por RANGO del arte (salieron {len(_md)})")
    _txt = [f"{m['talles']} → {m['texto']}" for m in _md]
    ok(_txt == ["XS a S → 6.5 × 6.5 cm", "M a L → 7.5 × 7.5 cm", "XL a 2XL → 8.5 × 8.5 cm"],
       f"cada medida con SU tramo de talles: {_txt}")

    # …y con UNA SOLA mesa (default / arte por talle) → la medida del TALLE GUÍA
    MP.mapeo_variantes_arte = lambda arte, reg, orden: {}
    MP.extraer_editables = lambda arte: [
        {"nombre": "escudo", "ident": "escudo", "capa": "Editable escudo", "pieza": "Frente",
         "w_cm": 7.5, "h_cm": 7.5, "mesa": 1, "svg": None, "thumb": None}]
    _r2 = S._procesos_ficha("pid", _prodm, "principal", "v_1", "arte.ai", talle_guia="M", reg=_REG,
                          marcas=S._editables_marca(_prodm, "principal"),
                          sin_marca=S._editables_sin_marca(_prodm, "principal"))
    _md2 = _r2[0]["medidas"] if _r2 else []
    ok(len(_md2) == 1 and _md2[0]["talles"] == "talle M" and _md2[0]["texto"] == "7.5 × 7.5 cm",
       f"sin rangos, la medida es la del TALLE GUÍA: {_md2}")

    # …y si el tamaño está CONFIGURADO, manda la configuración (no el arte)
    _prodc = dict(_prodm, editables_config={"Editable escudo": {"capa": "Editable escudo", "rangos": [
        {"variantes": ["XS", "S", "M"], "apaisado": {"ancho": "8", "alto": "8"}, "vertical": {"ancho": "", "alto": ""}},
        {"variantes": ["L", "XL", "2XL"], "apaisado": {"ancho": "10", "alto": "10"}, "vertical": {"ancho": "", "alto": ""}}]}})
    _r3 = S._procesos_ficha("pid", _prodc, "principal", "v_1", "arte.ai", talle_guia="M", reg=_REG,
                          marcas=S._editables_marca(_prodc, "principal"),
                          sin_marca=S._editables_sin_marca(_prodc, "principal"))
    _t3 = [f"{m['talles']} → {m['texto']}" for m in (_r3[0]["medidas"] if _r3 else [])]
    ok(_t3 == ["XS a M → 8.0 × 8.0 cm", "L a 2XL → 10.0 × 10.0 cm"],
       f"el tamaño CONFIGURADO manda sobre el del arte: {_t3}")
finally:
    S._orden_var, MP.mapeo_variantes_arte, MP.extraer_editables = _orden_orig, _map_orig, _ext_orig

print()
if FALLOS:
    print("✗ FALLA:")
    for f in FALLOS:
        print("   ·", f)
    sys.exit(1)
print("OK marcas: cruz de 3 cm en negro con su letra; la marca se lee en los 3 formatos; "
      "y «sin marca» saca la cruz sin que el objeto vuelva a sublimarse")
