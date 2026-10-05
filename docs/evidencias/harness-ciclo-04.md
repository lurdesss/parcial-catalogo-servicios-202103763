# Ciclo de harness 04 — Validación en Docker

- **Tarea:** validar la aplicación con Docker (pendiente desde los ciclos anteriores, que se hicieron sin Docker).
- **Cambio:** ninguno en el código; se ejecutaron los controles del README en Docker 29.7.2 / Compose v5.4.0 (Windows 11) el 2026-10-04.
- **Control 1:** `docker compose --profile test run --rm --build tests` → All checks passed, 31 passed, exit 0.
- **Fallo observado:** `docker compose exec -T app python scripts/smoke.py flow` y `sh scripts/persistence_check.sh` fallaron con `AssertionError: No se pudo iniciar sesión como admin`.
- **Causa:** se ejecutaron antes de `sh scripts/setup_eval.sh`; las cuentas `EVAL_ADMIN_USER`/`EVAL_VIEWER_USER` todavía no existían. No es un defecto del código sino del orden de pasos.
- **Corrección:** ejecutar `sh scripts/setup_eval.sh` (creó admin_demo y consulta_demo; importación 58 creados, N1=12, N2=46, coincide=true). El README ya indica ese orden.
- **Nueva ejecución:** `smoke.py flow` con `EXPECT_REAL_CONTROL=1` → todos OK (12/46, segunda importación idempotente); `persistence_check.sh` → P12 OK tras `docker compose restart`.
- **Lección para el contexto:** `smoke.py` y `persistence_check.sh` dependen de `setup_eval.sh`; se anota en `AGENTS.md`.
