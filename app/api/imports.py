import json

from flask import Blueprint, current_app, jsonify

from ..errors import ApiError
from ..extensions import db
from ..importer import ImportFailure, run_import
from ..models import ImportObservation, ImportRun
from .serializers import iso
from .util import paginate

bp = Blueprint("imports", __name__, url_prefix="/api/import")


def run_dict(r, observations=None):
    d = {"id": r.id, "started_at": iso(r.started_at), "finished_at": iso(r.finished_at), "status": r.status,
         "file_name": r.file_name, "file_sha256": r.file_sha256, "created": r.created, "updated": r.updated,
         "skipped": r.skipped, "observed": r.observed, "n1_codes": r.n1_codes, "n2_codes": r.n2_codes,
         "summary": json.loads(r.summary) if r.summary else None}
    if observations is not None:
        d["observations"] = [{"kind": o.kind, "sheet": o.sheet, "row_ref": o.row_ref, "code": o.code,
                              "detail": o.detail, "evidence": json.loads(o.evidence) if o.evidence else None}
                             for o in observations]
    return d


@bp.post("/run")
def run():
    try:
        run_ = run_import(current_app.config["CATALOG_XLSX"], current_app.config["IMPORT_MAPPING"])
    except ImportFailure as e:
        raise ApiError(422, "import_failed", str(e))
    return jsonify(run_dict(run_)), 201


@bp.get("/runs")
def runs():
    return jsonify(paginate(db.select(ImportRun).order_by(ImportRun.id.desc()), run_dict))


@bp.get("/runs/<int:rid>")
def run_detail(rid):
    r = db.session.get(ImportRun, rid)
    if not r:
        raise ApiError(404, "not_found", f"Importación {rid} no existe.")
    obs = db.session.scalars(db.select(ImportObservation).where(ImportObservation.run_id == rid)
                             .order_by(ImportObservation.id)).all()
    return jsonify(run_dict(r, obs))
