# -*- coding: utf-8 -*-
"""CONTRATO: UNA ACTUALIZACIÓN QUE SALE BIEN NO PUEDE MARCARSE COMO FALLIDA.

EL CASO REAL (2026-09-01, versión 1.0.32 al VPS): el usuario publicó y le apareció «Última
actualización: falló — el paquete quedó APARCADO para aplicarlo a mano». El servidor seguía en la
versión vieja y el paquete, sano, sin aplicar.

La causa era una CARRERA del modo «reinicio» (Linux con `Restart=always`, sin root):

    1. el servidor lanza al ayudante y se apaga a los 2 segundos;
    2. systemd lo levanta enseguida — con la versión VIEJA, porque el ayudante recién está
       respaldando y descomprimiendo;
    3. ese arranque ve la marca «en curso», la declara interrumpida y APARCA el paquete;
    4. y como el servidor volvió, el puerto nunca se libera: el ayudante espera 90 s y termina
       pidiendo un `systemctl restart` que sin root no puede hacer.

El fallo quedó registrado 14 segundos después de publicar: justo el tiempo de ese ida y vuelta.

Acá se prueban las dos mitades del arreglo, sin tocar nada real (todo en una carpeta temporal):
  · el servidor NO se apaga hasta que el ayudante avisa que ya descomprimió (`listo.flag`);
  · un arranque en medio de una actualización VIVA no la da por fallada.

    py verificar_actualizacion_carrera.py
"""
import os
import sys
import time
import json
import shutil
import tempfile
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

fallos = []


def ok(cond, msg):
    # la consola de Windows es cp1252: un emoji la haría reventar a mitad del contrato
    linea = ("  OK    " if cond else "  FALLA ") + msg
    try:
        print(linea)
    except UnicodeEncodeError:
        print(linea.encode("ascii", "replace").decode("ascii"))
    if not cond:
        fallos.append(msg)


import actualizaciones as ACT  # noqa: E402
import registro as LOG            # noqa: E402

# ── todo el módulo, apuntado a una carpeta de juguete ────────────────────────────────────────
TMP = tempfile.mkdtemp(prefix="tizada_act_")
# 🔴 EL REGISTRO TAMBIÉN. Este contrato simula una actualización que se corta, y `actualizaciones`
# deja constancia de eso en el registro del sistema: sin redirigirlo, un TEST escribiría una falla
# INVENTADA en el registro real y mañana alguien la investigaría. Pasó apenas se escribió esto.
LOG.usar_carpeta(TMP)
ACT.CARPETA = TMP
ACT.PENDIENTE = os.path.join(TMP, "pendiente.json")
ACT.PAQUETE = os.path.join(TMP, "pendiente.zip")
ACT.ULTIMA = os.path.join(TMP, "ultima.json")
ACT.EN_CURSO = os.path.join(TMP, "en_curso.json")
ACT.LISTO = os.path.join(TMP, "listo.flag")

print("\n1 · EL SERVIDOR ESPERA A QUE LA VERSIÓN NUEVA ESTÉ EN EL DISCO")
ACT.ESPERA_AYUDANTE = 6          # para no hacer esperar al contrato
t0 = time.time()
threading.Timer(1.2, lambda: open(ACT.LISTO, "w").write("1")).start()
llego = ACT.esperar_al_ayudante()
tardo = time.time() - t0
ok(llego, "se espera la señal del ayudante («ya descomprimí») antes de apagarse")
ok(1.0 < tardo < 4.0, f"y se apaga en cuanto llega, no antes ni mucho después ({tardo:.1f} s)")

os.remove(ACT.LISTO)
t0 = time.time()
llego2 = ACT.esperar_al_ayudante()
tardo2 = time.time() - t0
ok(not llego2, "🔴 si el ayudante nunca avisa, NO se espera para siempre")
ok(tardo2 >= ACT.ESPERA_AYUDANTE, f"se respeta el tope antes de seguir igual ({tardo2:.1f} s)")

