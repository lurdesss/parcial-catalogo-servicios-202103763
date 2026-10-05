from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..errors import ApiError
from ..extensions import db
from ..models import Criticality, Section, ServiceClass, ServiceL1, ServiceL2, ServiceType, User
from ..validation import Validator, like_escape
from .serializers import l1_dict, l2_dict
from .util import bool_arg, commit_or_conflict, int_arg, paginate

bp = Blueprint("services", __name__, url_prefix="/api/services")


def _search(q, model, term):
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(model.code).like(like, escape="\\") | func.lower(model.name).like(like, escape="\\"))
    return q


# ------------------------------------------------------------------------ nivel 1
@bp.get("/l1")
def list_l1():
    q = _search(db.select(ServiceL1), ServiceL1, (request.args.get("q") or "").strip())
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(ServiceL1.is_active.is_(active))
    return jsonify(paginate(q.order_by(ServiceL1.code), l1_dict))


def _l1(oid):
    obj = db.session.get(ServiceL1, oid)
    if not obj:
        raise ApiError(404, "not_found", f"Servicio de nivel 1 {oid} no existe.")
    return obj


@bp.get("/l1/<int:oid>")
def get_l1(oid):
    return jsonify(l1_dict(_l1(oid)))


def _dup(model, code, exclude=None):
    q = db.select(model.id).where(func.lower(model.code) == code.lower())
    if exclude:
        q = q.where(model.id != exclude)
    if db.session.scalar(q):
        raise ApiError(409, "duplicate_code", f"Ya existe un servicio con el código «{code}».", fields={"code": "Código duplicado."})


@bp.post("/l1")
def create_l1():
    v = Validator(request.get_json(silent=True))
    code = v.text("code", "El código", max_len=40)
    name = v.text("name", "El nombre", max_len=300)
    v.check()
    _dup(ServiceL1, code)
    obj = ServiceL1(code=code, name=name, is_active=True)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(l1_dict(obj)), 201


@bp.put("/l1/<int:oid>")
def update_l1(oid):
    obj = _l1(oid)
    data = request.get_json(silent=True)
    Validator(data)
    if "code" in data and data["code"] != obj.code and obj.code_original:
        raise ApiError(400, "immutable_code", "El código de un servicio importado no puede modificarse.", fields={"code": "No modificable."})
    v = Validator({"code": data.get("code", obj.code), "name": data.get("name", obj.name)})
    code = v.text("code", "El código", max_len=40)
    name = v.text("name", "El nombre", max_len=300)
    active = Validator(data).boolean("is_active", "El estado", default=obj.is_active)
    v.check()
    _dup(ServiceL1, code, exclude=obj.id)
    if not active and obj.is_active:
        children = db.session.scalars(db.select(ServiceL2).where(ServiceL2.level1_id == obj.id, ServiceL2.is_active.is_(True))).all()
        if children and not bool_arg("cascade"):
            raise ApiError(409, "has_dependents", f"Tiene {len(children)} servicio(s) de nivel 2 activo(s). Desactívelos primero o confirme la baja en cascada.",
                           extra={"dependents": len(children)})
        for c in children:
            c.is_active = False
    obj.code, obj.name, obj.is_active = code, name, active
    commit_or_conflict()
    return jsonify(l1_dict(obj))


@bp.delete("/l1/<int:oid>")
def deactivate_l1(oid):
    obj = _l1(oid)
    children = db.session.scalars(db.select(ServiceL2).where(ServiceL2.level1_id == obj.id, ServiceL2.is_active.is_(True))).all()
    if children and not bool_arg("cascade"):
        raise ApiError(409, "has_dependents", f"Tiene {len(children)} servicio(s) de nivel 2 activo(s). Desactívelos primero o confirme la baja en cascada.",
                       extra={"dependents": len(children)})
    for c in children:
        c.is_active = False
    obj.is_active = False
    commit_or_conflict()
    return jsonify(l1_dict(obj))


# ------------------------------------------------------------------------ nivel 2
def _l2(oid):
    obj = db.session.get(ServiceL2, oid)
    if not obj:
        raise ApiError(404, "not_found", f"Servicio de nivel 2 {oid} no existe.")
    return obj


@bp.get("/l2")
def list_l2():
    q = _search(db.select(ServiceL2), ServiceL2, (request.args.get("q") or "").strip())
    for arg, col in (("level1_id", ServiceL2.level1_id), ("class_id", ServiceL2.class_id),
                     ("criticality_id", ServiceL2.criticality_id), ("type_id", ServiceL2.type_id),
                     ("section_id", ServiceL2.section_id)):
        val = int_arg(arg)
        if val is not None:
            q = q.where(col == val)
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(ServiceL2.is_active.is_(active))
    rs = request.args.get("review_status")
    if rs:
        q = q.where(ServiceL2.review_status == rs)
    return jsonify(paginate(q.order_by(ServiceL2.code), l2_dict))


@bp.get("/l2/<int:oid>")
def get_l2(oid):
    return jsonify(l2_dict(_l2(oid)))


def _ref(model, v, field, label, current_id, fields):
    """Valida una referencia; un valor inactivo solo se admite si ya estaba asignado."""
    rid = v.integer(field, label, required=False)
    if rid is None:
        return None
    obj = db.session.get(model, rid)
    if not obj:
        raise ApiError(400, "invalid_reference", f"{label} con id {rid} no existe.", fields={field: "Referencia inexistente."})
    if not obj.is_active and rid != current_id:
        raise ApiError(409, "inactive_reference", f"{label} indicado está inactivo.", fields={field: "Inactivo."})
    return rid


