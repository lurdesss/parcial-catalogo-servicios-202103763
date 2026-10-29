"""Motor de tickets: creación, transiciones (Grafo 2, ver app/workflow.py) y reglas propias
de cada uno de los 7 procesos. app/api/tickets.py es la capa HTTP delgada sobre este módulo
(mismo patrón que app/importer.py + app/api/imports.py). Ver docs/PROCESOS.md.
"""
import base64

from sqlalchemy import func

from . import workflow
from .errors import ApiError
from .extensions import db
from .models import (
    Process,
    Queue,
    ServiceL1,
    ServiceL2,
    Ticket,
    TicketAccessDetail,
    TicketAttachment,
    TicketChangeDetail,
    TicketCiLink,
    TicketComment,
    TicketEventDetail,
    TicketHistory,
    TicketIncidentDetail,
    TicketNewServiceDetail,
    TicketProblemDetail,
    TicketRelation,
    User,
    utcnow,
)
from .security import queue_permission
from .validation import Validator

INCIDENT_PRIORITY = {"I0": "baja", "I1": "media", "I2": "media", "I3": "alta", "I4": "alta", "I5": "alta", "I6": "alta"}
INCIDENT_CATEGORIES = tuple(INCIDENT_PRIORITY)
EVENT_CATEGORIES = ("E0", "E1", "E2", "E3")
CHANGE_TYPES = ("estandar", "normal", "emergencia")
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf", "image/png", "image/jpeg", "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


# ----------------------------------------------------------------------------- autorización
def can_view_ticket(user, ticket):
    if user.role == "admin":
        return True
    if user.id in (ticket.requester_user_id, ticket.creator_user_id, ticket.assignee_user_id):
        return True
    return queue_permission(user, ticket.queue, "view")


def require_view(user, ticket):
    if not can_view_ticket(user, ticket):
        raise ApiError(403, "forbidden", "No tiene acceso a este ticket.")


def _authorize_transition(user, ticket, transition):
    if user.role == "admin":
        return
    if transition.action == "reabrir" and user.id == ticket.requester_user_id:
        return
    perm = transition.required_perm or "work"
    if queue_permission(user, ticket.queue, perm):
        return
    raise ApiError(403, "forbidden", f"No tiene el permiso «{perm}» sobre la cola de este ticket para esa acción.")


# -------------------------------------------------------------------------------- bitácora
def _history(ticket, actor, action, field=None, old=None, new=None):
    db.session.add(TicketHistory(ticket_id=ticket.id, actor_user_id=actor.id if actor else None,
                                  action=action, field=field, old_value=old, new_value=new))


# --------------------------------------------------------------------------------- creación
def _build_detail(process_code, ticket, payload):
    """Crea la tabla de detalle 1-1 del proceso; devuelve la prioridad sugerida (o None)."""
    v = Validator(payload)
    if process_code == "incidentes":
        category = v.choice("category", "La categoría del incidente", INCIDENT_CATEGORIES)
        est = v.integer("estimated_minutes", "La duración estimada", required=False)
        redundancy = v.boolean("redundancy_available", "Redundancia disponible", default=None)
        v.check()
        db.session.add(TicketIncidentDetail(ticket_id=ticket.id, category=category, estimated_minutes=est,
                                             redundancy_available=redundancy))
        return INCIDENT_PRIORITY[category]
    if process_code == "eventos":
        category = v.choice("category", "La categoría del evento", EVENT_CATEGORIES)
        v.check()
        db.session.add(TicketEventDetail(ticket_id=ticket.id, category=category))
        return None
    if process_code == "cambios":
        change_type = v.choice("change_type", "El tipo de cambio", CHANGE_TYPES, required=False) or "normal"
        risk = v.text("risk_level", "El nivel de riesgo", required=False, max_len=10)
        test_plan = v.text("test_plan", "El plan de pruebas", required=False, max_len=5000)
        rollback = v.text("rollback_plan", "El plan de reversión", required=False, max_len=5000)
        v.check()
        db.session.add(TicketChangeDetail(ticket_id=ticket.id, change_type=change_type, risk_level=risk,
                                           test_plan=test_plan, rollback_plan=rollback))
        return None
    if process_code == "problemas":
        root_cause = v.text("root_cause", "La causa raíz", required=False, max_len=5000)
        v.check()
        linked_incident_id = payload.get("linked_incident_id")
        db.session.add(TicketProblemDetail(ticket_id=ticket.id, root_cause=root_cause,
                                            linked_incident_id=linked_incident_id))
        return None
    if process_code == "accesos":
        beneficiary_id = v.integer("beneficiary_user_id", "El beneficiario")
        resource = v.text("resource", "El recurso")
        permission = v.text("permission_requested", "El permiso solicitado", required=False, max_len=300)
        v.check()
        if not db.session.get(User, beneficiary_id):
            raise ApiError(400, "invalid_reference", f"El usuario beneficiario {beneficiary_id} no existe.",
                           fields={"beneficiary_user_id": "No existe."})
        db.session.add(TicketAccessDetail(ticket_id=ticket.id, beneficiary_user_id=beneficiary_id,
                                           resource=resource, permission_requested=permission))
        return None
    if process_code == "nuevos_servicios":
        proposed_name = v.text("proposed_name", "El nombre propuesto", max_len=300)
        level1_id = v.integer("proposed_level1_id", "El servicio de nivel 1")
        v.check()
        if not db.session.get(ServiceL1, level1_id):
            raise ApiError(400, "invalid_reference", f"El servicio de nivel 1 {level1_id} no existe.",
                           fields={"proposed_level1_id": "No existe."})
        db.session.add(TicketNewServiceDetail(ticket_id=ticket.id, proposed_name=proposed_name,
                                               proposed_level1_id=level1_id))
        return None
    return None  # servicios_tecnologia: usa directamente el service_l2_id del ticket


