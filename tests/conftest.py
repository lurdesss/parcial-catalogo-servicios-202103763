import os

import pytest

from app import create_app
from app.extensions import db
from app.models import Area, Company, Department, Position, Section, User
from app.security import hash_password
from tests.synthetic_xlsx import build

ADMIN = ("admin_test", "Admin-Pass-123")
VIEWER = ("viewer_test", "Viewer-Pass-123")


@pytest.fixture()
def app(tmp_path):
    uri = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path / 'test.db'}"
    xlsx = build(tmp_path / "sintetico.xlsx")
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": uri,
                      "CATALOG_XLSX": str(xlsx), "IMPORT_MAPPING": "data/mapeo_importacion.json"})
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class Client:
    """Cliente con cookie y token CSRF; las escrituras envían X-CSRF-Token automáticamente."""

    def __init__(self, app):
        self.c = app.test_client()
        self.csrf = None

    def login(self, creds):
        r = self.c.post("/api/auth/login", json={"username": creds[0], "password": creds[1]})
        if r.status_code == 200:
            self.csrf = r.get_json()["csrf_token"]
        return r

    def _h(self):
        return {"X-CSRF-Token": self.csrf} if self.csrf else {}

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, json=None):
        return self.c.post(url, json=json, headers=self._h())

    def put(self, url, json=None):
        return self.c.put(url, json=json, headers=self._h())

    def delete(self, url):
        return self.c.delete(url, headers=self._h())


@pytest.fixture()
def org(app):
    """Jerarquía mínima + un admin y un usuario de consulta (ids devueltos)."""
    c = Company(code="E1", name="Empresa 1")
    db.session.add(c); db.session.flush()
    a = Area(code="A1", name="Área 1", company_id=c.id); db.session.add(a); db.session.flush()
    d = Department(code="D1", name="Depto 1", area_id=a.id); db.session.add(d); db.session.flush()
    s1 = Section(code="S1", name="Sección 1", department_id=d.id)
    s2 = Section(code="S2", name="Sección 2", department_id=d.id)
    db.session.add_all([s1, s2]); db.session.flush()
    p1 = Position(code="P1", name="Puesto 1", section_id=s1.id)
    p2 = Position(code="P2", name="Puesto 2", section_id=s2.id)
    db.session.add_all([p1, p2]); db.session.flush()
    adm = User(name="Admin", username=ADMIN[0], role="admin", position_id=p1.id, password_hash=hash_password(ADMIN[1]))
    view = User(name="Viewer", username=VIEWER[0], role="consulta", position_id=p2.id, password_hash=hash_password(VIEWER[1]))
    db.session.add_all([adm, view]); db.session.commit()
    return {"company": c.id, "area": a.id, "dept": d.id, "s1": s1.id, "s2": s2.id, "p1": p1.id, "p2": p2.id,
            "admin": adm.id, "viewer": view.id}


@pytest.fixture()
def admin(app, org):
    cl = Client(app)
    assert cl.login(ADMIN).status_code == 200
    return cl


@pytest.fixture()
def viewer(app, org):
    cl = Client(app)
    assert cl.login(VIEWER).status_code == 200
    return cl


@pytest.fixture()
def anon(app):
    return Client(app)
