from app.extensions import db
from app.models import User


def _mk(admin, entity, **body):
    return admin.post(f"/api/org/{entity}", json=body)


def test_P04_jerarquia_completa_y_usuario(admin):
    c = _mk(admin, "companies", code="EMP", name="Empresa").get_json()
    a = _mk(admin, "areas", code="AR", name="Área", company_id=c["id"]).get_json()
    d = _mk(admin, "departments", code="DP", name="Depto", area_id=a["id"]).get_json()
    s = _mk(admin, "sections", code="SC", name="Sección", department_id=d["id"]).get_json()
    p = _mk(admin, "positions", code="PU", name="Puesto", section_id=s["id"]).get_json()
    r = admin.post("/api/users", json={"name": "Ana", "username": "Ana@Demo.com", "password": "Clave-segura-1",
                                       "role": "consulta", "position_id": p["id"]})
    assert r.status_code == 201
    u = admin.get(f"/api/users/{r.get_json()['id']}").get_json()
    assert u["username"] == "ana@demo.com"
    assert u["organization"]["company"]["code"] == "EMP"          # empresa derivada de la jerarquía
    assert u["organization"]["text"] == "Empresa > Área > Depto > Sección > Puesto"
    assert "password_hash" not in u


def test_P05_codigo_duplicado_y_referencia_inexistente(admin, org):
    assert _mk(admin, "companies", code="E1", name="Otra").status_code == 409
    r = _mk(admin, "companies", code="e1", name="Otra")        # sin distinguir mayúsculas
    assert r.status_code == 409 and "Ya existe" in r.get_json()["error"]["message"]
    # códigos subordinados: únicos dentro del padre, repetibles en otro padre
    c2 = _mk(admin, "companies", code="E2", name="Empresa 2").get_json()
    assert _mk(admin, "areas", code="A1", name="Mismo código otro padre", company_id=c2["id"]).status_code == 201
    assert _mk(admin, "areas", code="A1", name="Dup", company_id=org["company"]).status_code == 409
    r = _mk(admin, "areas", code="ZZ", name="Huérfana", company_id=99999)
    assert r.status_code == 400 and "no existe" in r.get_json()["error"]["message"]
    r = admin.post("/api/users", json={"name": "x", "username": "admin_test", "password": "Password-1", "role": "consulta", "position_id": org["p1"]})
    assert r.status_code == 409
    r = admin.post("/api/users", json={"name": "x", "username": "nuevo@x", "password": "corta", "role": "consulta", "position_id": org["p1"]})
    assert r.status_code == 400 and "password" in r.get_json()["error"]["fields"]
    r = admin.post("/api/users", json={"name": "x", "username": "n2@x", "password": "Password-1", "role": "root", "position_id": org["p1"]})
    assert r.status_code == 400


def test_no_asociaciones_con_padres_inactivos(admin, org):
    c = _mk(admin, "companies", code="E9", name="Temporal").get_json()
    assert admin.delete(f"/api/org/companies/{c['id']}").status_code == 200
    r = _mk(admin, "areas", code="A9", name="Nueva", company_id=c["id"])
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "inactive_parent"


def test_baja_con_dependientes_requiere_confirmacion_y_no_borra(admin, org):
    r = admin.delete(f"/api/org/areas/{org['area']}")
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "has_dependents"
    assert admin.get(f"/api/org/areas/{org['area']}").get_json()["is_active"] is True
    # En cascada sí, pero el admin en sesión pertenece a ese árbol: se rechaza
    r = admin.delete(f"/api/org/areas/{org['area']}?cascade=true")
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "self_deactivation"


def test_baja_en_cascada_es_logica(admin, org):
    c = _mk(admin, "companies", code="EC", name="Cascada").get_json()
    a = _mk(admin, "areas", code="AC", name="A", company_id=c["id"]).get_json()
    d = _mk(admin, "departments", code="DC", name="D", area_id=a["id"]).get_json()
    assert admin.delete(f"/api/org/companies/{c['id']}").status_code == 409
    r = admin.delete(f"/api/org/companies/{c['id']}?cascade=true")
    assert r.status_code == 200 and r.get_json()["deactivated_records"] == 3
    assert admin.get(f"/api/org/departments/{d['id']}").get_json()["is_active"] is False   # sigue existiendo
    r = admin.put(f"/api/org/departments/{d['id']}", json={"is_active": True})             # padre inactivo
    assert r.status_code == 409


def test_no_se_cambia_el_padre_y_ultimo_admin_protegido(admin, org):
    r = admin.put(f"/api/org/areas/{org['area']}", json={"company_id": 12345})
    assert r.status_code == 400
    r = admin.put(f"/api/users/{org['admin']}", json={"role": "consulta"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "last_admin"
    assert admin.delete(f"/api/users/{org['admin']}").status_code == 409


def test_desactivar_usuario_revoca_sesiones(admin, viewer, org):
    assert admin.delete(f"/api/users/{org['viewer']}").status_code == 200
    assert viewer.get("/api/auth/me").status_code == 401
    assert db.session.get(User, org["viewer"]).is_active is False
