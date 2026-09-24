"""Arma el INSTALADOR de la extensión de Illustrator: `Instalar-USER-PRO-Illustrator.exe`.

Correr:  py extension_illustrator/construir.py

Qué hace (todo con lo que ya trae la PC, sin bajar nada):
  1. Dibuja las imágenes de la marca desde `frontend/public/logo.svg` (el ISOTIPO del sistema):
     - los íconos de la extensión en Illustrator (`com.tizadapro.illustrator/img/icono*.png`);
     - el ISOLOGO del instalador (isotipo + «USER PRO» + «Motor de Sublimación»);
     - el ícono del .exe (`.ico`, de 16 a 256 px).
  2. Empaqueta la extensión (`com.tizadapro.illustrator/`) en un ZIP que va ADENTRO del .exe.
  3. Compila `instalador/Instalador.cs` con el compilador de C# de Windows (.NET Framework 4, viene
     con Windows 10/11) → un único .exe que instala y registra el desinstalador.

🔴 LA VERSIÓN SUBE SOLA (pedido del usuario 2026-09-23: «cada cambio que haya que descargar, con su
versión»). Se calcula una HUELLA de todo lo que va adentro del instalador (la extensión y el código
del instalador, sin contar el número de versión); si cambió desde la última vez
(`historial_versiones.json`), la versión sube (1.5.0 → 1.6.0) y se escribe en el manifiesto y en el
puente. El .exe lleva la versión en el NOMBRE (`Instalar-USER-PRO-Illustrator-1.6.0.exe`) y se
borran los de versiones anteriores. Sin cambios, se rearma con la misma versión.

Las imágenes de la marca SÍ se pasan a píxeles a propósito: son íconos del programa, no el arte del
usuario (la ley del vector original es para los archivos del cliente).
"""
import datetime
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile

import fitz
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EXT = os.path.join(AQUI, "com.tizadapro.illustrator")
INST = os.path.join(AQUI, "instalador")
OBRA = os.path.join(AQUI, "build")                       # intermedios (no van a git)
HISTORIAL = os.path.join(AQUI, "historial_versiones.json")
MANIFIESTO = os.path.join(EXT, "CSXS", "manifest.xml")
PUENTE = os.path.join(EXT, "js", "puente.js")


def salida(v):
    return os.path.join(AQUI, f"Instalar-USER-PRO-Illustrator-{v}.exe")
LOGO = os.path.join(RAIZ, "frontend", "public", "logo.svg")
CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

CIAN = (0, 213, 255)          # --cmyk-cyan de la app: hsl(190, 100%, 50%)
FUENTE_B = r"C:\Windows\Fonts\segoeuib.ttf"
FUENTE_R = r"C:\Windows\Fonts\segoeui.ttf"


def isotipo(alto):
    """El isotipo con fondo transparente, `alto` px de alto."""
    d = fitz.open(LOGO)
    r = d[0].rect
    z = alto / r.height
    pm = d[0].get_pixmap(matrix=fitz.Matrix(z * 2, z * 2), alpha=True)
    im = Image.frombytes("RGBA", (pm.width, pm.height), pm.samples)
    return im.resize((round(r.width * z), alto), Image.LANCZOS)