def create_ticket(process_code, data, actor):
    process = db.session.scalar(db.select(Process).where(Process.code == process_code))
    if not process:
        raise ApiError(404, "not_found", f"Proceso «{process_code}» no existe.")
    v = Validator(data)
    title = v.text("title", "El título", max_len=300)
    description = v.text("description", "La descripción", required=False, max_len=10000)
    queue_id = v.integer("queue_id", "La cola")
    requester_id = v.integer("requester_user_id", "El solicitante", required=False) or actor.id
    # accesos puede referirse a un recurso fuera del catálogo; nuevos_servicios propone un
    # servicio que todavía no existe. En ambos casos el servicio N2 es opcional.
    service_required = process_code not in ("accesos", "nuevos_servicios")
    service_id = v.integer("service_l2_id", "El servicio", required=service_required)
    priority = v.choice("priority", "La prioridad", ("baja", "media", "alta"), required=False) or "media"
    impact = v.text("impact", "El impacto", required=False, max_len=10)
    urgency = v.text("urgency", "La urgencia", required=False, max_len=10)
    channel = v.text("channel", "El canal", required=False, max_len=30) or "portal"
    v.check()

    queue = db.session.get(Queue, queue_id)
    if not queue or not queue.is_active:
        raise ApiError(400, "invalid_reference", f"La cola {queue_id} no existe o está inactiva.", fields={"queue_id": "Inválida."})
    if queue.process_id != process.id:
        raise ApiError(400, "queue_process_mismatch", "La cola indicada no pertenece a este proceso.",
                       fields={"queue_id": "No pertenece al proceso."})
    requester = db.session.get(User, requester_id)
    if not requester or not requester.is_active:
        raise ApiError(400, "invalid_reference", f"El solicitante {requester_id} no existe o está inactivo.",
                       fields={"requester_user_id": "Inválido."})
    if requester_id != actor.id and actor.role != "admin" and not queue_permission(actor, queue, "work"):
        raise ApiError(403, "forbidden", "No puede crear tickets en nombre de otro usuario sin permiso sobre la cola.")
    service = None
    if service_id is not None:
        service = db.session.get(ServiceL2, service_id)
        if not service or not service.is_active:
            raise ApiError(400, "invalid_reference", f"El servicio {service_id} no existe o está inactivo.",
                           fields={"service_l2_id": "Inválido."})

    initial = workflow.initial_state(process.id)
    ticket = Ticket(number="", title=title, description=description, ticket_type=process.ticket_type,
                     process_id=process.id, queue_id=queue.id, service_l2_id=service.id if service else None,
                     requester_user_id=requester_id, creator_user_id=actor.id, state=initial.code,
                     priority=priority, impact=impact, urgency=urgency, channel=channel)
    db.session.add(ticket)
    db.session.flush()  # asigna ticket.id
    ticket.number = f"TCK-{ticket.id:06d}"
    suggested_priority = _build_detail(process_code, ticket, data.get("detail") or {})
    if suggested_priority and "priority" not in data:
        ticket.priority = suggested_priority
    _history(ticket, actor, "creado", new=ticket.state)
    return ticket


# -------------------------------------------------------------------------------- comentarios
def add_comment(ticket, actor, body, visibility):
    if visibility == "interno" and actor.id == ticket.requester_user_id and actor.role != "admin":
        raise ApiError(403, "forbidden", "El solicitante no puede crear notas internas.")
    comment = TicketComment(ticket_id=ticket.id, author_user_id=actor.id, body=body, visibility=visibility,
                             created_at=utcnow())
    db.session.add(comment)
    _history(ticket, actor, "comentario", field=visibility)
    return comment


