# -*- coding: utf-8 -*-
"""CONTRATO: UN MOLDE ARCHIVADO NO SE USA — `py verificar_molde_archivado.py` (MAPA 745)

Pedido del usuario (2026-10-23): «poder archivar moldes; los archivados no se pueden usar (ni el molde ni
sus variables) en pedido, no aparecen en pedido, y en Configuración van en un espacio aparte de donde se
vuelven a habilitar». Permiso propio `molde.archivar` (lo recibe el admin solo).

Se verifica, en el entorno aislado de `verificar_navegador_tizada` (`db` es un doble, nada de MSSQL ni de
`datos/` del usuario):
  1. archivar y volver a habilitar guarda / saca la marca, sin tocar nada más del molde;
  2. sin el permiso `molde.archivar` → 403; un «Mi artículo» o una copia de pedido → 400;
  3. `GET /api/productos` dice `archivado` (Configuración lo necesita); el diagnóstico lo explica;
  4. no se activa, el plan del pedido lo frena (también la COPIA a medida de una plantilla archivada),
     no se hace una copia a medida nueva, y la PC no lo baja de fondo;
  5. la API externa: no publica sus variables ni el molde, y el pedido vuelve con `molde-archivado`.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import verificar_navegador_tizada as VT       # noqa: E402  (entorno aislado + doble de la base)

S, ok, FALLOS, _DOCS, _REG = VT.S, VT.ok, VT.FALLOS, VT._DOCS, VT._REG
import integracion_externa as IE              # noqa: E402
import auth                                   # noqa: E402

A, B, T, C, P = "prod_arch_a", "prod_arch_b", "prod_arch_tpl", "prod_arch_copia", "prod_arch_propio"
REG = {"Frente": {"M": {"mesa": 1, "pieza_idx": 0}}}


def _var(cl):
    return [{"clave": cl, "label": cl.upper(), "valores": [{"pieza_idx": 0, "pieza_id": 1}]}]


def _cat_guia(cat):
    # el talle guía: con él la variable resuelve sus piezas por `pieza_idx` (como un molde de verdad)
    for p in cat["productos"]:
        p["variante_guia"] = "M"
    return cat


def _catalogo():
    am = {"pieza": "Bandera", "margen": {}, "ancho_m": 1, "alto_m": 1, "variable": "v_tpl"}
    return {"activo": A, "productos": [
        {"id": A, "nombre": "Camiseta A", "variantes": _var("v_a")},
        {"id": B, "nombre": "Camiseta B", "variantes": _var("v_b"), "editables": {"x": 1}},
        {"id": T, "nombre": "Bandera", "variantes": _var("v_tpl"), "a_medida": dict(am)},
        {"id": C, "nombre": "Bandera 1x1", "variantes": _var("v_copia"), "efimero": True,
         "a_medida": dict(am, de=T, variable="v_copia")},
        {"id": P, "nombre": "Mío", "variantes": _var("v_p"), "propio": True, "creado_por": 7},
    ]}


def _prod(pid):
    return next(p for p in _DOCS["catalogo"]["productos"] if p["id"] == pid)


def main():
    print("CONTRATO — UN MOLDE ARCHIVADO NO SE USA\n")
    _DOCS["catalogo"] = _cat_guia(_catalogo())
    for pid in (A, B, T, C, P):
        _REG[pid] = REG
        os.makedirs(os.path.join(S.ENTRADA, pid), exist_ok=True)
        open(os.path.join(S.ENTRADA, pid, "plantilla.ai"), "wb").close()
    cli = S.app.test_client()

    print("0 · EL PERMISO")
    ok(any(p[0] == "molde.archivar" for p in auth.PERMISOS), "`molde.archivar` está en el catálogo de permisos")
    ok("molde.archivar" in dict((r[0], r[4]) for r in auth.ROLES_DEFAULT)["admin"], "el admin lo recibe solo")

    print("\n1 · ARCHIVAR Y VOLVER A HABILITAR")
    r = cli.post("/api/productos/archivar", json={"id": B, "archivar": True})
    ok(r.status_code == 200 and isinstance(_prod(B).get("archivado"), dict), f"archivar → marca guardada ({r.status_code})")
    ok(_prod(B).get("editables") == {"x": 1} and _prod(B).get("variantes") == _var("v_b"),
       "no toca nada más del molde (variables, editables)")
    r = cli.post("/api/productos/archivar", json={"id": T, "archivar": True})
    ok(r.status_code == 200, "se archiva la plantilla a medida")

    print("\n2 · QUIÉN PUEDE Y QUÉ")
    ok(cli.post("/api/productos/archivar", json={"id": C}).status_code == 400, "la copia de un pedido no se archiva (400)")
    ok(cli.post("/api/productos/archivar", json={"id": P}).status_code == 400, "un «Mi artículo» no se archiva (400)")
    _u0, _on0 = S._usuario_actual, S._USUARIOS_ON
    try:
        S._USUARIOS_ON = True
        S._usuario_actual = lambda: {"id": 2, "usuario": "op", "nombre": "Op", "permisos": ["molde.ver", "molde.editar"]}
        r = cli.post("/api/productos/archivar", json={"id": A})
        ok(r.status_code == 403 and "molde.archivar" in (r.get_json() or {}).get("error", ""),
           f"sin `molde.archivar` → 403 que dice qué permiso falta ({r.status_code})")
        S._usuario_actual = lambda: {"id": 1, "usuario": "adm", "nombre": "Admin", "permisos": ["molde.ver", "molde.archivar"]}
        r = cli.post("/api/productos/archivar", json={"id": A})
        ok(r.status_code == 200 and (_prod(A).get("archivado") or {}).get("por_nombre") == "Admin",
           "con `molde.archivar` (y sin `molde.editar`) archiva y anota quién")
        r = cli.post("/api/productos/archivar", json={"id": A, "archivar": False})
        ok(r.status_code == 200 and "archivado" not in _prod(A), "…y lo vuelve a habilitar")
    finally:
        S._usuario_actual, S._USUARIOS_ON = _u0, _on0

    print("\n3 · LO QUE VE LA PANTALLA")
    lista = {p["id"]: p for p in cli.get("/api/productos").get_json()["productos"]}
    ok(lista[B].get("archivado") and not lista[A].get("archivado"), "`GET /api/productos` dice cuál está archivado")
    ok((lista[C].get("archivado") or {}).get("de_plantilla") is True, "la copia de una plantilla archivada viene marcada (de_plantilla)")
    diag = {m["id"]: m for m in cli.get("/api/productos/diagnostico").get_json()["moldes"]}
    ok(diag[B]["archivado"] and "ARCHIVADO" in diag[B]["motivo"], "el diagnóstico lo explica")

    print("\n4 · NO SE USA")
    r = cli.post("/api/productos/activar", json={"id": B})
    ok(r.status_code == 409, f"no se activa ({r.status_code})")
    for pid, que in ((B, "el molde"), (C, "la copia a medida de una plantilla archivada")):
        r = cli.post("/api/pedido/plan", json={"prendas": [{"talle": "M", "cantidad": 1}], "molds": [pid]})
        ok(r.status_code == 409 and "archivado" in ((r.get_json() or {}).get("error") or ""),
           f"el plan del pedido frena {que} ({r.status_code})")
    _, _, err = S._a_medida_crear({"a_medida_de": T, "efimero": True, "ancho_m": 1, "alto_m": 1},
                                  _DOCS["catalogo"], "prod_x")
    ok(bool(err) and err[1] == 409, "no se arma una copia a medida nueva de la plantilla archivada")
    bajar = cli.get("/api/moldes/para_bajar").get_json() or {}
    _ids = {m.get("id") or m.get("pid") for m in (bajar.get("moldes") or [])}
    ok(A in _ids and B not in _ids and T not in _ids, f"la PC no lo baja de fondo (y sí el habilitado: {sorted(_ids)})")

    print("\n5 · LA API EXTERNA")
    ok(IE._molde_listo(_prod(B), REG) == (False, "está archivado"), "`_molde_listo` → «está archivado»")
    _vars = {v["clave"] for v in IE.variables_publicas(_DOCS["catalogo"])}
    ok("v_a" in _vars and "v_b" not in _vars and "v_tpl" not in _vars,
       f"no publica sus variables, y sí las del habilitado ({sorted(_vars)})")
    ok("molde-archivado" in IE.ALARMAS and IE.ALARMAS["molde-archivado"][1] is True, "alarma `molde-archivado` (frena)")
    with S.app.test_request_context():
        ok(IE.v1_molde(B)[1] == 404, "`/moldes/<pid>` de un archivado → 404")
        ok(all(m["codigo"] != B for m in IE.v1_moldes().get_json()["moldes"]), "`/moldes` no lo lista")

    print("\n6 · VOLVER A HABILITAR LO DEJA COMO ESTABA")
    r = cli.post("/api/productos/archivar", json={"id": B, "archivar": False})
    ok(r.status_code == 200 and "archivado" not in _prod(B) and _prod(B).get("editables") == {"x": 1},
       "sin la marca y con todo lo suyo")
    ok(cli.post("/api/productos/activar", json={"id": B}).status_code == 200, "se vuelve a activar")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROJO — {len(FALLOS)} falla(s)")
        return 1
    print("✅ CONTRATO VERDE — un molde archivado no se usa, y se vuelve a habilitar tal cual")
    return 0


if __name__ == "__main__":
    sys.exit(main())
