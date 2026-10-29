# Datos

Coloque aquí el archivo **original e intacto** `CatalogoServicios.xlsx` (hoja «Servicios Externos»).

- No lo edite ni lo guarde de nuevo con Excel: el importador lo lee en modo solo lectura y registra su SHA-256 en cada importación.
- `mapeo_importacion.json` fija nombres canónicos para conflictos (p. ej. `SE.12`). Revíselo contra el archivo real.

## Parcial 3
`CMDB.xlsx` también se conserva aquí **sin modificar** (fuente de Parcial 3; no se importa con un comando, su
alcance real se documenta en `docs/contexto/05-cmdb-jerarquia.md` porque es solo una plantilla de ejemplo, no un
conjunto de datos a cargar). Las diapositivas fuente (`Service Desk.pptx.pdf`, `Transicion.pptx.pdf`) están en
`docs/fuentes/`. Los dispositivos de la CMDB se generan, no se importan: `flask generate-cmdb --seed --count`.
