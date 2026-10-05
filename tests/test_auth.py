from app.extensions import db
from app.models import User
from tests.conftest import ADMIN, VIEWER, Client


def test_P01_login_valido_e_invalido(app, org, anon):
    r = anon.login(ADMIN)
    assert r.status_code == 200
    body = r.get_json()
    assert body["user"]["role"] == "admin" and "password_hash" not in str(body)
    bad = Client(app).login((ADMIN[0], "incorrecta"))
    assert bad.status_code == 401
    assert Client(app).login(("no_existe", "x")).status_code == 401


def test_password_se_guarda_con_hash_salado(app, org):
    u = db.session.get(User, org["admin"])
    assert ADMIN[1] not in u.password_hash and u.password_hash.startswith("scrypt:")
    other = db.session.get(User, org["viewer"])
    assert u.password_hash != other.password_hash


def test_P02_sin_sesion_logout_e_inactivo(app, org, anon):
    assert anon.get("/api/services/l2").status_code == 401
    assert anon.get("/api/users").status_code == 401
    # logout invalida la credencial de sesión (no basta con borrar la cookie en el cliente)
    cl = Client(app)
    cl.login(ADMIN)
    cookie = cl.c.get_cookie("catalogo_session")
    assert cl.get("/api/auth/me").status_code == 200
    assert cl.post("/api/auth/logout").status_code == 200
    assert cl.get("/api/auth/me").status_code == 401
    replay = Client(app)
    replay.c.set_cookie("catalogo_session", cookie.value)
    assert replay.get("/api/auth/me").status_code == 401
    # usuario desactivado: sesión existente rechazada y no puede volver a entrar
    v = Client(app)
    v.login(VIEWER)
    assert v.get("/api/auth/me").status_code == 200
    u = db.session.get(User, org["viewer"])
    u.is_active = False
    db.session.commit()
    assert v.get("/api/auth/me").status_code == 401
    assert Client(app).login(VIEWER).status_code == 401


def test_csrf_requerido_en_escrituras(app, org, admin):
    admin.csrf = None
    r = admin.post("/api/org/companies", json={"code": "X", "name": "X"})
    assert r.status_code == 403 and r.get_json()["error"]["code"] == "csrf"


def test_P03_consulta_lee_pero_no_modifica(viewer, org):
    assert viewer.get("/api/services/l2").status_code == 200
    assert viewer.get("/api/org/companies").status_code == 200
    users = viewer.get("/api/users").get_json()
    assert "password_hash" not in str(users) and "scrypt" not in str(users)
    for method, url, body in [
        ("post", "/api/org/companies", {"code": "Z", "name": "Z"}),
        ("put", f"/api/org/companies/{org['company']}", {"name": "Hack"}),
        ("delete", f"/api/org/companies/{org['company']}", None),
        ("post", "/api/users", {"name": "n", "username": "n@x", "password": "Password-1", "role": "admin", "position_id": org["p1"]}),
        ("post", "/api/services/l1", {"code": "SE.99", "name": "x"}),
        ("post", "/api/catalogs/types", {"name": "Nuevo"}),
        ("post", "/api/import/run", None),
    ]:
        r = getattr(viewer, method)(url, json=body) if body is not None else getattr(viewer, method)(url)
        assert r.status_code == 403, (method, url, r.status_code)
