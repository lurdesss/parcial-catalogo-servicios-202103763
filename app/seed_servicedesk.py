"""Datos de demostración de Service Desk: ≥1 cola por proceso, permisos de cola para los
roles funcionales, y ≥35 tickets (5 por proceso) en distintos estados, incluyendo eventos
E0-E3 e incidentes I0-I6 (enunciado §11). Idempotente: cada ticket de demostración tiene un
título fijo y no se recrea si ya existe.

Requiere haber ejecutado antes: import-catalog (servicios), generate-cmdb (opcional, para
vincular CI) y create-eval-users (cuentas admin_demo/agente_demo/aprobador_demo/solicitante_demo).
"""
from . import ticket_engine
from .cli_helpers import demo_org
from .extensions import db
from .models import Process, Queue, QueuePermission, ServiceL1, ServiceL2, User

DEFAULT_TARGETS = {"alta": 480, "media": 1440, "baja": 2880}  # minutos, tiempo calendario
APPROVING_PROCESSES = {"cambios", "accesos", "nuevos_servicios"}


def _get_or_create_queue(process):
    code = f"Q-{process.code.upper()}"
    q = db.session.scalar(db.select(Queue).where(Queue.code == code))
    if q:
        return q
    q = Queue(code=code, name=f"Cola — {process.name}", description=f"Cola única de demostración para {process.name}.",
              process_id=process.id, is_active=True, support_level="nivel1", ordering_rule="priority_then_age",
              targets=DEFAULT_TARGETS)
    db.session.add(q)
    db.session.flush()
    return q


def _grant(queue, role_code, **perms):
    existing = db.session.scalar(db.select(QueuePermission).where(
        QueuePermission.queue_id == queue.id, QueuePermission.principal_role == role_code))
    if existing:
        for k, v in perms.items():
            setattr(existing, k, v)
        return existing
    perm = QueuePermission(queue_id=queue.id, principal_role=role_code, **perms)
    db.session.add(perm)
    return perm


def _user(username):
    return db.session.scalar(db.select(User).where(User.username == username))


def _ticket_exists(title):
    from .models import Ticket
    return db.session.scalar(db.select(Ticket).where(Ticket.title == title))


def _maybe_create(actor, process_code, title, **kw):
    if _ticket_exists(title):
        return None
    process = db.session.scalar(db.select(Process).where(Process.code == process_code))
    queue = _get_or_create_queue(process)
    data = {"process_code": process_code, "title": title, "queue_id": queue.id, **kw}
    ticket = ticket_engine.create_ticket(process_code, data, actor)
    db.session.flush()
    return ticket


def _advance(ticket, default_actor, *actions, overrides=None):
    """Aplica una secuencia de transiciones. `overrides` permite usar un actor distinto
    (p.ej. el aprobador) solo para ciertas acciones, demostrando el control de permisos por
    rol/cola incluso en la carga masiva de datos de demostración."""
    overrides = overrides or {}
    for action in actions:
        process = ticket.process
        actor = overrides.get(action, default_actor)
        ticket_engine.apply_transition(ticket, process.code, action, actor)


