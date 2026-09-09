"""
CONTRATO: **LA CONFIGURACIÓN DE UN MOLDE SE GUARDA Y SE VUELVE A APLICAR** —
`py verificar_config_guardada.py`.

🔴 LO QUE LO MOTIVÓ (pedido del usuario 2026-09-08): un molde que trae el diseño adentro se sube
PARA UN PEDIDO y se borra con él — y con él se van el nombrado de las piezas, los grupos, las
variables, las telas y el talle de guía. Volver a usar el MISMO archivo en otro pedido obligaba a
rehacer todos los pasos. Ahora esa configuración se guarda en la base **atada al ARCHIVO** (sha1),
no al molde, y el usuario **elige a mano** cuál aplicar.

Lo que se verifica:

  1. **Guardar** deja la configuración con sus piezas, grupos, variables y el resto de los campos.
  2. **La lista dice qué tan bien calza**: `igual` si es del mismo archivo, `parecida` si es otro
     archivo con las mismas piezas y mesas, `distinta` si no. Es una AYUDA para elegir: nada se
     aplica solo.
  3. **Aplicar** le devuelve al molde nuevo el nombrado (pieza por pieza, por `(mesa, idx_mesa)`),
     los grupos, las variables y los campos guardados.
  4. 🔴 **Los grupos y las variables se reubican POR NOMBRE**, no por el `pieza_idx` guardado: si en
     el molde nuevo las piezas quedaron en otro orden, aplicar los índices viejos apuntaría a otra
     pieza — y una tizada mal sale igual de bien impresa.
  5. **Lo que no entra se DICE** (`sin_lugar`, `piezas_perdidas`): el usuario tiene que poder ver
     si acomodó bien.
  6. **Borrar** una configuración no toca ningún molde.
  7. 🔴 **El MISMO molde con OTRO DISEÑO adentro se reconoce igual**: el archivo cambia (otro
     `sha1`) pero las piezas miden lo mismo, y esa HUELLA es la identidad. Un molde distinto
     con la misma cantidad de piezas NO se confunde.
  8. 🔴 **Son de cada usuario**: nadie ve, aplica ni borra la receta de otro.

⚠️ No toca nada del usuario: `DATOS`/`ENTRADA` van a un temporal, el catálogo y el registro son
dobles en memoria y la base es un doble que guarda las configuraciones en un dict (si algo intenta
ir a MSSQL de verdad, la prueba se cae).
"""
import json
import os
import sys
import tempfile
import types

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
_TMP = tempfile.mkdtemp(prefix="verif_cfgmolde_")
os.environ["TIZADA_DATOS"] = os.path.join(_TMP, "datos")
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
os.environ["TIZADA_FUENTES"] = os.path.join(RAIZ, "catalogo_fuentes")
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

# ── EL DOBLE DE `db`: las configuraciones viven en un dict; todo lo demás explota ──────────────
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
_CFGS, _SEQ = {}, [0]


def _guardar_cfg(nombre, sha1, molde, piezas_n, mesas_n, datos, creado_por=None, id_=None,
                 huella=None):
    _SEQ[0] += 1
    i = int(id_ or _SEQ[0])
    _CFGS[i] = {"id": i, "nombre": nombre, "sha1": sha1, "molde": molde, "piezas_n": piezas_n,
                "mesas_n": mesas_n, "creado_en": "2026-09-08", "creado_por": creado_por,
                "huella": huella,
                "datos": json.loads(json.dumps(datos))}     # copia: nadie se lleva la referencia
    return i


def _listar_cfg(creado_por=None, todas=False):
    """Como la de verdad: SÓLO las del usuario que pregunta (ver `db.listar_configs_molde`)."""
    return [dict(c, datos=None) for c in _CFGS.values()
            if todas or (c.get("creado_por") or None) == (creado_por or None)]


