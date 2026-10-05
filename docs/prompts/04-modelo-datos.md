# Prompt 04 — Revisión del modelo de datos y la jerarquía
- **Tema:** diseño del modelo
- **Estado:** USADO (real).
- **Herramienta / modelo / versión / fecha de uso (REAL):** Claude Code (extensión de VS Code), modelo Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-04 ~22:42. Revisó `app/models.py`, `app/api/org.py` y `app/api/services.py`, y ejecutó `alembic check` en el contenedor.
- **Objetivo:** revisar integridad del modelo (claves, unicidad, huérfanos, bajas lógicas) frente al enunciado.
- **Contexto a adjuntar:** `app/models.py`, `migrations/versions/0001_esquema_inicial.py`, `docs/contexto/01-reglas-de-negocio.md`, `app/api/org.py`, el enunciado (§3.2 y §3.3).
- **Criterio de aceptación:** hallazgos con archivo/línea y propuesta mínima; distingue lo que fuerza la BD de lo que solo valida el servidor.

## Prompt (copiar tal cual)
```
<rol>Eres un arquitecto de bases de datos relacionales (PostgreSQL) que revisa un modelo antes de entregarlo.</rol>

<contexto>
Jerarquía obligatoria: Empresa → Área → Departamento → Sección → Puesto → Usuario, un único padre por registro, códigos de subordinadas únicos dentro de su padre, la empresa del usuario derivada de su jerarquía, sin huérfanos, sin asociaciones nuevas con padres inactivos, bajas lógicas con política coherente. Servicios N1/N2 con códigos únicos, min ≤ max, ausente ≠ 0, responsable de un N2 = usuario de la sección asignada. Adjunto models.py, la migración, las reglas de negocio y org.py.
</contexto>

<tarea>Audita el modelo y responde: (1) ¿qué reglas del enunciado están garantizadas por restricciones de la BD y cuáles dependen solo del código?; (2) ¿existe alguna forma de crear un registro huérfano o contradictorio saltándose la API (p. ej. SQL directo)?; (3) ¿faltan índices o restricciones razonables?; (4) ¿la política de baja lógica tiene huecos (por ejemplo reactivar un hijo con padre inactivo, o desactivar una sección con servicios)?; (5) ¿la migración coincide con models.py?</tarea>

<restricciones>
- No rediseñes la jerarquía ni cambies nombres de tablas.
- Propón cambios mínimos y di si requieren nueva migración.
- Cita archivo y línea o nombre de función en cada hallazgo.
- Si no estás seguro de algo, márcalo como "a verificar" y di cómo verificarlo.
</restricciones>

<formato_de_salida>Tabla: # | Hallazgo | Archivo/función | Severidad (alta/media/baja) | Propuesta mínima | ¿Requiere migración? Al final, 3 pruebas automáticas sugeridas que demostrarían los hallazgos de severidad alta.</formato_de_salida>

<criterio_de_aceptacion>Ningún hallazgo sin referencia al código; separa claramente "garantizado por la BD" de "validado por la app".</criterio_de_aceptacion>
```

## Resultado REAL
**Garantizado por la BD:** un único padre obligatorio (FK `NOT NULL` en `areas.company_id`, `departments.area_id`, `sections.department_id`, `positions.section_id` y `users.position_id`, `models.py` l. 34–80); código único dentro del padre (`uq_*_code`, l. 29, 40, 51, 62); códigos N1/N2 únicos (l. 120 y 137); `min ≤ max` (`ck_l2_min_max`, l. 133); ausente ≠ 0 (columnas `Numeric` anulables, l. 148–149); rol y `activo_excel` restringidos por CHECK. **Migración:** `docker compose exec -T app alembic check` → «No new upgrade operations detected» (coincide con `models.py`).

**Validado solo por la app:**

| # | Hallazgo | Archivo/función | Severidad | Propuesta mínima | ¿Migración? |
|---|---|---|---|---|---|
| 1 | Responsable de un N2 = usuario de la sección: solo lo verifica `_l2_values` (`services.py` l. 198); con SQL directo se puede asignar un responsable de otra sección | `services.py::_l2_values` | media | trigger o FK compuesta; se acepta como regla de la app y queda declarado | sí (si se implementa) |
| 2 | No se crean asociaciones con padres inactivos: solo lo valida `_check_parent` (`org.py` l. 122–130); la BD lo permite | `org.py::_check_parent` | baja | aceptado: el estado activo no se expresa bien con un CHECK | — |
| 3 | La reactivación de un hijo con padre inactivo la bloquea `update_unit` (`org.py` l. 181) | `org.py::update_unit` | — (sin hueco) | — | — |
| 4 | Desactivar una unidad con servicios activos: `deactivate_tree` (l. 58–91) lista los N2 afectados y exige `cascade` | `org.py::deactivate_tree` | — (sin hueco) | — | — |
| 5 | Índices: las FK de `services_l2.class_id`, `criticality_id` y `type_id` no tienen índice | `models.py` l. 143–145 | baja | `index=True` si crecen los filtros (hoy hay 46 filas) | sí |

No se encontró una forma de crear huérfanos (todas las FK son `NOT NULL`, sin `ON DELETE CASCADE`, y las bajas son lógicas). Los registros contradictorios con SQL directo solo son posibles en los puntos 1 y 2.

Pruebas que ya cubren los hallazgos: `test_P11…` (responsable de otra sección rechazado), `test_P05…` (duplicados y referencias), `test_migrations` (migración ↔ modelo). No hubo hallazgos de severidad alta.

## Decisiones y cambios aplicados
Sin cambios de código ni migración. Los puntos 1 y 2 se aceptan como validación de la aplicación y quedan declarados como limitación; el punto 5 no se justifica con 46 servicios.
