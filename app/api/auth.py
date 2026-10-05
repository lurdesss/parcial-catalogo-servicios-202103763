from flask import Blueprint, g, jsonify, request

from ..errors import ApiError
from ..security import authenticate, end_session, start_session
from .serializers import user_dict

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    user = authenticate(data.get("username"), data.get("password"))
    if not user:
        raise ApiError(401, "invalid_credentials", "Usuario o contraseña incorrectos.")
    csrf = start_session(user)
    return jsonify(user=user_dict(user), csrf_token=csrf)


@bp.post("/logout")
def logout():
    end_session()
    return jsonify(ok=True)


@bp.get("/me")
def me():
    return jsonify(user=user_dict(g.user), csrf_token=g.session.csrf_token)
