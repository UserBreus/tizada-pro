# -*- coding: utf-8 -*-
"""EL REGISTRO DEL SISTEMA — qué pasó, cuándo y POR QUÉ.

── POR QUÉ EXISTE ────────────────────────────────────────────────────────────────────────────────
El 2026-09-01 una actualización al servidor publicado dijo «falló» y en pantalla no había forma de
saber más: el motivo estaba en un archivo del VPS (`_actualizacion/actualizador_log.txt`), al que
sólo se llega por SSH. Todo el diagnóstico dependió de mirar el código y atar cabos por las horas.
Pedido del usuario: *«agregá logs a este sistema en la parte de configuración para poder ver las
fallas y que deje registrado el por qué»*.

── QUÉ GUARDA ────────────────────────────────────────────────────────────────────────────────────
Un evento por línea (JSON), en `logs/eventos.jsonl`:

    cuando   marca de tiempo
    tipo     "error" | "aviso" | "info"
    area     de qué parte del sistema («actualizacion», «pedido», «servidor»…)
    que      el título, en una línea y en criollo
    porque   EL MOTIVO: la causa, con nombres y números. Es lo que hoy no quedaba en ningún lado
    datos    lo que haga falta para entenderlo (versión, archivo, cuánto tardó…)

🔴 REGLAS DURAS:
  · **el registro NUNCA rompe lo que estaba registrando**: todo va dentro de try/except y, si algo
    sale mal escribiendo, se sigue como si nada;
  · **no guarda datos del usuario** (ni moldes, ni pedidos, ni nombres de prendas): sólo qué pasó;
  · **se escribe con `os.replace` cuando rota** (nunca un archivo a medio escribir) y se le pone un
    tope de tamaño, para que un error repetido no llene el disco de un servidor de producción.
"""
import io
import os
import json
import time
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
# `TIZADA_LOGS`: la aplicación de escritorio manda el registro a la carpeta de datos del usuario
# (la del programa instalado no es lugar para escribir). Los workers del pool la heredan por entorno.
CARPETA = os.environ.get("TIZADA_LOGS") or os.path.join(AQUI, "logs")
ARCHIVO = os.path.join(CARPETA, "eventos.jsonl")
VIEJO = os.path.join(CARPETA, "eventos.anterior.jsonl")

MAX_BYTES = 2 * 1024 * 1024      # 2 MB y rota: alcanza para miles de eventos
MAX_DETALLE = 4000               # un traceback entero no aporta más que su final

_candado = threading.Lock()
TIPOS = ("error", "aviso", "info")


def _rotar_si_hace_falta():
    try:
        if os.path.exists(ARCHIVO) and os.path.getsize(ARCHIVO) > MAX_BYTES:
            os.replace(ARCHIVO, VIEJO)          # atómico: nunca quedan dos a medias
    except OSError:
        pass


