"""
CONTRATO DE IDENTIDAD DE LAS PIEZAS — se corre con `py verificar_piezas.py`.

Prueba las dos funciones que deciden **cómo se llama** y **quién es** cada pieza. Las dos tuvieron
bugs que le movieron el trabajo al usuario, y los dos son invisibles hasta que ya pasaron:

  · `nombres_normalizados`  — renumeraba TODO un genérico por orden de índice, así que el nombre
                              que vos pusiste terminaba en OTRA pieza.
  · `_regenerar_piezas_index` — el id "estable" colgaba del NOMBRE, así que al renombrar una pieza
                              su id se mudaba con el nombre (o se emitía uno nuevo y las variables
                              que lo apuntaban quedaban colgadas).

⚠️ No toca NADA del usuario. Dos aislamientos, y hacen falta los dos:
   · `TIZADA_DATOS` → un temporal (los archivos).
   · el módulo `db` → un doble que EXPLOTA (la base MSSQL).
"""
import json
import os
import sys
import tempfile
import types

_TMP = tempfile.mkdtemp(prefix="verif_piezas_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
# Segunda barrera por si algo esquivara el doble de abajo: que no haya adónde conectarse.
os.environ["TIZADA_DB_SERVER"] = r"localhost\NO_EXISTE_ES_UNA_PRUEBA"

# ⛔ LA BASE DEL USUARIO NO SE TOCA — y `TIZADA_DATOS` NO alcanza para eso.
#    La conexión sale de `TIZADA_DB_*`, que no tiene NADA que ver con `DATOS`: redirigir los
#    archivos da una sensación de aislamiento que no existe. Correr esta prueba tal cual
#    **escribió un producto y 3 piezas en la base REAL del usuario** (hubo que borrar `prod_test`
#    a mano). Y no es sólo `sync_piezas_molde`: `_guardar_catalogo` reescribe las tablas
#    normalizadas enteras, y hasta LEER el catálogo puede terminar llamándolo.
#    Por eso se reemplaza el MÓDULO COMPLETO antes de importar `servidor` (que hace `import db` a
#    nivel de módulo): así queda cubierto también lo que alguien agregue mañana, y falla RUIDOSO.
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n}) — revisar el aislamiento")))
sys.modules["db"] = _falso_db

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motor_pedido as MP          # noqa: E402
import servidor as S               # noqa: E402

FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)


def asign(*pares):
    return [{"idx": i, "nombre": n} for i, n in pares]


# ══ 1. NOMBRES: lo que el usuario escribió no se toca ═════════════════════════════════════════
n = MP.nombres_normalizados(asign((5, "Frente 2"), (9, "Frente 1")))
ok(n[5] == "Frente 2" and n[9] == "Frente 1",
   f"se intercambiaron los nombres que puso el usuario: {n}")

n = MP.nombres_normalizados(asign((3, "Frente 2")))
ok(n[3] == "Frente 2", f"a un genérico con una sola pieza se le borró el número: {n}")

# ⬇⬇ ESTA ES LA QUE ATRAPA EL BUG (verificada: falla con el código viejo) ⬇⬇
# Dos piezas quedan con el MISMO texto → hay que desambiguar. El código viejo renumeraba TODO el
# genérico 1..N por orden de índice, así que «Frente 7» —que el usuario había puesto bien— pasaba
# a ser «Frente 1». Ahora lo único que ya era único no se toca.
n = MP.nombres_normalizados(asign((1, "Frente 7"), (4, "Frente"), (8, "Frente")))
ok(n[1] == "Frente 7", f"se pisó un nombre único al desambiguar repetidos: {n}")
ok(len({n[1], n[4], n[8]}) == 3, f"quedaron nombres repetidos (colisionan en el registro): {n}")

# idempotencia: volver a pasar el resultado no puede cambiar nada
n1 = MP.nombres_normalizados(asign((1, "Espalda"), (2, "Espalda"), (3, "Cuello")))
n2 = MP.nombres_normalizados([{"idx": i, "nombre": v} for i, v in n1.items()])
ok(n1 == n2, f"no es idempotente: {n1} -> {n2}")

# agregar una pieza NUEVA no puede mover el nombre de las que ya estaban
base = MP.nombres_normalizados(asign((1, "Manga 1"), (2, "Manga 2")))
mas = MP.nombres_normalizados(asign((1, "Manga 1"), (2, "Manga 2"), (7, "Manga")))
ok(all(mas[i] == base[i] for i in base),
   f"nombrar una pieza nueva le cambió el nombre a las viejas: {base} -> {mas}")


