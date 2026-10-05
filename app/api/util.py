from flask import request
from sqlalchemy import func

from ..errors import ApiError
from ..extensions import db


def paginate(query, serialize, max_per_page=500):
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(max_per_page, max(1, int(request.args.get("per_page", 25))))
    except ValueError:
        raise ApiError(400, "validation", "page y per_page deben ser enteros.")
    total = db.session.scalar(db.select(func.count()).select_from(query.order_by(None).subquery()))
    rows = db.session.scalars(query.limit(per_page).offset((page - 1) * per_page)).all()
    return {"items": [serialize(r) for r in rows], "total": total, "page": page,
            "per_page": per_page, "pages": max(1, -(-total // per_page))}


def bool_arg(name):
    v = request.args.get(name)
    if v is None or v == "":
        return None
    if v.lower() in ("true", "1"):
        return True
    if v.lower() in ("false", "0"):
        return False
    raise ApiError(400, "validation", f"{name} debe ser true o false.")


def int_arg(name):
    v = request.args.get(name)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        raise ApiError(400, "validation", f"{name} debe ser entero.")


def commit_or_conflict(message="El registro entra en conflicto con otro existente (dato duplicado o referenciado)."):
    from sqlalchemy.exc import IntegrityError
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "conflict", message)
