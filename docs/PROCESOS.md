# PROCESOS — tipos, colas, permisos, estados, transiciones y escalamiento

## 1. Roles y colas
`users.role` (`admin`/`consulta`) **no cambió** respecto a Parcial 2: sigue controlando el mantenimiento de
organización, catálogo, CMDB y colas (siempre exige `admin`, ver `app/security.py::guard_request`). Se agregaron tres
roles **funcionales, aditivos** en `user_service_roles` — un usuario puede tener varios a la vez:

| Rol | Para qué sirve |
|---|---|
| `solicitante` | Crear tickets propios y consultarlos (portal del solicitante = filtro "solo mis tickets" en la UI) |
| `agente` | Atender tickets de las colas donde tenga `can_work` (tomar, transicionar, comentar, transferir si tiene `can_transfer`) |
| `aprobador` | Ejecutar las transiciones marcadas `required_perm = "approve"` en las colas donde tenga `can_approve` |

Cada **cola** pertenece a exactamente un proceso y autoriza a roles o a usuarios específicos
(`queue_permissions.principal_role` XOR `principal_user_id`) con 5 permisos independientes: `can_view`, `can_work`,
`can_transfer`, `can_approve`, `can_manage`. `admin` tiene control total siempre, sin necesidad de un permiso
explícito. **Pertenecer a una cola nunca eleva los permisos del rol base `consulta`** (enunciado §5): la pertenencia
solo habilita acciones sobre tickets a través de `SELF_AUTH_BLUEPRINTS`/`queue_permission`, nunca escritura en
org/catálogo/CMDB/colas.

**Política de asignación** (documentada, enunciado §5): manual por defecto — "tomar" (`POST /tickets/<id>/tomar`) es
un `UPDATE … WHERE assignee_user_id IS NULL` atómico (ver §4). **Regla de ordenamiento** por defecto:
`priority_then_age` (prioridad `alta`>`media`>`baja`, luego antigüedad) — aplicada por la UI al listar tickets de una
cola (orden del API); es la única regla implementada, declarada como tal en `queues.ordering_rule` por si se agregan
otras en el futuro. No se deja ningún ticket huérfano al desactivar un usuario: `assignee_user_id` queda `NULL` (sigue
visible y reclamable); desactivar una cola (`is_active=false`) no borra sus tickets, solo impide crear nuevos en ella.

## 2. Tipos de ticket y mapeo a los 7 procesos (enunciado §7, diapositiva 14)
| Tipo de ticket (diapo. 14) | Proceso(s) |
|---|---|
| Solicitud de acceso | `accesos` |
| Evento | `eventos` |
| Incidente | `incidentes` |
| Solicitud de cambio | `cambios` |
| Requisición de servicio | `servicios_tecnologia` (servicio existente) **y** `nuevos_servicios` (subtipo explícito: servicio que aún no existe) |
| Problema | `problemas` |

## 3. Los 7 procesos: estados, transiciones, aprobaciones
Grafo completo y consultable en vivo: `GET /api/processes/<code>/grafo` (expone exactamente lo que
`app/workflow.py`/`app/ticket_engine.py` aplican — nunca una descripción que pueda desincronizarse del código).
Fuente de los datos: `app/reference_data.py` (`STATES`, `TRANSITIONS`).

### 3.1 Gestión de nuevos servicios
`solicitado → analisis → {aprobado → implementado → cerrado | rechazado}`. Al **aprobar**, el servidor crea o vincula
el `ServiceL2` (por nombre, sin distinguir mayúsculas, bajo el `services_l1` propuesto) para no duplicarlo —
`app/ticket_engine.py::_create_or_link_service`. Distinto de `servicios_tecnologia` (que opera sobre un servicio **ya
existente**) y de un incidente (no hay interrupción involucrada).