# ══ 2. IDENTIDAD: el id no sigue al nombre ════════════════════════════════════════════════════
PID = "prod_test"
os.makedirs(os.path.join(_TMP, "productos", PID), exist_ok=True)


def reg(*pares):
    """registro sintético: {clave: {talle: {mesa, pieza_idx}}} con dos talles."""
    return {clave: {"M": {"mesa": 1, "pieza_idx": idx}, "L": {"mesa": 1, "pieza_idx": idx + 100}}
            for clave, idx in pares}


r1 = reg(("Frente 1", 3), ("Frente 2", 7), ("Cuello 1", 11))
_, clave2id_1, _ = S._regenerar_piezas_index(PID, reg=r1, guia="M")
id_frente1 = clave2id_1["Frente 1"]

# (a) re-correr sin cambios no mueve ningún id
_, clave2id_2, _ = S._regenerar_piezas_index(PID, reg=r1, guia="M")
ok(clave2id_1 == clave2id_2, "re-correr el índice movió ids sin que cambiara nada")

# (b) RENOMBRAR una pieza (misma posición, otro nombre) conserva su id  ← el bug 2
#     ATRAPA EL BUG: verificado que con el código viejo devuelve un id NUEVO (pz_0001 -> pz_0004).
r2 = reg(("Frente Principal", 3), ("Frente 2", 7), ("Cuello 1", 11))
_, clave2id_3, _ = S._regenerar_piezas_index(PID, reg=r2, guia="M")
ok(clave2id_3.get("Frente Principal") == id_frente1,
   f"el id siguió al NOMBRE en vez de a la pieza: {id_frente1} -> {clave2id_3.get('Frente Principal')}")

# (c) el id de una pieza retirada NO se recicla
r3 = reg(("Frente Principal", 3), ("Cuello 1", 11))          # se fue «Frente 2»
_, clave2id_4, _ = S._regenerar_piezas_index(PID, reg=r3, guia="M")
r4 = reg(("Frente Principal", 3), ("Cuello 1", 11), ("Manga 1", 20))   # entra una nueva
_, clave2id_5, _ = S._regenerar_piezas_index(PID, reg=r4, guia="M")
id_frente2 = clave2id_1["Frente 2"]
ok(clave2id_5["Manga 1"] != id_frente2,
   f"la pieza nueva RECICLÓ el id de una retirada ({id_frente2}) — la regla dice que nunca se reusa")

# (d) la pieza retirada sigue en piezas.json (marcada), para poder recuperarla
#     ATRAPA EL BUG: con el código viejo la pieza desaparecía del archivo y su id se perdía.
pz = json.load(open(os.path.join(_TMP, "productos", PID, "piezas.json"), encoding="utf-8"))
retiradas = [p for p in pz["piezas"] if p.get("retirada")]
ok(any(p["id"] == id_frente2 for p in retiradas),
   "la pieza que salió del registro se BORRÓ de piezas.json (se pierde su id para siempre)")

# (e2) RENOMBRAR no puede dejar una entrada RETIRADA con el id de una pieza VIVA.
#      Si el id sigue vivo, la pieza no se fue: se renombró. Con las dos entradas, cualquier
#      `{id: clave}` armado recorriendo la lista se queda con la ÚLTIMA —el nombre VIEJO— y la
#      pieza renombrada desaparece del visor. Pasó de verdad: 24 mangas del molde real.
pz_e = json.load(open(os.path.join(_TMP, "productos", PID, "piezas.json"), encoding="utf-8"))
_vivos = {p["id"] for p in pz_e["piezas"] if not p.get("retirada")}
_choque = [p for p in pz_e["piezas"] if p.get("retirada") and p["id"] in _vivos]
ok(not _choque,
   f"quedaron entradas RETIRADAS con el id de una pieza viva (el nombre viejo pisa al nuevo): "
   f"{[(p['id'], p.get('clave')) for p in _choque][:4]}")
_ids = [p["id"] for p in pz_e["piezas"]]
ok(len(_ids) == len(set(_ids)), f"hay ids repetidos en piezas.json: {len(_ids)} entradas, {len(set(_ids))} ids")

# (e) cambiar el talle guía no cambia ningún id
_, clave2id_6, _ = S._regenerar_piezas_index(PID, reg=r4, guia="L")
ok(all(clave2id_6.get(k) == v for k, v in clave2id_5.items()),
   f"cambiar el talle guía movió los ids: {clave2id_5} -> {clave2id_6}")


