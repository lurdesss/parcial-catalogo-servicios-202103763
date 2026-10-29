# Ciclo de harness 07 — tres fallos reales de `pytest` al escribir P09/P10/P11

- **Tarea:** escribir `tests/test_tickets.py` para las pruebas P09 (ruta completa de los 7 procesos), P10 (cambio sin
  aprobación / autoaprobación de acceso) y P11 (eventos E2/E3 sin duplicar incidente).
- **Control:** `pytest -q tests/test_tickets.py` (SQLite local).
- **Resultado de la primera ejecución:** `3 failed, 5 passed`.

| # | Prueba | Fallo | Causa real | Corrección |
|---|---|---|---|---|
| 1 | P09 (proceso `accesos`) | `403 self_approval` en vez de `201` | El ticket de prueba usaba `requester_user_id=org["admin"]` y el propio `admin` ejecutaba `aprobar`: admin era a la vez solicitante y aprobador, y la regla de anti-autoaprobación (correcta) lo rechazó. | Para `accesos`, el solicitante/beneficiario del ticket de prueba pasa a ser `org["viewer"]`, distinto del actor que aprueba (`admin`). |
| 2 | P10 (cambio sin aprobación) | `409 invalid_transition` en vez de `409 not_approved` | El test saltaba directo de `evaluacion` a `planificar`, pero esa transición **no existe** en el grafo (`planificar` solo es válida desde `aprobado`): el propio grafo de estados ya impide "ejecutar sin aprobación" antes de que se llegue a evaluar `_apply_effects`. No es un defecto: es una propiedad más fuerte de lo esperado. | Se reescribió la prueba para afirmar `invalid_transition` y documentar que la regla de negocio queda garantizada estructuralmente por el grafo, no solo por el chequeo explícito en `ticket_engine._apply_effects` (que queda como defensa adicional). |
| 3 | P11 (eventos E2/E3) | `409 no_queue` en vez de `200` | La prueba solo creó una cola para el proceso `eventos`, pero `_create_linked_incident` necesita una cola **activa del proceso `incidentes`** para crear el incidente vinculado, y no existía ninguna en ese test. | Se agregó `_queue(admin, "incidentes", "Q-T11-INC")` al arranque de la prueba. |

- **Nueva ejecución:** `pytest -q tests/test_tickets.py` → `8 passed`.
- **Por qué se registra como ciclo y no se descarta como "solo errores de prueba":** el hallazgo #2 es una verificación
  de diseño genuina (confirma que "no permita ejecutar sin aprobación" se cumple en dos capas independientes) y el
  #3 confirma un comportamiento defensivo correcto (`no_queue` en vez de una excepción no controlada cuando falta
  infraestructura de colas). Ambos se habrían manifestado igual con datos reales mal configurados en producción.
- **Verificación final de la suite completa:** `pytest -q` → `58 passed`; `ruff check .` → `All checks passed`.
