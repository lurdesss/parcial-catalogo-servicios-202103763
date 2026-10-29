# Prompt 09a — Diseño de la jerarquía CMDB (v1, incompleto)

- **N.º / tema:** modelo — jerarquía de clasificación de CI
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** diseñar `ci_classes` reproduciendo "los niveles, denominaciones y relaciones de la lección 22 y de
  `CMDB.xlsx`" (enunciado §2).
- **Contexto suministrado:** `CMDB.xlsx` y `Service Desk.pptx.pdf` (únicas fuentes disponibles en ese momento).
- **Instrucciones:** "Diseña la jerarquía de clasificación de CI a partir de estas dos fuentes."
- **Restricciones:** no inventar una clasificación y presentarla como transcripción de la "lección 22".
- **Salida esperada:** árbol de clases de CI con cita de la fuente para cada nivel.
- **Criterio de aceptación:** cada nodo del árbol debe tener una celda o diapositiva de origen citable.
- **Resultado real y observaciones:** **no se pudo completar.** Ninguna de las dos fuentes entregadas define niveles
  más allá de los dos ejemplos "Hardware"/"Software" de `CMDB.xlsx`. Se decidió no inventar y, en su lugar, preguntar
  al responsable del proyecto por la "lección 22" (no incluida todavía) — ver Prompt 09b.
- **Iteración:** prompt inicial → problema observado (fuente insuficiente) → prompt revisado (09b) → resultado
  comprobado.