_falso_db.guardar_config_molde = _guardar_cfg
_falso_db.listar_configs_molde = _listar_cfg
_falso_db.leer_config_molde = lambda i: (dict(_CFGS[int(i)]) if int(i) in _CFGS else None)
_falso_db.borrar_config_molde = lambda i: (1 if _CFGS.pop(int(i), None) else 0)
_falso_db.guardar_registro = lambda pid, piezas, reg: 1
_falso_db.leer_registro = lambda pid: None
_falso_db.registro_rev = lambda pid: 1
sys.modules["db"] = _falso_db

sys.path.insert(0, RAIZ)
import servidor as S            # noqa: E402

FALLOS = []


def ok(cond, que):
    print(("  OK   " if cond else "  FALLA ") + que)
    if not cond:
        FALLOS.append(que)


# ── EL MOLDE DE MENTIRA ───────────────────────────────────────────────────────────────────────
# Un registro del camino B: cada pieza en su mesa, con `idx_mesa` (la identidad que no depende del
# talle) y `pieza_idx` (la posición dentro del talle, que es la que usan grupos y variables).
def _registro(nombres, idx_desde=0):
    """{nombre: {talle: {mesa, idx_mesa, pieza_idx}}} — una pieza por mesa, dos talles."""
    reg = {}
    for i, n in enumerate(nombres):
        # Las MEDIDAS son la huella del molde: es lo que no cambia cuando cambia el diseño de
        # adentro. Cada pieza mide distinto a propósito, para que la huella tenga señal.
        reg[n] = {t: {"mesa": i + 1, "idx_mesa": 0, "pieza_idx": idx_desde + i,
                      "w_cm": 30.0 + i, "h_cm": 40.0 + 2 * i,
                      "bbox_mu": [0, 0, 10, 10]} for t in ("S", "M")}
    return reg


NOMBRES = ["Espalda", "Frente", "Manga derecha", "Manga izquierda"]
PID_A, PID_B, PID_C, PID_D = ("prod_config_a", "prod_config_b", "prod_config_c",
                              "prod_config_d")
CAT = {"activo": PID_A, "productos": [
    {"id": PID_A, "nombre": "CAMISETA (pedido de ayer)", "origen": "con_diseno", "efimero": True,
     "variante_guia": "M",
     "grupos": [{"id": "gp_1", "nombre": "Comun", "piezas": [0, 1]},
                {"id": "gp_2", "nombre": "Mangas", "piezas": [2, 3]}],
     "variantes": [{"clave": "v_1", "label": "Cuello redondo", "grupoId": "gp_1",
                    "valores": [{"id": "v_0", "label": "Frente", "pieza_idx": 1},
                                {"id": "v_1", "label": "Espalda", "pieza_idx": 0}]}],
     "telas_cfg": {"todas": ["Delta"], "por_pieza": {}, "max_var": {}},
     # 🔴 LO QUE MÁS IMPORTA GUARDAR (pedido del usuario): DÓNDE VA LA ETIQUETA en cada pieza —se
     # marca a mano, pieza por pieza, y cuelga del NOMBRE de la pieza— y cuáles no llevan.
     "etiqueta": {"posiciones": {"Frente": {"rx": 0.5, "ry": 0.9},
                                 "Espalda": {"rx": 0.5, "ry": 0.1},
                                 "v_1§Manga derecha": {"rx": 0.2, "ry": 0.5}},
                  "piezas_off": ["Manga izquierda"], "zonas": {}, "size_mm": 4.2},
     "referencia_medida": "alto"},
    # El molde NUEVO: el mismo archivo subido otra vez. Sus piezas todavía se llaman «Pieza N» y
    # 🔴 quedaron en OTRO ORDEN dentro del talle: si la configuración se aplicara por `pieza_idx`,
    # los grupos y las variables señalarían la pieza equivocada.
    {"id": PID_B, "nombre": "CAMISETA (pedido de hoy)", "origen": "con_diseno", "efimero": True},
    {"id": PID_C, "nombre": "PANTALON (otro molde)", "origen": "con_diseno", "efimero": True},
    {"id": PID_D, "nombre": "CAMISETA (una pieza sin detectar)", "origen": "con_diseno", "efimero": True},
]}
REGISTROS = {
    PID_A: _registro(NOMBRES),
    PID_B: {f"Pieza {i + 1}": {t: {"mesa": i + 1, "idx_mesa": 0, "pieza_idx": (i + 2) % 4,
                                   "w_cm": 30.0 + i, "h_cm": 40.0 + 2 * i,
                                   "bbox_mu": [0, 0, 10, 10]} for t in ("S", "M")}
            for i in range(4)},
    # OTRO MOLDE: mismas 4 piezas en 4 mesas, pero MIDEN DISTINTO. Sirve para comprobar que la
    # huella no confunde dos moldes sólo porque tengan la misma cantidad de piezas.
    PID_C: {f"Pieza {i + 1}": {t: {"mesa": i + 1, "idx_mesa": 0, "pieza_idx": i,
                                   "w_cm": 12.0 + i, "h_cm": 90.0 + i,
                                   "bbox_mu": [0, 0, 10, 10]} for t in ("S", "M")}
            for i in range(4)},
    # EL MISMO molde, pero una pieza no se detecto en esta subida (pasa). Tiene que seguir
    # reconociendose: es lo que justifica que la huella sea de TODOS los talles y que haya un
    # parecido por porcentaje en vez de un si/no.
    PID_D: {f"Pieza {i + 1}": {t: {"mesa": i + 1, "idx_mesa": 0, "pieza_idx": i,
                                   "w_cm": 30.0 + i, "h_cm": 40.0 + 2 * i,
                                   "bbox_mu": [0, 0, 10, 10]} for t in ("S", "M")}
            for i in range(3)},
}
PRODUCCION = {PID_A: {"espaciado_mm": 7, "margen_mm": 12, "rotacion": "auto"}}
GUARDADOS = {}


