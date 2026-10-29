# Historial del contexto (`AGENTS.md`)

| Versión | Fecha | Cambio | Motivo (hallazgo o decisión) |
|---|---|---|---|
| v1 | 2026-10-04 | Creación de AGENTS.md y docs/contexto | Contexto inicial a partir del enunciado |
| v2 | 2026-10-04 | Convención DOM: `replaceChildren` no aplana arreglos → usar *spread* | **Hallazgo:** la prueba jsdom de la UI mostró el selector de responsable vacío; causa: `replaceChildren(op, ops.map(...))` insertaba texto. Ver `docs/evidencias/harness-ciclo-02.md` |
| v3 | 2026-10-04 | Convención de pruebas PostgreSQL: `db.session.remove()` antes de `db.drop_all()` | **Hallazgo:** `test_persistence` se colgó sobre PostgreSQL real (bloqueo propio); en SQLite no ocurría. Ver `docs/evidencias/harness-ciclo-03.md` |
| v3 | 2026-10-04 | Nota de estado en 02-analisis-excel.md: análisis basado en enunciado, Excel real pendiente | **Decisión:** el archivo no estaba disponible; se evitó inventar su contenido |
| v4 | 2026-10-04 | `02-analisis-excel.md` pasa de «pendiente» a «verificado con el archivo real»; justificación de SE.12 reescrita con evidencia (B100 = nombre del N2 SE.12.3); filas 42/67 documentadas | **Hallazgo:** al disponer del Excel real se confirmó 12/46 y se obtuvo la evidencia que sustenta el nombre canónico |
| v5 | 2026-10-04 | AGENTS.md §4: `smoke.py` y `persistence_check.sh` dependen de `setup_eval.sh` | **Hallazgo:** en la validación con Docker el humo falló al iniciar sesión como admin por no haber creado las cuentas. Ver `docs/evidencias/harness-ciclo-04.md` |

> Para que el versionado sea verificable: haga un commit por cada versión (o un commit que actualice AGENTS.md por cada
> hallazgo) y anote aquí el SHA. Estado real: las versiones v1–v5 se desarrollaron antes de inicializar el control de versiones y se
> publicaron juntas en el primer commit completo del repositorio; no existen SHAs por versión.

## Parcial 3

| Versión | Fecha | Cambio | Motivo (hallazgo o decisión) | Commit |
|---|---|---|---|---|
| v6 | 2026-10-29 | `AGENTS.md` reescrito para Parcial 3; se agregan `docs/contexto/04-parcial3-alcance.md` y `05-cmdb-jerarquia.md`; se conservan `CMDB.xlsx`, `Service Desk.pptx.pdf` y `Transicion.pptx.pdf` en el repo | **Hallazgo:** ni `CMDB.xlsx` ni `Service Desk.pptx.pdf` (los dos archivos entregados inicialmente) contienen una jerarquía de clasificación de CI con niveles/denominaciones; se preguntó al responsable del proyecto, quien aportó `Transicion.pptx.pdf` como el contenido real de la "lección 22" (en realidad solo el espacio de clase donde se mostró `CMDB.xlsx`). Verificado ese archivo, tampoco define niveles (solo el modelo conceptual de campos, que sí coincide con `CMDB.xlsx`). Se documentó el vacío en vez de inventar la jerarquía y presentarla como proveniente de una fuente inexistente. | `ver git log` |
| v7 | 2026-10-29 | `AGENTS.md` §5: se documenta la decisión de **no modificar** `users.role` (admin/consulta) y agregar los roles funcionales de Service Desk como tabla aditiva `user_service_roles` | **Decisión de diseño:** normalizar todos los roles en una sola tabla hubiera exigido reescribir `guard_request`, los serializadores y las pruebas de autorización ya aprobadas de Parcial 2, con riesgo de regresión. La alternativa aditiva cumple "un usuario puede tener varios roles" sin tocar código ya calificado; verificado ejecutando la suite completa de Parcial 2 sin cambios (34/34 siguen pasando) tras el cambio. | `ver git log` |
| v8 | 2026-10-29 | `AGENTS.md` §5: dos lecciones agregadas tras fallos reales de pruebas — (a) `service_l2_id` no puede ser obligatorio para los procesos `accesos`/`nuevos_servicios`; (b) la siembra masiva de tickets debe asignar el actor correcto **por acción**, no uno solo para toda la secuencia | **Hallazgo:** `pytest` falló primero con `ApiError validation` al crear un ticket de `nuevos_servicios` (exigía un servicio que por definición no existe todavía); después `flask seed-servicedesk-demo` falló con 403 al intentar que el aprobador ejecutara `provisionar` (acción que requiere `can_work`, no `can_approve`). Ambos se corrigieron y se reprodujo la ejecución con éxito (ver `docs/evidencias/harness-ciclo-05.md` y `harness-ciclo-06.md`). | `ver git log` |

> Nota: los SHA exactos de v6–v8 se completan en un commit final de esta fase (`docs: referencias de commits en CAMBIOS.md`)
> una vez existen, para evitar citar un SHA que todavía no se ha creado.
