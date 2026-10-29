# IA.md — evidencia consolidada de las 4 ingenierías (Parcial 3)

Herramienta usada en toda la sesión: **Claude Code (Claude Sonnet 5)**, 2026-10-29. Esta sesión construyó Parcial 3
sobre el repositorio ya entregado de Parcial 2; los commits citados abajo son reales (`git log`), no reconstruidos.

## 1. Context Engineering
- `AGENTS.md` ampliado para Parcial 3 (alcance, fuentes, convenciones nuevas) — commit `468f563`.
- `docs/contexto/04-parcial3-alcance.md` y `05-cmdb-jerarquia.md` — commit `468f563`.
- **≥3 actualizaciones justificadas** (`docs/contexto/CAMBIOS.md` v6–v8):
  - v6 (`468f563`): hallazgo de que ninguna fuente entregada trae una jerarquía de CI verificable.
  - v7 (`3a8127c`): decisión de no tocar `users.role`, roles funcionales aditivos (verificada: 0 regresiones en P2).
  - v8 (`8eb3d95`): dos lecciones de datos/validación encontradas al ejecutar `flask seed-servicedesk-demo` de verdad.
- Regla de datos no confiables extendida explícitamente a CMDB/tickets en `AGENTS.md` §3 (comentarios, adjuntos,
  atributos sintéticos).

## 2. Prompt Engineering
Registro completo en `docs/prompts/` (commit `dd5ae61`), 10 archivos cubriendo los 8 temas exigidos (requisitos/CMDB,
modelo, colas, procesos, seguridad, los dos grafos, pruebas) con el formato de `docs/prompts/PLANTILLA.md`. Dos
mejoras con resultado comprobado:

| Mejora | Prompt inicial | Problema observado | Prompt revisado | Resultado comprobado |
|---|---|---|---|---|
| 1 | `09a-jerarquia-cmdb-v1.md` | Ninguna fuente entregada alcanzaba para diseñar niveles | `09b-jerarquia-cmdb-v2.md` | 17 `ci_classes` sembradas; `tests/test_cmdb.py::test_P04…` pasa |
| 2 | `14a-siembra-demo-v1.md` | `403` real al ejecutar `flask seed-servicedesk-demo` (actor sin permiso `can_work`) | `14b-siembra-demo-v2.md` | 35 tickets creados; repetir da 0 nuevos; conteos de BD verificados |

## 3. Harness Engineering
Se reutilizó el harness de Parcial 2 sin reemplazarlo (`AGENTS.md` §4), ampliado con:
- `flask generate-cmdb --seed --count` (reproducible, idempotente — ver `docs/prompts/13…`).
- `flask seed-servicedesk-demo` (idempotente — ver ciclos 05/06).
- `scripts/setup_eval.sh` y `scripts/smoke.py` ampliados para cubrir CMDB/Service Desk (commit `8eb3d95`).
- Límites de operación sin cambios: no leer/publicar secretos, no modificar los archivos fuente conservados
  (`data/CMDB.xlsx`, `docs/fuentes/*.pdf` se suman a `data/CatalogoServicios.xlsx`), nada destructivo fuera de datos
  de prueba aislados.
- Datos de prueba controlados: `tests/conftest.py` siembra `reference_data.seed_orm()` sobre una BD SQLite temporal
  por prueba (o PostgreSQL efímero en Docker), nunca sobre datos reales.
- Verificación local sin Docker completada primero (`ruff check .` + `pytest -q`, 58/58 — `docs/prompts/15…`); la
  verificación completa con Docker se completó después, en la misma sesión, una vez reiniciado el daemon (ver
  `docs/PRUEBAS.md` §3 y `docs/evidencias/harness-ciclo-08.md`): `docker compose --profile test run` → 58 passed
  sobre PostgreSQL real; `setup_eval.sh`, `smoke.py flow`, `persistence_check.sh` y `ui_tests` todos en verde tras
  corregir dos fallos reales encontrados en el propio arnés de verificación (no en la aplicación).

## 4. Loop Engineering
Tres ciclos completos **tarea → cambio propuesto → ejecución → evaluación → corrección → nueva verificación**, ninguno
introducido deliberadamente (los tres surgieron de ejecutar los comandos reales):

| Ciclo | Tipo de fallo | Resumen | Commit del fix |
|---|---|---|---|
| `docs/evidencias/harness-ciclo-05.md` | **Defecto funcional** | `service_l2_id` exigido a un proceso (`nuevos_servicios`) que por definición aún no tiene servicio | `8eb3d95` |
| `docs/evidencias/harness-ciclo-06.md` | **Datos/permisos** | Siembra masiva usaba un único actor para toda una secuencia de transiciones con permisos distintos | `8eb3d95` |
| `docs/evidencias/harness-ciclo-07.md` | Verificación de diseño vía 3 fallos reales de `pytest` | Confirma que "no ejecutar cambio sin aprobación" está garantizado en dos capas; corrige 2 defectos de configuración de prueba | `5423e6d` |
| `docs/evidencias/harness-ciclo-08.md` | **Harness/datos** | Dos fallos reales en la primera verificación completa con Docker/PostgreSQL: un control de humo asumía que el catálogo no crecía (sí puede, por `nuevos_servicios` aprobados) y un ticket marcador no incluía un `service_l2_id` obligatorio | `1da5bb8` |

## 5. Los dos grafos (para la defensa)
- **Grafo 1 — dependencias de CI** (`app/graph_cmdb.py`): nodos = `devices`, aristas = `device_relations` con tipo.
  `depende_de`/`alojado_en` son dirigidas y sin ciclos; `conectado_a` es de conectividad y admite ciclos. Expuesto en
  `GET /api/cmdb/devices/<id>/impacto`.
- **Grafo 2 — flujo de tickets** (`app/workflow.py`): nodos = `process_states`, aristas = `process_transitions` por
  proceso. Expuesto en `GET /api/processes/<code>/grafo`; es la misma estructura que usa `ticket_engine.apply_transition`
  para aceptar o rechazar cada acción, nunca una descripción aparte.
