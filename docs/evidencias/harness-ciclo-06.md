# Ciclo de harness 06 — actor equivocado en la siembra masiva de tickets (permisos)

- **Tarea:** continuar `flask seed-servicedesk-demo` tras corregir el ciclo 05; avanzar cada ticket de demostración
  por una secuencia de transiciones realista usando un único actor por proceso (`_advance(ticket, actor, *acciones)`).
- **Cambio propuesto:** para `accesos`, usar `aprobador_demo` como actor de toda la secuencia
  `("aprobar", "provisionar")`, razonando que ya es parte del "equipo" que atiende esa cola.
- **Control:** `flask seed-servicedesk-demo` (CLI real).
- **Fallo observado:**
  ```
  app.errors.ApiError: No tiene el permiso «work» sobre la cola de este ticket para esa acción.
  ```
  al llegar a la acción `provisionar` del primer ticket de `accesos`.
- **Causa:** es un **problema de datos/permisos**, no de lógica de transición: `aprobador_demo` solo tiene
  `can_approve` sobre esas colas (otorgado explícitamente en `run()`), no `can_work`. `provisionar` requiere
  `can_work` (es la atención operativa del acceso ya aprobado, no una aprobación). El diseño de autorización
  (`app/security.py::queue_permission`) es correcto; el error estaba en la siembra, que asumía que "aprobador" podía
  ejecutar cualquier paso de la cola.
- **Corrección:** `_advance` se amplió para aceptar `overrides` por acción
  (`_advance(t, admin, *acciones, overrides={"aprobar": aprobador, "rechazar": aprobador})`): el aprobador solo actúa
  en los pasos que realmente requieren su permiso; el resto de la secuencia la ejecuta `admin` (que siempre tiene
  control total, igual que en Parcial 2).
- **Nueva ejecución:** `flask seed-servicedesk-demo` → `Service Desk demo: 7 colas, 35 tickets nuevos creados.`
  Verificado además que **repetirlo no duplica** (`0 tickets nuevos creados` en una segunda corrida) y que las
  categorías quedaron correctamente distribuidas: incidentes `{I0:1, I1:1, I2:3(*), I3:1, I5:1, I6:1}` — el `I2:3`
  son los 3 incidentes auto-creados por los eventos E2/E3 del ciclo siguiente, no un error de conteo.
- **Lección para el contexto:** agregada a `AGENTS.md` §5 (v8 en `docs/contexto/CAMBIOS.md`, commit `8eb3d95`): la
  siembra masiva debe pasar el actor correcto **por acción**, nunca uno solo para una secuencia completa.
