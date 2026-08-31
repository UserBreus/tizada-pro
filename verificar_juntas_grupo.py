# -*- coding: utf-8 -*-
"""Contrato: los vinculos «van juntas» del GRUPO llegan al motor (`juntas_piezas`).

Sin tocar nada del usuario: `_traducir_prendas` se llama con un `prod` y un registro ARMADOS ACA.
Cubre los tres casos: vinculo en el grupo (nuevo), vinculo dentro de la variante (molde viejo) y
los dos a la vez.
"""
import sys, os, types

RAIZ = r"C:\Users\user2\Documents\tincho\codigos\TIZADA PRO"
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")   # sin usuarios: import limpio
import servidor as S

# ── registro ficticio: 3 piezas en el talle M, con sus pieza_idx ────────────────────────────
REG = {
    "Manga corta derecha 1": {"M": {"pieza_idx": 0}},
    "Vivo manga 1":          {"M": {"pieza_idx": 1}},
    "Espalda 1":             {"M": {"pieza_idx": 2}},
}
IDS = {"Manga corta derecha 1": 1, "Vivo manga 1": 2, "Espalda 1": 3}

def _prod(juntas_grupo=None, juntas_var=None):
    return {
        "id": "ZZ_test", "nombre": "TEST", "variante_guia": "M",
        "grupos": [{"id": "gp_1", "nombre": "G", "piezas": [0, 1, 2],
                    **({"juntas": juntas_grupo} if juntas_grupo else {})}],
        "variantes": [{
            "clave": "v_1", "label": "V1", "grupoId": "gp_1",
            "valores": [{"pieza_id": IDS[n], "pieza_idx": REG[n]["M"]["pieza_idx"], "label": n} for n in REG],
            **({"juntas": juntas_var} if juntas_var else {}),
        }],
    }

def _correr(prod):
    """Devuelve las `juntas_piezas` que le llegarian al motor para la prenda de la variable v_1."""
    prendas = [{"cantidad": 1, "talle": "M", "__variante": "v_1"}]
    # el indice pieza_id→clave sale de piezas.json; se inyecta el que necesita la traduccion
    _orig = S._cargar
    def _fake(nombre, pid=None):
        if nombre == "piezas.json":
            return {"piezas": [{"id": v, "clave": k} for k, v in IDS.items()]}
        return _orig(nombre, pid) if pid else _orig(nombre)
    S._cargar = _fake
    try:
        out = S._traducir_prendas(prendas, prod, {"productos": [prod]}, reg=REG)
    finally:
        S._cargar = _orig
    return (out[0] or {}).get("juntas_piezas")

J_GRUPO = [{"id": "j_g", "nombre": "Manga corta derecha", "piezas": [0, 1]}]
J_VAR   = [{"id": "j_v", "nombre": "Espalda+algo",       "piezas": [1, 2]}]

ok = True
casos = [
    ("solo en el GRUPO (nuevo)",            _prod(juntas_grupo=J_GRUPO),               [["Manga corta derecha 1", "Vivo manga 1"]]),
    ("solo en la VARIANTE (molde viejo)",   _prod(juntas_var=J_VAR),                   [["Vivo manga 1", "Espalda 1"]]),
    ("en los DOS lados",                    _prod(juntas_grupo=J_GRUPO, juntas_var=J_VAR),
                                            [["Manga corta derecha 1", "Vivo manga 1"], ["Vivo manga 1", "Espalda 1"]]),
    ("sin vinculos",                        _prod(),                                    None),
]
for nombre, prod, esperado in casos:
    got = _correr(prod)
    bien = (got == esperado)
    ok &= bien
    print(("  OK  " if bien else " FALLA") + f" · {nombre}: {got}")

# -- (2) el endpoint que guarda los grupos NO se come el campo `juntas` ---------------------
_cat = {"productos": [{"id": "ZZ_test", "nombre": "TEST"}]}
S._cargar_catalogo_para_editar = lambda: _cat
S._guardar_catalogo = lambda c: None                      # NO escribir el catalogo real
S._guard_id = lambda cuerpo: None                         # sin sesion en el test
_grupos = [{"id": "gp_1", "nombre": "G", "piezas": [0, 1],
            "juntas": [{"id": "j_g", "nombre": "Manga corta derecha", "piezas": [0, 1]}]}]
with S.app.test_request_context(json={"id": "ZZ_test", "grupos": _grupos}):
    S.set_grupos()
_guardado = (_cat["productos"][0].get("grupos") or [{}])[0].get("juntas")
_bien = _guardado == _grupos[0]["juntas"]
ok &= _bien
print(("  OK  " if _bien else " FALLA") + " * POST /api/productos/grupos conserva juntas: " + str(_guardado))

print("\nRESULTADO:", "OK - los vinculos del grupo llegan al motor" if ok else "FALLA")
sys.exit(0 if ok else 1)
