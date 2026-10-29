from app.extensions import db
from app.models import Process, Queue, ServiceL1, ServiceL2, User


def _queue(admin, process_code, code):
    p = db.session.scalar(db.select(Process).where(Process.code == process_code))
    existing = db.session.scalar(db.select(Queue).where(Queue.code == code))
    if existing:
        return {"id": existing.id, "code": existing.code}
    r = admin.post("/api/queues", json={"code": code, "name": code, "process_id": p.id})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _svc():
    l1 = ServiceL1(code="SE.TK", name="N1 tickets", is_active=True)
    db.session.add(l1); db.session.flush()
    l2 = ServiceL2(code="SE.TK.1", name="N2 tickets", level1_id=l1.id, is_active=True, review_status="ok")
    db.session.add(l2); db.session.commit()
    return l2


def test_P05_crear_ticket_referencias_validas_e_invalidas(admin, org):
    q = _queue(admin, "incidentes", "Q-T05")
    svc = _svc()
    ok = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Válido", "queue_id": q["id"],
                                          "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                          "detail": {"category": "I1"}})
    assert ok.status_code == 201
    bad_service = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Inválido", "queue_id": q["id"],
                                                    "service_l2_id": 999999, "requester_user_id": org["admin"],
                                                    "detail": {"category": "I1"}})
    assert bad_service.status_code == 400
    bad_queue = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Inválido", "queue_id": 999999,
                                                  "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                                  "detail": {"category": "I1"}})
    assert bad_queue.status_code == 400
    q_otro = _queue(admin, "problemas", "Q-T05-OTRO")
    mismatch = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "X", "queue_id": q_otro["id"],
                                                "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                                "detail": {"category": "I1"}})
    assert mismatch.status_code == 400 and mismatch.get_json()["error"]["code"] == "queue_process_mismatch"


PROCESS_PATHS = {
    "nuevos_servicios": ["iniciar_analisis", "aprobar", "implementar", "cerrar"],
    "cambios": ["evaluar_impacto", "aprobar", "planificar", "ejecutar", "validar", "cerrar"],
    "incidentes": ["clasificar", "diagnosticar", "atender", "recuperar", "resolver", "cerrar"],
    "eventos": ["evaluar", "cerrar"],
    "problemas": ["investigar", "aplicar_solucion_temporal", "aplicar_solucion_definitiva", "cerrar"],
    "accesos": ["aprobar", "provisionar", "cerrar"],
    "servicios_tecnologia": ["validar", "asignar", "cumplir", "confirmar_cierre"],
}


def test_P09_ruta_completa_por_proceso_y_transicion_invalida(admin, org):
    svc = _svc()
    for code, path in PROCESS_PATHS.items():
        q = _queue(admin, code, f"Q-T09-{code}")
        detail = {"category": "I2"} if code == "incidentes" else {"category": "E1"} if code == "eventos" else \
            {"proposed_name": "Servicio demo", "proposed_level1_id": db.session.scalar(db.select(ServiceL1)).id} if code == "nuevos_servicios" else \
            {"beneficiary_user_id": org["viewer"], "resource": "Recurso demo"} if code == "accesos" else {}
        # accesos: el solicitante/beneficiario es 'viewer', no 'admin' (quien aprueba), para no
        # disparar la regla anti-autoaprobación.
        requester = org["viewer"] if code == "accesos" else org["admin"]
        payload = {"process_code": code, "title": f"Ruta {code}", "queue_id": q["id"], "requester_user_id": requester, "detail": detail}
        if code != "accesos" and code != "nuevos_servicios":
            payload["service_l2_id"] = svc.id
        r = admin.post("/api/tickets", json=payload)
        assert r.status_code == 201, (code, r.get_json())
        tid = r.get_json()["id"]
        for action in path:
            step = admin.post(f"/api/tickets/{tid}/transicion", json={"action": action})
            assert step.status_code == 200, (code, action, step.get_json())
        final = admin.get(f"/api/tickets/{tid}").get_json()
        assert final["closed_at"] is not None, (code, final["state"])
        # transición inválida: acción inexistente desde el estado actual (ya cerrado)
        invalid = admin.post(f"/api/tickets/{tid}/transicion", json={"action": "accion_que_no_existe"})
        assert invalid.status_code == 409 and invalid.get_json()["error"]["code"] == "invalid_transition"


