/* USER PRO (TIZADA PRO) — el puente entre el navegador y Illustrator (corre dentro de Illustrator, CEP + Node).
 *
 * Escucha SOLO en 127.0.0.1:47850 (esta PC; nada de afuera llega): TIZADA, abierta en el navegador
 * de esta misma PC, le manda el PLAN de la plantilla ya calculado (`frontend/src/motor/molde/
 * illustrator.js → planIllustrator`) y acá se le pide a Illustrator que lo dibuje
 * (`jsx/tizada.jsx → tizadaArmar`).
 *
 * 🔴 SEGURIDAD: el script de Illustrator puede tocar archivos de la PC, así que lo que llega por la
 * red NUNCA se pega como código. Se valida campo por campo (`sanear`: sólo números y textos, con
 * topes) y se vuelve a escribir con JSON.stringify: el plan llega a Illustrator como DATO.
 */
/* global require, window */
(function () {
  'use strict'
  var PUERTO = 47850
  var VERSION = '1.25.0'
  var TOPE_CUERPO = 80 * 1024 * 1024
  var http = require('http')
  var fs = require('fs')
  var os = require('os')
  var path = require('path')

  // `contacto`: la última vez que USER PRO (una página del navegador, con su origen) habló con el
  // puente. Con eso el panel distingue «lista, esperando» de «conectado con USER PRO».
  var estado = { escuchando: false, error: null, ultima: null, log: [], contacto: null }
  var cola = Promise.resolve()

  function anotar(texto) {
    estado.log.unshift({ t: Date.now(), texto: texto })
    if (estado.log.length > 30) estado.log.length = 30
  }

  // LA RAM Y EL PROCESADOR DE ESTA PC (pedido del usuario 2026-09-24: el Monitor de USER PRO tiene
  // que mostrar lo que consume la computadora que lo abre). El navegador no deja leerlos; el puente
  // corre DENTRO de la PC, con Node: `os` los da. El % de procesador es contra la consulta anterior
  // (la primera vez, desde que arrancó la PC). Código para Node 8 (Illustrator 2020).
  var cpuAnt = null
  function sistemaAhora() {
    var cpus = os.cpus() || [], ocupado = 0, total = 0
    for (var i = 0; i < cpus.length; i++) {
      var t = cpus[i].times
      var tot = t.user + t.nice + t.sys + t.idle + t.irq
      total += tot
      ocupado += tot - t.idle
    }
    var pct = null
    if (cpuAnt && total > cpuAnt.total) pct = Math.round(1000 * (ocupado - cpuAnt.ocupado) / (total - cpuAnt.total)) / 10
    else if (total > 0) pct = Math.round(1000 * ocupado / total) / 10
    cpuAnt = { ocupado: ocupado, total: total }
    return { nucleos: cpus.length, cpu_pct: pct,
             ram_total_mb: Math.round(os.totalmem() / 1048576), ram_libre_mb: Math.round(os.freemem() / 1048576) }
  }

  function versionIllustrator() {
    try { return JSON.parse(window.__adobe_cep__.getHostEnvironment()).appVersion || '' } catch (e) { return '' }
  }

  function evalScript(src) {
    return new Promise(function (ok) { window.__adobe_cep__.evalScript(src, function (r) { ok(String(r)) }) })
  }

  // ── validación: sólo lo que el dibujo necesita, con tipos y topes ──
  function num(v) { var n = Number(v); if (!isFinite(n)) throw new Error('número inválido en el plan'); return n }
  function txt(v, tope) { return String(v == null ? '' : v).slice(0, tope || 200) }
  function lista(v, tope, que) {
    if (!Array.isArray(v)) throw new Error('falta ' + que + ' en el plan')
    if (v.length > tope) throw new Error('demasiados ' + que + ' (' + v.length + ')')
    return v
  }
  function sanear(p) {
    if (!p || typeof p !== 'object') throw new Error('el plan no es un objeto')
    var out = {
      titulo: txt(p.titulo, 120),
      archivo: nombreArchivo(p.archivo || p.titulo),
      ancho: num(p.ancho), alto: num(p.alto),
      activa: Math.max(0, Math.floor(num(p.activa || 0))),
      capas: [], mesas: [], caminos: [], textos: [], fondos: [],
      guias: !!p.guias,
    }
    if (out.ancho <= 0 || out.alto <= 0 || out.ancho > 16383 || out.alto > 16383) throw new Error('el lienzo no entra en Illustrator')
    lista(p.capas, 60, 'capas').forEach(function (c) {
      var col = lista(c.color || [128, 128, 128], 3, 'color')
      out.capas.push({ nombre: txt(c.nombre, 120), color: [num(col[0]), num(col[1]), num(col[2])], bloqueada: !!c.bloqueada })
    })
    if (!out.capas.length) throw new Error('el plan no trae capas')
    lista(p.mesas, 1000, 'mesas').forEach(function (m) {
      var r = lista(m.rect, 4, 'rect')
      out.mesas.push({ nombre: txt(m.nombre, 120), rect: [num(r[0]), num(r[1]), num(r[2]), num(r[3])] })
    })
    if (!out.mesas.length) throw new Error('el plan no trae mesas')
    var puntos = 0
    lista(p.caminos, 20000, 'caminos').forEach(function (k) {
      var col = lista(k.color || [0, 0, 0, 100], 4, 'color')
      var subs = lista(k.sub, 500, 'sub-caminos').map(function (sp) {
        var pts = lista(sp.p, 200000, 'puntos').map(function (q) {
          return [num(q[0]), num(q[1]), num(q[2]), num(q[3]), num(q[4]), num(q[5])]
        })
        puntos += pts.length
        return { p: pts, c: !!sp.c }
      })
      out.caminos.push({ capa: Math.floor(num(k.capa)), sub: subs, ancho: num(k.ancho || 1),
                         color: [num(col[0]), num(col[1]), num(col[2]), num(col[3])] })
    })
    if (puntos > 3000000) throw new Error('el plan trae demasiados puntos')
    lista(p.fondos || [], 1000, 'fondos').forEach(function (f) {
      var r = lista(f.rect, 4, 'rect'), col = lista(f.color || [0, 0, 0, 10], 4, 'color')
      out.fondos.push({ capa: Math.floor(num(f.capa)), rect: [num(r[0]), num(r[1]), num(r[2]), num(r[3])],
                        color: [num(col[0]), num(col[1]), num(col[2]), num(col[3])] })
    })
    lista(p.textos, 5000, 'textos').forEach(function (t) {
      out.textos.push({ capa: Math.floor(num(t.capa)), t: txt(t.t, 200), x: num(t.x), y: num(t.y), tam: num(t.tam || 12), vector: !!t.vector })
    })
    // el SVG de los contornos va a un ARCHIVO temporal (no al script): se importa de una vez
    out.svg = (typeof p.svg === 'string' && p.svg.length < 60 * 1024 * 1024 && p.svg.indexOf('<svg') >= 0) ? p.svg : null
    return out
  }

  // un nombre de archivo válido en Windows y en Mac (sin \ / : * ? " < > | ni caracteres de control)
  function nombreArchivo(v) {
    var n = String(v == null ? '' : v).replace(/[\\\/:*?"<>|\u0000-\u001f]/g, ' ').replace(/\s+/g, ' ').trim()
    n = n.replace(/[. ]+$/, '').slice(0, 100)
    return n || 'Plantilla'
  }

  // DÓNDE se guarda el documento: Documentos › USER PRO › Plantillas, con el nombre del molde y la
  // variable. Si ya hay uno con ese nombre NO se pisa: «… (2).ai», «… (3).ai».
  function rutaParaGuardar(nombre) {
    var carpeta = path.join(os.homedir(), 'Documents', 'USER PRO', 'Plantillas')
    // de a una carpeta y no con `{recursive: true}`: Illustrator 2020 trae Node 8, que no lo conoce
    // (llegó en Node 10.12) y sin la carpeta el documento quedaba sin guardar
    var partes = path.resolve(carpeta).split(path.sep), acum = ''
    for (var j = 0; j < partes.length; j++) {
      acum = j === 0 ? partes[0] + path.sep : path.join(acum, partes[j])
      if (partes[j] && !fs.existsSync(acum)) fs.mkdirSync(acum)
    }
    var ruta = path.join(carpeta, nombre + '.ai')
    for (var i = 2; fs.existsSync(ruta) && i < 1000; i++) ruta = path.join(carpeta, nombre + ' (' + i + ').ai')
    return ruta
  }

  // texto JavaScript seguro: JSON + todo lo que no es ASCII escapado (ExtendScript es ES3)
  function literal(o) {
    return JSON.stringify(o).replace(/[\u007f-\uffff]/g, function (c) {
      return '\\u' + ('0000' + c.charCodeAt(0).toString(16)).slice(-4)
    })
  }

  function armar(planCrudo) {
    var plan = sanear(planCrudo)
    var svgArchivo = null
    if (plan.svg) {
      svgArchivo = path.join(os.tmpdir(), 'tizada_guias_' + Date.now() + '_' + Math.floor(Math.random() * 1e6) + '.svg')
      fs.writeFileSync(svgArchivo, plan.svg, 'utf8')
    }
    delete plan.svg
    plan.svgArchivo = svgArchivo
    try { plan.guardarEn = rutaParaGuardar(plan.archivo) } catch (e) { plan.guardarEn = null }
    var t0 = Date.now()
    return evalScript('tizadaArmar(' + literal(plan) + ')').then(function (r) {
      if (svgArchivo) { try { fs.unlinkSync(svgArchivo) } catch (e) { /* nada */ } }
      if (r.indexOf('OK:') === 0) {
        var partes = r.slice(3).split(':')
        var res = { ok: true, mesas: Number(partes[0]) || plan.mesas.length, metodo: partes[1] || '', ms: Date.now() - t0 }
        if (partes[2] === '1' && plan.guardarEn) { res.archivo = path.basename(plan.guardarEn); res.carpeta = path.dirname(plan.guardarEn) }
        res.textosFallidos = Number(partes[3]) || 0
        estado.ultima = { t: Date.now(), titulo: plan.titulo, mesas: res.mesas, ms: res.ms }
        anotar('Armada «' + plan.titulo + '»: ' + res.mesas + ' mesas en ' + (res.ms / 1000).toFixed(1) + ' s')
        return res
      }
      var msg = r.indexOf('ERROR:') === 0 ? r.slice(6) : (r === 'EvalScript error.' ? 'el script de Illustrator falló' : r)
      anotar('No se pudo armar «' + plan.titulo + '»: ' + msg)
      throw new Error(msg)
    })
  }

  function responder(res, origen, codigo, cuerpo) {
    res.writeHead(codigo, {
      'Content-Type': 'application/json; charset=utf-8',
      'Access-Control-Allow-Origin': origen || '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Allow-Private-Network': 'true',
      'Vary': 'Origin',
      'Cache-Control': 'no-store',
    })
    res.end(JSON.stringify(cuerpo))
  }

  function atender(req, res) {
    var origen = req.headers.origin
    // el panel pregunta con Node (sin origen): eso no es USER PRO
    if (origen && origen !== 'null' && origen.indexOf('file:') !== 0) {
      if (!estado.contacto || estado.contacto.origen !== origen) anotar('Conectado con USER PRO (' + origen.replace(/^https?:\/\//, '') + ')')
      estado.contacto = { origen: origen, t: Date.now() }
    }
    if (req.method === 'OPTIONS') return responder(res, origen, 204, {})
    if (req.method === 'GET' && req.url.split('?')[0] === '/estado') {
      return responder(res, origen, 200, { app: 'TIZADA PRO', version: VERSION, illustrator: versionIllustrator(),
                                           ultima: estado.ultima, log: estado.log, contacto: estado.contacto,
                                           ahora: Date.now(), sistema: sistemaAhora() })
    }
    if (req.method === 'POST' && req.url.split('?')[0] === '/plantilla') {
      var trozos = [], largo = 0, cortado = false
      req.on('data', function (b) {
        largo += b.length
        if (largo > TOPE_CUERPO) { cortado = true; req.destroy(); return }
        trozos.push(b)
      })
      req.on('end', function () {
        if (cortado) return
        var plan
        try { plan = JSON.parse(Buffer.concat(trozos).toString('utf8')) } catch (e) {
          return responder(res, origen, 400, { ok: false, error: 'el plan no es JSON' })
        }
        // de a una: Illustrator arma un documento por vez
        cola = cola.then(function () { return armar(plan) }).then(function (r) {
          responder(res, origen, 200, r)
        }, function (e) {
          responder(res, origen, 422, { ok: false, error: e.message || String(e) })
        })
      })
      return
    }
    responder(res, origen, 404, { ok: false, error: 'no existe' })
  }

  /** Levanta el puente. Si el puerto ya lo tiene otro puente de TIZADA (el panel y el invisible, o
   *  dos Illustrator abiertos), no es un error: atiende ése. */
  function iniciar(alTerminar) {
    if (estado.escuchando) { if (alTerminar) alTerminar(estado); return }
    var srv = http.createServer(atender)
    srv.on('error', function (e) {
      estado.error = e.code === 'EADDRINUSE' ? 'ocupado' : (e.message || String(e))
      if (alTerminar) alTerminar(estado)
    })
    srv.listen(PUERTO, '127.0.0.1', function () {
      estado.escuchando = true
      estado.error = null
      anotar('Conectado: esperando plantillas de TIZADA PRO')
      if (alTerminar) alTerminar(estado)
    })
  }

  window.tizadaPuente = { iniciar: iniciar, estado: estado, PUERTO: PUERTO, VERSION: VERSION }
})()
