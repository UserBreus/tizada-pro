// LOS FORMATOS DE DESCARGA DE LA TIZADA PARA CORTE (MAPA 816). Aparte de `exportar.js` para que la pantalla
// los liste sin cargar el motor (el que escribe los archivos corre en un hilo, `corte_exportar`).
// `ayuda` = para qué máquina/programa sirve, en una línea (el «?» de la ventana de descarga).
export const FORMATOS_CORTE = {
  pdf: { ext: 'pdf', nombre: 'PDF', mime: 'application/pdf', ayuda: 'La hoja tal cual se ve: para imprimir o para la mesa de corte que lee PDF.' },
  dxf: { ext: 'dxf', nombre: 'DXF 2000', mime: 'application/dxf', ayuda: 'Programas de corte actuales (LightBurn, RDWorks, AutoCAD). Curvas exactas, en milímetros.' },
  ai: { ext: 'ai', nombre: 'Illustrator 3 (AI)', mime: 'application/postscript', ayuda: 'El AI viejo que leen muchas máquinas láser. Curvas exactas.' },
  plt: { ext: 'plt', nombre: 'PLT (HPGL)', mime: 'application/vnd.hp-hpgl', ayuda: 'Plotters de corte y láser viejos. Las curvas van en tramos de 0,02 mm.' },
  svg: { ext: 'svg', nombre: 'SVG', mime: 'image/svg+xml', ayuda: 'LightBurn, Inkscape y programas nuevos. Curvas exactas, en milímetros.' },
  eps: { ext: 'eps', nombre: 'EPS', mime: 'application/postscript', ayuda: 'Programas viejos que no abren AI (CorelDRAW viejo y similares).' },
}
export const ORDEN_FORMATOS_CORTE = ['dxf', 'ai', 'plt', 'svg', 'eps', 'pdf']
