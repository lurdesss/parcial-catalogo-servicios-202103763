import json

from ..models import Area, Company, Department, Position, Section


def iso(dt):
    return dt.isoformat() if dt else None


def num(d):
    return None if d is None else float(d)


def position_path(pos):
    """Empresa > Área > Departamento > Sección > Puesto (la empresa se deriva de la jerarquía)."""
    if pos is None:
        return None
    sec = pos.section
    dep = sec.department
    area = dep.area
    comp = area.company
    return {
        "company": {"id": comp.id, "code": comp.code, "name": comp.name},
        "area": {"id": area.id, "code": area.code, "name": area.name},
        "department": {"id": dep.id, "code": dep.code, "name": dep.name},
        "section": {"id": sec.id, "code": sec.code, "name": sec.name},
        "position": {"id": pos.id, "code": pos.code, "name": pos.name},
        "text": " > ".join([comp.name, area.name, dep.name, sec.name, pos.name]),
    }


def section_path(sec):
    if sec is None:
        return None
    dep = sec.department
    area = dep.area
    comp = area.company
    return {"id": sec.id, "code": sec.code, "name": sec.name,
            "text": " > ".join([comp.name, area.name, dep.name, sec.name])}


PARENT_REL = {Company: None, Area: "company", Department: "area", Section: "department", Position: "section"}
PARENT_FK = {Company: None, Area: "company_id", Department: "area_id", Section: "department_id", Position: "section_id"}


def unit_dict(obj):
    cls = type(obj)
    d = {"id": obj.id, "code": obj.code, "name": obj.name, "is_active": obj.is_active,
         "created_at": iso(obj.created_at), "updated_at": iso(obj.updated_at)}
    rel = PARENT_REL[cls]
    if rel:
        parent = getattr(obj, rel)
        d[PARENT_FK[cls]] = getattr(obj, PARENT_FK[cls])
        d["parent_name"] = f"{parent.code} · {parent.name}"
    return d


def user_dict(u):
    """Nunca incluye password_hash."""
    return {"id": u.id, "name": u.name, "username": u.username, "role": u.role,
            "is_active": u.is_active, "position_id": u.position_id,
            "organization": position_path(u.position)}


def catalog_dict(c):
    return {"id": c.id, "name": c.name, "sort_order": c.sort_order, "is_active": c.is_active}


def l1_dict(s):
    return {"id": s.id, "code": s.code, "code_original": s.code_original, "name": s.name,
            "is_active": s.is_active, "source_sheet": s.source_sheet, "source_range": s.source_range,
            "source_notes": json.loads(s.source_notes) if s.source_notes else None}


def _ref(o):
    return None if o is None else {"id": o.id, "name": o.name}


def l2_dict(s):
    return {
        "id": s.id, "code": s.code, "code_original": s.code_original, "name": s.name,
        "level1": {"id": s.level1.id, "code": s.level1.code, "name": s.level1.name},
        "activo_excel": s.activo_excel, "activo_raw": s.activo_raw,
        "class": _ref(s.service_class), "criticality": _ref(s.criticality), "type": _ref(s.service_type),
        "description": s.description, "metric": s.metric,
        "min_value": num(s.min_value), "max_value": num(s.max_value),
        "section": section_path(s.section),
        "responsible": None if s.responsible is None else
        {"id": s.responsible.id, "name": s.responsible.name, "username": s.responsible.username},
        "is_active": s.is_active, "review_status": s.review_status,
        "source_sheet": s.source_sheet, "source_range": s.source_range,
        "source_notes": json.loads(s.source_notes) if s.source_notes else None,
        "updated_at": iso(s.updated_at),
    }
