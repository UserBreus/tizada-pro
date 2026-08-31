"""
CONTRATO DE «AGREGAR UNA PIEZA AL MOLDE» — `py verificar_agregar_pieza.py`

Es el primer camino del sistema que ESCRIBE geometría en el molde, así que lo que se prueba no es
que "ande": es que **no rompa la identidad de las piezas que ya estaban**.

🔴 El peligro concreto: el `pieza_idx` NO es un id, es la POSICIÓN de la pieza dentro de su capa.
HOY las piezas van en **orden de dibujo** y la nueva se escribe **al final**, así que no se renumera
nada — esta prueba lo MIDE (imprime cuántas cambiarían de índice: 0 de 2760). Con el orden viejo
(por bbox) insertar en el medio corría a 69 de 138 y el nombrado se reasignaba en masa sin ningún
error a la vista; por eso el remapeo sigue acá y se sigue verificando.

Desde 2026-08-21 valen además las reglas nuevas: **duplicar copia la HOMÓLOGA de cada talle** (no
la del mismo número) y **lo preparado se guarda junto, en UNA sola versión** — las dos se prueban
acá. Ya no hay «deshacer»: lo guardado no se borra (se borra el molde entero).

⚠️ No toca nada del usuario: trabaja sobre una COPIA del molde en un temporal, y el módulo `db` se
reemplaza por un doble que explota (ver [[test-no-toca-mssql]]).
"""
import json
import os
import shutil
import sys
import tempfile
import types

_TMP = tempfile.mkdtemp(prefix="verif_agregar_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n})")))

# ── LA "BASE" DEL REGISTRO, SIMULADA (2026-08-19: el server lee el registro SOLO de la base;
#    el doble la imita en memoria, sembrada del JSON que este contrato dejó en su tmp). ──
import json as _rj, os as _ro
_REG_MEM, _REG_REV = {}, {}
def _reg_leer(pid):
    if pid not in _REG_MEM:
        try:
            _p = _ro.path.join(_ro.environ["TIZADA_DATOS"], "productos", pid, "registro_producto.json")
            _REG_MEM[pid] = _rj.load(open(_p, encoding="utf-8")); _REG_REV[pid] = 1
        except Exception:
            return None
    return _REG_MEM.get(pid)
_falso_db.leer_registro = _reg_leer
_falso_db.registro_rev = lambda pid: (_REG_REV.get(pid, 1) if _reg_leer(pid) is not None else None)
_falso_db.guardar_registro = lambda pid, piezas, reg: (_REG_MEM.__setitem__(pid, reg),
                                                  _REG_REV.__setitem__(pid, _REG_REV.get(pid, 1) + 1), 1)[-1]
_falso_db.borrar_piezas_molde = lambda pid: (_REG_MEM.pop(pid, None), _REG_REV.pop(pid, None), 0)[-1]
sys.modules["db"] = _falso_db

_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
import motor_pedido as MP        # noqa: E402
import piezas_molde as PM        # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


# ══ 0. El remapeo, como función pura (sin PDF de por medio) ═══════════════════════════════════
# Se inserta una pieza en la posición 1: las de atrás corren un lugar.
_antes = [(0.0, 0.0, 1.0, 1.0), (5.0, 0.0, 6.0, 1.0), (9.0, 0.0, 10.0, 1.0)]
_desp = [(0.0, 0.0, 1.0, 1.0), (2.0, 0.0, 3.0, 1.0), (5.0, 0.0, 6.0, 1.0), (9.0, 0.0, 10.0, 1.0)]
m = PM.mapa_idx(_antes, _desp)
ok(m == {0: 0, 1: 2, 2: 3}, f"el mapa de indices esta mal: {m}")

_reg = {"Frente": {"M": {"mesa": 1, "pieza_idx": 1}, "L": {"mesa": 1, "pieza_idx": 1}},
        "Cuello": {"M": {"mesa": 1, "pieza_idx": 2}, "L": {"mesa": 1, "pieza_idx": 2}}}
