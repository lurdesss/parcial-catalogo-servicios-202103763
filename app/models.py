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


# ============================================================ PARCIAL 3: Service Desk
# Roles base (admin/consulta) se mantienen sin cambios (ver User arriba). Los roles
# funcionales de Service Desk son ADITIVOS: un usuario puede tener 0..N de ellos además
# de su rol base. No se toca el CHECK de User.role para no romper nada del Parcial 2.
SERVICE_ROLES = ("solicitante", "agente", "aprobador")


class UserServiceRole(db.Model):
    __tablename__ = "user_service_roles"
    __table_args__ = (CheckConstraint("role_code IN ('solicitante','agente','aprobador')", name="ck_usr_role"),)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    role_code = db.Column(db.String(20), primary_key=True)
    user = db.relationship("User", backref="service_roles")


# ------------------------------------------------------------------------- 7 procesos
class Process(db.Model):
    __tablename__ = "processes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    ticket_type = db.Column(db.String(30), nullable=False)  # tipo de ticket (diapositiva 14) al que se mapea


class ProcessState(db.Model):
    __tablename__ = "process_states"
    __table_args__ = (UniqueConstraint("process_id", "code", name="uq_state_process_code"),)
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_initial = db.Column(db.Boolean, nullable=False, default=False)
    is_final = db.Column(db.Boolean, nullable=False, default=False)


class ProcessTransition(db.Model):
    """Grafo de flujo de un proceso: nodos = process_states, aristas = esta tabla."""
    __tablename__ = "process_transitions"
    __table_args__ = (UniqueConstraint("process_id", "from_code", "to_code", "action", name="uq_transition"),)
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    from_code = db.Column(db.String(30), nullable=False)
    to_code = db.Column(db.String(30), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    required_perm = db.Column(db.String(20))  # None = basta can_work; 'approve' = exige can_approve en la cola


# ------------------------------------------------------------------------------ colas
class Queue(Timestamps, db.Model):
    __tablename__ = "queues"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    support_level = db.Column(db.String(20), nullable=False, default="nivel1")
    ordering_rule = db.Column(db.String(30), nullable=False, default="priority_then_age")
    targets = db.Column(db.JSON)  # {"alta": 240, "media": 480, "baja": 1440} minutos objetivo de 1ª atención
    process = db.relationship("Process")


class QueuePermission(db.Model):
    """Autoriza una cola a un rol (principal_role) o a un usuario (principal_user_id), nunca ambos."""
    __tablename__ = "queue_permissions"
    __table_args__ = (
        CheckConstraint("(principal_role IS NOT NULL) <> (principal_user_id IS NOT NULL)", name="ck_qp_principal_xor"),
    )
    id = db.Column(db.Integer, primary_key=True)
    queue_id = db.Column(db.Integer, db.ForeignKey("queues.id"), nullable=False, index=True)
    principal_role = db.Column(db.String(20))
    principal_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    can_view = db.Column(db.Boolean, nullable=False, default=True)
    can_work = db.Column(db.Boolean, nullable=False, default=False)
    can_transfer = db.Column(db.Boolean, nullable=False, default=False)
    can_approve = db.Column(db.Boolean, nullable=False, default=False)
    can_manage = db.Column(db.Boolean, nullable=False, default=False)
    queue = db.relationship("Queue", backref="permissions")
    principal_user = db.relationship("User")


# -------------------------------------------------------------------------------- CMDB
class CiClass(Timestamps, db.Model):
    """Jerarquía de clasificación de CI (catálogo editable, auto-referenciado). Ver docs/MODELO.md
    para el mapeo con CMDB.xlsx y Transicion.pptx.pdf (no hay fuente con niveles verificables más
    allá de Hardware/Software; esta jerarquía es una decisión de proyecto documentada)."""
    __tablename__ = "ci_classes"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("ci_classes.id"), index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    requires_ip = db.Column(db.Boolean, nullable=False, default=False)
    parent = db.relationship("CiClass", remote_side=[id])


class Location(Timestamps, db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(150), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Device(Timestamps, db.Model):
    __tablename__ = "devices"
    __table_args__ = (CheckConstraint("status IN ('activo','inactivo','retirado')", name="ck_device_status"),)
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(60), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    ci_class_id = db.Column(db.Integer, db.ForeignKey("ci_classes.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="activo")
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), index=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    ip_address = db.Column(db.String(45))          # nunca obligatoria
    serial_number = db.Column(db.String(100))
    attributes = db.Column(db.JSON)                 # atributos técnicos según la clase
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    generator_seed = db.Column(db.Integer)           # semilla que lo generó (reproducibilidad/idempotencia)
    ci_class = db.relationship("CiClass")
    location = db.relationship("Location")
    owner = db.relationship("User")


class DeviceRelation(db.Model):
    """Relaciones técnicas entre CI (distintas de la jerarquía de clasificación). depende_de/alojado_en
    no admiten ciclos; conectado_a sí (ver app/graph_cmdb.py)."""
    __tablename__ = "device_relations"
    __table_args__ = (UniqueConstraint("from_device_id", "to_device_id", "relation_type", name="uq_device_relation"),)
    id = db.Column(db.Integer, primary_key=True)
    from_device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False, index=True)
    to_device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False, index=True)
    relation_type = db.Column(db.String(20), nullable=False)
    from_device = db.relationship("Device", foreign_keys=[from_device_id])
    to_device = db.relationship("Device", foreign_keys=[to_device_id])


class ServiceCiLink(db.Model):
    __tablename__ = "service_ci_links"
    service_l2_id = db.Column(db.Integer, db.ForeignKey("services_l2.id"), primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), primary_key=True)


