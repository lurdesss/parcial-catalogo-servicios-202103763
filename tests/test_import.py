import json
from pathlib import Path

import pytest

from app.extensions import db
from app.importer import ImportFailure, run_import
from app.models import ImportObservation, ServiceL1, ServiceL2
from tests.synthetic_xlsx import build

REAL = Path("data/CatalogoServicios.xlsx")


def _l2(code):
    return db.session.scalar(db.select(ServiceL2).where(ServiceL2.code == code))


def _kinds(run_id):
    return [o.kind for o in db.session.scalars(db.select(ImportObservation).where(ImportObservation.run_id == run_id))]


def test_sintetico_celdas_combinadas_y_filas_continuacion(app):
    run = run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    assert run.status == "ok"
    assert (run.n1_codes, run.n2_codes) == (3, 7)
    # N1 SE.01 está combinado en A5:A8 -> UN servicio N1; SE.01.1 combinado en C5:C6 -> UN servicio N2
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL1)) == 3
    s = _l2("SE.01.1")
    assert s.level1.code == "SE.01" and s.name == "Monitorear Servidores"
    assert s.source_range.startswith("C5:C6") and "filas 5-6" in s.source_range
    assert s.activo_excel == "S" and float(s.min_value) == 95 and float(s.max_value) == 99.9
    k = _kinds(run.id)
    assert "fila_sin_codigo" in k                       # fila 8: no se asigna a SE.01.2 ni a otro
    assert _l2("SE.01.2").description is None
    assert "conflicto_atributo" in k                    # métrica distinta en fila 6 vs 5
    assert s.metric == "Disponibilidad"                 # gana el primer valor
    assert "lista_opciones" in k and not any("lista" in (x.name or "").lower() for x in db.session.scalars(db.select(ServiceL2)))


def test_P08_se12_conflicto_y_ausentes(app):
    run = run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    l1 = db.session.scalar(db.select(ServiceL1).where(ServiceL1.code == "SE.12"))
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL1).where(ServiceL1.code == "SE.12")) == 1
    assert l1.name == "Suministrar Analitica"                       # nombre canónico configurado
    notes = json.loads(l1.source_notes)
    assert {n["valor"] for n in notes["nombres_encontrados"]} == {"Suministrar Analitica", "Mantener Tableros de Control"}
    obs = db.session.scalars(db.select(ImportObservation).where(
        ImportObservation.run_id == run.id, ImportObservation.code == "SE.12", ImportObservation.kind == "conflicto_atributo")).all()
    assert len(obs) == 1 and "99" in obs[0].row_ref and "100" in obs[0].row_ref
    for code in ("SE.12.1", "SE.12.2", "SE.12.3"):
        s = _l2(code)
        assert s.review_status == "revisar"
        assert s.class_id is None and s.criticality_id is None and s.type_id is None and s.metric is None
        assert s.min_value is None and s.max_value is None           # ausente != 0
    assert _l2("SE.12.1").activo_excel is None                       # no se inventa ACTIVO
    assert _l2("SE.12.2").activo_excel is None and _l2("SE.12.2").activo_raw == "?"   # desconocido conservado
    assert "atributos_incompletos" in _kinds(run.id) and "activo_desconocido" in _kinds(run.id)


def test_mapeos_y_valores_fuera_de_catalogo(app):
    run = run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    k = _kinds(run.id)
    assert _l2("SE.01.2").service_class.name == "A DEMANDA"          # «a demanda» → catálogo, con mapeo registrado
    assert "mapeo_etiqueta" in k
    s = _l2("SE.02.1")                                               # «Muy Alta» no existe: se deja vacío, no se inventa
    assert s.criticality_id is None and "valor_fuera_de_catalogo" in k
    assert s.min_value is None and s.max_value is None and "umbral_invalido" in k
    assert _l2("SE.02.2").code_original == " SE.02.2" and "mapeo_codigo" in k   # código normalizado con original conservado


