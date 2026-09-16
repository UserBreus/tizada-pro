# -*- coding: utf-8 -*-
"""Arma `escritorio/salida/Instalar TIZADA PRO <versión>.exe` a partir de la carpeta que dejó
PyInstaller (`escritorio/dist/TIZADA PRO`). Lo llama `CONSTRUIR-APLICACION.bat`.

  1. comprime el programa en `app.zip`;
  2. compila el desinstalador y el instalador con el `csc.exe` de .NET Framework que trae Windows
     (nada de herramientas de terceros), metiendo el zip, el desinstalador, la versión y el logo
     como recursos del instalador;
  3. prueba el instalador en una carpeta temporal (`/prueba:`) y verifica que el programa quedó
     entero: si falta un archivo, el instalador NO se entrega.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DIST = os.path.join(AQUI, "dist", "TIZADA PRO")
TRABAJO = os.path.join(AQUI, "build_instalador")
SALIDA = os.path.join(AQUI, "salida")
CSC = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Microsoft.NET", "Framework64", "v4.0.30319", "csc.exe")


def paso(t):
    print(f"\n== {t}", flush=True)


def compilar(fuente, salida, recursos=()):
    cmd = [CSC, "-nologo", "-target:winexe", "-optimize", "-codepage:65001", f"-out:{salida}",
           "-win32icon:" + os.path.join(AQUI, "recursos", "tizada.ico"),
           "-r:System.Windows.Forms.dll", "-r:System.Drawing.dll", "-r:System.IO.Compression.dll"]
    cmd += [f"-resource:{ruta},{nombre}" for ruta, nombre in recursos]
    cmd.append(fuente)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit(f"no compiló {os.path.basename(fuente)}")


def main():
    if not os.path.exists(os.path.join(DIST, "TIZADA PRO.exe")):
        raise SystemExit("falta la carpeta de PyInstaller (escritorio/dist/TIZADA PRO): corré el paso anterior")
    if not os.path.exists(CSC):
        raise SystemExit(f"no encuentro el compilador de .NET Framework: {CSC}")
    version = open(os.path.join(RAIZ, "VERSION"), encoding="utf-8").read().strip()
    shutil.rmtree(TRABAJO, ignore_errors=True)
    os.makedirs(TRABAJO)
    os.makedirs(SALIDA, exist_ok=True)

    paso("Comprimiendo el programa")
    zip_ruta = os.path.join(TRABAJO, "app.zip")
    archivos = []
    for raiz, _dirs, arch in os.walk(DIST):
        for a in arch:
            archivos.append(os.path.join(raiz, a))
    with zipfile.ZipFile(zip_ruta, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in archivos:
            z.write(f, os.path.relpath(f, DIST).replace(os.sep, "/"))
    print(f"   {len(archivos)} archivos · {os.path.getsize(zip_ruta) / 1e6:.0f} MB")

    paso("Compilando el desinstalador y el instalador")
    with open(os.path.join(TRABAJO, "version.txt"), "w", encoding="utf-8") as fh:
        fh.write(version)
    desins = os.path.join(TRABAJO, "desinstalar.exe")
    compilar(os.path.join(AQUI, "instalador", "Desinstalador.cs"), desins)
    instalador = os.path.join(TRABAJO, f"Instalar TIZADA PRO {version}.exe")
    compilar(os.path.join(AQUI, "instalador", "Instalador.cs"), instalador, [
        (zip_ruta, "app.zip"), (desins, "desinstalar.exe"),
        (os.path.join(TRABAJO, "version.txt"), "version.txt"),
        (os.path.join(AQUI, "recursos", "tizada.png"), "logo.png")])

    paso("Probando el instalador en una carpeta temporal")
    prueba = tempfile.mkdtemp(prefix="tizada_instalador_prueba_")
    try:
        destino = os.path.join(prueba, "TIZADA PRO")
        r = subprocess.run([instalador, f"/prueba:{destino}"], timeout=900)
        if r.returncode != 0:
            raise SystemExit(f"el instalador de prueba terminó con error ({r.returncode})")
        faltan = [f for f in archivos
                  if not os.path.exists(os.path.join(destino, os.path.relpath(f, DIST)))]
        distintos = [f for f in archivos if os.path.exists(os.path.join(destino, os.path.relpath(f, DIST)))
                     and os.path.getsize(f) != os.path.getsize(os.path.join(destino, os.path.relpath(f, DIST)))]
        if faltan or distintos or not os.path.exists(os.path.join(destino, "Desinstalar TIZADA PRO.exe")):
            raise SystemExit(f"la instalación de prueba quedó incompleta: faltan {len(faltan)}, "
                             f"distintos {len(distintos)}")
        print(f"   OK: los {len(archivos)} archivos quedaron iguales, más el desinstalador")
    finally:
        shutil.rmtree(prueba, ignore_errors=True)

    final = os.path.join(SALIDA, os.path.basename(instalador))
    shutil.copy2(instalador, final)
    paso(f"LISTO: {final} ({os.path.getsize(final) / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
