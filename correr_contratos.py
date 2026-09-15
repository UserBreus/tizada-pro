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
import os
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
TOPE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 60
LENTO = TOPE * 0.5          # pasó, pero tardó demasiado para lo que mide

def main():
    os.chdir(AQUI)
    # 🔴 UN CONTRATO NO PUEDE COMERSE LA MÁQUINA. `verificar_desplegado` levanta un pool para el
    # alta y, sin tope, son 6 workers de ~1,4 GB: 8,5 GB sólo para correr una prueba (medido
    # 2026-09-15, con el usuario trabajando al lado). Se acota acá, no en cada contrato.
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               TIZADA_PROCESOS=os.environ.get("TIZADA_PROCESOS", "2"))
    files = sorted(f for f in os.listdir(AQUI) if f.startswith("verificar_") and f.endswith(".py"))
    print(f"{len(files)} contratos · tope {TOPE}s cada uno\n")
    rojos, lentos, verdes, t0 = [], [], 0, time.time()
    for f in files:
        t = time.time()
        try:
            r = subprocess.run([sys.executable, f], capture_output=True, text=True,
                               timeout=TOPE, env=env, errors="replace")
            dur, code, out = time.time() - t, r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
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
