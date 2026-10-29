from datetime import timedelta

from app.extensions import db
from app.models import Process, Queue, ServiceL1, ServiceL2, Ticket, TicketHistory, utcnow


def _svc():
    l1 = ServiceL1(code="SE.DB", name="N1 dashboard", is_active=True)
    db.session.add(l1); db.session.flush()
    l2 = ServiceL2(code="SE.DB.1", name="N2 dashboard", level1_id=l1.id, is_active=True, review_status="ok")
    db.session.add(l2); db.session.commit()
    return l2


def test_P17_indicadores_con_datos_controlados(admin, org):
    process = db.session.scalar(db.select(Process).where(Process.code == "incidentes"))
    queue = Queue(code="Q-DASH", name="Dashboard", process_id=process.id, is_active=True,
                  targets={"alta": 60, "media": 240, "baja": 1440})
    db.session.add(queue); db.session.flush()
    svc = _svc()
    now = utcnow()

    # Ticket 1: resuelto en 30 min, objetivo 60 (alta) -> cumple
    t1 = Ticket(number="TCK-D1", title="D1", ticket_type="incidente", process_id=process.id, queue_id=queue.id,
               service_l2_id=svc.id, requester_user_id=org["admin"], creator_user_id=org["admin"],
               state="cerrado", priority="alta", created_at=now - timedelta(minutes=30),
               resolved_at=now, closed_at=now)
    # Ticket 2: resuelto en 400 min, objetivo 240 (media) -> no cumple
    t2 = Ticket(number="TCK-D2", title="D2", ticket_type="incidente", process_id=process.id, queue_id=queue.id,
               service_l2_id=svc.id, requester_user_id=org["admin"], creator_user_id=org["admin"],
               state="cerrado", priority="media", created_at=now - timedelta(minutes=400),
               resolved_at=now, closed_at=now)
    # Ticket 3: abierto, creado hace 5 horas, aún sin asignar (cuenta en antigüedad, no en 1a atención)
    t3 = Ticket(number="TCK-D3", title="D3", ticket_type="incidente", process_id=process.id, queue_id=queue.id,
               service_l2_id=svc.id, requester_user_id=org["admin"], creator_user_id=org["admin"],
               state="registrado", priority="baja", created_at=now - timedelta(hours=5))
    db.session.add_all([t1, t2, t3]); db.session.flush()
    db.session.add(TicketHistory(ticket_id=t1.id, actor_user_id=org["admin"], action="tomado",
                                 created_at=t1.created_at + timedelta(minutes=5)))
    db.session.commit()

    r = admin.get("/api/dashboard/indicadores")
    assert r.status_code == 200
    body = r.get_json()
    assert body["tiempo"] == "calendario"
    assert body["tickets_evaluados_cumplimiento"] == 2
    assert body["cumplimiento_objetivo_pct"] == 50.0
    assert body["antiguedad_horas_promedio_abiertos"] >= 4.9  # t3 sigue abierto
    assert body["primera_atencion_horas_promedio"] is not None

    resumen = admin.get("/api/dashboard/resumen").get_json()
    assert resumen["total"] >= 3
    assert resumen["abiertos"] >= 1
    assert resumen["por_estado"].get("cerrado", 0) >= 2