def _instalar_dobles():
    """Catálogo y registro en memoria; el archivo del molde, un temporal con contenido conocido."""
    S._cargar_catalogo = lambda *a, **k: CAT
    S._cargar_catalogo_para_editar = lambda *a, **k: CAT
    S._guardar_catalogo = lambda c, *a, **k: GUARDADOS.__setitem__("catalogo", True)
    S._soltar_edicion_catalogo = lambda *a, **k: None
    S._cargar = lambda nombre, pid=None, sub=None: (
        REGISTROS.get(pid) if nombre == "registro_producto.json"
        else PRODUCCION.get(pid) if nombre == "config_produccion.json" else None)
    S._guardar_registro = lambda pid, reg, reset=False: REGISTROS.__setitem__(pid, reg)
    S._migrar_nombres_pieza = lambda pid, ren: GUARDADOS.setdefault("migrados", []).append(ren)
    S._uid_actual = lambda *a, **k: 7
    S._usuario_actual = lambda *a, **k: {"id": 7, "permisos": ["molde.editar", "pedido.crear"]}
    S._USUARIOS_ON = False
    # Los dos moldes son el MISMO archivo: mismo contenido, mismo sha1.
    for pid in (PID_A, PID_B, PID_C, PID_D):
        d = os.path.join(os.environ["TIZADA_ENTRADA"], pid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "plantilla.ai"), "wb") as f:
            # A y B son el MISMO archivo (el mismo molde subido dos veces); C es otro molde,
            # asi que tambien es otro archivo: si no, se reconoceria por el sha1 y esta parte
            # de la prueba no probaria nada.
            f.write(b"%PDF-1.6 otro molde distinto\n" if pid == PID_C
                    else b"%PDF-1.6 el mismo, con una pieza menos\n" if pid == PID_D
                    else b"%PDF-1.6 el mismo archivo en dos pedidos\n")


_instalar_dobles()
CLI = S.app.test_client()

print("CONTRATO: LA CONFIGURACIÓN DEL MOLDE SE GUARDA Y SE VUELVE A APLICAR\n")