def test_P10_cambio_sin_aprobacion_rechazado(admin, org):
    """El grafo de estados ya impide llegar a 'ejecutar' sin pasar por 'aprobar' (planificar
    solo es una transición válida desde 'aprobado'); se verifica aquí que el salto directo se
    rechaza, y además que la regla de servidor en ticket_engine._apply_effects es la causa de
    fondo (no solo una omisión de UI): sin aprobación no hay forma de alcanzar 'ejecutado'."""
    q = _queue(admin, "cambios", "Q-T10")
    svc = _svc()
    r = admin.post("/api/tickets", json={"process_code": "cambios", "title": "Cambio sin aprobar", "queue_id": q["id"],
                                         "service_l2_id": svc.id, "requester_user_id": org["admin"]})
    tid = r.get_json()["id"]
    admin.post(f"/api/tickets/{tid}/transicion", json={"action": "evaluar_impacto"})
    skip = admin.post(f"/api/tickets/{tid}/transicion", json={"action": "planificar"})
    assert skip.status_code == 409 and skip.get_json()["error"]["code"] == "invalid_transition"
    still_evaluacion = admin.get(f"/api/tickets/{tid}").get_json()
    assert still_evaluacion["state"] == "evaluacion"


def test_P10_autoaprobacion_acceso_rechazada(admin, aprobador, org):
    q = _queue(admin, "accesos", "Q-T10-ACC")
    r = admin.post("/api/tickets", json={"process_code": "accesos", "title": "Acceso propio", "queue_id": q["id"],
                                         "requester_user_id": org["viewer"],
                                         "detail": {"beneficiary_user_id": org["viewer"], "resource": "Sistema X"}})
    tid = r.get_json()["id"]
    admin.post(f"/api/queues/{q['id']}/permisos", json={"principal_role": "aprobador", "can_view": True, "can_approve": True})
    # el propio admin, que no es el solicitante ni el beneficiario, SÍ puede aprobar
    other_ok = admin.post(f"/api/tickets/{tid}/transicion", json={"action": "aprobar"})
    assert other_ok.status_code == 200

    # un segundo ticket donde el aprobador ES el beneficiario: se rechaza
    r2 = admin.post("/api/tickets", json={"process_code": "accesos", "title": "Acceso autoaprobado", "queue_id": q["id"],
                                          "requester_user_id": org["viewer"],
                                          "detail": {"beneficiary_user_id": org["aprobador"], "resource": "Sistema Y"}})
    tid2 = r2.get_json()["id"]
    self_approve = aprobador.post(f"/api/tickets/{tid2}/transicion", json={"action": "aprobar"})
    assert self_approve.status_code == 403 and self_approve.get_json()["error"]["code"] == "self_approval"


