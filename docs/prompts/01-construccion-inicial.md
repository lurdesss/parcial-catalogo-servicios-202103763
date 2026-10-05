# Prompt 01 — construcción inicial del proyecto (REAL)

- **Tema:** modelo + autenticación + importación + pruebas/Docker (arranque del proyecto)
- **Herramienta, modelo, fecha:** Claude (claude.ai), Claude Sonnet 5.5 · 2026-10-04
- **Objetivo:** generar el código base de la aplicación a partir del enunciado del parcial.
- **Contexto suministrado:** texto completo del enunciado (Software Avanzado, 25 pts). **No se adjuntó** `CatalogoServicios.xlsx`.
- **Instrucciones (texto literal del usuario):** «comienza a realizar el codigo para esto que te estoy pidiendo» (con el enunciado adjunto).
- **Restricciones (del enunciado):** autenticación local, hash con sal, roles, PostgreSQL preferente, Docker, importación repetible con casos SE.12/celdas combinadas, 12 N1 / 46 N2, pruebas P01–P12, documentación Markdown.
- **Salida esperada:** repositorio ejecutable con `docker compose up --build -d`.
- **Criterio de aceptación:** `scripts/check.sh` en 0; humo HTTP y UI en verde; importación idempotente.
- **Resultado real:** código generado; el asistente advirtió que faltaba el Excel y **no inventó su contenido**: probó el importador con un libro sintético (`tests/synthetic_xlsx.py`). Fallos encontrados y corregidos: ver `docs/evidencias/harness-ciclo-0*.md`.
- **Limitación honesta:** este fue un único prompt amplio. El enunciado exige ≥5 prompts utilizados y 2 iteraciones de mejora.

## Pendiente de registrar por el estudiante (con prompts REALES que use)
Use `PLANTILLA.md` para: (2) análisis del Excel real, (3) ajuste del modelo/importador tras ver el archivo, (4) autenticación/seguridad, (5) pruebas o Docker. Para la iteración de mejora, guarde el prompt inicial, el problema observado, el prompt revisado y el resultado comprobado. **No invente prompts que no haya usado.**
