# -*- coding: utf-8 -*-
"""CONTRATO: CADA CAMPO CON SU TIPOGRAFÍA, VARIAS COLUMNAS DE NOMBRE/NÚMERO POR MOLDE, Y LA CAPA «TALLE»
`py verificar_campos_por_molde.py`

Pedido del usuario (2026-09-16), tres cosas:
  1. *«si un molde viene con nombre y número con diferentes fuentes, que tenga que asignarle la
     fuente a cada una; que no sea obligatorio que los dos usen la misma»*;
  2. *«si usa talle de una columna o de otra, eso bien, pero en las demás columnas no corre esa
     regla: nombre y número pueden crear 10 columnas diferentes de número y usar las 10»*;
  3. *«en el diseño con base, si viene con una capa que se llame talle, que tome el texto y le
     ponga el talle de la columna correspondiente»*.

Lo que se prueba:
  1. `@campo:<campo>` en el mapa de reemplazos manda sobre el reemplazo POR FUENTE sólo para ese
     campo; sin elección por campo todo es como antes; la ficha y el estado de fuentes lo usan;
  2. `_traducir_prendas`: el número / nombre / talle de la columna ELEGIDA por el molde gana aunque
     haya otra columna rotulada «Número» (antes el rótulo pisaba la elección); las columnas extra
     (`mapeo_columnas["col:<id>"]`) cuentan como usadas para las obligatorias; la pantalla
     (Configuración › Planilla) deja prender varias de nombre/número y una sola de talle/manga;
  3. la capa «talle» recibe el talle de la columna del molde, tal cual (sin mayúsculas).

⚠️ No toca datos ni la base: planillas y moldes armados en memoria.
"""
import io
import os
import re
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.chdir(AQUI)
_TMP = tempfile.mkdtemp(prefix="verif_campos_")
os.environ["TIZADA_DATOS"] = _TMP
os.environ["TIZADA_ENTRADA"] = os.path.join(_TMP, "entrada")
os.environ["TIZADA_TRABAJOS"] = os.path.join(_TMP, "trabajos")
_falso_db = types.ModuleType("db")
_falso_db.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(
    AssertionError(f"LA PRUEBA INTENTO TOCAR MSSQL (db.{n})")))
sys.modules["db"] = _falso_db
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")

FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def main():
    import registro as L
    L.usar_carpeta(os.path.join(_TMP, "logs"))
    import motor_pedido as MP
    import servidor as S

    print("1 · 🔴 LA TIPOGRAFÍA DE CADA CAMPO")
    carpeta = {"carpetas": [], "alias": {"Anton-Regular": "Bebas Neue", "@campo:numero": "Bungee Regular"}}
    ok(MP.clave_fuente_campo("Número") == "@campo:numero" and MP.clave_fuente_campo("00") == "@campo:numero",
       "la clave de un campo se normaliza igual que el motor (acentos, alias «00» → número)")
    ok(MP.fuente_de_campo("Número", "Anton-Regular", carpeta) == ("Bungee Regular", True),
       "🔴 el número usa la elegida PARA ÉL…")
    ok(MP.fuente_de_campo("Nombre", "Anton-Regular", carpeta) == ("Anton-Regular", False),
       "…y el nombre, con la misma fuente de origen, sigue con la suya (y su reemplazo por fuente)")
    ok(MP.fuente_de_campo("Nombre", "Anton-Regular", "una/carpeta") == ("Anton-Regular", False),
       "con una carpeta sin reemplazos (texto) no cambia nada")
    motor = io.open("motor_pedido.py", encoding="utf-8").read()
    ok("_fnom_nombre, _por_campo = fuente_de_campo(campo, pl[\"fuente\"], carpeta_fuentes)" in motor
       and "fnom = fuente(_fnom_nombre, sin_alias=_por_campo)" in motor,
       "el estampado usa la tipografía del campo, y ésa NO pasa por el reemplazo por fuente")
    pers = {"2": {"Nombre": {"fuente": "Anton-Regular"}, "Número": {"fuente": "Anton-Regular"}}}
    fx = {"carpetas": [os.path.join(AQUI, "catalogo_fuentes")], "alias": {"@campo:numero": "Bungee Regular"}}
    fx0 = {"carpetas": fx["carpetas"], "alias": {}}
    cat_fx = {r: i.get("interno") for r, i in MP.catalogo_fuentes(fx0).items()}
    campos, falt = S._campos_de_fuentes(pers, fx, fx0, cat_fx)
    por = {c["campo"]: c for c in campos}
    ok(set(por) == {"Nombre", "Número"} and por["Número"]["elegida"] == "Bungee Regular"
       and por["Nombre"]["elegida"] is None and por["Nombre"]["original"] == "Anton Regular",
       f"el estado de fuentes devuelve cada campo con su original y su elegida ({[(c['campo'], c['elegida']) for c in campos]})")
    ok(falt == [], "sin faltantes cuando la fuente existe")
    pers_f = {"2": {"Nombre": {"fuente": "NoExiste-X"}, "Número": {"fuente": "NoExiste-X"}}}
    _c2, falt2 = S._campos_de_fuentes(pers_f, {**fx, "alias": {"@campo:numero": "Bungee Regular"}}, fx0, cat_fx)
    ok(falt2 == ["NoExiste-X"], "una fuente que no está sigue faltando si ALGÚN campo que la usa no tiene elegida")
    _c3, falt3 = S._campos_de_fuentes(pers_f, {**fx, "alias": {"@campo:numero": "Bungee Regular",
                                                                "@campo:nombre": "Anton Regular"}}, fx0, cat_fx)
    ok(falt3 == [], "…y deja de faltar cuando cada campo tiene la suya")
    g = S._fuentes_guia(pers, "M", fx)
    ok({(f["campo"], f["fuente"]) for f in g} == {("Nombre", "Anton Regular"), ("Número", "Bungee Regular")},
       f"la ficha técnica dice la tipografía de cada campo ({[(f['campo'], f['fuente']) for f in g]})")
    app = io.open(os.path.join("frontend", "src", "App.jsx"), encoding="utf-8").read()
    ok('data-tour="arte-fuente-campo"' in app and "_campoFuenteSel" in app
       and "const _objetivo = _cs ? _cs.clave" in app,
       "el modal de Fuentes se elige por CAMPO (y sin campos, por fuente como siempre)")
    ok("'arte-fuente-campo'" in io.open(os.path.join("frontend", "src", "diccionario.js"), encoding="utf-8").read(),
       "…y la ayuda lo explica")

    print("\n2 · 🔴 VARIAS COLUMNAS DE NOMBRE Y DE NÚMERO, Y LA ELEGIDA MANDA")
    tpl = {"id": "tpl_x", "columnas": [
        {"id": "talle", "label": "Talle", "role": "talle", "obligatoria": True},
        {"id": "talle_short", "label": "Talle short", "role": "talle"},
        {"id": "nombre", "label": "Nombre", "role": "nombre"},
        {"id": "numero", "label": "Número", "role": "numero"},
        {"id": "numero_short", "label": "Número short", "role": "numero", "obligatoria": True},
        {"id": "numero_2", "label": "Número 2", "role": "numero"},
    ]}
    cat = {"plantillas_planillas": [tpl], "reglas_planilla": [], "productos": []}
    short = {"id": "p_short", "planilla_template_id": "tpl_x",
             "mapeo_columnas": {"talle": "talle_short", "talle_elegido": True, "nombre": "nombre",
                                "numero": "numero_short", "col:numero_2": "numero_2"}}
    fila = {"talle": "L", "talle_short": "Mfem", "nombre": "perez", "numero": "10",
            "numero_short": "7", "numero_2": "99"}
    out = S._traducir_prendas([fila], short, cat)
    ok(len(out) == 1, "la fila se fabrica")
    pn = {MP._norm_nombre(k): v for k, v in out[0]["personalizacion"].items()}
    ok(pn.get("numero") == "7",
       f"🔴 la capa «Número» del short lleva SU columna («Número short» = 7), no la rotulada «Número» ({pn.get('numero')})")
    ok(pn.get("numero 2") == "99", "una columna extra («Número 2») va a la capa que se llama como ella")
    ok(pn.get("talle") == "Mfem" and out[0]["talle"] == "Mfem",
       f"la capa «talle» lleva el talle de la columna del molde, tal cual ({pn.get('talle')})")
    ok(pn.get("nombre") == "perez", "el nombre, de su columna")
    sin_extra = S._traducir_prendas([{**fila, "numero_short": ""}], short, cat)
    ok(sin_extra == [], "la columna obligatoria que el molde usa («Número short») se exige")
    camiseta = {"id": "p_cam", "planilla_template_id": "tpl_x",
                "mapeo_columnas": {"talle": "talle", "talle_elegido": True, "nombre": "nombre", "numero": "numero"}}
    out_c = S._traducir_prendas([{**fila, "numero_short": ""}], camiseta, cat)
    pc = {MP._norm_nombre(k): v for k, v in out_c[0]["personalizacion"].items()} if out_c else {}
    ok(out_c and pc.get("numero") == "10" and pc.get("talle") == "L",
       "la camiseta (que no usa «Número short») se fabrica igual, con SU número y SU talle")
    # la pantalla
    ok("const ROLES_UNA_COLUMNA = ['talle', 'manga'];" in app and "const ROLES_VARIAS_COLUMNAS = ['nombre', 'numero'];" in app,
       "Configuración › Planilla: talle y manga una por molde; nombre y número, varias")
    ok(app.count("columnaUsadaEnMolde(mapeoColumnas, c)") >= 2 and "alternarColumnaMolde(prev, c, cols)" in app,
       "la vista del molde y la prueba de planilla usan la misma regla")
    # la regla del front, ejecutada con Node
    import subprocess, json
    m = re.search(r"const ROLES_UNA_COLUMNA.*?\nfunction SelectorColumnaTalle", app, re.S)
    js = m.group(0).rsplit("function SelectorColumnaTalle", 1)[0] + r"""
const cols = [{id:'talle',role:'talle'},{id:'talle_short',role:'talle'},{id:'numero',role:'numero'},
              {id:'numero_short',role:'numero'},{id:'numero_2',role:'numero'}];
let m = {talle:'talle', numero:'numero'};
const pasos = [];
m = alternarColumnaMolde(m, cols[3], cols); pasos.push(['prende numero_short', ['numero','numero_short','numero_2'].filter(i => columnaUsadaEnMolde(m, cols.find(c=>c.id===i)))]);
m = alternarColumnaMolde(m, cols[4], cols); pasos.push(['prende numero_2', ['numero','numero_short','numero_2'].filter(i => columnaUsadaEnMolde(m, cols.find(c=>c.id===i)))]);
m = alternarColumnaMolde(m, cols[2], cols); pasos.push(['apaga la principal', m.numero, ['numero','numero_short','numero_2'].filter(i => columnaUsadaEnMolde(m, cols.find(c=>c.id===i)))]);
m = alternarColumnaMolde(m, cols[1], cols); pasos.push(['talle short', m.talle, columnaUsadaEnMolde(m, cols[0])]);
console.log(JSON.stringify(pasos));
"""
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    try:
        pasos = json.loads(r.stdout)
    except Exception:
        pasos = None
        print(r.stderr[:500])
    ok(pasos and pasos[0][1] == ["numero", "numero_short"], f"prender otra columna de número SUMA, no reemplaza ({pasos and pasos[0]})")
    ok(pasos and pasos[1][1] == ["numero", "numero_short", "numero_2"], "…y se pueden usar varias")
    ok(pasos and pasos[2][1] == "numero_short" and pasos[2][2] == ["numero_short", "numero_2"],
       "apagar la principal pasa la principal a la siguiente prendida (la capa «Número» nunca queda sin columna)")
    ok(pasos and pasos[3][1] == "talle_short" and pasos[3][2] is False, "el talle sigue siendo UNO: elegir otro apaga el anterior")

    print("\n3 · LA CAPA «TALLE»")
    ok("if _norm_nombre(campo) != \"talle\":" in motor, "el motor estampa el talle tal cual (no en mayúsculas: «Mfem» no es «MFEM»)")
    ok('<Capa nombre="talle"' in app, "la guía de capas de Configuración explica la capa «talle»")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        return 1
    print("✅ CONTRATO VERDE — cada campo con su tipografía, cada molde con sus columnas y la capa talle con su talle")
    return 0


if __name__ == "__main__":
    import shutil
    try:
        rc = main()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(rc)