def test_P07_repetir_importacion_no_duplica(app):
    first = run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    n1 = db.session.scalar(db.select(db.func.count()).select_from(ServiceL1))
    n2 = db.session.scalar(db.select(db.func.count()).select_from(ServiceL2))
    again = run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    assert again.id != first.id and again.status == "ok"
    assert (again.created, again.updated) == (0, 0) and again.skipped == n1 + n2
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL1)) == n1
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL2)) == n2
    assert again.observed > 0                                        # las incidencias se registran en cada corrida


def test_reimportar_no_pisa_asignaciones_ni_baja_logica(admin, org, app):
    run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    s = _l2("SE.01.1")
    s.section_id, s.responsible_user_id, s.is_active = org["s1"], org["admin"], False
    db.session.commit()
    run_import(app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
    s = _l2("SE.01.1")
    assert (s.section_id, s.responsible_user_id, s.is_active) == (org["s1"], org["admin"], False)


def test_encabezados_invalidos_abortan_y_registran(app, tmp_path):
    bad = build(tmp_path / "malo.xlsx", corrupt_headers=True)
    with pytest.raises(ImportFailure):
        run_import(bad, app.config["IMPORT_MAPPING"])
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL2)) == 0
    from app.models import ImportRun
    assert db.session.scalar(db.select(ImportRun.status).order_by(ImportRun.id.desc())) == "error"


def test_endpoint_importacion_y_reporte(admin, viewer):
    r = admin.post("/api/import/run")
    assert r.status_code == 201 and r.get_json()["observed"] > 0
    rid = r.get_json()["id"]
    detail = viewer.get(f"/api/import/runs/{rid}").get_json()          # consulta puede leer el reporte
    assert any(o["kind"] == "conflicto_atributo" for o in detail["observations"])
    assert viewer.post("/api/import/run").status_code == 403


def test_importar_no_modifica_el_archivo(app):
    import hashlib
    p = Path(app.config["CATALOG_XLSX"])
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    run_import(p, app.config["IMPORT_MAPPING"])
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before


@pytest.mark.skipif(not REAL.is_file(), reason="Falta data/CatalogoServicios.xlsx (archivo real); P06 no ejecutado.")
def test_P06_archivo_original_12_n1_y_46_n2(app):
    run = run_import(REAL, app.config["IMPORT_MAPPING"])
    assert run.status == "ok"
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL1)) == 12
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL2)) == 46
    again = run_import(REAL, app.config["IMPORT_MAPPING"])
    assert again.created == 0 and again.updated == 0
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL2)) == 46
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL1).where(ServiceL1.code == "SE.12")) == 1


@pytest.mark.skipif(not REAL.is_file(), reason="Falta data/CatalogoServicios.xlsx (archivo real).")
def test_P08_archivo_original_se12_y_filas_huerfanas(app):
    run = run_import(REAL, app.config["IMPORT_MAPPING"])
    l1 = db.session.scalar(db.select(ServiceL1).where(ServiceL1.code == "SE.12"))
    assert l1.name == "Suministrar Analitica"
    assert {n["valor"] for n in json.loads(l1.source_notes)["nombres_encontrados"]} == {"Suministrar Analitica", "Mantener Tableros de Control"}
    for code in ("SE.12.1", "SE.12.2", "SE.12.3"):
        s = _l2(code)
        assert s.review_status == "revisar" and s.activo_excel is None
        assert s.class_id is None and s.criticality_id is None and s.type_id is None
        assert s.level1.code == "SE.12"
    assert _l2("SE.12.3").code == "SE.12.3" and "n1_inferido_por_prefijo" in _kinds(run.id)
    orphans = db.session.scalars(db.select(ImportObservation).where(
        ImportObservation.run_id == run.id, ImportObservation.kind == "fila_sin_codigo")).all()
    assert sorted(o.row_ref for o in orphans) == ["fila 42", "fila 67"]      # huecos entre combinaciones: no se asignan
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL2).where(ServiceL2.review_status == "revisar")) == 3
    assert db.session.scalar(db.select(db.func.count()).select_from(ServiceL2).where(ServiceL2.activo_excel == "N")) == 1