print("1 · GUARDAR la configuración del molde de ayer")
r = CLI.post("/api/molde/config/guardar", json={"pid": PID_A, "nombre": "Camiseta · cuello redondo"})
d = r.get_json() or {}
ok(r.status_code == 200 and d.get("ok"), f"se guarda (HTTP {r.status_code}: {d})")
ok(d.get("piezas") == 4, f"con sus 4 piezas ({d.get('piezas')})")
_g = _CFGS.get(d.get("id"), {}).get("datos") or {}
ok([p["nombre"] for p in _g.get("piezas") or []] == sorted(NOMBRES, key=lambda n: NOMBRES.index(n)),
   f"guarda el NOMBRADO, ordenado por mesa ({[p['nombre'] for p in _g.get('piezas') or []]})")
ok((_g.get("campos") or {}).get("variante_guia") == "M" and len((_g.get("campos") or {}).get("grupos") or []) == 2,
   "guarda el talle de guía, los grupos y las variables")
ok((_g.get("produccion") or {}).get("espaciado_mm") == 7, "guarda también la config de producción")
print(f"    OK    guardada: {len(_g.get('piezas') or [])} piezas · campos {sorted((_g.get('campos') or {}).keys())}")

print("\n2 · LA LISTA DICE QUÉ TAN BIEN CALZA (ayuda para elegir, no se aplica sola)")
d = (CLI.get(f"/api/molde/config/lista?pid={PID_B}").get_json() or {})
_c = (d.get("configs") or [{}])[0]
ok(_c.get("estado") == "igual", f"mismo archivo → «igual» ({_c.get('estado')}: {_c.get('detalle')})")
with open(os.path.join(os.environ["TIZADA_ENTRADA"], PID_B, "plantilla.ai"), "ab") as f:
    f.write(b"otro archivo, mismas piezas\n")
S._SHA1_CACHE.clear()
_c = ((CLI.get(f"/api/molde/config/lista?pid={PID_B}").get_json() or {}).get("configs") or [{}])[0]
# 🔴 LO QUE PEDÍA EL USUARIO (2026-09-09): el MISMO molde con OTRO DISEÑO adentro es otro archivo
# —otro sha1— y antes caía en «parecida» sólo si coincidían las cuentas de piezas y mesas. Ahora se
# reconoce por la HUELLA: las piezas miden lo mismo, así que el nombrado y la etiqueta sirven tal cual.
ok(_c.get("estado") == "mismo_molde",
   f"otro archivo, mismo molde → «mismo_molde» ({_c.get('estado')}: {_c.get('detalle')})")
print(f"    OK    {_c.get('detalle')}")

print("\n2b · 🔴 Y NO CONFUNDE DOS MOLDES DISTINTOS (misma cantidad de piezas, otras medidas)")
_c2 = ((CLI.get(f"/api/molde/config/lista?pid={PID_C}").get_json() or {}).get("configs") or [{}])[0]
ok(_c2.get("estado") == "distinta",
   f"otro molde con 4 piezas en 4 mesas NO se toma por el mismo ({_c2.get('estado')}: {_c2.get('detalle')})")
print(f"    OK    {_c2.get('detalle')}")

print("\n2c · UNA PIEZA QUE NO SE DETECTO NO PUEDE TIRAR ABAJO EL RECONOCIMIENTO")
_c3 = ((CLI.get(f"/api/molde/config/lista?pid={PID_D}").get_json() or {}).get("configs") or [{}])[0]
ok(_c3.get("estado") == "parecida",
   f"el mismo molde con una pieza menos sigue saliendo como parecida ({_c3.get('estado')})")
print(f"    OK    {_c3.get('detalle')}")

print("\n3 · 🔴 APLICARLA AL MOLDE NUEVO (las piezas están en OTRO ORDEN a propósito)")
_id = list(_CFGS)[0]
r = CLI.post("/api/molde/config/aplicar", json={"pid": PID_B, "id": _id})
d = r.get_json() or {}
ok(r.status_code == 200 and d.get("ok"), f"se aplica (HTTP {r.status_code}: {d})")
ok(d.get("piezas_nombradas") == 4, f"nombra las 4 piezas ({d.get('piezas_nombradas')})")
ok(sorted(REGISTROS[PID_B].keys()) == sorted(NOMBRES),
   f"el molde nuevo queda con los nombres de la configuración ({sorted(REGISTROS[PID_B].keys())})")
