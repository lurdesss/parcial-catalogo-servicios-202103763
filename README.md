# Catálogo de Servicios de TI + Service Desk y CMDB — Software Avanzado

Aplicación web (Flask + PostgreSQL + Docker) que sistematiza `data/CatalogoServicios.xlsx` con usuarios, estructura
organizacional y autenticación local (**Parcial 2**), ampliada con un **Service Desk** completo (tickets, colas, 7
procesos ITIL) y una **CMDB** con ≥5000 dispositivos sintéticos reproducibles (**Parcial 3**), sobre el mismo
repositorio y base de datos.

- **Integrante:** `COMPLETAR nombre` · **Carné:** `202103763`
- **Catedrático (GitHub):** `maldanap-usac` · **Etiquetas de entrega:** `parcial-v2.0` (Parcial 2) · `parcial-v3.0` (Parcial 3)

## Requisitos
Docker Engine 24+ y Docker Compose v2 (`docker compose version`). Nada más en el equipo anfitrión.

## Puesta en marcha
```bash
# El Excel original ya está en data/CatalogoServicios.xlsx; CMDB.xlsx y las diapositivas fuente en docs/fuentes/
cp .env.example .env          # edite POSTGRES_PASSWORD y SECRET_KEY (ver comentarios del archivo)
docker compose up --build -d  # construye, espera a PostgreSQL (healthcheck) y aplica migraciones
sh scripts/setup_eval.sh      # cuentas (5 roles) + importación + CMDB (seed=42, 5000 CI) + colas y tickets demo
```
Equivalente manual de `setup_eval.sh`:
```bash
docker compose exec app flask create-eval-users
docker compose exec app flask import-catalog
docker compose exec app flask seed-demo
docker compose exec app flask generate-cmdb --seed 42 --count 5000
docker compose exec app flask seed-servicedesk-demo
```
- **URL:** http://localhost:8000 (puerto configurable con `APP_PORT`) · **Salud:** `/health`
- **Cuentas de evaluación** (solo demostración, definidas en `.env`; valores del ejemplo):

  | Rol | Usuario | Contraseña |
  |---|---|---|
  | administrador | `admin_demo` | `Admin-Demo-2026!` |
  | consulta | `consulta_demo` | `Consulta-Demo-2026!` |
  | solicitante | `solicitante_demo` | `Solicitante-Demo-2026!` |
  | agente | `agente_demo` | `Agente-Demo-2026!` |
  | aprobador | `aprobador_demo` | `Aprobador-Demo-2026!` |

  Un usuario puede tener varios roles funcionales a la vez (ver `docs/PROCESOS.md` §1); estas 5 cuentas están
  separadas solo para que cada rol se pueda probar de forma aislada durante la evaluación.
- Importar el catálogo también es posible desde la pantalla **Importación** (rol admin). Es repetible y no duplica.
  `generate-cmdb` y `seed-servicedesk-demo` también son repetibles sin duplicar (ver `docs/PRUEBAS.md` §2).

## Pruebas
```bash
# Suite completa (ruff + pytest P01–P18) sobre un PostgreSQL efímero y aislado; no toca los datos de evaluación
docker compose --profile test run --rm --build tests
# Humo HTTP sobre el sistema en marcha (login, roles, importación x2, catálogo, procesos, CMDB, tickets, tablero)
docker compose exec -T app python scripts/smoke.py flow
# P18: reinicia contenedores SIN borrar volúmenes y verifica que catálogo, CMDB y tickets persisten
sh scripts/persistence_check.sh
# Interfaz (opcional, jsdom): requiere app en marcha y cuentas de evaluación
docker compose --profile ui run --rm ui_tests
```
Cobertura por tipo: ver `docs/RESOLUCION.md` §7 (Parcial 2) y `docs/PRUEBAS.md` (Parcial 3). Código de salida ≠ 0 si algo falla.

## Operación
```bash
docker compose logs -f app        # logs (también: db)
docker compose stop               # apagado normal (conserva datos)
docker compose start              # reinicio normal
docker compose down               # elimina contenedores, CONSERVA los volúmenes pgdata y uploads_data
```
**Reinicio destructivo (solo datos de prueba):** `docker compose down -v` borra los volúmenes y todos los datos
(incluidos los adjuntos de tickets); luego repita «Puesta en marcha».

## Documentación
`AGENTS.md` (contexto para IA) · `docs/RESOLUCION.md` (Parcial 2 + 3) · `docs/MODELO.md` · `docs/PROCESOS.md` ·
`docs/IA.md` · `docs/PRUEBAS.md` · `docs/contexto/` · `docs/prompts/` · `docs/evidencias/` · `docs/fuentes/`
