# Alcance y fuentes de Parcial 3

## Material obligatorio y su alcance real (verificado, no asumido)
| Fuente | Qué contiene realmente | Dónde se usó |
|---|---|---|
| `data/CatalogoServicios.xlsx` | Catálogo de servicios N1/N2 (ya importado en Parcial 2; sin cambios) | `app/importer.py` (sin cambios) |
| `data/CMDB.xlsx` (hoja `CMDB`, `B4:U6`) | **Plantilla delgada**: 20 columnas de atributos de CI y solo 2 filas de ejemplo (`Servidor1`=Hardware, `Aplicación`=Software). No es una taxonomía multinivel. | Base de las columnas de `devices.attributes` y de los 2 valores de ejemplo de `ci_classes` (Hardware/Software) |
| `docs/fuentes/Service Desk.pptx.pdf` (16 diapositivas) | Niveles de soporte 0–4/0–3 (diapo. 11–13), tipos de ticket (diapo. 14), eventos E0–E3 (diapo. 15), incidentes I0–I6 (diapo. 16). Coincide con el texto ya citado en el enunciado §7. | `app/reference_data.py` (TRANSITIONS, mapeo de tipos), `app/ticket_engine.py` (`INCIDENT_PRIORITY`) |
| `docs/fuentes/Transicion.pptx.pdf` (25 diapositivas) | Transición de servicios ITIL: SACM, CMDB/CMS (diapo. 9–14, con la lista de campos que **coincide exactamente** con las columnas de `CMDB.xlsx`), gestión de cambios, liberaciones, conocimiento (DIKW/SKMS). Confirmado con el catedrático que es el material de la «lección 22» mencionada en el enunciado. Tampoco trae niveles de clasificación de CI más allá del principio general «los CI se agrupan y clasifican». | Justifica el modelo conceptual de `devices` (campos de la diapo. 11 ≈ columnas de `CMDB.xlsx`) |

## Hallazgo relevante (motivó una actualización de contexto — ver `CAMBIOS.md` y `docs/contexto/05-cmdb-jerarquia.md`)
Al iniciar el trabajo solo se habían entregado `CMDB.xlsx` y `Service Desk.pptx.pdf`. Verificando ambos contra el
enunciado se detectó que **ninguno de los dos contiene una jerarquía de clasificación de CI con niveles y
denominaciones** (el enunciado exige reproducir "los niveles, denominaciones y relaciones de la lección 22 y de
CMDB.xlsx"). Se preguntó al responsable del proyecto, quien aportó `Transicion.pptx.pdf` (el contenido real de la
"lección 22", que resultó ser solo el espacio de la clase donde se presentó `CMDB.xlsx`, no una lección distinta con
más datos). Verificado ese archivo, se confirmó que tampoco define niveles: es el marco conceptual de **qué campos**
debe tener un CI, no **cómo clasificarlos**. Ver la decisión de proyecto resultante en `docs/contexto/05-cmdb-jerarquia.md`.

## Decisiones de diseño (no estaban en el enunciado ni en las fuentes; se registran para que sean auditables)
1. **Roles funcionales aditivos, no se tocó `users.role`.** En vez de normalizar `admin`/`consulta` junto con
   `solicitante`/`agente`/`aprobador` en una sola tabla de roles (que hubiera obligado a reescribir toda la
   autorización y las pruebas ya aprobadas de Parcial 2), se agregó `user_service_roles` como tabla aditiva. Razón:
   minimizar el riesgo de regresión sobre funcionalidad ya calificada, cumpliendo igual "un usuario puede tener varios
   roles" (ver `docs/PROCESOS.md` §Roles y colas).
2. **Concurrencia de "tomar ticket" sin locks explícitos.** Se usa un `UPDATE … WHERE assignee_user_id IS NULL`
   atómico y se verifica `rowcount`; es portable entre SQLite (pruebas) y PostgreSQL (producción) y se comprobó con
   hilos reales en `tests/test_queues.py::test_P07…` (no es una prueba simulada).
3. **Sin pausas explícitas de SLA.** El tablero de indicadores mide tiempos de extremo a extremo; se documenta como
   limitación conocida en `docs/RESOLUCION.md` en vez de inventar un mecanismo de pausa no pedido explícitamente por
   el enunciado como requisito funcional.
4. **E2/E3 crean un incidente con categoría I2 por defecto.** Ninguna fuente define qué categoría de incidente debe
   resultar de un evento; I2 (impacto medio, 8h) se eligió como valor razonable intermedio y se documenta como
   decisión de proyecto en `docs/PROCESOS.md`, nunca presentada como dato de las diapositivas.
