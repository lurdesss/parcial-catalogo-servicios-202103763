# Registro de prompts

| N.º | Archivo | Tema | Estado | Iteración |
|---|---|---|---|---|
| 1 | `01-construccion-inicial.md` | Construcción inicial (modelo, auth, importación, Docker) | **Usado (real)** | — |
| 2 | `03-analisis-excel.md` | Análisis del Excel | **Usado (real)** | Sin cambios de código; confirmó 12/46, filas 42/67 y SE.12; nuevo: espacio en I5 |
| 3 | `04-modelo-datos.md` | Diseño del modelo | **Usado (real)** | Sin cambios; `alembic check` OK; reglas solo-app declaradas |
| 4 | `05a` → `05b` | Autenticación | **Usado (real)** (05a y 05b) | **Mejora 1**: v1 genérico → v2 estructurado |
| 5 | `06-importador-casos-borde.md` | Importación | **Usado (real)** | Defecto confirmado (filas >101 sin observación) → corregido + prueba |
| 6 | `07a` → `07b` | Pruebas / Docker | **Usado (real)** (07a y 07b) | **Mejora 2**: v1 genérico → v2 estructurado |

### Parcial 3

| N.º | Archivo | Tema | Estado | Iteración |
|---|---|---|---|---|
| 7 | `08-analisis-cmdb-service-desk.md` | Análisis de fuentes (CMDB.xlsx, PDF) | **Usado (real)** | — |
| 8 | `09a` → `09b` | Jerarquía CMDB | **Usado (real)** (09a y 09b) | **Mejora 1**: fuente insuficiente → se obtiene `Transicion.pptx.pdf` y se documenta la decisión |
| 9 | `10-modelo-ampliado.md` | Modelo (CMDB + Service Desk) | **Usado (real)** | — |
| 10 | `11-colas-y-roles.md` | Colas, permisos, roles múltiples | **Usado (real)** | — |
| 11 | `12-motor-tickets-procesos.md` | Motor de tickets, Grafo 2 | **Usado (real)** | — |
| 12 | `13-generador-cmdb-grafo-dependencias.md` | Generador CMDB, Grafo 1 | **Usado (real)** | — |
| 13 | `14a` → `14b` | Datos de demostración de Service Desk | **Usado (real)** (14a y 14b) | **Mejora 2**: actor único (403 real) → actor por acción |
| 14 | `15-pruebas-docker.md` | Pruebas P03–P18 | **Usado (real)** | — |

## Cómo usar este registro (para que la evidencia sea real)
1. Adjunte los archivos indicados y pegue el prompt **tal cual**. Ejecute siempre la versión `a` antes de la `b`.
2. Complete en el archivo: herramienta, modelo/versión y fecha **reales**; un extracto de la respuesta; qué comprobó ejecutando (comando y salida); qué aceptó y qué descartó.
3. Cambie el estado a «Usado (real)» **solo** cuando lo haya ejecutado. Si un prompt no se usa, déjelo como pendiente o bórrelo; no lo presente como usado.
4. Si el resultado de v1 fue bueno, dígalo: la mejora debe describir lo que realmente observó.

## Buenas prácticas aplicadas en los prompts
Rol explícito · contexto con archivos nombrados · una tarea verificable · restricciones y alcance · regla de datos no confiables · formato de salida fijo · criterio de aceptación comprobable · «no verificable» permitido (evita alucinar) · cada hallazgo debe poder reproducirse con un comando o prueba.
