# -*- mode: python ; coding: utf-8 -*-
# RECETA DE EMPAQUETADO de la aplicación de escritorio (PyInstaller, modo carpeta).
# La corre `CONSTRUIR-APLICACION.bat`; a mano: `escritorio\.venv\Scripts\pyinstaller escritorio\TizadaPro.spec`.
#
# Qué va adentro y por qué:
#   · los módulos propios que usa el servidor — muchos se importan ADENTRO de funciones y el
#     analizador podría no verlos: se listan todos (`verificar_rip_compatible` también, lo usa la
#     tizada para chequear el PDF);
#   · la pantalla compilada (`frontend/dist`), el esquema de la base, VERSION;
#   · las tipografías DEL SISTEMA (no las subidas por el usuario: la app arranca vacía);
#   · los perfiles de color de Adobe de esta PC (sin ellos, en otra PC el color sale distinto);
#   · `config_externo.json` (la API de telas): sin él no hay telas y no se puede armar una tizada.
import glob
import os

RAIZ = os.path.abspath(os.path.join(SPECPATH, ".."))

MODULOS = ["actualizaciones", "api_usuarios", "aplanar_rip", "auth", "cortar_capas", "db",
           "empaquetar", "ficha_tecnica", "hoja_pike", "importar_dxf", "molde_real",
           "motor_pedido", "nesting_contorno", "objetos_agregados", "piezas_con_diseno",
           "piezas_molde", "procesos", "registro", "servidor", "texto_curvas", "variantes_molde",
           "verificar_rip_compatible"]

datas = [
    (os.path.join(RAIZ, "frontend", "dist"), os.path.join("frontend", "dist")),
    (os.path.join(RAIZ, "db", "schema.sql"), "db"),
    (os.path.join(RAIZ, "VERSION"), "."),
    (os.path.join(SPECPATH, "recursos", "tizada.ico"), "recursos"),
]
if os.path.exists(os.path.join(RAIZ, "config_externo.json")):
    datas.append((os.path.join(RAIZ, "config_externo.json"), "."))
for f in glob.glob(os.path.join(RAIZ, "catalogo_fuentes", "*")):
    if os.path.isfile(f) and not os.path.basename(f).startswith("subida_"):
        datas.append((f, "catalogo_fuentes_base"))
for d in (r"C:\Program Files (x86)\Common Files\Adobe\Color\Profiles\Recommended",
          r"C:\Program Files\Common Files\Adobe\Color\Profiles\Recommended"):
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.lower().endswith((".icc", ".icm")):
                datas.append((os.path.join(d, f), "perfiles_icc"))
        break

a = Analysis(
    [os.path.join(SPECPATH, "app_escritorio.py")],
    pathex=[RAIZ],
    binaries=[],
    datas=datas,
    hiddenimports=MODULOS + ["webview.platforms.edgechromium", "clr", "pyodbc", "waitress"],
    hookspath=[],
    runtime_hooks=[],
    # Nada de esto lo usa el sistema y suma cientos de MB si el analizador lo arrastra.
    excludes=["matplotlib", "IPython", "jupyter", "notebook", "pytest", "PyQt5", "PySide2",
              "PySide6", "tkinter", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="TIZADA PRO",
    icon=os.path.join(SPECPATH, "recursos", "tizada.ico"),
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="TIZADA PRO", upx=False)
