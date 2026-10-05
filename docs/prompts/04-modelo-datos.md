# Prompt 04 — Revisión del modelo de datos y la jerarquía
- **Tema:** diseño del modelo
- **Estado:** PENDIENTE DE EJECUTAR (no cuenta como evidencia hasta completar los campos «REAL»).
- **Herramienta / modelo / versión / fecha de uso (REAL):** COMPLETAR al ejecutarlo (p. ej. Claude en claude.ai, modelo mostrado en la interfaz, fecha).
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

## Resultado REAL — COMPLETAR
## Decisiones y cambios aplicados — COMPLETAR
