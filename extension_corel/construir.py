"""Arma el INSTALADOR de USER PRO para CorelDRAW: `Instalar-USER-PRO-Corel-<versión>.exe`.

Correr:  py extension_corel/construir.py

UN solo programa (ver `instalador/Instalador.cs`): la ventana de instalar, el PUENTE en segundo plano
(`puente/Puente.cs`, 127.0.0.1:47851) y el armado en Corel por COM (`puente/ArmarCorel.cs`).
Se compila con el compilador de C# que trae Windows (.NET Framework 4), sin bajar nada.

🔴 LA VERSIÓN SUBE SOLA, igual que la de Illustrator (regla del usuario 2026-09-23: «cada cambio que
haya que descargar, con su versión»): una HUELLA de todo lo que va adentro (el código del programa y
`frontend/src/motor/molde/corel.js`, que decide QUÉ se arma); si cambió desde la última vez
(`historial_versiones.json`), sube (1.0.0 → 1.1.0). El .exe lleva la versión en el nombre y se
borran los de versiones anteriores.

Las imágenes de la marca salen del mismo lugar que las del instalador de Illustrator
(`extension_illustrator/construir.py`: isotipo e isologo desde `frontend/public/logo.svg`).
"""
import datetime
import glob
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PUENTE = os.path.join(AQUI, "puente")
INST = os.path.join(AQUI, "instalador")
COMPLEMENTO = os.path.join(AQUI, "complemento")          # la barra «TIZADA PRO» dentro de Corel
OBRA = os.path.join(AQUI, "build")                       # intermedios (no van a git)
HISTORIAL = os.path.join(AQUI, "historial_versiones.json")
CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
NET = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319"
PLAN_WEB = os.path.join(RAIZ, "frontend", "src", "motor", "molde", "corel.js")


def salida(v):
    return os.path.join(AQUI, f"Instalar-USER-PRO-Corel-{v}.exe")


