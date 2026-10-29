# Prompt 12 — Motor de tickets y los 7 procesos (Grafo 2)

- **N.º / tema:** procesos — flujo de estados de cada uno de los 7 procesos obligatorios
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** modelar los 7 procesos (enunciado §6) como un grafo de estados/transiciones genérico y reutilizable
  (no un formulario distinto con el nombre cambiado por proceso), con las reglas propias de cada uno: aprobación
  obligatoria antes de ejecutar un cambio, anti-autoaprobación en accesos, vínculo evento→incidente sin duplicar,
  problema→cambio, nuevo servicio→crea o vincula el catálogo sin duplicarlo.
- **Contexto suministrado:** enunciado §4–§7 completo; `docs/contexto/04-parcial3-alcance.md`.
- **Instrucciones:** "Diseña `process_states`/`process_transitions` como datos (no si/else por proceso en el código);
  un motor genérico (`app/workflow.py`) debe validar cualquier transición contra ese grafo. Las reglas específicas de
  cada proceso van en una función de efectos separada del motor genérico."
- **Restricciones:** ningún salto de estado fuera de una arista explícita del grafo; los permisos de cada transición
  deben evaluarse contra la cola del ticket, no contra un rol fijo en el código.
- **Salida esperada:** `app/reference_data.py` (TRANSITIONS por proceso), `app/workflow.py` (motor genérico),
  `app/ticket_engine.py` (reglas específicas).
- **Criterio de aceptación:** `tests/test_tickets.py::test_P09…` recorre la ruta completa de los 7 procesos y verifica
  que una acción inexistente se rechaza con `invalid_transition`.
- **Resultado real y observaciones:** implementado según lo pedido. `GET /api/processes/<code>/grafo` expone el mismo
  grafo que usa el motor, para que la UI y la defensa puedan mostrarlo tal como lo aplica el servidor (no una
  descripción aparte que podría desincronizarse). Verificado: `test_P09…` recorre los 7 procesos con éxito y confirma
  que, tras cerrar un ticket, una acción inventada se rechaza con 409 `invalid_transition`.
