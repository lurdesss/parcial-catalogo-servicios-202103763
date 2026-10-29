# Prompt 08 — Análisis de las fuentes de Parcial 3 (CMDB.xlsx, PDF)

- **N.º / tema:** análisis del Excel y fuentes de CMDB / Service Desk
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** determinar con precisión qué contiene realmente cada fuente entregada (`CMDB.xlsx`,
  `Service Desk.pptx.pdf`) antes de diseñar el modelo, para no inventar datos ni presentarlos como provenientes de una
  fuente que no los tiene.
- **Contexto suministrado:** enunciado completo de Parcial 3; `CMDB.xlsx` (leído con `openpyxl`, celda por celda);
  `Service Desk.pptx.pdf` (16 diapositivas, leídas íntegras).
- **Instrucciones:** "Lee CMDB.xlsx con openpyxl (hoja, dimensiones, todas las celdas no vacías) y el PDF completo;
  reporta estructura real, no un resumen genérico de qué debería tener una CMDB."
- **Restricciones:** no asumir contenido no verificado; si una fuente no alcanza para un requisito del enunciado, debe
  decirse explícitamente en vez de rellenar con texto genérico.
- **Salida esperada:** inventario exacto de columnas/filas de `CMDB.xlsx` y de qué diapositiva respalda cada dato del
  enunciado (niveles de soporte, tipos de ticket, eventos E0–E3, incidentes I0–I6).
- **Criterio de aceptación:** cada afirmación debe poder verificarse releyendo el archivo citado.
- **Resultado real y observaciones:** `CMDB.xlsx` resultó ser una plantilla de 20 columnas con solo 2 filas de ejemplo
  (`Servidor1`=Hardware, `Aplicación`=Software), **no** una taxonomía. `Service Desk.pptx.pdf` sí respalda íntegramente
  las diapositivas 11–16 ya citadas en el enunciado §7. Esto llevó directamente al Prompt 09 (no había jerarquía CMDB
  verificable con lo entregado).
