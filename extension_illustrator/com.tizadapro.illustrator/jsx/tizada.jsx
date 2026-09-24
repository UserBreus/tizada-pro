// TIZADA PRO — arma la PLANTILLA en Illustrator (ExtendScript = JavaScript viejo, ES3: nada de
// let/const/flechas/forEach). Lo llama el puente (`js/puente.js`) con el plan que calculó TIZADA
// en el navegador (`frontend/src/motor/molde/illustrator.js → planIllustrator`).
//
// Qué arma (lo que el motor espera leer del arte):
//   · UNA MESA DE TRABAJO POR PIEZA, del tamaño de la caja del diseño y con el nombre de la mesa
//     («Frente», «#M Frente», «#S-XL Frente»);
//   · las CAPAS, de abajo hacia arriba: diseño · Editable … · personalización (Nombre, Número…) ·
//     guias (bloqueada);
//   · en «guias», el CONTORNO de cada pieza centrado en su mesa, convertido en GUÍA de Illustrator,
//     y su NOMBRE como texto vivo arriba a la izquierda de la mesa (con ese texto el motor asigna
//     cada mesa a su pieza; por eso es texto y no guía);
//   · en «diseño», el FONDO rojo clarito de cada mesa (el color viene en el plan).
// Las mesas quedan acomodadas como las piezas en el molde (lo calcula USER PRO).
// Coordenadas del plan: puntos, origen arriba a la izquierda, «y» hacia abajo.
// Al final GUARDA el documento donde diga el plan (`guardarEn`: el nombre del molde y la variable),
// como .ai con compatibilidad PDF (la que lee el sistema al subir el arte).
// Devuelve «OK:<mesas>:<método>:<1 si se guardó>:<nombres que no se pudieron escribir>» o
// «ERROR:<motivo>».