def _illu():
    """Las funciones de imágenes del armado de Illustrator (una sola forma de dibujar la marca)."""
    ruta = os.path.join(RAIZ, "extension_illustrator", "construir.py")
    spec = importlib.util.spec_from_file_location("construir_illustrator", ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def imagenes():
    os.makedirs(OBRA, exist_ok=True)
    il = _illu()
    iso = il.isotipo(1024)
    il.isologo(220, True).save(os.path.join(OBRA, "isologo_oscuro.png"))
    verde = il.tenir(iso, il.TONOS_COREL)
    # el ícono del .exe y del conector junto al reloj: en VERDE (el de Illustrator va en naranja)
    il.cuadrado(verde, 256, 0.02).save(os.path.join(OBRA, "icono.ico"),
                                     sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    # el ícono del botón de la barra de Corel (se ve a 18 px; más grande para pantallas con zoom)
    il.cuadrado(verde, 64, 0.0).save(os.path.join(OBRA, "isotipo_verde.png"))


def compilar_boton():
    """`TizadaPro.dll`: el botón de la barra de Corel (control WPF, ver `complemento/BotonTizada.cs`).
    Lleva adentro el isotipo en verde. Se arma en `build/` y va como recurso del instalador."""
    wpf = os.path.join(NET, "WPF")
    dll = os.path.join(OBRA, "TizadaPro.dll")
    cmd = [CSC, "/nologo", "/target:library", "/optimize+", "/codepage:65001", "/platform:anycpu",
           "/out:" + dll,
           "/resource:" + os.path.join(OBRA, "isotipo_verde.png") + ",isotipo.png",
           "/r:System.dll", "/r:System.Core.dll", "/r:System.Xaml.dll",
           "/r:" + os.path.join(wpf, "PresentationCore.dll"),
           "/r:" + os.path.join(wpf, "PresentationFramework.dll"),
           "/r:" + os.path.join(wpf, "WindowsBase.dll"),
           os.path.join(COMPLEMENTO, "BotonTizada.cs")]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        sys.exit("No compiló el botón de Corel (TizadaPro.dll).")
    return dll


def fuentes():
    return sorted(glob.glob(os.path.join(PUENTE, "*.cs")) + glob.glob(os.path.join(INST, "*.cs")))


def huella():
    h = hashlib.sha1()
    rutas = fuentes() + [os.path.join(INST, "app.manifest"), PLAN_WEB] + sorted(glob.glob(os.path.join(COMPLEMENTO, "*")))
    # el color del ícono (instalador, conector y botón) también es «algo que se descarga»
    h.update(repr(_illu().TONOS_COREL).encode())
    for r in sorted(rutas):
        h.update(os.path.relpath(r, RAIZ).replace(os.sep, "/").encode())
        h.update(open(r, "rb").read())
    return h.hexdigest()


def versionar():
    """La versión de este armado: la misma si nada cambió, la siguiente si cambió algo."""
    try:
        hist = json.load(open(HISTORIAL, encoding="utf-8"))
    except (OSError, ValueError):
        hist = []
    hu = huella()
    if hist and hist[-1].get("huella") == hu:
        return hist[-1]["version"]
    if hist:
        a, b, _c = (int(n) for n in hist[-1]["version"].split("."))
        v = f"{a}.{b + 1}.0"
    else:
        v = "1.0.0"
    hist.append({"version": v, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "huella": hu})
    with open(HISTORIAL + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(hist, fh, ensure_ascii=False, indent=1)
    os.replace(HISTORIAL + ".tmp", HISTORIAL)
    return v


def compilar(v):
    if not os.path.exists(CSC):
        sys.exit("No encontré el compilador de C# de Windows (" + CSC + ").")
    # la versión entra al programa por un archivo generado (el .cs no se toca a mano en cada versión)
    with open(os.path.join(OBRA, "Version.cs"), "w", encoding="utf-8") as fh:
        fh.write('namespace UserPro { static class Version { public const string Texto = "%s"; } }\n' % v)
    SALIDA = salida(v)
    tmp = SALIDA + ".tmp.exe"
    cmd = [CSC, "/nologo", "/target:winexe", "/optimize+", "/codepage:65001", "/platform:anycpu",
           "/out:" + tmp,
           "/win32icon:" + os.path.join(OBRA, "icono.ico"),
           "/win32manifest:" + os.path.join(INST, "app.manifest"),
           "/resource:" + os.path.join(OBRA, "isologo_oscuro.png") + ",isologo.png",
           "/resource:" + os.path.join(OBRA, "icono.ico") + ",icono.ico",
           ] + ["/resource:" + os.path.join(COMPLEMENTO, a) + ",complemento." + a for a in ("AppUI.xslt", "UserUI.xslt", "CorelDrw.addon")] + [
           "/resource:" + compilar_boton() + ",complemento.TizadaPro.dll",
           "/r:System.dll", "/r:System.Core.dll", "/r:System.Drawing.dll", "/r:System.Windows.Forms.dll",
           # `dynamic` (COM de Corel sin la biblioteca de tipos: sirve igual de la 2022 a la 2026)
           "/r:Microsoft.CSharp.dll",
           # JavaScriptSerializer (el JSON del plan) sin bajar nada
           "/r:" + os.path.join(NET, "System.Web.Extensions.dll"),
           ] + fuentes() + [os.path.join(OBRA, "Version.cs")]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        sys.exit("No compiló.")
    os.replace(tmp, SALIDA)
    for viejo in glob.glob(os.path.join(AQUI, "Instalar-USER-PRO-Corel*.exe")):
        if os.path.abspath(viejo) != os.path.abspath(SALIDA):
            os.remove(viejo)
    print(f"Listo: {os.path.basename(SALIDA)} ({os.path.getsize(SALIDA) // 1024} KB)")


if __name__ == "__main__":
    imagenes()
    v = versionar()
    print("Versión:", v)
    compilar(v)
