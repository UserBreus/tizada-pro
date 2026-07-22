import React, { useState, useEffect, useRef, useMemo } from 'react';
import { createPortal } from 'react-dom';

// --- Inline SVG Icons Component for clean, dependency-free icons ---
// Acepta `style` además de `className`. Si no se pasa ni estilo ni clase,
// usa un tamaño por defecto (18px) para que ningún icono se renderice gigante.
function Icon({ name, className = "", style }) {
  const icons = {
    pedidos: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/>
        <line x1="3" y1="6" x2="21" y2="6"/>
        <path d="M16 10a4 4 0 0 1-8 0"/>
      </svg>
    ),
    productos: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <path d="M8 11h8"/>
        <path d="M12 7v8"/>
      </svg>
    ),
    config: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
    ),
    plus: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
    ),
    user: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    ),
    shield: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    ),
    trash: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <polyline points="3 6 5 6 21 6"/>
        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
      </svg>
    ),
    edit: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
        <path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
      </svg>
    ),
    eye: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>
        <circle cx="12" cy="12" r="3"/>
      </svg>
    ),
    upload: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
    ),
    check: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
    ),
    cross: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    ),
    alert: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    ),
    download: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
    ),
    copy: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
      </svg>
    ),
    arrowRight: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5">
        <line x1="5" y1="12" x2="19" y2="12"/>
        <polyline points="12 5 19 12 12 19"/>
      </svg>
    ),
    columnas: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <line x1="12" y1="3" x2="12" y2="21" />
      </svg>
    ),
    distribucion: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="9" rx="1" />
        <rect x="14" y="3" width="7" height="5" rx="1" />
        <rect x="14" y="12" width="7" height="9" rx="1" />
        <rect x="3" y="16" width="7" height="5" rx="1" />
      </svg>
    ),
    nesting: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m15 15 6 6m0-6-6 6M9 9l6 6m0-6-6 6M3 3l6 6M9 3 3 9" />
      </svg>
    ),
    telas: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M5 3a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2H5zm0 4h14M5 12h14M5 17h14" />
      </svg>
    ),
    fuentes: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="4 7 4 4 20 4 20 7" />
        <line x1="9" y1="20" x2="15" y2="20" />
        <line x1="12" y1="4" x2="12" y2="20" />
      </svg>
    ),
    search: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
    reset: (
      <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
        <path d="M3 3v5h5" />
      </svg>
    )
  };
  const el = icons[name];
  if (!el) return null;
  // style explícito → se reenvía. Sin style ni className → tamaño por defecto.
  const mergedStyle = { ...((!className && !style) ? { width: 18, height: 18 } : {}), ...(style || {}) };
  return Object.keys(mergedStyle).length ? React.cloneElement(el, { style: mergedStyle }) : el;
}

// Función helper para desglosar el progreso del backend y calcular porcentaje + texto detallado
const getProgresoDetalle = (progresoStr, estado) => {
  if (estado === 'en cola') {
    return { pct: 5, texto: 'Esperando en cola de procesamiento...' };
  }
  if (!progresoStr) {
    return { pct: 10, texto: 'Iniciando procesamiento de archivos...' };
  }
  
  const parts = progresoStr.split(':');
  if (parts.length < 2) {
    return { pct: 15, texto: progresoStr };
  }
  
  const fase = parts[0].trim();
  const valor = parts[1].trim();
  
  if (fase === 'piezas') {
    const valParts = valor.split(' - ');
    const nums = valParts[0].split('/');
    const hechas = parseInt(nums[0], 10) || 0;
    const total = parseInt(nums[1], 10) || 1;
    const pct = Math.round((hechas / total) * 65);
    const detalle = valParts[1] ? ` (${valParts[1]})` : '';
    return { 
      pct, 
      texto: `Procesando diseño en pieza: ${hechas} de ${total}${detalle}` 
    };
  }
  
  if (fase === 'nesting') {
    return { 
      pct: 75, 
      texto: `Calculando tizada óptima (Nesting) de tela: ${valor}` 
    };
  }
  
  if (fase === 'previews') {
    const valParts = valor.split(' - ');
    const nums = valParts[0].split('/');
    const hechas = parseInt(nums[0], 10) || 0;
    const total = parseInt(nums[1], 10) || 1;
    const pct = 80 + Math.round((hechas / total) * 20);
    const detalle = valParts[1] ? ` (Tela ${valParts[1]})` : '';
    return { 
      pct, 
      texto: `Generando vistas previas de impresión: página ${hechas} de ${total}${detalle}`
    };
  }

  if (fase === 'perfil') {
    return { pct: 98, texto: 'Unificando color e incrustando el perfil…' };
  }

  return { pct: 50, texto: progresoStr };
};

// ── Animación de carga: LOGO con registro CMYK (fantasmas C/M/Y que se desalinean y "registran"
//    como una impresora) + barrido del cabezal + cronómetro mm:ss + fase. Moderno/futurista. ──
const _LOGO_INNER = `
<g>
<path d="M274.5,419.1c3.2,3.2,7.7,5.4,11.8,7.2s1.4-.4,1.1,1.6c-7.4,1.4-13.8,7.6-17.4,13.9-1.2,2.1-1.6,5-3.5,6.2-1.6-8.3-10.6-18.7-19-20.1s-1.3.4-1.2-1.5c9.4-1.7,18-11,20.1-20.1,1.1,0,1.2,1.2,1.6,1.9,1.8,3.8,3.4,7.9,6.4,11Z"/>
<path d="M485.5,415.1c-.2.9-2.4,2.2-3.4,2-56.9,1.3-114.2-1.9-171.1,0-1.7,0-3.4.9-4.6.8s-11.2-5.2-12.6-6.1c-8.1-4.9-16.7-17.4-18-26.9-2.2-17,1.3-38.8,0-56.5-.5-6-4.6-11.7-10.2-13.7s-9.3-.5-9.9-4v-95.5c11.7-2.4,23.3-3.3,34.8-6.7,23-6.7,35.8-16.6,46-38.3,1.1-2.4.7-5.4,4-6.1l122.5,23.4c1.2.8.8,11.2.7,13.2-.7,18.4-1.1,36.5,1.6,54.8.9,6,2.3,12.1,3.8,18l-.3,1.9-82.4,39.4,98.2-10c0,.7.9,1.6.9,1.8v108.3Z"/>
<path d="M514.2,537.7c.3.1,2.8,3.3,2.4,4.2l-.4,61.6c-1.5,3.7-4,7.1-7.4,9.3s-.9,1-1.7,1l-229.7.2-1.2-1.2-.4-144.4c4.1-14.7,14.3-27.5,29.9-30.5h173.2c1.4.5,1.9,2.8,2.1,4.2,3.3,32.1-13,80.9,27.1,94.4,1.9.6,5.1.7,6.2,1.2Z"/>
<g>
<path d="M98.1,524c.7-.7,9-4.5,10.6-5.2,14.5-6,31.5-9.7,47.2-10.5-.3-1.6-1.6-1.3-2.7-1.5-17.2-3.8-35.8-4.9-53.4-6.2l-2-1.1c-.7-.7-.7-1.5-.8-2.3-1.9-17.4,1.5-38,0-55.8l1.6-3.1,125.8-.3c1.5.3,2.6-1.6,3.8-1.6,1.9,0,12.7,6.1,14.7,7.7,3.8,3.1,13.3,14.3,13.6,19s-.8,2.9-.8,4.6c-1.2,52.1,1,104.3,0,156.4l-1.6,3.1H98.6l-1.2-1.2-.4-97.9c0-1.3.1-3,1-4Z"/>
<path d="M168,188.8c8.8,4.7,16.5,11.4,25.3,16.3s10.6,5.5,15.5,7.7,14.5,4.9,20.1,7.8,2.3,2.5,2.1,4.9c-1.7,22.7-4.5,48.4-3.2,71.2s4.3,23.6,17.1,28.6c2.8,1.1,10,1.7,10.7,4,.6,18.8-.4,37.6,0,56.4,0,2.1,1.1,3.8.7,6-1.5,7.2-12.2,18.3-18.7,21.6s-4.3,1.4-6.2,2.3c-2.8,1.3-2.5,3-7.1,1.3h-122.9c0,0-1.7-1.5-1.7-1.5l-.3-183.7c1.9-3,5.7-1.7,8.7-2.1,24.3-3.4,42.4-14.2,55.7-34.8,1.3-2.1,1.8-4.7,4-6.1Z"/>
</g>
</g>
<path d="M294.4,132.2v12.4H93.6c-1.6,0-11,3.7-13,4.8-10.1,5.4-18.3,17-20.5,28.3s-1,5.6-1,6v233.3h-12.4v-237.9c0-1.9,3.5-12.5,4.5-14.8,5.6-13.1,17.6-24.6,31.1-29.2s8.6-2.7,9.7-2.7h202.4Z"/>
<path d="M566.8,428.6v179.1c0,10.3-9.5,27.1-16.6,34.5s-25,18.6-35.6,18.6h-222.5v-12l1.3-1.1,220.4-.2c19.5-1.6,40.7-23.2,40.7-42.9v-176h12.4Z"/>
<path d="M304.5,144.6v-12l1.3-1.1h174c18.4.4,34,13.8,36.8,32l-.4,247.3c-2.8,3.5-11.6,3-12-1.9v-239.9c-.8-8-3.6-15.7-10.5-20.4-1.3-.9-8-4-9.2-4h-179.9Z"/>
<path d="M282,647.6v13.2H90.5c-10.4,0-26-11.5-32.5-19.3-4.7-5.6-11.2-19.5-11.2-26.7v-186.1h12l1.1,1.3.2,185.5c1.3,12.7,13.1,26.9,25.3,30.4.9.3,7.2,1.7,7.5,1.7h189.2Z"/>
<path d="M514.2,537.7c2-1.8,4.2-2,6.2-4.3s3.9-6.6,3.9-7.7v-97.1h17.8v149c0,.8-2.7,8.5-3.3,9.9-4.9,12.1-16.8,23.6-30,25.3,3.4-2.2,5.8-5.6,7.4-9.3l.4-61.6c.5-.9-2.1-4.1-2.4-4.2Z"/>
<path d="M566.8,417h-12.4v-172.9c0-6.7-5.7-20.2-9.7-25.9-5.4-7.7-12.2-12.4-20.4-16.7v-25.9c16.8,4.4,31.8,18.8,38.3,34.8,1.2,3.1,4.3,12.2,4.3,15.1v191.5Z"/>
<path d="M542,417h-17.8v-199.6c3.5.8,7.4,5,9.6,7.8s8.2,13.7,8.2,16.6v175.3Z"/>
<rect x="505.6" y="437.8" width="7.8" height="79.1"/>
<path d="M513,425.5c-2.6.7,1.2,9.8-5.7,6.1,1-8.9-3.3-4.8-9-6.8-1.7-7.5,4.4-4.8,8.5-4.7,17.1.5,33.8-.4,51.1,0,10.8.2,21.7-.2,32.5,0l1.6.7c.7,1.6.7,3.6-.8,4.7h-78.2Z"/>
<path d="M20.9,425.5c-1.5-1.1-1.5-3-.8-4.7l1.6-.7,52.2-.8c-.2-2.2-.4-7,2.7-7s2.5,5.4,2.9,7.2,2.1,2.4,1,4.4-1.5,1.5-1.6,1.5H20.9Z"/>
<path d="M290.5,636v40.6c0,2.4-6.2,2.4-6.2,0v-47.2c0-.1,1.2-1.4,1.5-1.6,2.8-1.5,3.2.8,4.7,1.5s2.9.3,3.9,1.5l.4,3.6-4.3,1.5Z"/>
<path d="M302.1,165.1c-2.3,2.9-4.2.3-6-.2s-4.9.9-4.9-2.9,2-2.7,4.6-2.8c2-5.2-.2-9.9,0-15.1s.8-3.5.8-5.3c.2-8-.3-16,0-23.9.9-2.8,5.3-.5,5.3.7v49.5Z"/>
<path d="M73.9,359.6c.4-2-.7-4.1-.8-5.8s.7-2.5.8-3.8c0-2.5-.3-5.5,0-7.8s4.9-2.4,5.4.8.4,12.4,0,14.7-3,3.1-5.3,1.8Z"/>
<path d="M239.8,159.3c2,1.3,1.7,5.4-.8,5.4h-16.3c-.3,0-2.1-1.9-2-2.7-.1-.8,1.7-2.7,2-2.7h17Z"/>
<path d="M73.9,235.9v-18.2c1.4-2.1,4.7-1.2,5.3.9s.4,15.3-.2,16.5-1.1,1.3-1.7,1.5l-3.3-.7Z"/>
<path d="M181,159.3h17c1.7,1.3,1.7,4.1,0,5.4h-17c-1.7-1.3-1.7-4.1,0-5.4Z"/>
<path d="M99,159.3h16.3c.3,0,2.1,1.9,2,2.7.1.8-1.7,2.7-2,2.7h-16.3c-.3,0-2.1-1.9-2-2.7l2-2.7Z"/>
<path d="M264.6,159.3h16.3c.3,0,2.1,1.9,2,2.7.1.8-1.7,2.7-2,2.7h-16.3c-.3,0-2.1-1.9-2-2.7l2-2.7Z"/>
<path d="M400.8,635.2c-2-.6-2.5-3.9-.2-4.9s15.2-1,16.9-.2,2.2,3.9.4,5c-4.5-.8-13.1,1.1-17,0Z"/>
<path d="M140,159.3h16.3c.3,0,2.1,1.9,2,2.7.1.8-1.7,2.7-2,2.7h-16.3l-1.8-3.4,1.8-2Z"/>
<path d="M73.9,300.5c1.1-1.8,4.1-1.5,5,.4s.6,15.4-.3,17.4-4.1.6-4.7-.7v-17Z"/>
<path d="M73.9,259.5c.3-1.2,4.2-1.8,4.7-.7,1,2,1.2,15.6.3,17.3s-1.1,1.3-1.7,1.5l-3.3-.7v-17.4Z"/>
<path d="M73.9,383.3c1.1-1.8,4.1-1.5,5,.4s.7,14.1.2,15.7-3.9,3.1-5.3.9v-17Z"/>
<path d="M441.4,635.2c-.3-1.4-1.1-3.2.2-4.5s16-1.4,17.9-.2.6,4.7-.7,4.7h-17.4Z"/>
<path d="M483.6,635.2c-2.2-1.8-1.5-4.2,1.1-5.1s14-.7,15.5,0,2.2,3.9.4,5h-17Z"/>
<path d="M318,635.2c-1.6-.9-1.8-4,0-4.5,4.9,0,9.7-1.4,14.6-.9s4.8,3.1,2.3,5.5h-17Z"/>
<path d="M78.3,194.7c-3.1,3.1-5.1-2.5-5.2-4.9s.7-2.5.8-3.8c.2-2.5-1-7.1,2.7-7.4s2.7,3.1,2.7,5.1.6,9.5-.9,11.1Z"/>
<path d="M358.6,630.6h17.4c1.7,1.3,1.7,3.4,0,4.6h-17c-1.7,0-.9-3.5-.4-4.6Z"/>
`;
// Cada pieza del logo por separado (para resaltarlas de a una, en orden).
const _LOGO_PATHS = (_LOGO_INNER.match(/d="[^"]+"/g) || []).map(s => s.slice(3, -1)).concat(["M505.6,437.8h7.8v79.1h-7.8Z"]);
function TizadaLoader({ det }) {
  const [seg, setSeg] = useState(0);
  useEffect(() => {
    const t0 = Date.now();
    const id = setInterval(() => setSeg(Math.floor((Date.now() - t0) / 1000)), 250);
    return () => clearInterval(id);
  }, []);
  const mm = String(Math.floor(seg / 60)).padStart(2, '0');
  const ss = String(seg % 60).padStart(2, '0');
  const pct = det?.pct ?? 0;
  return (
    <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, padding: '20px 12px' }}>
      <style>{`
        @keyframes tzFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
        /* Resaltar UNA pieza HACIA ADELANTE (se agranda + brilla + sombra = se acerca), y vuelve.
           Con el delay escalonado, el resalte RECORRE las piezas en orden, una tras otra. */
        @keyframes tzPop {
          0%, 18%, 100% { transform: scale(1); filter: brightness(1); }
          9% { transform: scale(1.28); filter: brightness(1.7) drop-shadow(0 6px 10px rgba(0,0,0,0.55)); }
        }
        .tzAnim > path { transform-box: fill-box; transform-origin: center; animation: tzPop 2.8s ease-in-out infinite; }
        @keyframes tzDots { 0%,20% { opacity:.2 } 50% { opacity:1 } 80%,100% { opacity:.2 } }
      `}</style>
      <div style={{ position: 'relative', width: 150, height: 145, animation: 'tzFloat 3s ease-in-out infinite', filter: 'drop-shadow(0 0 7px rgba(0,150,255,0.5))' }}>
        <svg viewBox="8 118 596 560" width="150" height="145" style={{ overflow: 'visible' }}>
          <defs>
            <linearGradient id="tzGrad" gradientUnits="userSpaceOnUse" x1="20" y1="130" x2="560" y2="660">
              <stop offset="0" stopColor="#00d8f5" />
              <stop offset="0.5" stopColor="#6a5cff" />
              <stop offset="1" stopColor="#ff4db8" />
            </linearGradient>
          </defs>
          {/* cada pieza del logo, con su delay en orden → el resalte hacia adelante las recorre */}
          <g className="tzAnim" fill="url(#tzGrad)">
            {_LOGO_PATHS.map((d, i) => (
              <path key={i} d={d} style={{ animationDelay: (i * (2.8 / _LOGO_PATHS.length)).toFixed(3) + 's' }} />
            ))}
          </g>
        </svg>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span style={{ fontSize: 32, fontWeight: 800, fontFamily: 'monospace', letterSpacing: 1.5, color: '#fff', fontVariantNumeric: 'tabular-nums' }}>{mm}:{ss}</span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>transcurrido</span>
      </div>
      <div style={{ width: '100%', maxWidth: 480 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 7 }}>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{det?.texto || 'Preparando…'}</span>
          <span style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent)' }}>{pct}%</span>
        </div>
        <div className="progress-bar-container"><div className="progress-bar shimmer" style={{ width: `${pct}%`, transition: 'width .4s ease' }}></div></div>
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
        Armando la tizada<span style={{ animation: 'tzDots 1.4s infinite' }}>…</span> no cierres esta ventana
      </div>
    </div>
  );
}

// Parseo seguro de respuestas JSON. Si el servidor devuelve HTML (típico cuando
// un endpoint no existe porque el Python en memoria está desactualizado), en vez
// de un críptico "Unexpected token '<'" damos un mensaje claro y accionable.
async function leerJson(res) {
  const txt = await res.text();
  try {
    return txt ? JSON.parse(txt) : {};
  } catch {
    const err = new Error('El servidor está desactualizado. Cerrá la ventana negra y volvé a abrir "iniciar.bat".');
    err.staleServer = true;
    throw err;
  }
}

// ── Combo: casilla editable + lista desplegable propia (scrolleable, compacta) ──
function ComboCell({ value, options, onChange, onFocusCell, cellId, onNavKey, noAbrir }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(null);
  const [verTodas, setVerTodas] = useState(false);   // true = mostrar todas (foco/flecha); false = filtrar por lo escrito
  const wrapRef = useRef(null);
  const inputRef = useRef(null);
  const abrir = (todas) => {
    if (noAbrir) return;   // hay varias celdas seleccionadas → no abrir el desplegable
    const r = inputRef.current?.getBoundingClientRect();
    if (r) setPos({ left: r.left, top: r.bottom + 2, width: r.width });
    setVerTodas(!!todas);
    setOpen(true);
  };
  useEffect(() => { if (noAbrir) setOpen(false); }, [noAbrir]);   // al pasar a multi-selección, cerrar
  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);
  const cs = { width: '100%', padding: '4px 22px 4px 8px', border: 'none', background: 'transparent', color: 'var(--text-primary)', outline: 'none', fontSize: 12.5, height: 30, boxSizing: 'border-box' };
  // Filtro tipo autocompletar: al escribir, muestra solo las opciones que se asemejan (sin acentos/mayúsc).
  // Si el texto coincide EXACTO con una opción (o está vacío), muestra todas para poder re-elegir.
  const _norm = (s) => (s == null ? '' : String(s)).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const _nv = _norm(value);
  // Al ESCRIBIR siempre filtra por lo tipeado (aunque sea un valor exacto). Muestra TODAS solo
  // cuando se abre por foco o por la flecha ▾ (verTodas), o si el campo está vacío.
  const filtradas = (verTodas || !_nv) ? options : options.filter(o => _norm(o).includes(_nv));
  // Valor INVÁLIDO: hay opciones fijas, la celda tiene texto y no coincide con ninguna.
  const invalido = options.length > 0 && _nv !== '' && !options.some(o => _norm(o) === _nv);
  return (
    <div ref={wrapRef} title={invalido ? 'Valor no válido — elegí uno de la lista' : undefined}
      style={{ position: 'relative', boxShadow: invalido ? 'inset 0 0 0 1.5px rgba(255,90,90,0.8)' : 'none', background: invalido ? 'rgba(255,70,70,0.08)' : 'transparent' }}>
      <input ref={inputRef} value={value} placeholder="escribí o elegí…" data-plc={cellId}
        onFocus={() => { onFocusCell?.(); abrir(true); }}
        onChange={e => { onChange(e.target.value); setVerTodas(false); if (!open) abrir(false); }}
        onBlur={() => { const ex = options.find(o => _norm(o) === _nv); if (ex && ex !== value) onChange(ex); }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === 'Tab') {
            const ex = options.find(o => _norm(o) === _nv);   // coincide sin importar mayús/minús
            if (ex) { if (ex !== value) onChange(ex); }        // → guarda el valor canónico
            else if (open && filtradas.length && _nv) onChange(filtradas[0]);   // parcial → autocompleta
            setOpen(false);
          }
          onNavKey?.(e);
        }}
        style={invalido ? { ...cs, color: '#ff8a8a', fontWeight: 700 } : cs} />
      <span onMouseDown={(e) => { e.preventDefault(); open ? setOpen(false) : abrir(true); }}
        style={{ position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)', color: 'var(--cmyk-cyan)', fontSize: 10, cursor: 'pointer' }}>▾</span>
      {open && pos && filtradas.length > 0 && createPortal(
        <div style={{ position: 'fixed', left: pos.left, top: pos.top, width: pos.width, zIndex: 3000, background: '#15151a', border: '1px solid var(--border-light)', borderRadius: 6, maxHeight: 130, overflowY: 'auto', boxShadow: '0 10px 24px rgba(0,0,0,0.55)' }}>
          {filtradas.map(o => (
            <div key={o} onMouseDown={(e) => { e.preventDefault(); onChange(o); setOpen(false); }}
              style={{ padding: '5px 10px', fontSize: 12.5, cursor: 'pointer', color: o === value ? 'var(--accent)' : 'var(--text-secondary)', background: o === value ? 'rgba(0,216,245,0.10)' : 'transparent' }}
              onMouseEnter={e => { if (o !== value) e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = o === value ? 'rgba(0,216,245,0.10)' : 'transparent'; }}>
              {o}
            </div>
          ))}
        </div>,
        document.getElementById('root') || document.body
      )}
    </div>
  );
}

// ── Planilla interactiva de prueba (estilo Google Sheets) ──────────────────
// Permite a quien crea la planilla cargarla como el operario y DUPLICAR valores
// arrastrando el tirador (fill handle) de una celda hacia abajo o los costados,
// sin importar si la celda es casilla, desplegable o botón.
function PlanillaTester({ columnas, reglas, variantes = [], onClose }) {
  const [rows, setRows] = useState(() => Array.from({ length: 6 }, () => ({})));
  const [sel, setSel] = useState(null);    // {r, c} celda seleccionada
  const [fill, setFill] = useState(null);  // {r, c} destino actual del arrastre
  const dragRef = useRef(null);            // {r, c} celda origen del arrastre

  const colInfo = (c) => {
    const regla = reglas.find(r => r.id === c.reglaId) || reglas.find(r => r.comportamiento === (c.role || 'none'));
    const role = c.role || regla?.comportamiento || 'none';
    const tipo = c.tipo || regla?.tipo || (role === 'manga' ? 'toggle' : role === 'talle' ? 'desplegable' : 'texto');
    let opts = (c.opciones || regla?.opciones || '').split(',').map(s => s.trim()).filter(Boolean);
    // La columna de variante toma SUS opciones de las variantes reales del molde.
    if (role === 'talle' && variantes && variantes.length) opts = variantes;
    return { role, tipo, opts };
  };

  const setCell = (r, cId, val) => setRows(prev => prev.map((row, i) => i === r ? { ...row, [cId]: val } : row));
  const addRow = () => setRows(prev => [...prev, {}]);

  useEffect(() => {
    const onUp = () => {
      const start = dragRef.current;
      if (start && fill) {
        const sc = columnas[start.c];
        const val = rows[start.r]?.[sc.id] ?? '';
        const r0 = Math.min(start.r, fill.r), r1 = Math.max(start.r, fill.r);
        const c0 = Math.min(start.c, fill.c), c1 = Math.max(start.c, fill.c);
        setRows(prev => prev.map((row, ri) => {
          if (ri < r0 || ri > r1) return row;
          const nr = { ...row };
          for (let ci = c0; ci <= c1; ci++) nr[columnas[ci].id] = val;
          return nr;
        }));
      }
      dragRef.current = null;
      setFill(null);
    };
    window.addEventListener('mouseup', onUp);
    return () => window.removeEventListener('mouseup', onUp);
  }, [fill, rows, columnas]);

  const enRango = (r, c) => {
    const start = dragRef.current;
    if (!start || !fill) return false;
    const r0 = Math.min(start.r, fill.r), r1 = Math.max(start.r, fill.r);
    const c0 = Math.min(start.c, fill.c), c1 = Math.max(start.c, fill.c);
    return r >= r0 && r <= r1 && c >= c0 && c <= c1;
  };

  const cellStyle = { width: '100%', padding: '4px 8px', border: 'none', background: 'transparent', color: 'var(--text-primary)', outline: 'none', fontSize: 12.5, height: 30 };

  return (
    <div className="animate-fade" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 12, marginBottom: 4, borderBottom: '1px solid var(--border-light)', gap: 12 }}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Probar planilla</div>
            <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 3, maxWidth: 640, lineHeight: 1.4 }}>Cargala como lo haría el operario. Seleccioná una celda y arrastrá el <b style={{ color: 'var(--accent)' }}>cuadradito</b> de la esquina para duplicar el valor hacia abajo o los costados (casilla, desplegable o botón).</div>
          </div>
          <button className="btn ghost" onClick={onClose} style={{ padding: '6px 12px', whiteSpace: 'nowrap' }}>← Volver</button>
        </div>
        <div style={{ overflow: 'auto', flex: 1, minHeight: 0, paddingTop: 12 }}>
          <table style={{ borderCollapse: 'separate', borderSpacing: 0, width: '100%', userSelect: fill ? 'none' : 'auto' }}>
            <thead>
              <tr>
                <th style={{ width: 36, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-light)' }}></th>
                {columnas.map((c, ci) => (
                  <th key={c.id} style={{ padding: '8px 10px', border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)', fontSize: 12.5, fontWeight: 700, color: 'var(--text-primary)', minWidth: 120 }}>{c.label || `Col ${ci + 1}`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>
                  <td style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace', border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.01)' }}>{ri + 1}</td>
                  {columnas.map((c, ci) => {
                    const { role, tipo, opts } = colInfo(c);
                    const v = row[c.id] ?? '';
                    const selected = sel && sel.r === ri && sel.c === ci;
                    const inRange = enRango(ri, ci);
                    const onOver = () => { if (dragRef.current) setFill({ r: ri, c: ci }); };
                    let control;
                    if (tipo === 'toggle') {
                      const two = opts.length >= 2 ? opts : (role === 'manga' ? ['Corta', 'Larga'] : ['A', 'B']);
                      control = (
                        <div style={{ display: 'flex', height: 30 }}>
                          {two.map(o => {
                            const on = v === o;
                            return <button key={o} type="button" onClick={() => { setCell(ri, c.id, o); setSel({ r: ri, c: ci }); }} style={{ flex: 1, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, background: on ? 'var(--accent)' : 'transparent', color: on ? 'var(--bg-primary)' : 'var(--text-secondary)' }}>{o}</button>;
                          })}
                        </div>
                      );
                    } else if (tipo === 'desplegable') {
                      // Combo propio: casilla editable + lista scrolleable y compacta
                      control = (
                        <ComboCell value={v} options={opts}
                          onChange={(val) => setCell(ri, c.id, val)}
                          onFocusCell={() => setSel({ r: ri, c: ci })} />
                      );
                    } else {
                      control = <input type="text" value={v} onFocus={() => setSel({ r: ri, c: ci })} onChange={e => setCell(ri, c.id, e.target.value)} style={cellStyle} />;
                    }
                    return (
                      <td key={c.id} onMouseOver={onOver} onMouseDown={() => setSel({ r: ri, c: ci })}
                        style={{ position: 'relative', border: '1px solid var(--border-light)', padding: 0,
                          boxShadow: selected ? 'inset 0 0 0 2px var(--accent)' : 'none',
                          background: inRange ? 'rgba(0,216,245,0.12)' : 'transparent' }}>
                        {control}
                        {selected && (
                          <span onMouseDown={(e) => { e.stopPropagation(); e.preventDefault(); dragRef.current = { r: ri, c: ci }; setFill({ r: ri, c: ci }); }}
                            title="Arrastrá para duplicar el valor"
                            style={{ position: 'absolute', right: -3, bottom: -3, width: 9, height: 9, background: 'var(--accent)', border: '1.5px solid var(--bg-primary)', borderRadius: 1, cursor: 'crosshair', zIndex: 3, boxShadow: '0 0 4px var(--accent)' }} />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <button className="btn ghost" onClick={addRow} style={{ marginTop: 12, fontSize: 12.5, padding: '7px 14px' }}>+ Agregar fila</button>
        </div>
    </div>
  );
}

// ── Selector EMERGENTE de variantes (talles/tamaños/…) ─────────────────────
// Ventana modal con todas las variantes del molde. Click = una; Shift+click entre
// dos = esas dos y todas las del medio. Devuelve la selección (set) por onChange.
function VariantesPicker({ variantes, seleccion, bloqueadas, onChange, onClose }) {
  const lastRef = useRef(null);
  const sel = new Set(seleccion || []);
  const blk = new Set(bloqueadas || []);   // ya usadas por otro rango: no seleccionables
  const click = (t, idx, e) => {
    if (blk.has(t)) return;
    const set = new Set(sel);
    if (e.shiftKey && lastRef.current != null) {
      const a = Math.min(lastRef.current, idx), b = Math.max(lastRef.current, idx);
      variantes.slice(a, b + 1).forEach(x => { if (!blk.has(x)) set.add(x); });   // saltea las bloqueadas
    } else {
      if (set.has(t)) set.delete(t); else set.add(t);
    }
    lastRef.current = idx;
    onChange([...set]);
  };
  return createPortal(
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 10010, background: 'rgba(2,6,12,0.92)', backdropFilter: 'blur(3px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div onClick={e => e.stopPropagation()} style={{ background: '#0b1622', border: '1px solid var(--border-light)', borderRadius: 14, padding: 18, maxWidth: 560, width: '100%', maxHeight: '82vh', overflow: 'auto', color: '#fff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>Elegí las variantes</h3>
          <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>{sel.size} elegida(s)</span>
        </div>
        <p style={{ margin: '0 0 13px', fontSize: 12, color: 'var(--text-secondary)' }}>Click = una. <b>Shift + click</b> entre dos = esas dos y todas las del medio. Las que ya están en otro rango aparecen <b>deshabilitadas</b>.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
          {(variantes || []).map((t, idx) => {
            const on = sel.has(t), dis = blk.has(t);
            return <button key={t} type="button" disabled={dis} onClick={(e) => click(t, idx, e)}
              style={{ padding: '8px 13px', borderRadius: 9, fontSize: 13, fontWeight: 700, cursor: dis ? 'not-allowed' : 'pointer', userSelect: 'none', opacity: dis ? 0.32 : 1, textDecoration: dis ? 'line-through' : 'none', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.15)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{t}</button>;
          })}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
          <button type="button" className="btn ghost" onClick={() => onChange((seleccion || []).filter(x => false))} style={{ padding: '7px 12px' }}>Limpiar</button>
          <button type="button" className="btn ghost" onClick={() => onChange([...(variantes || [])].filter(x => !blk.has(x)))} style={{ padding: '7px 12px' }}>Todas (libres)</button>
          <button type="button" className="btn primary" onClick={onClose} style={{ padding: '7px 16px', marginLeft: 'auto' }}>Listo</button>
        </div>
      </div>
    </div>,
    document.body
  );
}

// ── Guía: cómo exportar el molde desde cada programa (AI / Corel-PDF / DXF) ──
/* NOMBRAR VARIANTES (talles).
   Un molde puede venir con las capas sin nombrar ("Layer 1", "Capa 3"): sin nombre de variante no hay
   molde utilizable. Acá el usuario les pone nombre. El sistema PROPONE la curva ordenando por
   tamaño (de la más chica a la más grande) y el usuario corrige: el tamaño dice cuál es menor,
   pero no si la menor se llama «0» o «XS». */
// ── Botón de ayuda reusable (§10.d) ────────────────────────────────────────
// PORQUÉ: el panel de Moldería se había llenado de párrafos de explicación que
// tapaban las herramientas. Cada explicación ahora vive detrás de este «?», al
// lado del título de su herramienta: el panel muestra sólo controles y el texto
// aparece en un globo SÓLO cuando el usuario lo pide. Posición FIJA por portal
// (getBoundingClientRect) para que ningún contenedor con overflow lo recorte —
// mismo criterio que el desplegable de ComboCell.
function Ayuda({ children, ancho = 260 }) {
  const btnRef = useRef(null);
  const [pos, setPos] = useState(null);            // {top,left} abierto · null cerrado
  const toggle = (e) => {
    e.stopPropagation();                            // no dispares el click del título/acordeón de atrás
    e.preventDefault();
    if (pos) { setPos(null); return; }
    const r = btnRef.current.getBoundingClientRect();
    // Debajo del «?»; si no entra a la derecha, se corre para no salirse de la pantalla.
    const left = Math.min(r.left, window.innerWidth - ancho - 10);
    setPos({ top: r.bottom + 6, left: Math.max(8, left) });
  };
  // Al hacer scroll el globo quedaría flotando lejos del botón → se cierra (y al redimensionar).
  useEffect(() => {
    if (!pos) return;
    const cerrar = () => setPos(null);
    window.addEventListener('scroll', cerrar, true);
    window.addEventListener('resize', cerrar);
    return () => { window.removeEventListener('scroll', cerrar, true); window.removeEventListener('resize', cerrar); };
  }, [pos]);
  return (
    <>
      <button ref={btnRef} type="button" onClick={toggle} aria-label="Ayuda" title="Ayuda"
        style={{ width: 16, height: 16, flexShrink: 0, padding: 0, borderRadius: 999, lineHeight: 1,
          fontSize: 10.5, fontWeight: 800, fontFamily: 'inherit', cursor: 'pointer', verticalAlign: 'middle',
          border: '1px solid ' + (pos ? 'var(--accent)' : 'var(--border-light)'),
          background: pos ? 'rgba(0,243,255,0.15)' : 'transparent',
          color: pos ? 'var(--accent)' : 'var(--text-muted)' }}>?</button>
      {pos && createPortal(
        <>
          {/* clic afuera cierra el globo */}
          <div onClick={() => setPos(null)} style={{ position: 'fixed', inset: 0, zIndex: 4000 }} />
          <div style={{ position: 'fixed', top: pos.top, left: pos.left, width: ancho, maxWidth: 'calc(100vw - 16px)',
            zIndex: 4001, padding: '10px 12px', borderRadius: 9, background: '#15151a',
            border: '1px solid var(--border-light)', boxShadow: '0 10px 26px rgba(0,0,0,0.55)',
            fontSize: 11.5, fontWeight: 400, lineHeight: 1.5, color: 'var(--text-secondary)',
            textAlign: 'left', textTransform: 'none', letterSpacing: 'normal', whiteSpace: 'normal' }}>
            {children}
          </div>
        </>,
        document.getElementById('root') || document.body
      )}
    </>
  );
}

// Herramienta de VARIANTES (talles). Dos modos, porque hay dos moldes reales (ver §10.c del mapa):
//  · POR CAPA   — el molde trae una capa por talle (sin nombrar o mal nombrada): se le pone nombre
//                 a cada capa. Es lo que hace este componente.
//  · POR PIEZAS — el molde trae TODAS las piezas en una sola capa: no hay capas que nombrar, hay
//                 que seleccionar piezas en el visor. Ese panel vive en App (necesita el visor) y
//                 entra acá como `children`; este componente sólo aporta el marco y el selector.
function NombrarVariantes({ pid, term, onListo, showError, showMsg, modoPiezas, onModo, children }) {
  const [info, setInfo] = React.useState(null);
  const [nombres, setNombres] = React.useState({});
  const [guardando, setGuardando] = React.useState(false);
  const [abierto, setAbierto] = React.useState(false);
  const modoAuto = React.useRef(false);   // el modo se sugiere UNA vez; después manda el usuario

  const cargar = React.useCallback(async () => {
    try {
      const r = await fetch(`/api/plantilla/variantes?pid=${encodeURIComponent(pid)}`);
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo leer el molde'); return; }
      setInfo(d);
      const ini = {};
      (d.sugerencia || []).forEach((capa, i) => { ini[capa] = (d.sugerencia_nombres || [])[i] || capa; });
      setNombres(ini);
    } catch (e) { showError('No se pudo leer el molde: ' + e.message); }
  }, [pid, showError]);

  // Si el molde NO tiene ni un talle reconocido no se puede usar (la detección falla y no se ve
  // nada): en ese caso la herramienta se abre sola, que es lo único que lo destraba.
  // Otro molde = otra radiografía: sin esto la herramienta seguía mostrando la del molde anterior
  // (y sugiriendo su modo), porque `info` sólo se cargaba una vez.
  React.useEffect(() => { setInfo(null); modoAuto.current = false; }, [pid]);
  React.useEffect(() => { if (!info) cargar(); }, [info, cargar]);
  // Se abre sola también cuando hay TRABAJO GUARDADO sin aplicar: si el panel arranca plegado, el
  // usuario vuelve, no ve nada y cree que perdió lo que había hecho (y no encuentra el botón).
  const pzPend = React.useMemo(() => {
    const a = info?.asignacion_piezas || {}, b = info?.asignacion_piezas_aplicada || {};
    const ks = Object.keys(a);
    return ks.length > 0 && (ks.length !== Object.keys(b).length || ks.some(k => a[k] !== b[k]));
  }, [info]);
  // «Falta nombrar» es del ARCHIVO (`sin_talles`), no del MOLDE: un molde ya resuelto POR PIEZAS
  // tiene el archivo original con una sola capa para siempre y seguía anunciando que falta todo.
  const faltaNombrar = !!info?.sin_talles && !info?.resuelto;
  React.useEffect(() => { if (faltaNombrar || pzPend) setAbierto(true); }, [faltaNombrar, pzPend]);
  // El modo lo decide el MOLDE: con 2+ capas de talle se nombra por capa; con una sola capa que
  // trae todas las piezas hay que repartirlas a mano. Se sugiere una sola vez (el usuario manda).
  React.useEffect(() => {
    if (!info) return;
    // Un molde que YA se definió POR PIEZAS se queda por piezas, siempre. Después de aplicar, sus
    // capas son LAS QUE CREAMOS NOSOTROS (una por variante), así que "tiene 2+ capas de talle" ya
    // no significa que sea un molde por capas: volver a modo capa mandaba al usuario a renombrar
    // las capas que él mismo acababa de definir.
    const yaPorPiezas = Object.keys(info.asignacion_piezas || {}).length > 0
      || Object.keys(info.asignacion_piezas_aplicada || {}).length > 0;
    // …pero el VISOR sólo se pone en «elegir piezas» si la herramienta está a la vista o si de
    // verdad falta hacer algo. Antes se activaba siempre: al abrir la Moldería de un molde ya
    // terminado, el visor pasaba a la vista del archivo ORIGINAL (36 piezas de «Capa 1», rótulos
    // encimados) con el panel PLEGADO — el usuario nunca lo pidió y no tenía cómo salir.
    if (onModo && (yaPorPiezas || info.modo_sugerido === 'piezas')) {
      onModo(abierto || faltaNombrar || pzPend);
      return;
    }
    // para el resto, la sugerencia corre una sola vez (el modo por capa ya es el de por defecto):
    // así un molde normal no dispara una recarga del visor cada vez que se abre la Moldería
    if (modoAuto.current) return;
    modoAuto.current = true;
  }, [info, onModo, abierto, faltaNombrar, pzPend]);

  // ¿parece que las capas NO están nombradas? (nombres tipo "Layer 3", "Capa 2", "Path 7")
  const sinNombrar = (info?.sugerencia || []).filter(c => /^(layer|capa|path|group|grupo)[\s_-]*\d*$/i.test(String(c).trim())).length;

  const aplicarCurva = (estilo) => {
    const capas = info?.sugerencia || [];
    const letras = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL', '7XL'];
    const ninos = ['0', '1', '2', '4', '6', '8', '10', '12', '14', '16'];
    let vals;
    if (estilo === 'numeros') vals = capas.map((_, i) => String(i + 1));
    else if (estilo === 'ninos') vals = capas.map((_, i) => ninos[i] ?? String(18 + (i - ninos.length) * 2));
    else {
      const i0 = Math.max(0, Math.floor((letras.length - capas.length) / 2) - 1);
      vals = capas.map((_, i) => letras[i0 + i] ?? `${i0 + i - 5}XL`);
    }
    const n = {}; capas.forEach((c, i) => { n[c] = vals[i]; }); setNombres(n);
  };

  const guardar = async () => {
    const vals = Object.values(nombres).map(v => String(v || '').trim());
    if (vals.some(v => !v)) { showError('Faltan nombres: cada variante tiene que tener el suyo'); return; }
    if (new Set(vals).size !== vals.length) { showError('Hay dos variantes con el mismo nombre'); return; }
    setGuardando(true);
    try {
      const r = await fetch('/api/plantilla/variantes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid, nombres }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudieron aplicar los nombres'); return; }
      showMsg(`${d.renombradas} ${term.variante.toLowerCase()}s nombradas. Ahora indicá qué es cada pieza.`);
      setInfo(null); setAbierto(false);
      onListo && onListo();
    } catch (e) { showError('No se pudo guardar: ' + e.message); }
    finally { setGuardando(false); }
  };

  return (
    <div style={{ border: '1px solid var(--border-light)', borderRadius: 10, overflow: 'hidden' }}>
      {/* Header como div (no button): así el «?» de ayuda puede ir anidado sin
          botón dentro de botón, y su stopPropagation evita abrir/cerrar el acordeón. */}
      <div role="button" tabIndex={0} onClick={() => setAbierto(a => !a)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setAbierto(a => !a); } }}
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '10px 12px', background: faltaNombrar ? 'rgba(245,165,36,0.10)' : 'rgba(255,255,255,0.02)', border: 0, color: '#fff', cursor: 'pointer', textAlign: 'left' }}>
        <span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, fontWeight: 700 }}>
            {faltaNombrar ? `⚠ Falta nombrar las ${term.variante.toLowerCase()}s` : `Nombrar ${term.variante.toLowerCase()}s`}
            <Ayuda ancho={250}>Si el molde vino con las capas sin nombre, decile cuál es cada {term.variante.toLowerCase()}</Ayuda>
          </span>
          {/* Sólo el ESTADO queda a la vista (aviso/✓ resuelto); la explicación se fue al «?». */}
          {(faltaNombrar || info?.resuelto) && (
            <span style={{ display: 'block', fontSize: 10.5, color: faltaNombrar ? 'var(--warning, #f5a524)' : 'var(--text-muted)' }}>
              {faltaNombrar
                ? (info?.una_sola_capa
                    ? 'El molde vino con todo en una sola capa: seleccioná las piezas de cada variante y escribile el nombre'
                    : `El molde no tiene ninguna capa con nombre de ${term.variante.toLowerCase()}: hasta que las nombres no se puede usar`)
                : `✓ ${(info.talles_registrados || []).length} ${term.variante.toLowerCase()}s definidas: ${(info.variantes_piezas?.length ? info.variantes_piezas : info.talles_registrados || []).join(' · ')}. Abrí sólo si querés corregirlas.`}
            </span>
          )}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          {pzPend && <span style={{ fontSize: 9.5, fontWeight: 700, padding: '2px 7px', borderRadius: 20, background: 'rgba(245,165,36,0.18)', color: 'var(--warning, #f5a524)', whiteSpace: 'nowrap' }}>guardado · falta aplicar</span>}
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{abierto ? '▲' : '▾'}</span>
        </span>
      </div>

      {abierto && (
        <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 10, borderTop: '1px solid var(--border-light)' }}>
          {!info ? <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Leyendo el molde…</div> : (
            <>
              <div style={{ display: 'flex', gap: 6, padding: 3, borderRadius: 9, background: 'rgba(0,0,0,0.25)' }}>
                {[[false, 'Por capa', `cada ${term.variante.toLowerCase()} en su capa`], [true, 'Por piezas', 'todo en una capa']].map(([m, lbl, sub]) => (
                  <button key={String(m)} type="button" onClick={() => onModo && onModo(m)} title={sub}
                    style={{ flex: 1, padding: '6px 4px', fontSize: 11, fontWeight: 700, borderRadius: 7, cursor: 'pointer', border: '1px solid ' + (modoPiezas === m ? 'var(--accent)' : 'transparent'), background: modoPiezas === m ? 'rgba(0,243,255,0.12)' : 'transparent', color: modoPiezas === m ? 'var(--accent)' : 'var(--text-muted)' }}>
                    {lbl}
                  </button>
                ))}
              </div>
            </>
          )}
          {info && modoPiezas ? children : null}
          {!info || modoPiezas ? null : (
            <>
              <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Encontré <b>{info.total_talles}</b> {term.variante.toLowerCase()}s, ordenadas de la más
                chica a la más grande. {info.formato === 'anidado'
                  ? 'Están dibujadas una encima de otra (molde anidado), así que se nombran por capa.'
                  : 'Cada una ocupa su propio bloque.'}
                {sinNombrar > 0 && <> <b style={{ color: 'var(--warning, #f5a524)' }}>{sinNombrar} sin nombrar.</b></>}
              </div>

              <div style={{ display: 'flex', gap: 6 }}>
                {[['letras', 'S · M · L'], ['numeros', '1 · 2 · 3'], ['ninos', '0 · 2 · 4']].map(([k, lbl]) => (
                  <button key={k} type="button" onClick={() => aplicarCurva(k)}
                    style={{ flex: 1, padding: '5px 4px', fontSize: 10.5, fontWeight: 700, borderRadius: 7, cursor: 'pointer', border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)' }}>
                    {lbl}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 300, overflowY: 'auto' }}>
                {(info.sugerencia || []).map((capa, i) => (
                  <div key={capa} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ width: 20, fontSize: 10, color: 'var(--text-muted)', textAlign: 'right' }}>{i + 1}</span>
                    <span style={{ flex: 1, minWidth: 0, fontSize: 11, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={`capa del archivo: ${capa}`}>{capa}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>→</span>
                    <input value={nombres[capa] ?? ''} onChange={e => setNombres(n => ({ ...n, [capa]: e.target.value }))}
                      style={{ width: 84, padding: '4px 7px', fontSize: 12, fontWeight: 700, borderRadius: 6, border: '1px solid var(--border-light)', background: 'rgba(0,0,0,0.25)', color: '#fff' }} />
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button type="button" className="btn success" disabled={guardando} onClick={guardar}
                  style={{ flex: 1, fontSize: 12 }}>
                  {guardando ? 'Aplicando…' : `Aplicar a ${(info.sugerencia || []).length} ${term.variante.toLowerCase()}s`}
                </button>
                <Ayuda ancho={240}>El archivo original no se toca: se guarda una versión nueva del molde con las capas nombradas.</Ayuda>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function AyudaExportMolde({ term }) {
  const V = (term?.variante || 'talle').toLowerCase();
  const secc = {
    marginTop: 10, padding: 12, borderRadius: 10, background: 'rgba(255,255,255,0.03)',
    border: '1px solid var(--border-light)', fontSize: 11.5, lineHeight: 1.5, color: 'var(--text-secondary)'
  };
  const h = { fontSize: 12.5, fontWeight: 700, color: '#fff', marginBottom: 5, display: 'flex', gap: 6, alignItems: 'center' };
  const li = { margin: '2px 0' };
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 }}>
        El sistema necesita 3 cosas del molde: las <b>piezas como vectores</b>, cada <b>{V}</b> por separado, y (si podés) el <b>nombre de cada pieza</b>. Si el molde <b>trae los nombres</b>, se aplican <b>solos</b> (no hay que reescribirlos); si no, los ponés una vez en el visor. Elegí tu programa:
      </div>

      <div style={secc}>
        <div style={h}>🅰️ Illustrator (.ai) — recomendado hoy</div>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li style={li}>Guardá como <b>.ai con compatibilidad PDF activada</b> (Illustrator lo hace por defecto).</li>
          <li style={li}>Cada <b>{V}</b> en su <b>propia capa</b>, con el nombre exacto del {V} (M, 3XL, 16…).</li>
          <li style={li}>Las piezas en <b>vectores</b> (trazados), no imágenes.</li>
          <li style={li}>Capa <b>guías</b> con el <b>nombre de cada pieza</b> como texto (ej. <code>manga corta derecha</code>) → el arte se mapea solo.</li>
        </ul>
      </div>

      <div style={secc}>
        <div style={h}>🅲 CorelDRAW u otro → PDF</div>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li style={li}>Exportá/Publicá como <b>PDF</b> (Archivo → Publicar como PDF).</li>
          <li style={li}>Que <b>NO rasterice</b>: dejá las piezas como <b>curvas/vectores</b> (sin “convertir a mapa de bits”).</li>
          <li style={li}>Cada <b>{V}</b> en una <b>capa</b> del documento (Corel exporta las capas al PDF).</li>
          <li style={li}>Nombres de pieza como <b>texto</b> en una capa <b>guías</b> (opcional, pero mapea el arte solo).</li>
          <li style={li}>Subilo acá como <b>.pdf</b>. El sistema lo lee igual que un .ai.</li>
        </ul>
      </div>

      <div style={secc}>
        <div style={h}>📐 Optitex / Gerber / Lectra / Audaces → DXF <span style={{ fontSize: 10, color: 'var(--warning)', fontWeight: 700 }}>BETA</span></div>
        <ul style={{ margin: 0, paddingLeft: 16 }}>
          <li style={li}>Exportá como <b>DXF-AAMA</b> o <b>DXF-ASTM</b> (no “DXF plano”).</li>
          <li style={li}>Tildá <b>exportar todos los {V}s / graduación</b> (que salga cada {V}, no uno solo).</li>
          <li style={li}>Incluí <b>nombres de pieza</b> y, si podés, piquetes/notches.</li>
          <li style={li}>En Optitex: <i>Guardar como → DXF</i>, formato <b>AAMA</b>, “All sizes”.</li>
          <li style={li}>Subilo acá como <b>.dxf</b> → el sistema lo convierte a piezas + {V}s automáticamente.</li>
          <li style={{ ...li, color: 'var(--warning)' }}>⚠️ Está en beta: si algún {V} o pieza no queda bien, avisá y lo ajustamos con tu archivo.</li>
        </ul>
      </div>
    </div>
  );
}

// ── Modal de configuración de tamaño de UNA capa editable (crear/editar) ────
function EditableTamanoModal({ inicial, variantes, esNueva, onGuardar, onEliminar, onCerrar }) {
  const [d, setD] = useState(() => JSON.parse(JSON.stringify(inicial || { capa: '', rangos: [] })));
  const [pickerJ, setPickerJ] = useState(null);
  const nuevoRango = () => ({ variantes: [], mantener: false, apaisado: { ancho: '', alto: '' }, vertical: { ancho: '', alto: '' } });
  const numSt = { width: 60, textAlign: 'center', padding: '6px 6px', borderRadius: 8, fontSize: 12.5, background: 'rgba(255,255,255,0.04)', color: '#fff', border: '1px solid var(--border-light)' };
  const delBtn = { width: 26, height: 26, flexShrink: 0, borderRadius: 7, border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 13, lineHeight: 1 };
  const upRango = (j, fn) => setD(s => ({ ...s, rangos: s.rangos.map((r, m) => m === j ? fn(r) : r) }));
  const addRango = () => setD(s => ({ ...s, rangos: [...(s.rangos || []), nuevoRango()] }));
  const delRango = (j) => setD(s => ({ ...s, rangos: s.rangos.filter((_, m) => m !== j) }));
  const setBox = (j, caja, dim, val) => upRango(j, r => ({ ...r, [caja]: { ...(r[caja] || {}), [dim]: val } }));
  const setMantener = (j, val) => upRango(j, r => ({ ...r, mantener: val }));
  const bloqueadasDe = (j) => new Set((d.rangos || []).filter((_, k) => k !== j).flatMap(r => r.variantes || []));
  const chip = (txt, on, fn) => (<button type="button" onClick={fn} style={{ padding: '5px 11px', borderRadius: 999, fontSize: 12, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{txt}</button>);
  const cajaUI = (titulo, sub, r, j, caja) => (
    <div style={{ flex: 1, minWidth: 190, padding: '8px 10px', borderRadius: 9, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)' }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{titulo}</div>
      <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginBottom: 7 }}>{sub}</div>
      <div style={{ display: 'flex', gap: 7, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>Ancho</span>
        <input type="number" step="0.1" min="0" placeholder="cm" value={(r[caja] || {}).ancho ?? ''} onChange={e => setBox(j, caja, 'ancho', e.target.value)} style={numSt} />
        <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>Alto</span>
        <input type="number" step="0.1" min="0" placeholder="cm" value={(r[caja] || {}).alto ?? ''} onChange={e => setBox(j, caja, 'alto', e.target.value)} style={numSt} />
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>cm</span>
      </div>
    </div>
  );
  return createPortal(
    <div onClick={onCerrar} style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(2,6,12,0.92)', backdropFilter: 'blur(3px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div onClick={e => e.stopPropagation()} style={{ background: '#0b1622', border: '1px solid var(--border-light)', borderRadius: 14, padding: 18, maxWidth: 640, width: '100%', maxHeight: '88vh', overflow: 'auto', color: '#fff', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h3 style={{ margin: 0, fontSize: 16 }}>{esNueva ? 'Registrar capa editable' : 'Editar capa'}</h3>
          <button type="button" onClick={onCerrar} title="Cerrar" style={{ ...delBtn, marginLeft: 'auto' }}>✕</button>
        </div>
        <input value={d.capa || ''} onChange={e => setD(s => ({ ...s, capa: e.target.value }))} placeholder="Nombre de la capa (ej. Editable escudo)"
          style={{ padding: '9px 11px', borderRadius: 8, fontSize: 13.5, fontWeight: 600, background: 'rgba(255,255,255,0.04)', color: '#fff', border: '1px solid var(--border-light)' }} />
        {(d.rangos || []).map((r, j) => (
          <div key={j} style={{ padding: '9px 10px', borderRadius: 9, border: '1px dashed var(--border-light)', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button type="button" onClick={() => setPickerJ(j)} className="btn ghost" style={{ flex: 1, textAlign: 'left', padding: '7px 11px', fontSize: 12.5 }}>
                {(r.variantes || []).length
                  ? <span><b style={{ color: 'var(--accent)' }}>{r.variantes.length}</b> variante(s): {r.variantes.slice(0, 10).join(', ')}{r.variantes.length > 10 ? '…' : ''}</span>
                  : <span style={{ color: 'var(--text-muted)' }}>Elegir variantes →</span>}
              </button>
              <button type="button" onClick={() => delRango(j)} title="Quitar rango" style={delBtn}>✕</button>
            </div>
            <div style={{ display: 'flex', gap: 7, alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>Tamaño:</span>
              {chip('Medida específica', !r.mantener, () => setMantener(j, false))}
              {chip('Mantener medida del diseño', !!r.mantener, () => setMantener(j, true))}
            </div>
            {r.mantener
              ? <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.45 }}>El objeto conserva su <b>tamaño original del diseño</b> (no escala con la variante). Se reubica como si escalara.</div>
              : <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>{cajaUI('Apaisado', 'más ancho que alto', r, j, 'apaisado')}{cajaUI('Vertical', 'más alto que ancho', r, j, 'vertical')}</div>}
          </div>
        ))}
        <button type="button" onClick={addRango} className="btn ghost" style={{ alignSelf: 'flex-start', padding: '6px 12px', fontSize: 12.5 }}>+ rango de variantes</button>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
          {!esNueva && <button type="button" className="btn ghost" onClick={() => onEliminar()} style={{ padding: '8px 14px', color: '#ff6b6b', borderColor: 'rgba(255,107,107,0.4)' }}>Eliminar</button>}
          <button type="button" className="btn ghost" onClick={onCerrar} style={{ padding: '8px 14px', marginLeft: 'auto' }}>Cancelar</button>
          <button type="button" className="btn primary" onClick={() => onGuardar(d)} style={{ padding: '8px 18px' }} disabled={!(d.capa || '').trim()}>Guardar</button>
        </div>
        {pickerJ != null && (
          <VariantesPicker variantes={variantes}
            seleccion={(d.rangos[pickerJ] || {}).variantes || []}
            bloqueadas={bloqueadasDe(pickerJ)}
            onChange={(vs) => upRango(pickerJ, r => ({ ...r, variantes: vs }))}
            onClose={() => setPickerJ(null)} />
        )}
      </div>
    </div>,
    document.body
  );
}

// ── Espacio INFINITO de las mesas de tizada ───────────────────────────────
// Zoom con la rueda SOLO sobre este espacio (no scrollea la página). Pan con
// el CLICK DERECHO arrastrando. Cada mesa a ESCALA REAL entre sí. El nombre se
// renombra con doble-click (se guarda al clickear afuera) y el archivo se
// descarga con ese nombre. Botón de descarga = solo el ícono, arriba a la izq.
// Zoom MÁXIMO del espacio de mesas. A zoom 1 la escala real es PXM=240 px/m; con 300 se llega a
// ~72000 px/m (≈720 px/cm) → una etiqueta de ~3 cm cubre toda la pantalla. Las mesas son SVG
// (vectorial: el navegador lo repinta a cualquier escala, no se pixela) → el techo lo pone esta
// constante, no la resolución del archivo.
const ZMAX = 300;

// ── Catálogo de fuentes: vista previa con la tipografía REAL ──
// Familia CSS única por fuente (el hash del archivo). El nombre interno no sirve como familia:
// puede repetirse, traer espacios/comillas y chocar con una fuente instalada en la PC.
const _famFuente = (f) => 'tzf_' + String(f.hash || f.archivo || '').replace(/[^a-zA-Z0-9]/g, '');
// Muestra por defecto (cuando el campo de prueba está vacío).
const MUESTRA_DEF = 'USER PRO 10';

// ── MARCO de colocación de un objeto sobre una pieza (ÚNICA fuente de verdad del frontend) ──
// Devuelve el rectángulo donde vive el objeto (x,y,w,h) y su centro/tamaño en fracciones de ese
// rectángulo. Lo usan TODAS las vistas (editor y visor del Arte); el motor hace la misma cuenta
// (`pos_marco_pieza` / `_pos_en_pieza`). Tener un solo resolvedor es lo que evita que una vista
// dibuje en un lugar y otra en otro.
//
//  · marco "arte"  → el objeto viene DENTRO del diseño: se escala y centra CON el diseño (la mesa
//                    del arte se ajusta al ALTO de la pieza y se centra a lo ancho).
//  · marco "pieza" → el objeto lo AGREGÓ el usuario: se mide contra la PIEZA (cm reales). No
//                    depende de la mesa del arte, que cambia de tamaño según el rango — atarlo a
//                    ella provocaba que se viera corrido al cambiar de rango.
// `aspMesa` = aspecto (ancho/alto) de la mesa del arte que ESA vista está dibujando para esa
// pieza y ese talle. Es un parámetro y no un dato del objeto porque las mesas cambian de tamaño
// según el rango: fijar una sola era lo que hacía que el objeto se viera corrido al cambiar de
// rango. El motor hace la misma cuenta en `pos_agregado_en_diseno`.
const marcoDeObjeto = (o, p, aspMesa) => {
  const mr = o.mesa_rect, bb = o.bbox_mu;
  // El diseño se coloca escalando al ALTO de la pieza y centrando el ancho.
  const aspecto = aspMesa || ((mr && mr[3]) ? mr[2] / mr[3] : (p.pw / p.ph));
  const h = p.ph, w = aspecto * h;
  const marco = { x: p.px + (p.pw - w) / 2, y: p.py, w, h };
  if (o._agregado) {
    // AGREGADO: vive DENTRO del diseño (como un editable del arte) → escala con él. Su tamaño
    // sale de sus cm reales contra el tamaño del DISEÑO sobre la pieza.
    const anchoDisenoCm = aspecto * (p.h_cm || 0);
    return {
      ...marco, fcx: 0.5, fcy: 0.5,
      fw: (o.w_cm > 0 && anchoDisenoCm > 0) ? o.w_cm / anchoDisenoCm : 0.3,
      fh: (o.h_cm > 0 && p.h_cm > 0) ? o.h_cm / p.h_cm : 0.3,
    };
  }
  return {
    ...marco,
    fcx: (mr && bb) ? ((bb[0] + bb[2]) / 2 - mr[0]) / mr[2] : 0.5,
    fcy: (mr && bb) ? ((bb[1] + bb[3]) / 2 - mr[1]) / mr[3] : 0.5,
    fw: (mr && bb) ? (bb[2] - bb[0]) / mr[2] : 0.3,
    fh: (mr && bb) ? (bb[3] - bb[1]) / mr[3] : 0.3,
  };
};

// ── Controles del laboratorio de fuentes (estilo programa de diseño) ──
// Paleta de la muestra: colores planos + el acento del sistema.
const _PALETA = ['#ffffff', '#000000', '#111417', '#e11d2e', '#f5a524', '#f7e733', '#17c964',
  '#00f3ff', '#1d4ed8', '#7c3aed', '#ec4899', '#9ca3af'];

// Botón de color con paleta propia (nada de <input type=color> pelado).
function SwatchColor({ value, onChange, titulo }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const fuera = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', fuera);
    return () => document.removeEventListener('mousedown', fuera);
  }, [open]);
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button type="button" onClick={() => setOpen(o => !o)} title={titulo}
        style={{ display: 'flex', alignItems: 'center', gap: 6, height: 30, padding: '0 8px', borderRadius: 7, cursor: 'pointer',
          border: '1px solid ' + (open ? 'var(--accent)' : 'var(--border-light)'), background: 'rgba(255,255,255,0.04)' }}>
        <span style={{ width: 16, height: 16, borderRadius: 4, background: value, border: '1px solid rgba(255,255,255,0.25)' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)' }}>{titulo}</span>
      </button>
      {open && (
        <div style={{ position: 'absolute', top: 36, left: 0, zIndex: 20, padding: 10, borderRadius: 10, width: 172,
          border: '1px solid var(--border-light)', background: 'var(--bg-card, #14181c)', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 6, marginBottom: 9 }}>
            {_PALETA.map(c => (
              <button key={c} type="button" onClick={() => { onChange(c); setOpen(false); }} title={c}
                style={{ width: 20, height: 20, borderRadius: 5, cursor: 'pointer', background: c,
                  border: '2px solid ' + (value.toLowerCase() === c ? 'var(--accent)' : 'rgba(255,255,255,0.2)') }} />
            ))}
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' }}>
            <input type="color" value={value} onChange={(e) => onChange(e.target.value)}
              style={{ width: 22, height: 22, padding: 0, border: 'none', background: 'none', cursor: 'pointer' }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>Personalizado</span>
          </label>
        </div>
      )}
    </div>
  );
}

// Campo numérico con desplegable de valores típicos (el <select> nativo queda fuera de estilo).
function NumeroConMenu({ value, onChange, opciones, min, max, step = 1, sufijo = '', ancho = 52 }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return;
    const fuera = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', fuera);
    return () => document.removeEventListener('mousedown', fuera);
  }, [open]);
  const cl = (v) => Math.max(min, Math.min(max, v));
  return (
    <div ref={ref} style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
      <input type="number" value={value} min={min} max={max} step={step}
        onChange={(e) => onChange(cl(parseFloat(e.target.value) || 0))}
        style={{ width: ancho, height: 30, padding: '0 4px 0 7px', fontSize: 12, fontWeight: 700, textAlign: 'left',
          borderRadius: '7px 0 0 7px', borderRight: 'none', border: '1px solid var(--border-light)',
          background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary, #fff)', outline: 'none' }} />
      <button type="button" onClick={() => setOpen(o => !o)} title="Valores típicos"
        style={{ height: 30, width: 18, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          borderRadius: '0 7px 7px 0', fontSize: 8, color: 'var(--text-muted)',
          border: '1px solid ' + (open ? 'var(--accent)' : 'var(--border-light)'), background: 'rgba(255,255,255,0.04)' }}>▼</button>
      {open && (
        <div style={{ position: 'absolute', top: 34, left: 0, zIndex: 20, minWidth: 74, padding: 4, borderRadius: 9, maxHeight: 210, overflowY: 'auto',
          border: '1px solid var(--border-light)', background: 'var(--bg-card, #14181c)', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
          {opciones.map(o => (
            <button key={o} type="button" onClick={() => { onChange(o); setOpen(false); }}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '5px 8px', borderRadius: 6, cursor: 'pointer', border: 'none',
                fontSize: 11.5, fontWeight: 700, background: value === o ? 'rgba(0,243,255,0.12)' : 'transparent',
                color: value === o ? 'var(--accent)' : 'var(--text-secondary)' }}>{o}{sufijo}</button>
          ))}
        </div>
      )}
    </div>
  );
}

// piezas de la barra de herramientas
const _grp = { display: 'flex', alignItems: 'center', gap: 6 };
const _sep = { width: 1, height: 20, background: 'var(--border-light)' };
const IcoLab = ({ d }) => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7"
    strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--text-muted)', flexShrink: 0 }}><path d={d} /></svg>
);

// ── LOGIN: la puerta del sistema. Sin sesión no se ve nada más. ──────────────
function LoginScreen({ onLogin }) {
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const entrar = async (e) => {
    e?.preventDefault();
    setError(''); setCargando(true);
    try {
      const r = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usuario: usuario.trim(), password }) });
      const d = await r.json();
      if (!r.ok) { setError(d.error || 'No se pudo entrar'); setCargando(false); return; }
      onLogin(d.usuario);
    } catch (err) { setError('No hay conexión con el servidor.'); setCargando(false); }
  };
  const inp = { width: '100%', padding: '12px 14px', fontSize: 14, borderRadius: 10, marginBottom: 12,
    background: 'rgba(255,255,255,0.04)', color: '#fff', border: '1px solid var(--border-light)', outline: 'none' };
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg, #0a0d0f)', padding: 20 }}>
      <form onSubmit={entrar} style={{ width: '100%', maxWidth: 380, padding: 32, borderRadius: 16,
        background: 'var(--bg-card, #14181c)', border: '1px solid var(--border-light)', boxShadow: '0 20px 60px rgba(0,0,0,0.5)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
          <img src="/logo.svg" alt="" style={{ width: 42, height: 42 }} />
          <div><h1 style={{ margin: 0, fontSize: 22 }}><span style={{ color: 'var(--accent)' }}>USER</span> PRO</h1></div>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 22px' }}>Iniciá sesión para continuar.</p>
        <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Usuario</label>
        <input style={inp} value={usuario} onChange={e => setUsuario(e.target.value)} autoFocus autoComplete="username" />
        <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Contraseña</label>
        <input style={inp} type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" />
        {error && <div style={{ fontSize: 12.5, color: 'var(--danger, #ff4d4f)', fontWeight: 600, margin: '2px 0 14px' }}>{error}</div>}
        <button type="submit" className="btn primary" disabled={cargando}
          style={{ width: '100%', padding: '12px', fontSize: 14, fontWeight: 700, marginTop: 6, opacity: cargando ? 0.6 : 1 }}>
          {cargando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}

// ── USUARIOS / ROLES / PERMISOS ──────────────────────────────────────────────
// Los permisos se resuelven en el SERVIDOR. Acá se pinta la UI: ocultar un botón NO es
// proteger nada (la API igual rechaza), es sólo no mostrarle a alguien lo que no puede usar.
function PantallaUsuarios({ onVolver, showMsg, showError, yo }) {
  const [tab, setTab] = useState('usuarios');
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [editUsr, setEditUsr] = useState(null);   // usuario en edición (null = cerrado; {} = nuevo)
  const [editRol, setEditRol] = useState(null);
  const [confirmar, setConfirmar] = useState(null);  // {tipo:'usuario'|'rol', id, label}

  const recargar = async () => {
    setCargando(true);
    try {
      const [u, r, p] = await Promise.all([
        fetch('/api/usuarios').then(x => x.json()),
        fetch('/api/roles').then(x => x.json()),
        fetch('/api/permisos').then(x => x.json()),
      ]);
      if (u.usuarios) setUsuarios(u.usuarios);
      if (r.roles) setRoles(r.roles);
      if (p.permisos) setPermisos(p.permisos);
      if (u.error) showError(u.error);
    } catch (e) { showError('No se pudo leer usuarios: ' + e.message); }
    setCargando(false);
  };
  useEffect(() => { recargar(); }, []);

  const puedeGestionar = (yo?.permisos || []).includes('usuario.gestionar');

  const guardarUsuario = async () => {
    const u = editUsr;
    if (!u.usuario?.trim()) { showError('Falta el usuario'); return; }
    if (!u.id && (u.password || '').length < 8) { showError('La contraseña tiene que tener al menos 8 caracteres'); return; }
    const body = { usuario: u.usuario.trim(), nombre: u.nombre || u.usuario, email: u.email || '', roles: u.roles || [] };
    if (u.password) body.password = u.password;
    if (u.id) body.activo = u.activo !== false;
    const r = await fetch(u.id ? `/api/usuarios/${u.id}` : '/api/usuarios',
      { method: u.id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const d = await r.json();
    if (!r.ok) { showError(d.error || 'No se pudo guardar'); return; }
    setEditUsr(null); showMsg(u.id ? 'Usuario actualizado.' : 'Usuario creado.'); recargar();
  };

  const guardarRol = async () => {
    const g = editRol;
    if (!g.id && !g.clave?.trim()) { showError('Falta la clave del rol'); return; }
    const body = { nombre: g.nombre || g.clave, descripcion: g.descripcion || '' };
    if (!g.id) body.clave = g.clave.trim();
    if (!g.es_sistema) body.permisos = g.permisos || [];   // el rol de sistema no cambia permisos
    const r = await fetch(g.id ? `/api/roles/${g.id}` : '/api/roles',
      { method: g.id ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const d = await r.json();
    if (!r.ok) { showError(d.error || 'No se pudo guardar'); return; }
    setEditRol(null); showMsg(g.id ? 'Rol actualizado.' : 'Rol creado.'); recargar();
  };

  const borrar = async () => {
    const c = confirmar;
    const r = await fetch(`/api/${c.tipo === 'usuario' ? 'usuarios' : 'roles'}/${c.id}`, { method: 'DELETE' });
    const d = await r.json();
    setConfirmar(null);
    if (!r.ok) { showError(d.error || 'No se pudo eliminar'); return; }
    showMsg((c.tipo === 'usuario' ? 'Usuario' : 'Rol') + ' eliminado.'); recargar();
  };

  const inp = { width: '100%', padding: '9px 11px', fontSize: 13, borderRadius: 8, background: 'rgba(255,255,255,0.04)',
    color: 'var(--text-primary, #fff)', border: '1px solid var(--border-light)', outline: 'none' };
  const lbl = { fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', display: 'block', marginBottom: 5 };
  const chipRol = (clave, on, fn) => (
    <button key={clave} type="button" onClick={fn} style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700,
      cursor: fn ? 'pointer' : 'default', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'),
      background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{clave}</button>
  );
  const porModulo = {};
  permisos.forEach(p => { (porModulo[p.modulo] = porModulo[p.modulo] || []).push(p); });

  return (
    <div className="panel animate-fade">
      <div style={{ marginBottom: 20 }}>
        <button className="btn ghost" onClick={onVolver} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
          ⬅ Volver al Panel de Configuración
        </button>
      </div>
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
        <div>
          <h2>Usuarios y permisos</h2>
          <p>Quién usa el sistema y qué puede hacer. Los permisos se aplican en el servidor.</p>
        </div>
        {puedeGestionar && (
          <button className="btn primary" style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}
            onClick={() => tab === 'usuarios' ? setEditUsr({ roles: [], activo: true }) : setEditRol({ permisos: [] })}>
            <Icon name="plus" style={{ width: 14, height: 14 }} /> {tab === 'usuarios' ? 'Nuevo usuario' : 'Nuevo rol'}
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        {[['usuarios', 'Usuarios', usuarios.length], ['roles', 'Roles', roles.length], ['permisos', 'Permisos', permisos.length]].map(([k, t, n]) => (
          <button key={k} type="button" onClick={() => setTab(k)} style={{ padding: '7px 14px', borderRadius: 8, fontSize: 12.5, fontWeight: 700, cursor: 'pointer',
            border: '1px solid ' + (tab === k ? 'var(--accent)' : 'var(--border-light)'),
            background: tab === k ? 'rgba(0,243,255,0.12)' : 'transparent', color: tab === k ? 'var(--accent)' : 'var(--text-muted)' }}>{t} ({n})</button>
        ))}
      </div>

      {cargando && <div className="card" style={{ padding: 20, fontSize: 13, color: 'var(--text-muted)' }}>Cargando…</div>}

      {/* ── USUARIOS ── */}
      {!cargando && tab === 'usuarios' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {usuarios.map((u, i) => (
            <div key={u.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
              borderTop: i ? '1px solid var(--border-light)' : 'none', opacity: u.activo ? 1 : 0.5 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'rgba(0,243,255,0.12)', color: 'var(--accent)', fontWeight: 800, fontSize: 13 }}>
                {(u.nombre || u.usuario).slice(0, 1).toUpperCase()}
              </div>
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ fontSize: 13.5, fontWeight: 700 }}>
                  {u.nombre} <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>· {u.usuario}</span>
                  {u.id === yo?.id && <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--accent)' }}>(vos)</span>}
                  {!u.activo && <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--text-muted)' }}>inactivo</span>}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {u.ultimo_acceso ? 'Último acceso: ' + u.ultimo_acceso.slice(0, 16).replace('T', ' ') : 'Nunca entró'}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 5, flexShrink: 0 }}>{(u.roles || []).map(r => chipRol(r, true, null))}</div>
              {puedeGestionar && (
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  <button type="button" onClick={() => setEditUsr({ ...u, password: '' })} title="Editar"
                    style={{ width: 26, height: 26, borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>
                    <Icon name="edit" style={{ width: 12, height: 12 }} />
                  </button>
                  <button type="button" onClick={() => setConfirmar({ tipo: 'usuario', id: u.id, label: u.usuario })} title="Eliminar"
                    style={{ width: 26, height: 26, borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>
                    <Icon name="trash" style={{ width: 12, height: 12 }} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── ROLES ── */}
      {!cargando && tab === 'roles' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
          {roles.map(r => (
            <div key={r.id} className="card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 7 }}>
                    <Icon name="shield" style={{ width: 13, height: 13, color: 'var(--accent)' }} /> {r.nombre}
                    {r.es_sistema && <span className="badge success" style={{ fontSize: 9 }}>sistema</span>}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{r.clave} · {r.usuarios} usuario/s</div>
                </div>
                {puedeGestionar && (
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    <button type="button" onClick={() => setEditRol({ ...r })} title="Editar"
                      style={{ width: 24, height: 24, borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>
                      <Icon name="edit" style={{ width: 11, height: 11 }} />
                    </button>
                    {!r.es_sistema && (
                      <button type="button" onClick={() => setConfirmar({ tipo: 'rol', id: r.id, label: r.nombre })} title="Eliminar"
                        style={{ width: 24, height: 24, borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                          border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>
                        <Icon name="trash" style={{ width: 11, height: 11 }} />
                      </button>
                    )}
                  </div>
                )}
              </div>
              {r.descripcion && <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>{r.descripcion}</div>}
              <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)', fontWeight: 700 }}>{r.permisos.length} permiso/s</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                {r.permisos.slice(0, 6).map(p => (
                  <span key={p} style={{ fontSize: 9.5, padding: '2px 6px', borderRadius: 5, background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>{p}</span>
                ))}
                {r.permisos.length > 6 && <span style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>+{r.permisos.length - 6}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── PERMISOS (catálogo, sólo lectura: los define el código) ── */}
      {!cargando && tab === 'permisos' && (
        <div className="card" style={{ padding: 24 }}>
          <div className="card-subtitle" style={{ marginBottom: 16 }}>
            Los permisos son por ACCIÓN, no por pantalla (las pantallas cambian, las acciones no). Los define el sistema; acá se ven para saber qué se le puede dar a cada rol.
          </div>
          {Object.entries(porModulo).map(([mod, ps]) => (
            <div key={mod} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase' }}>{mod}</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
                {ps.map(p => (
                  <div key={p.id} style={{ border: '1px solid var(--border-light)', borderRadius: 8, padding: '9px 12px', background: 'rgba(0,0,0,0.1)' }}>
                    <div style={{ fontSize: 12.5, fontWeight: 700 }}>{p.nombre}</div>
                    <div style={{ fontSize: 10, color: 'var(--accent)', fontFamily: 'monospace' }}>{p.clave}</div>
                    {p.descripcion && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{p.descripcion}</div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── MODAL usuario ── */}
      <Modal open={!!editUsr} onClose={() => setEditUsr(null)} titulo={editUsr?.id ? 'Editar usuario' : 'Nuevo usuario'}
        subtitulo={editUsr?.id ? 'Dejá la contraseña vacía para no cambiarla.' : 'Mínimo 8 caracteres de contraseña.'} maxWidth={520}>
        {editUsr && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div><label style={lbl}>Usuario</label>
                <input style={inp} value={editUsr.usuario || ''} disabled={!!editUsr.id}
                  onChange={e => setEditUsr(u => ({ ...u, usuario: e.target.value }))} /></div>
              <div><label style={lbl}>Nombre</label>
                <input style={inp} value={editUsr.nombre || ''} onChange={e => setEditUsr(u => ({ ...u, nombre: e.target.value }))} /></div>
            </div>
            <div><label style={lbl}>Email (opcional)</label>
              <input style={inp} value={editUsr.email || ''} onChange={e => setEditUsr(u => ({ ...u, email: e.target.value }))} /></div>
            <div><label style={lbl}>Contraseña {editUsr.id ? '(vacío = no cambiar)' : ''}</label>
              <input style={inp} type="password" value={editUsr.password || ''} autoComplete="new-password"
                onChange={e => setEditUsr(u => ({ ...u, password: e.target.value }))} /></div>
            <div>
              <label style={lbl}>Roles</label>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {roles.map(r => chipRol(r.clave, (editUsr.roles || []).includes(r.clave), () => setEditUsr(u => {
                  const s = new Set(u.roles || []); s.has(r.clave) ? s.delete(r.clave) : s.add(r.clave);
                  return { ...u, roles: [...s] };
                })))}
              </div>
            </div>
            {editUsr.id && (
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, cursor: 'pointer' }}>
                <input type="checkbox" checked={editUsr.activo !== false} onChange={e => setEditUsr(u => ({ ...u, activo: e.target.checked }))} />
                Activo (si lo desactivás no puede entrar, pero su historial queda)
              </label>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 6 }}>
              <button className="btn ghost" onClick={() => setEditUsr(null)}>Cancelar</button>
              <button className="btn primary" onClick={guardarUsuario}>Guardar</button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── MODAL rol ── */}
      <Modal open={!!editRol} onClose={() => setEditRol(null)} titulo={editRol?.id ? 'Editar rol' : 'Nuevo rol'}
        subtitulo="Elegí qué acciones puede hacer este rol." maxWidth={640}>
        {editRol && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div><label style={lbl}>Clave</label>
                <input style={inp} value={editRol.clave || ''} disabled={!!editRol.id} placeholder="ej: supervisor"
                  onChange={e => setEditRol(g => ({ ...g, clave: e.target.value }))} /></div>
              <div><label style={lbl}>Nombre</label>
                <input style={inp} value={editRol.nombre || ''} onChange={e => setEditRol(g => ({ ...g, nombre: e.target.value }))} /></div>
            </div>
            <div><label style={lbl}>Descripción</label>
              <input style={inp} value={editRol.descripcion || ''} onChange={e => setEditRol(g => ({ ...g, descripcion: e.target.value }))} /></div>
            <div>
              <label style={lbl}>Permisos {editRol.es_sistema && <span style={{ color: 'var(--text-muted)' }}>— el rol de sistema no los puede cambiar (si se los sacan, nadie podría volver a dárselos)</span>}</label>
              <div style={{ maxHeight: 300, overflowY: 'auto', border: '1px solid var(--border-light)', borderRadius: 8, padding: 10 }}>
                {Object.entries(porModulo).map(([mod, ps]) => (
                  <div key={mod} style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 5 }}>{mod}</div>
                    {ps.map(p => (
                      <label key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, padding: '3px 0',
                        cursor: editRol.es_sistema ? 'not-allowed' : 'pointer', opacity: editRol.es_sistema ? 0.5 : 1 }}>
                        <input type="checkbox" disabled={editRol.es_sistema} checked={(editRol.permisos || []).includes(p.clave)}
                          onChange={() => setEditRol(g => {
                            const s = new Set(g.permisos || []); s.has(p.clave) ? s.delete(p.clave) : s.add(p.clave);
                            return { ...g, permisos: [...s] };
                          })} />
                        <span style={{ fontWeight: 600 }}>{p.nombre}</span>
                        <span style={{ fontSize: 9.5, color: 'var(--accent)', fontFamily: 'monospace' }}>{p.clave}</span>
                      </label>
                    ))}
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn ghost" onClick={() => setEditRol(null)}>Cancelar</button>
              <button className="btn primary" onClick={guardarRol}>Guardar</button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── MODAL confirmar borrado (nada de diálogos del navegador) ── */}
      <Modal open={!!confirmar} onClose={() => setConfirmar(null)} titulo="¿Eliminar?" maxWidth={420} centrado>
        {confirmar && (
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
              Se va a eliminar {confirmar.tipo === 'usuario' ? 'el usuario' : 'el rol'} <b style={{ color: '#fff' }}>{confirmar.label}</b>. No se puede deshacer.
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn ghost" onClick={() => setConfirmar(null)}>Cancelar</button>
              <button className="btn" style={{ background: 'var(--danger, #ff4d4f)', color: '#fff' }} onClick={borrar}>Eliminar</button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// ── Detalle de UNA fuente: tabla de glifos (lo que tiene y lo que le falta) + laboratorio ──
function DetalleFuente({ f, onVolver }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  // laboratorio ('' = el lienzo muestra MUESTRA_DEF como marca de agua)
  const [txt, setTxt] = useState('');
  const [size, setSize] = useState(64);
  const [color, setColor] = useState('#ffffff');
  const [borde, setBorde] = useState(0);
  const [colorBorde, setColorBorde] = useState('#00f3ff');
  const [fondo, setFondo] = useState('#111417');
  const [esp, setEsp] = useState(0);
  const fam = _famFuente(f);

  useEffect(() => {
    let vivo = true;
    fetch('/api/fuente/glifos/' + encodeURIComponent(f.archivo))
      .then(r => r.json())
      .then(d => { if (vivo) { if (d.error) setErr(d.error); else setData(d); } })
      .catch(e => { if (vivo) setErr(String(e)); });
    return () => { vivo = false; };
  }, [f.archivo]);

  // CHEQUEO del texto de prueba: qué caracteres escritos NO tiene esta fuente. Se calcula con
  // los glifos que informó el servidor (dibujables de verdad), no con lo que muestre el navegador
  // — si la fuente no tiene el glifo, Chrome lo suple con otra tipografía y engaña.
  const tiene = useMemo(() => {
    const s = new Set();
    (data?.grupos || []).forEach(g => g.celdas.forEach(c => { if (c.tiene) s.add(c.ch); }));
    return s;
  }, [data]);
  const faltantes = useMemo(() => {
    if (!data) return [];
    const efectivo = txt.trim() ? txt : MUESTRA_DEF;   // vacío = lo que se ve es la muestra por defecto
    return [...new Set([...efectivo].filter(c => !c.trim() ? false : !tiene.has(c)))];
  }, [txt, tiene, data]);

  return (
    <div className="panel animate-fade">
      <style>{`@font-face{font-family:'${fam}';src:url('/api/fuente/archivo/${encodeURIComponent(f.archivo)}');font-display:swap;}`}</style>
      <div style={{ marginBottom: 20 }}>
        <button className="btn ghost" onClick={onVolver} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
          ⬅ Volver al Catálogo de Fuentes
        </button>
      </div>
      <div className="panel-header">
        <h2>{data?.interno || f.interno}</h2>
        <p>{f.archivo}{data ? ` · ${data.total_cmap} caracteres en la fuente` : ''}</p>
      </div>

      {err && <div className="card" style={{ margin: '20px 0', padding: 16, color: 'var(--danger, #ff4d4f)', fontSize: 13 }}>No se pudieron leer los glifos: {err}</div>}

      {/* ── TABLA DE CARACTERES ── */}
      <div className="card" style={{ margin: '20px 0', padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 6 }}>
          <div className="card-title" style={{ margin: 0 }}>Caracteres de la fuente</div>
          {data && (
            <span className={'badge ' + (data.faltan ? 'warning' : 'success')} style={{ fontSize: 10, flexShrink: 0 }}>
              {data.faltan ? `Le faltan ${data.faltan}` : 'Están todos'}
            </span>
          )}
        </div>
        <div className="card-subtitle" style={{ marginBottom: 18 }}>Cada celda muestra el carácter en esta tipografía · Celda vacía en rojo = la fuente NO lo tiene (no se puede estampar).</div>
        {!data && !err && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Leyendo la fuente…</div>}
        {(data?.grupos || []).map((g, gi) => (
          <div key={gi} style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-secondary)' }}>{g.titulo}</span>
              {!!g.faltan && <span style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--danger, #ff4d4f)' }}>faltan {g.faltan}</span>}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(58px, 1fr))', gap: 6 }}>
              {g.celdas.map((c, ci) => (
                <div key={ci} title={c.tiene ? c.ch : `La fuente no tiene "${c.ch}"`}
                  style={{ position: 'relative', height: 64, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: '1px solid ' + (c.tiene ? 'var(--border-light)' : 'rgba(255,77,79,0.65)'),
                    background: c.tiene ? 'rgba(255,255,255,0.03)' : 'rgba(255,77,79,0.18)' }}>
                  {/* la etiqueta chica identifica la celda (sin ella no se sabe cuál falta) */}
                  <span style={{ position: 'absolute', top: 3, left: 5, fontSize: 8.5, opacity: 0.7,
                    color: c.tiene ? 'var(--text-muted)' : 'var(--danger, #ff4d4f)' }}>{c.ch}</span>
                  {/* el glifo, en la tipografía REAL. Si la fuente NO lo tiene, la celda va VACÍA y
                      en rojo: dibujarlo sería mentira (lo pintaría otra tipografía, no ésta). */}
                  {c.tiene && <span style={{ fontFamily: `'${fam}'`, fontSize: 30, color: 'var(--text-primary, #fff)' }}>{c.ch}</span>}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* ── LABORATORIO ── */}
      <div className="card" style={{ margin: '20px 0', padding: 24 }}>
        <div className="card-title">Probar la fuente</div>
        <div className="card-subtitle" style={{ marginBottom: 14 }}>Escribí directamente sobre la muestra.</div>

        {/* BARRA DE HERRAMIENTAS */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', padding: 8, marginBottom: -1,
          border: '1px solid var(--border-light)', borderRadius: '10px 10px 0 0', background: 'rgba(255,255,255,0.03)' }}>
          {/* tamaño */}
          <div style={_grp} title="Tamaño de la letra">
            <IcoLab d="M3 17V5h6M6 5v12M12 17V9h5M14.5 9v8" />
            <NumeroConMenu value={size} onChange={setSize} min={8} max={400} opciones={[24, 36, 48, 64, 96, 128, 180, 240]} />
          </div>
          <div style={_sep} />
          {/* borde */}
          <div style={_grp} title="Grosor del borde">
            <IcoLab d="M12 3a9 9 0 100 18 9 9 0 000-18zm0 4a5 5 0 110 10 5 5 0 010-10z" />
            <NumeroConMenu value={borde} onChange={setBorde} min={0} max={20} step={0.5} opciones={[0, 1, 2, 3, 4, 6, 8, 12]} ancho={46} />
            <SwatchColor value={colorBorde} onChange={setColorBorde} titulo="Borde" />
          </div>
          <div style={_sep} />
          {/* espaciado */}
          <div style={_grp} title="Espaciado entre letras">
            <IcoLab d="M4 5v14M20 5v14M8 12h8M8 12l2-2M8 12l2 2M16 12l-2-2M16 12l-2 2" />
            <NumeroConMenu value={esp} onChange={setEsp} min={-20} max={60} opciones={[-4, 0, 2, 4, 8, 16, 24]} ancho={46} />
          </div>
          <div style={_sep} />
          {/* colores */}
          <div style={_grp}>
            <SwatchColor value={color} onChange={setColor} titulo="Relleno" />
            <SwatchColor value={fondo} onChange={setFondo} titulo="Fondo" />
          </div>
          <div style={{ flex: 1 }} />
          <button type="button" onClick={() => { setSize(64); setBorde(0); setEsp(0); setColor('#ffffff'); setColorBorde('#00f3ff'); setFondo('#111417'); }}
            title="Volver a los valores iniciales"
            style={{ height: 30, padding: '0 10px', borderRadius: 7, cursor: 'pointer', fontSize: 11, fontWeight: 700,
              border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>↺ Reiniciar</button>
        </div>

        {/* LIENZO EDITABLE: se escribe acá mismo, con la fuente y los colores aplicados */}
        <style>{`.tzLab:empty:before{content:attr(data-ph);opacity:.35}`}</style>
        <div className="tzLab" contentEditable suppressContentEditableWarning spellCheck={false}
          data-ph={MUESTRA_DEF} onInput={(e) => setTxt(e.currentTarget.textContent)}
          title="Escribí acá"
          style={{ border: '1px solid var(--border-light)', borderRadius: '0 0 10px 10px', background: fondo, padding: 24, minHeight: 150,
            display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'auto', outline: 'none', cursor: 'text',
            fontFamily: `'${fam}', system-ui`, fontSize: size, lineHeight: 1.25, color, letterSpacing: esp,
            WebkitTextStrokeWidth: borde ? borde + 'px' : 0, WebkitTextStrokeColor: colorBorde,
            paintOrder: 'stroke fill', whiteSpace: 'pre-wrap', wordBreak: 'break-word', textAlign: 'center' }} />

        {/* aviso de chequeo: caracteres escritos que la fuente NO tiene */}
        {!!faltantes.length && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, padding: '9px 12px', borderRadius: 8,
            border: '1px solid rgba(255,77,79,0.5)', background: 'rgba(255,77,79,0.08)', fontSize: 12, color: 'var(--danger, #ff4d4f)', fontWeight: 600 }}>
            <span>Esta fuente NO tiene: {faltantes.map(c => `"${c}"`).join(' · ')} — no se van a poder estampar.</span>
          </div>
        )}
        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 8 }}>
          Vista de referencia del navegador. La tizada estampa el contorno REAL de la fuente (texto a curvas) — el borde de acá es solo para probar la forma.
        </div>
      </div>
    </div>
  );
}

function MesasInfinito({ mesas, job }) {
  const [view, setView] = useState({ zoom: 1, panX: 0, panY: 0 });
  // Nombres editados: PERSISTEN ligados a ESTE pedido (clave = id del trabajo). Un pedido NUEVO
  // tiene otro id → arranca con los nombres por defecto ("Mesa N"). Se guardan en localStorage.
  const LS_KEY = 'tizada_mesas_nombres_' + (job?.resultado?.id || '');
  const [nombres, setNombres] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; } catch (_e) { return {}; }
  });
  const [editando, setEditando] = useState(null);  // key de la mesa en edición
  useEffect(() => {
    try { localStorage.setItem(LS_KEY, JSON.stringify(nombres)); } catch (_e) { /* storage lleno/bloqueado */ }
  }, [LS_KEY, nombres]);
  const wrapRef = useRef(null);
  const viewRef = useRef(view); viewRef.current = view;

  // ZOOM con la rueda: listener nativo NO pasivo → preventDefault corta el scroll de la página
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const b = el.getBoundingClientRect();
      const mx = e.clientX - b.left, my = e.clientY - b.top;
      setView(v => {
        const f = e.deltaY < 0 ? 1.12 : 1 / 1.12;
        const nz = Math.max(0.15, Math.min(ZMAX, v.zoom * f));
        const k = nz / v.zoom;
        return { zoom: nz, panX: mx - (mx - v.panX) * k, panY: my - (my - v.panY) * k };
      });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  // PAN arrastrando con el CLICK DERECHO (izquierdo queda libre para editar el nombre)
  const startPan = (e) => {
    if (e.button !== 2) return;
    e.preventDefault();
    const sx = e.clientX, sy = e.clientY, px = viewRef.current.panX, py = viewRef.current.panY;
    const mv = (ev) => setView(v => ({ ...v, panX: px + (ev.clientX - sx), panY: py + (ev.clientY - sy) }));
    const up = () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
  };

  const sanit = (s) => ((s || 'mesa').replace(/[\\/:*?"<>|\n\r\t]+/g, '_').trim() || 'mesa');

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 3, display: 'flex', gap: 4 }}>
        <button type="button" onClick={() => setView({ zoom: 1, panX: 0, panY: 0 })} title="Ver todo" style={{ background: 'rgba(0,0,0,0.55)', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 11, padding: '3px 9px' }}>Ver todo</button>
        <button type="button" onClick={() => setView(v => ({ ...v, zoom: Math.max(0.15, v.zoom / 1.25) }))} title="Alejar" style={{ background: 'rgba(0,0,0,0.55)', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 14, padding: '0 9px', lineHeight: '22px' }}>−</button>
        <button type="button" onClick={() => setView(v => ({ ...v, zoom: Math.min(ZMAX, v.zoom * 1.25) }))} title="Acercar" style={{ background: 'rgba(0,0,0,0.55)', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 14, padding: '0 9px', lineHeight: '22px' }}>+</button>
      </div>
      <div ref={wrapRef} onMouseDown={startPan} onContextMenu={(e) => e.preventDefault()}
        style={{ position: 'relative', height: '74vh', overflow: 'hidden', borderRadius: 12, background: 'rgba(0,0,0,0.22)', backgroundImage: 'radial-gradient(rgba(255,255,255,0.07) 1px, transparent 1px)', backgroundSize: '24px 24px', cursor: 'grab' }}>
        <div style={{ position: 'absolute', left: 0, top: 0, transform: `translate(${view.panX}px, ${view.panY}px) scale(${view.zoom})`, transformOrigin: '0 0', display: 'flex', gap: 80, padding: 48, alignItems: 'flex-start' }}>
          {(() => { let gi = 0; return mesas.flatMap((hoja, hi) => {
            const pvs = (hoja.previews && hoja.previews.length) ? hoja.previews : [null];
            const urlPdf = `/trabajos/${job.resultado.id}/${hoja.archivo}`;
            return pvs.map((pv, pi) => {
              const gidx = gi++;                        // índice global en orden de aparición
              const altoCm = (hoja.alturas_cm && hoja.alturas_cm[pi] != null) ? hoja.alturas_cm[pi] : hoja.consumo_cm;
              const anchoCm = hoja.ancho_cm || 180;
              const PXM = 240;   // px por metro: ESCALA REAL común a todas las mesas
              const w = (anchoCm / 100) * PXM, h = (altoCm / 100) * PXM;
              const key = hoja.archivo + '::' + pi;     // ESTABLE por trabajo → el nombre persiste a esta mesa
              const tela = hoja.tela || '';
              const nombreDef = 'Mesa ' + (gidx + 1) + (tela ? ' - ' + tela : '');   // secuencial + guión + tela
              const nombre = nombres[key] != null ? nombres[key] : nombreDef;
              return (
                <div key={key} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
                  {/* ARRIBA: nombre a la IZQUIERDA (doble-click para renombrar) y el ícono de
                      descarga al lado CONTRARIO (derecha), en la misma línea. */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: w, justifyContent: 'space-between' }}>
                    {editando === key
                      ? <input autoFocus value={nombre}
                          onChange={(e) => setNombres(n => ({ ...n, [key]: e.target.value }))}
                          onBlur={() => setEditando(null)}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === 'Escape') setEditando(null); }}
                          onMouseDown={(e) => e.stopPropagation()}
                          style={{ fontSize: 12, fontWeight: 700, color: '#000', background: '#fff', border: '1px solid var(--accent)', borderRadius: 5, padding: '2px 6px', flex: 1, minWidth: 0, marginRight: 8, outline: 'none' }} />
                      : <span onDoubleClick={() => setEditando(key)} title="Doble-click para renombrar"
                          style={{ fontSize: 12, fontWeight: 700, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', cursor: 'text', userSelect: 'none' }}>{nombre}</span>}
                    <a href={`/api/trabajos/${job.resultado.id}/mesa/${hoja.archivo}?pi=${pi}&nombre=${encodeURIComponent(sanit(nombre))}`} download={sanit(nombre) + '.pdf'} title="Descargar esta mesa"
                      onMouseDown={(e) => e.stopPropagation()} onContextMenu={(e) => e.stopPropagation()}
                      style={{ flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: 26, height: 26, background: 'var(--accent)', color: '#000', borderRadius: 7, textDecoration: 'none' }}>
                      <Icon name="download" style={{ width: 14, height: 14 }} />
                    </a>
                  </div>
                  {/* LA MESA a escala real (solo la hoja, sin marco extra) */}
                  {pv
                    ? <img src={`/trabajos/${job.resultado.id}/${pv}`} alt={nombre} draggable={false}
                        style={{ width: w, height: h, display: 'block' }} />
                    : <div style={{ width: w, height: h, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 11 }}>Sin vista previa</div>}
                  {/* ABAJO: tamaño ancho × alto */}
                  <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--accent)', whiteSpace: 'nowrap' }}>
                    {(anchoCm / 100).toFixed(2)} × {(altoCm / 100).toFixed(2)} m
                  </div>
                </div>
              );
            });
          }); })()}
        </div>
      </div>
    </div>
  );
}

// ── Mapeador de arte VISUAL (reutilizable: operario y ajuste interno) ──────
// Muestra el molde con el diseño encima (a escala, sin deformar). Se toca una
// pieza y se elige en qué mesa del diseño está. Mismo mapeador en los dos lados.
// Baseline text-on-path de la ETIQUETA sobre el borde (COMPARTIDA por el visor de etiqueta y el del
// arte). Dado el contorno + posición (t o rx/ry), devuelve {d, segLen} del segmento del borde donde
// apoyar el texto. MISMA lógica que el motor. Ver [[etiqueta-baseline-no-romper]] — NO cambiar.
function _segmentoEdge(pathD, t, ccx, ccy, offIn, rx, ry) {
  try {
    const el = document.createElementNS('http://www.w3.org/2000/svg', 'path'); el.setAttribute('d', pathD);
    const len = el.getTotalLength(); if (!len) return null;
    const at = (l) => el.getPointAtLength(((l % len) + len) % len);
    const dirAt = (l) => { const u = at(l - 1.5), v = at(l + 1.5); return Math.atan2(v.y - u.y, v.x - u.x); };
    let bestL;
    if (rx != null && ry != null) {
      let minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9;
      const nb = Math.max(60, Math.min(500, Math.round(len / 3)));
      for (let i = 0; i <= nb; i++) { const p = at(len * i / nb); if (p.x < minx) minx = p.x; if (p.x > maxx) maxx = p.x; if (p.y < miny) miny = p.y; if (p.y > maxy) maxy = p.y; }
      const ax = minx + rx * (maxx - minx), ay = miny + ry * (maxy - miny);
      const ns = Math.max(80, Math.min(700, Math.round(len / 2))); let bd = 1e18; bestL = 0;
      for (let i = 0; i <= ns; i++) { const L = len * i / ns, p = at(L), d = (p.x - ax) ** 2 + (p.y - ay) ** 2; if (d < bd) { bd = d; bestL = L; } }
    } else { bestL = ((t * len) % len + len) % len; }
    const wd = Math.max(2.5, len / 160), st = Math.max(0.8, len / 600);
    const turnAt = (l) => Math.abs((((dirAt(l + wd) - dirAt(l - wd)) + Math.PI) % (2 * Math.PI)) - Math.PI);
    const walk = (sg) => { let d = st; while (d < len * 0.48) { if (turnAt(bestL + sg * d) > 0.5) break; d += st; } return d; };
    const a = bestL - walk(-1), b = bestL + walk(1);
    const segLen = b - a; if (segLen <= 1) return null;
    const M = Math.max(16, Math.min(64, Math.round(segLen / 3)));
    const pts = []; for (let i = 0; i <= M; i++) pts.push(at(a + segLen * i / M));
    const mid = at(a + segLen / 2), mid2 = at(a + segLen / 2 + 1.5);
    const reverse = ((mid2.y - mid.y) * (ccx - mid.x) + (-(mid2.x - mid.x)) * (ccy - mid.y)) < 0;
    let ord = reverse ? pts.slice().reverse() : pts;
    if (offIn) {
      ord = ord.map((q, k) => {
        const pa = ord[Math.max(0, k - 1)], pb = ord[Math.min(ord.length - 1, k + 1)];
        let tx = pb.x - pa.x, ty = pb.y - pa.y; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
        let nx = -ty, ny = tx; if (nx * (ccx - q.x) + ny * (ccy - q.y) < 0) { nx = ty; ny = -tx; }
        return { x: q.x + nx * offIn, y: q.y + ny * offIn };
      });
    }
    return { d: 'M ' + ord.map(q => `${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' L '), segLen };
  } catch { return null; }
}

function MapeadorArteVisual({ canvasLayout, mapeoData, mapeoValores, setMapeoValores, onMapeoChange, selectedPiezaMapeo, setSelectedPiezaMapeo, etqNombres, bordeConfig, etiquetaConfig, talleRef, previewPiezas, onGuardar, onCerrar, panelIzquierdo, onCargarDiseno, titulo, acciones, objetosEditables, editablesRaw, vf, telaModo, telaColorPieza, telaSelSet, onTelaClick, onTelaVacio, panelTela, cargando }) {
  // Aplicar un cambio de mapeo hecho por el usuario (arrastrar/tocar/quitar): si hay auto-guardado
  // (onMapeoChange) persiste solo; si no, solo actualiza el estado local (comportamiento viejo).
  const aplicarMapeo = onMapeoChange || setMapeoValores;
  const segCacheArte = React.useRef(new Map());   // cache de _segmentoEdge (path+pos → baseline) para no re-medir en cada render
  // Visor con PAN + ZOOM (arrastrar + rueda), como el de Configuración: espacio infinito donde se
  // navega libremente. `artVB` = viewBox actual {x,y,w,h}; null = ajustado a la vista (fit).
  const [artVB, setArtVB] = React.useState(null);
  const artWrapRef = React.useRef(null);
  const _domVB = () => {
    const el = artWrapRef.current && artWrapRef.current.querySelector('svg');
    const n = ((el && el.getAttribute('viewBox')) || '0 0 100 100').split(/\s+/).map(Number);
    return { x: n[0], y: n[1], w: n[2], h: n[3] };
  };
  const _artZoom = (mx, my, f) => setArtVB(prev => {
    const b = prev || _domVB();
    const nw = Math.max(1, b.w * f), nh = Math.max(1, b.h * f);
    return { x: b.x + (b.w - nw) * mx, y: b.y + (b.h - nh) * my, w: nw, h: nh };
  });
  const artPanStart = (e) => {
    if (e.button !== 0 || !artWrapRef.current) return;
    const box = artWrapRef.current.getBoundingClientRect();
    const base = artVB || _domVB(); const sx = e.clientX, sy = e.clientY;
    const mv = (ev) => setArtVB({ ...base, x: base.x - (ev.clientX - sx) / box.width * base.w, y: base.y - (ev.clientY - sy) / box.height * base.h });
    const up = () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
  };
  React.useEffect(() => {   // rueda = zoom (listener no-pasivo para poder preventDefault)
    const el = artWrapRef.current; if (!el) return;
    const h = (e) => { e.preventDefault(); const b = el.getBoundingClientRect(); _artZoom((e.clientX - b.left) / b.width, (e.clientY - b.top) / b.height, e.deltaY < 0 ? 1 / 1.15 : 1.15); };
    el.addEventListener('wheel', h, { passive: false });
    return () => el.removeEventListener('wheel', h);
  }, []);
  // Al cambiar de variante/talle (cambia el encuadre auto), volver a "Ver todo".
  React.useEffect(() => { setArtVB(null); }, [vf && vf.vb]);
  // Piezas SIN diseño asignado (van en ROJO; no se debe avanzar si hay alguna).
  // VARIABLE-FIRST: si hay variable (vf), se cuentan SOLO sus piezas, no las del molde entero.
  const _piezasVar = vf ? new Set((canvasLayout?.layout || []).filter(p => vf.show.has(p.idx)).map(p => (etqNombres?.[p.idx] || p.name || '').trim()).filter(Boolean)) : null;
  const _sinDiseno = (mapeoData?.piezas || []).filter(p => !mapeoValores[p] && (!_piezasVar || _piezasVar.has(p)));
  const _conDiseno = mapeoData?.mesas?.length > 0;
  return (
    <div className="animate-fade" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 9, marginBottom: 9, borderBottom: '1px solid var(--border-light)', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, minWidth: 0 }}>
          {titulo || <div style={{ fontSize: 14, fontWeight: 700 }}>Mapear diseño</div>}
          <span title="Arrastrá cada diseño (panel derecho) sobre su pieza del molde. Al Guardar, el mapeo queda fijo en el molde: los próximos diseños con el mismo orden de mesas se aplican solos."
            style={{ cursor: 'help', color: 'var(--text-muted)', fontSize: 11, fontWeight: 700, fontStyle: 'italic', border: '1px solid var(--border-light)', borderRadius: '50%', width: 17, height: 17, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>i</span>
          {_conDiseno && _sinDiseno.length > 0 && (
            <button type="button" onClick={() => setSelectedPiezaMapeo(_sinDiseno[0])} title={'Sin diseño: ' + _sinDiseno.join(', ')}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 10px', borderRadius: 999, cursor: 'pointer', border: '1px solid #ff4d4d', background: 'rgba(255,77,77,0.12)', color: '#ff7a7a', fontSize: 12, fontWeight: 700, flexShrink: 0, whiteSpace: 'nowrap' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ff4d4d' }} /> {_sinDiseno.length} pieza{_sinDiseno.length === 1 ? '' : 's'} sin diseño
            </button>
          )}
          {_conDiseno && _sinDiseno.length === 0 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: 'var(--success)', flexShrink: 0 }}>
              <Icon name="check" style={{ width: 13, height: 13, strokeWidth: 3 }} /> Todas con diseño
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
          {/* Pan + zoom: arrastrá para mover, rueda para zoom (como el visor de Configuración). */}
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <button type="button" onClick={() => setArtVB(null)} title="Ver todo (ajustar a la vista)" style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 11, padding: '2px 8px' }}>Ver todo</button>
            <button type="button" onClick={() => _artZoom(0.5, 0.5, 1.25)} title="Alejar" style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 13, padding: '0 8px', lineHeight: '20px' }}>−</button>
            <button type="button" onClick={() => _artZoom(0.5, 0.5, 1 / 1.25)} title="Acercar" style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 13, padding: '0 8px', lineHeight: '20px' }}>+</button>
          </div>
          {acciones}
          {onCerrar && <button className="btn ghost" onClick={onCerrar} style={{ padding: '6px 12px', whiteSpace: 'nowrap' }}>← Volver</button>}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 14, flex: 1, minHeight: 0 }}>
        {panelIzquierdo}
        <div ref={artWrapRef} onMouseDown={artPanStart} style={{ flex: 1, minWidth: 0, background: '#0c0c0e', border: '1px solid var(--border-light)', borderRadius: 10, padding: 12, overflow: 'hidden', display: 'flex', alignItems: 'stretch', justifyContent: 'stretch', cursor: 'grab' }}>
          {canvasLayout?.layout?.length ? (() => {
            // VER VARIANTE: si viene `vf`, se muestran SOLO sus piezas y se ACOMODAN (translate por `vf.pos`,
            // el mismo orden guardado en Variables). `px/py` quedan en coords YA acomodadas (para labels y encuadre);
            // el dibujo del contorno/diseño usa las coords ORIGINALES dentro de un <g transform> (ver abajo).
            const piezas = canvasLayout.layout
              .filter(p => (etqNombres[p.idx] || p.name))
              .filter(p => !vf || vf.show.has(p.idx))
              .map(p => { const o = vf ? (vf.pos.get(p.idx) || { dx: 0, dy: 0 }) : { dx: 0, dy: 0 }; return { ...p, nombre: etqNombres[p.idx] || p.name, _dx: o.dx, _dy: o.dy, px: p.px + o.dx, py: p.py + o.dy }; });
            // Ubicar el cartel de cada pieza a un costado (abajo/arriba/der/izq) SIN
            // superponerse a las piezas ni a otros carteles.
            const LH = 15, GAP = 6, CW = 5.4;
            const inter = (a, b) => !(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y);
            const ocupados = piezas.map(p => ({ x: p.px, y: p.py, w: p.pw, h: p.ph }));
            const labels = [];
            for (const p of piezas) {
              const W = Math.max(30, p.nombre.length * CW + 12);
              const cx = p.px + p.pw / 2, cy = p.py + p.ph / 2;
              const cands = [
                { x: cx - W / 2, y: p.py + p.ph + GAP, ax: cx, ay: p.py + p.ph },
                { x: cx - W / 2, y: p.py - GAP - LH, ax: cx, ay: p.py },
                { x: p.px + p.pw + GAP, y: cy - LH / 2, ax: p.px + p.pw, ay: cy },
                { x: p.px - GAP - W, y: cy - LH / 2, ax: p.px, ay: cy },
              ];
              let chosen = null;
              for (const c of cands) {
                const r = { x: c.x, y: c.y, w: W, h: LH };
                if (!ocupados.some(o => inter(r, o)) && !labels.some(l => inter(r, l.r))) { chosen = { r, ax: c.ax, ay: c.ay }; break; }
              }
              if (!chosen) {
                let r = { x: cx - W / 2, y: p.py + p.ph + GAP, w: W, h: LH };
                let t = 0;
                while ((ocupados.some(o => inter(r, o)) || labels.some(l => inter(r, l.r))) && t < 60) { r = { ...r, y: r.y + LH + 3 }; t++; }
                chosen = { r, ax: cx, ay: p.py + p.ph };
              }
              labels.push({ p, nombre: p.nombre, ...chosen });
            }
            const all = [...ocupados, ...labels.map(l => l.r)];
            const minX = Math.min(...all.map(a => a.x)), minY = Math.min(...all.map(a => a.y));
            const maxX = Math.max(...all.map(a => a.x + a.w)), maxY = Math.max(...all.map(a => a.y + a.h));
            const PAD = 6;
            const vb = `${minX - PAD} ${minY - PAD} ${(maxX - minX) + 2 * PAD} ${(maxY - minY) + 2 * PAD}`;
            const _gen = (n) => (n || '').replace(/\s+\d+\s*$/, '').trim();
            const drop = (pzName) => (e) => {
              e.preventDefault(); const mesa = e.dataTransfer.getData('mesa'); if (!mesa) return;
              // Aplica el diseño a TODAS las piezas del mismo nombre genérico (una mesa 'Cuello'
              // cubre 'Cuello 25', 'Cuello 12', …) — así se mapea una vez, no pieza por pieza.
              const g = _gen(pzName); const next = { ...mapeoValores };
              (mapeoData?.piezas || []).forEach(pz => { if (_gen(pz) === g) next[pz] = parseInt(mesa); });
              next[pzName] = parseInt(mesa);
              aplicarMapeo(next); setSelectedPiezaMapeo(pzName);
            };
            return (
              <svg viewBox={artVB ? `${artVB.x} ${artVB.y} ${artVB.w} ${artVB.h}` : vb}
                preserveAspectRatio="xMidYMid meet"
                onClick={() => { if (telaModo) onTelaVacio && onTelaVacio(); }}
                style={{ width: '100%', height: '100%', display: 'block', userSelect: 'none' }}>
                {piezas.map((p) => {
                  const pzName = p.nombre;
                  const isSelected = selectedPiezaMapeo === pzName;
                  // ARTE POR RANGO (#talle/#rango): el diseño mostrado es el del TALLE que se ve
                  // (mapeo_talles), no el default del 1er rango (bug "primero aparece el 6XL").
                  const _mtz = mapeoData?.mapeo_talles?.[pzName];
                  const mappedMesaIdx = (_mtz && talleRef && _mtz[talleRef]) || mapeoValores[pzName];
                  const mappedMesa = mapeoData?.mesas?.find(m => m.mesa === parseInt(mappedMesaIdx));
                  // MODO TELA: pintar la pieza con el color de su tela + resaltar si está seleccionada.
                  const _genN = _gen(pzName);
                  const telaCol = telaModo && telaColorPieza ? telaColorPieza(_genN) : null;
                  const telaSeld = telaModo && telaSelSet && telaSelSet.has(_genN);
                  // Colocación del diseño en la pieza (escala al alto, centrado al ancho) — la MISMA
                  // que usan los objetos editables para caer EXACTO sobre el diseño.
                  // coords ORIGINALES (el `path_svg`/diseño viven acá); el <g transform> las lleva al acomodo de la variante.
                  const ox = p.px - p._dx, oy = p.py - p._dy;
                  let imgX = ox, imgY = oy, imgW = p.pw, imgH = p.ph;
                  if (mappedMesa) {
                    const aspecto = mappedMesa.aspecto || (mappedMesa.w_cm && mappedMesa.h_cm ? mappedMesa.w_cm / mappedMesa.h_cm : (p.pw / p.ph));
                    imgH = p.ph; imgW = aspecto * imgH; imgX = ox + (p.pw - imgW) / 2; imgY = oy;
                  }
                  // Mientras se carga el mapeo de OTRA variable, no dibujar diseños con datos viejos
                  // (flash de "otro diseño"): contorno neutro hasta tener el mapeo nuevo.
                  const edis = (mappedMesa && !cargando) ? (objetosEditables || []).filter(o => o.idx === p.idx) : [];
                  // RENDER REAL del motor para esta pieza (SVG con contorno + diseño + borde + etiqueta,
                  // fondo blanco, cm reales). Si existe, se MUESTRA y NO se re-dibuja nada → arte = tizada.
                  const pv = (!telaModo && !cargando && previewPiezas) ? previewPiezas[pzName] : null;
                  return (
                    <g key={p.idx} transform={(p._dx || p._dy) ? `translate(${p._dx} ${p._dy})` : undefined} style={{ cursor: 'pointer' }} onClick={(e) => { if (telaModo) { e.stopPropagation(); onTelaClick && onTelaClick(_genN); } else setSelectedPiezaMapeo(pzName); }} onDragOver={(e) => e.preventDefault()} onDrop={drop(pzName)}>
                      <title>{pzName} {mappedMesaIdx ? `(Mesa ${mappedMesaIdx})` : '(sin diseño)'}</title>
                      <defs><clipPath id={`clipmapv-${p.idx}`}><path d={p.path_svg} /></clipPath></defs>
                      {/* RENDER REAL del motor (la pieza tal cual sale en la tizada). Si está, NO se re-dibuja nada. */}
                      {pv && <image href={`data:image/svg+xml;base64,${pv.svg}`} x={ox} y={oy} width={p.pw} height={p.ph} preserveAspectRatio="none" />}
                      {!pv && mappedMesa && !cargando && <image href={mappedMesa.svg ? `data:image/svg+xml;base64,${mappedMesa.svg}` : `data:image/png;base64,${mappedMesa.thumb}`} x={imgX} y={imgY} width={imgW} height={imgH} preserveAspectRatio="none" clipPath={`url(#clipmapv-${p.idx})`} opacity={0.9} />}
                      {/* BORDE DE CORTE REAL (WYSIWYG): igual que el motor — trazo 2× recortado al EXTERIOR del
                          contorno, así se ve solo la mitad de afuera, con el color/grosor configurado del molde. */}
                      {!pv && !telaModo && bordeConfig?.activo && (() => {
                        const pxmm = p.h_cm ? p.ph / (p.h_cm * 10) : (p.w_cm ? p.pw / (p.w_cm * 10) : 0.033);
                        const bw = Math.max(0.3, (bordeConfig.ancho_mm || 2) * pxmm * 2);
                        const c = bordeConfig.color || [0, 0, 0, 0.85];
                        const rgb = `rgb(${Math.round(255 * (1 - (c[0] || 0)) * (1 - (c[3] || 0)))},${Math.round(255 * (1 - (c[1] || 0)) * (1 - (c[3] || 0)))},${Math.round(255 * (1 - (c[2] || 0)) * (1 - (c[3] || 0)))})`;
                        return (<>
                          <clipPath id={`bordeout-${p.idx}`}><path d={`M-99999 -99999H99999V99999H-99999Z ${p.path_svg}`} clipRule="evenodd" /></clipPath>
                          <path d={p.path_svg} fill="none" stroke={rgb} strokeWidth={bw} clipPath={`url(#bordeout-${p.idx})`} />
                        </>);
                      })()}
                      {/* objetos editables, ubicados con la MISMA colocación que el diseño y recortados al contorno */}
                      {!pv && edis.map((o) => {
                        // TODO objeto (del arte o agregado) se ubica DENTRO DEL DISEÑO: sus
                        // fracciones ya vienen calculadas contra la mesa del talle en vista.
                        const cx = imgX + (o.fcx + o.dx) * imgW, cy = imgY + (o.fcy + o.dy) * imgH;
                        const w = o.fw * imgW * o.scale, h = o.fh * imgH * o.scale;
                        return (
                          <g key={'edov-' + o.nombre} clipPath={`url(#clipmapv-${p.idx})`}>
                            <g transform={`rotate(${o.rot} ${cx} ${cy})`}>
                              <image href={o.svg ? `data:image/svg+xml;base64,${o.svg}` : `data:image/png;base64,${o.thumb}`} x={cx - w / 2} y={cy - h / 2} width={w} height={h} preserveAspectRatio="none" />
                            </g>
                          </g>
                        );
                      })}
                      <path d={p.path_svg} vectorEffect="non-scaling-stroke" style={telaModo ? { fill: telaCol ? telaCol + '4d' : 'rgba(255,255,255,0.03)', stroke: telaSeld ? 'var(--accent)' : (telaCol || 'rgba(255,255,255,0.35)'), strokeWidth: telaSeld ? 4 : 1.6, strokeDasharray: 'none' } : { fill: pv ? 'none' : (isSelected ? 'rgba(0,243,255,0.14)' : mappedMesaIdx ? 'rgba(16,185,129,0.05)' : 'rgba(255,77,77,0.14)'), stroke: isSelected ? 'var(--accent)' : mappedMesaIdx ? 'var(--success)' : '#ff4d4d', strokeWidth: isSelected ? 3 : (mappedMesaIdx ? (pv ? 0 : 1.5) : (pv ? 1.2 : 2.4)), strokeDasharray: (mappedMesaIdx || isSelected || pv) ? 'none' : '7 5' }} />
                      {/* ETIQUETA (talle · nombre · nº) en la posición configurada — indica dónde y qué dice
                          la etiqueta de corte que llevará la pieza en la tizada. */}
                      {!pv && !telaModo && etiquetaConfig?.activo && (() => {
                        const ec = etiquetaConfig;
                        if (new Set((ec.piezas_off || []).map(_gen)).has(_genN)) return null;   // esta pieza NO lleva etiqueta (igual que el motor)
                        const pos = (ec.posiciones || {})[pzName] || (ec.posiciones || {})[_genN] || ec.posicion || { rx: 0.5, ry: 0.92 };
                        const txt = [ec.mostrar?.talle && (talleRef || '2XL'), ec.mostrar?.pieza && pzName, ec.mostrar?.numero && '#01'].filter(Boolean).join(ec.separador || '-');
                        if (!txt) return null;
                        const pxmm = p.h_cm ? p.ph / (p.h_cm * 10) : (p.w_cm ? p.pw / (p.w_cm * 10) : 0.033);
                        const fs = Math.max(0.6, (ec.size_mm || 3) * pxmm);
                        const ox = p.px - p._dx, oy = p.py - p._dy;
                        const lx = ox + (pos.rx != null ? pos.rx : 0.5) * p.pw, ly = oy + (pos.ry != null ? pos.ry : 0.92) * p.ph;
                        const c = ec.color || [0.15, 0.15, 0.15, 0.3];
                        const rgb = `rgb(${Math.round(255 * (1 - (c[0] || 0)) * (1 - (c[3] || 0)))},${Math.round(255 * (1 - (c[1] || 0)) * (1 - (c[3] || 0)))},${Math.round(255 * (1 - (c[2] || 0)) * (1 - (c[3] || 0)))})`;
                        const pAlign = pos.align || ec.align || 'centro';
                        const anchor = pAlign === 'izquierda' ? 'start' : pAlign === 'derecha' ? 'end' : 'middle';
                        // TEXT-ON-PATH: si la etiqueta tiene posición COLOCADA (`t`), el texto SIGUE la curva
                        // del borde igual que la tizada (con cache para no re-medir); si no, recto centrado.
                        const ccx = ox + p.pw / 2, ccy = oy + p.ph / 2, _offIn = 0.18 * pxmm;
                        let seg = null;
                        if (pos.t != null) {
                          const _k = `${p.path_svg}|${pos.t}|${pos.rx}|${pos.ry}|${_offIn}|${ccx}|${ccy}`;
                          const _m = segCacheArte.current;
                          if (_m.has(_k)) seg = _m.get(_k);
                          else { seg = _segmentoEdge(p.path_svg, pos.t, ccx, ccy, _offIn, pos.rx, pos.ry); if (_m.size > 4000) _m.clear(); _m.set(_k, seg); }
                        }
                        if (seg) {
                          const mg = Math.min(seg.segLen * 0.03, 4);
                          const so = pAlign === 'izquierda' ? mg : pAlign === 'derecha' ? Math.max(mg, seg.segLen - mg) : seg.segLen / 2;
                          return (
                            <g clipPath={`url(#clipmapv-${p.idx})`}>
                              <path id={`arteetq-${p.idx}`} d={seg.d} fill="none" stroke="none" />
                              <text fontSize={fs} fontWeight="800" textAnchor={anchor} fill={rgb} style={{ pointerEvents: 'none', fontFamily: 'sans-serif' }}>
                                <textPath href={`#arteetq-${p.idx}`} startOffset={so}>{txt}</textPath>
                              </text>
                            </g>
                          );
                        }
                        return <text x={lx} y={ly} textAnchor={anchor} fontSize={fs} fontWeight="800" fill={rgb} clipPath={`url(#clipmapv-${p.idx})`} style={{ pointerEvents: 'none', fontFamily: 'sans-serif' }}>{txt}</text>;
                      })()}
                    </g>
                  );
                })}
                {labels.map((l) => {
                  const pzName = l.nombre;
                  const isSelected = selectedPiezaMapeo === pzName;
                  const mesa = mapeoValores[pzName];
                  const lcx = l.r.x + l.r.w / 2, lcy = l.r.y + l.r.h / 2;
                  const col = isSelected ? 'var(--accent)' : mesa ? 'var(--success)' : '#ff4d4d';
                  return (
                    <g key={'lbl' + l.p.idx} style={{ cursor: 'pointer' }} onClick={(e) => { if (telaModo) { e.stopPropagation(); onTelaClick && onTelaClick(_gen(pzName)); } else setSelectedPiezaMapeo(pzName); }} onDragOver={(e) => e.preventDefault()} onDrop={drop(pzName)}>
                      <line x1={l.ax} y1={l.ay} x2={lcx} y2={lcy} stroke={col} strokeWidth={1} strokeDasharray="3 2" />
                      <rect x={l.r.x} y={l.r.y} width={l.r.w} height={l.r.h} rx={4} fill="rgba(0,0,0,0.9)" stroke={isSelected ? 'var(--accent)' : mesa ? 'var(--success)' : 'rgba(255,255,255,0.3)'} strokeWidth={isSelected ? 1.6 : 1} />
                      <text x={lcx} y={lcy + 3.2} textAnchor="middle" style={{ fill: '#fff', fontSize: 9.5, fontWeight: 600, fontFamily: 'sans-serif', pointerEvents: 'none' }}>{pzName}{mesa ? ` · M${mesa}` : ''}</text>
                    </g>
                  );
                })}
              </svg>
            );
          })() : (
            <div style={{ color: 'var(--text-muted)', fontSize: 12.5, textAlign: 'center', padding: 20 }}>Cargando el molde…</div>
          )}
        </div>
        {telaModo ? panelTela : (
        <div style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: 'var(--text-secondary)' }}>Diseños</div>
            {onCargarDiseno && (
              <button className="btn ghost" style={{ padding: '5px 10px', fontSize: 11 }} onClick={onCargarDiseno} title="Cargar otro diseño">
                <Icon name="upload" style={{ width: 12, height: 12, marginRight: 4 }} /> Cargar
              </button>
            )}
          </div>
          {!mapeoData?.mesas?.length && (
            <div title="Subí el .ai del cliente para esta variable" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', color: 'var(--text-muted)', gap: 8, padding: 14, border: '1px dashed var(--border-light)', borderRadius: 10, cursor: onCargarDiseno ? 'pointer' : 'default' }}
              onClick={onCargarDiseno || undefined}>
              <Icon name="upload" style={{ width: 20, height: 20, opacity: 0.6 }} />
              <div style={{ fontSize: 11.5 }}>Sin diseño</div>
            </div>
          )}
          {mapeoData?.mesas?.length > 0 && mapeoData?.piezas?.length > 0 && (
            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', lineHeight: 1.35, marginBottom: 8 }}>
              <b>Arrastrá</b> el diseño sobre la pieza del molde (se guarda solo). O tocá una pieza en el molde y después su <b>diseño</b>.
            </div>
          )}
          <div style={{ flex: 1, overflowY: 'auto', display: mapeoData?.mesas?.length ? 'grid' : 'none', gridTemplateColumns: '1fr 1fr', gap: 12, paddingRight: 4, alignContent: 'start' }}>
            {mapeoData?.mesas?.map(m => {
              const usadaEn = Object.keys(mapeoValores).find(pz => mapeoValores[pz] === m.mesa);
              // Nombre REAL del diseño: el de la capa «guías» (lo que se escribe en la
              // plantilla y NO se ve en el diseño, sirve para auto-asociarlo a la pieza).
              const nombre = m.nombre_detectado || m.sugerencia || `Mesa ${m.mesa}`;
              // Diseño COMPLETO: el thumbnail de la mesa trae los editables OCULTOS → los superponemos
              // en su posición ORIGINAL dentro del diseño (fracción del bbox en la mesa), así se ve como
              // en la pieza. Se muestran a su tamaño/lugar de base (sin el ajuste del pedido).
              const _asp = m.aspecto || (m.w_cm && m.h_cm ? m.w_cm / m.h_cm : 1);
              const _W = 1000, _H = _asp ? Math.round(1000 / _asp) : 1000;
              const _eds = (editablesRaw || []).filter(o => o.mesa === m.mesa && o.mesa_rect && o.bbox_mu).map(o => {
                const mr = o.mesa_rect, bb = o.bbox_mu;
                const cx = ((bb[0] + bb[2]) / 2 - mr[0]) / mr[2] * _W, cy = ((bb[1] + bb[3]) / 2 - mr[1]) / mr[3] * _H;
                const w = (bb[2] - bb[0]) / mr[2] * _W, h = (bb[3] - bb[1]) / mr[3] * _H;
                return { nombre: o.nombre, href: o.svg ? `data:image/svg+xml;base64,${o.svg}` : (o.thumb ? `data:image/png;base64,${o.thumb}` : null), x: cx - w / 2, y: cy - h / 2, w, h };
              }).filter(o => o.href);
              return (
                <div key={m.mesa} draggable onDragStart={(e) => { e.dataTransfer.setData('mesa', String(m.mesa)); e.dataTransfer.effectAllowed = 'copy'; }}
                  onClick={() => { if (!selectedPiezaMapeo) return; const g = (selectedPiezaMapeo || '').replace(/\s+\d+\s*$/, '').trim(); const next = { ...mapeoValores }; (mapeoData?.piezas || []).forEach(pz => { if ((pz || '').replace(/\s+\d+\s*$/, '').trim() === g) next[pz] = m.mesa; }); aplicarMapeo(next); }}
                  title={selectedPiezaMapeo ? `Clic = poner este diseño en «${selectedPiezaMapeo}»` : (usadaEn ? `Asignado a ${usadaEn}` : 'Tocá una pieza (o su cartel) y después este diseño; o arrastralo sobre la pieza')}
                  style={{ cursor: selectedPiezaMapeo ? 'pointer' : 'grab', display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                  {/* Caja FIJA (mismo alto/ancho para todos): el diseño se adapta dentro
                      sin deformar — alto manda si es más alto, ancho si es más ancho. */}
                  <div style={{ width: '100%', height: 96, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                    {_eds.length ? (
                      <svg viewBox={`0 0 ${_W} ${_H}`} preserveAspectRatio="xMidYMid meet" style={{ width: '100%', height: '100%', display: 'block', pointerEvents: 'none' }}>
                        <image href={m.svg ? `data:image/svg+xml;base64,${m.svg}` : `data:image/png;base64,${m.thumb}`} x={0} y={0} width={_W} height={_H} preserveAspectRatio="none" />
                        {_eds.map(o => (<image key={o.nombre} href={o.href} x={o.x} y={o.y} width={o.w} height={o.h} preserveAspectRatio="none" />))}
                      </svg>
                    ) : (
                      <img src={`data:image/png;base64,${m.thumb}`} draggable={false}
                        style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', display: 'block', pointerEvents: 'none' }} />
                    )}
                  </div>
                  <div style={{ fontSize: 10, fontWeight: 700, textAlign: 'center', color: usadaEn ? 'var(--success)' : 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={nombre}>
                    {nombre}{usadaEn ? ' ✓' : ''}
                  </div>
                </div>
              );
            })}
          </div>
          {mapeoData?.mesas?.length > 0 && selectedPiezaMapeo && mapeoValores[selectedPiezaMapeo] && (
            <button className="btn ghost" style={{ width: '100%', marginTop: 8, fontSize: 11, padding: '6px 8px' }} onClick={() => { const next = { ...mapeoValores }; delete next[selectedPiezaMapeo]; aplicarMapeo(next); }}>
              Quitar diseño de «{selectedPiezaMapeo}»
            </button>
          )}
        </div>
        )}
      </div>
    </div>
  );
}

// Modal reusable (diálogo centrado con fondo): los formularios de crear/editar van
// acá, NO metidos dentro de la lista. Cierra con ×, Escape o clic fuera.
function Modal({ open, onClose, titulo, subtitulo, children, maxWidth = 640, centrado = false }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = prev; };
  }, [open, onClose]);
  if (!open) return null;
  return createPortal(
    <div className="modal-overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose?.(); }}
      style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(0,0,0,0.62)', backdropFilter: 'blur(5px)', display: 'flex', alignItems: centrado ? 'center' : 'flex-start', justifyContent: 'center', padding: centrado ? '24px 20px' : '6vh 20px 24px', overflowY: 'auto' }}>
      <div className="modal-pop" onMouseDown={(e) => e.stopPropagation()}
        style={{ width: '100%', maxWidth, background: '#141417', border: '1px solid var(--border-light)', borderRadius: 16, boxShadow: '0 24px 70px rgba(0,0,0,0.6)', overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: '88vh' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, padding: '16px 20px', borderBottom: '1px solid var(--border-light)' }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 800 }}>{titulo}</div>
            {subtitulo && <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 3 }}>{subtitulo}</div>}
          </div>
          <button onClick={onClose} title="Cerrar (Esc)" style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 24, lineHeight: 1, padding: '0 2px', flexShrink: 0 }}>×</button>
        </div>
        <div style={{ padding: 20, overflowY: 'auto' }}>{children}</div>
      </div>
    </div>,
    document.body
  );
}

// ── Conversiones de color (CMYK 0..1 ↔ RGB 0..255 ↔ HSV ↔ HEX) ──
const _cmyk2rgb = (c) => ({ r: Math.round(255 * (1 - (c[0] || 0)) * (1 - (c[3] || 0))), g: Math.round(255 * (1 - (c[1] || 0)) * (1 - (c[3] || 0))), b: Math.round(255 * (1 - (c[2] || 0)) * (1 - (c[3] || 0))) });
const _rgb2cmyk = ({ r, g, b }) => { r /= 255; g /= 255; b /= 255; const k = 1 - Math.max(r, g, b); if (k >= 0.9999) return [0, 0, 0, 1]; return [(1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k].map(x => Math.round(x * 1000) / 1000); };
const _rgb2hex = ({ r, g, b }) => '#' + [r, g, b].map(x => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0')).join('');
const _hex2rgb = (h) => { h = (h || '').replace('#', '').trim(); if (h.length === 3) h = h.split('').map(c => c + c).join(''); if (!/^[0-9a-fA-F]{6}$/.test(h)) return null; const n = parseInt(h, 16); return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 }; };
const _rgb2hsv = ({ r, g, b }) => { r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let h = 0; if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; h *= 60; if (h < 0) h += 360; } return { h, s: mx ? d / mx : 0, v: mx }; };
const _hsv2rgb = ({ h, s, v }) => { const c = v * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - c; let r = 0, g = 0, b = 0; if (h < 60) [r, g, b] = [c, x, 0]; else if (h < 120) [r, g, b] = [x, c, 0]; else if (h < 180) [r, g, b] = [0, c, x]; else if (h < 240) [r, g, b] = [0, x, c]; else if (h < 300) [r, g, b] = [x, 0, c]; else [r, g, b] = [c, 0, x]; return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255), b: Math.round((b + m) * 255) }; };

function ColorPickerModal({ open, color, titulo, onClose, onApply }) {
  // Trabaja en HSV (UI fluida) + CMYK (salida exacta cuando se tipea CMYK).
  const [hsv, setHsv] = useState({ h: 0, s: 0, v: 0 });
  const [cmyk, setCmyk] = useState([0, 0, 0, 1]);
  const svRef = useRef(null), hueRef = useRef(null), drag = useRef(null);
  useEffect(() => { if (open) { const c = color || [0, 0, 0, 1]; setCmyk(c); setHsv(_rgb2hsv(_cmyk2rgb(c))); } }, [open]);
  if (!open) return null;
  const rgb = _hsv2rgb(hsv), hex = _rgb2hex(rgb);
  const fromHsv = (nh) => { setHsv(nh); setCmyk(_rgb2cmyk(_hsv2rgb(nh))); };
  const fromRgb = (nr) => { setHsv(_rgb2hsv(nr)); setCmyk(_rgb2cmyk(nr)); };
  const fromCmyk = (nc) => { setCmyk(nc); setHsv(_rgb2hsv(_cmyk2rgb(nc))); };
  const onSV = (e) => { const r = svRef.current.getBoundingClientRect(); const s = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); const v = Math.max(0, Math.min(1, 1 - (e.clientY - r.top) / r.height)); fromHsv({ ...hsv, s, v }); };
  const onHue = (e) => { const r = hueRef.current.getBoundingClientRect(); const h = Math.max(0, Math.min(359.9, ((e.clientY - r.top) / r.height) * 360)); fromHsv({ ...hsv, h }); };
  const startDrag = (which, e) => { drag.current = which; (which === 'sv' ? onSV : onHue)(e); const mv = (ev) => { if (drag.current === 'sv') onSV(ev); else onHue(ev); }; const up = () => { drag.current = null; window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); }; window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up); };
  const numIn = { width: 52, padding: '5px 7px', borderRadius: 6, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-light)', color: '#fff', fontSize: 12.5, textAlign: 'right' };
  const row = (lbl, val, on, max, suf) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, justifyContent: 'space-between' }}>
      <span style={{ fontSize: 12, color: 'var(--text-secondary)', width: 16 }}>{lbl}</span>
      <input type="number" min="0" max={max} value={val} onChange={(e) => on(parseFloat(e.target.value) || 0)} style={numIn} />
      {suf && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{suf}</span>}
    </div>
  );
  const hueColor = _rgb2hex(_hsv2rgb({ h: hsv.h, s: 1, v: 1 }));
  return (
    <Modal open={open} onClose={onClose} titulo={titulo || 'Selector de color'} maxWidth={520} centrado>
      <div style={{ display: 'flex', gap: 16 }}>
        {/* Cuadro Saturación / Brillo */}
        <div ref={svRef} onMouseDown={(e) => startDrag('sv', e)} style={{ position: 'relative', width: 230, height: 230, borderRadius: 8, cursor: 'crosshair', flexShrink: 0, background: `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, ${hueColor})` }}>
          <span style={{ position: 'absolute', left: `${hsv.s * 100}%`, top: `${(1 - hsv.v) * 100}%`, width: 14, height: 14, borderRadius: '50%', border: '2px solid #fff', boxShadow: '0 0 0 1px rgba(0,0,0,0.5)', transform: 'translate(-50%,-50%)', pointerEvents: 'none' }} />
        </div>
        {/* Barra de tono */}
        <div ref={hueRef} onMouseDown={(e) => startDrag('hue', e)} style={{ position: 'relative', width: 22, height: 230, borderRadius: 6, cursor: 'ns-resize', flexShrink: 0, background: 'linear-gradient(to bottom, #f00 0%, #f0f 17%, #00f 33%, #0ff 50%, #0f0 67%, #ff0 83%, #f00 100%)' }}>
          <span style={{ position: 'absolute', top: `${(hsv.h / 360) * 100}%`, left: -3, right: -3, height: 4, background: '#fff', border: '1px solid rgba(0,0,0,0.5)', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
        </div>
        {/* Valores */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 9, minWidth: 0 }}>
          <div style={{ height: 46, borderRadius: 8, border: '1px solid var(--border-light)', background: hex }} title="Color elegido" />
          {row('H', Math.round(hsv.h), (v) => fromHsv({ ...hsv, h: Math.max(0, Math.min(360, v)) }), 360, '°')}
          {row('S', Math.round(hsv.s * 100), (v) => fromHsv({ ...hsv, s: Math.max(0, Math.min(100, v)) / 100 }), 100, '%')}
          {row('B', Math.round(hsv.v * 100), (v) => fromHsv({ ...hsv, v: Math.max(0, Math.min(100, v)) / 100 }), 100, '%')}
          <div style={{ height: 1, background: 'var(--border-light)', margin: '1px 0' }} />
          {row('R', rgb.r, (v) => fromRgb({ ...rgb, r: Math.max(0, Math.min(255, v)) }), 255)}
          {row('G', rgb.g, (v) => fromRgb({ ...rgb, g: Math.max(0, Math.min(255, v)) }), 255)}
          {row('B', rgb.b, (v) => fromRgb({ ...rgb, b: Math.max(0, Math.min(255, v)) }), 255)}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 16, marginTop: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, auto)', gap: 8 }}>
          {['C', 'M', 'Y', 'K'].map((L, i) => (
            <div key={L} style={{ textAlign: 'center' }}>
              <input type="number" min="0" max="100" value={Math.round((cmyk[i] || 0) * 100)} onChange={(e) => { const c = [...cmyk]; c[i] = Math.max(0, Math.min(100, parseFloat(e.target.value) || 0)) / 100; fromCmyk(c); }} style={{ ...numIn, width: 46 }} />
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3, fontWeight: 700 }}>{L}</div>
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3, fontWeight: 700 }}>HEX</div>
          <input value={hex} onChange={(e) => { const r = _hex2rgb(e.target.value); if (r) fromRgb(r); }} style={{ ...numIn, width: 90, textAlign: 'left' }} />
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button className="btn ghost" onClick={onClose} style={{ padding: '8px 16px' }}>Cancelar</button>
          <button className="btn primary" onClick={() => { onApply(cmyk); onClose(); }} style={{ padding: '8px 18px' }}>OK</button>
        </div>
      </div>
    </Modal>
  );
}

export default function App() {
  const [activoTab, setActivoTab] = useState(() => {
    return window.location.pathname === '/admin' ? 'config' : 'pedidos';
  });
  const [estado, setEstado] = useState(null);
  const [productosCat, setProductosCat] = useState({ activo: 'prod_default', productos: [] });
  const [filas, setFilas] = useState([]);
  const [csvImport, setCsvImport] = useState(null);   // { filas:[{valores, issues:[{colId,label,raw,opciones}]}] } al importar CSV con valores inválidos
  const [csvFix, setCsvFix] = useState({});           // `${i}:${colId}` -> valor elegido para la celda inválida
  const [csvOmit, setCsvOmit] = useState({});         // i -> true si esa fila no se carga
  const [nFilasAgregar, setNFilasAgregar] = useState(1);   // cuántas filas agrega el botón "Agregar Fila"
  const [fuenteChars, setFuenteChars] = useState(null);    // Set de caracteres que SOPORTA la fuente del diseño (null = sin dato)
  const [plSel, setPlSel] = useState(null);       // planilla pedido: ANCLA del rango {r,c}
  const [plSelEnd, setPlSelEnd] = useState(null); // OTRA esquina del rango seleccionado {r,c}
  const [plFill, setPlFill] = useState(null);     // {r,c} destino del arrastre del fill-handle
  const [plSelDrag, setPlSelDrag] = useState(false); // true mientras se arrastra (corta userSelect)
  const plDragRef = useRef(null);                 // {r,c} esquina origen del fill-handle
  const plFillSrcRef = useRef(null);              // rango origen {r0,c0,r1,c1} al empezar a llenar
  const plSelDragRef = useRef(false);             // true mientras se selecciona un rango arrastrando
  const [modoDisenador, setModoDisenador] = useState(() => {
    return window.location.pathname === '/admin';
  });
  const [adminSubView, setAdminSubView] = useState('dashboard');
  const [columnasConfig, setColumnasConfig] = useState([]);
  const [config, setConfig] = useState(null);
  // TELAS: registro GLOBAL (nombre + ancho) + grupos combinables. La asignación pieza→tela vive
  // en el PEDIDO (telaBaseMolde/telaPorPieza, declarados abajo tras `_wiz`).
  const [telasReg, setTelasReg] = useState({ telas: [], grupos: [] });
  const [telasAsigMolde, setTelasAsigMolde] = useState([]);                        // telas (ids) asignadas al molde en edición
  const [telaSelPiezas, setTelaSelPiezas] = useState([]);                          // piezas (nombre genérico) seleccionadas para asignar tela
  const [telaModoVer, setTelaModoVer] = useState(false);                           // "Ver telas de pieza": pinta por tela + panel de telas
  const [telaModalOpen, setTelaModalOpen] = useState(false);                       // modal "Asignar tela al pedido"
  const [telaBusqueda, setTelaBusqueda] = useState('');                            // buscador del modal de telas
  const [trabajoId, setTrabajoId] = useState(null);
  const [trabajoEstado, setTrabajoEstado] = useState(null);
  // Avance del wizard guardado (para no perderlo al recargar la página). Se lee
  // una sola vez (no en cada render).
  const _wizRef = useRef(undefined);
  if (_wizRef.current === undefined) { try { _wizRef.current = JSON.parse(localStorage.getItem('tizada_wizard')) || {}; } catch { _wizRef.current = {}; } }
  const _wiz = _wizRef.current;
  // Pedido multi-molde: moldes elegidos (tarjetas) y un trabajo por molde.
  const [moldesSeleccionados, setMoldesSeleccionados] = useState(_wiz.moldesSeleccionados || []);
  const [trabajosMulti, setTrabajosMulti] = useState(_wiz.trabajosMulti || []); // [{productoId, nombre, jobId, estado, resultado, error}]
  const [telaActiva, setTelaActiva] = useState(_wiz.telaActiva ?? null); // pestaña de tela en los resultados
  const [telaBaseMolde, setTelaBaseMolde] = useState(_wiz.telaBaseMolde || {});   // { [pid]: telaId } — tela base del pedido
  const [telaPorPieza, setTelaPorPieza] = useState(_wiz.telaPorPieza || {});       // { [pid]: { [pieza]: telaId } } — override por pieza
  // Wizard del Pedido: paso actual + índice del molde en el paso de diseños.
  const [pedidoPaso, setPedidoPaso] = useState(_wiz.pedidoPaso || 'moldes'); // moldes | arte | planilla | generar | resultados
  const [arteIdx, setArteIdx] = useState(_wiz.arteIdx || 0);
  const [moldePreviews, setMoldePreviews] = useState({}); // { [id]: {img_w, img_h, piezas} }
  const [arteCargado, setArteCargado] = useState(_wiz.arteCargado || {}); // { ["<diseno>|<moldId>"]: true } — arte cargado en ESTE pedido
  // Múltiples DISEÑOS por pedido: cada diseño (nombre) tiene su arte por molde.
  // Los diseños se ESCRIBEN (ninguno hardcodeado). disenoMoldes = qué moldes van en cada diseño.
  const [disenosPedido, setDisenosPedido] = useState(_wiz.disenosPedido || []); // [{id(slug), nombre}]
  const [disenoMoldes, setDisenoMoldes] = useState(_wiz.disenoMoldes || {}); // { [disenoId]: [moldId...] } — derivado de las variables elegidas (el molde queda por detrás)
  const [disenoVars, setDisenoVars] = useState(_wiz.disenoVars || {}); // { [disenoId]: [claveVariable...] } — VARIABLE-FIRST: lo que se elige en el paso 1
  const [disenoActivo, setDisenoActivo] = useState(_wiz.disenoActivo || ''); // diseño que se está editando (paso 2)
  const [asignDiseno, setAsignDiseno] = useState('todos'); // a qué diseño se asignan los moldes en el paso 1 ('todos' o un id)
  const [nuevoDisenoNombre, setNuevoDisenoNombre] = useState(''); // input para escribir un diseño nuevo

  // Modales y Formularios
  const [creandoProducto, setCreandoProducto] = useState(false);
  const [nuevoProductoNombre, setNuevoProductoNombre] = useState('');
  const [modalEtqOpen, setModalEtqOpen] = useState(false);
  const [mapeandoOperario, setMapeandoOperario] = useState(false); // vista de mapeo visual en Pedidos
  const [moldeReload, setMoldeReload] = useState(0); // disparador para recargar la detección del molde
  const [etqData, setEtqData] = useState(null);
  const [visorView, setVisorView] = useState({ k: 1, tx: 0, ty: 0 });  // zoom/pan del Visor del Molde
  const [visorW, setVisorW] = useState(0);   // ancho en px del contenedor del visor (para tamaño real y número constante)
  const [visorH, setVisorH] = useState(0);   // alto en px del contenedor del visor (para "Ver todo")
  const [etqHover, setEtqHover] = useState(null);  // resaltado del contorno bajo el mouse (etiqueta)
  const [etqPiezaSel, setEtqPiezaSel] = useState(null);  // pieza cuya alineación se está editando (la última tocada)
  const [zonasModo, setZonasModo] = useState(false);     // ETIQUETA: modo "zonas de texto" (elegir esquinas → dividir la pieza en zonas)
  const [zonaSel, setZonaSel] = useState(0);             // índice de la zona cuyo contenido se edita
  const [etqSeleccion, setEtqSeleccion] = useState(null);
  const [etqNombres, setEtqNombres] = useState({});
  const [etqNombreInput, setEtqNombreInput] = useState('');
  const [modoAcomodar, setModoAcomodar] = useState(false);
  const [pzOffsets, setPzOffsets] = useState({});
  const [varPickerRow, setVarPickerRow] = useState(null);   // fila (índice) cuyo picker de VARIABLE está abierto (null = cerrado)
  const dragInfo = useRef({ idx: null, startX: 0, startY: 0, initialX: 0, initialY: 0, hasMoved: false });
  const [modalMapeoOpen, setModalMapeoOpen] = useState(false);
  const [mapeoData, setMapeoData] = useState(null);
  const [mapeoCargando, setMapeoCargando] = useState(false);   // cargando el mapeo de OTRA variable (1ª vez) → no dibujar diseños viejos
  const [asignando, setAsignando] = useState(null);            // ventana "Asignando el diseño a cada variante… {hecho,total,talle}" al cargar el arte
  const [mapeandoDiseno, setMapeandoDiseno] = useState(false); // tab Plantilla: false=medidas (default), true=mapear diseño sobre el molde
  const [mapeoValores, setMapeoValores] = useState({});
  const [previewPiezas, setPreviewPiezas] = useState({});   // {pieza: {svg, w_cm, h_cm}} = render REAL del motor por pieza (fuente única, WYSIWYG)
  const [selectedPiezaMapeo, setSelectedPiezaMapeo] = useState('');
  const [piezasSeleccionadas, setPiezasSeleccionadas] = useState([]);
  const [filtroPiezaConfig, setFiltroPiezaConfig] = useState('');
  const [modalConfirmOpen, setModalConfirmOpen] = useState(false);
  const [confirmProductoId, setConfirmProductoId] = useState('');
  const [modalTalleGuiaOpen, setModalTalleGuiaOpen] = useState(false);
  const [catalogoGrupos, setCatalogoGrupos] = useState([]);
  const [nuevaPiezaInput, setNuevaPiezaInput] = useState('');
  // Panel inline de selección de pieza en la barra lateral:
  // null = oculto · 'grupos' = lista de grupos · <nombre de grupo> = sus piezas
  const [panelPiezas, setPanelPiezas] = useState(null);
  const [nuevoGrupoInput, setNuevoGrupoInput] = useState('');
  
  // Spreadsheet template states
  const [plantillasPlanillas, setPlantillasPlanillas] = useState([]);
  const [planillaEditando, setPlanillaEditando] = useState(null);
  const [nombrePlanillaEditando, setNombrePlanillaEditando] = useState('');
  const [columnasPlanillaEditando, setColumnasPlanillaEditando] = useState([]);
  // Biblioteca de reglas (campos reutilizables) + columna seleccionada en el editor
  const [reglasPlanilla, setReglasPlanilla] = useState([]);
  const [nestingPresets, setNestingPresets] = useState([]); // presets de nesting (reglas de acomodo)
  const [colSeleccionada, setColSeleccionada] = useState(null); // índice de columna en edición (panel izq)
  const [reglaEditando, setReglaEditando] = useState(null); // regla en edición en el espacio de Reglas
  const [nestingEditando, setNestingEditando] = useState(null); // preset de nesting en edición
  const [gruposTizada, setGruposTizada] = useState([]); // grupos de moldes que comparten tizada
  const [grupoTizadaEditando, setGrupoTizadaEditando] = useState(null); // grupo en edición
  const [nestingTab, setNestingTab] = useState('presets'); // pestaña en Reglas de Nesting: presets | grupos
  const [perfilesData, setPerfilesData] = useState(null); // {perfiles, cmyk, rgb, config, hay_perfiles}
  const [perfilAviso, setPerfilAviso] = useState(null); // {estado, mensaje, incrustado, predeterminado, espacio} → modal al cargar diseño
  const [perfilesArte, setPerfilesArte] = useState({}); // { "<diseno>|<moldId>": {nombre, espacio} } perfil efectivo de cada arte cargado
  const [perfilUnificar, setPerfilUnificar] = useState(null); // {nombres:[...], espacio} → modal "elegí a qué perfil unificar"
  const [perfilForzado, setPerfilForzado] = useState(null); // archivo ICC elegido para unificar la exportación
  const [probandoPlanilla, setProbandoPlanilla] = useState(false); // modal de prueba de la planilla
  
  // Integrated workspace states
  // tabAjustesMolde: 'menu' (lista de botones) | 'molderia' | 'diseno' | 'planilla'
  const [tabAjustesMolde, setTabAjustesMolde] = useState('menu');
  // molderiaAbierta: id de la moldería en la que entramos a configurar (null = grilla)
  const [molderiaAbierta, setMolderiaAbierta] = useState(null);
  // modoMiMolde: pid del molde PROPIO que el usuario está configurando DESDE el pedido. No es
  // otra pantalla: es la misma config de Moldería en modo RECORTADO (sin el paso Variables, que
  // es de setup del catálogo) + salida directa de vuelta al pedido.
  const [modoMiMolde, setModoMiMolde] = useState(null);
  // Pestaña de la grilla del paso "Diseños": el catálogo compartido o lo que subió el usuario.
  const [pedidoTabMoldes, setPedidoTabMoldes] = useState('catalogo'); // 'catalogo' | 'mios'
  // Modal "Subir mi propio molde" (nombre + archivo).
  const [subirMoldeOpen, setSubirMoldeOpen] = useState(false);
  const [borrarArt, setBorrarArt] = useState(null);   // artículo propio a eliminar (modal de confirmación)
  const [subirMoldeNombre, setSubirMoldeNombre] = useState('');
  const [subirMoldeFile, setSubirMoldeFile] = useState(null);
  const [subirMoldeBusy, setSubirMoldeBusy] = useState(false);
  const [guiaCapasOpen, setGuiaCapasOpen] = useState(false);   // modal "qué va en cada capa del .ai"
  const [bordeConfig, setBordeConfig] = useState({ activo: true, ancho_mm: 2.0, color: [0, 0, 0, 0.85] });  // borde de corte del molde
  const [etiquetaConfig, setEtiquetaConfig] = useState(null);  // etiqueta de identificación del molde
  // ── Objetos editables (capa "Editable …" del diseño) ──
  const [editableData, setEditableData] = useState(null);      // {objetos, talles, piezas} del diseño activo
  const [editableDisenos, setEditableDisenos] = useState([]);  // diseños del molde que tienen objetos editables
  const [editableDiseno, setEditableDiseno] = useState('principal');  // diseño (id) en edición
  const [editableSel, setEditableSel] = useState([]);          // nombres de los objetos seleccionados (multi: Ctrl/Shift+click)
  const [edAlinearMesa, setEdAlinearMesa] = useState(false);   // false = alinear entre la SELECCIÓN; true = con la MESA DE TRABAJO
  const [edRotOpen, setEdRotOpen] = useState(false);           // desplegable de ángulos de rotación
  const [edSoloTalle, setEdSoloTalle] = useState(false);       // true = el ajuste va SOLO al talle en vista (no a todo el rango)
  const [edLink, setEdLink] = useState(true);                  // enlace An./Al.: true = escala proporcional
  const [editableTalle, setEditableTalle] = useState(null);    // talle/variante en edición
  const [editableScope, setEditableScope] = useState('todas'); // alcance: 'una' | 'rango' | 'todas'
  const [editableVarsSel, setEditableVarsSel] = useState([]);  // talles/variantes ELEGIDOS (scope) — popup de tarjetas
  const [editVarPickerOpen, setEditVarPickerOpen] = useState(false);
  // ── Modelos / Variables (arquitectura genérica; el TALLE queda aparte) ──
  const [variantesEdit, setVariantesEdit] = useState([]);   // [{clave,label,valores:[{id,label}]}] — TIPOS de pieza / VARIABLES (generadas)
  const [modelosEdit, setModelosEdit] = useState([]);       // [{id,nombre,variables:[{id,nombre,build:{clave:valorId}}]}]
  const [conjuntosEdit, setConjuntosEdit] = useState([]);   // [{id,nombre,piezas:[idx]}] — piezas que "van juntas" (multi-parte)
  const [gruposPz, setGruposPz] = useState([]);             // [{id,nombre,piezas:[idx]}] — GRUPOS de piezas (la generación corre dentro de cada uno)
  const [grupoPzAbierto, setGrupoPzAbierto] = useState(null); // id del grupo abierto en detalle | null = lista de grupos
  const [asignandoGrupoPz, setAsignandoGrupoPz] = useState(null); // id del grupo al que se le eligen piezas en el visor
  const [nuevoGrupoPzNombre, setNuevoGrupoPzNombre] = useState(''); // nombre para crear un grupo nuevo
  const [nuevaVarNombre, setNuevaVarNombre] = useState('');  // nombre para crear una variable A MANO dentro del grupo
  const [modeloSel, setModeloSel] = useState(0);            // índice del modelo activo
  const [varSel, setVarSel] = useState(null);               // índice de la variable en edición (null = ninguna)
  const [tiposAbierto, setTiposAbierto] = useState(true);   // sección "Tipos de pieza" expandida
  const [varGuardando, setVarGuardando] = useState(false);  // guardando variantes/modelos
  const [asignandoTipo, setAsignandoTipo] = useState(null); // clave del tipo al que se están asignando piezas desde el visor (null = ninguno)
  const [vinculandoJuntas, setVinculandoJuntas] = useState(null); // clave de la variable en la que se está armando un vínculo "van juntas" (null = ninguno)
  const [juntasSel, setJuntasSel] = useState(new Set());   // idxs elegidos para el vínculo en curso
  const [juntasNombre, setJuntasNombre] = useState('');    // nombre elegido para el vínculo (el de una de las piezas)
  const [asignandoConjunto, setAsignandoConjunto] = useState(null); // id del conjunto "van juntas" al que se le eligen piezas en el visor
  const [modalNombres, setModalNombres] = useState(false);   // ventana con los nombres puestos (renombrar / eliminar / quitar piezas)
  const [renombrarBuf, setRenombrarBuf] = useState(null);    // {gen, valor} — grupo de nombres en edición dentro del modal
  const [grupoNombresAbierto, setGrupoNombresAbierto] = useState(null); // nombre genérico expandido en el modal (muestra sus piezas)
  const [editandoNombre, setEditandoNombre] = useState(null); // nombre genérico que se está editando EN EL VISOR (tocar piezas suma/quita)
  const [guardandoNoms, setGuardandoNoms] = useState(false); // guardando nombres desde el modal
  const [modalTipoClave, setModalTipoClave] = useState(null); // clave del tipo cuya ventana emergente (lista de piezas) está abierta
  const [rubber, setRubber] = useState(null); // recuadro de selección (marquee) en el visor: {x0,y0,x1,y1} en px de pantalla
  const [varStep, setVarStep] = useState('nombrar'); // paso del flujo Variables: 'nombrar' | 'organizar'
  const [selNombrar, setSelNombrar] = useState(() => new Set()); // piezas seleccionadas en el paso "Nombrar"
  // ── Variantes POR PIEZAS (molde con TODO en una sola capa): se seleccionan piezas en el visor y
  // se les escribe el nombre de la variante. Reusa `selNombrar` + el marquee (`iniciarRubber`).
  const [varPzModo, setVarPzModo] = useState(false);      // herramienta activa (el visor pasa a modo selección)
  const [varPzAsig, setVarPzAsig] = useState({});          // {pieza_idx: "nombre de variante"}
  const [varPzInput, setVarPzInput] = useState('');        // texto libre: una letra, un número o palabras
  const [varPzGuardando, setVarPzGuardando] = useState(false);
  // GUARDADO AUTOMÁTICO del borrador: el trabajo («estas 6 piezas son la M») se perdía entero si
  // el usuario salía sin apretar Aplicar. Aplicar PARTE el PDF (caro) → no se puede hacer en cada
  // clic; lo que se persiste solo es la asignación cruda, y aplicar queda para cuando termina.
  const [varPzAplicado, setVarPzAplicado] = useState({});  // lo que YA está partido en el molde
  const [varPzEstado, setVarPzEstado] = useState('');       // '', 'guardando', 'guardado', 'error'
  const varPzUltimo = useRef(null);                         // última asignación persistida (JSON)
  // ── EMPAREJAR TALLES (§10.c): cuando el molde NO trae las piezas dispuestas parecido en cada
  // talle, la heurística de propagación de nombres no tiene señal. Acá el usuario SELECCIONA
  // piezas y las REACOMODA (virtual, solo para emparejar) y/o corrige a mano la pieza homóloga.
  const [empModo, setEmpModo] = useState(false);
  const [empData, setEmpData] = useState(null);      // GET /api/plantilla/emparejado
  const [empTalle, setEmpTalle] = useState(null);    // talle que se está corrigiendo (≠ guía)
  const [empFijar, setEmpFijar] = useState(null);    // nombre de pieza esperando "tocá la correcta"
  const [empGuardando, setEmpGuardando] = useState(false);
  // Camino PRINCIPAL (§10.c): agrupar piezas homólogas. Un solo gesto — tocar la pieza en el
  // talle guía, escribirle el nombre y confirmar: eso define a la vez CÓMO SE LLAMA y CUÁL ES
  // en cada talle. El panel viejo (reacomodar/corregir por índice) queda como 'avanzado'.
  const [empVista, setEmpVista] = useState('simple');   // 'simple' (agrupar) | 'avanzado'
  const [empNombreInput, setEmpNombreInput] = useState('');
  // TODAS LAS VARIANTES JUNTAS: el gesto es el MISMO que nombrar piezas — se ven todas las piezas
  // de todos los talles a la vez, se seleccionan las que son la misma y se escribe el nombre. Eso
  // define de una el nombre Y la correspondencia. Sólo sirve en moldes `extendido`: si los talles
  // están dibujados uno encima del otro (`anidado`) se cae al flujo de a un talle (§10.c).
  const [empTodas, setEmpTodas] = useState(false);        // la vista junta está activa
  const [empTodasData, setEmpTodasData] = useState(null); // GET /api/plantilla/deteccion_todas
  const [empTodasMotivo, setEmpTodasMotivo] = useState(''); // por qué NO se pudo mostrar todo junto
  const [empGrupoSel, setEmpGrupoSel] = useState('');    // grupo elegido para decir «esta pieza es esa»
  // Lista de grupos: con 36 piezas la lista cruda es ilegible (36 filas idénticas con los mismos
  // chips y el mismo botón). Se muestra POR MINIATURA, filtrada por lo que falta, y una sola fila
  // abierta a la vez — el detalle (chips por talle) sólo aparece en la fila que se está mirando.
  const [empGuiaPzs, setEmpGuiaPzs] = useState([]);      // piezas del talle GUÍA (para las miniaturas)
  const [empFiltro, setEmpFiltro] = useState('pend');    // 'pend' | 'listas' | 'todas'
  const [empAbierto, setEmpAbierto] = useState(null);    // nombre del grupo expandido (uno solo)
  const [empBuscar, setEmpBuscar] = useState('');
  const [empRenombrar, setEmpRenombrar] = useState(null); // {nombre, valor} edición en línea del nombre
  const empRenomCancel = React.useRef(false);            // Escape: el blur que viene después NO debe guardar
  const [resaltarNombre, setResaltarNombre] = useState(null); // nombre genérico resaltado en el visor (lista de piezas agrupada)
  const [grupoAislado, setGrupoAislado] = useState(null);   // clave del grupo abierto en DETALLE (visor aislado + edición); null = lista de grupos
  const [nuevoGrupoNombre, setNuevoGrupoNombre] = useState(''); // nombre para crear una VARIABLE nueva (Paso 2)
  const [modeloAbierto, setModeloAbierto] = useState(null); // id del MODELO (grupo de variables) abierto en detalle (Paso 3) | null = lista
  const [nuevoModeloNombre, setNuevoModeloNombre] = useState(''); // nombre para crear un modelo nuevo
  // ── Visor "acomodar" con TODOS los talles nesteados por pieza ──
  const [nidoData, setNidoData] = useState(null);           // {vb,w,h,piezas:[{nombre,cx,cy,talles:[{talle,d}]}]}
  const [nidoLoading, setNidoLoading] = useState(false);
  const [nidoError, setNidoError] = useState(null);         // si el nido no se pudo armar (ej. sin nombres) → visor normal
  const [nidoOffsets, setNidoOffsets] = useState({});       // {nombre: {x,y}} desplazamiento a mano (px del marco del nido)
  const nidoDragRef = useRef(false);                        // ¿se está arrastrando una pieza del nido? (congela el viewBox)
  const nidoVbRef = useRef(null);                           // último viewBox del nido calculado sin arrastrar (para congelar)
  const [verVariante, setVerVariante] = useState(null);     // clave de la variante a VER acomodada en Plantilla/Etiqueta (null = todas, vista normal)
  const [comboVisor, setComboVisor] = useState(null);       // combinación (array de idx) que se está mostrando en el visor al tocar una variable generada
  const [editableRangoTo, setEditableRangoTo] = useState(null); // talle "hasta" cuando el alcance es 'rango'
  const [editorEditOpen, setEditorEditOpen] = useState(false); // modal del editor de objetos (en Pedidos→Arte)
  const [editorTfs, setEditorTfs] = useState({});   // {obj: {talle: {dx,dy,rot,scale}}} transformaciones en edición
  const editorTfsRef = useRef({});                  // espejo de editorTfs (leer el valor actual sin re-crear closures)
  React.useEffect(() => { editorTfsRef.current = editorTfs; }, [editorTfs]);
  const editorSvgRef = useRef(null);                // <svg> del editor (para mapear pantalla→viewBox)
  const [edVB, setEdVB] = useState(null);           // viewBox del visor del editor (pan/zoom); null = auto (variante)
  const editorDrag = useRef(null);                  // estado de arrastre activo
  const editorCtx = useRef(null);                   // contexto cargado (pid|diseño|variante) → al reabrir el MISMO, conservar lo editado
  // ── Historial del editor de editables (deshacer/rehacer + Ctrl+Z) ──
  const editorHist = useRef({ stack: [], idx: -1 });   // pila de snapshots de editorTfs
  const [editorHistVer, setEditorHistVer] = useState(0);   // fuerza re-render de los botones (habilitar/deshabilitar)
  const _clonetf = (t) => JSON.parse(JSON.stringify(t || {}));
  const histReset = (tfs) => { editorHist.current = { stack: [_clonetf(tfs)], idx: 0 }; setEditorHistVer(v => v + 1); };
  const histCommit = (tfs) => {
    const h = editorHist.current;
    if (h.idx >= 0 && JSON.stringify(h.stack[h.idx]) === JSON.stringify(tfs)) return;   // sin cambio real
    const stack = h.stack.slice(0, h.idx + 1); stack.push(_clonetf(tfs));
    if (stack.length > 120) stack.shift();
    editorHist.current = { stack, idx: stack.length - 1 }; setEditorHistVer(v => v + 1);
  };
  const editorUndo = () => { const h = editorHist.current; if (h.idx > 0) { h.idx -= 1; setEditorTfs(_clonetf(h.stack[h.idx])); setEditorHistVer(v => v + 1); } };
  const editorRedo = () => { const h = editorHist.current; if (h.idx < h.stack.length - 1) { h.idx += 1; setEditorTfs(_clonetf(h.stack[h.idx])); setEditorHistVer(v => v + 1); } };
  // Ctrl+Z = deshacer · Ctrl+Y / Ctrl+Shift+Z = rehacer (solo con el editor abierto).
  React.useEffect(() => {
    if (!editorEditOpen) return;
    const onKey = (e) => {
      const k = (e.key || '').toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === 'z' && !e.shiftKey) { e.preventDefault(); editorUndo(); }
      else if ((e.ctrlKey || e.metaKey) && (k === 'y' || (k === 'z' && e.shiftKey))) { e.preventDefault(); editorRedo(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editorEditOpen]);
  // ── Config de TAMAÑO de capas editables (molde, por nombre de capa, por rangos de variantes) ──
  const [editConfig, setEditConfig] = useState([]);        // [{capa, rangos:[{variantes, apaisado, vertical}]}]
  const [editConfigVariantes, setEditConfigVariantes] = useState([]);  // variantes del molde (orden de archivo)
  const [editModal, setEditModal] = useState(null);  // {idx, draft} de la capa en edición en el modal (o null)
  const [verAyudaExport, setVerAyudaExport] = useState(false);  // Molde: guía de cómo exportar desde AI/Corel/Optitex
  const [procesando, setProcesando] = useState(null);          // overlay "cargando" al subir molde/arte (null = oculto)
  const [configMedida, setConfigMedida] = useState('default');  // Plantilla: cómo se adapta el diseño → 'default' | 'rango' | 'talle'
  const [rangoMedida, setRangoMedida] = useState([]);           // variantes del rango (modo 'rango')
  const rangoLastRef = useRef(null);                            // para shift+click en el rango
  const [medidasVar, setMedidasVar] = useState(null);          // medidas de TODAS las variantes (para 'rango')
  const [picker, setPicker] = useState(null);  // {titulo, color, onApply} para el ColorPickerModal
  const [mapeoColumnas, setMapeoColumnas] = useState({
    talle: 'talle',
    nombre: 'nombre',
    numero: 'numero',
    manga: 'manga',
    manga_corta_val: 'corta',
    manga_larga_val: 'larga'
  });
  const [selectedPlanillaTemplateId, setSelectedPlanillaTemplateId] = useState('plan_default');
  const [terminologiaEdit, setTerminologiaEdit] = useState({ variante: 'Talle', molde: 'Molde' });
  const [nombreMoldeEdit, setNombreMoldeEdit] = useState('');
  
  // Previsualizador Vectorial Zoom
  const [zoomPreviewUrl, setZoomPreviewUrl] = useState(null);
  const [zoomState, setZoomState] = useState({ zoom: 1.0, pan: { x: 0, y: 0 } });
  const zoomLevel = zoomState.zoom;
  const panOffset = zoomState.pan;
  const [esArrastrando, setEsArrastrando] = useState(false);
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const viewerRef = useRef(null);
  const [zoomSvgContent, setZoomSvgContent] = useState('');

  const handleZoom = (newScale, clientX, clientY) => {
    setZoomState(prev => {
      // Limit zoom: max 50,000% (scale 500.0), min 100% (scale 1.0)
      const clampedScale = Math.max(1.0, Math.min(500.0, newScale));
      
      if (clampedScale === 1.0) {
        return { zoom: 1.0, pan: { x: 0, y: 0 } };
      }
      
      let newPan = prev.pan;
      if (clientX !== undefined && clientY !== undefined && viewerRef.current) {
        const rect = viewerRef.current.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const cx = clientX - centerX;
        const cy = clientY - centerY;
        
        const k = clampedScale / prev.zoom;
        newPan = {
          x: cx * (1 - k) + prev.pan.x * k,
          y: cy * (1 - k) + prev.pan.y * k
        };
      } else {
        const k = clampedScale / prev.zoom;
        newPan = {
          x: prev.pan.x * k,
          y: prev.pan.y * k
        };
      }
      
      return { zoom: clampedScale, pan: newPan };
    });
  };

  useEffect(() => {
    if (!zoomPreviewUrl) {
      setZoomSvgContent('');
      return;
    }
    fetch(zoomPreviewUrl)
      .then(res => {
        if (!res.ok) throw new Error("Error loading SVG");
        return res.text();
      })
      .then(text => {
        setZoomSvgContent(text);
      })
      .catch(err => {
        console.error("Error fetching preview SVG:", err);
        setZoomSvgContent('');
      });
  }, [zoomPreviewUrl]);

  // Feedback
  const [mensajeInformativo, setMensajeInformativo] = useState('');
  const [errorInformativo, setErrorInformativo] = useState('');
  const [advertenciaInformativa, setAdvertenciaInformativa] = useState('');
  
  const fileInputPlantillaRef = useRef(null);
  const fileInputMiMoldeRef = useRef(null);   // molde propio subido desde el pedido
  const fileInputArteRef = useRef(null);
  const fileInputFuenteRef = useRef(null);
  const [muestraGlobal, setMuestraGlobal] = useState('');   // texto de prueba: se ve en TODAS las tarjetas del catálogo
  const [fuenteABorrar, setFuenteABorrar] = useState(null); // archivo con la confirmación de borrado abierta
  const [fuenteDetalle, setFuenteDetalle] = useState(null); // fuente abierta en su pantalla de detalle (null = la lista)
  const [buscarFuente, setBuscarFuente] = useState('');     // filtro del catálogo (nombre interno o archivo)
  // SESIÓN: quién soy y qué puedo. Sirve para pintar la UI; quien PROTEGE es el backend.
  const [yo, setYo] = useState(null);
  const [authListo, setAuthListo] = useState(false);   // ya se consultó /yo (evita parpadeo del login)
  const [authOn, setAuthOn] = useState(true);          // ¿la API de usuarios está viva? (si no, no se exige login)
  const recargarYo = () => fetch('/api/auth/yo').then(r => r.json())
    .then(d => { setYo(d.usuario || null); setAuthOn(true); })
    .catch(() => { setYo(null); setAuthOn(false); })
    .finally(() => setAuthListo(true));
  useEffect(() => { recargarYo(); }, []);
  const cerrarSesion = () => fetch('/api/auth/logout', { method: 'POST' }).then(() => setYo(null));
  // AL INICIAR SESIÓN hay que volver a pedir el catálogo. La app se monta ANTES del login (la
  // pantalla de login se dibuja recién al final del render), así que el fetch del arranque sale
  // SIN sesión y el server oculta los moldes propios de quien no está identificado: la lista
  // quedaba con un solo molde para toda la sesión → "Mis artículos" vacío y subir el mismo molde
  // creaba OTRO artículo cada vez (así aparecieron 4 «Molde short»).
  useEffect(() => {
    if (!yo?.id) return;
    fetchProductos();
    fetchEstado();
    fetchCatalogoPiezas();
  }, [yo?.id]);

  // Valores derivados del estado. DEBEN declararse antes que los useEffect/useMemo
  // que los referencian (p. ej. en sus arrays de dependencias), de lo contrario
  // se produce un ReferenceError de "Temporal Dead Zone" al iniciar la app.
  const activoProdDetalle = productosCat.productos.find(p => p.id === productosCat.activo);

  // EL MOLDE QUE SE ESTÁ CONFIGURANDO. Todo guardado del flujo de configuración tiene que ir
  // contra ESTE pid y mandarlo explícito: si no, el endpoint escribe en el molde "activo" del
  // server, que llega TARDE (`handleActivarProducto` es async y no se espera al abrir la moldería)
  // y que además se resetea cuando la sesión se cae. Con varios artículos con el MISMO nombre,
  // eso terminaba guardando el nombrado de piezas en el molde equivocado.
  const pidCfg = molderiaAbierta || modoMiMolde || productosCat.activo || '';
  // Sufijo `?pid=`/`&pid=` listo para pegar en una URL de GET.
  const qPid = (sep = '?') => (pidCfg ? `${sep}pid=${encodeURIComponent(pidCfg)}` : '');

  const cols = activoProdDetalle?.columnas || [
    { id: 'talle', label: 'Talle', role: 'talle' },
    { id: 'nombre', label: 'Nombre', role: 'nombre' },
    { id: 'numero', label: 'Número', role: 'numero' },
    { id: 'manga', label: 'Manga', role: 'manga' }
  ];

  // Terminología configurable del producto activo (cómo se llaman los conceptos
  // de cara al usuario). Solo cambian las etiquetas; el funcionamiento es igual.
  const term = { variante: 'Talle', molde: 'Molde', ...(activoProdDetalle?.terminologia || {}) };

  // Mapa pieza(idx) → clave del tipo al que fue asignada (pestaña Variables). Se
  // usa para colorear las piezas en el visor y saber a qué grupo pertenece cada una.
  const piezaTipoMap = React.useMemo(() => {
    const m = {};
    (variantesEdit || []).forEach(t => (t.valores || []).forEach(v => {
      if (v.pieza_idx != null) m[v.pieza_idx] = t.clave;
    }));
    return m;
  }, [variantesEdit]);

  // Grupos para el selector: catálogo guardado + las piezas que ya tiene ESTE
  // molde (registro) se suman a "Prenda Superior". Así siempre se ven aunque
  // el catálogo falle.
  const gruposParaElegir = React.useMemo(() => {
    const grupos = (catalogoGrupos || []).map(g => ({ nombre: g.nombre, piezas: [...(g.piezas || [])] }));
    let sup = grupos.find(g => (g.nombre || '').toLowerCase() === 'prenda superior');
    if (!sup) { sup = { nombre: 'Prenda Superior', piezas: [] }; grupos.unshift(sup); }
    const vistos = new Set(grupos.flatMap(g => g.piezas.map(p => p.toLowerCase())));
    for (const p of Object.values(etqNombres || {}).map(v => String(v).trim()).filter(Boolean)) {
      if (!vistos.has(p.toLowerCase())) { sup.piezas.push(p); vistos.add(p.toLowerCase()); }
    }
    return grupos;
  }, [catalogoGrupos, etqNombres]);

  const canvasLayout = React.useMemo(() => {
    // AGRUPAR con todas las variantes juntas: el visor dibuja las piezas de TODOS los talles
    // (mismo lienzo, mismas coordenadas en mm). Es la MISMA lista de siempre — cada pieza trae
    // además `talle` y `t_idx` (su índice dentro de su talle = el `pieza_idx` del registro).
    const src = (empModo && empTodas && empTodasData?.piezas?.length) ? empTodasData : etqData;
    if (!src?.piezas) return { layout: [], width: 850, height: 400, vb: '0 0 850 400' };

    // Siempre usar las posiciones originales del PDF
    const layout = src.piezas.map((p) => ({
      ...p,
      tx: 0,
      ty: 0,
      x_new: p.px,
      y_new: p.py
    }));

    const W = src.img_w || 850, H = src.img_h || 400;
    // El viewBox debe ABARCAR todas las piezas: sus coordenadas pueden exceder
    // img_w/img_h (el pixmap se recorta al borde de la página, las coords no) →
    // si no, las piezas del borde derecho/inferior se ven CORTADAS.
    let minX = 0, minY = 0, maxX = W, maxY = H;
    src.piezas.forEach(p => {
      minX = Math.min(minX, p.px); minY = Math.min(minY, p.py);
      maxX = Math.max(maxX, p.px + p.pw); maxY = Math.max(maxY, p.py + p.ph);
    });
    const PAD = Math.max(6, Math.max(maxX - minX, maxY - minY) * 0.01);
    const vbW = maxX - minX + 2 * PAD, vbH = maxY - minY + 2 * PAD;
    const vb = `${(minX - PAD).toFixed(1)} ${(minY - PAD).toFixed(1)} ${vbW.toFixed(1)} ${vbH.toFixed(1)}`;

    // Escala real: cm por unidad de viewBox (promedio de las piezas con medida).
    // Sirve para mostrar el zoom relativo al TAMAÑO REAL (100% = 1:1), no al "ver todo".
    let sumCm = 0, nCm = 0;
    src.piezas.forEach(p => {
      if (p.pw > 2 && p.w_cm > 0) { sumCm += p.w_cm / p.pw; nCm++; }
      if (p.ph > 2 && p.h_cm > 0) { sumCm += p.h_cm / p.ph; nCm++; }
    });
    const cmPerUnit = nCm ? sumCm / nCm : 0;

    // ── LUGAR PARA EL RÓTULO ──────────────────────────────────────────────────
    // Cada pieza dibuja su chapita (número + nombre) en su CENTRO. Cuando las piezas se
    // superponen —36 piezas de 6 variantes, o el molde sin separar— esos centros caen casi
    // encima y los rótulos se pisan («2XL 2XL» ilegible). `sep` = distancia (en unidades del
    // viewBox) al centro más cercano: multiplicada por el zoom da los PÍXELES DE PANTALLA
    // disponibles, que es lo único que decide si el rótulo se lee o no.
    const cen = layout.map(p => [p.px + p.pw / 2, p.py + p.ph / 2]);
    const sep = new Map();
    layout.forEach((p, i) => {
      let d2 = Infinity;
      for (let j = 0; j < cen.length; j++) {
        if (j === i) continue;
        const dx = cen[i][0] - cen[j][0], dy = cen[i][1] - cen[j][1];
        const v = dx * dx + dy * dy;
        if (v < d2) d2 = v;
      }
      sep.set(p.idx, Math.sqrt(d2));
    });

    // Vista de TODAS las variantes juntas: cada variante es un bloque de piezas. El nombre de la
    // variante va UNA vez por bloque (antes iba en cada pieza: 36 rótulos encimados).
    let clusters = null;
    if (layout.length && layout[0].talle != null) {
      const cajas = new Map();
      layout.forEach(p => {
        const c = cajas.get(p.talle) || { talle: p.talle, x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity, n: 0 };
        c.x0 = Math.min(c.x0, p.px); c.y0 = Math.min(c.y0, p.py);
        c.x1 = Math.max(c.x1, p.px + p.pw); c.y1 = Math.max(c.y1, p.py + p.ph);
        c.n++;
        cajas.set(p.talle, c);
      });
      clusters = [...cajas.values()];
    }

    return { layout, width: W, height: H, vb, vbW, vbH, cmPerUnit, sep, clusters };
  }, [etqData, empModo, empTodas, empTodasData]);

  // Las variantes del MOLDE. `etqData.talles` es de la DETECCIÓN que se está mostrando: en la
  // vista «asignar variantes por piezas» son las capas del archivo original (una sola, «Capa 1»).
  // Todo lo que hable de las variantes del molde tiene que salir de acá.
  const tallesMolde = React.useMemo(
    () => (etqData?.talles_reales?.length ? etqData.talles_reales : (etqData?.talles || [])), [etqData]);

  // Píxeles de PANTALLA que necesita una chapita para leerse: el círculo mide 22 px, así que con
  // menos de 24 px hasta la otra pieza los números se pisan → se deja sólo un punto (el rótulo
  // vuelve acercando el zoom o tocando la pieza). Los TEXTOS de arriba/abajo (variante, nombre de
  // la pieza) son mucho más anchos que el círculo y necesitan bastante más aire: TXT_MIN_PX.
  const LBL_MIN_PX = 24;
  const TXT_MIN_PX = 60;
  const rotulosOcultos = React.useMemo(() => {
    const s = canvasLayout.sep;
    if (!s) return 0;
    const k = visorView.k || 1;
    let n = 0;
    s.forEach(v => { if (v * k < LBL_MIN_PX) n++; });
    return n;
  }, [canvasLayout, visorView.k]);

  // ───────── Deshacer / Rehacer (Ctrl+Z / Ctrl+Y) ─────────
  // Historial de los estados editables del cliente. Cada cambio guarda una
  // instantánea; Ctrl+Z restaura la anterior, Ctrl+Y / Ctrl+Shift+Z la siguiente.
  const histRef = useRef({ stack: [], ptr: -1, skip: false, last: null });
  const undoSnapshot = { filas, etqNombres, pzOffsets, mapeoValores };

  useEffect(() => {
    const h = histRef.current;
    if (h.skip) { h.skip = false; return; }
    const snap = JSON.stringify(undoSnapshot);
    if (snap === h.last) return;
    h.stack = h.stack.slice(0, h.ptr + 1);   // descartar rama de "rehacer"
    h.stack.push(snap);
    if (h.stack.length > 120) h.stack.shift();
    h.ptr = h.stack.length - 1;
    h.last = snap;
  }, [filas, etqNombres, pzOffsets, mapeoValores]);

  const aplicarSnapshot = (snap) => {
    const s = JSON.parse(snap);
    const h = histRef.current;
    h.skip = true;
    h.last = snap;
    setFilas(s.filas);
    setEtqNombres(s.etqNombres);
    setPzOffsets(s.pzOffsets);
    setMapeoValores(s.mapeoValores);
  };

  const deshacer = () => {
    const h = histRef.current;
    if (h.ptr <= 0) { showMsg('Nada para deshacer'); return; }
    h.ptr -= 1;
    aplicarSnapshot(h.stack[h.ptr]);
    showMsg('Deshecho ↶  (Ctrl+Y para rehacer)');
  };

  const rehacer = () => {
    const h = histRef.current;
    if (h.ptr >= h.stack.length - 1) { showMsg('Nada para rehacer'); return; }
    h.ptr += 1;
    aplicarSnapshot(h.stack[h.ptr]);
    showMsg('Rehecho ↷');
  };

  // refs para evitar closures obsoletas en el listener de teclado (deps [])
  const deshacerRef = useRef(() => {});
  const rehacerRef = useRef(() => {});
  // Con el editor de EDITABLES abierto, Ctrl+Z/Ctrl+Y van a SU historial (el mismo que los botones
  // ↶/↷ del editor). El global restaura filas/etqNombres/pzOffsets/mapeoValores — estado del que
  // depende el editor para dibujar — así que ahí dentro dejaba el visor en negro en vez de deshacer.
  deshacerRef.current = () => {
    if (!editorEditOpen) return deshacer();
    const h = editorHist.current;
    if (h.idx <= 0) { showMsg('Nada para deshacer'); return; }
    editorUndo(); showMsg('Deshecho ↶  (Ctrl+Y para rehacer)');
  };
  rehacerRef.current = () => {
    if (!editorEditOpen) return rehacer();
    const h = editorHist.current;
    if (h.idx >= h.stack.length - 1) { showMsg('Nada para rehacer'); return; }
    editorRedo(); showMsg('Rehecho ↷');
  };

  useEffect(() => {
    const onKey = (e) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const k = (e.key || '').toLowerCase();
      if (k === 'z' && !e.shiftKey) { e.preventDefault(); deshacerRef.current(); }
      else if (k === 'y' || (k === 'z' && e.shiftKey)) { e.preventDefault(); rehacerRef.current(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // URL routing POPSTATE listener and navegarA helper
  const navegarA = (ruta) => {
    window.history.pushState({}, '', ruta);
    const isSearchAdmin = ruta === '/admin';
    setModoDisenador(isSearchAdmin);
    setActivoTab(isSearchAdmin ? 'config' : 'pedidos');
    setAdminSubView('dashboard');
  };

  useEffect(() => {
    const handleLocationChange = () => {
      const isSearchAdmin = window.location.pathname === '/admin';
      setModoDisenador(isSearchAdmin);
      setActivoTab(isSearchAdmin ? 'config' : 'pedidos');
      setAdminSubView('dashboard');
    };
    window.addEventListener('popstate', handleLocationChange);
    return () => window.removeEventListener('popstate', handleLocationChange);
  }, []);

  // Load filas and columns configuration when active product changes
  useEffect(() => {
    if (!productosCat.activo) return;
    const key = `tizada_filas_${productosCat.activo}`;
    const saved = localStorage.getItem(key);
    const activoProd = productosCat.productos.find(p => p.id === productosCat.activo);
    const cols = activoProd?.columnas || [
      { id: 'talle', label: 'Talle', role: 'talle' },
      { id: 'nombre', label: 'Nombre', role: 'nombre' },
      { id: 'numero', label: 'Número', role: 'numero' },
      { id: 'manga', label: 'Manga', role: 'manga' }
    ];
    
    const defaultRow = {};
    cols.forEach(c => {
      if (c.role === 'talle') defaultRow[c.id] = (estado?.talles?.[0] || 'M');
      else if (c.role === 'manga') defaultRow[c.id] = 'corta';
      else if (c.role === 'diseno') defaultRow[c.id] = ((disenosPedido.find(d => d.id === disenoActivo) || disenosPedido[0])?.nombre || 'Principal');   // arranca con el diseño que se editó en el Arte
      else defaultRow[c.id] = '';
    });
    
    if (saved) {
      try {
        setFilas(JSON.parse(saved));
      } catch (e) {
        setFilas([defaultRow]);
      }
    } else {
      setFilas([defaultRow]);
    }

    if (activoProd) {
      setColumnasConfig(activoProd.columnas || cols);
    }
  }, [productosCat.activo, productosCat.productos, estado?.talles]);

  // Sync rows of active product to local storage
  useEffect(() => {
    if (!productosCat.activo || filas.length === 0) return;
    const key = `tizada_filas_${productosCat.activo}`;
    localStorage.setItem(key, JSON.stringify(filas));
  }, [filas, productosCat.activo]);

  const handleUpdateColumnConfig = (idx, field, val) => {
    const next = [...columnasConfig];
    next[idx][field] = val;
    if (field === 'label') {
      const norm = val.toLowerCase().replace(/[^a-z0-9]/g, '_').trim();
      next[idx]['id'] = norm || `col_${idx}`;
    }
    setColumnasConfig(next);
  };

  const handleAddColumnConfig = () => {
    setColumnasConfig([...columnasConfig, { id: `col_${columnasConfig.length}`, label: '', role: 'none' }]);
  };

  const handleRemoveColumnConfig = (idx) => {
    setColumnasConfig(columnasConfig.filter((_, i) => i !== idx));
  };

  const handleSaveColumnConfig = async () => {
    if (!columnasConfig.some(c => c.role === 'talle')) {
      showError("Debe haber al menos una columna con el rol 'Talle'");
      return;
    }
    try {
      const res = await fetch('/api/productos/config_columnas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: productosCat.activo,
          columnas: columnasConfig
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      showMsg("Configuración de columnas guardada ✓");
      await fetchProductos();
    } catch (err) {
      showError(err.message);
    }
  };

  // Load general state on mount & catalog
  useEffect(() => {
    fetchEstado();
    fetchProductos();
    fetchCatalogoPiezas();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setModalEtqOpen(false);
        setModalMapeoOpen(false);
        setModalConfirmOpen(false);
        setModalTalleGuiaOpen(false);
        setCreandoProducto(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const fetchEstado = async () => {
    try {
      const res = await fetch('/api/estado_general');
      const data = await res.json();
      setEstado(data);
    } catch (e) {
      console.error("Error al conectar con servidor", e);
    }
  };

  const fetchProductos = async () => {
    try {
      const res = await fetch('/api/productos');
      const data = await res.json();
      setProductosCat(data);
      setConfirmProductoId(data.activo);
    } catch (e) {
      console.error("Error al obtener catálogo", e);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch(`/api/config${qPid()}`);
      const data = await res.json();
      setConfig(data);
    } catch (e) {
      console.error("Error al obtener configuración", e);
    }
  };

  // TELAS: registro global (nombre+ancho) + grupos combinables.
  const fetchTelas = async () => {
    try {
      const r = await fetch('/api/telas');
      if (r.ok) setTelasReg(await r.json());
    } catch (e) { console.error('telas', e); }
  };
  const guardarTelas = async (telas, grupos) => {
    try {
      const r = await fetch('/api/telas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ telas, grupos }) });
      if (r.ok) { setTelasReg(await r.json()); showMsg('Telas guardadas ✓'); }
    } catch (e) { showError('No se pudieron guardar las telas'); }
  };
  const guardarTelasAsignadas = async (pid, telaIds) => {
    try {
      await fetch('/api/productos/telas_asignadas', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: pid, telas: telaIds }) });
    } catch (e) { showError('No se pudieron guardar las telas del molde'); }
  };
  // Color guía por tela (paleta fija, determinística por posición en el registro).
  const _PALETA_TELAS = ['#22d3ee', '#a78bfa', '#f472b6', '#facc15', '#34d399', '#fb923c', '#60a5fa', '#f87171', '#e879f9', '#4ade80'];
  const colorDeTela = (telaId) => {
    const i = (telasReg.telas || []).findIndex(t => t.id === telaId);
    return i >= 0 ? _PALETA_TELAS[i % _PALETA_TELAS.length] : '#9ca3af';
  };
  const nombreDeTela = (telaId) => ((telasReg.telas || []).find(t => t.id === telaId) || {}).nombre || '';

  const fetchPlantillasPlanillas = async () => {
    try {
      const res = await fetch('/api/plantillas_planillas');
      const data = await res.json();
      setPlantillasPlanillas(data);
    } catch (e) {
      console.error("Error al obtener plantillas de planillas", e);
    }
  };

  const fetchReglasPlanilla = async () => {
    try {
      const res = await fetch('/api/reglas_planilla');
      if (!res.ok) { setReglasPlanilla([]); return; }
      setReglasPlanilla(await res.json());
    } catch (e) {
      console.error("Error al obtener reglas de planilla", e);
    }
  };

  const fetchNestingPresets = async () => {
    try {
      const res = await fetch('/api/nesting_presets');
      if (!res.ok) { setNestingPresets([]); return; }
      setNestingPresets(await res.json());
    } catch (e) {
      console.error("Error al obtener presets de nesting", e);
    }
  };

  const fetchPerfiles = async () => {
    try {
      const r = await fetch('/api/perfiles');
      if (r.ok) setPerfilesData(await r.json());
    } catch (e) { /* sin perfiles */ }
  };
  const guardarPerfilDefault = async (espacio, archivo) => {
    try {
      const r = await fetch('/api/perfiles/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ [espacio]: archivo }) });
      if (r.ok) { const d = await r.json(); setPerfilesData(prev => prev ? { ...prev, config: d.config } : prev); showMsg('Perfil predeterminado guardado ✓'); }
    } catch (e) { showError('No se pudo guardar el perfil'); }
  };
  // Avisar el perfil de color del diseño recién cargado → ventana emergente CENTRADA.
  // Aparece YA con "Detectando perfil…" y se actualiza al detectarse (no demora en salir).
  const avisarPerfilDiseno = async (diseno, moldId) => {
    setPerfilAviso({ estado: 'detectando' });
    try {
      const r = await fetch(`/api/arte/perfil?diseno=${encodeURIComponent(diseno || 'principal')}${qPid('&')}`);
      if (!r.ok) { setPerfilAviso(null); return; }
      const p = await r.json();
      setPerfilAviso(p);
      // Recordar el perfil EFECTIVO de este arte (incrustado o el que se le asigna),
      // para detectar al ir a la planilla si hay perfiles distintos entre diseños.
      if (moldId) {
        const efectivo = p.incrustado || p.predeterminado;
        setPerfilesArte(prev => ({ ...prev, [(diseno || 'principal') + '|' + moldId]: { nombre: efectivo, espacio: p.espacio } }));
      }
    } catch (e) { setPerfilAviso(null); }
  };

  // Ir del paso Arte a la Planilla. Si los diseños tienen perfiles de color DISTINTOS,
  // primero pregunta a cuál unificar la exportación (con aviso de variación de color).
  const irAPlanillaDesdeArte = async () => {
    if (!todasArteCargadas) return;
    if (bloqueaPorSinDiseno()) return;   // alguna pieza del molde activo sin diseño → no avanza, la marca en rojo
    // SINCRONIZAR el diseño de las filas con lo PREPARADO: una fila cuyo diseño NO esté entre los
    // que el usuario preparó en este pedido (`disenosPedido`) — ej. un valor viejo/vacío pegado en
    // la planilla — se corrige al diseño activo. Así la tizada usa lo que preparaste, no otro/vacío.
    const _disCol = cols.find(c => c.role === 'diseno');
    if (_disCol && disenosPedido.length) {
      const _validos = new Set(disenosPedido.map(d => d.nombre).filter(Boolean));
      const _nomActivo = (disenosPedido.find(d => d.id === disenoActivo) || disenosPedido[0])?.nombre;
      if (_nomActivo) {
        setFilas(prev => prev.map(f => {
          // UN solo diseño preparado → TODAS las filas usan ese (sin importar el valor viejo).
          // Varios → se respeta el de la fila si es uno de los preparados; si no, al activo.
          const _usar = (disenosPedido.length === 1) ? _nomActivo
            : (_validos.has(f[_disCol.id]) ? f[_disCol.id] : _nomActivo);
          return f[_disCol.id] === _usar ? f : { ...f, [_disCol.id]: _usar };
        }));
      }
    }
    const claves = tareasArte.map(t => t.did + '|' + t.mid);
    const nombres = [...new Set(claves.map(k => perfilesArte[k]?.nombre).filter(Boolean))];
    if (nombres.length > 1) {
      if (!perfilesData) await fetchPerfiles();
      setPerfilUnificar({ nombres, espacio: perfilesArte[claves[0]]?.espacio || 'CMYK' });
    } else {
      setPerfilForzado(null);   // un solo perfil → se usa tal cual, sin transformar
      setPedidoPaso('planilla');
    }
  };
  const elegirPerfilUnificado = (nombre) => {
    const prof = (perfilesData?.perfiles || []).find(p => p.nombre === nombre);
    setPerfilForzado(prof?.archivo || null);
    setPerfilUnificar(null);
    setPedidoPaso('planilla');
  };

  const fetchGruposTizada = async () => {
    try {
      const res = await fetch('/api/grupos_tizada');
      if (!res.ok) { setGruposTizada([]); return; }
      setGruposTizada(await res.json());
    } catch (e) { console.error("Error al obtener grupos de tizada", e); }
  };

  const guardarGrupoTizadaCfg = async (grupo) => {
    try {
      const res = await fetch('/api/grupos_tizada/guardar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(grupo),
      });
      const data = await leerJson(res);
      if (!res.ok) { showError(data.error || 'No se pudo guardar el grupo'); return null; }
      await fetchGruposTizada();
      showMsg('Grupo de tizada guardado ✓');
      return data.id;
    } catch (e) { showError('Error al guardar: ' + e.message); return null; }
  };

  const eliminarGrupoTizadaCfg = async (id) => {
    if (!confirm('¿Eliminar este grupo de tizada?')) return;
    try {
      const res = await fetch('/api/grupos_tizada/eliminar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }),
      });
      const data = await leerJson(res);
      if (!res.ok) { showError(data.error || 'No se pudo eliminar'); return; }
      await fetchGruposTizada();
    } catch (e) { showError('Error al eliminar: ' + e.message); }
  };

  // Catálogo filtrado por el buscador: matchea el nombre interno O el archivo, sin distinguir
  // mayúsculas ni acentos (buscar "espanol" tiene que encontrar "Español").
  // marcas combinantes de NFD. Se arma desde string con escapes \u para no depender de que los
  // caracteres literales sobrevivan la codificación del archivo.
  const _ACENTOS = new RegExp('[\\u0300-\\u036f]', 'g');
  const _sinTildes = (s) => (s || '').normalize('NFD').replace(_ACENTOS, '').toLowerCase();
  const _fuentesFiltradas = useMemo(() => {
    const q = _sinTildes(buscarFuente).trim();
    const todas = estado?.fuentes || [];
    if (!q) return todas;
    return todas.filter(f => _sinTildes(f.interno).includes(q) || _sinTildes(f.archivo).includes(q));
  }, [estado?.fuentes, buscarFuente]);

  // Saca una tipografía del catálogo (ya confirmada EN la tarjeta, no hay diálogo del navegador).
  const eliminarFuente = async (archivo) => {
    try {
      const res = await fetch('/api/fuente/archivo/' + encodeURIComponent(archivo), { method: 'DELETE' });
      const data = await leerJson(res);
      if (!res.ok) { showError(data.error || 'No se pudo eliminar la fuente'); return; }
      setFuenteABorrar(null);
      await fetchEstado();
      showMsg('Fuente eliminada del catálogo.');
    } catch (e) { showError('Error al eliminar: ' + e.message); }
  };

  const guardarNestingPreset = async (preset) => {
    try {
      const res = await fetch('/api/nesting_presets/guardar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(preset),
      });
      const data = await leerJson(res);
      if (!res.ok) { showError(data.error || 'No se pudo guardar el nesting'); return null; }
      await fetchNestingPresets();
      showMsg('Nesting guardado ✓');
      return data.id;
    } catch (e) { showError('Error al guardar: ' + e.message); return null; }
  };

  const eliminarNestingPreset = async (id) => {
    if (!confirm('¿Eliminar este nesting? Los moldes que lo usaban vuelven al estándar.')) return;
    try {
      const res = await fetch('/api/nesting_presets/eliminar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }),
      });
      const data = await leerJson(res);
      if (!res.ok) { showError(data.error || 'No se pudo eliminar'); return; }
      await fetchNestingPresets();
      await fetchProductos();
    } catch (e) { showError('Error al eliminar: ' + e.message); }
  };

  const asignarNestingAMolde = async (productoId, nesting_preset_id) => {
    try {
      const res = await fetch('/api/productos/nesting_preset', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ producto_id: productoId, nesting_preset_id }),
      });
      if (!res.ok) { const d = await leerJson(res); showError(d.error || 'No se pudo asignar'); return; }
      await fetchProductos();
      showMsg('Nesting del molde actualizado ✓');
    } catch (e) { showError('Error: ' + e.message); }
  };

  const guardarGrupoTizada = async (productoId, grupo) => {
    try {
      const res = await fetch('/api/productos/grupo_tizada', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ producto_id: productoId, grupo_tizada: grupo }),
      });
      if (!res.ok) { const d = await leerJson(res); showError(d.error || 'No se pudo guardar'); return; }
      await fetchProductos();
      showMsg('Grupo de tizada actualizado ✓');
    } catch (e) { showError('Error: ' + e.message); }
  };

  const fetchCatalogoPiezas = async () => {
    try {
      const res = await fetch('/api/catalogo_piezas');
      if (!res.ok) { setCatalogoGrupos([]); return; }  // server viejo → modal igual muestra piezas del molde
      const data = await leerJson(res);
      if (Array.isArray(data)) setCatalogoGrupos(data);
    } catch (e) {
      setCatalogoGrupos([]);  // sin catálogo: la unión con las piezas del molde sigue funcionando
    }
  };

  // Al cambiar de producto activo, el catálogo del backend suma las piezas
  // registradas en ese molde → lo recargamos para verlas en el selector.
  useEffect(() => {
    if (productosCat.activo) fetchCatalogoPiezas();
  }, [productosCat.activo]);

  const agregarPiezaCatalogo = async (asignarAlSeleccionado = false) => {
    const nombre = nuevaPiezaInput.trim();
    const grupo = (panelPiezas && panelPiezas !== 'grupos') ? panelPiezas : 'Prenda Superior';
    if (!nombre) return;
    try {
      const res = await fetch('/api/catalogo_piezas/agregar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, grupo })
      });
      const data = await leerJson(res);
      if (!res.ok) throw new Error(data.error);
      setCatalogoGrupos(data.catalogo_grupos || []);
      setNuevaPiezaInput('');
      if (asignarAlSeleccionado && etqSeleccion !== null) {
        setEtqNombres({ ...etqNombres, [etqSeleccion]: nombre });
      }
      showMsg('Pieza guardada en el grupo ✓');
    } catch (err) {
      showError(err.message);
    }
  };

  const eliminarPiezaCatalogo = async (nombre, grupo) => {
    try {
      const res = await fetch('/api/catalogo_piezas/eliminar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre, grupo })
      });
      const data = await leerJson(res);
      if (!res.ok) throw new Error(data.error);
      setCatalogoGrupos(data.catalogo_grupos || []);
    } catch (err) {
      showError(err.message);
    }
  };

  const agregarGrupoCatalogo = async () => {
    const nombre = nuevoGrupoInput.trim();
    if (!nombre) return;
    try {
      const res = await fetch('/api/catalogo_grupos/agregar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre })
      });
      const data = await leerJson(res);
      if (!res.ok) throw new Error(data.error);
      setCatalogoGrupos(data.catalogo_grupos || []);
      setNuevoGrupoInput('');
      setPanelPiezas(nombre); // entrar al grupo recién creado
      showMsg('Grupo creado ✓');
    } catch (err) {
      showError(err.message);
    }
  };

  const handleCreatePlanilla = () => {
    setPlanillaEditando({
      id: '',
      nombre: 'Nueva Planilla',
      columnas: [
        { id: 'talle', label: 'Talle', role: 'talle' },
        { id: 'nombre', label: 'Nombre', role: 'nombre' },
        { id: 'numero', label: 'Número', role: 'numero' },
        { id: 'manga', label: 'Manga', role: 'manga' }
      ]
    });
    setNombrePlanillaEditando('Nueva Planilla');
    setColumnasPlanillaEditando([
      { id: 'talle', label: 'Talle', role: 'talle' },
      { id: 'nombre', label: 'Nombre', role: 'nombre' },
      { id: 'numero', label: 'Número', role: 'numero' },
      { id: 'manga', label: 'Manga', role: 'manga' }
    ]);
  };

  const handleEditPlanilla = (plan) => {
    setPlanillaEditando(plan);
    setNombrePlanillaEditando(plan.nombre);
    setColumnasPlanillaEditando(plan.columnas || []);
  };

  const handleDeletePlanilla = async (id) => {
    if (id === 'plan_default') {
      showError("No se puede eliminar la planilla por defecto");
      return;
    }
    if (!confirm("¿Seguro que deseas eliminar esta plantilla de planilla? Los productos que la usan volverán a la planilla por defecto.")) return;
    try {
      const res = await fetch('/api/plantillas_planillas/eliminar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      showMsg("Planilla eliminada ✓");
      await fetchPlantillasPlanillas();
      await fetchProductos();
      await fetchEstado();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleAssignPlanillaToProduct = async (productoId, templateId) => {
    try {
      const res = await fetch('/api/productos/asignar_planilla', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ producto_id: productoId, planilla_template_id: templateId })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      showMsg("Planilla asociada al producto ✓");
      await fetchProductos();
      await fetchEstado();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleSavePlanilla = async () => {
    if (!nombrePlanillaEditando.trim()) {
      showError("El nombre de la planilla no puede estar vacío");
      return;
    }
    if (!columnasPlanillaEditando.some(c => c.role === 'talle')) {
      showError("Debe haber al menos una columna con el rol 'Talle'");
      return;
    }
    try {
      const res = await fetch('/api/plantillas_planillas/guardar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: planillaEditando.id,
          nombre: nombrePlanillaEditando.trim(),
          columnas: columnasPlanillaEditando
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      showMsg("Planilla guardada ✓");
      setPlanillaEditando(null);
      await fetchPlantillasPlanillas();
      await fetchProductos();
      await fetchEstado();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleAddEditorColumn = () => {
    const nextIdx = columnasPlanillaEditando.length;
    setColumnasPlanillaEditando([
      ...columnasPlanillaEditando,
      { id: `col_${nextIdx}`, label: `Columna ${nextIdx + 1}`, role: 'none' }
    ]);
  };

  const handleRemoveEditorColumn = (idx) => {
    setColumnasPlanillaEditando(columnasPlanillaEditando.filter((_, i) => i !== idx));
  };

  // Reordenar columnas arrastrando su cabecera (A/B/C…) en el editor de la config.
  const moverColumnaEditor = (from, to) => {
    if (from == null || to == null || from === to) return;
    setColumnasPlanillaEditando(prev => {
      const next = [...prev];
      const [m] = next.splice(from, 1);
      next.splice(to, 0, m);
      return next;
    });
    setColSeleccionada(to);
  };

  const handleUpdateEditorColumn = (idx, field, val) => {
    const next = [...columnasPlanillaEditando];
    next[idx] = { ...next[idx], [field]: val };
    if (field === 'label') {
      const norm = val.toLowerCase().replace(/[^a-z0-9]/g, '_').trim();
      next[idx]['id'] = norm || `col_${idx}`;
    }
    setColumnasPlanillaEditando(next);
  };

  // Aplica una regla (preset) a una columna: copia comportamiento/tipo/opciones y recuerda el id
  const aplicarReglaAColumna = (idx, reglaId) => {
    const regla = reglasPlanilla.find(r => r.id === reglaId);
    const next = [...columnasPlanillaEditando];
    if (!regla) { next[idx] = { ...next[idx], reglaId: '' }; setColumnasPlanillaEditando(next); return; }
    next[idx] = {
      ...next[idx],
      reglaId,
      role: regla.comportamiento || 'none',
      tipo: regla.tipo || 'texto',
      opciones: regla.opciones || '',
      label: (next[idx].label && next[idx].label.trim()) ? next[idx].label : regla.nombre,
    };
    setColumnasPlanillaEditando(next);
  };

  const guardarRegla = async (regla) => {
    try {
      const res = await fetch('/api/reglas_planilla/guardar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(regla),
      });
      const data = await leerJson(res);
      if (!res.ok) { alert(data.error || 'No se pudo guardar la regla'); return; }
      await fetchReglasPlanilla();
      setReglaEditando(null);
    } catch (e) { alert('Error al guardar la regla: ' + e.message); }
  };

  const eliminarRegla = async (id) => {
    if (!confirm('¿Eliminar esta regla?')) return;
    try {
      const res = await fetch('/api/reglas_planilla/eliminar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }),
      });
      const data = await leerJson(res);
      if (!res.ok) { alert(data.error || 'No se pudo eliminar'); return; }
      await fetchReglasPlanilla();
    } catch (e) { alert('Error al eliminar: ' + e.message); }
  };

  useEffect(() => {
    fetchPlantillasPlanillas();
    fetchReglasPlanilla();
    fetchNestingPresets();
    fetchGruposTizada();
    if (activoTab === 'config') {
      fetchConfig();
    }
  }, [activoTab]);

  // Polling for tizada job
  useEffect(() => {
    let interval;
    if (trabajoId) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`/api/trabajo/${trabajoId}`);
          const data = await res.json();
          setTrabajoEstado(data);
          if (data.estado === 'listo' || data.estado === 'error') {
            setTrabajoId(null);
            fetchEstado();
            fetchProductos();
          }
        } catch (e) {
          console.error("Error al sondear trabajo", e);
        }
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [trabajoId]);

  const handleCrearProducto = async (e) => {
    e.preventDefault();
    if (!nuevoProductoNombre.trim()) return;
    try {
      const res = await fetch('/api/productos/crear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nombre: nuevoProductoNombre.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      setNuevoProductoNombre('');
      setCreandoProducto(false);
      await fetchProductos();
      await fetchEstado();
      showMsg("Molde creado y activado ✓");
    } catch (err) {
      showError(err.message);
    }
  };

  const handleActivarProducto = async (id) => {
    // Al cambiar a OTRO molde, limpiar la detección/mapeo del anterior para que
    // no se vea por un instante el molde previo mientras carga el nuevo.
    // (Solo si cambia: si es el mismo, el efecto no recargaría y quedaría en blanco.)
    if (id !== productosCat.activo) {
      setEtqData(null);
      setMapeoData(null);
      setEtqNombres({});
    }
    try {
      const res = await fetch('/api/productos/activar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      await fetchProductos();
      await fetchEstado();
      showMsg("Molde activado ✓");
      if (activoTab === 'config') fetchConfig();
    } catch (err) {
      showError(err.message);
    }
  };

  const handleEliminarProducto = async (id, e) => {
    e.stopPropagation();
    if (id === 'prod_default') {
      showError("No se puede eliminar el molde por defecto");
      return;
    }
    if (!confirm("¿Seguro que deseas eliminar este molde y todos sus archivos?")) return;
    try {
      const res = await fetch('/api/productos/eliminar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      await fetchProductos();
      await fetchEstado();
      showMsg("Molde eliminado ✓");
    } catch (err) {
      showError(err.message);
    }
  };

  const handleRenombrarProducto = async (id, nombreActual) => {
    const nuevoNombre = prompt("Nuevo nombre del molde:", nombreActual);
    if (!nuevoNombre || !nuevoNombre.trim()) return;
    try {
      const res = await fetch('/api/productos/renombrar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, nombre: nuevoNombre.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      await fetchProductos();
      showMsg("Molde renombrado ✓");
    } catch (err) {
      showError(err.message);
    }
  };

  const handleUploadFile = async (type, file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append('archivo', file);
    // el archivo entra al molde que se está configurando, no al "activo" del server
    if (pidCfg) formData.append('pid', pidCfg);
    
    let url = '';
    if (type === 'plantilla') url = '/api/plantilla';
    else if (type === 'arte') url = '/api/arte';
    else if (type === 'fuente') url = '/api/fuente';

    const grande = file.size > 3 * 1024 * 1024 || /\.dxf$/i.test(file.name || '');
    setProcesando(type === 'plantilla'
      ? (grande ? 'Procesando el molde… los archivos grandes o DXF pueden tardar unos segundos.' : 'Procesando el molde…')
      : 'Subiendo y procesando el archivo…');
    try {
      const res = await fetch(url, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Error al procesar archivo");
      
      if (type === 'arte' && data.modo === 'separado' && (!data.auto || !data.aprobado)) {
        showMsg("Arte subido. Asigna las piezas.");
        abrirMapeo(data);
      } else {
        showMsg("Archivo procesado con éxito ✓");
        // Aviso no bloqueante: campos de planilla sin su capa en el diseño.
        if (type === 'arte' && data.campos_personalizacion) avisarCapasFaltantes(data.campos_personalizacion);
      }
      if (type === 'arte') avisarPerfilDiseno('principal');   // cartel del perfil YA
      fetchEstado();
      await fetchProductos();        // esperar a que el molde figure con plantilla
      setMoldeReload(v => v + 1);    // y recargar la detección visual al instante
    } catch (err) {
      showError(err.message);
    } finally {
      setProcesando(null);
    }
  };

  // ── MI PROPIO MOLDE (desde el pedido) ──────────────────────────────────────
  // Abre la config de un molde propio REUSANDO las pantallas de Configuración → Moldería
  // (deep-link), pero en modo recortado: ver `modoMiMolde`.
  const abrirConfigMiMolde = async (pid) => {
    if (!pid) return;
    setModoMiMolde(pid);
    setActivoTab('config');
    setAdminSubView('productos');
    await handleActivarProducto(pid);   // la config lee el molde ACTIVO → activarlo primero
    setMolderiaAbierta(pid);
    setTabAjustesMolde('molderia');
  };

  // Crear el molde propio + subirle el archivo. Se hace con `pid` explícito para NO depender
  // del molde activo (dos usuarios subiendo a la vez se pisaban los archivos).
  const subirMiMolde = async () => {
    const nombre = subirMoldeNombre.trim();
    if (!nombre || !subirMoldeFile) return;
    setSubirMoldeBusy(true);
    const grande = subirMoldeFile.size > 3 * 1024 * 1024 || /\.dxf$/i.test(subirMoldeFile.name || '');
    setProcesando(grande ? 'Procesando tu molde… los archivos grandes o DXF pueden tardar unos segundos.' : 'Procesando tu molde…');
    let pid = null;
    try {
      // Si ya tenés un artículo con ese nombre, se RE-SUBE el molde ahí en vez de crear otro:
      // cada reintento creaba un artículo nuevo y quedaban tres "Molde short" iguales.
      const yaExiste = (productosCat.productos || []).find(
        p => p.propio && (p.nombre || '').trim().toLowerCase() === nombre.toLowerCase());
      const r = yaExiste
        ? { ok: true, json: async () => ({ id: yaExiste.id }) }
        : await fetch('/api/productos/crear', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nombre, propio: true })
          });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || 'No se pudo crear el artículo');
      pid = d.id;
      const fd = new FormData();
      fd.append('archivo', subirMoldeFile);
      fd.append('pid', pid);
      const r2 = await fetch('/api/plantilla', { method: 'POST', body: fd });
      const d2 = await r2.json();
      if (!r2.ok) throw new Error(d2.error || 'No se pudo procesar el molde');
      showMsg('Molde subido ✓ — ahora indicá qué es cada pieza');
    } catch (err) {
      showError(err.message);
    } finally {
      setSubirMoldeBusy(false);
      setProcesando(null);
      await fetchProductos();
      setMoldeReload(v => v + 1);
      setSubirMoldeOpen(false); setSubirMoldeNombre(''); setSubirMoldeFile(null);
      // Aunque el archivo haya fallado, el artículo ya existe: se entra igual a su config
      // para poder re-subirlo desde ahí (si no, quedaría un molde huérfano inalcanzable).
      if (pid) await abrirConfigMiMolde(pid);
    }
  };

  const abrirEtiquetador = async (talleRef = null) => {
    // Evitar que el objeto del evento de React se tome como talle
    const ref = (talleRef && typeof talleRef === 'string') ? talleRef : null;
    showMsg("Cargando moldería...");
    try {
      const url = ref 
        ? `/api/plantilla/deteccion?talle_ref=${encodeURIComponent(ref)}${qPid('&')}`
        : `/api/plantilla/deteccion${qPid()}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      setEtqData(data);
      setEtqSeleccion(data.piezas?.length ? 0 : null);
      setEtqNombres(data.nombres_existentes || {});
      setModalEtqOpen(true);
      showMsg("");
    } catch (err) {
      showError(err.message);
    }
  };

  // Resetear offsets cuando cambian las piezas o talle de guía
  useEffect(() => {
    setPzOffsets({});
  }, [etqData]);

  // EMPAREJAR TALLES: el visor tiene que arrancar con el acomodo a mano YA guardado de ese
  // talle. Va DESPUÉS del reset de arriba a propósito (los efectos corren en orden de
  // declaración): si no, cada recarga de la detección borraría el reacomodo del usuario.
  useEffect(() => {
    if (!empModo || !empTalle) return;
    const g = (empData?.acomodo || {})[empTalle] || {};
    const o = {};
    Object.entries(g).forEach(([k, v]) => { o[k] = { x: Number(v[0]) || 0, y: Number(v[1]) || 0 }; });
    setPzOffsets(o);
  }, [etqData, empModo, empTalle, empData]);

  const startDrag = (e, idx) => {
    if (e.button !== 0) return; // solo click izquierdo
    // Asignando variantes POR PIEZAS: tocar una pieza la selecciona/deselecciona (mismo gesto
    // que el nombrado de piezas, para que se aprenda una sola vez).
    if (varPzModo) { toggleSelNombrar(idx); e.preventDefault(); return; }
    // EMPAREJAR TALLES: si hay una pieza esperando corrección, tocar en el visor la fija;
    // si no, se arrastra para reacomodar (y el clic sin movimiento selecciona/deselecciona).
    if (empModo) {
      // En la vista junta el índice del visor es global: la corrección se resuelve por (talle, t_idx).
      if (empFijar) { const nom = empFijar; setEmpFijar(null); (empTodas ? fijarPiezaTodas : fijarPiezaEmp)(nom, idx); e.preventDefault(); return; }
      // AGRUPAR (camino principal): el gesto es SOLO seleccionar. Arrastrar piezas es del
      // ajuste avanzado — acá confundiría (el usuario cree que mueve el molde).
      if (empVista === 'simple') { toggleSelNombrar(idx); e.preventDefault(); return; }
      // arrastrar una pieza YA seleccionada mueve todas las seleccionadas juntas
      const grupo = selNombrar.has(idx) ? Array.from(selNombrar) : [idx];
      const inis = {};
      grupo.forEach(i => { inis[i] = pzOffsets[i] || { x: 0, y: 0 }; });
      dragInfo.current = { idx, startX: e.clientX, startY: e.clientY, initialX: 0, initialY: 0,
                           hasMoved: false, emp: true, inis };
      e.preventDefault();
      return;
    }
    // Pestaña Variables, paso Nombrar: tocar una pieza la selecciona/deselecciona.
    if (tabAjustesMolde === 'variables' && varStep === 'nombrar') {
      // Editando un nombre existente: tocar suma/quita la pieza de ese nombre.
      if (editandoNombre) { toggleNombreEnPieza(editandoNombre, idx); e.preventDefault(); return; }
      toggleSelNombrar(idx);
      e.preventDefault();
      return;
    }
    // Pestaña Variables, armando un vínculo "van juntas": tocar suma/saca del vínculo en curso.
    if (tabAjustesMolde === 'variables' && vinculandoJuntas) {
      setJuntasSel(prev => { const n = new Set(prev); if (n.has(idx)) n.delete(idx); else n.add(idx); return n; });
      e.preventDefault();
      return;
    }
    // Pestaña Variables con un tipo activo: tocar una pieza la asigna/saca de ese tipo.
    if (tabAjustesMolde === 'variables' && asignandoTipo) {
      togglePiezaEnTipo(asignandoTipo, idx);
      e.preventDefault();
      return;
    }
    // Eligiendo piezas para un CONJUNTO "van juntas": tocar la suma/saca.
    if (tabAjustesMolde === 'variables' && asignandoConjunto) {
      togglePiezaEnConjunto(asignandoConjunto, idx);
      e.preventDefault();
      return;
    }
    // Eligiendo piezas para un GRUPO: tocar la suma/saca.
    if (tabAjustesMolde === 'variables' && asignandoGrupoPz) {
      togglePiezaEnGrupoPz(asignandoGrupoPz, idx);
      e.preventDefault();
      return;
    }
    setEtqSeleccion(idx);

    // Si no está activo el modo de acomodar, no permitir arrastre (solo seleccionar)
    if (!modoAcomodar) return;
    
    const currentOffset = pzOffsets[idx] || { x: 0, y: 0 };
    dragInfo.current = {
      idx,
      startX: e.clientX,
      startY: e.clientY,
      initialX: currentOffset.x,
      initialY: currentOffset.y,
      hasMoved: false
    };
    e.preventDefault();
  };

  const handleDrag = (e) => {
    const { idx, startX, startY, initialX, initialY } = dragInfo.current;
    if (idx === null || (!modoAcomodar && !dragInfo.current.emp)) return;

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      dragInfo.current.hasMoved = true;
    }

    const svgEl = e.currentTarget;
    const rect = svgEl.getBoundingClientRect();
    // px de pantalla → unidades del viewBox. Se usa el ANCHO DEL VIEWBOX, no `img_w`: las
    // piezas pueden exceder la página (por eso el viewBox se agranda) y con img_w la pieza
    // se corría más/menos que el mouse.
    const scale = (canvasLayout.vbW || canvasLayout.width) / (rect.width || 1);

    const inis = dragInfo.current.inis;
    if (inis) {   // arrastre en grupo (emparejar talles): todas las seleccionadas juntas
      setPzOffsets((prev) => {
        const n = { ...prev };
        Object.entries(inis).forEach(([k, v]) => { n[k] = { x: v.x + dx * scale, y: v.y + dy * scale }; });
        return n;
      });
      return;
    }
    setPzOffsets((prev) => ({
      ...prev,
      [idx]: {
        x: initialX + dx * scale,
        y: initialY + dy * scale
      }
    }));
  };

  const endDrag = () => {
    const d = dragInfo.current;
    // En "emparejar talles" el mismo gesto sirve para las dos cosas: si no hubo movimiento
    // fue un clic → selecciona/deselecciona la pieza (mismo gesto que el resto del visor).
    if (d.idx !== null && d.emp && !d.hasMoved) toggleSelNombrar(d.idx);
    dragInfo.current.idx = null;
    dragInfo.current.inis = null;
    dragInfo.current.emp = false;
  };

  const asignarNombresEtq = () => {
    if (!etqNombreInput.trim()) return;
    const indices = Array.from(etqSeleccion);
    if (!indices.length) {
      showError("Selecciona al menos una pieza");
      return;
    }
    const nextNombres = { ...etqNombres };
    if (indices.length === 1) {
      nextNombres[indices[0]] = etqNombreInput.trim();
    } else {
      indices.forEach((idx, k) => {
        nextNombres[idx] = `${etqNombreInput.trim()} ${k + 1}`;
      });
    }
    setEtqNombres(nextNombres);
    setEtqSeleccion(new Set());
    setEtqNombreInput('');
  };

  const guardarEtiquetas = async () => {
    const asign = Object.entries(etqNombres).map(([idx, val]) => ({
      idx: parseInt(idx),
      nombre: val
    }));
    try {
      const res = await fetch('/api/plantilla/etiquetas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          // `pid` EXPLÍCITO: sin él el server escribe el registro del molde "activo" — con varios
          // artículos iguales dando vueltas, el nombrado terminaba en el molde equivocado y el
          // que el usuario estaba mirando quedaba sin nombrar.
          pid: pidCfg,
          asignaciones: asign,
          mesa: etqData.mesa,
          talle_ref: etqData.talle_ref
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      showMsg("Etiquetas guardadas con éxito ✓");
      fetchEstado();
      fetchProductos();
    } catch (err) {
      showError(err.message);
    }
  };

  const abrirMapeo = async (det) => {
    setMapeoData(det);
    const prev = det.mapeo || {};
    const inicial = { ...prev };
    
    // Orden de prioridad: 1) mapeo ya guardado del archivo · 2) MAPEO FIJO del
    // molde (configurado una vez, se reusa) · 3) estimación de arranque.
    if (Object.keys(prev).length === 0) {
      if (det.mapeo_fijo && Object.keys(det.mapeo_fijo).length) {
        Object.assign(inicial, det.mapeo_fijo);
      } else {
        det.mesas?.forEach(m => { if (m.sugerencia) inicial[m.sugerencia] = m.mesa; });
      }
    }
    
    setMapeoValores(inicial);
    setSelectedPiezaMapeo(det.piezas_variable?.[0] || det.piezas?.[0] || '');   // 1ª de la VARIABLE, no del molde
    setTabAjustesMolde('diseno');
    
    // Cargar moldería vectorial para la previsualización interactiva
    try {
      const res = await fetch(`/api/plantilla/deteccion${qPid()}`);
      if (res.ok) {
        const data = await res.json();
        setEtqData(data);
        if (data.nombres_existentes) {
          setEtqNombres(data.nombres_existentes);
        }
      }
    } catch (err) {
      console.warn("No se pudo cargar la moldería visual, usando listado como fallback:", err);
    }
  };

  const persistirMapeo = async (valores, { silencioso = false } = {}) => {
    const mapeo = {};
    Object.entries(valores || {}).forEach(([pieza, mesa]) => {
      if (mesa) mapeo[pieza] = parseInt(mesa);
    });
    try {
      const res = await fetch('/api/arte/mapeo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // REGLA mapeo-por-variable: el mapeo se guarda PARA la variable activa (v_xxx);
        // sin variable (molde sin variables) va a la base compartida.
        body: JSON.stringify({ pid: pidCfg, mapeo, diseno: disenoActivo, variante: verVariante || '' })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      // Mantener FRESCO el caché de deteccion de esta variable (para que revisitarla no pise
      // lo recién guardado con un mapeo viejo).
      const _dk = `${productosCat.activo}|${disenoActivo}|${verVariante || ''}`;
      if (_detArteCache.current[_dk]) _detArteCache.current[_dk] = { ..._detArteCache.current[_dk], mapeo };
      showMsg(silencioso ? "Mapeo guardado ✓" : "Mapeo de arte guardado ✓");
      if (!silencioso && data.campos_personalizacion) avisarCapasFaltantes(data.campos_personalizacion);
      fetchEstado();
    } catch (err) {
      showError(err.message);
    }
  };
  const guardarMapeo = () => persistirMapeo(mapeoValores);
  // Auto-guardado: al arrastrar/tocar un diseño sobre una pieza, el mapeo se guarda solo (ya no hay
  // botón "Guardar mapeo"). Actualiza el estado local y persiste el mapeo NUEVO (no el de estado, que
  // sería viejo) de forma silenciosa.
  const guardarMapeoAuto = (next) => { setMapeoValores(next); persistirMapeo(next, { silencioso: true }); };

  // Abre el mapeador VISUAL en el flujo del operario (mismo mapeador que el interno).
  const abrirMapeoOperario = async () => {
    showMsg("Cargando diseño y molde...");
    try {
      const res = await fetch(`/api/arte/deteccion?variante=${encodeURIComponent(verVariante || '')}${qPid('&')}`);
      if (!res.ok) { const e = await leerJson(res); showError(e.error || 'No se pudo cargar el diseño'); return; }
      const det = await res.json();
      setMapeoData(det);
      const prev = det.mapeo || {};
      const inicial = { ...prev };
      if (Object.keys(prev).length === 0) {
        if (det.mapeo_fijo && Object.keys(det.mapeo_fijo).length) Object.assign(inicial, det.mapeo_fijo);
        else det.mesas?.forEach(m => { if (m.sugerencia) inicial[m.sugerencia] = m.mesa; });
      }
      setMapeoValores(inicial);
      setSelectedPiezaMapeo(det.piezas_variable?.[0] || det.piezas?.[0] || '');   // 1ª de la VARIABLE, no del molde
      const r2 = await fetch(`/api/plantilla/deteccion${qPid()}`);
      if (r2.ok) { const data = await r2.json(); setEtqData(data); setEtqNombres(data.nombres_existentes || {}); }
      setMapeandoOperario(true);
      showMsg("");
    } catch (err) {
      showError(err.message);
    }
  };


  // Mapeo y Sincronización del Espacio de Trabajo
  useEffect(() => {
    if (activoProdDetalle) {
      setMapeoColumnas(activoProdDetalle.mapeo_columnas || {
        talle: 'talle',
        nombre: 'nombre',
        numero: 'numero',
        manga: 'manga',
        manga_corta_val: 'corta',
        manga_larga_val: 'larga'
      });
      setSelectedPlanillaTemplateId(activoProdDetalle.planilla_template_id || 'plan_default');
      setTerminologiaEdit({ variante: 'Talle', molde: 'Molde', ...(activoProdDetalle.terminologia || {}) });
      setNombreMoldeEdit(activoProdDetalle.nombre || '');
      // Buffers de Modelos/Variables (se resetean al valor persistido cuando cambia el molde)
      setVariantesEdit(Array.isArray(activoProdDetalle.variantes) ? activoProdDetalle.variantes : []);
      setModelosEdit(Array.isArray(activoProdDetalle.modelos) ? activoProdDetalle.modelos : []);
      setConjuntosEdit(Array.isArray(activoProdDetalle.conjuntos) ? activoProdDetalle.conjuntos : []);
      setGruposPz(Array.isArray(activoProdDetalle.grupos) ? activoProdDetalle.grupos : []);
      setModeloSel(0); setVarSel(null);
    }
  }, [activoProdDetalle]);

  // Al entrar a la pestaña "Telas asignadas" del molde: cargar el registro global + sembrar las asignadas.
  useEffect(() => {
    if (tabAjustesMolde === 'telas') {
      fetchTelas();
      setTelasAsigMolde(Array.isArray(activoProdDetalle?.telas_asignadas) ? activoProdDetalle.telas_asignadas : []);
    }
  }, [tabAjustesMolde, activoProdDetalle]);

  // Al salir de la pestaña Variables se corta el modo "asignar piezas" y la selección de nombrado.
  useEffect(() => { setResaltarNombre(null); setGrupoAislado(null); setModeloAbierto(null); setComboVisor(null); setModoAcomodar(false); setAsignandoConjunto(null); setGrupoPzAbierto(null); setAsignandoGrupoPz(null); setEditandoNombre(null); setVinculandoJuntas(null); setJuntasSel(new Set()); if (tabAjustesMolde !== 'variables') { setAsignandoTipo(null); setSelNombrar(new Set()); } }, [tabAjustesMolde]);

  // Cargar automáticamente la detección del molde y datos de diseño al cambiar de producto activo o subview
  useEffect(() => {
    if (adminSubView === 'productos' && activoProdDetalle) {
      // 1. Cargar plantilla detección para el lienzo (Moldería)
      const cargarDeteccionMolde = async () => {
        if (!activoProdDetalle.plantilla) {
          setEtqData(null);
          return;
        }
        try {
          // Respetar la variante de guía elegida: primero la guardada en la base
          // (compartida entre usuarios); si el server aún no la devuelve, el caché
          // del navegador. Así al recargar NO se pierde y no vuelve al talle 1.
          const guia = activoProdDetalle?.variante_guia
            || localStorage.getItem('tizada_talleguia_' + pidCfg) || '';
          let res = await fetch(`/api/plantilla/deteccion${guia ? `?talle_ref=${encodeURIComponent(guia)}${qPid('&')}` : qPid()}`);
          if (!res.ok && guia) {
            // La variante guardada ya no existe en esta plantilla → cargar la por defecto.
            res = await fetch(`/api/plantilla/deteccion${qPid()}`);
          } else if (res.ok && guia) {
            // La guía puede haber quedado apuntando al nombre VIEJO de la capa («Capa 1») después
            // de nombrar las variantes: el server ya no falla (responde 200 con el estado), así
            // que hay que validarla contra las variantes reales o se sigue mostrando la vieja.
            const _d = await res.clone().json().catch(() => null);
            const _t = _d?.talles || [];
            if (_t.length && !_t.includes(guia)) {
              localStorage.removeItem('tizada_talleguia_' + pidCfg);
              res = await fetch(`/api/plantilla/deteccion${qPid()}`);
            }
          }
          if (res.ok) {
            const data = await res.json();
            setEtqData(data);
            setEtqNombres(data.nombres_existentes || {});
            if (data.piezas?.length && etqSeleccion === null) {
              setEtqSeleccion(0);
            }
          } else {
            setEtqData(null);
          }
        } catch (e) {
          console.error("Error al pre-cargar detección de molde", e);
          setEtqData(null);
        }
      };

      // 2. Cargar datos de mapeo de arte si hay arte subido
      const cargarMapeoArte = async () => {
        if (!activoProdDetalle.arte) {
          setMapeoData(null);
          return;
        }
        try {
          const res = await fetch(`/api/arte/deteccion?variante=${encodeURIComponent(verVariante || '')}${qPid('&')}`);
          if (res.ok) {
            const data = await res.json();
            setMapeoData(data);
            setMapeoValores(data.mapeo || {});
            setSelectedPiezaMapeo(data.piezas?.[0] || '');
          } else {
            setMapeoData(null);
          }
        } catch (e) {
          console.error("Error al pre-cargar mapeo de arte", e);
          setMapeoData(null);
        }
      };

      cargarDeteccionMolde();
      cargarMapeoArte();
    }
  }, [adminSubView, pidCfg, moldeReload]);

  const cambiarTalleGuia = async (talleRef) => {
    showMsg("Actualizando talle de guía...");
    try {
      const url = `/api/plantilla/deteccion?talle_ref=${encodeURIComponent(talleRef)}${qPid('&')}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      setEtqData(data);
      setEtqNombres(data.nombres_existentes || {});
      if (pidCfg) {
        // 1) Caché del navegador: hace que al RECARGAR no se pierda (anda con
        //    cualquier versión del servidor).
        localStorage.setItem('tizada_talleguia_' + pidCfg, talleRef);
        // 2) Base de datos: compartido entre todos los usuarios (server al día).
        try {
          await fetch('/api/productos/variante_guia', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: pidCfg, variante: talleRef })
          });
          fetchProductos();
        } catch (e) { /* el cambio visual y el caché ya se aplicaron */ }
      }
      showMsg("");
    } catch (err) {
      showError(err.message);
    }
  };

  const guardarReferencia = async (ref) => {
    if (!activoProdDetalle) return;
    try {
      const r = await fetch('/api/productos/referencia_medida', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, referencia: ref })
      });
      const d = await leerJson(r);
      if (!r.ok) throw new Error(d.error);
      // Recalcular las medidas con la nueva referencia (vuelve a pedir la detección).
      const guia = activoProdDetalle?.variante_guia;
      const res = await fetch(`/api/plantilla/deteccion${guia ? `?talle_ref=${encodeURIComponent(guia)}${qPid('&')}` : qPid()}`);
      if (res.ok) {
        const data = await leerJson(res);
        setEtqData(data);
        setEtqNombres(data.nombres_existentes || {});
      }
      fetchProductos();
      showMsg(`Referencia: ${ref === 'ancho' ? 'el ancho manda' : 'el alto manda'} ✓`);
    } catch (err) {
      showError(err.message);
    }
  };

  const guardarConfigMapeoColumnas = async () => {
    try {
      const res = await fetch('/api/productos/config_mapeo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: activoProdDetalle.id,
          planilla_template_id: selectedPlanillaTemplateId,
          mapeo_columnas: mapeoColumnas
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      showMsg("Configuración de planilla guardada ✓");
      fetchProductos();
    } catch (err) {
      showError(err.message);
    }
  };

  const guardarTerminologia = async () => {
    const variante = (terminologiaEdit.variante || '').trim() || 'Talle';
    const nombreMolde = (nombreMoldeEdit || '').trim();
    if (!nombreMolde) { showError('El nombre del molde no puede estar vacío'); return; }
    try {
      // 1) Renombrar el molde (es su nombre real, el que se ve en la tarjeta).
      if (nombreMolde !== activoProdDetalle.nombre) {
        const r1 = await fetch('/api/productos/renombrar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: activoProdDetalle.id, nombre: nombreMolde })
        });
        const d1 = await leerJson(r1);
        if (!r1.ok) throw new Error(d1.error);
      }
      // 2) Guardar el nombre configurable de la variante.
      const r2 = await fetch('/api/productos/terminologia', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, terminologia: { variante, molde: terminologiaEdit.molde || 'Molde' } })
      });
      const d2 = await leerJson(r2);
      if (!r2.ok) throw new Error(d2.error);
      showMsg('Guardado ✓');
      await fetchProductos();
    } catch (err) {
      showError(err.message);
    }
  };

  // ── Modelos / Variables ──
  const uidVar = () => Math.random().toString(36).slice(2, 9);

  const guardarVariablesModelos = async () => {
    if (!activoProdDetalle) return;
    const noms = modelosEdit.map(m => (m.nombre || '').trim().toLowerCase()).filter(Boolean);
    if (new Set(noms).size !== noms.length) { showError('Hay nombres de modelo repetidos'); return; }
    setVarGuardando(true);
    try {
      const r1 = await fetch('/api/productos/variantes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, variantes: variantesEdit })
      });
      const d1 = await leerJson(r1); if (!r1.ok) throw new Error(d1.error || 'Error al guardar variantes');
      const r2 = await fetch('/api/productos/modelos', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, modelos: modelosEdit })
      });
      const d2 = await leerJson(r2); if (!r2.ok) throw new Error(d2.error || 'Error al guardar modelos');
      // No recargamos productos para no cortar la edición: el estado local ya es lo persistido.
      showMsg('Variables guardadas ✓');
    } catch (err) {
      showError(err.message || 'No se pudo guardar');
    } finally {
      setVarGuardando(false);
    }
  };

  // Guardar los grupos (variantes). `guardarGruposCon` acepta el array a persistir
  // (para cuando el estado todavía no se actualizó, p. ej. al crear un grupo nuevo).
  const guardarGruposCon = async (arr, silencioso) => {
    if (!activoProdDetalle) return;
    try {
      const r = await fetch('/api/productos/variantes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, variantes: arr })
      });
      const d = await leerJson(r); if (!r.ok) throw new Error(d.error || 'No se pudo guardar');
      if (!silencioso) showMsg('Variable guardada ✓');
    } catch (err) { showError(err.message || 'No se pudo guardar'); }
  };

  // Guardar los modelos (grupos de variables). Acepta el array a persistir (estado quizá no actualizado aún).
  const guardarModelosCon = async (arr) => {
    if (!activoProdDetalle) return;
    try {
      const r = await fetch('/api/productos/modelos', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, modelos: arr })
      });
      const d = await leerJson(r); if (!r.ok) throw new Error(d.error || 'No se pudo guardar');
      showMsg('Modelo guardado ✓');
    } catch (err) { showError(err.message || 'No se pudo guardar'); }
  };

  // ── Generación AUTOMÁTICA de variables (mismo nombre = alternativas; "van juntas" = una pieza multi-parte) ──
  const guardarConjuntosCon = async (arr) => {
    if (!activoProdDetalle) return;
    try {
      const r = await fetch('/api/productos/conjuntos', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, conjuntos: arr })
      });
      const d = await leerJson(r); if (!r.ok) throw new Error(d.error || 'No se pudo guardar');
    } catch (err) { showError(err.message || 'No se pudo guardar'); }
  };
  // Functional update + guardado con debounce: varios toggles seguidos no se pisan entre sí.
  const _conjSaveT = useRef(null);
  const aplicarConjuntos = (fn) => setConjuntosEdit(prev => { const nueva = fn(prev || []); clearTimeout(_conjSaveT.current); _conjSaveT.current = setTimeout(() => guardarConjuntosCon(nueva), 300); return nueva; });
  const togglePiezaEnConjunto = (id, idx) => aplicarConjuntos(arr => arr.map(c => c.id === id ? { ...c, piezas: (c.piezas || []).includes(idx) ? c.piezas.filter(x => x !== idx) : [...(c.piezas || []), idx] } : c));
  const agregarPiezasAConjunto = (id, idxs) => aplicarConjuntos(arr => arr.map(c => c.id === id ? { ...c, piezas: [...new Set([...(c.piezas || []), ...idxs])] } : c));
  const nombreDePieza = (idx) => (etqNombres[idx] || '').trim();
  // ── GRUPOS de piezas: la generación corre DENTRO de cada grupo (piezas repetibles entre grupos) ──
  const guardarGruposPzCon = async (arr) => {
    if (!activoProdDetalle) return;
    try {
      const r = await fetch('/api/productos/grupos', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: activoProdDetalle.id, grupos: arr })
      });
      const d = await leerJson(r); if (!r.ok) throw new Error(d.error || 'No se pudo guardar');
    } catch (err) { showError(err.message || 'No se pudo guardar'); }
  };
  const _gpzSaveT = useRef(null);
  const aplicarGruposPz = (fn) => setGruposPz(prev => { const nueva = fn(prev || []); clearTimeout(_gpzSaveT.current); _gpzSaveT.current = setTimeout(() => guardarGruposPzCon(nueva), 300); return nueva; });
  const togglePiezaEnGrupoPz = (id, idx) => aplicarGruposPz(arr => arr.map(g => g.id === id ? { ...g, piezas: (g.piezas || []).includes(idx) ? g.piezas.filter(x => x !== idx) : [...(g.piezas || []), idx] } : g));
  const agregarPiezasAGrupoPz = (id, idxs) => aplicarGruposPz(arr => arr.map(g => g.id === id ? { ...g, piezas: [...new Set([...(g.piezas || []), ...idxs])] } : g));
  const delVariablePorClave = (clave) => { const nueva = (variantesEdit || []).filter(v => v.clave !== clave); setVariantesEdit(nueva); guardarGruposCon(nueva, true); };
  // Arma las "unidades" (cosas que ocupan un lugar/slot) y las agrupa por nombre genérico.
  // `idxsBase` (opcional) = piezas permitidas (las del grupo); sin él, todas las nombradas.

  // ── Nido: todos los talles nesteados por pieza, para acomodar EN el visor ──
  // Se precarga apenas se entra a la pestaña Variables (y el server lo cachea en disco),
  // así al abrir una variable ya está listo.
  const cargarNido = async (force = false) => {
    if (nidoLoading) return;                 // ya en curso
    if (!force && nidoData) return;          // ya lo tenemos
    // OJO: NO cortar por `nidoError` — un fallo transitorio (cache fría del nido que
    // tarda minutos tras reiniciar el server) bloqueaba para siempre el reintento y el
    // visor caía al modo normal (numeritos) sin avisar. Ahora reintenta.
    setNidoError(null);
    setNidoLoading(true);
    try {
      const ctrl = new AbortController();
      const to = setTimeout(() => ctrl.abort(), 240000);   // 4 min: la 1ª vez (cache fría) puede tardar
      let r;
      try { r = await fetch(`/api/plantilla/nido${qPid()}`, { signal: ctrl.signal }); }
      finally { clearTimeout(to); }
      const d = await leerJson(r);
      if (!r.ok) throw new Error(d.error || 'No se pudo armar el nido');
      setNidoData(d);
    } catch (err) { setNidoError(err.name === 'AbortError' ? 'El nido tardó demasiado (probá de nuevo).' : (err.message || 'no disponible')); }
    finally { setNidoLoading(false); }
  };
  // Cargar el nido al entrar a Variables o al abrir una variable. Si hubo error NO reintenta
  // solo (evita loop) — el usuario reintenta con el botón del panel.
  // En Variables SIEMPRE; en Plantilla/Etiqueta SOLO si hay una variante elegida (para reproducir su acomodo).
  useEffect(() => { const necesita = tabAjustesMolde === 'variables' || (['diseno', 'etiqueta'].includes(tabAjustesMolde) && verVariante); if (necesita && etqData && !nidoData && !nidoLoading && !nidoError) cargarNido(); }, [tabAjustesMolde, etqData, grupoAislado, verVariante]);
  // Al abrir una variable en detalle, cargar su acomodo guardado y cerrar cualquier vínculo en curso.
  useEffect(() => {
    setVinculandoJuntas(null); setJuntasSel(new Set()); setJuntasNombre('');
    if (!grupoAislado) return;
    const v = (variantesEdit || []).find(g => g.clave === grupoAislado);
    setNidoOffsets((v && v.acomodo && typeof v.acomodo === 'object') ? v.acomodo : {});
  }, [grupoAislado]);
  // Backfill del ORDEN (cm) para variantes que tienen `acomodo` pero todavía no `orden`: al abrirlas
  // en Variables con el nido cargado, se calcula y guarda una vez → Etiqueta/Plantilla ya lo reproducen.
  useEffect(() => {
    if (tabAjustesMolde !== 'variables' || !grupoAislado || !nidoData) return;
    const g = (variantesEdit || []).find(t => t.clave === grupoAislado);
    if (!g || (g.orden && Object.keys(g.orden).length) || !g.acomodo || !Object.keys(g.acomodo).length) return;
    const orden = ordenCmDeNido(grupoAislado);
    if (orden && Object.keys(orden).length) {
      const nueva = (variantesEdit || []).map(x => x.clave === grupoAislado ? { ...x, orden } : x);
      setVariantesEdit(nueva); guardarGruposCon(nueva, true);
    }
  }, [grupoAislado, nidoData, tabAjustesMolde]);
  // Al soltar una pieza: guardar su posición (auto-guardado) + recalcular el ORDEN en cm (fuente
  // profesional que reproducen Etiqueta/Plantilla idéntico).
  const guardarAcomodoPieza = (nombre, off) => {
    const g0 = (variantesEdit || []).find(g => g.clave === grupoAislado);
    const acNuevo = { ...((g0 && g0.acomodo) || {}), [nombre]: off };
    const orden = ordenCmDeNido(grupoAislado, acNuevo);
    const nueva = (variantesEdit || []).map(g => g.clave === grupoAislado ? { ...g, acomodo: acNuevo, ...(orden ? { orden } : {}) } : g);
    setVariantesEdit(nueva);
    guardarGruposCon(nueva, true);
  };
  // Piezas del nido que pertenecen a la variable abierta. Matcheo por ÍNDICE exacto
  // (el nido trae el idx del talle guía); fallback por nombre para cachés viejas.
  const nidoVarPiezas = (clave = grupoAislado) => {
    if (!nidoData || !clave) return [];
    const g = (variantesEdit || []).find(t => t.clave === clave);
    if (!g) return [];
    const idxs = new Set((g.valores || []).map(v => v.pieza_idx).filter(x => x != null));
    const conIdx = (nidoData.piezas || []).some(p => p.idx != null);
    if (conIdx) return (nidoData.piezas || []).filter(p => p.idx != null && idxs.has(p.idx));
    const nombres = new Set((g.valores || []).map(v => (v.label || etqNombres[v.pieza_idx] || '').trim()).filter(Boolean));
    return (nidoData.piezas || []).filter(p => nombres.has(p.nombre));
  };
  // Re-acomoda las piezas de la variable en una GRILLA COMPACTA propia (las posiciones
  // del nido son de la grilla global de TODAS las piezas → quedan desparramadas/pegadas).
  // BBox real de un path SVG (parsea M/L/C) — para NO depender del hw/hh del backend.
  const _pathBBox = (d) => {
    if (!d) return null;
    const t = d.replace(/,/g, ' ').split(/\s+/).filter(Boolean);
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, i = 0;
    const acc = (x, y) => { if (isFinite(x) && isFinite(y)) { if (x < x0) x0 = x; if (y < y0) y0 = y; if (x > x1) x1 = x; if (y > y1) y1 = y; } };
    while (i < t.length) {
      const c = t[i];
      if (c === 'M' || c === 'L') { acc(+t[i + 1], +t[i + 2]); i += 3; }
      else if (c === 'C') { acc(+t[i + 1], +t[i + 2]); acc(+t[i + 3], +t[i + 4]); acc(+t[i + 5], +t[i + 6]); i += 7; }
      else i += 1;
    }
    return x1 >= x0 ? [x0, y0, x1, y1] : null;
  };
  const nidoLayoutVar = () => {
    const piezas = nidoVarPiezas();
    if (!piezas.length) return null;
    // Medir la pila REAL (todas las tallas) de cada pieza a partir de sus paths dibujados:
    // así el espaciado siempre calza con lo que se ve, sin importar qué trajo el backend.
    const med = piezas.map(p => {
      let X0 = Infinity, Y0 = Infinity, X1 = -Infinity, Y1 = -Infinity;
      (p.talles || []).forEach(t => { const b = _pathBBox(t.d); if (b) { if (b[0] < X0) X0 = b[0]; if (b[1] < Y0) Y0 = b[1]; if (b[2] > X1) X1 = b[2]; if (b[3] > Y1) Y1 = b[3]; } });
      const ok = X1 >= X0;
      return { p, cx: ok ? (X0 + X1) / 2 : (p.cx || 0), cy: ok ? (Y0 + Y1) / 2 : (p.cy || 0),
               hw: ok ? Math.max((X1 - X0) / 2, 1) : (p.hw || 40), hh: ok ? Math.max((Y1 - Y0) / 2, 1) : (p.hh || 40) };
    });
    const cols = Math.max(1, Math.round(Math.sqrt(med.length)));
    const GAP = Math.max(30, 0.35 * Math.max(...med.map(m => m.hw)));   // separación generosa y visible
    const filas = [];
    for (let i = 0; i < med.length; i += cols) filas.push(med.slice(i, i + cols));
    const items = []; let y = GAP;
    filas.forEach(fs => {
      const rowH = Math.max(...fs.map(m => m.hh));
      let x = GAP;
      fs.forEach(m => {
        items.push({ p: m.p, dx: (x + m.hw) - m.cx, dy: (y + rowH) - m.cy, mcx: m.cx, mcy: m.cy, mhw: m.hw, mhh: m.hh });
        x += 2 * m.hw + GAP;
      });
      y += 2 * rowH + GAP;
    });
    // ── VIEWBOX = caja que abarca TODAS las piezas CON su acomodo (offsets) + margen amplio.
    //    Así NO hay recorte: si arrastrás una pieza lejos, el lienzo la sigue conteniendo
    //    (no hay "límite invisible"). Durante el arrastre se CONGELA (nidoVbRef) para que el
    //    lienzo no se mueva bajo el cursor; al soltar, se recalcula para encuadrar todo. ──
    let X0 = Infinity, Y0 = Infinity, X1 = -Infinity, Y1 = -Infinity;
    items.forEach(it => {
      const off = nidoOffsets[it.p.nombre] || { x: 0, y: 0 };
      const cx = it.dx + off.x + it.mcx, cy = it.dy + off.y + it.mcy;
      if (cx - it.mhw < X0) X0 = cx - it.mhw; if (cx + it.mhw > X1) X1 = cx + it.mhw;
      if (cy - it.mhh < Y0) Y0 = cy - it.mhh; if (cy + it.mhh > Y1) Y1 = cy + it.mhh;
    });
    if (!(X1 >= X0)) { X0 = 0; Y0 = 0; X1 = 1000; Y1 = 1000; }
    const cw = X1 - X0, ch = Y1 - Y0;
    const mX = Math.max(cw * 0.6, 320), mY = Math.max(ch * 0.6, 320);   // margen generoso para arrastrar sin recorte
    const live = { x: Math.floor(X0 - mX), y: Math.floor(Y0 - mY), w: Math.ceil(cw + 2 * mX), h: Math.ceil(ch + 2 * mY) };
    const use = (nidoDragRef.current && nidoVbRef.current) ? nidoVbRef.current : live;  // congelar durante el arrastre
    if (!nidoDragRef.current) nidoVbRef.current = live;
    return { vb: `${use.x} ${use.y} ${use.w} ${use.h}`, vbW: use.w, items };
  };
  // ORDEN PROFESIONAL: el acomodo de la variante en CENTÍMETROS reales (unidad independiente de
  // la vista). Se calcula UNA vez desde el nido (grilla + `acomodo`) y se guarda en la variante;
  // cualquier herramienta lo reproduce IDÉNTICO convirtiendo cm→px, sin depender del nido.
  // Escala nido px→cm = mediana de (ancho de la pieza en el talle actual, en px del nido) / (su ancho real en cm).
  const ordenCmDeNido = (clave, acomodoOverride) => {
    if (!nidoData || !canvasLayout || !canvasLayout.layout) return null;
    const g = (variantesEdit || []).find(t => t.clave === clave);
    if (!g) return null;
    const acomodo = acomodoOverride || (g.acomodo && typeof g.acomodo === 'object' ? g.acomodo : {});
    const piezas = nidoVarPiezas(clave);
    if (!piezas.length) return null;
    const talleSel = etqData?.talle_ref;
    const cmDeNombre = {};
    canvasLayout.layout.forEach(p => { const nm = (etqNombres[p.idx] || p.name || '').trim(); if (nm && p.w_cm) cmDeNombre[nm] = p.w_cm; });
    const med = piezas.map(p => {
      let X0 = Infinity, Y0 = Infinity, X1 = -Infinity, Y1 = -Infinity;
      (p.talles || []).forEach(t => { const b = _pathBBox(t.d); if (b) { if (b[0] < X0) X0 = b[0]; if (b[1] < Y0) Y0 = b[1]; if (b[2] > X1) X1 = b[2]; if (b[3] > Y1) Y1 = b[3]; } });
      const tal = (p.talles || []).find(t => t.talle === talleSel) || (p.talles || [])[(p.talles || []).length - 1];
      const bM = tal ? _pathBBox(tal.d) : null;
      return { p, cx: (X0 + X1) / 2, cy: (Y0 + Y1) / 2, hw: Math.max((X1 - X0) / 2, 1), hh: Math.max((Y1 - Y0) / 2, 1), wM: bM ? (bM[2] - bM[0]) : (X1 - X0) };
    });
    const cols = Math.max(1, Math.round(Math.sqrt(med.length)));
    const GAP = Math.max(30, 0.35 * Math.max(...med.map(m => m.hw)));
    const centros = []; let y = GAP;
    for (let i = 0; i < med.length; i += cols) {
      const fs = med.slice(i, i + cols); const rowH = Math.max(...fs.map(m => m.hh)); let x = GAP;
      fs.forEach(m => {
        const off = acomodo[m.p.nombre] || { x: 0, y: 0 };
        centros.push({ name: m.p.nombre, x: x + m.hw + (off.x || 0), y: y + rowH + (off.y || 0), wM: m.wM, wcm: cmDeNombre[m.p.nombre] });
        x += 2 * m.hw + GAP;
      });
      y += 2 * rowH + GAP;
    }
    const ratios = centros.filter(c => c.wcm > 0 && c.wM > 0).map(c => c.wM / c.wcm).sort((a, b) => a - b);
    if (!ratios.length) return null;
    const pxPorCm = ratios[Math.floor(ratios.length / 2)];   // px del nido por cm real
    if (!(pxPorCm > 0)) return null;
    let minx = Infinity, miny = Infinity; centros.forEach(c => { if (c.x < minx) minx = c.x; if (c.y < miny) miny = c.y; });
    const orden = {};
    centros.forEach(c => { orden[c.name] = { cx: (c.x - minx) / pxPorCm, cy: (c.y - miny) / pxPorCm }; });
    return orden;
  };
  // Convierte un ORDEN (cm) a traslados de las piezas del molde (px) → { show, pos, vb }.
  const varianteDesdeOrden = (orden, pcs) => {
    if (!orden || !canvasLayout || !canvasLayout.cmPerUnit) return null;
    const pxPorCm = 1 / canvasLayout.cmPerUnit;
    const matched = [];
    pcs.forEach(pc => { const nm = (etqNombres[pc.idx] || pc.name || '').trim(); const o = nm && orden[nm]; if (o) matched.push({ pc, o }); });
    if (matched.length < Math.max(2, pcs.length * 0.6)) return null;
    const pos = new Map(); let X0 = Infinity, Y0 = Infinity, X1 = -Infinity, Y1 = -Infinity;
    matched.forEach(({ pc, o }) => {
      const tcx = o.cx * pxPorCm, tcy = o.cy * pxPorCm;
      pos.set(pc.idx, { dx: tcx - (pc.px + pc.pw / 2), dy: tcy - (pc.py + pc.ph / 2) });
      if (tcx - pc.pw / 2 < X0) X0 = tcx - pc.pw / 2; if (tcy - pc.ph / 2 < Y0) Y0 = tcy - pc.ph / 2;
      if (tcx + pc.pw / 2 > X1) X1 = tcx + pc.pw / 2; if (tcy + pc.ph / 2 > Y1) Y1 = tcy + pc.ph / 2;
    });
    const pad = (X1 - X0) * 0.06 + 25;
    return { show: new Set(matched.map(m => m.pc.idx)), pos, vb: `${(X0 - pad).toFixed(1)} ${(Y0 - pad).toFixed(1)} ${(X1 - X0 + 2 * pad).toFixed(1)} ${(Y1 - Y0 + 2 * pad).toFixed(1)}` };
  };
  // VER VARIANTE en Plantilla/Etiqueta: SOLO las piezas de la variante. Primero intenta reproducir
  // el ACOMODO del nido (así se ve igual que en Variables y en toda la app); si no hay nido/acomodo,
  // cae a una grilla compacta automática. Devuelve { show:Set(idx), pos:Map(idx→{dx,dy}), vb }.
  const varianteFiltro = (clave) => {
    const g = (variantesEdit || []).find(t => t.clave === clave);
    if (!g || !canvasLayout || !canvasLayout.layout) return null;
    // Piezas de la variante por CLAVE ESTABLE (pieza_id → clave, talle-independiente). Antes se
    // resolvía por etqNombres[pieza_idx], pero el pieza_idx VARÍA por talle → al cambiar de talle
    // la pieza no matcheaba y desaparecía del visor. El id no cambia nunca.
    const id2clave = {};
    (etqData?.piezas_id || []).forEach(p => { if (p.id && p.clave) id2clave[p.id] = p.clave; });
    const nombres = new Set((g.valores || [])
      .map(v => (id2clave[v.pieza_id] || etqNombres[v.pieza_idx] || v.label || '').trim())
      .filter(Boolean));
    // Si la variante tiene id estable, se matchea SOLO por nombre (el fallback por pieza_idx
    // incluiría piezas erróneas a talles no-guía, donde el idx apunta a otra pieza).
    const usaId = (g.valores || []).some(v => v.pieza_id && id2clave[v.pieza_id]);
    const idxsVar = new Set((g.valores || []).map(v => v.pieza_idx));
    const pcs = canvasLayout.layout.filter(p => {
      const nm = (etqNombres[p.idx] || p.name || '').trim();
      if (nm && nombres.has(nm)) return true;
      return !usaId && idxsVar.has(p.idx);
    });
    const show = new Set(pcs.map(p => p.idx));
    if (!pcs.length) return { show, pos: new Map(), vb: null };
    // 1) ORDEN profesional guardado (cm) → reproducción EXACTA sin depender del nido.
    // 2) si no está guardado pero el nido está cargado, lo calcula al vuelo (y el efecto lo backfillea).
    const orden = (g.orden && typeof g.orden === 'object' && Object.keys(g.orden).length) ? g.orden : ordenCmDeNido(clave);
    if (orden) { const r = varianteDesdeOrden(orden, pcs); if (r) return r; }
    // Fallback: grilla compacta automática.
    const n = pcs.length;
    const cols = Math.max(1, Math.round(Math.sqrt(n)));
    const avgW = pcs.reduce((s, p) => s + p.pw, 0) / n;
    const GAP = Math.max(8, 0.22 * avgW);
    const pos = new Map();
    let x = GAP, y = GAP, rowH = 0, col = 0, maxW = 0;
    pcs.forEach(p => {
      if (col >= cols) { col = 0; x = GAP; y += rowH + GAP; rowH = 0; }
      pos.set(p.idx, { dx: x - p.px, dy: y - p.py });   // llevar la pieza (px,py) a la celda (x,y)
      x += p.pw + GAP; if (p.ph > rowH) rowH = p.ph; if (x > maxW) maxW = x; col++;
    });
    return { show, pos, vb: `0 0 ${Math.ceil(maxW + GAP)} ${Math.ceil(y + rowH + GAP)}` };
  };
  // Claves de registro (nombres estables) de UNA variable — para acotar el panel de nombres y la
  // descarga de guía a SOLO sus piezas. Misma resolución id→clave que varianteFiltro.
  const nombresDeVariante = (clave) => {
    const g = (variantesEdit || []).find(t => t.clave === clave);
    if (!g) return [];
    const id2clave = {};
    (etqData?.piezas_id || []).forEach(p => { if (p.id && p.clave) id2clave[p.id] = p.clave; });
    return [...new Set((g.valores || []).map(v => (id2clave[v.pieza_id] || etqNombres[v.pieza_idx] || v.label || '').trim()).filter(Boolean))];
  };
  // Prefijo de MESA según el modo de la Plantilla (#talle / #rango / nada en default). Es lo que
  // el arte lee para auto-mapear — idéntico a `nombre_mesa` del motor (motor_pedido.pdf_guia_medidas).
  const mesaPrefijo = () => {
    if (configMedida === 'talle' && etqData?.talle_ref) return `#${etqData.talle_ref} `;
    if (configMedida === 'rango' && rangoMedida.length) return `#${rangoMedida[0]}-${rangoMedida[rangoMedida.length - 1]} `;
    return '';
  };
  // Selector "Ver variante" para Plantilla/Etiqueta: TARJETAS con las variables (las que tienen
  // piezas). "Todas" = vista completa. Al elegir una, el visor se REDUCE a sus piezas (con su
  // etiqueta/diseño real) y se re-encuadra a ellas → se trabaja de a una variante.
  // Variables que tienen piezas asignadas (las "reales" para ver/etiquetar de a una).
  const varsConPiezas = (variantesEdit || []).filter(v => (v.valores || []).some(x => x.pieza_idx != null));
  // Grupo de la variable que se está viendo/editando (para acotar la config de etiqueta a
  // ESE grupo: la posición por nombre se aplica a las piezas del mismo nombre PERO del mismo
  // grupo, no globalmente). Clave de posición = "grupo§nombre"; si no hay grupo, el nombre solo.
  const grupoActualEtq = (varsConPiezas.find(v => v.clave === verVariante) || {}).grupoId || null;
  const claveNombreEtq = (gen) => grupoActualEtq ? grupoActualEtq + '§' + gen : gen;
  // Etiqueta POR PIEZA POR VARIABLE: clave = <claveVariante>§<nombre COMPLETO> → cada pieza de cada
  // variable con su propia posición, aislada de las demás (aunque compartan nombre o grupo). Sin
  // variante elegida → nombre completo solo (fallback). El nombre completo (ej. "Frente 8") es
  // estable entre talles (es la clave del registro).
  const claveEtqPieza = (nombreCompleto) => verVariante ? verVariante + '§' + nombreCompleto : nombreCompleto;
  const renderSelVerVariante = (soloVariables = false) => {
    const vars = varsConPiezas;
    const card = (activo, titulo, sub, onClick, key) => (
      <button key={key} type="button" onClick={onClick} style={{
        textAlign: 'left', padding: '9px 11px', borderRadius: 10, cursor: 'pointer', minWidth: 0,
        border: '1.5px solid ' + (activo ? 'var(--accent)' : 'var(--border-light)'),
        background: activo ? 'rgba(0,243,255,0.10)' : 'rgba(255,255,255,0.02)',
        display: 'flex', flexDirection: 'column', gap: 2, boxShadow: activo ? '0 0 0 1px var(--accent) inset' : 'none'
      }}>
        <span style={{ fontSize: 12.5, fontWeight: 700, color: activo ? 'var(--accent)' : 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{titulo}</span>
        <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>{sub}</span>
      </button>
    );
    return (
      <div style={{ border: '1px solid var(--border-light)', borderRadius: 12, padding: 12, display: 'flex', flexDirection: 'column', gap: 9 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)' }}>Ver variante <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· trabajá con una sola a la vez</span></div>
        {vars.length === 0 ? (
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>No hay variantes con piezas. Armalas en <b>Variables</b>.</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
            {!soloVariables && card(!verVariante, 'Todas', 'vista completa', () => setVerVariante(null), '__todas')}
            {vars.map(v => { const n = (v.valores || []).filter(x => x.pieza_idx != null).length; return card(verVariante === v.clave, v.label || 'variante', n + ' pza' + (n === 1 ? '' : 's'), () => setVerVariante(v.clave), v.clave); })}
          </div>
        )}
      </div>
    );
  };
  // Arrastre de una pieza del nido en el visor (mueve TODAS sus tallas juntas).
  // La escala (unidades del viewBox por px de pantalla) se mide del SVG REAL en pantalla:
  // así el arrastre sigue al cursor 1:1 sin importar el zoom, el aspect ni el "letterbox".
  const nidoDragStart = (nombre, e) => {
    if (e.button !== 0 || !nidoData) return;
    e.preventDefault(); e.stopPropagation();
    const svg = e.currentTarget.ownerSVGElement;
    const rect = svg && svg.getBoundingClientRect();
    const vb = ((svg && svg.getAttribute('viewBox')) || '').split(/\s+/).map(Number);
    const W = vb[2], H = vb[3];
    if (!rect || !rect.width || !rect.height || !(W > 0) || !(H > 0)) return;
    // preserveAspectRatio 'meet' (default) → escala uniforme = el menor de los dos ejes.
    const pxPorUnidad = Math.min(rect.width / W, rect.height / H);
    if (!(pxPorUnidad > 0)) return;
    const escala = 1 / pxPorUnidad;               // px de pantalla → unidades del viewBox
    nidoDragRef.current = true;                    // congelar el viewBox mientras se arrastra (no se mueve bajo el cursor)
    const ini = nidoOffsets[nombre] || { x: 0, y: 0 };
    const sx = e.clientX, sy = e.clientY;
    let ultimo = ini;
    const mv = (ev) => { ultimo = { x: ini.x + (ev.clientX - sx) * escala, y: ini.y + (ev.clientY - sy) * escala }; setNidoOffsets(o => ({ ...o, [nombre]: ultimo })); };
    const up = () => {
      window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up);
      nidoDragRef.current = false;                  // descongelar → el viewBox se recalcula para encuadrar todo
      if (ultimo !== ini) guardarAcomodoPieza(nombre, ultimo);
      else setNidoOffsets(o => ({ ...o }));         // sin movimiento: forzar re-render para soltar el congelado
    };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
  };
  const guardarGrupos = () => guardarGruposCon(variantesEdit);


  // ── Asignar piezas del visor a un TIPO (Fase 1) ──
  // Cada valor de un tipo ES una pieza real: {id:'v_<idx>', label:<nombre>, pieza_idx:<idx>}.
  // Una pieza pertenece a un solo tipo → togglear la saca de cualquier otro (reasignar).
  const _nombreDeIdx = (idx) => (etqNombres[idx] || '').trim() || (etqData?.piezas?.[idx]?.nombre || '').trim() || `Pieza ${idx + 1}`;
  // Crea el valor de una pieza; si está en un vínculo "van juntas" toma el nombre del vínculo.
  const _valorDeIdx = (idx, juntas) => { const b = _juntaDeIdx(juntas, idx); return { id: 'v_' + idx, label: (b ? (b.nombre || '').trim() : '') || _nombreDeIdx(idx), pieza_idx: idx }; };
  const togglePiezaEnTipo = (clave, idx) => {
    // MULTIGRUPO: togglea la pieza SOLO en este grupo; no la saca de los demás.
    setVariantesEdit(prev => prev.map(t => {
      if (t.clave !== clave) return t;
      const juntas = t.juntas || [];
      const b = _juntaDeIdx(juntas, idx);
      const afectadas = b ? (b.piezas || []) : [idx];    // "van juntas": la unidad entera entra/sale junta
      const yaEsta = (t.valores || []).some(v => v.pieza_idx === idx);
      let vals;
      if (yaEsta) { const quitar = new Set(afectadas); vals = (t.valores || []).filter(v => !quitar.has(v.pieza_idx)); }
      else {
        const yaSet = new Set((t.valores || []).map(v => v.pieza_idx));
        const nuevos = afectadas.filter(i => !yaSet.has(i)).map(i => _valorDeIdx(i, juntas));
        vals = dedupePorNombre([...(t.valores || []), ...nuevos], juntas);
      }
      return { ...t, valores: vals };
    }));
  };
  const quitarPieza = (idx) => setVariantesEdit(prev => prev.map(t => ({ ...t, valores: (t.valores || []).filter(v => v.pieza_idx !== idx) })));
  const quitarPiezaDeGrupo = (clave, idx) => setVariantesEdit(prev => prev.map(t => t.clave === clave ? { ...t, valores: (t.valores || []).filter(v => v.pieza_idx !== idx) } : t));
  const renombrarPieza = (idx, label) => setVariantesEdit(prev => prev.map(t => ({ ...t, valores: (t.valores || []).map(v => v.pieza_idx === idx ? { ...v, label } : v) })));
  // Agregar VARIAS piezas de una al grupo destino (selección por recuadro). MULTIGRUPO:
  // solo agrega al grupo destino (no las saca de los otros grupos). Expande los vínculos.
  const agregarPiezasATipo = (clave, idxs) => {
    if (!idxs || !idxs.length) return;
    setVariantesEdit(prev => prev.map(t => {
      if (t.clave !== clave) return t;
      const juntas = t.juntas || [];
      const expandido = new Set();
      idxs.forEach(idx => { const b = _juntaDeIdx(juntas, idx); (b ? (b.piezas || []) : [idx]).forEach(i => expandido.add(i)); });
      const yaSet = new Set((t.valores || []).map(v => v.pieza_idx));
      const nuevos = [...expandido].filter(idx => !yaSet.has(idx)).map(idx => _valorDeIdx(idx, juntas));
      return { ...t, valores: dedupePorNombre([...(t.valores || []), ...nuevos], juntas) };
    }));
  };
  // ── Vínculos "van juntas" dentro de una variable ──
  const crearVinculoJuntas = (clave, idxs, nombre) => {
    const piezas = Array.from(new Set(idxs)).sort((a, b) => a - b);
    if (piezas.length < 2) { showError('Elegí al menos 2 piezas para vincularlas'); return; }
    const nom = (nombre || '').trim() || _nombreDeIdx(piezas[0]);
    const setP = new Set(piezas);
    const nueva = (variantesEdit || []).map(t => {
      if (t.clave !== clave) return t;
      // sacar esas piezas de vínculos previos, agregar el nuevo, y re-etiquetar sus valores
      const juntasPrev = (t.juntas || []).map(b => ({ ...b, piezas: (b.piezas || []).filter(i => !setP.has(i)) })).filter(b => (b.piezas || []).length >= 2);
      const juntas = [...juntasPrev, { id: 'j_' + uidVar(), nombre: nom, piezas }];
      const valores = (t.valores || []).map(v => setP.has(v.pieza_idx) ? { ...v, label: nom } : v);
      return { ...t, juntas, valores };
    });
    setVariantesEdit(nueva); guardarGruposCon(nueva, true);
  };
  const borrarVinculoJuntas = (clave, jid) => {
    const nueva = (variantesEdit || []).map(t => t.clave === clave ? { ...t, juntas: (t.juntas || []).filter(b => b.id !== jid) } : t);
    setVariantesEdit(nueva); guardarGruposCon(nueva, true);
  };
  // ── Paso 1: Nombrar piezas (selección con clic + recuadro) ──
  // Nombre genérico = sin el número final ("Espalda 8" → "Espalda"). Agrupa las piezas por familia.
  const nombreGenerico = (nom) => (nom || '').replace(/\s+\d+\s*$/, '').trim();
  // REGLA de variable (la REFERENCIA es el NOMBRE, no el id): un solo SLOT por NOMBRE. No pueden
  // convivir dos "Frente", dos "Cuello", dos "Manga"… en la misma variable. Un slot lo llena UNA
  // pieza suelta O un vínculo "van juntas" (manga corta + su vivo) que comparte nombre y ocupa un
  // solo slot con TODAS sus piezas.
  const _genDeValor = (v) => nombreGenerico(((etqNombres[v.pieza_idx] != null ? etqNombres[v.pieza_idx] : (v.label || '')) || '').toString().trim());
  // El vínculo "van juntas" que contiene esta pieza dentro de la variable (o null).
  const _juntaDeIdx = (juntas, idx) => (juntas || []).find(b => (b.piezas || []).includes(idx)) || null;
  // Nombre de slot de un valor: el del vínculo si está vinculado, sino su nombre genérico.
  const _slotDeValor = (v, juntas) => { const b = _juntaDeIdx(juntas, v.pieza_idx); return b ? ('#' + (b.id || (b.nombre || '').trim())) : _genDeValor(v); };
  // Dedup por slot: las piezas SIN nombre y sin vínculo entran siempre; por cada slot con
  // nombre queda lo ÚLTIMO agregado — si es un vínculo, quedan TODAS sus piezas juntas.
  const dedupePorNombre = (vals, juntas) => {
    const grupos = new Map(); const orden = [];
    (vals || []).forEach(v => {
      const s = _slotDeValor(v, juntas);
      if (!s) { orden.push({ solo: v }); return; }
      if (!grupos.has(s)) { grupos.set(s, []); orden.push({ slot: s }); }
      grupos.get(s).push(v);
    });
    const out = []; const hecho = new Set();
    orden.forEach(o => {
      if (o.solo) { out.push(o.solo); return; }
      if (hecho.has(o.slot)) return; hecho.add(o.slot);
      const arr = grupos.get(o.slot);
      const conJunta = arr.filter(v => _juntaDeIdx(juntas, v.pieza_idx));
      if (conJunta.length) {                              // el slot es un vínculo → quedan TODAS las piezas del último vínculo nombrado
        const ult = _juntaDeIdx(juntas, conJunta[conJunta.length - 1].pieza_idx);
        arr.filter(v => { const b = _juntaDeIdx(juntas, v.pieza_idx); return b && b.id === ult.id; }).forEach(v => out.push(v));
      } else { out.push(arr[arr.length - 1]); }            // pieza suelta → la última
    });
    return out;
  };
  const toggleSelNombrar = (idx) => setSelNombrar(prev => { const n = new Set(prev); if (n.has(idx)) n.delete(idx); else n.add(idx); return n; });
  const addSelNombrar = (idxs) => setSelNombrar(prev => { const n = new Set(prev); idxs.forEach(i => n.add(i)); return n; });
  const nombrarSeleccionadas = () => {
    const base = (etqNombreInput || '').trim();
    if (!base) { showError('Escribí un nombre para las piezas seleccionadas'); return; }
    const idxs = Array.from(selNombrar).sort((a, b) => a - b);
    if (!idxs.length) { showError('Seleccioná al menos una pieza (clic o recuadro)'); return; }
    const next = { ...etqNombres };
    idxs.forEach(idx => { next[idx] = base; });
    _renumerar(next, base);   // renumera TODO el genérico (nuevas + existentes) → nombres únicos, sin colisión
    setEtqNombres(next);
    setSelNombrar(new Set());
    setEtqNombreInput('');
  };

  // ── VARIANTES POR PIEZAS ────────────────────────────────────────────────────────────────────
  // Cambiar de molde corta el modo: la asignación pertenece a ESE molde y sus índices de pieza.
  useEffect(() => {
    setVarPzModo(false); setVarPzAsig({}); setVarPzInput(''); setVarPzAplicado({}); setVarPzEstado('');
    varPzUltimo.current = null;   // sin esto el autoguardado del molde nuevo compararía con el viejo
    setEmpModo(false); setEmpData(null); setEmpTalle(null); setEmpFijar(null);
    // La vista junta es geometría de ESTE molde: si sobrevive al cambio, el visor dibujaría las
    // piezas del molde anterior con los índices del nuevo.
    setEmpTodas(false); setEmpTodasData(null); setEmpTodasMotivo('');
  }, [activoProdDetalle?.id]);
  // Serialización ESTABLE (claves ordenadas) para comparar sin depender del orden de las claves.
  const _varPzSerial = (obj) => JSON.stringify(Object.keys(obj || {})
    .map(k => parseInt(k, 10)).sort((a, b) => a - b).map(k => [k, obj[k]]));
  // El visor tiene que mostrar TODAS las piezas del molde (no las de un talle): por eso la
  // detección se pide con `candidatas=1`, que además lee el molde ORIGINAL — así los índices de
  // pieza no se mueven y la asignación guardada se puede volver a abrir y corregir.
  const activarVarPz = React.useCallback(async (on) => {
    setVarPzModo(on);
    setSelNombrar(new Set());
    setVarPzInput('');
    const pid = pidCfg;
    try {
      const r = await fetch(`/api/plantilla/deteccion?pid=${encodeURIComponent(pid)}${on ? '&candidatas=1' : ''}`);
      if (r.ok) { const d = await r.json(); setEtqData(d); setEtqNombres(d.nombres_existentes || {}); }
    } catch { }
    if (on) {
      try {
        const r = await fetch(`/api/plantilla/variantes?pid=${encodeURIComponent(pid)}`);
        if (r.ok) {
          const d = await r.json();
          const a = {};
          Object.entries(d.asignacion_piezas || {}).forEach(([k, v]) => { a[parseInt(k, 10)] = v; });
          setVarPzAsig(a);
          const ap = {};
          Object.entries(d.asignacion_piezas_aplicada || {}).forEach(([k, v]) => { ap[parseInt(k, 10)] = v; });
          setVarPzAplicado(ap);
          // lo recién LEÍDO ya está en el server: se marca como persistido para que el
          // autoguardado no dispare un POST al abrir la herramienta
          varPzUltimo.current = _varPzSerial(a);
          setVarPzEstado(Object.keys(a).length ? 'guardado' : '');
        }
      } catch { }
    } else {
      varPzUltimo.current = null; setVarPzEstado('');
    }
  }, [pidCfg]);

  // AUTOGUARDADO: cada cambio de la asignación se persiste solo (con un respiro de 500 ms para no
  // pegarle al server en cada clic). Sólo guarda el BORRADOR: partir el PDF sigue siendo manual.
  useEffect(() => {
    if (!varPzModo) return;
    const s = _varPzSerial(varPzAsig);
    if (varPzUltimo.current === null) { varPzUltimo.current = s; return; }  // primer render tras cargar
    if (s === varPzUltimo.current) return;
    const pid = pidCfg;
    setVarPzEstado('guardando');
    const t = setTimeout(async () => {
      try {
        const r = await fetch('/api/plantilla/variantes_piezas_borrador', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pid, asignaciones: varPzAsig }),
        });
        if (!r.ok) { setVarPzEstado('error'); return; }
        varPzUltimo.current = s;
        setVarPzEstado('guardado');
      } catch { setVarPzEstado('error'); }
    }, 500);
    return () => clearTimeout(t);
  }, [varPzAsig, varPzModo, pidCfg]);

  const asignarVariantePz = () => {
    const nom = (varPzInput || '').trim();
    if (!nom) { showError(`Escribí el nombre de la ${term.variante.toLowerCase()} (una letra, un número o palabras)`); return; }
    const idxs = Array.from(selNombrar);
    if (!idxs.length) { showError('Seleccioná al menos una pieza (clic o recuadro)'); return; }
    setVarPzAsig(prev => { const n = { ...prev }; idxs.forEach(i => { n[i] = nom; }); return n; });
    setSelNombrar(new Set());
    setVarPzInput('');
  };
  const quitarVariantePz = (nom) => setVarPzAsig(prev => {
    const n = {}; Object.entries(prev).forEach(([k, v]) => { if (v !== nom) n[k] = v; }); return n;
  });
  const guardarVariantesPz = async () => {
    const pid = pidCfg;
    if (!Object.keys(varPzAsig).length) { showError('Todavía no asignaste ninguna pieza'); return; }
    setVarPzGuardando(true);
    try {
      const r = await fetch('/api/plantilla/variantes_piezas', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid, asignaciones: varPzAsig }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudieron aplicar las variantes'); return; }
      showMsg(`${(d.variantes || []).length} ${term.variante.toLowerCase()}s listas (${(d.piezas || []).length} piezas). Ahora indicá qué es cada pieza.`);
      // lo aplicado pasa a ser lo que había en el borrador → deja de haber pendiente
      setVarPzAplicado({ ...varPzAsig });
      varPzUltimo.current = _varPzSerial(varPzAsig);
      setVarPzEstado('guardado');
      await fetchProductos();
      // salir del modo: el visor vuelve a la vista normal, que ya muestra los talles nuevos
      await activarVarPz(false);
    } catch (e) { showError('No se pudo guardar: ' + e.message); }
    finally { setVarPzGuardando(false); }
  };

  // ── Gestión de nombres puestos (ventana emergente): renombrar / eliminar / quitar piezas ──
  const renombrarGrupoNombres = (gen, nuevoBase) => {
    const base = (nuevoBase || '').trim();
    if (!base || base === gen) return;
    const next = { ...etqNombres };
    // Renombrar el grupo viejo al nombre base (sin número)…
    let toco = false;
    Object.entries(next).forEach(([idx, nm]) => { if (nm && nombreGenerico(nm) === gen) { next[idx] = base; toco = true; } });
    if (!toco) return;
    // …y RENUMERAR TODO el genérico `base` junto (las recién renombradas + las que YA se
    // llamaban base) → nombres ÚNICOS. Antes numeraba 1..N ignorando las existentes, creaba
    // duplicados y al guardar el registro (dict por nombre) colisionaba y PERDÍA la pieza.
    _renumerar(next, base);
    setEtqNombres(next);
    if (grupoNombresAbierto === gen) setGrupoNombresAbierto(base);
  };
  const eliminarGrupoNombres = (gen) => {
    const next = { ...etqNombres };
    Object.entries(next).forEach(([idx, nm]) => { if (nm && nombreGenerico(nm) === gen) next[idx] = ''; });
    setEtqNombres(next);
    setResaltarNombre(r => r === gen ? null : r);
  };
  const quitarNombrePieza = (idx) => setEtqNombres(prev => ({ ...prev, [idx]: '' }));
  // Renumera todas las piezas de un nombre genérico 1..N (por número actual / idx). 1 sola → sin número.
  const _renumerar = (obj, gen) => {
    const items = Object.entries(obj)
      .filter(([, nm]) => nm && nombreGenerico(nm) === gen)
      .map(([idx, nm]) => ({ idx: parseInt(idx, 10), num: parseInt((String(nm).match(/(\d+)\s*$/) || [])[1] || '0', 10) }))
      .sort((a, b) => (a.num - b.num) || (a.idx - b.idx));
    if (items.length === 1) obj[items[0].idx] = gen;
    else items.forEach((it, k) => { obj[it.idx] = `${gen} ${k + 1}`; });
    return obj;
  };
  // Editar un nombre EN EL VISOR: tocar una pieza la suma o la quita de ese nombre.
  const toggleNombreEnPieza = (gen, idx) => setEtqNombres(prev => {
    const next = { ...prev };
    if (next[idx] && nombreGenerico(next[idx]) === gen) next[idx] = '';   // ya era de este nombre → quitar
    else next[idx] = gen;                                                  // sumar a este nombre
    return _renumerar(next, gen);
  });
  const agregarPiezasANombre = (gen, idxs) => setEtqNombres(prev => {
    const next = { ...prev };
    idxs.forEach(idx => { next[idx] = gen; });
    return _renumerar(next, gen);
  });

  // Recuadro de selección (marquee): clic izq. sostenido sobre un espacio vacío + arrastrar →
  // en "Nombrar" agrega las piezas a la selección; en "organizar" las asigna al tipo activo.
  // Usa coords de pantalla (getBoundingClientRect) para no lidiar con el zoom/pan.
  const iniciarRubber = (e) => {
    const cont = visorWheel.current.el;
    const modoNombrar = tabAjustesMolde === 'variables' && varStep === 'nombrar';
    const modoConj = tabAjustesMolde === 'variables' && asignandoConjunto;
    const modoGrupoPz = tabAjustesMolde === 'variables' && asignandoGrupoPz;
    if (!cont || (!asignandoTipo && !modoNombrar && !modoConj && !modoGrupoPz && !varPzModo && !empModo)) return;
    const clave = asignandoTipo;
    e.preventDefault();
    const x0 = e.clientX, y0 = e.clientY;
    setRubber({ x0, y0, x1: x0, y1: y0 });
    const mv = (ev) => setRubber({ x0, y0, x1: ev.clientX, y1: ev.clientY });
    const up = (ev) => {
      window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up);
      const rx0 = Math.min(x0, ev.clientX), ry0 = Math.min(y0, ev.clientY);
      const rx1 = Math.max(x0, ev.clientX), ry1 = Math.max(y0, ev.clientY);
      if (rx1 - rx0 > 3 || ry1 - ry0 > 3) {
        const idxs = [];
        cont.querySelectorAll('[data-piece]').forEach(g => {
          const b = g.getBoundingClientRect();
          if (b.right >= rx0 && b.left <= rx1 && b.bottom >= ry0 && b.top <= ry1) idxs.push(parseInt(g.getAttribute('data-piece'), 10));
        });
        if (idxs.length) { if (empModo) { addSelNombrar(idxs); } else if (varPzModo) { addSelNombrar(idxs); } else if (modoNombrar) { if (editandoNombre) agregarPiezasANombre(editandoNombre, idxs); else addSelNombrar(idxs); } else if (modoConj) agregarPiezasAConjunto(asignandoConjunto, idxs); else if (modoGrupoPz) agregarPiezasAGrupoPz(asignandoGrupoPz, idxs); else if (clave) agregarPiezasATipo(clave, idxs); }
      }
      setRubber(null);
    };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
  };

  const guardarConfig = async (nuevaConfig) => {
    const targetConfig = nuevaConfig || config;
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...targetConfig, pid: pidCfg })
      });
      const data = await res.json();
      if (!res.ok) throw new Error("No se pudo guardar la configuración");
      setConfig(data);
      showMsg("Configuración guardada ✓");
    } catch (err) {
      showError(err.message);
    }
  };

  const handleDropOnFabric = (pieza, fabricName) => {
    if (!pieza || !fabricName) return;
    const nextAsig = { ...config.asignacion };
    
    // Si la pieza arrastrada forma parte de la selección múltiple, mover todo el lote
    if (piezasSeleccionadas.includes(pieza)) {
      piezasSeleccionadas.forEach(p => {
        nextAsig[p] = fabricName;
      });
      showMsg(`${piezasSeleccionadas.length} piezas reasignadas a la tela '${fabricName}' ✓`);
      setPiezasSeleccionadas([]);
    } else {
      nextAsig[pieza] = fabricName;
      showMsg(`Pieza '${pieza}' reasignada a la tela '${fabricName}' ✓`);
    }
    
    const next = { ...config, asignacion: nextAsig };
    setConfig(next);
    guardarConfig(next);
  };

  const checkConfirmAndGenerate = () => {
    setConfirmProductoId(productosCat.activo);
    setModalConfirmOpen(true);
  };

  const ejecutarGenerarSublimacion = async () => {
    setModalConfirmOpen(false);
    
    // Si eligió un producto diferente en la confirmación, primero lo activamos
    if (confirmProductoId !== productosCat.activo) {
      try {
        await fetch('/api/productos/activar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: confirmProductoId })
        });
      } catch (e) {
        showError("Error al cambiar de producto activo antes de tizar");
        return;
      }
    }

    try {
      const res = await fetch('/api/generar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prendas: filas })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      
      setTrabajoId(data.id);
      setTrabajoEstado({ estado: 'en cola', progreso: '', resultado: null, error: null });
      showMsg("Tizada enviada a cola de procesamiento...");
    } catch (err) {
      showError(err.message);
    }
  };

  // ── Pedido multi-molde ──
  const moldeById = (id) => productosCat.productos.find(p => p.id === id);
  // Plantilla común de la selección (todos deben usar la misma).
  const plantillaComun = (() => {
    const ids = moldesSeleccionados.length ? moldesSeleccionados : [];
    const tpl = ids.map(id => moldeById(id)?.planilla_template_id).filter(Boolean);
    return tpl.length ? tpl[0] : (moldeById(productosCat.activo)?.planilla_template_id || 'plan_default');
  })();

  // Al entrar/cambiar de molde activo, arrancar con ese molde elegido.
  useEffect(() => {
    if (productosCat.activo && moldesSeleccionados.length === 0) {
      setMoldesSeleccionados([productosCat.activo]);
    }
  }, [productosCat.activo]);

  const toggleMoldeSeleccion = (id) => {
    setMoldesSeleccionados(prev => {
      if (prev.includes(id)) {
        const next = prev.filter(x => x !== id);
        return next.length ? next : prev; // siempre al menos 1
      }
      // Solo se pueden sumar moldes de la MISMA plantilla del primero elegido.
      const tplBase = prev.length ? moldeById(prev[0])?.planilla_template_id : moldeById(id)?.planilla_template_id;
      if (prev.length && moldeById(id)?.planilla_template_id !== tplBase) {
        showError('Ese molde usa otra planilla. Solo podés combinar moldes con la misma planilla.');
        return prev;
      }
      return [...prev, id];
    });
  };

  const generarMulti = async () => {
    const ids = (moldesSeleccionados.length ? moldesSeleccionados : [productosCat.activo]).filter(Boolean);
    if (!ids.length) { showError('Elegí al menos un molde.'); return; }
    const sinArte = ids.filter(id => !arteEnPedido(id));
    if (sinArte.length) {
      showError('Cargá el diseño en el paso Arte para: ' + sinArte.map(id => moldeById(id)?.nombre).join(', '));
      return;
    }
    setTrabajoEstado(null); setTrabajoId(null); setTelaActiva(null);
    // UN solo trabajo: todos los moldes en la MISMA tizada, agrupados por tela.
    setTrabajosMulti([{ productoId: ids.join(','), nombre: ids.map(id => moldeById(id)?.nombre).join(' + '), jobId: null, estado: 'en cola', resultado: null, error: null, progreso: '' }]);
    setPedidoPaso('resultados');   // navegar al paso 5 SOLO cuando el trabajo ya arrancó (evita pantalla en negro)
    try {
      const _edoverride = (editableData?.objetos?.length && editableDiseno) ? { [editableDiseno]: { [verVariante || '*']: editorTfs } } : undefined;   // ajuste por pedido de editables POR VARIABLE
      // A prueba de balas: recalcular la VARIABLE correcta de cada fila JUSTO acá (de su
      // diseño → su molde), sin depender del efecto que rellena __variante. Solo se pisa si
      // la variable guardada no es del molde de esa fila (evita mandar una variable de otro molde).
      const _disCol = cols.find(c => c.role === 'diseno');
      const prendasFinal = (hayVariablesPlanilla ? filas.map(f => {
        const cl = varianteDeDiseno(_disCol ? (f[_disCol.id] || '') : '');
        const claveOk = cl && (!f.__variante || !variablesDisponibles.some(v => v.clave === f.__variante && ids.includes(v.moldeId)));
        return claveOk ? { ...f, __variante: cl } : f;
      }) : filas);
      // TELAS del pedido: tela base por molde + overrides por pieza (id → nombre para el motor).
      const _telaNom = {}; (telasReg.telas || []).forEach(t => { _telaNom[t.id] = t.nombre; });
      const tela_base = {}, asignaciones = {};
      ids.forEach(pid => {
        const b = telaBaseMolde[pid]; if (b && _telaNom[b]) tela_base[pid] = _telaNom[b];
        const ov = telaPorPieza[pid] || {}; const o = {};
        Object.entries(ov).forEach(([pz, tid]) => { if (tid && _telaNom[tid]) o[pz] = _telaNom[tid]; });
        if (Object.keys(o).length) asignaciones[pid] = o;
      });
      const res = await fetch('/api/generar_multi', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ molds: ids, prendas: prendasFinal, default_diseno: disenoActivo || disenosPedido[0]?.id || 'principal', perfil_forzado: perfilForzado || undefined, editables: _edoverride, tela_base, asignaciones }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      setTrabajosMulti(prev => prev.map(t => ({ ...t, jobId: data.id, estado: 'generando' })));
    } catch (err) {
      setTrabajosMulti(prev => prev.map(t => ({ ...t, estado: 'error', error: err.message })));
    }
    showMsg('Generando la tizada…');
  };

  // Sondeo de los trabajos multi-molde.
  useEffect(() => {
    const pend = trabajosMulti.filter(t => t.jobId && (t.estado === 'generando' || t.estado === 'en cola'));
    if (!pend.length) return;
    const iv = setInterval(async () => {
      for (const t of pend) {
        try {
          const d = await (await fetch('/api/trabajo/' + t.jobId)).json();
          setTrabajosMulti(prev => prev.map(x => x.jobId === t.jobId
            ? { ...x, estado: d.estado, progreso: d.progreso, resultado: d.resultado ?? x.resultado, error: d.error } : x));
        } catch (e) { /* reintenta al próximo tick */ }
      }
    }, 1200);
    return () => clearInterval(iv);
  }, [trabajosMulti]);

  // Guardar el avance del wizard para no perderlo al recargar la página.
  useEffect(() => {
    try {
      localStorage.setItem('tizada_wizard', JSON.stringify({
        pedidoPaso, moldesSeleccionados, arteIdx, arteCargado, telaActiva, trabajosMulti, disenosPedido, disenoActivo, disenoMoldes, disenoVars,
        telaBaseMolde, telaPorPieza,
      }));
    } catch (e) { /* localStorage lleno o no disponible */ }
  }, [pedidoPaso, moldesSeleccionados, arteIdx, arteCargado, telaActiva, trabajosMulti, disenosPedido, disenoActivo, disenoMoldes, disenoVars, telaBaseMolde, telaPorPieza]);

  // Cargar el registro de telas al entrar al paso Arte (para el selector de tela por pieza).
  useEffect(() => { if (pedidoPaso === 'arte') fetchTelas(); }, [pedidoPaso]);

  // moldesSeleccionados = unión de los moldes asignados a algún diseño (lo usan la
  // planilla y la generación). Se deriva de disenoMoldes.
  useEffect(() => {
    const union = [...new Set(Object.values(disenoMoldes).flat())];
    setMoldesSeleccionados(prev => (prev.length === union.length && prev.every(x => union.includes(x)) ? prev : union));
  }, [disenoMoldes]);

  // El primer molde elegido es el "primario": se mantiene activo para que la
  // planilla (columnas/variantes) y el estado de arte sean los de la selección.
  useEffect(() => {
    const first = moldesSeleccionados[0];
    if (first && first !== productosCat.activo) handleActivarProducto(first);
  }, [moldesSeleccionados]);

  // Miniaturas vectoriales de los moldes (para las tarjetas). Se piden una vez.
  const fetchMoldePreview = async (id) => {
    if (!id || moldePreviews[id]) return;
    try {
      const r = await fetch(`/api/productos/${id}/preview`);
      if (r.ok) { const data = await r.json(); setMoldePreviews(prev => ({ ...prev, [id]: data })); }
    } catch (e) { /* sin preview: la tarjeta usa un ícono */ }
  };
  useEffect(() => {
    if (activoTab === 'pedidos' || (activoTab === 'config' && adminSubView === 'nesting')) {
      productosCat.productos.forEach(p => fetchMoldePreview(p.id));
    }
  }, [activoTab, adminSubView, productosCat.productos.length]);

  // Ítems del paso ARTE de un diseño (lo que recorre `arteIdx`): cada VARIABLE elegida, con su
  // molde por detrás, MÁS cada molde elegido ENTERO. Los moldes propios que sube el usuario no
  // tienen Variables (ese paso se les recorta) → sin esto no tendrían pantalla de arte.
  const itemsArteDe = (did) => {
    const vs = ((disenoVars || {})[did] || []).map(cl => {
      const p = productosCat.productos.find(x => (x.variantes || []).some(v => v.clave === cl));
      const vo = p && (p.variantes || []).find(v => v.clave === cl);
      return { clave: cl, moldeId: p && p.id, label: (vo && vo.label) || 'Variable' };
    }).filter(x => x.moldeId);
    const conVar = new Set(vs.map(x => x.moldeId));
    const ms = ((disenoMoldes || {})[did] || []).filter(m => !conVar.has(m)).map(m => {
      const p = productosCat.productos.find(x => x.id === m);
      return { clave: null, moldeId: m, label: (p && p.nombre) || 'Molde' };
    });
    return [...vs, ...ms];
  };

  // En el paso de DISEÑOS, el molde mostrado debe estar activo (para que "Cargar
  // diseño" suba a ese molde y el estado de arte sea el suyo).
  useEffect(() => {
    // Solo en el flujo de PEDIDOS→Arte. Si el usuario está en CONFIGURACIÓN (activoTab='config'),
    // este efecto NO debe correr: `pedidoPaso` queda en 'arte' al cambiar de sección y, como pisa
    // `verVariante` (deps la incluyen), hacía que en Config→Etiqueta cambiar de variable "volviera
    // sola a la primera" (la del arte). Ver [[operario-vs-config]].
    if (activoTab !== 'pedidos' || pedidoPaso !== 'arte') { return; }
    // VARIABLE-FIRST: se navega por VARIABLE. El molde es el de la variable (por detrás).
    // Los moldes elegidos ENTEROS (propios, sin variables) entran como ítem sin clave.
    const it = itemsArteDe(disenoActivo)[arteIdx] || {};
    const clave = it.clave;
    const id = it.moldeId;
    if (!id) return;
    if (id !== productosCat.activo) { handleActivarProducto(id); return; } // al activar, el efecto vuelve a correr
    if (clave && verVariante !== clave) setVerVariante(clave);   // el visor de arte muestra SOLO las piezas de la variable
    if (!clave && verVariante) setVerVariante(null);             // molde entero → sin filtro de variable
    // Siempre se ve el MOLDE (vacío). El DISEÑO solo si en ESTE pedido ya se subió (para ESTE diseño).
    if (arteCargado[disenoActivo + '|' + id]) cargarMapeadorOperario(); else { setMapeoData(null); cargarMoldeOperario(); }
  }, [activoTab, pedidoPaso, arteIdx, productosCat.activo, arteCargado, disenoActivo, disenoVars, disenoMoldes, verVariante]);

  // Render de la miniatura vectorial de un molde (siluetas de las piezas).
  const MoldePreviewSVG = ({ id, height = 90, color = 'rgba(0,216,245,0.85)' }) => {
    const pv = moldePreviews[id];
    if (!pv || !pv.piezas?.length) {
      return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}><Icon name="productos" style={{ width: 22, height: 22, opacity: 0.5 }} /></div>;
    }
    return (
      <svg viewBox={`0 0 ${pv.img_w} ${pv.img_h}`} style={{ width: '100%', height, display: 'block' }} preserveAspectRatio="xMidYMid meet">
        {pv.piezas.map((p, i) => (
          <path key={i} d={p.path_svg} style={{ fill: 'rgba(255,255,255,0.05)', stroke: color, strokeWidth: 2.5 }} />
        ))}
      </svg>
    );
  };

  // Preview vectorial de UNA variable (pestaña Variables): solo las piezas de esa
  // variable, recortadas a su bbox. Usa las siluetas de moldePreviews[pid] filtradas
  // por pieza_idx. Sirve para elegir la variable por fila en la planilla.
  const VariantePreviewSVG = ({ pid, variante, height = 66, color = 'var(--accent)' }) => {
    const pv = moldePreviews[pid];
    const idxs = new Set((variante?.valores || []).map(v => v.pieza_idx).filter(x => x != null));
    const pcs = (pv?.piezas || []).filter(p => idxs.has(p.idx));
    if (!pcs.length) {
      return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}><Icon name="productos" style={{ width: 20, height: 20, opacity: 0.5 }} /></div>;
    }
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    pcs.forEach(p => { minX = Math.min(minX, p.px); minY = Math.min(minY, p.py); maxX = Math.max(maxX, p.px + p.pw); maxY = Math.max(maxY, p.py + p.ph); });
    const pad = Math.max(4, (maxX - minX) * 0.04);
    const vb = `${(minX - pad).toFixed(1)} ${(minY - pad).toFixed(1)} ${(maxX - minX + 2 * pad).toFixed(1)} ${(maxY - minY + 2 * pad).toFixed(1)}`;
    return (
      <svg viewBox={vb} style={{ width: '100%', height, display: 'block' }} preserveAspectRatio="xMidYMid meet">
        {pcs.map((p, i) => (
          <path key={i} d={p.path_svg} style={{ fill: 'rgba(255,255,255,0.05)', stroke: color, strokeWidth: 2.5 }} />
        ))}
      </svg>
    );
  };

  // Carga SOLO el molde (sus piezas) del molde activo → se ve el molde vacío aunque
  // todavía no haya diseño cargado.
  const cargarMoldeOperario = async () => {
    try {
      const r = await fetch(`/api/plantilla/deteccion${qPid()}`);
      if (r.ok) { const data = await r.json(); setEtqData(data); setEtqNombres(data.nombres_existentes || {}); }
    } catch (e) { /* sin molde */ }
  };

  // Carga el mapeador (diseño sobre el molde) del molde ACTIVO, inline en el paso
  // de Diseños — sin pantalla completa. Igual que abrirMapeoOperario pero embebido.
  // Aplica una deteccion del arte al estado del mapeador (mapeoData + valores iniciales).
  // Devuelve el mapeo aplicado (para usarlo YA, sin esperar el re-render del estado).
  const _aplicarDetArte = (det) => {
    setMapeoData(det);
    const prev = det.mapeo || {};
    const inicial = { ...prev };
    if (Object.keys(prev).length === 0) {
      if (det.mapeo_fijo && Object.keys(det.mapeo_fijo).length) Object.assign(inicial, det.mapeo_fijo);
      else det.mesas?.forEach(m => { if (m.sugerencia) inicial[m.sugerencia] = m.mesa; });
    }
    setMapeoValores(inicial);
    setSelectedPiezaMapeo(det.piezas_variable?.[0] || det.piezas?.[0] || '');   // 1ª de la VARIABLE, no del molde
    return inicial;
  };
  const cargarMapeadorOperario = async () => {
    // CACHÉ por (molde, diseño, variable): una variable ya visitada carga INSTANTÁNEO desde
    // memoria (sin neutro). El neutro (mapeoCargando) queda SOLO para la primerísima vez.
    const _dk = `${productosCat.activo}|${disenoActivo}|${verVariante || ''}`;
    const _hit = _detArteCache.current[_dk];
    let _mapa = _hit ? _aplicarDetArte(_hit) : null;
    try {
      if (!_hit) setMapeoCargando(true);
      // REGLA mapeo-por-variable: se pide el mapeo DE la variable activa (autoritativo si tiene
      // el suyo; si no, la base). Al cambiar de variable el efecto re-corre y recarga el suyo.
      const res = await fetch(`/api/arte/deteccion?diseno=${encodeURIComponent(disenoActivo)}&variante=${encodeURIComponent(verVariante || '')}${qPid('&')}`);
      if (!res.ok) { if (!_hit) setMapeoData(null); return null; }
      const det = await res.json();
      _detArteCache.current[_dk] = det;
      if (!_hit) _mapa = _aplicarDetArte(det);   // con caché ya aplicado, solo refrescamos el caché (sin re-pintar)
      // Geometría del molde al talle guía: también cacheada → revisitar variable = instantáneo.
      const _k2 = `${productosCat.activo}|__guia__`;
      const _det2 = _talleDetCache.current[_k2];
      if (_det2) { setEtqData(_det2); setEtqNombres(_det2.nombres_existentes || {}); }
      else {
        const r2 = await fetch(`/api/plantilla/deteccion${qPid()}`);
        if (r2.ok) { const data = await r2.json(); _talleDetCache.current[_k2] = data; setEtqData(data); setEtqNombres(data.nombres_existentes || {}); }
      }
      // WYSIWYG: cargar el BORDE de corte + la ETIQUETA REALES del molde para mostrarlos en el visor
      // del arte tal cual saldrán en la tizada (no solo el diseño).
      cargarBorde(); cargarEtiqueta();
    } catch (e) { /* sin mapeo */ }
    finally { setMapeoCargando(false); }
    return _mapa;
  };
  // "ASIGNANDO EL DISEÑO A CADA VARIANTE…": al CARGAR el arte se arma YA el render real de
  // TODOS los talles (una sola espera, visible, con progreso) → después navegar es instantáneo
  // desde memoria. Cada (diseño, variable, talle) guarda lo suyo; re-subir el arte lo renueva.
  const asignarTodasLasVariantes = async (mapeo) => {
    const pid = pidCfg, clave = verVariante, dis = disenoActivo;
    const talles = tallesMolde.length ? tallesMolde : (estado?.talles || []);
    if (!pid || !clave || !talles.length || !mapeo || !Object.keys(mapeo).length) return;
    _prefetchTok.current++;   // esta pasada manda: abortar cualquier precarga de fondo previa
    setAsignando({ hecho: 0, total: talles.length, talle: '' });
    const _sleep = (ms) => new Promise(r => setTimeout(r, ms));
    try {
      // GENERACIÓN EN PARALELO en el server (ProcessPool, ~4x): un endpoint arma TODOS los talles
      // a la vez y el front hace polling del progreso. PyMuPDF no es thread-safe → multiproceso.
      let usoParalelo = false;
      try {
        const r = await fetch('/api/arte/asignar_todo', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pid, diseno: dis, variante: clave, mapeo })
        });
        if (r.ok) {
          const { job, total } = await r.json();
          usoParalelo = true;
          for (let guard = 0; guard < 2000; guard++) {   // polling del progreso (hasta ~16min)
            await _sleep(500);
            let s; try { s = await (await fetch('/api/arte/asignar_estado?job=' + job)).json(); } catch (e) { break; }
            setAsignando({ hecho: s.hecho || 0, total: total || talles.length, talle: '' });
            if (s.done) break;
          }
        }
      } catch (e) { usoParalelo = false; }
      // Cargar los renders (ya en caché de disco) + geometría a la MEMORIA del navegador
      // → el cambio entre variantes queda instantáneo. Salen del caché, es rápido.
      for (let i = 0; i < talles.length; i++) {
        const t = talles[i];
        setAsignando({ hecho: i, total: talles.length, talle: String(t) });
        const k = _pvKeyCon(mapeo, t);
        if (!_pvCache.current[k]) {
          try {
            const res = await fetch('/api/arte/preview_piezas', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ pid, diseno: dis, variante: clave, mapeo, editables: { [clave || '*']: {} }, talle: t, sin_prewarm: true })
            });
            if (res.ok) { const d = await res.json(); if (d.piezas) _pvGuardar(k, d.piezas); }
          } catch (e) { /* sigue con el próximo talle */ }
        }
        if (!_talleDetCache.current[`${pid}|${t}`]) {
          try {
            const r = await fetch(`/api/plantilla/deteccion?talle_ref=${encodeURIComponent(t)}${qPid('&')}`);
            if (r.ok) _talleDetCache.current[`${pid}|${t}`] = await r.json();
          } catch (e) { /* sigue */ }
        }
        setAsignando({ hecho: talles.length, total: talles.length, talle: String(t) });
      }
    } finally { setAsignando(null); }
  };
  // RENDER REAL del motor por pieza, CACHEADO en disco (/api/arte/preview_piezas): una sola fuente
  // de verdad con la tizada. La 1ª vez por config arma+guarda (unos segundos; mientras tanto se ve
  // el re-dibujo JS de placeholder); después es instantáneo desde el caché. El visor MUESTRA ese SVG
  // (no lo re-dibuja). Si falla o aún no está, cae al re-dibujo JS. `_pvReq` descarta respuestas viejas.
  const _pvReq = React.useRef(0);
  // PRECARGA TOTAL DE TALLES: los renders reales de TODOS los talles se guardan en MEMORIA
  // (además del caché en disco del server) y la geometría del molde por talle también →
  // cambiar de talle es un intercambio instantáneo, sin fetch y sin contornos vacíos.
  const _pvCache = React.useRef({});        // clave(pid|diseño|variable|talle|mapeo|edits) → piezas
  const _talleDetCache = React.useRef({});  // `${pid}|${talle}` → /api/plantilla/deteccion de ese talle
  const _detArteCache = React.useRef({});   // `${pid}|${diseño}|${variable}` → /api/arte/deteccion (mapeador)
  const _prefetchTok = React.useRef(0);     // aborta una precarga vieja si cambió el contexto
  const _pvKeyCon = (mapeo, talle) => `${productosCat.activo}|${disenoActivo}|${verVariante}|${talle}|${JSON.stringify(mapeo || {})}|${JSON.stringify(editorTfs || {})}`;
  const _pvKeyDe = (talle) => _pvKeyCon(mapeoValores, talle);
  const _pvGuardar = (k, piezas) => {
    if (Object.keys(_pvCache.current).length > 300) _pvCache.current = {};   // tope de memoria
    _pvCache.current[k] = piezas;
  };
  // Precarga en background del RESTO de los talles (render + geometría). Corre tras cargar el
  // talle actual; el server ya los tiene en disco (pre-warm) → cada pedido es rápido. Con
  // ediciones de editables SIN guardar (override) no se precarga (cambia con cada arrastre).
  const _prefetchTalles = (mapeo, talleActual) => {
    const pid = pidCfg, clave = verVariante, dis = disenoActivo;
    if (Object.keys(editorTfs || {}).length) return;
    const todos = tallesMolde.length ? tallesMolde : (estado?.talles || []);
    const iAct = todos.findIndex(t => String(t) === String(talleActual || ''));
    // ORDEN: primero los talles VECINOS del actual (los más probables de tocar) y de ahí se abre.
    const talles = todos
      .map((t, i) => ({ t, d: iAct >= 0 ? Math.abs(i - iAct) : i }))
      .filter(x => String(x.t) !== String(talleActual || ''))
      .sort((a, b) => a.d - b.d).map(x => x.t);
    if (!talles.length) return;
    const tok = ++_prefetchTok.current;
    (async () => {
      for (const t of talles) {
        if (tok !== _prefetchTok.current) return;         // cambió variable/mapeo/talle → abortar
        const k = _pvKeyCon(mapeo, t);
        if (!_pvCache.current[k]) {
          try {
            // `bg: true` → el server le CEDE EL PASO a lo que pida el usuario (nunca compite)
            const res = await fetch('/api/arte/preview_piezas', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ pid, diseno: dis, variante: clave, mapeo, editables: { [clave || '*']: {} }, talle: t, bg: true })
            });
            if (res.ok) { const d = await res.json(); if (d.piezas) _pvGuardar(k, d.piezas); }
          } catch (e) { /* siguiente talle */ }
        }
        if (tok !== _prefetchTok.current) return;
        if (!_talleDetCache.current[`${pid}|${t}`]) {
          try {
            const r = await fetch(`/api/plantilla/deteccion?talle_ref=${encodeURIComponent(t)}${qPid('&')}`);
            if (r.ok) _talleDetCache.current[`${pid}|${t}`] = await r.json();
          } catch (e) { /* siguiente */ }
        }
      }
    })();
  };
  const cargarPreviewPiezas = async (mapeoOverride) => {
    const pid = pidCfg, clave = verVariante;
    if (pedidoPaso !== 'arte' || !pid || !clave) { setPreviewPiezas({}); return; }
    const mapeo = mapeoOverride || mapeoValores;
    const talle = etqData?.talle_ref;
    const k = _pvKeyCon(mapeo, talle);
    const hit = _pvCache.current[k];
    if (hit) {   // EN MEMORIA → instantáneo (sincrónico: se pinta en el mismo frame, sin blanco)
      setPreviewPiezas(hit);
      _prefetchTalles(mapeo, talle);
      return;
    }
    const req = ++_pvReq.current;
    try {
      const res = await fetch('/api/arte/preview_piezas', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid, diseno: disenoActivo, variante: clave, mapeo, editables: { [clave || '*']: editorTfs }, talle })   // override de editables POR VARIABLE (clave) + el TALLE que se ve
      });
      if (req !== _pvReq.current) return;                 // llegó una respuesta vieja → descartar
      if (res.ok) {
        const d = await res.json();
        if (req === _pvReq.current) { setPreviewPiezas(d.piezas || {}); if (d.piezas) _pvGuardar(k, d.piezas); _prefetchTalles(mapeo, talle); }
      }
    } catch (e) { /* cae al re-dibujo JS */ }
  };
  // Al cambiar de variante/diseño: limpiar YA (se ve el re-dibujo JS de la nueva variante) para no
  // mostrar por un instante las piezas de la anterior.
  React.useEffect(() => { setPreviewPiezas({}); }, [verVariante, disenoActivo]);
  // Al cambiar de TALLE: el render cacheado es de OTRO talle y se dibuja estirado a las medidas nuevas
  // (efecto feo de "molde estirado"). Limpiarlo YA (cae al placeholder, ya a medidas correctas) y
  // re-pedir el render del talle nuevo SIN debounce (es un cambio discreto y el caché lo hace instantáneo).
  React.useEffect(() => {
    if (pedidoPaso !== 'arte' || !verVariante) return;
    setPreviewPiezas({});
    cargarPreviewPiezas();
  }, [etqData?.talle_ref]);
  // Refrescar el render real al entrar al Arte / cambiar variante / mover el mapeo o el override
  // (debounce largo: espera a que dejes de arrastrar; el caché hace instantáneos los repetidos).
  React.useEffect(() => {
    if (pedidoPaso !== 'arte' || !verVariante) return;
    const id = setTimeout(() => cargarPreviewPiezas(), 700);
    return () => clearTimeout(id);
  }, [mapeoValores, verVariante, disenoActivo, pedidoPaso, productosCat.activo, editorTfs]);
  // Ver cómo queda el diseño en una VARIANTE (talle): re-detecta el molde a ese talle.
  // PRECARGA TOTAL: si geometría y render del talle destino YA están en memoria, el cambio es
  // un intercambio en el MISMO frame (sin fetch). Si no, el visor sigue mostrando el diseño
  // correcto del talle vía `mapeo_talles` (placeholder) hasta que llegue el render real —
  // NUNCA contornos vacíos ni diseños de otro talle.
  const verVarianteOperario = async (talle) => {
    const pid = pidCfg;
    const _prevHit = _pvCache.current[_pvKeyDe(talle)];
    const _detHit = _talleDetCache.current[`${pid}|${talle}`];
    if (_detHit) {
      setEtqData(_detHit); setEtqNombres(_detHit.nombres_existentes || {});
      if (_prevHit) setPreviewPiezas(_prevHit);
      return;
    }
    try {
      const r = await fetch(`/api/plantilla/deteccion?talle_ref=${encodeURIComponent(talle)}${qPid('&')}`);
      if (r.ok) {
        const data = await r.json();
        _talleDetCache.current[`${pid}|${talle}`] = data;
        setEtqData(data); setEtqNombres(data.nombres_existentes || {});
        if (_prevHit) setPreviewPiezas(_prevHit);
      }
    } catch (e) { /* mantiene la variante actual */ }
  };

  // ── EMPAREJAR TALLES (§10.c) ──────────────────────────────────────────────────────────
  // Herramienta para el molde que NO trae las piezas dispuestas parecido en cada talle: el
  // emparejado automático (posición relativa + forma + área) se queda sin señal y propaga el
  // nombre a la pieza equivocada. Dos salidas, en el MISMO visor de siempre:
  //   1) REACOMODAR — seleccionar piezas (clic / recuadro) y arrastrarlas hasta que el talle
  //      quede dispuesto como el guía. Es virtual: solo mueve la caja con la que se empareja.
  //   2) CORREGIR — decir a mano «esta pieza en este talle es la #N». Manda sobre todo.
  // `silencioso` = precarga para poder MOSTRAR los grupos ya hechos sin entrar al modo (el usuario
  // volvía, veía el panel vacío y creía que había perdido el trabajo). No molesta con errores.
  const cargarEmparejado = async (silencioso) => {
    const pid = pidCfg;
    try {
      const r = await fetch(`/api/plantilla/emparejado?pid=${encodeURIComponent(pid)}`);
      const d = await r.json();
      if (!r.ok) { if (!silencioso) showError(d.error || 'No se pudo leer el emparejado'); return null; }
      setEmpData(d);
      cargarPzsGuia(d.guia, pid);
      return d;
    } catch (e) { if (!silencioso) showError('No se pudo leer el emparejado: ' + e.message); return null; }
  };

  // Geometría del talle GUÍA: la lista de grupos muestra la SILUETA de cada pieza (el nombre solo
  // no alcanza para saber cuál es). Es la misma detección que ya usa el visor → sale del caché.
  const cargarPzsGuia = async (guia, pid) => {
    if (!guia) return;
    const k = `${pid}|${guia}`;
    const hit = _talleDetCache.current[k];
    if (hit) { setEmpGuiaPzs(hit.piezas || []); return; }
    try {
      const r = await fetch(`/api/plantilla/deteccion?pid=${encodeURIComponent(pid)}&talle_ref=${encodeURIComponent(guia)}`);
      if (!r.ok) return;
      const d = await r.json();
      _talleDetCache.current[k] = d;
      setEmpGuiaPzs(d.piezas || []);
    } catch (e) { /* sin miniaturas: la lista funciona igual */ }
  };

  // TODAS LAS VARIANTES JUNTAS: las piezas de todos los talles en un solo lienzo, para que el
  // gesto sea el mismo que nombrar («esto, esto y esto son el Frente») y no haya que ir talle
  // por talle. Devuelve la vista si se pudo, o `null` con el motivo cargado en `empTodasMotivo`.
  const cargarTodasVariantes = async (empd) => {
    const pid = pidCfg;
    try {
      const r = await fetch(`/api/plantilla/deteccion_todas?pid=${encodeURIComponent(pid)}`);
      const d = await r.json();
      if (!r.ok) { setEmpTodasMotivo(d.error || 'no se pudieron leer todas las variantes'); return null; }
      // ANIDADO = los talles están dibujados uno ENCIMA del otro: mostrarlos juntos es un amasijo
      // ilegible (no se puede distinguir el frente del S del frente del M). Ahí se trabaja de a uno.
      if (d.formato === 'anidado') {
        setEmpTodasMotivo(`Este molde tiene los ${term.variante.toLowerCase()}s dibujados uno ENCIMA del otro: mostrarlos juntos sería ilegible, así que se agrupa de a un ${term.variante.toLowerCase()}.`);
        return null;
      }
      // La correspondencia se guarda por (talle, pieza_idx) y ese índice es RELATIVO a la mesa: si
      // esta vista mirara otra mesa que el emparejado, la selección apuntaría a piezas que no son.
      if (empd?.mesa != null && d.mesa != null && empd.mesa !== d.mesa) {
        setEmpTodasMotivo('El molde tiene el bloque repartido en varias mesas: se agrupa de a un ' + term.variante.toLowerCase() + '.');
        return null;
      }
      setEmpTodasMotivo('');
      setEmpTodasData(d);
      return d;
    } catch (e) { setEmpTodasMotivo('no se pudieron leer todas las variantes: ' + e.message); return null; }
  };

  // Nombre que hoy tiene la pieza `idx` del talle `t` (según el registro re-propagado).
  const _nombreEnTalle = (t, idx) => {
    const a = (empData?.asignacion || {})[t] || {};
    return Object.keys(a).find(n => a[n] === idx) || '';
  };

  // Precarga al abrir la Moldería de un molde con varios talles: así el panel plegado ya puede
  // decir «N piezas agrupadas» y el trabajo hecho antes se VE sin tener que entrar al modo.
  useEffect(() => {
    if (tabAjustesMolde !== 'molderia') return;
    if (!((tallesMolde || []).length > 1) || empData || empModo) return;
    let vivo = true;
    (async () => { const d = await cargarEmparejado(true); if (!vivo && d) { /* descartado */ } })();
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminSubView, tabAjustesMolde, tallesMolde.length, activoProdDetalle?.id]);

  const abrirTalleEmp = async (t) => {
    setEmpTalle(t); setEmpFijar(null); setSelNombrar(new Set());
    await verVarianteOperario(t);
  };

  const activarEmparejar = async (on, vista) => {
    setEmpFijar(null); setSelNombrar(new Set()); setEmpNombreInput('');
    // La lista arranca limpia (filtro en «pendientes», nada abierto ni a medio renombrar):
    // el foco tiene que estar en lo que falta, no en el estado de la sesión anterior.
    setEmpAbierto(null); setEmpBuscar(''); setEmpRenombrar(null); setEmpFiltro('pend');
    setEmpModo(on);
    const v = vista || empVista;
    if (vista) setEmpVista(vista);
    if (!on) {
      setEmpTalle(null); setPzOffsets({}); setEmpTodas(false);
      const g = empData?.guia;
      if (g) await verVarianteOperario(g);
      return;
    }
    setModoAcomodar(false);
    const d = await cargarEmparejado();
    if (!d) { setEmpModo(false); return; }
    const otros = (d.talles || []).filter(t => t !== d.guia);
    // AGRUPAR arranca SIEMPRE en el talle guía: es ahí donde se elige la pieza y se le pone
    // el nombre. El modo avanzado arranca en otro talle (ahí se corrige, la guía no se toca).
    const t0 = v === 'simple' ? d.guia : otros[0];
    if (!t0) { showError(`El molde tiene un solo ${term.variante.toLowerCase()}: no hay nada que emparejar`); setEmpModo(false); return; }
    setEmpTalle(t0); setEmpFijar(null);
    await verVarianteOperario(t0);
    // AGRUPAR: intentar la vista con TODAS las variantes juntas (el gesto que pidió el usuario).
    // Sólo se puede en moldes `extendido`; si no, queda el flujo de a un talle con su explicación.
    if (v === 'simple') setEmpTodas(!!(await cargarTodasVariantes(d)));
    else setEmpTodas(false);
  };

  // Offsets del visor (unidades del viewBox = mm) → payload {idx: [dx_mm, dy_mm]}.
  const _empAcomodoPayload = () => {
    const out = {};
    Object.entries(pzOffsets || {}).forEach(([k, v]) => {
      if (v && (Math.abs(v.x) > 0.01 || Math.abs(v.y) > 0.01)) {
        out[k] = [Math.round(v.x * 100) / 100, Math.round(v.y * 100) / 100];
      }
    });
    return out;
  };

  // Guarda el ajuste y RE-PROPAGA el nombrado con él (el backend rehace el registro).
  const _postEmparejado = async (extra = {}, msg = 'Emparejado aplicado ✓') => {
    if (!empTalle) return;
    setEmpGuardando(true);
    try {
      const r = await fetch('/api/plantilla/emparejado', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: pidCfg, talle: empTalle, acomodo: _empAcomodoPayload(), ...extra }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo aplicar el emparejado'); return; }
      setEmpData(prev => ({ ...(prev || {}), ...d }));
      _talleDetCache.current = {};      // el registro cambió → los nombres por talle quedaron viejos
      setNidoData(null); setNidoError(null);   // el nido se arma con el emparejado: hay que rearmarlo
      await verVarianteOperario(empTalle);
      await fetchProductos();
      showMsg(msg);
    } catch (e) { showError('No se pudo aplicar: ' + e.message); }
    finally { setEmpGuardando(false); }
  };

  const aplicarEmparejado = () => _postEmparejado({});
  const fijarPiezaEmp = (nombre, idx) => _postEmparejado({ manual: { [nombre]: idx } }, `«${nombre}» fijada a la pieza #${idx + 1} ✓`);
  const soltarPiezaEmp = (nombre) => _postEmparejado({ manual: { [nombre]: null } }, `«${nombre}» vuelve al emparejado automático`);
  const resetAcomodoEmp = () => { setPzOffsets({}); _postEmparejado({ reset: 'acomodo', acomodo: {} }, 'Posiciones restablecidas'); };

  // ── AGRUPAR PIEZAS HOMÓLOGAS (camino principal) ───────────────────────────────────────
  // «Estas piezas son la misma y se llama Frente»: un gesto define el NOMBRE y la
  // CORRESPONDENCIA entre talles. Backend: POST /api/plantilla/grupo_pieza (guarda el nombre
  // en la guía + las confirmaciones en `manual`, que la heurística no pisa nunca).
  const _postGrupo = async (body, msg) => {
    setEmpGuardando(true);
    try {
      const r = await fetch('/api/plantilla/grupo_pieza', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: pidCfg, ...body }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo guardar el grupo'); return false; }
      setEmpData(prev => ({ ...(prev || {}), ...d }));
      _talleDetCache.current = {};              // el registro cambió → los nombres por talle quedaron viejos
      setNidoData(null); setNidoError(null);    // el nido se arma con el emparejado: hay que rearmarlo
      if (empTalle) await verVarianteOperario(empTalle);
      await fetchProductos();
      if (msg) showMsg(msg);
      return true;
    } catch (e) { showError('No se pudo guardar: ' + e.message); return false; }
    finally { setEmpGuardando(false); }
  };

  // Miniatura de la pieza del talle guía: en una lista de 36 filas el nombre solo no alcanza
  // para saber CUÁL es (y menos si todavía se llama «Pieza 7»). Es el mismo `path_svg` que
  // dibuja el visor, recortado al bbox de la pieza.
  const miniPieza = (idx, col, tam = 30) => {
    const p = (empGuiaPzs || []).find(x => x.idx === idx);
    if (!p || !p.path_svg || !(p.pw > 0) || !(p.ph > 0)) {
      return <div style={{ width: tam, height: tam, flex: '0 0 auto', borderRadius: 6, background: 'rgba(255,255,255,0.05)' }} />;
    }
    const pad = Math.max(p.pw, p.ph) * 0.05 + 0.5;
    return (
      <svg width={tam} height={tam} style={{ flex: '0 0 auto', display: 'block' }}
        viewBox={`${p.px - pad} ${p.py - pad} ${p.pw + 2 * pad} ${p.ph + 2 * pad}`} preserveAspectRatio="xMidYMid meet">
        <path d={p.path_svg} fill={col} fillOpacity={0.18} stroke={col} strokeWidth={1.2} vectorEffect="non-scaling-stroke" />
      </svg>
    );
  };

  // Color estable por nombre de grupo: la MISMA pieza se pinta igual en todos los talles.
  const colorGrupo = (nombre) => {
    let h = 0;
    for (let i = 0; i < (nombre || '').length; i++) h = (h * 31 + nombre.charCodeAt(i)) % 360;
    return `hsl(${h}, 72%, 58%)`;
  };
  // El color de grupo es `hsl(...)`, NO hex: pegarle un sufijo de alfa («…55») da un color
  // INVÁLIDO y el borde se pierde. Para transparencia hay que pasar por `hsla`.
  const colorGrupoA = (nombre, a) => colorGrupo(nombre).replace('hsl(', 'hsla(').replace(')', `, ${a})`);

  const crearGrupoPieza = async () => {
    const idxs = Array.from(selNombrar);
    if (idxs.length !== 1) { showError(`Tocá UNA pieza en ${empData?.guia}: el grupo es esa misma pieza en todos los ${term.variante.toLowerCase()}s`); return; }
    const nom = (empNombreInput || '').trim();
    if (!nom) { showError('Escribí qué es la pieza (Frente, Espalda, Manga…)'); return; }
    const viejo = (etqNombres[idxs[0]] || '').trim();
    const ok = await _postGrupo({ nombre: nom, guia_idx: idxs[0], renombrar_de: viejo && viejo !== nom ? viejo : '' },
      viejo && viejo !== nom ? `«${viejo}» ahora se llama «${nom}» ✓` : `«${nom}» agrupada en todos los ${term.variante.toLowerCase()}s ✓`);
    if (ok) { setEmpNombreInput(''); setSelNombrar(new Set()); }
  };

  // EL GESTO PRINCIPAL con todas las variantes juntas: se seleccionan las piezas que son LA MISMA
  // (una por talle) y se escribe qué es. Un solo llamado deja el nombre en el registro y la
  // correspondencia CONFIRMADA en todos los talles elegidos — no hay que ir talle por talle.
  const crearGrupoTodas = async () => {
    const porIdx = new Map((empTodasData?.piezas || []).map(p => [p.idx, p]));
    const sel = Array.from(selNombrar).map(g => porIdx.get(g)).filter(Boolean);
    if (!sel.length) { showError(`Seleccioná en el visor las piezas que son la misma (una por ${term.variante.toLowerCase()})`); return; }
    const nom = (empNombreInput || '').trim();
    if (!nom) { showError('Escribí qué es la pieza (Frente, Espalda, Manga…)'); return; }
    // Dos piezas del MISMO talle no pueden ser «la misma pieza»: se avisa y no se guarda a medias.
    const porTalle = {}, dup = [];
    sel.forEach(p => {
      if (porTalle[p.talle] != null) { if (!dup.includes(p.talle)) dup.push(p.talle); }
      else porTalle[p.talle] = p.t_idx;
    });
    if (dup.length) {
      showError(`Elegiste 2 piezas del mismo ${term.variante.toLowerCase()} (${dup.join(', ')}): una pieza es UNA sola por ${term.variante.toLowerCase()}`);
      return;
    }
    const guia = empData?.guia;
    if (porTalle[guia] == null) {
      showError(`Falta la pieza de ${guia}: el nombre se guarda en ese ${term.variante.toLowerCase()} y de ahí se propaga`);
      return;
    }
    const guia_idx = porTalle[guia];
    const piezas = { ...porTalle }; delete piezas[guia];
    const viejo = _nombreEnTalle(guia, guia_idx);       // la pieza ya tenía nombre → esto es renombrar
    const faltan = (empData?.talles || []).filter(t => porTalle[t] == null);
    const msg = faltan.length
      ? `«${nom}» guardada en ${sel.length} ${term.variante.toLowerCase()}s — en ${faltan.join(', ')} no elegiste ninguna, quedó la propuesta del sistema`
      : `«${nom}»: ${sel.length} piezas agrupadas y confirmadas ✓`;
    const ok = await _postGrupo({ nombre: nom, guia_idx, piezas, renombrar_de: viejo && viejo !== nom ? viejo : '' }, msg);
    if (ok) { setEmpNombreInput(''); setSelNombrar(new Set()); }
  };

  // Índice de la pieza de un grupo en el talle GUÍA (la clave con la que el backend lo identifica).
  const _idxGuiaDe = (nombre) => {
    const ng = empData?.nombres_guia || {};
    const k = Object.keys(ng).find(x => ng[x] === nombre);
    return k == null ? null : parseInt(k, 10);
  };

  // Corregir una pieza desde la vista junta: el talle sale de la pieza clickeada, no de `empTalle`
  // (acá no hay «un talle abierto»). Se manda como confirmación fija, igual que el resto.
  const fijarPiezaTodas = (nombre, gidx) => {
    const p = (empTodasData?.piezas || []).find(x => x.idx === gidx);
    if (!p) return;
    if (p.talle === empData?.guia) {
      showError(`Esa pieza es de ${p.talle}, el ${term.variante.toLowerCase()} donde se nombra: para cambiar ahí, seleccionala y escribí el nombre`);
      return;
    }
    const gi = _idxGuiaDe(nombre);
    if (gi == null) { showError(`No encuentro «${nombre}» en ${empData?.guia}`); return; }
    return _postGrupo({ nombre, guia_idx: gi, piezas: { [p.talle]: p.t_idx } },
      `«${nombre}» en ${p.talle} = pieza #${p.t_idx + 1} ✓`);
  };

  // Seleccionar en el visor todas las piezas de un grupo ya hecho (para revisarlo o rehacerlo).
  const seleccionarGrupoTodas = (nombre) => {
    const s = new Set();
    (empTodasData?.piezas || []).forEach(p => { if (_nombreEnTalle(p.talle, p.t_idx) === nombre) s.add(p.idx); });
    setSelNombrar(s);
    setEmpNombreInput(esNombreProvisorio(nombre) ? '' : nombre);
  };

  const borrarGrupoPieza = (nombre) => _postGrupo({ nombre, eliminar: true }, `«${nombre}» deshecha`);

  // Confirmar en bloque lo que propuso el sistema: pasa de «propuesto» a FIJO en todos los talles.
  const confirmarTodoGrupo = (nombre) => {
    const piezas = {};
    (empData?.talles || []).forEach(t => {
      if (t === empData?.guia) return;
      const j = ((empData?.asignacion || {})[t] || {})[nombre];
      if (j != null) piezas[t] = j;
    });
    if (!Object.keys(piezas).length) { showError('Todavía no hay ninguna propuesta que confirmar'); return; }
    return _postGrupo({ nombre, guia_idx: parseInt(Object.keys(empData?.nombres_guia || {}).find(k => empData.nombres_guia[k] === nombre), 10), piezas },
      `«${nombre}» confirmada en ${Object.keys(piezas).length} ${term.variante.toLowerCase()}s ✓`);
  };

  // CONFIRMAR TODO DE UNA VEZ. Fila por fila eran 36 clics y 36 re-propagaciones del registro
  // (cada POST rehace el registro entero). Acá va UN solo POST a /api/plantilla/emparejado SIN
  // `talle`: en ese modo el endpoint acepta el diccionario COMPLETO de `manual` y re-propaga una
  // sola vez. `asignacion` ya trae lo que hay hoy (propuesto + lo confirmado antes), así que
  // congelarla es exactamente «dar por buena la propuesta».
  const confirmarTodasLasPropuestas = async () => {
    const ng = empData?.nombres_guia || {};
    const nombres = Object.values(ng);
    const manual = {};
    (empData?.talles || []).forEach(t => {
      if (t === empData?.guia) return;
      const asig = (empData?.asignacion || {})[t] || {};
      const d = {};
      nombres.forEach(n => { if (asig[n] != null) d[n] = asig[n]; });
      if (Object.keys(d).length) manual[t] = d;
    });
    if (!Object.keys(manual).length) { showError('Todavía no hay ninguna propuesta que confirmar'); return; }
    setEmpGuardando(true);
    try {
      const r = await fetch('/api/plantilla/emparejado', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: pidCfg, manual }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo confirmar'); return; }
      setEmpData(prev => ({ ...(prev || {}), ...d }));
      _talleDetCache.current = {};      // el registro cambió → los nombres por talle quedaron viejos
      setNidoData(null); setNidoError(null);
      if (empTalle) await verVarianteOperario(empTalle);
      await fetchProductos();
      showMsg(`Confirmadas ${nombres.length} piezas en todos los ${term.variante.toLowerCase()}s ✓`);
    } catch (e) { showError('No se pudo confirmar: ' + e.message); }
    finally { setEmpGuardando(false); }
  };

  // Renombrar SIN tener que ir a buscar la pieza en el visor: la fila ya sabe cuál es (`idxGuia`).
  // Es el camino natural para reemplazar los provisorios «Pieza 3».
  const renombrarGrupo = async (idxGuia, viejo, nuevo) => {
    const nom = (nuevo || '').trim();
    if (!nom || nom === viejo) { setEmpRenombrar(null); return; }
    const ok = await _postGrupo({ nombre: nom, guia_idx: idxGuia, renombrar_de: viejo || '' },
      `«${viejo}» ahora se llama «${nom}» ✓`);
    if (ok) { setEmpRenombrar(null); setEmpAbierto(a => (a === viejo ? nom : a)); }
  };

  // Nombre puesto por el sistema para que el registro exista (§10.c): no dice nada y hay que
  // reemplazarlo. Se marca distinto en la lista para que se note que es provisorio.
  const esNombreProvisorio = (n) => /^pieza\s*\d+$/i.test((n || '').trim());

  // ESTADO GLOBAL del agrupado (una sola pasada, se usa en el encabezado y en la lista). Antes
  // cada fila cantaba su «0/5 confirmadas» y no había forma de saber cuánto faltaba EN TOTAL ni
  // si ya se podía seguir; eso es lo que se contesta acá arriba.
  const empStats = (() => {
    const ng = empData?.nombres_guia || {};
    const otros = (empData?.talles || []).filter(t => t !== empData?.guia);
    const asigT = empData?.asignacion || {}, manT = empData?.manual || {};
    const filas = Object.entries(ng).map(([i, n]) => {
      const nombre = n, idxGuia = parseInt(i, 10);
      const fijos = otros.filter(t => (manT[t] || {})[nombre] != null).length;
      const faltan = otros.filter(t => (asigT[t] || {})[nombre] == null).length;
      return { idxGuia, nombre, fijos, faltan, listo: faltan === 0 && fijos === otros.length,
               provisorio: esNombreProvisorio(nombre) };
    }).sort((a, b) => a.idxGuia - b.idxGuia);
    const total = (empGuiaPzs || []).length || filas.length;
    const provisorias = filas.filter(f => f.provisorio).length;
    return {
      filas, otros, total,
      agrupadas: filas.length,
      conNombrePropio: filas.length - provisorias,
      provisorias,
      confirmadas: filas.filter(f => f.listo).length,
      conFalta: filas.filter(f => f.faltan > 0).length,
      sinAgrupar: Math.max(0, total - filas.length),
      porConfirmar: filas.filter(f => !f.listo && f.faltan === 0).length,
    };
  })();

  // Ir a un talle a revisar/corregir una pieza: abre ese talle y queda esperando el clic.
  const cambiarVistaEmp = async (v) => {
    setEmpVista(v); setEmpFijar(null); setSelNombrar(new Set()); setEmpNombreInput('');
    const otros = (empData?.talles || []).filter(t => t !== empData?.guia);
    // Cada vista trabaja sobre un talle distinto: agrupar se hace en la GUÍA (ahí se nombra),
    // el ajuste avanzado en OTRO talle (la guía no se corrige contra sí misma).
    const t = v === 'simple' ? empData?.guia : (empTalle && empTalle !== empData?.guia ? empTalle : otros[0]);
    if (t && t !== empTalle) { setEmpTalle(t); await verVarianteOperario(t); }
    // El ajuste avanzado (reacomodar/corregir por índice) trabaja sobre UN talle: la vista junta
    // no aplica ahí. Al volver a agrupar se reintenta (los datos ya están cargados).
    if (v !== 'simple') setEmpTodas(false);
    else setEmpTodas(!!(empTodasData?.piezas?.length ? empTodasData : await cargarTodasVariantes(empData)));
  };

  const revisarPiezaEnTalle = async (nombre, talle) => {
    // Vista junta: NO hay que cambiar de talle (están todos a la vista) — sólo quedar esperando
    // el clic sobre la pieza correcta, en el talle que sea.
    if (empTodas) { setSelNombrar(new Set()); setEmpGrupoSel(nombre); setEmpFijar(nombre); return; }
    if (talle === empData?.guia) { await abrirTalleEmp(talle); setEmpFijar(null); return; }
    setEmpTalle(talle); setSelNombrar(new Set()); setEmpGrupoSel(nombre);
    await verVarianteOperario(talle);
    setEmpFijar(nombre);
  };

  // Medidas de todas las variantes (para el modo 'rango': cubrir el talle más grande del rango).
  const cargarMedidasVar = async () => {
    if (medidasVar) return;
    try { const r = await fetch(`/api/plantilla/medidas_variantes${qPid()}`); if (r.ok) setMedidasVar(await r.json()); } catch (e) { /* sin datos */ }
  };
  // Cambiar la configuración de medida del visor (default / rango / talle).
  const cambiarConfigMedida = (k) => {
    setConfigMedida(k);
    if (k === 'rango') cargarMedidasVar();
    if (k === 'talle') return;   // 'talle' maneja su propia detección por chip
    // GUÍA: en 'rango' con un rango ya elegido, la guía debe estar DENTRO del rango; si ya lo está,
    // no se toca. En 'default' (o rango sin talles), se vuelve a la guía del molde.
    const enRango = (k === 'rango' && rangoMedida.length && tallesMolde)
      ? tallesMolde.filter(x => rangoMedida.includes(x)) : [];
    if (enRango.length) {
      if (!enRango.includes(etqData?.talle_ref)) verVarianteOperario(enRango[0]);
      return;
    }
    fetch(`/api/plantilla/deteccion${qPid()}`).then(r => r.ok ? r.json() : null)
      .then(d => { if (d) { setEtqData(d); setEtqNombres(d.nombres_existentes || {}); } }).catch(() => { });
  };
  // Capas del ARTE que el .ai debe tener (para pre-crearlas como OCG en la guía): «diseño», «guias»
  // y una por cada columna de texto/número de la planilla. MISMA lógica que el modal "Qué va en cada
  // capa". Los nombres NO distinguen mayúsculas/acentos (el motor los usa igual que el arte real).
  const capasArteNombres = () => {
    const out = ['diseño', 'guias'];
    const seen = new Set(out.map(x => x.toLowerCase()));
    const reglaDe = (c) => (reglasPlanilla || []).find(r => r.id === c.reglaId) || (reglasPlanilla || []).find(r => r.comportamiento === (c.role || 'none'));
    for (const c of (cols || [])) {
      const reg = reglaDe(c); const comp = reg?.comportamiento || c.role;
      if (comp !== 'nombre' && comp !== 'numero') continue;
      const nom = (reg?.nombre || c.label || '').trim(); const k = nom.toLowerCase();
      if (!nom || seen.has(k)) continue; seen.add(k);
      out.push(nom);
    }
    return out;
  };
  // Descargar la GUÍA como .ai NATIVO: abre en Illustrator con las CAPAS del arte ya armadas
  // (molde, guias con los nombres como texto vivo, y diseño + texto/número vacías). Piezas de la
  // variable en curso + el modo (default/rango) para el nombre de mesa.
  const descargarPdfGuia = async () => {
    const params = new URLSearchParams({ config: configMedida, formato: 'ai' });
    if (pidCfg) params.set('pid', pidCfg);
    params.set('capas', JSON.stringify(capasArteNombres()));
    if (configMedida === 'rango' && rangoMedida.length) {
      params.set('rango', rangoMedida.join(','));
      if (etqData?.talle_ref) params.set('guia', etqData.talle_ref);   // la guía elegida dentro del rango
    }
    // SOLO las piezas de la variable en curso (las que no trabajamos no van en la descarga).
    if (verVariante) { const keys = nombresDeVariante(verVariante); if (keys.length) params.set('piezas', JSON.stringify(keys)); }
    try {
      const res = await fetch('/api/plantilla/pdf_guia?' + params.toString());
      if (!res.ok) { const e = await res.json().catch(() => ({})); showError(e.error || 'No se pudo generar la guía .ai'); return; }
      const blob = await res.blob();
      const cd = res.headers.get('Content-Disposition') || '';
      const m = cd.match(/filename="?([^"]+)"?/);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = m ? m[1] : 'guia.ai';
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    } catch { showError('No se pudo generar la guía .ai'); }
  };
  // Descargar la BASE (contornos del molde, sin recuadro/nombre/medidas). Si hay una VARIABLE
  // elegida → SOLO sus piezas (lo que se está trabajando). Sin variable → el .ai base completo.
  const descargarBase = () => {
    if (verVariante) {
      const params = new URLSearchParams({ config: configMedida, limpio: '1' });
      if (pidCfg) params.set('pid', pidCfg);
      if (configMedida === 'rango' && rangoMedida.length) { params.set('rango', rangoMedida.join(',')); if (etqData?.talle_ref) params.set('guia', etqData.talle_ref); }
      const keys = nombresDeVariante(verVariante); if (keys.length) params.set('piezas', JSON.stringify(keys));
      window.open('/api/plantilla/pdf_guia?' + params.toString(), '_blank');
    } else {
      window.open(`/api/productos/${pidCfg}/descargar_plantilla`, '_blank');
    }
  };
  // Toggle de una variante en el rango (con soporte shift+click para seleccionar un tramo).
  const toggleRango = (t, idx, e) => {
    const set = new Set(rangoMedida);
    // Ancla del shift+click: la del último click de ESTA sesión; si no hay (p. ej. el rango vino
    // guardado y es el 1er click), se usa la ÚLTIMA pieza YA seleccionada, en orden del archivo.
    // Sin esto, shift+click como primera acción no tenía desde dónde arrancar y solo agregaba una.
    let ancla = rangoLastRef.current;
    if (e.shiftKey && ancla == null && rangoMedida.length && tallesMolde) {
      const sel = tallesMolde.map((x, i) => (set.has(x) ? i : -1)).filter(i => i >= 0);
      if (sel.length) ancla = sel[sel.length - 1];
    }
    if (e.shiftKey && ancla != null && tallesMolde) {
      // El shift+click AGREGA o QUITA el rango según el estado de la pieza clickeada: si ya estaba
      // seleccionada, deselecciona todo el rango; si no, lo selecciona. Mismo gesto, las dos cosas.
      const a = Math.min(ancla, idx), b = Math.max(ancla, idx);
      const quitar = set.has(t);
      tallesMolde.slice(a, b + 1).forEach(x => (quitar ? set.delete(x) : set.add(x)));
    } else { if (set.has(t)) set.delete(t); else set.add(t); }
    rangoLastRef.current = idx;
    const nuevo = [...set];
    setRangoMedida(nuevo);
    // La GUÍA del rango (base del cálculo + variante que se ve) debe estar SIEMPRE DENTRO del rango.
    // Si la guía actual quedó fuera (o no hay), se elige la 1ª del rango (por orden de archivo) → el
    // visor muestra las piezas de ESA variante y los cálculos se basan en ella.
    if (nuevo.length && tallesMolde) {
      const enOrden = tallesMolde.filter(x => nuevo.includes(x));
      if (enOrden.length && !enOrden.includes(etqData.talle_ref)) verVarianteOperario(enOrden[0]);
    }
  };

  // Subir el diseño del cliente DENTRO del wizard (inline, sin pantalla completa).
  const cargarDisenoWizard = async (file) => {
    if (!file) return;
    const id = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId;   // VARIABLE-FIRST: el molde es el del ítem actual
    const fd = new FormData(); fd.append('archivo', file); fd.append('diseno', disenoActivo); if (id) fd.append('pid', id);
    showMsg('Subiendo y procesando el diseño…');
    try {
      const res = await fetch('/api/arte', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al procesar el diseño');
      _pvCache.current = {}; _detArteCache.current = {}; _prefetchTok.current++;   // arte NUEVO → tirar precargas (serían del arte viejo)
      setArteCargado(prev => ({ ...prev, [disenoActivo + '|' + id]: true }));
      avisarPerfilDiseno(disenoActivo, id);   // dispara YA el cartel del perfil (no espera los refrescos)
      // Si es un diseño NO principal, lo registro en el molde para que aparezca
      // como opción en la columna "Diseño" de la planilla.
      if (disenoActivo !== 'principal') {
        const nom = disenosPedido.find(d => d.id === disenoActivo)?.nombre || disenoActivo;
        try { await fetch('/api/disenos/guardar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid: id, nombre: nom }) }); } catch (e) {}
      }
      await fetchEstado();
      await fetchProductos();
      const _mapa = await cargarMapeadorOperario();
      if (data.campos_personalizacion) avisarCapasFaltantes(data.campos_personalizacion);
      showMsg('Diseño cargado ✓');
      // Una sola espera, VISIBLE: se asigna el diseño a todos los talles ahora (ventana con
      // progreso) → después navegar entre variantes es instantáneo desde memoria.
      await asignarTodasLasVariantes(_mapa || {});
    } catch (e) { showError(e.message); }
  };

  // Avanzar/retroceder el wizard del pedido.
  // ── Diseños del pedido (modelo nuevo) ──────────────────────────────────────
  // Paleta de colores para distinguir cada diseño visualmente.
  const DISENO_COLORS = ['#00d8f5', '#7c5cff', '#ff6b9d', '#ffb020', '#34d399', '#ff7a45', '#22d3ee', '#a78bfa'];
  const colorDeDiseno = (did) => DISENO_COLORS[Math.max(0, disenosPedido.findIndex(d => d.id === did)) % DISENO_COLORS.length];
  // Unión de moldes de las variables elegidas (el molde queda por detrás de la variable).
  const moldesUnion = [...new Set(Object.values(disenoMoldes).flat())];
  // VARIABLE-FIRST: TODAS las variables (con piezas) de TODOS los moldes, cada una con su
  // molde detrás. Es lo que se elige directamente en el pedido (ya no se elige el molde).
  const variablesDisponibles = productosCat.productos.flatMap(p =>
    (p.variantes || []).filter(v => (v.valores || []).some(x => x.pieza_idx != null))
      .map(v => ({ ...v, moldeId: p.id, moldeNombre: p.nombre, planilla: p.planilla_template_id })));
  // Grilla del paso "Diseños": en «Catálogo» van las variables de los moldes COMPARTIDOS; los
  // moldes propios del usuario tienen su propia pestaña («Mis artículos»).
  const _moldePropio = (mid) => !!(productosCat.productos.find(p => p.id === mid) || {}).propio;
  const varsCatalogo = variablesDisponibles.filter(v => !_moldePropio(v.moldeId));
  const varByClave = (clave) => variablesDisponibles.find(v => v.clave === clave) || null;
  const varsDeDiseno = (did) => disenoVars[did] || [];
  // Pool de variables ELEGIDAS en el pedido (unión de todos los diseños) → lo que ofrece la planilla.
  const variablesPlanilla = [...new Set(Object.values(disenoVars).flat())].map(varByClave).filter(Boolean);
  const hayVariablesPlanilla = variablesPlanilla.length > 0;
  const varianteDeFila = (fila) => variablesPlanilla.find(v => v.clave === fila?.__variante) || null;
  const moldeDeVariante = (fila) => varianteDeFila(fila)?.moldeId || moldesUnion[0] || productosCat.activo;
  // Elegir/soltar una VARIABLE en el/los diseño(s) activo(s). Sincroniza disenoMoldes (el
  // molde de la variable entra por detrás para que arte y generación sigan funcionando).
  const toggleVarEnDiseno = (clave) => {
    const targets = asignDiseno === 'todos' ? disenosPedido.map(d => d.id) : [asignDiseno];
    if (!targets.length) { showError('Primero escribí un diseño.'); return; }
    const nv = { ...disenoVars };
    const enTodos = targets.every(did => (nv[did] || []).includes(clave));
    targets.forEach(did => { const s = new Set(nv[did] || []); if (enTodos) s.delete(clave); else s.add(clave); nv[did] = [...s]; });
    setDisenoVars(nv);
    const nm = { ...disenoMoldes };
    // Los moldes elegidos ENTEROS (los propios, que no tienen variables) NO salen de `nv`:
    // hay que conservarlos o este recálculo los borraría al tocar cualquier variable.
    disenosPedido.forEach(d => {
      const enteros = (disenoMoldes[d.id] || []).filter(m => moldeSinVariables(m));
      nm[d.id] = [...new Set([...(nv[d.id] || []).map(cl => varByClave(cl)?.moldeId).filter(Boolean), ...enteros])];
    });
    setDisenoMoldes(nm);
  };
  // ¿Este molde no ofrece variables? (los propios del usuario: se eligen ENTEROS y el motor
  // genera todas sus piezas, que es justo lo que se quiere para un artículo propio).
  const moldeSinVariables = (mid) => !variablesDisponibles.some(v => v.moldeId === mid);
  // (elegir/soltar un MOLDE ENTERO en el diseño → `toggleMoldeEnDiseno`, más abajo: ya existía)
  // Si el molde tiene variables, cada fila DEBE tener una (si no, el motor generaría
  // TODAS las piezas). La variable de cada fila sale de su DISEÑO (como antes el molde) —
  // NO hay columna de variable: el Diseño de la fila define la variable a generar.
  const _clavesVar = variablesPlanilla.map(v => v.clave).join('|');
  const varianteDeDiseno = (dNombre) => {
    const d = disenosPedido.find(x => x.nombre === dNombre) || disenosPedido[0];
    const claves = disenoVars[d?.id] || [];
    if (claves[0]) return claves[0];
    // Fallback: la primera variable DEL MOLDE de este diseño — NUNCA de otro molde
    // (antes caía a variablesPlanilla[0], que podía ser la variable de un molde distinto).
    const mid = (disenoMoldes[d?.id] || [])[0] || moldesUnion[0];
    return (variablesDisponibles.find(v => v.moldeId === mid) || {}).clave || null;
  };
  useEffect(() => {
    if (!hayVariablesPlanilla || pedidoPaso !== 'planilla') return;
    const disenoCol = cols.find(c => c.role === 'diseno');
    setFilas(prev => {
      let changed = false;
      const next = prev.map(f => {
        const cl = varianteDeDiseno(disenoCol ? (f[disenoCol.id] || '') : '');
        return (cl && f.__variante !== cl) ? (changed = true, { ...f, __variante: cl }) : f;
      });
      return changed ? next : prev;
    });
  }, [hayVariablesPlanilla, pedidoPaso, _clavesVar, filas]);
  // Diseños que todavía NO tienen ningún molde VÁLIDO asignado. No se puede avanzar
  // a Arte hasta que CADA diseño tenga al menos un molde existente (no alcanza con que
  // uno lo tenga; un id viejo/borrado en el estado tampoco cuenta).
  const _moldesValidos = new Set(productosCat.productos.map(p => p.id));
  const disenosSinMolde = disenosPedido.filter(d => !(disenoMoldes[d.id] || []).some(m => _moldesValidos.has(m)));
  const puedeIrAArte = disenosPedido.length > 0 && disenosSinMolde.length === 0;
  // Tareas de arte: un (diseño, molde) por cada asignación.
  const tareasArte = disenosPedido.flatMap(d => (disenoMoldes[d.id] || []).map(mid => ({ did: d.id, mid })));
  const todasArteCargadas = tareasArte.length > 0 && tareasArte.every(t => arteCargado[t.did + '|' + t.mid]);
  // ¿El arte del PEDIDO está cargado para este molde? (lo que importa para generar, NO la
  // validación de la raíz del molde — que puede no existir si el diseño va en disenos/<slug>).
  const arteEnPedido = (mid) => disenosPedido.some(d => arteCargado[d.id + '|' + mid]);
  const moldesDeDiseno = (did) => disenoMoldes[did] || [];

  // Escribir un diseño nuevo (input del sistema, no ventana del navegador).
  const agregarDisenoPedido = () => {
    const nombre = (nuevoDisenoNombre || '').trim();
    if (!nombre) return;
    const slug = nombre.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'diseno';
    if (disenosPedido.some(d => d.id === slug)) { showError('Ya existe un diseño con ese nombre.'); return; }
    setDisenosPedido(prev => [...prev, { id: slug, nombre }]);
    setDisenoMoldes(prev => ({ ...prev, [slug]: prev[slug] || [] }));
    setAsignDiseno(slug);
    setNuevoDisenoNombre('');
  };
  const quitarDisenoPedido = (did) => {
    setDisenosPedido(prev => prev.filter(d => d.id !== did));
    setDisenoMoldes(prev => { const n = { ...prev }; delete n[did]; return n; });
    setArteCargado(prev => { const n = { ...prev }; Object.keys(n).forEach(k => { if (k.startsWith(did + '|')) delete n[k]; }); return n; });
    if (asignDiseno === did) setAsignDiseno('todos');
    if (disenoActivo === did) { setDisenoActivo(''); setArteIdx(0); }
  };
  // Asignar/quitar un molde a un diseño (o a TODOS si asignDiseno==='todos').
  const toggleMoldeEnDiseno = (mid) => {
    const targets = asignDiseno === 'todos' ? disenosPedido.map(d => d.id) : [asignDiseno];
    if (!targets.length) { showError('Primero escribí un diseño.'); return; }
    setDisenoMoldes(prev => {
      const n = { ...prev };
      // Si está en TODOS los targets, lo saco de todos; si no, lo agrego a los que falten.
      const enTodos = targets.every(did => (n[did] || []).includes(mid));
      targets.forEach(did => {
        const lst = new Set(n[did] || []);
        if (enTodos) lst.delete(mid); else lst.add(mid);
        n[did] = [...lst];
      });
      return n;
    });
  };

  const irPasoArte = () => {
    if (!disenosPedido.length) { showError('Escribí al menos un diseño.'); return; }
    if (disenosSinMolde.length) {
      const nombres = disenosSinMolde.map(d => `«${d.nombre}»`).join(', ');
      showError(`Falta elegir variable para ${disenosSinMolde.length === 1 ? 'el diseño' : 'los diseños'} ${nombres}. Cada diseño necesita al menos una variable.`);
      return;
    }
    setMapeoData(null);
    const primero = disenosPedido.find(d => (disenoMoldes[d.id] || []).length) || disenosPedido[0];
    setDisenoActivo(primero.id); setArteIdx(0); setPedidoPaso('arte');
  };
  // Borde de corte del molde: cargar / guardar.
  const cargarBorde = async () => {
    const pid = pidCfg; if (!pid) return;
    try { const r = await fetch(`/api/productos/borde_corte?pid=${pid}`); if (r.ok) setBordeConfig(await r.json()); } catch { }
  };
  const guardarBorde = async (next) => {
    const pid = pidCfg; if (!pid) return;
    const cfg = next || bordeConfig;
    setBordeConfig(cfg);
    try {
      const r = await fetch('/api/productos/borde_corte', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid, ...cfg }) });
      if (r.ok) { setBordeConfig(await r.json()); showMsg('Borde de corte guardado ✓'); } else showError('No se pudo guardar el borde');
    } catch { showError('No se pudo guardar el borde'); }
  };
  // Etiqueta de identificación del molde: cargar / guardar.
  const cargarEtiqueta = async () => {
    const pid = pidCfg; if (!pid) return;
    try { const r = await fetch(`/api/productos/etiqueta?pid=${pid}`); if (r.ok) setEtiquetaConfig(await r.json()); } catch { }
  };
  const cargarTalleEtq = async (talle) => {
    // Re-detecta el molde al talle elegido. IMPORTANTE: actualizar TAMBIÉN etqNombres (idx→nombre)
    // al mismo talle, si no canvasLayout queda en ese talle y los nombres en el guía → el visor
    // no matchea la pieza y desaparece al cambiar de talle.
    try { const r = await fetch(`/api/plantilla/deteccion?talle_ref=${encodeURIComponent(talle)}${qPid('&')}`); if (r.ok) { const d = await r.json(); setEtqData(d); setEtqNombres(d.nombres_existentes || {}); } } catch { }
  };
  // Carga los objetos editables: recorre los diseños del molde y deja los que TIENEN objetos.
  const cargarEditables = async (preferido) => {
    const pid = pidCfg; if (!pid) return;
    let lista = [{ id: 'principal', nombre: 'Principal' }];
    try { const rd = await fetch('/api/disenos?molds=' + encodeURIComponent(pid)); if (rd.ok) { const dd = await rd.json(); lista = (dd.por_molde || {})[pid] || lista; } } catch { }
    const conObj = [];
    for (const d of lista) {
      try {
        const r = await fetch(`/api/productos/editables?pid=${pid}&diseno=${encodeURIComponent(d.id)}`);
        if (r.ok) { const dat = await r.json(); if ((dat.objetos || []).length) conObj.push({ ...d, ...dat }); }
      } catch { }
    }
    setEditableDisenos(conObj.map(c => ({ id: c.id, nombre: c.nombre })));
    const elegido = conObj.find(c => c.id === preferido) || conObj[0];
    if (elegido) {
      setEditableDiseno(elegido.id); setEditableData(elegido);
      setEditableSel(elegido.objetos[0]?.nombre || null);
      setEditableTalle(elegido.talles?.[Math.floor((elegido.talles.length - 1) / 2)] || elegido.talles?.[0] || null);
    } else { setEditableData({ objetos: [], talles: [], piezas: [] }); }
  };
  // Config de TAMAÑO de capas editables (del molde, por nombre de capa). Sin gráficos: el
  // usuario escribe el nombre de la capa y define rangos de talles con su tamaño máximo (cm).
  const cargarEditConfig = async () => {
    const pid = pidCfg; if (!pid) return;
    try {
      const r = await fetch(`/api/productos/editables_config?pid=${pid}`);
      if (r.ok) { const d = await r.json(); setEditConfig(d.config || []); setEditConfigVariantes(d.variantes || []); }
    } catch { }
  };
  const guardarEditConfig = async (cfg) => {
    const pid = pidCfg; if (!pid) return;
    const lista = (cfg || editConfig || []).filter(c => (c.capa || '').trim());
    setEditConfig(lista);
    try {
      const r = await fetch('/api/productos/editables_config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid, config: lista }) });
      if (r.ok) showMsg('Capa editable guardada ✓'); else showError('No se pudo guardar.');
    } catch { showError('No se pudo guardar.'); }
  };
  // Carga los editables de un (molde, diseño) puntual — para el editor en Pedidos→Arte.
  const cargarEditablesPedido = async (pid, diseno, variante) => {
    if (!pid) return { objetos: [] };
    try {
      const r = await fetch(`/api/productos/editables?pid=${encodeURIComponent(pid)}&diseno=${encodeURIComponent(diseno || 'principal')}&variante=${encodeURIComponent(variante || '*')}`);   // transforms POR VARIABLE
      if (r.ok) {
        const d = await r.json();
        // Los OBJETOS AGREGADOS ya vienen en `d.objetos` desde /api/productos/editables, con la
        // MISMA forma que los del arte. Sólo se marcan para las acciones de la barra.
        d.objetos = (d.objetos || []).map(o => (o.agregado ? _objAgregadoAEditable(o, '') : o));
        setEditableData(d); setEditableDiseno(diseno || 'principal');
        // Al reabrir el MISMO contexto (mismo molde+diseño+variable) con ediciones en memoria, NO pisar:
        // el usuario debe seguir viendo lo que editó. Solo se recarga la base al cambiar de contexto.
        const ctxKey = `${pid}|${diseno || 'principal'}|${variante || '*'}`;
        const keep = ctxKey === editorCtx.current && Object.keys(editorTfsRef.current || {}).length > 0;
        if (!keep) {
          setEditableSel(d.objetos?.[0]?.nombre || null);
          const _t0 = d.talles?.[Math.floor((d.talles.length - 1) / 2)] || d.talles?.[0] || null; setEditableTalle(_t0); setEditableVarsSel(_t0 ? [_t0] : []);
          // arranca desde la BASE guardada por diseño (los ajustes del pedido se hacen encima)
          const base = Object.fromEntries((d.objetos || []).map(o => [o.nombre, { ...(o.transforms || {}) }]));
          setEditorTfs(base); histReset(base);
        }
        editorCtx.current = ctxKey;
        return d;
      }
    } catch { }
    return { objetos: [] };
  };
  // ── OBJETOS AGREGADOS: subir un PNG/SVG/PDF/AI y sumarlo al editor como un editable más ──
  const fileInputObjetoRef = React.useRef(null);
  const [subiendoObjeto, setSubiendoObjeto] = React.useState(false);
  // Objeto recién subido que ESPERA que el usuario elija EN QUÉ PIEZA va. Sin pieza no se
  // agrega: el objeto vive sobre una pieza concreta (ahí lo posiciona el editor y lo estampa
  // el motor), así que la elegís vos — no se adivina.
  const [objPendiente, setObjPendiente] = React.useState(null);
  // Convierte el objeto que devuelve el backend a la FORMA de un editable del arte, para que el
  // editor lo dibuje y lo transforme igual. Sin mesa_rect/bbox_mu → centerOf lo pone centrado en
  // la pieza (0.5, 0.5) al 30% (default razonable); el usuario lo mueve/escala con las herramientas.
  // El objeto AGREGADO viene del backend con la MISMA forma que uno del arte (mesa_rect,
  // bbox_mu, pos, svg base64…): no necesita ningún trato especial para dibujarse. Sólo se
  // marcan `_agregado`/`_oid` para las acciones de la barra (quitar de pieza / duplicar / borrar).
  const _objAgregadoAEditable = (o, piezaDefault) => ({
    ...o,
    nombre: o.nombre || o.id,
    _oid: o.oid || o.id, _agregado: true,
    pieza: o.pieza || piezaDefault || '',
    svg: o.svg && !o.oid ? btoa(unescape(encodeURIComponent(o.svg))) : (o.svg || ''),
    transforms: o.transforms || {},
  });
  const agregarObjeto = async (file) => {
    if (!file) return;
    const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;
    setSubiendoObjeto(true);
    try {
      const fd = new FormData();
      fd.append('archivo', file); fd.append('pid', _mid); fd.append('diseno', editableDiseno);
      const r = await fetch('/api/productos/objeto_agregar', { method: 'POST', body: fd });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo agregar el objeto'); return; }
      // Subido: ahora el usuario ELIGE en qué pieza va (no se asigna solo). `_nuevo` = si cancela,
      // se borra (no quedan huérfanos); un objeto YA existente que se recoloca no se borra.
      setObjPendiente({ ..._objAgregadoAEditable(d.objeto, ''), _nuevo: true });
    } catch (e) { showError('No se pudo subir: ' + e.message); }
    finally { setSubiendoObjeto(false); }
  };
  // El objeto se coloca EN EL PUNTO donde el usuario clickeó sobre el diseño: `tf0` trae el
  // dx/dy (fracción de la pieza) de ese punto, y `talles` el alcance en el que se aplica.
  const asignarObjetoAPieza = async (pieza, tf0, talles) => {
    if (!objPendiente || !pieza) return;
    const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;
    const nombre = objPendiente.nombre, _oid = objPendiente._oid;
    setObjPendiente(null);
    // COLOCAR = INYECTAR el objeto en el arte como una capa `Editable <nombre>`, en la mesa de esa
    // pieza (en cada rango que use). Desde ahí ES un editable del diseño: no hay sistema paralelo
    // ni datos que sincronizar — el editor, el visor del Arte y el motor lo tratan igual.
    const tf = { dx: 0, dy: 0, ...(tf0 || {}) };
    try {
      const r = await fetch(`/api/productos/objeto_agregado/${_oid}/colocar`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: _mid, diseno: editableDiseno, pieza,
                               fx: 0.5 + (tf.dx || 0), fy: 0.5 + (tf.dy || 0) }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo colocar el objeto'); return; }
      // El arte cambió → se relee todo desde el diseño (única fuente de verdad).
      editorCtx.current = null;                 // fuerza recargar la base
      await cargarEditablesPedido(_mid, editableDiseno, verVariante);
      setEditableSel([nombre]);
      showMsg(`"${nombre}" agregado al diseño en ${pieza}. Ya es un objeto editable más.`);
    } catch (e) { showError('No se pudo colocar: ' + e.message); }
  };
  // QUITAR DEL DISEÑO un objeto ya inyectado: borra su capa del arte (contraparte de "colocar").
  // Sólo alcanza a las capas que agregó el usuario; las que trae el .ai original no se tocan.
  const quitarObjetoDelArte = async (capa) => {
    const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;
    try {
      const r = await fetch('/api/productos/editable_quitar', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: _mid, diseno: editableDiseno, capa }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo quitar del diseño'); return; }
      editorCtx.current = null;                 // el arte cambió → se relee todo
      await cargarEditablesPedido(_mid, editableDiseno, verVariante);
      setEditableSel([]);
      showMsg(`"${capa.replace(/^Editable\s+/i, '')}" se quitó del diseño.`);
    } catch (e) { showError('No se pudo quitar: ' + e.message); }
  };
  // QUITAR de la pieza: el objeto NO se borra — queda en la barra, sin pieza, listo para colocarlo
  // en otra. (Un objeto vive en UNA sola pieza; para tenerlo en dos, se duplica.)
  const quitarObjetoDePieza = async (oid) => {
    const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;
    setEditableData(prev => ({ ...(prev || {}), objetos: ((prev || {}).objetos || []).map(o => (o._oid === oid ? { ...o, pieza: '' } : o)) }));
    try {
      await fetch(`/api/productos/objeto_agregado/${oid}/pieza`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: _mid, diseno: editableDiseno, pieza: '' }),
      });
    } catch { }
  };
  // DUPLICAR: copia el objeto para poder ponerlo TAMBIÉN en otra pieza. La copia nace sin pieza.
  const duplicarObjetoAgregado = async (oid) => {
    const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;
    try {
      const r = await fetch(`/api/productos/objeto_agregado/${oid}/duplicar`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pid: _mid, diseno: editableDiseno }),
      });
      const d = await r.json();
      if (!r.ok) { showError(d.error || 'No se pudo duplicar'); return; }
      const copia = _objAgregadoAEditable(d.objeto, '');
      setEditableData(prev => ({ ...(prev || {}), objetos: [...((prev || {}).objetos || []), copia] }));
      showMsg(`"${copia.nombre}" creado. Tocá "Colocar" y elegí la pieza.`);
    } catch (e) { showError('No se pudo duplicar: ' + e.message); }
  };
  // RECOLOCAR un objeto que ya existe (sin pieza): reusa el flujo de "tocá sobre el diseño".
  const recolocarObjeto = (o) => setObjPendiente({ ...o, _nuevo: false });
  const borrarObjetoAgregado = async (oid) => {
    const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;
    try {
      await fetch(`/api/productos/objeto_agregado/${oid}?pid=${encodeURIComponent(_mid)}&diseno=${encodeURIComponent(editableDiseno)}`, { method: 'DELETE' });
      setEditableData(prev => ({ ...(prev || {}), objetos: ((prev || {}).objetos || []).filter(o => o._oid !== oid) }));
    } catch (e) { showError('No se pudo borrar: ' + e.message); }
  };
  // Al ver el paso Arte (con el molde+arte cargado), cargar sus objetos editables para
  // mostrarlos POSICIONADOS sobre la pieza (reflejando la base + ajustes del pedido).
  React.useEffect(() => {
    if (pedidoPaso !== 'arte') return;
    const mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId;
    if (mid && arteCargado[disenoActivo + '|' + mid]) cargarEditablesPedido(mid, disenoActivo, verVariante);   // POR VARIABLE: recarga al cambiar de variable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedidoPaso, disenoActivo, arteIdx, arteCargado, verVariante]);
  // Reset del encuadre (pan/zoom) del editor al abrirlo o cambiar de variante.
  React.useEffect(() => { setEdVB(null); }, [editorEditOpen, verVariante]);
  // Posiciones de los objetos editables sobre las piezas (overlay del paso Arte).
  // Cada objeto editable → su FRACCIÓN dentro del diseño (mesa del arte). Se posiciona en el
  // render con la MISMA colocación que el thumbnail del diseño (escala al alto, centrado al
  // ancho), así cae EXACTO sobre el diseño y no "suelto" (antes usaba _pos_en_pieza, otra fórmula).
  const editablesOverlay = React.useMemo(() => {
    const ed = editableData; if (!ed || !canvasLayout?.layout?.length) return [];
    const T = etqData?.talle_ref || ed.talles?.[0];
    return (ed.objetos || []).flatMap(o => {
      // Matchear por nombre GENÉRICO: el editable está guardado en una pieza específica (ej.
      // "Frente 9") pero la VARIABLE elegida usa OTRA del mismo tipo (ej. "Frente 18"). Se genera
      // el overlay para TODAS las piezas de ese genérico (el visor solo dibuja las de la variante,
      // filtradas por vf) → si tomáramos solo la 1ª ("Frente 1") su idx no estaría en la variante.
      const _og = nombreGenerico(o.pieza || '');
      if (!o._agregado && (!o.mesa_rect || !o.bbox_mu)) return [];
      // Transform del talle en vista; si ese talle no tiene el suyo se usa cualquiera guardado
      // (mismo criterio que el motor) → el objeto se ve donde se puso, no en la posición base.
      const _tfs = editorTfs[o.nombre] || {};
      const tf = _tfs[T] || Object.values(_tfs).find(Boolean) || { dx: 0, dy: 0, rot: 0, scale: 1 };
      return canvasLayout.layout
        .filter(q => nombreGenerico(etqNombres[q.idx] || q.name || '') === _og)
        .map(p => {
          // MISMO resolvedor que el editor, con la mesa del TALLE en vista → las dos vistas
          // colocan igual, por construcción, aunque cada rango use una mesa de otro tamaño.
          const _pn = etqNombres[p.idx] || p.name || '';
          const _mi = (mapeoData?.mapeo_talles?.[_pn]?.[T]) || mapeoValores[_pn];
          const _me = _mi ? (mapeoData?.mesas || []).find(x => x.mesa === parseInt(_mi)) : null;
          const _asp = _me ? (_me.aspecto || (_me.w_cm && _me.h_cm ? _me.w_cm / _me.h_cm : null)) : null;
          const m = marcoDeObjeto(o, p, _asp);
          return {
            nombre: o.nombre, thumb: o.thumb, svg: o.svg, idx: p.idx, _agregado: o._agregado,
            rot: tf.rot, scale: tf.scale, dx: tf.dx, dy: tf.dy,
            fcx: m.fcx, fcy: m.fcy, fw: m.fw, fh: m.fh,
          };
        });
    });
  }, [editableData, editorTfs, canvasLayout, etqData, etqNombres]);
  // ── Zoom (rueda, AL CURSOR) y pan (click derecho) del Visor del Molde ──
  // Listener de rueda NATIVO no-pasivo: preventDefault corta el scroll de la página y
  // el zoom solo actúa cuando el mouse está SOBRE el visor (afuera, scroll normal).
  const visorWheel = useRef({ activo: false, el: null, h: null });
  const esqCache = useRef(new Map());   // pathD -> esquinas (largos de arco) para no recalcular en cada hover
  const segCacheRef = useRef(new Map());   // ETIQUETA: cache de segmentoEdge (path+posición → baseline) para NO re-medir el contorno (getPointAtLength ×cientos) en cada re-render/hover
  visorWheel.current.activo = !!etqData && tabAjustesMolde !== 'planilla';
  const setVisorEl = React.useCallback((el) => {
    const w = visorWheel.current;
    if (w.el && w.h) w.el.removeEventListener('wheel', w.h);
    if (w.ro) { w.ro.disconnect(); w.ro = null; }
    w.el = el;
    if (el) {
      const med = () => { setVisorW(el.clientWidth || 0); setVisorH(el.clientHeight || 0); };
      med();
      try { w.ro = new ResizeObserver(med); w.ro.observe(el); } catch { /* sin ResizeObserver */ }
      w.h = (e) => {
        if (!w.activo) return;
        e.preventDefault();
        const rect = el.getBoundingClientRect();
        const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
        // Escala REAL (k = px de pantalla por mm). Rango amplio: desde alejarse a un molde
        // de varios metros (~0.01) hasta acercarse al detalle (~80 px/mm).
        setVisorView(v => { const nk = Math.max(0.01, Math.min(80, v.k * (e.deltaY < 0 ? 1.15 : 1 / 1.15))); const r = nk / v.k; return { k: nk, tx: cx - (cx - v.tx) * r, ty: cy - (cy - v.ty) * r }; });
      };
      el.addEventListener('wheel', w.h, { passive: false });
    }
  }, []);
  // ── Escala REAL del visor (como Illustrator): k = px de pantalla por mm ──
  const PX_MM_100 = 96 / 25.4;                 // px por mm a 100% (1:1 real, ~3.78)
  const visorSvgRef = useRef(null);            // el <svg> del molde montado (medidas/etiqueta/mapeo/base)
  const _fitK = (wMm, hMm) => {
    if (!(wMm > 0) || !(hMm > 0) || !visorW || !visorH) return PX_MM_100 * 0.25;
    return Math.max(0.01, Math.min(visorW / wMm, visorH / hMm) * 0.94);
  };
  const _encuadrar = (wMm, hMm, k) => {        // centra un contenido wMm×hMm (mm) a zoom k
    const kk = k || _fitK(wMm, hMm);
    setVisorView({ k: kk, tx: Math.max(0, (visorW - wMm * kk) / 2), ty: Math.max(0, (visorH - hMm * kk) / 2) });
  };
  const _vbActivo = () => {                    // dims (mm) del viewBox del svg montado
    const vb = visorSvgRef.current?.viewBox?.baseVal;
    return vb && vb.width ? { w: vb.width, h: vb.height } : null;
  };
  const verTodoVisor = () => { const d = _vbActivo(); if (d) _encuadrar(d.w, d.h); };            // "Ver todo"
  const visor100 = () => { const d = _vbActivo(); if (d) _encuadrar(d.w, d.h, PX_MM_100); };      // "100%" (1:1 real)
  // Tamaño intrínseco (px = mm reales) del svg del molde según su viewBox (todo o variante).
  const svgRealSize = (vf, fw, fh) => (vf && vf.vb) ? { w: Number(vf.vb.split(' ')[2]), h: Number(vf.vb.split(' ')[3]) } : { w: fw, h: fh };
  const panVisor = (e) => {
    e.preventDefault();
    const sx = e.clientX, sy = e.clientY, base = visorView;
    const mv = (ev) => setVisorView({ k: base.k, tx: base.tx + (ev.clientX - sx), ty: base.ty + (ev.clientY - sy) });
    const up = () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up);
  };
  const resetVisor = () => verTodoVisor();   // "⟲" = Ver todo (encuadra el molde completo a escala real)
  // Al abrir el visor o cambiar de vista/variante, encuadrar automáticamente ("Ver todo").
  // Espera a tener el contenedor medido (visorW/H) y el svg montado (delay corto).
  useEffect(() => {
    if (!etqData || tabAjustesMolde === 'planilla' || !visorW || !visorH) return;
    const id = setTimeout(() => verTodoVisor(), 70);
    return () => clearTimeout(id);
  }, [etqData, tabAjustesMolde, verVariante, mapeandoDiseno, visorW, visorH, canvasLayout.vb]);
  // ETIQUETA sobre molde con muchas piezas: trabajar SIEMPRE de a una variable (nunca "Todas").
  // Evita el text-on-path de TODAS las piezas (lento) → auto-selecciona la primera variable.
  useEffect(() => {
    if (tabAjustesMolde === 'etiqueta' && !verVariante && varsConPiezas.length) {
      setVerVariante(varsConPiezas[0].clave);
    }
  }, [tabAjustesMolde, verVariante, varsConPiezas.length]);
  const guardarEtiqueta = async () => {
    const pid = pidCfg; if (!pid || !etiquetaConfig) return;
    try {
      const r = await fetch('/api/productos/etiqueta', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid, ...etiquetaConfig }) });
      if (r.ok) { setEtiquetaConfig(await r.json()); showMsg('Etiqueta guardada ✓'); } else showError('No se pudo guardar la etiqueta');
    } catch { showError('No se pudo guardar la etiqueta'); }
  };
  // ── ZONAS de texto de la etiqueta (por NOMBRE GENÉRICO, como la posición) ──
  // `zonas[gen] = { puntos:[t…(0-1, esquinas elegidas)], cont:[{mostrar,texto,align}…] }`.
  // Contorno cerrado: N puntos = N tramos (zona i = de puntos[i] a puntos[(i+1)%N]).
  const _zonaDefault = () => ({ mostrar: { talle: false, pieza: true, numero: false }, texto: '', align: 'centro' });
  const toggleZonaPunto = (gen, t) => {
    setEtiquetaConfig(prev => {
      const zonas = { ...((prev && prev.zonas) || {}) };
      const z = zonas[gen] || { puntos: [], cont: [] };
      const tol = 0.02;
      let puntos = (z.puntos || []).slice();
      const idx = puntos.findIndex(p => Math.min(Math.abs(p - t), 1 - Math.abs(p - t)) < tol);
      if (idx >= 0) puntos.splice(idx, 1); else puntos.push(t);
      puntos = Array.from(new Set(puntos.map(p => Math.round(p * 1000) / 1000))).sort((a, b) => a - b);
      const cont = puntos.map((_, i) => (z.cont && z.cont[i]) || _zonaDefault());
      if (puntos.length) zonas[gen] = { puntos, cont }; else delete zonas[gen];
      return { ...prev, zonas };
    });
  };
  const setZonaCont = (gen, i, patch) => {
    setEtiquetaConfig(prev => {
      const zonas = { ...((prev && prev.zonas) || {}) };
      const z = zonas[gen]; if (!z) return prev;
      const cont = (z.cont || []).slice(); cont[i] = { ...(cont[i] || _zonaDefault()), ...patch };
      zonas[gen] = { ...z, cont };
      return { ...prev, zonas };
    });
  };
  const limpiarZonas = (gen) => setEtiquetaConfig(prev => { const zonas = { ...((prev && prev.zonas) || {}) }; delete zonas[gen]; return { ...prev, zonas }; });
  // Piezas del molde ACTIVO sin diseño asignado. No se avanza si hay alguna:
  // se marca en rojo (en el mapeador) y se salta a la pieza que falta.
  const bloqueaPorSinDiseno = () => {
    if (!mapeoData?.mesas?.length) return false;   // todavía sin diseño cargado → otro control lo maneja
    // VARIABLE-FIRST: solo importan las piezas de la variable que se está viendo (no el molde entero).
    const _vf = verVariante ? varianteFiltro(verVariante) : null;
    const _pv = _vf ? new Set((canvasLayout?.layout || []).filter(p => _vf.show.has(p.idx)).map(p => (etqNombres?.[p.idx] || p.name || '').trim()).filter(Boolean)) : null;
    const faltan = (mapeoData?.piezas || []).filter(p => !mapeoValores[p] && (!_pv || _pv.has(p)));
    if (faltan.length) {
      setSelectedPiezaMapeo(faltan[0]);            // ir a la pieza que falta (queda resaltada)
      showError(`Faltan ${faltan.length} pieza(s) sin diseño: ${faltan.slice(0, 4).join(', ')}${faltan.length > 4 ? '…' : ''}. Asigná su diseño (arrastralo a la pieza en ROJO) para continuar.`);
      return true;
    }
    return false;
  };
  const arteSiguiente = () => {
    if (bloqueaPorSinDiseno()) return;
    const itemsDis = itemsArteDe(disenoActivo);   // se avanza por variable (o por molde entero)
    if (arteIdx < itemsDis.length - 1) { setArteIdx(arteIdx + 1); return; }
    // siguiente diseño que tenga algo que cargar
    const idx = disenosPedido.findIndex(d => d.id === disenoActivo);
    const siguiente = disenosPedido.slice(idx + 1).find(d => itemsArteDe(d.id).length);
    if (siguiente) { setDisenoActivo(siguiente.id); setArteIdx(0); }
    else if (todasArteCargadas) irAPlanillaDesdeArte();
  };

  // Empezar un pedido nuevo desde 0: limpia toda la selección y vuelve al paso 1.
  const reiniciarPedido = () => {
    if (!confirm('¿Empezar un pedido nuevo desde 0? Se borrará la selección actual.')) return;
    setMoldesSeleccionados([]);
    setTrabajosMulti([]);
    setArteCargado({});
    setMapeoData(null);
    setArteIdx(0);
    setTelaActiva(null);
    setDisenosPedido([]);
    setDisenoMoldes({});
    setDisenoVars({});
    setDisenoActivo('');
    setAsignDiseno('todos');
    setNuevoDisenoNombre('');
    setPerfilesArte({});
    setPerfilForzado(null);
    setPedidoPaso('moldes');
  };

  const showMsg = (txt) => {
    setMensajeInformativo(txt);
    setErrorInformativo('');
    setTimeout(() => setMensajeInformativo(prev => prev === txt ? '' : prev), 5000);
  };

  const showError = (txt) => {
    setErrorInformativo(txt);
    setMensajeInformativo('');
    setTimeout(() => setErrorInformativo(prev => prev === txt ? '' : prev), 7000);
  };

  const showWarn = (txt) => {
    setAdvertenciaInformativa(txt);
    setTimeout(() => setAdvertenciaInformativa(prev => prev === txt ? '' : prev), 10000);
  };

  // Aviso (no bloqueante) al subir el diseño: si la planilla cargó un dato que se
  // estampa (nombre/número) pero el diseño NO trae su capa, avisar que no se va a
  // estampar. Si la planilla no cargó nada en ese campo, no avisa nada.
  const avisarCapasFaltantes = (camposDetectados) => {
    const norm = (s) => (s || '').toString().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/-/g, ' ').replace(/\s+/g, ' ').trim();
    const detectadas = new Set((camposDetectados || []).map(norm));
    const persCols = (cols || []).filter(c => ['nombre', 'numero'].includes(c.role || 'none'));
    const faltan = persCols.filter(c => {
      const tieneDato = (filas || []).some(f => String(f[c.id] ?? '').trim() !== '');
      if (!tieneDato) return false;  // planilla vacía en este campo → no avisar
      return !(detectadas.has(norm(c.label)) || detectadas.has(norm(c.role)));  // el diseño no trae su capa
    }).map(c => c.label);
    if (faltan.length) {
      showWarn(`El diseño no tiene la capa de ${faltan.join(' ni ')}. Lo que cargaste en la planilla en ${faltan.length > 1 ? 'esos campos' : 'ese campo'} no se va a estampar.`);
    }
  };

  // Garments list helper
  const addPrenda = () => {
    const newRow = {};
    cols.forEach(c => {
      if (c.role === 'talle') newRow[c.id] = (estado?.talles?.[0] || 'M');
      else if (c.role === 'manga') newRow[c.id] = 'corta';
      else if (c.role === 'diseno') newRow[c.id] = ((disenosPedido.find(d => d.id === disenoActivo) || disenosPedido[0])?.nombre || 'Principal');   // fila nueva → el diseño PREPARADO en el Arte (no el 1º de la lista, que puede ser otro/vacío)
      else newRow[c.id] = '';
    });
    setFilas([...filas, newRow]);
  };

  // Agrega N filas de una (N = campo al lado del botón; default 1)
  const agregarFilas = () => {
    const n = Math.max(1, Math.min(500, parseInt(nFilasAgregar, 10) || 1));
    const nuevas = Array.from({ length: n }, () => _defaultRow());
    setFilas([...filas, ...nuevas]);
  };

  // ── Importar un archivo CSV a la planilla ────────────────────────────────
  // Vuelca las filas del CSV. En las columnas con opciones FIJAS (talle, diseño,
  // manga, desplegables) solo acepta valores que coincidan con lo predefinido;
  // si el valor no coincide, deja la celda VACÍA. Mapea columnas por encabezado
  // (nombre/rol) o, si no hay encabezado reconocible, por posición.
  const _parseCSV = (text) => {
    text = String(text || '').replace(/^﻿/, '');   // saca el BOM
    const primera = (text.split(/\r?\n/)[0] || '');
    const cnt = { ',': 0, ';': 0, '\t': 0 }; let qq = false;
    for (const ch of primera) { if (ch === '"') qq = !qq; else if (!qq && cnt[ch] != null) cnt[ch]++; }
    const delim = (cnt[';'] > cnt[','] && cnt[';'] >= cnt['\t']) ? ';' : (cnt['\t'] > cnt[','] ? '\t' : ',');
    const rows = []; let row = [], field = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) { if (ch === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; } else field += ch; }
      else if (ch === '"') q = true;
      else if (ch === delim) { row.push(field); field = ''; }
      else if (ch === '\n') { row.push(field); rows.push(row); row = []; field = ''; }
      else if (ch === '\r') { /* nada */ }
      else field += ch;
    }
    if (field !== '' || row.length) { row.push(field); rows.push(row); }
    return rows.filter(r => r.some(x => (x || '').trim() !== ''));
  };
  const _normTxt = (s) => (s == null ? '' : String(s)).trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const _opcionesDeCol = (c) => {   // devuelve la lista de valores válidos, o null si la columna es libre
    if (c.role === 'talle') { const t = estado?.talles || []; return t.length ? t : null; }
    if (c.role === 'diseno') { const d = disenosPedido.map(x => x.nombre); return d.length ? d : null; }
    const tipo = c.tipo || (c.role === 'manga' ? 'toggle' : 'texto');
    const opts = (c.opciones || '').split(',').map(s => s.trim()).filter(Boolean);
    if (tipo === 'desplegable') return opts.length ? opts : null;
    if (tipo === 'toggle' || c.role === 'manga') return opts.length >= 2 ? opts : (c.role === 'manga' ? ['corta', 'larga'] : ['A', 'B']);
    return null;   // nombre / número / texto: valor libre
  };
  const _defaultRow = () => { const r = {}; cols.forEach(c => {
    if (c.role === 'talle') r[c.id] = (estado?.talles?.[0] || 'M');
    else if (c.role === 'manga') r[c.id] = 'corta';
    else if (c.role === 'diseno') r[c.id] = ((disenosPedido.find(d => d.id === disenoActivo) || disenosPedido[0])?.nombre || 'Principal');
    else r[c.id] = '';
  }); return r; };
  const importarCSVTexto = (texto) => {
    const rows = _parseCSV(texto);
    if (!rows.length) { showError('El CSV está vacío.'); return; }
    const matchCol = (h) => cols.find(c => [c.label, c.id, c.role, (c.role === 'diseno' ? 'diseño' : null), (c.role === 'numero' ? 'número' : null)]
      .some(x => x && _normTxt(x) === _normTxt(h)));
    const headerMap = rows[0].map(h => matchCol(h) || null);
    const tieneHeader = headerMap.some(Boolean);
    const mapping = tieneHeader ? headerMap : rows[0].map((_, i) => cols[i] || null);
    const dataRows = tieneHeader ? rows.slice(1) : rows;
    // Armo cada fila; marco las celdas cuyo valor NO coincide con las opciones fijas (issues).
    const preview = dataRows.map(r => {
      const valores = _defaultRow();
      const issues = [];
      mapping.forEach((c, ci) => {
        if (!c) return;
        const raw = (r[ci] != null ? String(r[ci]) : '').trim();
        if (raw === '') return;
        const opts = _opcionesDeCol(c);
        if (opts) {   // columna con opciones fijas → validar
          const m = opts.find(o => _normTxt(o) === _normTxt(raw));
          if (m != null) valores[c.id] = m;
          else issues.push({ colId: c.id, label: c.label || c.id, raw, opciones: opts });   // no coincide → a resolver
        } else valores[c.id] = raw;
      });
      return { valores, issues };
    });
    if (!preview.length) { showError('El CSV no tenía filas de datos.'); return; }
    const conProblemas = preview.some(f => f.issues.length);
    if (conProblemas) {
      // Abro el modal de resolución (mostrar filas con valor incorrecto, elegir valor o no cargarla)
      setCsvFix({}); setCsvOmit({});
      setCsvImport({ filas: preview });
      return;
    }
    // Sin problemas → importar directo (reemplaza la planilla) con aviso in-app
    setFilas(preview.map(f => f.valores));
    showMsg(`Importadas ${preview.length} fila(s) del CSV.`);
  };
  // Confirmar la importación desde el modal de resolución de valores inválidos
  const aplicarImportCSV = () => {
    if (!csvImport) return;
    const finales = [];
    csvImport.filas.forEach((f, i) => {
      if (csvOmit[i]) return;                       // fila que el usuario decidió NO cargar
      const row = { ...f.valores };
      f.issues.forEach(iss => { row[iss.colId] = csvFix[`${i}:${iss.colId}`] || ''; });   // valor elegido (o vacío)
      finales.push(row);
    });
    setCsvImport(null); setCsvFix({}); setCsvOmit({});
    if (!finales.length) { showError('No se cargó ninguna fila (todas se omitieron).'); return; }
    setFilas(finales);
    showMsg(`Importadas ${finales.length} fila(s) del CSV.`);
  };
  const onImportCSVFile = (e) => {
    const file = e.target.files && e.target.files[0];
    e.target.value = '';   // permite volver a importar el mismo archivo
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => { try { importarCSVTexto(String(reader.result || '')); } catch (err) { showError('No se pudo leer el CSV: ' + (err.message || err)); } };
    reader.onerror = () => showError('No se pudo leer el archivo.');
    reader.readAsText(file);
  };

  const updateFila = (i, field, val) => {
    const next = [...filas];
    next[i][field] = val;
    setFilas(next);
  };

  // Navegación tipo planilla: Enter = baja (misma columna), Tab = derecha (misma fila,
  // salta a la fila siguiente al pasar la última columna). Shift+Tab = izquierda.
  const _focusCelda = (r, c) => {
    const el = document.querySelector(`[data-plc="${r}-${c}"]`);
    if (el) { el.focus(); try { el.select && el.select(); } catch (_e) { /* no-op */ } }
  };
  const navKeyPlanilla = (e, r, c) => {
    const nCols = cols.length, nFil = filas.length;
    if (e.key === 'Enter') {
      e.preventDefault();
      if (r + 1 < nFil) _focusCelda(r + 1, c);
    } else if (e.key === 'Tab') {
      e.preventDefault();
      if (e.shiftKey) {
        let nc = c - 1, nr = r;
        if (nc < 0) { nc = nCols - 1; nr = r - 1; }
        if (nr >= 0) _focusCelda(nr, nc);
      } else {
        let nc = c + 1, nr = r;
        if (nc >= nCols) { nc = 0; nr = r + 1; }
        if (nr < nFil) _focusCelda(nr, nc);
      }
    }
  };

  // Celdas con valor INVÁLIDO: columna con opciones fijas + valor que no coincide con ninguna.
  // Se usa para bloquear el paso siguiente (no se puede continuar con valores inexistentes).
  // Caracteres que SOPORTA la tipografía de personalización del/los diseño(s) del pedido.
  // Si el pedido tiene varios moldes, se intersecan (un caracter sirve si TODAS las fuentes lo tienen).
  useEffect(() => {
    if (pedidoPaso !== 'planilla') return;
    const ids = (moldesSeleccionados.length ? moldesSeleccionados : [productosCat.activo]).filter(Boolean);
    if (!ids.length) { setFuenteChars(null); return; }
    let cancelado = false;
    (async () => {
      try {
        const sets = [];
        for (const id of ids) {
          const r = await fetch(`/api/pedido/fuente_chars?producto_id=${encodeURIComponent(id)}`);
          const d = await r.json();
          if (d && d.ok && d.chars) sets.push(new Set([...d.chars]));
        }
        if (cancelado) return;
        if (!sets.length) { setFuenteChars(null); return; }
        let inter = sets[0];
        for (const s of sets.slice(1)) inter = new Set([...inter].filter(c => s.has(c)));
        setFuenteChars(inter);
      } catch (_e) { if (!cancelado) setFuenteChars(null); }
    })();
    return () => { cancelado = true; };
  }, [pedidoPaso, moldesSeleccionados.join(','), productosCat.activo]);

  // ¿La fuente NO tiene este caracter? (los espacios nunca se marcan)
  const faltaEnFuente = (ch) => !!fuenteChars && fuenteChars.size > 0 && String(ch).trim() !== '' && !fuenteChars.has(ch);
  // Texto TAL CUAL se ve/estampa en esa columna (el nombre se muestra en mayúsculas)
  const _textoCol = (c, v) => (c.role === 'nombre' ? String(v ?? '').toUpperCase() : String(v ?? ''));
  // ¿Es una columna de TEXTO LIBRE que se estampa? (talle/diseño/desplegables/toggles no)
  const _colEsTexto = (c) => {
    const tipo = c.tipo || (c.role === 'manga' ? 'toggle' : 'texto');
    return !(c.role === 'talle' || c.role === 'diseno' || tipo === 'desplegable' || tipo === 'toggle');
  };
  // Caracteres de TODA la planilla que la fuente no tiene (para el aviso de arriba)
  const faltantesFuente = (() => {
    if (!fuenteChars || !fuenteChars.size) return [];
    const out = new Set();
    filas.forEach(f => cols.forEach(c => {
      if (!_colEsTexto(c)) return;
      [..._textoCol(c, f[c.id])].forEach(ch => { if (faltaEnFuente(ch)) out.add(ch); });
    }));
    return [...out];
  })();

  const _normV = (s) => (s == null ? '' : String(s)).trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const planillaInvalidos = () => {
    const bad = [];
    filas.forEach((f, i) => {
      cols.forEach(c => {
        const opts = _opcionesDeCol(c);
        if (!opts || !opts.length) return;   // columna libre → no valida
        const v = String(f[c.id] ?? '').trim();
        if (v !== '' && !opts.some(o => _normV(o) === _normV(v))) bad.push({ i, label: c.label || c.id, v });
      });
    });
    return bad;
  };

  const removeFila = (i) => {
    const next = filas.filter((_, idx) => idx !== i);
    if (next.length) {
      setFilas(next);
    } else {
      const newRow = {};
      cols.forEach(c => {
        if (c.role === 'talle') newRow[c.id] = (estado?.talles?.[0] || 'M');
        else if (c.role === 'manga') newRow[c.id] = 'corta';
        else if (c.role === 'diseno') newRow[c.id] = ((disenosPedido.find(d => d.id === disenoActivo) || disenosPedido[0])?.nombre || 'Principal');   // fila nueva → el diseño PREPARADO en el Arte (no el 1º de la lista, que puede ser otro/vacío)
        else newRow[c.id] = '';
      });
      setFilas([newRow]);
    }
  };

  // Fill-handle de la planilla del pedido (estilo Excel/Sheets): al soltar el arrastre, copia el
  // valor de la celda origen a TODO el rectángulo seleccionado (vertical y horizontal), sea cual
  // sea el tipo de cada celda (texto, desplegable o botón). Ver [[PlanillaTester]].
  // Rango seleccionado (normalizado) y pertenencia de una celda.
  const plRango = () => {
    if (!plSel) return null;
    const e = plSelEnd || plSel;
    return { r0: Math.min(plSel.r, e.r), r1: Math.max(plSel.r, e.r), c0: Math.min(plSel.c, e.c), c1: Math.max(plSel.c, e.c) };
  };
  const plEnFill = (r, c) => {   // preview del rectángulo que se va a llenar mientras arrastrás
    const s = plFillSrcRef.current; if (!s || !plFill) return false;
    const R0 = Math.min(s.r0, plFill.r), R1 = Math.max(s.r1, plFill.r);
    const C0 = Math.min(s.c0, plFill.c), C1 = Math.max(s.c1, plFill.c);
    return r >= R0 && r <= R1 && c >= C0 && c <= C1;
  };
  // Relleno estilo Excel: si el origen es una progresión de NÚMEROS la continúa; si no,
  // repite los valores en el mismo orden hacia donde se arrastra.
  const _esNum = (s) => { const t = String(s).trim(); return t !== '' && Number.isFinite(Number(t)); };
  const _seq = (vals) => {   // {nums,d} si es progresión aritmética (len>=2 y todos números); si no null
    if (vals.length < 2 || !vals.every(_esNum)) return null;
    const nums = vals.map(v => Number(String(v).trim()));
    const d = nums[1] - nums[0];
    for (let i = 2; i < nums.length; i++) if (nums[i] - nums[i - 1] !== d) return null;
    return { nums, d };
  };
  const _valFill = (srcVals, j) => {   // valor para el offset j (0 = primer origen)
    const seq = _seq(srcVals);
    if (seq) { const raw = seq.nums[0] + seq.d * j; return Number.isInteger(raw) ? String(raw) : String(Math.round(raw * 1e6) / 1e6); }
    const len = srcVals.length, idx = ((j % len) + len) % len;
    return srcVals[idx];
  };
  const aplicarFill = (prev, src, target) => {
    const rows = prev.map(r => ({ ...r }));
    const vertical = target.r > src.r1 || target.r < src.r0;
    if (vertical) {
      const R0 = Math.min(src.r0, target.r), R1 = Math.max(src.r1, target.r);
      for (let c = src.c0; c <= src.c1; c++) {
        const col = cols[c]; if (!col) continue;
        const srcVals = []; for (let rr = src.r0; rr <= src.r1; rr++) srcVals.push(String(rows[rr]?.[col.id] ?? ''));
        for (let r = R0; r <= R1; r++) { if (r >= src.r0 && r <= src.r1) continue; if (rows[r]) rows[r][col.id] = _valFill(srcVals, r - src.r0); }
      }
    } else {
      const C0 = Math.min(src.c0, target.c), C1 = Math.max(src.c1, target.c);
      for (let r = src.r0; r <= src.r1; r++) {
        if (!rows[r]) continue;
        const srcVals = []; for (let cc = src.c0; cc <= src.c1; cc++) srcVals.push(String(rows[r]?.[cols[cc]?.id] ?? ''));
        for (let c = C0; c <= C1; c++) { if (c >= src.c0 && c <= src.c1) continue; if (cols[c]) rows[r][cols[c].id] = _valFill(srcVals, c - src.c0); }
      }
    }
    return rows;
  };
  useEffect(() => {
    const onUp = () => {
      if (plDragRef.current && plFill && plFillSrcRef.current) {
        const src = plFillSrcRef.current, target = plFill;
        setFilas(prev => aplicarFill(prev, src, target));
      }
      plDragRef.current = null; plFillSrcRef.current = null; plSelDragRef.current = false;
      setPlFill(null); setPlSelDrag(false);
    };
    window.addEventListener('mouseup', onUp);
    return () => window.removeEventListener('mouseup', onUp);
  }, [plFill, filas, cols, plSel, plSelEnd]);

  const loadExample = () => {
    const tallesDisponibles = estado?.talles?.length ? estado.talles : ["S", "M", "L", "XL"];
    const nombresEjemplo = ["FELIPE", "PIPOWSKI", "RODRIGUEZ", "DIEGO", "SILVA", "TECHERA"];
    
    const examples = Array.from({ length: 5 }).map((_, idx) => {
      const row = {};
      cols.forEach(c => {
        if (c.role === 'talle') {
          row[c.id] = tallesDisponibles[idx % tallesDisponibles.length];
        } else if (c.role === 'manga') {
          row[c.id] = idx % 2 === 0 ? 'corta' : 'larga';
        } else if (c.role === 'nombre') {
          row[c.id] = nombresEjemplo[idx % nombresEjemplo.length];
        } else if (c.role === 'numero') {
          row[c.id] = (idx * 5 + 3).toString();
        } else {
          row[c.id] = `Ejemplo ${idx + 1}`;
        }
      });
      return row;
    });
    setFilas(examples);
  };

  // PUERTA DE LOGIN: si el sistema de usuarios está activo y no hay sesión, se muestra el login y
  // NADA más. Mientras se consulta /yo no se pinta nada (evita el parpadeo login→app). Si la API
  // de usuarios no está viva (base caída), NO se traba el sistema: se deja pasar.
  if (!authListo) return <div style={{ minHeight: '100vh', background: 'var(--bg, #0a0d0f)' }} />;
  if (authOn && !yo) return <LoginScreen onLogin={(u) => { setYo(u); }} />;

  return (
    <div className="app-container">
      {/* Sidebar Panel */}
      {modoDisenador && (
        <aside className="sidebar">
          <div className="logo-section">
            <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
              <img src="/logo.svg" alt="USER PRO" style={{ width: 40, height: 40, flexShrink: 0, display: 'block' }} />
              <div>
                <h1 style={{ margin: 0 }}><span>USER</span> PRO</h1>
                <div className="logo-subtitle">Motor de Sublimación</div>
              </div>
            </div>
          </div>

          <nav className="nav-menu">
            <button 
              className={`nav-item ${activoTab === 'pedidos' ? 'active' : ''}`}
              onClick={() => {
                setActivoTab('pedidos');
                setAdminSubView('dashboard');
                setModoMiMolde(null);   // salir por el menú también sale del modo «mi molde»
              }}
            >
              <Icon name="pedidos" />
              Pedidos
            </button>
            <button 
              className={`nav-item ${activoTab === 'config' ? 'active' : ''}`}
              onClick={() => {
                setActivoTab('config');
                setAdminSubView('dashboard');
                setModoMiMolde(null);   // salir por el menú también sale del modo «mi molde»
              }}
            >
              <Icon name="config" />
              Configuración
            </button>
          </nav>

          <div className="sidebar-footer">
            {/* usuario logueado + cerrar sesión */}
            {yo && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 12, padding: '8px 10px',
                borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-light)' }}>
                <div style={{ width: 30, height: 30, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center',
                  justifyContent: 'center', background: 'rgba(0,243,255,0.12)', color: 'var(--accent)', fontWeight: 800, fontSize: 13 }}>
                  {(yo.nombre || yo.usuario).slice(0, 1).toUpperCase()}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{yo.nombre}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{(yo.roles || []).join(', ') || yo.usuario}</div>
                </div>
                <button type="button" onClick={cerrarSesion} title="Cerrar sesión"
                  style={{ flexShrink: 0, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 15, padding: 4 }}>⏻</button>
              </div>
            )}
            <button
              className="btn ghost"
              style={{
                width: '100%',
                padding: '8px 12px',
                fontSize: '12.5px',
                border: '1px solid var(--border-light)',
                borderRadius: '8px',
                color: 'var(--cmyk-cyan)',
                borderColor: 'var(--cmyk-cyan)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginBottom: '16px',
                cursor: 'pointer',
                fontWeight: 600,
                transition: 'var(--transition-smooth)'
              }}
              onClick={() => navegarA('/')}
            >
              ⬅ Panel Operario
            </button>
            
            <div className="connection-badge">
              <div className={`status-dot ${!estado ? 'error' : ''}`}></div>
              <span>{estado ? "Servidor Activo" : "Sin Conexión"}</span>
            </div>
            {activoProdDetalle && (
              <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
                Activo: <b style={{ color: 'var(--accent)' }}>{activoProdDetalle.nombre}</b>
              </div>
            )}
          </div>
        </aside>
      )}

      {/* Main Panel Content */}
      <main className="main-content">
        
        {/* Operator Top Header Bar */}
        {!modoDisenador && (
          <header style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '16px 24px',
            borderBottom: '1px solid var(--border-light)',
            backgroundColor: 'rgba(10, 10, 12, 0.4)',
            backdropFilter: 'blur(20px)',
            marginBottom: '20px',
            borderRadius: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <img src="/logo.svg" alt="USER PRO" style={{ width: 34, height: 34, flexShrink: 0, display: 'block' }} />
              <h1 style={{ fontSize: '18px', fontWeight: 800, margin: 0 }}>
                <span style={{ color: 'var(--cmyk-cyan)', textShadow: '0 0 12px var(--cmyk-cyan)' }}>USER</span> PRO
              </h1>
              <span style={{
                fontSize: '10px',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                borderLeft: '1px solid var(--border-light)',
                paddingLeft: '12px'
              }}>
                Panel de Producción
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div className="connection-badge" style={{ margin: 0 }}>
                <div className={`status-dot ${!estado ? 'error' : ''}`}></div>
                <span style={{ fontSize: '12px' }}>{estado ? "Servidor Activo" : "Sin Conexión"}</span>
              </div>
            </div>
          </header>
        )}
        
        {/* Overlay "cargando" bloqueante (subida/procesamiento de molde, DXF grande, etc.) */}
        {procesando && createPortal(
          <div style={{ position: 'fixed', inset: 0, zIndex: 10050, background: 'rgba(2,6,12,0.82)', backdropFilter: 'blur(4px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 18 }}>
            <div style={{ width: 46, height: 46, border: '4px solid rgba(255,255,255,0.15)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'ldspin 0.8s linear infinite' }} />
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 600, maxWidth: 440, textAlign: 'center', lineHeight: 1.5, padding: '0 20px' }}>{procesando}</div>
            <style>{`@keyframes ldspin{to{transform:rotate(360deg)}}`}</style>
          </div>,
          document.body
        )}

        {/* ── Ventana: nombres puestos (renombrar / eliminar registro / quitar piezas) ── */}
        {modalNombres && createPortal((() => {
          const grupos = []; const map = {};
          (etqData?.piezas || []).forEach(pz => {
            const nm = etqNombres[pz.idx];
            if (!nm) return;
            const g = nombreGenerico(nm);
            if (!map[g]) { map[g] = { nombre: g, items: [] }; grupos.push(map[g]); }
            map[g].items.push({ idx: pz.idx, nombre: nm });
          });
          grupos.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
          const totalPiezas = grupos.reduce((a, g) => a + g.items.length, 0);
          const cerrar = () => { setModalNombres(false); setRenombrarBuf(null); setResaltarNombre(null); };
          return (
            /* Panel FLOTANTE a la derecha: no tapa la pantalla (pointerEvents:none en el wrapper)
               → el visor de la izquierda sigue 100% usable (ver, zoom, arrastrar) con esto abierto. */
            <div style={{ position: 'fixed', top: 70, right: 18, bottom: 18, width: 'min(430px, 46vw)', zIndex: 10070, display: 'flex', alignItems: 'stretch', pointerEvents: 'none' }}>
              <div style={{ width: '100%', maxHeight: '100%', background: '#0c1322', border: '1px solid var(--accent)', borderRadius: 14, display: 'flex', flexDirection: 'column', overflow: 'hidden', boxShadow: '0 18px 60px rgba(0,0,0,0.65)', pointerEvents: 'auto' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '13px 16px', borderBottom: '1px solid var(--border-light)' }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>Nombres puestos</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{grupos.length} nombre{grupos.length === 1 ? '' : 's'} · {totalPiezas} pieza{totalPiezas === 1 ? '' : 's'} — tocá un nombre para <b>editar sus piezas en el visor</b></div>
                  </div>
                  <button type="button" onClick={cerrar} style={{ width: 28, height: 28, borderRadius: 8, border: '1px solid var(--border-light)', background: 'transparent', color: '#d4d4d8', cursor: 'pointer', fontSize: 14, flexShrink: 0 }}>✕</button>
                </div>
                <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 7 }}>
                  {grupos.length === 0 && <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '14px 0' }}>Todavía no hay piezas nombradas.</div>}
                  {grupos.map(g => {
                    const editando = renombrarBuf && renombrarBuf.gen === g.nombre;
                    const editarEnVisor = () => { setEditandoNombre(g.nombre); setSelNombrar(new Set()); setEtqNombreInput(''); setModalNombres(false); setResaltarNombre(null); };
                    return (
                      <div key={g.nombre} style={{ border: '1px solid var(--border-light)', borderRadius: 10, overflow: 'hidden' }}>
                        <div onMouseEnter={() => setResaltarNombre(g.nombre)} onMouseLeave={() => setResaltarNombre(r => r === g.nombre ? null : r)} onClick={() => { if (!editando) editarEnVisor(); }} title="Editar sus piezas en el visor" style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 10px', cursor: 'pointer', background: 'rgba(255,255,255,0.02)' }}>
                          {editando ? (<>
                            <input autoFocus value={renombrarBuf.valor} onClick={(e) => e.stopPropagation()} onChange={(e) => setRenombrarBuf({ gen: g.nombre, valor: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') { renombrarGrupoNombres(g.nombre, renombrarBuf.valor); setRenombrarBuf(null); } else if (e.key === 'Escape') setRenombrarBuf(null); }} style={{ flex: 1, padding: '5px 9px', fontSize: 12.5, borderRadius: 8, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--accent)', color: '#fff', outline: 'none' }} />
                            <button type="button" title="Aplicar" onClick={(e) => { e.stopPropagation(); renombrarGrupoNombres(g.nombre, renombrarBuf.valor); setRenombrarBuf(null); }} style={{ width: 26, height: 26, borderRadius: 7, border: '1px solid var(--success)', background: 'rgba(16,185,129,0.12)', color: 'var(--success)', cursor: 'pointer', fontSize: 13, flexShrink: 0 }}>✓</button>
                            <button type="button" title="Cancelar" onClick={(e) => { e.stopPropagation(); setRenombrarBuf(null); }} style={{ width: 26, height: 26, borderRadius: 7, border: '1px solid var(--border-light)', background: 'transparent', color: '#d4d4d8', cursor: 'pointer', fontSize: 12, flexShrink: 0 }}>✕</button>
                          </>) : (<>
                            <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.nombre}</span>
                            <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>{g.items.length} pza{g.items.length === 1 ? '' : 's'}</span>
                            <button type="button" title="Editar sus piezas en el visor" onClick={(e) => { e.stopPropagation(); editarEnVisor(); }} className="btn ghost" style={{ fontSize: 11, padding: '3px 9px', flexShrink: 0 }}>Editar piezas</button>
                            <button type="button" title="Renombrar" onClick={(e) => { e.stopPropagation(); setRenombrarBuf({ gen: g.nombre, valor: g.nombre }); }} style={{ width: 26, height: 26, borderRadius: 7, border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 12, flexShrink: 0 }}>✎</button>
                            <button type="button" title="Eliminar este registro (las piezas quedan sin nombre)" onClick={(e) => { e.stopPropagation(); eliminarGrupoNombres(g.nombre); }} style={{ width: 26, height: 26, borderRadius: 7, border: '1px solid rgba(239,68,68,0.4)', background: 'transparent', color: '#f87171', cursor: 'pointer', fontSize: 12, flexShrink: 0 }}>🗑</button>
                          </>)}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ display: 'flex', gap: 8, padding: '12px 16px', borderTop: '1px solid var(--border-light)' }}>
                  <button type="button" className="btn primary" style={{ flex: 1, fontSize: 12.5 }} disabled={guardandoNoms} onClick={async () => { setGuardandoNoms(true); try { await guardarEtiquetas(); } finally { setGuardandoNoms(false); } }}>{guardandoNoms ? 'Guardando…' : 'Guardar cambios'}</button>
                  <button type="button" className="btn" style={{ flex: 1, fontSize: 12.5 }} onClick={cerrar}>Cerrar</button>
                </div>
              </div>
            </div>
          );
        })(), document.body)}

        {/* Alerts & Messages — toasts flotantes: no ocupan lugar en el layout */}
        {(mensajeInformativo || errorInformativo || advertenciaInformativa) && createPortal(
          <div style={{ position: 'fixed', top: 24, right: 24, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 'min(380px, calc(100vw - 48px))', pointerEvents: 'none' }}>
            {advertenciaInformativa && (
              <div className="animate-fade" style={{ backgroundColor: 'rgba(180,120,0,0.16)', border: '1px solid var(--warning, #e0a020)', color: 'var(--warning, #e0a020)', padding: '12px 18px', fontSize: 13.5, display: 'flex', alignItems: 'center', gap: 10, borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,0.45)', backdropFilter: 'blur(8px)', pointerEvents: 'auto' }}>
                <Icon name="alert" style={{ width: 18, height: 18, flexShrink: 0 }} />
                <span>{advertenciaInformativa}</span>
                <button onClick={() => setAdvertenciaInformativa('')} style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: 16, lineHeight: 1, padding: 0, opacity: 0.7 }} title="Cerrar">×</button>
              </div>
            )}
            {mensajeInformativo && (
              <div className="animate-fade" style={{ backgroundColor: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)', padding: '12px 18px', fontSize: 13.5, display: 'flex', alignItems: 'center', gap: 10, borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,0.45)', backdropFilter: 'blur(8px)' }}>
                <Icon name="check" className="status-dot" style={{ background: 'none', strokeWidth: 3, flexShrink: 0 }} />
                <span>{mensajeInformativo}</span>
              </div>
            )}
            {errorInformativo && (
              <div className="animate-fade" style={{ backgroundColor: 'var(--error-bg)', border: '1px solid var(--error)', color: 'var(--error)', padding: '12px 18px', fontSize: 13.5, display: 'flex', alignItems: 'center', gap: 10, borderRadius: 12, boxShadow: '0 10px 30px rgba(0,0,0,0.45)', backdropFilter: 'blur(8px)' }}>
                <Icon name="alert" style={{ width: 18, height: 18, flexShrink: 0 }} />
                <span>{errorInformativo}</span>
              </div>
            )}
          </div>,
          document.body
        )}

        {/* Resolver valores del CSV que no coinciden con las opciones (importación de planilla) */}
        <Modal open={!!csvImport} onClose={() => { setCsvImport(null); setCsvFix({}); setCsvOmit({}); }}
          titulo="Revisá los valores del CSV"
          subtitulo="Estas filas traen valores que no coinciden con las opciones. Elegí el valor correcto o marcá que no se cargue esa fila."
          maxWidth={720}>
          {csvImport && (() => {
            const problemRows = csvImport.filas.map((f, i) => ({ f, i })).filter(x => x.f.issues.length);
            const totalCargar = csvImport.filas.filter((_, i) => !csvOmit[i]).length;
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
                  {problemRows.length} fila(s) con valores a revisar. Se importarán <b style={{ color: 'var(--accent)' }}>{totalCargar}</b> de {csvImport.filas.length} fila(s) y se reemplazará la planilla actual.
                </div>
                {problemRows.map(({ f, i }) => {
                  const omit = !!csvOmit[i];
                  return (
                    <div key={i} style={{ border: '1px solid var(--border-light)', borderRadius: 10, padding: 12, opacity: omit ? 0.5 : 1, background: 'rgba(255,255,255,0.02)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontWeight: 800, fontSize: 13.5, letterSpacing: 0.2 }}>Fila {i + 1}</span>
                        <button type="button" onClick={() => setCsvOmit(o => ({ ...o, [i]: !omit }))}
                          style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none', cursor: 'pointer', color: omit ? 'var(--accent)' : 'var(--text-secondary)', fontSize: 12, fontWeight: 600, padding: 0 }}>
                          <span style={{ width: 34, height: 20, borderRadius: 999, background: omit ? 'var(--accent)' : 'rgba(255,255,255,0.16)', position: 'relative', transition: 'background .15s', flexShrink: 0 }}>
                            <span style={{ position: 'absolute', top: 2, left: omit ? 16 : 2, width: 16, height: 16, borderRadius: '50%', background: '#fff', transition: 'left .15s', boxShadow: '0 1px 3px rgba(0,0,0,0.4)' }} />
                          </span>
                          No cargar esta fila
                        </button>
                      </div>
                      {/* contexto: el resto de los datos de la fila (los válidos) */}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: f.issues.length ? 12 : 0 }}>
                        {cols.map(c => {
                          if (f.issues.some(iss => iss.colId === c.id)) return null;
                          const v = f.valores[c.id];
                          return v ? <span key={c.id} style={{ fontSize: 11.5, color: '#fff', background: 'rgba(255,255,255,0.045)', border: '1px solid var(--border-light)', borderRadius: 999, padding: '3px 11px', display: 'inline-flex', gap: 6 }}><span style={{ color: 'var(--text-muted)' }}>{c.label}</span>{v}</span> : null;
                        })}
                      </div>
                      {/* celdas inválidas: valor incorrecto marcado + selector de valor válido */}
                      {f.issues.map(iss => {
                        const k = `${i}:${iss.colId}`;
                        return (
                          <div key={iss.colId} style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: 12.5, minWidth: 78, fontWeight: 700 }}>{iss.label}</span>
                            <span style={{ fontSize: 11.5, fontWeight: 700, color: '#ff9a9a', background: 'rgba(255,70,70,0.13)', border: '1px solid rgba(255,70,70,0.4)', borderRadius: 999, padding: '3px 10px', whiteSpace: 'nowrap' }}>«{iss.raw}» ✕</span>
                            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>→</span>
                            {[...iss.opciones, ''].map(o => {
                              const sel = (csvFix[k] || '') === o;
                              const vacio = o === '';
                              return (
                                <button key={o || '__vacio'} type="button" disabled={omit} onClick={() => setCsvFix(fx => ({ ...fx, [k]: o }))}
                                  style={{ padding: '5px 13px', borderRadius: 999, fontSize: 12.5, fontWeight: 700, cursor: omit ? 'default' : 'pointer', transition: 'all .15s',
                                    border: sel ? '1px solid var(--accent)' : '1px solid var(--border-light)',
                                    background: sel ? 'var(--accent)' : 'rgba(255,255,255,0.03)',
                                    color: sel ? '#000' : (vacio ? 'var(--text-muted)' : 'var(--text-secondary)'),
                                    fontStyle: vacio ? 'italic' : 'normal', opacity: omit ? 0.5 : 1 }}>
                                  {vacio ? 'vacío' : o}
                                </button>
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
                <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 6 }}>
                  <button className="btn ghost" style={{ padding: '8px 16px', fontSize: 12.5 }} onClick={() => { setCsvImport(null); setCsvFix({}); setCsvOmit({}); }}>Cancelar</button>
                  <button className="btn primary" style={{ padding: '8px 16px', fontSize: 12.5 }} onClick={aplicarImportCSV}>Importar {totalCargar} fila(s)</button>
                </div>
              </div>
            );
          })()}
        </Modal>

        {/* Aviso de perfil de color al cargar un diseño (ventana emergente centrada) */}
        <Modal open={!!perfilAviso} onClose={() => setPerfilAviso(null)} titulo="Perfil de color del diseño" maxWidth={460} centrado>
          {perfilAviso && perfilAviso.estado === 'detectando' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '6px 0' }}>
              <span className="perfil-spinner" style={{ width: 26, height: 26, borderRadius: '50%', flexShrink: 0, border: '3px solid rgba(0,216,245,0.25)', borderTopColor: 'var(--accent)' }} />
              <div style={{ fontSize: 14, fontWeight: 600 }}>Detectando perfil…</div>
            </div>
          )}
          {perfilAviso && perfilAviso.estado !== 'detectando' && (() => {
            const est = perfilAviso.estado;
            const col = est === 'ok' ? 'var(--success)' : 'var(--warning, #e0a020)';
            const fila = (lbl, val, fuerte) => (
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 13, padding: '8px 0', borderBottom: '1px solid var(--border-light)' }}>
                <span style={{ color: 'var(--text-muted)' }}>{lbl}</span>
                <b style={{ color: fuerte ? 'var(--accent)' : '#fff', textAlign: 'right' }}>{val}</b>
              </div>
            );
            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
                  <span style={{ width: 46, height: 46, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: col + '22', border: '1px solid ' + col, boxShadow: '0 0 18px ' + col + '44' }}>
                    <Icon name={est === 'ok' ? 'check' : 'alert'} style={{ width: 22, height: 22, color: col }} />
                  </span>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 15.5, color: col }}>{est === 'ok' ? 'Perfil correcto' : est === 'sin_perfil' ? 'El diseño viene sin perfil' : 'Perfil distinto al predeterminado'}</div>
                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Espacio de color: {perfilAviso.espacio}</div>
                  </div>
                </div>
                <div style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{perfilAviso.mensaje}</div>
                <div>
                  {perfilAviso.incrustado && fila('Perfil del diseño', perfilAviso.incrustado)}
                  {fila(perfilAviso.estado === 'sin_perfil' ? 'Se asignará' : 'Predeterminado', perfilAviso.predeterminado, true)}
                </div>
                <button className="btn primary" onClick={() => setPerfilAviso(null)} style={{ alignSelf: 'flex-end', padding: '9px 20px' }}>Entendido</button>
              </div>
            );
          })()}
        </Modal>

        {/* Unificar perfil: si los diseños tienen perfiles distintos, elegir a cuál transformar todo */}
        <Modal open={!!perfilUnificar} onClose={() => setPerfilUnificar(null)} titulo="Tus diseños tienen perfiles distintos" maxWidth={480} centrado>
          {perfilUnificar && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Para exportar, todos los diseños deben ir con <b style={{ color: '#fff' }}>un mismo perfil</b>. Elegí a cuál unificar:
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {perfilUnificar.nombres.map(nom => {
                  const prof = (perfilesData?.perfiles || []).find(p => p.nombre === nom);
                  const cols = prof?.colores || [];
                  return (
                    <button key={nom} type="button" onClick={() => elegirPerfilUnificado(nom)}
                      style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '11px 13px', borderRadius: 11, cursor: 'pointer', textAlign: 'left', transition: 'all .15s',
                        border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)' }}>
                      {cols.length > 0 && <span style={{ display: 'flex', width: 44, height: 18, borderRadius: 4, overflow: 'hidden', flexShrink: 0, boxShadow: '0 0 0 1px rgba(255,255,255,0.12)' }}>{cols.map((c, i) => <span key={i} style={{ flex: 1, background: c }} />)}</span>}
                      <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{nom}</span>
                      <span style={{ fontSize: 16, color: 'var(--accent)' }}>→</span>
                    </button>
                  );
                })}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontSize: 12.5, color: 'var(--warning, #e0a020)', background: 'rgba(180,120,0,0.10)', border: '1px solid var(--warning, #e0a020)', borderRadius: 9, padding: '10px 12px' }}>
                <Icon name="alert" style={{ width: 16, height: 16, flexShrink: 0 }} />
                <span>Si reemplazás el perfil, podés tener <b>variación en los colores</b>.</span>
              </div>
            </div>
          )}
        </Modal>

        {/* Tab 1: Pedidos */}
        {activoTab === 'pedidos' && (
          <div className="panel animate-fade" style={['moldes', 'arte', 'planilla'].includes(pedidoPaso) ? { display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 } : {}}>
            {/* Título + pasos en UNA fila */}
            {(() => {
              const pasos = [
                { k: 'moldes', label: 'Diseños' }, { k: 'arte', label: 'Arte' },
                { k: 'planilla', label: 'Planilla' }, { k: 'resultados', label: 'Tizadas' },
              ];
              const idx = pasos.findIndex(p => p.k === pedidoPaso);
              return (
                <div style={{ display: 'flex', alignItems: 'center', gap: 24, margin: '0 0 14px', flexWrap: 'wrap', rowGap: 10, flexShrink: 0 }}>
                  <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, whiteSpace: 'nowrap', letterSpacing: '-0.01em' }}>Panel de Pedidos</h2>
                  <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', rowGap: 8 }}>
                  {pasos.map((p, i) => {
                    const done = i < idx, cur = i === idx;
                    return (
                      <div key={p.k} style={{ display: 'flex', alignItems: 'center' }}>
                        <span style={{ width: 23, height: 23, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11.5, fontWeight: 700,
                          background: cur ? 'var(--accent)' : done ? 'rgba(0,216,245,0.18)' : 'rgba(255,255,255,0.06)',
                          color: cur ? '#000' : done ? 'var(--accent)' : 'var(--text-muted)', border: (done || cur) ? '1px solid var(--accent)' : '1px solid var(--border-light)' }}>
                          {done ? '✓' : i + 1}
                        </span>
                        <span style={{ fontSize: 12.5, marginLeft: 8, fontWeight: cur ? 700 : 500, color: cur ? '#fff' : done ? 'var(--text-secondary)' : 'var(--text-muted)' }}>{p.label}</span>
                        {i < pasos.length - 1 && <div style={{ width: 30, height: 2, margin: '0 12px', background: i < idx ? 'var(--accent)' : 'var(--border-light)' }} />}
                      </div>
                    );
                  })}
                  </div>
                </div>
              );
            })()}

            {/* Paso 1 · Escribir diseños + asignar moldes (columna de alto fijo, sin scroll de página) */}
            {pedidoPaso === 'moldes' && !mapeandoOperario && (
              <div className="animate-fade" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                {/* Cabecera fija: escribir diseño + chips */}
                <div style={{ flexShrink: 0 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ position: 'relative', flex: '1 1 260px', maxWidth: 340 }}>
                      <Icon name="edit" style={{ width: 14, height: 14, position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
                      <input value={nuevoDisenoNombre} onChange={(e) => setNuevoDisenoNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') agregarDisenoPedido(); }}
                        placeholder="Escribí un diseño y Enter"
                        style={{ width: '100%', height: 38, padding: '0 12px 0 34px', borderRadius: 9, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none', fontSize: 13.5 }} />
                    </div>
                    <button className="btn primary" onClick={agregarDisenoPedido} disabled={!nuevoDisenoNombre.trim()} style={{ padding: '9px 14px', borderRadius: 9, display: 'flex', alignItems: 'center', gap: 5, fontSize: 13 }}>
                      <Icon name="plus" style={{ width: 13, height: 13 }} /> Diseño
                    </button>
                  </div>
                  {disenosPedido.length > 0 && (
                    <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 11, alignItems: 'center' }}>
                      <button type="button" onClick={() => setAsignDiseno('todos')}
                        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 999, cursor: 'pointer', fontSize: 12.5, fontWeight: 700, transition: 'all .18s',
                          border: asignDiseno === 'todos' ? '1.5px solid var(--accent)' : '1px solid var(--border-light)', background: asignDiseno === 'todos' ? 'rgba(0,216,245,0.14)' : 'rgba(255,255,255,0.03)', color: asignDiseno === 'todos' ? 'var(--accent)' : 'var(--text-secondary)' }}>
                        <Icon name="productos" style={{ width: 13, height: 13 }} /> Todos
                      </button>
                      {disenosPedido.map(d => {
                        const on = asignDiseno === d.id, col = colorDeDiseno(d.id), n = moldesDeDiseno(d.id).length;
                        return (
                          <div key={d.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                            <button type="button" onClick={() => setAsignDiseno(d.id)}
                              style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '6px 12px', borderRadius: 999, cursor: 'pointer', fontSize: 12.5, fontWeight: 700, transition: 'all .18s',
                                border: on ? `1.5px solid ${col}` : '1px solid var(--border-light)', background: on ? `${col}22` : 'rgba(255,255,255,0.03)', color: on ? '#fff' : 'var(--text-secondary)', boxShadow: on ? `0 0 14px ${col}33` : 'none' }}>
                              <span style={{ width: 8, height: 8, borderRadius: '50%', background: col, flexShrink: 0 }} />
                              {d.nombre}
                              {n > 0 && <span style={{ fontSize: 10.5, fontWeight: 800, color: col }}>{n}</span>}
                            </button>
                            <button type="button" title="Quitar diseño" onClick={() => quitarDisenoPedido(d.id)}
                              style={{ width: 22, height: 22, borderRadius: '50%', border: 'none', background: 'rgba(255,255,255,0.04)', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Pestañas: el catálogo compartido vs. lo que subió este usuario */}
                {(() => {
                  const nMios = productosCat.productos.filter(p => p.propio).length;
                  const tabs = [{ k: 'catalogo', n: 'Catálogo', c: varsCatalogo.length }, { k: 'mios', n: 'Mis artículos', c: nMios }];
                  return (
                    <div style={{ flexShrink: 0, display: 'flex', gap: 6, marginTop: 14, background: 'rgba(255,255,255,0.03)', padding: 4, borderRadius: 10, alignSelf: 'flex-start' }}>
                      {tabs.map(t => (
                        <button key={t.k} type="button" onClick={() => setPedidoTabMoldes(t.k)}
                          style={{ padding: '7px 16px', borderRadius: 8, fontSize: 12.5, fontWeight: 700, cursor: 'pointer', border: 'none', display: 'flex', alignItems: 'center', gap: 7,
                            background: pedidoTabMoldes === t.k ? 'var(--accent)' : 'transparent', color: pedidoTabMoldes === t.k ? '#04222b' : 'var(--text-secondary)' }}>
                          {t.n}
                          <span style={{ fontSize: 10.5, fontWeight: 800, opacity: 0.75 }}>{t.c}</span>
                        </button>
                      ))}
                    </div>
                  );
                })()}

                {/* Cuerpo: grilla de moldes (SIEMPRE visible, aunque no haya diseños) */}
                <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', marginTop: 12, paddingRight: 2 }}>
                  {disenosPedido.length === 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-light)', borderRadius: 10, padding: '9px 12px', marginBottom: 12 }}>
                      <Icon name="edit" style={{ width: 14, height: 14, opacity: 0.6, flexShrink: 0 }} />
                      Escribí un diseño arriba y después tocá las variables que van en él.
                    </div>
                  )}
                  {pedidoTabMoldes === 'catalogo' && varsCatalogo.length === 0 && (
                    <div style={{ fontSize: 12.5, color: 'var(--text-muted)', padding: '12px 0' }}>No hay variables creadas. Armalas en <b>Configuración › Variables</b>.</div>
                  )}

                  {/* ── MIS ARTÍCULOS: los moldes que subió este usuario. No tienen Variables
                      (ese paso se les recorta), así que se eligen ENTEROS: el motor genera
                      todas sus piezas. ── */}
                  {pedidoTabMoldes === 'mios' && (() => {
                    const mios = productosCat.productos.filter(p => p.propio);
                    return (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(158px, 1fr))', gap: 11 }}>
                        {mios.map(p => {
                          const susDisenos = disenosPedido.filter(d => (disenoMoldes[d.id] || []).includes(p.id));
                          const enActivo = asignDiseno === 'todos'
                            ? (disenosPedido.length > 0 && disenosPedido.every(d => (disenoMoldes[d.id] || []).includes(p.id)))
                            : (disenoMoldes[asignDiseno] || []).includes(p.id);
                          const colAct = asignDiseno === 'todos' ? 'var(--accent)' : colorDeDiseno(asignDiseno);
                          return (
                            <div key={p.id}
                              style={{ position: 'relative', textAlign: 'left', padding: 10, borderRadius: 12, transition: 'all .18s',
                                border: enActivo ? `1.5px solid ${colAct}` : '1px solid var(--border-light)',
                                background: enActivo ? `${colAct === 'var(--accent)' ? 'rgba(0,216,245,0.08)' : colAct + '14'}` : 'rgba(255,255,255,0.02)',
                                boxShadow: enActivo ? `0 0 16px ${colAct === 'var(--accent)' ? 'rgba(0,216,245,0.16)' : colAct + '2e'}` : 'none' }}>
                              <button type="button" onClick={() => toggleMoldeEnDiseno(p.id)} title={p.plantilla ? 'Usar este artículo en el diseño' : 'Todavía no tiene el molde procesado'}
                                style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'inherit' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 7 }}>
                                  <span style={{ fontWeight: 700, fontSize: 12.5, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.nombre}</span>
                                  <span style={{ width: 19, height: 19, borderRadius: '50%', border: enActivo ? 'none' : '1.5px solid var(--border-light)', background: enActivo ? colAct : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'all .18s' }}>
                                    {enActivo && <Icon name="check" style={{ width: 11, height: 11, color: '#000', strokeWidth: 3 }} />}
                                  </span>
                                </div>
                                <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: 6 }}>
                                  <MoldePreviewSVG id={p.id} height={64} color={enActivo ? colAct : 'rgba(255,255,255,0.5)'} />
                                </div>
                                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 7, minHeight: 15, alignItems: 'center' }}>
                                  <span style={{ fontSize: 10, fontWeight: 700, color: p.plantilla ? 'var(--success)' : 'var(--warning)' }}>{p.plantilla ? 'Molde OK' : 'Sin molde'}</span>
                                  {/* Con dos artículos del MISMO nombre la tarjeta es idéntica y no
                                      hay forma de saber en cuál se venía trabajando: se muestra la
                                      fecha sólo en ese caso (si no, es ruido). */}
                                  {mios.filter(x => (x.nombre || '') === (p.nombre || '')).length > 1 && p.creado ? (
                                    <span title="Fecha en que se creó este artículo" style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                                      {new Date(p.creado * 1000).toLocaleString('es-UY', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                                    </span>
                                  ) : null}
                                  {susDisenos.map(d => (
                                    <span key={d.id} title={d.nombre} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 700, color: colorDeDiseno(d.id), background: colorDeDiseno(d.id) + '1c', padding: '1px 6px', borderRadius: 999 }}>
                                      <span style={{ width: 5, height: 5, borderRadius: '50%', background: colorDeDiseno(d.id) }} />{d.nombre}
                                    </span>
                                  ))}
                                </div>
                              </button>
                              <div style={{ display: 'flex', gap: 5, marginTop: 8 }}>
                                <button type="button" className="btn ghost" style={{ flex: 1, fontSize: 11, padding: '5px 8px' }}
                                  onClick={() => abrirConfigMiMolde(p.id)}>
                                  ⚙ Configurar
                                </button>
                                {/* Eliminar el artículo propio: con modal propio, nunca `confirm()`
                                    del navegador (el sistema usa sus propios avisos). */}
                                <button type="button" className="btn ghost" title="Eliminar este artículo"
                                  style={{ fontSize: 11, padding: '5px 9px', color: 'var(--danger, #ff5a6e)' }}
                                  onClick={(e) => { e.stopPropagation(); setBorrarArt(p); }}>
                                  🗑
                                </button>
                              </div>
                            </div>
                          );
                        })}
                        {/* Tarjeta "+" para sumar otro artículo propio */}
                        <button type="button" onClick={() => { setSubirMoldeNombre(''); setSubirMoldeFile(null); setSubirMoldeOpen(true); }}
                          style={{ minHeight: 150, borderRadius: 12, border: '1.5px dashed var(--border-light)', background: 'rgba(255,255,255,0.02)', color: 'var(--text-secondary)', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, fontSize: 12.5, fontWeight: 700 }}>
                          <Icon name="plus" style={{ width: 18, height: 18 }} />
                          Subir mi propio molde
                        </button>
                      </div>
                    );
                  })()}

                  <div style={{ display: pedidoTabMoldes === 'catalogo' ? 'grid' : 'none', gridTemplateColumns: 'repeat(auto-fill, minmax(158px, 1fr))', gap: 11 }}>
                      {varsCatalogo.map(v => {
                        const susDisenos = disenosPedido.filter(d => varsDeDiseno(d.id).includes(v.clave));
                        const enActivo = asignDiseno === 'todos' ? (disenosPedido.length > 0 && disenosPedido.every(d => varsDeDiseno(d.id).includes(v.clave))) : varsDeDiseno(asignDiseno).includes(v.clave);
                        const tplBase = variablesPlanilla.length ? variablesPlanilla[0].planilla : v.planilla;
                        const distintaPlanilla = variablesPlanilla.length > 0 && !variablesPlanilla.some(x => x.clave === v.clave) && v.planilla !== tplBase;
                        const nPz = (v.valores || []).filter(x => x.pieza_idx != null).length;
                        const colAct = asignDiseno === 'todos' ? 'var(--accent)' : colorDeDiseno(asignDiseno);
                        return (
                          <button key={v.clave} type="button" disabled={distintaPlanilla} onClick={() => toggleVarEnDiseno(v.clave)}
                            title={distintaPlanilla ? 'Usa otra planilla — no se puede combinar' : `${v.moldeNombre} · ${nPz} pza${nPz === 1 ? '' : 's'}`}
                            style={{ textAlign: 'left', cursor: distintaPlanilla ? 'not-allowed' : 'pointer', padding: 10, borderRadius: 12, transition: 'all .18s',
                              border: enActivo ? `1.5px solid ${colAct}` : '1px solid var(--border-light)',
                              background: enActivo ? `${colAct === 'var(--accent)' ? 'rgba(0,216,245,0.08)' : colAct + '14'}` : 'rgba(255,255,255,0.02)',
                              boxShadow: enActivo ? `0 0 16px ${colAct === 'var(--accent)' ? 'rgba(0,216,245,0.16)' : colAct + '2e'}` : 'none', opacity: distintaPlanilla ? 0.4 : 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 7 }}>
                              <span style={{ fontWeight: 700, fontSize: 12.5, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.label || 'Variable'}</span>
                              <span style={{ width: 19, height: 19, borderRadius: '50%', border: enActivo ? 'none' : '1.5px solid var(--border-light)', background: enActivo ? colAct : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'all .18s' }}>
                                {enActivo && <Icon name="check" style={{ width: 11, height: 11, color: '#000', strokeWidth: 3 }} />}
                              </span>
                            </div>
                            <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: 6, position: 'relative' }}>
                              <VariantePreviewSVG pid={v.moldeId} variante={v} height={64} color={enActivo ? colAct : 'rgba(255,255,255,0.5)'} />
                              <span style={{ position: 'absolute', top: 4, right: 4, fontSize: 9.5, fontWeight: 800, color: 'var(--text-muted)', background: 'rgba(0,0,0,0.5)', padding: '1px 6px', borderRadius: 999 }}>{nPz} pza{nPz === 1 ? '' : 's'}</span>
                            </div>
                            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 7, minHeight: 15, alignItems: 'center' }}>
                              <span style={{ fontSize: 10, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '100%' }}>{v.moldeNombre}</span>
                              {susDisenos.map(d => (
                                  <span key={d.id} title={d.nombre} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 700, color: colorDeDiseno(d.id), background: colorDeDiseno(d.id) + '1c', padding: '1px 6px', borderRadius: 999 }}>
                                    <span style={{ width: 5, height: 5, borderRadius: '50%', background: colorDeDiseno(d.id) }} />{d.nombre}
                                  </span>
                                ))}
                            </div>
                          </button>
                        );
                      })}
                  </div>
                </div>

                {/* Barra inferior fija */}
                <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 10, paddingTop: 12, marginTop: 4, borderTop: '1px solid var(--border-light)' }}>
                  {(moldesUnion.length > 0 || disenosPedido.length > 0) && (
                    <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5, color: 'var(--text-secondary)' }} onClick={reiniciarPedido} title="Empezar de 0">↺ Nuevo pedido</button>
                  )}
                  {/* El cliente puede traer SU molde: se sube acá mismo y queda en «Mis artículos». */}
                  <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5, display: 'flex', alignItems: 'center', gap: 6 }}
                    onClick={() => { setPedidoTabMoldes('mios'); setSubirMoldeNombre(''); setSubirMoldeFile(null); setSubirMoldeOpen(true); }}
                    title="Subir un molde propio (.ai · .pdf · .dxf)">
                    <Icon name="upload" style={{ width: 13, height: 13 }} /> Subir mi propio molde
                  </button>
                  <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
                    {disenosPedido.length > 0 && disenosSinMolde.length > 0 && (
                      <span style={{ fontSize: 11.5, color: 'var(--warning)', maxWidth: 280, textAlign: 'right', lineHeight: 1.35 }}>
                        Falta elegir variable en {disenosSinMolde.map(d => `«${d.nombre}»`).join(', ')}
                      </span>
                    )}
                    <button onClick={irPasoArte} disabled={!puedeIrAArte}
                      style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '11px 20px', borderRadius: 10, border: 'none',
                        cursor: puedeIrAArte ? 'pointer' : 'not-allowed', fontSize: 14, fontWeight: 800,
                        background: puedeIrAArte ? 'var(--accent)' : 'rgba(255,255,255,0.07)', color: puedeIrAArte ? '#001016' : 'var(--text-muted)', transition: 'all .2s' }}>
                      Cargar el arte <span style={{ fontSize: 16 }}>→</span>
                    </button>
                  </div>
                </div>
              </div>
            )}

            {mapeandoOperario ? (
              <div className="card" style={{ marginTop: 8, padding: 18, height: 'calc(100vh - 230px)', minHeight: 480, display: 'flex' }}>
                <MapeadorArteVisual
                  canvasLayout={canvasLayout}
                  mapeoData={mapeoData}
                  cargando={mapeoCargando}
                  mapeoValores={mapeoValores}
                  setMapeoValores={setMapeoValores}
                  onMapeoChange={guardarMapeoAuto}
                  selectedPiezaMapeo={selectedPiezaMapeo}
                  setSelectedPiezaMapeo={setSelectedPiezaMapeo}
                  etqNombres={etqNombres}
                  bordeConfig={bordeConfig}
                  etiquetaConfig={etiquetaConfig}
                  talleRef={etqData?.talle_ref}
                  previewPiezas={previewPiezas}
                  editablesRaw={editableData?.objetos || []}
                  onGuardar={guardarMapeo}
                  onCerrar={() => setMapeandoOperario(false)}
                />
              </div>
            ) : (
            <div style={['arte', 'planilla'].includes(pedidoPaso) ? { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' } : {}}>
              {pedidoPaso === 'planilla' && (
                <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
                <div className="card" style={{ padding: 16 }}>
                  {/* Título + (al lado contrario) aviso de caracteres que la fuente NO tiene */}
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
                    <div className="card-title">3 · Cargá la planilla (una sola vez)</div>
                    {faltantesFuente.length > 0 && (
                      <div style={{ flexShrink: 0, maxWidth: 460, display: 'flex', gap: 10, alignItems: 'flex-start', padding: '9px 13px', borderRadius: 10,
                        background: 'rgba(255,60,60,0.12)', border: '1.5px solid #ff4d4d', boxShadow: '0 0 14px rgba(255,60,60,0.25)' }}>
                        <span style={{ fontSize: 17, lineHeight: 1.1 }}>⚠</span>
                        <div style={{ fontSize: 12, lineHeight: 1.45 }}>
                          <b style={{ color: '#ff8a8a' }}>Los caracteres marcados en rojo no los tiene la fuente cargada.</b>
                          <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>Revisá la fuente, eliminá los caracteres o reemplazá la fuente del diseño.</div>
                          <div style={{ marginTop: 5, display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>Faltan:</span>
                            {faltantesFuente.map((ch, k) => (
                              <span key={k} style={{ fontFamily: 'monospace', fontWeight: 800, color: '#ff4d4d', background: 'rgba(255,60,60,0.2)', border: '1px solid rgba(255,80,80,0.5)', borderRadius: 4, padding: '0 5px' }}>{ch}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="card-subtitle">Cada fila es una prenda: elegí su <b>variable</b> y su talle. Los mismos datos sirven para todas las variables del pedido.</div>
                  
                  <div style={{ overflowX: 'auto', border: '1px solid var(--border-light)', borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.15)', marginTop: 12 }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', margin: 0, userSelect: (plFill || plSelDrag) ? 'none' : 'auto' }}>
                      <thead>
                        <tr style={{ backgroundColor: 'rgba(255,255,255,0.03)', borderBottom: '2px solid var(--border-light)' }}>
                          <th style={{ width: 45, padding: '8px 10px', borderRight: '1px solid var(--border-light)', textAlign: 'center', fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>#</th>
                          {cols.map(c => (
                            <th key={c.id} style={{ padding: '8px 10px', borderRight: '1px solid var(--border-light)', textAlign: 'left', fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>
                              {c.label} {c.role !== 'none' && <span style={{ fontSize: 9, opacity: 0.5, fontStyle: 'italic', fontWeight: 'normal' }}>({c.role})</span>}
                            </th>
                          ))}
                          <th style={{ width: 40, padding: 8 }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {filas.map((fila, i) => (
                          <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                            <td style={{ padding: '6px 10px', borderRight: '1px solid var(--border-light)', textAlign: 'center', fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>
                              {(i + 1).toString().padStart(2, '0')}
                            </td>
                            {cols.map((c, ci) => {
                              const cellValue = fila[c.id] !== undefined ? fila[c.id] : '';
                              const tipo = c.tipo || (c.role === 'manga' ? 'toggle' : 'texto');
                              const opts = (c.opciones || '').split(',').map(s => s.trim()).filter(Boolean);
                              const toggleOpts = opts.length >= 2 ? opts : (c.role === 'manga' ? ['corta', 'larga'] : ['A', 'B']);
                              const _rg = plRango();
                              const enSel = !!_rg && i >= _rg.r0 && i <= _rg.r1 && ci >= _rg.c0 && ci <= _rg.c1;
                              const esHandle = !!_rg && i === _rg.r1 && ci === _rg.c1;   // esquina inf-der del rango
                              const plMulti = !!_rg && (_rg.r0 !== _rg.r1 || _rg.c0 !== _rg.c1);   // hay más de una celda seleccionada
                              const enFill = plEnFill(i, ci);
                              const foco = () => { setPlSel({ r: i, c: ci }); setPlSelEnd({ r: i, c: ci }); };
                              let control;
                              const plc = `${i}-${ci}`;
                              if (c.role === 'talle') {
                                /* variante: opciones = variantes del molde (escribible: podés tipear o elegir) */
                                control = <ComboCell value={cellValue} options={estado?.talles || []} onChange={(v) => updateFila(i, c.id, v)} onFocusCell={foco} cellId={plc} onNavKey={(e) => navKeyPlanilla(e, i, ci)} noAbrir={plMulti} />;
                              } else if (c.role === 'diseno') {
                                /* diseño: opciones = los diseños del pedido */
                                control = <ComboCell value={cellValue} options={disenosPedido.map(d => d.nombre)} onChange={(v) => updateFila(i, c.id, v)} onFocusCell={foco} cellId={plc} onNavKey={(e) => navKeyPlanilla(e, i, ci)} noAbrir={plMulti} />;
                              } else if (tipo === 'desplegable') {
                                control = <ComboCell value={cellValue} options={opts} onChange={(v) => updateFila(i, c.id, v)} onFocusCell={foco} cellId={plc} onNavKey={(e) => navKeyPlanilla(e, i, ci)} noAbrir={plMulti} />;
                              } else if (tipo === 'toggle') {
                                control = (
                                  <div data-plc={plc} tabIndex={0} onFocus={foco} onKeyDown={(e) => navKeyPlanilla(e, i, ci)}
                                    style={{ display: 'flex', height: 32, outline: 'none' }}>
                                    {toggleOpts.map(o => {
                                      const on = cellValue ? cellValue === o : o === toggleOpts[0];
                                      return (
                                        <button key={o} type="button" tabIndex={-1} onClick={() => { updateFila(i, c.id, o); foco(); }}
                                          style={{ flex: 1, border: 'none', cursor: 'pointer', fontSize: 11.5, fontWeight: 600, background: on ? 'var(--accent)' : 'transparent', color: on ? 'var(--bg-primary)' : 'var(--text-secondary)', transition: 'background 0.15s' }}>
                                          {o}
                                        </button>
                                      );
                                    })}
                                  </div>
                                );
                              } else {
                                // Texto libre. Si la FUENTE del diseño no tiene algún caracter, se pinta
                                // de ROJO: el input queda con texto transparente y debajo una capa espejo
                                // (misma tipografía/tamaño/padding) que dibuja letra por letra.
                                const _esNum = c.role === 'numero';
                                const _chars = _colEsTexto(c) ? [..._textoCol(c, cellValue)] : [];
                                const _hayFalta = _chars.some(faltaEnFuente);
                                const _fBase = { padding: '6px 8px', fontSize: 13, lineHeight: '20px', height: 32, boxSizing: 'border-box',
                                  fontFamily: _esNum ? 'monospace' : 'inherit', fontWeight: c.role === 'nombre' ? 600 : 'normal' };
                                control = (
                                  <div style={{ position: 'relative' }}>
                                    {_hayFalta && (
                                      <div aria-hidden style={{ ..._fBase, position: 'absolute', inset: 0, whiteSpace: 'pre', overflow: 'hidden', pointerEvents: 'none' }}>
                                        {_chars.map((ch, k) => (
                                          <span key={k} style={faltaEnFuente(ch)
                                            ? { color: '#ff4d4d', fontWeight: 800, background: 'rgba(255,60,60,0.22)', borderRadius: 2 }
                                            : { color: 'var(--text-primary)' }}>{ch}</span>
                                        ))}
                                      </div>
                                    )}
                                    <input
                                      type={_esNum ? 'number' : 'text'}
                                      value={cellValue}
                                      placeholder="..."
                                      data-plc={plc}
                                      onFocus={foco}
                                      onKeyDown={(e) => navKeyPlanilla(e, i, ci)}
                                      title={_hayFalta ? 'La fuente del diseño no tiene los caracteres en rojo' : undefined}
                                      style={{ ..._fBase, width: '100%', border: 'none', background: 'none', outline: 'none', position: 'relative',
                                        color: _hayFalta ? 'transparent' : 'var(--text-primary)', caretColor: 'var(--text-primary)',
                                        textTransform: c.role === 'nombre' ? 'uppercase' : 'none' }}
                                      onChange={(e) => updateFila(i, c.id, e.target.value)}
                                    />
                                  </div>
                                );
                              }
                              // Borde accent SOLO en los lados externos del rango → recuadro único.
                              const bs = [];
                              if (enSel && _rg) {
                                if (i === _rg.r0) bs.push('inset 0 2px 0 var(--accent)');
                                if (i === _rg.r1) bs.push('inset 0 -2px 0 var(--accent)');
                                if (ci === _rg.c0) bs.push('inset 2px 0 0 var(--accent)');
                                if (ci === _rg.c1) bs.push('inset -2px 0 0 var(--accent)');
                              }
                              return (
                                <td key={c.id}
                                  onMouseDown={(e) => {
                                    if (e.shiftKey && plSel) { e.preventDefault(); setPlSelEnd({ r: i, c: ci }); return; }   // Shift+click: extiende el rango desde el ancla
                                    setPlSel({ r: i, c: ci }); setPlSelEnd({ r: i, c: ci }); plSelDragRef.current = true;
                                  }}
                                  onMouseOver={() => {
                                    if (plDragRef.current) setPlFill({ r: i, c: ci });
                                    else if (plSelDragRef.current) { setPlSelEnd({ r: i, c: ci }); if (!(plSel && plSel.r === i && plSel.c === ci)) setPlSelDrag(true); }
                                  }}
                                  style={{ position: 'relative', padding: 0, borderRight: '1px solid var(--border-light)',
                                    boxShadow: bs.length ? bs.join(', ') : 'none',
                                    background: enFill ? 'rgba(0,216,245,0.20)' : (enSel ? 'rgba(0,216,245,0.10)' : 'transparent') }}>
                                  {control}
                                  {esHandle && (
                                    <span onMouseDown={(e) => { e.stopPropagation(); e.preventDefault(); plFillSrcRef.current = plRango(); plDragRef.current = { r: i, c: ci }; setPlFill({ r: i, c: ci }); setPlSelDrag(true); }}
                                      title="Arrastrá para copiar/seguir la secuencia (vertical u horizontal)"
                                      style={{ position: 'absolute', right: -1, bottom: -1, width: 9, height: 9, background: 'var(--accent)', border: '1.5px solid var(--bg-primary)', borderRadius: 1, cursor: 'crosshair', zIndex: 3, boxShadow: '0 0 4px var(--accent)' }} />
                                  )}
                                </td>
                              );
                            })}
                            <td style={{ padding: 0, textAlign: 'center' }}>
                              <button 
                                className="quitar" 
                                onClick={() => removeFila(i)} 
                                style={{ border: 'none', background: 'none', color: 'var(--error)', cursor: 'pointer', fontSize: 18, width: '100%', height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                              >
                                ×
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'stretch', gap: 6 }}>
                      <button className="btn" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={agregarFilas}>
                        <Icon name="plus" style={{ width: 13, height: 13 }} /> Agregar {(parseInt(nFilasAgregar, 10) || 1) > 1 ? `${parseInt(nFilasAgregar, 10)} filas` : 'Fila'}
                      </button>
                      <input type="number" min="1" max="500" value={nFilasAgregar}
                        onChange={(e) => setNFilasAgregar(e.target.value)}
                        onFocus={(e) => e.target.select()}
                        onKeyDown={(e) => { if (e.key === 'Enter') agregarFilas(); }}
                        title="Cuántas filas agregar"
                        style={{ width: 54, textAlign: 'center', padding: '0 6px', borderRadius: 8, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-light)', color: '#fff', fontSize: 13, fontWeight: 700, outline: 'none' }} />
                    </div>
                    <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={loadExample}>
                      Cargar Ejemplo
                    </button>
                    <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={() => document.getElementById('csvPedidoInput')?.click()}
                      title="Cargar filas desde un archivo CSV (Excel). En talle/diseño/manga solo acepta valores válidos; si no coinciden, deja la celda vacía.">
                      ⬆ Importar CSV
                    </button>
                    <input id="csvPedidoInput" type="file" accept=".csv,text/csv,text/plain" style={{ display: 'none' }} onChange={onImportCSVFile} />
                  </div>
                </div>
                </div>
                {/* Barra inferior fija (igual que en los otros pasos) */}
                <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 10, paddingTop: 12, marginTop: 4, borderTop: '1px solid var(--border-light)' }}>
                  <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={() => { setArteIdx(0); setPedidoPaso('arte'); }}>← Arte</button>
                  <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5, color: 'var(--text-secondary)' }} onClick={reiniciarPedido} title="Empezar de 0">↺ Nuevo pedido</button>
                  {(() => {
                    // De la planilla se ENVÍA directo a generar la tizada (no hay paso de revisión).
                    const invalidos = planillaInvalidos();
                    const cols_inv = [...new Set(invalidos.map(x => x.label))];
                    const sinArte = moldesSeleccionados.filter(id => !arteEnPedido(id));
                    const bloq = !filas.length || invalidos.length > 0 || !moldesSeleccionados.length || sinArte.length > 0;
                    const motivo = invalidos.length ? `Corregí los valores que no están entre las opciones (${cols_inv.join(', ')})`
                      : sinArte.length ? `Falta el diseño en el paso Arte para: ${sinArte.map(id => moldeById(id)?.nombre).join(', ')}`
                        : !filas.length ? 'Agregá al menos una fila' : '';
                    return (
                      <>
                        <span style={{ marginLeft: 'auto', fontSize: 12, color: (invalidos.length || sinArte.length) ? '#ff8a8a' : 'var(--text-muted)', fontWeight: (invalidos.length || sinArte.length) ? 700 : 400 }}>
                          {invalidos.length ? `⚠ ${invalidos.length} valor(es) inválido(s) en ${cols_inv.join(', ')}`
                            : sinArte.length ? `⚠ Falta el diseño de ${sinArte.map(id => moldeById(id)?.nombre).join(', ')}`
                              : `${filas.length} fila${filas.length === 1 ? '' : 's'}`}
                        </span>
                        <button onClick={() => { if (!bloq) generarMulti(); }} disabled={bloq} title={motivo}
                          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '11px 22px', borderRadius: 10, border: 'none', cursor: bloq ? 'not-allowed' : 'pointer', fontSize: 14, fontWeight: 800,
                            background: bloq ? 'rgba(255,255,255,0.07)' : 'var(--accent)', color: bloq ? 'var(--text-muted)' : '#001016', transition: 'all .2s' }}>
                          Enviar <span style={{ fontSize: 16 }}>→</span>
                        </button>
                      </>
                    );
                  })()}
                </div>
                </div>
              )}

              {/* Picker de VARIABLE por fila: tarjetas con preview de las piezas de cada variable */}
              <Modal open={varPickerRow !== null} onClose={() => setVarPickerRow(null)}
                titulo="Elegí la variable"
                subtitulo={varPickerRow !== null ? `Prenda ${(varPickerRow + 1).toString().padStart(2, '0')} · define qué piezas se generan` : ''}
                maxWidth={760}>
                {variablesPlanilla.length === 0 ? (
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>Este molde no tiene variables. Armalas en Configuración › Variables.</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10 }}>
                    {variablesPlanilla.map(v => {
                      const on = varPickerRow !== null && filas[varPickerRow]?.__variante === v.clave;
                      const n = (v.valores || []).filter(x => x.pieza_idx != null).length;
                      const gpn = v.grupoId ? ((moldeById(v.moldeId)?.grupos || []).find(g => g.id === v.grupoId) || {}).nombre : null;
                      return (
                        <button key={v.clave} type="button" onClick={() => { updateFila(varPickerRow, '__variante', v.clave); setVarPickerRow(null); }}
                          style={{ textAlign: 'left', padding: 10, borderRadius: 12, cursor: 'pointer', transition: 'all .15s',
                            border: on ? '1.5px solid var(--accent)' : '1px solid var(--border-light)', background: on ? 'rgba(0,216,245,0.08)' : 'rgba(255,255,255,0.02)',
                            boxShadow: on ? '0 0 16px rgba(0,216,245,0.16)' : 'none' }}>
                          <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: 6, marginBottom: 7 }}>
                            <VariantePreviewSVG pid={v.moldeId} variante={v} height={78} color={on ? 'var(--accent)' : 'rgba(255,255,255,0.6)'} />
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
                            <span style={{ fontSize: 12.5, fontWeight: 700, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.label || 'Variable'}</span>
                            {on && <Icon name="check" style={{ width: 13, height: 13, color: 'var(--accent)', strokeWidth: 3, flexShrink: 0 }} />}
                          </div>
                          <div style={{ fontSize: 10.5, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{n} pza{n === 1 ? '' : 's'}{gpn ? ` · ${gpn}` : ''}</div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </Modal>

              {/* Paso 2 · Diseño por molde (uno a uno) */}
              {pedidoPaso === 'arte' && !mapeandoOperario && (() => {
                // VARIABLE-FIRST: se navega por VARIABLE (cada una con su molde por detrás).
                // Cada ítem es una VARIABLE elegida o un MOLDE entero (los propios no tienen variables).
                const itemsDis = itemsArteDe(disenoActivo);
                const itActual = itemsDis[arteIdx] || {};
                const varClaveActual = itActual.clave;
                const vObjActual = varClaveActual ? varByClave(varClaveActual) : { label: itActual.label };
                const _id = itActual.moldeId;
                const _m = moldeById(_id);
                const _moldeListo = !!canvasLayout?.layout?.length;
                const _tieneDiseno = !!mapeoData?.mesas?.length;
                const colAct = colorDeDiseno(disenoActivo);
                const cargadoActual = !!arteCargado[disenoActivo + '|' + _id];
                // VER VARIANTE en el pedido: las variantes del sistema (las de Variables) CON piezas. Al elegir
                // una en las tarjetas, el visor muestra SOLO sus piezas acomodadas (mismo acomodo que en Variables).
                const _varsPieza = (variantesEdit || []).filter(v => (v.valores || []).some(x => x.pieza_idx != null));
                // VARIABLE-FIRST estricto: si hay una variable activa NUNCA se cae a dibujar el molde
                // entero (135). Si `varianteFiltro` aún no resuelve (canvasLayout no listo / variable sin
                // piezas), se usa un filtro VACÍO como piso — antes caía a `null` = las 135 del molde.
                const vfArte = verVariante ? (varianteFiltro(verVariante) || { show: new Set(), pos: new Map(), vb: null }) : null;
                // ── TELA del pedido para este molde ──
                const _molProd = productosCat.productos.find(p => p.id === _id) || {};
                const _telasMol = (telasReg.telas || []).filter(t => (_molProd.telas_asignadas || []).includes(t.id));
                const _telaBaseId = telaBaseMolde[_id] || (_telasMol[0] && _telasMol[0].id) || null;
                const _telaDeGen = (gen) => (telaPorPieza[_id] || {})[gen] || _telaBaseId;
                const _telaActiva = telaModoVer && _telasMol.length > 0;
                const aplicarTela = (telaId) => {
                  if (telaSelPiezas.length) {   // hay piezas seleccionadas → override solo a esas
                    setTelaPorPieza(m => { const mm = { ...(m[_id] || {}) }; telaSelPiezas.forEach(g => { if (telaId === _telaBaseId) delete mm[g]; else mm[g] = telaId; }); return { ...m, [_id]: mm }; });
                  } else {                        // sin selección → tela base para TODAS (limpia overrides)
                    setTelaBaseMolde(m => ({ ...m, [_id]: telaId })); setTelaPorPieza(m => ({ ...m, [_id]: {} }));
                  }
                  setTelaModalOpen(false); setTelaSelPiezas([]); setTelaBusqueda('');
                };
                const panelTelaJSX = (
                  <div style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: 'var(--text-secondary)' }}>Telas</div>
                      <button className="btn ghost" style={{ padding: '5px 10px', fontSize: 11 }} onClick={() => { setTelaModoVer(false); setTelaSelPiezas([]); }}>← Volver</button>
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {_telasMol.map(t => (
                        <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 9px', borderRadius: 8, border: '1px solid var(--border-light)' }}>
                          <span style={{ width: 15, height: 15, borderRadius: 4, background: colorDeTela(t.id), flexShrink: 0 }} />
                          <span style={{ fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.nombre}</span>
                          {t.id === _telaBaseId && <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>base</span>}
                        </div>
                      ))}
                    </div>
                    <div style={{ fontSize: 10.5, color: 'var(--text-muted)', margin: '8px 0', lineHeight: 1.4 }}>{telaSelPiezas.length ? `${telaSelPiezas.length} pieza(s) seleccionada(s)` : 'Tocá piezas para elegirlas; tocá vacío para deseleccionar.'}</div>
                    <button className="btn primary" style={{ width: '100%' }} onClick={() => setTelaModalOpen(true)}>Asignar tela</button>
                  </div>
                );
                return (
                <div className="animate-fade" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                  {/* Navegación por DISEÑO (chips con progreso) */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap', marginBottom: 10, flexShrink: 0 }}>
                    {disenosPedido.map(d => {
                      const on = d.id === disenoActivo, col = colorDeDiseno(d.id);
                      const ms = moldesDeDiseno(d.id), done = ms.filter(m => arteCargado[d.id + '|' + m]).length;
                      const full = ms.length > 0 && done === ms.length;
                      return (
                        <button key={d.id} type="button" onClick={() => { setDisenoActivo(d.id); setArteIdx(0); }}
                          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderRadius: 999, cursor: 'pointer', fontSize: 13, fontWeight: 700, transition: 'all .18s',
                            border: on ? `1.5px solid ${col}` : '1px solid var(--border-light)', background: on ? `${col}22` : 'rgba(255,255,255,0.03)', color: on ? '#fff' : 'var(--text-secondary)', boxShadow: on ? `0 0 14px ${col}33` : 'none' }}>
                          <span style={{ width: 9, height: 9, borderRadius: '50%', background: col }} />
                          {d.nombre}
                          <span style={{ fontSize: 11, fontWeight: 800, color: full ? '#34d399' : 'var(--text-muted)' }}>{full ? '✓' : `${done}/${ms.length}`}</span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Navegación por VARIABLE (miniaturas con estado) del diseño activo */}
                  <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 6, marginBottom: 10, flexShrink: 0 }}>
                    {itemsDis.map((it, idx) => {
                      const vo = it.clave ? varByClave(it.clave) : null;
                      const on = idx === arteIdx, loaded = !!arteCargado[disenoActivo + '|' + it.moldeId];
                      return (
                        <button key={it.clave || 'm:' + it.moldeId} type="button" onClick={() => setArteIdx(idx)}
                          style={{ position: 'relative', flexShrink: 0, width: 92, padding: 8, borderRadius: 12, cursor: 'pointer', transition: 'all .18s',
                            border: on ? `1.5px solid ${colAct}` : '1px solid var(--border-light)', background: on ? `${colAct}14` : 'rgba(255,255,255,0.02)' }}>
                          <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: 4 }}>
                            {vo
                              ? <VariantePreviewSVG pid={vo.moldeId} variante={vo} height={46} color={on ? colAct : 'rgba(255,255,255,0.45)'} />
                              : <MoldePreviewSVG id={it.moldeId} height={46} color={on ? colAct : 'rgba(255,255,255,0.45)'} />}
                          </div>
                          <div style={{ fontSize: 10.5, fontWeight: 600, color: on ? '#fff' : 'var(--text-secondary)', marginTop: 5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{(vo && vo.label) || it.label || 'Variable'}</div>
                          <span style={{ position: 'absolute', top: 6, right: 6, width: 16, height: 16, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: loaded ? '#34d399' : 'rgba(255,255,255,0.12)', color: '#001016' }}>
                            {loaded && <Icon name="check" style={{ width: 9, height: 9, strokeWidth: 3.5 }} />}
                          </span>
                        </button>
                      );
                    })}
                  </div>


                  {/* .ai Y .pdf: un .ai YA es un PDF (Illustrator guarda con compat. PDF) y todo el
                      motor lo lee con PyMuPDF/pikepdf como PDF — nunca hubo nada "de Illustrator".
                      Habilitar .pdf permite probar exportaciones de Corel/Affinity. OJO: que ENTRE no
                      garantiza que se lea TODO; depende de que el exportador conserve las capas OCG y
                      el texto VIVO, y de que su forma de aplanar la apariencia sea la que el parser
                      entiende (Affinity: capas OK y texto OK, pero la PILA sale vacía → colores/bordes
                      mal). Ver MAPA changelog 2026-07-16. */}
                  <input type="file" ref={fileInputArteRef} accept=".ai,.pdf" onChange={(e) => cargarDisenoWizard(e.target.files[0])} hidden />
                  {/* La navegación de arriba YA es por variable → el visor muestra solo sus piezas (vfArte). */}
                  {_moldeListo ? (
                    /* Tarjeta única: cabecera (nombre del molde + cargar) + [ talles | molde | diseños ] */
                    <div className="card" style={{ padding: 14, flex: 1, minHeight: 0, display: 'flex' }}>
                      <MapeadorArteVisual
                        canvasLayout={canvasLayout}
                        mapeoData={mapeoData}
                        cargando={mapeoCargando}
                        mapeoValores={mapeoValores}
                        setMapeoValores={setMapeoValores}
                        onMapeoChange={guardarMapeoAuto}
                        selectedPiezaMapeo={selectedPiezaMapeo}
                        setSelectedPiezaMapeo={setSelectedPiezaMapeo}
                        objetosEditables={editablesOverlay}
                        editablesRaw={editableData?.objetos || []}
                        etqNombres={etqNombres}
                        bordeConfig={bordeConfig}
                        etiquetaConfig={etiquetaConfig}
                        talleRef={etqData?.talle_ref}
                        previewPiezas={previewPiezas}
                        onGuardar={guardarMapeo}
                        onCerrar={null}
                        vf={vfArte}
                        onCargarDiseno={() => fileInputArteRef.current.click()}
                        titulo={(
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                            <span style={{ width: 9, height: 9, borderRadius: '50%', background: colAct, flexShrink: 0 }} />
                            <span style={{ fontSize: 15, fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{vObjActual?.label || 'Variable'}</span>
                            <span style={{ fontSize: 11.5, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>· {_m?.nombre} · {disenosPedido.find(d => d.id === disenoActivo)?.nombre}</span>
                          </div>
                        )}
                        acciones={(<>
                          {_tieneDiseno && estado?.arte && <span className={`badge ${estado.arte.aprobado ? 'success' : 'error'}`}>{estado.arte.aprobado ? 'Aprobado ✓' : 'Observado ✗'}</span>}
                          {cargadoActual && (
                            <button className="btn" style={{ padding: '8px 16px', fontSize: 12.5, fontWeight: 800, borderRadius: 9, gap: 7,
                              background: 'var(--cmyk-magenta)', color: 'var(--bg-primary)', borderColor: 'var(--cmyk-magenta)' }}
                              title="Editar el diseño: mover, rotar, escalar y espejar lo que sea editable"
                              onClick={async () => { await cargarEditablesPedido(_id, disenoActivo, verVariante); setEditorEditOpen(true); }}>
                              <Icon name="edit" style={{ width: 14, height: 14 }} /> Editar diseño
                            </button>
                          )}
                          <button className="btn primary" style={{ padding: '8px 14px', fontSize: 12.5, borderRadius: 9 }} onClick={() => fileInputArteRef.current.click()}>
                            <Icon name="upload" style={{ width: 13, height: 13 }} /> {cargadoActual ? 'Cambiar arte' : 'Cargar arte'}
                          </button>
                          {_telasMol.length > 0 && (
                            <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5, borderRadius: 9, ...(telaModoVer ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}) }} onClick={() => { setTelaModoVer(v => !v); setTelaSelPiezas([]); }} title="Ver y asignar telas por pieza">
                              <Icon name="telas" style={{ width: 13, height: 13 }} /> Ver telas de pieza
                            </button>
                          )}
                        </>)}
                        telaModo={_telaActiva}
                        telaColorPieza={(gen) => colorDeTela(_telaDeGen(gen))}
                        telaSelSet={new Set(telaSelPiezas)}
                        onTelaClick={(gen) => setTelaSelPiezas(s => s.includes(gen) ? s.filter(x => x !== gen) : [...s, gen])}
                        onTelaVacio={() => setTelaSelPiezas([])}
                        panelTela={panelTelaJSX}
                        panelIzquierdo={estado?.talles?.length > 0 ? (
                          <div style={{ width: 150, flexShrink: 0, border: '1px solid var(--border-light)', borderRadius: 10, background: 'rgba(0,0,0,0.25)', overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: 'var(--text-secondary)', padding: '11px 12px', borderBottom: '1px solid var(--border-light)' }}>{term.variante === 'Talle' ? 'Talles' : term.variante}</div>
                            <div style={{ overflowY: 'auto', flex: 1 }}>
                              {estado.talles.map(t => {
                                const on = (etqData?.talle_ref || '') === t;
                                return (
                                  <button key={t} type="button" onClick={() => verVarianteOperario(t)}
                                    style={{ width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', border: 'none', borderLeft: on ? '3px solid var(--accent)' : '3px solid transparent', borderBottom: '1px solid rgba(255,255,255,0.04)', cursor: 'pointer', background: on ? 'rgba(0,216,245,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-secondary)', fontWeight: on ? 700 : 500, fontSize: 13 }}>
                                    <Icon name="eye" style={{ width: 13, height: 13, opacity: on ? 1 : 0.35, flexShrink: 0 }} />
                                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t}</span>
                                    {on && <span style={{ marginLeft: 'auto', fontSize: 9 }}>●</span>}
                                  </button>
                                );
                              })}
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', padding: '9px 12px', borderTop: '1px solid var(--border-light)', lineHeight: 1.4 }}>Tocá un talle para verlo en esa variante.</div>
                          </div>
                        ) : null}
                      />
                    </div>
                  ) : (
                    <div className="card" style={{ padding: 14, flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>Cargando el molde…</div>
                  )}

                  {/* Modal "Asignar tela al pedido": buscador + telas usables en el pedido */}
                  {telaModalOpen && (
                    <div onClick={() => setTelaModalOpen(false)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                      <div onClick={e => e.stopPropagation()} style={{ width: 420, maxWidth: '92vw', maxHeight: '80vh', background: '#141416', border: '1px solid var(--border-light)', borderRadius: 14, padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <h3 style={{ fontSize: 16, fontWeight: 700 }}>Asignar tela al pedido</h3>
                          <button className="btn ghost" style={{ padding: '4px 9px' }} onClick={() => setTelaModalOpen(false)}>✕</button>
                        </div>
                        <div style={{ fontSize: 12.5, color: telaSelPiezas.length ? 'var(--accent)' : 'var(--text-secondary)', lineHeight: 1.45 }}>
                          {telaSelPiezas.length ? `Se aplicará a ${telaSelPiezas.length} pieza(s): ${telaSelPiezas.join(', ')}` : 'No hay piezas seleccionadas → se aplicará a TODAS las piezas.'}
                        </div>
                        <input autoFocus placeholder="Buscar tela…" value={telaBusqueda} onChange={e => setTelaBusqueda(e.target.value)}
                          style={{ height: 38, fontSize: 13, padding: '0 12px', borderRadius: 9, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' }} />
                        <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {_telasMol.filter(t => t.nombre.toLowerCase().includes(telaBusqueda.toLowerCase())).map(t => (
                            <button key={t.id} onClick={() => aplicarTela(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 10, cursor: 'pointer', border: '1px solid var(--border-light)', background: 'transparent', color: '#fff', textAlign: 'left' }}>
                              <span style={{ width: 16, height: 16, borderRadius: 4, background: colorDeTela(t.id), flexShrink: 0 }} />
                              <span style={{ fontSize: 13.5, fontWeight: 600 }}>{t.nombre}</span>
                              {t.id === _telaBaseId && <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>base actual</span>}
                            </button>
                          ))}
                          {_telasMol.filter(t => t.nombre.toLowerCase().includes(telaBusqueda.toLowerCase())).length === 0 && (
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: 10 }}>No hay telas. Registralas en Config › Telas y asignalas al molde.</div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Barra inferior fija */}
                  <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 10, paddingTop: 12, marginTop: 4, borderTop: '1px solid var(--border-light)' }}>
                    <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={() => setPedidoPaso('moldes')}>← Diseños</button>
                    {_tieneDiseno && estado?.arte && !estado.arte.aprobado && (
                      <span style={{ fontSize: 11.5, color: 'var(--warning, #e0a020)' }}>Ajustá el mapeo y «Guardar mapeo».</span>
                    )}
                    <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-muted)' }}>{tareasArte.filter(t => arteCargado[t.did + '|' + t.mid]).length}/{tareasArte.length} con arte</span>
                    <button onClick={irAPlanillaDesdeArte} disabled={!todasArteCargadas}
                      title={todasArteCargadas ? '' : 'Cargá el arte de todos los moldes de todos los diseños'}
                      style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '11px 20px', borderRadius: 10, border: 'none',
                        cursor: todasArteCargadas ? 'pointer' : 'not-allowed', fontSize: 14, fontWeight: 800,
                        background: todasArteCargadas ? 'var(--accent)' : 'rgba(255,255,255,0.07)', color: todasArteCargadas ? '#001016' : 'var(--text-muted)', transition: 'all .2s' }}>
                      A la planilla <span style={{ fontSize: 16 }}>→</span>
                    </button>
                  </div>
                </div>
                );
              })()}

              {/* Editor de OBJETOS EDITABLES (modal) — mover/rotar/escalar sobre la silueta del molde */}
              {editorEditOpen && (() => {
                const ed = editableData || { objetos: [], talles: [] };
                const _mid = (itemsArteDe(disenoActivo)[arteIdx] || {}).moldeId || productosCat.activo;   // fallback: nunca undefined (evita guardar en el molde equivocado)
                // El editor trabaja sobre la VARIANTE elegida (no todo el molde): filtra sus piezas
                // y matchea los objetos por nombre GENÉRICO (el objeto está en "Frente 9" y la
                // variante usa "Frente 18", ambos "Frente").
                const _vfEd = verVariante ? varianteFiltro(verVariante) : null;
                const _piezasEd = (canvasLayout.layout || []).filter(p => !_vfEd || _vfEd.show.has(p.idx));
                const _voDe = (p) => (_vfEd ? (_vfEd.pos.get(p.idx) || { dx: 0, dy: 0 }) : { dx: 0, dy: 0 });
                const piezaDe = (nm) => _piezasEd.find(p => nombreGenerico(etqNombres[p.idx] || p.name || '') === nombreGenerico(nm || ''));
                const talles = ed.talles || [];
                // ARTE POR RANGO / POR TALLE: si el arte tiene mesas #rango/#talle, los talles se
                // agrupan por "firma" (qué mesa usa cada pieza en ese talle) → cada grupo es UN
                // espacio de edición (un diseño distinto) y se muestran SOLO sus editables. Un
                // arte de una sola mesa (sin #) da 1 grupo → funciona como siempre.
                const _mtAll = mapeoData?.mapeo_talles || {};
                const _hayMt = Object.keys(_mtAll).length > 0;
                const _mesaDeEd = (pz, t) => ((_mtAll[pz] || {})[t]) || mapeoValores[pz];
                const _grupos = [];
                if (_hayMt && talles.length) {
                  const bySig = new Map();
                  talles.forEach(t => {
                    const sig = (mapeoData?.piezas || []).map(pz => _mesaDeEd(pz, t) || 0).join(',');
                    if (!bySig.has(sig)) { const g = { talles: [] }; bySig.set(sig, g); _grupos.push(g); }
                    bySig.get(sig).talles.push(t);
                  });
                  _grupos.forEach(g => { g.label = g.talles.length > 1 ? `${g.talles[0]}–${g.talles[g.talles.length - 1]}` : String(g.talles[0]); });
                }
                const _porGrupos = _grupos.length > 1;
                // El SCOPE (a qué variantes se aplica) = las elegidas en el popup de tarjetas. La
                // vista del visor muestra la 1ª elegida. Sin selección → el talle base.
                const _selT = (editableVarsSel && editableVarsSel.length) ? (talles.length ? editableVarsSel.filter(t => talles.includes(t)) : editableVarsSel) : [];   // si aún no cargaron los talles, no perder el rango elegido
                // Talle GUÍA (el que se VE): el elegido con los chips si está dentro del alcance; si no, el 1º del rango.
                const T = (editableTalle && _selT.includes(editableTalle)) ? editableTalle : (_selT[0] || editableTalle || talles[0]);
                // Grupo (rango del arte) activo = el del talle en vista. Con arte por rango y sin
                // selección explícita, el alcance por defecto es TODO el rango (lo natural: el
                // diseño es el mismo en todos sus talles).
                const _grpAct = _porGrupos ? (_grupos.find(g => g.talles.includes(T)) || _grupos[0]) : null;
                const curTfOf = (nm, t) => (editorTfs[nm] || {})[t] || { dx: 0, dy: 0, rot: 0, scale: 1 };
                // Escala por eje: `sx`/`sy` mandan (enlace desactivado = ancho y alto libres);
                // si no están, valen `scale` (uniforme, legacy). Igual que el motor.
                const _SX = (tf) => (tf && tf.sx != null ? tf.sx : ((tf && tf.scale) ?? 1));
                const _SY = (tf) => (tf && tf.sy != null ? tf.sy : ((tf && tf.scale) ?? 1));
                // RANGO en edición (todos sus talles) — independiente del alcance elegido.
                // RANGO al que se aplica el ajuste. El talle EN VISTA (T) siempre forma parte: es
                // sobre el que el usuario está moviendo el objeto. Si quedaba afuera del cálculo
                // (p. ej. porque el arte le da una mesa propia y cae en otro grupo), el cambio se
                // guardaba en todo el rango MENOS en el talle que se estaba mirando.
                const _rangoTalles = (() => {
                  const base = (_selT.length ? _selT : (_grpAct ? _grpAct.talles : [T])).filter(Boolean);
                  return (T && !base.includes(T)) ? [...base, T] : base;
                })();
                // Alcance del ajuste: por DEFECTO todo el rango (lo natural: el diseño es el mismo en
                // todos sus talles). Con `edSoloTalle` el cambio va SOLO al talle en vista (excepción
                // puntual): el motor ya resuelve por talle, así que el resto del rango queda como estaba.
                const scopeTalles = () => (edSoloTalle ? [T].filter(Boolean) : _rangoTalles);
                const _selResumen = _selT.length === 0 ? (_grpAct ? _grpAct.label : (T || '—')) : _selT.length === talles.length ? 'Todas' : _selT.length === 1 ? _selT[0] : `${_selT.length} variantes`;
                // Editables DEL GRUPO en vista: solo los objetos cuya mesa está activa en el talle T
                // (con una mesa por rango, saca los duplicados de los otros rangos de la lista).
                const _mesasActT = new Set((mapeoData?.piezas || []).map(pz => parseInt(_mesaDeEd(pz, T))).filter(Boolean));
                // Los objetos AGREGADOS por el usuario siempre se muestran para su pieza (no
                // pasan por el filtro de mesa del arte: no tienen mesa del arte).
                // Los AGREGADOS siempre están en la BARRA (con o sin pieza asignada): sin pieza
                // quedan disponibles para colocarlos. El lienzo igual solo dibuja los que tienen
                // pieza (el render corta con `piezaDe`).
                const _objsEd = (ed.objetos || []).filter(o => o._agregado || (piezaDe(o.pieza) && (!_hayMt || _mesasActT.has(o.mesa))));
                const _objsUnicos = _objsEd.filter((o, i) => _objsEd.findIndex(x => x.nombre === o.nombre) === i);
                const toVB = (cx, cy) => { const svg = editorSvgRef.current; if (!svg) return { x: 0, y: 0 }; const pt = svg.createSVGPoint(); pt.x = cx; pt.y = cy; const q = pt.matrixTransform(svg.getScreenCTM().inverse()); return { x: q.x, y: q.y }; };
                // Pan/zoom del visor del editor: rueda = zoom (al cursor); CLICK DERECHO arrastrado = mover el espacio.
                const _edFullVB = () => { const s = (_vfEd && _vfEd.vb) ? _vfEd.vb : `0 0 ${canvasLayout.width} ${canvasLayout.height}`; const n = s.split(/\s+/).map(Number); return { x: n[0], y: n[1], w: n[2], h: n[3] }; };
                const _edVBnow = edVB || _edFullVB();
                const edWheel = (e) => { const r = e.currentTarget.getBoundingClientRect(); const mx = (e.clientX - r.left) / r.width, my = (e.clientY - r.top) / r.height; const f = e.deltaY < 0 ? 1 / 1.15 : 1.15; setEdVB(prev => { const b = prev || _edFullVB(); const nw = Math.max(1, b.w * f), nh = Math.max(1, b.h * f); return { x: b.x + (b.w - nw) * mx, y: b.y + (b.h - nh) * my, w: nw, h: nh }; }); };
                const edPan = (e) => { if (e.button !== 2) return; e.preventDefault(); const r = e.currentTarget.getBoundingClientRect(); const base = edVB || _edFullVB(); const sx = e.clientX, sy = e.clientY; const mv = (ev) => setEdVB({ ...base, x: base.x - (ev.clientX - sx) / r.width * base.w, y: base.y - (ev.clientY - sy) / r.height * base.h }); const up = () => { window.removeEventListener('mousemove', mv); window.removeEventListener('mouseup', up); }; window.addEventListener('mousemove', mv); window.addEventListener('mouseup', up); };
                // TALLES a los que se aplica el ajuste de UN objeto: aquellos donde SU PIEZA usa la
                // MISMA mesa del arte que en el talle en vista, es decir donde se ve EXACTAMENTE el
                // mismo diseño. NO se usa el "grupo" global porque ese se arma con la firma de TODAS
                // las piezas: dos talles pueden mostrar el mismo diseño PARA ESTA PIEZA y caer en
                // grupos distintos → el objeto se movía en unos y en otros no. (Caso real: para
                // 'Frente 1' la mesa 12 cubre 2XL,3XL,4,4XL,5XL,6,6XL; los talles 4 y 6 quedaban
                // fuera del rango 2XL–6XL y no se actualizaban.)
                const tallesDeObjeto = (nm) => {
                  if (edSoloTalle) return [T].filter(Boolean);
                  const o = _objsUnicos.find(x => x.nombre === nm);
                  const pz = o && o.pieza;
                  if (!pz || !talles.length) return _rangoTalles;
                  const mT = String(_mesaDeEd(pz, T) ?? '');
                  const ts = talles.filter(t => String(_mesaDeEd(pz, t) ?? '') === mT);
                  return ts.length ? ts : _rangoTalles;
                };
                const setTfScoped = (nm, patch) => setEditorTfs(prev => { const cur = (prev[nm] || {})[T] || { dx: 0, dy: 0, rot: 0, scale: 1 }; const tf = { ...cur, ...patch }; const o = { ...(prev[nm] || {}) }; tallesDeObjeto(nm).forEach(t => { o[t] = tf; }); return { ...prev, [nm]: o }; });
                // Aplica un cambio a VARIOS objetos y registra el historial con el valor NUEVO en el mismo
                // paso. (No usar setTimeout+ref: el ref se sincroniza en un efecto que puede correr después
                // → se guardaba el estado viejo y Ctrl+Z quedaba desfasado.)
                const aplicarTf = (nombres, patchDe) => setEditorTfs(prev => {
                  const next = { ...prev };
                  (nombres || []).forEach(nm => {
                    const cur = (prev[nm] || {})[T] || { dx: 0, dy: 0, rot: 0, scale: 1 };
                    const tf = { ...cur, ...(patchDe(nm, cur) || {}) };
                    const o = { ...(prev[nm] || {}) };
                    tallesDeObjeto(nm).forEach(t => { o[t] = tf; });
                    next[nm] = o;
                  });
                  histCommit(next);   // el historial guarda EXACTAMENTE lo que queda aplicado
                  return next;
                });
                // Colocación en COORDENADAS DEL DISEÑO: el objeto vive dentro del diseño → su posición
                // base (`fcx/fcy` del bbox_mu) Y su movimiento (`dx/dy`) se miden en fracción del DISEÑO
                // colocado en la pieza (`imgW/imgH` = encaje: alto manda, ancho centrado). Igual que el
                // motor (`_matriz_editable` con `dx*awf*W` = ancho del diseño). No depende del talle guía
                // ni de la pieza donde se registró el objeto. `imgH = p.ph` (el alto del diseño = alto pieza).
                // Aspecto de la MESA DEL ARTE de esta pieza para el TALLE en vista (T). Es lo que
                // define dónde y con qué tamaño se coloca el diseño sobre la pieza; cambia por
                // rango, por eso se resuelve acá y no se toma un valor fijo.
                const _aspMesaDe = (p) => {
                  const _pn = etqNombres[p.idx] || p.name || '';
                  const _mi = (mapeoData?.mapeo_talles?.[_pn]?.[T]) || mapeoValores[_pn];
                  const _m = _mi ? (mapeoData?.mesas || []).find(x => x.mesa === parseInt(_mi)) : null;
                  return _m ? (_m.aspecto || (_m.w_cm && _m.h_cm ? _m.w_cm / _m.h_cm : null)) : null;
                };
                // El marco (y con él imgW/imgH) sale del resolvedor ÚNICO `marcoDeObjeto`.
                const _imgDim = (o, p) => { const m = marcoDeObjeto(o, p, _aspMesaDe(p)); return { imgW: m.w, imgH: m.h, imgX: m.x, imgY: m.y }; };
                const centerOf = (o, p, tf) => {
                  const { x: imgX, y: imgY, w: imgW, h: imgH, fcx, fcy, fw, fh } = marcoDeObjeto(o, p, _aspMesaDe(p));
                  // w/h SIEMPRE positivos (un <image> con ancho negativo no dibuja); el signo de
                  // sx/sy es el ESPEJO y se aplica como transform (sgx/sgy).
                  return { cx: imgX + (fcx + tf.dx) * imgW, cy: imgY + (fcy + tf.dy) * imgH,
                    w: fw * imgW * Math.abs(_SX(tf)), h: fh * imgH * Math.abs(_SY(tf)),
                    sgx: _SX(tf) < 0 ? -1 : 1, sgy: _SY(tf) < 0 ? -1 : 1 };
                };
                // Mapear pantalla→viewBox con una CTM YA CACHEADA (no llamar getScreenCTM en cada
                // movimiento: es una lectura de layout sincrónica que hace el arrastre pesado).
                const _cToVB = (cx, cy, ictm) => { const svg = editorSvgRef.current; if (!svg || !ictm) return { x: 0, y: 0 }; const pt = svg.createSVGPoint(); pt.x = cx; pt.y = cy; const q = pt.matrixTransform(ictm); return { x: q.x, y: q.y }; };
                const onMove = (e) => { const d = editorDrag.current; if (!d) return; const m = _cToVB(e.clientX, e.clientY, d.ictm); if (d.tipo === 'move') { const _ddx = m.x - d.start.x, _ddy = m.y - d.start.y; (d.grupo && d.grupo.length ? d.grupo : [{ nm: d.nm, imgW: d.imgW, imgH: d.imgH, tf0: d.tf0 }]).forEach(g => setTfScoped(g.nm, { dx: g.tf0.dx + _ddx / g.imgW, dy: g.tf0.dy + _ddy / g.imgH })); } else if (d.tipo === 'scale') { const _f = Math.hypot(m.x - d.cx, m.y - d.cy) / (d.dist0 || 1); const _c = (v) => Math.max(0.1, Math.min(8, v)); setTfScoped(d.nm, { scale: _c(d.scale0 * _f), sx: _c(d.sx0 * _f), sy: _c(d.sy0 * _f) }); } else if (d.tipo === 'rot') setTfScoped(d.nm, { rot: Math.round(d.rot0 + (Math.atan2(m.y - d.cy, m.x - d.cx) * 180 / Math.PI - d.ang0)) }); };
                const onUp = () => { if (editorDrag.current) { editorDrag.current = null; histCommit(editorTfsRef.current); } };
                const start = (e, tipo, o, p) => {
                  // Colocando un objeto nuevo: el click debe llegar al lienzo (no arrastrar el de
                  // abajo), así se puede colocar ENCIMA de otro objeto.
                  if (objPendiente) return;
                  e.stopPropagation(); e.preventDefault();
                  // Selección: si el objeto ya está en la selección se respeta (para mover en grupo);
                  // si no, pasa a ser la selección (Ctrl/Shift lo SUMA en vez de reemplazar).
                  // Ctrl/Shift SUMA, pero solo si es de la MISMA pieza (si no, arranca selección nueva).
                  const _add = (e.ctrlKey || e.metaKey || e.shiftKey) && _mismaPieza(o);
                  const _selNow = editableSel.includes(o.nombre) ? editableSel : (_add ? [...editableSel, o.nombre] : [o.nombre]);
                  setEditableSel(_selNow);
                  const svg = editorSvgRef.current; const ictm = (svg && svg.getScreenCTM()) ? svg.getScreenCTM().inverse() : null;
                  const m = _cToVB(e.clientX, e.clientY, ictm);
                  const tf = curTfOf(o.nombre, T); const vo = _voDe(p); const c = centerOf(o, p, tf);
                  const { imgW, imgH } = _imgDim(o, p);   // el mover se mide en fracción del DISEÑO
                  // PIVOTE = centro del objeto YA con el acomodo de la variante (vo). Sin esto el
                  // giro/escala se hacían alrededor de un punto corrido → "al reves"/pesado.
                  const cx = c.cx + vo.dx, cy = c.cy + vo.dy;
                  // GRUPO a mover: cada objeto seleccionado con SU tf inicial y SUS dimensiones de diseño
                  // (pueden estar en piezas distintas → el mismo desplazamiento en pantalla se convierte
                  // a la fracción que le corresponde a cada uno).
                  const _grupo = _selNow.map(nm => {
                    const oo = _objsUnicos.find(x => x.nombre === nm); if (!oo) return null;
                    const pp = piezaDe(oo.pieza); if (!pp) return null;
                    const dd = _imgDim(oo, pp);
                    return { nm, imgW: dd.imgW, imgH: dd.imgH, tf0: curTfOf(nm, T) };
                  }).filter(Boolean);
                  editorDrag.current = { tipo, nm: o.nombre, p, imgW, imgH, ictm, start: m, tf0: tf, grupo: _grupo, cx, cy, dist0: Math.hypot(m.x - cx, m.y - cy) || 1, scale0: tf.scale, sx0: _SX(tf), sy0: _SY(tf), ang0: Math.atan2(m.y - cy, m.x - cx) * 180 / Math.PI, rot0: tf.rot };
                };
                // Click en el FONDO del visor = deseleccionar. Los objetos cortan la propagación al
                // arrancar su arrastre (`start`), así que todo mousedown que llega acá es espacio vacío.
                // El botón derecho no toca la selección: sigue siendo el pan del espacio.
                // COLOCAR un objeto recién subido EN EL PUNTO clickeado: se busca la pieza bajo el
                // cursor y se calcula el dx/dy (fracción de esa pieza) para que el CENTRO del objeto
                // caiga exactamente ahí. La base del objeto es el centro de la pieza (0.5, 0.5).
                const colocarObjetoEnClick = (e) => {
                  const svg = editorSvgRef.current;
                  const ictm = (svg && svg.getScreenCTM()) ? svg.getScreenCTM().inverse() : null;
                  const m = _cToVB(e.clientX, e.clientY, ictm);
                  const hit = _piezasEd.find(p => {
                    const vo = _voDe(p);
                    return m.x >= p.px + vo.dx && m.x <= p.px + vo.dx + p.pw
                        && m.y >= p.py + vo.dy && m.y <= p.py + vo.dy + p.ph;
                  });
                  if (!hit) { showError('Tocá sobre una pieza del diseño para colocar el objeto ahí.'); return; }
                  const vo = _voDe(hit);
                  const dx = (m.x - (hit.px + vo.dx)) / hit.pw - 0.5;   // 0.5 = centro (base del objeto)
                  const dy = (m.y - (hit.py + vo.dy)) / hit.ph - 0.5;
                  const nm = (etqNombres[hit.idx] || hit.name || '').trim();
                  asignarObjetoAPieza(nm, { dx, dy }, scopeTalles());
                };
                const edFondo = (e) => {
                  if (e.button === 0 && objPendiente) { e.preventDefault(); colocarObjetoEnClick(e); return; }
                  if (e.button === 0) setEditableSel([]);
                  edPan(e);
                };
                const chip = (txt, on, fn) => (<button type="button" onClick={fn} style={{ padding: '5px 11px', borderRadius: 999, fontSize: 12, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{txt}</button>);
                const selStyle = { padding: '5px 8px', borderRadius: 8, fontSize: 12, background: 'rgba(255,255,255,0.04)', color: '#fff', border: '1px solid var(--border-light)' };
                // GUARDAR: persiste TODOS los objetos del diseño (con su transform actual) por VARIABLE +
                // alcance de variantes → sobrevive al recargar y al reabrir (se relee de la base). Devuelve
                // true si guardó (para poder cerrar recién ahí).
                // GUARDA **TODO** LO EDITADO, en TODOS los rangos/talles de la sesión — no solo el
                // rango que está en vista. `editorTfs` = {nombre: {talle: tf}} y acumula lo de cada
                // rango que el usuario visitó; antes se persistía sólo `scopeTalles()` del rango en
                // pantalla y los otros rangos SE PERDÍAN al guardar.
                const guardarTodo = async () => {
                  if (!_mid) { showError('No pude determinar el molde — reabrí el editor.'); return false; }
                  // Todos los objetos del diseño (de cualquier rango), por nombre.
                  const porNombre = new Map();
                  (ed.objetos || []).forEach(o => { if (!porNombre.has(o.nombre)) porNombre.set(o.nombre, o); });
                  // Por objeto: agrupar los talles que comparten el MISMO transform (1 request por grupo).
                  const envios = [];
                  Object.entries(editorTfs || {}).forEach(([nombre, porTalle]) => {
                    const o = porNombre.get(nombre);
                    if (!o || !porTalle) return;
                    const grupos = new Map();
                    Object.entries(porTalle).forEach(([talle, tf]) => {
                      if (!talle || !tf) return;
                      const k = JSON.stringify(tf);
                      if (!grupos.has(k)) grupos.set(k, { tf, talles: [] });
                      grupos.get(k).talles.push(talle);
                    });
                    grupos.forEach(g => envios.push({ o, tf: g.tf, talles: g.talles }));
                  });
                  if (!envios.length) {   // nada tocado: al menos persistir el alcance en vista
                    const ts0 = (scopeTalles() || []).filter(Boolean);
                    _objsUnicos.forEach(o => envios.push({ o, tf: curTfOf(o.nombre, T), talles: ts0.length ? ts0 : [T].filter(Boolean) }));
                  }
                  try {
                    for (const e of envios) {
                      if (!e.talles.length) continue;
                      if (e.o._agregado) {   // objeto AGREGADO: su transform va al manifiesto (+ su pieza)
                        await fetch(`/api/productos/objeto_agregado/${e.o._oid}/transform`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid: _mid, diseno: editableDiseno, talles: e.talles, transform: e.tf, variante: verVariante || '*', pieza: e.o.pieza }) });
                      } else {
                        await fetch('/api/productos/editables', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pid: _mid, diseno: editableDiseno, nombre: e.o.nombre, talles: e.talles, transform: e.tf, variante: verVariante || '*' }) });   // POR VARIABLE
                      }
                    }
                    const _nT = new Set(envios.flatMap(e => e.talles)).size;
                    showMsg(`Guardado: ${porNombre.size} objeto/s en ${_nT} talle/s (todos los rangos editados).`);
                    return true;
                  } catch { showError('No se pudo guardar.'); return false; }
                };
                // ALINEAR (estilo Illustrator). `modo`: 'sel' = entre los objetos seleccionados (según el
                // bbox de la selección) · 'mesa' = contra la MESA DE TRABAJO (el diseño colocado en la
                // pieza). `eje`: izq|ch|der (horizontal) · arr|cv|aba (vertical). Trabaja en coords del
                // canvas y convierte el desplazamiento a la fracción de diseño de CADA objeto.
                const _alinear = (eje) => {
                  const objs = editableSel.map(nm => {
                    const o = _objsUnicos.find(x => x.nombre === nm); if (!o) return null;
                    const p = piezaDe(o.pieza); if (!p) return null;
                    const tf = curTfOf(nm, T);
                    return { nm, c: centerOf(o, p, tf), d: _imgDim(o, p), tf };
                  }).filter(Boolean);
                  if (!objs.length) return;
                  const mesa = edAlinearMesa;
                  if (!mesa && objs.length < 2) { showError('Elegí 2 o más objetos (Ctrl+click) para alinearlos entre sí.'); return; }
                  let R;
                  if (mesa) {   // la "mesa de trabajo" = el DISEÑO colocado sobre la pieza
                    const d0 = objs[0].d;
                    R = { x0: d0.imgX, x1: d0.imgX + d0.imgW, y0: d0.imgY, y1: d0.imgY + d0.imgH };
                  } else {      // bbox de la SELECCIÓN
                    R = { x0: Math.min(...objs.map(a => a.c.cx - a.c.w / 2)), x1: Math.max(...objs.map(a => a.c.cx + a.c.w / 2)),
                          y0: Math.min(...objs.map(a => a.c.cy - a.c.h / 2)), y1: Math.max(...objs.map(a => a.c.cy + a.c.h / 2)) };
                  }
                  aplicarTf(objs.map(a => a.nm), (nm) => {
                    const a = objs.find(x => x.nm === nm);
                    let ncx = a.c.cx, ncy = a.c.cy;
                    if (eje === 'izq') ncx = R.x0 + a.c.w / 2;
                    else if (eje === 'ch') ncx = (R.x0 + R.x1) / 2;
                    else if (eje === 'der') ncx = R.x1 - a.c.w / 2;
                    else if (eje === 'arr') ncy = R.y0 + a.c.h / 2;
                    else if (eje === 'cv') ncy = (R.y0 + R.y1) / 2;
                    else if (eje === 'aba') ncy = R.y1 - a.c.h / 2;
                    return { dx: a.tf.dx + (ncx - a.c.cx) / a.d.imgW, dy: a.tf.dy + (ncy - a.c.cy) / a.d.imgH };
                  });
                };
                // ROTAR y ESPEJAR: funcionan sobre TODOS los objetos seleccionados a la vez.
                // La selección MÚLTIPLE nunca cruza piezas: espejar/alinear/mover en grupo solo tiene
                // sentido entre objetos de la MISMA pieza (cada pieza tiene su propio espacio).
                const _piezaDeSel = () => { const p0 = _objsUnicos.find(x => x.nombre === editableSel[0]); return p0 ? p0.pieza : null; };
                const _mismaPieza = (o) => !editableSel.length || _piezaDeSel() === o.pieza;
                const _rotarSel = (deg) => aplicarTf(editableSel, (nm, cur) => ({ rot: Math.round(((cur.rot || 0) + deg) % 360) }));
                // ESPEJAR = reflejar la SELECCIÓN COMPLETA como una unidad (igual que Illustrator): no
                // alcanza con dar vuelta cada objeto en su lugar, sus POSICIONES también se reflejan
                // contra el bbox de la selección (el de más a la izquierda queda a la derecha). Con un
                // solo objeto el bbox es el suyo → se refleja en el lugar, sin moverse.
                const _espejarSel = (eje) => {
                  const objs = editableSel.map(nm => {
                    const o = _objsUnicos.find(x => x.nombre === nm); if (!o) return null;
                    const p = piezaDe(o.pieza); if (!p) return null;
                    const tf = curTfOf(nm, T);
                    return { nm, c: centerOf(o, p, tf), d: _imgDim(o, p), tf };
                  }).filter(Boolean);
                  if (!objs.length) return;
                  const R = { x0: Math.min(...objs.map(a => a.c.cx - a.c.w / 2)), x1: Math.max(...objs.map(a => a.c.cx + a.c.w / 2)),
                              y0: Math.min(...objs.map(a => a.c.cy - a.c.h / 2)), y1: Math.max(...objs.map(a => a.c.cy + a.c.h / 2)) };
                  const Sx = (R.x0 + R.x1) / 2, Sy = (R.y0 + R.y1) / 2;   // eje del espejo
                  aplicarTf(objs.map(a => a.nm), (nm, cur) => {
                    const a = objs.find(x => x.nm === nm);
                    const sx = cur.sx != null ? cur.sx : (cur.scale ?? 1);
                    const sy = cur.sy != null ? cur.sy : (cur.scale ?? 1);
                    // el objeto se da vuelta (signo negativo) Y su centro se refleja contra el eje
                    if (eje === 'h') return { sx: -sx, sy, dx: a.tf.dx + (2 * Sx - 2 * a.c.cx) / a.d.imgW };
                    return { sx, sy: -sy, dy: a.tf.dy + (2 * Sy - 2 * a.c.cy) / a.d.imgH };
                  });
                };
                // VOLVER AL DISEÑO PRINCIPAL: todos los objetos vuelven a como carga el diseño (sin mover/
                // rotar/escalar) en el alcance elegido. Es deshacible (queda en el historial).
                const volverPrincipal = () => {
                  const next = { ...editorTfs };
                  _objsUnicos.forEach(o => { const m = { ...(next[o.nombre] || {}) }; scopeTalles().forEach(t => { m[t] = { dx: 0, dy: 0, rot: 0, scale: 1 }; }); next[o.nombre] = m; });
                  setEditorTfs(next); histCommit(next);
                };
                const _h = editorHist.current; const _canUndo = _h.idx > 0; const _canRedo = _h.idx < _h.stack.length - 1;
                return (
                  <div style={{ position: 'fixed', inset: 0, zIndex: 2000, background: 'rgba(2,6,12,0.93)', backdropFilter: 'blur(3px)', display: 'flex', flexDirection: 'column', padding: 16 }}
                    onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}>
                    {/* COLOCAR el objeto recién subido: aviso NO bloqueante — el usuario toca
                        sobre el diseño y el objeto se coloca justo en ese punto de esa pieza. */}
                    {objPendiente && (
                      <div style={{ position: 'absolute', top: 62, left: '50%', transform: 'translateX(-50%)', zIndex: 2200,
                        display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px', borderRadius: 999,
                        border: '1px solid var(--accent)', background: 'rgba(0,243,255,0.12)', backdropFilter: 'blur(4px)',
                        boxShadow: '0 6px 24px rgba(0,0,0,0.45)' }}>
                        <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--accent)' }}>
                          Tocá sobre el diseño dónde va «{objPendiente.nombre}»
                        </span>
                        <button type="button" onClick={() => { if (objPendiente._nuevo) borrarObjetoAgregado(objPendiente._oid); setObjPendiente(null); }}
                          style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, cursor: 'pointer',
                            border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>Cancelar</button>
                      </div>
                    )}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexShrink: 0, flexWrap: 'wrap' }}>
                      <Icon name="edit" style={{ width: 18, height: 18, color: 'var(--accent)' }} />
                      <h3 style={{ margin: 0, fontSize: 16 }}>Editar diseño</h3>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{moldeById(_mid)?.nombre} · {(disenosPedido.find(d => d.id === disenoActivo) || {}).nombre || disenoActivo}</span>
                      <button className="btn ghost" style={{ marginLeft: 'auto', padding: '8px 12px' }} onClick={volverPrincipal} title="Volver a como viene el diseño (sin ediciones), en el alcance elegido"><Icon name="reset" style={{ width: 13, height: 13 }} /> Volver al diseño principal</button>
                      <button className="btn ghost" style={{ padding: '8px 12px', opacity: _canUndo ? 1 : 0.4 }} onClick={editorUndo} disabled={!_canUndo} title="Deshacer (Ctrl+Z)">↶ Deshacer</button>
                      <button className="btn ghost" style={{ padding: '8px 12px', opacity: _canRedo ? 1 : 0.4 }} onClick={editorRedo} disabled={!_canRedo} title="Rehacer (Ctrl+Y)">↷ Rehacer</button>
                      <button className="btn ghost" style={{ padding: '8px 14px' }} onClick={() => setEditorEditOpen(false)}>Cerrar</button>
                      <button className="btn primary" style={{ padding: '8px 16px' }} onClick={async () => { if (await guardarTodo()) setEditorEditOpen(false); }}><Icon name="check" style={{ width: 13, height: 13 }} /> Guardar</button>
                    </div>
                    <div style={{ display: 'flex', gap: 10, flex: 1, minHeight: 0 }}>
                      {/* lista de objetos */}
                      <div style={{ width: 150, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto' }}>
                        {_objsUnicos.map(o => (
                          <button key={o.nombre} type="button" title="Click = seleccionar · Ctrl/Shift+click = sumar (solo objetos de la MISMA pieza)"
                            onClick={(e) => {
                              const add = e.ctrlKey || e.metaKey || e.shiftKey;
                              if (!add) { setEditableSel([o.nombre]); return; }
                              if (editableSel.includes(o.nombre)) { setEditableSel(editableSel.filter(n => n !== o.nombre)); return; }
                              if (!_mismaPieza(o)) { showError('Solo podés seleccionar objetos de la MISMA pieza.'); return; }
                              setEditableSel([...editableSel, o.nombre]);
                            }}
                            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 8px', borderRadius: 9, cursor: 'pointer', textAlign: 'left', border: '1px solid ' + (editableSel.includes(o.nombre) ? 'var(--accent)' : 'var(--border-light)'), background: editableSel.includes(o.nombre) ? 'rgba(0,243,255,0.10)' : 'rgba(255,255,255,0.02)', color: '#fff' }}>
                            <span style={{ width: 34, height: 34, flexShrink: 0, borderRadius: 6, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}><img alt="" src={o.thumb ? `data:image/png;base64,${o.thumb}` : (o.svg ? `data:image/svg+xml;base64,${o.svg}` : '')} style={{ maxWidth: '100%', maxHeight: '100%' }} /></span>
                            <span style={{ minWidth: 0, flex: 1 }}>
                              <span style={{ display: 'block', fontSize: 12.5, fontWeight: 700, textTransform: 'capitalize', overflow: 'hidden', textOverflow: 'ellipsis' }}>{o.nombre}</span>
                              {o._agregado && <span style={{ display: 'block', fontSize: 9.5, color: o.pieza ? 'var(--text-muted)' : 'var(--warning, #f5a524)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {o.pieza ? `en ${o.pieza}` : 'sin pieza'}
                              </span>}
                            </span>
                            {o._agregado && <span onClick={(e) => { e.stopPropagation(); borrarObjetoAgregado(o._oid); }} title="Borrar este objeto"
                              style={{ flexShrink: 0, fontSize: 12, color: 'var(--text-muted)', padding: '2px 4px', cursor: 'pointer' }}>✕</span>}
                          </button>
                        ))}
                        {/* Acciones del objeto AGREGADO seleccionado: un objeto vive en UNA pieza.
                            Para ponerlo en otra: se quita de la actual (y se recoloca), o se DUPLICA. */}
                        {(() => {
                          // Objeto YA INYECTADO en el arte (es una capa del diseño): la única acción
                          // propia es SACARLO del arte — el resto (mover/rotar/escalar) es igual que
                          // cualquier editable, y de la pieza no se lo puede "quitar" sin borrar la capa.
                          const _iny = editableSel.length === 1
                            ? _objsUnicos.find(o => o.nombre === editableSel[0] && o.quitable) : null;
                          if (_iny) return (
                            <div style={{ display: 'flex', gap: 5, marginTop: 2 }}>
                              <button type="button" title="Saca este objeto del diseño (borra su capa del arte)"
                                onClick={() => quitarObjetoDelArte(_iny.capa || _iny.nombre)}
                                style={{ flex: 1, padding: '6px', borderRadius: 8, cursor: 'pointer', fontSize: 10.5, fontWeight: 700,
                                  border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)' }}>
                                Quitar del diseño
                              </button>
                            </div>
                          );
                          const _sel = editableSel.length === 1 ? _objsUnicos.find(o => o.nombre === editableSel[0] && o._agregado) : null;
                          if (!_sel) return null;
                          const _bs = { flex: 1, padding: '6px 6px', borderRadius: 8, cursor: 'pointer', fontSize: 10.5, fontWeight: 700,
                            border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-secondary)' };
                          return (
                            <div style={{ display: 'flex', gap: 5, marginTop: 2 }}>
                              {_sel.pieza
                                ? <button type="button" style={_bs} title="Lo saca de la pieza pero queda acá para colocarlo en otra"
                                    onClick={() => quitarObjetoDePieza(_sel._oid)}>Quitar de pieza</button>
                                : <button type="button" style={{ ..._bs, borderColor: 'var(--accent)', color: 'var(--accent)' }} title="Tocá el diseño para colocarlo"
                                    onClick={() => recolocarObjeto(_sel)}>Colocar</button>}
                              <button type="button" style={_bs} title="Una copia para poder usarlo TAMBIÉN en otra pieza"
                                onClick={() => duplicarObjetoAgregado(_sel._oid)}>Duplicar</button>
                            </div>
                          );
                        })()}
                        {/* AGREGAR OBJETO: PNG/SVG/PDF/AI → entra como un editable más */}
                        <input type="file" ref={fileInputObjetoRef} accept=".png,.svg,.pdf,.ai,.jpg,.jpeg" hidden
                          onChange={(e) => { const f = e.target.files[0]; e.target.value = ''; agregarObjeto(f); }} />
                        <button type="button" onClick={() => fileInputObjetoRef.current && fileInputObjetoRef.current.click()} disabled={subiendoObjeto}
                          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7, padding: '9px 8px', borderRadius: 9, cursor: subiendoObjeto ? 'wait' : 'pointer',
                            fontSize: 12.5, fontWeight: 800, border: '1px dashed var(--accent)', background: 'rgba(0,243,255,0.06)', color: 'var(--accent)' }}>
                          <Icon name="plus" style={{ width: 13, height: 13 }} /> {subiendoObjeto ? 'Subiendo…' : 'Agregar objeto'}
                        </button>
                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>Arrastrá para mover · manija de arriba rota · esquina escala. Agregá PNG/SVG/PDF/AI.</div>
                      </div>
                      {/* visor — rueda = zoom · click derecho arrastrado = mover el espacio */}
                      <div onWheel={edWheel} onMouseDown={edFondo} onContextMenu={(e) => e.preventDefault()}
                        style={{ flex: 1, minHeight: 0, background: 'rgba(0,0,0,0.35)', borderRadius: 12, border: '1px solid var(--border-light)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: objPendiente ? 'crosshair' : undefined }}>
                        <svg ref={editorSvgRef} viewBox={`${_edVBnow.x} ${_edVBnow.y} ${_edVBnow.w} ${_edVBnow.h}`} preserveAspectRatio="xMidYMid meet" style={{ width: '100%', height: '100%', display: 'block', userSelect: 'none' }}>
                          {_piezasEd.map(p => {
                            const vo = _voDe(p);
                            // FONDO = el diseño real (no editable): SVG de la mesa mapeada (detectar_arte
                            // ya oculta los editables), colocado con el encaje del diseño y recortado al
                            // contorno → editás sobre el diseño, viendo dónde cae cada objeto.
                            const _pn = etqNombres[p.idx] || p.name || '';
                            // ARTE POR RANGO: el fondo del editor muestra el diseño del TALLE en vista (T)
                            const _mi = (mapeoData?.mapeo_talles?.[_pn]?.[T]) || mapeoValores[_pn];
                            const _mesa = _mi ? (mapeoData?.mesas || []).find(m => m.mesa === parseInt(_mi)) : null;
                            const _asp = _mesa ? (_mesa.aspecto || (_mesa.w_cm && _mesa.h_cm ? _mesa.w_cm / _mesa.h_cm : p.pw / p.ph)) : (p.pw / p.ph);
                            const _iH = p.ph, _iW = _asp * _iH, _iX = p.px + (p.pw - _iW) / 2, _iY = p.py;
                            return (
                            <g key={p.idx} transform={(vo.dx || vo.dy) ? `translate(${vo.dx} ${vo.dy})` : undefined}>
                              <defs><clipPath id={`edclip-${p.idx}`}><path d={p.path_svg} /></clipPath></defs>
                              {_mesa?.svg && <image href={`data:image/svg+xml;base64,${_mesa.svg}`} x={_iX} y={_iY} width={_iW} height={_iH} preserveAspectRatio="none" clipPath={`url(#edclip-${p.idx})`} opacity={0.92} />}
                              <path d={p.path_svg} vectorEffect="non-scaling-stroke" fill={_mesa?.svg ? 'none' : 'rgba(0,243,255,0.04)'} stroke="rgba(0,243,255,0.5)" strokeWidth="1.1" />
                            </g>
                          ); })}
                          {_objsEd.map(o => {
                            // marco "pieza" (agregados) no usa mesa_rect/bbox_mu: los resuelve `marcoDeObjeto`.
                            const p = piezaDe(o.pieza);
                            if (!p || (!o._agregado && (!o.mesa_rect || !o.bbox_mu))) return null;
                            const vo = _voDe(p);
                            const tf = curTfOf(o.nombre, T); const c = centerOf(o, p, tf); const sel = editableSel.includes(o.nombre); const solo = sel && editableSel.length === 1;
                            return (
                              <g key={o.nombre} transform={(vo.dx || vo.dy) ? `translate(${vo.dx} ${vo.dy})` : undefined}>
                                <g clipPath={`url(#edclip-${p.idx})`}>
                                  <g transform={`rotate(${tf.rot} ${c.cx} ${c.cy})` + ((c.sgx < 0 || c.sgy < 0) ? ` translate(${c.cx} ${c.cy}) scale(${c.sgx} ${c.sgy}) translate(${-c.cx} ${-c.cy})` : '')}>
                                    <image href={o.svg ? `data:image/svg+xml;base64,${o.svg}` : `data:image/png;base64,${o.thumb}`} x={c.cx - c.w / 2} y={c.cy - c.h / 2} width={c.w} height={c.h} preserveAspectRatio="none" onMouseDown={(e) => start(e, 'move', o, p)} style={{ cursor: 'move' }} />
                                  </g>
                                </g>
                                {sel && (
                                  <g transform={`rotate(${tf.rot} ${c.cx} ${c.cy})`}>
                                    <rect x={c.cx - c.w / 2} y={c.cy - c.h / 2} width={c.w} height={c.h} fill="none" stroke="var(--accent)" strokeWidth={1.6} strokeDasharray={solo ? undefined : '5 4'} />
                                    {/* manijas SOLO con un objeto seleccionado (con varios se alinea desde el panel) */}
                                    {solo && <>
                                      <line x1={c.cx} y1={c.cy - c.h / 2} x2={c.cx} y2={c.cy - c.h / 2 - 26} stroke="var(--accent)" strokeWidth={1.6} />
                                      <circle cx={c.cx} cy={c.cy - c.h / 2 - 26} r={7} fill="#fff" stroke="var(--accent)" strokeWidth={2.5} onMouseDown={(e) => start(e, 'rot', o, p)} style={{ cursor: 'grab' }} />
                                      <circle cx={c.cx + c.w / 2} cy={c.cy + c.h / 2} r={7} fill="var(--accent)" onMouseDown={(e) => start(e, 'scale', o, p)} style={{ cursor: 'nwse-resize' }} />
                                    </>}
                                  </g>
                                )}
                              </g>
                            );
                          })}
                        </svg>
                      </div>
                      {/* ── PANEL DERECHO: herramientas de edición (estilo Illustrator) ── */}
                      <div style={{ width: 208, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', paddingLeft: 10, borderLeft: '1px solid var(--border-light)' }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                      {/* ARTE POR RANGO/TALLE: el espacio de edición es POR GRUPO del arte (un chip
                          por rango #XS-L / por talle #M); elegirlo muestra SUS editables y el ajuste
                          se aplica a sus talles. Arte de una sola mesa → picker de variantes normal. */}
                      {_porGrupos ? (<>
                        <span style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginLeft: 10 }}>{_grupos.some(g => g.talles.length > 1) ? 'Rango del arte:' : 'Talle del arte:'}</span>
                        {_grupos.map(g => {
                          const on = _grpAct === g;
                          return (
                            <button key={g.label} type="button" onClick={() => { setEditableVarsSel(g.talles); setEditableTalle(g.talles[0]); verVarianteOperario(g.talles[0]); }}
                              style={{ padding: '5px 12px', borderRadius: 999, fontSize: 12, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{g.label}</button>
                          );
                        })}
                      </>) : (<>
                        {/* Variantes: popup de tarjetas (elegís 1, varias o todas; Shift entre 2 = el rango).
                            Lo elegido es el ALCANCE (a qué variantes se aplica); el visor muestra la 1ª. */}
                        <span style={{ fontSize: 11.5, color: 'var(--text-secondary)', marginLeft: 10 }}>Variantes:</span>
                        <button type="button" onClick={() => setEditVarPickerOpen(true)} style={{ ...selStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
                          {_selResumen} <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>▾</span>
                        </button>
                        {editVarPickerOpen && (
                          <VariantesPicker variantes={talles} seleccion={_selT} bloqueadas={[]}
                            onChange={(ns) => { setEditableVarsSel(ns); const f = ns[0]; if (f && f !== T) { setEditableTalle(f); verVarianteOperario(f); } }}
                            onClose={() => setEditVarPickerOpen(false)} />
                        )}
                      </>)}
                        </div>
                    {/* TALLE en vista + ALCANCE del ajuste: por defecto va a TODO el rango; se puede
                        elegir aplicarlo SOLO al talle que estás viendo (excepción puntual). */}
                    {_rangoTalles.length > 1 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, flexShrink: 0, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>{edSoloTalle ? 'Editar talle:' : 'Ver talle:'}</span>
                        {_rangoTalles.map(t => (
                          <button key={t} type="button" onClick={() => { setEditableTalle(t); verVarianteOperario(t); }}
                            style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (T === t ? 'var(--accent)' : 'var(--border-light)'), background: T === t ? 'rgba(0,243,255,0.12)' : 'transparent', color: T === t ? 'var(--accent)' : 'var(--text-muted)' }}>{t}</button>
                        ))}
                        {/* Aplicar a: TODO EL RANGO (default) | SOLO ESTE TALLE */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 10, paddingLeft: 10, borderLeft: '1px solid var(--border-light)' }}>
                          <span style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>Aplicar a:</span>
                          {/* El conteo es el ALCANCE REAL del objeto seleccionado (los talles que
                              muestran el mismo diseño para SU pieza), no el del grupo global. */}
                          {[{ k: false, l: `Todo el rango (${(editableSel.length === 1 ? tallesDeObjeto(editableSel[0]) : _rangoTalles).length})` }, { k: true, l: `Solo ${T || 'este talle'}` }].map(op => (
                            <button key={String(op.k)} type="button" onClick={() => setEdSoloTalle(op.k)}
                              title={op.k ? 'El cambio se guarda SOLO en este talle; el resto del rango queda como está' : 'El cambio se guarda en todos los talles del rango'}
                              style={{ padding: '4px 11px', borderRadius: 999, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', transition: 'all .15s',
                                border: '1px solid ' + (edSoloTalle === op.k ? 'var(--accent)' : 'var(--border-light)'),
                                background: edSoloTalle === op.k ? 'var(--accent)' : 'transparent',
                                color: edSoloTalle === op.k ? '#001016' : 'var(--text-muted)' }}>{op.l}</button>
                          ))}
                        </div>
                        <span style={{ fontSize: 10.5, color: edSoloTalle ? 'var(--accent)' : 'var(--text-muted)' }}>
                          {edSoloTalle ? `· el ajuste va SOLO a ${T}` : '· el ajuste va a todo el rango'}
                        </span>
                      </div>
                    )}
                    {/* MEDIDAS del objeto seleccionado: An./Al. REALES en cm (del diseño) + enlace de
                        proporción (como Illustrator). Con el enlace ON escala proporcional; OFF deja
                        ancho y alto libres (sx/sy independientes → el motor deforma igual). */}
                    {(() => {
                      const _o = editableSel.length === 1 ? _objsUnicos.find(o => o.nombre === editableSel[0]) : null;
                      if (!_o || !(_o.w_cm > 0) || !(_o.h_cm > 0)) return null;
                      const _tf = curTfOf(_o.nombre, T);
                      const _wCm = _o.w_cm * _SX(_tf), _hCm = _o.h_cm * _SY(_tf);
                      const _aplicar = (patch) => { setTfScoped(_o.nombre, patch); setTimeout(() => histCommit(editorTfsRef.current), 0); };
                      const _setW = (v) => { const n = parseFloat(String(v).replace(',', '.')); if (!(n > 0)) return; const f = Math.max(0.1, Math.min(8, n / _o.w_cm)); _aplicar(edLink ? { scale: f, sx: f, sy: f } : { sx: f }); };
                      const _setH = (v) => { const n = parseFloat(String(v).replace(',', '.')); if (!(n > 0)) return; const f = Math.max(0.1, Math.min(8, n / _o.h_cm)); _aplicar(edLink ? { scale: f, sx: f, sy: f } : { sy: f }); };
                      const _inp = { width: 74, padding: '5px 7px', borderRadius: 7, background: 'rgba(0,0,0,0.35)', border: '1px solid var(--border-light)', color: '#fff', fontSize: 12.5, fontWeight: 700, textAlign: 'right', outline: 'none' };
                      const _lbl = { display: 'flex', alignItems: 'center', gap: 5, fontSize: 11.5, color: 'var(--text-secondary)' };
                      return (
                        <div style={{ marginBottom: 4, flexShrink: 0 }}>
                          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-secondary)', letterSpacing: 0.4, marginBottom: 7 }}>TAMAÑO</div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, flex: 1 }}>
                          <label style={_lbl}><span style={{ width: 20 }}>An.</span>
                            <input key={`w|${_o.nombre}|${T}|${_wCm.toFixed(2)}`} defaultValue={_wCm.toFixed(2)}
                              onBlur={(e) => _setW(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }} style={_inp} /> cm
                          </label>
                          <label style={_lbl}><span style={{ width: 20 }}>Al.</span>
                            <input key={`h|${_o.nombre}|${T}|${_hCm.toFixed(2)}`} defaultValue={_hCm.toFixed(2)}
                              onBlur={(e) => _setH(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }} style={_inp} /> cm
                          </label>
                          </div>
                          <button type="button" onClick={() => setEdLink(v => !v)}
                            title={edLink ? 'Proporción ENLAZADA: al cambiar uno, el otro acompaña' : 'Proporción LIBRE: ancho y alto independientes (deforma)'}
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 26, borderRadius: 7, cursor: 'pointer', transition: 'all .15s',
                              border: '1px solid ' + (edLink ? 'var(--accent)' : 'var(--border-light)'),
                              background: edLink ? 'var(--accent)' : 'rgba(255,255,255,0.04)', color: edLink ? '#001016' : 'var(--text-muted)' }}>
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                              <path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7" />
                              <path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7" />
                              {!edLink && <line x1="3" y1="21" x2="21" y2="3" stroke="#ff6b6b" strokeWidth="2.2" />}
                            </svg>
                          </button>
                          </div>
                          <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6 }}>
                            <b style={{ color: 'var(--accent)' }}>{_o.nombre}</b> · {_o.w_cm}×{_o.h_cm} cm al 100%
                          </div>
                        </div>
                      );
                    })()}
                    {/* ── ROTAR y ESPEJAR: aplican a TODOS los objetos seleccionados ── */}
                    {editableSel.length > 0 && (() => {
                      const _bt = { flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, height: 28, borderRadius: 7, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.04)', color: '#fff', cursor: 'pointer', fontSize: 11, fontWeight: 700 };
                      return (
                        <div style={{ flexShrink: 0 }}>
                          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-secondary)', letterSpacing: 0.4, marginBottom: 7 }}>
                            ROTAR {editableSel.length > 1 && <span style={{ color: 'var(--accent)' }}>({editableSel.length})</span>}
                          </div>
                          {/* Desplegable propio (no <select> nativo) con varios ángulos; rota lo elegido */}
                          <div style={{ position: 'relative', marginBottom: 6 }}>
                            <button type="button" onClick={() => setEdRotOpen(v => !v)} style={{ ..._bt, width: '100%', justifyContent: 'space-between', padding: '0 9px' }}>
                              <span>Rotar por ángulo…</span><span style={{ fontSize: 9, color: 'var(--text-muted)' }}>▾</span>
                            </button>
                            {edRotOpen && (
                              <div style={{ position: 'absolute', top: 31, left: 0, right: 0, zIndex: 30, background: '#15151a', border: '1px solid var(--border-light)', borderRadius: 8, maxHeight: 190, overflowY: 'auto', boxShadow: '0 10px 24px rgba(0,0,0,0.55)' }}>
                                {[-180, -135, -120, -90, -60, -45, -30, -22.5, -15, -10, -5, 5, 10, 15, 22.5, 30, 45, 60, 90, 120, 135, 180].map(a => (
                                  <div key={a} onClick={() => { _rotarSel(a); setEdRotOpen(false); }}
                                    style={{ padding: '5px 10px', fontSize: 12, cursor: 'pointer', color: a < 0 ? '#ffb36b' : 'var(--text-secondary)' }}
                                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.07)'}
                                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                                    {a > 0 ? `↻ +${a}°` : `↺ ${a}°`}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                          <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
                            <button type="button" style={_bt} onClick={() => _rotarSel(-90)} title="Rotar 90° antihorario">↺ 90°</button>
                            <button type="button" style={_bt} onClick={() => _rotarSel(90)} title="Rotar 90° horario">↻ 90°</button>
                            <button type="button" style={_bt} onClick={() => aplicarTf(editableSel, () => ({ rot: 0 }))} title="Volver a 0°">0°</button>
                          </div>
                          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-secondary)', letterSpacing: 0.4, margin: '10px 0 7px' }}>ESPEJAR</div>
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button type="button" style={_bt} onClick={() => _espejarSel('h')} title="Espejar horizontal (izquierda ↔ derecha)">
                              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M12 3v18" strokeDasharray="3 3" /><path d="M9 7 4 12l5 5z" fill="currentColor" /><path d="M15 7l5 5-5 5z" /></svg>
                              Horiz.
                            </button>
                            <button type="button" style={_bt} onClick={() => _espejarSel('v')} title="Espejar vertical (arriba ↔ abajo)">
                              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M3 12h18" strokeDasharray="3 3" /><path d="M7 9l5-5 5 5z" fill="currentColor" /><path d="M7 15l5 5 5-5z" /></svg>
                              Vert.
                            </button>
                          </div>
                        </div>
                      );
                    })()}
                        <div>
                          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-secondary)', letterSpacing: 0.4, marginBottom: 7 }}>ALINEAR</div>
                          {/* Modo: entre la SELECCIÓN o contra la MESA DE TRABAJO */}
                          <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
                            {[{ k: false, l: 'Con selección' }, { k: true, l: 'Con mesa' }].map(op => (
                              <button key={String(op.k)} type="button" onClick={() => setEdAlinearMesa(op.k)}
                                title={op.k ? 'Alinear respecto del diseño (mesa de trabajo)' : 'Alinear los objetos seleccionados ENTRE SÍ'}
                                style={{ flex: 1, padding: '4px 6px', borderRadius: 7, fontSize: 10.5, fontWeight: 700, cursor: 'pointer', transition: 'all .15s',
                                  border: '1px solid ' + (edAlinearMesa === op.k ? 'var(--accent)' : 'var(--border-light)'),
                                  background: edAlinearMesa === op.k ? 'var(--accent)' : 'transparent', color: edAlinearMesa === op.k ? '#001016' : 'var(--text-muted)' }}>{op.l}</button>
                            ))}
                          </div>
                          {/* Íconos de alineación estándar: la LÍNEA es la referencia y las dos BARRAS
                              (una larga y una corta) muestran cómo quedan los objetos respecto de ella. */}
                          {[[['izq', 'Alinear a la izquierda', <><line x1="3" y1="3" x2="3" y2="21" /><rect x="6" y="6" width="14" height="4.6" rx="1" /><rect x="6" y="13.4" width="8.5" height="4.6" rx="1" /></>],
                             ['ch', 'Centrar horizontal', <><line x1="12" y1="3" x2="12" y2="21" /><rect x="5" y="6" width="14" height="4.6" rx="1" /><rect x="7.75" y="13.4" width="8.5" height="4.6" rx="1" /></>],
                             ['der', 'Alinear a la derecha', <><line x1="21" y1="3" x2="21" y2="21" /><rect x="4" y="6" width="14" height="4.6" rx="1" /><rect x="9.5" y="13.4" width="8.5" height="4.6" rx="1" /></>]],
                            [['arr', 'Alinear arriba', <><line x1="3" y1="3" x2="21" y2="3" /><rect x="6" y="6" width="4.6" height="14" rx="1" /><rect x="13.4" y="6" width="4.6" height="8.5" rx="1" /></>],
                             ['cv', 'Centrar vertical', <><line x1="3" y1="12" x2="21" y2="12" /><rect x="6" y="5" width="4.6" height="14" rx="1" /><rect x="13.4" y="7.75" width="4.6" height="8.5" rx="1" /></>],
                             ['aba', 'Alinear abajo', <><line x1="3" y1="21" x2="21" y2="21" /><rect x="6" y="4" width="4.6" height="14" rx="1" /><rect x="13.4" y="9.5" width="4.6" height="8.5" rx="1" /></>]]].map((fila, fi) => (
                            <div key={fi} style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                              {fila.map(([eje, tit, ico]) => (
                                <button key={eje} type="button" onClick={() => _alinear(eje)} title={tit}
                                  disabled={editableSel.length === 0 || (!edAlinearMesa && editableSel.length < 2)}
                                  style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', height: 30, borderRadius: 7,
                                    border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.04)',
                                    color: (editableSel.length === 0 || (!edAlinearMesa && editableSel.length < 2)) ? 'var(--text-muted)' : '#fff',
                                    cursor: (editableSel.length === 0 || (!edAlinearMesa && editableSel.length < 2)) ? 'not-allowed' : 'pointer', opacity: (editableSel.length === 0 || (!edAlinearMesa && editableSel.length < 2)) ? 0.45 : 1 }}>
                                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" stroke="currentColor" strokeWidth="2" strokeLinecap="round">{ico}</svg>
                                </button>
                              ))}
                            </div>
                          ))}
                          <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.4 }}>
                            {editableSel.length === 0 ? 'Elegí un objeto.'
                              : !edAlinearMesa && editableSel.length < 2 ? 'Para alinear entre sí elegí 2 o más (Ctrl+click).'
                                : edAlinearMesa ? `${editableSel.length} objeto/s → se alinean con la mesa.`
                                  : `${editableSel.length} objetos → se alinean entre sí.`}
                          </div>
                        </div>
                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', borderTop: '1px solid var(--border-light)', paddingTop: 9, lineHeight: 1.45 }}>
                          <b style={{ color: 'var(--text-secondary)' }}>Selección</b><br />
                          Click = uno · <b>Ctrl/Shift+click</b> = sumar varios.<br />
                          Con varios, arrastrar los mueve <b>juntos</b>.
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* Ventana "Asignando el diseño a cada variante…" (al cargar el arte, una sola vez) */}
              {asignando && (
                <div style={{ position: 'fixed', inset: 0, zIndex: 3000, background: 'rgba(2,6,12,0.82)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ background: '#141416', border: '1px solid var(--border-light)', borderRadius: 14, padding: '26px 36px', textAlign: 'center', minWidth: 340 }}>
                    <div style={{ fontSize: 15.5, fontWeight: 700, marginBottom: 8 }}>Asignando el diseño a cada variante…</div>
                    <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 14 }}>
                      {asignando.talle ? `Variante ${asignando.talle}` : ''} · {asignando.hecho}/{asignando.total}
                    </div>
                    <div style={{ height: 8, borderRadius: 999, background: 'rgba(255,255,255,0.08)', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.round(100 * asignando.hecho / Math.max(1, asignando.total))}%`, background: 'var(--accent)', borderRadius: 999, transition: 'width .3s' }} />
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 12 }}>Es una sola vez por diseño: después el cambio de variante es instantáneo.</div>
                  </div>
                </div>
              )}

            </div>
            )}

            {/* Paso 5 · Resultados: una mesa por molde + descargar todo (ZIP) */}
            {pedidoPaso === 'resultados' && trabajosMulti.length === 0 && (
              <div className="card animate-fade" style={{ marginTop: 8, padding: 20 }}>
                <div className="card-title" style={{ margin: 0 }}>5 · Tizadas</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '14px 0' }}>No hay ninguna tizada en curso.</div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={() => setPedidoPaso('planilla')}>← Volver a la planilla</button>
                  <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5, color: 'var(--text-secondary)' }} onClick={reiniciarPedido}>↺ Nuevo pedido</button>
                </div>
              </div>
            )}
            {pedidoPaso === 'resultados' && trabajosMulti.length > 0 && (
              <div className="card animate-fade" style={{ marginTop: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                  <div className="card-title" style={{ margin: 0 }}>
                    5 · Tizadas armadas
                    {trabajosMulti.some(t => t.estado === 'generando' || t.estado === 'en cola') && <span className="badge warning" style={{ marginLeft: 10 }}>Procesando</span>}
                  </div>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={() => setPedidoPaso('planilla')}>← Atrás</button>
                    {(() => {
                      const j = trabajosMulti[0];
                      const hojas = (j?.estado === 'listo' && j?.resultado?.hojas) || [];
                      if (!hojas.length) return null;
                      const totalMesas = hojas.reduce((s, h) => s + ((h.previews && h.previews.length) ? h.previews.length : 1), 0);
                      const sanit = (s) => ((s || 'mesa').replace(/[\\/:*?"<>|\n\r\t]+/g, '_').trim() || 'mesa');
                      return (
                        <button className="btn primary" style={{ padding: '8px 14px', fontSize: 12.5 }}
                          onClick={async () => {
                            // Descarga CADA MESA por separado (una página = un archivo), con su NOMBRE,
                            // aunque varias sean del mismo PDF/tela. Usa los nombres editados (localStorage).
                            const nombres = (() => { try { return JSON.parse(localStorage.getItem('tizada_mesas_nombres_' + j.resultado.id) || '{}'); } catch (_e) { return {}; } })();
                            for (const tl of [...new Set(hojas.map(h => h.tela))]) {
                              let gi = 0;
                              for (const h of hojas.filter(x => x.tela === tl)) {
                                const pvs = (h.previews && h.previews.length) ? h.previews : [null];
                                for (let pi = 0; pi < pvs.length; pi++) {
                                  const nombre = nombres[h.archivo + '::' + pi] != null ? nombres[h.archivo + '::' + pi] : ('Mesa ' + (gi + 1) + (tl ? ' - ' + tl : ''));
                                  gi++;
                                  const a = document.createElement('a');
                                  a.href = `/api/trabajos/${j.resultado.id}/mesa/${h.archivo}?pi=${pi}&nombre=${encodeURIComponent(sanit(nombre))}`;
                                  a.download = sanit(nombre) + '.pdf';
                                  document.body.appendChild(a); a.click(); a.remove();
                                  await new Promise(r => setTimeout(r, 500));
                                }
                              }
                            }
                          }}>
                          <Icon name="download" style={{ width: 13, height: 13 }} /> Descargar todo ({totalMesas})
                        </button>
                      );
                    })()}
                    <button className="btn ghost" style={{ padding: '8px 14px', fontSize: 12.5 }} onClick={reiniciarPedido} title="Empezar un pedido nuevo desde 0">↺ Nuevo pedido</button>
                  </div>
                </div>

                {(() => {
                  const job = trabajosMulti[0];
                  if (!job) return null;
                  if (job.estado === 'error') return <div style={{ color: 'var(--error)', fontSize: 13, marginTop: 14 }}>{job.error}</div>;
                  if (job.estado !== 'listo') {
                    const det = getProgresoDetalle(job.progreso, job.estado);
                    return <TizadaLoader det={det} />;
                  }
                  const hojas = job.resultado?.hojas || [];
                  const telas = [...new Set(hojas.map(h => h.tela))];
                  const tela = (telaActiva && telas.includes(telaActiva)) ? telaActiva : telas[0];
                  const mesas = hojas.filter(h => h.tela === tela);   // mesas de esa tela (una por grupo)
                  const avisos = job.resultado?.avisos || [];
                  return (
                    <div style={{ marginTop: 16 }}>
                      {/* AVISO: piezas que salieron EN BLANCO por no tener diseño (la tizada SÍ se generó) */}
                      {avisos.length > 0 && (
                        <div style={{ display: 'flex', gap: 11, alignItems: 'flex-start', marginBottom: 16, padding: '13px 16px', borderRadius: 12, background: 'rgba(180,120,0,0.12)', border: '1px solid var(--warning, #e0a020)' }}>
                          <Icon name="alert" style={{ width: 19, height: 19, color: 'var(--warning, #e0a020)', flexShrink: 0, marginTop: 1 }} />
                          <div style={{ fontSize: 13, color: 'var(--warning, #e0a020)', lineHeight: 1.5 }}>
                            <b>Algunas piezas salieron en blanco.</b> La tizada se generó, pero estas piezas no tienen diseño (van con su borde de corte, sin gráfica):
                            <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
                              {avisos.map((a, i) => <li key={i} style={{ marginTop: 2 }}>{a}</li>)}
                            </ul>
                            <div style={{ marginTop: 6, color: 'var(--text-secondary)', fontSize: 12.5 }}>Si querés que lleven gráfica, agregá su mesa en el arte y volvé a generar.</div>
                          </div>
                        </div>
                      )}
                      {/* Pestañas de TELA: solo si hay más de una tela */}
                      {telas.length > 1 && (
                        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', borderBottom: '1px solid var(--border-light)', paddingBottom: 12 }}>
                          {telas.map(tl => (
                            <button key={tl} type="button" onClick={() => setTelaActiva(tl)}
                              className={'chip' + (tl === tela ? ' active' : '')} style={{ padding: '9px 18px', cursor: 'pointer', fontWeight: 700, fontSize: 13 }}>{tl}</button>
                          ))}
                        </div>
                      )}
                      {/* ESPACIO INFINITO de las mesas (componente propio: zoom con rueda sin scrollear
                          la página, pan con click DERECHO, nombre renombrable, descarga con ese nombre). */}
                      <MesasInfinito mesas={mesas} job={job} />
                    </div>
                  );
                })()}
              </div>
            )}

            {/* Job Execution & Results */}
            {trabajoEstado && (
              <div className="card animate-fade" style={{ marginTop: 24 }}>
                <div className="card-title">
                  Estado del Trabajo
                  {trabajoId && <span className="badge warning" style={{ marginLeft: 10 }}>Procesando</span>}
                </div>
                
                {trabajoEstado.estado === 'generando' || trabajoEstado.estado === 'en cola' ? (() => {
                  const det = getProgresoDetalle(trabajoEstado.progreso, trabajoEstado.estado);
                  return <TizadaLoader det={det} />;
                })() : trabajoEstado.estado === 'error' ? (
                  <div style={{ color: 'var(--error)', marginTop: 8, display: 'flex', gap: 10, alignItems: 'center' }}>
                    <Icon name="alert" style={{ width: 18, height: 18 }} />
                    <span>Error al generar: {trabajoEstado.error}</span>
                  </div>
                ) : trabajoEstado.estado === 'listo' ? (
                  <div style={{ marginTop: 16 }} className="animate-fade">
                    <div className="card-title" style={{ fontSize: 15, marginBottom: 12 }}>Tizada Completa</div>
                    
                    {/* Render sheets */}
                    {trabajoEstado.resultado?.hojas?.map((hoja, k) => (
                      <div key={k} className="hoja" style={{ border: '1px solid var(--border-light)', borderRadius: 12, padding: 16, backgroundColor: 'rgba(255,255,255,0.01)', marginBottom: 16 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 12 }}>
                          <span style={{ fontWeight: 700, fontSize: 14 }}>Tela {hoja.tela}</span>
                          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            {hoja.paginas} pág(s) · {(hoja.consumo_cm / 100).toFixed(2)} m · {hoja.aprovechamiento}% eficiencia
                          </span>
                          <a 
                            href={`/trabajos/${trabajoEstado.resultado.id}/${hoja.archivo}`} 
                            download 
                            className="btn" 
                            style={{ padding: '6px 12px', fontSize: 12, marginLeft: 'auto' }}
                          >
                            <Icon name="download" style={{ width: 12, height: 12 }} /> Descargar PDF
                          </a>
                        </div>
                        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
                          {hoja.previews?.map((pv, pIdx) => (
                            <div 
                              key={pIdx} 
                              className="preview-thumbnail"
                              style={{ 
                                width: 100, 
                                height: 140, 
                                border: '1px solid var(--border-light)', 
                                borderRadius: 8, 
                                overflow: 'hidden', 
                                cursor: 'pointer',
                                transition: 'transform 0.2s, border-color 0.2s',
                                backgroundColor: '#fff',
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                padding: 4
                              }}
                              onClick={() => {
                                setZoomPreviewUrl(`/trabajos/${trabajoEstado.resultado.id}/${pv}`);
                                setZoomState({ zoom: 1.0, pan: { x: 0, y: 0 } });
                                setEsArrastrando(false);
                              }}
                              title="Click para ver a detalle (Vectorial)"
                            >
                              <img 
                                src={`/trabajos/${trabajoEstado.resultado.id}/${pv}`} 
                                alt="Preview" 
                                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} 
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}

                    <div className="card-title" style={{ fontSize: 14, marginTop: 24, marginBottom: 8 }}>Validaciones de Seguridad Imprenta</div>
                    <ul style={{ listStyle: 'none' }}>
                      {trabajoEstado.resultado?.validaciones?.map((val, vIdx) => (
                        <li key={vIdx} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px dashed var(--border-light)' }}>
                          <span style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
                            <span style={{ color: val.ok ? 'var(--success)' : 'var(--error)', fontWeight: 800 }}>
                              {val.ok ? "✓" : "✗"}
                            </span>
                            {val.nombre}
                          </span>
                      <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-secondary)' }}>{val.detalle}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Configuración Avanzada (CRM Dashboard & Subviews) */}
        {activoTab === 'config' && (
          <>
            {/* 1. CRM Dashboard */}
            {adminSubView === 'dashboard' && (
              <div className="panel animate-fade">
                <div className="panel-header">
                  <h2>Panel de Configuración</h2>
                  <p>Ajustes globales, catálogo de moldes, distribución de piezas y reglas de nesting.</p>
                </div>

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                  gap: '24px',
                  marginTop: '20px'
                }}>
                  {/* Card 1: Productos y Molderías */}
                  <div className="crm-config-card cyan" onClick={() => setAdminSubView('productos')}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="productos" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Moldería</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Molderías registradas: carga de moldes base (.ai) y etiquetado de piezas.
                      </p>
                    </div>
                  </div>

                  {/* Card 2: Planillas */}
                  <div className="crm-config-card magenta" onClick={() => setAdminSubView('columnas')}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="columnas" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Planillas</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        En este campo podras editar o crear nuevas planillas.
                      </p>
                    </div>
                  </div>

                  {/* Card 2b: Reglas de planilla — campos de personalización = capas del diseño */}
                  <div className="crm-config-card green" onClick={() => { setReglaEditando(null); setAdminSubView('reglas'); }}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="fuentes" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Reglas de planilla · Capas</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Acá creás los campos que se estampan (nombre, número, palabra, número 2…). Cada campo es una <b>capa</b> que debe tener el diseño — y acá ves cómo deben llamarse.
                      </p>
                    </div>
                  </div>

                  {/* Card 3: Telas (registro global + grupos combinables) */}
                  <div className="crm-config-card magenta" onClick={() => {
                    setAdminSubView('telas');
                    fetchTelas();
                  }}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="telas" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Telas</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Registrá tus telas (nombre + ancho) y armá grupos de telas que se pueden combinar entre sí.
                      </p>
                    </div>
                  </div>

                  {/* Card 4: Reglas de Nesting */}
                  <div className="crm-config-card cyan" onClick={() => {
                    setAdminSubView('nesting');
                    fetchConfig();
                  }}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="nesting" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Reglas de Nesting</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Configuración de márgenes, espaciado de costuras y políticas de rotación de moldes.
                      </p>
                    </div>
                  </div>

                  {/* Card 6: Catálogo de Fuentes */}
                  <div className="crm-config-card yellow" onClick={() => setAdminSubView('fuentes')}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="fuentes" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Catálogo de Fuentes</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Administración de tipografías TrueType cargadas para nombres/números en curvas.
                      </p>
                    </div>
                  </div>

                  {/* Card: Usuarios y permisos */}
                  <div className="crm-config-card cyan" onClick={() => setAdminSubView('usuarios')}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="user" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Usuarios y permisos</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Quién usa el sistema y qué puede hacer: usuarios, roles y permisos.
                      </p>
                    </div>
                  </div>

                  {/* Card: Perfil de color (ICC) */}
                  <div className="crm-config-card magenta" onClick={() => { fetchPerfiles(); setAdminSubView('perfil'); }}>
                    <div>
                      <div className="crm-icon-container">
                        <Icon name="distribucion" style={{ width: 18, height: 18 }} />
                      </div>
                      <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 12, color: 'var(--text-primary)' }}>Perfil de color</h3>
                      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Perfil ICC predeterminado para los diseños. Detecta y avisa el perfil incrustado al cargar un arte.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. Productos y Molderías Subview */}
            {adminSubView === 'productos' && (
              <div className="panel animate-fade">
                {!molderiaAbierta && (
                  <div style={{ marginBottom: 20 }}>
                    <button className="btn ghost" onClick={() => setAdminSubView('dashboard')} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
                      ⬅ Volver al Panel de Configuración
                    </button>
                  </div>
                )}

                {!molderiaAbierta ? (
                  <>
                    <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                      <div>
                        <h2>Moldería</h2>
                        <p>Tus molderías registradas. Hacé clic en una para configurar molde, diseño y planilla.</p>
                      </div>
                      <button className="btn primary" onClick={() => setCreandoProducto(true)}>
                        <Icon name="plus" style={{ width: 14, height: 14 }} /> Nueva Moldería
                      </button>
                    </div>

                    <div className="product-crm-grid" style={{ marginBottom: 24 }}>
                      {productosCat.productos.map(p => {
                        const esActivo = p.id === productosCat.activo;
                        return (
                          <div
                            key={p.id}
                            className={`product-card ${esActivo ? 'active' : ''}`}
                            onClick={() => { handleActivarProducto(p.id); setMolderiaAbierta(p.id); setTabAjustesMolde('menu'); }}
                          >
                            <div className="product-card-header">
                              <div className="product-card-title">{p.nombre}</div>
                              {esActivo && <div className="badge success" style={{ fontSize: 9 }}>Activo</div>}
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: -4, fontSize: 11, color: 'var(--text-muted)' }}>
                              <Icon name="productos" style={{ width: 12, height: 12 }} />
                              <span>variante: <b style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{p.terminologia?.variante || 'Talle'}</b></span>
                            </div>

                            <div className="product-card-status">
                              <span className={`badge ${p.plantilla ? 'success' : 'neutral'}`} style={{ fontSize: 9 }}>
                                {p.plantilla ? `${p.terminologia?.molde || 'Molde'} OK` : `Sin ${p.terminologia?.molde || 'Molde'}`}
                              </span>
                              <span className={`badge ${p.arte ? 'success' : 'neutral'}`} style={{ fontSize: 9 }}>
                                {p.arte ? "Diseño OK" : "Sin Diseño"}
                              </span>
                            </div>

                            <div className="product-card-actions">
                              <button
                                className="btn ghost"
                                style={{ padding: '4px 8px', fontSize: 11 }}
                                onClick={(e) => { e.stopPropagation(); handleRenombrarProducto(p.id, p.nombre); }}
                              >
                                <Icon name="edit" style={{ width: 11, height: 11 }} />
                              </button>
                              {p.id !== 'prod_default' && (
                                <button
                                  className="btn danger-ghost"
                                  style={{ padding: '4px 8px', fontSize: 11 }}
                                  onClick={(e) => handleEliminarProducto(p.id, e)}
                                >
                                  <Icon name="trash" style={{ width: 11, height: 11 }} />
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : activoProdDetalle && (
                  <>
                    <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                        {modoMiMolde ? (
                          /* Vino desde el PEDIDO: la salida natural es volver al pedido, no a la
                             grilla de molderías (que es pantalla de configuración/catálogo). */
                          <button className="btn primary" onClick={() => { setModoMiMolde(null); setMolderiaAbierta(null); setTabAjustesMolde('menu'); setAdminSubView('dashboard'); setActivoTab('pedidos'); setPedidoPaso('moldes'); setPedidoTabMoldes('mios'); }} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '8px 14px' }}>
                            ← Volver al pedido
                          </button>
                        ) : (
                          <button className="btn ghost" onClick={() => { setMolderiaAbierta(null); setTabAjustesMolde('menu'); }} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '8px 12px' }}>
                            ⬅ Molderías
                          </button>
                        )}
                        <div>
                          <h2 style={{ margin: 0 }}>{activoProdDetalle.nombre}{modoMiMolde ? <span style={{ fontSize: 11, fontWeight: 700, marginLeft: 10, padding: '2px 8px', borderRadius: 999, background: 'rgba(0,216,245,0.14)', color: 'var(--accent)', verticalAlign: 'middle' }}>MI ARTÍCULO</span> : null}</h2>
                          <p style={{ margin: 0 }}>{modoMiMolde ? 'Cargá los talles del molde e indicá qué es cada pieza. Después volvé al pedido.' : 'Configurá el molde, el diseño y la planilla de esta moldería.'}</p>
                        </div>
                      </div>
                    </div>

                    <div className="workspace-container animate-fade" style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 24, marginTop: 8, alignItems: 'start' }}>
                      {/* Barra lateral de Ajustes (Derecha) */}
                      <div className="card settings-sidebar" style={{ display: 'flex', flexDirection: 'column', gap: 14, height: 'fit-content', order: 2 }}>
                        {tabAjustesMolde === 'menu' ? (
                          <div className="settings-drawer" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: 2 }}>Ajustes de la moldería</div>
                            {/* En «mi molde» se saca Variables: el usuario no arma modelos/combinaciones
                                de un artículo propio — carga sus talles e indica qué es cada pieza. */}
                            {[
                              { id: 'molderia', icon: 'productos', label: 'Moldería', desc: 'Etiquetá las piezas del molde', disabled: false },
                              { id: 'variables', icon: 'columnas', label: 'Variables', desc: 'Modelos y combinaciones de piezas (el talle va aparte)', disabled: false },
                              { id: 'diseno', icon: 'distribucion', label: 'Plantilla', desc: 'Medidas de cada pieza y carga del diseño', disabled: false },
                              { id: 'planilla', icon: 'columnas', label: 'Planilla', desc: 'Vinculá las columnas del Excel', disabled: false },
                              { id: 'nestingsel', icon: 'nesting', label: 'Nesting', desc: 'Qué acomodo (separación/giro) usa este molde', disabled: false },
                              { id: 'telas', icon: 'telas', label: 'Telas asignadas', desc: 'Qué telas del registro están disponibles para este molde', disabled: false },
                              { id: 'borde', icon: 'distribucion', label: 'Borde de corte', desc: 'Si lleva borde, el color y el tamaño (mm)', disabled: false },
                              { id: 'etiqueta', icon: 'columnas', label: 'Etiqueta', desc: 'Qué muestra, dónde, en qué piezas, color y tamaño', disabled: false },
                              { id: 'editable', icon: 'distribucion', label: 'Editable', desc: 'Mover, rotar y escalar los objetos de la capa «Editable» del diseño', disabled: false },
                              { id: 'terminologia', icon: 'config', label: 'Nombres', desc: `Cómo se llaman ${term.variante.toLowerCase()} y ${term.molde.toLowerCase()}`, disabled: false },
                            ].filter(item => !(modoMiMolde && item.id === 'variables')).map(item => (
                              <button
                                key={item.id}
                                className="setting-nav-btn"
                                disabled={item.disabled}
                                onClick={() => { setTabAjustesMolde(item.id); if (item.id === 'diseno') setMapeandoDiseno(false); if (item.id === 'borde') cargarBorde(); if (item.id === 'etiqueta') { cargarEtiqueta(); cargarBorde(); } if (item.id === 'editable') cargarEditConfig(); }}
                              >
                                <span className="setting-nav-icon"><Icon name={item.icon} /></span>
                                <span className="setting-nav-text">
                                  <span className="setting-nav-label">{item.label}</span>
                                  <span className="setting-nav-desc">{item.desc}</span>
                                </span>
                                <Icon name="arrowRight" className="setting-nav-arrow" />
                              </button>
                            ))}
                          </div>
                        ) : (
                          <div key={tabAjustesMolde} className="settings-slide" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                            <button className="btn ghost" onClick={() => setTabAjustesMolde('menu')} style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, padding: '6px 10px' }}>
                              ⬅ Volver a ajustes
                            </button>

                      {/* Contenido según pestaña activa */}
                      {tabAjustesMolde === 'telas' && (() => {
                        const T = telasReg.telas || [];
                        const sel = new Set(telasAsigMolde);
                        const toggle = (id) => { const s = new Set(sel); s.has(id) ? s.delete(id) : s.add(id); setTelasAsigMolde([...s]); guardarTelasAsignadas(activoProdDetalle?.id, [...s]); };
                        return (
                          <div className="animate-fade" style={{ padding: 4 }}>
                            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Telas asignadas a este molde</h3>
                            <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 14, lineHeight: 1.5, maxWidth: 620 }}>
                              Elegí qué telas del registro están disponibles para este molde. En el pedido solo aparecerán estas (y las que combinen con la tela base). Las telas y los grupos se administran en <b>Configuración › Telas</b>.
                            </p>
                            {T.length === 0 ? (
                              <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: '16px 0' }}>No hay telas registradas todavía. Andá a Configuración › Telas para registrarlas.</div>
                            ) : (
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                {T.map(t => {
                                  const on = sel.has(t.id);
                                  return (
                                    <button key={t.id} type="button" onClick={() => toggle(t.id)}
                                      style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderRadius: 10, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--success)' : 'var(--border-light)'), background: on ? 'rgba(16,185,129,0.1)' : 'transparent', color: on ? 'var(--success)' : 'var(--text-secondary)', fontSize: 13, fontWeight: 600 }}>
                                      <span style={{ width: 9, height: 9, borderRadius: '50%', background: on ? 'var(--success)' : 'rgba(255,255,255,0.15)' }} />
                                      {t.nombre} <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>· {t.ancho_cm}cm</span>
                                    </button>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })()}
                      {tabAjustesMolde === 'borde' && (() => {
                        const bcLabel = { display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 6, color: 'var(--text-secondary)' };
                        const bcInput = { padding: '9px 11px', borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none', fontSize: 14, textAlign: 'center' };
                        const col = bordeConfig.color || [0, 0, 0, 0];
                        const css = `rgb(${Math.round(255 * (1 - col[0]) * (1 - col[3]))},${Math.round(255 * (1 - col[1]) * (1 - col[3]))},${Math.round(255 * (1 - col[2]) * (1 - col[3]))})`;
                        const setCol = (i, v) => { const c = [...col]; c[i] = Math.max(0, Math.min(100, parseFloat(v) || 0)) / 100; setBordeConfig({ ...bordeConfig, color: c }); };
                        return (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                              El <b>borde de corte</b> es la línea que rodea cada pieza en la tizada (guía para cortar). Elegí si lleva, su <b>color</b> y su <b>tamaño</b>.
                            </div>
                            <button type="button" onClick={() => setBordeConfig({ ...bordeConfig, activo: !bordeConfig.activo })}
                              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '11px 13px', borderRadius: 10, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)', cursor: 'pointer', color: '#fff' }}>
                              <span style={{ fontSize: 13, fontWeight: 600 }}>Lleva borde de corte</span>
                              <span style={{ width: 40, height: 23, borderRadius: 999, background: bordeConfig.activo ? 'var(--accent)' : 'rgba(255,255,255,0.16)', position: 'relative', transition: 'all .2s', flexShrink: 0 }}>
                                <span style={{ position: 'absolute', top: 2.5, left: bordeConfig.activo ? 19 : 2.5, width: 18, height: 18, borderRadius: '50%', background: '#fff', transition: 'all .2s' }} />
                              </span>
                            </button>
                            {bordeConfig.activo && (
                              <>
                                <div>
                                  <label style={bcLabel}>Tamaño del borde (mm)</label>
                                  <input type="number" min="0.2" max="20" step="0.1" value={bordeConfig.ancho_mm}
                                    onChange={(e) => setBordeConfig({ ...bordeConfig, ancho_mm: parseFloat(e.target.value) || 0 })}
                                    style={{ ...bcInput, width: 130 }} />
                                </div>
                                <div>
                                  <label style={bcLabel}>Color del borde (CMYK %)</label>
                                  <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
                                    {['C', 'M', 'Y', 'K'].map((lbl, i) => (
                                      <div key={lbl} style={{ textAlign: 'center' }}>
                                        <input type="number" min="0" max="100" value={Math.round((col[i] || 0) * 100)}
                                          onChange={(e) => setCol(i, e.target.value)} style={{ ...bcInput, width: 56 }} />
                                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 4, fontWeight: 700 }}>{lbl}</div>
                                      </div>
                                    ))}
                                    <div title="Aproximación en pantalla" style={{ width: 42, height: 42, borderRadius: 9, border: '1px solid var(--border-light)', marginLeft: 6, background: css, flexShrink: 0 }} />
                                  </div>
                                  <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 7, lineHeight: 1.4 }}>El default es negro 85% (0·0·0·85). La muestra es una aproximación en pantalla; el valor CMYK es el exacto que va al PDF.</div>
                                </div>
                              </>
                            )}
                            <button className="btn primary" onClick={() => guardarBorde()} style={{ marginTop: 4, alignSelf: 'flex-start', padding: '9px 18px' }}>Guardar borde</button>
                          </div>
                        );
                      })()}

                      {tabAjustesMolde === 'etiqueta' && etiquetaConfig && (() => {
                        const ec = etiquetaConfig;
                        const setEC = (patch) => setEtiquetaConfig({ ...ec, ...patch });
                        const lbl = { display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 6, color: 'var(--text-secondary)' };
                        const inp = { padding: '8px 10px', borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none', fontSize: 13.5, textAlign: 'center' };
                        const css = (c) => `rgb(${Math.round(255 * (1 - c[0]) * (1 - c[3]))},${Math.round(255 * (1 - c[1]) * (1 - c[3]))},${Math.round(255 * (1 - c[2]) * (1 - c[3]))})`;
                        const Sw = ({ on, onClick }) => (
                          <span onClick={onClick} style={{ width: 38, height: 22, borderRadius: 999, background: on ? 'var(--accent)' : 'rgba(255,255,255,0.16)', position: 'relative', cursor: 'pointer', transition: 'all .2s', flexShrink: 0 }}>
                            <span style={{ position: 'absolute', top: 2.5, left: on ? 18 : 2.5, width: 17, height: 17, borderRadius: '50%', background: '#fff', transition: 'all .2s' }} />
                          </span>
                        );
                        const chip = (txt, on, onClick) => (
                          <button key={txt} type="button" onClick={onClick} style={{ padding: '6px 12px', borderRadius: 999, fontSize: 12, fontWeight: 600, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'rgba(255,255,255,0.02)', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{txt}</button>
                        );
                        const swatchBtn = (val, titulo, onApply) => (
                          <button type="button" onClick={() => setPicker({ titulo, color: val, onApply })}
                            style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)', cursor: 'pointer', color: '#fff', width: '100%' }}>
                            <span style={{ width: 26, height: 26, borderRadius: 6, border: '1px solid var(--border-light)', background: css(val), flexShrink: 0 }} />
                            <span style={{ fontSize: 12.5 }}>Elegir color</span>
                            <span style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text-muted)', fontFamily: 'ui-monospace, monospace' }}>C{Math.round((val[0] || 0) * 100)} M{Math.round((val[1] || 0) * 100)} Y{Math.round((val[2] || 0) * 100)} K{Math.round((val[3] || 0) * 100)}</span>
                          </button>
                        );
                        const offSet = new Set((ec.piezas_off || []).map(nombreGenerico));   // por NOMBRE GENÉRICO (tolera datos viejos con número)
                        const pos = ec.posicion || { rx: 0.5, ry: 0.92 };
                        const align = ec.align || 'centro';
                        const anchorSvg = align === 'izquierda' ? 'start' : align === 'derecha' ? 'end' : 'middle';
                        const nombrePc = (pc) => etqNombres[pc.idx] || pc.name || 'Pieza';
                        const muestraDe = (pc) => [ec.mostrar.talle && '2XL', ec.mostrar.pieza && nombrePc(pc), ec.mostrar.numero && '#01'].filter(Boolean).join(ec.separador || '-') || '·';
                        const piezasVisor = canvasLayout?.layout?.filter(p => (etqNombres[p.idx] || p.name)) || [];
                        // Click sobre el contorno → posición relativa (rx,ry) en el bbox de esa pieza; se aplica a todas.
                        const onPickContorno = (e) => {
                          const svg = e.currentTarget;
                          let p; try { const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; p = pt.matrixTransform(svg.getScreenCTM().inverse()); } catch { return; }
                          const hit = piezasVisor.find(pc => p.x >= pc.px && p.x <= pc.px + pc.pw && p.y >= pc.py && p.y <= pc.py + pc.ph) || piezasVisor[0];
                          if (!hit) return;
                          setEtiquetaConfig(prev => ({ ...prev, posicion: { rx: Math.max(0, Math.min(1, (p.x - hit.px) / hit.pw)), ry: Math.max(0, Math.min(1, (p.y - hit.py) / hit.ph)) } }));
                        };
                        return (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                              La <b>etiqueta</b> identifica cada pieza cortada. Elegí qué muestra, dónde, en qué piezas, y su tamaño y color.
                            </div>
                            {varsConPiezas.length > 0 && <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.4, marginTop: -6 }}>Se trabaja <b>una variable a la vez</b> (más rápido y sin tocar las de otros grupos).</div>}
                            {renderSelVerVariante(true)}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <span style={{ fontSize: 13, fontWeight: 600 }}>Mostrar etiqueta</span>
                              <Sw on={ec.activo} onClick={() => setEC({ activo: !ec.activo })} />
                            </div>
                            {ec.activo && (<>
                              <div>
                                <label style={lbl}>Qué muestra</label>
                                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                  {chip(term.variante || 'Talle', ec.mostrar.talle, () => setEC({ mostrar: { ...ec.mostrar, talle: !ec.mostrar.talle } }))}
                                  {chip('Nombre de pieza', ec.mostrar.pieza, () => setEC({ mostrar: { ...ec.mostrar, pieza: !ec.mostrar.pieza } }))}
                                  {chip('Número de prenda', ec.mostrar.numero, () => setEC({ mostrar: { ...ec.mostrar, numero: !ec.mostrar.numero } }))}
                                </div>
                              </div>
                              <div>
                                <label style={lbl}>Dónde se muestra — tocá el punto del contorno donde la querés (se ve en cada pieza y se aplica a todas)</label>
                                {(estado?.talles || []).length > 1 && (
                                  <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', alignItems: 'center', marginBottom: 8 }}>
                                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Variante:</span>
                                    {estado.talles.map(t => (
                                      <button key={t} type="button" onClick={() => cargarTalleEtq(t)}
                                        style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (etqData?.talle_ref === t ? 'var(--accent)' : 'var(--border-light)'), background: etqData?.talle_ref === t ? 'rgba(0,243,255,0.12)' : 'transparent', color: etqData?.talle_ref === t ? 'var(--accent)' : 'var(--text-muted)' }}>{t}</button>
                                    ))}
                                  </div>
                                )}
                                <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '11px 13px', borderRadius: 10, border: '1px solid var(--border-light)', background: 'rgba(0,243,255,0.05)', lineHeight: 1.5, display: 'flex', alignItems: 'center', gap: 9 }}>
                                  <Icon name="eye" style={{ width: 15, height: 15, color: 'var(--accent)', flexShrink: 0 }} />
                                  <span>En el <b>Visor del Molde</b> (a la izquierda) tocá el <b>borde de cada pieza</b> donde querés su etiqueta. Cada pieza se ubica por separado y el texto se apoya y se inclina según el borde.</span>
                                </div>
                              </div>
                              <div>
                                {(() => {
                                  // Alineación POR PIEZA: edita la pieza seleccionada (la última tocada). Si no
                                  // hay ninguna colocada/seleccionada, fija el default global (pieza sin propia).
                                  const selKey = etqPiezaSel ? claveEtqPieza(etqPiezaSel) : null;
                                  const selPos = etqPiezaSel ? ((ec.posiciones || {})[selKey] || (ec.posiciones || {})[etqPiezaSel]) : null;
                                  const selAlign = selPos?.align || align;
                                  const setAlignPieza = (a) => {
                                    if (etqPiezaSel && selPos) setEtiquetaConfig({ ...ec, posiciones: { ...ec.posiciones, [selKey]: { ...selPos, align: a } } });
                                    else setEC({ align: a });
                                  };
                                  return (<>
                                    <label style={lbl}>Alineación del texto {etqPiezaSel && selPos ? <span style={{ color: 'var(--accent)', fontWeight: 700 }}>— {etqPiezaSel}</span> : <span style={{ color: 'var(--text-muted)' }}>— tocá una pieza en el visor</span>}</label>
                                    <div style={{ display: 'flex', gap: 6 }}>
                                      {chip('Izquierda', selAlign === 'izquierda', () => setAlignPieza('izquierda'))}
                                      {chip('Centrado', selAlign === 'centro', () => setAlignPieza('centro'))}
                                      {chip('Derecha', selAlign === 'derecha', () => setAlignPieza('derecha'))}
                                    </div>
                                  </>);
                                })()}
                              </div>
                              <div>
                                <label style={lbl}>Tamaño del texto (mm)</label>
                                <input type="number" min="1" max="40" step="0.5" value={ec.size_mm}
                                  onChange={(e) => setEC({ size_mm: parseFloat(e.target.value) || 0 })} style={{ ...inp, width: 110 }} />
                              </div>
                              <div>
                                <label style={lbl}>Color del texto</label>
                                {swatchBtn(ec.color, 'Color del texto', (c) => setEC({ color: c }))}
                              </div>
                              <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 12 }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                                  <span style={{ fontSize: 13, fontWeight: 600 }}>Borde del texto (halo)</span>
                                  <Sw on={ec.borde_activo} onClick={() => setEC({ borde_activo: !ec.borde_activo })} />
                                </div>
                                {ec.borde_activo && (<>
                                  <label style={lbl}>Color del borde</label>
                                  {swatchBtn(ec.borde_color, 'Color del borde', (c) => setEC({ borde_color: c }))}
                                  <label style={{ ...lbl, marginTop: 12 }}>Tamaño del borde (mm)</label>
                                  <input type="number" min="0" max="10" step="0.1" value={ec.borde_mm}
                                    onChange={(e) => setEC({ borde_mm: parseFloat(e.target.value) || 0 })} style={{ ...inp, width: 110 }} />
                                </>)}
                              </div>
                              <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 12 }}>
                                <label style={lbl}>En qué piezas se muestra <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· por nombre (cae en todas las de ese nombre)</span></label>
                                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                  {[...new Set((ec.piezas || []).map(nombreGenerico).filter(Boolean))].map(g => chip(g, !offSet.has(g), () => {
                                    const off = new Set(offSet); off.has(g) ? off.delete(g) : off.add(g);
                                    setEC({ piezas_off: [...off] });
                                  }))}
                                </div>
                                {!(ec.piezas || []).length && <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Registrá la plantilla del molde para ver sus piezas.</div>}
                              </div>
                            </>)}
                            <button className="btn primary" onClick={guardarEtiqueta} style={{ alignSelf: 'flex-start', padding: '9px 18px' }}>Guardar etiqueta</button>
                            <ColorPickerModal open={!!picker} color={picker?.color} titulo={picker?.titulo}
                              onClose={() => setPicker(null)} onApply={(c) => picker?.onApply?.(c)} />
                          </div>
                        );
                      })()}

                      {tabAjustesMolde === 'editable' && (() => {
                        const variantes = editConfigVariantes || [];
                        const abrirNueva = () => setEditModal({ idx: null, draft: { capa: '', rangos: [{ variantes: [], mantener: false, apaisado: { ancho: '', alto: '' }, vertical: { ancho: '', alto: '' } }] } });
                        const abrirEditar = (i) => setEditModal({ idx: i, draft: editConfig[i] });
                        const onGuardar = (d) => { const nuevo = editModal.idx == null ? [...editConfig, d] : editConfig.map((c, k) => k === editModal.idx ? d : c); guardarEditConfig(nuevo); setEditModal(null); };
                        const onEliminar = () => { guardarEditConfig(editConfig.filter((_, k) => k !== editModal.idx)); setEditModal(null); };
                        const resumen = (c) => { const n = (c.rangos || []).length, v = (c.rangos || []).reduce((a, r) => a + (r.variantes || []).length, 0); return `${n} rango(s) · ${v} variante(s)`; };
                        return (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 13 }}>
                            <div>
                              <h3 style={{ margin: 0, fontSize: 16 }}>Tamaño de objetos editables</h3>
                              <p style={{ margin: '4px 0 0', fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>Registrá la <b>capa</b> editable (ej. <i>Editable escudo</i>) y, por <b>rango de variantes</b>, su tamaño máximo (o "mantener medida del diseño"). Es general del molde: sirve para cualquier diseño con esa capa. Capa no registrada → <b>escala con el diseño</b>. Lo que el operario ajuste en <b>Pedidos → Arte</b> manda sobre esto.</p>
                            </div>
                            {!variantes.length ? (
                              <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', padding: '12px 14px', borderRadius: 10, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)' }}>
                                Registrá primero la plantilla del molde (para tener las variantes disponibles).
                              </div>
                            ) : (editConfig || []).length === 0 ? (
                              <div style={{ fontSize: 12.5, color: 'var(--text-muted)', padding: '14px', borderRadius: 10, border: '1px dashed var(--border-light)', textAlign: 'center' }}>
                                No hay capas registradas todavía.
                              </div>
                            ) : (editConfig || []).map((c, i) => (
                              <button key={i} type="button" onClick={() => abrirEditar(i)}
                                style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '11px 13px', borderRadius: 10, cursor: 'pointer', textAlign: 'left', border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)', color: '#fff' }}>
                                <span style={{ flex: 1 }}>
                                  <span style={{ display: 'block', fontSize: 13.5, fontWeight: 700 }}>{c.capa || '(sin nombre)'}</span>
                                  <span style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{resumen(c)}</span>
                                </span>
                                <span style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 700 }}>Editar →</span>
                              </button>
                            ))}
                            <button type="button" onClick={abrirNueva} className="btn ghost" style={{ alignSelf: 'flex-start', padding: '8px 14px' }} disabled={!variantes.length}><Icon name="distribucion" style={{ width: 13, height: 13 }} /> Registrar capa</button>
                            {editModal && (
                              <EditableTamanoModal inicial={editModal.draft} variantes={variantes} esNueva={editModal.idx == null}
                                onGuardar={onGuardar} onEliminar={onEliminar} onCerrar={() => setEditModal(null)} />
                            )}
                          </div>
                        );
                      })()}

                      {tabAjustesMolde === 'nestingsel' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                            Elegí el <b>nesting</b> (separación, margen y giro de piezas) que se usa al generar la tizada de <b>este molde</b>.
                          </div>
                          <div>
                            <label style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Nesting de este molde</label>
                            <select
                              value={activoProdDetalle?.nesting_preset_id || 'nesting_default'}
                              onChange={(e) => asignarNestingAMolde(activoProdDetalle.id, e.target.value)}
                              style={{ width: '100%', height: 40, padding: '0 11px', borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', fontSize: 14, cursor: 'pointer' }}
                            >
                              {nestingPresets.map(n => <option key={n.id} value={n.id} style={{ background: '#121214' }}>{n.nombre}</option>)}
                            </select>
                          </div>
                          {(() => {
                            const sel = nestingPresets.find(n => n.id === (activoProdDetalle?.nesting_preset_id || 'nesting_default')) || nestingPresets[0];
                            const rotTxt = { auto: 'No girar', ninguna: 'No girar', '90': '90°', '180': '180°', libre: 'Libre' };
                            return sel ? (
                              <div className="card" style={{ padding: 14, fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                                Separación: <b>{sel.espaciado_mm} mm</b> · Margen: <b>{sel.margen_mm} mm</b> · Giro: <b>{rotTxt[sel.rotacion] || sel.rotacion}</b>
                              </div>
                            ) : null;
                          })()}
                          <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                            Los nesting se crean y editan en <b>Configuración → Reglas de Nesting</b>.
                          </div>

                          {/* Grupo de tizada (solo lectura): se configura en Reglas de Nesting */}
                          <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 16, marginTop: 4 }}>
                            <label style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>Grupo de tizada</label>
                            {(() => {
                              const g = gruposTizada.find(gr => (gr.moldes || []).includes(activoProdDetalle?.id));
                              const otros = g ? (g.moldes || []).filter(pid => pid !== activoProdDetalle?.id).map(pid => productosCat.productos.find(p => p.id === pid)?.nombre).filter(Boolean) : [];
                              return g
                                ? <div className="card" style={{ padding: 14, fontSize: 12.5, lineHeight: 1.6 }}>
                                    En el grupo <b style={{ color: 'var(--accent)' }}>{g.nombre}</b>.{otros.length ? <> Comparte mesa con: <b>{otros.join(', ')}</b>.</> : ' (sin otros moldes todavía)'}
                                  </div>
                                : <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>Este molde no está en ningún grupo → se arma en su <b>propia tizada</b>.</div>;
                            })()}
                            <button className="btn ghost" style={{ marginTop: 12, fontSize: 12 }} onClick={() => { setGrupoTizadaEditando(null); setNestingTab('grupos'); setAdminSubView('nesting'); }}>
                              Configurar grupos de tizada →
                            </button>
                            <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 8, lineHeight: 1.45 }}>
                              Los grupos (qué moldes comparten mesa) se crean en <b>Configuración → Reglas de Nesting</b>.
                            </small>
                          </div>
                        </div>
                      )}

                      {tabAjustesMolde === 'molderia' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                          {/* Botones de Carga (la explicación de qué hace este panel vive en el «?») */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <button className="btn ghost" onClick={() => fileInputPlantillaRef.current.click()} style={{ fontSize: 11.5, flex: 1 }}>
                              <Icon name="upload" style={{ width: 12, height: 12, marginRight: 6 }} /> Re-subir Plantilla
                            </button>
                            <Ayuda ancho={240}>Carga y registra las piezas vectoriales del molde `.ai`.</Ayuda>
                            <input
                              type="file"
                              ref={fileInputPlantillaRef}
                              accept=".ai,.pdf,.dxf"
                              onChange={(e) => handleUploadFile('plantilla', e.target.files[0])}
                              hidden
                            />
                          </div>

                          {etqData ? (
                            <>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                  <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>{term.variante} de Guía</span>
                                  <button
                                    type="button"
                                    className={`btn ${modoAcomodar ? 'success' : 'ghost'}`}
                                    style={{ padding: '4px 10px', fontSize: 11, display: 'flex', alignItems: 'center', gap: 5 }}
                                    onClick={() => setModoAcomodar(!modoAcomodar)}
                                  >
                                    <Icon name={modoAcomodar ? 'check' : 'edit'} style={{ width: 11, height: 11 }} />
                                    {modoAcomodar ? 'Guardando pos.' : 'Acomodar piezas'}
                                  </button>
                                </div>
                                {/* La guía es del MOLDE, no de la vista: en el modo «asignar variantes
                                    por piezas» el visor muestra el archivo ORIGINAL (una sola capa) y acá
                                    salía el nombre de esa capa («Capa 1») como si fuera el talle de guía.
                                    Mientras dura ese modo se muestra, pero no se cambia (los índices de
                                    pieza son los del original: recargar el visor rompería la asignación). */}
                                <button
                                  type="button"
                                  className="btn"
                                  disabled={varPzModo}
                                  title={varPzModo ? 'Terminá de asignar las piezas para cambiar la guía' : ''}
                                  style={{ width: '100%', justifyContent: 'space-between', padding: '10px 14px', fontSize: 13, opacity: varPzModo ? 0.65 : 1, cursor: varPzModo ? 'not-allowed' : 'pointer' }}
                                  onClick={() => { if (!varPzModo) setModalTalleGuiaOpen(true); }}
                                >
                                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{ color: 'var(--text-secondary)', fontSize: 11.5, fontWeight: 600 }}>Actual:</span>
                                    <span style={{ fontWeight: 700, color: 'var(--accent)', fontSize: 14 }}>{etqData.guia || etqData.talle_ref}</span>
                                  </span>
                                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{varPzModo ? '' : 'Cambiar ▾'}</span>
                                </button>
                              </div>

                              {/* Molde recién subido al que le falta nombrar los talles: no es un
                                  error, es el paso que sigue. Se dice explícitamente porque si no
                                  el visor queda vacío y parece que el molde no cargó. */}
                              {(etqData?.falta_nombrar_variantes || etqData?.sin_variantes) && !etqData?.resuelto && (
                                <div style={{ fontSize: 12, lineHeight: 1.5, padding: '11px 13px', borderRadius: 10, border: '1px solid var(--warning, #f5a524)', background: 'rgba(245,165,36,0.10)', color: 'var(--text-secondary)' }}>
                                  <b style={{ color: 'var(--warning, #f5a524)' }}>El molde se cargó, pero todavía no se puede usar.</b><br />
                                  {etqData?.sin_variantes
                                    ? <>Vino con <b>todas las piezas en una sola capa</b>: en el visor están las {(etqData?.piezas || []).length} piezas.
                                      Seleccioná las de cada {term.variante.toLowerCase()} y escribile el nombre acá abajo.</>
                                    : <>Vino sin los nombres de {term.variante.toLowerCase()} en las capas, así que no se pueden
                                      detectar las piezas. Nombralas acá abajo y aparecen solas.</>}
                                </div>
                              )}

                              {/* Nombrar variantes: sólo hace falta si el molde vino con las capas
                                  sin nombre, pero se deja siempre disponible para corregirlas. */}
                              <NombrarVariantes
                                pid={activoProdDetalle?.id}
                                term={term}
                                showError={showError}
                                showMsg={showMsg}
                                modoPiezas={varPzModo}
                                onModo={activarVarPz}
                                onListo={async () => {
                                  // el molde cambió (capas nombradas + registro rehecho): recargar
                                  // la detección para ver las piezas y los talles nuevos
                                  await fetchProductos();
                                  try {
                                    const r = await fetch(`/api/plantilla/deteccion?pid=${encodeURIComponent(activoProdDetalle?.id || '')}`);
                                    if (r.ok) { const d = await r.json(); setEtqData(d); setEtqNombres(d.nombres_existentes || {}); }
                                  } catch { }
                                }}
                              >
                                {/* MODO POR PIEZAS: el molde trae todo en una capa → se seleccionan
                                    piezas en el visor (clic o recuadro) y se les escribe el nombre. */}
                                {(() => {
                                  const total = (etqData?.piezas || []).length;
                                  const asignadas = Object.keys(varPzAsig).length;
                                  const porVar = {};
                                  Object.entries(varPzAsig).forEach(([k, v]) => { (porVar[v] = porVar[v] || []).push(parseInt(k, 10)); });
                                  const nombresVar = Object.keys(porVar);
                                  // ¿queda trabajo sin aplicar? El borrador se guarda solo, pero
                                  // partir el molde (lo caro) lo dispara el usuario: hay que
                                  // decírselo con todas las letras y con el botón A LA VISTA.
                                  const pendiente = _varPzSerial(varPzAsig) !== _varPzSerial(varPzAplicado);
                                  return (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
                                      {/* Barra PEGADA arriba: el botón de aplicar no puede quedar al
                                          final de una lista larga (el usuario no lo encontraba). */}
                                      <div style={{ position: 'sticky', top: 0, zIndex: 3, display: 'flex', flexDirection: 'column', gap: 6, padding: '8px 8px 9px', margin: '-4px -4px 0', borderRadius: 9, background: 'rgba(12,14,18,0.94)', backdropFilter: 'blur(4px)', border: '1px solid ' + (pendiente ? 'var(--warning, #f5a524)' : 'var(--border-light)') }}>
                                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, fontSize: 10.5 }}>
                                          <span style={{ color: 'var(--text-muted)' }}>
                                            Asignadas <b style={{ color: 'var(--success)' }}>{asignadas}</b> de {total}
                                          </span>
                                          <span style={{ color: varPzEstado === 'error' ? 'var(--danger, #ef4444)' : 'var(--text-muted)' }}>
                                            {varPzEstado === 'guardando' ? 'Guardando…'
                                              : varPzEstado === 'guardado' ? '✓ Guardado automático'
                                                : varPzEstado === 'error' ? '⚠ No se pudo guardar' : ''}
                                          </span>
                                        </div>
                                        <button type="button" className="btn success" style={{ width: '100%', fontSize: 12 }}
                                          disabled={varPzGuardando || !asignadas || !pendiente} onClick={guardarVariantesPz}>
                                          {varPzGuardando ? 'Aplicando…'
                                            : !pendiente ? 'Aplicado al molde ✓'
                                              : `Aplicar al molde (${nombresVar.length} ${term.variante.toLowerCase()}${nombresVar.length === 1 ? '' : 's'})`}
                                        </button>
                                        <div style={{ fontSize: 10, lineHeight: 1.35, color: pendiente ? 'var(--warning, #f5a524)' : 'var(--text-muted)' }}>
                                          {pendiente
                                            ? 'Lo que asignás se guarda solo: si salís y volvés está todo acá. Falta aplicarlo al molde (tarda unos segundos).'
                                            : 'El molde ya está partido con estas ' + term.variante.toLowerCase() + 's.'}
                                        </div>
                                      </div>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-muted)' }}>
                                        <span>Seleccionadas: <b style={{ color: 'var(--accent)' }}>{selNombrar.size}</b> ·
                                        Asignadas: <b style={{ color: 'var(--success)' }}>{asignadas}</b> de {total}</span>
                                        <Ayuda ancho={260}>Seleccioná en el visor las piezas de una {term.variante.toLowerCase()} (clic, o arrastrá un recuadro) y escribile el nombre. Después repetí con la siguiente. El archivo original no se toca: se guarda una versión nueva del molde con una capa por {term.variante.toLowerCase()}.</Ayuda>
                                      </div>
                                      <input value={varPzInput} onChange={e => setVarPzInput(e.target.value)}
                                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); asignarVariantePz(); } }}
                                        placeholder={`Nombre de la ${term.variante.toLowerCase()} (S, 38, Talle único…)`}
                                        style={{ width: '100%', padding: '7px 9px', fontSize: 12.5, fontWeight: 700, borderRadius: 7, border: '1px solid var(--border-light)', background: 'rgba(0,0,0,0.25)', color: '#fff' }} />
                                      <div style={{ display: 'flex', gap: 6 }}>
                                        <button type="button" className="btn primary" style={{ flex: 1, fontSize: 12 }}
                                          disabled={!selNombrar.size} onClick={asignarVariantePz}>
                                          Asignar {selNombrar.size || ''} pieza{selNombrar.size === 1 ? '' : 's'}
                                        </button>
                                        {selNombrar.size > 0 && <button type="button" className="btn ghost" style={{ fontSize: 12 }} onClick={() => setSelNombrar(new Set())}>Limpiar</button>}
                                      </div>

                                      {nombresVar.length > 0 && (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 220, overflowY: 'auto' }}>
                                          {nombresVar.map(nom => (
                                            <div key={nom} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, background: 'rgba(16,185,129,0.10)', border: '1px solid var(--border-light)' }}>
                                              <span style={{ flex: 1, minWidth: 0, fontSize: 12, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{nom}</span>
                                              <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>{porVar[nom].length} pieza{porVar[nom].length === 1 ? '' : 's'}</span>
                                              <button type="button" title="Seleccionar sus piezas para corregir"
                                                onClick={() => setSelNombrar(new Set(porVar[nom]))}
                                                style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 10.5, padding: '1px 6px' }}>Ver</button>
                                              <button type="button" title="Quitar esta variante" onClick={() => quitarVariantePz(nom)}
                                                style={{ background: 'none', border: 0, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 13, lineHeight: 1 }}>×</button>
                                            </div>
                                          ))}
                                        </div>
                                      )}

                                      {asignadas < total && (
                                        <div style={{ fontSize: 10.5, color: 'var(--warning, #f5a524)', lineHeight: 1.4 }}>
                                          Faltan {total - asignadas} piezas sin {term.variante.toLowerCase()}: van a quedar fuera del molde utilizable.
                                        </div>
                                      )}
                                    </div>
                                  );
                                })()}
                              </NombrarVariantes>

                              {/* EMPAREJAR TALLES (§10.c). El nombre de una pieza se propaga al resto de
                                  los talles comparando cómo están dispuestas. Si el molde NO viene
                                  acomodado de forma parecida en cada talle, esa comparación no tiene
                                  señal → acá el usuario reacomoda a mano y/o corrige la pieza homóloga. */}
                              {(tallesMolde.length > 1) && (
                                <div style={{ border: '1px solid var(--border-light)', borderRadius: 12, padding: 12, display: 'flex', flexDirection: 'column', gap: 10, background: empModo ? 'rgba(245,158,11,0.06)' : 'transparent' }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                                      <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>La misma pieza en cada {term.variante.toLowerCase()}</span>
                                      {/* La explicación (colapsada o en-modo) se movió acá: cambia según el modo. */}
                                      <Ayuda ancho={280}>{!empModo ? (
                                        <>Cada pieza existe en todos los {term.variante.toLowerCase()}s. Acá se ven <b>todas juntas</b>:
                                          <b> seleccionás las que son la misma</b> (la de cada {term.variante.toLowerCase()}) y escribís
                                          <b> qué es</b> («Frente»). Con eso queda definido su nombre <i>y</i> la correspondencia entre
                                          {' '}{term.variante.toLowerCase()}s. Se guarda solo, en el momento.</>
                                      ) : empTodas ? (
                                        <>En el visor están <b>todas las piezas de todos los {term.variante.toLowerCase()}s</b>.
                                          Seleccioná las que son <b>la misma pieza</b> (la de {(empData?.talles || []).slice(0, 3).join(', ')}…)
                                          y escribí qué es: «Frente». Es el mismo gesto que nombrar — con eso queda el
                                          nombre <i>y</i> la correspondencia entre {term.variante.toLowerCase()}s.</>
                                      ) : (
                                        <>Tocá la pieza en <b style={{ color: 'var(--accent)' }}>{empData?.guia}</b>, escribí qué es y
                                          confirmá: queda con ese nombre en <b>todos</b> los {term.variante.toLowerCase()}s. El sistema
                                          <b> propone</b> cuál es la misma en cada uno — lo que confirmes vos queda fijo y no se
                                          vuelve a mover.</>
                                      )}</Ayuda>
                                    </span>
                                    <button type="button" className={`btn ${empModo ? 'success' : 'ghost'}`}
                                      style={{ padding: '4px 10px', fontSize: 11 }}
                                      onClick={() => activarEmparejar(!empModo, 'simple')}>
                                      {empModo ? 'Salir' : 'Agrupar piezas'}
                                    </button>
                                  </div>
                                  {!empModo ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                      {/* Lo YA hecho se ve SIN entrar al modo: los grupos se guardan en
                                          el momento (cada uno pega contra el backend), pero al volver el
                                          panel arrancaba vacío y parecía que se había perdido todo. */}
                                      {(() => {
                                        const s = empStats;
                                        if (!s.agrupadas) return null;
                                        // Mismo resumen que adentro (agrupadas / total / confirmadas): así el
                                        // estado real se lee SIN entrar al modo y se sabe si falta algo.
                                        const falta = s.sinAgrupar || s.conFalta || s.provisorias;
                                        return (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '8px 10px', borderRadius: 9, background: falta ? 'rgba(245,165,36,0.07)' : 'rgba(16,185,129,0.08)', border: `1px solid ${falta ? 'rgba(245,165,36,0.28)' : 'rgba(16,185,129,0.25)'}` }}>
                                            <span style={{ fontSize: 11, color: falta ? '#f5a524' : 'var(--success)', fontWeight: 700 }}>
                                              {falta ? '●' : '✓'} {s.agrupadas} de {s.total} piezas agrupadas · {s.confirmadas} confirmadas (guardado)
                                            </span>
                                            {!!(s.sinAgrupar || s.conFalta || s.provisorias) && (
                                              <span style={{ fontSize: 10.5, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                                                {s.sinAgrupar ? `Faltan ${s.sinAgrupar} por agrupar. ` : ''}
                                                {s.conFalta ? `${s.conFalta} sin correspondencia en algún ${term.variante.toLowerCase()}. ` : ''}
                                                {s.provisorias ? `${s.provisorias} con nombre provisorio.` : ''}
                                              </span>
                                            )}
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                              {s.filas.slice(0, 12).map(f => (
                                                <span key={f.nombre} style={{ fontSize: 10, padding: '2px 7px', borderRadius: 20, background: 'rgba(255,255,255,0.06)', color: f.provisorio ? 'var(--text-muted)' : 'var(--text-secondary)', fontStyle: f.provisorio ? 'italic' : 'normal', border: `1px solid ${colorGrupoA(f.nombre, 0.4)}` }}>{f.nombre}</span>
                                              ))}
                                              {s.filas.length > 12 && <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>+{s.filas.length - 12}</span>}
                                            </div>
                                          </div>
                                        );
                                      })()}
                                    </div>
                                  ) : empVista === 'simple' ? (
                                    <>
                                      {/* CAMINO PRINCIPAL: un gesto = nombre + correspondencia. La explicación
                                          (empTodas / por-talle) se movió al «?» del título de la sección. */}
                                      {/* Por qué NO se puede mostrar todo junto (molde anidado / varias mesas): se dice
                                          en una línea, no se deja al usuario adivinando por qué ve un talle solo. */}
                                      {!empTodas && empTodasMotivo && (
                                        <div style={{ fontSize: 11, color: '#f5a524', lineHeight: 1.45, padding: '7px 10px', borderRadius: 8, background: 'rgba(245,165,36,0.08)', border: '1px solid rgba(245,165,36,0.25)' }}>
                                          {empTodasMotivo}
                                        </div>
                                      )}

                                      {/* PROGRESO GLOBAL + QUÉ FALTA PARA SEGUIR. Antes cada fila cantaba su
                                          «0/5 confirmadas» y no había ningún número del conjunto: con 36 piezas
                                          era imposible saber cuánto quedaba ni si ya se podía avanzar. */}
                                      {(() => {
                                        const s = empStats;
                                        const pctN = s.total ? Math.round(100 * s.agrupadas / s.total) : 0;
                                        const pctC = s.total ? Math.round(100 * s.confirmadas / s.total) : 0;
                                        // Un solo mensaje, el del primer obstáculo REAL: agrupar → cubrir todos
                                        // los talles → sacarse los provisorios de encima → listo.
                                        const pl = (n, uno, varios) => (n === 1 ? uno : varios);
                                        const est = s.sinAgrupar > 0
                                          ? { c: '#f5a524', t: empTodas
                                              ? <>{pl(s.sinAgrupar, 'Falta', 'Faltan')} <b>{s.sinAgrupar}</b> {pl(s.sinAgrupar, 'pieza', 'piezas')} por agrupar: {pl(s.sinAgrupar, 'seleccionala', 'seleccionalas')} en el visor (las grises) junto con su homóloga de cada {term.variante.toLowerCase()} y escribí qué {pl(s.sinAgrupar, 'es', 'son')}.</>
                                              : <>{pl(s.sinAgrupar, 'Falta', 'Faltan')} <b>{s.sinAgrupar}</b> {pl(s.sinAgrupar, 'pieza', 'piezas')} por agrupar: {pl(s.sinAgrupar, 'tocala', 'tocalas')} en el visor (estás viendo {empTalle}{empTalle !== empData?.guia ? ` — el nombrado se hace en ${empData?.guia}` : ''}).</> }
                                          : s.conFalta > 0
                                            ? { c: '#f5a524', t: <><b>{s.conFalta}</b> {pl(s.conFalta, 'pieza no tiene', 'piezas no tienen')} correspondencia en algún {term.variante.toLowerCase()}: abrí la fila y tocá el chip naranja.</> }
                                            : s.provisorias > 0
                                              ? { c: 'var(--text-secondary)', t: <>Todas agrupadas. <b>{s.provisorias}</b> {pl(s.provisorias, 'sigue', 'siguen')} con nombre provisorio («Pieza 3»): conviene ponerle{pl(s.provisorias, '', 's')} el de verdad.</> }
                                              : { c: 'var(--success)', t: <>✓ Todo agrupado{s.confirmadas === s.agrupadas ? ' y confirmado' : ''}: ya podés seguir.</> };
                                        return (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 7, padding: '9px 11px', borderRadius: 9, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)' }}>
                                            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, flexWrap: 'wrap' }}>
                                              <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)' }}>{s.agrupadas} de {s.total}</span>
                                              <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>piezas agrupadas</span>
                                              <span style={{ fontSize: 11.5, color: '#c4b5fd', marginLeft: 'auto', fontWeight: 700 }}>{s.confirmadas} confirmadas</span>
                                            </div>
                                            {/* Dos capas en la misma barra: agrupado (accent) y, adentro, confirmado (violeta) */}
                                            <div style={{ position: 'relative', height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
                                              <div style={{ position: 'absolute', inset: 0, width: `${pctN}%`, background: 'var(--accent)', opacity: 0.45 }} />
                                              <div style={{ position: 'absolute', inset: 0, width: `${pctC}%`, background: '#a78bfa' }} />
                                            </div>
                                            <div style={{ fontSize: 11, lineHeight: 1.45, color: est.c }}>{est.t}</div>
                                            {s.agrupadas > 0 && s.confirmadas < s.agrupadas && (
                                              <button type="button" className="btn ghost" style={{ fontSize: 11, alignSelf: 'flex-start' }}
                                                disabled={empGuardando}
                                                title="Da por buena la propuesta del sistema para TODAS las piezas, en todos los talles (queda fija: la heurística no la vuelve a mover)"
                                                onClick={confirmarTodasLasPropuestas}>
                                                {empGuardando ? 'Confirmando…' : `✓ Confirmar todo (${s.agrupadas - s.confirmadas} ${pl(s.agrupadas - s.confirmadas, 'pieza', 'piezas')})`}
                                              </button>
                                            )}
                                          </div>
                                        );
                                      })()}

                                      {/* ── TODAS LAS VARIANTES JUNTAS: el gesto es UNO — seleccionar y nombrar ── */}
                                      {empTodas && (() => {
                                        const porIdx = new Map((empTodasData?.piezas || []).map(p => [p.idx, p]));
                                        const sel = Array.from(selNombrar).map(g => porIdx.get(g)).filter(Boolean);
                                        const cuenta = {};                       // cuántas seleccionadas por talle
                                        sel.forEach(p => { cuenta[p.talle] = (cuenta[p.talle] || 0) + 1; });
                                        const talles = empData?.talles || [];
                                        const dup = talles.filter(t => (cuenta[t] || 0) > 1);
                                        const faltan = talles.filter(t => !cuenta[t]);
                                        const guia = empData?.guia;
                                        const sinGuia = sel.length > 0 && !cuenta[guia];
                                        // Si la selección cae sobre un grupo que YA existe, esto es RENOMBRAR/rehacer.
                                        const yaEs = (() => {
                                          const ns = new Set(sel.map(p => _nombreEnTalle(p.talle, p.t_idx)).filter(Boolean));
                                          return ns.size === 1 ? Array.from(ns)[0] : '';
                                        })();
                                        return (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
                                            {/* Un chip por variante: se ve de un vistazo cuáles ya elegiste y cuál falta. */}
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, alignItems: 'center' }}>
                                              <span style={{ fontSize: 10.5, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Selección</span>
                                              <Ayuda ancho={250}>Clic para elegir una pieza, o arrastrá un recuadro para varias. Se <b>guarda al confirmar</b>: podés salir y volver.</Ayuda>
                                              {talles.map(t => {
                                                const n = cuenta[t] || 0;
                                                const col = n > 1 ? '#ef4444' : n === 1 ? 'var(--accent)' : 'var(--border-light)';
                                                return (
                                                  <span key={t} style={{ padding: '3px 9px', borderRadius: 999, fontSize: 11, fontWeight: 700, border: `1px solid ${col}`, color: n ? (n > 1 ? '#ef4444' : 'var(--accent)') : 'var(--text-muted)', background: n === 1 ? 'rgba(0,243,255,0.10)' : 'transparent' }}>
                                                    {t === guia ? '★ ' : ''}{t}{n > 1 ? ` ×${n}` : n === 1 ? ' ✓' : ''}
                                                  </span>
                                                );
                                              })}
                                              {selNombrar.size > 0 && <button type="button" className="btn ghost" style={{ fontSize: 11, marginLeft: 'auto' }} onClick={() => { setSelNombrar(new Set()); setEmpNombreInput(''); }}>Limpiar</button>}
                                            </div>
                                            {/* Lo que está mal se dice ANTES de apretar el botón, no después. */}
                                            {!!dup.length && (
                                              <div style={{ fontSize: 11, color: '#ef4444', lineHeight: 1.45 }}>
                                                Elegiste 2 piezas de {dup.join(', ')}: una pieza es <b>una sola</b> por {term.variante.toLowerCase()}. Sacá la que sobra.
                                              </div>
                                            )}
                                            {sinGuia && !dup.length && (
                                              <div style={{ fontSize: 11, color: '#f5a524', lineHeight: 1.45 }}>
                                                Falta la pieza de <b>{guia}</b>: el nombre se guarda en ese {term.variante.toLowerCase()}.
                                              </div>
                                            )}
                                            {!dup.length && !sinGuia && sel.length > 0 && !!faltan.length && (
                                              <div style={{ fontSize: 11, color: '#f5a524', lineHeight: 1.45 }}>
                                                Sin pieza elegida en <b>{faltan.join(', ')}</b>: se puede guardar igual, ahí queda la propuesta del sistema (revisala en la lista).
                                              </div>
                                            )}
                                            {yaEs && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Estas piezas ya son «<b style={{ color: colorGrupo(yaEs) }}>{yaEs}</b>»: confirmar las vuelve a guardar con lo que escribas.</div>}
                                            <div style={{ display: 'flex', gap: 6 }}>
                                              <input value={empNombreInput} onChange={e => setEmpNombreInput(e.target.value)}
                                                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); crearGrupoTodas(); } }}
                                                placeholder="Todo esto es… (Frente, Espalda, Manga…)"
                                                style={{ flex: 1, minWidth: 0, padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary)', fontSize: 12 }} />
                                              <button type="button" className="btn primary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}
                                                disabled={empGuardando || !sel.length || !!dup.length || sinGuia || !empNombreInput.trim()}
                                                onClick={crearGrupoTodas}>
                                                {empGuardando ? 'Guardando…' : `Es esta pieza ✓${sel.length ? ` (${sel.length})` : ''}`}
                                              </button>
                                            </div>
                                          </div>
                                        );
                                      })()}

                                      {/* Qué talle está mostrando el visor (la guía primero: es donde se nombra). */}
                                      {!empTodas && (<>
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, alignItems: 'center' }}>
                                        <span style={{ fontSize: 10.5, color: 'var(--text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>Viendo</span>
                                        {/* En modo corregir (viendo un {variante} que no es la guía) la explicación va acá. */}
                                        {empTalle !== empData?.guia && <Ayuda ancho={260}>Estás viendo <b style={{ color: 'var(--accent)' }}>{empTalle}</b>: cada pieza muestra el nombre que le tocó (✓ = confirmado por vos). ¿Alguna está mal? Tocá la pieza correcta y decí cuál es.</Ayuda>}
                                        {(empData?.talles || []).map(t => {
                                          const on = empTalle === t;
                                          const esGuia = t === empData?.guia;
                                          return (
                                            <button key={t} type="button" onClick={() => { setEmpFijar(null); setSelNombrar(new Set()); abrirTalleEmp(t); }}
                                              style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>
                                              {esGuia ? '★ ' : ''}{t}
                                            </button>
                                          );
                                        })}
                                      </div>

                                      {empTalle === empData?.guia ? (
                                        <>
                                          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                            <span style={{ fontSize: 11.5, color: 'var(--text-muted)', flex: 1 }}>
                                              Seleccionadas: <b style={{ color: 'var(--accent)' }}>{selNombrar.size}</b>
                                              {selNombrar.size === 1 && etqNombres[Array.from(selNombrar)[0]] ? <> · ya es «<b>{etqNombres[Array.from(selNombrar)[0]]}</b>»</> : null}
                                            </span>
                                            <Ayuda ancho={250}>Cada grupo se <b>guarda al confirmarlo</b>: podés salir y volver, queda todo.</Ayuda>
                                            {selNombrar.size > 0 && <button type="button" className="btn ghost" style={{ fontSize: 11 }} onClick={() => setSelNombrar(new Set())}>Limpiar</button>}
                                          </div>
                                          <div style={{ display: 'flex', gap: 6 }}>
                                            <input value={empNombreInput} onChange={e => setEmpNombreInput(e.target.value)}
                                              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); crearGrupoPieza(); } }}
                                              placeholder="¿Qué es esta pieza? (Frente, Espalda, Manga…)"
                                              style={{ flex: 1, minWidth: 0, padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary)', fontSize: 12 }} />
                                            <button type="button" className="btn primary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}
                                              disabled={empGuardando || selNombrar.size !== 1 || !empNombreInput.trim()}
                                              onClick={crearGrupoPieza}>
                                              {empGuardando ? 'Guardando…' : (selNombrar.size === 1 && etqNombres[Array.from(selNombrar)[0]] ? 'Renombrar' : 'Es esta pieza ✓')}
                                            </button>
                                          </div>
                                        </>
                                      ) : (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                          {selNombrar.size === 1 && (
                                            <div style={{ display: 'flex', gap: 6 }}>
                                              <select value={empGrupoSel} onChange={e => setEmpGrupoSel(e.target.value)}
                                                style={{ flex: 1, minWidth: 0, padding: '7px 10px', borderRadius: 8, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary)', fontSize: 12 }}>
                                                <option value="">Esta pieza es…</option>
                                                {Object.values(empData?.nombres_guia || {}).map(n => <option key={n} value={n}>{n}</option>)}
                                              </select>
                                              <button type="button" className="btn primary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}
                                                disabled={empGuardando || !empGrupoSel}
                                                onClick={() => { const i = Array.from(selNombrar)[0]; setSelNombrar(new Set()); fijarPiezaEmp(empGrupoSel, i); }}>
                                                Es la misma ✓
                                              </button>
                                            </div>
                                          )}
                                        </div>
                                      )}
                                      </>)}

                                      {empFijar && (
                                        <div style={{ fontSize: 11.5, fontWeight: 700, color: '#18181b', background: '#f5a524', borderRadius: 8, padding: '7px 10px' }}>
                                          Tocá en el visor la pieza que es «{empFijar}» {empTodas ? `(en el ${term.variante.toLowerCase()} que sea)` : `en ${empTalle}`}
                                          <button type="button" onClick={() => setEmpFijar(null)} style={{ float: 'right', background: 'none', border: 0, cursor: 'pointer', fontWeight: 900 }}>×</button>
                                        </div>
                                      )}

                                      {/* GRUPOS ARMADOS. Con 36 piezas la lista plana (chips de todos los
                                          talles + «Confirmar todo» repetidos en CADA fila) es puro ruido:
                                          acá la fila es una línea con MINIATURA y estado, y el detalle
                                          (chips por talle, confirmar, deshacer) se abre sólo en la fila
                                          que se está mirando. El filtro deja a la vista lo que falta. */}
                                      {(() => {
                                        const s = empStats;
                                        if (!s.filas.length) return <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Todavía no agrupaste ninguna pieza: tocá una en el visor y escribí qué es.</div>;
                                        const q = empBuscar.trim().toLowerCase();
                                        const pend = s.filas.filter(f => !f.listo || f.provisorio);
                                        const listas = s.filas.filter(f => f.listo && !f.provisorio);
                                        const base = empFiltro === 'pend' ? pend : empFiltro === 'listas' ? listas : s.filas;
                                        const vista = q ? base.filter(f => f.nombre.toLowerCase().includes(q)) : base;
                                        const tabs = [['pend', 'Pendientes', pend.length], ['listas', 'Listas', listas.length], ['todas', 'Todas', s.filas.length]];
                                        return (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                            <div style={{ display: 'flex', gap: 5, alignItems: 'center', flexWrap: 'wrap' }}>
                                              {tabs.map(([k, lbl, n]) => (
                                                <button key={k} type="button" onClick={() => setEmpFiltro(k)}
                                                  style={{ padding: '3px 9px', borderRadius: 999, fontSize: 10.5, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (empFiltro === k ? 'var(--accent)' : 'var(--border-light)'), background: empFiltro === k ? 'rgba(0,243,255,0.12)' : 'transparent', color: empFiltro === k ? 'var(--accent)' : 'var(--text-muted)' }}>
                                                  {lbl} {n}
                                                </button>
                                              ))}
                                              {s.filas.length > 8 && (
                                                <input value={empBuscar} onChange={e => setEmpBuscar(e.target.value)} placeholder="Buscar…"
                                                  style={{ marginLeft: 'auto', width: 110, padding: '3px 8px', borderRadius: 7, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary)', fontSize: 11 }} />
                                              )}
                                            </div>
                                            {!vista.length ? (
                                              <div style={{ fontSize: 11.5, color: empFiltro === 'pend' ? 'var(--success)' : 'var(--text-muted)', padding: '6px 2px' }}>
                                                {empFiltro === 'pend' ? '✓ No queda ninguna pendiente.' : 'Nada para mostrar acá.'}
                                              </div>
                                            ) : (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 320, overflowY: 'auto' }}>
                                              {vista.map(f => {
                                                const col = colorGrupo(f.nombre);
                                                const abierta = empAbierto === f.nombre;
                                                const editando = empRenombrar?.nombre === f.nombre;
                                                // «0/5» no decía nada: lo que importa es si está lista, si le
                                                // falta algún talle, o si sigue siendo sólo una propuesta.
                                                const estado = f.faltan ? { c: '#f5a524', t: `falta en ${f.faltan}` }
                                                  : f.listo ? { c: '#c4b5fd', t: '✓ listo' }
                                                    : f.fijos === 0 ? { c: 'var(--text-muted)', t: 'propuesta' }
                                                      : { c: 'var(--text-muted)', t: `${f.fijos}/${s.otros.length} confirmadas` };
                                                return (
                                                  <div key={f.nombre} onMouseEnter={() => setResaltarNombre(nombreGenerico(f.nombre))} onMouseLeave={() => setResaltarNombre(null)}
                                                    style={{ borderRadius: 8, background: abierta ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.02)', border: '1px solid var(--border-light)', borderLeft: `3px solid ${col}` }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px' }}>
                                                      {miniPieza(f.idxGuia, col)}
                                                      {editando ? (
                                                        <input autoFocus value={empRenombrar.valor}
                                                          onChange={e => setEmpRenombrar({ nombre: f.nombre, valor: e.target.value })}
                                                          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); empRenomCancel.current = true; renombrarGrupo(f.idxGuia, f.nombre, empRenombrar.valor); } if (e.key === 'Escape') { empRenomCancel.current = true; setEmpRenombrar(null); } }}
                                                          onBlur={() => { if (empRenomCancel.current) { empRenomCancel.current = false; return; } renombrarGrupo(f.idxGuia, f.nombre, empRenombrar.valor); }}
                                                          placeholder="Frente, Espalda, Manga…"
                                                          style={{ flex: 1, minWidth: 0, padding: '4px 8px', borderRadius: 7, border: '1px solid var(--accent)', background: 'rgba(0,0,0,0.35)', color: 'var(--text-primary)', fontSize: 12 }} />
                                                      ) : (
                                                        // El nombre ES el botón de renombrar: el provisorio se ve como tal
                                                        // (itálica, gris, «poner nombre») e invita a reemplazarlo ahí mismo.
                                                        <button type="button" title="Tocá para cambiarle el nombre"
                                                          onClick={() => { empRenomCancel.current = false; setEmpRenombrar({ nombre: f.nombre, valor: f.provisorio ? '' : f.nombre }); if (empTodas) seleccionarGrupoTodas(f.nombre); else if (empTalle === empData?.guia) setSelNombrar(new Set([f.idxGuia])); }}
                                                          style={{ flex: 1, minWidth: 0, textAlign: 'left', background: 'none', border: 0, cursor: 'text', padding: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 12, fontWeight: f.provisorio ? 500 : 800, fontStyle: f.provisorio ? 'italic' : 'normal', color: f.provisorio ? 'var(--text-muted)' : col }}>
                                                          {f.nombre}{f.provisorio ? <span style={{ fontSize: 10, fontStyle: 'normal', marginLeft: 6, color: 'var(--accent)' }}>✎ poner nombre</span> : null}
                                                        </button>
                                                      )}
                                                      <span style={{ fontSize: 10.5, color: estado.c, fontWeight: 700, whiteSpace: 'nowrap' }}>{estado.t}</span>
                                                      <button type="button" title={abierta ? 'Cerrar' : `Ver ${term.variante.toLowerCase()} por ${term.variante.toLowerCase()}`}
                                                        onClick={() => setEmpAbierto(abierta ? null : f.nombre)}
                                                        style={{ background: 'none', border: 0, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 11, lineHeight: 1, padding: '2px 3px' }}>{abierta ? '▲' : '▼'}</button>
                                                    </div>
                                                    {abierta && (
                                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '0 8px 7px 8px' }}>
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                                          {(empData?.talles || []).map(t => {
                                                            const esGuia = t === empData?.guia;
                                                            const j = ((empData?.asignacion || {})[t] || {})[f.nombre];
                                                            const fijo = ((empData?.manual || {})[t] || {})[f.nombre] != null;
                                                            const est = { guia: { bg: 'rgba(0,243,255,0.14)', bd: 'var(--accent)', fg: 'var(--accent)', t: '★ ' },
                                                                          fijo: { bg: 'rgba(167,139,250,0.18)', bd: '#a78bfa', fg: '#c4b5fd', t: '✓ ' },
                                                                          prop: { bg: 'rgba(255,255,255,0.04)', bd: 'var(--border-light)', fg: 'var(--text-muted)', t: '' },
                                                                          falta: { bg: 'rgba(245,165,36,0.16)', bd: '#f5a524', fg: '#f5a524', t: '! ' } }[esGuia ? 'guia' : (j == null ? 'falta' : (fijo ? 'fijo' : 'prop'))];
                                                            return (
                                                              <button key={t} type="button" disabled={empGuardando}
                                                                title={esGuia ? `${t}: acá le pusiste el nombre` : (j == null ? `${t}: ninguna pieza le tocó — tocá acá y elegila` : (fijo ? `${t}: confirmada por vos` : `${t}: propuesta del sistema — tocá acá para corregirla`))}
                                                                onClick={() => revisarPiezaEnTalle(f.nombre, t)}
                                                                style={{ padding: '2px 7px', borderRadius: 999, fontSize: 10.5, fontWeight: 700, cursor: 'pointer', border: `1px solid ${est.bd}`, background: est.bg, color: est.fg }}>
                                                                {est.t}{t}
                                                              </button>
                                                            );
                                                          })}
                                                        </div>
                                                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                                          {empTodas && (
                                                            <button type="button" title="Marcar en el visor las piezas de este grupo (para revisarlo o rehacerlo)"
                                                              onClick={() => seleccionarGrupoTodas(f.nombre)}
                                                              style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 10.5, padding: '2px 7px' }}>Ver en el visor</button>
                                                          )}
                                                          <button type="button" title="Dar por buena la propuesta del sistema en todos" disabled={empGuardando || f.fijos === s.otros.length}
                                                            onClick={() => confirmarTodoGrupo(f.nombre)}
                                                            style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 10.5, padding: '2px 7px' }}>Confirmar esta pieza</button>
                                                          <button type="button" title="Deshacer este grupo (le saca el nombre y sus confirmaciones)" disabled={empGuardando}
                                                            onClick={() => { setEmpAbierto(null); borrarGrupoPieza(f.nombre); }}
                                                            style={{ marginLeft: 'auto', background: 'none', border: 0, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 10.5 }}>Deshacer ×</button>
                                                        </div>
                                                      </div>
                                                    )}
                                                  </div>
                                                );
                                              })}
                                            </div>
                                            )}
                                          </div>
                                        );
                                      })()}

                                      <button type="button" className="btn ghost" style={{ fontSize: 11, alignSelf: 'flex-start' }}
                                        onClick={() => cambiarVistaEmp('avanzado')}>Ajuste avanzado ▸</button>
                                    </>
                                  ) : (
                                    <>
                                      <button type="button" className="btn ghost" style={{ fontSize: 11, alignSelf: 'flex-start' }}
                                        onClick={() => cambiarVistaEmp('simple')}>◂ Volver a agrupar piezas</button>
                                      <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                        Guía: <b style={{ color: 'var(--accent)' }}>{empData?.guia}</b>. Elegí abajo
                                        el {term.variante.toLowerCase()} a corregir: el visor lo muestra a él.
                                      </div>
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                                        {(empData?.talles || []).filter(t => t !== empData?.guia).map(t => {
                                          const on = empTalle === t;
                                          const tieneAjuste = !!(empData?.acomodo || {})[t] || !!(empData?.manual || {})[t];
                                          return (
                                            <button key={t} type="button" onClick={() => abrirTalleEmp(t)}
                                              style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>
                                              {t}{tieneAjuste ? ' •' : ''}
                                            </button>
                                          );
                                        })}
                                      </div>

                                      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5, padding: '9px 11px', borderRadius: 9, background: 'rgba(255,255,255,0.03)' }}>
                                        <b style={{ color: 'var(--text-secondary)' }}>1 · Reacomodar.</b> Tocá una pieza para
                                        seleccionarla (o arrastrá un recuadro) y <b>arrastrala</b> hasta dejar
                                        este {term.variante.toLowerCase()} acomodado como el de guía. No mueve el molde:
                                        solo la referencia con la que se emparejan las piezas.
                                      </div>
                                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                        <span style={{ fontSize: 11.5, color: 'var(--text-muted)', flex: 1 }}>
                                          Seleccionadas: <b style={{ color: 'var(--accent)' }}>{selNombrar.size}</b> ·
                                          Movidas: <b style={{ color: 'var(--warning, #f5a524)' }}>{Object.keys(_empAcomodoPayload()).length}</b>
                                        </span>
                                        {selNombrar.size > 0 && <button type="button" className="btn ghost" style={{ fontSize: 11 }} onClick={() => setSelNombrar(new Set())}>Limpiar sel.</button>}
                                        <button type="button" className="btn ghost" style={{ fontSize: 11 }} disabled={empGuardando} onClick={resetAcomodoEmp}>Restablecer</button>
                                      </div>
                                      <button type="button" className="btn primary" style={{ width: '100%', fontSize: 12 }}
                                        disabled={empGuardando} onClick={aplicarEmparejado}>
                                        {empGuardando ? 'Aplicando…' : 'Aplicar y re-emparejar'}
                                      </button>

                                      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5, padding: '9px 11px', borderRadius: 9, background: 'rgba(255,255,255,0.03)' }}>
                                        <b style={{ color: 'var(--text-secondary)' }}>2 · Corregir a mano.</b> Si ni así queda,
                                        tocá «Cambiar» en la pieza mal emparejada y después la pieza correcta en el
                                        visor. Una corrección a mano <b>nunca</b> se pisa con lo automático.
                                      </div>
                                      {empFijar && (
                                        <div style={{ fontSize: 11.5, fontWeight: 700, color: '#18181b', background: '#f5a524', borderRadius: 8, padding: '7px 10px' }}>
                                          Tocá en el visor la pieza que es «{empFijar}» en {empTalle}
                                          <button type="button" onClick={() => setEmpFijar(null)} style={{ float: 'right', background: 'none', border: 0, cursor: 'pointer', fontWeight: 900 }}>×</button>
                                        </div>
                                      )}
                                      {(() => {
                                        const ng = empData?.nombres_guia || {};
                                        const asig = (empData?.asignacion || {})[empTalle] || {};
                                        const fijos = (empData?.manual || {})[empTalle] || {};
                                        const filas = Object.entries(ng).map(([i, n]) => ({ idxGuia: parseInt(i, 10), nombre: n }))
                                          .sort((a, b) => a.idxGuia - b.idxGuia);
                                        if (!filas.length) return <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Todavía no hay piezas nombradas.</div>;
                                        return (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 3, maxHeight: 260, overflowY: 'auto' }}>
                                            {filas.map(f => {
                                              const j = asig[f.nombre];
                                              const fijo = fijos[f.nombre] != null;
                                              return (
                                                <div key={f.nombre} onMouseEnter={() => setResaltarNombre(nombreGenerico(f.nombre))} onMouseLeave={() => setResaltarNombre(null)}
                                                  style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '4px 8px', borderRadius: 7, background: fijo ? 'rgba(167,139,250,0.12)' : 'rgba(255,255,255,0.03)', border: '1px solid var(--border-light)' }}>
                                                  <span style={{ flex: 1, minWidth: 0, fontSize: 11.5, fontWeight: 700, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.nombre}</span>
                                                  <span style={{ fontSize: 11, color: j == null ? 'var(--warning, #f5a524)' : (fijo ? '#c4b5fd' : 'var(--text-muted)'), fontWeight: 700 }}>
                                                    {j == null ? 'sin emparejar' : `#${j + 1}`}{fijo ? ' ✋' : ''}
                                                  </span>
                                                  <button type="button" disabled={empGuardando}
                                                    onClick={() => setEmpFijar(empFijar === f.nombre ? null : f.nombre)}
                                                    style={{ background: 'none', border: '1px solid var(--border-light)', color: empFijar === f.nombre ? 'var(--accent)' : 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 10.5, padding: '1px 6px' }}>Cambiar</button>
                                                  {fijo && <button type="button" title="Volver al emparejado automático" disabled={empGuardando}
                                                    onClick={() => soltarPiezaEmp(f.nombre)}
                                                    style={{ background: 'none', border: 0, color: 'var(--text-muted)', cursor: 'pointer', fontSize: 13, lineHeight: 1 }}>×</button>}
                                                </div>
                                              );
                                            })}
                                          </div>
                                        );
                                      })()}
                                    </>
                                  )}
                                </div>
                              )}

                              {/* En «mi molde» no hay pestaña Variables: el nombrado de piezas (que vive
                                  DENTRO de ese paso) se alcanza desde acá — es el mismo editor. */}
                              {modoMiMolde ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <button type="button" className="btn ghost" style={{ flex: 1, fontSize: 12.5 }}
                                    onClick={() => { setTabAjustesMolde('variables'); setVarStep('nombrar'); setAsignandoTipo(null); setGrupoAislado(null); setModeloAbierto(null); setGrupoPzAbierto(null); setEditandoNombre(null); }}>
                                    Indicar qué es cada pieza →
                                  </button>
                                  <Ayuda ancho={270}>Dos cosas para que tu molde sirva: que cada {term.variante.toLowerCase()} tenga su nombre (arriba) y que <b>cada pieza</b> diga qué es (Frente, Espalda, Manga…).</Ayuda>
                                </div>
                              ) : (
                                <Ayuda ancho={270}>Acá cargás y acomodás las piezas del molde. Para <b>nombrar cada pieza</b> (y armar variables), andá a la pestaña <b>Variables</b>.</Ayuda>
                              )}
                            </>
                          ) : activoProdDetalle?.plantilla ? (
                            <div style={{ color: 'var(--text-muted)', fontSize: 12.5, textAlign: 'center', padding: 28 }}>Cargando el molde…</div>
                          ) : (
                            <div className="upload-zone" onClick={() => fileInputPlantillaRef.current.click()} style={{ padding: '24px 16px' }}>
                              <Icon name="upload" className="upload-icon" />
                              <div style={{ fontSize: 12.5, fontWeight: 600 }}>Subí el molde (.ai · .pdf · .dxf)</div>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>Illustrator, Corel/PDF o DXF (Optitex, Gerber…)</div>
                            </div>
                          )}
                          <button type="button" className="btn ghost" style={{ width: '100%', fontSize: 11.5, marginTop: 8 }} onClick={() => setVerAyudaExport(v => !v)}>
                            {verAyudaExport ? '▲ Ocultar' : '❓ ¿Cómo exportar el molde desde tu programa?'}
                          </button>
                          {verAyudaExport && <AyudaExportMolde term={term} />}
                        </div>
                      )}

                      {tabAjustesMolde === 'diseno' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                          {!activoProdDetalle.plantilla ? (
                            <div style={{ textAlign: 'center', padding: '24px 14px', border: '1px dashed var(--border-light)', borderRadius: 12 }}>
                              <Icon name="alert" style={{ width: 22, height: 22, color: 'var(--warning)' }} />
                              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 8 }}>Este molde todavía no tiene base</div>
                              <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>Subí el molde (.ai) en <b>Moldería</b> para ver las medidas de cada pieza y poder cargar el diseño.</div>
                              <button className="btn primary" style={{ marginTop: 14 }} onClick={() => setTabAjustesMolde('molderia')}>Ir a Moldería</button>
                            </div>
                          ) : (
                            <>
                          {renderSelVerVariante()}
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                            Elegí la dimensión de <b>referencia</b> del diseño. El sistema calcula la otra para que cubra <b>todos los talles</b> sin huecos. Las medidas se ven sobre cada pieza en el visor.
                          </div>

                          <div>
                            <label style={{ display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 6, color: 'var(--text-secondary)' }}>Dimensión de referencia</label>
                            <div style={{ display: 'flex', gap: 6 }}>
                              {[{ k: 'alto', l: 'Alto manda' }, { k: 'ancho', l: 'Ancho manda' }].map(o => (
                                <button
                                  key={o.k}
                                  type="button"
                                  className={`chip ${(etqData?.referencia_medida || 'alto') === o.k ? 'active' : ''}`}
                                  style={{ flex: 1, textAlign: 'center', padding: '8px 6px' }}
                                  onClick={() => guardarReferencia(o.k)}
                                >
                                  {o.l}
                                </button>
                              ))}
                            </div>
                            <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 6, lineHeight: 1.4 }}>
                              {(etqData?.referencia_medida || 'alto') === 'alto'
                                ? 'El alto del diseño iguala el alto de la pieza; el ancho se calcula para cubrir el talle más ancho.'
                                : 'El ancho del diseño iguala el ancho de la pieza; el alto se calcula para cubrir el talle más alto.'}
                            </small>
                          </div>

                          {tallesMolde.length > 0 && (
                            <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 12 }}>
                              <label style={{ display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 7, color: 'var(--text-secondary)' }}>Cómo se adapta el diseño</label>
                              <div style={{ display: 'flex', gap: 6 }}>
                                {[['default', 'Default'], ['rango', 'Por rango'], ['talle', `${(term?.variante || 'Talle')} por ${(term?.variante || 'talle').toLowerCase()}`]].map(([k, lbl]) => (
                                  <button key={k} type="button" onClick={() => cambiarConfigMedida(k)}
                                    style={{ flex: '1 1 0', padding: '7px 8px', borderRadius: 9, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', lineHeight: 1.2, border: '1px solid ' + (configMedida === k ? 'var(--accent)' : 'var(--border-light)'), background: configMedida === k ? 'rgba(0,243,255,0.15)' : 'transparent', color: configMedida === k ? 'var(--accent)' : 'var(--text-muted)' }}>{lbl}</button>
                                ))}
                              </div>
                              {configMedida === 'default' && (
                                <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 8, lineHeight: 1.4 }}>Un solo diseño cubre TODOS los {(term?.variante || 'variante').toLowerCase()}s (mesa <b>sin</b> <code>#</code>). La caja punteada es la medida que sirve para todos.</small>
                              )}
                              {configMedida === 'talle' && (
                                <div style={{ marginTop: 9 }}>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                    {tallesMolde.map(t => (
                                      <button key={t} type="button" onClick={() => verVarianteOperario(t)}
                                        className={`chip ${etqData.talle_ref === t ? 'active' : ''}`} style={{ padding: '5px 11px' }}>{t}</button>
                                    ))}
                                  </div>
                                  <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 7, lineHeight: 1.4 }}>Cada pieza con su tamaño real en el {(term?.variante || 'variante').toLowerCase()} elegido (un diseño por {(term?.variante || 'variante').toLowerCase()}, mesa <code>#{etqData.talle_ref || 'XS'} Pieza</code>).</small>
                                </div>
                              )}
                              {configMedida === 'rango' && (
                                <div style={{ marginTop: 9 }}>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                    {tallesMolde.map((t, idx) => {
                                      const on = rangoMedida.includes(t);
                                      return <button key={t} type="button" onClick={(e) => toggleRango(t, idx, e)}
                                        style={{ padding: '5px 11px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', userSelect: 'none', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.15)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{t}</button>;
                                    })}
                                  </div>
                                  {rangoMedida.length > 0 && (
                                    <div style={{ marginTop: 9 }}>
                                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, marginBottom: 5, color: 'var(--text-secondary)' }}>Guía del rango <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(la base del cálculo)</span></label>
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                        {rangoMedida.map(t => {
                                          const cur = etqData.talle_ref === t;
                                          return <button key={t} type="button" onClick={() => verVarianteOperario(t)}
                                            style={{ padding: '4px 10px', borderRadius: 8, fontSize: 11.5, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (cur ? 'var(--accent)' : 'var(--border-light)'), background: cur ? 'rgba(0,243,255,0.15)' : 'transparent', color: cur ? 'var(--accent)' : 'var(--text-muted)' }}>{t}</button>;
                                        })}
                                      </div>
                                    </div>
                                  )}
                                  <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 7, lineHeight: 1.4 }}>Elegí el rango (click o <b>shift+click</b>) y la <b>guía del rango</b>. La caja iguala la dimensión de referencia de la <b>guía elegida</b> y crece con la proporción crítica <b>de ese rango</b>. En el arte: <code>#{rangoMedida[0] || 'XS'}-{rangoMedida[rangoMedida.length - 1] || 'L'} Pieza</code>.</small>
                                </div>
                              )}
                              <button type="button" className="btn ghost" style={{ width: '100%', marginTop: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }} onClick={descargarPdfGuia}>
                                <Icon name="download" style={{ width: 14, height: 14 }} />
                                {verVariante ? 'Descargar guía .ai (solo esta variable)' : 'Descargar guía .ai (molde completo)'}
                              </button>
                            </div>
                          )}

                          {mapeoData && (
                            <button className="btn" type="button"
                              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, borderColor: mapeandoDiseno ? 'var(--accent)' : undefined, color: mapeandoDiseno ? 'var(--accent)' : undefined }}
                              onClick={() => setMapeandoDiseno(v => !v)}>
                              <Icon name="eye" style={{ width: 14, height: 14 }} />
                              {mapeandoDiseno ? '↩ Ver medidas de las piezas' : 'Mapear diseño al molde'}
                            </button>
                          )}

                          <div style={{ display: 'flex', gap: 8, borderTop: '1px solid var(--border-light)', paddingTop: 12 }}>
                            <button type="button" onClick={descargarBase}
                              className="btn ghost"
                              title={verVariante ? 'Descargar solo los contornos de la variable en curso' : 'Descargar el .ai base del molde completo'}
                              style={{ fontSize: 11.5, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}
                            >
                              <Icon name="download" style={{ width: 12, height: 12, marginRight: 6 }} /> {verVariante ? 'Descargar base (variable)' : 'Descargar Base'}
                            </button>
                          </div>

                          {/* Guía "qué va en cada capa del .ai" → ventana emergente. */}
                          <button type="button" className="btn ghost" onClick={() => setGuiaCapasOpen(true)}
                            style={{ width: '100%', fontSize: 11.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span>Qué va en cada capa del .ai</span>
                            <span style={{ opacity: 0.55, fontSize: 15 }}>›</span>
                          </button>
                          <Modal open={guiaCapasOpen} onClose={() => setGuiaCapasOpen(false)} centrado maxWidth={560}
                            titulo="Cómo armar el .ai" subtitulo="Una capa por cada cosa · los nombres no distinguen mayúsculas ni acentos">
                            {(() => {
                              const copia = (t) => { navigator.clipboard?.writeText(t); showMsg(`Copiado: ${t}`); };
                              const reglaDe = (c) => (reglasPlanilla || []).find(r => r.id === c.reglaId) || (reglasPlanilla || []).find(r => r.comportamiento === (c.role || 'none'));
                              const capasTexto = (() => {
                                const seen = new Set(), out = [];
                                for (const c of (cols || [])) {
                                  const reg = reglaDe(c); const comp = reg?.comportamiento || c.role;
                                  if (comp !== 'nombre' && comp !== 'numero') continue;
                                  const nom = (reg?.nombre || c.label || '').trim(); const k = nom.toLowerCase();
                                  if (!nom || seen.has(k)) continue; seen.add(k);
                                  out.push({ nombre: nom, comp, columna: c.label || nom });
                                }
                                return out;
                              })();
                              const Capa = ({ nombre, color, tipo, children }) => (
                                <div style={{ display: 'flex', gap: 14, padding: '15px 0', borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                                  <div style={{ flexShrink: 0, width: 158 }}>
                                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '3px 4px 3px 10px' }}>
                                      <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 12.5, fontWeight: 700, color: '#fff', borderBottom: `2px solid ${color}`, paddingBottom: 1 }}>{nombre}</span>
                                      <button type="button" onClick={() => copia(nombre)} title="Copiar nombre de la capa"
                                        style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 24, height: 24, borderRadius: 6, border: 'none', background: 'transparent', color: 'var(--text-secondary)', cursor: 'pointer', transition: 'var(--transition-smooth)' }}
                                        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(0,243,255,0.12)'; e.currentTarget.style.color = 'var(--accent)'; }}
                                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}>
                                        <Icon name="copy" style={{ width: 13, height: 13 }} />
                                      </button>
                                    </div>
                                    <div style={{ fontSize: 9.5, color: 'var(--text-muted)', marginTop: 7, textTransform: 'uppercase', letterSpacing: '.06em' }}>{tipo}</div>
                                  </div>
                                  <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.55 }}>{children}</div>
                                </div>
                              );
                              return (
                                <div>
                                  <Capa nombre="diseño" color="#a78bfa" tipo="Se imprime">
                                    El arte que <b>se imprime</b>: gráficos, fondo y colores. El texto del diseño va en <b>curvas</b> (Texto → Crear contornos). El color sale tal cual viene, en CMYK exacto.
                                  </Capa>
                                  <Capa nombre="guias" color="#34d399" tipo="No se imprime">
                                    El <b>nombre de cada pieza</b> como texto, uno por mesa. No se imprime: el sistema lo usa para colocar cada diseño en su pieza solo. Los nombres exactos están en «Nombres de las piezas».
                                  </Capa>
                                  <div style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '.06em', marginTop: 18, marginBottom: -2 }}>
                                    Textos que se personalizan{capasTexto.length ? ' · una capa por cada uno' : ''}
                                  </div>
                                  {capasTexto.length ? capasTexto.map(ct => (
                                    <Capa key={ct.nombre} nombre={ct.nombre} color="#38bdf8" tipo={ct.comp === 'numero' ? 'Número' : 'Texto'}>
                                      El {ct.comp === 'numero' ? 'número' : 'texto'} de la columna <b>«{ct.columna}»</b> de la planilla. Hacé una capa con <b>este nombre exacto</b>; lo que escribas adentro es el placeholder. Se respeta su <b>tipografía, color y borde</b>.
                                    </Capa>
                                  )) : (
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '13px 0', lineHeight: 1.5, borderTop: '1px solid rgba(255,255,255,0.07)' }}>
                                      La planilla de este molde todavía no tiene columnas de texto/número que se estampen. Agregalas en <b>Planilla</b> y acá vas a ver una capa por cada una.
                                    </div>
                                  )}
                                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 16, lineHeight: 1.6, borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 13 }}>
                                    El texto se ubica <b>centrado</b> en el lugar del placeholder y toma el <b>tamaño</b> que tiene en el archivo, escalado igual que el resto del diseño en esa pieza. Si falta una capa, la tizada se arma igual y ese dato no se estampa.
                                  </div>
                                </div>
                              );
                            })()}
                          </Modal>

                          {/* Nombres de las piezas: para rotular la capa "guias" en Illustrator
                              (texto que no se imprime) y que el arte se auto-mapee sin errores. */}
                          {estado?.plantilla?.piezas?.length > 0 && (() => {
                            // Nombre de MESA que el arte LEE: nombre genérico ("Cuello 1..25" → "Cuello") +
                            // prefijo del modo (#talle / #rango; nada en default). Si hay una VARIABLE elegida,
                            // solo sus piezas (el número es el id interno, no se rotula en el diseño).
                            const _kv = verVariante ? nombresDeVariante(verVariante) : [];
                            const _keys = _kv.length ? _kv : (estado.plantilla.piezas || []);
                            const _pref = mesaPrefijo();
                            const nombresGen = [...new Set(_keys.map(nombreGenerico).filter(Boolean))].map(g => _pref + g);
                            return (
                            <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 12 }}>
                              <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 4 }}>Nombres de las piezas</div>
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.4 }}>
                                Pegalos como <b>texto</b> en la capa <b>guias</b> de cada mesa del diseño (no se imprime y el arte se mapea solo). El <b>#</b> sale del modo de arriba{_pref ? <> (<code>{_pref.trim()}</code>)</> : ' (default: sin #)'}{verVariante ? ' · solo la variable elegida' : ''}. Tocá uno para copiarlo, o copiá todos.
                              </div>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 8 }}>
                                {nombresGen.map(p => (
                                  <span key={p}
                                    onClick={() => { navigator.clipboard?.writeText(p); showMsg(`Copiado: ${p}`); }}
                                    title="Copiar este nombre"
                                    style={{ fontSize: 10.5, padding: '3px 8px', borderRadius: 5, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-light)', cursor: 'pointer', color: 'var(--text-primary)' }}>
                                    {p}
                                  </span>
                                ))}
                              </div>
                              <button className="btn ghost" style={{ width: '100%', fontSize: 11.5 }}
                                onClick={() => { navigator.clipboard?.writeText(nombresGen.join('\n')); showMsg('Nombres copiados ✓'); }}>
                                📋 Copiar todos los nombres
                              </button>
                            </div>
                            );
                          })()}

                          {mapeoData ? (
                            <>
                              <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 10 }}>
                                <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 8 }}>
                                  Mapeo de Mesas de Trabajo
                                </div>
                                <div style={{ maxHeight: '250px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                                  {mapeoData.piezas?.map(piezaName => {
                                    const val = mapeoValores[piezaName] || '';
                                    const isSel = selectedPiezaMapeo === piezaName;
                                    return (
                                      <div 
                                        key={piezaName}
                                        style={{
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'space-between',
                                          padding: '5px 8px',
                                          borderRadius: 6,
                                          backgroundColor: isSel ? 'rgba(0,243,255,0.08)' : 'rgba(255,255,255,0.01)',
                                          border: isSel ? '1px solid var(--accent)' : '1px solid transparent',
                                          cursor: 'pointer'
                                        }}
                                        onClick={() => setSelectedPiezaMapeo(piezaName)}
                                      >
                                        <span style={{ fontSize: 12, fontWeight: 600 }}>{piezaName}</span>
                                        <select
                                          value={val}
                                          style={{ padding: '3px 6px', fontSize: 11, width: '110px', borderRadius: 4, background: '#18181b', color: '#fff', border: '1px solid var(--border-light)' }}
                                          onChange={(e) => {
                                            const next = { ...mapeoValores };
                                            if (e.target.value) {
                                              next[piezaName] = parseInt(e.target.value);
                                            } else {
                                              delete next[piezaName];
                                            }
                                            setMapeoValores(next);
                                          }}
                                          onClick={(e) => e.stopPropagation()}
                                        >
                                          <option value="">-- Sin asignar --</option>
                                          {mapeoData.mesas?.map(m => (
                                            <option key={m.mesa} value={m.mesa}>Mesa {m.mesa}</option>
                                          ))}
                                        </select>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>

                              <button 
                                className="btn primary" 
                                style={{ width: '100%', marginTop: 8 }}
                                onClick={guardarMapeo}
                              >
                                Guardar Mapeo de Arte
                              </button>
                            </>
                          ) : (
                            <div className="upload-zone" onClick={() => fileInputArteRef.current.click()} style={{ padding: '24px 16px' }}>
                              <Icon name="upload" className="upload-icon" />
                              <div style={{ fontSize: 12.5, fontWeight: 600 }}>Sube el arte del diseño (.ai)</div>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>Para mapear las piezas impresas</div>
                            </div>
                          )}
                            </>
                          )}
                        </div>
                      )}

                      {tabAjustesMolde === 'planilla' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                          <div>
                            <label style={{ display: 'block', fontSize: 11, fontWeight: 700, marginBottom: 8, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Planilla vinculada</label>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                              {plantillasPlanillas.map(t => {
                                const sel = t.id === selectedPlanillaTemplateId;
                                return (
                                  <button key={t.id} onClick={() => setSelectedPlanillaTemplateId(t.id)}
                                    style={{ padding: '8px 13px', borderRadius: 9, fontSize: 12.5, fontWeight: 600, cursor: 'pointer', transition: 'all .2s',
                                      border: sel ? '1px solid var(--accent)' : '1px solid var(--border-light)',
                                      background: sel ? 'linear-gradient(180deg, rgba(0,216,245,0.14), rgba(0,216,245,0.03))' : 'transparent',
                                      color: sel ? 'var(--accent)' : 'var(--text-secondary)',
                                      boxShadow: sel ? '0 0 12px rgba(0,216,245,0.18)' : 'none' }}>
                                    {t.nombre}
                                  </button>
                                );
                              })}
                            </div>
                          </div>

                          {(() => {
                            const activeTemplate = plantillasPlanillas.find(t => t.id === selectedPlanillaTemplateId);
                            const cols = activeTemplate?.columnas || [];
                            const colsDeRol = (role) => cols.filter(c => (c.role || 'none') === role);
                            const usaManga = colsDeRol('manga').length > 0 && mapeoColumnas.manga;
                            const variantesCount = colsDeRol('talle').length;
                            return (
                              <>
                                <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 14, fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                                  Tocá los <b style={{ color: 'var(--accent)' }}>interruptores</b> en cada columna de la izquierda para encender las que usa <b>este molde</b>{variantesCount > 1 ? ' y elegir cuál es la variante' : ''}.
                                </div>

                                {usaManga && (
                                  <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 12 }}>
                                    <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Valores de Manga</div>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                      <div>
                                        <label style={{ display: 'block', fontSize: 10.5, fontWeight: 600, marginBottom: 4, color: 'var(--text-muted)' }}>Corta:</label>
                                        <input type="text" value={mapeoColumnas.manga_corta_val || ''} placeholder="corta" style={{ width: '100%', padding: '7px 9px', fontSize: 12, borderRadius: 7, backgroundColor: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff' }} onChange={(e) => setMapeoColumnas({ ...mapeoColumnas, manga_corta_val: e.target.value })} />
                                      </div>
                                      <div>
                                        <label style={{ display: 'block', fontSize: 10.5, fontWeight: 600, marginBottom: 4, color: 'var(--text-muted)' }}>Larga:</label>
                                        <input type="text" value={mapeoColumnas.manga_larga_val || ''} placeholder="larga" style={{ width: '100%', padding: '7px 9px', fontSize: 12, borderRadius: 7, backgroundColor: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff' }} onChange={(e) => setMapeoColumnas({ ...mapeoColumnas, manga_larga_val: e.target.value })} />
                                      </div>
                                    </div>
                                  </div>
                                )}

                                <button className="btn ghost" style={{ width: '100%', marginTop: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, color: 'var(--cmyk-cyan)', borderColor: 'var(--cmyk-cyan)' }} onClick={() => setProbandoPlanilla(v => !v)}>
                                  <Icon name="eye" style={{ width: 14, height: 14 }} /> {probandoPlanilla ? 'Cerrar visor' : 'Visualizar cómo carga este molde'}
                                </button>
                                <button className="btn primary" style={{ width: '100%' }} onClick={guardarConfigMapeoColumnas}>
                                  Guardar configuración de este molde
                                </button>
                              </>
                            );
                          })()}
                        </div>
                      )}

                      {tabAjustesMolde === 'terminologia' && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                            Elegí cómo se llaman los conceptos de cara al usuario. Solo cambian las etiquetas: el funcionamiento es exactamente el mismo.
                          </div>
                          <div>
                            <label style={{ display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 5, color: 'var(--text-secondary)' }}>Nombre de la variante (lo que hoy es “Talle”)</label>
                            <input
                              type="text"
                              value={terminologiaEdit.variante}
                              placeholder="Talle"
                              style={{ width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-light)', color: '#fff' }}
                              onChange={(e) => setTerminologiaEdit({ ...terminologiaEdit, variante: e.target.value })}
                            />
                            <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 4 }}>Ej.: Talle, Color, Variante, Modelo… Si tu molde no usa talles, nómbralo como quieras (cada capa del archivo es una variante).</small>
                          </div>
                          <div>
                            <label style={{ display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 5, color: 'var(--text-secondary)' }}>Nombre del molde</label>
                            <input
                              type="text"
                              value={nombreMoldeEdit}
                              placeholder="Ej.: Camiseta River, Buzo Capucha…"
                              style={{ width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-light)', color: '#fff' }}
                              onChange={(e) => setNombreMoldeEdit(e.target.value)}
                            />
                            <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 4 }}>Es el nombre que se muestra en la tarjeta del molde.</small>
                          </div>
                          <button className="btn primary" style={{ width: '100%', marginTop: 4 }} onClick={guardarTerminologia}>
                            Guardar Nombres
                          </button>
                        </div>
                      )}

                      {tabAjustesMolde === 'variables' && (() => {
                        const lbl = { display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 6, color: 'var(--text-secondary)' };
                        const inp = { width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' };
                        const iconBtn = { width: 30, height: 30, flexShrink: 0, borderRadius: 8, border: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.02)', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 14, lineHeight: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' };
                        const dangerBtn = { ...iconBtn, color: '#f87171', borderColor: 'rgba(248,113,113,0.3)' };
                        const chip = (txt, on, onClick, key) => (<button key={key} type="button" onClick={onClick} style={{ padding: '5px 11px', borderRadius: 8, fontSize: 11.5, fontWeight: 600, cursor: 'pointer', border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'rgba(255,255,255,0.02)', color: on ? 'var(--accent)' : 'var(--text-muted)' }}>{txt}</button>);
                        const tipos = variantesEdit;
                        const modelo = modelosEdit[modeloSel] || null;
                        const variables = (modelo && modelo.variables) || [];
                        const varActual = (varSel != null) ? variables[varSel] : null;
                        const varTerm = (term.variante || 'Talle').toLowerCase();
                        const valorLabel = (clave, vid) => { const t = tipos.find(x => x.clave === clave); const v = t && (t.valores || []).find(z => z.id === vid); return v ? v.label : null; };
                        const addTipo = () => setVariantesEdit(prev => [...prev, { clave: 't_' + uidVar(), label: '', valores: [] }]);
                        const renameTipo = (i, label) => setVariantesEdit(prev => prev.map((t, k) => k === i ? { ...t, label } : t));
                        const delTipo = (i) => { const clave = tipos[i] && tipos[i].clave; setVariantesEdit(prev => prev.filter((_, k) => k !== i)); if (clave) setModelosEdit(prev => prev.map(m => ({ ...m, variables: (m.variables || []).map(v => { const b = { ...(v.build || {}) }; delete b[clave]; return { ...v, build: b }; }) }))); };
                        const seedCamiseta = () => setVariantesEdit(['Frente', 'Espalda', 'Manga', 'Costadillo'].map(n => ({ clave: 't_' + uidVar(), label: n, valores: [] })));
                        const addModelo = () => { setModeloSel(modelosEdit.length); setVarSel(null); setModelosEdit(prev => [...prev, { id: 'm_' + uidVar(), nombre: 'Modelo ' + (prev.length + 1), variables: [] }]); };
                        const renameModelo = (i, nombre) => setModelosEdit(prev => prev.map((m, k) => k === i ? { ...m, nombre } : m));
                        const delModelo = (i) => { setModeloSel(0); setVarSel(null); setModelosEdit(prev => prev.filter((_, k) => k !== i)); };
                        const addVariable = () => { if (!modelo) return; const k = variables.length; setVarSel(k); setModelosEdit(prev => prev.map((m, mi) => mi === modeloSel ? { ...m, variables: [...(m.variables || []), { id: 'var_' + uidVar(), nombre: 'Variable ' + (k + 1), build: {} }] } : m)); };
                        const renameVariable = (k, nombre) => setModelosEdit(prev => prev.map((m, mi) => mi === modeloSel ? { ...m, variables: m.variables.map((v, z) => z === k ? { ...v, nombre } : v) } : m));
                        const delVariable = (k) => { setVarSel(null); setModelosEdit(prev => prev.map((m, mi) => mi === modeloSel ? { ...m, variables: m.variables.filter((_, z) => z !== k) } : m)); };
                        const setBuild = (k, clave, vid) => setModelosEdit(prev => prev.map((m, mi) => mi === modeloSel ? { ...m, variables: m.variables.map((v, z) => { if (z !== k) return v; const b = { ...(v.build || {}) }; if (b[clave] === vid) delete b[clave]; else b[clave] = vid; return { ...v, build: b }; }) } : m));
                        return (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            {/* Selector de pasos (se oculta al entrar al detalle de un grupo) */}
                            {/* En «mi molde» sólo existe el paso Nombrar (Grupos/Modelos son del catálogo). */}
                            {!grupoAislado && !modeloAbierto && !grupoPzAbierto && !modoMiMolde && (
                            <div style={{ display: 'flex', gap: 6, background: 'rgba(255,255,255,0.03)', padding: 4, borderRadius: 10 }}>
                              {[{ k: 'nombrar', n: '1. Nombrar' }, { k: 'grupos', n: '2. Grupos' }, { k: 'combinar', n: '3. Modelos' }].map(s => (
                                <button key={s.k} type="button" onClick={() => { setVarStep(s.k); setAsignandoTipo(null); setGrupoAislado(null); setModeloAbierto(null); setComboVisor(null); setModoAcomodar(false); setAsignandoConjunto(null); setGrupoPzAbierto(null); setAsignandoGrupoPz(null); setEditandoNombre(null); }} style={{ flex: 1, padding: '8px 8px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer', border: 'none', background: varStep === s.k ? 'var(--accent)' : 'transparent', color: varStep === s.k ? '#04222b' : 'var(--text-secondary)' }}>{s.n}</button>
                              ))}
                            </div>
                            )}

                            {varStep === 'nombrar' && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.45 }}>
                                  <b>Paso 1.</b> Nombrá las piezas del molde. Seleccionalas en el visor (clic, o <b>arrastrá un recuadro</b> desde un espacio vacío para varias), escribí el nombre y aplicá. Si elegís varias, se numeran solas (Frente 1, Frente 2…).
                                </div>
                                {!etqData ? (
                                  <div style={{ fontSize: 12, color: 'var(--warning)', padding: '9px 11px', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 10, background: 'rgba(245,158,11,0.06)' }}>
                                    Subí el molde en la pestaña <b>Moldería</b> para ver las piezas.
                                  </div>
                                ) : editandoNombre ? (() => {
                                  const nEd = Object.values(etqNombres).filter(nm => nm && nombreGenerico(nm) === editandoNombre).length;
                                  return (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, border: '1px solid var(--accent)', borderRadius: 12, padding: 12, background: 'rgba(0,243,255,0.05)' }}>
                                      <div style={{ fontSize: 13.5, fontWeight: 700 }}>Editando: <span style={{ color: 'var(--accent)' }}>{editandoNombre}</span></div>
                                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>Tocá una pieza en el visor para <b>sumarla o quitarla</b> de este nombre (o arrastrá un recuadro para sumar varias). Las <b style={{ color: 'var(--accent)' }}>celestes</b> son las que tienen este nombre.</div>
                                      <div style={{ fontSize: 12 }}><b style={{ color: 'var(--accent)', fontSize: 15 }}>{nEd}</b> pieza{nEd === 1 ? '' : 's'} con «{editandoNombre}»</div>
                                      <button type="button" className="btn primary" style={{ width: '100%' }} onClick={() => { setEditandoNombre(null); guardarEtiquetas(); }}>Listo</button>
                                    </div>
                                  );
                                })() : (
                                  <>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                      Seleccionadas: <b style={{ color: 'var(--accent)' }}>{selNombrar.size}</b> · Nombradas: <b style={{ color: 'var(--success)' }}>{Object.values(etqNombres).filter(Boolean).length}</b> de {etqData.piezas.length}
                                    </div>
                                    <input value={etqNombreInput} onChange={(e) => setEtqNombreInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); nombrarSeleccionadas(); } }} placeholder="Nombre (ej.: Frente, Cuello…)" style={inp} />
                                    <div style={{ display: 'flex', gap: 8 }}>
                                      <button type="button" className="btn primary" style={{ flex: 1 }} disabled={!selNombrar.size} onClick={nombrarSeleccionadas}>Nombrar {selNombrar.size || ''} pieza{selNombrar.size === 1 ? '' : 's'}</button>
                                      {selNombrar.size > 0 && <button type="button" className="btn ghost" onClick={() => setSelNombrar(new Set())}>Limpiar</button>}
                                    </div>
                                    <button type="button" className="btn" style={{ width: '100%' }} onClick={guardarEtiquetas}>Guardar nombres</button>
                                    <button type="button" className="btn ghost" style={{ width: '100%', fontSize: 12 }} onClick={() => { setRenombrarBuf(null); setGrupoNombresAbierto(null); setModalNombres(true); }}>
                                      Nombres puestos ({Object.values(etqNombres).filter(Boolean).length}) — ver / editar
                                    </button>
                                    <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5, borderTop: '1px solid var(--border-light)', paddingTop: 10 }}>
                                      {modoMiMolde
                                        ? <>Cuando termines, guardá los nombres y volvé al pedido con el botón de arriba.</>
                                        : <>Cuando termines, pasá a <b>Grupos</b> (arriba) para revisar cómo quedaron agrupadas.</>}
                                    </div>
                                  </>
                                )}
                              </div>
                            )}

                            {varStep === 'grupos' && (
                              !etqData ? (
                                <div style={{ fontSize: 12, color: 'var(--warning)', padding: '9px 11px', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 10, background: 'rgba(245,158,11,0.06)' }}>Subí el molde en <b>Moldería</b> para ver las piezas.</div>
                              ) : grupoAislado ? (() => {
                                /* ── DETALLE DEL GRUPO ── */
                                const gi = (variantesEdit || []).findIndex(x => x.clave === grupoAislado);
                                const g = variantesEdit[gi];
                                if (!g) return <button className="btn ghost" onClick={() => setGrupoAislado(null)}>⬅ Volver</button>;
                                const nPz = (g.valores || []).filter(v => v.pieza_idx != null).length;
                                const asignando = asignandoTipo === g.clave;
                                const vinc = vinculandoJuntas === g.clave;
                                const bundles = g.juntas || [];
                                const nombresSel = Array.from(new Set(Array.from(juntasSel).map(i => nombreGenerico(_nombreDeIdx(i))).filter(Boolean)));
                                return (
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    <button type="button" className="btn ghost" onClick={() => { setAsignandoTipo(null); setVinculandoJuntas(null); setModoAcomodar(false); setGrupoAislado(null); }} style={{ alignSelf: 'flex-start', fontSize: 12, padding: '6px 10px' }}>⬅ Volver a las variables</button>
                                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                      <input value={g.label} placeholder="Nombre de la variable" onChange={(e) => renameTipo(gi, e.target.value)} style={{ ...inp, fontWeight: 600, fontSize: 14 }} />
                                      <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>{nPz} pza{nPz === 1 ? '' : 's'}</span>
                                    </div>
                                    {!vinc && (
                                      <div style={{ display: 'flex', gap: 6 }}>
                                        <button type="button" className="btn primary" style={{ flex: 1, fontSize: 12 }} onClick={() => guardarGrupos()}>Guardar cambios</button>
                                        <button type="button" className="btn" style={{ flex: 1, fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, borderColor: asignando ? 'var(--accent)' : undefined, color: asignando ? 'var(--accent)' : undefined }} onClick={() => { setModoAcomodar(false); setAsignandoTipo(asignando ? null : g.clave); }}>
                                          <Icon name={asignando ? 'check' : 'plus'} style={{ width: 12, height: 12 }} /> {asignando ? 'Listo' : 'Cargar piezas'}
                                        </button>
                                      </div>
                                    )}
                                    {/* ── MODO VINCULAR "van juntas": elegir 2+ piezas + nombre común ── */}
                                    {vinc && (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, border: '1px solid #f59e0b', borderRadius: 12, padding: 12, background: 'rgba(245,158,11,0.06)' }}>
                                        <div style={{ fontSize: 13, fontWeight: 700, color: '#f59e0b' }}>⛓ Piezas que van juntas</div>
                                        <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>Tocá <b>acá en el visor</b> (sobre la variante acomodada) <b>2 o más</b> piezas que van <b>siempre juntas</b> (ej.: manga corta + su vivo). Al elegir la principal, la compañera entra sola; y comparten un mismo nombre.</div>
                                        <div style={{ fontSize: 12 }}><b style={{ color: '#f59e0b', fontSize: 15 }}>{juntasSel.size}</b> pieza{juntasSel.size === 1 ? '' : 's'} elegida{juntasSel.size === 1 ? '' : 's'}</div>
                                        {nombresSel.length > 0 && (
                                          <div>
                                            <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginBottom: 5 }}>¿Qué nombre usan las dos? (tocá uno)</div>
                                            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                                              {nombresSel.map(nm => (
                                                <button key={nm} type="button" onClick={() => setJuntasNombre(nm)} style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (juntasNombre === nm ? '#f59e0b' : 'var(--border-light)'), background: juntasNombre === nm ? 'rgba(245,158,11,0.14)' : 'transparent', color: juntasNombre === nm ? '#f59e0b' : 'var(--text-muted)' }}>{nm}</button>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                        <div style={{ display: 'flex', gap: 6 }}>
                                          <button type="button" className="btn primary" style={{ flex: 1, fontSize: 12 }} disabled={juntasSel.size < 2} onClick={() => { crearVinculoJuntas(g.clave, Array.from(juntasSel), juntasNombre || (nombresSel[0] || '')); setVinculandoJuntas(null); setJuntasSel(new Set()); setJuntasNombre(''); }}>Crear vínculo</button>
                                          <button type="button" className="btn ghost" style={{ flex: 1, fontSize: 12 }} onClick={() => { setVinculandoJuntas(null); setJuntasSel(new Set()); setJuntasNombre(''); }}>Cancelar</button>
                                        </div>
                                      </div>
                                    )}
                                    {!asignando && !vinc && nidoLoading && (
                                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5, color: 'var(--text-secondary)', padding: '7px 10px', border: '1px solid var(--border-light)', borderRadius: 9 }}>
                                        <span style={{ width: 13, height: 13, border: '2px solid rgba(255,255,255,0.15)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
                                        Armando todos los talles… (una sola vez, después queda al instante)
                                      </div>
                                    )}
                                    {!asignando && !vinc && !nidoLoading && nidoError && (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 11.5, color: 'var(--warning)', padding: '8px 10px', border: '1px solid rgba(245,158,11,0.35)', borderRadius: 9, background: 'rgba(245,158,11,0.06)' }}>
                                        <div>No se pudo armar el nido de talles: {nidoError}</div>
                                        <button type="button" className="btn" style={{ alignSelf: 'flex-start', fontSize: 11, padding: '4px 12px' }} onClick={() => cargarNido(true)}>↻ Reintentar</button>
                                      </div>
                                    )}
                                    {!asignando && !vinc && !nidoLoading && !nidoError && nidoData && nidoVarPiezas().length === 0 && (
                                      <div style={{ fontSize: 11.5, color: 'var(--warning)', padding: '7px 10px', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 9, background: 'rgba(245,158,11,0.06)' }}>
                                        Las piezas de esta variable no tienen <b>nombre</b> — se muestra solo el talle actual. Nombralas en el <b>Paso 1</b> para ver todos los talles.
                                      </div>
                                    )}
                                    {/* ── Piezas que van juntas (vínculos de la variable) ── */}
                                    {!asignando && !vinc && (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 7, border: '1px solid var(--border-light)', borderRadius: 11, padding: 11 }}>
                                        <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-secondary)' }}>⛓ Piezas que van juntas <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· van y se nombran juntas (ej. manga + su vivo)</span></div>
                                        {bundles.length > 0 && (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                                            {bundles.map(b => (
                                              <div key={b.id} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, padding: '5px 8px', borderRadius: 8, background: 'rgba(167,139,250,0.10)', border: '1px solid rgba(167,139,250,0.3)' }}>
                                                <span style={{ color: '#c4b5fd', fontWeight: 700 }}>{b.nombre}</span>
                                                <span style={{ color: 'var(--text-muted)' }}>· {(b.piezas || []).length} piezas: {(b.piezas || []).map(i => _nombreDeIdx(i)).join(', ')}</span>
                                                <button title="Quitar vínculo" onClick={() => borrarVinculoJuntas(g.clave, b.id)} style={{ marginLeft: 'auto', border: 'none', background: 'transparent', color: '#f87171', cursor: 'pointer', fontSize: 13, lineHeight: 1 }}>✕</button>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                        <button type="button" className="btn" disabled={nPz < 2} style={{ fontSize: 11.5, alignSelf: 'flex-start', padding: '5px 12px', opacity: nPz < 2 ? 0.5 : 1 }} onClick={() => { setAsignandoTipo(null); setModoAcomodar(false); setJuntasSel(new Set()); setJuntasNombre(''); setVinculandoJuntas(g.clave); }}>＋ Vincular piezas</button>
                                        {nPz < 2 && <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>Cargá al menos 2 piezas para poder vincularlas.</div>}
                                      </div>
                                    )}
                                    {!vinc && (estado?.talles || []).length > 1 && (
                                      <div>
                                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginBottom: 5 }}>Resaltar {term.variante.toLowerCase()} (celeste en el visor):</div>
                                        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                                          {estado.talles.map(t => (
                                            <button key={t} type="button" onClick={() => cargarTalleEtq(t)} style={{ padding: '4px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700, cursor: 'pointer', border: '1px solid ' + (etqData?.talle_ref === t ? 'var(--accent)' : 'var(--border-light)'), background: etqData?.talle_ref === t ? 'rgba(0,243,255,0.12)' : 'transparent', color: etqData?.talle_ref === t ? 'var(--accent)' : 'var(--text-muted)' }}>{t}</button>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                    {!vinc && (
                                      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5, borderTop: '1px solid var(--border-light)', paddingTop: 10 }}>
                                        {asignando ? <>Tocá las piezas (o arrastrá un recuadro) que <b>forman esta variable</b>. Después <b>Listo</b>.</> : <>En el visor ves las piezas de esta variable con <b>todos sus talles nesteados</b>. <b>Arrastrá una pieza</b> para acomodarla (se mueven todas sus tallas juntas) — la posición <b>se guarda sola</b>.</>}
                                      </div>
                                    )}
                                  </div>
                                );
                              })() : grupoPzAbierto ? (() => {
                                /* ── DETALLE DEL GRUPO: elegir piezas + VARIABLES A MANO (sin generación automática) ── */
                                const gp = (gruposPz || []).find(x => x.id === grupoPzAbierto);
                                if (!gp) return <button className="btn ghost" onClick={() => { setGrupoPzAbierto(null); setAsignandoGrupoPz(null); }}>⬅ Volver</button>;
                                const eligiendo = asignandoGrupoPz === gp.id;
                                const varsGrupo = (variantesEdit || []).filter(v => v.grupoId === gp.id);
                                const varAsignando = asignandoTipo ? varsGrupo.find(v => v.clave === asignandoTipo) : null;
                                const inpG = { width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' };
                                const crearVar = () => {
                                  const clave = 'v_' + uidVar();
                                  const nueva = [...(variantesEdit || []), { clave, label: nuevaVarNombre.trim(), grupoId: gp.id, valores: [] }];
                                  setVariantesEdit(nueva); guardarGruposCon(nueva, true);
                                  setNuevaVarNombre(''); setAsignandoGrupoPz(null); setAsignandoTipo(clave);
                                };
                                return (
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    <button type="button" className="btn ghost" onClick={() => { setAsignandoGrupoPz(null); setAsignandoTipo(null); setGrupoPzAbierto(null); }} style={{ alignSelf: 'flex-start', fontSize: 12, padding: '6px 10px' }}>⬅ Volver a los grupos</button>
                                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                      <input value={gp.nombre} placeholder="Nombre del grupo" onChange={(e) => aplicarGruposPz(arr => arr.map(g => g.id === gp.id ? { ...g, nombre: e.target.value } : g))} style={{ ...inpG, fontWeight: 600, fontSize: 14 }} />
                                      <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>{(gp.piezas || []).length} pza{(gp.piezas || []).length === 1 ? '' : 's'}</span>
                                    </div>
                                    <button type="button" className="btn" style={{ width: '100%', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, borderColor: eligiendo ? 'var(--accent)' : undefined, color: eligiendo ? 'var(--accent)' : undefined }} onClick={() => { setAsignandoTipo(null); setAsignandoGrupoPz(eligiendo ? null : gp.id); }}>
                                      <Icon name={eligiendo ? 'check' : 'plus'} style={{ width: 12, height: 12 }} /> {eligiendo ? 'Listo' : 'Elegir piezas del grupo'}
                                    </button>
                                    {eligiendo && (
                                      <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.5, padding: '8px 10px', border: '1px solid var(--accent)', borderRadius: 9, background: 'rgba(0,243,255,0.05)' }}>
                                        Tocá las piezas (o arrastrá un recuadro). Una pieza <b>puede estar en varios grupos</b>. Después <b>Listo</b>.
                                      </div>
                                    )}
                                    {!eligiendo && (<>
                                      {/* eligiendo piezas de una VARIABLE */}
                                      {varAsignando ? (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, border: '1px solid var(--accent)', borderRadius: 12, padding: 12, background: 'rgba(0,243,255,0.05)' }}>
                                          <div style={{ fontSize: 13, fontWeight: 700 }}>{varAsignando.label || 'Variable'}</div>
                                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>Tocá en el visor (o arrastrá un recuadro) las piezas del grupo que <b>forman esta variable</b>. Tocá una elegida para sacarla.</div>
                                          <div style={{ fontSize: 12 }}><b style={{ color: 'var(--accent)', fontSize: 15 }}>{((varAsignando.valores || []).filter(x => x.pieza_idx != null)).length}</b> pieza{((varAsignando.valores || []).filter(x => x.pieza_idx != null)).length === 1 ? '' : 's'} elegida{((varAsignando.valores || []).filter(x => x.pieza_idx != null)).length === 1 ? '' : 's'}</div>
                                          <button type="button" className="btn primary" style={{ width: '100%' }} onClick={() => { setAsignandoTipo(null); guardarGrupos(); }}>Listo</button>
                                        </div>
                                      ) : (<>
                                        {/* crear variable A MANO */}
                                        <div style={{ border: '1px solid var(--border-light)', borderRadius: 12, padding: 11, display: 'flex', flexDirection: 'column', gap: 8 }}>
                                          <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-secondary)' }}>Nueva variable <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· ponele nombre y elegí sus piezas</span></div>
                                          <div style={{ display: 'flex', gap: 6 }}>
                                            <input value={nuevaVarNombre} onChange={(e) => setNuevaVarNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && nuevaVarNombre.trim()) { e.preventDefault(); crearVar(); } }} placeholder="Nombre (ej.: Cuello V manga corta)" style={{ ...inpG, flex: 1, width: 'auto' }} />
                                            <button type="button" className="btn primary" style={{ fontSize: 12, whiteSpace: 'nowrap' }} disabled={!nuevaVarNombre.trim()} onClick={crearVar}>+ Elegir piezas</button>
                                          </div>
                                        </div>
                                        {/* Variables del grupo */}
                                        {varsGrupo.length === 0 ? (
                                          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '6px 0' }}>Todavía no hay variables en este grupo.</div>
                                        ) : (
                                          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                            <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', fontWeight: 700 }}>Variables de «{gp.nombre || 'grupo'}» ({varsGrupo.length}) <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>· tocá una para verla / acomodarla</span></div>
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, maxHeight: 380, overflowY: 'auto' }}>
                                              {varsGrupo.map(v => {
                                                const nPz = (v.valores || []).filter(x => x.pieza_idx != null).length;
                                                return (
                                                  <div key={v.clave} onClick={() => { setAsignandoTipo(null); setGrupoAislado(v.clave); }} style={{ border: '1px solid var(--border-light)', borderRadius: 10, padding: '10px 11px', cursor: 'pointer', background: 'rgba(255,255,255,0.02)', position: 'relative' }}>
                                                    <div style={{ fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 14 }}>{v.label || 'Variable'}</div>
                                                    <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 3 }}>{nPz} pza{nPz === 1 ? '' : 's'}</div>
                                                    <button title="Elegir piezas" onClick={(e) => { e.stopPropagation(); setAsignandoGrupoPz(null); setAsignandoTipo(v.clave); }} style={{ position: 'absolute', bottom: 5, right: 5, borderRadius: 6, border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 10, padding: '2px 7px' }}>piezas</button>
                                                    <button title="Borrar variable" onClick={(e) => { e.stopPropagation(); delVariablePorClave(v.clave); }} style={{ position: 'absolute', top: 5, right: 5, width: 20, height: 20, borderRadius: 6, border: 'none', background: 'transparent', color: '#f87171', cursor: 'pointer', fontSize: 13, lineHeight: 1 }}>✕</button>
                                                  </div>
                                                );
                                              })}
                                            </div>
                                          </div>
                                        )}
                                      </>)}
                                    </>)}
                                  </div>
                                );
                              })() : (
                                /* ── LISTA DE GRUPOS (la generación corre DENTRO de cada grupo) ── */
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                  {(() => {
                                    const inpG = { width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' };
                                    const crear = () => { const id = 'gp_' + uidVar(); const nueva = [...(gruposPz || []), { id, nombre: nuevoGrupoPzNombre.trim(), piezas: [] }]; setGruposPz(nueva); guardarGruposPzCon(nueva); setNuevoGrupoPzNombre(''); setGrupoPzAbierto(id); setAsignandoGrupoPz(id); };
                                    return (<>
                                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.45 }}>Creá <b>grupos de piezas</b> y armá las variables <b>a mano adentro de cada grupo</b>. Una pieza puede estar en varios grupos.</div>
                                      <input value={nuevoGrupoPzNombre} onChange={(e) => setNuevoGrupoPzNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && nuevoGrupoPzNombre.trim()) { e.preventDefault(); crear(); } }} placeholder="Nombre del grupo (ej.: MP1)" style={inpG} />
                                      <button type="button" className="btn primary" style={{ width: '100%' }} disabled={!nuevoGrupoPzNombre.trim()} onClick={crear}>Crear grupo</button>
                                    </>);
                                  })()}
                                  {(gruposPz || []).length === 0 ? (
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '10px 0' }}>Todavía no hay grupos. Escribí un nombre y tocá “Crear grupo”.</div>
                                  ) : (
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                      {(gruposPz || []).map(g => {
                                        const nVars = (variantesEdit || []).filter(v => v.grupoId === g.id).length;
                                        return (
                                          <div key={g.id} onClick={() => { setAsignandoGrupoPz(null); setGrupoPzAbierto(g.id); }} style={{ border: '1px solid var(--border-light)', borderRadius: 10, padding: '11px 12px', cursor: 'pointer', background: 'rgba(255,255,255,0.02)', position: 'relative' }}>
                                            <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 14 }}>{g.nombre || 'Sin nombre'}</div>
                                            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{(g.piezas || []).length} pza{(g.piezas || []).length === 1 ? '' : 's'}{nVars ? <span style={{ color: 'var(--success)' }}> · {nVars} var.</span> : ''}</div>
                                            <button title="Borrar grupo (y sus variables)" onClick={(e) => { e.stopPropagation(); const nv = (variantesEdit || []).filter(v => v.grupoId !== g.id); setVariantesEdit(nv); guardarGruposCon(nv, true); aplicarGruposPz(arr => arr.filter(x => x.id !== g.id)); }} style={{ position: 'absolute', top: 5, right: 5, width: 20, height: 20, borderRadius: 6, border: 'none', background: 'transparent', color: '#f87171', cursor: 'pointer', fontSize: 13, lineHeight: 1 }}>✕</button>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                </div>
                              )
                            )}

                            {varStep === 'combinar' && (() => {
                              const variables = (variantesEdit || []).filter(v => (v.valores || []).some(x => x.pieza_idx != null)); // variables con piezas
                              const modelos = (modelosEdit || []).filter(m => Array.isArray(m.variantes)); // modelos con la forma nueva (grupo de variables)
                              const piezasDe = (v) => (v.valores || []).map(x => x.pieza_idx).filter(x => x != null);
                              const mismasPiezas = (a, b) => a && b && a.length === b.length && a.every(x => b.includes(x));
                              // aplicar un cambio a los modelos y persistir
                              const aplicarModelos = (fn) => { const nueva = fn(modelosEdit || []); setModelosEdit(nueva); guardarModelosCon(nueva); };

                              // ── DETALLE DEL MODELO (elegir qué variables lo componen) ──
                              if (modeloAbierto) {
                                const modelo = (modelosEdit || []).find(m => m.id === modeloAbierto);
                                if (!modelo) return <button type="button" className="btn ghost" onClick={() => { setModeloAbierto(null); setComboVisor(null); }}>⬅ Volver</button>;
                                const enModelo = new Set(modelo.variantes || []);
                                return (
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                    <button type="button" className="btn ghost" onClick={() => { setModeloAbierto(null); setComboVisor(null); }} style={{ alignSelf: 'flex-start', fontSize: 12, padding: '6px 10px' }}>⬅ Volver a los modelos</button>
                                    <input value={modelo.nombre} placeholder="Nombre del modelo" onChange={(e) => aplicarModelos(arr => arr.map(m => m.id === modelo.id ? { ...m, nombre: e.target.value } : m))} style={{ ...inp, fontWeight: 600, fontSize: 14 }} />
                                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>Tocá las <b>variables</b> que forman este modelo (quedan con <b style={{ color: 'var(--accent)' }}>✓</b>). El <b>👁</b> la muestra en el visor.</div>
                                    {variables.length === 0 ? (
                                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', padding: '9px 11px', border: '1px dashed var(--border-light)', borderRadius: 10 }}>Todavía no hay variables. Crealas en el <b>Paso 2 · Variables</b>.</div>
                                    ) : (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                        {variables.map(v => {
                                          const on = enModelo.has(v.clave);
                                          const pz = piezasDe(v);
                                          const viendo = mismasPiezas(comboVisor, pz);
                                          return (
                                            <div key={v.clave} style={{ display: 'flex', alignItems: 'stretch', gap: 6, border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), borderRadius: 9, background: on ? 'rgba(0,243,255,0.06)' : 'rgba(255,255,255,0.02)', overflow: 'hidden' }}>
                                              <button type="button" onClick={() => aplicarModelos(arr => arr.map(m => m.id === modelo.id ? { ...m, variantes: on ? (m.variantes || []).filter(c => c !== v.clave) : [...(m.variantes || []), v.clave] } : m))} style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', color: '#e4e4e7' }}>
                                                <span style={{ width: 16, height: 16, borderRadius: 4, flexShrink: 0, border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'var(--accent)' : 'transparent', color: '#04222b', fontSize: 12, fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 }}>{on ? '✓' : ''}</span>
                                                <span style={{ fontSize: 12.5, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.label || 'Sin nombre'}{(() => { const gpn = v.grupoId ? ((gruposPz || []).find(x => x.id === v.grupoId) || {}).nombre : null; return gpn ? <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}> · {gpn}</span> : null; })()}</span>
                                                <span style={{ fontSize: 10.5, color: 'var(--text-muted)', flexShrink: 0 }}>{pz.length} pza{pz.length === 1 ? '' : 's'}</span>
                                              </button>
                                              <button type="button" title="Ver en el visor" onClick={() => setComboVisor(viendo ? null : pz)} style={{ width: 34, flexShrink: 0, border: 'none', borderLeft: '1px solid var(--border-light)', background: viendo ? 'rgba(16,185,129,0.15)' : 'transparent', color: viendo ? 'var(--success)' : 'var(--text-muted)', cursor: 'pointer', fontSize: 14 }}>👁</button>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    )}
                                    <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5, borderTop: '1px solid var(--border-light)', paddingTop: 10 }}>Este modelo tiene <b style={{ color: 'var(--accent)' }}>{(modelo.variantes || []).length}</b> variable{(modelo.variantes || []).length === 1 ? '' : 's'}. Se guarda solo.</div>
                                  </div>
                                );
                              }

                              // ── LISTA DE MODELOS ──
                              return (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                  {!etqData ? (
                                    <div style={{ fontSize: 12, color: 'var(--warning)', padding: '9px 11px', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 10, background: 'rgba(245,158,11,0.06)' }}>Subí el molde en <b>Moldería</b>.</div>
                                  ) : (<>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.45 }}>Un <b>modelo</b> es un grupo de <b>variables</b> ya creadas. Ponele nombre y elegí sus variables.</div>
                                    {(() => { const crear = () => { const id = 'mod_' + uidVar(); const nueva = [...(modelosEdit || []), { id, nombre: nuevoModeloNombre.trim(), variantes: [] }]; setModelosEdit(nueva); guardarModelosCon(nueva); setNuevoModeloNombre(''); setComboVisor(null); setModeloAbierto(id); };
                                      return (<>
                                        <input value={nuevoModeloNombre} onChange={(e) => setNuevoModeloNombre(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && nuevoModeloNombre.trim()) { e.preventDefault(); crear(); } }} placeholder="Nombre del modelo (ej.: Pro)" style={inp} />
                                        <button type="button" className="btn primary" style={{ width: '100%' }} disabled={!nuevoModeloNombre.trim()} onClick={crear}>Crear modelo</button>
                                      </>); })()}
                                    {modelos.length === 0 ? (
                                      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '10px 0' }}>Todavía no hay modelos. Escribí un nombre y tocá “Crear modelo”.</div>
                                    ) : (
                                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                        {modelos.map(m => {
                                          const nVars = (m.variantes || []).length;
                                          return (
                                            <div key={m.id} onClick={() => { setComboVisor(null); setModeloAbierto(m.id); }} style={{ border: '1px solid var(--border-light)', borderRadius: 10, padding: '11px 12px', cursor: 'pointer', background: 'rgba(255,255,255,0.02)', position: 'relative' }}>
                                              <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', paddingRight: 14 }}>{m.nombre || 'Sin nombre'}</div>
                                              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>{nVars} variable{nVars === 1 ? '' : 's'}</div>
                                              <button title="Borrar modelo" onClick={(e) => { e.stopPropagation(); aplicarModelos(arr => arr.filter(x => x.id !== m.id)); }} style={{ position: 'absolute', top: 5, right: 5, width: 20, height: 20, borderRadius: 6, border: 'none', background: 'transparent', color: '#f87171', cursor: 'pointer', fontSize: 13, lineHeight: 1 }}>✕</button>
                                            </div>
                                          );
                                        })}
                                      </div>
                                    )}
                                  </>)}
                                </div>
                              );
                            })()}

                          </div>
                        );
                      })()}
                          </div>
                        )}
                      </div>

                    {/* Lienzo del molde (Izquierda) — alto fijo: no se estira con la barra lateral */}
                    <div className="card" style={{ display: 'flex', flexDirection: 'column', padding: 20, height: 620, overflow: 'hidden', order: 1, position: 'sticky', top: 24 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, borderBottom: '1px solid var(--border-light)', paddingBottom: 10 }}>
                        <div style={{ fontSize: 14, fontWeight: 700 }}>
                          {tabAjustesMolde === 'planilla' ? 'Planilla · mapeo de columnas' : 'Visor del Molde Vectorial'}
                        </div>
                        {etqData && tabAjustesMolde !== 'planilla' && (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {/* Qué está mostrando el visor. En las vistas especiales NO es una capa
                                de talle: con «por piezas» es el archivo sin separar y en la vista
                                junta son todas las variantes a la vez — decir «Capa: Capa 1» ahí
                                hacía creer que el molde había perdido sus variantes. */}
                            {varPzModo
                              ? `Mesa: ${etqData.mesa} · todas las piezas, sin separar`
                              : (empModo && empTodas && empTodasData?.piezas?.length)
                                ? `Mesa: ${etqData.mesa} · todas las ${term.variante.toLowerCase()}s juntas`
                                : `Mesa: ${etqData.mesa} · ${term.variante}: ${etqData.talle_ref}`}
                          </div>
                        )}
                      </div>

                      <div style={{
                        flex: 1,
                        background: 'rgba(9, 9, 11, 0.4)',
                        backgroundImage: 'radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px)',
                        backgroundSize: '16px 16px',
                        border: '1px solid var(--border-light)',
                        borderRadius: 12,
                        padding: 16,
                        display: 'flex',
                        alignItems: (etqData && tabAjustesMolde !== 'planilla') ? 'flex-start' : 'center',
                        justifyContent: (etqData && tabAjustesMolde !== 'planilla') ? 'flex-start' : 'center',
                        overflow: (etqData && tabAjustesMolde !== 'planilla') ? 'hidden' : 'auto',
                        minHeight: 400,
                        backgroundColor: '#0c0c0e',
                        position: 'relative'
                      }}
                        ref={setVisorEl}
                        onMouseDown={(e) => {
                          if (e.button === 2 && etqData && tabAjustesMolde !== 'planilla') { panVisor(e); return; }
                          // `empModo` va acá o el recuadro NO se dibuja al agrupar piezas: este panel
                          // vive fuera de la pestaña Variables (el gesto quedaba sólo con el clic).
                          if (e.button === 0 && (varPzModo || empModo || (tabAjustesMolde === 'variables' && (asignandoTipo || asignandoConjunto || asignandoGrupoPz || varStep === 'nombrar'))) && !(e.target.closest && e.target.closest('[data-piece]'))) iniciarRubber(e);
                          /* nota: en modo editar-nombre el recuadro también aplica (varStep==='nombrar') */
                        }}
                        onContextMenu={(e) => { if (etqData && tabAjustesMolde !== 'planilla') e.preventDefault(); }}>
                        {rubber && visorWheel.current.el && (() => {
                          const r = visorWheel.current.el.getBoundingClientRect();
                          const l = Math.min(rubber.x0, rubber.x1) - r.left, t = Math.min(rubber.y0, rubber.y1) - r.top;
                          const w = Math.abs(rubber.x1 - rubber.x0), h = Math.abs(rubber.y1 - rubber.y0);
                          return <div style={{ position: 'absolute', left: l, top: t, width: w, height: h, border: '1.5px dashed var(--accent)', background: 'rgba(0,243,255,0.10)', zIndex: 6, pointerEvents: 'none', borderRadius: 3 }} />;
                        })()}
                        {etqData && tabAjustesMolde !== 'planilla' && (
                          <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 3, display: 'flex', gap: 6, alignItems: 'center', background: 'rgba(0,0,0,0.55)', borderRadius: 8, padding: '4px 8px', fontSize: 11, color: 'var(--text-muted)' }}>
                            <span>Rueda: zoom · clic der.: mover</span>
                            <span title="Tamaño real. 100% = 1:1 físico. Las piezas se ven a su medida real, no importa cuántas sean." style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                              {(() => {
                                const pct = (visorView.k / PX_MM_100) * 100;   // k = px de pantalla por mm
                                return (pct >= 100 ? Math.round(pct) : pct.toFixed(pct < 10 ? 1 : 0)) + '%';
                              })()}
                            </span>
                            {/* Se dice cuántas piezas quedaron sin rótulo: si no, «faltan números»
                                parece un error del sistema en vez de falta de lugar en pantalla. */}
                            {rotulosOcultos > 0 && (
                              <span title="Hay piezas encimadas: sus rótulos no entran sin pisarse. Acercá el zoom (rueda) o tocá una pieza para ver el suyo."
                                style={{ color: 'var(--warning, #f5a524)', whiteSpace: 'nowrap' }}>
                                {rotulosOcultos} sin rótulo · acercá el zoom
                              </span>
                            )}
                            <button type="button" onClick={verTodoVisor} title="Ver todo el molde" style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 11, padding: '1px 7px' }}>Ver todo</button>
                            <button type="button" onClick={visor100} title="Tamaño real 1:1" style={{ background: 'none', border: '1px solid var(--border-light)', color: 'var(--text-secondary)', borderRadius: 5, cursor: 'pointer', fontSize: 11, padding: '1px 7px' }}>100%</button>
                          </div>
                        )}
                        {etqData && tabAjustesMolde === 'variables' && asignandoTipo && (() => {
                          const tActivo = (variantesEdit || []).find(t => t.clave === asignandoTipo);
                          const nPz = (tActivo?.valores || []).filter(v => v.pieza_idx != null).length;
                          return (
                            <div style={{ position: 'absolute', top: 8, left: '50%', transform: 'translateX(-50%)', zIndex: 4, display: 'flex', gap: 12, alignItems: 'center', background: 'rgba(0,20,24,0.92)', border: '1px solid var(--accent)', borderRadius: 10, padding: '8px 12px', fontSize: 12.5, color: '#fff', maxWidth: '92%', boxShadow: '0 6px 20px rgba(0,0,0,0.5)' }}>
                              <Icon name="edit" style={{ width: 14, height: 14, color: 'var(--accent)', flexShrink: 0 }} />
                              <span>Asignando a <b style={{ color: 'var(--accent)' }}>{tActivo?.label || 'este tipo'}</b> ({nPz}) — tocá una pieza, o <b>arrastrá un recuadro</b> desde un espacio vacío para elegir varias. Tocá una asignada para quitarla.</span>
                              <button type="button" onClick={() => { const c = asignandoTipo; setAsignandoTipo(null); if (grupoPzAbierto) { guardarGrupos(); } else if (!grupoAislado) setModalTipoClave(c); }} className="btn success" style={{ padding: '5px 14px', fontSize: 12, fontWeight: 700, flexShrink: 0 }}>Terminar de asignar ✓</button>
                            </div>
                          );
                        })()}
                        <div style={(etqData && tabAjustesMolde !== 'planilla')
                          ? { position: 'absolute', top: 0, left: 0, transform: `translate(${visorView.tx}px, ${visorView.ty}px)`, transformOrigin: '0 0', transition: 'none' }
                          : { width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        {tabAjustesMolde === 'planilla' ? (
                          probandoPlanilla ? (
                            <PlanillaTester
                              columnas={(plantillasPlanillas.find(t => t.id === selectedPlanillaTemplateId)?.columnas || []).filter(c => { const role = c.role || 'none'; if (['talle', 'nombre', 'numero', 'manga'].includes(role)) return mapeoColumnas[role] === c.id; return true; })}
                              reglas={reglasPlanilla}
                              variantes={tallesMolde || []}
                              onClose={() => setProbandoPlanilla(false)}
                            />
                          ) : (
                          /* Planilla en el área grande: vista de cómo carga ESTE molde */
                          <div style={{ width: '100%', alignSelf: 'stretch', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 14 }}>
                            {(() => {
                              const activeTemplate = plantillasPlanillas.find(t => t.id === selectedPlanillaTemplateId);
                              const cols = activeTemplate?.columnas || [];
                              const usada = (c) => {
                                const role = c.role || 'none';
                                if (['talle', 'nombre', 'numero', 'manga'].includes(role)) return mapeoColumnas[role] === c.id;
                                return true;
                              };
                              const ej = { talle: ['M', 'L', 'S'], nombre: ['GONZALEZ', 'PEREZ', 'ALVAREZ'], numero: ['10', '7', '9'], manga: ['Corta', 'Larga', 'Corta'], none: ['Texto', 'Texto', 'Texto'] };
                              const boxLook = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, padding: '6px 10px', borderRadius: 6, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-light)', fontSize: 13, color: 'var(--text-primary)', minHeight: 32, boxSizing: 'border-box' };
                              return (
                                <>
                                  <div style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>Así carga <b>este molde</b>. Las columnas en gris no se usan acá; a la derecha elegís cuál es la variante y qué columnas usar.</div>
                                  {cols.length === 0 ? (
                                    <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: '16px 0' }}>Esta planilla no tiene columnas. Agregalas en «Planillas».</div>
                                  ) : (
                                    <div style={{ overflowX: 'auto', border: '1px solid var(--border-light)', borderRadius: 10, background: '#0b0b0d' }}>
                                      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                                        <thead>
                                          <tr>
                                            {cols.map(c => {
                                              const role = c.role || 'none';
                                              const mapeable = ['talle', 'nombre', 'numero', 'manga'].includes(role);
                                              const on = usada(c);
                                              const esVariante = role === 'talle';
                                              const toggle = () => { if (!mapeable) return; setMapeoColumnas(prev => ({ ...prev, [role]: prev[role] === c.id ? '' : c.id })); };
                                              return (
                                                <th key={c.id} style={{ padding: 8, borderRight: '1px solid var(--border-light)', borderBottom: '1px solid var(--border-light)', minWidth: 150, verticalAlign: 'top' }}>
                                                  <div onClick={toggle} title={mapeable ? (on ? 'Tocá para no usar en este molde' : 'Tocá para usar en este molde') : ''}
                                                    style={{ cursor: mapeable ? 'pointer' : 'default', borderRadius: 11, padding: '11px 12px', transition: 'all .2s',
                                                      border: on ? '1px solid var(--accent)' : '1px dashed var(--border-light)',
                                                      background: on ? 'linear-gradient(180deg, rgba(0,216,245,0.12), rgba(0,216,245,0.02))' : 'transparent',
                                                      boxShadow: on ? '0 0 16px rgba(0,216,245,0.16)' : 'none',
                                                      opacity: on ? 1 : 0.55 }}>
                                                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', textAlign: 'center', marginBottom: mapeable ? 9 : 0 }}>{c.label}</div>
                                                    {mapeable ? (
                                                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7 }}>
                                                        <span style={{ width: 36, height: 19, borderRadius: 10, background: on ? 'var(--accent)' : 'rgba(255,255,255,0.13)', position: 'relative', transition: 'background .2s', flexShrink: 0, boxShadow: on ? '0 0 8px rgba(0,216,245,0.5)' : 'none' }}>
                                                          <span style={{ position: 'absolute', top: 2.5, left: on ? 19 : 2.5, width: 14, height: 14, borderRadius: '50%', background: '#fff', transition: 'left .2s' }} />
                                                        </span>
                                                        <span style={{ fontSize: 9.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.5, color: on ? 'var(--accent)' : 'var(--text-muted)', minWidth: 56 }}>
                                                          {esVariante ? (on ? '⚡ variante' : 'usar variante') : (on ? 'en uso' : 'sin usar')}
                                                        </span>
                                                      </div>
                                                    ) : (
                                                      <div style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5, textAlign: 'center', marginTop: 6 }}>dato</div>
                                                    )}
                                                  </div>
                                                </th>
                                              );
                                            })}
                                          </tr>
                                        </thead>
                                        <tbody>
                                          {[0, 1, 2].map(ri => (
                                            <tr key={ri}>
                                              {cols.map(c => {
                                                const role = c.role || 'none';
                                                const regla = reglasPlanilla.find(r => r.id === c.reglaId) || reglasPlanilla.find(r => r.comportamiento === role);
                                                const tipo = c.tipo || regla?.tipo || (role === 'manga' ? 'toggle' : role === 'talle' ? 'desplegable' : 'texto');
                                                const opts = ((c.opciones || regla?.opciones || '').split(',').map(s => s.trim()).filter(Boolean));
                                                const on = usada(c);
                                                const cell = role === 'talle' ? (
                                                  <div style={boxLook}><span>{ej.talle[ri] || 'M'}</span><span style={{ color: 'var(--cmyk-cyan)', fontSize: 10 }}>▾</span></div>
                                                ) : tipo === 'desplegable' ? (
                                                  <div style={boxLook}><span>{opts.length ? opts[ri % opts.length] : 'opción'}</span><span style={{ color: 'var(--cmyk-cyan)', fontSize: 10 }}>▾</span></div>
                                                ) : tipo === 'toggle' ? (
                                                  <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border-light)', minHeight: 32 }}>
                                                    {(opts.length >= 2 ? opts : (role === 'manga' ? ['Corta', 'Larga'] : ['Opción A', 'Opción B'])).map((o, oi) => {
                                                      const act = oi === (ri % Math.max(opts.length, 2));
                                                      return <div key={oi} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4px 6px', fontSize: 11, fontWeight: 600, background: act ? 'var(--accent)' : 'transparent', color: act ? 'var(--bg-primary)' : 'var(--text-muted)' }}>{o}</div>;
                                                    })}
                                                  </div>
                                                ) : (
                                                  <div style={{ ...boxLook, color: 'var(--text-secondary)', fontFamily: role === 'numero' ? 'monospace' : 'inherit' }}>{ej[role]?.[ri] || ej.none[ri]}</div>
                                                );
                                                return <td key={c.id} style={{ padding: '8px 12px', borderRight: '1px solid var(--border-light)', borderBottom: '1px solid rgba(255,255,255,0.03)', opacity: on ? 1 : 0.3 }}>{cell}</td>;
                                              })}
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  )}
                                </>
                              );
                            })()}
                          </div>
                          )
                        ) : etqData ? (
                          tabAjustesMolde === 'diseno' && mapeoData && mapeandoDiseno ? (() => { const vf = verVariante ? varianteFiltro(verVariante) : null; const _sz = svgRealSize(vf, canvasLayout.width, canvasLayout.height); return (
                            /* Canvas Mapeador de Arte overlay */
                            <svg
                              ref={visorSvgRef}
                              viewBox={vf && vf.vb ? vf.vb : `0 0 ${canvasLayout.width} ${canvasLayout.height}`}
                              width={_sz.w * visorView.k} height={_sz.h * visorView.k}
                              style={{ display: 'block', userSelect: 'none', overflow: 'visible' }}
                            >
                              {canvasLayout.layout.map((p) => {
                                if (vf && !vf.show.has(p.idx)) return null;   // VER VARIANTE: solo las piezas de la variante
                                const pzName = etqNombres[p.idx] || p.name || '';
                                if (!pzName) return null;

                                const isSelected = selectedPiezaMapeo === pzName;
                                const mappedMesaIdx = mapeoValores[pzName];
                                const mappedMesa = mapeoData.mesas?.find(m => m.mesa === mappedMesaIdx);

                                const vo = vf ? (vf.pos.get(p.idx) || { dx: 0, dy: 0 }) : null;   // Ver variante: juntar en grilla compacta
                                return (
                                  <g
                                    key={p.idx}
                                    transform={vo ? `translate(${vo.dx} ${vo.dy})` : undefined}
                                    style={{ cursor: 'pointer' }}
                                    onClick={() => setSelectedPiezaMapeo(pzName)}
                                  >
                                    <title>{pzName} {mappedMesaIdx ? `(Mesa ${mappedMesaIdx})` : '(sin diseño)'}</title>
                                    <defs>
                                      <clipPath id={`clip-map-piece-integrated-${p.idx}`}>
                                        <path d={p.path_svg} />
                                      </clipPath>
                                    </defs>
                                    
                                    {mappedMesa ? (() => {
                                      // Escala PROPORCIONAL: el arte se ajusta al ALTO de la pieza y el
                                      // ancho crece/se achica en la misma proporción (centrado, sin deformar).
                                      // Lo que sobra a los costados lo recorta el contorno (clipPath).
                                      const aspecto = mappedMesa.aspecto
                                        || (mappedMesa.w_cm && mappedMesa.h_cm ? mappedMesa.w_cm / mappedMesa.h_cm : (p.pw / p.ph));
                                      const imgH = p.ph;
                                      const imgW = aspecto * imgH;
                                      const imgX = p.px + (p.pw - imgW) / 2;
                                      return (
                                        <image
                                          href={`data:image/png;base64,${mappedMesa.thumb}`}
                                          x={imgX}
                                          y={p.py}
                                          width={imgW}
                                          height={imgH}
                                          preserveAspectRatio="none"
                                          clipPath={`url(#clip-map-piece-integrated-${p.idx})`}
                                          opacity={0.9}
                                        />
                                      );
                                    })() : null}
                                    
                                    <path
                                      d={p.path_svg}
                                      vectorEffect="non-scaling-stroke"
                                      style={{
                                        fill: isSelected
                                          ? 'rgba(0, 243, 255, 0.14)'
                                          : mappedMesaIdx
                                            ? 'rgba(16, 185, 129, 0.05)'
                                            : 'rgba(255, 255, 255, 0.01)',
                                        stroke: isSelected
                                          ? 'var(--accent)'
                                          : mappedMesaIdx
                                            ? 'var(--success)'
                                            : 'rgba(255, 255, 255, 0.25)',
                                        strokeWidth: isSelected ? 2.5 : 1.5,
                                        transition: 'fill 0.2s, stroke 0.2s, stroke-width 0.2s'
                                      }}
                                    />
                                    
                                    <g transform={`translate(${p.px + p.pw / 2}, ${p.py + p.ph / 2})`}>
                                      <rect 
                                        x={-(pzName.length * 4) - 8} 
                                        y={-10} 
                                        width={(pzName.length * 8) + 16} 
                                        height={20} 
                                        rx={4}
                                        fill="rgba(0,0,0,0.85)"
                                        stroke={isSelected ? 'var(--accent)' : mappedMesaIdx ? 'var(--success)' : 'rgba(255,255,255,0.15)'}
                                        strokeWidth={1}
                                      />
                                      <text 
                                        textAnchor="middle" 
                                        y={4} 
                                        style={{ fill: '#fff', fontSize: 10, fontWeight: 'bold', fontFamily: 'sans-serif' }}
                                      >
                                        {pzName}
                                      </text>
                                      {mappedMesaIdx && (
                                        <g transform="translate(0, 16)">
                                          <rect x={-24} y={-7} width={48} height={14} rx={3} fill="var(--success)" />
                                          <text textAnchor="middle" y={3} style={{ fill: '#fff', fontSize: 9, fontWeight: 'bold', fontFamily: 'sans-serif' }}>
                                            Mesa {mappedMesaIdx}
                                          </text>
                                        </g>
                                      )}
                                    </g>
                                  </g>
                                );
                              })}
                            </svg>
                          ); })() : tabAjustesMolde === 'diseno' ? (() => {
                            /* Canvas: medidas del diseño por pieza (viewBox que ENGLOBA todo para que nada se corte) */
                            const refMed = etqData.referencia_medida || 'alto';
                            const guiaEsAncho = refMed === 'ancho';
                            const vf = verVariante ? varianteFiltro(verVariante) : null;   // VER VARIANTE: reducir a sus piezas + re-encuadrar
                            const cajaDe = (p) => {
                              const nombrePz = etqNombres[p.idx] || '';
                              const m = (nombrePz && etqData.medidas_diseno) ? etqData.medidas_diseno[nombrePz] : null;
                              let ancho, alto;
                              if (configMedida === 'talle') { ancho = p.w_cm; alto = p.h_cm; }
                              else if (configMedida === 'rango') {
                                const mv = medidasVar?.piezas?.find(q => q.nombre === nombrePz);
                                const dimsR = (mv && rangoMedida.length) ? rangoMedida.map(t => mv.medidas[t]).filter(Boolean) : [];
                                if (dimsR.length && guiaEsAncho) { const r = Math.max(...dimsR.map(d => d.h_cm / d.w_cm)); ancho = p.w_cm; alto = Math.round(p.w_cm * r * 10) / 10; }
                                else if (dimsR.length) { const r = Math.max(...dimsR.map(d => d.w_cm / d.h_cm)); alto = p.h_cm; ancho = Math.round(p.h_cm * r * 10) / 10; }
                                else { ancho = m ? m.ancho_cm : p.w_cm; alto = m ? m.alto_cm : p.h_cm; }
                              } else { ancho = m ? m.ancho_cm : p.w_cm; alto = m ? m.alto_cm : p.h_cm; }
                              const pxcm = p.w_cm ? (p.pw / p.w_cm) : (p.h_cm ? (p.ph / p.h_cm) : 1);
                              const rectW = Math.max(6, ancho * pxcm), rectH = Math.max(6, alto * pxcm);
                              const cx = p.px + p.pw / 2, cy = p.py + p.ph / 2;
                              return { nombrePz, ancho, alto, rectW, rectH, cx, cy, rx: cx - rectW / 2, ry: cy - rectH / 2 };
                            };
                            // El recuadro y sus etiquetas pueden sobresalir de la pieza → ampliar el viewBox para que TODO sea visible.
                            let minX = 0, minY = 0, maxX = etqData.img_w, maxY = etqData.img_h;
                            canvasLayout.layout.forEach(p => {
                              const c = cajaDe(p);
                              minX = Math.min(minX, c.rx - 24, c.cx - 42);
                              minY = Math.min(minY, c.ry - 24, c.cy - 40);
                              maxX = Math.max(maxX, c.rx + c.rectW + 6, c.cx + 42);
                              maxY = Math.max(maxY, c.ry + c.rectH + 6, c.cy + 40);
                            });
                            const PAD = 14;
                            const _vbw = vf && vf.vb ? Number(vf.vb.split(' ')[2]) : (maxX - minX) + 2 * PAD;
                            const _vbh = vf && vf.vb ? Number(vf.vb.split(' ')[3]) : (maxY - minY) + 2 * PAD;
                            return (
                            <svg
                              ref={visorSvgRef}
                              viewBox={vf && vf.vb ? vf.vb : `${minX - PAD} ${minY - PAD} ${(maxX - minX) + 2 * PAD} ${(maxY - minY) + 2 * PAD}`}
                              width={_vbw * visorView.k} height={_vbh * visorView.k}
                              style={{ display: 'block', userSelect: 'none', overflow: 'visible' }}
                            >
                              {/* Sin fondo ráster (rectángulo gris): las siluetas vectoriales + cajas flotan en el espacio. */}
                              {canvasLayout.layout.map((p) => {
                                if (vf && !vf.show.has(p.idx)) return null;   // VER VARIANTE: solo las piezas de la variante
                                const { nombrePz, ancho, alto, rectW, rectH, cx, cy, rx, ry } = cajaDe(p);
                                const esTalle = configMedida === 'talle';
                                // resaltar la dimensión de referencia (como el default), salvo en 'talle por talle'
                                const hlAncho = !esTalle && guiaEsAncho, hlAlto = !esTalle && !guiaEsAncho;
                                const vo = vf ? (vf.pos.get(p.idx) || { dx: 0, dy: 0 }) : null;   // Ver variante: juntar en grilla compacta
                                return (
                                  <g key={p.idx} transform={vo ? `translate(${vo.dx} ${vo.dy})` : undefined}>
                                    {/* pieza del molde (contorno): resaltada en 'talle', tenue en el resto. Trazo de PANTALLA
                                        constante (non-scaling-stroke) para que se vea nítido a cualquier zoom. */}
                                    <path d={p.path_svg} vectorEffect="non-scaling-stroke" style={esTalle ? { fill: 'rgba(0,243,255,0.07)', stroke: 'var(--accent)', strokeWidth: 1.5 } : { fill: 'rgba(255,255,255,0.04)', stroke: 'rgba(255,255,255,0.25)', strokeWidth: 1.2 }} />
                                    {/* RECUADRO del diseño (SIEMPRE, también en 'talle': el recuadro va por fuera de la pieza) */}
                                    <rect x={rx} y={ry} width={rectW} height={rectH} vectorEffect="non-scaling-stroke" fill={esTalle ? 'none' : 'rgba(0,243,255,0.08)'} stroke="var(--accent)" strokeWidth={1.5} strokeDasharray="6 4" />
                                    {/* ancho (arriba del recuadro) */}
                                    <g transform={`translate(${cx}, ${ry - 11})`}>
                                      <rect x={-38} y={-9} width={76} height={18} rx={4} fill="rgba(0,0,0,0.9)" stroke="var(--accent)" strokeWidth={0.75} />
                                      <text textAnchor="middle" y={4} style={{ fill: hlAncho ? 'var(--accent)' : '#fff', fontSize: 11, fontWeight: hlAncho ? 800 : 600, fontFamily: 'sans-serif' }}>↔ {ancho} cm</text>
                                    </g>
                                    {/* alto (a la izquierda del recuadro, rotado) */}
                                    <g transform={`translate(${rx - 11}, ${cy}) rotate(-90)`}>
                                      <rect x={-34} y={-9} width={68} height={18} rx={4} fill="rgba(0,0,0,0.9)" stroke="var(--accent)" strokeWidth={0.75} />
                                      <text textAnchor="middle" y={4} style={{ fill: hlAlto ? 'var(--accent)' : '#fff', fontSize: 11, fontWeight: hlAlto ? 800 : 600, fontFamily: 'sans-serif' }}>↕ {alto} cm</text>
                                    </g>
                                    {/* nombre (centro) */}
                                    {nombrePz && (
                                      <text x={cx} y={cy + 4} textAnchor="middle" style={{ fill: '#fff', fontSize: 11, fontWeight: 700, fontFamily: 'sans-serif', paintOrder: 'stroke', stroke: 'rgba(0,0,0,0.7)', strokeWidth: 3 }}>{nombrePz}</text>
                                    )}
                                  </g>
                                );
                              })}
                            </svg>
                            );
                          })() : tabAjustesMolde === 'etiqueta' && etiquetaConfig ? (() => {
                            /* Visor de ETIQUETA: las etiquetas sobre cada pieza + click en el contorno para ubicar */
                            const ec = etiquetaConfig;
                            const cssC = (c) => `rgb(${Math.round(255 * (1 - (c?.[0] || 0)) * (1 - (c?.[3] || 0)))},${Math.round(255 * (1 - (c?.[1] || 0)) * (1 - (c?.[3] || 0)))},${Math.round(255 * (1 - (c?.[2] || 0)) * (1 - (c?.[3] || 0)))})`;
                            const posG = ec.posicion || { rx: 0.5, ry: 0.92 };
                            const posPorPieza = ec.posiciones || {};
                            const bc = bordeConfig || {};   // borde de corte REAL configurado del molde
                            const align = ec.align || 'centro';
                            const anchor = align === 'izquierda' ? 'start' : align === 'derecha' ? 'end' : 'middle';
                            const off = new Set((ec.piezas_off || []).map(nombreGenerico));   // piezas_off por NOMBRE GENÉRICO
                            const vf = verVariante ? varianteFiltro(verVariante) : null;   // VER VARIANTE: reducir a sus piezas + re-encuadrar
                            const nombrePc = (p) => etqNombres[p.idx] || p.name || ('Pieza ' + (p.idx + 1));
                            const muestraDe = (p) => [ec.mostrar?.talle && (etqData.talle_ref || '2XL'), ec.mostrar?.pieza && nombrePc(p), ec.mostrar?.numero && '#01'].filter(Boolean).join(ec.separador || '-') || '·';
                            // Apoyar el texto en el CONTORNO: punto más cercano del path + ángulo de la tangente.
                            const snapContorno = (d, cx, cy, pc) => {
                              try {
                                const el = document.createElementNS('http://www.w3.org/2000/svg', 'path'); el.setAttribute('d', d);
                                const len = el.getTotalLength(); if (!len) return null;
                                let best = null; const N = 160;
                                for (let i = 0; i <= N; i++) { const l = len * i / N; const pt = el.getPointAtLength(l); const dd = (pt.x - cx) ** 2 + (pt.y - cy) ** 2; if (!best || dd < best.dd) best = { dd, l, x: pt.x, y: pt.y }; }
                                const p2 = el.getPointAtLength(Math.min(len, best.l + 1.5));
                                // tangente del borde + normal hacia ADENTRO de la pieza, para que el
                                // texto se APOYE en el borde y entre hacia la pieza (no hacia afuera).
                                let tx = p2.x - best.x, ty = p2.y - best.y; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
                                let nx = -ty, ny = tx;
                                const ccx = pc.px + pc.pw / 2, ccy = pc.py + pc.ph / 2;
                                if ((ccx - best.x) * nx + (ccy - best.y) * ny < 0) { nx = -nx; ny = -ny; }   // normal hacia el centro
                                const ang = Math.atan2(nx, -ny) * 180 / Math.PI;   // "arriba" del texto = normal hacia adentro
                                // `t` = posición RELATIVA en el contorno (0..1). Se guarda esta (no el largo de
                                // arco absoluto) para que la etiqueta caiga en el MISMO lugar en todos los talles.
                                return { rx: Math.max(0, Math.min(1, (best.x - pc.px) / pc.pw)), ry: Math.max(0, Math.min(1, (best.y - pc.py) / pc.ph)), ang: Math.round(ang * 10) / 10, x: best.x, y: best.y, l: best.l, len, t: best.l / len };
                              } catch { return null; }
                            };
                            const piezaBajoMouse = (e) => {
                              const svg = e.currentTarget; let p;
                              try { const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; p = pt.matrixTransform(svg.getScreenCTM().inverse()); } catch { return null; }
                              // en "Ver variante" las piezas están TRASLADADAS a la grilla compacta → hit-test y
                              // snap en coords locales de la pieza (restando su traslado).
                              const hit = canvasLayout.layout.find(pc => {
                                if (vf && !vf.show.has(pc.idx)) return false;
                                const o = (vf && vf.pos.get(pc.idx)) || { dx: 0, dy: 0 };
                                return p.x >= pc.px + o.dx && p.x <= pc.px + o.dx + pc.pw && p.y >= pc.py + o.dy && p.y <= pc.py + o.dy + pc.ph;
                              });
                              if (!hit) return null;
                              const o = (vf && vf.pos.get(hit.idx)) || { dx: 0, dy: 0 };
                              return { hit, snap: snapContorno(hit.path_svg, p.x - o.dx, p.y - o.dy, hit) };
                            };
                            const onPick = (e) => {
                              const r = piezaBajoMouse(e); if (!r || !r.snap) return;
                              const _nm = nombrePc(r.hit);   // NOMBRE COMPLETO → SOLO esta pieza (por pieza, no todos los del nombre)
                              setEtqPiezaSel(_nm);   // queda seleccionada para editar la alineación de ESA pieza
                              setEtiquetaConfig(prev => { const _k = claveEtqPieza(_nm); const prevPc = (prev.posiciones || {})[_k] || {}; return { ...prev, posiciones: { ...(prev.posiciones || {}), [_k]: { rx: r.snap.rx, ry: r.snap.ry, ang: r.snap.ang, t: r.snap.t, ...(prevPc.align ? { align: prevPc.align } : {}) } } }; });   // clave = variante§nombre-completo (POR PIEZA POR VARIABLE); t/rx/ry = posición relativa (estable entre talles)
                            };
                            // ZONAS: tocar una pieza solo la SELECCIONA (no coloca etiqueta) → aparecen sus esquinas.
                            const onPickZona = (e) => {
                              const r = piezaBajoMouse(e); if (!r) return;
                              setEtqPiezaSel(nombreGenerico(nombrePc(r.hit))); setZonaSel(0);
                            };
                            const onHover = (e) => {
                              const r = piezaBajoMouse(e);
                              if (!r || !r.snap) { setEtqHover(h => h ? null : h); return; }
                              setEtqHover({ idx: r.hit.idx, x: r.snap.x, y: r.snap.y, ang: r.snap.ang, t: r.snap.t });
                            };
                            // ESQUINAS (cortes radicales) del contorno: arcos donde la dirección cambia de
                            // golpe. Cada esquina es un inicio/fin → el borde queda partido en SEGMENTOS.
                            const esquinasDe = (el, len) => {
                              const at = (l) => el.getPointAtLength(((l % len) + len) % len);
                              const N = Math.max(120, Math.min(700, Math.round(len)));
                              const step = len / N, h = Math.max(2.5, len / 160);
                              const dirAt = (l) => { const a = at(l - h), b = at(l + h); return Math.atan2(b.y - a.y, b.x - a.x); };
                              const turn = new Array(N);
                              for (let i = 0; i < N; i++) { const l = i * step; const d0 = dirAt(l - step * 1.5), d1 = dirAt(l + step * 1.5); turn[i] = Math.abs((((d1 - d0) + Math.PI) % (2 * Math.PI)) - Math.PI); }
                              const thr = 0.5, cor = []; let i = 0;   // ~28° de quiebre = esquina
                              while (i < N) { if (turn[i] > thr) { let j = i, best = i; while (j < N + 5 && turn[j % N] > thr * 0.5) { if (turn[j % N] > turn[best % N]) best = j; j++; } cor.push(((best % N) * step) % len); i = j; } else i++; }
                              // unir esquinas muy juntas (clusters) y el wrap 0/len
                              const out = []; cor.sort((a, b) => a - b);
                              for (const c of cor) { if (!out.length || Math.min(Math.abs(c - out[out.length - 1]), len - Math.abs(c - out[out.length - 1])) > len / 40) out.push(c); }
                              if (out.length > 1 && Math.min(Math.abs(out[0] - out[out.length - 1]), len - Math.abs(out[0] - out[out.length - 1])) < len / 40) out.pop();
                              return out;
                            };
                            // Segmento (entre dos esquinas) que contiene la posición relativa `t`. Devuelve el
                            // path d del segmento ENTERO orientado hacia adentro y su largo (fijo, NO depende
                            // del tamaño del texto) para alinear izq/centro/der respecto a esos dos puntos.
                            const segmentoEdge = _segmentoEdge;   // función compartida (misma que usa el visor del arte)
                            // ── ZONAS: esquinas del contorno como puntos (x,y,t) para dibujarlos y elegirlos ──
                            const esquinasXY = (pathD) => {
                              try {
                                const el = document.createElementNS('http://www.w3.org/2000/svg', 'path'); el.setAttribute('d', pathD);
                                const len = el.getTotalLength(); if (!len) return null;
                                const cor = esquinasDe(el, len);
                                return { len, el, corners: cor.map(l => { const q = el.getPointAtLength(l); return { t: ((l % len) + len) % len / len, x: q.x, y: q.y }; }) };
                              } catch { return null; }
                            };
                            // baseline de UNA zona entre dos t EXPLÍCITOS (t0→t1 hacia adelante, wrap), apoyada hacia adentro.
                            const zonaSegPath = (el, len, t0, t1, ccx, ccy, offIn) => {
                              try {
                                const at = (l) => el.getPointAtLength(((l % len) + len) % len);
                                let a = t0 * len, b = t1 * len; if (b <= a) b += len;   // tramo hacia adelante (wrap-aware)
                                const segLen = b - a; if (segLen <= 1) return null;
                                const M = Math.max(16, Math.min(90, Math.round(segLen / 3)));
                                const pts = []; for (let i = 0; i <= M; i++) pts.push(at(a + segLen * i / M));
                                const mid = at(a + segLen / 2), mid2 = at(a + segLen / 2 + 1.5);
                                const reverse = ((mid2.y - mid.y) * (ccx - mid.x) + (-(mid2.x - mid.x)) * (ccy - mid.y)) < 0;   // texto SIEMPRE derecho
                                let ord = reverse ? pts.slice().reverse() : pts;
                                if (offIn) {
                                  ord = ord.map((q, k) => {
                                    const pa = ord[Math.max(0, k - 1)], pb = ord[Math.min(ord.length - 1, k + 1)];
                                    let tx = pb.x - pa.x, ty = pb.y - pa.y; const tl = Math.hypot(tx, ty) || 1; tx /= tl; ty /= tl;
                                    let nx = -ty, ny = tx; if (nx * (ccx - q.x) + ny * (ccy - q.y) < 0) { nx = ty; ny = -tx; }
                                    return { x: q.x + nx * offIn, y: q.y + ny * offIn };
                                  });
                                }
                                return { d: 'M ' + ord.map(q => `${q.x.toFixed(1)} ${q.y.toFixed(1)}`).join(' L '), segLen };
                              } catch { return null; }
                            };
                            return (
                              <svg ref={visorSvgRef} viewBox={vf && vf.vb ? vf.vb : `0 0 ${canvasLayout.width} ${canvasLayout.height}`}
                                width={(vf && vf.vb ? Number(vf.vb.split(' ')[2]) : canvasLayout.width) * visorView.k} height={(vf && vf.vb ? Number(vf.vb.split(' ')[3]) : canvasLayout.height) * visorView.k}
                                onClick={zonasModo ? onPickZona : (ec.activo ? onPick : undefined)} onMouseMove={(ec.activo && !zonasModo) ? onHover : undefined} onMouseLeave={() => setEtqHover(null)}
                                style={{ display: 'block', userSelect: 'none', overflow: 'visible', cursor: zonasModo ? 'copy' : (ec.activo ? 'crosshair' : 'default') }}>
                                {/* sin imagen de fondo: las piezas van sobre el espacio del visor */}
                                {canvasLayout.layout.map((p) => {
                                  if (vf && !vf.show.has(p.idx)) return null;   // VER VARIANTE: solo las piezas de la variante
                                  if (varsConPiezas.length && !vf) return null; // molde con variables: NO procesar todas (lento) hasta elegir una
                                  const name = nombrePc(p);
                                  const gen = nombreGenerico(name);   // la posición/alineación es por NOMBRE GENÉRICO (todos los frentes juntos)
                                  const omit = off.has(gen);
                                  const pp = posPorPieza[claveEtqPieza(name)] || posPorPieza[claveNombreEtq(gen)] || posPorPieza[gen] || posPorPieza[name];   // POR PIEZA POR VARIABLE primero; fallback legacy: grupo§genérico, genérico global, nombre completo
                                  const rx = pp ? pp.rx : posG.rx, ry = pp ? pp.ry : posG.ry, ang = pp ? (pp.ang || 0) : 0;
                                  const pAlign = (pp && pp.align) || align;   // alineación POR PIEZA (default global)
                                  const pAnchor = pAlign === 'izquierda' ? 'start' : pAlign === 'derecha' ? 'end' : 'middle';
                                  // Tamaño REAL: size_mm convertido a px del lienzo según las medidas de ESA
                                  // pieza (px por mm) — IGUAL que el motor (`size_mm*MM`, sin piso). NO poner piso
                                  // en px: en un molde grande (17 m → escala chica) 3 mm da ~0.2px y un piso de
                                  // 1.5px lo hacía ENORME en piezas chicas (vivo 3.5cm = 68%). Sin piso queda REAL
                                  // (proporcional). Chico al ver todo el molde (correcto), se agranda con el zoom.
                                  const pxmm = p.h_cm ? p.ph / (p.h_cm * 10) : (p.w_cm ? p.pw / (p.w_cm * 10) : p.ph * 0.0033);
                                  const fs = Math.max(0.05, (ec.size_mm || 3) * pxmm);
                                  const tw = Math.max(fs, (muestraDe(p) || '').length * fs * 0.55);   // ancho aprox del texto
                                  const lx = p.px + rx * p.pw, ly = p.py + ry * p.ph;
                                  const vo = vf ? (vf.pos.get(p.idx) || { dx: 0, dy: 0 }) : null;   // traslado a la grilla compacta (Ver variante)
                                  const zonasPc = null;   // "Zonas de texto" ELIMINADO: se ignoran zonas guardadas
                                  const editZonas = false;
                                  return (
                                    <g key={p.idx} transform={vo ? `translate(${vo.dx} ${vo.dy})` : undefined}>
                                      <defs>
                                        <clipPath id={`etqclip-${p.idx}`}><path d={p.path_svg} /></clipPath>
                                        {/* recorte al EXTERIOR del contorno (even-odd) para dibujar el borde por fuera */}
                                        <clipPath id={`etqout-${p.idx}`}><path d={`M-99999 -99999H99999V99999H-99999Z ${p.path_svg}`} clipRule="evenodd" /></clipPath>
                                      </defs>
                                      {/* relleno de la pieza (resaltada si está seleccionada para editar su alineación) */}
                                      <path d={p.path_svg} style={{ fill: omit ? 'rgba(255,255,255,0.015)' : (name === etqPiezaSel ? 'rgba(0,243,255,0.13)' : 'rgba(0,243,255,0.04)'), stroke: 'none' }} />
                                      {/* borde de corte por FUERA del contorno (como el motor): trazo 2× recortado al
                                          exterior → solo la mitad externa se ve. Así el TEXTO (recortado al contorno,
                                          adentro) queda DETRÁS del borde y respeta su grosor; la base/los descendentes
                                          que cruzan el contorno quedan ocultos bajo el borde. */}
                                      <path d={p.path_svg} fill="none"
                                        clipPath={(bc.activo && !omit) ? `url(#etqout-${p.idx})` : undefined}
                                        stroke={omit ? 'rgba(255,255,255,0.18)' : (bc.activo ? cssC(bc.color || [0, 0, 0, 0.85]) : 'rgba(0,243,255,0.4)')}
                                        strokeWidth={omit ? Math.max(0.05, 0.85 * pxmm) : (bc.activo ? Math.max(0.05, (bc.ancho_mm || 2) * pxmm * 2) : Math.max(0.05, 1.0 * pxmm))} />
                                      {/* etiqueta: SIGUE el contorno (text-on-path, como Illustrator) cuando está
                                          colocada; recta si es la posición por defecto. Recortada al contorno. */}
                                      {ec.activo && !omit && (() => {
                                        const stl = { paintOrder: 'stroke', stroke: ec.borde_activo ? cssC(ec.borde_color || [0, 0, 0, 0.05]) : 'transparent', strokeWidth: ec.borde_activo ? Math.max(0.02, fs * 0.07 * (ec.borde_mm || 1)) : 0, fontFamily: 'sans-serif', pointerEvents: 'none' };
                                        const _offIn = 0.18 * pxmm;   // apoyar sobre el borde (descendentes quedan ocultos bajo el contorno)
                                        const ccx = p.px + p.pw / 2, ccy = p.py + p.ph / 2;
                                        // ── ZONAS por esquinas: reemplazan la etiqueta única cuando la pieza tiene ≥2 puntos.
                                        //    Cada zona = tramo entre dos puntos consecutivos (los t se ENGANCHAN a la
                                        //    esquina más cercana de ESTA pieza → estable aunque el talle esté gradado). ──
                                        if (zonasPc) {
                                          const geo = esquinasXY(p.path_svg);
                                          const pts = zonasPc.puntos || [], cont = zonasPc.cont || [];
                                          const snapT = (t) => { if (!geo || !geo.corners.length) return t; let best = t, bd = 1; for (const c of geo.corners) { const d = Math.min(Math.abs(c.t - t), 1 - Math.abs(c.t - t)); if (d < bd) { bd = d; best = c.t; } } return best; };
                                          return (
                                            <g clipPath={`url(#etqclip-${p.idx})`}>
                                              {geo && pts.map((t0, i) => {
                                                const t1 = pts[(i + 1) % pts.length];
                                                const seg = zonaSegPath(geo.el, geo.len, snapT(t0), snapT(t1), ccx, ccy, _offIn);
                                                if (!seg) return null;
                                                const c = cont[i] || {};
                                                const txt = [c.mostrar && c.mostrar.talle && (etqData.talle_ref || '2XL'), c.mostrar && c.mostrar.pieza && name, c.mostrar && c.mostrar.numero && '#01', c.texto].filter(Boolean).join(ec.separador || '-');
                                                if (!txt) return null;
                                                const zAlign = c.align || pAlign, zAnchor = zAlign === 'izquierda' ? 'start' : zAlign === 'derecha' ? 'end' : 'middle';
                                                const mg = Math.min(seg.segLen * 0.03, 4);
                                                const so = zAlign === 'izquierda' ? mg : zAlign === 'derecha' ? Math.max(mg, seg.segLen - mg) : seg.segLen / 2;
                                                return (
                                                  <g key={i}>
                                                    <path id={`etqz-${p.idx}-${i}`} d={seg.d} fill="none" stroke="none" />
                                                    <text fontSize={fs} fontWeight="800" textAnchor={zAnchor} fill={cssC(ec.color || [0.15, 0.15, 0.15, 0.3])} style={stl}>
                                                      <textPath href={`#etqz-${p.idx}-${i}`} startOffset={so}>{txt}</textPath>
                                                    </text>
                                                  </g>
                                                );
                                              })}
                                            </g>
                                          );
                                        }
                                        // ── etiqueta única (comportamiento original, sin zonas) ──
                                        const txt = muestraDe(p);
                                        // CACHE: segmentoEdge mide el contorno con cientos de getPointAtLength (carísimo).
                                        // La geometría solo depende de (path + posición + tamaño), estables entre re-renders
                                        // y hovers → se cachea y NO se re-mide en cada frame. Se invalida sola: la clave
                                        // incluye path_svg (cambia por talle) y t/rx/ry (cambian al editar la posición).
                                        let seg = null;
                                        if (pp && pp.t != null) {
                                          const _k = `${p.path_svg}|${pp.t}|${pp.rx}|${pp.ry}|${_offIn}|${ccx}|${ccy}`;
                                          const _m = segCacheRef.current;
                                          if (_m.has(_k)) seg = _m.get(_k);
                                          else { seg = segmentoEdge(p.path_svg, pp.t, ccx, ccy, _offIn, pp.rx, pp.ry); if (_m.size > 4000) _m.clear(); _m.set(_k, seg); }
                                        }
                                        // alineación DENTRO del segmento fijo (entre las dos esquinas). El margen
                                        // se basa en el SEGMENTO (no en la fuente) → el anclaje NO se mueve al
                                        // cambiar el tamaño del texto: queda siempre pegado al mismo borde/punto.
                                        const mg = seg ? Math.min(seg.segLen * 0.03, 4) : 0;
                                        const off = seg ? (pAlign === 'izquierda' ? mg : pAlign === 'derecha' ? Math.max(mg, seg.segLen - mg) : seg.segLen / 2) : 0;
                                        return (
                                          <g clipPath={`url(#etqclip-${p.idx})`}>
                                            {seg ? (
                                              <>
                                                <path id={`etqbl-${p.idx}`} d={seg.d} fill="none" stroke="none" />
                                                <text fontSize={fs} fontWeight="800" textAnchor={pAnchor} fill={cssC(ec.color || [0.15, 0.15, 0.15, 0.3])} style={stl}>
                                                  <textPath href={`#etqbl-${p.idx}`} startOffset={off}>{txt}</textPath>
                                                </text>
                                              </>
                                            ) : (
                                              <g transform={`rotate(${ang} ${lx} ${ly})`}>
                                                <text x={lx} y={ly} textAnchor={pAnchor} fontSize={fs} fontWeight="800" fill={cssC(ec.color || [0.15, 0.15, 0.15, 0.3])} style={stl}>{txt}</text>
                                              </g>
                                            )}
                                          </g>
                                        );
                                      })()}
                                      {/* ── OVERLAY edición de zonas: tramos + esquinas clicables de la pieza elegida ── */}
                                      {editZonas && (() => {
                                        const geo = esquinasXY(p.path_svg);
                                        if (!geo) return null;
                                        const pts = zonasPc ? (zonasPc.puntos || []) : ((zdef && zdef.puntos) || []);
                                        const dotR = Math.max(0.6, Math.min(p.pw, p.ph) * 0.05);
                                        const ccx = p.px + p.pw / 2, ccy = p.py + p.ph / 2;
                                        const near = (t) => pts.some(pt => Math.min(Math.abs(pt - t), 1 - Math.abs(pt - t)) < 0.02);
                                        return (
                                          <g>
                                            {pts.length >= 2 && pts.map((t0, i) => {
                                              const t1 = pts[(i + 1) % pts.length];
                                              const seg = zonaSegPath(geo.el, geo.len, t0, t1, ccx, ccy, 0);
                                              if (!seg) return null;
                                              const on = zonaSel === i;
                                              return <path key={'zs' + i} d={seg.d} fill="none" stroke={on ? '#22c55e' : (i % 2 ? '#f59e0b' : '#38bdf8')} strokeWidth={dotR * (on ? 0.75 : 0.5)} strokeLinecap="round" strokeLinejoin="round" opacity={on ? 0.95 : 0.6} style={{ pointerEvents: 'none' }} />;
                                            })}
                                            {geo.corners.map((cc, i) => {
                                              const sel = near(cc.t);
                                              return <circle key={'c' + i} cx={cc.x} cy={cc.y} r={dotR} fill={sel ? '#00f3ff' : '#0b0f14'} stroke="#00f3ff" strokeWidth={dotR * 0.3} style={{ cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); toggleZonaPunto(gen, cc.t); }} />;
                                            })}
                                          </g>
                                        );
                                      })()}
                                    </g>
                                  );
                                })}
                                {/* SEGMENTO COMPLETO bajo el mouse (de esquina a esquina) = lo que se selecciona */}
                                {etqHover && ec.activo && etqHover.t != null && (() => {
                                  const ph2 = canvasLayout.layout.find(q => q.idx === etqHover.idx);
                                  if (!ph2) return null;
                                  const pmm = ph2.h_cm ? ph2.ph / (ph2.h_cm * 10) : ph2.ph * 0.0033;
                                  const tr = segmentoEdge(ph2.path_svg, etqHover.t, ph2.px + ph2.pw / 2, ph2.py + ph2.ph / 2);
                                  if (!tr) return null;
                                  const bw = bc.activo ? Math.max(0.8, (bc.ancho_mm || 2) * pmm) : 1.3;
                                  const vo = vf ? (vf.pos.get(ph2.idx) || { dx: 0, dy: 0 }) : null;   // seguir el traslado de la pieza en "Ver variante"
                                  const linea = <path d={tr.d} fill="none" stroke="#22c55e" strokeWidth={Math.max(1, bw)} strokeLinecap="round" strokeLinejoin="round" opacity={0.95} />;
                                  return vo ? <g transform={`translate(${vo.dx} ${vo.dy})`}>{linea}</g> : linea;
                                })()}
                              </svg>
                            );
                          })() : (
                            /* Canvas Etiquetador base */
                            (() => {
                            const _vbBase = (() => { if (tabAjustesMolde === 'variables' && varStep === 'grupos' && grupoAislado && !asignandoTipo && nidoData) { const L = nidoLayoutVar(); if (L) return L.vb; } return canvasLayout.vb; })();
                            const _aBase = (_vbBase || '0 0 0 0').split(' ').map(Number);
                            return (
                            <svg
                              ref={visorSvgRef}
                              viewBox={_vbBase}
                              width={_aBase[2] * visorView.k} height={_aBase[3] * visorView.k}
                              style={{ display: 'block', userSelect: 'none', overflow: 'visible' }}
                              onMouseMove={handleDrag}
                              onMouseUp={endDrag}
                              onMouseLeave={endDrag}
                            >
                              {/* Sin fondo ráster completo (el rectángulo gris): el molde flota en el
                                  espacio infinito. Cada pieza trae su propia imagen recortada + contorno. */}
                              {(() => {
                                // Tamaño CONSTANTE en pantalla: `spx(n)` convierte n px de pantalla a
                                // unidades del viewBox al zoom actual. Así el número (pin) y el grosor de
                                // línea NO crecen ni se achican con el zoom → siempre legibles, nunca tapan.
                                const k = visorView.k || 1;
                                const sc = 1;   // escala REAL: svg dibujado a px=mm; constante en pantalla = n/k
                                const spx = (n) => n * sc / k;
                                // ── DETALLE DE VARIABLE: nido (todos los talles nesteados por pieza, arrastrables)
                                //    en una GRILLA COMPACTA propia de la variable (no la global). ──
                                const nidoOn = tabAjustesMolde === 'variables' && varStep === 'grupos' && grupoAislado && !asignandoTipo && nidoData;
                                const layoutN = nidoOn ? nidoLayoutVar() : null;
                                if (nidoOn && layoutN) {
                                  const vbWN = layoutN.vbW || 1100;
                                  const scN = 1;   // escala REAL (svg = px del nido); constante en pantalla = n/k
                                  const spn = (n) => n * scN / k;
                                  const talleSel = etqData?.talle_ref;
                                  const gAbierta = (variantesEdit || []).find(t => t.clave === grupoAislado);
                                  const enLink = !!vinculandoJuntas;    // eligiendo piezas para un vínculo, EN el mismo nido acomodado
                                  return layoutN.items.map(({ p: pieza, dx, dy, mcx, mcy, mhw, mhh }) => {
                                    const off = nidoOffsets[pieza.nombre] || { x: 0, y: 0 };
                                    const bnd = gAbierta && _juntaDeIdx(gAbierta.juntas, pieza.idx);   // vínculo "van juntas"
                                    const linkSel = enLink && juntasSel.has(pieza.idx);
                                    const label = bnd ? (bnd.nombre || pieza.nombre) : pieza.nombre;
                                    const toggleLink = (e) => { e.preventDefault(); e.stopPropagation(); setJuntasSel(prev => { const n = new Set(prev); if (n.has(pieza.idx)) n.delete(pieza.idx); else n.add(pieza.idx); return n; }); };
                                    return (
                                      <g key={'nido-' + pieza.nombre} transform={`translate(${dx + off.x}, ${dy + off.y})`} style={{ cursor: enLink ? 'pointer' : 'grab' }} onMouseDown={enLink ? toggleLink : (e) => nidoDragStart(pieza.nombre, e)}>
                                        <title>{label}{bnd ? ' · van juntas' : ''} — {enLink ? 'tocá para vincular/soltar' : 'todos los talles (arrastrá para acomodar)'}</title>
                                        {/* área de click invisible que cubre toda la pila (agarrar/tocar en cualquier lado) */}
                                        <rect x={mcx - mhw} y={mcy - mhh} width={2 * mhw} height={2 * mhh} fill="transparent" />
                                        {pieza.talles.map((t, ti) => {
                                          const sel = t.talle === talleSel;
                                          const col = linkSel ? '#f59e0b' : (sel ? '#00d8f5' : (bnd ? 'rgba(167,139,250,0.7)' : 'rgba(16,185,129,0.55)'));
                                          return <path key={ti} d={t.d} fill={ti === pieza.talles.length - 1 ? (linkSel ? 'rgba(245,158,11,0.12)' : (bnd ? 'rgba(167,139,250,0.08)' : 'rgba(16,185,129,0.06)')) : 'none'} stroke={col} strokeWidth={spn(linkSel || sel ? 2 : 1.1)} style={{ pointerEvents: 'none' }} />;
                                        })}
                                        <text x={pieza.cx} y={pieza.cy} fontSize={spn(12.5)} fill={linkSel ? '#fbbf24' : (bnd ? '#c4b5fd' : '#34d399')} textAnchor="middle" dominantBaseline="middle" style={{ pointerEvents: 'none', fontWeight: 700, paintOrder: 'stroke', stroke: 'rgba(2,6,12,0.85)', strokeWidth: spn(3) }}>{label}{linkSel ? ' ✓' : (bnd ? ' ⛓' : '')}</text>
                                      </g>
                                    );
                                  });
                                }
                                // AGRUPAR con todas las variantes juntas: el nombre y el "confirmado" de cada
                                // pieza salen de (talle, t_idx), no del idx del visor (que acá es un
                                // correlativo global). Se arma UNA vez por render, no por pieza.
                                const empTodasInfo = (empModo && empTodas) ? (() => {
                                  const nom = {}, fijo = {};
                                  const asigT = empData?.asignacion || {}, manT = empData?.manual || {};
                                  Object.keys(asigT).forEach(t => {
                                    Object.entries(asigT[t] || {}).forEach(([n, i]) => {
                                      nom[`${t}|${i}`] = n;
                                      if ((manT[t] || {})[n] != null || t === empData?.guia) fijo[`${t}|${i}`] = true;
                                    });
                                  });
                                  return { nom, fijo };
                                })() : null;
                                // Piezas del grupo que se está asignando (multigrupo: una pieza puede estar en varios grupos).
                                const activoSet = asignandoTipo ? new Set((((variantesEdit || []).find(t => t.clave === asignandoTipo) || {}).valores || []).map(v => v.pieza_idx)) : null;
                                // Conjunto "van juntas" activo: sus piezas se resaltan.
                                const conjActivoSet = asignandoConjunto ? new Set((((conjuntosEdit || []).find(c => c.id === asignandoConjunto) || {}).piezas) || []) : null;
                                // Grupo de piezas activo (eligiendo piezas): las suyas resaltadas.
                                const grupoPzActivoSet = asignandoGrupoPz ? new Set((((gruposPz || []).find(g => g.id === asignandoGrupoPz) || {}).piezas) || []) : null;
                                // Detalle de grupo: mostrar SOLO sus piezas (salvo que estés cargando nuevas → se ven todas).
                                // Aislar por NOMBRE (estable entre talles): el grupo se define en el talle guía y sus
                                // piezas se mapean al talle actual por el nombre (nombres_existentes viene por talle del registro).
                                const aislarClave = grupoAislado;
                                const aisladoSet = (() => {
                                  // Mostrando una combinación generada: sólo sus piezas (una por nombre + comodines).
                                  if (comboVisor && comboVisor.length && tabAjustesMolde === 'variables') return new Set(comboVisor);
                                  // GRUPO de piezas abierto: solo las suyas (también al elegir piezas de una
                                  // VARIABLE — se elige únicamente entre las piezas del grupo).
                                  if (tabAjustesMolde === 'variables' && grupoPzAbierto && !asignandoGrupoPz && (asignandoTipo || (!grupoAislado && !aislarClave))) {
                                    const gp = (gruposPz || []).find(x => x.id === grupoPzAbierto);
                                    if (gp && (gp.piezas || []).length) return new Set(gp.piezas);
                                    return null;
                                  }
                                  if (!(aislarClave && !asignandoTipo && tabAjustesMolde === 'variables')) return null;
                                  const g = (variantesEdit || []).find(t => t.clave === aislarClave);
                                  if (!g) return null;
                                  const ne = etqData?.nombres_existentes;
                                  const usarNombres = ne && Object.keys(ne).length > 0;
                                  const grupoNombres = new Set((g.valores || []).map(v => (v.label || etqNombres[v.pieza_idx] || '').trim()).filter(Boolean));
                                  const grupoIdxs = new Set((g.valores || []).map(v => v.pieza_idx));
                                  const nombreDe = (idx) => (usarNombres ? (ne[idx] != null ? ne[idx] : (ne[String(idx)] || '')) : (etqNombres[idx] || '')).trim();
                                  return new Set(canvasLayout.layout.filter(p => {
                                    const nm = nombreDe(p.idx);
                                    if (nm && grupoNombres.has(nm)) return true;   // por nombre (sirve en todos los talles)
                                    if (!nm && grupoIdxs.has(p.idx)) return true;  // sin nombre → cae al idx (solo válido en la guía)
                                    return false;
                                  }).map(p => p.idx));
                                })();
                                // TODAS LAS VARIANTES JUNTAS: el nombre de la variante va UNA vez por
                                // bloque (arriba a la izquierda de sus piezas), no en cada pieza. Con 6
                                // variantes × 6 piezas encimadas, repetirlo 36 veces daba «2XL 2XL».
                                // Lo mismo mientras se ASIGNAN las variantes por piezas: el bloque se
                                // arma con lo que el usuario lleva asignado, así ve de un vistazo qué
                                // quedó en cada variante aunque los nombres por pieza no entren.
                                const bloquesVarPz = (() => {
                                  if (!varPzModo) return [];
                                  const cajas = new Map();
                                  canvasLayout.layout.forEach(p => {
                                    const v = (varPzAsig[p.idx] || '').trim();
                                    if (!v) return;
                                    const c = cajas.get(v) || { talle: v, x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity, n: 0 };
                                    c.x0 = Math.min(c.x0, p.px); c.y0 = Math.min(c.y0, p.py);
                                    c.x1 = Math.max(c.x1, p.px + p.pw); c.y1 = Math.max(c.y1, p.py + p.ph);
                                    c.n++; cajas.set(v, c);
                                  });
                                  return [...cajas.values()];
                                })();
                                const colChip = varPzModo ? '#34d399' : '#93c5fd';
                                const chipsVariante = (empTodasInfo ? (canvasLayout.clusters || []) : bloquesVarPz).map(c => (
                                  <g key={'clv_' + c.talle} pointerEvents="none">
                                    <text x={c.x0 + spx(7)} y={c.y0 + spx(7)} fill={colChip} fontSize={spx(17)} fontWeight={900}
                                      textAnchor="start" dominantBaseline="hanging"
                                      style={{ paintOrder: 'stroke', stroke: 'rgba(2,6,12,0.9)', strokeWidth: spx(4.5) }}>
                                      {c.talle}
                                    </text>
                                    <text x={c.x0 + spx(7)} y={c.y0 + spx(27)} fill={colChip} opacity={0.65} fontSize={spx(10.5)} fontWeight={700}
                                      textAnchor="start" dominantBaseline="hanging"
                                      style={{ paintOrder: 'stroke', stroke: 'rgba(2,6,12,0.9)', strokeWidth: spx(3.5) }}>
                                      {c.n} pza{c.n === 1 ? '' : 's'}
                                    </text>
                                  </g>
                                ));
                                return (<>{chipsVariante}{canvasLayout.layout.map((p) => {
                                if (aisladoSet && !aisladoSet.has(p.idx)) return null;
                                const esSeleccionado = etqSeleccion === p.idx;
                                // En la vista junta el nombre NO puede salir de `etqNombres` (es el de UN
                                // talle): cada pieza trae el suyo, el de su propia variante.
                                const nombrePz = empTodasInfo ? (empTodasInfo.nom[`${p.talle}|${p.t_idx}`] || '') : (etqNombres[p.idx] || '');
                                // Coloreo por estado según el paso de Variables.
                                const enVar = tabAjustesMolde === 'variables';
                                const enNombrar = enVar && varStep === 'nombrar';
                                const claveP = (enVar && !enNombrar) ? piezaTipoMap[p.idx] : null;
                                const enActivo = enVar && !!activoSet && activoSet.has(p.idx);
                                const asignada = enVar && claveP != null;
                                const selN = enNombrar && selNombrar.has(p.idx);
                                const enJuntaSel = enVar && !!vinculandoJuntas && juntasSel.has(p.idx);
                                const destacada = esSeleccionado || enActivo || selN || enJuntaSel;
                                // El BORDE es la línea REAL del archivo (contorno), fina y neutra.
                                // El RELLENO verde (o cyan) marca el estado. Nada dibujado de más.
                                let fillCol, badgeFill, textFill;
                                if (enNombrar && editandoNombre) {
                                  // Editando un nombre: las piezas de ESE nombre resaltadas (cyan), el resto neutro.
                                  if (nombrePz && nombreGenerico(nombrePz) === editandoNombre) { fillCol = 'rgba(0,243,255,0.24)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                  else { fillCol = 'rgba(255,255,255,0.03)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                } else if (enNombrar) {
                                  if (selN) { fillCol = 'rgba(0,243,255,0.22)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                  else if (nombrePz) { fillCol = 'rgba(16,185,129,0.26)'; badgeFill = '#10b981'; textFill = '#18181b'; }
                                  else { fillCol = 'rgba(16,185,129,0.10)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                } else if (enVar) {
                                  if (vinculandoJuntas) { // armando "van juntas": elegidas en ÁMBAR, ya vinculadas en violeta, resto neutro
                                    const yaVinc = (() => { const g = (variantesEdit || []).find(t => t.clave === vinculandoJuntas); return g && _juntaDeIdx(g.juntas, p.idx); })();
                                    if (juntasSel.has(p.idx)) { fillCol = 'rgba(245,158,11,0.36)'; badgeFill = '#f59e0b'; textFill = '#18181b'; }
                                    else if (yaVinc) { fillCol = 'rgba(167,139,250,0.24)'; badgeFill = '#a78bfa'; textFill = '#18181b'; }
                                    else { fillCol = 'rgba(255,255,255,0.03)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                  }
                                  else if (conjActivoSet) { // eligiendo piezas de un conjunto: las suyas resaltadas, el resto neutro
                                    if (conjActivoSet.has(p.idx)) { fillCol = 'rgba(167,139,250,0.34)'; badgeFill = '#a78bfa'; textFill = '#18181b'; }
                                    else { fillCol = 'rgba(255,255,255,0.03)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                  }
                                  else if (grupoPzActivoSet) { // eligiendo piezas de un GRUPO: las suyas en cyan, el resto neutro
                                    if (grupoPzActivoSet.has(p.idx)) { fillCol = 'rgba(0,243,255,0.22)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                    else { fillCol = 'rgba(255,255,255,0.03)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                  }
                                  else if (comboVisor && comboVisor.length) { fillCol = 'rgba(16,185,129,0.30)'; badgeFill = '#10b981'; textFill = '#18181b'; } // pieza de la combinación mostrada
                                  else if (enActivo) { fillCol = 'rgba(0,243,255,0.22)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                  else if (asignandoTipo) { fillCol = 'rgba(255,255,255,0.03)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; } // asignando un grupo: las de OTROS grupos van neutras (no marcadas)
                                  else if (asignada) { fillCol = 'rgba(16,185,129,0.26)'; badgeFill = '#10b981'; textFill = '#18181b'; }
                                  else { fillCol = 'rgba(16,185,129,0.12)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                } else {
                                  fillCol = esSeleccionado ? 'rgba(0,243,255,0.18)' : nombrePz ? 'rgba(16,185,129,0.26)' : 'rgba(16,185,129,0.12)';
                                  badgeFill = esSeleccionado ? '#00d8f5' : nombrePz ? '#10b981' : '#3f3f46';
                                  textFill = esSeleccionado || nombrePz ? '#18181b' : '#ffffff';
                                }
                                // Resaltado por nombre genérico (hover en la lista agrupada de piezas).
                                const resaltada = resaltarNombre != null && ((nombrePz && nombreGenerico(nombrePz) === resaltarNombre) || (resaltarNombre === '(sin asignar)' && !nombrePz));
                                if (resaltada) { fillCol = 'rgba(0,243,255,0.34)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                // Asignando variantes POR PIEZAS: este coloreo MANDA sobre el resto (el visor
                                // está dedicado a eso). Cyan = seleccionada, verde = ya tiene variante.
                                const varPzNom = varPzModo ? (varPzAsig[p.idx] || '') : '';
                                const varPzSel = varPzModo && selNombrar.has(p.idx);
                                if (varPzModo) {
                                  if (varPzSel) { fillCol = 'rgba(0,243,255,0.24)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                  else if (varPzNom) { fillCol = 'rgba(16,185,129,0.28)'; badgeFill = '#10b981'; textFill = '#18181b'; }
                                  else { fillCol = 'rgba(255,255,255,0.04)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                }
                                // EMPAREJAR TALLES: este coloreo MANDA (el visor esta dedicado a eso).
                                // cyan = seleccionada para reacomodar · violeta = corregida a mano ·
                                // verde = emparejada sola · ambar = sin emparejar (ninguna pieza le toco).
                                let empSel = false;
                                let empEsFijo = false;
                                if (empTodasInfo) {
                                  // TODAS LAS VARIANTES JUNTAS: cyan = seleccionada ahora · color del grupo =
                                  // ya agrupada (más opaca si el usuario la confirmó) · gris = todavía suelta.
                                  empSel = selNombrar.has(p.idx);
                                  empEsFijo = !!empTodasInfo.fijo[`${p.talle}|${p.t_idx}`];
                                  if (empSel) { fillCol = 'rgba(0,243,255,0.30)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                  else if (nombrePz) { const c = colorGrupo(nombrePz); fillCol = colorGrupoA(nombrePz, empEsFijo ? 0.42 : 0.20); badgeFill = c; textFill = '#18181b'; }
                                  else { fillCol = 'rgba(255,255,255,0.04)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                }
                                else if (empModo && empTalle) {
                                  const _asig = (empData?.asignacion || {})[empTalle] || {};
                                  const _fij = (empData?.manual || {})[empTalle] || {};
                                  const _nomAqui = Object.keys(_asig).find(n => _asig[n] === p.idx);
                                  empSel = selNombrar.has(p.idx);
                                  empEsFijo = !!(_nomAqui && _fij[_nomAqui] != null);
                                  // AGRUPAR: cada grupo con SU color (el mismo en todos los talles), para que
                                  // se vea de un vistazo que «esta de acá» y «esta de allá» son la misma pieza.
                                  if (empVista === 'simple') {
                                    if (empSel) { fillCol = 'rgba(0,243,255,0.30)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                    else if (_nomAqui) { const c = colorGrupo(_nomAqui); fillCol = c.replace('hsl(', 'hsla(').replace(')', `, ${empEsFijo ? 0.42 : 0.20})`); badgeFill = c; textFill = '#18181b'; }
                                    else { fillCol = 'rgba(255,255,255,0.04)'; badgeFill = '#3f3f46'; textFill = '#ffffff'; }
                                    if (empFijar) { badgeFill = '#f5a524'; textFill = '#18181b'; }
                                  }
                                  else if (empSel) { fillCol = 'rgba(0,243,255,0.26)'; badgeFill = '#00d8f5'; textFill = '#18181b'; }
                                  else if (_nomAqui && _fij[_nomAqui] != null) { fillCol = 'rgba(167,139,250,0.30)'; badgeFill = '#a78bfa'; textFill = '#18181b'; }
                                  else if (_nomAqui) { fillCol = 'rgba(16,185,129,0.26)'; badgeFill = '#10b981'; textFill = '#18181b'; }
                                  else { fillCol = 'rgba(245,165,36,0.18)'; badgeFill = '#f5a524'; textFill = '#18181b'; }
                                  if (empFijar) { badgeFill = '#f5a524'; textFill = '#18181b'; }
                                }
                                const strokeCol = (destacada || resaltada || varPzSel || empSel) ? 'rgba(255,255,255,0.95)' : 'rgba(255,255,255,0.5)';

                                const offset = pzOffsets[p.idx] || { x: 0, y: 0 };
                                const tx = p.tx + offset.x;
                                const ty = p.ty + offset.y;

                                return (
                                  <g
                                    key={p.idx}
                                    data-piece={p.idx}
                                    transform={`translate(${tx}, ${ty})`}
                                    style={{ cursor: (modoAcomodar || (empModo && empVista !== 'simple' && !empFijar)) ? (dragInfo.current.idx === p.idx ? 'grabbing' : 'grab') : (empModo && empFijar ? 'crosshair' : 'pointer') }}
                                    onMouseDown={(e) => startDrag(e, p.idx)}
                                  >
                                    <title>{empTodasInfo
                                      ? `${p.talle} · pieza #${p.t_idx + 1}${nombrePz ? ` — ${nombrePz}` : ' (sin agrupar)'}`
                                      : (nombrePz ? `${nombrePz} (Pieza #${p.idx + 1})` : `Pieza #${p.idx + 1} (sin asignar)`)}</title>

                                    <path
                                      d={p.path_svg}
                                      style={{ fill: fillCol, stroke: strokeCol, strokeWidth: spx((destacada || resaltada) ? 2 : 1.3), transition: 'fill 0.2s' }}
                                    />

                                    {/* RÓTULO: sólo si hay lugar en PANTALLA para que se lea (o si la
                                        pieza está elegida/resaltada, que siempre tiene que verse).
                                        Con las piezas encimadas —el molde sin separar, o las 6
                                        variantes juntas— los centros caen a milímetros y antes se
                                        dibujaban igual: dos círculos y dos nombres pisados. */}
                                    {(() => {
                                      const room = (canvasLayout.sep?.get(p.idx) ?? Infinity) * k;
                                      const forzado = destacada || resaltada || varPzSel || empSel;
                                      if (room < LBL_MIN_PX && !forzado) {
                                        // Apretada: un punto del color de su estado. La pieza sigue
                                        // clicable y el nombre está en el tooltip; el rótulo vuelve
                                        // acercando el zoom o tocándola.
                                        return (
                                          <circle cx={p.px + p.pw / 2} cy={p.py + p.ph / 2} r={spx(3.2)}
                                            fill={badgeFill} stroke="rgba(0,0,0,0.55)" strokeWidth={spx(1)} pointerEvents="none" />
                                        );
                                      }
                                      const holgado = room >= TXT_MIN_PX || forzado;   // ¿entra también el texto de arriba/abajo?
                                      return (
                                    <g transform={`translate(${p.px + p.pw / 2}, ${p.py + p.ph / 2})`}>
                                      <circle r={spx(11)} fill="rgba(0,0,0,0.5)" transform={`translate(${spx(1)}, ${spx(1.5)})`} />
                                      <circle r={spx(11)} fill={badgeFill} stroke="#ffffff" strokeWidth={spx(1.5)} style={{ transition: 'fill 0.2s' }} />
                                      <text fill={textFill} fontSize={spx(11.5)} fontWeight={900} textAnchor="middle" dominantBaseline="central" pointerEvents="none">
                                        {(empTodasInfo ? p.t_idx : p.idx) + 1}
                                      </text>
                                      {/* De qué variante es esta pieza. En la vista junta el nombre de la
                                          variante ya va UNA vez por bloque: acá sólo se repite si sobra
                                          lugar (zoom cerca) o si la pieza está elegida. */}
                                      {empTodasInfo && holgado && (
                                        <text y={spx(-20)} fill="#93c5fd" fontSize={spx(12)} fontWeight={800} textAnchor="middle" dominantBaseline="middle" pointerEvents="none"
                                          style={{ paintOrder: 'stroke', stroke: 'rgba(2,6,12,0.85)', strokeWidth: spx(3) }}>
                                          {p.talle}
                                        </text>
                                      )}
                                      {/* el nombre de la variante va DEBAJO del número: puede ser
                                          "S" o "Talle único", no entra dentro del círculo */}
                                      {varPzNom && holgado && (
                                        <text y={spx(24)} fill="#34d399" fontSize={spx(12.5)} fontWeight={800} textAnchor="middle" dominantBaseline="middle" pointerEvents="none"
                                          style={{ paintOrder: 'stroke', stroke: 'rgba(2,6,12,0.85)', strokeWidth: spx(3) }}>
                                          {varPzNom}
                                        </text>
                                      )}
                                      {/* Emparejando: que pieza del talle GUIA le toco a esta, escrito encima */}
                                      {empModo && nombrePz && holgado && (
                                        <text y={spx(24)} fill={empVista === 'simple' ? colorGrupo(nombrePz) : '#e4e4e7'} fontSize={spx(12)} fontWeight={800} textAnchor="middle" dominantBaseline="middle" pointerEvents="none"
                                          style={{ paintOrder: 'stroke', stroke: 'rgba(2,6,12,0.85)', strokeWidth: spx(3) }}>
                                          {nombrePz}{empVista === 'simple' && empEsFijo ? ' ✓' : ''}
                                        </text>
                                      )}
                                    </g>
                                      );
                                    })()}
                                  </g>
                                );
                                })}</>);
                              })()}
                            </svg>
                            );
                            })()
                          )
                        ) : activoProdDetalle?.plantilla ? (
                          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Cargando el molde…</div>
                        ) : (
                          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                            <Icon name="upload" style={{ width: 32, height: 32, strokeWidth: 1.5, opacity: 0.5, marginBottom: 12 }} />
                            <div>Sube la plantilla vectorial del molde (.ai)</div>
                            <div style={{ fontSize: 11, marginTop: 4 }}>Al hacerlo se procesará y mostrará aquí de forma interactiva.</div>
                          </div>
                        )}
                        </div>
                      </div>
                    </div>
                  </div>
                  </>
                )}
              </div>
            )}

            {/* 3. Columnas de Planilla Subview */}
            {adminSubView === 'columnas' && (
              planillaEditando === null ? (
                <div className="panel animate-fade">
                  <div style={{ marginBottom: 20 }}>
                    <button className="btn ghost" onClick={() => setAdminSubView('dashboard')} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
                      ⬅ Volver al Panel de Configuración
                    </button>
                  </div>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                    <div>
                      <h2>Plantillas de Planilla</h2>
                      <p>Define la estructura de columnas Excel y asócialas a tus productos.</p>
                    </div>
                    <button className="btn primary" onClick={handleCreatePlanilla} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Icon name="plus" style={{ width: 14, height: 14 }} /> Nueva Planilla
                    </button>
                  </div>

                  {/* Repository grid */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 240px))',
                    gap: '16px',
                    marginTop: '20px'
                  }}>
                    {plantillasPlanillas.map((plan) => {
                      const productosAsociados = productosCat.productos.filter(p => p.planilla_template_id === plan.id);
                      const esAsociadaAlActivo = activoProdDetalle?.planilla_template_id === plan.id;
                      
                      return (
                        <div 
                          key={plan.id} 
                          className="card animate-fade" 
                          onClick={() => handleEditPlanilla(plan)}
                          style={{ 
                            padding: 16, 
                            display: 'flex', 
                            flexDirection: 'column', 
                            justifyContent: 'space-between', 
                            minHeight: 160,
                            maxWidth: 240,
                            cursor: 'pointer',
                            border: esAsociadaAlActivo ? '1px solid var(--accent)' : '1px solid var(--border-light)',
                            boxShadow: esAsociadaAlActivo ? '0 0 12px rgba(0, 243, 255, 0.15)' : 'none'
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                              <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>{plan.nombre}</h3>
                              {esAsociadaAlActivo && (
                                <span className="badge success" style={{ fontSize: 9, textTransform: 'uppercase', whiteSpace: 'nowrap' }}>Activa</span>
                              )}
                            </div>
                            
                            {/* Preview columns */}
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, margin: '12px 0 10px 0' }}>
                              {plan.columnas?.map((c, i) => (
                                <span key={i} className="badge neutral" style={{ fontSize: 10, textTransform: 'none', backgroundColor: 'rgba(255,255,255,0.04)', borderColor: 'var(--border-light)', whiteSpace: 'nowrap' }}>
                                  {c.label} <span style={{ opacity: 0.5, fontStyle: 'italic', fontSize: 8 }}>({c.role})</span>
                                </span>
                              ))}
                            </div>

                            {/* Associated products list */}
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
                              {productosAsociados.length > 0 ? (
                                <span>Vinculada a: <b>{productosAsociados.map(p => p.nombre).join(', ')}</b></span>
                              ) : (
                                <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>Sin productos asociados</span>
                              )}
                            </div>
                          </div>

                          <div style={{ display: 'flex', gap: 6, marginTop: 14, borderTop: '1px solid var(--border-light)', paddingTop: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                            {!esAsociadaAlActivo && activoProdDetalle ? (
                              <button 
                                className="btn ghost" 
                                style={{ padding: '5px 10px', fontSize: '11.5px', whiteSpace: 'nowrap', color: 'var(--cmyk-cyan)', borderColor: 'var(--cmyk-cyan)' }} 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAssignPlanillaToProduct(activoProdDetalle.id, plan.id);
                                }}
                              >
                                Usar para {activoProdDetalle.nombre}
                              </button>
                            ) : (
                              <span style={{ fontSize: 11, color: 'var(--success)', fontWeight: 600 }}>Planilla Activa ✓</span>
                            )}

                            {plan.id !== 'plan_default' && (
                              <button 
                                className="btn danger-ghost" 
                                style={{ padding: '5px 8px', fontSize: '11.5px', whiteSpace: 'nowrap', marginLeft: 'auto' }} 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeletePlanilla(plan.id);
                                }}
                              >
                                <Icon name="trash" style={{ width: 11, height: 11 }} />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="panel animate-fade">
                  {/* Editor Header Bar */}
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    borderBottom: '1px solid var(--border-light)', 
                    paddingBottom: 16, 
                    marginBottom: 20,
                    flexWrap: 'wrap',
                    gap: 16
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <button className="btn ghost" onClick={() => setPlanillaEditando(null)} style={{ padding: '6px 12px', fontSize: 12 }}>
                        ⬅ Volver
                      </button>
                      {/* Editable Spreadsheet Name */}
                      <input
                        type="text"
                        value={nombrePlanillaEditando}
                        onChange={(e) => setNombrePlanillaEditando(e.target.value)}
                        placeholder="Nombre de la planilla..."
                        style={{
                          fontSize: 18,
                          fontWeight: 800,
                          background: 'transparent',
                          border: 'none',
                          borderBottom: '1px dashed var(--border-light)',
                          color: '#fff',
                          outline: 'none',
                          width: 250,
                          padding: '2px 4px'
                        }}
                      />
                    </div>
                    
                    <div style={{ display: 'flex', gap: 10 }}>
                      {activoProdDetalle && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginRight: 8 }}>
                          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Asociar a {activoProdDetalle.nombre}:</span>
                          <input 
                            type="checkbox"
                            checked={activoProdDetalle.planilla_template_id === planillaEditando.id}
                            onChange={(e) => {
                              if (planillaEditando.id) {
                                handleAssignPlanillaToProduct(activoProdDetalle.id, e.target.checked ? planillaEditando.id : 'plan_default');
                              } else {
                                showError("Primero debes guardar la planilla para poder asociarla");
                              }
                            }}
                            style={{ width: 16, height: 16, cursor: 'pointer' }}
                          />
                        </div>
                      )}
                      <button className="btn ghost" onClick={() => setProbandoPlanilla(true)} style={{ padding: '8px 16px', fontSize: 13, height: 36, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--cmyk-cyan)', borderColor: 'var(--cmyk-cyan)' }}>
                        <Icon name="eye" style={{ width: 14, height: 14 }} /> Visualizar
                      </button>
                      <button className="btn success" onClick={handleSavePlanilla} style={{ backgroundColor: 'var(--success)', color: 'white', padding: '8px 16px', fontSize: 13, height: 36 }}>
                        Guardar Planilla
                      </button>
                    </div>
                  </div>

                  {probandoPlanilla ? (
                  <div className="card" style={{ padding: 18, minHeight: 460, display: 'flex' }}>
                    <PlanillaTester columnas={columnasPlanillaEditando} reglas={reglasPlanilla} onClose={() => setProbandoPlanilla(false)} />
                  </div>
                  ) : (
                  <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>

                  {/* Barra de herramientas de la columna (izquierda) */}
                  {colSeleccionada !== null && columnasPlanillaEditando[colSeleccionada] && (() => {
                    const idx = colSeleccionada;
                    const col = columnasPlanillaEditando[idx];
                    const letter = String.fromCharCode(65 + idx);
                    const reglaActual = reglasPlanilla.find(r => r.id === col.reglaId) || reglasPlanilla.find(r => r.comportamiento === col.role);
                    const tipoLabel = { texto: 'Casilla de texto', desplegable: 'Desplegable', toggle: 'Botón de opciones' };
                    const compLabel = { talle: `${term.variante} (mapea el molde)`, nombre: 'Nombre (se estampa)', numero: 'Número (se estampa)', manga: 'Toggle de pieza', none: 'Solo dato' };
                    return (
                      <div className="settings-drawer" style={{ width: 300, flexShrink: 0, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-light)', borderRadius: 12, padding: 18, position: 'sticky', top: 20 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                          <div style={{ fontSize: 14, fontWeight: 700 }}>Columna {letter}</div>
                          <button onClick={() => setColSeleccionada(null)} style={{ border: 'none', background: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 18, lineHeight: 1 }}>×</button>
                        </div>
                        <label style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 5 }}>Encabezado de la columna</label>
                        <input type="text" value={col.label || ''} placeholder="Nombre de columna…" onChange={(e) => handleUpdateEditorColumn(idx, 'label', e.target.value)}
                          style={{ width: '100%', padding: '8px 10px', borderRadius: 7, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none', fontSize: 13, marginBottom: 16 }} />
                        <label style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 5 }}>¿Qué es esta columna?</label>
                        <select value={col.reglaId || (reglaActual?.id) || ''} onChange={(e) => aplicarReglaAColumna(idx, e.target.value)}
                          style={{ width: '100%', padding: '8px 10px', borderRadius: 7, background: '#121214', border: '1px solid var(--border-light)', color: 'var(--cmyk-cyan)', outline: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                          <option value="" style={{ background: '#121214', color: '#fff' }}>— Elegí una regla —</option>
                          {reglasPlanilla.map(r => <option key={r.id} value={r.id} style={{ background: '#121214', color: '#fff' }}>{r.nombre}</option>)}
                        </select>
                        {reglaActual ? (
                          <div style={{ marginTop: 14, padding: 12, borderRadius: 8, background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-light)', fontSize: 12, lineHeight: 1.7 }}>
                            <div><span style={{ color: 'var(--text-muted)' }}>Se carga como:</span> <b>{tipoLabel[reglaActual.tipo] || reglaActual.tipo}</b></div>
                            {reglaActual.comportamiento === 'talle' ? (
                              <div><span style={{ color: 'var(--text-muted)' }}>Opciones:</span> las variantes del molde</div>
                            ) : (reglaActual.tipo !== 'texto' && reglaActual.opciones) ? (
                              <div><span style={{ color: 'var(--text-muted)' }}>Opciones:</span> {reglaActual.opciones}</div>
                            ) : null}
                            <div><span style={{ color: 'var(--text-muted)' }}>Qué hace:</span> {compLabel[reglaActual.comportamiento] || reglaActual.comportamiento}</div>
                          </div>
                        ) : (
                          <div style={{ marginTop: 12, fontSize: 11.5, color: 'var(--text-muted)', fontStyle: 'italic' }}>Elegí qué representa esta columna. Las reglas se definen en «Reglas de planilla».</div>
                        )}
                        <button className="btn ghost" onClick={() => setAdminSubView('reglas')} style={{ marginTop: 16, width: '100%', fontSize: 12, padding: '7px 10px', color: 'var(--cmyk-cyan)', borderColor: 'var(--cmyk-cyan)' }}>
                          ⚙ Gestionar reglas
                        </button>
                      </div>
                    );
                  })()}

                  <div style={{ flex: 1, minWidth: 0 }}>
                  {/* Google Sheets Grid */}
                  <div className="card" style={{ padding: 0, overflowX: 'auto', backgroundColor: '#09090b', border: '1px solid var(--border-light)', borderRadius: 10 }}>
                    <table style={{ borderCollapse: 'collapse', width: '100%', margin: 0, tableLayout: 'fixed', minWidth: 600 }}>
                      <thead>
                        {/* Fila 0: Column Letters & Deletes */}
                        <tr style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border-light)' }}>
                          <th style={{ width: 75, borderRight: '1px solid var(--border-light)', padding: '6px 8px', textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>
                            
                          </th>
                          {columnasPlanillaEditando.map((col, idx) => {
                            const letter = String.fromCharCode(65 + idx); // A, B, C...
                            const activa = colSeleccionada === idx;
                            return (
                              <th key={idx} draggable onClick={() => setColSeleccionada(idx)}
                                onDragStart={(e) => { e.dataTransfer.setData('colidx', String(idx)); e.dataTransfer.effectAllowed = 'move'; }}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={(e) => { e.preventDefault(); moverColumnaEditor(parseInt(e.dataTransfer.getData('colidx'), 10), idx); }}
                                title="Arrastrá para reordenar · clic para configurar" style={{ borderRight: '1px solid var(--border-light)', padding: '6px 8px', textAlign: 'center', position: 'relative', cursor: 'grab', background: activa ? 'rgba(0,216,245,0.10)' : 'transparent', borderBottom: activa ? '2px solid var(--cmyk-cyan)' : 'none' }}>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                                  <span style={{ fontSize: 13, opacity: activa ? 1 : 0.6 }}>⚙</span>
                                  <span style={{ fontSize: 12, fontFamily: 'monospace', fontWeight: 'bold', color: 'var(--cmyk-cyan)' }}>{letter}</span>
                                </span>
                                {columnasPlanillaEditando.length > 1 && (
                                  <button
                                    onClick={(e) => { e.stopPropagation(); handleRemoveEditorColumn(idx); }}
                                    style={{
                                      position: 'absolute',
                                      right: 4,
                                      top: 4,
                                      border: 'none',
                                      background: 'none',
                                      color: 'var(--error)',
                                      cursor: 'pointer',
                                      fontSize: 13,
                                      padding: '0 2px'
                                    }}
                                    title="Eliminar columna"
                                  >
                                    ×
                                  </button>
                                )}
                              </th>
                            );
                          })}
                          {/* Column for adding new */}
                          <th style={{ width: 60, padding: 4 }}></th>
                        </tr>

                        {/* Fila 1: Editable Header Cell */}
                        <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                          <td style={{ borderRight: '1px solid var(--border-light)', padding: '8px 10px', textAlign: 'center', backgroundColor: 'rgba(255,255,255,0.01)', fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>
                            Cabecera
                          </td>
                          {columnasPlanillaEditando.map((col, idx) => (
                            <td key={idx} style={{ borderRight: '1px solid var(--border-light)', padding: 0 }}>
                              <input 
                                type="text" 
                                value={col.label} 
                                placeholder="Nombre de columna..."
                                onChange={(e) => handleUpdateEditorColumn(idx, 'label', e.target.value)}
                                style={{
                                  width: '100%',
                                  padding: '8px 10px',
                                  border: 'none',
                                  background: 'transparent',
                                  color: '#fff',
                                  outline: 'none',
                                  fontSize: 13,
                                  fontWeight: 700,
                                  height: 38
                                }}
                              />
                            </td>
                          ))}
                          {/* Column for adding new */}
                          <td rowSpan={5} style={{ verticalAlign: 'middle', textAlign: 'center', padding: 10 }}>
                            <button 
                              className="btn ghost" 
                              onClick={handleAddEditorColumn} 
                              style={{ 
                                borderRadius: '50%', 
                                width: 32, 
                                height: 32, 
                                minWidth: 32, 
                                padding: 0, 
                                display: 'inline-flex', 
                                alignItems: 'center', 
                                justifyContent: 'center',
                                borderColor: 'var(--cmyk-cyan)',
                                color: 'var(--cmyk-cyan)'
                              }}
                              title="Agregar Columna"
                            >
                              <Icon name="plus" style={{ width: 14, height: 14 }} />
                            </button>
                          </td>
                        </tr>

                        {/* Fila 2: Qué es cada columna — clic para configurar en la barra izquierda */}
                        <tr style={{ borderBottom: '1px solid var(--border-light)', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                          <td style={{ borderRight: '1px solid var(--border-light)', padding: '8px 10px', textAlign: 'center', fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>
                            Tipo
                          </td>
                          {columnasPlanillaEditando.map((col, idx) => {
                            const regla = reglasPlanilla.find(r => r.id === col.reglaId) || reglasPlanilla.find(r => r.comportamiento === (col.role || 'none'));
                            const tipoTxt = { texto: 'casilla', desplegable: 'desplegable', toggle: 'botón de opciones' };
                            const t = col.tipo || regla?.tipo;
                            const activa = colSeleccionada === idx;
                            return (
                              <td key={idx} onClick={() => setColSeleccionada(idx)} title="Configurar columna" style={{ borderRight: '1px solid var(--border-light)', padding: '8px 10px', textAlign: 'center', cursor: 'pointer', background: activa ? 'rgba(0,216,245,0.06)' : 'transparent' }}>
                                {regla ? (
                                  <span style={{ display: 'inline-flex', flexDirection: 'column', gap: 2, lineHeight: 1.2 }}>
                                    <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--cmyk-magenta)' }}>{regla.nombre}</span>
                                    <span style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>{tipoTxt[t] || t}</span>
                                  </span>
                                ) : (
                                  <span style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>⚙ elegir…</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      </thead>
                      <tbody>
                        {/* Filas de VISTA PREVIA: cómo se verá la planilla real (controles de verdad) */}
                        {[0, 1, 2].map((rowIdx) => {
                          const ej = {
                            talle: ['M', 'L', 'S'],
                            nombre: ['GONZALEZ', 'PEREZ', 'ALVAREZ'],
                            numero: ['10', '7', '9'],
                            manga: ['Corta', 'Larga', 'Corta'],
                            none: ['Texto', 'Texto', 'Texto'],
                          };
                          const boxLook = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, padding: '5px 9px', borderRadius: 6, background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-light)', fontSize: 12.5, color: 'var(--text-primary)', minHeight: 30, boxSizing: 'border-box' };
                          return (
                            <tr key={rowIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                              <td style={{ borderRight: '1px solid var(--border-light)', padding: '8px 10px', textAlign: 'center', backgroundColor: 'rgba(255,255,255,0.01)', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                                {rowIdx + 1}
                              </td>
                              {columnasPlanillaEditando.map((col, idx) => {
                                const regla = reglasPlanilla.find(r => r.id === col.reglaId) || reglasPlanilla.find(r => r.comportamiento === (col.role || 'none'));
                                const role = col.role || regla?.comportamiento || 'none';
                                const tipo = col.tipo || regla?.tipo || (role === 'manga' ? 'toggle' : role === 'talle' ? 'desplegable' : 'texto');
                                const opts = ((col.opciones || regla?.opciones || '').split(',').map(s => s.trim()).filter(Boolean));
                                return (
                                  <td key={idx} style={{ borderRight: '1px solid var(--border-light)', padding: '5px 6px', verticalAlign: 'middle' }}>
                                    {role === 'talle' ? (
                                      <div style={boxLook}><span>{ej.talle[rowIdx] || 'M'}</span><span style={{ color: 'var(--cmyk-cyan)', fontSize: 10 }}>▾</span></div>
                                    ) : tipo === 'desplegable' ? (
                                      <div style={boxLook}><span>{opts.length ? opts[rowIdx % opts.length] : 'opción'}</span><span style={{ color: 'var(--cmyk-cyan)', fontSize: 10 }}>▾</span></div>
                                    ) : tipo === 'toggle' ? (
                                      <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border-light)', minHeight: 30 }}>
                                        {(opts.length >= 2 ? opts : (role === 'manga' ? ['Corta', 'Larga'] : ['Opción A', 'Opción B'])).map((o, oi) => {
                                          const on = oi === (rowIdx % Math.max(opts.length, 2));
                                          return <div key={oi} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '4px 6px', fontSize: 11, fontWeight: 600, background: on ? 'var(--accent)' : 'transparent', color: on ? 'var(--bg-primary)' : 'var(--text-muted)' }}>{o}</div>;
                                        })}
                                      </div>
                                    ) : (
                                      <div style={{ ...boxLook, color: 'var(--text-secondary)', fontFamily: role === 'numero' ? 'monospace' : 'inherit' }}>{ej[role]?.[rowIdx] || ej.none[rowIdx]}</div>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Help panel inside editor */}
                  <div style={{ marginTop: 20, backgroundColor: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-light)', borderRadius: 10, padding: 16 }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>💡 Cómo armar la planilla</h4>
                    <p style={{ margin: 0, fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      • Hacé clic en el <b>⚙</b> de cada columna para abrir su barra a la izquierda y elegir <b>qué es</b> (su regla).<br />
                      • Las reglas (casilla / desplegable / botón, y qué hace cada una) se crean en <b>«Reglas de planilla»</b>.<br />
                      • Necesitás al menos una columna con una regla de tipo <b>{term.variante}</b>: define qué variante del molde usa cada fila. Cada fila = una copia.
                    </p>
                  </div>
                  </div>
                  </div>
                  )}
                </div>
              )
            )}

            {/* 3b. Reglas de planilla (biblioteca de campos reutilizables) */}
            {adminSubView === 'reglas' && (() => {
              const labelStyle = { display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 };
              const inputStyle = { width: '100%', padding: '9px 11px', borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none', fontSize: 13.5 };
              const comps = [
                { v: 'talle', label: `${term.variante} — elige la variante del molde` },
                { v: 'diseno', label: 'Diseño — elige cuál de los diseños del pedido lleva la fila' },
                { v: 'nombre', label: 'Se estampa como TEXTO (nombre, palabra…) → capa en el diseño' },
                { v: 'numero', label: 'Se estampa como NÚMERO (número, número 2…) → capa en el diseño' },
                { v: 'manga', label: 'Toggle de pieza (como Manga)' },
                { v: 'none', label: 'Solo dato (no afecta el molde)' },
              ];
              const tipoTxt = { texto: 'Casilla de texto', desplegable: 'Desplegable', toggle: 'Botón de opciones' };
              const compTxt = { talle: `${term.variante} (variante del molde)`, diseno: 'Diseño del pedido', nombre: 'Se estampa (texto)', numero: 'Se estampa (número)', manga: 'Toggle de pieza', none: 'Solo dato' };
              return (
                <div className="panel animate-fade">
                  <div style={{ marginBottom: 20 }}>
                    <button className="btn ghost" onClick={() => { setReglaEditando(null); setAdminSubView('dashboard'); }} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
                      ⬅ Volver al Panel de Configuración
                    </button>
                  </div>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                    <div>
                      <h2>Reglas de planilla</h2>
                      <p>Campos reutilizables: definí cómo se cargan (casilla / desplegable / botón) y qué hacen. Después, en cada columna de la planilla, solo elegís la regla.</p>
                    </div>
                    <button className="btn primary" onClick={() => setReglaEditando({ nombre: '', tipo: 'texto', opciones: '', comportamiento: 'none' })} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Icon name="plus" style={{ width: 14, height: 14 }} /> Nueva Regla
                    </button>
                  </div>

                  {/* Capas que debe tener el archivo de diseño — para copiarle al diseñador.
                      El texto/número se toman SEGÚN LA CAPA donde estén. */}
                  {(() => {
                    const sysLayers = [
                      { n: 'diseño', d: 'el arte que se imprime' },
                      { n: 'guias', d: 'nombres de las piezas (no se imprime)' },
                    ];
                    // Capas de personalización = las REGLAS que se estampan (nombre/número).
                    // El nombre de la regla ES el nombre de la capa que debe tener el diseño.
                    const persFields = [...new Set(
                      (reglasPlanilla || [])
                        .filter(r => ['nombre', 'numero'].includes(r.comportamiento))
                        .map(r => (r.nombre || '').trim())
                    )].filter(Boolean);
                    const todas = [...sysLayers.map(s => s.n), ...persFields];
                    const chip = (txt, extra) => (
                      <span key={txt} onClick={() => { navigator.clipboard?.writeText(txt); showMsg(`Copiado: ${txt}`); }}
                        title="Clic para copiar"
                        style={{ fontSize: 11.5, padding: '4px 10px', borderRadius: 6, background: extra || 'rgba(255,255,255,0.04)', border: '1px solid var(--border-light)', cursor: 'pointer', color: 'var(--text-primary)' }}>
                        {txt}
                      </span>
                    );
                    return (
                      <div className="card" style={{ padding: 18, marginTop: 20, border: '1px solid var(--border-light)', maxWidth: 720 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>📐 Capas que debe tener el archivo de diseño</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14, lineHeight: 1.5 }}>
                          En Illustrator, el diseñador crea una capa con cada uno de estos nombres. El <b>texto</b> y el <b>número</b> se estampan <b>según la capa</b> donde estén (mayúsculas y acentos no importan). Tocá un nombre para copiarlo.
                        </div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 6 }}>Capas del sistema</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14, alignItems: 'center' }}>
                          {sysLayers.map(s => (
                            <span key={s.n} onClick={() => { navigator.clipboard?.writeText(s.n); showMsg(`Copiado: ${s.n}`); }} title="Clic para copiar"
                              style={{ fontSize: 11.5, padding: '4px 10px', borderRadius: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-light)', cursor: 'pointer' }}>
                              {s.n} <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>· {s.d}</span>
                            </span>
                          ))}
                        </div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 6 }}>Capas de personalización (texto / número)</div>
                        {persFields.length ? (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
                            {persFields.map(f => chip(f, 'rgba(0,159,227,0.08)'))}
                          </div>
                        ) : (
                          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginBottom: 12 }}>Todavía no hay campos que se estampen. Creá reglas con «Se estampa (Nombre/Número)» y usalas en la planilla.</div>
                        )}
                        <button className="btn ghost" style={{ fontSize: 11.5 }}
                          onClick={() => { navigator.clipboard?.writeText(todas.join('\n')); showMsg('Capas copiadas ✓'); }}>
                          📋 Copiar todas las capas
                        </button>
                        <div style={{ fontSize: 10.5, color: 'var(--text-muted)', marginTop: 10, lineHeight: 1.5 }}>
                          No es obligatorio: si el diseño no trae alguna de estas capas, igual se procesa. Solo que, al subir el diseño, te avisamos qué dato cargado en la planilla no se va a estampar por no tener su capa.
                        </div>
                      </div>
                    );
                  })()}

                  <Modal open={!!reglaEditando} onClose={() => setReglaEditando(null)}
                    titulo={reglaEditando?.id ? 'Editar regla' : 'Nueva regla'} maxWidth={560}>
                    {reglaEditando && (() => {
                      const r = reglaEditando;
                      const set = (k, v) => setReglaEditando({ ...r, [k]: v });
                      return (
                        <div style={{ display: 'grid', gap: 14 }}>
                          <div>
                            <label style={labelStyle}>Nombre</label>
                            <input type="text" value={r.nombre} placeholder="Ej. Color, Equipo, Talle…" onChange={(e) => set('nombre', e.target.value)} style={inputStyle} />
                          </div>
                          <div>
                            <label style={labelStyle}>¿Cómo se carga en la planilla?</label>
                            <div style={{ display: 'flex', gap: 8 }}>
                              {[{ v: 'texto', l: 'Casilla' }, { v: 'desplegable', l: 'Desplegable' }, { v: 'toggle', l: 'Botón de opciones' }].map(o => (
                                <button key={o.v} type="button" onClick={() => set('tipo', o.v)} className={'chip' + (r.tipo === o.v ? ' active' : '')} style={{ flex: 1, padding: '8px', cursor: 'pointer', justifyContent: 'center' }}>{o.l}</button>
                              ))}
                            </div>
                            {r.tipo === 'toggle' && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>Un botón por cada opción que escribas (2 o más).</div>}
                          </div>
                          {(r.tipo === 'desplegable' || r.tipo === 'toggle') && r.comportamiento !== 'talle' && r.comportamiento !== 'diseno' && (
                            <div>
                              <label style={labelStyle}>Opciones {r.tipo === 'toggle' ? '(2 o más, separadas por coma)' : '(separadas por coma)'}</label>
                              <input type="text" value={r.opciones} placeholder={r.tipo === 'toggle' ? 'Corta, Larga' : 'Rojo, Azul, Verde'} onChange={(e) => set('opciones', e.target.value)} style={inputStyle} />
                            </div>
                          )}
                          {r.comportamiento === 'talle' && (r.tipo === 'desplegable' || r.tipo === 'toggle') && (
                            <div style={{ fontSize: 11.5, color: 'var(--text-muted)', fontStyle: 'italic' }}>Las opciones salen automáticamente de las variantes del molde.</div>
                          )}
                          {r.comportamiento === 'diseno' && (
                            <div style={{ fontSize: 11.5, color: 'var(--accent)', background: 'rgba(0,216,245,0.07)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '9px 11px', lineHeight: 1.45 }}>
                              No hay que cargar opciones acá: el desplegable se llena solo con los <b>diseños que escribís en el pedido</b> (paso «Diseños»). Solo creá esta columna y agregala a la planilla.
                            </div>
                          )}
                          <div>
                            <label style={labelStyle}>¿Qué hace con ese dato?</label>
                            <select value={r.comportamiento} onChange={(e) => set('comportamiento', e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
                              {comps.map(c => <option key={c.v} value={c.v} style={{ background: '#121214', color: '#fff' }}>{c.label}</option>)}
                            </select>
                          </div>
                          {r.comportamiento === 'manga' && (
                            <div>
                              <label style={labelStyle}>Palabra clave <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>(la palabra en los nombres de las piezas)</span></label>
                              <input type="text" value={r.clave || ''} placeholder="Ej. manga, sisa, capucha…" onChange={(e) => set('clave', e.target.value)} style={inputStyle} />
                              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.45, background: 'rgba(0,216,245,0.06)', border: '1px solid var(--border-light)', borderRadius: 8, padding: '8px 10px' }}>
                                Las piezas del molde que mencionen esta palabra se agrupan por la opción elegida. Ej: clave <b>{r.clave || 'manga'}</b> + opción <b>{(r.opciones || 'Corta').split(',')[0].trim()}</b> → entran las piezas que dicen «{(r.clave || 'manga')} {(r.opciones || 'Corta').split(',')[0].trim().toLowerCase()}». Puede tener varias piezas (vivo, refuerzo…).
                              </div>
                            </div>
                          )}
                          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
                            <button className="btn ghost" onClick={() => setReglaEditando(null)} style={{ padding: '8px 16px' }}>Cancelar</button>
                            <button className="btn success" onClick={() => guardarRegla(r)} style={{ backgroundColor: 'var(--success)', color: 'white', padding: '8px 16px' }}>Guardar regla</button>
                          </div>
                        </div>
                      );
                    })()}
                  </Modal>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 14, marginTop: 20 }}>
                    {reglasPlanilla.map(r => (
                      <div key={r.id} className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column' }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{r.nombre}</h3>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6, flex: 1 }}>
                          <div><span style={{ color: 'var(--text-muted)' }}>Carga:</span> {tipoTxt[r.tipo] || r.tipo}</div>
                          {r.tipo !== 'texto' && r.comportamiento !== 'talle' && r.opciones && <div><span style={{ color: 'var(--text-muted)' }}>Opciones:</span> {r.opciones}</div>}
                          <div><span style={{ color: 'var(--text-muted)' }}>Hace:</span> {compTxt[r.comportamiento] || r.comportamiento}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 8, marginTop: 14, borderTop: '1px solid var(--border-light)', paddingTop: 10 }}>
                          <button className="btn ghost" onClick={() => setReglaEditando({ ...r })} style={{ padding: '5px 12px', fontSize: 11.5 }}>Editar</button>
                          <button className="btn ghost" onClick={() => eliminarRegla(r.id)} style={{ padding: '5px 12px', fontSize: 11.5, color: 'var(--error)', borderColor: 'var(--error)' }}>Eliminar</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* 5. Reglas de Nesting Subview */}
            {adminSubView === 'nesting' && (() => {
              const inputStyle = { height: 40, width: '100%', fontSize: 14, padding: '0 11px', borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' };
              const labelStyle = { fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 6, fontWeight: 600 };
              const rotTxt = { auto: 'No girar', ninguna: 'No girar', '90': 'Giros 90°', '180': 'Giros 180°', libre: 'Giro libre' };
              // En el editor de grupo el panel ocupa todo el alto (grilla scrollea adentro, barra al fondo, sin hueco).
              // En lista/presets crece natural y scrollea la página.
              const enEditorGrupo = nestingTab === 'grupos' && !!grupoTizadaEditando;
              return (
                <div className="panel animate-fade" style={enEditorGrupo ? { display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)', overflow: 'hidden' } : {}}>
                  <div style={{ marginBottom: 20, flexShrink: 0 }}>
                    <button className="btn ghost" onClick={() => { setNestingEditando(null); setAdminSubView('dashboard'); }} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
                      ⬅ Volver al Panel de Configuración
                    </button>
                  </div>
                  <h2 style={{ marginBottom: 4 }}>Reglas de Nesting</h2>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>Configurá los nesting (separación, margen y giro) y los grupos de moldes que comparten la misma tizada.</p>
                  {/* Pestañas: Nesting | Grupos de tizada */}
                  <div style={{ display: 'flex', gap: 4, marginBottom: 24, borderBottom: '1px solid var(--border-light)' }}>
                    {[{ k: 'presets', l: 'Nesting' }, { k: 'grupos', l: 'Grupos de tizada' }].map(t => (
                      <button key={t.k} type="button" onClick={() => { setNestingTab(t.k); setNestingEditando(null); setGrupoTizadaEditando(null); }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '10px 16px', fontSize: 14, fontWeight: nestingTab === t.k ? 700 : 500,
                          color: nestingTab === t.k ? 'var(--accent)' : 'var(--text-secondary)', borderBottom: nestingTab === t.k ? '2px solid var(--accent)' : '2px solid transparent', marginBottom: -1 }}>
                        {t.l}
                      </button>
                    ))}
                  </div>

                  {nestingTab === 'presets' && (<>
                  <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
                    <div>
                      <h3 style={{ fontSize: 17, fontWeight: 700 }}>Plantillas de nesting</h3>
                      <p>Guardá distintos nesting como plantillas. Después, en cada molde elegís cuál usar.</p>
                    </div>
                    <button className="btn primary" onClick={() => setNestingEditando({ nombre: '', espaciado_mm: 5, margen_mm: 10, rotacion: 'ninguna' })} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Icon name="plus" style={{ width: 14, height: 14 }} /> Nuevo Nesting
                    </button>
                  </div>

                  <Modal open={!!nestingEditando} onClose={() => setNestingEditando(null)}
                    titulo={nestingEditando?.id ? 'Editar nesting' : 'Nuevo nesting'} maxWidth={520}>
                    {nestingEditando && (() => {
                      const n = nestingEditando;
                      const set = (k, v) => setNestingEditando({ ...n, [k]: v });
                      return (
                        <div style={{ display: 'grid', gap: 16 }}>
                          <div>
                            <label style={labelStyle}>Nombre</label>
                            <input type="text" value={n.nombre} placeholder="Ej. Estándar, Apretado, Sin giro…" onChange={(e) => set('nombre', e.target.value)} style={inputStyle} />
                          </div>
                          <div>
                            <label style={labelStyle}>Separación de seguridad entre piezas (mm)</label>
                            <input type="number" value={n.espaciado_mm} onChange={(e) => set('espaciado_mm', parseFloat(e.target.value) || 0)} style={inputStyle} />
                            <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: 4 }}>Al menos 5 mm para evitar superposición al cortar.</small>
                          </div>
                          <div>
                            <label style={labelStyle}>Margen del borde de la tela (mm)</label>
                            <input type="number" value={n.margen_mm} onChange={(e) => set('margen_mm', parseFloat(e.target.value) || 0)} style={inputStyle} />
                          </div>
                          <div>
                            <label style={labelStyle}>Giro de piezas <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>— se aplica igual a TODAS las piezas</span></label>
                            <select value={n.rotacion === 'auto' ? 'ninguna' : n.rotacion} onChange={(e) => set('rotacion', e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
                              <option value="ninguna">No girar ninguna pieza</option>
                              <option value="90">Permitir giros de 90°</option>
                              <option value="180">Permitir giros de 180°</option>
                              <option value="libre">Giro libre (mayor aprovechamiento)</option>
                            </select>
                          </div>
                          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 4 }}>
                            <button className="btn ghost" onClick={() => setNestingEditando(null)} style={{ padding: '8px 16px' }}>Cancelar</button>
                            <button className="btn success" style={{ backgroundColor: 'var(--success)', color: 'white', padding: '8px 16px' }}
                              onClick={async () => { const id = await guardarNestingPreset(n); if (id) setNestingEditando(null); }}>Guardar nesting</button>
                          </div>
                        </div>
                      );
                    })()}
                  </Modal>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14, marginTop: 20 }}>
                    {nestingPresets.map(n => (
                      <div key={n.id} className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column' }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{n.nombre}</h3>
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.7, flex: 1 }}>
                          Separación: <b>{n.espaciado_mm} mm</b><br />
                          Margen: <b>{n.margen_mm} mm</b><br />
                          Giro: <b>{rotTxt[n.rotacion] || n.rotacion}</b>
                        </div>
                        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                          <button className="btn ghost" style={{ flex: 1, fontSize: 12 }} onClick={() => setNestingEditando({ ...n })}>Editar</button>
                          {n.id !== 'nesting_default' && (
                            <button className="btn ghost" style={{ fontSize: 12, color: 'var(--error)' }} onClick={() => eliminarNestingPreset(n.id)}>Eliminar</button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  </>)}

                  {/* ── Grupos de tizada: qué moldes se arman JUNTOS en la misma mesa ── */}
                  {/* Botón → entra a la VISTA del editor (no popup). Volver = lista. */}
                  {nestingTab === 'grupos' && (grupoTizadaEditando ? (() => {
                    const g = grupoTizadaEditando;
                    const toggle = (pid) => setGrupoTizadaEditando(prev => ({ ...prev, moldes: prev.moldes.includes(pid) ? prev.moldes.filter(x => x !== pid) : [...prev.moldes, pid] }));
                    return (
                      <div className="animate-fade" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                        <button className="btn ghost" onClick={() => setGrupoTizadaEditando(null)} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px', marginBottom: 18, flexShrink: 0, alignSelf: 'flex-start' }}>
                          ⬅ Volver a los grupos
                        </button>
                        <h3 style={{ fontSize: 18, fontWeight: 800, margin: '0 0 4px', flexShrink: 0 }}>{g.id ? 'Editar grupo de tizada' : 'Nuevo grupo de tizada'}</h3>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: 22, flexShrink: 0 }}>Ponele un nombre y tocá los moldes que se arman juntos en la misma mesa de trabajo.</p>
                        <label style={{ ...labelStyle, flexShrink: 0 }}>Nombre del grupo</label>
                        <input type="text" value={g.nombre} placeholder="Ej. Conjunto deportivo, Equipo de fútbol…" onChange={(e) => setGrupoTizadaEditando({ ...g, nombre: e.target.value })} style={{ ...inputStyle, marginBottom: 22, maxWidth: 480, flexShrink: 0 }} />
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 12, flexShrink: 0 }}>Moldes que comparten tizada · {g.moldes.length} elegido{g.moldes.length === 1 ? '' : 's'}</div>
                        {/* Grilla de moldes VISUALES (silueta) que CRECE y scrollea adentro: soporta miles */}
                        <div style={{ flex: 1, minHeight: 120, overflowY: 'auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 14, alignContent: 'start', paddingRight: 2 }}>
                          {productosCat.productos.map(p => {
                            const on = g.moldes.includes(p.id);
                            return (
                              <button key={p.id} type="button" onClick={() => toggle(p.id)}
                                style={{ textAlign: 'left', cursor: 'pointer', padding: 12, borderRadius: 12, transition: 'all .15s',
                                  border: on ? '1.5px solid var(--accent)' : '1px solid var(--border-light)',
                                  background: on ? 'linear-gradient(180deg, rgba(0,216,245,0.10), rgba(0,216,245,0.02))' : 'rgba(255,255,255,0.02)',
                                  boxShadow: on ? '0 0 16px rgba(0,216,245,0.16)' : 'none' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 8 }}>
                                  <span style={{ fontWeight: 700, fontSize: 13.5, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.nombre}</span>
                                  <span style={{ width: 22, height: 22, borderRadius: '50%', flexShrink: 0, border: on ? 'none' : '1.5px solid var(--border-light)', background: on ? 'var(--accent)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    {on && <Icon name="check" style={{ width: 12, height: 12, color: '#000', strokeWidth: 3 }} />}
                                  </span>
                                </div>
                                <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: 8 }}>
                                  <MoldePreviewSVG id={p.id} height={84} color={on ? 'var(--accent)' : 'rgba(255,255,255,0.5)'} />
                                </div>
                              </button>
                            );
                          })}
                        </div>
                        {/* Barra de acciones FOOTER: siempre al fondo, fuera del scroll de la grilla */}
                        <div style={{ flexShrink: 0, display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'flex-end', padding: '14px 0 2px', borderTop: '1px solid var(--border-light)' }}>
                          <span style={{ marginRight: 'auto', fontSize: 12.5, color: 'var(--text-secondary)' }}>{g.moldes.length} molde{g.moldes.length === 1 ? '' : 's'} en el grupo</span>
                          <button className="btn ghost" onClick={() => setGrupoTizadaEditando(null)} style={{ padding: '8px 16px' }}>Cancelar</button>
                          <button className="btn success" style={{ backgroundColor: 'var(--success)', color: 'white', padding: '8px 18px' }}
                            onClick={async () => { const id = await guardarGrupoTizadaCfg(g); if (id) setGrupoTizadaEditando(null); }}>Guardar grupo</button>
                        </div>
                      </div>
                    );
                  })() : (
                  <div>
                    <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16, marginBottom: 0 }}>
                      <div>
                        <h3 style={{ fontSize: 17, fontWeight: 700 }}>Grupos de tizada</h3>
                        <p>Elegí qué moldes se arman <b>juntos en la misma mesa de trabajo</b>. Creá un grupo, ponele un nombre y tocá los moldes que comparten tizada. Los moldes que no estén en ningún grupo se arman por separado.</p>
                      </div>
                      <button className="btn primary" onClick={() => setGrupoTizadaEditando({ nombre: '', moldes: [] })} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Icon name="plus" style={{ width: 14, height: 14 }} /> Nuevo grupo
                      </button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14, marginTop: 20 }}>
                      {gruposTizada.length === 0 && (
                        <div style={{ fontSize: 12.5, color: 'var(--text-muted)', gridColumn: '1 / -1' }}>Todavía no hay grupos. Sin grupos, cada molde se arma en su propia tizada. Creá uno para combinar moldes en la misma mesa.</div>
                      )}
                      {gruposTizada.map(g => {
                        const nombres = (g.moldes || []).map(pid => productosCat.productos.find(p => p.id === pid)?.nombre).filter(Boolean);
                        return (
                          <div key={g.id} className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column' }}>
                            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{g.nombre}</h3>
                            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.6, flex: 1 }}>
                              {nombres.length ? <>Comparten mesa:<br /><b>{nombres.join(' · ')}</b></> : <span style={{ color: 'var(--text-muted)' }}>Sin moldes asignados.</span>}
                            </div>
                            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                              <button className="btn ghost" style={{ flex: 1, fontSize: 12 }} onClick={() => setGrupoTizadaEditando({ ...g, moldes: [...(g.moldes || [])] })}>Editar</button>
                              <button className="btn ghost" style={{ fontSize: 12, color: 'var(--error)' }} onClick={() => eliminarGrupoTizadaCfg(g.id)}>Eliminar</button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  ))}
                </div>
              );
            })()}

            {/* 6. Telas Subview (registro global + grupos combinables) */}
            {adminSubView === 'telas' && (() => {
              const inS = { height: 36, fontSize: 13, padding: '0 10px', borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' };
              const T = telasReg.telas || [], G = telasReg.grupos || [];
              const setT = (ts) => setTelasReg({ ...telasReg, telas: ts });
              const setG = (gs) => setTelasReg({ ...telasReg, grupos: gs });
              return (
                <div className="panel animate-fade">
                  <div style={{ marginBottom: 20 }}>
                    <button className="btn ghost" onClick={() => setAdminSubView('dashboard')} style={{ fontSize: 12.5, padding: '6px 12px' }}>⬅ Volver al Panel de Configuración</button>
                  </div>
                  <div className="panel-header"><h2 style={{ fontSize: 20, fontWeight: 700 }}>Telas</h2></div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '6px 0 18px', lineHeight: 1.5, maxWidth: 640 }}>
                    Registrá tus telas (nombre + ancho de rollo). El <b>alto</b> de la hoja se configura en Reglas de Nesting. Después armá <b>grupos</b> de telas que se pueden combinar entre sí en una misma prenda.
                  </p>

                  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Telas registradas</h3>
                  {T.map((t, i) => (
                    <div key={t.id || i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'center' }}>
                      <input value={t.nombre} onChange={e => { const ts = [...T]; ts[i] = { ...ts[i], nombre: e.target.value }; setT(ts); }} placeholder="Nombre de la tela" style={{ ...inS, flex: 1, maxWidth: 260 }} />
                      <input type="number" value={t.ancho_cm} onChange={e => { const ts = [...T]; ts[i] = { ...ts[i], ancho_cm: e.target.value }; setT(ts); }} placeholder="Ancho" style={{ ...inS, width: 100 }} />
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>cm de ancho</span>
                      <button className="btn ghost" onClick={() => setT(T.filter((_, j) => j !== i))} title="Quitar" style={{ padding: '4px 9px' }}>✕</button>
                    </div>
                  ))}
                  <button className="btn ghost" onClick={() => setT([...T, { id: 'tl_n' + Date.now(), nombre: '', ancho_cm: 180 }])} style={{ marginTop: 4, fontSize: 12.5 }}>+ Agregar tela</button>

                  <h3 style={{ fontSize: 14, fontWeight: 700, margin: '26px 0 6px' }}>Grupos combinables</h3>
                  <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 12, maxWidth: 640 }}>Tocá las telas que se pueden combinar entre sí. En el pedido, una pieza podrá cambiar su tela por otra del mismo grupo (si está asignada al molde).</p>
                  {G.map((g, gi) => (
                    <div key={g.id || gi} style={{ border: '1px solid var(--border-light)', borderRadius: 10, padding: 12, marginBottom: 10 }}>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 10, alignItems: 'center' }}>
                        <input value={g.nombre} onChange={e => { const gs = [...G]; gs[gi] = { ...gs[gi], nombre: e.target.value }; setG(gs); }} placeholder="Nombre del grupo" style={{ ...inS, flex: 1, maxWidth: 260 }} />
                        <button className="btn ghost" onClick={() => setG(G.filter((_, j) => j !== gi))} title="Quitar grupo" style={{ padding: '4px 9px' }}>✕</button>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {T.length === 0 && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Registrá telas arriba primero.</span>}
                        {T.map(t => {
                          const on = (g.telas || []).includes(t.id);
                          return <button key={t.id} onClick={() => { const gs = [...G]; const s = new Set(g.telas || []); on ? s.delete(t.id) : s.add(t.id); gs[gi] = { ...gs[gi], telas: [...s] }; setG(gs); }} style={{ padding: '4px 11px', borderRadius: 999, border: '1px solid ' + (on ? 'var(--accent)' : 'var(--border-light)'), background: on ? 'rgba(0,243,255,0.12)' : 'transparent', color: on ? 'var(--accent)' : 'var(--text-secondary)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>{t.nombre || '(sin nombre)'}</button>;
                        })}
                      </div>
                    </div>
                  ))}
                  <button className="btn ghost" onClick={() => setG([...G, { id: 'gt_n' + Date.now(), nombre: '', telas: [] }])} style={{ fontSize: 12.5 }}>+ Agregar grupo</button>

                  <div style={{ marginTop: 26, paddingTop: 16, borderTop: '1px solid var(--border-light)' }}>
                    <button className="btn success" onClick={() => guardarTelas(T, G)} style={{ padding: '9px 20px', fontWeight: 700 }}>Guardar telas</button>
                  </div>
                </div>
              );
            })()}


            {/* 7. Catálogo de Fuentes Subview */}
            {/* Perfil de color (ICC) */}
            {adminSubView === 'perfil' && (
              <div className="panel animate-fade">
                <div style={{ marginBottom: 20 }}>
                  <button className="btn ghost" onClick={() => setAdminSubView('dashboard')} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
                    ⬅ Volver al Panel de Configuración
                  </button>
                </div>
                <div className="panel-header" style={{ marginBottom: 14 }}>
                  <h2>Perfil de color</h2>
                  <p>Elegí el perfil ICC <b>predeterminado</b> para los diseños. Al cargar un arte, el sistema lee el perfil <b>incrustado</b> y avisa si no coincide con el predeterminado (o si viene sin perfil). Los colores no se modifican: solo se asigna/recomienda el perfil.</p>
                </div>
                {!perfilesData ? (
                  <div style={{ color: 'var(--text-secondary)', padding: 20 }}>Cargando perfiles…</div>
                ) : !perfilesData.hay_perfiles ? (
                  <div style={{ color: 'var(--warning, #e0a020)', padding: 16, border: '1px solid var(--border-light)', borderRadius: 10 }}>No se encontraron perfiles ICC en el sistema. Instalá los perfiles de color (vienen con Adobe) o definí la carpeta con la variable <code>TIZADA_PERFILES</code>.</div>
                ) : (
                  [{ k: 'cmyk', t: 'CMYK (impresión)' }, { k: 'rgb', t: 'RGB (pantalla)' }].map(grp => {
                    const lista = perfilesData[grp.k] || [];
                    const actual = perfilesData.config?.[grp.k];
                    const actualNombre = (lista.find(p => p.archivo === actual) || {}).nombre || actual;
                    return (
                      <div key={grp.k} style={{ marginBottom: 28 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14, flexWrap: 'wrap' }}>
                          <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '.09em', textTransform: 'uppercase', color: grp.k === 'cmyk' ? '#7c5cff' : '#00d8f5', background: (grp.k === 'cmyk' ? '#7c5cff' : '#00d8f5') + '1e', padding: '5px 11px', borderRadius: 999 }}>{grp.t}</span>
                          {(() => { const dp = lista.find(p => p.archivo === actual); return (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
                              Predeterminado:
                              {dp?.colores?.length > 0 && <span style={{ display: 'flex', width: 56, height: 13, borderRadius: 4, overflow: 'hidden', boxShadow: '0 0 0 1px rgba(255,255,255,0.12)' }}>{dp.colores.map((c, i) => <span key={i} style={{ flex: 1, background: c }} />)}</span>}
                              <b style={{ color: '#fff' }}>{actualNombre || '—'}</b>
                            </span>
                          ); })()}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(226px, 1fr))', gap: 12 }}>
                          {lista.map(p => {
                            const sel = p.archivo === actual;
                            const cols = (p.colores && p.colores.length) ? p.colores : ['#2a2a30', '#33333a', '#3c3c44', '#45454e', '#4e4e58', '#575762'];
                            return (
                              <button key={p.archivo} type="button" className="perfil-card" onClick={() => guardarPerfilDefault(grp.k, p.archivo)} title={p.archivo}
                                style={{ position: 'relative', textAlign: 'left', display: 'flex', flexDirection: 'column', padding: 0, borderRadius: 13, overflow: 'hidden', cursor: 'pointer', transition: 'all .18s',
                                  border: sel ? '1.5px solid var(--accent)' : '1px solid var(--border-light)',
                                  background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.012))',
                                  boxShadow: sel ? '0 0 22px rgba(0,216,245,0.28), inset 0 0 0 1px rgba(0,216,245,0.14)' : 'none' }}>
                                {/* franja de COLORES REALES que produce el perfil (referencia) */}
                                <div style={{ display: 'flex', height: 22 }}>
                                  {cols.map((c, ci) => <span key={ci} style={{ flex: 1, background: c }} />)}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '10px 12px' }}>
                                  <span style={{ fontSize: 12.5, fontWeight: sel ? 700 : 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.nombre}</span>
                                  {sel
                                    ? <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 18, height: 18, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0, boxShadow: '0 0 10px rgba(0,216,245,0.6)' }}><Icon name="check" style={{ width: 11, height: 11, color: '#001016', strokeWidth: 3.5 }} /></span>
                                    : <span style={{ fontSize: 10.5, fontWeight: 600, color: 'var(--text-muted)', flexShrink: 0, opacity: 0.65 }}>Usar</span>}
                                </div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {adminSubView === 'usuarios' && (
              <PantallaUsuarios onVolver={() => setAdminSubView('dashboard')} showMsg={showMsg} showError={showError} yo={yo} />
            )}

            {/* DETALLE de una fuente: tabla de glifos + laboratorio. Tiene su propio "Volver". */}
            {adminSubView === 'fuentes' && fuenteDetalle && (
              <DetalleFuente f={fuenteDetalle} onVolver={() => setFuenteDetalle(null)} />
            )}

            {adminSubView === 'fuentes' && !fuenteDetalle && (
              <div className="panel animate-fade">
                <div style={{ marginBottom: 20 }}>
                  <button className="btn ghost" onClick={() => setAdminSubView('dashboard')} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, padding: '6px 12px' }}>
                    ⬅ Volver al Panel de Configuración
                  </button>
                </div>
                <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
                  <div>
                    <h2>Catálogo de Fuentes</h2>
                    <p>Sube y gestiona tipografías TTF/OTF para el redibujado de textos del Excel.</p>
                  </div>
                  {/* BUSCADOR: filtra en tiempo real por nombre interno o archivo */}
                  <div style={{ position: 'relative', flexShrink: 0, width: 260 }}>
                    <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', display: 'flex', color: 'var(--text-muted)', pointerEvents: 'none' }}>
                      <Icon name="search" style={{ width: 13, height: 13 }} />
                    </span>
                    <input value={buscarFuente} onChange={(e) => setBuscarFuente(e.target.value)} spellCheck={false}
                      placeholder="Buscar fuente…"
                      style={{ width: '100%', height: 34, padding: '0 28px 0 30px', fontSize: 12.5, borderRadius: 8,
                        background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary, #fff)', border: '1px solid var(--border-light)', outline: 'none' }} />
                    {!!buscarFuente && (
                      <button type="button" onClick={() => setBuscarFuente('')} title="Limpiar"
                        style={{ position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)', width: 18, height: 18, borderRadius: 5,
                          display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', border: 'none',
                          background: 'transparent', color: 'var(--text-muted)', fontSize: 11 }}>✕</button>
                    )}
                  </div>
                </div>

                <div className="card" style={{ margin: '20px 0', padding: 24 }}>
                  {/* título + SUBIR a la derecha, en la misma línea */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                    <div className="card-title" style={{ margin: 0 }}>Tipografías Registradas en el Servidor</div>
                    <input type="file" ref={fileInputFuenteRef} accept=".ttf,.otf" onChange={(e) => handleUploadFile('fuente', e.target.files[0])} hidden />
                    <button className="btn primary" onClick={() => fileInputFuenteRef.current.click()} style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                      <Icon name="plus" style={{ width: 14, height: 14 }} /> Subir Nueva Fuente (.ttf / .otf)
                    </button>
                  </div>
                  {/* MUESTRA GLOBAL: lo que se escribe acá se ve al instante en TODAS las tarjetas,
                      con la tipografía real de cada una → comparar fuentes con el mismo texto. */}
                  <input value={muestraGlobal} onChange={(e) => setMuestraGlobal(e.target.value)}
                    spellCheck={false} placeholder={`Escribí para probar todas las fuentes… (${MUESTRA_DEF})`}
                    style={{ width: '100%', margin: '14px 0 20px', padding: '10px 12px', fontSize: 13.5, borderRadius: 8,
                      background: 'rgba(255,255,255,0.04)', color: 'var(--text-primary, #fff)', border: '1px solid var(--border-light)', outline: 'none' }} />

                  {/* Cada fuente del catálogo se declara con @font-face apuntando al archivo REAL
                      del servidor → la tarjeta la dibuja de verdad, no una tipografía cualquiera. */}
                  <style>{(estado?.fuentes || []).map(f => `@font-face{font-family:'${_famFuente(f)}';src:url('/api/fuente/archivo/${encodeURIComponent(f.archivo)}');font-display:swap;}`).join('')}</style>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
                    {!estado?.fuentes?.length ? (
                      <div style={{ gridColumn: 'span 2', color: 'var(--text-secondary)', fontSize: 13, padding: '12px 0' }}>No hay fuentes cargadas. Sube tipografías TrueType (.ttf/.otf) como Impact o Arial Bold.</div>
                    ) : !_fuentesFiltradas.length ? (
                      <div style={{ gridColumn: 'span 2', color: 'var(--text-secondary)', fontSize: 13, padding: '12px 0' }}>Ninguna fuente coincide con “{buscarFuente}”.</div>
                    ) : (
                      _fuentesFiltradas.map((f, idx) => {
                        const fam = _famFuente(f);
                        const txt = muestraGlobal.trim() ? muestraGlobal : MUESTRA_DEF;   // vacío = muestra por defecto
                        const porBorrar = fuenteABorrar === f.archivo;
                        return (
                          <div key={idx} onClick={() => { if (!porBorrar) setFuenteDetalle(f); }}
                            title="Ver todos los glifos y probar la fuente"
                            style={{ border: '1px solid ' + (porBorrar ? 'var(--danger, #ff4d4f)' : 'var(--border-light)'), borderRadius: 10, backgroundColor: 'rgba(0,0,0,0.1)', overflow: 'hidden', cursor: porBorrar ? 'default' : 'pointer' }}>
                            {/* encabezado: nombre interno (el que debe coincidir con el arte) + archivo */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, padding: '9px 14px', borderBottom: '1px solid var(--border-light)', background: 'rgba(255,255,255,0.03)' }}>
                              <div style={{ minWidth: 0 }}>
                                <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.interno}</div>
                                <div style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{f.archivo}</div>
                              </div>
                              {/* ELIMINAR: confirmación EN LA TARJETA (nada de diálogos del navegador).
                                  Borrar una fuente que un arte usa lo deja sin tipografía → se pregunta. */}
                              {porBorrar ? (
                                <div onClick={(e) => e.stopPropagation()} style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                                  <span style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>¿Eliminar?</span>
                                  <button type="button" onClick={() => eliminarFuente(f.archivo)} title="Confirmar"
                                    style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 9px', borderRadius: 6, cursor: 'pointer', border: 'none', background: 'var(--danger, #ff4d4f)', color: '#fff' }}>Sí</button>
                                  <button type="button" onClick={() => setFuenteABorrar(null)} title="Cancelar"
                                    style={{ fontSize: 10.5, fontWeight: 700, padding: '3px 9px', borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>No</button>
                                </div>
                              ) : (
                                <button type="button" onClick={(e) => { e.stopPropagation(); setFuenteABorrar(f.archivo); }} title="Eliminar esta fuente del catálogo"
                                  style={{ flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', width: 24, height: 24, borderRadius: 6, cursor: 'pointer', border: '1px solid var(--border-light)', background: 'transparent', color: 'var(--text-muted)' }}>
                                  <Icon name="trash" style={{ width: 12, height: 12 }} />
                                </button>
                              )}
                            </div>
                            {/* la muestra, en la tipografía REAL de esta fuente */}
                            <div style={{ fontFamily: `'${fam}', system-ui`, fontSize: 34, lineHeight: 1.25, padding: '14px 14px 16px',
                              color: 'var(--text-primary, #fff)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{txt}</div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* --- MODAL: Subir MI PROPIO MOLDE (desde el pedido) --- */}
      {/* Confirmar la eliminación de un artículo propio: borra el molde Y sus archivos, así que
          se pide confirmación explícita y se avisa que no se puede deshacer. */}
      <Modal open={!!borrarArt} onClose={() => setBorrarArt(null)} centrado maxWidth={430}
        titulo="Eliminar artículo">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text-secondary)' }}>
            Se va a eliminar <b style={{ color: '#fff' }}>{borrarArt?.nombre}</b> y todos sus
            archivos (molde, diseños y configuración). <b>No se puede deshacer.</b>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn ghost" style={{ flex: 1 }}
              onClick={() => setBorrarArt(null)}>Cancelar</button>
            <button type="button" className="btn" style={{ flex: 1, background: 'var(--danger, #ff5a6e)', color: '#fff' }}
              onClick={async () => {
                const id = borrarArt?.id; setBorrarArt(null);
                try {
                  const r = await fetch('/api/productos/eliminar', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id }),
                  });
                  const d = await r.json();
                  if (!r.ok) { showError(d.error || 'No se pudo eliminar'); return; }
                  await fetchProductos();
                  showMsg('Artículo eliminado ✓');
                } catch (e) { showError('No se pudo eliminar: ' + e.message); }
              }}>Eliminar</button>
          </div>
        </div>
      </Modal>

      <Modal open={subirMoldeOpen} onClose={() => { if (!subirMoldeBusy) setSubirMoldeOpen(false); }} centrado maxWidth={520}
        titulo="Subir mi propio molde"
        subtitulo="Queda en «Mis artículos», sólo para vos. Después indicás qué es cada pieza.">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 6, color: 'var(--text-secondary)' }}>Nombre del artículo</label>
            <input value={subirMoldeNombre} onChange={(e) => setSubirMoldeNombre(e.target.value)} autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter' && subirMoldeNombre.trim() && subirMoldeFile && !subirMoldeBusy) subirMiMolde(); }}
              placeholder="Ej. Remera de mi club"
              style={{ width: '100%', padding: '9px 11px', fontSize: 13.5, borderRadius: 9, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11.5, fontWeight: 700, marginBottom: 6, color: 'var(--text-secondary)' }}>Archivo del molde</label>
            {/* La zona se PINTA en verde cuando el archivo ya está elegido: sin eso, con archivo
                y sin archivo se veían casi igual y no quedaba claro que ya estaba cargado. */}
            <div className="upload-zone" onClick={() => !subirMoldeBusy && fileInputMiMoldeRef.current?.click()}
              style={{ padding: '22px 16px', cursor: subirMoldeBusy ? 'default' : 'pointer',
                       ...(subirMoldeFile ? { borderColor: 'var(--success, #2ecc71)', background: 'rgba(46,204,113,0.08)' } : {}) }}>
              {subirMoldeFile
                ? <div style={{ fontSize: 22, lineHeight: 1, color: 'var(--success, #2ecc71)' }}>✓</div>
                : <Icon name="upload" className="upload-icon" />}
              <div style={{ fontSize: 12.5, fontWeight: 700, color: subirMoldeFile ? 'var(--success, #2ecc71)' : undefined }}>
                {subirMoldeFile ? subirMoldeFile.name : 'Elegí el molde (.ai · .pdf · .dxf)'}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                {subirMoldeFile ? 'Archivo cargado · tocá para cambiarlo' : 'Illustrator, Corel/PDF o DXF (Optitex, Gerber…)'}
              </div>
            </div>
            <input type="file" ref={fileInputMiMoldeRef} accept=".ai,.pdf,.dxf" hidden
              onChange={(e) => { const f = e.target.files[0]; setSubirMoldeFile(f || null); if (f && !subirMoldeNombre.trim()) setSubirMoldeNombre((f.name || '').replace(/\.(ai|pdf|dxf)$/i, '')); e.target.value = ''; }} />
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Al subirlo se abre su configuración: ahí les ponés nombre a los {term.variante.toLowerCase()}s (si vinieron sin nombre) e indicás qué es cada pieza. Con eso ya se puede usar en el pedido.
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button type="button" className="btn ghost" disabled={subirMoldeBusy} onClick={() => setSubirMoldeOpen(false)}>Cancelar</button>
            {/* El botón se PINTA cuando ya está todo listo (archivo elegido + nombre): es la
                confirmación visual de que el archivo se cargó y se puede continuar. Apagado
                mientras falte algo, para que se vea qué falta en vez de un botón muerto. */}
            <button type="button" className={`btn ${subirMoldeFile && subirMoldeNombre.trim() ? 'success' : 'ghost'}`}
              disabled={subirMoldeBusy || !subirMoldeNombre.trim() || !subirMoldeFile}
              style={subirMoldeFile && subirMoldeNombre.trim() && !subirMoldeBusy
                ? { fontWeight: 700, boxShadow: '0 0 0 3px rgba(46,204,113,0.18)' } : { opacity: 0.55 }}
              onClick={subirMiMolde}>
              {subirMoldeBusy ? 'Subiendo…' : (subirMoldeFile && subirMoldeNombre.trim() ? '✓ Subir y configurar' : 'Subir y configurar')}
            </button>
          </div>
        </div>
      </Modal>

      {/* --- MODAL 1: Crear nuevo producto --- */}
      {creandoProducto && (
        <div className="modal-overlay" onClick={(e) => { if (e.target.classList.contains('modal-overlay')) setCreandoProducto(false); }}>
          <form className="modal-content" onSubmit={handleCrearProducto} style={{ maxWidth: 450 }}>
            <div className="modal-header">
              <h3>Crear Nuevo Molde</h3>
              <button type="button" className="quitar" style={{ border: 'none', background: 'none', fontSize: 24, cursor: 'pointer' }} onClick={() => setCreandoProducto(false)}>×</button>
            </div>
            
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Nombre del molde</label>
              <input
                type="text"
                value={nuevoProductoNombre}
                placeholder="Ej. Camiseta River, Buzo Capucha…"
                required 
                onChange={(e) => setNuevoProductoNombre(e.target.value)}
              />
            </div>
            
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button type="button" className="btn ghost" onClick={() => setCreandoProducto(false)}>Cancelar</button>
              <button type="submit" className="btn primary">Crear Molde</button>
            </div>
          </form>
        </div>
      )}

      {/* --- MODAL 4: Confirmación antes de Generar Sublimación --- */}
      {modalConfirmOpen && (
        <div className="modal-overlay" onClick={(e) => { if (e.target.classList.contains('modal-overlay')) setModalConfirmOpen(false); }}>
          <div className="modal-content" style={{ maxWidth: 480 }}>
            <div className="modal-header">
              <h3>Confirmar Tizada de Sublimación</h3>
              <button className="quitar" style={{ border: 'none', background: 'none', fontSize: 24, cursor: 'pointer' }} onClick={() => setModalConfirmOpen(false)}>×</button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>Molde a Utilizar</label>
                <select 
                  value={confirmProductoId}
                  onChange={(e) => setConfirmProductoId(e.target.value)}
                >
                  {productosCat.productos.map(p => (
                    <option key={p.id} value={p.id}>{p.nombre} {p.id === productosCat.activo ? "(Activo)" : ""}</option>
                  ))}
                </select>
              </div>

              <div style={{ border: '1px solid var(--border-light)', borderRadius: 12, padding: 14, backgroundColor: 'rgba(0,0,0,0.2)', fontSize: 13 }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>Resumen de producción:</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', marginBottom: 4 }}>
                  <span>Prendas a procesar</span>
                  <b>{filas.length}</b>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                  <span>Espaciado entre piezas</span>
                  <b>{(config?.espaciado_mm || 5)} mm</b>
                </div>
              </div>
              
              <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Se generarán los moldes vectoriales recortados por su contorno y se estamparán las personalizaciones en curvas en los archivos correspondientes.
              </p>
            </div>

            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button className="btn ghost" onClick={() => setModalConfirmOpen(false)}>Cancelar</button>
              <button className="btn primary" onClick={ejecutarGenerarSublimacion}>
                Confirmar e Iniciar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* --- MODAL: Piezas de un TIPO (Variables). Ventana emergente con la lista de
              piezas asignadas + botón para asignar en el visor. --- */}
      {modalTipoClave && (() => {
        const t = (variantesEdit || []).find(x => x.clave === modalTipoClave);
        if (!t) return null;
        const piezas = (t.valores || []).filter(v => v.pieza_idx != null).sort((a, b) => a.pieza_idx - b.pieza_idx);
        return createPortal(
          <div className="modal-overlay" onMouseDown={(e) => { if (e.target.classList.contains('modal-overlay')) setModalTipoClave(null); }}>
            <div className="modal-content" style={{ maxWidth: 560, display: 'flex', flexDirection: 'column', maxHeight: '85vh' }}>
              <div className="modal-header">
                <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
                  Piezas del grupo “{t.label || 'sin nombre'}”
                  <span style={{ fontSize: 12.5, color: 'var(--text-muted)', fontWeight: 400 }}>{piezas.length} pieza{piezas.length === 1 ? '' : 's'}</span>
                </h3>
                <button className="quitar" style={{ border: 'none', background: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setModalTipoClave(null)}>×</button>
              </div>
              <button type="button" className="btn primary" disabled={!etqData}
                onClick={() => { setModalTipoClave(null); setAsignandoTipo(t.clave); }}
                style={{ width: '100%', marginBottom: 14, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, opacity: etqData ? 1 : 0.5 }}>
                <Icon name="edit" style={{ width: 15, height: 15 }} /> Asignar piezas en el visor
              </button>
              <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6, paddingRight: 2 }}>
                {piezas.length === 0 ? (
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: '22px 0', lineHeight: 1.6 }}>
                    Todavía no hay piezas en este tipo.<br />Tocá <b>“Asignar piezas en el visor”</b> y elegilas tocándolas.
                  </div>
                ) : piezas.map(v => (
                  <div key={v.id} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 11.5, fontWeight: 800, color: '#18181b', background: 'var(--success)', borderRadius: 6, minWidth: 28, height: 26, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{v.pieza_idx + 1}</span>
                    <input value={v.label} placeholder="Nombre de la pieza" onChange={(e) => renombrarPieza(v.pieza_idx, e.target.value)}
                      style={{ flex: 1, padding: '8px 11px', fontSize: 13, borderRadius: 8, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--border-light)', color: '#fff', outline: 'none' }} />
                    <button title="Quitar de este grupo" onClick={() => quitarPiezaDeGrupo(t.clave, v.pieza_idx)}
                      style={{ width: 34, height: 34, flexShrink: 0, borderRadius: 8, border: '1px solid rgba(248,113,113,0.3)', background: 'transparent', color: '#f87171', cursor: 'pointer', fontSize: 15 }}>✕</button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border-light)' }}>
                <button className="btn ghost" onClick={() => setModalTipoClave(null)}>Cerrar</button>
                <button className="btn primary" onClick={() => guardarGrupos()}>Guardar grupo</button>
              </div>
            </div>
          </div>,
          document.body
        );
      })()}

      {/* --- MODAL: Selector de variante (Talle de Guía) en botones cuadrados --- */}
      {modalTalleGuiaOpen && etqData && (
        <div className="modal-overlay" onClick={(e) => { if (e.target.classList.contains('modal-overlay')) setModalTalleGuiaOpen(false); }}>
          <div className="modal-content" style={{ maxWidth: 560 }}>
            <div className="modal-header">
              <h3>{term.variante} de Guía</h3>
              <button type="button" className="quitar" style={{ border: 'none', background: 'none', fontSize: 24, cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setModalTalleGuiaOpen(false)}>×</button>
            </div>
            <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 18 }}>
              Elegí con qué {term.variante.toLowerCase()} querés ver y etiquetar el molde.
            </p>
            <div className="talle-grid">
              {/* las variantes REALES del molde: `talles` puede ser el de la vista «por piezas»
                  (las capas del archivo original), donde la única opción sería «Capa 1» */}
              {tallesMolde.map(t => (
                <button
                  key={t}
                  type="button"
                  className={`talle-square ${(etqData.guia || etqData.talle_ref) === t ? 'active' : ''}`}
                  onClick={() => { cambiarTalleGuia(t); setModalTalleGuiaOpen(false); }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Lightbox de Previsualización Vectorial */}
      {zoomPreviewUrl && (
        <div 
          className="modal-overlay" 
          style={{ 
            position: 'fixed', 
            top: 0, 
            left: 0, 
            width: '100vw', 
            height: '100vh', 
            backgroundColor: 'rgba(0, 0, 0, 0.85)', 
            backdropFilter: 'blur(8px)',
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            zIndex: 3000,
            animation: 'fadeIn 0.2s ease-out',
            padding: 20
          }}
        >
          <div className="card animate-fade" style={{ width: '92vw', height: '92vh', padding: 20, display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-dark)', border: '1px solid var(--border-light)' }}>
            
            {/* Header / Barra de Controles */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontWeight: 700, fontSize: 15 }}>Vista Previa Vectorial</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Mesa de Tizada</span>
              </div>
              
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <button 
                  className="btn secondary" 
                  style={{ padding: '6px 12px', fontSize: 12 }} 
                  onClick={() => handleZoom(zoomLevel / 1.15)}
                >
                  Zoom -
                </button>
                <span style={{ fontFamily: 'monospace', fontSize: 13, minWidth: 55, textAlign: 'center', fontWeight: 'bold' }}>
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button 
                  className="btn secondary" 
                  style={{ padding: '6px 12px', fontSize: 12 }} 
                  onClick={() => handleZoom(zoomLevel * 1.15)}
                >
                  Zoom +
                </button>
                <button 
                  className="btn secondary" 
                  style={{ padding: '6px 12px', fontSize: 12 }} 
                  onClick={() => handleZoom(1.0)}
                >
                  Restablecer
                </button>
                <button 
                  className="btn" 
                  style={{ padding: '6px 12px', fontSize: 12, backgroundColor: 'var(--error)', color: '#fff', marginLeft: 10 }} 
                  onClick={() => {
                    setZoomPreviewUrl(null);
                    handleZoom(1.0);
                    setEsArrastrando(false);
                    isDraggingRef.current = false;
                  }}
                >
                  Cerrar
                </button>
              </div>
            </div>
            
            {/* Contenedor del Visor */}
            <div 
              ref={viewerRef}
              style={{ 
                flex: 1, 
                overflow: 'hidden', 
                border: '1px solid var(--border-light)', 
                borderRadius: 8, 
                backgroundColor: 'rgba(0,0,0,0.6)', 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center',
                padding: 20,
                position: 'relative',
                cursor: esArrastrando ? 'grabbing' : 'grab',
                userSelect: 'none'
              }}
              onMouseDown={(e) => {
                if (zoomLevel <= 1.0) return; // Disable drag/pan when zoom is 1.0
                if (e.button === 2) {
                  isDraggingRef.current = true;
                  dragStartRef.current = { x: e.clientX, y: e.clientY };
                  setEsArrastrando(true);
                  e.preventDefault();
                }
              }}
              onMouseMove={(e) => {
                if (zoomLevel <= 1.0) return; // Disable drag/pan when zoom is 1.0
                if (isDraggingRef.current) {
                  const dx = e.clientX - dragStartRef.current.x;
                  const dy = e.clientY - dragStartRef.current.y;
                  setZoomState(prev => ({
                    ...prev,
                    pan: { x: prev.pan.x + dx, y: prev.pan.y + dy }
                  }));
                  dragStartRef.current = { x: e.clientX, y: e.clientY };
                }
              }}
              onMouseUp={(e) => {
                if (e.button === 2) {
                  isDraggingRef.current = false;
                  setEsArrastrando(false);
                }
              }}
              onMouseLeave={() => {
                isDraggingRef.current = false;
                setEsArrastrando(false);
              }}
              onContextMenu={(e) => e.preventDefault()}
              onWheel={(e) => {
                e.preventDefault();
                const zoomFactor = 1.15;
                const nextScale = e.deltaY < 0 ? zoomLevel * zoomFactor : zoomLevel / zoomFactor;
                handleZoom(nextScale, e.clientX, e.clientY);
              }}
            >
              <style>{`
                .viewer-svg-container svg {
                  max-width: 85vw !important;
                  max-height: 80vh !important;
                  width: auto !important;
                  height: auto !important;
                  display: block !important;
                }
              `}</style>
              
              {zoomSvgContent ? (
                <div 
                  className="viewer-svg-container"
                  dangerouslySetInnerHTML={{ __html: zoomSvgContent }} 
                  style={{ 
                    transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
                    transformOrigin: 'center center', 
                    display: 'inline-block', 
                    boxShadow: '0 8px 30px rgba(0,0,0,0.7)',
                    borderRadius: 4,
                    backgroundColor: 'white',
                    transition: 'none',
                    pointerEvents: 'none',
                    userSelect: 'none'
                  }} 
                />
              ) : (
                <div style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
                  Cargando vista previa vectorial...
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