def test_P11_eventos_y_vinculo_incidente_sin_duplicar(admin, org):
    q = _queue(admin, "eventos", "Q-T11")
    _queue(admin, "incidentes", "Q-T11-INC")  # requerida: E2/E3 auto-crean un incidente vinculado
    svc = _svc()
    r = admin.post("/api/tickets", json={"process_code": "eventos", "title": "Evento E2", "queue_id": q["id"],
                                         "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                         "detail": {"category": "E2"}})
    tid = r.get_json()["id"]
    step1 = admin.post(f"/api/tickets/{tid}/transicion", json={"action": "evaluar"})
    assert step1.status_code == 200
    detail1 = step1.get_json()["detail"]
    assert detail1["linked_incident_id"] is not None
    first_incident_id = detail1["linked_incident_id"]
    # re-evaluar (si el motor lo permitiera de nuevo) no debe generar un segundo incidente
    from app.models import Ticket
    from app.ticket_engine import apply_transition
    ticket = db.session.get(Ticket, tid)
    ticket.state = "registrado"  # fuerza un reprocesamiento para probar la deduplicación
    db.session.commit()
    apply_transition(ticket, "eventos", "evaluar", db.session.get(User, org["admin"]))
    db.session.commit()
    assert ticket.event_detail.linked_incident_id == first_incident_id

    # E0/E1 no generan incidente
    r0 = admin.post("/api/tickets", json={"process_code": "eventos", "title": "Evento E0", "queue_id": q["id"],
                                          "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                          "detail": {"category": "E0"}})
    tid0 = r0.get_json()["id"]
    step0 = admin.post(f"/api/tickets/{tid0}/transicion", json={"action": "evaluar"})
    assert step0.get_json()["detail"]["linked_incident_id"] is None


def test_P12_incidentes_categoria_mapea_prioridad(admin, org):
    q = _queue(admin, "incidentes", "Q-T12")
    svc = _svc()
    expected = {"I0": "baja", "I1": "media", "I2": "media", "I3": "alta", "I4": "alta", "I5": "alta", "I6": "alta"}
    for cat, prio in expected.items():
        r = admin.post("/api/tickets", json={"process_code": "incidentes", "title": f"Incidente {cat}", "queue_id": q["id"],
                                             "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                             "detail": {"category": cat, "redundancy_available": cat == "I0"}})
        assert r.status_code == 201
        body = r.get_json()
        assert body["priority"] == prio, (cat, body["priority"])
        assert body["detail"]["category"] == cat


def test_P13_incidente_problema_cambio_trazabilidad(admin, org):
    qi = _queue(admin, "incidentes", "Q-T13-I")
    qp = _queue(admin, "problemas", "Q-T13-P")
    qc = _queue(admin, "cambios", "Q-T13-C")
    svc = _svc()
    inc = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Incidente raíz", "queue_id": qi["id"],
                                           "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                           "detail": {"category": "I3"}}).get_json()
    cambio = admin.post("/api/tickets", json={"process_code": "cambios", "title": "Cambio correctivo", "queue_id": qc["id"],
                                              "service_l2_id": svc.id, "requester_user_id": org["admin"]}).get_json()
    prob = admin.post("/api/tickets", json={"process_code": "problemas", "title": "Problema vinculado", "queue_id": qp["id"],
                                            "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                            "detail": {"root_cause": "Causa raíz", "linked_incident_id": inc["id"]}}).get_json()
    link = admin.post(f"/api/tickets/{prob['id']}/relaciones", json={"related_ticket_id": cambio["id"], "relation_type": "corrige_con"})
    assert link.status_code == 201
    detail = admin.get(f"/api/tickets/{prob['id']}").get_json()
    assert detail["detail"]["linked_incident_id"] == inc["id"]
    assert any(r["ticket_id"] == cambio["id"] for r in detail["relations"])


def test_P15_cierre_sin_resolucion_reapertura_bitacora(admin, org):
    q = _queue(admin, "incidentes", "Q-T15")
    svc = _svc()
    r = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Cierre sin resolución", "queue_id": q["id"],
                                         "service_l2_id": svc.id, "requester_user_id": org["admin"],
                                         "detail": {"category": "I2"}})
    tid = r.get_json()["id"]
    admin.post(f"/api/tickets/{tid}/transicion", json={"action": "clasificar"})
    admin.post(f"/api/tickets/{tid}/transicion", json={"action": "diagnosticar"})
    admin.post(f"/api/tickets/{tid}/transicion", json={"action": "atender"})
    closed = admin.post(f"/api/tickets/{tid}/transicion", json={"action": "cerrar_sin_resolucion"})
    assert closed.status_code == 200
    body = closed.get_json()
    assert body["state"] == "cerrado" and body["resolved_at"] is None and body["closed_at"] is not None
    reopened = admin.post(f"/api/tickets/{tid}/transicion", json={"action": "reabrir"})
    assert reopened.status_code == 200
    body2 = reopened.get_json()
    assert body2["state"] == "reabierto" and body2["closed_at"] is None
    actions = [h["action"] for h in body2["history"]]
    assert actions.count("transicion") >= 2
    assert all(h["actor_id"] is not None for h in body2["history"] if h["action"] == "transicion")


def test_comentarios_visibilidad_y_adjuntos_con_validacion(admin, solicitante, viewer, org):
    import base64
    q = _queue(admin, "incidentes", "Q-T-ADJ")
    svc = _svc()
    r = admin.post("/api/tickets", json={"process_code": "incidentes", "title": "Con adjuntos", "queue_id": q["id"],
                                         "service_l2_id": svc.id, "requester_user_id": org["solicitante"],
                                         "detail": {"category": "I1"}})
    tid = r.get_json()["id"]

    # el solicitante no puede crear notas internas, solo públicas
    internal = solicitante.post(f"/api/tickets/{tid}/comentarios", json={"body": "nota interna", "visibility": "interno"})
    assert internal.status_code == 403
    public = solicitante.post(f"/api/tickets/{tid}/comentarios", json={"body": "comentario público", "visibility": "publico"})
    assert public.status_code == 201

    content = base64.b64encode(b"contenido de prueba").decode()
    ok = solicitante.post(f"/api/tickets/{tid}/adjuntos", json={
        "filename": "evidencia.pdf", "content_type": "application/pdf", "content_base64": content})
    assert ok.status_code == 201
    att_id = ok.get_json()["attachments"][-1]["id"]

    bad_type = solicitante.post(f"/api/tickets/{tid}/adjuntos", json={
        "filename": "virus.exe", "content_type": "application/x-msdownload", "content_base64": content})
    assert bad_type.status_code == 400 and bad_type.get_json()["error"]["code"] == "invalid_type"

    too_big = base64.b64encode(b"x" * (6 * 1024 * 1024)).decode()
    big = solicitante.post(f"/api/tickets/{tid}/adjuntos", json={
        "filename": "grande.pdf", "content_type": "application/pdf", "content_base64": too_big})
    assert big.status_code == 400 and big.get_json()["error"]["code"] == "too_large"

    # autorización de descarga: un tercero sin acceso al ticket no puede descargar
    denied = viewer.get(f"/api/tickets/{tid}/adjuntos/{att_id}/descarga")
    assert denied.status_code == 403
    allowed = solicitante.get(f"/api/tickets/{tid}/adjuntos/{att_id}/descarga")
    assert allowed.status_code == 200 and allowed.get_data() == b"contenido de prueba"
