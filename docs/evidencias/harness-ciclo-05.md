# Ciclo de harness 05 — `service_l2_id` obligatorio rompía `nuevos_servicios`

- **Tarea:** construir `app/seed_servicedesk.py` para sembrar ≥35 tickets de demostración (5 por proceso).
- **Cambio propuesto:** `ticket_engine.create_ticket` exigía `service_l2_id` para todo proceso salvo `accesos`
  (`service_required = process_code != "accesos"`), siguiendo el enunciado §4 ("cada ticket tendrá como mínimo…
  servicio de nivel 2").
- **Control:** `flask seed-servicedesk-demo` (CLI real, contra SQLite local).
- **Fallo observado:**
  ```
  app.errors.ApiError: Hay datos inválidos; revise los campos indicados.
  ```
  al intentar crear el primer ticket `[DEMO] Nuevo servicio #1` (proceso `nuevos_servicios`).
- **Causa:** el proceso "Gestión de nuevos servicios" **propone un servicio que todavía no existe en el catálogo**
  (`TicketNewServiceDetail.proposed_name`/`proposed_level1_id`); exigir un `service_l2_id` ya existente es
  contradictorio con el propio proceso. El enunciado habla del caso general; `nuevos_servicios` es la excepción
  obligada por su propia naturaleza (igual que `accesos`, que ya estaba exceptuado).
- **Corrección:** `service_required = process_code not in ("accesos", "nuevos_servicios")` en
  `app/ticket_engine.py::create_ticket`.
- **Nueva ejecución:** `flask seed-servicedesk-demo` → `Service Desk demo: 7 colas, 35 tickets nuevos creados.`
  (incluye los 5 de `nuevos_servicios`, 2 de ellos aprobados y con un `ServiceL2` creado/vinculado).
- **Lección para el contexto:** agregada a `AGENTS.md` §5 (v8 en `docs/contexto/CAMBIOS.md`, commit `8eb3d95`).
