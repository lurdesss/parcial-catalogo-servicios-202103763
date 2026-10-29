# Prompt 09b — Diseño de la jerarquía CMDB (v2, con `Transicion.pptx.pdf` y decisión documentada)

- **N.º / tema:** modelo — jerarquía de clasificación de CI
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** cerrar el vacío del Prompt 09a: obtener la fuente real de la "lección 22" o, si no existe, diseñar una
  jerarquía razonable y declararla explícitamente como decisión de proyecto (nunca como dato de una fuente inexistente).
- **Contexto suministrado:** respuesta del responsable del proyecto ("lección 22 no es más que el espacio en el que se
  almacenaba CMDB.xlsx"); `Transicion.pptx.pdf` (25 diapositivas, aportado en ese momento y leído completo).
- **Instrucciones:** "Verifica si Transicion.pptx.pdf trae niveles de clasificación de CI. Si tampoco los trae, diseña
  una jerarquía configurable basada en los dos ejemplos de CMDB.xlsx + práctica ITIL estándar, y documenta el vacío."
- **Restricciones:** las mismas del Prompt 09a; además, la jerarquía debe quedar en una tabla editable (no un enum
  fijo en código), porque el enunciado pide poder mantenerla como catálogo.
- **Salida esperada:** `app/reference_data.py::CI_CLASSES` + `docs/contexto/05-cmdb-jerarquia.md` con la justificación.
- **Criterio de aceptación:** la migración siembra la jerarquía sin error; `tests/test_cmdb.py::test_P04…` verifica
  que no admite ciclos y que las clases no-hoja rechazan dispositivos.
- **Resultado real y observaciones:** `Transicion.pptx.pdf` p.9–14 confirmó el modelo conceptual de campos de CMDB
  (coincide con las columnas de `CMDB.xlsx`) pero tampoco trae niveles. Se implementó la jerarquía de
  `docs/contexto/05-cmdb-jerarquia.md` (Hardware/Software/Documentación/Instalaciones con 13 subclases). Verificado:
  `alembic upgrade head` sobre SQLite limpio sembró 17 `ci_classes`; `pytest tests/test_cmdb.py` → 10 passed.
- **Iteración:** prompt inicial (09a, sin fuente suficiente) → problema observado → prompt revisado (este) → resultado
  comprobado con pruebas reales.