def run():
    s1, s2, p1, p2 = demo_org()
    admin = _user("admin_demo") or _user("admin_test")
    solicitante = _user("solicitante_demo") or admin
    agente = _user("agente_demo") or admin
    aprobador = _user("aprobador_demo") or admin
    if not admin:
        raise SystemExit("Ejecute primero 'flask create-eval-users'.")

    processes = db.session.scalars(db.select(Process)).all()
    queues = {p.code: _get_or_create_queue(p) for p in processes}
    db.session.flush()
    for code, q in queues.items():
        _grant(q, "agente", can_view=True, can_work=True, can_transfer=True, can_approve=False, can_manage=False)
        if code in APPROVING_PROCESSES:
            _grant(q, "aprobador", can_view=True, can_work=False, can_transfer=False, can_approve=True, can_manage=False)
    db.session.commit()

    l1 = db.session.scalar(db.select(ServiceL1).where(ServiceL1.is_active.is_(True)))
    l2 = db.session.scalar(db.select(ServiceL2).where(ServiceL2.is_active.is_(True)))
    svc_id = l2.id if l2 else None
    created = []

    # --- incidentes: I0, I1, I3, I5, I6 en distintos estados
    for cat, estado_destino in (("I0", None), ("I1", ("clasificar", "diagnosticar")),
                               ("I3", ("clasificar", "diagnosticar", "atender", "recuperar", "resolver")),
                               ("I5", ("clasificar", "diagnosticar", "atender", "recuperar", "resolver", "cerrar")),
                               ("I6", ("clasificar", "diagnosticar", "atender", "recuperar", "resolver", "cerrar", "reabrir"))):
        t = _maybe_create(solicitante, "incidentes", f"[DEMO] Incidente {cat}", service_l2_id=svc_id,
                          detail={"category": cat})
        if t:
            if estado_destino:
                _advance(t, admin, *estado_destino)
            created.append(t)

    # --- eventos: E0, E1, E2, E3 x2 (segundo para probar no-duplicación del incidente vinculado)
    for i, cat in enumerate(("E0", "E1", "E2", "E3", "E3"), start=1):
        t = _maybe_create(solicitante, "eventos", f"[DEMO] Evento {cat} #{i}", service_l2_id=svc_id,
                          detail={"category": cat})
        if t:
            _advance(t, admin, "evaluar")
            created.append(t)

    # --- cambios: normal pendiente, aprobado+ejecutado+validado+cerrado, rechazado, emergencia, reabierto
    for i, (change_type, acciones) in enumerate((
            ("normal", ()), ("normal", ("evaluar_impacto", "aprobar", "planificar", "ejecutar", "validar", "cerrar")),
            ("normal", ("evaluar_impacto", "rechazar")), ("emergencia", ("evaluar_impacto",)),
            ("estandar", ("evaluar_impacto", "aprobar", "planificar", "ejecutar", "validar", "cerrar", "reabrir"))), start=1):
        t = _maybe_create(solicitante, "cambios", f"[DEMO] Cambio {change_type} #{i}", service_l2_id=svc_id,
                          detail={"change_type": change_type, "test_plan": "Plan de prueba de demostración.",
                                  "rollback_plan": "Revertir a la versión anterior."})
        if t:
            _advance(t, admin, *acciones, overrides={"aprobar": aprobador, "rechazar": aprobador})
            created.append(t)

    # --- problemas: 5 en distintas etapas
    for i, acciones in enumerate(((), ("investigar",), ("investigar", "marcar_error_conocido"),
                                  ("investigar", "aplicar_solucion_temporal", "aplicar_solucion_definitiva"),
                                  ("investigar", "aplicar_solucion_temporal", "aplicar_solucion_definitiva", "cerrar")), start=1):
        t = _maybe_create(solicitante, "problemas", f"[DEMO] Problema #{i}", service_l2_id=svc_id,
                          detail={"root_cause": "Causa raíz de demostración."})
        if t:
            _advance(t, admin, *acciones)
            created.append(t)

    # --- accesos: aprobado (por un tercero, no autoaprobado), rechazado, pendiente, provisionado, revocado
    for i, acciones in enumerate((("aprobar", "provisionar"), ("rechazar",), (),
                                  ("aprobar", "provisionar"), ("aprobar", "provisionar", "revocar")), start=1):
        beneficiary = solicitante if solicitante != admin else _user("consulta_demo") or admin
        t = _maybe_create(solicitante, "accesos", f"[DEMO] Acceso #{i}",
                          detail={"beneficiary_user_id": beneficiary.id, "resource": "Sistema de demostración",
                                  "permission_requested": "Lectura"})
        if t:
            _advance(t, admin, *acciones, overrides={"aprobar": aprobador, "rechazar": aprobador})
            created.append(t)

    # --- nuevos servicios: aprobado (crea servicio), rechazado, pendiente, en análisis, implementado+cerrado
    for i, acciones in enumerate((("iniciar_analisis", "aprobar", "implementar", "cerrar"),
                                  ("iniciar_analisis", "rechazar"), (), ("iniciar_analisis",),
                                  ("iniciar_analisis", "aprobar", "implementar")), start=1):
        if not l1:
            break
        t = _maybe_create(solicitante, "nuevos_servicios", f"[DEMO] Nuevo servicio #{i}",
                          detail={"proposed_name": f"Servicio de demostración {i}", "proposed_level1_id": l1.id})
        if t:
            _advance(t, admin, *acciones, overrides={"aprobar": aprobador})
            created.append(t)

    # --- servicios de tecnología: 5 en distintas etapas
    for i, acciones in enumerate(((), ("validar",), ("validar", "asignar"),
                                  ("validar", "asignar", "cumplir"), ("validar", "asignar", "cumplir", "confirmar_cierre")), start=1):
        t = _maybe_create(solicitante, "servicios_tecnologia", f"[DEMO] Requisición de servicio #{i}", service_l2_id=svc_id)
        if t:
            _advance(t, agente, *acciones)
            created.append(t)

    db.session.commit()
    return {"tickets_creados": len(created), "colas": len(queues)}
