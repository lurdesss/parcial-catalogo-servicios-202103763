# Prompt 07a — Docker y pruebas, revisión (VERSIÓN 1, deliberadamente genérica)
- **Tema:** pruebas / Docker · **Iteración de mejora n.º 2: versión inicial**
- **Estado:** USADO (real).
- **Herramienta / modelo / versión / fecha de uso (REAL):** Claude Code (extensión de VS Code), modelo Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-04 ~22:50, con solo `Dockerfile` y `compose.yaml` como contexto.
- **Propósito:** ejecutar primero; registrar honestamente lo que faltó.

## Prompt (copiar tal cual)
```
Revisa mi Dockerfile y compose.yaml y dime si van a funcionar.
```

## Extracto de la respuesta
«Sí, deberían funcionar: imagen `python:3.12-slim` con usuario sin privilegios (uid 10001), `depends_on` con `service_healthy`, healthchecks en `db` y `app`, volumen `pgdata` para persistencia, Excel montado `:ro`, perfil `test` con PostgreSQL efímero en `tmpfs` y `POSTGRES_PASSWORD` obligatoria con `:?`. Sugerencias: fijar versiones exactas de las imágenes y usar `.dockerignore`.»

## Problema observado
La respuesta describió bien los archivos, pero respondió «van a funcionar» **sin ejecutar nada** y quedó corta frente a lo que pasó de verdad:
1. **No detectó el fallo que sí ocurrió** en la validación del 2026-10-04 (`docs/evidencias/harness-ciclo-04.md`): `smoke.py flow` y `persistence_check.sh` fallan si antes no se ejecuta `setup_eval.sh`. Es una dependencia entre scripts, invisible desde `Dockerfile`/`compose.yaml`.
2. **No dijo qué no podía verificar con lo adjunto**: el `entrypoint.sh` (reintentos de migración con 2 workers de gunicorn), los permisos del montaje `./data:ro` para uid 10001 en Linux, ni qué pasa si falta `.env` (`env_file: .env` lo exige).
3. **No propuso comandos ni criterios** para comprobarlo (servicio `tests`, smoke, reinicio con persistencia), ni separó «funciona» de «está demostrado».

Conclusión: hay que pedir ejecución real, lista de comandos con criterio de éxito y explicitar lo no verificable → versión 07b.