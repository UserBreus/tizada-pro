# -*- coding: utf-8 -*-
"""CORTE POR BYTES de las capas OCG de una página.

Por qué existe (2026-09-15, ver changelog 457 del mapa): un molde con el diseño adentro trae UNA
capa por talle y **el dibujo entero repetido en cada una** — la CAMISETA real del usuario son
2.350.680 operadores en una sola página, 61,4 MB descomprimidos, y **un talle es el 5 % de eso**.
Para quedarse con un talle, el desplegado parseaba la mesa ENTERA y la recorría veinte veces:
el pico de memoria de un solo worker llegaba a **4.547 MB**, y el alta lanza hasta 9 o 12 workers.

La idea: el content-stream marca cada capa con `/OC /MCn BDC … EMC`. Encontrar esos marcadores es
un **escaneo de bytes**; parsear es construir 2,35 M de objetos Python. Cortando primero y
parseando después **sólo el trozo del talle**, el pico baja a **420 MB** (medido, −91 %).

🔴 ESTE MÓDULO NO DECIDE NADA SOBRE EL DIBUJO. Sólo dice **dónde empieza y dónde termina** cada
capa. Quién se queda y quién se va lo siguen decidiendo `molde_real._saltar_bloques` /
`_raspar_instrucciones`, con el trozo como entrada en vez de la mesa entera.

🔴 Y SI NO PUEDE GARANTIZAR EL CORTE, DEVUELVE `None` y el que llama sigue por el camino de
siempre. Se verifica reconstruyendo: los trozos pegados tienen que dar el stream original **byte a
byte**. Un molde con una estructura que no se entienda no se procesa «a medias»: se procesa como
antes.
"""
import re

import pikepdf

# 🔴 DOS BARRIDOS, NO UNO. Un solo regex que busque marcas Y `q`/`Q` en los 61 MB crea ~800.000
# objetos `Match` y cuesta 5 s. Las MARCAS son 40 en todo el archivo: se buscan con un patrón
# propio (milisegundos) y el balance de `q`/`Q` se cuenta con `findall` sobre cada bloque, que
# corre entero en C.
_RX_MARCAS = re.compile(
    rb"/OC\s*(/[^\s/\[\]<>(){}%]+)\s*(BDC)"       # 1,2: apertura de capa con nombre
    rb"|(?<![\w.])(BDC|BMC|EMC)(?![\w.])"          # 3: cualquier otra marca
)
_RX_QQ = re.compile(rb"(?<![\w.])([qQ])(?![\w.])")
_RX_BTET = re.compile(rb"(?<![\w.])(BT|ET)(?![\w.])")


def contenido_crudo(pag):
    """Los bytes del content-stream de una página (uno o varios streams, unidos por '\\n')."""
    c = pag.obj.get("/Contents") if hasattr(pag, "obj") else pag.get("/Contents")
    if c is None:
        return b""
    if isinstance(c, pikepdf.Array):
        return b"\n".join(s.read_bytes() for s in c)
    return c.read_bytes()


def _nombres_de(marca, pag, norm):
    """El/los nombre(s) de capa de un `/MCn`, resueltos por el /Properties de la página."""
    try:
        props = (pag.obj.get("/Resources") or {}).get("/Properties") or {}
        obj = props.get(marca.decode("latin-1"))
        if obj is None:
            return set()
        t = obj.get("/Type")
        if t == pikepdf.Name("/OCG"):
            return {norm(str(obj.get("/Name")))}
        if t == pikepdf.Name("/OCMD"):
            ocgs = obj.get("/OCGs")
            if isinstance(ocgs, pikepdf.Array):
                return {norm(str(o.get("/Name"))) for o in ocgs}
            if ocgs is not None:
                return {norm(str(ocgs.get("/Name")))}
    except Exception:
        pass
    return set()


