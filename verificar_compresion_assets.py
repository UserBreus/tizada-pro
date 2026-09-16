# -*- coding: utf-8 -*-
"""CONTRATO: EL FRONTEND SE BAJA UNA VEZ Y COMPRIMIDO — `py verificar_compresion_assets.py`

Reporte del usuario (2026-09-16): «lo veo muy lento». Medido en el servidor publicado: el JS de la
app (1.094.110 bytes) viajaba SIN comprimir y con `Cache-Control: no-store`, así que el navegador lo
volvía a bajar entero en cada carga — 3 s por F5, por pestaña y por persona.

Se vigila:
  1. `/assets/*` (nombre con hash de Vite) → `immutable` por un año, y gzip si el navegador lo acepta;
     descomprimido es BYTE A BYTE el archivo.
  2. Sin `Accept-Encoding: gzip` → el archivo crudo, intacto.
  3. `index.html` sigue en no-store: es lo que hace que una versión nueva aparezca sola.
  4. Un JSON grande de la API se comprime y sigue siendo el mismo JSON.
  5. 🔴 Un PDF NO se toca: sin `Content-Encoding` y con su `Content-Length` real (el panel de
     descargas mide el avance contra ese número; un PDF ya viene comprimido).
  6. Una respuesta chica (< 1 KB) no se comprime.

⚠️ No toca la base (módulo `db` reemplazado) ni datos del usuario.
"""
import glob
import gzip
import io
import json
import os
import sys
import tempfile
import types

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
_falso = types.ModuleType("db")
_falso.__getattr__ = lambda n: (lambda *a, **k: (_ for _ in ()).throw(AssertionError(f"MSSQL (db.{n})")))
_falso.get_doc = lambda c, default=None: default
_falso.set_doc = lambda c, o: None
_falso.proyectar_catalogo = lambda c: None
sys.modules["db"] = _falso
sys.modules["api_usuarios"] = types.ModuleType("api_usuarios")
import registro as LOG                                   # noqa: E402
LOG.usar_carpeta(tempfile.mkdtemp(prefix="verif_gzip_"))
import servidor as S                                     # noqa: E402
from flask import jsonify, send_file                     # noqa: E402

FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  FALLA ") + msg)
    if not cond:
        FALLOS.append(msg)


# Las rutas de prueba van ANTES del primer pedido: Flask no deja agregar rutas a una app que ya
# atendió uno.
@S.app.get("/__prueba_json_grande")
def _prueba_json():
    return jsonify({"filas": [{"talle": "M", "nombre": f"Jugador {i}", "numero": i} for i in range(400)]})


@S.app.get("/__prueba_json_chico")
def _prueba_chico():
    return jsonify({"ok": True})


_PDF = os.path.join(tempfile.mkdtemp(prefix="verif_gzip_pdf_"), "h.pdf")
import pikepdf                                           # noqa: E402
_d = pikepdf.new()
for _ in range(30):
    _d.add_blank_page(page_size=(500, 500))
_d.save(_PDF)


@S.app.get("/__prueba_pdf")
def _prueba_pdf():
    return send_file(_PDF, mimetype="application/pdf", as_attachment=True, download_name="h.pdf")


GZ = {"Accept-Encoding": "gzip, deflate, br"}
cli = S.app.test_client()

js = sorted(glob.glob(os.path.join(RAIZ, "frontend", "dist", "assets", "*.js")), key=os.path.getsize)
if not js:
    print("  (no hay frontend/dist compilado: correr `npm run build`)")
    sys.exit(1)
arch = js[-1]
crudo = open(arch, "rb").read()
url = "/assets/" + os.path.basename(arch)

print(f"\n1 · {url} ({len(crudo)/1e3:.0f} KB)")
r = cli.get(url, headers=GZ)
cc = r.headers.get("Cache-Control", "")
ok(r.status_code == 200, "contesta 200")
ok("immutable" in cc and "max-age=31536000" in cc and "no-store" not in cc,
   f"🔴 se cachea para siempre (Cache-Control: {cc})")
ok(r.headers.get("Content-Encoding") == "gzip", "viaja comprimido con gzip")
cuerpo = r.get_data()
ok(gzip.decompress(cuerpo) == crudo, "descomprimido es BYTE A BYTE el archivo")
ok(int(r.headers.get("Content-Length", 0)) == len(cuerpo), "Content-Length = los bytes comprimidos")
ok("Accept-Encoding" in (r.headers.get("Vary") or ""), "declara Vary: Accept-Encoding")
print(f"    {len(crudo)/1e3:.0f} KB → {len(cuerpo)/1e3:.0f} KB")
r2 = cli.get(url, headers=GZ)
ok(r2.get_data() == cuerpo, "la segunda vez sale del caché y da lo mismo")

print("\n2 · el mismo asset, sin aceptar gzip")
r = cli.get(url)
ok(not r.headers.get("Content-Encoding") and r.get_data() == crudo, "llega crudo e intacto")

print("\n3 · index.html")
r = cli.get("/")
cc = r.headers.get("Cache-Control", "")
ok("no-store" in cc and "immutable" not in cc, "sigue en no-store (así aparece sola la versión nueva)")

print("\n4 · un JSON grande de la API")
r = cli.get("/__prueba_json_grande", headers=GZ)
ok(r.headers.get("Content-Encoding") == "gzip", "se comprime")
ok(json.loads(gzip.decompress(r.get_data()))["filas"][399]["numero"] == 399, "y es el mismo JSON")

print("\n5 · 🔴 un PDF")
r = cli.get("/__prueba_pdf", headers=GZ)
ok(not r.headers.get("Content-Encoding"), "NO se comprime (ya viene comprimido)")
ok(int(r.headers.get("Content-Length", -1)) == os.path.getsize(_PDF) == len(r.get_data()),
   "su Content-Length es el tamaño real del archivo (lo usa el panel de descargas)")

print("\n6 · una respuesta chica")
r = cli.get("/__prueba_json_chico", headers=GZ)
ok(not r.headers.get("Content-Encoding"), "menos de 1 KB: no se comprime")

print()
if FALLOS:
    print(f"  {len(FALLOS)} FALLO(S)")
    sys.exit(1)
print("  OK: el frontend se baja una vez y comprimido; los PDF no se tocan")
