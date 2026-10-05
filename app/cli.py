import os

import click

from .extensions import db
from .importer import ImportFailure, run_import
from .models import Area, Company, Department, Position, Section, ServiceL2, User
from .security import hash_password


def _get_or_create(model, defaults=None, **keys):
    obj = db.session.scalar(db.select(model).filter_by(**keys))
    if obj:
        return obj, False
    obj = model(**keys, **(defaults or {}))
    db.session.add(obj)
    db.session.flush()
    return obj, True


def _demo_org():
    c, _ = _get_or_create(Company, {"name": "Organización Demo", "is_active": True}, code="DEMO")
    a, _ = _get_or_create(Area, {"name": "Tecnología", "is_active": True}, company_id=c.id, code="TI")
    d, _ = _get_or_create(Department, {"name": "Operaciones TI", "is_active": True}, area_id=a.id, code="OPS")
    s1, _ = _get_or_create(Section, {"name": "Soporte", "is_active": True}, department_id=d.id, code="SOP")
    s2, _ = _get_or_create(Section, {"name": "Desarrollo", "is_active": True}, department_id=d.id, code="DEV")
    p1, _ = _get_or_create(Position, {"name": "Analista de soporte", "is_active": True}, section_id=s1.id, code="AN-SOP")
    p2, _ = _get_or_create(Position, {"name": "Analista de desarrollo", "is_active": True}, section_id=s2.id, code="AN-DEV")
    return s1, s2, p1, p2


def register(app):
    @app.cli.command("import-catalog")
    @click.option("--file", "path", default=None, help="Ruta del Excel (por defecto CATALOG_XLSX).")
    def import_catalog(path):
        """Importa el catálogo desde el Excel original (repetible)."""
        try:
            run = run_import(path or app.config["CATALOG_XLSX"], app.config["IMPORT_MAPPING"])
        except ImportFailure as e:
            raise SystemExit(f"ERROR: {e}")
        click.echo(f"Importación #{run.id}: creados={run.created} actualizados={run.updated} "
                   f"omitidos={run.skipped} observados={run.observed} | N1={run.n1_codes} N2={run.n2_codes}")
        click.echo(f"Resumen: {run.summary}")

    @app.cli.command("create-eval-users")
    def create_eval_users():
        """Crea (o actualiza) las cuentas de evaluación admin y consulta desde variables de entorno."""
        cfg = {}
        for role, prefix in (("admin", "EVAL_ADMIN"), ("consulta", "EVAL_VIEWER")):
            user, pwd = os.environ.get(f"{prefix}_USER"), os.environ.get(f"{prefix}_PASSWORD")
            if not user or not pwd or len(pwd) < 8:
                raise SystemExit(f"Defina {prefix}_USER y {prefix}_PASSWORD (mín. 8 caracteres) en .env.")
            cfg[role] = (user.strip().lower(), pwd)
        _, _, p1, p2 = _demo_org()
        for (role, (username, pwd)), pos in zip(cfg.items(), (p1, p2)):
            u, created = _get_or_create(User, {"name": f"Demo {role}", "role": role, "is_active": True,
                                               "position_id": pos.id, "password_hash": hash_password(pwd)}, username=username)
            if not created:
                u.password_hash, u.role, u.is_active = hash_password(pwd), role, True
            click.echo(f"{'Creado' if created else 'Actualizado'}: {username} ({role})")
        db.session.commit()

    @app.cli.command("seed-demo")
    def seed_demo():
        """Asigna 3 servicios N2 importados a secciones/usuarios de demostración (idempotente)."""
        s1, s2, p1, p2 = _demo_org()
        users = {p.id: db.session.scalar(db.select(User).where(User.position_id == p.id, User.is_active.is_(True)).order_by(User.id)) for p in (p1, p2)}
        services = db.session.scalars(db.select(ServiceL2).where(ServiceL2.is_active.is_(True)).order_by(ServiceL2.code).limit(3)).all()
        if len(services) < 3:
            raise SystemExit("Importe primero el catálogo (flask import-catalog); se requieren al menos 3 servicios N2.")
        plan = [(services[0], s1, users[p1.id]), (services[1], s2, users[p2.id]), (services[2], s1, None)]
        for svc, sec, usr in plan:
            svc.section_id, svc.responsible_user_id = sec.id, usr.id if usr else None
            click.echo(f"{svc.code} → sección {sec.code}, responsable {usr.username if usr else '—'}")
        db.session.commit()
