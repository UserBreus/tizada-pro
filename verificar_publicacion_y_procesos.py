# -*- coding: utf-8 -*-
"""CONTRATO: LO QUE SE PUBLICA SE PUEDE IDENTIFICAR, Y UN PROCESO TRABADO NO CUELGA EL SERVIDOR
`py verificar_publicacion_y_procesos.py`

Reporte del usuario (2026-09-16): *«lo que mandé al servidor no fue completo desde el botón de
enviar: quedó una versión vieja pero dice que es nueva»*. Medido con el paquete que viajó
(`dist/TIZADAPRO_1.0.37_1a2aa37.zip`, 15:20): su `servidor.py` es EXACTAMENTE el del commit
`1a2aa37`; la compresión del JS se escribió después (15:36) y se commiteó también como 1.0.37.
El botón mandó todo lo que había; lo que faltaba era poder SABER qué código tiene cada lado.
Y el publicado informaba `commit 730693a` (un checkout de git del 29/07 que nadie actualiza).

En el mismo análisis del servidor publicado (Linux): ningún pool elegía cómo crear sus procesos
(`fork` en Linux, con 8 hilos atendiendo) y había `.result()` sin tope en pedidos web: la
explicación más probable del cuelgue silencioso del 14/9.

Lo que se prueba:
  1. el paquete lleva `_huella_publicada.py` con la huella del código, y coincide con la que
     calcula el taller sobre sus archivos; cambiar un .py cambia la huella; los fines de línea no;
  2. `_version()` de una instalación por paquete informa la huella y el commit DEL PAQUETE, no los
     de git; `/api/actualizacion/estado` y la pantalla de Publicación la muestran y la comparan;
  3. todos los pools usan `procesos.pool` (spawn) y un proceso trabado se mata al vencer el tope;
  4. ningún `.result()` / `as_completed` / `wait` espera para siempre en el servidor, el aplanado
     ni el desplegado; `_ASIGNAR_JOBS` se recorre sobre una copia; el aplanado no se reintenta
     adentro del servidor.

⚠️ No toca datos: el paquete de prueba se arma en un temporal, sin compilar la pantalla.
"""
import glob
import io
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.chdir(AQUI)

FALLOS = []


