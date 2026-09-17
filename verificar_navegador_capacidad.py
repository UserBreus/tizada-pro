# -*- coding: utf-8 -*-
"""
CONTRATO: LA PUERTA DE POTENCIA CIERRA CUANDO NO ALCANZA Y ABRE CUANDO SOBRA — `py verificar_navegador_capacidad.py`

PLAN_NAVEGADOR.md, etapa 5 («quien no tenga la potencia no podrá enviar»). `frontend/src/motor/
capacidad.js` mide la máquina antes de cada trabajo pesado: memoria declarada, una reserva de prueba
del tamaño que el trabajo pide y un benchmark corto. Acá se corre en Node con la memoria LIMITADA
declarada por el navegador (lo primero que mira la puerta): con 1 GB un molde de 117 MB tiene que
ser rechazado, con motivo en palabras; con 8 GB tiene que pasar (y la reserva de prueba y el
benchmark corren de verdad). No toca nada del usuario ni la base.
"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = os.path.dirname(os.path.abspath(__file__))
NODE = os.path.join(AQUI, "frontend", "src", "motor", "pruebas", "capacidad.mjs")
FALLOS = []


def ok(cond, msg):
    if not cond:
        FALLOS.append(msg)
    print(("  OK    " if cond else "  FALLA ") + msg)


def correr(mem_gb, mb_trabajo):
    cmd = ["node", NODE, str(mb_trabajo), "molde"] + ([str(mem_gb)] if mem_gb else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=300)
    if r.returncode != 0:
        return {"puede": False, "motivo": "el proceso se cortó: " + r.stderr[-200:], "necesita": None}
    return json.loads(r.stdout.strip().splitlines()[-1])


print("\n1 · CON POCA MEMORIA, LA PUERTA CIERRA")
r = correr(1, 117)
ok(r["puede"] is False, f"un molde de 117 MB en una máquina que declara 1 GB: rechazado ({r.get('motivo', '')[:110]}…)")
ok(bool(r.get("motivo")), "y el motivo está en palabras para la pantalla")

print("\n2 · CON MEMORIA DE SOBRA, LA PUERTA ABRE")
r = correr(8, 117)
ok(r["puede"] is True, f"el mismo molde con 8 GB: pasa (necesita {r.get('necesita')} MB · {r.get('puntos')} puntos de potencia)")
ok((r.get("benchmark") or 0) > 0, f"el benchmark mide algo ({r.get('benchmark')} puntos)")

print()
if FALLOS:
    print(f"❌ CONTRATO ROTO — {len(FALLOS)} falla(s):")
    for f in FALLOS:
        print("   · " + f)
    sys.exit(1)
print("✅ CONTRATO VERDE — la puerta de potencia cierra sin memoria y abre con memoria")