### 3.2 Gestión de cambios
`solicitado → evaluacion → {aprobado → planificado → ejecutado → validado → cerrado → reabierto → validado |
rechazado}`. Campos propios: tipo de cambio (`estandar`/`normal`/`emergencia`), plan de pruebas, plan de reversión, CI
afectados (`ticket_ci_links`). **No se puede ejecutar sin aprobación** en dos capas independientes: (a) el propio
grafo no tiene una arista `evaluacion → planificar` ni `… → ejecutar` (solo existe `aprobado → planificado`); (b)
`app/ticket_engine.py::_apply_effects` verifica además que `change_detail.approved_at` esté definido. Ver
`docs/evidencias/harness-ciclo-07.md` (hallazgo #2) para la verificación real de esta doble garantía.

### 3.3 Gestión de incidentes
`registrado → clasificado → diagnostico → atencion → {escalado ⇄ atencion | recuperado → resuelto → cerrado |
cerrado (sin resolución)} → reabierto → diagnostico`. Categoría I0–I6 obligatoria al crear (ver §4). "Cierre sin
resolución" es la arista `atencion → cerrado` (acción `cerrar_sin_resolucion`), distinta de
`resuelto → cerrado`; ambas dejan `closed_at` establecido, pero solo la segunda deja `resolved_at`. Reapertura
(`cerrado → reabierto`) está disponible tanto para `admin`/agentes con `can_work` como para el **propio solicitante**
sobre su ticket (única excepción al permiso de cola, ver `app/ticket_engine.py::_authorize_transition`).

### 3.4 Gestión de eventos
`registrado → evaluado → cerrado`. Categoría E0–E3 obligatoria al crear. Al **evaluar**: E0/E1 no generan ningún
efecto adicional (solo registro); E2/E3 crean (o reutilizan, si ya existe) un incidente vinculado —
`app/ticket_engine.py::_create_linked_incident` — y lo enlaza vía `ticket_event_details.linked_incident_id` +
`ticket_relations` (`relation_type="genera_incidente"`), evitando duplicarlo si el mismo evento se reprocesa
(verificado en `tests/test_tickets.py::test_P11…`). **Decisión de proyecto** (ninguna fuente lo especifica): la
categoría del incidente auto-creado es `I2` por defecto, documentada aquí y no presentada como dato de las diapositivas.

### 3.5 Gestión de problemas
`registrado → investigacion → {solucion_temporal | error_conocido} → solucion_definitiva → cerrado`. Permite vincular
el incidente de origen (`linked_incident_id`) y el cambio que implementa la corrección (`linked_change_id`), ambos
consultables en la ficha del ticket (trazabilidad incidente↔problema↔cambio, probada en
`tests/test_tickets.py::test_P13…`).

### 3.6 Gestión de accesos
`solicitado → {aprobado → provisionado → {cerrado | revocado} | rechazado}`. Campos propios: beneficiario (puede ser
distinto del solicitante), recurso, permiso solicitado, aprobador. **Anti-autoaprobación** (enunciado §6): al
`aprobar`, el servidor rechaza con `403 self_approval` si el actor es el solicitante **o** el beneficiario del
acceso — probado con ambos casos en `tests/test_tickets.py::test_P10_autoaprobacion_acceso_rechazada`.

### 3.7 Gestión de servicios de tecnología
`solicitado → validacion → asignado → cumplido → cerrado`. Opera siempre sobre un `service_l2_id` existente; sin
campos de detalle propios. Se distingue de `nuevos_servicios` (que propone un servicio inexistente) y de `incidentes`
(no hay interrupción, es una solicitud de cumplimiento normal del catálogo).

## 4. Parámetros de la lección 25 (Service Desk.pptx.pdf)
- **Niveles de soporte:** la diapositiva 11 usa 0–4 (Autoservicio/Help Desk/Soporte Técnico/Ingenieros/Externo); las
  diapositivas 12–13 usan 0–3 y ubican a los proveedores en el nivel 3. Se adoptó el esquema de **5 niveles (0–4)** de
  la diapositiva 11 por ser el más detallado, con `queues.support_level` configurable (`nivel0`…`nivel4`) y
  equivalencia documentada: nivel 3 (diapo. 12–13, "Proveedores") ≈ nivel 4 (diapo. 11, "Externo"). Ruta de
  escalamiento: autoservicio/FAQ (nivel 0, sin ticket) → Help Desk (cola de primer nivel) → Soporte Técnico →
  Ingenieros → Externo/Proveedor (`acción escalar` dentro de `incidentes`, o transferencia entre colas de distinto
  nivel, enunciado §8/§9). Los porcentajes 20/70/5/5 de la diapositiva 12 son referencias del material, **no** cuotas
  que el sistema fuerce (enunciado §7, último párrafo).
- **Categorías de incidente I0–I6:** tabla de duración/prioridad/redundancia de la diapositiva 16, implementada en
  `app/ticket_engine.py::INCIDENT_PRIORITY` (I0→baja; I1–I2→media; I3–I6→alta). Las duraciones **no** constituyen un
  SLA de resolución por sí mismas (enunciado §7); el objetivo de resolución real vive en `queues.targets` (minutos
  por prioridad) y lo usa el tablero de indicadores. Los rótulos temporales se solapan (p. ej. I2 ≤8h incluye el
  rango de I1); se resolvió con una regla complementaria determinista: la categoría se recibe explícitamente al crear
  el ticket (no se infiere automáticamente de una duración), decisión de proyecto documentada aquí porque el
  enunciado pide definir una regla "sin atribuirla a la presentación".
- **Eventos E0–E3:** tabla de la diapositiva 15, implementada tal cual (ver §3.4).

## 5. Tablero de indicadores — cómo se calcula cada uno
Documentado también como docstring en `app/api/dashboard.py` (código y documento no deben desincronizarse):
- **Tiempo usado: CALENDARIO** (24/7), no hábil — declarado explícitamente (enunciado §7 lo exige).
- **Antigüedad:** `ahora − created_at`, solo tickets con `closed_at IS NULL` (abiertos).
- **Primera atención:** primera fila de `ticket_history` con acción `tomado`/`asignado`, menos `created_at`; tickets
  sin asignar aún no cuentan (no se ha dado "primera atención").
- **Resolución:** `resolved_at − created_at`; `resolved_at` se actualiza en **cada** entrada a `resuelto`/`recuperado`
  (incluida tras una reapertura), de modo que un ticket reabierto y vuelto a resolver refleja su resolución más
  reciente, no la primera.
- **Cumplimiento de objetivo:** % de tickets resueltos cuyo tiempo de resolución está dentro de
  `queues.targets[prioridad]` (minutos); tickets sin objetivo configurado para su prioridad no se cuentan ni a favor
  ni en contra.
- **Pausas:** esta versión no implementa un estado de "pausa" explícito (no es un requisito de estado exigido por el
  enunciado); se documenta como limitación conocida en `docs/RESOLUCION.md`.
