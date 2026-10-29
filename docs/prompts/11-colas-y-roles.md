# Prompt 11 — Colas, permisos y roles funcionales (seguridad)

- **N.º / tema:** seguridad — roles múltiples y permisos por cola
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** permitir que un usuario tenga varios roles (enunciado §11) y que las colas autoricen de forma granular
  (consultar/atender/transferir/aprobar/administrar) sin debilitar el "defecto-denegar" ya aprobado en Parcial 2.
- **Contexto suministrado:** `app/security.py` de Parcial 2 (`guard_request`, exige `role == admin` para toda
  escritura); enunciado §5 (colas y roles) y §3 ("amplíe los permisos… sin concederle modificaciones" al rol consulta).
- **Instrucciones:** "No reescribas la autorización existente de org/catálogo/CMDB (debe seguir exigiendo admin).
  Agrega un mecanismo de permiso por cola que solo aplique al blueprint de tickets."
- **Restricciones:** el rol `consulta` no debe ganar capacidad de escritura por pertenecer a una cola (enunciado
  §5: "Los permisos del rol de consulta no deben elevarse accidentalmente por pertenecer a una cola").
- **Salida esperada:** `queue_permission()`/`require_queue_perm()` en `app/security.py`; `SELF_AUTH_BLUEPRINTS`.
- **Criterio de aceptación:** `tests/test_auth.py::test_P03…` (Parcial 2) sigue pasando sin cambios; nueva prueba
  `tests/test_queues.py::test_P06…` demuestra que un agente sin permiso recibe 403 y, tras otorgárselo, 200.
- **Resultado real y observaciones:** implementado tal como se pidió. Verificado con la suite completa: 58 passed
  (34 pruebas de Parcial 2 — `test_auth`7 + `test_import`11 + `test_migrations`1 + `test_org`7 + `test_persistence`1
  + `test_services`7, esta última extendida para P18 sin tocar su lógica de Parcial 2 — más 24 nuevas de Parcial 3:
  `test_cmdb`7 + `test_dashboard`1 + `test_processes`4 + `test_queues`3 + `test_tickets`9). El rol `consulta` base
  nunca se tocó; los roles funcionales son aditivos vía `user_service_roles` (ver `docs/contexto/CAMBIOS.md` v7).
