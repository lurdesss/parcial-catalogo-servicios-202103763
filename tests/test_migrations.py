import os
import sqlite3

from alembic import command
from alembic.config import Config


def test_migracion_inicial_crea_el_esquema(tmp_path):
    db_file = tmp_path / "mig.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_file}")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_file}")
    command.upgrade(cfg, "head")
    tables = {r[0] for r in sqlite3.connect(db_file).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"companies", "areas", "departments", "sections", "positions", "users", "user_sessions",
            "services_l1", "services_l2", "service_classes", "criticalities", "service_types",
            "import_runs", "import_observations"} <= tables