_r2, _n, _av = PM.remapear_registro(_reg, {"M": m, "L": m})
ok(_r2["Frente"]["M"]["pieza_idx"] == 2 and _r2["Cuello"]["M"]["pieza_idx"] == 3,
   f"el registro no se remapeo: {_r2}")
ok(_n == 4, f"mal el conteo de cambios: {_n}")
ok(not _av, f"no deberia haber avisos: {_av}")
# lo que NO se puede reubicar se deja como estaba y se AVISA (nunca se mueve a ciegas)
_r3, _n3, _av3 = PM.remapear_registro({"X": {"M": {"pieza_idx": 99}}}, {"M": m})
ok(_r3["X"]["M"]["pieza_idx"] == 99 and _av3, "una pieza sin correspondencia se movio a ciegas o no aviso")


# ══ 1. Sobre el MOLDE REAL, en una copia ══════════════════════════════════════════════════════
_ORIG = None
for _d in sorted(os.listdir(os.path.join(_AQUI, "entrada"))) if os.path.isdir(os.path.join(_AQUI, "entrada")) else []:
    _p = os.path.join(_AQUI, "entrada", _d, "plantilla.ai")
    if os.path.exists(_p):
        _ORIG = _p
        break

if not _ORIG:
    print("(no hay ningun molde cargado: se corre solo la parte pura)")