def evento(tipo, area, que, porque="", **datos):
    """Deja constancia de algo. Devuelve el evento (o None si no se pudo escribir: nunca explota)."""
    try:
        t = tipo if tipo in TIPOS else "info"
        ev = {"cuando": time.time(), "tipo": t, "area": str(area or "sistema")[:40],
              "que": str(que or "")[:300], "porque": str(porque or "")[-MAX_DETALLE:]}
        if datos:
            # sólo lo que se pueda escribir como JSON: un objeto raro no puede tumbar el registro
            limpio = {}
            for k, v in datos.items():
                try:
                    json.dumps(v)
                    limpio[str(k)[:40]] = v
                except (TypeError, ValueError):
                    limpio[str(k)[:40]] = str(v)[:200]
            ev["datos"] = limpio
        with _candado:
            os.makedirs(CARPETA, exist_ok=True)
            _rotar_si_hace_falta()
            with io.open(ARCHIVO, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev
    except Exception:
        return None                             # el registro jamás rompe lo que estaba pasando


def error(area, que, porque="", **datos):
    return evento("error", area, que, porque, **datos)


def aviso(area, que, porque="", **datos):
    return evento("aviso", area, que, porque, **datos)


def info(area, que, porque="", **datos):
    return evento("info", area, que, porque, **datos)


def leer(limite=200, tipo=None, area=None, desde=None):
    """Los últimos eventos, del más nuevo al más viejo. `tipo`/`area` filtran; `desde` es una marca
    de tiempo (para traer sólo lo nuevo)."""
    filas = []
    orden = {}                                  # id(evento) → en qué lugar del archivo estaba
    for ruta in (VIEJO, ARCHIVO):               # el anterior y el actual: la rotación no esconde nada
        try:
            if not os.path.exists(ruta):
                continue
            with io.open(ruta, encoding="utf-8") as fh:
                for linea in fh:
                    linea = linea.strip()
                    if not linea:
                        continue
                    try:
                        ev = json.loads(linea)
                    except ValueError:
                        continue                # una línea rota no se lleva puesto el resto
                    orden[id(ev)] = len(filas)
                    filas.append(ev)
        except OSError:
            continue
    # 🔴 Se desempata por el lugar que ocupa en el archivo. Sin eso, dos eventos de la MISMA
    # centésima de segundo (el reloj de Windows tiene ese grano) salían en el orden en que se
    # escribieron, o sea al revés de lo que dice la pantalla: primero el más viejo.
    filas.sort(key=lambda e: ((e.get("cuando") or 0), orden.get(id(e), 0)), reverse=True)
    if tipo:
        filas = [e for e in filas if e.get("tipo") == tipo]
    if area:
        filas = [e for e in filas if e.get("area") == area]
    if desde:
        filas = [e for e in filas if (e.get("cuando") or 0) > float(desde)]
    return filas[:max(1, int(limite))]


def resumen():
    """Para el cartel de la pantalla: cuántos errores hay y cuándo fue el último."""
    ultimos = leer(500)
    errores = [e for e in ultimos if e.get("tipo") == "error"]
    return {"total": len(ultimos), "errores": len(errores),
            "ultimo_error": (errores[0] if errores else None)}


def limpiar():
    """Vacía el registro (lo pide la pantalla con un botón). Los archivos, no la carpeta."""
    for f in (ARCHIVO, VIEJO):
        try:
            os.remove(f)
        except OSError:
            pass


# ══════════════════════════════════════════════════════════════════════════════════════════════
# LA CONSOLA DEL SERVIDOR — lo mismo que se ve en la ventana negra, pero guardado
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Pedido del usuario (2026-09-01): «los logs deben ser todo lo que abriría en un PowerShell; y lo
# que falle debe quedar en un ARCHIVO, no en la base de datos, con fecha y hora real».
#
# Hasta ahora esa salida existía sólo mientras la ventana estuviera abierta: si el servidor corría
# como servicio (o en el VPS, donde no hay ventana), TODO lo que imprimía se perdía. Con esto, cada
# línea que el servidor escribe queda en `logs/consola.log` con su fecha y hora adelante.
#
# 🔴 NO es la base de datos ni la toca: es un archivo de texto plano que se puede abrir con
#    cualquier cosa, y que rota solo para no llenar el disco.
CONSOLA = os.path.join(CARPETA, "consola.log")
CONSOLA_VIEJA = os.path.join(CARPETA, "consola.anterior.log")
MAX_CONSOLA = 4 * 1024 * 1024

_candado_consola = threading.Lock()
_espejado = False


def _rotar_consola():
    try:
        if os.path.exists(CONSOLA) and os.path.getsize(CONSOLA) > MAX_CONSOLA:
            os.replace(CONSOLA, CONSOLA_VIEJA)
    except OSError:
        pass


class _Espejo(object):
    """Deja pasar todo a la ventana de siempre Y lo copia al archivo, línea por línea, con la hora.

    Va por línea entera (no por `write`) porque un solo `print` puede llegar en varios pedazos y
    marcarlos todos con la hora dejaría el archivo ilegible."""

    def __init__(self, salida, marca=""):
        self._salida = salida
        self._marca = marca
        self._resto = ""

    def write(self, texto):
        try:
            if self._salida is not None:
                self._salida.write(texto)
        except Exception:
            pass                                  # que la ventana falle no puede frenar al servidor
        try:
            self._guardar(texto)
        except Exception:
            pass                                  # ni que falle el archivo
        return len(texto or "")

    def _guardar(self, texto):
        self._resto += texto or ""
        if "\n" not in self._resto:
            return                                # todavía no hay línea entera
        partes = self._resto.split("\n")
        self._resto = partes.pop()                # lo que quedó a medias espera al próximo write
        ahora = time.strftime("%d/%m/%Y %H:%M:%S")
        with _candado_consola:
            os.makedirs(CARPETA, exist_ok=True)
            _rotar_consola()
            with io.open(CONSOLA, "a", encoding="utf-8", errors="replace") as fh:
                for linea in partes:
                    fh.write(u"%s %s%s\n" % (ahora, self._marca, linea.rstrip("\r")))

    def flush(self):
        try:
            if self._salida is not None:
                self._salida.flush()
        except Exception:
            pass

    def isatty(self):
        try:
            return bool(self._salida) and self._salida.isatty()
        except Exception:
            return False

    def fileno(self):
        # werkzeug y algunas librerías lo piden. Sin ventana de verdad (arranque con `pythonw`,
        # servicio) `self._salida` es None: hay que fallar como falla un flujo sin descriptor
        # —eso lo saben manejar— y no con un AttributeError, que nadie espera.
        if self._salida is None:
            raise io.UnsupportedOperation("no hay una salida de verdad detrás del espejo")
        return self._salida.fileno()

    def writelines(self, lineas):
        for l in lineas:
            self.write(l)

    def __getattr__(self, nombre):
        """Lo que el espejo no implementa, se lo pide a la salida de verdad.

        Sin esto, cualquiera que llamara algo normal de un flujo después de enganchar el espejo se
        comía un AttributeError: `sys.stdout.reconfigure(encoding='utf-8')` —la primera línea de
        casi todos los contratos `verificar_*.py`— reventaba apenas importaban `servidor`."""
        if nombre.startswith("_") or self._salida is None:
            raise AttributeError(nombre)
        return getattr(self._salida, nombre)

    @property
    def encoding(self):
        return getattr(self._salida, "encoding", "utf-8")


def espejar_consola():
    """Engancha el espejo. Se llama UNA vez, lo antes posible: lo que se imprima antes se pierde."""
    global _espejado
    if _espejado:
        return False
    import sys
    try:
        sys.stdout = _Espejo(sys.stdout)
        # Sin marca de «error» para stderr A PROPÓSITO: werkzeug escribe TODOS los pedidos por ahí,
        # también los que salieron bien. Marcarlos pintaba de rojo hasta un 200 y el archivo mentía.
        sys.stderr = _Espejo(sys.stderr)
        _espejado = True
        return True
    except Exception:
        return False


def leer_consola(limite=400, buscar=""):
    """Las últimas líneas de la consola, en orden (la más vieja arriba, como en la ventana)."""
    lineas = []
    for ruta in (CONSOLA_VIEJA, CONSOLA):          # la vieja primero: así el orden queda derecho
        try:
            if not os.path.exists(ruta):
                continue
            with io.open(ruta, encoding="utf-8", errors="replace") as fh:
                lineas.extend(fh.read().splitlines())
        except OSError:
            continue
    if buscar:
        b = str(buscar).lower()
        lineas = [l for l in lineas if b in l.lower()]
    n = max(1, min(5000, int(limite or 400)))
    return lineas[-n:]


def usar_carpeta(ruta):
    """Manda TODO el registro a otra carpeta (el sandbox de sólo lectura y los contratos).

    🔴 Existe para que nadie tenga que acordarse de las rutas una por una: apenas se agregó la
    consola, el sandbox — que las reasignaba a mano — siguió escribiéndola en la carpeta de verdad.
    Si mañana se suma otro archivo, se agrega acá y todos los que llaman quedan bien solos."""
    global CARPETA, ARCHIVO, VIEJO, CONSOLA, CONSOLA_VIEJA
    CARPETA = ruta
    ARCHIVO = os.path.join(ruta, "eventos.jsonl")
    VIEJO = os.path.join(ruta, "eventos.anterior.jsonl")
    CONSOLA = os.path.join(ruta, "consola.log")
    CONSOLA_VIEJA = os.path.join(ruta, "consola.anterior.log")
    return ruta


def limpiar_consola():
    for f in (CONSOLA, CONSOLA_VIEJA):
        try:
            os.remove(f)
        except OSError:
            pass
