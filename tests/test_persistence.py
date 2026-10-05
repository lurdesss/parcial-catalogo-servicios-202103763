import os

from app import create_app
from app.extensions import db
from app.models import Company


def test_P12_datos_persisten_al_recrear_la_aplicacion(tmp_path):
    """Equivalente en proceso del reinicio de contenedores: nueva instancia de la app sobre la misma BD.
    La prueba real con Docker está en scripts/persistence_check.sh."""
    uri = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'p.db'}"
    cfg = {"TESTING": True, "SECRET_KEY": "k", "SQLALCHEMY_DATABASE_URI": uri}
    app1 = create_app(cfg)
    with app1.app_context():
        db.drop_all(); db.create_all()
        db.session.add(Company(code="PERSIST", name="Persistente")); db.session.commit()
        db.session.remove(); db.engine.dispose()
    app2 = create_app(cfg)
    with app2.app_context():
        assert db.session.scalar(db.select(Company.name).where(Company.code == "PERSIST")) == "Persistente"
        db.session.remove()   # sin esto, DROP TABLE espera a la propia transacción abierta (bloqueo en PostgreSQL)
        db.drop_all()
