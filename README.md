# Motor de Sublimación — USER

Aplicación web local que convierte la moldería y el arte de Illustrator (`.ai`)
en **hojas listas para el plotter** (`HOJA_Principal.pdf` / `HOJA_RIB.pdf`),
con el texto en curvas, las piezas anidadas por su contorno real y todas las
validaciones de imprenta hechas automáticamente.

---

## Qué hace

1. **Plantilla (molde).** Lee un `.ai` con la moldería y registra cada pieza y
   talle (contorno + etiqueta). → pestaña *Producto y diseño · paso 1*.
2. **Arte.** Valida el diseño del cliente contra la plantilla (estructura, capas,
   tintas planas, cobertura, tipografías, placeholders). → *paso 2*.
3. **Tipografías.** Catálogo por nombre interno; el texto del pedido se entrega
   en curvas (cero fuentes vivas en la salida). → *paso 3*.
4. **Pedido.** Cargás talle, nombre, número y manga por prenda; el motor genera
   cada pieza (clip del contorno sobre el arte, borde de corte, etiqueta y
   personalización), **anida** por contorno real y exporta las hojas con sus
   previews y validaciones. → pestaña *Pedidos*.

---

## La regla clave de la plantilla

> **Una mesa de trabajo por pieza. Todos los talles como capas dentro de esa
> misma mesa. Cada capa de talle con un texto `TALLE-Pieza-#`.**

La guía completa, con los nombres exactos de talles, piezas y capas, está en
**[`CONVENCION_PLANTILLA.md`](CONVENCION_PLANTILLA.md)**. Al subir la plantilla,
la app muestra pieza por pieza qué detectó y **te dice exactamente qué corregir**
si algo no cumple la convención.

---

## Instalación (una vez)

1. Instalá **Python 3.11+** desde <https://www.python.org/downloads/>
   (marcá *“Add Python to PATH”*).
2. Abrí la carpeta `motor_web` en una terminal y ejecutá:
   ```
   pip install -r requirements.txt
   ```

## Uso (cada día)

1. Doble clic en **`iniciar.bat`** (dejá la ventana abierta).
2. Abrí el navegador en <http://localhost:8050>.
3. *Producto y diseño* (la primera vez): subí plantilla, tipografías y arte.
4. *Pedidos*: cargá las prendas → **Generar sublimación**.

Las hojas quedan en `trabajos/<id>/`. Más detalle de instalación en
[`INSTRUCCIONES.md`](INSTRUCCIONES.md).

---

## Estructura del proyecto

```
motor_web/
├── servidor.py             API web (Flask) y endpoints
├── motor_pedido.py         alta de plantilla, validación de arte, generación del pedido
├── molde_real.py           extracción de contornos por capa/talle + limpieza de capas
├── nesting_contorno.py     anidado true-shape (por silueta) y composición de hojas
├── texto_curvas.py         texto → trazados vectoriales (sin fuentes vivas)
├── static/index.html       interfaz web
├── datos/                  registros y configuración generados (config_producto.json, …)
├── entrada/                plantilla.ai y arte.ai vigentes
├── catalogo_fuentes/       tipografías subidas
└── trabajos/<id>/          salida de cada pedido (HOJA_*.pdf, previews, pedido.json)
```

---

## Validaciones automáticas de cada hoja

- **Texto en curvas** — cero fuentes vivas (ninguna sustitución posible en el RIP).
- **Balance de streams** — compatibilidad con Acrobat (sin `q/Q` huérfanos).
- **Espaciado mínimo** — ≥ 5 mm de borde a borde entre piezas.
- **Tintas planas** — separaciones presentes según el arte.

Si alguna da ✗, no mandes la hoja al plotter.

---

## Problemas comunes

| Síntoma | Solución |
|---|---|
| `python no se reconoce…` | Reinstalá Python marcando *Add to PATH*. |
| El puerto 8050 está ocupado | Iniciá con otro puerto sin tocar el código: `set PORT=8001` y luego `py servidor.py` (o `PORT=8001 py servidor.py`). |
| “falta plantilla registrada o arte aprobado” | Subí ambos en *Producto y diseño* y revisá los ✗. |
| Una pieza aparece “repartida en varias mesas” | Pasá todos sus talles a **una sola** mesa (ver convención). |

La ventana negra muestra el detalle de cualquier error del servidor.
