import hashlib
import hmac
import secrets
from datetime import timedelta

from flask import current_app, g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .errors import ApiError
from .extensions import db
from .models import User, UserSession, utcnow

MIN_PASSWORD = 8
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")
PUBLIC_ENDPOINTS = {"auth.login", "health"}
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def hash_password(password: str) -> str:
    """scrypt con sal aleatoria por contraseña (Werkzeug)."""
    return generate_password_hash(password, method="scrypt")


def check_password_policy(password):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        raise ApiError(400, "validation", "Hay datos inválidos; revise los campos indicados.",
                       fields={"password": f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres."})


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(username, password):
    user = db.session.scalar(db.select(User).where(User.username == (username or "").strip().lower()))
    ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, password or "")
    if not user or not ok or not user.is_active:
        return None
    return user


def start_session(user):
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    db.session.add(UserSession(
        token_hash=_digest(token), csrf_token=csrf, user_id=user.id,
        expires_at=utcnow() + timedelta(hours=current_app.config["SESSION_HOURS"]),
    ))
    db.session.commit()
    session.clear()
    session["sid"] = token
    session.permanent = True
    return csrf


def end_session():
    token = session.get("sid")
    if token:
        db.session.execute(db.delete(UserSession).where(UserSession.token_hash == _digest(token)))
        db.session.commit()
    session.clear()


def revoke_user_sessions(user_id):
    db.session.execute(db.delete(UserSession).where(UserSession.user_id == user_id))


def _load_session():
    token = session.get("sid")
    if not token:
        return None, None
    us = db.session.scalar(db.select(UserSession).where(UserSession.token_hash == _digest(token)))
    if not us:
        return None, None
    if us.expires_at < utcnow() or not us.user.is_active:
        db.session.delete(us)
        db.session.commit()
        return None, None
    return us.user, us


def guard_request():
    """Política por defecto: todo /api exige sesión; todo método de escritura exige rol admin y CSRF."""
    if not request.path.startswith("/api/") or request.endpoint in PUBLIC_ENDPOINTS:
        return None
    user, us = _load_session()
    if not user:
        raise ApiError(401, "unauthenticated", "Debe iniciar sesión.")
    g.user, g.session = user, us
    if request.method in UNSAFE:
        sent = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(sent, us.csrf_token):
            raise ApiError(403, "csrf", "Token CSRF inválido o ausente.")
        if request.endpoint != "auth.logout" and user.role != "admin":
            raise ApiError(403, "forbidden", "Su rol no permite modificar datos.")
    return None
