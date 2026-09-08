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


def _guardar_cfg(nombre, sha1, molde, piezas_n, mesas_n, datos, creado_por=None, id_=None):
    _SEQ[0] += 1
    i = int(id_ or _SEQ[0])
    _CFGS[i] = {"id": i, "nombre": nombre, "sha1": sha1, "molde": molde, "piezas_n": piezas_n,
                "mesas_n": mesas_n, "creado_en": "2026-09-08", "creado_por": creado_por,
                "datos": json.loads(json.dumps(datos))}     # copia: nadie se lleva la referencia
    return i


_falso_db.guardar_config_molde = _guardar_cfg
_falso_db.listar_configs_molde = lambda: [dict(c, datos=None) for c in _CFGS.values()]
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
        reg[n] = {t: {"mesa": i + 1, "idx_mesa": 0, "pieza_idx": idx_desde + i,
                      "bbox_mu": [0, 0, 10, 10]} for t in ("S", "M")}
    return reg


NOMBRES = ["Espalda", "Frente", "Manga derecha", "Manga izquierda"]
PID_A, PID_B = "prod_config_a", "prod_config_b"
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
]}
REGISTROS = {
    PID_A: _registro(NOMBRES),
    PID_B: {f"Pieza {i + 1}": {t: {"mesa": i + 1, "idx_mesa": 0, "pieza_idx": (i + 2) % 4,
                                   "bbox_mu": [0, 0, 10, 10]} for t in ("S", "M")}
            for i in range(4)},
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
    for pid in (PID_A, PID_B):
        d = os.path.join(os.environ["TIZADA_ENTRADA"], pid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "plantilla.ai"), "wb") as f:
            f.write(b"%PDF-1.6 el mismo archivo en dos pedidos\n")


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
ok(_c.get("estado") == "parecida", f"otro archivo con las mismas piezas → «parecida» ({_c.get('estado')})")
print(f"    OK    {_c.get('detalle')}")

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

print("\n6 · BORRAR la configuración no toca ningún molde")
_antes = dict(REGISTROS[PID_B])
r = CLI.delete(f"/api/molde/config/{_id}")
ok((r.get_json() or {}).get("ok") and _id not in _CFGS, "se borra de la lista")
ok(REGISTROS[PID_B] == _antes, "y el molde queda igual (era sólo la receta)")

print()
if FALLOS:
    print(f"❌ {len(FALLOS)} FALLO(S):")
    for f in FALLOS:
        print("   -", f)
    sys.exit(1)
print("✅ CONTRATO VERDE — la configuración se guarda, se elige a mano y vuelve al molde nuevo")
