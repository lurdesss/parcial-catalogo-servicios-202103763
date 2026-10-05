# Harness — ciclo 03: bloqueo en PostgreSQL que SQLite no revelaba (fallo NO deliberado)

- **Herramienta / modelo:** Claude (claude.ai, Claude Sonnet 5.5) · **Fecha:** 2026-10-04
- **Tarea:** comprobar que la suite funciona sobre PostgreSQL 16 (motor preferido) y no solo sobre SQLite.
- **Control ejecutado:** `TEST_DATABASE_URL=postgresql+psycopg://…/catalogo_test python -m pytest -q`
- **Fallo detectado:** la ejecución superó el límite de 300 s (colgada). Se acotó por archivo con `timeout 90`:
  ```
  tests/test_auth.py exit=0 · test_org.py exit=0 · test_services.py exit=0 · test_import.py exit=0
  tests/test_persistence.py exit=124      <-- tiempo agotado
  ```
- **Diagnóstico:** `test_P12` hacía `db.drop_all()` con la sesión aún dentro de la transacción del `SELECT` previo; en PostgreSQL `DROP TABLE` espera ese bloqueo (se bloquea contra sí mismo). SQLite lo toleraba.
- **Corrección:** `db.session.remove()` antes de `db.drop_all()` (regla en `AGENTS.md`, contexto v3).
- **Nueva ejecución:**
  - PostgreSQL 16 → `29 passed, 1 skipped in 11.79s`
  - SQLite → `29 passed, 1 skipped in 9.78s`
- **Entorno de esta comprobación:** PostgreSQL 16 instalado con apt en el sandbox (no Docker). **Pendiente:** repetirlo con `docker compose --profile test run --rm --build tests`.
- **Commit:** sin SHA propio: corrección anterior a la inicialización de Git, publicada en el primer commit completo
