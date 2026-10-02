# -*- coding: utf-8 -*-
"""CONTRATO: UNA TIPOGRAFÍA SE GUARDA CON SU NOMBRE Y NO PISA OTRA SIN PREGUNTAR — `py verificar_fuente_ya_existe.py`

Pedido del usuario (2026-10-01):
  · «si yo subo una fuente es esa fuente»: se guarda con el nombre del archivo, sin `subida_`;
  · «si se llama igual a otra, que diga esa fuente ya existe: ¿reemplazarla o dejar la misma?»;
  · «obvio que también se pueden subir familias»: Regular, Bold, Black… de una familia conviven.

Se prueba contra `POST /api/fuente` con una carpeta de catálogo DESCARTABLE (copias de tipografías
del catálogo real): nunca se toca `catalogo_fuentes/`. También la migración de los `subida_*`.
"""
import os
import shutil
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8")
_AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AQUI)
os.chdir(_AQUI)
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")   # sin usuarios: import limpio
import registro as _LOG_PRUEBA   # noqa: E402
_LOG_PRUEBA.usar_carpeta(tempfile.mkdtemp(prefix="verif_logs_"))
import servidor as S          # noqa: E402
import motor_pedido as MP     # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


REAL = os.path.join(_AQUI, "catalogo_fuentes")


def real(nombre_parcial):
    """Una tipografía del catálogo real (sólo se LEE y se copia)."""
    for a in sorted(os.listdir(REAL)):
        if nombre_parcial.lower() in a.lower() and a.lower().endswith((".ttf", ".otf")):
            return os.path.join(REAL, a)
    raise SystemExit(f"no encontré «{nombre_parcial}» en catalogo_fuentes para la prueba")


TMP = tempfile.mkdtemp(prefix="verif_fuente_existe_")
S.FUENTES = TMP
S.app.config["TESTING"] = True
cli = S.app.test_client()


def subir(origen, nombre, reemplaza=None):
    datos = open(origen, "rb").read()
    import fitz
    nom = MP.nombres_fuente(datos)
    form = {"archivo": (__import__("io").BytesIO(datos), nombre), "interno": fitz.Font(fontbuffer=datos).name,
            "completo": nom["completo"], "ps": nom["ps"], "sin_contorno": "[]", "choca_con": "null"}
    if reemplaza:
        form["reemplaza"] = reemplaza
    r = cli.post("/api/fuente", data=form, content_type="multipart/form-data")
    return r.status_code, r.get_json(silent=True) or {}


try:
    m54 = real("Superstar M54")
    arial_bold = real("Arial-Bold")
    arial_black = real("ariblk")
    anton = real("Anton-Regular")

    print("1. se guarda con su nombre real")
    st, d = subir(m54, "Superstar M54.ttf")
    ok(st == 200 and os.path.exists(os.path.join(TMP, "Superstar M54.ttf")), f"queda «Superstar M54.ttf» (status {st})")
    ok(not any(a.startswith("subida_") for a in os.listdir(TMP)), "ningún archivo lleva «subida_»")

    print("2. el mismo nombre de archivo: pregunta (409) y no pisa")
    antes = open(os.path.join(TMP, "Superstar M54.ttf"), "rb").read()
    st, d = subir(anton, "Superstar M54.ttf")
    ok(st == 409 and (d.get("existe") or {}).get("archivo") == "Superstar M54.ttf", f"contesta «ya existe» (status {st})")
    ok(open(os.path.join(TMP, "Superstar M54.ttf"), "rb").read() == antes, "la que estaba sigue intacta")
    st, d = subir(anton, "SUPERSTAR m54.TTF")
    ok(st == 409, f"mismo nombre con otras mayúsculas también pregunta (status {st})")

    print("3. la misma fuente con otro nombre de archivo: también pregunta")
    st, d = subir(m54, "copia de la m54.ttf")
    ok(st == 409 and (d.get("existe") or {}).get("archivo") == "Superstar M54.ttf", f"la reconoce por adentro (status {st})")
    ok(not os.path.exists(os.path.join(TMP, "copia de la m54.ttf")), "no quedó guardada sin permiso")

    print("4. «Reemplazarla»")
    st, d = subir(m54, "copia de la m54.ttf", reemplaza="Superstar M54.ttf")
    ok(st == 200, f"entra con reemplaza (status {st})")
    ok(os.path.exists(os.path.join(TMP, "copia de la m54.ttf")) and not os.path.exists(os.path.join(TMP, "Superstar M54.ttf")),
       "queda la nueva y se saca la vieja (no la misma fuente dos veces)")
    st, d = subir(anton, "copia de la m54.ttf", reemplaza="copia de la m54.ttf")
    ok(st == 200 and open(os.path.join(TMP, "copia de la m54.ttf"), "rb").read() == open(anton, "rb").read(),
       "mismo nombre + reemplaza: queda el archivo nuevo")

    print("5. familias: estilos distintos conviven")
    st1, _ = subir(arial_bold, "Arial-Bold.ttf")
    st2, d2 = subir(arial_black, "ariblk.ttf")
    ok(st1 == 200 and st2 == 200, f"Arial Bold y Arial Black entran las dos ({st1}, {st2})")

    print("6. el resolvedor distingue por PostScript")
    _cat = {"carpetas": [TMP], "alias": {}}
    ok(os.path.basename(MP.resolver_fuente("Arial-Black", _cat) or "") == "ariblk.ttf", "«Arial-Black» → ariblk.ttf")
    ok(os.path.basename(MP.resolver_fuente("Arial-BoldMT", _cat) or "") == "Arial-Bold.ttf", "«Arial-BoldMT» → Arial-Bold.ttf")

    print("7. las cargadas antes como subida_* pasan a su nombre (sin perder nada)")
    MIG = tempfile.mkdtemp(prefix="verif_fuente_mig_")
    S.FUENTES = MIG
    shutil.copy(m54, os.path.join(MIG, "subida_Superstar M54.ttf"))          # sólo con prefijo → se renombra
    shutil.copy(anton, os.path.join(MIG, "Anton-Regular.ttf"))
    shutil.copy(anton, os.path.join(MIG, "subida_Anton-Regular.ttf"))         # copia idéntica → se saca
    shutil.copy(arial_bold, os.path.join(MIG, "Impacto.ttf"))
    shutil.copy(arial_black, os.path.join(MIG, "subida_Impacto.ttf"))        # distinta con el mismo nombre → no se toca
    S._quitar_prefijo_fuentes()
    quedan = sorted(os.listdir(MIG))
    ok("Superstar M54.ttf" in quedan and "subida_Superstar M54.ttf" not in quedan, "subida_Superstar M54.ttf → Superstar M54.ttf")
    ok("subida_Anton-Regular.ttf" not in quedan and "Anton-Regular.ttf" in quedan, "la copia idéntica se saca, la buena queda")
    ok("subida_Impacto.ttf" in quedan and "Impacto.ttf" in quedan, "si hay otra DISTINTA con ese nombre no se toca ninguna")
    shutil.rmtree(MIG, ignore_errors=True)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print()
print("FALLAS:" if FALLOS else "TODO OK", *FALLOS, sep="\n  · ")
sys.exit(1 if FALLOS else 0)
