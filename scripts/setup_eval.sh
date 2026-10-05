#!/bin/sh
# Migraciones (ya aplicadas por el entrypoint), importación, cuentas de evaluación y asignaciones demo.
set -eu
docker compose exec -T app alembic upgrade head
docker compose exec -T app flask create-eval-users
docker compose exec -T app flask import-catalog
docker compose exec -T app flask seed-demo
