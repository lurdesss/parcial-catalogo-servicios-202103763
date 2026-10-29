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
# Blueprints de Parcial 3 cuyas vistas autorizan sus propias escrituras (queue_permission /
# reglas de proceso) en vez del "solo admin" de Parcial 2. Todo lo demás (org, catálogos,
# CMDB, colas) sigue exigiendo rol admin para escribir, igual que antes.
SELF_AUTH_BLUEPRINTS = {"tickets"}


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
    """Política por defecto: todo /api exige sesión; todo método de escritura exige CSRF y,
    salvo en SELF_AUTH_BLUEPRINTS, rol admin (igual que el Parcial 2)."""
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
        bp = (request.endpoint or "").split(".")[0]
        if request.endpoint != "auth.logout" and user.role != "admin" and bp not in SELF_AUTH_BLUEPRINTS:
            raise ApiError(403, "forbidden", "Su rol no permite modificar datos.")
    return None


# ------------------------------------------------------------- Parcial 3: roles y colas
def service_role_codes(user):
    """Roles funcionales de Service Desk del usuario (además de su rol base admin/consulta)."""
    return {r.role_code for r in user.service_roles}


def has_service_role(user, code):
    return code in service_role_codes(user)


def queue_permission(user, queue, perm):
    """perm en {'view','work','transfer','approve','manage'}. admin tiene control total siempre
    (igual que en el resto del sistema); el resto se evalúa por rol o por usuario en queue_permissions."""
    if user.role == "admin":
        return True
    principal_codes = {user.role} | service_role_codes(user)
    attr = f"can_{perm}"
    for p in queue.permissions:
        matches = p.principal_user_id == user.id or (p.principal_role and p.principal_role in principal_codes)
        if matches and getattr(p, attr):
            return True
    return False


def require_queue_perm(user, queue, perm, message=None):
    if not queue_permission(user, queue, perm):
        raise ApiError(403, "forbidden", message or "No tiene permiso sobre esta cola para esta acción.")
