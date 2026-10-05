import pytest


@pytest.fixture()
def cat(admin):
    """Catálogos y un N1 base."""
    ids = {}
    for kind, name in (("classes", "RECURRENTE"), ("criticalities", "High"), ("types", "Back End")):
        ids[kind] = admin.post(f"/api/catalogs/{kind}", json={"name": name}).get_json()["id"]
    ids["l1"] = admin.post("/api/services/l1", json={"code": "SE.01", "name": "Infraestructura"}).get_json()["id"]
    return ids


def _body(cat, **over):
    b = {"code": "SE.01.1", "name": "Monitoreo", "level1_id": cat["l1"], "activo_excel": "S",
         "class_id": cat["classes"], "criticality_id": cat["criticalities"], "type_id": cat["types"],
         "metric": "Disponibilidad", "min_value": 90, "max_value": 99}
    b.update(over)
    return b


def test_crear_consultar_ficha_y_desactivar(admin, cat):
    r = admin.post("/api/services/l2", json=_body(cat))
    assert r.status_code == 201
    sid = r.get_json()["id"]
    ficha = admin.get(f"/api/services/l2/{sid}").get_json()
    assert ficha["level1"]["code"] == "SE.01" and ficha["class"]["name"] == "RECURRENTE" and ficha["min_value"] == 90
    assert admin.delete(f"/api/services/l2/{sid}").get_json()["is_active"] is False
    assert admin.get(f"/api/services/l2/{sid}").status_code == 200   # baja lógica: sigue existiendo


def test_P05_codigo_duplicado_y_referencias(admin, cat):
    assert admin.post("/api/services/l2", json=_body(cat)).status_code == 201
    r = admin.post("/api/services/l2", json=_body(cat, code="se.01.1"))
    assert r.status_code == 409 and "Ya existe" in r.get_json()["error"]["message"]
    r = admin.post("/api/services/l2", json=_body(cat, code="SE.01.2", class_id=9999))
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "invalid_reference"
    r = admin.post("/api/services/l2", json=_body(cat, code="SE.01.3", level1_id=9999))
    assert r.status_code == 400
    r = admin.post("/api/services/l2", json={"code": "", "name": ""})
    assert r.status_code == 400 and {"code", "name", "level1_id"} <= set(r.get_json()["error"]["fields"])


def test_P09_minimo_mayor_que_maximo(admin, cat):
    r = admin.post("/api/services/l2", json=_body(cat, min_value=10, max_value=5))
    assert r.status_code == 400 and "mínimo" in r.get_json()["error"]["message"]
    ok = admin.post("/api/services/l2", json=_body(cat)).get_json()
    r = admin.put(f"/api/services/l2/{ok['id']}", json={"min_value": 100})
    assert r.status_code == 400
    # un solo extremo informado es válido; ausente no se convierte en cero
    r = admin.post("/api/services/l2", json=_body(cat, code="SE.01.9", min_value=None, max_value=7))
    assert r.status_code == 201 and r.get_json()["min_value"] is None and r.get_json()["max_value"] == 7
    r = admin.post("/api/services/l2", json=_body(cat, code="SE.01.8", min_value="abc"))
    assert r.status_code == 400


def test_P10_busqueda_y_filtros_con_paginacion(admin, cat):
    other = admin.post("/api/services/l1", json={"code": "SE.02", "name": "Soporte"}).get_json()["id"]
    low = admin.post("/api/catalogs/criticalities", json={"name": "Low"}).get_json()["id"]
    admin.post("/api/services/l2", json=_body(cat, code="SE.01.1", name="Monitoreo de servidores"))
    admin.post("/api/services/l2", json=_body(cat, code="SE.01.2", name="Respaldo de datos", criticality_id=low))
    admin.post("/api/services/l2", json=_body(cat, code="SE.02.1", name="Atender incidentes", level1_id=other, type_id=None, class_id=None))
    s = admin.post("/api/services/l2", json=_body(cat, code="SE.02.2", name="Atender peticiones", level1_id=other)).get_json()
    admin.delete(f"/api/services/l2/{s['id']}")

    def codes(qs):
        return [i["code"] for i in admin.get(f"/api/services/l2?{qs}").get_json()["items"]]
    assert codes("q=respaldo") == ["SE.01.2"]
    assert codes("q=SE.02") == ["SE.02.1", "SE.02.2"]
    assert codes(f"level1_id={other}&is_active=true") == ["SE.02.1"]
    assert codes("is_active=false") == ["SE.02.2"]
    assert codes(f"criticality_id={low}") == ["SE.01.2"]
    assert codes(f"type_id={cat['types']}&is_active=true") == ["SE.01.1", "SE.01.2"]
    assert codes(f"class_id={cat['classes']}&q=monitoreo") == ["SE.01.1"]
    assert codes("q=%25") == []                                   # el comodín se escapa
    page = admin.get("/api/services/l2?per_page=2&page=2").get_json()
    assert page["total"] == 4 and page["pages"] == 2 and [i["code"] for i in page["items"]] == ["SE.02.1", "SE.02.2"]


def test_P11_responsable_debe_pertenecer_a_la_seccion(admin, cat, org):
    s = admin.post("/api/services/l2", json=_body(cat)).get_json()
    # el usuario consulta pertenece a la sección S2; asignar S1 debe rechazarse
    r = admin.put(f"/api/services/l2/{s['id']}", json={"section_id": org["s1"], "responsible_user_id": org["viewer"]})
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "responsible_not_in_section"
    r = admin.put(f"/api/services/l2/{s['id']}", json={"section_id": org["s2"], "responsible_user_id": org["viewer"]})
    assert r.status_code == 200 and r.get_json()["responsible"]["username"] == "viewer_test"
    assert r.get_json()["section"]["text"].endswith("Sección 2")
    r = admin.put(f"/api/services/l2/{s['id']}", json={"section_id": None, "responsible_user_id": org["viewer"]})
    assert r.status_code == 400                                    # responsable sin sección
    # mover al usuario a otra sección mientras es responsable activo se rechaza
    assert admin.put(f"/api/users/{org['viewer']}", json={"position_id": org["p1"]}).status_code == 409
    # la sección con servicios activos no se puede desactivar
    r = admin.delete(f"/api/org/sections/{org['s2']}")
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "has_dependents"
    r = admin.delete(f"/api/org/sections/{org['s2']}?cascade=true")      # ni en cascada: hay que reasignar
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "has_services"
    assert "SE.01.1" in r.get_json()["error"]["message"]


def test_baja_de_n1_con_hijos_y_catalogo_inactivo(admin, cat):
    admin.post("/api/services/l2", json=_body(cat))
    r = admin.delete(f"/api/services/l1/{cat['l1']}")
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "has_dependents"
    admin.delete(f"/api/catalogs/types/{cat['types']}")
    r = admin.post("/api/services/l2", json=_body(cat, code="SE.01.5"))
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "inactive_reference"
    assert admin.delete(f"/api/services/l1/{cat['l1']}?cascade=true").status_code == 200
    assert admin.post("/api/services/l2", json=_body(cat, code="SE.01.6", type_id=None)).status_code == 409


def test_consulta_puede_leer_ficha(viewer, admin, cat):
    sid = admin.post("/api/services/l2", json=_body(cat)).get_json()["id"]
    assert viewer.get(f"/api/services/l2/{sid}").status_code == 200
