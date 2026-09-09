# -*- coding: utf-8 -*-
"""GENERADOR DE `API_RUTAS.md` — `py generar_api_rutas.py [--escribir]`

El documento decía «Generado automáticamente del código» pero **el generador no estaba en el
repo**: quedó atrasado en las dos ramas (al unirlas, en septiembre de 2026, le faltaban 25 rutas y
le sobraba una que ya no existe). Esto lo rehace.

QUÉ HACE Y QUÉ NO:
  · Lee las rutas de `servidor.py` y `api_usuarios.py` con `ast` (no con expresiones regulares:
    un decorador partido en dos líneas se escapaba).
  · **CONSERVA las secciones y las filas que ya están.** El agrupado («Sistema», «Arte», «Telas»…)
    lo escribió una persona y no se puede deducir del código: pisarlo sería perder trabajo. Cada
    ruta nueva entra en la sección de la ruta que MÁS se le parece (prefijo más largo en común).
  · Saca las filas de rutas que ya no existen en el código, y las nombra al final.
  · Recalcula el total.

Sin `--escribir` no toca nada: dice qué cambiaría. Es lo que conviene mirar primero.
"""
import ast
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(AQUI, "API_RUTAS.md")
FUENTES = ["servidor.py", "api_usuarios.py"]
METODOS = ("get", "post", "put", "patch", "delete")


# ── 1. LAS RUTAS QUE HAY EN EL CÓDIGO ────────────────────────────────────────────────────────
def _params_de(fn):
    """Los parámetros que la función LEE, con la misma nomenclatura del documento:
    `body{}` (JSON), `q=` (query string), `form=` (multipart) y `file=` (archivo subido)."""
    body, q, form, files = set(), set(), set(), set()
    # de qué variables sale el JSON del cuerpo (`cuerpo = request.get_json(...)`)
    vars_json = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
            f = n.value.func
            if isinstance(f, ast.Attribute) and f.attr in ("get_json",):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        vars_json.add(t.id)
            # `cuerpo = request.get_json(...) or {}`
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.BoolOp):
            for v in n.value.values:
                if (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute)
                        and v.func.attr == "get_json"):
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            vars_json.add(t.id)

    def _clave(nodo):
        """La cadena literal de un `.get("x")` o `["x"]`."""
        if isinstance(nodo, ast.Call) and nodo.args and isinstance(nodo.args[0], ast.Constant) \
                and isinstance(nodo.args[0].value, str):
            return nodo.args[0].value
        return None

    for n in ast.walk(fn):
        # request.args / request.form / request.files → .get("x")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get":
            duenio = n.func.value
            if isinstance(duenio, ast.Attribute) and isinstance(duenio.value, ast.Name) \
                    and duenio.value.id == "request":
                k = _clave(n)
                if k:
                    {"args": q, "form": form, "files": files}.get(duenio.attr, set()).add(k)
            elif isinstance(duenio, ast.Name) and duenio.id in vars_json:
                k = _clave(n)
                if k:
                    body.add(k)
        # request.args["x"] / request.files["x"]
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Attribute) \
                and isinstance(n.value.value, ast.Name) and n.value.value.id == "request" \
                and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
            {"args": q, "form": form, "files": files}.get(n.value.attr, set()).add(n.slice.value)
    partes = []
    for etiqueta, conj in (("body", body), ("q", q), ("form", form), ("file", files)):
        if conj:
            partes.append(f"{etiqueta}: " + ", ".join(sorted(conj)))
    return " · ".join(partes) if partes else "—"


def _descripcion(fn):
    """La primera parte del docstring, en una línea y recortada como en el documento."""
    doc = ast.get_docstring(fn) or ""
    doc = " ".join(doc.split())
    return doc[:150]


def rutas_del_codigo():
    """[(metodo, ruta, descripcion, params)] de todo el backend, sin repetidos."""
    out = {}
    for archivo in FUENTES:
        arbol = ast.parse(io.open(os.path.join(AQUI, archivo), encoding="utf-8").read())
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in nodo.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)):
                    continue
                duenio = dec.func.value
                if not (isinstance(duenio, ast.Name) and duenio.id in ("app", "bp")):
                    continue
                if not dec.args or not isinstance(dec.args[0], ast.Constant):
                    continue
                ruta = dec.args[0].value
                if dec.func.attr in METODOS:
                    metodos = [dec.func.attr.upper()]
                elif dec.func.attr == "route":
                    metodos = ["GET"]
                    for kw in dec.keywords:
                        if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                            metodos = [e.value.upper() for e in kw.value.elts
                                       if isinstance(e, ast.Constant)]
                else:
                    continue
                for m in metodos:
                    out[(m, ruta)] = (_descripcion(nodo), _params_de(nodo))
    return out


# ── 2. EL DOCUMENTO QUE YA ESTÁ ──────────────────────────────────────────────────────────────
FILA = re.compile(r"^\| *(GET|POST|PUT|PATCH|DELETE) *\| *`([^`]+)` *\|(.*)\|(.*)\|\s*$")


