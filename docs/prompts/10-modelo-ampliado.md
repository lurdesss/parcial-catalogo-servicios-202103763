# Prompt 10 — Modelo de datos ampliado (CMDB + Service Desk)

- **N.º / tema:** modelo — 25 tablas nuevas, aditivas sobre el esquema de Parcial 2
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** diseñar e implementar en `app/models.py` las entidades de CMDB (`ci_classes`, `locations`, `devices`,
  `device_relations`, `service_ci_links`) y Service Desk (`processes`, `process_states`, `process_transitions`,
  `queues`, `queue_permissions`, `tickets` + 6 tablas de detalle por proceso, `ticket_ci_links`, `ticket_relations`,
  `ticket_comments`, `ticket_attachments`, `ticket_history`), generando la migración correspondiente.
- **Contexto suministrado:** `app/models.py` existente (Parcial 2), enunciado §4–§8, `docs/contexto/04-parcial3-alcance.md`.
- **Instrucciones:** "Agrega los modelos nuevos sin alterar ninguna tabla existente (todo debe ser `CREATE TABLE`, sin
  `ALTER`), usando `sa.JSON` genérico (no `postgresql.JSONB`) para que las pruebas sigan corriendo sobre SQLite.
  Genera la migración con `alembic revision --autogenerate` contra una base SQLite limpia y revísala a mano."
- **Restricciones:** nada de columnas con tipos específicos de un solo motor; CHECK constraints explícitos para los
  enumerados (categoría de incidente/evento, tipo de cambio, visibilidad de comentario, etc.).
- **Salida esperada:** `app/models.py` ampliado + `migrations/versions/0002_service_desk_cmdb.py`.
- **Criterio de aceptación:** `alembic upgrade head` sin error sobre SQLite limpio; `db.create_all()` configura todas
  las relaciones sin `InvalidRequestError` (claves foráneas ambiguas).
- **Resultado real y observaciones:** varias tablas tienen más de una clave foránea hacia `tickets.id` (p. ej.
  `ticket_relations.ticket_id`/`related_ticket_id`, `ticket_problem_details.linked_incident_id`/`linked_change_id`);
  se declaró `foreign_keys=` explícito en cada `relationship()` afectada **antes** de ejecutar nada, para evitar el
  error típico de SQLAlchemy "relación ambigua" (`AmbiguousForeignKeysError`). Verificado: `db.create_all()` configuró
  las 37 tablas sin error en la primera ejecución real; `alembic upgrade head` aplicó 0001+0002 sobre SQLite limpio y
  sembró 7 procesos, 44 estados, 43 transiciones, 17 clases de CI y 5 ubicaciones.
