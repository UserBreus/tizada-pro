# USER · Motor de Sublimación — instalación en tu PC (Windows)

## Instalar (una sola vez)
1. Instalá Python 3.11 o superior desde https://www.python.org/downloads/
   ⚠ En el instalador, marcá la casilla **"Add Python to PATH"**.
2. Abrí la carpeta `motor_web`, hacé clic en la barra de dirección del
   Explorador, escribí `cmd` y Enter. En la ventana negra:
       pip install -r requirements.txt
   (tarda unos minutos la primera vez)

## Usar (cada día)
1. Doble clic en `iniciar.bat` (dejá la ventana negra abierta).
2. Abrí el navegador en  http://localhost:8050
3. Pestaña **Producto y diseño** (la primera vez):
   - Subí la plantilla base (.ai) → el sistema registra piezas y talles.
   - Subí las tipografías (.ttf): IMPACT.TTF, ARIALBD.TTF
     (están en C:\Windows\Fonts — copialas al escritorio para poder subirlas).
   - Subí el arte del cliente (.ai) → validación automática con checklist.
4. Pestaña **Pedidos**: cargá talle, nombre, número y manga por prenda
   → **Generar sublimación** → en ~40 s aparecen las hojas con sus
   validaciones, previews y links de descarga.

## Dónde quedan los archivos
- `trabajos/<id>/HOJA_Principal.pdf` y `HOJA_RIB.pdf` → directo al RIP.
- `entrada/` plantilla y arte vigentes · `catalogo_fuentes/` tipografías.

## Si algo falla
- "python no se reconoce…" → reinstalá Python marcando *Add to PATH*.
- El puerto 8050 está ocupado → iniciá con otro puerto sin editar código:
  en la ventana negra escribí  `set PORT=8001`  y luego  `py servidor.py`.
- La ventana negra muestra el detalle de cualquier error: mandámelo.

Validaciones automáticas de cada trabajo: texto en curvas (cero fuentes),
balance de streams (compatibilidad Acrobat), espaciado ≥ 5 mm entre bordes,
tintas planas presentes. Si alguna da ✗, no mandes la hoja al plotter.
