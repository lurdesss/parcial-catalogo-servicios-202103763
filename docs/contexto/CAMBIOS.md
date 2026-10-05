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
