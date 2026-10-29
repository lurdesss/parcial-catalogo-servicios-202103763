from flask import Blueprint, jsonify

from .. import workflow
from ..errors import ApiError
from ..extensions import db
from ..models import Process
from .serializers import process_dict

bp = Blueprint("processes", __name__, url_prefix="/api/processes")


def _process(code):
    obj = db.session.scalar(db.select(Process).where(Process.code == code))
    if not obj:
        raise ApiError(404, "not_found", f"Proceso «{code}» no existe.")
    return obj


@bp.get("")
def list_processes():
    rows = db.session.scalars(db.select(Process).order_by(Process.id)).all()
    return jsonify([process_dict(p) for p in rows])


@bp.get("/<code>/grafo")
def process_graph(code):
    """Grafo 2: estados (nodos) y transiciones (aristas) del proceso."""
    return jsonify(workflow.graph_dict(_process(code)))
