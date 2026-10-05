# Prompt 05b — Autenticación, revisión (VERSIÓN 2, mejorada)
- **Tema:** autenticación · **Iteración de mejora n.º 1: prompt revisado**
- **Estado:** USADO (real).
- **Herramienta / modelo / versión / fecha de uso (REAL):** Claude Code (extensión de VS Code), modelo Claude Opus 5.5 (`claude-opus-5-5`), 2026-10-04 ~22:45. Ejecutado después de 05a con el contexto ampliado (`security.py`, `auth.py`, `org.py`, `config.py`, `serializers.py`, `tests/test_auth.py`).
- **Cambios respecto a 05a (buenas prácticas aplicadas):** rol definido, contexto y requisitos explícitos, lista de amenazas a revisar, restricciones, formato de salida, criterio de aceptación y petición de pruebas.
- **Contexto a adjuntar:** `app/security.py`, `app/api/auth.py`, `app/api/org.py`, `tests/test_auth.py`, `docs/contexto/01-reglas-de-negocio.md`.

## Prompt (copiar tal cual)
```
<rol>Eres un revisor de seguridad de aplicaciones web (OWASP ASVS nivel 1) que audita una autenticación local en Flask.</rol>

<contexto>
Requisitos del proyecto: login local usuario/correo + contraseña validado contra la BD; contraseñas con hash especializado y sal (nunca texto plano ni cifrado reversible); rutas y operaciones protegidas EN EL SERVIDOR; dos roles (administrador: mantiene usuarios, organización y catálogos; consulta: solo lectura y sin acceso a hashes/secretos); usuarios desactivados no pueden acceder; el cierre de sesión debe invalidar la sesión; credenciales de evaluación solo de demostración y sin secretos reales en Git. Implementación: sesiones en tabla user_sessions (SHA-256 del token), cookie firmada con solo el token, CSRF por cabecera X-CSRF-Token, política por defecto-denegar en guard_request.
</contexto>

<tarea>Revisa el código adjunto buscando incumplimientos de los requisitos y debilidades en: hash y política de contraseñas; enumeración de usuarios y temporización; fijación y expiración de sesión; invalidez de sesión tras logout, desactivación o cambio de contraseña; CSRF; escalada de privilegios (¿algún endpoint de escritura accesible al rol consulta?); fuga de password_hash en alguna respuesta; protección contra fuerza bruta (indica si falta); configuración de cookies y SECRET_KEY.</tarea>

<restricciones>
- Distingue "defecto real" de "mejora opcional"; no reportes riesgos que el código ya mitiga sin explicar por qué no aplican.
- No propongas proveedores externos de login ni dependencias de IA.
- Cada hallazgo debe citar archivo y función y explicar cómo explotarlo o probarlo.
- Si algo no se puede concluir con el código adjunto, escribe "no verificable con lo adjunto".
</restricciones>

<formato_de_salida>1) Veredicto en 3 líneas. 2) Tabla: # | Hallazgo | Archivo/función | Severidad | Cómo reproducirlo | Corrección mínima. 3) Lista de pruebas automáticas adicionales (nombre + qué afirma) que aún no están en tests/test_auth.py.</formato_de_salida>

<criterio_de_aceptacion>Todo hallazgo es reproducible con una petición HTTP o una prueba; sin recomendaciones genéricas.</criterio_de_aceptacion>
```

## Resultado comprobado
**Veredicto:** no se encontraron defectos reales que incumplan los requisitos. Las amenazas pedidas están mitigadas en el servidor; las mejoras pendientes son opcionales (fuerza bruta, cookie `Secure` por defecto). Se añadieron 2 pruebas que antes faltaban.

| # | Hallazgo | Archivo/función | Severidad | Cómo reproducirlo | Corrección mínima |
|---|---|---|---|---|---|
| 1 | Sin límite de intentos de login (fuerza bruta) | `auth.py::login` | mejora opcional (ya declarada como limitación) | N peticiones `POST /api/auth/login` con clave errónea → siempre 401, nunca bloqueo | contador por usuario/IP; fuera de alcance |
| 2 | `SESSION_COOKIE_SECURE` es falso por defecto | `config.py` l. 18 | mejora opcional | el `Set-Cookie` del login no lleva `Secure` | `COOKIE_SECURE=1` cuando se sirva por HTTPS (ya configurable) |
| 3 | El cambio de contraseña revoca las sesiones del usuario: **mitigado, pero sin prueba** | `org.py::update_user` (`revoke_user_sessions`) | — | prueba nueva `test_cambio_de_password_revoca_sesiones` | — |
| 4 | Fijación de sesión: **mitigada** (`start_session` hace `session.clear()` y emite un token nuevo; una cookie impuesta no existe en `user_sessions`), pero sin prueba | `security.py::start_session` | — | prueba nueva `test_login_emite_sesion_nueva_sin_fijacion` | — |

Descartados con explicación (no aplican): enumeración por tiempo (`authenticate` compara contra `_DUMMY_HASH` y devuelve el mismo 401); fuga de `password_hash` (`user_dict` no lo incluye; `test_P03` lo afirma); escalada de privilegios (`guard_request` exige admin en todo POST/PUT/PATCH/DELETE salvo logout; `test_P03` lo recorre); CSRF (`hmac.compare_digest`, `test_csrf_requerido_en_escrituras`); `SECRET_KEY` vacía (`app/__init__.py` aborta el arranque); usuario desactivado (`_load_session` lo rechaza; `test_P02`).

**Comparación con 05a:** 05a dijo «está bien» con consejos genéricos; 05b recorrió cada amenaza con archivo y función, separó defecto de mejora, descartó riesgos explicando por qué y produjo pruebas concretas.

**Comprobación:** se agregaron ambas pruebas a `tests/test_auth.py` y se ejecutó `docker compose --profile test run --rm --build tests` → ruff OK, **33 passed** (antes 31). Ningún hallazgo resultó ser falso positivo y no se encontró ningún defecto que requiriera cambiar código de la aplicación.
