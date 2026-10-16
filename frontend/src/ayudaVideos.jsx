// LA AYUDA EN VIDEO (MAPA 689) — reemplaza a los tutoriales paso a paso que se dibujaban sobre la pantalla.
//
// Pedido del usuario (2026-10-12): «quitá la ayuda paso a paso; los videos tutoriales van en la carpeta de
// Drive y se ven en NUESTRO reproductor, moderno, con velocidades y de todo, que funcione rápido».
//
// · La lista sale de `GET /api/ayuda/videos` (la carpeta de Drive; una subcarpeta = una sección).
// · El video lo sirve NUESTRO servidor (`/api/ayuda/video/<id>`), que lo bajó una vez de Drive: con `Range`
//   se adelanta y atrasa al instante. Si todavía no está, se pregunta cómo va (`…/estado`) y se muestra el avance.
// · El reproductor es propio: controles que se esconden solos, barra con lo cargado y la hora al pasar el
//   mouse, ±10 s, velocidades de 0,5× a 2×, volumen, pantalla completa, imagen en imagen, seguir desde donde
//   quedó, el siguiente solo y atajos de teclado. Velocidad y volumen se recuerdan.
// · Sin textos explicativos en pantalla (regla MAPA 648): los atajos están en el `title` del teclado.
import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { rutaApi } from './base.js'   // el publicado vive en una sub-ruta: <video>/<img> no pasan por fetch

const VELOCIDADES = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]
const ATAJOS = 'Espacio/K: reproducir o pausar · J/L: −10/+10 s · ←/→: −5/+5 s · ↑/↓: volumen · M: silencio · F: pantalla completa · P: imagen en imagen · < >: velocidad · 0–9: saltar al 0–90 %'

const leer = (k, def) => { try { const v = localStorage.getItem(k); return v === null ? def : JSON.parse(v) } catch { return def } }
const guardar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)) } catch { /* sin almacenamiento: no pasa nada */ } }

function hms(s) {
  if (!Number.isFinite(s) || s < 0) s = 0
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = Math.floor(s % 60)
  return (h ? `${h}:${String(m).padStart(2, '0')}` : String(m)) + ':' + String(x).padStart(2, '0')
}

// íconos propios (trazos simples, se ven bien a cualquier tamaño)
const I = {
  play: <path d="M8 5v14l11-7z" fill="currentColor" />,
  pausa: <><rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor" /><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor" /></>,
  atras: <><path d="M11 7 6 12l5 5" /><path d="M6 12h9a4 4 0 0 1 0 8" /><text x="14" y="10" fontSize="6" fill="currentColor" stroke="none">10</text></>,
  adelante: <><path d="m13 7 5 5-5 5" /><path d="M18 12H9a4 4 0 0 0 0 8" /><text x="3" y="10" fontSize="6" fill="currentColor" stroke="none">10</text></>,
  vol: <><path d="M4 9v6h4l5 4V5L8 9z" fill="currentColor" stroke="none" /><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11" /></>,
  mudo: <><path d="M4 9v6h4l5 4V5L8 9z" fill="currentColor" stroke="none" /><path d="m17 9 5 6M22 9l-5 6" /></>,
  completa: <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />,
  salirCompleta: <path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" />,
  pip: <><rect x="3" y="5" width="18" height="14" rx="2" /><rect x="12" y="12" width="7" height="5" rx="1" fill="currentColor" /></>,
  teclado: <><rect x="2" y="6" width="20" height="12" rx="2" /><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10" /></>,
  cerrar: <path d="M6 6l12 12M18 6 6 18" />,
  buscar: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
  siguiente: <><path d="M6 5v14l9-7z" fill="currentColor" stroke="none" /><path d="M18 5v14" /></>,
  repetir: <><path d="M17 2l3 3-3 3" /><path d="M20 5H8a4 4 0 0 0-4 4v1M7 22l-3-3 3-3" /><path d="M4 19h12a4 4 0 0 0 4-4v-1" /></>,
  drive: <><path d="M8 3h8l6 10-4 7H6l-4-7z" /><path d="M8 3l6 10H2M16 3 10 13M22 13H10l-4 7" /></>,
}
const Ico = ({ n, s = 20 }) => (
  <svg viewBox="0 0 24 24" width={s} height={s} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{I[n]}</svg>
)

