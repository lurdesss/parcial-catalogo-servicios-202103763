# Prompt 13 — Generador reproducible de CMDB y grafo de dependencias (Grafo 1)

- **N.º / tema:** CMDB — generador de 5000 dispositivos + grafo de relaciones técnicas
- **Herramienta, modelo y versión · fecha de uso:** Claude Code (Claude Sonnet 5) · 2026-10-29
- **Objetivo:** generador reproducible por semilla que inserte ≥5000 dispositivos distintos (enunciado §8), y un
  recorrido de dependencias para identificar servicios potencialmente afectados por un CI, sin usar IA ni librerías
  de datos sintéticos externas (debe funcionar sin suscripción de IA).
- **Contexto suministrado:** `app/models.py` (Device, DeviceRelation, ServiceCiLink), `docs/contexto/05-cmdb-jerarquia.md`.
- **Instrucciones:** "Usa solo `random.Random(seed)` y listas curadas, nada de Faker. El `asset_tag` debe ser
  determinista a partir de la semilla para que repetir la carga actualice en vez de duplicar. depende_de/alojado_en no
  deben admitir ciclos; conectado_a sí."
- **Restricciones:** nunca asignar IP a una clase que no la requiere; el total debe contar dispositivos, no filas de
  catálogos ni relaciones.
- **Salida esperada:** `app/cmdb_generator.py` (`generate(seed, count)`), `app/graph_cmdb.py`
  (`would_create_cycle_relation`, `impact_of`, `affected_services`), comando `flask generate-cmdb`.
- **Criterio de aceptación:** generar 5000 reporta exactamente 5000 creados la primera vez y 0 creados/5000
  actualizados la segunda; `tests/test_cmdb.py::test_P14…` verifica que un ciclo `depende_de` se rechaza y que
  `conectado_a` sí lo admite.
- **Resultado real y observaciones:** `flask generate-cmdb --seed 7 --count 5000` tardó 1.7 s y produjo
  `creados=5000, actualizados=0`; repetir con `--seed 42 --count 500` dos veces dio `creados=500/actualizados=0` y
  luego `creados=0/actualizados=500` (idempotente, verificado con el conteo real de filas en `devices`, no solo con
  el mensaje del comando). `tests/test_cmdb.py::test_P14…` confirma el rechazo de ciclos y el recorrido de impacto.