function tizadaArmar(plan) {
    var cs0 = app.coordinateSystem;
    var ui0 = app.userInteractionLevel;
    try {
        app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
        app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;

        // El documento nace con una mesa CHICA y todo el dibujo se CENTRA sobre ella: la mesa con
        // que nace un documento queda en el centro del lienzo de Illustrator, así lo armado queda
        // lejos de los bordes del lienzo (pegado al borde, Illustrator falla con «PARM»).
        // (en Illustrator la «y» crece hacia arriba: arriba > abajo)
        var doc = app.documents.add(DocumentColorSpace.CMYK, 1000, 1000);
        var r0 = doc.artboards[0].artboardRect;
        var L = (r0[0] + r0[2]) / 2 - plan.ancho / 2;
        var T = (r0[1] + r0[3]) / 2 + plan.alto / 2;
        var X = function (x) { return L + x; };
        var Y = function (y) { return T - y; };

        // ── capas, de abajo hacia arriba (la primera reusa la «Capa 1» del documento nuevo) ──
        var capas = [];
        var i, j;
        for (i = 0; i < plan.capas.length; i++) {
            var c = plan.capas[i];
            var lay = (i === 0) ? doc.layers[0] : doc.layers.add();
            if (i > 0) { try { lay.zOrder(ZOrderMethod.BRINGTOFRONT); } catch (e0) { } }
            lay.name = c.nombre;
            var rgb = new RGBColor();
            rgb.red = c.color[0]; rgb.green = c.color[1]; rgb.blue = c.color[2];
            lay.color = rgb;
            capas.push(lay);
        }

        // ── una mesa de trabajo por pieza ──
        for (i = 0; i < plan.mesas.length; i++) {
            var m = plan.mesas[i];
            var rect = [X(m.rect[0]), Y(m.rect[1]), X(m.rect[2]), Y(m.rect[3])];
            var ab;
            if (i === 0) { ab = doc.artboards[0]; ab.artboardRect = rect; }
            else { ab = doc.artboards.add(rect); }
            ab.name = m.nombre;
        }

        var negro = new CMYKColor();
        negro.cyan = 0; negro.magenta = 0; negro.yellow = 0; negro.black = 100;

        // ── el fondo de cada mesa (rojo clarito, el color viene en el plan), en «diseño» ──
        for (i = 0; i < (plan.fondos || []).length; i++) {
            var f = plan.fondos[i];
            var fr = capas[f.capa].pathItems.rectangle(Y(f.rect[1]), X(f.rect[0]), f.rect[2] - f.rect[0], f.rect[3] - f.rect[1]);
            var gris = new CMYKColor();
            gris.cyan = f.color[0]; gris.magenta = f.color[1]; gris.yellow = f.color[2]; gris.black = f.color[3];
            fr.stroked = false;
            fr.filled = true;
            fr.fillColor = gris;
            fr.name = 'fondo';
        }

        // ── los contornos: de una sola vez importando el SVG; si no se puede, punto por punto ──
        var metodo = 'ninguno';
        if (plan.caminos.length) {
            var capaGuias = capas[plan.caminos[0].capa];
            var hechos = [];
            if (plan.svgArchivo && tizadaImportarSvg(plan, capaGuias, L, T, negro, hechos)) {
                metodo = 'svg';
            } else {
                hechos = [];
                for (i = 0; i < plan.caminos.length; i++) tizadaDibujarCamino(plan.caminos[i], capas, X, Y, hechos);
                metodo = 'puntos';
            }
            // el molde como GUÍAS de Illustrator (no se imprimen, no se seleccionan sin querer)
            if (plan.guias) {
                for (i = 0; i < hechos.length; i++) { try { hechos[i].guides = true; } catch (eg) { } }
            }
        }

        // ── el nombre de cada mesa, como texto vivo, arriba a la izquierda de su mesa ──
        // (el plan da la LÍNEA BASE del texto, ya adentro de la mesa)
        // Un nombre que Illustrator no acepta NO corta todo el armado: se reintenta con el tamaño de
        // letra de siempre y, si igual falla, se sigue con las demás y se cuenta (va en la respuesta).
        var textosFallidos = 0;
        for (i = 0; i < plan.textos.length; i++) {
            var t = plan.textos[i];
            var tf = null;
            try {
                tf = capas[t.capa].textFrames.pointText([X(t.x), Y(t.y)]);
                tf.contents = t.t || 'Pieza';
                var ca = tf.textRange.characterAttributes;
                try { ca.size = Math.max(1, Math.min(1000, t.tam)); } catch (es) { }
                ca.fillColor = negro;
                tf.textRange.paragraphAttributes.justification = Justification.LEFT;
                // el TÍTULO del talle va como VECTOR (contornos), no como texto: texto vivo sólo
                // son los nombres de las mesas, que es lo que lee el sistema al subir el arte
                if (t.vector) { try { tf.createOutline(); } catch (eo) { } }
            } catch (et) {
                textosFallidos++;
            }
        }

        // ── al final: bloquear lo que va bloqueado y dejar al diseñador parado en «diseño» ──
        for (j = 0; j < plan.capas.length; j++) capas[j].locked = !!plan.capas[j].bloqueada;
        try { doc.activeLayer = capas[plan.activa] || capas[0]; } catch (e1) { }
        try { doc.artboards.setActiveArtboardIndex(0); } catch (e2) { }
        try { app.executeMenuCommand('fitall'); } catch (e3) { }
        var guardado = '0';
        if (plan.guardarEn) {
            try {
                var op = new IllustratorSaveOptions();
                op.pdfCompatible = true;
                doc.saveAs(new File(plan.guardarEn), op);
                guardado = '1';
            } catch (es) { guardado = '0'; }
        }
        try { BridgeTalk.bringToFront('illustrator'); } catch (e4) { }

        return 'OK:' + plan.mesas.length + ':' + metodo + ':' + guardado + ':' + textosFallidos;
    } catch (e) {
        return 'ERROR:' + (e.message || String(e)) + (e.line ? ' (linea ' + e.line + ')' : '');
    } finally {
        try { app.coordinateSystem = cs0; } catch (e5) { }
        try { app.userInteractionLevel = ui0; } catch (e6) { }
    }
}

