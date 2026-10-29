"""Utilidades compartidas entre comandos CLI (app/cli.py) y datos de demostración
(app/seed_servicedesk.py)."""
from .extensions import db
from .models import Area, Company, Department, Position, Section


def get_or_create(model, defaults=None, **keys):
    obj = db.session.scalar(db.select(model).filter_by(**keys))
    if obj:
        return obj, False
    obj = model(**keys, **(defaults or {}))
    db.session.add(obj)
    db.session.flush()
    return obj, True


def demo_org():
    c, _ = get_or_create(Company, {"name": "Organización Demo", "is_active": True}, code="DEMO")
    a, _ = get_or_create(Area, {"name": "Tecnología", "is_active": True}, company_id=c.id, code="TI")
    d, _ = get_or_create(Department, {"name": "Operaciones TI", "is_active": True}, area_id=a.id, code="OPS")
    s1, _ = get_or_create(Section, {"name": "Soporte", "is_active": True}, department_id=d.id, code="SOP")
    s2, _ = get_or_create(Section, {"name": "Desarrollo", "is_active": True}, department_id=d.id, code="DEV")
    p1, _ = get_or_create(Position, {"name": "Analista de soporte", "is_active": True}, section_id=s1.id, code="AN-SOP")
    p2, _ = get_or_create(Position, {"name": "Analista de desarrollo", "is_active": True}, section_id=s2.id, code="AN-DEV")
    return s1, s2, p1, p2
