from app.extensions import db
from app.models import CiClass, Device, Location


def _leaf(code):
    return db.session.scalar(db.select(CiClass).where(CiClass.code == code))


def _loc():
    return db.session.scalar(db.select(Location))


def _mk_device(admin, code="HW.WKS", tag="CI-TEST-00001", name="PC demo"):
    cls, loc = _leaf(code), _loc()
    r = admin.post("/api/cmdb/devices", json={
        "asset_tag": tag, "name": name, "ci_class_id": cls.id, "location_id": loc.id})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def test_P04_jerarquia_ci_corresponde_a_fuentes_y_rechaza_ciclos(admin):
    hw = db.session.scalar(db.select(CiClass).where(CiClass.code == "HW"))
    assert hw.parent_id is None
    srv = db.session.scalar(db.select(CiClass).where(CiClass.code == "HW.SRV"))
    assert srv.parent_id == hw.id and srv.requires_ip is True
    # ciclo: HW no puede quedar bajo su propio descendiente HW.SRV
    r = admin.put(f"/api/cmdb/ci-classes/{hw.id}", json={"code": "HW", "name": "Hardware", "parent_id": srv.id})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "cycle"
    # padre inexistente: rechazado
    r2 = admin.post("/api/cmdb/ci-classes", json={"code": "ZZ", "name": "Inválida", "parent_id": 999999})
    assert r2.status_code == 400


def test_P03_consulta_lee_cmdb_pero_no_escribe(viewer):
    assert viewer.get("/api/cmdb/devices").status_code == 200
    assert viewer.get("/api/cmdb/ci-classes").status_code == 200
    cls = _leaf("HW.WKS")
    r = viewer.post("/api/cmdb/devices", json={"asset_tag": "X", "name": "X", "ci_class_id": cls.id})
    assert r.status_code == 403


def test_device_requires_leaf_class(admin):
    hw = db.session.scalar(db.select(CiClass).where(CiClass.code == "HW"))
    r = admin.post("/api/cmdb/devices", json={"asset_tag": "CI-X", "name": "X", "ci_class_id": hw.id})
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "not_leaf_class"


def test_device_ip_never_mandatory(admin):
    # SW.APP no requiere IP y el dispositivo se crea sin ip_address sin error
    d = _mk_device(admin, code="SW.APP", tag="CI-APP-1", name="App demo")
    assert d["ip_address"] is None


def test_P14_relaciones_ci_y_ciclos_segun_tipo(admin):
    a = _mk_device(admin, "HW.SRV", "CI-A", "Servidor A")
    b = _mk_device(admin, "HW.SRV", "CI-B", "Servidor B")
    c = _mk_device(admin, "HW.SRV", "CI-C", "Servidor C")
    # depende_de: A->B, B->C permitido; C->A crearía ciclo y se rechaza
    assert admin.post(f"/api/cmdb/devices/{a['id']}/relaciones", json={"to_device_id": b["id"], "relation_type": "depende_de"}).status_code == 201
    assert admin.post(f"/api/cmdb/devices/{b['id']}/relaciones", json={"to_device_id": c["id"], "relation_type": "depende_de"}).status_code == 201
    r = admin.post(f"/api/cmdb/devices/{c['id']}/relaciones", json={"to_device_id": a["id"], "relation_type": "depende_de"})
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "cycle"
    # conectado_a SÍ admite ciclos
    assert admin.post(f"/api/cmdb/devices/{c['id']}/relaciones", json={"to_device_id": a["id"], "relation_type": "conectado_a"}).status_code == 201

    # recorrido de dependencias: si B falla, A se ve afectado (A depende de B)
    impacto = admin.get(f"/api/cmdb/devices/{b['id']}/impacto").get_json()
    affected_ids = {d["device_id"] for d in impacto["dispositivos_relacionados"]}
    assert a["id"] in affected_ids


def test_P16_filtros_y_paginacion_dispositivos(admin):
    cls, loc = _leaf("HW.WKS"), _loc()
    for i in range(30):
        db.session.add(Device(asset_tag=f"CI-BULK-{i:03d}", name=f"Bulk {i}", ci_class_id=cls.id,
                              location_id=loc.id, status="activo", is_active=True))
    db.session.commit()
    r = admin.get("/api/cmdb/devices?per_page=10&page=2&ci_class_id=%d" % cls.id)
    body = r.get_json()
    assert r.status_code == 200 and body["per_page"] == 10 and len(body["items"]) == 10
    assert body["total"] >= 30
    r2 = admin.get("/api/cmdb/devices?q=CI-BULK-001")
    assert any(d["asset_tag"] == "CI-BULK-001" for d in r2.get_json()["items"])


def test_servicio_vinculado_a_ci(admin, org):
    from app.models import ServiceL1, ServiceL2
    l1 = ServiceL1(code="SE.TEST", name="N1 test", is_active=True)
    db.session.add(l1); db.session.flush()
    l2 = ServiceL2(code="SE.TEST.1", name="N2 test", level1_id=l1.id, is_active=True, review_status="ok")
    db.session.add(l2); db.session.commit()
    d = _mk_device(admin, "HW.SRV", "CI-SVC", "Servidor con servicio")
    r = admin.post(f"/api/cmdb/devices/{d['id']}/servicios", json={"service_l2_id": l2.id})
    assert r.status_code == 201
    listed = admin.get(f"/api/cmdb/devices/{d['id']}/servicios").get_json()
    assert any(s["id"] == l2.id for s in listed)
