# Registro de prompts

| N.º | Archivo | Tema | Estado | Iteración |
|---|---|---|---|---|
| 1 | `01-construccion-inicial.md` | Construcción inicial (modelo, auth, importación, Docker) | **Usado (real)** | — |
| 2 | `03-analisis-excel.md` | Análisis del Excel | **Usado (real)** | Sin cambios de código; confirmó 12/46, filas 42/67 y SE.12; nuevo: espacio en I5 |
| 3 | `04-modelo-datos.md` | Diseño del modelo | **Usado (real)** | Sin cambios; `alembic check` OK; reglas solo-app declaradas |
| 4 | `05a` → `05b` | Autenticación | Pendiente de ejecutar | **Mejora 1**: v1 genérico → v2 estructurado |
| 5 | `06-importador-casos-borde.md` | Importación | Pendiente de ejecutar | — |
| 6 | `07a` → `07b` | Pruebas / Docker | Pendiente de ejecutar | **Mejora 2**: v1 genérico → v2 estructurado |

## Cómo usar este registro (para que la evidencia sea real)
1. Adjunte los archivos indicados y pegue el prompt **tal cual**. Ejecute siempre la versión `a` antes de la `b`.
2. Complete en el archivo: herramienta, modelo/versión y fecha **reales**; un extracto de la respuesta; qué comprobó ejecutando (comando y salida); qué aceptó y qué descartó.
3. Cambie el estado a «Usado (real)» **solo** cuando lo haya ejecutado. Si un prompt no se usa, déjelo como pendiente o bórrelo; no lo presente como usado.
4. Si el resultado de v1 fue bueno, dígalo: la mejora debe describir lo que realmente observó.

## Buenas prácticas aplicadas en los prompts
Rol explícito · contexto con archivos nombrados · una tarea verificable · restricciones y alcance · regla de datos no confiables · formato de salida fijo · criterio de aceptación comprobable · «no verificable» permitido (evita alucinar) · cada hallazgo debe poder reproducirse con un comando o prueba.
