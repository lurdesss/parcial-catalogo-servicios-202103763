from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from ..errors import ApiError
from ..extensions import db
from ..models import Area, Company, Department, Position, Section, ServiceL2, User
from ..security import check_password_policy, hash_password, revoke_user_sessions
from ..validation import Validator, like_escape
from .serializers import unit_dict, user_dict
from .util import bool_arg, commit_or_conflict, int_arg, paginate

bp = Blueprint("org", __name__, url_prefix="/api")

UNITS = {
    "companies": (Company, "Empresa", None),
    "areas": (Area, "Área", ("company_id", Company, "La empresa")),
    "departments": (Department, "Departamento", ("area_id", Area, "El área")),
    "sections": (Section, "Sección", ("department_id", Department, "El departamento")),
    "positions": (Position, "Puesto", ("section_id", Section, "La sección")),
}
CHILD = {Company: (Area, "company_id"), Area: (Department, "area_id"),
         Department: (Section, "department_id"), Section: (Position, "section_id"),
         Position: (User, "position_id")}


def _cfg(entity):
    cfg = UNITS.get(entity)
    if not cfg:
        raise ApiError(404, "not_found", f"Entidad desconocida: {entity}.")
    return cfg


def _get(model, oid, label):
    obj = db.session.get(model, oid)
    if not obj:
        raise ApiError(404, "not_found", f"{label} con id {oid} no existe.")
    return obj


# ---------------------------------------------------------------- política de baja
def children_of(obj):
    spec = CHILD.get(type(obj))
    if not spec:
        return []
    model, fk = spec
    return db.session.scalars(db.select(model).where(getattr(model, fk) == obj.id)).all()


def active_descendants(obj):
    out, stack = [], [c for c in children_of(obj) if c.is_active]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(c for c in children_of(n) if c.is_active)
    return out


def deactivate_tree(obj, cascade):
    """Baja lógica con política explícita:
    1. Con dependientes activos se rechaza (409) salvo cascade=true, que los da de baja de forma visible.
    2. Nunca se da de baja una sección/usuario con servicios activos asignados: hay que reasignarlos.
    3. No se puede dar de baja a quien está en sesión ni al último administrador activo."""
    direct = [c for c in children_of(obj) if c.is_active]
    if direct and not cascade:
        raise ApiError(409, "has_dependents",
                       f"Tiene {len(direct)} registro(s) dependiente(s) activo(s). Desactívelos primero o confirme la baja en cascada.",
                       extra={"dependents": len(direct)})
    nodes = [obj] + active_descendants(obj)
    sec_ids = [n.id for n in nodes if isinstance(n, Section)]
    usr_ids = [n.id for n in nodes if isinstance(n, User)]
    if g.user.id in usr_ids:
        raise ApiError(409, "self_deactivation", "No puede desactivar su propio usuario ni una unidad que lo contiene.")
    cond = []
    if sec_ids:
        cond.append(ServiceL2.section_id.in_(sec_ids))
    if usr_ids:
        cond.append(ServiceL2.responsible_user_id.in_(usr_ids))
    if cond:
        from sqlalchemy import or_
        codes = db.session.scalars(
            db.select(ServiceL2.code).where(ServiceL2.is_active.is_(True), or_(*cond)).order_by(ServiceL2.code).limit(10)).all()
        if codes:
            raise ApiError(409, "has_services",
                           "Hay servicios activos asignados a esta unidad o a sus usuarios; reasígnelos antes de desactivar: "
                           + ", ".join(codes), extra={"services": codes})
    admins_left = db.session.scalar(db.select(func.count()).select_from(User).where(
        User.role == "admin", User.is_active.is_(True), User.id.notin_(usr_ids or [0])))
    if any(isinstance(n, User) and n.role == "admin" for n in nodes) and admins_left == 0:
        raise ApiError(409, "last_admin", "No se puede desactivar al último administrador activo.")
    for n in nodes:
        n.is_active = False
        if isinstance(n, User):
            revoke_user_sessions(n.id)
    return len(nodes)


