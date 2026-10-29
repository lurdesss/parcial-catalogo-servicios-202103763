import threading

from app.extensions import db
from app.models import Process, ServiceL1, ServiceL2
from tests.conftest import AGENTE, Client


def _process(code):
    return db.session.scalar(db.select(Process).where(Process.code == code))


def _mk_queue(admin, code="Q-TEST-INC", process_code="incidentes"):
    p = _process(process_code)
    r = admin.post("/api/queues", json={"code": code, "name": "Cola de prueba", "process_id": p.id})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _svc():
    l1 = ServiceL1(code="SE.QT", name="N1 colas", is_active=True)
    db.session.add(l1); db.session.flush()
    l2 = ServiceL2(code="SE.QT.1", name="N2 colas", level1_id=l1.id, is_active=True, review_status="ok")
    db.session.add(l2); db.session.commit()
    return l2


def test_P06_permiso_de_cola_por_rol_y_por_usuario(admin, agente, org):
    q = _mk_queue(admin)
    svc = _svc()
    # sin permiso: el agente no puede crear/atender tickets de esa cola más allá de su propio rol
    r = agente.post("/api/tickets", json={"process_code": "incidentes", "title": "T1", "queue_id": q["id"],
                                          "service_l2_id": svc.id, "detail": {"category": "I2"}})
    # crear como solicitante de sí mismo siempre se permite (no requiere permiso de cola)
    assert r.status_code == 201
    ticket = r.get_json()
    claim = agente.post(f"/api/tickets/{ticket['id']}/tomar")
    assert claim.status_code == 403  # sin can_work en esta cola todavía

    admin.post(f"/api/queues/{q['id']}/permisos", json={"principal_role": "agente", "can_view": True, "can_work": True})
    claim2 = agente.post(f"/api/tickets/{ticket['id']}/tomar")
    assert claim2.status_code == 200
    assert claim2.get_json()["assignee"]["username"] == AGENTE[0]


def test_P07_orden_determinista_y_dos_agentes_mismo_ticket(app, admin, org):
    q = _mk_queue(admin, code="Q-TEST-CONC")
    admin.post(f"/api/queues/{q['id']}/permisos", json={"principal_role": "agente", "can_view": True, "can_work": True})
    svc = _svc()
    r = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Concurrencia", "queue_id": q["id"],
                                         "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                         "detail": {"category": "I2"}})
    tid = r.get_json()["id"]

    results = []

    def attempt():
        cl = Client(app)
        cl.login(AGENTE)
        results.append(cl.post(f"/api/tickets/{tid}/tomar").status_code)

    t1, t2 = threading.Thread(target=attempt), threading.Thread(target=attempt)
    t1.start(); t1.join()
    t2.start(); t2.join()
    assert sorted(results) == [200, 409]  # solo uno de los dos obtiene la asignación


def test_P08_transferencia_valida_proceso_destino(admin, org):
    q1 = _mk_queue(admin, code="Q-TEST-T1", process_code="incidentes")
    q_otro_proceso = _mk_queue(admin, code="Q-TEST-T2", process_code="problemas")
    q_mismo_proceso = _mk_queue(admin, code="Q-TEST-T3", process_code="incidentes")
    admin.post(f"/api/queues/{q1['id']}/permisos", json={"principal_role": "agente", "can_view": True, "can_transfer": True})
    svc = _svc()
    r = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Transferible", "queue_id": q1["id"],
                                         "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                         "detail": {"category": "I1"}})
    tid = r.get_json()["id"]
    bad = admin.post(f"/api/tickets/{tid}/transferir", json={"queue_id": q_otro_proceso["id"]})
    assert bad.status_code == 400 and bad.get_json()["error"]["code"] == "queue_process_mismatch"
    ok = admin.post(f"/api/tickets/{tid}/transferir", json={"queue_id": q_mismo_proceso["id"], "reason": "balanceo"})
    assert ok.status_code == 200
    hist = ok.get_json()["history"]
    assert any(h["action"] == "transferido" for h in hist)
