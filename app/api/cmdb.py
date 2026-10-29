from flask import Blueprint, jsonify, request
from sqlalchemy import func

from .. import graph_cmdb
from ..errors import ApiError
from ..extensions import db
from ..models import CiClass, Device, DeviceRelation, Location, ServiceCiLink, ServiceL2, User
from ..validation import Validator, like_escape
from .serializers import ci_class_dict, device_dict, device_relation_dict, l2_dict, location_dict
from .util import bool_arg, commit_or_conflict, int_arg, paginate

bp = Blueprint("cmdb", __name__, url_prefix="/api/cmdb")

RELATION_TYPES = ("depende_de", "alojado_en", "conectado_a")


# -------------------------------------------------------------------- clasificación (CI)
def _ci_class(cid):
    obj = db.session.get(CiClass, cid)
    if not obj:
        raise ApiError(404, "not_found", f"Clase de CI {cid} no existe.")
    return obj


@bp.get("/ci-classes")
def list_ci_classes():
    q = db.select(CiClass)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(CiClass.code).like(like, escape="\\") | func.lower(CiClass.name).like(like, escape="\\"))
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(CiClass.is_active.is_(active))
    parent = request.args.get("parent_id")
    if parent is not None:
        q = q.where(CiClass.parent_id.is_(None) if parent in ("", "null") else CiClass.parent_id == int(parent))
    return jsonify(paginate(q.order_by(CiClass.code), ci_class_dict, max_per_page=1000))


@bp.post("/ci-classes")
def create_ci_class():
    v = Validator(request.get_json(silent=True))
    code = v.text("code", "El código", max_len=30)
    name = v.text("name", "El nombre", max_len=150)
    parent_id = v.integer("parent_id", "La clase padre", required=False)
    requires_ip = v.boolean("requires_ip", "Requiere IP", default=False)
    v.check()
    if parent_id is not None and not db.session.get(CiClass, parent_id):
        raise ApiError(400, "invalid_reference", f"La clase padre {parent_id} no existe.", fields={"parent_id": "No existe."})
    if db.session.scalar(db.select(CiClass.id).where(func.lower(CiClass.code) == code.lower())):
        raise ApiError(409, "duplicate_code", f"Ya existe una clase de CI con el código «{code}».", fields={"code": "Duplicado."})
    obj = CiClass(code=code, name=name, parent_id=parent_id, requires_ip=requires_ip, is_active=True)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(ci_class_dict(obj)), 201


@bp.put("/ci-classes/<int:cid>")
def update_ci_class(cid):
    obj = _ci_class(cid)
    data = request.get_json(silent=True) or {}
    v = Validator({"code": data.get("code", obj.code), "name": data.get("name", obj.name),
                   "parent_id": data.get("parent_id", obj.parent_id)})
    code = v.text("code", "El código", max_len=30)
    name = v.text("name", "El nombre", max_len=150)
    parent_id = v.integer("parent_id", "La clase padre", required=False)
    requires_ip = Validator(data).boolean("requires_ip", "Requiere IP", default=obj.requires_ip)
    active = Validator(data).boolean("is_active", "El estado", default=obj.is_active)
    v.check()
    if parent_id is not None:
        parent = db.session.get(CiClass, parent_id)
        if not parent:
            raise ApiError(400, "invalid_reference", f"La clase padre {parent_id} no existe.", fields={"parent_id": "No existe."})
        if graph_cmdb.would_create_cycle_classification(obj.id, parent_id):
            raise ApiError(409, "cycle", "Esa asignación crearía un ciclo en la jerarquía de clasificación.",
                           fields={"parent_id": "Crearía un ciclo."})
    if db.session.scalar(db.select(CiClass.id).where(func.lower(CiClass.code) == code.lower(), CiClass.id != obj.id)):
        raise ApiError(409, "duplicate_code", f"Ya existe una clase de CI con el código «{code}».", fields={"code": "Duplicado."})
    if not active and obj.is_active:
        children = db.session.scalar(db.select(func.count()).select_from(CiClass).where(CiClass.parent_id == obj.id, CiClass.is_active.is_(True)))
        devices = db.session.scalar(db.select(func.count()).select_from(Device).where(Device.ci_class_id == obj.id, Device.is_active.is_(True)))
        if children or devices:
            raise ApiError(409, "has_dependents", "Tiene subclases o dispositivos activos; desactívelos primero.",
                           extra={"children": children, "devices": devices})
    obj.code, obj.name, obj.parent_id, obj.requires_ip, obj.is_active = code, name, parent_id, requires_ip, active
    commit_or_conflict()
    return jsonify(ci_class_dict(obj))


# -------------------------------------------------------------------------- ubicaciones
def _location(lid):
    obj = db.session.get(Location, lid)
    if not obj:
        raise ApiError(404, "not_found", f"Ubicación {lid} no existe.")
    return obj


