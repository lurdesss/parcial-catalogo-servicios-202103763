#!/bin/sh
# Controles de calidad y pruebas. Código de salida != 0 si algo falla.
set -eu
echo "== ruff (calidad) =="
ruff check .
echo "== pytest (P01-P12 y apoyo) =="
python -m pytest -q
echo "== CONTROLES OK =="
