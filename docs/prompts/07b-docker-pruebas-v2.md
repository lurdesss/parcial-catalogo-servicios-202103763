# Prompt 07b — Docker y pruebas, revisión (VERSIÓN 2, mejorada)
- **Tema:** pruebas / Docker · **Iteración de mejora n.º 2: prompt revisado**
- **Estado:** PENDIENTE DE EJECUTAR (no cuenta como evidencia hasta completar los campos «REAL»).
- **Herramienta / modelo / versión / fecha de uso (REAL):** COMPLETAR al ejecutarlo (p. ej. Claude en claude.ai, modelo mostrado en la interfaz, fecha).
- **Contexto a adjuntar:** `Dockerfile`, `compose.yaml`, `.dockerignore`, `.env.example`, `scripts/`, `README.md`, `tests/conftest.py`.
- **Resultado a comprobar ejecutando:** cada hallazgo se valida corriendo los comandos en una máquina con Docker, desde un clon limpio.

## Prompt (copiar tal cual)
```
<rol>Eres un ingeniero DevOps que prepara un proyecto para que un tercero lo clone y lo ejecute sin ayuda.</rol>

<contexto>
Criterio de entrega: tras clonar, configurar variables y ejecutar "docker compose up --build -d", todo debe funcionar sin instalar lenguaje, framework ni base de datos en el equipo anfitrión. Requisitos: Dockerfile, .dockerignore, compose.yaml, .env.example sin secretos reales; PostgreSQL con volumen persistente; el arranque espera a sus dependencias; documentar URL, puertos, versiones de Docker/Compose, logs, detención y reinicio, separando el apagado normal del reinicio destructivo; migraciones, importación, cuentas de evaluación y pruebas ejecutables en contenedores; pruebas que aíslen sus datos de los de evaluación; el Excel original no debe alterarse. Stack: Flask + gunicorn + PostgreSQL 16; servicios db, app, db_test y tests (perfil test), ui_tests (perfil ui).
</contexto>

<tarea>Simula mentalmente un clon limpio y recorre el README paso a paso. Identifica todo lo que podría fallar: variables sin definir, orden de arranque, permisos de archivos en el volumen o en el montaje ./data, contraseñas con caracteres especiales en la URL de la BD, migraciones que corren dos veces con varios workers, healthchecks, puertos ocupados, tamaño/caché de la imagen, imagen de pruebas vs. producción, que "docker compose down -v" no aparezca en el procedimiento normal, y si las pruebas pueden tocar la BD de evaluación.</tarea>

<restricciones>
- No agregues servicios ni herramientas fuera del stack indicado.
- No sugieras guardar secretos reales en el repositorio.
- Cada riesgo debe llevar el comando exacto que lo comprueba y el resultado que indicaría que está bien.
- Distingue "fallará seguro" de "podría fallar según el entorno".
</restricciones>

<formato_de_salida>Lista ordenada por probabilidad de fallo: Riesgo | Archivo/línea | Comando de comprobación | Resultado esperado | Corrección mínima. Termina con un checklist de 10 pasos "clon limpio → todo verde" que pueda ejecutar una persona.</formato_de_salida>

<criterio_de_aceptacion>Cada riesgo es verificable con un comando; el checklist final se puede ejecutar de principio a fin.</criterio_de_aceptacion>
```

## Resultado comprobado — COMPLETAR
(comparar con 07a; qué riesgos se confirmaron al ejecutar los comandos en Docker; correcciones y commit)