// Importa el SVG de los contornos (uno solo, del tamaño del lienzo) y lo ubica por el rectángulo de
// referencia `tizada_ref` (sin relleno ni trazo, exactamente del tamaño del lienzo): con él se sabe
// la escala y el lugar exactos. Si no aparece, NO se adivina: se descarta y se dibuja punto por punto.
function tizadaImportarSvg(plan, capa, L, T, negro, hechos) {
    var g = null;
    try {
        g = capa.groupItems.createFromFile(new File(plan.svgArchivo));
        var ref = tizadaBuscarRef(g, plan.ancho / plan.alto);
        if (!ref) { g.remove(); return false; }
        var rb = ref.geometricBounds;               // [izq, arriba, der, abajo]
        var s = plan.ancho / (rb[2] - rb[0]);
        if (Math.abs(s - 1) > 0.0005) {
            g.resize(s * 100, s * 100, true, true, true, true, 100, Transformation.TOPLEFT);
            rb = ref.geometricBounds;
        }
        g.translate(L - rb[0], T - rb[1]);
        ref.remove();
        tizadaPintar(g, negro, hechos);
        return true;
    } catch (e) {
        try { if (g) g.remove(); } catch (e2) { }
        return false;
    }
}

function tizadaBuscarRef(cont, proporcion) {
    var items = cont.pageItems;
    for (var i = 0; i < items.length; i++) {
        var it = items[i];
        if (it.typename === 'GroupItem') {
            var r = tizadaBuscarRef(it, proporcion);
            if (r) return r;
        } else if (it.typename === 'PathItem') {
            if (it.name === 'tizada_ref') return it;
            if (!it.filled && !it.stroked && it.height > 0 && Math.abs(it.width / it.height - proporcion) < 0.01) return it;
        }
    }
    return null;
}

// `hechos` junta los trazados (para volverlos guías). Un trazado compuesto no puede ser guía: se
// suelta en trazados sueltos (el plan ya manda cada sub-camino aparte, esto es por las dudas).
function tizadaPintar(cont, negro, hechos) {
    var items = cont.pageItems;
    var i, it;
    var compuestos = [];
    for (i = 0; i < items.length; i++) {
        it = items[i];
        if (it.typename === 'GroupItem') tizadaPintar(it, negro, hechos);
        else if (it.typename === 'CompoundPathItem') compuestos.push(it);
        else if (it.typename === 'PathItem') { tizadaTrazo(it, negro); hechos.push(it); }
    }
    for (i = 0; i < compuestos.length; i++) {
        var cp = compuestos[i];
        for (var j = cp.pathItems.length - 1; j >= 0; j--) {
            var suelto = cp.pathItems[j];
            try { suelto.move(cont, ElementPlacement.PLACEATEND); } catch (em) { }
            tizadaTrazo(suelto, negro);
            hechos.push(suelto);
        }
        try { if (cp.pathItems.length === 0) cp.remove(); } catch (er) { }
    }
}

function tizadaTrazo(p, negro) {
    p.filled = false;
    p.stroked = true;
    p.strokeColor = negro;
    p.strokeWidth = 1;
}

// Un contorno dibujado punto por punto (lo que se usa si la importación del SVG no anduvo).
// Cada punto: [x, y, manija de entrada x, y, manija de salida x, y]. Cada sub-camino es un trazado
// SUELTO (no compuesto): así se puede volver guía.
function tizadaDibujarCamino(k, capas, X, Y, hechos) {
    var lay = capas[k.capa];
    var negro = new CMYKColor();
    negro.black = k.color[3]; negro.cyan = k.color[0]; negro.magenta = k.color[1]; negro.yellow = k.color[2];
    for (var a = 0; a < k.sub.length; a++) {
        var sp = k.sub[a];
        var pi = lay.pathItems.add();
        var anc = [];
        var b;
        for (b = 0; b < sp.p.length; b++) anc.push([X(sp.p[b][0]), Y(sp.p[b][1])]);
        pi.setEntirePath(anc);
        // sólo los puntos con curva: en los rectos las manijas ya quedan sobre el punto
        for (b = 0; b < sp.p.length; b++) {
            var q = sp.p[b];
            if (q[2] !== q[0] || q[3] !== q[1] || q[4] !== q[0] || q[5] !== q[1]) {
                var pp = pi.pathPoints[b];
                pp.leftDirection = [X(q[2]), Y(q[3])];
                pp.rightDirection = [X(q[4]), Y(q[5])];
            }
        }
        pi.closed = sp.c;
        tizadaTrazo(pi, negro);
        pi.strokeWidth = k.ancho;
        hechos.push(pi);
    }
}
