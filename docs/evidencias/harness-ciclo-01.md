# Harness — ciclo 01: expectativa errónea en prueba P11 (fallo NO deliberado)

- **Herramienta / modelo:** Claude (claude.ai, Claude Sonnet 5.5) · **Fecha:** 2026-10-04
- **Tarea:** implementar la política de bajas lógicas y la regla P11 (responsable de la sección correcta) con sus pruebas.
- **Cambio propuesto por la IA:** `app/api/org.py` (`deactivate_tree`), `app/api/services.py` (`_l2_values`) y `tests/test_services.py::test_P11…`.
- **Control ejecutado:** `python -m pytest -x -q`
- **Fallo detectado (salida literal, recortada):**
  ```
  >       assert r.status_code == 409 and r.get_json()["error"]["code"] == "has_services"
  E       AssertionError: assert (409 == 409 and 'has_dependents' == 'has_services'
  FAILED tests/test_services.py::test_P11_responsable_debe_pertenecer_a_la_seccion
  1 failed, 26 passed, 1 skipped
  ```
- **Diagnóstico (decisión humana/IA):** el servidor era correcto según la política (§Bajas, regla 2 antes de la 3): la sección tiene un puesto con usuarios activos, por lo que responde `has_dependents` primero. El error estaba en la expectativa de la prueba.
- **Corrección:** la prueba ahora verifica `has_dependents` sin cascada y `has_services` (con el código `SE.01.1` en el mensaje) con `?cascade=true`.
- **Nueva ejecución:** `python -m pytest -q` → `29 passed, 1 skipped`; `ruff check .` → `All checks passed!`
- **Commit de la corrección:** sin SHA propio: corrección anterior a la inicialización de Git, publicada en el primer commit completo
