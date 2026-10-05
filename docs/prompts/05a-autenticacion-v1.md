# Prompt 05a — Autenticación, revisión (VERSIÓN 1, deliberadamente genérica)
- **Tema:** autenticación · **Iteración de mejora n.º 1: versión inicial**
- **Estado:** USADO (real).
- **Herramienta / modelo / versión / fecha de uso (REAL):** Claude Code (extensión de VS Code), modelo Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-04 ~22:44, con solo `app/security.py` y `app/api/auth.py` como contexto.
- **Propósito:** ejecutar PRIMERO este prompt breve, anotar sus carencias reales y luego ejecutar 05b. Si la respuesta resulta buena, regístrelo así; no fuerce un «problema» que no ocurrió.

## Prompt (copiar tal cual)
```
Revisa la seguridad de mi autenticación y dime si está bien. Código adjunto: app/security.py y app/api/auth.py.
```

## Extracto de la respuesta
«En general está bien: contraseñas con scrypt y sal (`hash_password`), comparación contra un hash ficticio cuando el usuario no existe (`authenticate`), sesión del lado del servidor con el token guardado como SHA-256, CSRF comparado con `hmac.compare_digest` y política de denegar por defecto en `guard_request`. Recomendaciones: limitar intentos de login, exigir contraseñas más complejas, rotar el token de sesión y revisar las cookies.»

## Problema observado
La respuesta no fue incorrecta, pero sí insuficiente para decidir algo:
1. **Concluyó «está bien» sin poder verificarlo:** las banderas de la cookie (HttpOnly, SameSite, Secure) se configuran fuera de los dos archivos adjuntos; solo dijo «revisar las cookies».
2. **No revisó la autorización por rol más allá de las escrituras:** no se preguntó si un usuario `consulta` puede leer datos sensibles por GET (p. ej. la lista de usuarios), porque el prompt no daba las reglas de negocio.
3. **No cubrió la revocación de sesiones** al desactivar un usuario ni la regla del último admin (están en `org.py`, que no se adjuntó).
4. **Recomendaciones genéricas sin prioridad ni severidad** (bloqueo por intentos y complejidad de contraseñas), y ninguna prueba propuesta para comprobarlas.

Conclusión: hace falta dar rol, reglas, amenazas concretas, formato con severidad y pedir pruebas → versión 05b.
