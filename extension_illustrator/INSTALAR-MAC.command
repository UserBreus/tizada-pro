#!/bin/bash
# USER PRO para Illustrator - instalador (Mac). Doble click; si el Mac no lo deja abrir:
# click derecho > Abrir.
DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/Application Support/Adobe/CEP/extensions/com.tizadapro.illustrator"
echo "Instalando USER PRO para Illustrator..."
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$DIR/com.tizadapro.illustrator/." "$DEST/" || { echo "No se pudo copiar la extension."; exit 1; }
for v in 9 10 11 12 13 14 15 16; do defaults write "com.adobe.CSXS.$v" PlayerDebugMode 1; done
echo ""
echo "Listo. Cerra Illustrator (si esta abierto) y volve a abrirlo."
echo "En Illustrator: Ventana > Extensiones > USER PRO muestra si esta conectada."