# ----------------------------------------------------------------------------- tickets
class Ticket(Timestamps, db.Model):
    __tablename__ = "tickets"
    __table_args__ = (CheckConstraint("priority IN ('baja','media','alta')", name="ck_ticket_priority"),)
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), nullable=False, unique=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    ticket_type = db.Column(db.String(30), nullable=False)
    process_id = db.Column(db.Integer, db.ForeignKey("processes.id"), nullable=False, index=True)
    queue_id = db.Column(db.Integer, db.ForeignKey("queues.id"), nullable=False, index=True)
    service_l2_id = db.Column(db.Integer, db.ForeignKey("services_l2.id"), index=True)
    requester_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    creator_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    state = db.Column(db.String(30), nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="media")
    impact = db.Column(db.String(10))
    urgency = db.Column(db.String(10))
    channel = db.Column(db.String(30), nullable=False, default="portal")
    resolved_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    process = db.relationship("Process")
    queue = db.relationship("Queue")
    service_l2 = db.relationship("ServiceL2")
    requester = db.relationship("User", foreign_keys=[requester_user_id])
    creator = db.relationship("User", foreign_keys=[creator_user_id])
    assignee = db.relationship("User", foreign_keys=[assignee_user_id])
    incident_detail = db.relationship("TicketIncidentDetail", uselist=False, backref="ticket")
    event_detail = db.relationship("TicketEventDetail", uselist=False, backref="ticket",
                                    foreign_keys="TicketEventDetail.ticket_id")
    change_detail = db.relationship("TicketChangeDetail", uselist=False, backref="ticket")
    problem_detail = db.relationship("TicketProblemDetail", uselist=False, backref="ticket",
                                      foreign_keys="TicketProblemDetail.ticket_id")
    access_detail = db.relationship("TicketAccessDetail", uselist=False, backref="ticket",
                                     foreign_keys="TicketAccessDetail.ticket_id")
    new_service_detail = db.relationship("TicketNewServiceDetail", uselist=False, backref="ticket")
    ci_links = db.relationship("TicketCiLink", backref="ticket")
    relations_from = db.relationship("TicketRelation", foreign_keys="TicketRelation.ticket_id", backref="ticket")
    comments = db.relationship("TicketComment", backref="ticket")
    attachments = db.relationship("TicketAttachment", backref="ticket")
    history = db.relationship("TicketHistory", backref="ticket")


class TicketIncidentDetail(db.Model):
    __tablename__ = "ticket_incident_details"
    __table_args__ = (CheckConstraint("category IN ('I0','I1','I2','I3','I4','I5','I6')", name="ck_incident_cat"),)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    category = db.Column(db.String(4), nullable=False)
    estimated_minutes = db.Column(db.Integer)
    actual_minutes = db.Column(db.Integer)
    redundancy_available = db.Column(db.Boolean)


class TicketEventDetail(db.Model):
    __tablename__ = "ticket_event_details"
    __table_args__ = (CheckConstraint("category IN ('E0','E1','E2','E3')", name="ck_event_cat"),)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    category = db.Column(db.String(4), nullable=False)
    linked_incident_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))


class TicketChangeDetail(db.Model):
    __tablename__ = "ticket_change_details"
    __table_args__ = (CheckConstraint("change_type IN ('estandar','normal','emergencia')", name="ck_change_type"),)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    change_type = db.Column(db.String(20), nullable=False, default="normal")
    risk_level = db.Column(db.String(10))
    test_plan = db.Column(db.Text)
    rollback_plan = db.Column(db.Text)
    approved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)


class TicketProblemDetail(db.Model):
    __tablename__ = "ticket_problem_details"
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    root_cause = db.Column(db.Text)
    workaround = db.Column(db.Text)
    known_error = db.Column(db.Boolean, nullable=False, default=False)
    permanent_solution = db.Column(db.Text)
    linked_change_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))
    linked_incident_id = db.Column(db.Integer, db.ForeignKey("tickets.id"))


class TicketAccessDetail(db.Model):
    __tablename__ = "ticket_access_details"
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    beneficiary_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resource = db.Column(db.String(300), nullable=False)
    permission_requested = db.Column(db.String(300))
    approver_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)
    beneficiary = db.relationship("User", foreign_keys=[beneficiary_user_id])
    approver = db.relationship("User", foreign_keys=[approver_user_id])


class TicketNewServiceDetail(db.Model):
    __tablename__ = "ticket_new_service_details"
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    proposed_name = db.Column(db.String(300), nullable=False)
    proposed_level1_id = db.Column(db.Integer, db.ForeignKey("services_l1.id"))
    created_service_l2_id = db.Column(db.Integer, db.ForeignKey("services_l2.id"))


class TicketCiLink(db.Model):
    __tablename__ = "ticket_ci_links"
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("devices.id"), primary_key=True)
    device = db.relationship("Device")


class TicketRelation(db.Model):
    __tablename__ = "ticket_relations"
    __table_args__ = (UniqueConstraint("ticket_id", "related_ticket_id", "relation_type", name="uq_ticket_relation"),)
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    related_ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    relation_type = db.Column(db.String(20), nullable=False, default="relacionado")


class TicketComment(db.Model):
    __tablename__ = "ticket_comments"
    __table_args__ = (CheckConstraint("visibility IN ('publico','interno')", name="ck_comment_visibility"),)
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.String(10), nullable=False, default="publico")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    author = db.relationship("User")


class TicketAttachment(db.Model):
    __tablename__ = "ticket_attachments"
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    storage_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)


class TicketHistory(db.Model):
    """Bitácora de auditoría append-only: nunca se borra ni se actualiza (ver app/api/tickets.py)."""
    __tablename__ = "ticket_history"
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(40), nullable=False)
    field = db.Column(db.String(60))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
