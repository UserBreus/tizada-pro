# -*- coding: utf-8 -*-
"""CORRE TODOS LOS CONTRATOS, CON TOPE DE TIEMPO.  `py correr_contratos.py [segundos]`

🔴 REGLA (usuario, 2026-09-15): lo que se pasa del tope NO se espera — se para y se arregla. Un
contrato que tarda minutos es en sí mismo un defecto: si la red de seguridad no se puede correr
rápido, no se corre, y deja de servir.

  · Tope por contrato: `TOPE` segundos (60 por defecto; el argumento manda).
  · El estado es el CÓDIGO DE SALIDA, nunca el texto. (Trampa ya pagada: tres contratos que
    pasaban decían «TODO OK: nada queda abierto, ni cuando falla» y un grep por «falla» los
    marcaba en rojo.)
  · Al final, la lista de los LENTOS aunque hayan pasado: son los próximos a arreglar.
"""
import io
import os
import subprocess
import sys
import time

import procesos

AQUI = os.path.dirname(os.path.abspath(__file__))
TOPE = next((int(a) for a in sys.argv[1:] if a.isdigit()), 60)
LENTO = TOPE * 0.5          # pasó, pero tardó demasiado para lo que mide

def main():
    # El corredor escribe emojis y acentos. Redirigido a un archivo, Windows le pone cp1252 a
    # stdout y el `print` del RESUMEN reventaba con UnicodeEncodeError: la tanda corria entera
    # y despues no se podia leer QUE fallo. La herramienta que reporta problemas no puede
    # romperse justo al reportarlos.
    for _f in (sys.stdout, sys.stderr):
        try:
            _f.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    os.chdir(AQUI)
    # 🔴 LOS HIJOS SE MUEREN CON ESTO. Un contrato levanta su propio pool: al cortar una corrida
    # quedaron 18 procesos sueltos con 8,8 GB en la máquina del usuario (2026-09-15). Con el Job
    # Object, matar el corredor se lleva todo lo que haya lanzado.
    procesos.atar_hijos()
    # 🔴 UN CONTRATO NO PUEDE COMERSE LA MÁQUINA. `verificar_desplegado` levanta un pool para el
    # alta y, sin tope, son 6 workers de ~1,4 GB: 8,5 GB sólo para correr una prueba (medido
    # 2026-09-15, con el usuario trabajando al lado). Se acota acá, no en cada contrato.
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               TIZADA_PROCESOS=os.environ.get("TIZADA_PROCESOS", "2"))
    files = sorted(f for f in os.listdir(AQUI) if f.startswith("verificar_") and f.endswith(".py"))
    # 🔴 LOS PESADOS SE DECLARAN Y SE SACAN DE LA TANDA RÁPIDA. Un contrato de integración sobre
    # el archivo real de 123 MB tarda minutos y no hay forma honesta de acortarlo (no existe un
    # molde liviano con varias mesas). Antes que subirle el tope a TODOS —o que la tanda entera
    # tarde media hora y nadie la corra—, se aparta: `--todos` lo incluye.
    todos = "--todos" in sys.argv
    pesados = set()
    for f in files:
        try:
            if "CONTRATO_LENTO" in io.open(os.path.join(AQUI, f), encoding="utf-8").read(2000):
                pesados.add(f)
        except Exception:
            pass
    if not todos and pesados:
        print("  (fuera de la tanda rapida, son de integracion: " + ", ".join(sorted(pesados))
              + " - correlos con --todos)", flush=True)
        files = [f for f in files if f not in pesados]
    print(f"{len(files)} contratos · tope {TOPE}s cada uno\n")
    rojos, lentos, verdes, t0 = [], [], 0, time.time()
    for f in files:
        t = time.time()
        # 🔴 AL CORTAR POR TOPE HAY QUE MATAR EL ÁRBOL, NO EL CONTRATO SOLO. `subprocess.run` con
        # `timeout` mata al hijo directo; el pool que ese contrato levantó queda vivo hasta que
        # termine la tanda entera (medido 2026-09-15: 13 procesos, 930 MB, con el corredor todavía
        # corriendo). El Job Object sólo actúa cuando muere el corredor, y acá el corredor sigue.
        pr = subprocess.Popen([sys.executable, f], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=env, errors="replace")
        try:
            so, se = pr.communicate(timeout=TOPE)
            dur, code, out = time.time() - t, pr.returncode, (so or "") + (se or "")
        except subprocess.TimeoutExpired:
            procesos.matar_arbol(pr.pid)
            try:
                pr.communicate(timeout=10)
            except Exception:
                pr.kill()
            dur, code, out = time.time() - t, 124, ""
        if code == 0:
            verdes += 1
            marca = "verde"
            if dur > LENTO:
                lentos.append((f, dur))
                marca = "verde (LENTO)"
        else:
            rojos.append((f, code, out))
            marca = "SE PASÓ DEL TOPE" if code == 124 else f"ROJO ({code})"
        print(f"  {dur:6.1f}s  {marca:<16} {f}", flush=True)
    print(f"\n{'='*78}\n{verdes} verdes · {len(rojos)} en rojo · {time.time()-t0:.0f}s en total")
    for f, code, out in rojos:
        print(f"\n🔴 {f}" + ("  — SE PASÓ DEL TOPE, hay que hacerlo más rápido" if code == 124 else ""))
        for ln in [x for x in out.splitlines() if x.strip()][-6:]:
            print("     " + ln)
    if lentos:
        print(f"\n⏳ pasan pero tardan (tope {TOPE}s): " +
              ", ".join(f"{f} {d:.0f}s" for f, d in sorted(lentos, key=lambda x: -x[1])))
    return 1 if rojos else 0


if __name__ == "__main__":
    sys.exit(main())