def _l2_values(data, existing=None):
    v = Validator(data)
    cur = lambda a: getattr(existing, a) if existing else None  # noqa: E731
    out = {
        "code": v.text("code", "El código", max_len=40),
        "name": v.text("name", "El nombre", max_len=300),
        "description": v.text("description", "La descripción", required=False, max_len=5000),
        "metric": v.text("metric", "La métrica", required=False, max_len=300),
        "min_value": v.decimal("min_value", "El mínimo"),
        "max_value": v.decimal("max_value", "El máximo"),
    }
    activo = v.text("activo_excel", "ACTIVO", required=False, max_len=1)
    if activo is not None and activo.upper() not in ("S", "N"):
        v.errors["activo_excel"] = "ACTIVO debe ser S, N o estar vacío."
    out["activo_excel"] = activo.upper() if activo else None
    out["review_status"] = v.choice("review_status", "El estado de revisión", ("ok", "revisar"), required=False) or (cur("review_status") or "ok")
    out["is_active"] = v.boolean("is_active", "El estado", default=True if not existing else existing.is_active)
    lvl = v.integer("level1_id", "El servicio de nivel 1")
    v.check()
    if out["min_value"] is not None and out["max_value"] is not None and out["min_value"] > out["max_value"]:
        raise ApiError(400, "validation", "El mínimo no puede ser mayor que el máximo.",
                       fields={"min_value": "Debe ser menor o igual al máximo.", "max_value": "Debe ser mayor o igual al mínimo."})
    l1 = db.session.get(ServiceL1, lvl)
    if not l1:
        raise ApiError(400, "invalid_reference", f"El servicio de nivel 1 con id {lvl} no existe.", fields={"level1_id": "Referencia inexistente."})
    if not l1.is_active and lvl != cur("level1_id"):
        raise ApiError(409, "inactive_reference", "El servicio de nivel 1 está inactivo.", fields={"level1_id": "Inactivo."})
    out["level1_id"] = lvl
    out["class_id"] = _ref(ServiceClass, v, "class_id", "La clase de servicio", cur("class_id"), v.errors)
    out["criticality_id"] = _ref(Criticality, v, "criticality_id", "La criticidad", cur("criticality_id"), v.errors)
    out["type_id"] = _ref(ServiceType, v, "type_id", "El tipo de servicio", cur("type_id"), v.errors)
    v.check()
    sid = v.integer("section_id", "La sección", required=False)
    uid = v.integer("responsible_user_id", "El usuario responsable", required=False)
    v.check()
    section = None
    if sid is not None:
        section = db.session.get(Section, sid)
        if not section:
            raise ApiError(400, "invalid_reference", f"La sección con id {sid} no existe.", fields={"section_id": "Referencia inexistente."})
        if not section.is_active and sid != cur("section_id"):
            raise ApiError(409, "inactive_reference", "La sección está inactiva.", fields={"section_id": "Inactiva."})
    if uid is not None:
        if section is None:
            raise ApiError(400, "validation", "Para asignar un usuario responsable debe indicar la sección.",
                           fields={"responsible_user_id": "Requiere una sección."})
        user = db.session.get(User, uid)
        if not user:
            raise ApiError(400, "invalid_reference", f"El usuario con id {uid} no existe.", fields={"responsible_user_id": "Referencia inexistente."})
        if not user.is_active and uid != cur("responsible_user_id"):
            raise ApiError(409, "inactive_reference", "El usuario responsable está inactivo.", fields={"responsible_user_id": "Inactivo."})
        if user.position.section_id != section.id:
            raise ApiError(400, "responsible_not_in_section",
                           "El usuario responsable debe pertenecer a la sección asignada al servicio.",
                           fields={"responsible_user_id": "No pertenece a la sección indicada."})
    out["section_id"], out["responsible_user_id"] = sid, uid
    return out


def _form(s):
    return {"code": s.code, "name": s.name, "level1_id": s.level1_id, "activo_excel": s.activo_excel,
            "class_id": s.class_id, "criticality_id": s.criticality_id, "type_id": s.type_id,
            "description": s.description, "metric": s.metric, "min_value": s.min_value, "max_value": s.max_value,
            "section_id": s.section_id, "responsible_user_id": s.responsible_user_id,
            "is_active": s.is_active, "review_status": s.review_status}


@bp.post("/l2")
def create_l2():
    vals = _l2_values(request.get_json(silent=True))
    _dup(ServiceL2, vals["code"])
    obj = ServiceL2(**vals)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(l2_dict(obj)), 201


@bp.put("/l2/<int:oid>")
def update_l2(oid):
    obj = _l2(oid)
    data = request.get_json(silent=True)
    Validator(data)
    if "code" in data and data["code"] != obj.code and obj.code_original:
        raise ApiError(400, "immutable_code", "El código de un servicio importado no puede modificarse.", fields={"code": "No modificable."})
    vals = _l2_values({**_form(obj), **data}, existing=obj)
    _dup(ServiceL2, vals["code"], exclude=obj.id)
    for k, val in vals.items():
        setattr(obj, k, val)
    commit_or_conflict()
    return jsonify(l2_dict(obj))


@bp.delete("/l2/<int:oid>")
def deactivate_l2(oid):
    obj = _l2(oid)
    obj.is_active = False
    commit_or_conflict()
    return jsonify(l2_dict(obj))