@bp.get("/locations")
def list_locations():
    q = db.select(Location)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(Location.code).like(like, escape="\\") | func.lower(Location.name).like(like, escape="\\"))
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(Location.is_active.is_(active))
    return jsonify(paginate(q.order_by(Location.code), location_dict, max_per_page=500))


@bp.post("/locations")
def create_location():
    v = Validator(request.get_json(silent=True))
    code = v.text("code", "El código", max_len=30)
    name = v.text("name", "El nombre", max_len=150)
    v.check()
    if db.session.scalar(db.select(Location.id).where(func.lower(Location.code) == code.lower())):
        raise ApiError(409, "duplicate_code", f"Ya existe una ubicación con el código «{code}».", fields={"code": "Duplicado."})
    obj = Location(code=code, name=name, is_active=True)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(location_dict(obj)), 201


@bp.put("/locations/<int:lid>")
def update_location(lid):
    obj = _location(lid)
    data = request.get_json(silent=True) or {}
    v = Validator({"code": data.get("code", obj.code), "name": data.get("name", obj.name)})
    code = v.text("code", "El código", max_len=30)
    name = v.text("name", "El nombre", max_len=150)
    active = Validator(data).boolean("is_active", "El estado", default=obj.is_active)
    v.check()
    if db.session.scalar(db.select(Location.id).where(func.lower(Location.code) == code.lower(), Location.id != obj.id)):
        raise ApiError(409, "duplicate_code", f"Ya existe una ubicación con el código «{code}».", fields={"code": "Duplicado."})
    obj.code, obj.name, obj.is_active = code, name, active
    commit_or_conflict()
    return jsonify(location_dict(obj))


# ------------------------------------------------------------------------- dispositivos
def _device(did):
    obj = db.session.get(Device, did)
    if not obj:
        raise ApiError(404, "not_found", f"Dispositivo {did} no existe.")
    return obj


@bp.get("/devices")
def list_devices():
    q = db.select(Device)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(Device.asset_tag).like(like, escape="\\") | func.lower(Device.name).like(like, escape="\\"))
    for arg, col in (("ci_class_id", Device.ci_class_id), ("location_id", Device.location_id), ("owner_user_id", Device.owner_user_id)):
        val = int_arg(arg)
        if val is not None:
            q = q.where(col == val)
    status = request.args.get("status")
    if status:
        q = q.where(Device.status == status)
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(Device.is_active.is_(active))
    return jsonify(paginate(q.order_by(Device.asset_tag), device_dict))


@bp.get("/devices/<int:did>")
def get_device(did):
    return jsonify(device_dict(_device(did)))


def _device_values(data, existing=None):
    v = Validator(data)
    cur = lambda a: getattr(existing, a) if existing else None  # noqa: E731
    asset_tag = v.text("asset_tag", "La etiqueta", max_len=60)
    name = v.text("name", "El nombre", max_len=200)
    ci_class_id = v.integer("ci_class_id", "La clase de CI")
    status = v.choice("status", "El estado", ("activo", "inactivo", "retirado"), required=False) or (cur("status") or "activo")
    location_id = v.integer("location_id", "La ubicación", required=False)
    owner_user_id = v.integer("owner_user_id", "El propietario", required=False)
    ip_address = v.text("ip_address", "La dirección IP", required=False, max_len=45)
    serial_number = v.text("serial_number", "El número de serie", required=False, max_len=100)
    active = v.boolean("is_active", "El estado", default=True if not existing else existing.is_active)
    v.check()
    ci_class = db.session.get(CiClass, ci_class_id)
    if not ci_class:
        raise ApiError(400, "invalid_reference", f"La clase de CI {ci_class_id} no existe.", fields={"ci_class_id": "No existe."})
    has_children = db.session.scalar(db.select(func.count()).select_from(CiClass).where(CiClass.parent_id == ci_class_id, CiClass.is_active.is_(True)))
    if has_children:
        raise ApiError(400, "not_leaf_class", "Solo se pueden asignar dispositivos a clases hoja (sin subclases activas).",
                       fields={"ci_class_id": "No es una clase hoja."})
    if location_id is not None and not db.session.get(Location, location_id):
        raise ApiError(400, "invalid_reference", f"La ubicación {location_id} no existe.", fields={"location_id": "No existe."})
    if owner_user_id is not None and not db.session.get(User, owner_user_id):
        raise ApiError(400, "invalid_reference", f"El usuario {owner_user_id} no existe.", fields={"owner_user_id": "No existe."})
    attrs = data.get("attributes") if isinstance(data.get("attributes"), dict) else (cur("attributes") or {})
    return {"asset_tag": asset_tag, "name": name, "ci_class_id": ci_class_id, "status": status,
            "location_id": location_id, "owner_user_id": owner_user_id, "ip_address": ip_address or None,
            "serial_number": serial_number or None, "attributes": attrs, "is_active": active}


@bp.post("/devices")
def create_device():
    vals = _device_values(request.get_json(silent=True) or {})
    if db.session.scalar(db.select(Device.id).where(func.lower(Device.asset_tag) == vals["asset_tag"].lower())):
        raise ApiError(409, "duplicate_tag", f"Ya existe un dispositivo con la etiqueta «{vals['asset_tag']}».", fields={"asset_tag": "Duplicado."})
    obj = Device(**vals)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(device_dict(obj)), 201