# (f) una pieza NUEVA no puede quedarse con el id de una que SIGUE EXISTIENDO
#     Resolviendo de a una clave (clave→ancla→nuevo) el resultado dependía del ORDEN del registro:
#     «Manga 2» entra en la posición que dejó «Frente Principal» y se lleva su id por ANCLA; después
#     «Frente Principal», que sigue viva, recibe el MISMO id por clave exacta → dos claves con un
#     solo pieza_id. Por eso la resolución va en DOS PASADAS (clave exacta primero, toda).
PID2 = "prod_test_orden"
os.makedirs(os.path.join(_TMP, "productos", PID2), exist_ok=True)
r_a = reg(("Frente Principal", 3), ("Espalda 1", 7))
_, c2i_a, _ = S._regenerar_piezas_index(PID2, reg=r_a, guia="M")
# «Manga 2» (nueva) cae justo en el 3, y «Frente Principal» se corrió al 5 pero sigue estando
r_b = reg(("Manga 2", 3), ("Frente Principal", 5), ("Espalda 1", 7))   # ← la nueva va PRIMERO
_, c2i_b, _ = S._regenerar_piezas_index(PID2, reg=r_b, guia="M")
ok(len(set(c2i_b.values())) == len(c2i_b),
   f"dos piezas distintas quedaron con el MISMO id: {c2i_b}")
ok(c2i_b["Frente Principal"] == c2i_a["Frente Principal"],
   f"la pieza nueva le robó el id a una que sigue existiendo: {c2i_a} -> {c2i_b}")


# ══ 3. NOMBRAR DESDE OTRO TALLE NO BORRA LO NOMBRADO ══════════════════════════════════════════
# La pantalla manda SÓLO las piezas del talle que se está mirando. Con eso se reconstruía TODO el
# registro, así que cualquier nombre cuya pieza no apareciera en ese talle se perdía.
_reg5 = {"Frente 1": {"M": {"mesa": 1, "pieza_idx": 3}, "L": {"mesa": 1, "pieza_idx": 103}},
         "Espalda 1": {"M": {"mesa": 1, "pieza_idx": 4}, "L": {"mesa": 1, "pieza_idx": 104}},
         "Cuello 1": {"M": {"mesa": 1, "pieza_idx": 9}}}          # ← no existe en L
_base5 = [{"idx": 3, "nombre": "Frente 1"}, {"idx": 4, "nombre": "Espalda 1"},
          {"idx": 9, "nombre": "Cuello 1"}]

# el idx que se ve en L se traduce al idx de la guía (M) — si no, se nombra OTRA pieza
_trad, _sin = S._asign_a_guia(_reg5, [{"idx": 103, "nombre": "Frente Nuevo"}], "L", "M")
ok(_trad == [{"idx": 3, "nombre": "Frente Nuevo"}] and not _sin,
   f"no se tradujo el indice del talle visto al de la guia: {_trad} / {_sin}")

# ⬇⬇ LA QUE ATRAPA EL BUG 5 ⬇⬇  «Cuello 1» no aparece en L, así que no viene en el payload:
# antes eso significaba «borrala». Ahora significa «no la tocaste».
_m = S._merge_asignaciones(_base5, _trad)
ok({a["nombre"] for a in _m} == {"Frente Nuevo", "Espalda 1", "Cuello 1"},
   f"nombrar desde otro talle borro piezas que no se veian ahi: {_m}")

# quitar un nombre TIENE que seguir siendo posible: el front manda el idx en blanco
_m2 = S._merge_asignaciones(_base5, [{"idx": 4, "nombre": ""}])
ok({a["nombre"] for a in _m2} == {"Frente 1", "Cuello 1"},
   f"no se pudo quitar un nombre (el blanco tiene que pisar): {_m2}")

# una pieza que el registro todavía no conoce no se puede traducir: la devuelve aparte para que
# el llamador la empareje por forma, en vez de tirarla en silencio
_t3, _s3 = S._asign_a_guia(_reg5, [{"idx": 777, "nombre": "Bolsillo"}], "L", "M")
ok(not _t3 and _s3 == [{"idx": 777, "nombre": "Bolsillo"}],
   f"se perdio una pieza nueva nombrada en otro talle: {_t3} / {_s3}")

# mirando la guía no se traduce nada (camino habitual, tiene que quedar igual que siempre)
_t4, _s4 = S._asign_a_guia(_reg5, _base5, "M", "M")
ok(_t4 == _base5 and not _s4, f"se toco el payload estando en la guia: {_t4}")


# ══ Veredicto ════════════════════════════════════════════════════════════════════════════════
import shutil
shutil.rmtree(_TMP, ignore_errors=True)
if FALLOS:
    print(f"\n✗ IDENTIDAD DE PIEZAS ROTA ({len(FALLOS)}):\n")
    for f in FALLOS:
        print("    ·", f)
    sys.exit(1)
print("OK identidad de piezas: los nombres no se mudan y los ids no siguen al nombre")
