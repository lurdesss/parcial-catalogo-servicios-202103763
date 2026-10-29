import os

import click

from . import cmdb_generator, seed_servicedesk
from .cli_helpers import demo_org, get_or_create
from .extensions import db
from .importer import ImportFailure, run_import
from .models import ServiceL2, User, UserServiceRole
from .security import hash_password


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
        """Crea (o actualiza) las cuentas de evaluación: admin, consulta y los 3 roles
        funcionales de Service Desk (solicitante/agente/aprobador, aditivos sobre 'consulta'),
        desde variables de entorno."""
        base_roles = {}
        for role, prefix in (("admin", "EVAL_ADMIN"), ("consulta", "EVAL_VIEWER")):
            user, pwd = os.environ.get(f"{prefix}_USER"), os.environ.get(f"{prefix}_PASSWORD")
            if not user or not pwd or len(pwd) < 8:
                raise SystemExit(f"Defina {prefix}_USER y {prefix}_PASSWORD (mín. 8 caracteres) en .env.")
            base_roles[role] = (user.strip().lower(), pwd)
        service_accounts = {}
        for svc_role, prefix in (("solicitante", "EVAL_SOLICITANTE"), ("agente", "EVAL_AGENTE"),
                                  ("aprobador", "EVAL_APROBADOR")):
            user, pwd = os.environ.get(f"{prefix}_USER"), os.environ.get(f"{prefix}_PASSWORD")
            if not user or not pwd or len(pwd) < 8:
                raise SystemExit(f"Defina {prefix}_USER y {prefix}_PASSWORD (mín. 8 caracteres) en .env.")
            service_accounts[svc_role] = (user.strip().lower(), pwd)

        _, _, p1, p2 = demo_org()
        positions = [p1, p2, p1, p2, p1]
        for (role, (username, pwd)), pos in zip(base_roles.items(), positions):
            u, created = get_or_create(User, {"name": f"Demo {role}", "role": role, "is_active": True,
                                              "position_id": pos.id, "password_hash": hash_password(pwd)}, username=username)
            if not created:
                u.password_hash, u.role, u.is_active = hash_password(pwd), role, True
            click.echo(f"{'Creado' if created else 'Actualizado'}: {username} ({role})")
        for i, (svc_role, (username, pwd)) in enumerate(service_accounts.items()):
            pos = positions[(2 + i) % len(positions)]
            u, created = get_or_create(User, {"name": f"Demo {svc_role}", "role": "consulta", "is_active": True,
                                              "position_id": pos.id, "password_hash": hash_password(pwd)}, username=username)
            if not created:
                u.password_hash, u.is_active = hash_password(pwd), True
            db.session.flush()
            if not db.session.get(UserServiceRole, (u.id, svc_role)):
                db.session.add(UserServiceRole(user_id=u.id, role_code=svc_role))
            click.echo(f"{'Creado' if created else 'Actualizado'}: {username} (consulta + {svc_role})")
        db.session.commit()

    @app.cli.command("seed-demo")
    def seed_demo():
        """Asigna 3 servicios N2 importados a secciones/usuarios de demostración (idempotente)."""
        s1, s2, p1, p2 = demo_org()
        users = {p.id: db.session.scalar(db.select(User).where(User.position_id == p.id, User.is_active.is_(True)).order_by(User.id)) for p in (p1, p2)}
        services = db.session.scalars(db.select(ServiceL2).where(ServiceL2.is_active.is_(True)).order_by(ServiceL2.code).limit(3)).all()
        if len(services) < 3:
            raise SystemExit("Importe primero el catálogo (flask import-catalog); se requieren al menos 3 servicios N2.")
        plan = [(services[0], s1, users[p1.id]), (services[1], s2, users[p2.id]), (services[2], s1, None)]
        for svc, sec, usr in plan:
            svc.section_id, svc.responsible_user_id = sec.id, usr.id if usr else None
            click.echo(f"{svc.code} → sección {sec.code}, responsable {usr.username if usr else '—'}")
        db.session.commit()

    @app.cli.command("generate-cmdb")
    @click.option("--seed", default=42, type=int, help="Semilla determinista (por defecto 42).")
    @click.option("--count", default=5000, type=int, help="Cantidad de dispositivos (por defecto 5000).")
    def generate_cmdb(seed, count):
        """Genera (o actualiza, si se repite con la misma semilla) dispositivos sintéticos de la CMDB."""
        report = cmdb_generator.generate(seed, count)
        click.echo(f"CMDB semilla={report['seed']}: creados={report['created']} actualizados={report['updated']} "
                   f"total={report['total']} (objetivo={count})")
        click.echo(f"Por nivel raíz: {report['por_nivel_raiz']}")
        click.echo(f"Por clase: {report['por_clase']}")
        click.echo(f"Relaciones creadas: {report['relaciones_creadas']} · Vínculos a servicios: {report['vinculos_servicio_creados']}")

    @app.cli.command("seed-servicedesk-demo")
    def seed_servicedesk_demo():
        """Crea ≥7 colas (una por proceso), sus permisos de rol y ≥35 tickets de demostración
        (idempotente: no duplica si ya existen)."""
        report = seed_servicedesk.run()
        click.echo(f"Service Desk demo: {report['colas']} colas, {report['tickets_creados']} tickets nuevos creados.")
