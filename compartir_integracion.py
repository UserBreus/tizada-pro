# -*- coding: utf-8 -*-
"""COMPARTIR LA INTEGRACIÓN (MAPA 690) — cada vez que se sube `main` de TIZADA PRO a GitHub, el repo
privado de la integración (`UserBreus/tizada-pro-integracion`, el que ven Santiago y useryoania) se
pone al día y se sube solo.

Pedido del usuario (2026-10-12): «que cuando subamos al git actualizaciones ya se le comparta; no
subir y por separado compartir». Antes era a mano (`actualizar_integracion.py` + commit + push en el
otro repo) y se olvidaba: ellos veían algo de hacía 4 días mientras `main` estaba al día.

Lo dispara el gancho `pre-push` de este repo (lo instala `--instalar`). Qué hace:
  1. Saca `documentacion/integracion_externa/` TAL COMO ESTÁ EN EL COMMIT QUE SE SUBE (no la copia de
     trabajo: lo que está a medio escribir en otra sesión no se comparte antes de estar en `main`).
  2. Corre el `actualizar_integracion.py` del repo de integración con esa copia.
  3. Revisa que lo que va a subir no lleve una llave de la API (`tzp_…`), un token de GitHub ni una
     clave privada. Si encuentra una, NO sube nada y lo dice.
  4. Commit + push del repo de integración (incluye lo que se cambió en el sistemita de prueba).
Si algo falla, avisa y sigue: compartir nunca frena la subida de TIZADA PRO.

    py compartir_integracion.py              → comparte lo que está en HEAD
    py compartir_integracion.py <sha>        → comparte lo que está en ese commit
    py compartir_integracion.py --preparar   → pone al día y revisa, sin commit ni push
    py compartir_integracion.py --instalar   → instala el gancho pre-push en este repo
"""
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import io

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
INTEG = os.environ.get("TIZADA_INTEGRACION_DIR") or os.path.join(os.path.dirname(AQUI), "TIZADAPRO PRUEBAEXT")
DOC = "documentacion/integracion_externa"

