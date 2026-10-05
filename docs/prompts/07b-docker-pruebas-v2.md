# Prompt 07b — Docker y pruebas, revisión (VERSIÓN 2, mejorada)
- **Tema:** pruebas / Docker · **Iteración de mejora n.º 2: prompt revisado**
- **Estado:** USADO (real).
- **Herramienta / modelo / versión / fecha de uso (REAL):** Claude Code (extensión de VS Code), modelo Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-04 ~22:51, después de 07a, con el contexto completo y los comandos ejecutados en Docker 29.7.2 / Compose v5.4.0 (Windows 11).
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

## Resultado comprobado
| Riesgo | Archivo/línea | Comando de comprobación | Resultado esperado | Estado real / corrección |
|---|---|---|---|---|
| Ejecutar el humo o la persistencia sin cuentas de evaluación — **fallará seguro** si se salta un paso | `README.md` l. 16, `scripts/smoke.py::admin` | `docker compose exec -T app python scripts/smoke.py flow` | todos `[OK]` | **Confirmado**: falló sin `setup_eval.sh` y pasó tras ejecutarlo (`harness-ciclo-04.md`); anotado en AGENTS.md |
| Falta `.env` — **fallará seguro** | `compose.yaml` (`env_file: .env`, `POSTGRES_PASSWORD:?`) | `docker compose config >/dev/null` sin `.env` | error explícito | mitigado: el README empieza con `cp .env.example .env` |
| `SECRET_KEY` sugerida con `python3` en el anfitrión — contradice «nada instalado» | `.env.example` l. 7 | — | — | **Corregido**: ahora se genera con `docker run --rm python:3.12-slim python -c …` |
| Contraseña con `@`, `/` o `:` rompe `DATABASE_URL` — **según el entorno** | `compose.yaml` (`DATABASE_URL`) | `docker compose exec -T app alembic current` | revisión `0001` sin error | mitigado: `.env.example` l. 2 exige solo letras y números |
| Permisos de `./data:ro` para uid 10001 — **según el entorno** (Linux con umask restrictivo) | `compose.yaml` (montaje), `Dockerfile` (`useradd --uid 10001`) | `docker compose exec -T app sh -c 'id; ls -l /srv/data'` | el archivo es legible por `appuser` | verificado en Windows: `uid=10001`, archivo legible; la importación leyó 58 servicios |
| Migraciones duplicadas con 2 workers | `scripts/entrypoint.sh` | `docker compose logs app \| grep -c "Aplicando migraciones"` | 1 por arranque | verificado: los logs muestran 2 «Aplicando migraciones» y 4 «Booting worker» en 2 arranques (inicial + `restart` de P12), es decir, una migración por arranque y 2 workers; `alembic upgrade head` corre en el entrypoint **antes** de `exec gunicorn` |
| Las pruebas tocan la BD de evaluación | `compose.yaml` (`tests` → `db_test` en `tmpfs`) | ejecutar `tests` y después `smoke.py flow` | los datos de evaluación siguen ahí | verificado: tras 4 ejecuciones de `tests`, `persistence_check.sh` y el smoke siguieron encontrando los datos |
| `down -v` en el procedimiento normal | `README.md` l. 46–48 | `grep -n "down" README.md` | solo `down`; `-v` aparte como destructivo | verificado |
| Puerto 8000 ocupado — **según el entorno** | `.env.example` `APP_PORT` | `docker compose ps` | `app` *healthy* | configurable con `APP_PORT` |
| Imagen de pruebas en producción | `Dockerfile` (`target runtime` / `test`) | `docker image ls` | `app` sin pytest | `app` 261 MB, `tests` 329 MB (etapas separadas); `.dockerignore` excluye `.env`, `.git` y `docs` |

**Checklist «clon limpio → todo verde»:** 1) `git clone … && cd …` · 2) `cp .env.example .env` y editar `POSTGRES_PASSWORD` (alfanumérica) y `SECRET_KEY` · 3) `docker compose version` (v2) · 4) `docker compose up --build -d` · 5) `docker compose ps` → `db` y `app` *healthy* · 6) `sh scripts/setup_eval.sh` → N1=12, N2=46, coincide=true · 7) `docker compose --profile test run --rm --build tests` → CONTROLES OK · 8) `docker compose exec -T app python scripts/smoke.py flow` → todos `[OK]` · 9) `sh scripts/persistence_check.sh` → P12 OK · 10) abrir http://localhost:8000 e iniciar sesión con `admin_demo`.

**Comparación con 07a:** 07a respondió «deberían funcionar» sin comandos; 07b obligó a dar un comando y un criterio por riesgo y a separar «fallará seguro» de «según el entorno». Así salieron a la luz la dependencia de `setup_eval.sh` (que sí falló de verdad) y la inconsistencia de `.env.example`. Los pasos 4 a 9 del checklist se ejecutaron realmente el 2026-10-04 (ver `docs/RESOLUCION.md` §8); el paso 1 (clon limpio desde la etiqueta) **no** se ejecutó.

## Correcciones
`.env.example`: generación de `SECRET_KEY` sin herramientas en el anfitrión. La dependencia de `setup_eval.sh` quedó documentada en AGENTS.md (v5).
