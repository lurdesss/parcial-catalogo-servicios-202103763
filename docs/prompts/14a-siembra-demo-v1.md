# Prompt 14a — Datos de demostración de Service Desk (v1, actor único por secuencia)

- **N.º / tema:** colas / datos de demostración — ≥7 colas, ≥35 tickets
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** sembrar 7 colas (una por proceso), sus permisos y ≥35 tickets (5 por proceso) en distintos estados,
  incluyendo eventos E0–E3 e incidentes I0–I6 (enunciado §11).
- **Contexto suministrado:** `app/ticket_engine.py`, cuentas de evaluación de los 5 roles.
- **Instrucciones:** "Para cada ticket de demostración, avanza una secuencia de acciones con un actor representativo
  del proceso (p.ej. el aprobador para accesos/cambios/nuevos servicios)."
- **Restricciones:** debe ser idempotente (no duplicar tickets al repetir el comando).
- **Salida esperada:** `app/seed_servicedesk.py::run()`, comando `flask seed-servicedesk-demo`.
- **Criterio de aceptación:** el comando termina con código 0 y reporta ≥35 tickets creados.
- **Resultado real y observaciones:** **falló.** `flask seed-servicedesk-demo` lanzó
  `No tiene el permiso «work» sobre la cola de este ticket para esa acción.` al llegar a la acción `provisionar` de
  un ticket de `accesos`, porque el aprobador usado como actor único de la secuencia no tiene `can_work`, solo
  `can_approve`. Ver `docs/evidencias/harness-ciclo-06.md` y el prompt revisado (14b).
- **Iteración:** prompt inicial → problema observado (403 real) → prompt revisado (14b) → resultado comprobado.
