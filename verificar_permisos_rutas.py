# -*- coding: utf-8 -*-
"""CONTRATO: NINGUNA RUTA PIDE UN PERMISO QUE NO LE CORRESPONDE — `py verificar_permisos_rutas.py`

🔴 EL BUG QUE ESTE CONTRATO CIERRA (auditoría 2026-09-15). La guarda general, cuando un POST no
trae `pid`, resuelve el molde ACTIVO y exige `molde.editar`. Está bien para las ~30 rutas que
escriben un molde sin declararlo, y MAL para las 31 que no tocan ninguno: un Operario no podía
grabar un tutorial, tomar una reserva, guardar una plantilla de planilla, cambiar el ancho de una
tela **ni cancelar su propia tizada**. De yapa, varias de esas rutas quedaban «protegidas» por
accidente: el único candado era un permiso que no tiene nada que ver con lo que hacen — y cuando
se las exime, quedan abiertas si nadie les pone el suyo.

`servidor._API_SIN_MOLDE` declara, ruta por ruta, qué le corresponde:
  · un permiso del catálogo (`config.editar`, `ayuda.grabar`, …),
  · `"dueño"` — no hay permiso que pedir: el endpoint mira por su cuenta de quién es cada cosa,
  · `"libre"` — no hay nada que proteger porque no escribe nada.

Lo que se verifica leyendo `servidor.py` (sin levantar el server ni tocar la base):
  1. Toda ruta de ESCRITURA bajo `/api/` está clasificada: o trabaja sobre un molde, o está en la
     tabla. Una ruta nueva que no esté en ninguna de las dos hace fallar el contrato.
  2. Las que declaran un permiso no resuelven ningún molde (si lo hacen, están mal ahí), y no
     sobra en la tabla ninguna ruta que ya no exista.
  3. Las marcadas `"dueño"` miran de verdad al dueño; las `"libre"` de verdad no escriben.
  4. Los permisos declarados existen en `auth.PERMISOS`.
  5. La guarda compara contra `request.url_rule.rule` y sólo para métodos de escritura: contra el
     path, las rutas con parámetro (`/api/trabajo/<tid>/cancelar`) no entrarían nunca.
"""
import ast
import io
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SRV = os.path.join(AQUI, "servidor.py")

# señales de que el handler resuelve/usa un molde (ahí la guarda de molde SÍ corresponde)
SENAL_MOLDE = ("_get_active_producto_id", "_pid_de_request", "_ruta_datos", "_ruta_entrada",
               "_cargar_catalogo", "producto_id", "pid")
# señales de que controla al dueño por su cuenta
SENAL_DUENO = ("_usuario_actual", "_config_es_mia", "creado_por", "token_ok", "_es_admin")
# señales de que escribe algo (una ruta "libre" no puede tener ninguna)
SENAL_ESCRIBE = ("os.remove", "shutil.", "_guardar", "os.replace", "json.dump")

FALLAS = []


def usa(cod, señales):
    """¿El código del handler menciona alguna de esas señales, como palabra entera?"""
    return any(re.search(r"\b" + re.escape(s) + r"\b", cod) for s in señales)


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLAS.append(msg)