print("\n2 · UN ARRANQUE EN MEDIO DE UNA ACTUALIZACIÓN VIVA NO LA DA POR FALLADA")
# el ayudante acaba de empezar (esto es lo que pasaba: systemd revive el servidor en el medio)
ACT._escribir(ACT.EN_CURSO, {"desde": "1.0.31", "hacia": "1.0.32", "inicio": time.time()})
ACT._escribir(ACT.PENDIENTE, {"version": "1.0.32", "cuando": time.time() - 5})
ACT.recuperar_si_quedo_a_medias()
ok(ACT._leer(ACT.ULTIMA) is None,
   "🔴 con el ayudante recién arrancado, el reinicio NO escribe «falló»")
ok(ACT._leer(ACT.EN_CURSO) is not None, "…y deja la marca: el ayudante sigue trabajando")
ok(float(ACT._leer(ACT.PENDIENTE).get("cuando", 0)) < ACT.MANUAL,
   "…y NO aparca el paquete (era lo que dejaba la versión vieja corriendo)")

print("\n3 · PERO UNA QUE SE CORTÓ DE VERDAD SÍ SE MARCA (y se aparca)")
ACT._escribir(ACT.EN_CURSO, {"desde": "1.0.31", "hacia": "1.0.32",
                             "inicio": time.time() - (ACT.ESPERA_AYUDANTE + 60)})
ACT._escribir(ACT.PENDIENTE, {"version": "1.0.32", "cuando": time.time() - 5})
ACT.recuperar_si_quedo_a_medias()
u = ACT._leer(ACT.ULTIMA) or {}
ok(u.get("ok") is False and u.get("version") == "1.0.32",
   "pasado el plazo sin noticias, se registra el fallo")
ok(float((ACT._leer(ACT.PENDIENTE) or {}).get("cuando", 0)) >= ACT.MANUAL,
   "y el paquete se aparca para aplicarlo a mano (no se reintenta solo: eso causó un bucle de caídas)")
ok(ACT._leer(ACT.EN_CURSO) is None, "la marca de «en curso» se limpia")

print("\n4 · UNA SEÑAL VIEJA NO PUEDE APAGAR EL SERVIDOR ANTES DE TIEMPO")
src = open(os.path.join(AQUI, "actualizaciones.py"), encoding="utf-8").read()
i = src.find("def aplicar(")
ok(i > 0 and "os.remove(LISTO)" in src[i:i + 2000],
   "🔴 al empezar una actualización se borra la señal de la anterior")

print("\n5 · EL AYUDANTE AVISA JUSTO DESPUÉS DE DESCOMPRIMIR (no antes)")
ayu = open(os.path.join(AQUI, "actualizador.py"), encoding="utf-8").read()
j = ayu.find('if modo == "reinicio":')
tramo = ayu[j:j + 1600]
ok(j > 0 and "avisar_listo(app)" in tramo, "en el modo «reinicio» el ayudante deja la señal")
ok(tramo.find("_descomprimir()") < tramo.find("avisar_listo(app)"),
   "🔴 y la deja DESPUÉS de descomprimir: si no, el servidor se apagaría con la versión vieja")
ok("listo.flag" in ayu[ayu.find("def resultado("):ayu.find("def resultado(") + 1400],
   "al terminar, la señal se limpia (no queda para la próxima)")

print()
print("6 · ESTE CONTRATO NO ENSUCIA EL REGISTRO DE VERDAD")
_real = os.path.join(AQUI, "logs", "eventos.jsonl")
_antes = os.path.getsize(_real) if os.path.exists(_real) else 0
ACT._escribir(ACT.EN_CURSO, {"desde": "1.0.0", "hacia": "9.9.9", "inicio": time.time() - 99999})
ACT._escribir(ACT.PENDIENTE, {"version": "9.9.9", "cuando": time.time() - 5})
ACT.recuperar_si_quedo_a_medias()
_despues = os.path.getsize(_real) if os.path.exists(_real) else 0
ok(_antes == _despues,
   "simular un fallo NO escribe en el registro real (lo haría investigar una falla inventada)")
ok(os.path.exists(LOG.ARCHIVO), "…queda en el registro de juguete, que es donde tiene que ir")

shutil.rmtree(TMP, ignore_errors=True)
print()
if fallos:
    print(f"  {len(fallos)} FALLO(S) — una actualización buena podría marcarse como fallida:")
    for f in fallos:
        print("   · " + f)
    sys.exit(1)
print("  OK: el servidor espera a que la versión nueva esté en disco, y un reinicio en el medio")
print("      no arruina una actualización que está saliendo bien.")