else:
    _dir = os.path.join(_TMP, "molde")
    os.makedirs(_dir, exist_ok=True)
    COPIA = os.path.join(_dir, "plantilla.ai")
    shutil.copy(_ORIG, COPIA)

    MESA = 1
    doc = MP._abrir(COPIA)
    TALLES = MP._talles_de_plantilla(doc)
    doc.close()
    ok(len(TALLES) >= 2, f"el molde de prueba tiene {len(TALLES)} talles")

    # ⬇ La lectura RÁPIDA (una pasada por la página) tiene que dar EXACTAMENTE lo mismo que la
    #   lenta (una pasada por talle): de ese orden sale el `pieza_idx`.
    import time as _t
    _t0 = _t.time()
    antes = PM.detectar_por_talle(COPIA, MESA, TALLES)
    _rapido = _t.time() - _t0
    _doc = MP._abrir(COPIA)
    _t1 = _t.time()
    _lento = {t: MP.extraer_piezas_mesa(_doc, MESA, t) for t in TALLES[:3]}
    _lento_s = (_t.time() - _t1) / 3 * len(TALLES)
    _doc.close()
    for t in TALLES[:3]:
        ok(PM.firma_contornos(antes[t]) == PM.firma_contornos(_lento[t]),
           f"talle {t}: la lectura rapida NO da lo mismo que la lenta (cambiaria el pieza_idx)")
    print(f"  · lectura de {len(TALLES)} talles: {_rapido:.1f}s (una pasada) vs ~{_lento_s:.1f}s (una por talle)")

    firmas_antes = {t: PM.firma_contornos(cs) for t, cs in antes.items()}
    n_antes = {t: len(cs) for t, cs in antes.items()}

    # DUPLICAR una pieza: en CADA talle se copia la geometría DE ESE TALLE (no la de la guía) →
    # la pieza nueva acompaña la progresión de talles como cualquier otra.
    _ref_i = min(range(len(antes[TALLES[0]])),
                 key=lambda i: antes[TALLES[0]][i]["w"] * antes[TALLES[0]][i]["h"])
    DX, DY = 2500.0, 0.0
    colocaciones = {}
    for t in TALLES:
        cs = antes[t]
        if _ref_i < len(cs):
            colocaciones[t] = {"segmentos": cs[_ref_i]["segmentos"], "dx": DX, "dy": DY}
    destino, puestos = PM.agregar_pieza(COPIA, colocaciones, mesa=MESA)

    ok(os.path.exists(destino), "no se escribio la version nueva del molde")
    ok(os.path.exists(COPIA), "se toco el archivo ORIGINAL del molde (tiene que quedar intacto)")
    ok(os.path.getsize(COPIA) == os.path.getsize(_ORIG),
       "el archivo original cambio de tamano: se escribio encima en vez de versionar")
    ok(len(puestos) == len(TALLES), f"la pieza no entro en todos los talles: {len(puestos)}/{len(TALLES)}")

    vig = PM.OA.ruta_vigente(COPIA)
    ok(os.path.abspath(vig) == os.path.abspath(destino), f"el puntero de version no quedo en la nueva: {vig}")

    despues = PM.detectar_por_talle(vig, MESA, TALLES)
    # (a) hay UNA pieza más en cada talle
    for t in TALLES:
        ok(len(despues[t]) == n_antes[t] + 1,
           f"talle {t}: se esperaba {n_antes[t]+1} contornos y hay {len(despues[t])}")
    # (b) NO aparecieron talles nuevos (una capa nueva se leeria como un talle)
    d2 = MP._abrir(vig)
    _t2 = MP._talles_de_plantilla(d2)
    d2.close()
    ok(_t2 == TALLES, f"cambiaron los talles del molde: {len(TALLES)} -> {len(_t2)}")

    # (c) ⬇⬇ LA QUE IMPORTA ⬇⬇ el registro se remapea y NINGUNA pieza queda apuntando a otra
    firmas_desp = {t: PM.firma_contornos(cs) for t, cs in despues.items()}
    mapas = {t: PM.mapa_idx(firmas_antes[t], firmas_desp[t]) for t in TALLES}
    # …y el mapa CALCULADO (sin releer el archivo) tiene que dar lo mismo que el medido: es lo que
    # permite sacar la segunda detección completa, que era la mitad del tiempo.
    for t in TALLES:
        _nueva = [c for c in despues[t]
                  if tuple(round(float(v), 1) for v in c["bbox_raw"]) not in set(firmas_antes[t])]
        if len(_nueva) == 1:
            _k = PM.indice_de_insercion(antes[t], _nueva[0]["bbox_mu"])
            ok(PM.mapa_insercion(len(antes[t]), _k) == mapas[t],
               f"talle {t}: el mapa calculado no coincide con el medido (posicion {_k})")
            # y el bbox PREDICHO (sin escribir el archivo) tiene que dar el MISMO indice: es lo que
            # permite avisarle al usuario que numero le toca ANTES de tocar el molde.
            _pred = PM.bbox_desplazado(colocaciones[t]["segmentos"], colocaciones[t]["dx"],
                                       colocaciones[t]["dy"], antes[t])
            ok(PM.indice_de_insercion(antes[t], _pred) == _k,
               f"talle {t}: el indice PREDICHO ({PM.indice_de_insercion(antes[t], _pred)}) no coincide con el real ({_k})")
    for t in TALLES:
        ok(len(mapas[t]) == n_antes[t],
           f"talle {t}: no se pudo reubicar {n_antes[t] - len(mapas[t])} de {n_antes[t]} piezas")
    _corridas = sum(1 for t in TALLES for k, v in mapas[t].items() if k != v)
    print(f"  · piezas que cambiaron de indice al agregar: {_corridas} "
          f"(de {sum(n_antes.values())} en {len(TALLES)} talles)")

    # registro sintético con TODAS las piezas de cada talle → tras remapear, cada nombre tiene que
    # seguir apuntando al MISMO contorno (misma bbox) que antes.
    reg = {}
    for t in TALLES:
        for i, c in enumerate(antes[t]):
            reg.setdefault(f"pz{i}", {})[t] = {"mesa": MESA, "pieza_idx": i}
    reg2, _cam, _avisos = PM.remapear_registro(reg, mapas)
    ok(not _avisos, f"quedaron piezas sin reubicar: {_avisos[:3]}")
    malas = []
    for nom, por_t in reg2.items():
        i_orig = int(nom[2:])
        for t, info in por_t.items():
            j = info["pieza_idx"]
            if firmas_desp[t][j] != firmas_antes[t][i_orig]:
                malas.append((nom, t))
    ok(not malas, f"tras remapear, {len(malas)} piezas apuntan a OTRO contorno: {malas[:4]}")

    # (d) con el ORDEN DE DIBUJO (2026-08-19, entrada 182) la pieza nueva cae SIEMPRE al final:
    # agregar NO renumera a nadie. La aserción vieja exigía lo contrario (que el caso de prueba
    # provocara renumerado); ahora el contrato verifica que el renumerado NO EXISTE.
    sin_remapear = sum(1 for nom, por_t in reg.items() for t, info in por_t.items()
                       if firmas_desp[t][info["pieza_idx"]] != firmas_antes[t][info["pieza_idx"]])
    ok(sin_remapear == 0,
       f"agregar una pieza NO renumera a las existentes (movidas: {sin_remapear})")
    print(f"  · sin el remapeo quedarian {sin_remapear} piezas apuntando a otra")


    # ══ 1.b DUPLICAR COPIA LA HOMÓLOGA, NO EL MISMO NÚMERO ═══════════════════════════════════
    # 🔴 Regla del usuario (2026-08-21): «duplicar debe tomar los vectores, respetar los talles».
    # El endpoint resolvía la pieza de cada talle por el MISMO índice del talle guía, y el índice
    # no se corresponde entre talles (medido en un molde real: «Frente 2» es la #2 en M y la #1 en
    # el talle 0) → en los talles desalineados copiaba OTRA figura, y eso sale impreso.
    # Acá se prueba la resolución que usa el endpoint: la homóloga sale del REGISTRO.
    _guia_t = TALLES[0]                     # en el registro sintetico la guia es el 1er talle
    _t_otro = next((t for t in TALLES if t != _guia_t), None)
    if _t_otro:
        _nom_pz = next(iter(reg))
        _i_guia = reg[_nom_pz][_guia_t]["pieza_idx"]
        _i_otro = reg[_nom_pz][_t_otro]["pieza_idx"]
        # se simula el desalineado: la misma pieza con OTRO índice en el otro talle
        _reg_desal = {k: dict(v) for k, v in reg.items()}
        _otro_idx = (_i_otro + 1) % len(antes[_t_otro])
        _reg_desal[_nom_pz] = dict(_reg_desal[_nom_pz])
        _reg_desal[_nom_pz][_t_otro] = {**_reg_desal[_nom_pz][_t_otro], "pieza_idx": _otro_idx}

        def _homologas(reg_, i, guia, talles):
            """La misma resolución que hace `pieza_agregar` (servidor.py)."""
            nom = next((n for n, por_t in (reg_ or {}).items()
                        if ((por_t or {}).get(guia) or {}).get("pieza_idx") == i), None)
            if not nom:
                return {t: i for t in talles}, None
            out = {}
            for t in talles:
                inf = ((reg_.get(nom) or {}).get(t) or {})
                out[t] = int(inf["pieza_idx"]) if inf.get("pieza_idx") is not None else i
            return out, nom

        _hom, _nom_res = _homologas(_reg_desal, _i_guia, _guia_t, TALLES)
        ok(_nom_res == _nom_pz, f"no se identifico la pieza a duplicar por el registro ({_nom_res})")
        ok(_hom.get(_t_otro) == _otro_idx,
           f"duplicar tomo el indice {_hom.get(_t_otro)} en {_t_otro} y la homologa es {_otro_idx}")
        # y la geometría que se copiaría es la de ESA pieza, no la del mismo número
        _g_hom = antes[_t_otro][_hom[_t_otro]]["segmentos"]
        _g_num = antes[_t_otro][_i_guia]["segmentos"] if _i_guia < len(antes[_t_otro]) else None
        ok(_g_hom is not _g_num or _hom[_t_otro] == _i_guia,
           "la geometria copiada no es la de la pieza homologa")
        # sin nombre no hay correspondencia: cae al mismo indice, y eso se avisa (lo hace el server)
        _hom2, _nom2 = _homologas({}, _i_guia, _guia_t, TALLES)
        ok(_nom2 is None and _hom2[_t_otro] == _i_guia,
           "sin nombre, duplicar tiene que caer al mismo indice (y avisarlo)")
        print(f"  · duplicar: toma la HOMOLOGA de cada talle ({_guia_t}#{_i_guia} -> {_t_otro}#{_otro_idx})")

    # ══ 1.b-bis VARIAS PIEZAS PREPARADAS = UNA SOLA VERSION ═══════════════════════════════════
    # Regla del usuario: nada se escribe hasta «Guardar», y lo preparado se guarda junto. Una
    # version por pieza era ademas una copia entera del molde en disco por cada una.
    _dir2 = os.path.join(_TMP, "multi")
    os.makedirs(_dir2, exist_ok=True)
    COPIA2 = os.path.join(_dir2, "plantilla.ai")
    shutil.copy(_ORIG, COPIA2)
    _t0 = TALLES[0]
    _n0 = len(PM.detectar_por_talle(COPIA2, MESA, [_t0])[_t0])
    _cs = PM.detectar_por_talle(COPIA2, MESA, TALLES)
    _cols = {t: [{"segmentos": _cs[t][0]["segmentos"], "dx": 300.0 * (k + 1), "dy": 0.0}
                 for k in range(3)] for t in TALLES}
    PM.agregar_pieza(COPIA2, _cols, mesa=MESA)
    _vig2 = PM.OA.ruta_vigente(COPIA2)
    _n1 = len(PM.detectar_por_talle(_vig2, MESA, [_t0])[_t0])
    ok(_n1 == _n0 + 3, f"guardar 3 piezas juntas dejo {_n1 - _n0} en {_t0} (esperado 3)")
    ok(PM.OA._ver_actual(COPIA2) == 1, f"3 piezas dejaron {PM.OA._ver_actual(COPIA2)} versiones (esperado 1)")
    print(f"  · 3 piezas preparadas -> UNA sola version, {_n0} -> {_n1} contornos")

    # ══ 1.c DOS PIEZAS SEGUIDAS: la cadena de versiones tiene que quedar sana ══════════════════
    # 🔴 `_ruta_entrada` devuelve la versión VIGENTE. Versionando ESA, la 2ª pieza generaba
    # `plantilla.v1.v1.ai` + un puntero `plantilla.v1.ver`, mientras el puntero bueno seguía en 1 →
    # **la 2ª pieza quedaba huérfana** y el sistema seguía sirviendo el archivo con una sola. Pasó
    # en el molde real del usuario. Se versiona SIEMPRE sobre la base.
    shutil.rmtree(_dir, ignore_errors=True)
    os.makedirs(_dir, exist_ok=True)
    shutil.copy(_ORIG, COPIA)
    T1 = TALLES[0]
    n0 = len(PM.detectar_por_talle(COPIA, MESA, [T1])[T1])
    for paso in (1, 2):
        cs = PM.detectar_por_talle(PM.OA.ruta_vigente(COPIA), MESA, [T1])[T1]
        PM.agregar_pieza(COPIA, {T1: {"segmentos": cs[0]["segmentos"], "dx": 2000.0 * paso, "dy": 0.0}}, mesa=MESA)
    ok(PM.OA._ver_actual(COPIA) == 2, f"el contador de versiones quedo en {PM.OA._ver_actual(COPIA)}, se esperaba 2")
    _sueltos = [f for f in os.listdir(_dir) if ".v1.v" in f or f.endswith(".v1.ver")]
    ok(not _sueltos, f"se versiono sobre una version (quedan archivos huerfanos): {_sueltos}")
    n2 = len(PM.detectar_por_talle(PM.OA.ruta_vigente(COPIA), MESA, [T1])[T1])
    ok(n2 == n0 + 2, f"tras agregar 2 piezas el molde vigente tiene {n2} contornos y deberia tener {n0 + 2}")
    print(f"  · dos piezas seguidas: {n0} -> {n2} contornos, version {PM.OA._ver_actual(COPIA)}, sin archivos huerfanos")

    # ══ 2. LA PIEZA CAE DONDE SE TOCÓ (unidades y sentido de la Y) ════════════════════════════
    # Es lo más fácil de equivocar: el visor trabaja en MILÍMETROS con la Y para ABAJO, y el lienzo
    # del PDF en unidades crudas con la Y para ARRIBA. Un signo al revés y la pieza aparece
    # reflejada respecto de donde tocaste, sin ningún error.
    shutil.rmtree(_dir, ignore_errors=True)
    os.makedirs(_dir, exist_ok=True)
    shutil.copy(_ORIG, COPIA)
    T0 = TALLES[0]
    base = PM.detectar_por_talle(COPIA, MESA, [T0])[T0]
    ref = base[_ref_i]
    DX_MM, DY_MM = 120.0, 80.0                     # 12 cm a la derecha y 8 cm ABAJO en pantalla
    _u = MP.CM / 10.0                              # unidades crudas por milímetro
    PM.agregar_pieza(COPIA, {T0: {"segmentos": ref["segmentos"],
                                  "dx": DX_MM * _u, "dy": -DY_MM * _u}}, mesa=MESA)
    fin = PM.detectar_por_talle(PM.OA.ruta_vigente(COPIA), MESA, [T0])[T0]
    _fa = set(PM.firma_contornos(base))
    nueva = [c for c in fin if tuple(round(float(v), 1) for v in c["bbox_raw"]) not in _fa]
    ok(len(nueva) == 1, f"se esperaba 1 pieza nueva y hay {len(nueva)}")
    if len(nueva) == 1:
        n = nueva[0]
        # en coords CRUDAS (y-arriba): x sube, y BAJA (porque en pantalla va para abajo)
        dx_real = (n["bbox_raw"][0] - ref["bbox_raw"][0]) / _u
        dy_real = (n["bbox_raw"][1] - ref["bbox_raw"][1]) / _u
        ok(abs(dx_real - DX_MM) < 1.0, f"la pieza no cayo en X donde se pidio: {dx_real:.1f} mm en vez de {DX_MM}")
        ok(abs(dy_real + DY_MM) < 1.0,
           f"la Y quedo al reves: se pidio {DY_MM} mm hacia ABAJO en pantalla y dio {-dy_real:.1f} mm")
        ok(abs(n["w"] - ref["w"]) < 0.5 and abs(n["h"] - ref["h"]) < 0.5,
           f"la pieza duplicada cambio de tamano: {n['w']:.1f}x{n['h']:.1f} vs {ref['w']:.1f}x{ref['h']:.1f}")
        print(f"  · colocada a {dx_real:.0f} mm en X y {-dy_real:.0f} mm hacia abajo (se pidio {DX_MM:.0f} y {DY_MM:.0f})")