def rutas_de_escritura(src, arbol):
    """{regla: (nombre_funcion, codigo)} de cada ruta POST/PUT/PATCH/DELETE bajo /api/."""
    out = {}
    for n in ast.walk(arbol):
        if not isinstance(n, ast.FunctionDef):
            continue
        reglas = []
        for d in n.decorator_list:
            f = d.func if isinstance(d, ast.Call) else d
            nom = getattr(f, "attr", None)
            if not isinstance(d, ast.Call) or not d.args:
                continue
            try:
                ruta = ast.literal_eval(d.args[0])
            except Exception:
                continue
            if nom in ("post", "put", "patch", "delete"):
                reglas.append(ruta)
            elif nom == "route":
                for kw in d.keywords:
                    if kw.arg != "methods":
                        continue
                    try:
                        ms = ast.literal_eval(kw.value)
                    except Exception:
                        ms = []
                    if any(str(m).upper() in ("POST", "PUT", "PATCH", "DELETE") for m in ms):
                        reglas.append(ruta)
        cod = ast.get_source_segment(src, n) or ""
        for r in reglas:
            if r.startswith("/api/"):
                out[r] = (n.name, cod)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print("CONTRATO — CADA RUTA PIDE EL PERMISO QUE LE CORRESPONDE\n")
    src = io.open(SRV, encoding="utf-8").read()
    rutas = rutas_de_escritura(src, ast.parse(src))

    m = re.search(r"^_API_SIN_MOLDE = \{.*?^\}", src, re.S | re.M)
    if not m:
        print("    ❌     no encontré `_API_SIN_MOLDE` en servidor.py")
        return 1
    tabla = ast.literal_eval(m.group(0).split("=", 1)[1].strip())
    sin_sesion = ast.literal_eval(re.search(r"^_API_SIN_SESION = (\(.*?\))", src, re.M).group(1))

    print(f"1 · CLASIFICACIÓN — {len(rutas)} rutas de escritura bajo /api/")
    sueltas = sorted(f"{r} ({fn})" for r, (fn, cod) in rutas.items()
                     if r not in tabla and not usa(cod, SENAL_MOLDE)
                     and not any(r.startswith(p) for p in sin_sesion))
    ok(not sueltas, "toda ruta de escritura trabaja un molde o está declarada en `_API_SIN_MOLDE`"
                    + ("" if not sueltas else f" — sin clasificar: {sueltas}"))

    print("\n2 · LA TABLA DICE LA VERDAD")
    # Las marcadas "dueño" SÍ pueden tocar moldes (los EFÍMEROS del pedido, que son de quien los
    # subió): lo que no puede pasar es que se les exija `molde.editar` del molde del catálogo.
    mal = sorted(r for r, perm in tabla.items()
                 if perm != "dueño" and r in rutas and usa(rutas[r][1], SENAL_MOLDE))
    ok(not mal, f"ninguna con permiso declarado resuelve un molde{'' if not mal else f' — {mal}'}")
    fantasma = sorted(r for r in tabla if r not in rutas)
    ok(not fantasma, f"ninguna sobra (ruta que ya no existe){'' if not fantasma else f' — {fantasma}'}")

    print("\n3 · NINGUNA QUEDA SIN CONTROL")
    sin_dueño = sorted(r for r, perm in tabla.items()
                       if perm == "dueño" and r in rutas and not usa(rutas[r][1], SENAL_DUENO))
    ok(not sin_dueño, f"las marcadas «dueño» miran de verdad al dueño{'' if not sin_dueño else f' — {sin_dueño}'}")
    falsas = sorted(r for r, perm in tabla.items()
                    if perm == "libre" and r in rutas and usa(rutas[r][1], SENAL_ESCRIBE))
    ok(not falsas, f"las marcadas «libre» no escriben nada{'' if not falsas else f' — {falsas}'}")

    print("\n4 · LOS PERMISOS EXISTEN")
    import auth
    validos = {p[0] for p in auth.PERMISOS} | {"dueño", "libre"}
    inventados = sorted({p for p in tabla.values() if p and p not in validos})
    ok(not inventados, f"todo lo declarado está en el catálogo de permisos{'' if not inventados else f' — {inventados}'}")

    print("\n5 · LA GUARDA MIRA LA REGLA, NO EL PATH")
    ok("_API_SIN_MOLDE[" in src and "url_rule" in src,
       "la guarda resuelve por `request.url_rule.rule` (con el path, las rutas con <parámetro> no entran)")
    ok(re.search(r'if request\.method in \("POST", "PUT", "PATCH", "DELETE"\):\s*\n\s*_regla', src) is not None,
       "…y sólo para métodos de escritura (el GET de la misma ruta no pide permiso)")

    print()
    print("✅ CONTRATO VERDE — ninguna ruta pide un permiso ajeno, y ninguna quedó sin control"
          if not FALLAS else f"❌ CONTRATO ROTO — {len(FALLAS)} falla(s)")
    return 1 if FALLAS else 0


if __name__ == "__main__":
    sys.exit(main())