def cuadrado(im, lado, margen=0.06):
    """El isotipo centrado en un cuadrado transparente (para íconos)."""
    m = round(lado * margen)
    iso = im.copy()
    iso.thumbnail((lado - 2 * m, lado - 2 * m), Image.LANCZOS)
    out = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    out.paste(iso, ((lado - iso.width) // 2, (lado - iso.height) // 2), iso)
    return out


def isologo(alto=220, fondo_oscuro=True):
    """Isotipo + «USER PRO» + «Motor de Sublimación», como la barra de la app."""
    iso = isotipo(alto)
    fb = ImageFont.truetype(FUENTE_B, round(alto * 0.46))
    fr = ImageFont.truetype(FUENTE_R, round(alto * 0.17))
    claro = (255, 255, 255) if fondo_oscuro else (20, 24, 30)
    gris = (150, 160, 172) if fondo_oscuro else (90, 98, 110)
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    w_user = tmp.textlength("USER", font=fb)
    w_pro = tmp.textlength(" PRO", font=fb)
    w_sub = tmp.textlength("Motor de Sublimación", font=fr)
    sep = round(alto * 0.14)
    ancho = iso.width + sep + round(max(w_user + w_pro, w_sub)) + 8
    out = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    out.paste(iso, (0, 0), iso)
    d = ImageDraw.Draw(out)
    x = iso.width + sep
    y = round(alto * 0.10)
    d.text((x, y), "USER", font=fb, fill=CIAN + (255,))
    d.text((x + w_user, y), " PRO", font=fb, fill=claro + (255,))
    d.text((x + 4, round(alto * 0.66)), "Motor de Sublimación", font=fr, fill=gris + (255,))
    return out


def imagenes():
    os.makedirs(OBRA, exist_ok=True)
    img = os.path.join(EXT, "img")
    os.makedirs(img, exist_ok=True)
    iso = isotipo(1024)
    # íconos del panel en Illustrator (23 px y el doble para pantallas de alta densidad)
    for lado, suf in ((23, ""), (46, "@2x")):
        cuadrado(iso, lado, 0.02).save(os.path.join(img, f"icono{suf}.png"))
    # el isotipo grande (panel y tutorial)
    cuadrado(iso, 256, 0.02).save(os.path.join(img, "isotipo.png"))
    # isologos (instalador = fondo oscuro; tutorial = fondo claro)
    isologo(220, True).save(os.path.join(OBRA, "isologo_oscuro.png"))
    isologo(220, False).save(os.path.join(img, "isologo_claro.png"))
    isologo(220, True).save(os.path.join(img, "isologo_oscuro.png"))
    # el ícono del .exe
    cuadrado(iso, 256, 0.02).save(os.path.join(OBRA, "icono.ico"),
                                  sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


def zip_extension():
    ruta = os.path.join(OBRA, "extension.zip")
    with zipfile.ZipFile(ruta + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _dirs, archivos in os.walk(EXT):
            for a in sorted(archivos):
                p = os.path.join(raiz, a)
                z.write(p, os.path.relpath(p, EXT).replace(os.sep, "/"))
    os.replace(ruta + ".tmp", ruta)
    return ruta


def version():
    m = re.search(r'ExtensionBundleVersion="([^"]+)"', open(MANIFIESTO, encoding="utf-8").read())
    return m.group(1) if m else "1.0.0"


def _sin_version(txt):
    # el número de versión no cuenta para la huella (si no, subirla cambiaría la huella)
    txt = re.sub(r'Version="\d+\.\d+\.\d+"', 'Version=""', txt)
    return re.sub(r"var VERSION = '[^']*'", "var VERSION = ''", txt)


def huella():
    """Todo lo que viaja adentro del instalador: la extensión (con sus imágenes) y el código del
    instalador. Si esto cambia, es una versión nueva."""
    h = hashlib.sha1()
    rutas = []
    for raiz, _dirs, archivos in os.walk(EXT):
        rutas += [os.path.join(raiz, a) for a in archivos]
    rutas += [os.path.join(INST, a) for a in os.listdir(INST)]
    # 🔴 y lo que decide QUÉ se arma en Illustrator (el plan: mesas, acomodo, nombres), aunque viva
    # en la pantalla: regla del usuario 2026-09-23, «cada vez que actualizamos algo, una versión».
    # Se olvidó una vez (una mesa por pieza, MAPA 538) por ser «sólo de la pantalla».
    rutas.append(os.path.join(RAIZ, "frontend", "src", "motor", "molde", "illustrator.js"))
    for r in sorted(rutas):
        h.update(os.path.relpath(r, AQUI).replace(os.sep, "/").encode())
        b = open(r, "rb").read()
        if r.endswith((".xml", ".js")):
            b = _sin_version(b.decode("utf-8")).encode("utf-8")
        h.update(b)
    return h.hexdigest()


def fijar_version(v):
    """Escribe la versión en el manifiesto (paquete y las dos extensiones) y en el puente."""
    for ruta, pat, rep in ((MANIFIESTO, r'((?:ExtensionBundle)?Version=")\d+\.\d+\.\d+(")', r"\g<1>" + v + r"\g<2>"),
                           (PUENTE, r"var VERSION = '[^']*'", f"var VERSION = '{v}'")):
        txt = open(ruta, encoding="utf-8").read()
        nuevo = re.sub(pat, rep, txt)
        if nuevo != txt:
            with open(ruta + ".tmp", "w", encoding="utf-8", newline="") as fh:
                fh.write(nuevo)
            os.replace(ruta + ".tmp", ruta)


def versionar():
    """La versión de este armado: la misma si nada cambió, la siguiente si cambió algo."""
    try:
        hist = json.load(open(HISTORIAL, encoding="utf-8"))
    except (OSError, ValueError):
        hist = []
    v, hu = version(), huella()
    if hist and hist[-1].get("huella") == hu:
        return v
    if hist:
        # algo cambió desde la última versión armada: la siguiente (a partir de la mayor conocida)
        ult = max([v] + [x["version"] for x in hist], key=lambda t: tuple(int(n) for n in t.split(".")))
        a, b, _c = (int(n) for n in ult.split("."))
        v = f"{a}.{b + 1}.0"
    fijar_version(v)
    hist.append({"version": v, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "huella": huella()})
    with open(HISTORIAL + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(hist, fh, ensure_ascii=False, indent=1)
    os.replace(HISTORIAL + ".tmp", HISTORIAL)
    return v


def compilar(zip_ruta):
    if not os.path.exists(CSC):
        sys.exit("No encontré el compilador de C# de Windows (" + CSC + ").")
    v = version()
    # la versión entra al programa por un archivo generado (el .cs no se toca a mano en cada versión)
    with open(os.path.join(OBRA, "Version.cs"), "w", encoding="utf-8") as fh:
        fh.write('namespace UserPro { static class Version { public const string Texto = "%s"; } }\n' % v)
    SALIDA = salida(v)
    tmp = SALIDA + ".tmp.exe"
    cmd = [CSC, "/nologo", "/target:winexe", "/optimize+", "/codepage:65001",
           "/out:" + tmp,
           "/win32icon:" + os.path.join(OBRA, "icono.ico"),
           "/win32manifest:" + os.path.join(INST, "app.manifest"),
           "/resource:" + zip_ruta + ",extension.zip",
           "/resource:" + os.path.join(OBRA, "isologo_oscuro.png") + ",isologo.png",
           "/resource:" + os.path.join(OBRA, "icono.ico") + ",icono.ico",
           "/r:System.dll", "/r:System.Drawing.dll", "/r:System.Windows.Forms.dll",
           "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll",
           os.path.join(INST, "Instalador.cs"), os.path.join(OBRA, "Version.cs")]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        sys.exit("No compiló el instalador.")
    os.replace(tmp, SALIDA)
    # los instaladores de versiones anteriores no quedan dando vueltas (el servidor sirve EL de hoy)
    for viejo in glob.glob(os.path.join(AQUI, "Instalar-USER-PRO-Illustrator*.exe")):
        if os.path.abspath(viejo) != os.path.abspath(SALIDA):
            os.remove(viejo)
    print(f"Listo: {os.path.basename(SALIDA)} ({os.path.getsize(SALIDA) // 1024} KB)")


if __name__ == "__main__":
    imagenes()
    v = versionar()
    print("Versión:", v)
    compilar(zip_extension())