# -------------------------------------------------------------------------------- adjuntos
def add_attachment(ticket, actor, filename, content_type, content_base64, storage_dir):
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        raise ApiError(400, "invalid_type", f"Tipo de archivo no permitido: {content_type}.")
    try:
        raw = base64.b64decode(content_base64, validate=True)
    except Exception:
        raise ApiError(400, "invalid_base64", "El contenido adjunto no es base64 válido.")
    if len(raw) > MAX_ATTACHMENT_BYTES:
        raise ApiError(400, "too_large", f"El adjunto excede el tamaño máximo de {MAX_ATTACHMENT_BYTES // (1024*1024)} MB.")
    if not raw:
        raise ApiError(400, "empty_file", "El adjunto no puede estar vacío.")
    import os
    import uuid
    os.makedirs(storage_dir, exist_ok=True)
    safe_name = f"{ticket.id}-{uuid.uuid4().hex}-{os.path.basename(filename)[:150]}"
    path = os.path.join(storage_dir, safe_name)
    with open(path, "wb") as f:
        f.write(raw)
    att = TicketAttachment(ticket_id=ticket.id, uploaded_by_user_id=actor.id, filename=filename[:255],
                            content_type=content_type, size_bytes=len(raw), storage_path=path, created_at=utcnow())
    db.session.add(att)
    _history(ticket, actor, "adjunto", new=filename)
    return att


# ------------------------------------------------------------------------- CI y relaciones
def link_ci(ticket, actor, device_id):
    if not db.session.get(TicketCiLink, (ticket.id, device_id)):
        db.session.add(TicketCiLink(ticket_id=ticket.id, device_id=device_id))
        _history(ticket, actor, "vinculo_ci", new=str(device_id))


def link_related_ticket(ticket, actor, related_id, relation_type):
    if not db.session.get(Ticket, related_id):
        raise ApiError(400, "invalid_reference", f"El ticket {related_id} no existe.")
    if not db.session.scalar(db.select(TicketRelation).where(
            TicketRelation.ticket_id == ticket.id, TicketRelation.related_ticket_id == related_id,
            TicketRelation.relation_type == relation_type)):
        db.session.add(TicketRelation(ticket_id=ticket.id, related_ticket_id=related_id, relation_type=relation_type))
        _history(ticket, actor, "relacion", new=f"{relation_type}:{related_id}")


# ------------------------------------------------------------------------------ asignación
def claim_ticket(ticket, actor):
    """Concurrencia: UPDATE atómico condicionado a que nadie lo haya tomado antes. Devuelve
    True si este actor obtuvo la asignación, False si ya estaba asignado (otro agente ganó)."""
    if not (actor.role == "admin" or queue_permission(actor, ticket.queue, "work")):
        raise ApiError(403, "forbidden", "No tiene permiso de atención sobre esta cola.")
    result = db.session.execute(
        db.update(Ticket).where(Ticket.id == ticket.id, Ticket.assignee_user_id.is_(None))
        .values(assignee_user_id=actor.id)
    )
    db.session.flush()
    if result.rowcount == 0:
        return False
    ticket.assignee_user_id = actor.id
    _history(ticket, actor, "tomado", new=actor.username)
    return True


def assign_ticket(ticket, actor, assignee_id):
    if not (actor.role == "admin" or queue_permission(actor, ticket.queue, "manage")
            or queue_permission(actor, ticket.queue, "work")):
        raise ApiError(403, "forbidden", "No tiene permiso para asignar tickets de esta cola.")
    assignee = db.session.get(User, assignee_id)
    if not assignee or not assignee.is_active:
        raise ApiError(400, "invalid_reference", f"El usuario {assignee_id} no existe o está inactivo.")
    if not (assignee.role == "admin" or queue_permission(assignee, ticket.queue, "work")):
        raise ApiError(400, "not_authorized_assignee", "El usuario indicado no tiene permiso de atención sobre esta cola.")
    old = ticket.assignee_user_id
    ticket.assignee_user_id = assignee.id
    _history(ticket, actor, "asignado", old=str(old), new=str(assignee.id))


def transfer_ticket(ticket, actor, new_queue_id, reason):
    if not (actor.role == "admin" or queue_permission(actor, ticket.queue, "transfer")):
        raise ApiError(403, "forbidden", "No tiene permiso de transferencia sobre la cola actual.")
    new_queue = db.session.get(Queue, new_queue_id)
    if not new_queue or not new_queue.is_active:
        raise ApiError(400, "invalid_reference", f"La cola {new_queue_id} no existe o está inactiva.")
    if new_queue.process_id != ticket.process_id:
        raise ApiError(400, "queue_process_mismatch", "La cola destino no pertenece al proceso de este ticket.",
                       fields={"queue_id": "No pertenece al proceso."})
    old = ticket.queue_id
    ticket.queue_id = new_queue.id
    ticket.assignee_user_id = None
    _history(ticket, actor, "transferido", field=reason, old=str(old), new=str(new_queue.id))