# --------------------------------------------------------------- unidades (CRUD)
@bp.get("/org/<entity>")
def list_units(entity):
    model, _, parent = _cfg(entity)
    q = db.select(model)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(model.code).like(like, escape="\\") | func.lower(model.name).like(like, escape="\\"))
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(model.is_active.is_(active))
    if parent:
        pid = int_arg("parent_id")
        if pid is not None:
            q = q.where(getattr(model, parent[0]) == pid)
    return jsonify(paginate(q.order_by(model.code), unit_dict))


@bp.get("/org/<entity>/<int:oid>")
def get_unit(entity, oid):
    model, label, _ = _cfg(entity)
    return jsonify(unit_dict(_get(model, oid, label)))


def _check_parent(parent_cfg, pid, must_be_active=True):
    fk, pmodel, plabel = parent_cfg
    parent = db.session.get(pmodel, pid)
    if not parent:
        raise ApiError(400, "invalid_reference", f"{plabel} con id {pid} no existe.",
                       fields={fk: f"{plabel} indicada no existe."})
    if must_be_active and not parent.is_active:
        raise ApiError(409, "inactive_parent", f"{plabel} está inactiva; no se pueden crear asociaciones nuevas con ella.",
                       fields={fk: f"{plabel} está inactiva."})
    return parent


def _dup_check(model, parent_cfg, code, parent_id, exclude_id=None):
    q = db.select(model.id).where(func.lower(model.code) == code.lower())
    if parent_cfg:
        q = q.where(getattr(model, parent_cfg[0]) == parent_id)
    if exclude_id:
        q = q.where(model.id != exclude_id)
    if db.session.scalar(q):
        where = "dentro de su padre" if parent_cfg else "en el sistema"
        raise ApiError(409, "duplicate_code", f"Ya existe un registro con el código «{code}» {where}.",
                       fields={"code": "Código duplicado."})


@bp.post("/org/<entity>")
def create_unit(entity):
    model, label, parent = _cfg(entity)
    v = Validator(request.get_json(silent=True))
    code = v.text("code", "El código", max_len=30)
    name = v.text("name", "El nombre")
    pid = v.integer(parent[0], parent[2]) if parent else None
    v.check()
    if parent:
        _check_parent(parent, pid)
    _dup_check(model, parent, code, pid)
    obj = model(code=code, name=name, is_active=True)
    if parent:
        setattr(obj, parent[0], pid)
    db.session.add(obj)
    commit_or_conflict()
    return jsonify(unit_dict(obj)), 201


@bp.put("/org/<entity>/<int:oid>")
def update_unit(entity, oid):
    model, label, parent = _cfg(entity)
    obj = _get(model, oid, label)
    data = request.get_json(silent=True)
    v = Validator(data)
    if parent and parent[0] in data and data[parent[0]] != getattr(obj, parent[0]):
        raise ApiError(400, "immutable_parent", "No se admite cambiar el padre de una unidad existente; cree una nueva.",
                       fields={parent[0]: "No modificable."})
    merged = Validator({"code": data.get("code", obj.code), "name": data.get("name", obj.name)})
    code = merged.text("code", "El código", max_len=30)
    name = merged.text("name", "El nombre")
    active = v.boolean("is_active", "El estado", default=obj.is_active)
    merged.errors.update(v.errors)
    merged.check()
    _dup_check(model, parent, code, getattr(obj, parent[0]) if parent else None, exclude_id=obj.id)
    if active and not obj.is_active and parent:
        _check_parent(parent, getattr(obj, parent[0]))
    if not active and obj.is_active:
        deactivate_tree(obj, cascade=bool_arg("cascade") or False)
    elif active and not obj.is_active:
        obj.is_active = True
    obj.code, obj.name = code, name
    commit_or_conflict()
    return jsonify(unit_dict(obj))


@bp.delete("/org/<entity>/<int:oid>")
def deactivate_unit(entity, oid):
    model, label, _ = _cfg(entity)
    obj = _get(model, oid, label)
    n = deactivate_tree(obj, cascade=bool_arg("cascade") or False) if obj.is_active else 0
    commit_or_conflict()
    return jsonify(unit_dict(obj) | {"deactivated_records": n})


