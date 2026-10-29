# Ciclo de harness 08 — verificación real con Docker (dos fallos reales en `scripts/smoke.py`)

- **Tarea:** ejecutar por primera vez el harness completo de Parcial 3 contra Docker/PostgreSQL real (pendiente desde
  el resto de la sesión, documentado como tal en `docs/PRUEBAS.md` §3): `docker compose up --build -d`,
  `scripts/setup_eval.sh`, `docker compose --profile test run --rm --build tests`,
  `docker compose exec -T app python scripts/smoke.py flow`, `scripts/persistence_check.sh`,
  `docker compose --profile ui run --rm ui_tests`.
- **Controles 1–3 (sin fallos):** build, arranque, migraciones y `setup_eval.sh` corrieron limpios (5 cuentas, 58
  servicios importados —coincide=true—, 5000 dispositivos de CMDB, 7 colas y 35 tickets). `docker compose --profile
  test run --rm --build tests` → ruff OK, **58 passed** en 65.74 s sobre PostgreSQL efímero real (no SQLite),
  `CONTROLES OK`.
- **Fallo 1 (control de humo):** `scripts/smoke.py flow` → `[FALLO] catálogo consultable  48`.
  - **Causa:** el chequeo (heredado de Parcial 2) asumía `total_servicios == n2_codes` (46) tras importar. Pero
    `setup_eval.sh` también ejecuta `seed-servicedesk-demo`, que aprueba tickets de `nuevos_servicios` y por tanto
    **crea servicios reales en el catálogo** (2, en esta corrida) — comportamiento correcto y deseado del enunciado
    ("la aprobación debe permitir crear… el servicio del catálogo"), no contemplado por el chequeo antiguo.
  - **Corrección:** `scripts/smoke.py` ahora verifica `total >= n2_codes` (el control de importación en sí,
    `n1_codes`/`n2_codes`/`coincide`, sigue exigiendo exactamente 12/46, sin cambios).
- **Fallo 2 (persistencia):** `scripts/persistence_check.sh` → `[FALLO] marcador de ticket creado o ya existente
  {'error': {'code': 'validation', 'fields': {'service_l2_id': 'El servicio es obligatorio.'}}}`.
  - **Causa:** `marker_write()` creaba un ticket de `incidentes` sin `service_l2_id`, pero ese proceso sí lo exige
    (a diferencia de `accesos`/`nuevos_servicios`). El propio servidor rechazó correctamente la petición inválida;
    el defecto estaba en el script de verificación, no en `ticket_engine`.
  - **Corrección:** `marker_write()` ahora consulta un servicio N2 existente y lo incluye en el ticket.
- **Nueva ejecución (tras reconstruir la imagen `app`):** `scripts/persistence_check.sh` completo → los tres
  marcadores (organización, CMDB, ticket) se crean, sobreviven a `docker compose restart` real, y se verifican de
  nuevo: `P12/P18 OK: los datos persisten tras reiniciar (volumen pgdata intacto).`
  `docker compose exec -T app python scripts/smoke.py flow` → todos los controles en `[OK]`, exit 0.
  `docker compose --profile ui run --rm ui_tests` → **todas** las vistas nuevas (Tickets, Tablero, Procesos, Colas,
  CMDB ×3) se cargaron sin error de JavaScript para admin y consulta, sin tocar `ui_smoke.js` (ya era genérico sobre
  `VIEWS`, escrito en Parcial 2).
- **Lección para el contexto:** un control de humo que asume una invariante de Parcial 2 ("el catálogo nunca crece
  solo") deja de ser válido cuando Parcial 3 agrega un flujo que modifica esa misma tabla de forma legítima; los
  scripts de verificación deben revisarse, no solo el código de la aplicación, al ampliar el alcance del sistema.