_prod_b = next(p for p in CAT["productos"] if p["id"] == PID_B)
# 🔴 LA REGLA DEL USUARIO (2026-09-08): «los ajustes que quiero que se guarden son los de la
# ETIQUETA; los nombres de las piezas es obligatorio siempre». Esas dos cosas entran SOLAS.
ok(len((_prod_b.get("etiqueta") or {}).get("posiciones") or {}) == 3,
   f"🔴 la ETIQUETA entra sin pedirla: 3 posiciones ({(_prod_b.get('etiqueta') or {}).get('posiciones')})")
ok((_prod_b.get("etiqueta") or {}).get("piezas_off") == ["Manga izquierda"],
   "…y también las piezas que NO llevan etiqueta")
ok(d.get("etiqueta_posiciones") == 3 and d.get("etiqueta_apagadas") == 1,
   f"y el informe lo dice ({d.get('etiqueta_posiciones')} posiciones, {d.get('etiqueta_apagadas')} apagadas)")
# …y lo que es DEL PEDIDO no se mete solo: aplicarlo siempre le imponía al pedido nuevo las
# decisiones del viejo sin que nadie las pidiera.
ok(_prod_b.get("variante_guia") is None, f"el {'talle'} de guía NO entra sin tildarlo ({_prod_b.get('variante_guia')})")
ok(_prod_b.get("telas_cfg") is None, f"las telas tampoco ({_prod_b.get('telas_cfg')})")
ok(not _prod_b.get("grupos") and not _prod_b.get("variantes"),
   f"ni los grupos y variables ({_prod_b.get('grupos')} · {_prod_b.get('variantes')})")
print("    OK    entraron la etiqueta y los nombres; el resto quedó afuera")

print("\n3b · …Y LO DEL PEDIDO ENTRA SI SE TILDA")
d = (CLI.post("/api/molde/config/aplicar",
              json={"pid": PID_B, "id": _id,
                    "partes": ["grupos_variables", "telas", "guia", "produccion"]}).get_json() or {})
_prod_b = next(p for p in CAT["productos"] if p["id"] == PID_B)
ok(_prod_b.get("variante_guia") == "M", "con «talle de guía» tildado, entra")
ok((_prod_b.get("telas_cfg") or {}).get("todas") == ["Delta"], "y las telas")
ok(json.load(open(os.path.join(os.environ["TIZADA_DATOS"], "productos", PID_B, "config_produccion.json"),
                  encoding="utf-8")).get("espaciado_mm") == 7,
   "y la config de producción")

print("\n4 · 🔴 LOS GRUPOS Y LAS VARIABLES SE REUBICAN POR NOMBRE, NO POR ÍNDICE")
# En el molde nuevo, «Espalda» quedó en el pieza_idx 2 y «Frente» en el 3 (ver REGISTROS[PID_B]).
_idx = {n: next(iter(v.values()))["pieza_idx"] for n, v in REGISTROS[PID_B].items()}
_g1 = next(g for g in _prod_b["grupos"] if g["nombre"] == "Comun")
ok(sorted(_g1["piezas"]) == sorted([_idx["Espalda"], _idx["Frente"]]),
   f"el grupo «Comun» apunta a Espalda y Frente en SU nuevo índice "
   f"({_g1['piezas']} vs esperado {sorted([_idx['Espalda'], _idx['Frente']])})")
_v = _prod_b["variantes"][0]
ok(sorted(v["pieza_idx"] for v in _v["valores"]) == sorted([_idx["Espalda"], _idx["Frente"]]),
   f"y la variable también ({[v['pieza_idx'] for v in _v['valores']]})")
print(f"    OK    índices viejos [0,1] → nuevos {sorted(_g1['piezas'])} (misma pieza, otro lugar)")

print("\n5 · LO QUE NO ENTRA SE DICE")
_CFGS[_id]["datos"]["piezas"].append({"mesa": 99, "idx_mesa": 0, "pieza_idx": 9, "nombre": "Capucha"})
d = (CLI.post("/api/molde/config/aplicar", json={"pid": PID_B, "id": _id}).get_json() or {})
ok(any("Capucha" in x for x in (d.get("sin_lugar") or [])),
   f"una pieza que este molde no tiene se informa, no se esconde ({d.get('sin_lugar')})")