# ----------------------------------------------------------------------- usuarios
@bp.get("/users")
def list_users():
    q = db.select(User)
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{like_escape(term.lower())}%"
        q = q.where(func.lower(User.name).like(like, escape="\\") | func.lower(User.username).like(like, escape="\\"))
    active = bool_arg("is_active")
    if active is not None:
        q = q.where(User.is_active.is_(active))
    sec = int_arg("section_id")
    if sec is not None:
        q = q.join(Position, User.position_id == Position.id).where(Position.section_id == sec)
    pos = int_arg("position_id")
    if pos is not None:
        q = q.where(User.position_id == pos)
    return jsonify(paginate(q.order_by(User.username), user_dict))


@bp.get("/users/<int:uid>")
def get_user(uid):
    return jsonify(user_dict(_get(User, uid, "Usuario")))


def _responsible_conflicts(user, new_section_id):
    return db.session.scalars(db.select(ServiceL2.code).where(
        ServiceL2.responsible_user_id == user.id, ServiceL2.is_active.is_(True),
        ServiceL2.section_id != new_section_id).limit(10)).all()


@bp.post("/users")
def create_user():
    data = request.get_json(silent=True)
    v = Validator(data)
    name = v.text("name", "El nombre")
    username = v.text("username", "El usuario o correo", lower=True)
    role = v.choice("role", "El rol", ("admin", "consulta"))
    pid = v.integer("position_id", "El puesto")
    v.check()
    check_password_policy((data or {}).get("password"))
    _check_parent(("position_id", Position, "El puesto"), pid)
    if db.session.scalar(db.select(User.id).where(User.username == username)):
        raise ApiError(409, "duplicate_username", f"Ya existe un usuario «{username}».", fields={"username": "Duplicado."})
    u = User(name=name, username=username, role=role, position_id=pid, is_active=True,
             password_hash=hash_password(data["password"]))
    db.session.add(u)
    commit_or_conflict()
    return jsonify(user_dict(u)), 201


@bp.put("/users/<int:uid>")
def update_user(uid):
    u = _get(User, uid, "Usuario")
    data = request.get_json(silent=True)
    Validator(data)  # exige objeto JSON
    v = Validator({"name": (data or {}).get("name", u.name), "username": (data or {}).get("username", u.username),
                   "role": (data or {}).get("role", u.role), "position_id": (data or {}).get("position_id", u.position_id),
                   "is_active": (data or {}).get("is_active", u.is_active)})
    name = v.text("name", "El nombre")
    username = v.text("username", "El usuario o correo", lower=True)
    role = v.choice("role", "El rol", ("admin", "consulta"))
    pid = v.integer("position_id", "El puesto")
    active = v.boolean("is_active", "El estado", default=u.is_active)
    v.check()
    if "password" in data and data["password"] not in (None, ""):
        check_password_policy(data["password"])
        u.password_hash = hash_password(data["password"])
        revoke_user_sessions(u.id)
    if db.session.scalar(db.select(User.id).where(User.username == username, User.id != u.id)):
        raise ApiError(409, "duplicate_username", f"Ya existe un usuario «{username}».", fields={"username": "Duplicado."})
    if pid != u.position_id:
        pos = _check_parent(("position_id", Position, "El puesto"), pid)
        bad = _responsible_conflicts(u, pos.section_id)
        if bad:
            raise ApiError(409, "responsible_conflict",
                           "El usuario es responsable de servicios de su sección actual; reasígnelos antes de moverlo: " + ", ".join(bad))
        u.position_id = pid
    if role != "admin" and u.role == "admin" and u.is_active:
        _ensure_other_admin(u)
    if not active and u.is_active:
        deactivate_tree(u, cascade=False)
    elif active and not u.is_active:
        _check_parent(("position_id", Position, "El puesto"), u.position_id)
        u.is_active = True
    u.name, u.username, u.role = name, username, role
    commit_or_conflict()
    return jsonify(user_dict(u))


def _ensure_other_admin(u):
    n = db.session.scalar(db.select(func.count()).select_from(User).where(
        User.role == "admin", User.is_active.is_(True), User.id != u.id))
    if n == 0:
        raise ApiError(409, "last_admin", "No se puede quitar el rol al último administrador activo.")


@bp.delete("/users/<int:uid>")
def deactivate_user(uid):
    u = _get(User, uid, "Usuario")
    if u.is_active:
        deactivate_tree(u, cascade=False)
    commit_or_conflict()
    return jsonify(user_dict(u))
