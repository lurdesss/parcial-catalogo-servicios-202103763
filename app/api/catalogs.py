from flask import Blueprint, jsonify, request

from ..errors import ApiError
from ..extensions import db
from ..models import Criticality, ServiceClass, ServiceType
from ..validation import Validator
from .serializers import catalog_dict
from .util import bool_arg, commit_or_conflict

bp = Blueprint("catalogs", __name__, url_prefix="/api/catalogs")
KINDS = {"classes": ServiceClass, "criticalities": Criticality, "types": ServiceType}


def _model(kind):
    m = KINDS.get(kind)
    if not m:
        raise ApiError(404, "not_found", f"Catálogo desconocido: {kind}.")
    return m


def _get(kind, cid):
    obj = db.session.get(_model(kind), cid)
    if not obj:
        raise ApiError(404, "not_found", f"Valor de catálogo {cid} no existe.")
    return obj


@bp.get("/<kind>")
def list_catalog(kind):
    m = _model(kind)
    q = db.select(m)
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(m.is_active.is_(active))
    return jsonify(items=[catalog_dict(c) for c in db.session.scalars(q.order_by(m.sort_order, m.name))])


def _unique(m, name, exclude=None):
    q = db.select(m.id).where(db.func.lower(m.name) == name.lower())
    if exclude:
        q = q.where(m.id != exclude)
    if db.session.scalar(q):
        raise ApiError(409, "duplicate_name", f"Ya existe el valor «{name}» en este catálogo.", fields={"name": "Duplicado."})


@bp.post("/<kind>")
def create_item(kind):
    m = _model(kind)
    v = Validator(request.get_json(silent=True))
    name = v.text("name", "El nombre", max_len=100)
    order = v.integer("sort_order", "El orden", required=False) or 0
    v.check()
    _unique(m, name)
    obj = m(name=name, sort_order=order, is_active=True)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(catalog_dict(obj)), 201


@bp.put("/<kind>/<int:cid>")
def update_item(kind, cid):
    obj = _get(kind, cid)
    data = request.get_json(silent=True)
    Validator(data)
    v = Validator({"name": data.get("name", obj.name), "sort_order": data.get("sort_order", obj.sort_order)})
    name = v.text("name", "El nombre", max_len=100)
    order = v.integer("sort_order", "El orden", required=False) or 0
    active = Validator(data).boolean("is_active", "El estado", default=obj.is_active)
    v.check()
    _unique(type(obj), name, exclude=obj.id)
    obj.name, obj.sort_order, obj.is_active = name, order, active
    commit_or_conflict()
    return jsonify(catalog_dict(obj))


@bp.delete("/<kind>/<int:cid>")
def deactivate_item(kind, cid):
    obj = _get(kind, cid)
    obj.is_active = False  # baja lógica: los servicios existentes conservan su referencia
    commit_or_conflict()
    return jsonify(catalog_dict(obj))
