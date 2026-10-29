# Prompt 15 — Pruebas P03–P18 y verificación con el harness existente

- **N.º / tema:** pruebas / Docker — cobertura P03–P18 reutilizando el harness de Parcial 2
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** automatizar los escenarios P03–P18 del enunciado §11 siguiendo el patrón ya establecido en
  `tests/conftest.py` (fixtures de cliente con CSRF automático), sin introducir un segundo framework de pruebas.
- **Contexto suministrado:** `tests/conftest.py`, `tests/test_org.py` y `tests/test_auth.py` de Parcial 2 como
  referencia de estilo; enunciado §11 con la lista completa P01–P18.
- **Instrucciones:** "Agrega fixtures de cliente para solicitante/agente/aprobador; siembra `reference_data.seed_orm()`
  después de `db.create_all()` porque las pruebas no pasan por Alembic. Cada archivo nuevo cubre los P-números que le
  correspondan, nombrados `test_P<NN>_…` igual que en Parcial 2."
- **Restricciones:** no debe requerir Postgres ni Docker para correr localmente (debe funcionar sobre SQLite, igual
  que las pruebas de Parcial 2); la concurrencia (P07) debe probarse con hilos reales, no simulada.
- **Salida esperada:** `tests/test_cmdb.py`, `test_queues.py`, `test_tickets.py`, `test_processes.py`,
  `test_dashboard.py`; `test_persistence.py` extendido a P18.
- **Criterio de aceptación:** `pytest -q` completo sale con código 0; `ruff check .` sin errores.
- **Resultado real y observaciones:** `pytest -q` → **58 passed** (ver desglose en el Prompt 11); `ruff check .` →
  `All checks passed`. La verificación completa con Docker (`docker compose --profile test run --rm --build tests`,
  `scripts/setup_eval.sh`, `scripts/persistence_check.sh`) quedó pendiente porque el daemon de Docker Desktop no
  estaba activo en el equipo durante esta sesión (`docker ps` → "no se pudo conectar al API de Docker"); documentado
  como paso pendiente en `docs/PRUEBAS.md` y `docs/RESOLUCION.md`, a ejecutar antes de la entrega.