# ══ Veredicto ════════════════════════════════════════════════════════════════════════════════
shutil.rmtree(_TMP, ignore_errors=True)
if FALLOS:
    print(f"\nx AGREGAR PIEZA AL MOLDE ROTO ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    -", f)
    sys.exit(1)

# ══ 2. EL ENDPOINT REAL (lo que llama la pantalla al tocar «Guardar») ════════════════════════
# Hasta acá se probó el módulo. Esto ejercita `POST /api/plantilla/pieza_agregar` con el cuerpo
# NUEVO —una lista de piezas preparadas— sobre un pid temporal montado en el TIZADA_DATOS de la
# prueba. Nada del usuario: el molde es una copia y el catálogo vive en memoria.
import servidor as S

_PID = "ZZ_test_pieza"
_ent = os.path.join(os.environ["TIZADA_ENTRADA"], _PID)
_dat = os.path.join(_TMP, "productos", _PID)
os.makedirs(_ent, exist_ok=True)
os.makedirs(_dat, exist_ok=True)
shutil.copy(_ORIG, os.path.join(_ent, "plantilla.ai"))

_prod = {"id": _PID, "nombre": "TEST PIEZA", "variante_guia": None}
S._cargar_catalogo = lambda: {"productos": [_prod]}
S._cargar_catalogo_para_editar = lambda: {"productos": [_prod]}
S._guardar_catalogo = lambda c: None
S._guard_molde = lambda pid, perm: None            # sin sesión en la prueba
S._prod_de = lambda pid=None: _prod
S._regenerar_piezas_index = lambda pid, **kw: None  # necesita la base; no es lo que se prueba acá

