# -*- coding: utf-8 -*-
"""ESPACIO DE TRABAJO REUSABLE PARA LOS CONTRATOS DEL CAMINO B.

🔴 POR QUÉ EXISTE (2026-09-15). Tres contratos —`verificar_desplegado`, `verificar_hoja_compartida`
y `verificar_alta_con_diseno`— empiezan igual: copian el molde REAL del usuario (123 MB) a un
temporal y lo DESPLIEGAN entero. Eso son ~90 s por contrato, cada vez, y los dejaba fuera del tope
de la tanda rápida. Regla del usuario: *«pone tiempo limite, si ves que demora mas de tantos
minutos paralo y arreglalo»* — y arreglarlo es **no rehacer un trabajo que ya está hecho**, no
subirle el tope.

El despliegue se guarda UNA vez en el temporal del sistema, con clave = sha1 del archivo + versión
del formato. Las corridas siguientes se llevan una COPIA de ese espacio (unos segundos) y pueden
escribir encima sin ensuciar el guardado. Si el .ai cambia, el sha1 cambia y se rehace solo.
`VERIF_SIN_CACHE=1` fuerza rehacerlo.

⚠️ NO toca nada del usuario: sólo LEE su archivo y trabaja sobre copias en el temporal.
"""
import hashlib
import os
import shutil
import tempfile
import time

VERSION = "v1"          # subir esto invalida todo lo guardado


def _clave(origen):
    """sha1 del archivo por trozos (leer 123 MB enteros para una clave cuesta más que la clave)."""
    h = hashlib.sha1()
    tam = os.path.getsize(origen)
    h.update(str(tam).encode())
    with open(origen, "rb") as f:
        h.update(f.read(1 << 20))
        if tam > (2 << 20):
            f.seek(tam - (1 << 20))
            h.update(f.read(1 << 20))
    return h.hexdigest()[:16]


def espacio_desplegado(origen, prefijo, procesos=None, alta=None):
    """`(carpeta, copia, alta, reusado)`: una carpeta NUEVA con `plantilla.ai` y su `desplegado/`.

    `alta` = la función que despliega (por defecto `piezas_con_diseno.alta_molde_con_diseno`); se
    la puede pasar para no importar el módulo dos veces. El que llama borra la carpeta cuando
    termina; el guardado en el temporal se queda para la próxima corrida.
    """
    import piezas_con_diseno as PD
    alta = alta or PD.alta_molde_con_diseno
    guardado = os.path.join(tempfile.gettempdir(),
                            f"contrato_molde_b_{_clave(origen)}_{VERSION}")
    listo = os.path.join(guardado, ".listo")
    reusado = os.path.exists(listo) and not os.environ.get("VERIF_SIN_CACHE")
    if not reusado:
        shutil.rmtree(guardado, ignore_errors=True)
        os.makedirs(guardado, exist_ok=True)
        t = time.time()
        print(f"    desplegando el molde ({os.path.getsize(origen)/1e6:.0f} MB) — "
              f"la primera vez tarda, después se reusa…", flush=True)
        shutil.copy2(origen, os.path.join(guardado, "plantilla.ai"))
        alta(os.path.join(guardado, "plantilla.ai"),
             procesos=procesos or max(2, (os.cpu_count() or 4) - 1))
        open(listo, "w").close()
        print(f"    desplegado en {time.time() - t:.0f}s", flush=True)
    carpeta = tempfile.mkdtemp(prefix=prefijo)
    # Copiar el espacio ya desplegado (unos segundos) en vez de volver a desplegarlo (~90 s).
    for n in os.listdir(guardado):
        if n == ".listo":
            continue
        o, d = os.path.join(guardado, n), os.path.join(carpeta, n)
        (shutil.copytree if os.path.isdir(o) else shutil.copy2)(o, d)
    copia = os.path.join(carpeta, "plantilla.ai")
    # El alta se vuelve a pedir sobre la copia: con el `desplegado/` ya al lado no lo rehace,
    # sólo lo LEE — que es justamente lo que el contrato 4 quiere comprobar.
    datos = alta(copia, procesos=procesos or max(2, (os.cpu_count() or 4) - 1))
    if reusado:
        print("    (molde desplegado reutilizado de una corrida anterior)", flush=True)
    return carpeta, copia, datos, reusado