print(f"    OK    aviso: {(d.get('sin_lugar') or ['-'])[0]}")

print("\n5b · 🔴 LAS CONFIGURACIONES SON DE CADA USUARIO")
# Decision del usuario (2026-09-09): «que se puedan guardar PARA ESE USUARIO que esta trabajando».
# La lista ya solo trae las propias; aplicar y borrar van por `id`, asi que tambien se controlan
# ahi — si no, alcanzaba con escribir el numero a mano para tocar la receta de otro.
_yo = S._uid_actual
S._uid_actual = lambda *a, **k: 9            # entra OTRA persona
_l = ((CLI.get(f"/api/molde/config/lista?pid={PID_B}").get_json() or {}).get("configs") or [])
ok(_l == [], f"otro usuario NO ve las mias (ve {len(_l)})")
_r = CLI.post("/api/molde/config/aplicar", json={"pid": PID_B, "id": _id})
ok(_r.status_code == 404, f"ni puede aplicarlas escribiendo el id a mano (HTTP {_r.status_code})")
_r = CLI.delete(f"/api/molde/config/{_id}")
ok(_r.status_code == 404 and _id in _CFGS, f"ni borrarlas (HTTP {_r.status_code})")
S._uid_actual = _yo
_l = ((CLI.get(f"/api/molde/config/lista?pid={PID_B}").get_json() or {}).get("configs") or [])
ok(len(_l) == 1, f"y el dueno las sigue viendo ({len(_l)})")
print("    OK    cada uno ve, aplica y borra las suyas")

print("\n6 · BORRAR la configuración no toca ningún molde")
_antes = dict(REGISTROS[PID_B])
r = CLI.delete(f"/api/molde/config/{_id}")
ok((r.get_json() or {}).get("ok") and _id not in _CFGS, "se borra de la lista")
ok(REGISTROS[PID_B] == _antes, "y el molde queda igual (era sólo la receta)")

print("\n6b · 🔴 APLICAR MIENTRAS EL MOLDE TODAVIA SE ESTA LEYENDO")
# Reporte del usuario (2026-09-09): subio el molde y apreto «Aplicar» a los 30 s. El camino B
# despliega el molde en un hilo de fondo y el registro de piezas aparece recien al final (en el
# caso real, 2 minutos), asi que se comio un cartel rojo TRES veces y volvio a nombrar a mano.
# El servidor tiene que DISTINGUIR «se esta leyendo» de «no hay molde», para que la pantalla
# pueda esperar y aplicarla sola en cuanto este: el usuario ya la eligio.
# (la de arriba ya se borro en el paso 6: se guarda una propia para esta prueba)
_nid = ((CLI.post("/api/molde/config/guardar",
                  json={"pid": PID_A, "nombre": "para probar la espera"}).get_json()) or {}).get("id")
_reg_d = REGISTROS[PID_D]
REGISTROS[PID_D] = {}                      # el molde esta subido pero todavia sin piezas
_r = CLI.post("/api/molde/config/aplicar", json={"pid": PID_D, "id": _nid})
_d = _r.get_json() or {}
ok(_r.status_code == 409 and _d.get("preparando") is True,
   f"con el molde subido y sin piezas todavia, avisa que se esta LEYENDO "
   f"(HTTP {_r.status_code}, preparando={_d.get('preparando')})")
ok("sola apenas termine" in (_d.get("error") or ""),
   f"y lo dice sin asustar: «{_d.get('error')}»")
_r2 = CLI.post("/api/molde/config/aplicar", json={"pid": "prod_que_no_existe", "id": _nid})
_d2 = _r2.get_json() or {}
ok(_r2.status_code == 409 and not _d2.get("preparando"),
   f"y si NO hay molde, eso NO es «preparando» (preparando={_d2.get('preparando')})")
