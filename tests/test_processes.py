def test_lista_siete_procesos(admin):
    r = admin.get("/api/processes")
    assert r.status_code == 200
    codes = {p["code"] for p in r.get_json()}
    assert codes == {"nuevos_servicios", "cambios", "incidentes", "eventos", "problemas",
                      "accesos", "servicios_tecnologia"}


def test_grafo_de_proceso_nodos_y_aristas(admin):
    r = admin.get("/api/processes/incidentes/grafo")
    assert r.status_code == 200
    body = r.get_json()
    state_codes = {s["code"] for s in body["states"]}
    assert "registrado" in state_codes and "cerrado" in state_codes
    assert any(s["is_initial"] for s in body["states"])
    assert any(s["is_final"] for s in body["states"])
    edges = {(t["from"], t["to"]) for t in body["transitions"]}
    assert ("registrado", "clasificado") in edges
    assert ("atencion", "cerrado") in edges  # cierre sin resolución


def test_grafo_proceso_inexistente(admin):
    assert admin.get("/api/processes/no_existe/grafo").status_code == 404


def test_grafo_disponible_para_consulta(viewer):
    assert viewer.get("/api/processes").status_code == 200
    assert viewer.get("/api/processes/cambios/grafo").status_code == 200
