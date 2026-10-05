# Prompt 05b — Autenticación, revisión (VERSIÓN 2, mejorada)
- **Tema:** autenticación · **Iteración de mejora n.º 1: prompt revisado**
- **Estado:** PENDIENTE DE EJECUTAR (no cuenta como evidencia hasta completar los campos «REAL»).
- **Herramienta / modelo / versión / fecha de uso (REAL):** COMPLETAR al ejecutarlo (p. ej. Claude en claude.ai, modelo mostrado en la interfaz, fecha).
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

## Resultado comprobado — COMPLETAR
(comparar con 05a: qué mejoró; qué hallazgos se confirmaron ejecutando una prueba/petición, cuáles eran falsos positivos; commit)