@bp.put("/devices/<int:did>")
def update_device(did):
    obj = _device(did)
    data = request.get_json(silent=True) or {}
    vals = _device_values(data, existing=obj)
    if db.session.scalar(db.select(Device.id).where(func.lower(Device.asset_tag) == vals["asset_tag"].lower(), Device.id != obj.id)):
        raise ApiError(409, "duplicate_tag", f"Ya existe un dispositivo con la etiqueta «{vals['asset_tag']}».", fields={"asset_tag": "Duplicado."})
    for k, val in vals.items():
        setattr(obj, k, val)
    commit_or_conflict()
    return jsonify(device_dict(obj))


@bp.delete("/devices/<int:did>")
def deactivate_device(did):
    obj = _device(did)
    obj.is_active = False
    obj.status = "retirado"
    commit_or_conflict()
    return jsonify(device_dict(obj))


# -------------------------------------------------------------- relaciones técnicas (CI)
@bp.get("/devices/<int:did>/relaciones")
def list_relations(did):
    _device(did)
    rows = db.session.scalars(db.select(DeviceRelation).where(
        (DeviceRelation.from_device_id == did) | (DeviceRelation.to_device_id == did))).all()
    return jsonify([device_relation_dict(r) for r in rows])


@bp.post("/devices/<int:did>/relaciones")
def create_relation(did):
    _device(did)
    v = Validator(request.get_json(silent=True))
    to_id = v.integer("to_device_id", "El CI relacionado")
    rtype = v.choice("relation_type", "El tipo de relación", RELATION_TYPES)
    v.check()
    if not db.session.get(Device, to_id):
        raise ApiError(400, "invalid_reference", f"El dispositivo {to_id} no existe.", fields={"to_device_id": "No existe."})
    if graph_cmdb.would_create_cycle_relation(did, to_id, rtype):
        raise ApiError(409, "cycle", f"Esa relación «{rtype}» crearía un ciclo; este tipo de relación no los admite.",
                       fields={"to_device_id": "Crearía un ciclo."})
    obj = DeviceRelation(from_device_id=did, to_device_id=to_id, relation_type=rtype)
    db.session.add(obj)
    commit_or_conflict("Esa relación ya existe entre estos dos CI.")
    return jsonify(device_relation_dict(obj)), 201


@bp.delete("/devices/<int:did>/relaciones/<int:rid>")
def delete_relation(did, rid):
    rel = db.session.get(DeviceRelation, rid)
    if not rel or rel.from_device_id != did:
        raise ApiError(404, "not_found", "Relación no encontrada para ese dispositivo.")
    db.session.delete(rel)
    commit_or_conflict()
    return jsonify(ok=True)


# ------------------------------------------------------------------- CI ↔ servicio y grafo
@bp.get("/devices/<int:did>/servicios")
def list_device_services(did):
    _device(did)
    rows = db.session.scalars(db.select(ServiceL2).join(ServiceCiLink, ServiceCiLink.service_l2_id == ServiceL2.id)
                               .where(ServiceCiLink.device_id == did)).all()
    return jsonify([l2_dict(s) for s in rows])


@bp.post("/devices/<int:did>/servicios")
def link_device_service(did):
    _device(did)
    v = Validator(request.get_json(silent=True))
    sid = v.integer("service_l2_id", "El servicio")
    v.check()
    if not db.session.get(ServiceL2, sid):
        raise ApiError(400, "invalid_reference", f"El servicio {sid} no existe.", fields={"service_l2_id": "No existe."})
    if not db.session.get(ServiceCiLink, (sid, did)):
        db.session.add(ServiceCiLink(service_l2_id=sid, device_id=did))
        commit_or_conflict()
    return jsonify(ok=True), 201


@bp.delete("/devices/<int:did>/servicios/<int:sid>")
def unlink_device_service(did, sid):
    link = db.session.get(ServiceCiLink, (sid, did))
    if link:
        db.session.delete(link)
        commit_or_conflict()
    return jsonify(ok=True)


@bp.get("/devices/<int:did>/impacto")
def device_impact(did):
    """Grafo 1: servicios potencialmente afectados si este CI falla (no afirma interrupción efectiva)."""
    _device(did)
    depth = int_arg("profundidad") or 10
    reached = graph_cmdb.impact_of(did, max_depth=depth)
    service_ids = {sid for sid, _ in graph_cmdb.affected_services(did, max_depth=depth)}
    services = db.session.scalars(db.select(ServiceL2).where(ServiceL2.id.in_(service_ids))).all() if service_ids else []
    return jsonify({
        "device_id": did,
        "dispositivos_relacionados": [{"device_id": d, "profundidad": depth_, "relation_type": rt} for d, depth_, rt in reached],
        "servicios_potencialmente_afectados": [l2_dict(s) for s in services],
    })
