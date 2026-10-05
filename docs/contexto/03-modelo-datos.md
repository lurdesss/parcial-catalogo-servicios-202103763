# Modelo de datos
Ver diagrama ER y diccionario en `docs/RESOLUCION.md` §3. Tablas: companies, areas, departments, sections, positions, users,
user_sessions, service_classes, criticalities, service_types, services_l1, services_l2, import_runs, import_observations.
Migración inicial: `migrations/versions/0001_esquema_inicial.py` (generada con Alembic autogenerate y verificada por `tests/test_migrations.py`).