REGISTROS[PID_D] = _reg_d
# …y la pantalla ESPERA en vez de tirar el cartel rojo
_app0 = open(os.path.join(RAIZ, "frontend", "src", "App.jsx"), encoding="utf-8").read()
_apl = _app0[_app0.index("const aplicarCfgMolde"):_app0.index("const cancelarEsperaCfg")]
ok("d.preparando" in _apl and "setTimeout(" in _apl,
   "la pantalla REINTENTA sola mientras el molde se lee, no muestra un error")
ok("setCfgEsperando(c.nombre)" in _apl, "y mientras tanto dice cual quedo esperando")
print("    OK    se apreta una vez y entra sola cuando el molde esta listo")

print("\n7 · 🔴 LA PANTALLA TRABAJA SOBRE EL MOLDE EXPLICITO, Y SIN TEXTO DE MAS")
# El modal se abre desde DOS lugares: Molderia (molde abierto en Configuracion) y el PEDIDO (el
# molde con diseno). `pidCfg` sirve para el primero y NO para el segundo —cae al ACTIVO del
# server—, asi que guardar desde el pedido habria escrito la configuracion de un molde adentro de
# otro (la trampa del §7 del mapa). Y el pid va POR ARGUMENTO: quien abre hace `setCfgPid` y pide
# la lista en el mismo gesto, cuando React todavia no actualizo el estado.
_app = open(os.path.join(RAIZ, "frontend", "src", "App.jsx"), encoding="utf-8").read()
ok("const cfgPidEfectivo" in _app, "el modal resuelve su molde en un solo lugar (`cfgPidEfectivo`)")
# Se mira SOLO el bloque de las funciones del modal: `pid: pidCfg` es correcto en el resto de la
# pantalla de configuracion (ahi el molde abierto ES el que se edita).
_bloque = _app[_app.index("const cargarCfgGuardadas"):_app.index("const showWarn")]
ok("pid: cfgPidEfectivo()" in _bloque and "const _pidAp = pidExplicito || cfgPidEfectivo()" in _bloque
   and "pid: _pidAp" in _bloque and "pid: pidCfg" not in _bloque,
   "guardar y aplicar usan ESE molde (el explicito, o el abierto en Configuracion), nunca `pidCfg`")
ok("cargarCfgGuardadas(_id, true)" in _app and "cargarCfgGuardadas(pidCfg, true)" in _app,
   "los dos lugares que abren el modal le pasan el molde por ARGUMENTO (estado de React)")
# …y el espacio de las herramientas quedo con los botones y nada mas (pedido del usuario).
ok("<span>Nombrar piezas</span>" in _app and "<span>Ubicar etiqueta</span>" in _app,
   "los botones se llaman «Nombrar piezas» y «Ubicar etiqueta»")
ok("Se nombran en Molderia, con todos los talles a la vista" not in _app
   and "Se nombran en Moldería, con todos los talles a la vista" not in _app,
   "se fue el parrafo que explicaba como nombrar")
ok("Con todo nombrado, elegís el talle guía" not in _app,
   "y el que explicaba como ubicar la etiqueta")
ok('data-tour="pieza-b-configuracion"' in _app,
   "y «Guardar configuracion» esta en el mismo panel del visor")
print("    OK    tres botones, sin texto, y cada uno sobre el molde que corresponde")

print("\n8 · GUARDAR ENCIMA DE UNA QUE YA ESTA (editarla, no juntar copias)")
# Pedido del usuario (2026-09-09): «si quiero editar una configuracion guardada me debe dejar; le
# hago cambios y en vez de guardar una nueva, guardar en la existente». Sin esto quedaban tres o
# cuatro casi iguales y no se sabia cual era la buena.
_id8 = ((CLI.post("/api/molde/config/guardar",
                  json={"pid": PID_A, "nombre": "la que se edita"}).get_json()) or {}).get("id")