def leer_doc():
    """(lineas, {(metodo, ruta): indice_de_linea}, {(metodo, ruta): seccion})."""
    lineas = io.open(DOC, encoding="utf-8").read().split("\n")
    donde, seccion_de, seccion = {}, {}, None
    for i, l in enumerate(lineas):
        if l.startswith("## "):
            seccion = l[3:].strip()
        m = FILA.match(l)
        if m:
            clave = (m.group(1), m.group(2))
            donde[clave] = i
            seccion_de[clave] = seccion
    return lineas, donde, seccion_de


# Familias que el parecido por prefijo NO acierta: son temas propios y merecen su sección. Sin
# esto, `/api/auth/login` caía en «Actualización» y `/api/permisos` en «Perfiles de color» (los dos
# empiezan con «/api/p…»), que es peor que no clasificarlas.
SECCIONES_FIJAS = [
    ("/api/auth/", "Usuarios / Roles / Permisos"),
    ("/api/usuarios", "Usuarios / Roles / Permisos"),
    ("/api/roles", "Usuarios / Roles / Permisos"),
    ("/api/permisos", "Usuarios / Roles / Permisos"),
    ("/api/registro", "Registro del sistema"),
    ("/api/consola", "Registro del sistema"),
    ("/api/tutoriales", "Ayuda guiada (tutoriales grabados)"),
    ("/api/molde/config", "Productos / Moldería"),
    ("/api/pedido/fuente", "Fuentes / Catálogo"),
]


def _seccion_para(ruta, seccion_de):
    """Dónde va una ruta nueva: primero las reglas fijas de arriba; si no, la sección de la ruta
    EXISTENTE que más se le parece (prefijo más largo en común)."""
    for pref, sec in SECCIONES_FIJAS:
        if ruta.startswith(pref):
            return sec
    mejor, largo = None, -1
    for (_m, r), sec in seccion_de.items():
        n = len(os.path.commonprefix([ruta, r]))
        if n > largo:
            mejor, largo = sec, n
    return mejor


def main():
    escribir = "--escribir" in sys.argv
    codigo = rutas_del_codigo()
    lineas, donde, seccion_de = leer_doc()
    faltan = sorted(set(codigo) - set(donde), key=lambda k: (k[1], k[0]))
    sobran = sorted(set(donde) - set(codigo), key=lambda k: (k[1], k[0]))

    print(f"rutas en el código: {len(codigo)} · filas en el documento: {len(donde)}")
    print(f"faltan {len(faltan)} · sobran {len(sobran)}")

    # las que sobran: se sacan sus líneas
    a_borrar = {donde[k] for k in sobran}
    for k in sobran:
        print(f"  - se saca (ya no existe en el código): {k[0]} {k[1]}")

    # las que faltan: se agregan al final de su sección
    nuevas_por_seccion = {}
    for k in faltan:
        sec = _seccion_para(k[1], seccion_de)
        desc, par = codigo[k]
        nuevas_por_seccion.setdefault(sec, []).append(f"| {k[0]} | `{k[1]}` | {desc} | {par} |")
        print(f"  + se agrega a «{sec}»: {k[0]} {k[1]}")

    salida, i = [], 0
    while i < len(lineas):
        l = lineas[i]
        # ¿es la última fila de una sección que tiene altas? entonces van detrás
        es_fila = bool(FILA.match(l))
        sig_no_fila = i + 1 >= len(lineas) or not FILA.match(lineas[i + 1])
        if i not in a_borrar:
            salida.append(l)
        if es_fila and sig_no_fila:
            sec = None
            for (m, r), idx in donde.items():
                if idx == i:
                    sec = seccion_de[(m, r)]
            for fila in nuevas_por_seccion.pop(sec, []):
                salida.append(fila)
        i += 1
    # cualquier sección que no se haya podido ubicar va al final, visible
    for sec, filas in nuevas_por_seccion.items():
        salida.append("")
        salida.append(f"## {sec}" if sec else "## Sin clasificar (movelas a su sección)")
        salida.append("")
        salida.append("| Método | Ruta | Descripción | Params |")
        salida.append("|---|---|---|---|")
        salida += filas

    total = sum(1 for l in salida if FILA.match(l))
    salida = [re.sub(r"Total: \*\*\d+ endpoints\*\*", f"Total: **{total} endpoints**", l)
              for l in salida]
    texto = "\n".join(salida)

    if not escribir:
        print(f"\n(prueba: no se escribió nada). El documento quedaría con {total} endpoints.")
        print("Para aplicarlo: py generar_api_rutas.py --escribir")
        return 0
    # atómico: .tmp + os.replace (un `open(w)` trunca antes de fallar)
    with io.open(DOC + ".tmp", "w", encoding="utf-8", newline="") as f:
        f.write(texto)
    os.replace(DOC + ".tmp", DOC)
    print(f"\nAPI_RUTAS.md actualizado: {total} endpoints.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
