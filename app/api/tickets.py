import os

from flask import Blueprint, current_app, g, jsonify, request, send_file
from sqlalchemy import func, or_

from .. import ticket_engine
from ..errors import ApiError
from ..extensions import db
from ..models import Device, Process, Queue, Ticket, TicketAttachment
from ..security import queue_permission
from ..validation import Validator, like_escape
from .serializers import ticket_detail_dict, ticket_list_dict
from .util import commit_or_conflict, int_arg, paginate

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

# Esta API es uno de los blueprints de SELF_AUTH_BLUEPRINTS (ver app/security.py): cada vista
# autoriza su propia escritura con queue_permission/ticket_engine en vez de exigir rol admin.


def _ticket(tid):
    obj = db.session.get(Ticket, tid)
    if not obj:
        raise ApiError(404, "not_found", f"Ticket {tid} no existe.")
    return obj


def _visible_queues_for(user):
    """Colas donde el usuario tiene al menos permiso de ver (o todas, si es admin)."""
    if user.role == "admin":
        return None  # sin filtro
    ids = [q.id for q in db.session.scalars(db.select(Queue)).all() if queue_permission(user, q, "view")]
    return ids


@bp.get("")
def list_tickets():
    user = g.user
    q = db.select(Ticket)
    if user.role != "admin":
        visible = _visible_queues_for(user)
        q = q.where(or_(Ticket.requester_user_id == user.id, Ticket.assignee_user_id == user.id,
                        Ticket.queue_id.in_(visible or [-1])))
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(Ticket.number).like(like, escape="\\") | func.lower(Ticket.title).like(like, escape="\\"))
    for arg, col in (("process_id", Ticket.process_id), ("queue_id", Ticket.queue_id),
                     ("service_l2_id", Ticket.service_l2_id), ("assignee_user_id", Ticket.assignee_user_id),
                     ("requester_user_id", Ticket.requester_user_id)):
        val = int_arg(arg)
        if val is not None:
            q = q.where(col == val)
    for arg, col in (("state", Ticket.state), ("priority", Ticket.priority), ("channel", Ticket.channel)):
        val = request.args.get(arg)
        if val:
            q = q.where(col == val)
    since = request.args.get("desde")
    if since:
        q = q.where(Ticket.created_at >= since)
    until = request.args.get("hasta")
    if until:
        q = q.where(Ticket.created_at <= until)
    return jsonify(paginate(q.order_by(Ticket.id.desc()), ticket_list_dict))


@bp.get("/<int:tid>")
def get_ticket(tid):
    t = _ticket(tid)
    ticket_engine.require_view(g.user, t)
    return jsonify(ticket_detail_dict(t))


@bp.post("")
def create_ticket():
    data = request.get_json(silent=True) or {}
    v = Validator(data)
    process_code = v.text("process_code", "El proceso", max_len=30)
    v.check()
    ticket = ticket_engine.create_ticket(process_code, data, g.user)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(ticket)), 201


@bp.post("/<int:tid>/comentarios")
def add_comment(tid):
    t = _ticket(tid)
    ticket_engine.require_view(g.user, t)
    v = Validator(request.get_json(silent=True))
    body = v.text("body", "El comentario", max_len=5000)
    visibility = v.choice("visibility", "La visibilidad", ("publico", "interno"), required=False) or "publico"
    v.check()
    ticket_engine.add_comment(t, g.user, body, visibility)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t)), 201


@bp.post("/<int:tid>/adjuntos")
def add_attachment(tid):
    t = _ticket(tid)
    ticket_engine.require_view(g.user, t)
    v = Validator(request.get_json(silent=True))
    filename = v.text("filename", "El nombre de archivo", max_len=255)
    content_type = v.text("content_type", "El tipo de contenido", max_len=100)
    content = v.text("content_base64", "El contenido", max_len=10_000_000)
    v.check()
    ticket_engine.add_attachment(t, g.user, filename, content_type, content, current_app.config["ATTACHMENTS_DIR"])
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t)), 201


@bp.get("/<int:tid>/adjuntos/<int:aid>/descarga")
def download_attachment(tid, aid):
    t = _ticket(tid)
    ticket_engine.require_view(g.user, t)
    att = db.session.get(TicketAttachment, aid)
    if not att or att.ticket_id != tid or not os.path.exists(att.storage_path):
        raise ApiError(404, "not_found", "Adjunto no encontrado.")
    return send_file(att.storage_path, mimetype=att.content_type, as_attachment=True, download_name=att.filename)


@bp.post("/<int:tid>/ci")
def link_ci(tid):
    t = _ticket(tid)
    if not (g.user.role == "admin" or queue_permission(g.user, t.queue, "work")):
        raise ApiError(403, "forbidden", "No tiene permiso de atención sobre esta cola.")
    v = Validator(request.get_json(silent=True))
    device_id = v.integer("device_id", "El CI")
    v.check()
    if not db.session.get(Device, device_id):
        raise ApiError(400, "invalid_reference", f"El dispositivo {device_id} no existe.")
    ticket_engine.link_ci(t, g.user, device_id)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t)), 201


@bp.post("/<int:tid>/relaciones")
def link_relation(tid):
    t = _ticket(tid)
    if not (g.user.role == "admin" or queue_permission(g.user, t.queue, "work")):
        raise ApiError(403, "forbidden", "No tiene permiso de atención sobre esta cola.")
    v = Validator(request.get_json(silent=True))
    related_id = v.integer("related_ticket_id", "El ticket relacionado")
    rtype = v.text("relation_type", "El tipo de relación", required=False, max_len=20) or "relacionado"
    v.check()
    ticket_engine.link_related_ticket(t, g.user, related_id, rtype)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t)), 201


@bp.post("/<int:tid>/tomar")
def claim(tid):
    t = _ticket(tid)
    got = ticket_engine.claim_ticket(t, g.user)
    commit_or_conflict()
    if not got:
        raise ApiError(409, "already_claimed", "Este ticket ya fue tomado por otro agente.")
    return jsonify(ticket_detail_dict(t))


@bp.post("/<int:tid>/asignar")
def assign(tid):
    t = _ticket(tid)
    v = Validator(request.get_json(silent=True))
    assignee_id = v.integer("assignee_user_id", "El responsable")
    v.check()
    ticket_engine.assign_ticket(t, g.user, assignee_id)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t))


@bp.post("/<int:tid>/transferir")
def transfer(tid):
    t = _ticket(tid)
    v = Validator(request.get_json(silent=True))
    queue_id = v.integer("queue_id", "La cola destino")
    reason = v.text("reason", "El motivo", required=False, max_len=500)
    v.check()
    ticket_engine.transfer_ticket(t, g.user, queue_id, reason)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t))


@bp.post("/<int:tid>/transicion")
def transition(tid):
    t = _ticket(tid)
    v = Validator(request.get_json(silent=True))
    action = v.text("action", "La acción", max_len=40)
    v.check()
    process = db.session.get(Process, t.process_id)
    ticket_engine.apply_transition(t, process.code, action, g.user)
    commit_or_conflict()
    return jsonify(ticket_detail_dict(t))
