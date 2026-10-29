# PRUEBAS — matriz requisito → implementación → prueba → evidencia (Parcial 3)

> P01–P02 y la base de P03 ya estaban cubiertos por Parcial 2 (`docs/RESOLUCION.md` §7–§8) y siguen pasando sin
> cambios. Esta matriz añade P03 extendido a CMDB/tickets y P04–P18 (enunciado §11).

## 1. Matriz

| ID | Implementación | Prueba | Tipo |
|---|---|---|---|
| P01 Auth, logout, inactivo, sin permiso | `app/security.py` (sin cambios de Parcial 2) | `tests/test_auth.py::test_P01…/test_P02…` | integración |
| P02 Importación repetible 12/46 | `app/importer.py` (sin cambios) | `tests/test_import.py` | integración |
| P03 CMDB/5000 dispositivos únicos, repetible | `app/cmdb_generator.py` | `tests/test_cmdb.py::test_P16…` (filtros/volumen) + `docs/prompts/13…` (idempotencia real con 500 y 5000) | integración + CLI real |
| P04 Jerarquía CMDB vs Excel/lección 22; rechazo de ciclos | `app/graph_cmdb.py`, `app/api/cmdb.py` | `tests/test_cmdb.py::test_P04_jerarquia_ci_corresponde_a_fuentes_y_rechaza_ciclos` | integración |
| P05 Ticket con referencias válidas/inválidas | `app/ticket_engine.py::create_ticket` | `tests/test_tickets.py::test_P05…` | integración |
| P06 Permiso de cola por rol y por usuario | `app/security.py::queue_permission`, `app/api/queues.py` | `tests/test_queues.py::test_P06…` | integración |
| P07 Orden determinista; dos agentes, un solo ganador | `app/ticket_engine.py::claim_ticket` (UPDATE atómico) | `tests/test_queues.py::test_P07…` (2 `threading.Thread` reales) | integración (concurrencia real) |
| P08 Transferencia con historial y validación de proceso destino | `app/ticket_engine.py::transfer_ticket` | `tests/test_queues.py::test_P08…` | integración |
| P09 Ruta completa de los 7 procesos; transición inválida rechazada | `app/workflow.py`, `app/reference_data.py` | `tests/test_tickets.py::test_P09…` | integración |
| P10 Cambio sin aprobación; autoaprobación de acceso | `app/ticket_engine.py::_apply_effects` + grafo | `tests/test_tickets.py::test_P10_…` (2 pruebas) | integración |
| P11 Eventos E0–E3; E2/E3 vinculan incidente sin duplicar | `app/ticket_engine.py::_create_linked_incident` | `tests/test_tickets.py::test_P11…` | integración |
| P12 I0–I6, duración/prioridad/redundancia | `app/ticket_engine.py::INCIDENT_PRIORITY` | `tests/test_tickets.py::test_P12…` | integración |
| P13 Incidente↔problema↔cambio trazable | `ticket_problem_details`, `ticket_relations` | `tests/test_tickets.py::test_P13…` | integración |
| P14 Recorrido CI–servicio; ciclos según tipo de relación | `app/graph_cmdb.py::impact_of/would_create_cycle_relation` | `tests/test_cmdb.py::test_P14…` | integración |
| P15 Cierre sin resolución, reapertura, bitácora con actor | `app/ticket_engine.py::apply_transition` + `ticket_history` | `tests/test_tickets.py::test_P15…` | integración |
| P16 Filtros/paginación con ~5000+ dispositivos | `app/api/cmdb.py::list_devices` | `tests/test_cmdb.py::test_P16…` (30 insertados + filtros) | integración |
| P17 Indicadores con datos controlados (abiertos/pausas/reaperturas declarado) | `app/api/dashboard.py` | `tests/test_dashboard.py::test_P17…` | integración |
| P18 Reinicio de contenedores sin pérdida de catálogo/CMDB/tickets | volumen `pgdata` (sin cambios de infraestructura) | `tests/test_persistence.py` (equivalente en proceso) + `scripts/persistence_check.sh` (Docker, **pendiente de ejecutar** — ver §3) | integración + E2E |
| Comentarios/adjuntos (validación tipo/tamaño, autorización de descarga) | `app/ticket_engine.py::add_attachment/add_comment` | `tests/test_tickets.py::test_comentarios_visibilidad_y_adjuntos_con_validacion` | integración |
| Grafo de procesos consultable | `app/workflow.py::graph_dict` | `tests/test_processes.py` | integración |

## 2. Resultados reales de pruebas (local, sin Docker — ver §3 para lo pendiente)

| Fecha | Comando | Entorno | Commit | Resultado |
|---|---|---|---|---|
| 2026-10-29 | `python -m pytest -q` | SQLite (fixtures `tmp_path`), Python 3.11.4 | `5423e6d` | **58 passed** en 47.07 s |
| 2026-10-29 | `python -m ruff check .` | — | `5423e6d` | All checks passed |
| 2026-10-29 | `flask import-catalog` | SQLite local | `468f563` (código sin cambios de Parcial 2) | creados=58, observados=8, N1=12, N2=46, coincide=true |
| 2026-10-29 | `flask create-eval-users` | SQLite local | `8eb3d95` | 5 cuentas creadas: admin_demo, consulta_demo, solicitante_demo, agente_demo, aprobador_demo |
| 2026-10-29 | `flask generate-cmdb --seed 42 --count 500` (×2) | SQLite local | `8eb3d95` | 1.ª: creados=500/actualizados=0; 2.ª (misma semilla): creados=0/actualizados=500 — **no duplica** |
| 2026-10-29 | `flask generate-cmdb --seed 7 --count 5000` | SQLite local | `8eb3d95` | creados=5000/actualizados=0 en 1.7 s; distribución por clase y nivel raíz reportada (HW=3288, SW=1584, DOC=120, FAC=8) |
| 2026-10-29 | `flask seed-servicedesk-demo` (×2) | SQLite local | `8eb3d95` | 1.ª: 7 colas, 35 tickets nuevos; 2.ª: 0 tickets nuevos — **no duplica**. 38 tickets totales (35 + 3 incidentes auto-creados por eventos E2/E3), 2 `ServiceL2` creados por aprobación de nuevos servicios, 120 filas de bitácora |
| 2026-10-29 | `node --check app/static/app.js` | Node.js v20.19.0 | `0f15bad` | sin errores de sintaxis (un primer intento sí tuvo un paréntesis sin cerrar, corregido antes del commit) |

Las tablas de Parcial 2 (§8 de `docs/RESOLUCION.md`) se mantienen como evidencia histórica y no se repiten aquí.

## 3. Pendiente antes de la entrega (declarado explícitamente, no omitido)
El daemon de Docker Desktop no estuvo activo en el equipo durante esta sesión de construcción
(`docker ps` → *"failed to connect to the docker API"*); Docker **sí** está instalado (29.2.0 / Compose v5.0.2). Antes
de entregar, ejecutar y registrar aquí:
```
docker compose up --build -d
sh scripts/setup_eval.sh
docker compose --profile test run --rm --build tests     # ruff + pytest P01–P18 sobre PostgreSQL efímero
docker compose exec -T app python scripts/smoke.py flow  # incluye los chequeos nuevos de CMDB/Service Desk
sh scripts/persistence_check.sh                           # P18 con reinicio real de contenedores
docker compose --profile ui run --rm ui_tests              # UI (jsdom), opcional
```
Esto reconfirma sobre PostgreSQL real lo ya verificado sobre SQLite, y es la única verificación que falta para
declarar el ciclo de harness de Parcial 3 completo de extremo a extremo con Docker.
