import os

from app import create_app, reference_data
from app.cli_helpers import demo_org
from app.extensions import db
from app.models import CiClass, Company, Device, Location, Process, Queue, Ticket, User
from app.security import hash_password


def test_P18_catalogo_cmdb_tickets_persisten_al_recrear_la_aplicacion(tmp_path):
    """Equivalente en proceso del reinicio de contenedores (P18): nueva instancia de la app
    sobre la misma BD, cubriendo catálogo/organización (ya probado en Parcial 2), CMDB y
    tickets. La prueba real con Docker está en scripts/persistence_check.sh."""
    uri = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'p.db'}"
    cfg = {"TESTING": True, "SECRET_KEY": "k", "SQLALCHEMY_DATABASE_URI": uri}
    app1 = create_app(cfg)
    with app1.app_context():
        db.drop_all(); db.create_all()
        reference_data.seed_orm()
        db.session.add(Company(code="PERSIST", name="Persistente")); db.session.flush()
        _, _, p1, _ = demo_org()
        user = User(name="Persist", username="persist_test", role="admin", position_id=p1.id,
                   password_hash=hash_password("Persist-Pass-123"), is_active=True)
        db.session.add(user); db.session.flush()
        loc = db.session.scalar(db.select(Location))
        cls = db.session.scalar(db.select(CiClass).where(CiClass.code == "HW.SRV"))
        db.session.add(Device(asset_tag="CI-PERSIST-1", name="Servidor persistente", ci_class_id=cls.id,
                              location_id=loc.id, status="activo", is_active=True))
        process = db.session.scalar(db.select(Process).where(Process.code == "incidentes"))
        queue = Queue(code="Q-PERSIST", name="Cola persistente", process_id=process.id, is_active=True)
        db.session.add(queue); db.session.flush()
        db.session.add(Ticket(number="TCK-PERSIST", title="Ticket persistente", ticket_type="incidente",
                              process_id=process.id, queue_id=queue.id, requester_user_id=user.id, creator_user_id=user.id,
                              state="registrado", priority="media"))
        db.session.commit()
        db.session.remove(); db.engine.dispose()
    app2 = create_app(cfg)
    with app2.app_context():
        assert db.session.scalar(db.select(Company.name).where(Company.code == "PERSIST")) == "Persistente"
        assert db.session.scalar(db.select(Device.name).where(Device.asset_tag == "CI-PERSIST-1")) == "Servidor persistente"
        assert db.session.scalar(db.select(Ticket.title).where(Ticket.number == "TCK-PERSIST")) == "Ticket persistente"
        db.session.remove()   # sin esto, DROP TABLE espera a la propia transacción abierta (bloqueo en PostgreSQL)
        db.drop_all()
