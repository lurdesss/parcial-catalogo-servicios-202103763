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
            "service_roles": sorted(r.role_code for r in u.service_roles),
            "is_active": u.is_active, "position_id": u.position_id,
            "organization": position_path(u.position)}


def user_ref(u):
    return None if u is None else {"id": u.id, "name": u.name, "username": u.username}


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


# ============================================================ PARCIAL 3: CMDB
def ci_class_dict(c):
    return {"id": c.id, "code": c.code, "name": c.name, "parent_id": c.parent_id,
            "is_active": c.is_active, "requires_ip": c.requires_ip,
            "parent_name": f"{c.parent.code} · {c.parent.name}" if c.parent else None}


def location_dict(loc):
    return {"id": loc.id, "code": loc.code, "name": loc.name, "is_active": loc.is_active}


def device_dict(d):
    return {
        "id": d.id, "asset_tag": d.asset_tag, "name": d.name,
        "ci_class": _ref(d.ci_class) | {"code": d.ci_class.code} if d.ci_class else None,
        "status": d.status, "location": _ref(d.location) | {"code": d.location.code} if d.location else None,
        "owner": user_ref(d.owner), "ip_address": d.ip_address, "serial_number": d.serial_number,
        "attributes": d.attributes or {}, "is_active": d.is_active,
        "updated_at": iso(d.updated_at),
    }


def device_relation_dict(r):
    return {"id": r.id, "from_device": {"id": r.from_device.id, "asset_tag": r.from_device.asset_tag, "name": r.from_device.name},
            "to_device": {"id": r.to_device.id, "asset_tag": r.to_device.asset_tag, "name": r.to_device.name},
            "relation_type": r.relation_type}


# ============================================================ PARCIAL 3: Service Desk
def process_dict(p):
    return {"id": p.id, "code": p.code, "name": p.name, "ticket_type": p.ticket_type}


def queue_permission_dict(p):
    return {"id": p.id, "principal_role": p.principal_role, "principal_user": user_ref(p.principal_user),
            "can_view": p.can_view, "can_work": p.can_work, "can_transfer": p.can_transfer,
            "can_approve": p.can_approve, "can_manage": p.can_manage}


def queue_dict(q, with_permissions=False):
    out = {"id": q.id, "code": q.code, "name": q.name, "description": q.description, "is_active": q.is_active,
           "process": process_dict(q.process), "support_level": q.support_level,
           "ordering_rule": q.ordering_rule, "targets": q.targets or {}}
    if with_permissions:
        out["permissions"] = [queue_permission_dict(p) for p in q.permissions]
    return out


def ticket_list_dict(t):
    return {
        "id": t.id, "number": t.number, "title": t.title, "ticket_type": t.ticket_type,
        "process": {"code": t.process.code, "name": t.process.name},
        "queue": {"id": t.queue.id, "code": t.queue.code, "name": t.queue.name},
        "service_l2": None if not t.service_l2 else {"id": t.service_l2.id, "code": t.service_l2.code, "name": t.service_l2.name},
        "requester": user_ref(t.requester), "assignee": user_ref(t.assignee),
        "state": t.state, "priority": t.priority, "impact": t.impact, "urgency": t.urgency, "channel": t.channel,
        "created_at": iso(t.created_at), "updated_at": iso(t.updated_at),
        "resolved_at": iso(t.resolved_at), "closed_at": iso(t.closed_at),
    }


def ticket_comment_dict(c):
    return {"id": c.id, "author": user_ref(c.author), "body": c.body, "visibility": c.visibility,
            "created_at": iso(c.created_at)}


def ticket_attachment_dict(a):
    return {"id": a.id, "filename": a.filename, "content_type": a.content_type, "size_bytes": a.size_bytes,
            "created_at": iso(a.created_at)}


def ticket_history_dict(h):
    return {"id": h.id, "actor_id": h.actor_user_id, "action": h.action, "field": h.field,
            "old_value": h.old_value, "new_value": h.new_value, "created_at": iso(h.created_at)}


def _detail_dict(t):
    if t.ticket_type == "incidente" and t.incident_detail:
        d = t.incident_detail
        return {"category": d.category, "estimated_minutes": d.estimated_minutes,
                "actual_minutes": d.actual_minutes, "redundancy_available": d.redundancy_available}
    if t.ticket_type == "evento" and t.event_detail:
        d = t.event_detail
        return {"category": d.category, "linked_incident_id": d.linked_incident_id}
    if t.ticket_type == "solicitud_cambio" and t.change_detail:
        d = t.change_detail
        return {"change_type": d.change_type, "risk_level": d.risk_level, "test_plan": d.test_plan,
                "rollback_plan": d.rollback_plan, "approved_by_id": d.approved_by_user_id, "approved_at": iso(d.approved_at)}
    if t.problem_detail:
        d = t.problem_detail
        return {"root_cause": d.root_cause, "workaround": d.workaround, "known_error": d.known_error,
                "permanent_solution": d.permanent_solution, "linked_change_id": d.linked_change_id,
                "linked_incident_id": d.linked_incident_id}
    if t.access_detail:
        d = t.access_detail
        return {"beneficiary": user_ref(d.beneficiary), "resource": d.resource,
                "permission_requested": d.permission_requested, "approver": user_ref(d.approver),
                "approved_at": iso(d.approved_at)}
    if t.new_service_detail:
        d = t.new_service_detail
        return {"proposed_name": d.proposed_name, "proposed_level1_id": d.proposed_level1_id,
                "created_service_l2_id": d.created_service_l2_id}
    return None


def ticket_detail_dict(t):
    return {
        **ticket_list_dict(t), "description": t.description, "creator": user_ref(t.creator),
        "detail": _detail_dict(t),
        "ci_links": [{"id": link.device.id, "asset_tag": link.device.asset_tag, "name": link.device.name} for link in t.ci_links],
        "relations": [{"ticket_id": r.related_ticket_id, "relation_type": r.relation_type} for r in t.relations_from],
        "comments": [ticket_comment_dict(c) for c in sorted(t.comments, key=lambda c: c.created_at)],
        "attachments": [ticket_attachment_dict(a) for a in t.attachments],
        "history": [ticket_history_dict(h) for h in sorted(t.history, key=lambda h: h.created_at)],
    }
