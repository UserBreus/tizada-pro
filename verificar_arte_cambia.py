# CONTRATO — «cargo el arte y no se cambia» (MAPA 674).
#
# Al cargar un arte (o volver a cargarlo enseguida) el visor seguía mostrando el anterior hasta recargar:
#   · un dibujo que ya estaba en camino con el arte viejo llegaba DESPUÉS de vaciar el caché y se guardaba
#     con la clave de ahora (la clave no sabe de qué arte es);
#   · la segunda carga se «colgaba» de la pasada de la primera (`_asignEnCurso`, misma clave) y no dibujaba
#     nada nuevo;
#   · el hilo del molde se rearma con el arte nuevo y el dibujo que lo usaba salía «cancelado» → caía al
#     servidor → 409 («las piezas las arma tu computadora») → el visor se quedaba como estaba.
# Este contrato mira que las tres cosas sigan cerradas. Es estático (lee App.jsx): no toca datos.
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
app = open(os.path.join(AQUI, "frontend", "src", "App.jsx"), encoding="utf-8").read()
FALLOS = []


def ok(cond, msg):
    print(("  OK    " if cond else "  ❌    ") + msg)
    if not cond:
        FALLOS.append(msg)


print("1. el caché de las previas tiene GENERACIÓN: un dibujo de antes de un vaciado no se guarda")
ok("const _pvLimpiar = () => { _pvCache.current = {}; _pvGen.current++; };" in app,
   "vaciar el caché sube la generación")
_sueltos = [m.start() for m in re.finditer(r"_pvCache\.current = \{\}", app)]
_permitidos = app.count("_pvCache.current = {}; _pvGen.current++;") + app.count("length > 300) _pvCache.current = {};")
ok(len(_sueltos) == _permitidos, f"nadie vacía el caché sin subir la generación ({len(_sueltos) - _permitidos} sueltos)")
ok("if (gen != null && gen !== _pvGen.current) return;" in app, "`_pvGuardar` descarta lo de otra generación")
ok(app.count("_pvGuardar(") == len(re.findall(r"_pvGuardar\([^;]*?, (?:gen|_gen)\)", app)),
   "todo lo que guarda en el caché dice de qué generación es")

print("2. la pasada de «todos los talles» es de UNA generación")
ok("const _kEnCurso = `${pid}|${clave}|${dis}|${talles.join(',')}|${_gen}`;" in app,
   "un arte nuevo arranca otra pasada en vez de colgarse de la anterior")
ok("_vigente = () => _epoca === _pedidoEpoca.current && _gen === _pvGen.current;" in app,
   "la pasada vieja deja de dibujar en cuanto cambia el arte")
ok("const _kGuia = _pvKeyCon(mapeo, _guia, fuentesReempl);" in app, "la clave del talle guía se toma al ARRANCAR, no al terminar")

print("3. el visor: dos intentos en esta computadora antes del servidor, y el arte nuevo se pide solo")
ok("for (let _intento = 0; _intento < 2; _intento++) {" in app and "const _vale = () => req === _pvReq.current && gen === _pvGen.current;" in app,
   "si el hilo se rearmó (arte nuevo) se reintenta acá; nada viejo se muestra")
ok("_pvLimpiar(); _detArteCache.current = {}; _prefetchTok.current++; _pvReq.current++;" in app,
   "al cargar el arte se cortan los dibujos en curso")
ok("productosCat.activo, editorTfs, arteCargado]);" in app, "cada carga de arte vuelve a pedir el dibujo aunque el mapeo no cambie")

print("4. (MAPA 675) un contexto del arte POR CONFIGURACIÓN: dos dibujos a la vez no se pisan")
previa = open(os.path.join(AQUI, "frontend", "src", "motor", "arte", "previa.js"), encoding="utf-8").read()
worker = open(os.path.join(AQUI, "frontend", "src", "motor", "obrero.worker.js"), encoding="utf-8").read()
ok("const clave = `${pid}|${d.id}|previa|${huella(JSON.stringify(cfg))}`" in previa and "clave: `${pid}|${d.id}|previa`" not in previa,
   "la clave del contexto del visor lleva la huella de su configuración (antes uno por diseño, rearmado por cada uno)")
ok("m.previasEnUso.set(clave, (m.previasEnUso.get(clave) || 0) + 1)" in previa and "!(m.previasEnUso.get(k) > 0)" in previa,
   "se guardan los últimos y nunca se suelta uno que se está usando")
ok("async contexto_a_soltar({ clave })" in worker, "el hilo sabe soltar un contexto viejo (con sus bases)")
ok("if (d.solo_navegador) {" in app and "'El visor del arte no pudo dibujar este talle'" in app,
   "si igual falla, el aviso dice el motivo de ACÁ, no el «recargá la página» del servidor")

print()
print("FALLAS:" if FALLOS else "TODO OK", *FALLOS, sep="\n  · ")
sys.exit(1 if FALLOS else 0)