def ok(cond, msg):
    print(("    OK    " if cond else "    ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


def _dormir(s):
    time.sleep(s)
    return s


def leer(f):
    return io.open(os.path.join(AQUI, f), encoding="utf-8").read()


def main():
    import empaquetar as E
    import procesos as PR

    print("1 · 🔴 EL PAQUETE DICE QUÉ CÓDIGO LLEVA")
    tmp = tempfile.mkdtemp(prefix="verif_pub_")
    try:
        _salida, _argv = E.SALIDA, sys.argv
        E.SALIDA = tmp
        sys.argv = ["empaquetar.py", "--sin-frontend", "--base", "/"]
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            E.main()
        E.SALIDA, sys.argv = _salida, _argv
        zips = glob.glob(os.path.join(tmp, "*.zip"))
        ok(len(zips) == 1, "se armó el paquete de prueba")
        with zipfile.ZipFile(zips[0]) as z:
            nombres = z.namelist()
            ok(E.HUELLA_ARCHIVO in nombres, f"el paquete lleva `{E.HUELLA_ARCHIVO}`")
            ns = {}
            exec(z.read(E.HUELLA_ARCHIVO).decode("utf-8"), ns)
        h = E.huella_codigo()
        ok(ns.get("HUELLA") == h and len(h) == 12,
           f"🔴 la huella del paquete ({ns.get('HUELLA')}) es la del código de acá ({h})")
        ok(ns.get("VERSION") == open("VERSION", encoding="utf-8").read().strip() and ns.get("ARMADO"),
           "…y dice versión y cuándo se armó")
        # cambiar un .py cambia la huella; los fines de línea no
        cop = os.path.join(tmp, "copia")
        os.makedirs(cop)
        for rel in E.archivos_huella():
            d = os.path.join(cop, *rel.split("/"))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(os.path.join(AQUI, *rel.split("/")), d)
        ok(E.huella_codigo(cop) == h, "una copia exacta da la misma huella")
        with open(os.path.join(cop, "texto_curvas.py"), "rb") as fh:
            b = fh.read()
        with open(os.path.join(cop, "texto_curvas.py"), "wb") as fh:
            fh.write(b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        ok(E.huella_codigo(cop) == h, "pasar un archivo a CRLF no cambia la huella (git en Windows lo hace solo)")
        with open(os.path.join(cop, "texto_curvas.py"), "ab") as fh:
            fh.write(b"\n# un cambio\n")
        ok(E.huella_codigo(cop) != h, "🔴 cambiar una línea de código SÍ cambia la huella")
        ok(not any(n.startswith(("datos/", "entrada/", "trabajos/")) for n in nombres),
           "el paquete sigue sin llevar datos del usuario")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n2 · 🔴 CADA LADO INFORMA SU CÓDIGO, Y LA PANTALLA LO COMPARA")
    srv = leer("servidor.py")
    ok('os.path.join(AQUI, "_huella_publicada.py")' in srv and '"origen": origen' in srv,
       "`_version()` lee la huella del paquete cuando la instalación vino por paquete")
    ok("if os.path.exists(_hp):" in srv and srv.index("if os.path.exists(_hp):") < srv.index('"rev-parse", "--short", "HEAD"'),
       "…y ahí NO le pregunta a git (el checkout del publicado es viejo y mentía el commit)")
    ok('_e.update({"commit": _vv.get("commit"), "huella": _vv.get("huella")' in srv,
       "`/api/actualizacion/estado` informa commit, huella y cuándo se armó")
    ok('"local": {**_version(), "huella": _huella_local()}' in srv,
       "la pantalla de Publicación calcula la huella de acá EN EL MOMENTO (el código pudo cambiar sin reiniciar)")
    app = leer(os.path.join("frontend", "src", "App.jsx"))
    ok("const codigoIgual = !!(hLocal && hRemoto && hLocal === hRemoto);" in app
       and "El publicado NO tiene el código de esta máquina" in app,
       "🔴 la pantalla compara el CÓDIGO y dice cuándo el publicado no lo tiene aunque diga el mismo número")
    ok("const igual = local && remoto && local === remoto && codigoIgual;" in app,
       "«no hay nada para publicar» exige mismo número Y mismo código")
    ok("_huella_publicada.py" in leer(".gitignore"), "la huella nunca se escribe en el repo")

    print("\n3 · 🔴 TODOS LOS POOLS CON `spawn`, Y UN PROCESO TRABADO SE MATA")
    crudos = []
    for f in glob.glob(os.path.join(AQUI, "*.py")):
        base = os.path.basename(f)
        if base.startswith("verificar_") or base == "procesos.py":
            continue
        if re.search(r"ProcessPoolExecutor\(", io.open(f, encoding="utf-8").read()):
            crudos.append(base)
    ok(not crudos, f"nadie crea un ProcessPoolExecutor a mano: todos pasan por `procesos.pool` ({crudos})")
    ok(PR.contexto().get_start_method() == "spawn", "el contexto es `spawn` (nunca `fork` con hilos)")
    t0 = time.time()
    try:
        with PR.seguro(PR.pool(1)) as ex:
            ex.submit(_dormir, 300).result(timeout=3)
        vencio = False
    except Exception:
        vencio = True
    dur = time.time() - t0
    ok(vencio and dur < 30, f"un hijo trabado 300 s se abandona al vencer el tope ({dur:.1f} s, sin esperarlo)")
    with PR.seguro(PR.pool(1)) as ex:
        ok(ex.submit(_dormir, 0.05).result(timeout=60) == 0.05, "y el pool siguiente anda normal")

    print("\n4 · NADA ESPERA PARA SIEMPRE")
    sin_tope = []
    for f in ("servidor.py", "aplanar_rip.py", "piezas_con_diseno.py", "hoja_pike.py"):
        lineas = leer(f).splitlines()
        for i, ln in enumerate(lineas, 1):
            # un `.result()` sin tope vale SÓLO sobre un futuro que ya terminó: el que entrega un
            # `as_completed(..., timeout=…)` o un `wait(...)` de las líneas de arriba
            previas = " ".join(lineas[max(0, i - 5):i - 1])
            if re.search(r"\.result\(\)", ln) and not re.search(r"as_completed\(|_listos", previas):
                sin_tope.append(f"{f}:{i}")
            if "as_completed(" in ln and "timeout" not in ln:
                sin_tope.append(f"{f}:{i}")
    ok(not sin_tope, f"ningún `.result()` ni `as_completed` sin tope ({sin_tope})")
    ok("wait(_pend, timeout=_TOPE_PROCESO_S, return_when=FIRST_COMPLETED)" in srv,
       "el pre-dibujado del arte tampoco espera sin tope")
    ok("for _vj in list(_ASIGNAR_JOBS.values()):" in srv,
       "`_ASIGNAR_JOBS` se recorre sobre una copia (dos subidas a la vez no tiran un 500)")
    ap = leer("aplanar_rip.py")
    ok("aplano acá mismo" not in ap and "_aplanar_en_proceso" in ap,
       "🔴 el aplanado ya no se reintenta ADENTRO del servidor (+620 MB justo cuando algo falló)")
    ok(srv.count('res.setdefault("avisos", []).append(') >= 2 and "no se pudo preparar para el RIP" in srv,
       "una hoja que no se pudo aplanar lo AVISA en el pedido y no frena a las demás")

    print()
    if FALLOS:
        print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
        for f in FALLOS:
            print("   ·", f)
        return 1
    print("✅ CONTRATO VERDE — cada lado dice qué código tiene y ningún proceso trabado cuelga el servidor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