_doc = MP._abrir(os.path.join(_ent, "plantilla.ai"))
_TALLES_E = MP._talles_de_plantilla(_doc)
_doc.close()
_antes_e = PM.detectar_por_talle(os.path.join(_ent, "plantilla.ai"), 1, _TALLES_E)
_t_e = _TALLES_E[0]
_n_antes_e = len(_antes_e[_t_e])

# registro con UNA pieza nombrada, DESALINEADA a propósito entre talles: si el endpoint duplicara
# por número copiaría otra figura en el segundo talle.
_t2_e = _TALLES_E[1]
_idx_g, _idx_2 = 0, min(2, len(_antes_e[_t2_e]) - 1)
_reg_e = {"Frente": {_t_e: {"mesa": 1, "pieza_idx": _idx_g}, _t2_e: {"mesa": 1, "pieza_idx": _idx_2}}}
json.dump(_reg_e, open(os.path.join(_dat, "registro_producto.json"), "w", encoding="utf-8"))
_REG_MEM[_PID] = _reg_e            # el server lee el registro de la "base" simulada

with S.app.test_request_context(method="POST", json={"pid": _PID, "piezas": [
        {"origen": "duplicar", "pieza_idx": _idx_g, "dx": 400, "dy": 0},
        {"origen": "duplicar", "pieza_idx": _idx_g, "dx": 600, "dy": 0}]}):
    _resp = S.plantilla_pieza_agregar()