function BotonCtl({ ico, onClick, titulo, activo, s }) {
  return (
    <button type="button" className={'tzv-btn' + (activo ? ' on' : '')} onClick={onClick} title={titulo} aria-label={titulo}>
      <Ico n={ico} s={s} />
    </button>
  )
}

// ── EL REPRODUCTOR ─────────────────────────────────────────────────────────────────────────────
function Reproductor({ video, onTerminar, haySiguiente, onSiguiente }) {
  const vRef = useRef(null), cajaRef = useRef(null), barraRef = useRef(null), ocultarRef = useRef(null)
  const [listo, setListo] = useState(false)
  const [pct, setPct] = useState(0)
  const [error, setError] = useState('')
  const [jugando, setJugando] = useState(false)
  const [t, setT] = useState(0)
  const [dur, setDur] = useState(0)
  const [cargado, setCargado] = useState([])
  const [vel, setVel] = useState(() => leer('tzv_vel', 1))
  const [vol, setVol] = useState(() => leer('tzv_vol', 1))
  const [mudo, setMudo] = useState(false)
  const [completa, setCompleta] = useState(false)
  const [verCtl, setVerCtl] = useState(true)
  const [menuVel, setMenuVel] = useState(false)
  const [hover, setHover] = useState(null)        // {x, t} sobre la barra
  const [aviso, setAviso] = useState('')          // «1,5×», «+10 s»… un instante en el centro
  const [retomar, setRetomar] = useState(null)    // segundos desde donde se siguió
  const [autoSig, setAutoSig] = useState(() => leer('tzv_auto', true))
  const avisoRef = useRef(null)

  // ¿ya está en el servidor? si no, se pregunta cómo va hasta que esté
  useEffect(() => {
    let vivo = true, timer = null
    setListo(false); setPct(0); setError(''); setT(0); setDur(0); setRetomar(null)
    const mirar = async () => {
      try {
        const r = await fetch(`/api/ayuda/video/${video.id}/estado`)
        const d = await r.json().catch(() => ({}))
        if (!vivo) return
        if (d.listo) { setListo(true); return }
        if (d.error) { setError(d.error); return }
        setPct(d.pct || 0)
        timer = setTimeout(mirar, 900)
      } catch { if (vivo) timer = setTimeout(mirar, 2000) }
    }
    if (video.listo) setListo(true); else mirar()
    return () => { vivo = false; clearTimeout(timer) }
  }, [video.id, video.listo])

  const flash = useCallback((txt) => {
    setAviso(txt); clearTimeout(avisoRef.current)
    avisoRef.current = setTimeout(() => setAviso(''), 700)
  }, [])

  const mostrarCtl = useCallback(() => {
    setVerCtl(true); clearTimeout(ocultarRef.current)
    ocultarRef.current = setTimeout(() => { if (vRef.current && !vRef.current.paused) setVerCtl(false) }, 2600)
  }, [])

  const alternar = useCallback(() => {
    const v = vRef.current; if (!v) return
    if (v.paused) v.play().catch(() => {}); else v.pause()
  }, [])
  const saltar = useCallback((d) => {
    const v = vRef.current; if (!v) return
    v.currentTime = Math.max(0, Math.min((v.duration || 0) - 0.1, v.currentTime + d))
    flash((d > 0 ? '+' : '−') + Math.abs(d) + ' s'); mostrarCtl()
  }, [flash, mostrarCtl])
  const ponerVel = useCallback((x) => {
    setVel(x); guardar('tzv_vel', x); if (vRef.current) vRef.current.playbackRate = x
    flash(String(x).replace('.', ',') + '×'); setMenuVel(false)
  }, [flash])
  const ponerVol = useCallback((x) => {
    const v = Math.max(0, Math.min(1, x)); setVol(v); guardar('tzv_vol', v); setMudo(v === 0)
    if (vRef.current) { vRef.current.volume = v; vRef.current.muted = v === 0 }
  }, [])
  const alternarMudo = useCallback(() => {
    const v = vRef.current; if (!v) return
    v.muted = !v.muted; setMudo(v.muted); flash(v.muted ? 'Silencio' : 'Sonido')
  }, [flash])
  const pantallaCompleta = useCallback(() => {
    const c = cajaRef.current; if (!c) return
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
    else c.requestFullscreen?.().catch(() => {})
  }, [])
  const imagenEnImagen = useCallback(async () => {
    const v = vRef.current; if (!v) return
    try { if (document.pictureInPictureElement) await document.exitPictureInPicture(); else await v.requestPictureInPicture() } catch { /* el navegador no lo deja */ }
  }, [])

  useEffect(() => {
    const f = () => setCompleta(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', f)
    return () => document.removeEventListener('fullscreenchange', f)
  }, [])

  // atajos de teclado (sólo con el reproductor abierto y sin escribir en un campo)
  useEffect(() => {
    const k = (e) => {
      if (/^(input|textarea|select)$/i.test(e.target.tagName)) return
      const v = vRef.current; if (!v || !listo) return
      const c = e.key
      let hecho = true
      if (c === ' ' || c === 'k' || c === 'K') alternar()
      else if (c === 'j' || c === 'J') saltar(-10)
      else if (c === 'l' || c === 'L') saltar(10)
      else if (c === 'ArrowLeft') saltar(-5)
      else if (c === 'ArrowRight') saltar(5)
      else if (c === 'ArrowUp') { ponerVol(vol + 0.1); flash(Math.round(Math.min(1, vol + 0.1) * 100) + ' %') }
      else if (c === 'ArrowDown') { ponerVol(vol - 0.1); flash(Math.round(Math.max(0, vol - 0.1) * 100) + ' %') }
      else if (c === 'm' || c === 'M') alternarMudo()
      else if (c === 'f' || c === 'F') pantallaCompleta()
      else if (c === 'p' || c === 'P') imagenEnImagen()
      else if (c === '>' || c === '.') ponerVel(VELOCIDADES[Math.min(VELOCIDADES.length - 1, VELOCIDADES.indexOf(vel) + 1)] || 1)
      else if (c === '<' || c === ',') ponerVel(VELOCIDADES[Math.max(0, VELOCIDADES.indexOf(vel) - 1)] || 1)
      else if (/^[0-9]$/.test(c) && v.duration) { v.currentTime = v.duration * Number(c) / 10; mostrarCtl() }
      else hecho = false
      if (hecho) { e.preventDefault(); e.stopPropagation() }
    }
    window.addEventListener('keydown', k, true)
    return () => window.removeEventListener('keydown', k, true)
  }, [listo, vol, vel, alternar, saltar, ponerVol, ponerVel, alternarMudo, pantallaCompleta, imagenEnImagen, flash, mostrarCtl])

  // la posición se guarda cada tanto: al volver, sigue desde ahí
  const claveRef = useRef('')
  claveRef.current = 'tzv_pos_' + video.id
  const alCargar = () => {
    const v = vRef.current; if (!v) return
    setDur(v.duration || 0)
    v.playbackRate = vel; v.volume = vol; v.muted = mudo
    const pos = leer(claveRef.current, 0)
    if (pos > 5 && v.duration && pos < v.duration - 8) { v.currentTime = pos; setRetomar(pos) }
    const durs = leer('tzv_dur', {}); durs[video.id] = v.duration; guardar('tzv_dur', durs)
    v.play().catch(() => {})
  }
  const alAvanzar = () => {
    const v = vRef.current; if (!v) return
    setT(v.currentTime)
    if (Math.floor(v.currentTime) % 4 === 0) guardar(claveRef.current, v.currentTime)
    const r = []
    for (let i = 0; i < v.buffered.length; i++) r.push([v.buffered.start(i), v.buffered.end(i)])
    setCargado(r)
  }
  const alTerminar = () => {
    guardar(claveRef.current, 0)
    const vistos = leer('tzv_vistos', {}); vistos[video.id] = true; guardar('tzv_vistos', vistos)
    setJugando(false); setVerCtl(true)
    onTerminar && onTerminar()
    if (autoSig && haySiguiente) onSiguiente()
  }

  const posDeEvento = (e) => {
    const b = barraRef.current.getBoundingClientRect()
    const x = Math.max(0, Math.min(b.width, (e.clientX ?? 0) - b.left))
    return { x, t: (x / b.width) * (dur || 0) }
  }
  const arrastre = useRef(false)
  const bajarBarra = (e) => {
    arrastre.current = true
    const p = posDeEvento(e); if (vRef.current) vRef.current.currentTime = p.t; setT(p.t)
    const mover = (ev) => { if (!arrastre.current) return; const q = posDeEvento(ev); if (vRef.current) vRef.current.currentTime = q.t; setT(q.t); setHover(q) }
    const soltar = () => { arrastre.current = false; window.removeEventListener('pointermove', mover); window.removeEventListener('pointerup', soltar) }
    window.addEventListener('pointermove', mover); window.addEventListener('pointerup', soltar)
  }

  const fr = dur ? (t / dur) * 100 : 0
  return (
    <div ref={cajaRef} className={'tzv-player' + (verCtl || !jugando ? '' : ' oculto')}
      onPointerMove={mostrarCtl} onPointerLeave={() => jugando && setVerCtl(false)}>
      {listo ? (
        <video ref={vRef} className="tzv-video" src={rutaApi(`/api/ayuda/video/${video.id}`)} preload="auto" playsInline
          poster={rutaApi(`/api/ayuda/miniatura/${video.id}?m=${video.mini || ''}`)}
          onLoadedMetadata={alCargar} onTimeUpdate={alAvanzar} onProgress={alAvanzar}
          onPlay={() => { setJugando(true); mostrarCtl() }} onPause={() => { setJugando(false); setVerCtl(true) }}
          onEnded={alTerminar} onError={() => setError('No se pudo reproducir este video.')}
          onClick={alternar} onDoubleClick={pantallaCompleta} />
      ) : (
        <div className="tzv-preparando">
          <img src={rutaApi(`/api/ayuda/miniatura/${video.id}?m=${video.mini || ''}`)} alt="" onError={(e) => { e.currentTarget.style.display = 'none' }} />
          <div className="tzv-prep-caja">
            {error ? <span className="tzv-error">{error}</span> : <>
              <div className="tzv-anillo" style={{ '--p': pct }}><span>{pct}%</span></div>
              <span>Preparando el video…</span>
            </>}
          </div>
        </div>
      )}

      {listo && !jugando && !error && (
        <button type="button" className="tzv-grande" onClick={alternar} aria-label="Reproducir"><Ico n="play" s={42} /></button>
      )}
      {aviso && <div className="tzv-flash">{aviso}</div>}
      {retomar !== null && t - retomar < 6 && (
        <div className="tzv-retomar">
          Desde {hms(retomar)}
          <button type="button" onClick={() => { if (vRef.current) vRef.current.currentTime = 0; setRetomar(null) }}>Desde el principio</button>
        </div>
      )}

      {listo && (
        <div className="tzv-ctl" onPointerDown={(e) => e.stopPropagation()}>
          <div ref={barraRef} className="tzv-barra" onPointerDown={bajarBarra}
            onPointerMove={(e) => setHover(posDeEvento(e))} onPointerLeave={() => !arrastre.current && setHover(null)}>
            <div className="tzv-pista">
              {cargado.map(([a, b], i) => dur ? <div key={i} className="tzv-cargado" style={{ left: `${(a / dur) * 100}%`, width: `${((b - a) / dur) * 100}%` }} /> : null)}
              <div className="tzv-hecho" style={{ width: `${fr}%` }} />
              {hover && <div className="tzv-sombra" style={{ width: `${hover.x}px` }} />}
            </div>
            <div className="tzv-perilla" style={{ left: `${fr}%` }} />
            {hover && <div className="tzv-burbuja" style={{ left: `${hover.x}px` }}>{hms(hover.t)}</div>}
          </div>
          <div className="tzv-fila">
            <BotonCtl ico={jugando ? 'pausa' : 'play'} onClick={alternar} titulo={jugando ? 'Pausar (K)' : 'Reproducir (K)'} s={22} />
            <BotonCtl ico="atras" onClick={() => saltar(-10)} titulo="Atrás 10 s (J)" />
            <BotonCtl ico="adelante" onClick={() => saltar(10)} titulo="Adelante 10 s (L)" />
            {haySiguiente && <BotonCtl ico="siguiente" onClick={onSiguiente} titulo="Siguiente video" />}
            <div className="tzv-vol">
              <BotonCtl ico={mudo || vol === 0 ? 'mudo' : 'vol'} onClick={alternarMudo} titulo="Silencio (M)" />
              <input type="range" min="0" max="1" step="0.02" value={mudo ? 0 : vol} onChange={(e) => ponerVol(Number(e.target.value))} aria-label="Volumen" />
            </div>
            <span className="tzv-tiempo">{hms(t)} / {hms(dur)}</span>
            <span style={{ flex: 1 }} />
            <BotonCtl ico="repetir" onClick={() => { const x = !autoSig; setAutoSig(x); guardar('tzv_auto', x); flash(x ? 'Sigue con el próximo' : 'Para al terminar') }}
              titulo={autoSig ? 'Al terminar: sigue con el próximo' : 'Al terminar: se detiene'} activo={autoSig} />
            <div className="tzv-velcaja">
              <button type="button" className="tzv-vel" onClick={() => setMenuVel((x) => !x)} title="Velocidad (< >)">{String(vel).replace('.', ',')}×</button>
              {menuVel && (
                <div className="tzv-menu">
                  {VELOCIDADES.slice().reverse().map((x) => (
                    <button key={x} type="button" className={x === vel ? 'on' : ''} onClick={() => ponerVel(x)}>{x === 1 ? 'Normal' : String(x).replace('.', ',') + '×'}</button>
                  ))}
                </div>
              )}
            </div>
            {'pictureInPictureEnabled' in document && <BotonCtl ico="pip" onClick={imagenEnImagen} titulo="Imagen en imagen (P)" />}
            <span className="tzv-btn" title={ATAJOS}><Ico n="teclado" /></span>
            <BotonCtl ico={completa ? 'salirCompleta' : 'completa'} onClick={pantallaCompleta} titulo="Pantalla completa (F)" />
          </div>
        </div>
      )}
    </div>
  )
}

// ── LA VENTANA DE AYUDA: la lista y el reproductor ─────────────────────────────────────────────
export default function AyudaVideos({ abierto, setAbierto }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [buscar, setBuscar] = useState('')
  const [actual, setActual] = useState(() => leer('tzv_actual', null))
  const [, setTick] = useState(0)

  const cargar = useCallback(async (recargar = false) => {
    setError('')
    try {
      const r = await fetch('/api/ayuda/videos' + (recargar ? '?recargar=1' : ''))
      const d = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(d.error || 'No se pudo leer la lista de videos')
      setDatos(d)
    } catch (e) { setError(String(e.message || e)) }
  }, [])
  useEffect(() => { if (abierto) cargar() }, [abierto, cargar])
  useEffect(() => {
    if (!abierto) return undefined
    const k = (e) => { if (e.key === 'Escape' && !document.fullscreenElement) setAbierto(false) }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [abierto, setAbierto])

  const todos = useMemo(() => (datos?.secciones || []).flatMap((s) => s.videos.map((v) => ({ ...v, seccion: s.nombre }))), [datos])
  const filtrados = useMemo(() => {
    const q = buscar.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    if (!q) return datos?.secciones || []
    return (datos?.secciones || []).map((s) => ({ ...s, videos: s.videos.filter((v) => v.titulo.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').includes(q)) }))
      .filter((s) => s.videos.length)
  }, [datos, buscar])
  const video = todos.find((v) => v.id === actual) || todos[0] || null
  const idx = video ? todos.findIndex((v) => v.id === video.id) : -1
  const elegir = (id) => { setActual(id); guardar('tzv_actual', id) }
  const vistos = leer('tzv_vistos', {}), durs = leer('tzv_dur', {})

  if (!abierto) return null
  return createPortal(
    <div className="tzv-fondo" onPointerDown={(e) => { if (e.target === e.currentTarget) setAbierto(false) }}>
      <div className="tzv-ventana" role="dialog" aria-label="Ayuda en video">
        <aside className="tzv-lado">
          <div className="tzv-cabeza">
            <b>Tutoriales</b>
            {datos?.carpeta && <a className="tzv-btn" href={datos.carpeta} target="_blank" rel="noreferrer" title="Abrir la carpeta en Drive"><Ico n="drive" s={18} /></a>}
          </div>
          <label className="tzv-buscar"><Ico n="buscar" s={16} /><input value={buscar} onChange={(e) => setBuscar(e.target.value)} placeholder="Buscar" /></label>
          <div className="tzv-lista">
            {error && <div className="tzv-error" style={{ padding: 12 }}>{error} <button type="button" className="tzv-link" onClick={() => cargar(true)}>Reintentar</button></div>}
            {!error && !datos && <div className="tzv-vacio">Cargando…</div>}
            {datos && !todos.length && <div className="tzv-vacio">La carpeta de tutoriales está vacía.</div>}
            {filtrados.map((s) => (
              <div key={s.nombre}>
                {(datos?.secciones || []).length > 1 && <div className="tzv-seccion">{s.nombre}</div>}
                {s.videos.map((v) => {
                  const pos = leer('tzv_pos_' + v.id, 0), d = durs[v.id]
                  const avance = vistos[v.id] ? 100 : (d ? Math.min(100, (pos / d) * 100) : 0)
                  return (
                    <button key={v.id} type="button" className={'tzv-item' + (video && v.id === video.id ? ' on' : '')} onClick={() => { elegir(v.id); setTick((x) => x + 1) }}>
                      <span className="tzv-mini">
                        <img src={rutaApi(`/api/ayuda/miniatura/${v.id}?m=${v.mini || ''}`)} alt="" loading="lazy" onError={(e) => { e.currentTarget.style.visibility = 'hidden' }} />
                        {d ? <span className="tzv-dur">{hms(d)}</span> : null}
                        {avance > 0 && <span className="tzv-visto" style={{ width: `${avance}%` }} />}
                      </span>
                      <span className="tzv-titulo">{v.titulo}</span>
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        </aside>
        <main className="tzv-principal">
          <div className="tzv-cabeza">
            <b className="tzv-titulo-grande">{video ? video.titulo : 'Ayuda'}</b>
            <BotonCtl ico="cerrar" onClick={() => setAbierto(false)} titulo="Cerrar (Esc)" />
          </div>
          {video ? (
            <Reproductor key={video.id} video={video} haySiguiente={idx >= 0 && idx < todos.length - 1}
              onSiguiente={() => idx < todos.length - 1 && elegir(todos[idx + 1].id)} onTerminar={() => setTick((x) => x + 1)} />
          ) : <div className="tzv-player tzv-vacio-grande" />}
        </main>
      </div>
    </div>,
    document.body,
  )
}