# Lo que NUNCA puede ir a un repo compartido. La llave real de la API es «tzp_» + 43 caracteres
# (`integracion_externa.crear_llave`); los ejemplos de la documentación son cortos o de mentira.
_SECRETOS = [
    (re.compile(r"tzp_[A-Za-z0-9_-]{30,}"), "una llave de la API de TIZADA (tzp_…)"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"), "un token de GitHub"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "una clave privada"),
]

GANCHO = """#!/bin/sh
# Instalado por `py compartir_integracion.py --instalar` (MAPA 690): al subir `main`, el repo de la
# integración se pone al día y se sube solo. Nunca frena esta subida (siempre sale con 0).
cero=0000000000000000000000000000000000000000
while read local_ref local_sha remote_ref remote_sha; do
  if [ "$remote_ref" = "refs/heads/main" ] && [ "$local_sha" != "$cero" ]; then
    py "$(git rev-parse --show-toplevel)/compartir_integracion.py" "$local_sha" \\
      || echo "AVISO: no se pudo compartir la integración (la subida de TIZADA PRO sigue igual)."
  fi
done
exit 0
"""


def _git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def instalar():
    ruta = os.path.join(_git(AQUI, "rev-parse", "--git-path", "hooks").strip(), "pre-push")
    ruta = ruta if os.path.isabs(ruta) else os.path.join(AQUI, ruta)
    if os.path.exists(ruta) and "compartir_integracion" not in open(ruta, encoding="utf-8", errors="replace").read():
        sys.exit(f"Ya hay otro gancho pre-push en {ruta}: no lo piso. Agregale a mano la llamada a este script.")
    with open(ruta + ".tmp", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(GANCHO)
    os.replace(ruta + ".tmp", ruta)
    print(f"Gancho instalado: {ruta}")


def _poner_al_dia(sha):
    """Copia la documentación del commit `sha` a una carpeta temporal y corre el actualizador del otro repo."""
    crudo = subprocess.run(["git", "archive", "--format=tar", sha, DOC], cwd=AQUI, capture_output=True)
    if crudo.returncode != 0:
        raise RuntimeError("git archive: " + crudo.stderr.decode("utf-8", "replace").strip())
    with tempfile.TemporaryDirectory(prefix="tizada_integ_") as tmp:
        with tarfile.open(fileobj=io.BytesIO(crudo.stdout)) as tar:
            tar.extractall(tmp, filter="data")
        env = dict(os.environ, TIZADA_PRO_DIR=tmp, PYTHONIOENCODING="utf-8")   # sin esto los acentos llegan rotos
        r = subprocess.run([sys.executable, os.path.join(INTEG, "actualizar_integracion.py")], cwd=INTEG, env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            raise RuntimeError("actualizar_integracion.py: " + (r.stderr or r.stdout).strip())
        print("  " + r.stdout.strip())


def _cambiados():
    """Archivos del repo de integración que cambiaron o son nuevos (respetando su .gitignore)."""
    salida = _git(INTEG, "status", "--porcelain", "--untracked-files=all")
    out = []
    for linea in salida.splitlines():
        ruta = linea[3:].strip().strip('"')
        if " -> " in ruta:
            ruta = ruta.split(" -> ", 1)[1]
        if linea[:2].strip() != "D":
            out.append(ruta)
    return out, bool(salida.strip())


def _revisar_secretos(archivos):
    hallados = []
    for rel in archivos:
        ruta = os.path.join(INTEG, rel)
        if not os.path.isfile(ruta) or rel.lower().endswith((".pdf", ".png", ".jpg", ".zip", ".ai")):
            continue
        try:
            txt = open(ruta, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for rx, que in _SECRETOS:
            # el ejemplo de la documentación es relleno («tzp_xxxx…»): una llave real tiene variedad
            if any(len(set(m.group(0)[4:])) > 8 for m in rx.finditer(txt)):
                hallados.append(f"{rel}: {que}")
    return hallados


def _rama_entrega(sha):
    """La rama `entrega-programadores` de `tizada-pro` es de donde el servidor de ellos toma TIZADA (la
    portada del repo de integración se lo indica). Se quedó en el 05/10 mientras `main` avanzaba: «ven los
    commits y no está el de hoy» (MAPA 690). Va siempre igual a `main`, sólo hacia adelante: si alguien le
    subió algo propio, no se pisa — se avisa."""
    r = subprocess.run(["git", "push", "-q", "origin", f"{sha}:refs/heads/entrega-programadores"], cwd=AQUI,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        print("  Rama entrega-programadores al día.")
    else:
        print("AVISO: no se pudo poner al día la rama entrega-programadores (¿tiene commits que main no?): "
              + (r.stderr or r.stdout).strip()[:300])


def compartir(sha="HEAD", preparar=False):
    if not preparar:
        _rama_entrega(sha)
    if not os.path.isdir(os.path.join(INTEG, ".git")):
        raise RuntimeError(f"No encuentro el repo de la integración en {INTEG} (TIZADA_INTEGRACION_DIR)")
    sha_c = _git(AQUI, "rev-parse", "--short", sha).strip()
    asunto = _git(AQUI, "log", "-1", "--format=%s", sha).strip()
    print(f"Compartiendo la integración con lo de TIZADA PRO {sha_c}…")
    _poner_al_dia(sha)
    archivos, hay = _cambiados()
    if not hay:
        print("  El repo de la integración ya estaba al día: nada para subir.")
        return
    malos = _revisar_secretos(archivos)
    if malos:
        raise RuntimeError("NO se subió: lo que iba a compartirse lleva datos privados →\n    " + "\n    ".join(malos))
    print(f"  {len(archivos)} archivo(s) cambiados, revisados: sin llaves ni tokens.")
    if preparar:
        print("  --preparar: queda listo para revisar, sin commit ni push.")
        return
    _git(INTEG, "add", "-A")
    _git(INTEG, "commit", "-q", "-m", f"Al día con TIZADA PRO {sha_c}: {asunto[:150]}")
    _git(INTEG, "push", "-q", "origin", "HEAD:main")
    print(f"  Subido a {_git(INTEG, 'remote', 'get-url', 'origin').strip()} ({_git(INTEG, 'rev-parse', '--short', 'HEAD').strip()}).")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--instalar" in args:
        instalar()
        sys.exit(0)
    try:
        compartir(next((a for a in args if not a.startswith("--")), "HEAD"), preparar="--preparar" in args)
    except Exception as e:
        print(f"AVISO: {e}")
        sys.exit(1)