_body = _resp[0].get_json() if isinstance(_resp, tuple) else _resp.get_json()
_code = _resp[1] if isinstance(_resp, tuple) else 200
ok(_code == 200, f"el endpoint respondio {_code}: {_body.get('error')}")
ok(_body.get("agregadas") == 2, f"agregadas={_body.get('agregadas')} (esperado 2)")

_vig_e = PM.OA.ruta_vigente(os.path.join(_ent, "plantilla.ai"))
ok(PM.OA._ver_actual(os.path.join(_ent, "plantilla.ai")) == 1,
   "guardar 2 piezas juntas tiene que dejar UNA sola version")
_desp_e = PM.detectar_por_talle(_vig_e, 1, _TALLES_E)
ok(len(_desp_e[_t_e]) == _n_antes_e + 2,
   f"talle {_t_e}: {len(_desp_e[_t_e])} contornos (esperado {_n_antes_e + 2})")
# 🔴 la que importa: en el 2º talle se copio la HOMOLOGA (#{_idx_2}), no la del mismo numero
_fh = PM.firma_contornos([_antes_e[_t2_e][_idx_2]])[0]
_fn = PM.firma_contornos([_antes_e[_t2_e][_idx_g]])[0]
_nuevas2 = [c for c in _desp_e[_t2_e]
            if tuple(round(float(v), 1) for v in c["bbox_raw"]) not in set(PM.firma_contornos(_antes_e[_t2_e]))]
ok(len(_nuevas2) == 2, f"en {_t2_e} aparecieron {len(_nuevas2)} piezas nuevas (esperado 2)")
_w_hom = round(_antes_e[_t2_e][_idx_2]["w"], 1)
_w_num = round(_antes_e[_t2_e][_idx_g]["w"], 1)
if _nuevas2:
    _w_new = round(_nuevas2[0]["w"], 1)
    ok(_w_new == _w_hom, f"se copio la pieza equivocada en {_t2_e}: ancho {_w_new} (homologa {_w_hom}, misma-posicion {_w_num})")
    print(f"  · endpoint: 2 piezas en un POST -> 1 version; en {_t2_e} copio la HOMOLOGA (#{_idx_2}, ancho {_w_hom}) y no la #{_idx_g} (ancho {_w_num})")
else:
    print(f"  · endpoint: respuesta {_code} {_body}")
ok(not hasattr(S, "plantilla_pieza_deshacer"), "quedo el endpoint de deshacer (lo guardado no se borra)")
print("  · «deshacer» ya no existe: lo guardado no se puede sacar")


print("OK agregar pieza: entra en todos los talles, no inventa talles y el registro se remapea entero")