# ----------------------------------------------------------------------------- transiciones
def _create_linked_incident(event_ticket, actor):
    """E2/E3: crea (o reutiliza) un incidente vinculado al mismo servicio/solicitante. Categoría
    por defecto I2: decisión de proyecto documentada en docs/PROCESOS.md (la diapositiva de
    eventos no define una categoría de incidente resultante)."""
    incidentes = db.session.scalar(db.select(Process).where(Process.code == "incidentes"))
    queue = db.session.scalar(db.select(Queue).where(Queue.process_id == incidentes.id, Queue.is_active.is_(True)).order_by(Queue.code))
    if not queue:
        raise ApiError(409, "no_queue", "No hay una cola activa de incidentes para vincular el evento.")
    data = {"title": f"Incidente generado por evento {event_ticket.number}", "queue_id": queue.id,
            "requester_user_id": event_ticket.requester_user_id, "service_l2_id": event_ticket.service_l2_id,
            "detail": {"category": "I2"}}
    incident = create_ticket("incidentes", data, actor)
    link_related_ticket(event_ticket, actor, incident.id, "genera_incidente")
    return incident


def _create_or_link_service(new_service_ticket, actor):
    """Aprobación de 'nuevos servicios': crea el ServiceL2 o lo vincula si ya existe uno con el
    mismo nombre (sin distinguir mayúsculas) bajo el mismo nivel 1, para no duplicarlo."""
    detail = new_service_ticket.new_service_detail
    existing = db.session.scalar(db.select(ServiceL2).where(
        ServiceL2.level1_id == detail.proposed_level1_id,
        func.lower(ServiceL2.name) == detail.proposed_name.strip().lower()))
    if existing:
        detail.created_service_l2_id = existing.id
        return existing
    code = f"NEW.{new_service_ticket.id}"
    svc = ServiceL2(code=code, name=detail.proposed_name, level1_id=detail.proposed_level1_id,
                     is_active=True, review_status="ok", source_sheet="service_desk",
                     source_range=f"ticket:{new_service_ticket.number}")
    db.session.add(svc)
    db.session.flush()
    detail.created_service_l2_id = svc.id
    return svc


def _apply_effects(ticket, process_code, action, actor):
    now = utcnow()
    if process_code == "cambios" and action == "aprobar":
        ticket.change_detail.approved_by_user_id = actor.id
        ticket.change_detail.approved_at = now
    if process_code == "cambios" and action == "ejecutar":
        if not ticket.change_detail or not ticket.change_detail.approved_at:
            raise ApiError(409, "not_approved", "No se puede ejecutar un cambio sin aprobación previa.")
    if process_code == "accesos" and action == "aprobar":
        if actor.id in (ticket.requester_user_id, ticket.access_detail.beneficiary_user_id):
            raise ApiError(403, "self_approval", "El solicitante o el beneficiario no pueden aprobar su propio acceso.")
        ticket.access_detail.approver_user_id = actor.id
        ticket.access_detail.approved_at = now
    if process_code == "eventos" and action == "evaluar":
        detail = ticket.event_detail
        if detail and detail.category in ("E2", "E3") and not detail.linked_incident_id:
            incident = _create_linked_incident(ticket, actor)
            detail.linked_incident_id = incident.id
    if process_code == "nuevos_servicios" and action == "aprobar":
        _create_or_link_service(ticket, actor)


def apply_transition(ticket, process_code, action, actor):
    process = ticket.process
    transition = workflow.find_transition(process.id, ticket.state, action)
    if not transition:
        raise ApiError(409, "invalid_transition",
                       f"No existe la transición «{action}» desde el estado «{ticket.state}» en este proceso.")
    _authorize_transition(actor, ticket, transition)
    _apply_effects(ticket, process_code, action, actor)
    old_state = ticket.state
    ticket.state = transition.to_code
    now = utcnow()
    if transition.to_code in ("resuelto", "recuperado"):
        ticket.resolved_at = now  # si se reabre y se vuelve a resolver, refleja la última resolución
    if workflow.is_final(process.id, transition.to_code):
        ticket.closed_at = now
    if transition.from_code == "cerrado":  # reapertura: ya no está cerrado
        ticket.closed_at = None
    _history(ticket, actor, "transicion", field=action, old=old_state, new=transition.to_code)
    return transition