_antes8 = len(_CFGS)
# se le cambia el nombre a una pieza y se guarda ENCIMA de la misma receta
REGISTROS[PID_A]["Espalda"] = REGISTROS[PID_A].pop("Espalda")
CAT["productos"][0]["etiqueta"]["posiciones"]["Manga izquierda"] = {"rx": 0.9, "ry": 0.9}
_r8 = CLI.post("/api/molde/config/guardar",
               json={"pid": PID_A, "nombre": "la que se edita", "id": _id8})
_d8 = _r8.get_json() or {}
ok(_r8.status_code == 200 and _d8.get("id") == _id8,
   f"guardar con `id` PISA la misma receta y devuelve su id ({_r8.status_code}, id={_d8.get('id')})")
ok(len(_CFGS) == _antes8, f"y NO deja una copia nueva ({len(_CFGS)} guardadas, eran {_antes8})")
_pos8 = ((_CFGS[_id8]["datos"].get("campos") or {}).get("etiqueta") or {}).get("posiciones") or {}
ok("Manga izquierda" in _pos8, f"y guarda el cambio (posiciones: {sorted(_pos8)})")
# …y NUNCA la de otro
_yo8 = S._uid_actual
S._uid_actual = lambda *a, **k: 9
_r8b = CLI.post("/api/molde/config/guardar",
                json={"pid": PID_A, "nombre": "te la piso", "id": _id8})
ok(_r8b.status_code == 404, f"otro usuario NO puede pisar la mia escribiendo el id (HTTP {_r8b.status_code})")
S._uid_actual = _yo8
ok(_CFGS[_id8]["nombre"] == "la que se edita", "y la receta quedo intacta")
print("    OK    se edita la que ya esta, y nadie pisa la de otro")

print("\n9 · LOS «ADEMAS» VIAJAN CON LA RECETA (no hay que tildarlos cada vez)")
# Pedido del usuario (2026-09-09): «si quiero agregar a una configuracion ya guardada estas
# opciones». Antes vivian solo en la pantalla: la receta no se acordaba de nada y habia que volver
# a tildar lo mismo en cada pedido.
_id9 = ((CLI.post("/api/molde/config/guardar",
                  json={"pid": PID_A, "nombre": "con extras",
                        "partes": ["guia", "telas", "inventada"]}).get_json()) or {}).get("id")
_g9 = _CFGS[_id9]["datos"].get("partes")
ok(sorted(_g9 or []) == ["guia", "telas"],
   f"se guardan las que eligio, y se descarta la que no existe ({_g9})")
_l9 = ((CLI.get(f"/api/molde/config/lista?pid={PID_A}").get_json() or {}).get("configs") or [])
_c9 = next((c for c in _l9 if c["id"] == _id9), {})
ok(sorted(_c9.get("partes") or []) == ["guia", "telas"],
   f"y la lista las devuelve, para poder verlas sin aplicar ({_c9.get('partes')})")

# APLICAR SIN MANDAR NADA usa las de la receta (es lo que hace el aviso, sin abrir el modal)
_prod9 = next(p for p in CAT["productos"] if p["id"] == PID_B)
_prod9.pop("variante_guia", None); _prod9.pop("telas_cfg", None)
_d9 = (CLI.post("/api/molde/config/aplicar", json={"pid": PID_B, "id": _id9}).get_json() or {})
ok(sorted(_d9.get("partes") or []) == ["guia", "telas"],
   f"aplicar SIN mandar partes usa las de la receta ({_d9.get('partes')})")
ok(_prod9.get("variante_guia") == "M" and (_prod9.get("telas_cfg") or {}).get("todas") == ["Delta"],
   "y de verdad entraron el talle de guia y las telas")
# …y si la pantalla manda una lista, manda ella (aunque sea vacia)
_prod9.pop("variante_guia", None)
_d9b = (CLI.post("/api/molde/config/aplicar",
                 json={"pid": PID_B, "id": _id9, "partes": []}).get_json() or {})
ok(not _d9b.get("partes") and _prod9.get("variante_guia") is None,
   f"si la pantalla manda la lista vacia, NO entra nada de eso ({_d9b.get('partes')})")
print("    OK    la receta se lleva sus «ademas» y se aplican solos")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — la configuración se guarda, se elige a mano y vuelve al molde nuevo")
