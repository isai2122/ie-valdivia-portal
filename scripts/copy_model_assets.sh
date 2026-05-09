#!/usr/bin/env bash
# Copia los PNG del modelo (entregables del notebook v2.1) al bundle estático.
set -euo pipefail
SRC="/app/uploads/project/Proyecto_MetanoSRGAN/produccion/resultados"
DEST="/app/frontend/public/assets/model"
mkdir -p "$DEST"
cp "$SRC/training_curve.png"     "$DEST/training_curve.png"
cp "$SRC/comparacion_visual.png" "$DEST/comparacion_visual.png"
echo "✓ Assets del modelo copiados a $DEST"
