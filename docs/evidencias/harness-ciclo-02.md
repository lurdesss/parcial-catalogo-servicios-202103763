# Harness — ciclo 02: error real de interfaz detectado por la prueba jsdom (fallo NO deliberado)

- **Herramienta / modelo:** Claude (claude.ai, Claude Sonnet 5.5) · **Fecha:** 2026-10-04
- **Tarea:** formulario de servicio N2 con selector de responsable dependiente de la sección.
- **Cambio propuesto por la IA:** `app/static/app.js` (`servicesView`/`editForm`, `fill`).
- **Control ejecutado:** script jsdom contra el servidor real (hoy versionado como `tests/ui/ui_smoke.js`).
- **Fallo detectado:** con la API devolviendo `[[2,"Demo consulta (consulta_demo)"]]` (log `OPTS`), el selector mostraba solo el placeholder:
  ```
  responsables ofrecidos para la sección: [ '— sin responsable —' ]
  FALLO TypeError: Cannot read properties of undefined (reading 'value')
  ```
- **Diagnóstico:** `Element.replaceChildren(a, lista.map(...))` nativo **no aplana arreglos**; convertía el arreglo en texto. Afectaba también a los filtros de la vista Servicios.
- **Corrección:** pasar los elementos con *spread*: `replaceChildren(op, ...lista.map(...))` (2 sitios). Regla agregada a `AGENTS.md` (contexto v2).
- **Nueva ejecución (salida literal):**
  ```
  responsables ofrecidos para la sección: [ '— sin responsable —', 'Demo consulta (consulta_demo)' ]
  con min>max -> El mínimo no puede ser mayor que el máximo.
  guardado -> Servicio guardado. | modal abierto: false
  ```
  y luego `node tests/ui/ui_smoke.js` → `UI OK` (exit 0).
- **Nota:** durante el desarrollo de `ui_smoke.js` un control falló por un error de la propia prueba (comprobaba los botones en la última vista); se corrigió y repitió.
- **Commit:** sin SHA propio: corrección anterior a la inicialización de Git, publicada en el primer commit completo
