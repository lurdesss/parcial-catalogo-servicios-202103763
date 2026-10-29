# Prompt 14b — Datos de demostración de Service Desk (v2, actor por acción)

- **N.º / tema:** colas / datos de demostración — ≥7 colas, ≥35 tickets
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** corregir el fallo del Prompt 14a sin debilitar el control de permisos (no usar `admin` para todo, que
  ocultaría si el modelo de permisos por cola realmente funciona).
- **Contexto suministrado:** el error real de 14a; `app/security.py::queue_permission`.
- **Instrucciones:** "Permite que `_advance` reciba un actor por defecto más overrides por acción, de modo que el
  aprobador actúe solo donde su permiso aplica (`aprobar`/`rechazar`) y el resto de la secuencia la ejecute un actor
  con `can_work`."
- **Restricciones:** las mismas de 14a; además, seguir siendo idempotente tras el cambio.
- **Salida esperada:** `_advance(ticket, default_actor, *actions, overrides=None)` en `app/seed_servicedesk.py`.
- **Criterio de aceptación:** `flask seed-servicedesk-demo` termina con código 0, reporta ≥35 tickets creados, y
  repetirlo reporta 0 tickets nuevos.
- **Resultado real y observaciones:** `Service Desk demo: 7 colas, 35 tickets nuevos creados.` en la primera corrida;
  `7 colas, 0 tickets nuevos creados.` en la segunda (idempotente). Verificado además el conteo real por tabla:
  38 tickets totales (35 de la siembra + 3 incidentes auto-creados por eventos E2/E3), 3 incidentes con
  `linked_incident_id` no nulo en `ticket_event_details`, 2 `ServiceL2` creados por aprobaciones de `nuevos_servicios`,
  120 filas en `ticket_history`.
- **Iteración:** prompt inicial (14a, con el 403 real) → problema observado → prompt revisado (este) → resultado
  comprobado con conteos reales de base de datos, no solo con el mensaje del comando.
