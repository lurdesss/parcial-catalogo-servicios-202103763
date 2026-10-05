# Análisis del Excel (`CatalogoServicios.xlsx`)

> **Estado:** reglas redactadas desde el enunciado y **verificadas contra el archivo real** el 2026-10-04
> (SHA-256 `de3b478a5faeeeaebce1aa7726e0e3321188a68e41bbb656e1d17b0c5b74dcf0`). Ver «Hallazgos con el archivo real».

## Estructura declarada
Hoja «Servicios Externos»; encabezados `A4:L4`; datos filas 5–101; listas de opciones `E112:H122` (E: S/N; F: clase; G: criticidad; H: tipo; 11 filas = 11 tipos, sin fila de encabezado).
Controles: 12 códigos N1 y 46 códigos N2 explícitos distintos. Las filas físicas ≠ servicios (celdas combinadas).

## Reglas implementadas (`app/importer.py`)
R1 celdas combinadas → valor de la celda principal solo dentro de su rango · R2 identidad por código N2 explícito, filas con el mismo código se agrupan ·
R3 conflicto de atributos → gana el primer valor, evidencia completa en `import_observations` y `source_notes`, o nombre canónico de `data/mapeo_importacion.json` ·
R4 filas sin código N2 con datos → omitidas y observadas, nunca asignadas ·
R5 ausentes = NULL, `review_status = revisar` · R6 códigos como texto, recorte de espacios con mapeo registrado · R7 idempotente.
Los encabezados se verifican; si no coinciden, la importación aborta y queda un `import_runs.status='error'`.

## Casos del enunciado
- **SE.12**: filas 99/100 con «Suministrar Analitica» y «Mantener Tableros de Control». Nombre canónico configurado: «Suministrar Analitica» (primera fila + nivel de agrupación). **Decisión provisional**; ambos valores quedan como evidencia.
- **SE.12.1–.3** como texto. Filas 99–101 con atributos incompletos → valores desconocidos + `revisar`.

## Hallazgos con el archivo real
- Una sola hoja, «Servicios Externos» (`A1:X1000`, 76 rangos combinados). Encabezados en `A4:L4` correctos. Listas en `E112:H122` con título «OPCIONES» en fila 111 (los valores coinciden con el enunciado).
- **Controles:** 12 N1 y 46 N2 ✔ (`import_runs.summary.control.coincide = true`). Importación: 58 creados; la repetición crea/actualiza 0.
- **ACTIVO:** 93 `S`, 1 `N`, 3 vacíos (los tres de SE.12). No hay valores desconocidos distintos de vacío.
- **SE.12:** B99 = «Suministrar Analitica», B100 = «Mantener Tableros de Control», A101 vacío. «Mantener Tableros de Control» es el nombre del N2 SE.12.3 (D101), de ahí que B100 parezca un valor desplazado del nivel 2. **Decisión: nombre N1 canónico = «Suministrar Analitica»** (evidencia de ambos valores conservada). Para SE.12.3 el N1 se infiere por el prefijo del código (observación `n1_inferido_por_prefijo`).
- **SE.12.1–.3:** sin ACTIVO, clase, criticidad ni tipo → NULL + `review_status = revisar`.
- **Filas sin código N2 fuera de combinación:** 42 y 67 (huecos entre `C40:C41`/`C43` y `C63:C66`/`C68:C73`); traen ACTIVO/clase/criticidad/tipo iguales a los de sus vecinos. Se documentan y **no se asignan** a ningún servicio (el enunciado lo prohíbe sin regla explícita).
- Los nombres del Excel se conservan tal cual, incluidas erratas (p. ej. SE.12.2 «Suministrar Análsis de Información»).
- Descripción: solo 1 celda con texto. Minimo/Maximo: sin valores numéricos que importar (no hay `valor_no_numerico`).
- 8 observaciones en total: 2 `fila_sin_codigo`, 1 `n1_inferido_por_prefijo`, 1 `conflicto_atributo`, 3 `atributos_incompletos`, 1 `lista_opciones`.
