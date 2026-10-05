from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint

from .extensions import db


def utcnow():
    """UTC ingenuo: se almacena igual en SQLite y PostgreSQL."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Timestamps:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# ---------------------------------------------------------------- organización
class Company(Timestamps, db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Area(Timestamps, db.Model):
    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_area_company_code"),)
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    company = db.relationship("Company")


class Department(Timestamps, db.Model):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("area_id", "code", name="uq_department_area_code"),)
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    area_id = db.Column(db.Integer, db.ForeignKey("areas.id"), nullable=False, index=True)
    area = db.relationship("Area")


class Section(Timestamps, db.Model):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("department_id", "code", name="uq_section_department_code"),)
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False, index=True)
    department = db.relationship("Department")


class Position(Timestamps, db.Model):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("section_id", "code", name="uq_position_section_code"),)
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False, index=True)
    section = db.relationship("Section")


class User(Timestamps, db.Model):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin','consulta')", name="ck_user_role"),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(200), nullable=False, unique=True)  # usuario o correo, en minúsculas
    password_hash = db.Column(db.String(300), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    position_id = db.Column(db.Integer, db.ForeignKey("positions.id"), nullable=False, index=True)
    position = db.relationship("Position")


class UserSession(db.Model):
    """Sesión del lado del servidor: el cierre de sesión la elimina y deja inservible la cookie."""
    __tablename__ = "user_sessions"
    id = db.Column(db.Integer, primary_key=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    csrf_token = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    user = db.relationship("User")


# ------------------------------------------------------------ catálogos de apoyo
class _CatalogItem(Timestamps):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class ServiceClass(_CatalogItem, db.Model):
    __tablename__ = "service_classes"


class Criticality(_CatalogItem, db.Model):
    __tablename__ = "criticalities"


class ServiceType(_CatalogItem, db.Model):
    __tablename__ = "service_types"


# -------------------------------------------------------------------- servicios
class ServiceL1(Timestamps, db.Model):
    __tablename__ = "services_l1"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True)
    code_original = db.Column(db.String(60))          # valor tal como venía en el Excel
    name = db.Column(db.String(300), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    source_sheet = db.Column(db.String(100))
    source_range = db.Column(db.String(200))
    source_notes = db.Column(db.Text)                 # JSON: transformaciones y evidencia


class ServiceL2(Timestamps, db.Model):
    __tablename__ = "services_l2"
    __table_args__ = (
        CheckConstraint("activo_excel IS NULL OR activo_excel IN ('S','N')", name="ck_l2_activo"),
        CheckConstraint("min_value IS NULL OR max_value IS NULL OR min_value <= max_value", name="ck_l2_min_max"),
        CheckConstraint("review_status IN ('ok','revisar')", name="ck_l2_review"),
    )
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), nullable=False, unique=True)
    code_original = db.Column(db.String(60))
    name = db.Column(db.String(300), nullable=False)
    level1_id = db.Column(db.Integer, db.ForeignKey("services_l1.id"), nullable=False, index=True)
    activo_excel = db.Column(db.String(1))            # S / N / NULL = desconocido
    activo_raw = db.Column(db.String(100))            # valor original si no es S/N
    class_id = db.Column(db.Integer, db.ForeignKey("service_classes.id"))
    criticality_id = db.Column(db.Integer, db.ForeignKey("criticalities.id"))
    type_id = db.Column(db.Integer, db.ForeignKey("service_types.id"))
    description = db.Column(db.Text)
    metric = db.Column(db.String(300))
    min_value = db.Column(db.Numeric(20, 6))
    max_value = db.Column(db.Numeric(20, 6))
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), index=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)   # baja lógica en el sistema
    review_status = db.Column(db.String(10), nullable=False, default="ok")
    source_sheet = db.Column(db.String(100))
    source_range = db.Column(db.String(200))
    source_notes = db.Column(db.Text)

    level1 = db.relationship("ServiceL1")
    service_class = db.relationship("ServiceClass")
    criticality = db.relationship("Criticality")
    service_type = db.relationship("ServiceType")
    section = db.relationship("Section")
    responsible = db.relationship("User")


# -------------------------------------------------------------------- importación
class ImportRun(db.Model):
    __tablename__ = "import_runs"
    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    finished_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="running")  # running/ok/error
    file_name = db.Column(db.String(300))
    file_sha256 = db.Column(db.String(64))
    created = db.Column(db.Integer, nullable=False, default=0)
    updated = db.Column(db.Integer, nullable=False, default=0)
    skipped = db.Column(db.Integer, nullable=False, default=0)
    observed = db.Column(db.Integer, nullable=False, default=0)
    n1_codes = db.Column(db.Integer, nullable=False, default=0)
    n2_codes = db.Column(db.Integer, nullable=False, default=0)
    summary = db.Column(db.Text)


class ImportObservation(db.Model):
    __tablename__ = "import_observations"
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("import_runs.id"), nullable=False, index=True)
    kind = db.Column(db.String(50), nullable=False)
    sheet = db.Column(db.String(100))
    row_ref = db.Column(db.String(100))
    code = db.Column(db.String(60))
    detail = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text)  # JSON
