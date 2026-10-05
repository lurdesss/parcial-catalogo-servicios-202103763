#!/bin/sh
# Espera a la base de datos (reintentos) y aplica migraciones antes de arrancar el servidor.
set -eu
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "[entrypoint] Aplicando migraciones..."
  i=0
  until alembic upgrade head; do
    i=$((i + 1))
    if [ "$i" -ge 20 ]; then echo "[entrypoint] La base de datos no estuvo disponible a tiempo" >&2; exit 1; fi
    echo "[entrypoint] Reintento $i/20 en 2 s..."
    sleep 2
  done
fi
exec "$@"