def cortar(pag, norm=None):
    """Ubica por bytes los bloques `/OC … BDC … EMC` de PRIMER nivel del content-stream.

    Devuelve `{"crudo", "trozos"}`; `trozos` es la lista EN ORDEN de
    `(nombres|None, bytes, sobras, balanceado)`:
      · `nombres` = capas del bloque; `None` para lo que está fuera de toda capa.
      · `balanceado` = el bloque se puede sacar ENTERO (no deja estado gráfico abierto). Si es
        False, el bloque viaja siempre — como en `molde_real._saltar_bloques`.
      · `sobras` = para un bloque que viaja siempre, los tramos `(ini, fin)` internos que SÍ se
        pueden descartar (grupos `q … Q` completos y sin marcas colgando: no dejan estado).
    O `None` si el corte no se puede garantizar.
    """
    if norm is None:
        from molde_real import _norm_capa as norm
    data = contenido_crudo(pag)
    if not data:
        return None

    # ── 1) las marcas: dónde empieza y termina cada bloque de primer nivel ──────────────────
    raiz = []                 # [(ini, fin, marca_oc|None)]
    pila = []                 # [(ini, marca)]
    for m in _RX_MARCAS.finditer(data):
        if m.group(2):                                   # /OC /MCn BDC
            pila.append((m.start(), m.group(1)))
        elif m.group(3) in (b"BDC", b"BMC"):
            pila.append((m.start(), None))
        else:                                            # EMC
            if not pila:
                return None
            ini, marca = pila.pop()
            if not pila:
                raiz.append((ini, m.end(), marca))
    if pila:
        return None
    oc = [e for e in raiz if e[2] is not None]
    if len(oc) < 2:
        return None                                      # sin capas que separar, no hay nada que ganar

    # ── 2) el balance de q/Q de cada bloque (contado en C) ─────────────────────────────────
    trozos = []
    pos = 0
    for ini, fin, marca in oc:
        if ini > pos:
            trozos.append((None, data[pos:ini], (), True))
        b = data[ini:fin]
        # UNA sola pasada para contar `q` y `Q` (dos regex sobre los 61 MB costaban 3,8 s; una
        # sola, 1,7). El `findall` corre entero en C y el conteo del resultado también.
        _qq = _RX_QQ.findall(b)
        balanceado = _qq.count(b"q") == _qq.count(b"Q")
        nombres = _nombres_de(marca, pag, norm)
        # 🔴 UN BLOQUE QUE ABRE UN ESTADO Y NO LO CIERRA NO SE PUEDE SACAR ENTERO: lo que viene
        # después lo hereda (en la CAMISETA real, el primer talle deja un recorte abierto que
        # abarca a los otros 19). Es la misma regla que `molde_real._saltar_bloques`. Viaja
        # siempre — pero de adentro se pueden descartar sus grupos `q … Q` completos, que son
        # puro dibujo y no dejan estado.
        trozos.append((nombres, b, () if balanceado else _grupos_qq(b), balanceado))
        pos = fin
    if pos < len(data):
        trozos.append((None, data[pos:], (), True))
    # VERIFICACIÓN de que no se perdió ni se duplicó nada. Se comparan LARGOS, no el contenido:
    # pegar los trozos para compararlos copiaba los 61 MB otra vez (1 s por nada), y los tramos
    # salen de cortar el mismo buffer en posiciones contiguas — si los largos dan, son iguales.
    if sum(len(t[1]) for t in trozos) != len(data):
        return None
    return {"crudo": data, "trozos": trozos}


def _grupos_qq(b):
    """Los tramos `q … Q` de primer nivel de `b` que además no dejan marcas ni texto abiertos.

    Un `q … Q` completo devuelve TODO el estado gráfico (color, recorte, transformación): sacarlo
    no puede cambiar lo que viene después. Lo que `q`/`Q` **no** cierra es un bloque de contenido
    marcado (`BDC`/`EMC`) ni uno de texto (`BT`/`ET`) — por eso se cuentan los tres.
    """
    marcas = []
    for m in _RX_MARCAS.finditer(b):
        marcas.append((m.start(), m.end(), -1 if (m.group(3) == b"EMC") else 1))
    for m in _RX_BTET.finditer(b):
        marcas.append((m.start(), m.end(), -1 if m.group(1) == b"ET" else 1))
    marcas.sort()
    out, pila, prof = [], [], 0
    im, nm_ = 0, len(marcas)
    saldo_marcas = 0
    for m in _RX_QQ.finditer(b):
        while im < nm_ and marcas[im][0] < m.start():
            saldo_marcas += marcas[im][2]; im += 1
        if m.group(1) == b"q":
            pila.append((m.start(), saldo_marcas)); prof += 1
        else:
            prof -= 1
            if prof < 0:
                return ()                                # desbalanceado: no se poda nada
            ini, saldo0 = pila.pop() if pila else (None, 0)
            if ini is not None and not pila and saldo0 == saldo_marcas:
                out.append((ini, m.end()))
    # Que al final quede un `q` sin cerrar es justamente el caso de este bloque (por eso viaja
    # siempre): los grupos COMPLETOS que se encontraron antes valen igual.
    return tuple(out)


def capas(corte):
    """Los nombres de capa (normalizados) que el corte encontró, en orden de aparición."""
    out = []
    for nombres, _b, _s, _bal in corte["trozos"]:
        for x in sorted(nombres or ()):
            if x not in out:
                out.append(x)
    return out


def solo(corte, objetivo, podar_sobras=True):
    """Los bytes de la página conservando SÓLO los bloques de `objetivo` (nombres ya
    normalizados), lo que está fuera de las capas y los bloques que no se pueden sacar enteros.

    `podar_sobras=True` además descarta, dentro de esos bloques que viajan siempre, sus grupos
    `q … Q` completos: es dibujo de OTRO talle que el recorrido de siempre iba a vaciar igual
    (deja sus `m`/`l`/`c` sin pintar). Sacarlo por bytes ahorra parsearlo — y de paso la página
    del talle queda sin operadores muertos, que el RIP igual tenía que leer.
    Con `podar_sobras=False` el resultado es byte a byte el mismo que sin cortar.
    """
    obj = {objetivo} if isinstance(objetivo, str) else set(objetivo)
    partes = []
    for nombres, b, sobras, balanceado in corte["trozos"]:
        es_mio = nombres is not None and bool(obj & nombres)
        if nombres is not None and balanceado and not es_mio:
            continue                                     # capa de otro talle: se saca entera
        if sobras and podar_sobras and not es_mio:
            # bloque que viaja siempre pero NO es el talle pedido: se le saca el dibujo
            pos = 0
            for a, z in sobras:
                if a > pos:
                    partes.append(b[pos:a])
                pos = z
            partes.append(b[pos:])
            continue
        partes.append(b)
    return b"".join(partes)


def instrucciones(datos):
    """Parsea un trozo de content-stream suelto y devuelve sus instrucciones.

    Va sobre un PDF de descarte para no crear objetos en el archivo del usuario.
    """
    tmp = pikepdf.Pdf.new()
    try:
        st = tmp.make_stream(datos)
        return list(pikepdf.parse_content_stream(st))
    finally:
        tmp.close()
