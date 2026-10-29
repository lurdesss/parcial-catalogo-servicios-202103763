from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..errors import ApiError
from ..extensions import db
from ..models import SERVICE_ROLES, Process, Queue, QueuePermission, User
from ..validation import Validator, like_escape
from .serializers import queue_dict
from .util import bool_arg, commit_or_conflict, int_arg, paginate

bp = Blueprint("queues", __name__, url_prefix="/api/queues")

ORDERING_RULES = ("priority_then_age",)
SUPPORT_LEVELS = ("nivel0", "nivel1", "nivel2", "nivel3", "nivel4")
PRINCIPAL_ROLES = ("admin", "consulta") + SERVICE_ROLES


def _queue(qid):
    obj = db.session.get(Queue, qid)
    if not obj:
        raise ApiError(404, "not_found", f"Cola {qid} no existe.")
    return obj


@bp.get("")
def list_queues():
    q = db.select(Queue)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(Queue.code).like(like, escape="\\") | func.lower(Queue.name).like(like, escape="\\"))
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(Queue.is_active.is_(active))
    pid = int_arg("process_id")
    if pid is not None:
        q = q.where(Queue.process_id == pid)
    return jsonify(paginate(q.order_by(Queue.code), queue_dict))


@bp.get("/<int:qid>")
def get_queue(qid):
    return jsonify(queue_dict(_queue(qid), with_permissions=True))


def _values(data, existing=None):
    v = Validator(data)
    cur = lambda a: getattr(existing, a) if existing else None  # noqa: E731
    code = v.text("code", "El código", max_len=30)
    name = v.text("name", "El nombre", max_len=200)
    desc = v.text("description", "La descripción", required=False, max_len=2000)
    process_id = v.integer("process_id", "El proceso")
    level = v.choice("support_level", "El nivel de soporte", SUPPORT_LEVELS, required=False) or (cur("support_level") or "nivel1")
    rule = v.choice("ordering_rule", "La regla de ordenamiento", ORDERING_RULES, required=False) or (cur("ordering_rule") or "priority_then_age")
    active = v.boolean("is_active", "El estado", default=True if not existing else existing.is_active)
    v.check()
    if existing and process_id != existing.process_id:
        raise ApiError(400, "immutable_process", "No se admite cambiar el proceso de una cola existente; cree una nueva.",
                       fields={"process_id": "No modificable."})
    if not db.session.get(Process, process_id):
        raise ApiError(400, "invalid_reference", f"El proceso {process_id} no existe.", fields={"process_id": "No existe."})
    targets = data.get("targets") if isinstance(data.get("targets"), dict) else (cur("targets") or {})
    return {"code": code, "name": name, "description": desc, "process_id": process_id,
            "support_level": level, "ordering_rule": rule, "targets": targets, "is_active": active}


@bp.post("")
def create_queue():
    vals = _values(request.get_json(silent=True) or {})
    if db.session.scalar(db.select(Queue.id).where(func.lower(Queue.code) == vals["code"].lower())):
        raise ApiError(409, "duplicate_code", f"Ya existe una cola con el código «{vals['code']}».", fields={"code": "Duplicado."})
    obj = Queue(**vals)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(queue_dict(obj)), 201


@bp.put("/<int:qid>")
def update_queue(qid):
    obj = _queue(qid)
    data = request.get_json(silent=True) or {}
    merged = {"code": data.get("code", obj.code), "name": data.get("name", obj.name),
              "description": data.get("description", obj.description), "process_id": data.get("process_id", obj.process_id),
              "support_level": data.get("support_level", obj.support_level), "ordering_rule": data.get("ordering_rule", obj.ordering_rule),
              "is_active": data.get("is_active", obj.is_active), "targets": data.get("targets", obj.targets)}
    vals = _values(merged, existing=obj)
    if db.session.scalar(db.select(Queue.id).where(func.lower(Queue.code) == vals["code"].lower(), Queue.id != obj.id)):
        raise ApiError(409, "duplicate_code", f"Ya existe una cola con el código «{vals['code']}».", fields={"code": "Duplicado."})
    for k, val in vals.items():
        setattr(obj, k, val)
    commit_or_conflict()
    return jsonify(queue_dict(obj))


@bp.delete("/<int:qid>")
def deactivate_queue(qid):
    obj = _queue(qid)
    obj.is_active = False
    commit_or_conflict()
    return jsonify(queue_dict(obj))


# ---------------------------------------------------------------------------- permisos
@bp.post("/<int:qid>/permisos")
def add_permission(qid):
    queue = _queue(qid)
    data = request.get_json(silent=True) or {}
    v = Validator(data)
    role = v.text("principal_role", "El rol", required=False, max_len=20)
    user_id = v.integer("principal_user_id", "El usuario", required=False)
    v.check()
    if (role is None) == (user_id is None):
        raise ApiError(400, "validation", "Indique exactamente un principal: rol o usuario.",
                       fields={"principal_role": "Indique uno u otro, no ambos ni ninguno."})
    if role is not None and role not in PRINCIPAL_ROLES:
        raise ApiError(400, "validation", f"Rol desconocido: {role}.", fields={"principal_role": "Rol inválido."})
    if user_id is not None and not db.session.get(User, user_id):
        raise ApiError(400, "invalid_reference", f"El usuario {user_id} no existe.", fields={"principal_user_id": "No existe."})
    perm = QueuePermission(
        queue_id=queue.id, principal_role=role, principal_user_id=user_id,
        can_view=bool(data.get("can_view", True)), can_work=bool(data.get("can_work", False)),
        can_transfer=bool(data.get("can_transfer", False)), can_approve=bool(data.get("can_approve", False)),
        can_manage=bool(data.get("can_manage", False)),
    )
    db.session.add(perm)
    commit_or_conflict()
    return jsonify(queue_dict(queue, with_permissions=True)), 201


@bp.delete("/<int:qid>/permisos/<int:pid>")
def remove_permission(qid, pid):
    perm = db.session.get(QueuePermission, pid)
    if not perm or perm.queue_id != qid:
        raise ApiError(404, "not_found", "Permiso no encontrado para esa cola.")
    db.session.delete(perm)
    commit_or_conflict()
    return jsonify(ok=True)
