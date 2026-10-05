#!/bin/sh
# P12: reinicia contenedores SIN borrar volúmenes y comprueba que los datos persisten. Solo requiere Docker Compose.
set -eu
docker compose exec -T app python scripts/smoke.py marker-write
docker compose restart
echo "Esperando a que la aplicación vuelva a responder..."
i=0
until docker compose exec -T app python scripts/smoke.py health >/dev/null 2>&1; do
  i=$((i + 1)); [ "$i" -ge 30 ] && { echo "La aplicación no volvió a responder" >&2; exit 1; }
  sleep 2
done
docker compose exec -T app python scripts/smoke.py marker-verify
echo "P12 OK: los datos persisten tras reiniciar (volumen pgdata intacto)."
