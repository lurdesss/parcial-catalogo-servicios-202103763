# Jerarquía de clasificación de CI — decisión de proyecto documentada

## Por qué es una decisión de proyecto y no una transcripción de fuente
El enunciado de Parcial 3 (§2) exige: *"La jerarquía de la CMDB debe reproducir los niveles, denominaciones y
relaciones de la lección 22 y de `CMDB.xlsx`… No sustituya esa jerarquía por… una clasificación inventada."* El propio
enunciado anticipa, en su nota editorial final, que el catedrático **no pudo verificar** el contenido de `CMDB.xlsx` ni
disponía de una "lección 22" independiente, por lo que **no enumera niveles**. Verificado el material realmente
entregado (ver `04-parcial3-alcance.md`):

- `CMDB.xlsx` (hoja `CMDB`, `B4:U6`): 20 columnas de atributos (Nombre del CI, Tipo de CI, Descripción, Número de
  Serie, Versión, Fecha de Adquisición, Estado Actual, Relaciones, Padres/Hijos, Ubicación Física,
  Propietario/Responsable, Fecha de Cambio, Descripción del Cambio, Documentación relacionada, Enlaces a Incidentes y
  Problemas, Niveles de Seguridad, Cumplimiento, Estado de Configuración, Número de Licencia, Fecha de Vencimiento) y
  **2 filas de ejemplo**: `Servidor1` (Tipo de CI = `Hardware`) y `Aplicación` (Tipo de CI = `Software`).
- `Transicion.pptx.pdf`, página 11 ("Transición de servicios ITIL — CMDB: Configuration Management Database — Campos
  que debería contemplar"): la **misma lista de campos** (identificación, atributos, relaciones y dependencias,
  ubicación y asignación, historial de cambios, documentación y enlaces, seguridad y cumplimiento, estado de
  configuración, licencias), confirmando que ambas fuentes describen el **mismo modelo conceptual de campos**, no una
  taxonomía de clases.
- Página 12 de la misma fuente: *"[Los CI] deberían seleccionarse usando criterios de selección establecidos,
  agruparse, clasificarse e identificarse…"* — un principio general, sin nombrar niveles concretos.

No existe, por tanto, una fuente verificable con una taxonomía de clases de CI más allá de los dos ejemplos
`Hardware`/`Software`. Inventar niveles y presentarlos como provenientes de "la lección 22" violaría la instrucción
explícita del enunciado; se optó en cambio por diseñar una jerarquía **razonable, configurable y declarada como
decisión propia**, partiendo de esos dos valores de ejemplo y de práctica ITIL estándar de clasificación de activos.

## Jerarquía implementada (`app/reference_data.py::CI_CLASSES`, sembrada por la migración 0002)
```
Hardware (HW)                         Software (SW)                 Documentación (DOC)    Instalaciones (FAC)
├─ Servidor (HW.SRV)  [requiere IP]    ├─ Sistema operativo (SW.OS)  ├─ Manual (DOC.MAN)     ├─ Centro de datos (FAC.DC)
├─ Estación de trabajo (HW.WKS)        ├─ Aplicación (SW.APP)        └─ Procedimiento          └─ Sala de servidores (FAC.SRV)
├─ Equipo de red (HW.NET) [requiere IP]├─ Base de datos (SW.DB)          (DOC.PROC)
├─ Almacenamiento (HW.STO)             └─ Licencia (SW.LIC)
└─ Periférico (HW.PER)
```
- Los dos nodos raíz `Hardware`/`Software` son los únicos valores que SÍ provienen de una fuente verificada
  (`CMDB.xlsx!C5:C6`). Sus hijos son una subdivisión estándar y editable (tabla `ci_classes`, autorreferenciada,
  mantenible desde la pantalla "CMDB — Clases" como cualquier otro catálogo).
- `requires_ip` es solo un dato orientativo usado por el generador sintético (§8 del enunciado: *"No asigne una
  dirección IP obligatoria a dispositivos que no la requieran"*); nunca se exige a nivel de base de datos — `ip_address`
  es `NULL`able para **todas** las clases, incluidas las que tienen `requires_ip = True`.
- Se valida que una clase con subclases activas no pueda recibir dispositivos directamente (`app/api/cmdb.py::_device_values`,
  error `not_leaf_class`), y que la jerarquía no admita ciclos (`app/graph_cmdb.py::would_create_cycle_classification`,
  probado en `tests/test_cmdb.py::test_P04…`).

## Trazabilidad de la decisión
- Hallazgo y pregunta al responsable: ver el historial de esta conversación (sesión de construcción, 2026-10-29) y
  `docs/contexto/04-parcial3-alcance.md`.
- Commit que introduce esta documentación y la jerarquía: ver `docs/contexto/CAMBIOS.md`.
