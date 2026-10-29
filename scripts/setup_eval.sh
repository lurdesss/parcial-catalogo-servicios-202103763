#!/bin/sh
# Migraciones (ya aplicadas por el entrypoint), cuentas de evaluación (5 roles), importación
# del catálogo, generación reproducible de la CMDB (>=5000 CI) y datos de demostración de
# Service Desk (colas, permisos, >=35 tickets). Todo es repetible sin duplicar (ver docs/PRUEBAS.md).
set -eu
docker compose exec -T app alembic upgrade head
docker compose exec -T app flask create-eval-users
docker compose exec -T app flask import-catalog
docker compose exec -T app flask seed-demo
docker compose exec -T app flask generate-cmdb --seed 42 --count 5000
docker compose exec -T app flask seed-servicedesk-demo
