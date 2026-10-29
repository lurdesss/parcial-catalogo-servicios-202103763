"""Datos estructurales de Parcial 3 (no son datos de demostración): los 7 procesos
obligatorios y su grafo de estados/transiciones (Grafo 2), y la jerarquía de clasificación
de CI + ubicaciones de la CMDB (Grafo 1 usa las relaciones entre dispositivos, no esto).

Única fuente de verdad de estos datos: la usan tanto `migrations/versions/0002_service_desk_cmdb.py`
(inserción SQL cruda, porque una migración de Alembic no tiene sesión ORM) como `seed_orm()`
de este mismo módulo (inserción vía SQLAlchemy ORM, usada por las pruebas —que crean el
esquema con `db.create_all()` y por tanto no ejecutan las migraciones— y disponible para
cualquier entorno que necesite poblar el esquema sin pasar por Alembic). Ver docs/MODELO.md
y docs/PROCESOS.md para la justificación de cada valor.
"""
PROCESSES = [
    ("nuevos_servicios", "Gestión de nuevos servicios", "requisicion_servicio"),
    ("cambios", "Gestión de cambios", "solicitud_cambio"),
    ("incidentes", "Gestión de incidentes", "incidente"),
    ("eventos", "Gestión de eventos", "evento"),
    ("problemas", "Gestión de problemas", "problema"),
    ("accesos", "Gestión de accesos", "solicitud_acceso"),
    ("servicios_tecnologia", "Gestión de servicios de tecnología", "requisicion_servicio"),
]

STATES = {
    "nuevos_servicios": [
        ("solicitado", "Solicitado", True, False), ("analisis", "En análisis", False, False),
        ("aprobado", "Aprobado", False, False), ("rechazado", "Rechazado", False, True),
        ("implementado", "Implementado", False, False), ("cerrado", "Cerrado", False, True),
    ],
    "cambios": [
        ("solicitado", "Solicitado", True, False), ("evaluacion", "Evaluación de impacto/riesgo", False, False),
        ("aprobado", "Aprobado", False, False), ("rechazado", "Rechazado", False, True),
        ("planificado", "Planificado", False, False), ("ejecutado", "Ejecutado", False, False),
        ("validado", "Validado", False, False), ("cerrado", "Cerrado", False, True),
        ("reabierto", "Reabierto", False, False),
    ],
    "incidentes": [
        ("registrado", "Registrado", True, False), ("clasificado", "Clasificado", False, False),
        ("diagnostico", "Diagnóstico", False, False), ("atencion", "En atención", False, False),
        ("escalado", "Escalado", False, False), ("recuperado", "Recuperado", False, False),
        ("resuelto", "Resuelto", False, False), ("cerrado", "Cerrado", False, True),
        ("reabierto", "Reabierto", False, False),
    ],
    "eventos": [
        ("registrado", "Registrado", True, False), ("evaluado", "Evaluado", False, False),
        ("cerrado", "Cerrado", False, True),
    ],
    "problemas": [
        ("registrado", "Registrado", True, False), ("investigacion", "Investigación de causa raíz", False, False),
        ("solucion_temporal", "Solución temporal aplicada", False, False),
        ("error_conocido", "Error conocido", False, False),
        ("solucion_definitiva", "Solución definitiva aplicada", False, False),
        ("cerrado", "Cerrado", False, True),
    ],
    "accesos": [
        ("solicitado", "Solicitado", True, False), ("aprobado", "Aprobado", False, False),
        ("rechazado", "Rechazado", False, True), ("provisionado", "Provisionado", False, False),
        ("revocado", "Revocado", False, True), ("cerrado", "Cerrado", False, True),
    ],
    "servicios_tecnologia": [
        ("solicitado", "Solicitado", True, False), ("validacion", "En validación", False, False),
        ("asignado", "Asignado", False, False), ("cumplido", "Cumplido", False, False),
        ("cerrado", "Cerrado", False, True),
    ],
}

# (from, to, accion, permiso_requerido)  permiso_requerido None == basta can_work de la cola
TRANSITIONS = {
    "nuevos_servicios": [
        ("solicitado", "analisis", "iniciar_analisis", None),
        ("analisis", "aprobado", "aprobar", "approve"),
        ("analisis", "rechazado", "rechazar", "approve"),
        ("aprobado", "implementado", "implementar", None),
        ("implementado", "cerrado", "cerrar", None),
    ],
    "cambios": [
        ("solicitado", "evaluacion", "evaluar_impacto", None),
        ("evaluacion", "aprobado", "aprobar", "approve"),
        ("evaluacion", "rechazado", "rechazar", "approve"),
        ("aprobado", "planificado", "planificar", None),
        ("planificado", "ejecutado", "ejecutar", None),  # el servidor exige approved_at
        ("ejecutado", "validado", "validar", None),
        ("validado", "cerrado", "cerrar", None),
        ("cerrado", "reabierto", "reabrir", None),
        ("reabierto", "validado", "revalidar", None),
    ],
    "incidentes": [
        ("registrado", "clasificado", "clasificar", None),
        ("clasificado", "diagnostico", "diagnosticar", None),
        ("diagnostico", "atencion", "atender", None),
        ("atencion", "escalado", "escalar", None),
        ("escalado", "atencion", "reasignar", None),
        ("atencion", "recuperado", "recuperar", None),
        ("escalado", "recuperado", "recuperar", None),
        ("recuperado", "resuelto", "resolver", None),
        ("resuelto", "cerrado", "cerrar", None),
        ("atencion", "cerrado", "cerrar_sin_resolucion", None),
        ("cerrado", "reabierto", "reabrir", None),
        ("reabierto", "diagnostico", "redirigir", None),
    ],
    "eventos": [
        ("registrado", "evaluado", "evaluar", None),
        ("evaluado", "cerrado", "cerrar", None),
    ],
    "problemas": [
        ("registrado", "investigacion", "investigar", None),
        ("investigacion", "solucion_temporal", "aplicar_solucion_temporal", None),
        ("investigacion", "error_conocido", "marcar_error_conocido", None),
        ("solucion_temporal", "solucion_definitiva", "aplicar_solucion_definitiva", None),
        ("error_conocido", "solucion_definitiva", "aplicar_solucion_definitiva", None),
        ("solucion_definitiva", "cerrado", "cerrar", None),
    ],
    "accesos": [
        ("solicitado", "aprobado", "aprobar", "approve"),
        ("solicitado", "rechazado", "rechazar", "approve"),
        ("aprobado", "provisionado", "provisionar", None),
        ("provisionado", "cerrado", "cerrar", None),
        ("provisionado", "revocado", "revocar", None),
    ],
    "servicios_tecnologia": [
        ("solicitado", "validacion", "validar", None),
        ("validacion", "asignado", "asignar", None),
        ("asignado", "cumplido", "cumplir", None),
        ("cumplido", "cerrado", "confirmar_cierre", None),
    ],
}

# Jerarquía de clasificación de CI: decisión de proyecto documentada en docs/MODELO.md porque
# ninguna fuente disponible entrega niveles/denominaciones verificables más allá de los
# ejemplos "Hardware"/"Software" (CMDB.xlsx!B4:U6, Transicion.pptx.pdf p.9-14).
# (code, name, parent_code|None, requires_ip)
CI_CLASSES = [
    ("HW", "Hardware", None, False),
    ("HW.SRV", "Servidor", "HW", True),
    ("HW.WKS", "Estación de trabajo", "HW", False),
    ("HW.NET", "Equipo de red", "HW", True),
    ("HW.STO", "Almacenamiento", "HW", False),
    ("HW.PER", "Periférico", "HW", False),
    ("SW", "Software", None, False),
    ("SW.OS", "Sistema operativo", "SW", False),
    ("SW.APP", "Aplicación", "SW", False),
    ("SW.DB", "Base de datos", "SW", False),
    ("SW.LIC", "Licencia", "SW", False),
    ("DOC", "Documentación", None, False),
    ("DOC.MAN", "Manual", "DOC", False),
    ("DOC.PROC", "Procedimiento", "DOC", False),
    ("FAC", "Instalaciones", None, False),
    ("FAC.DC", "Centro de datos", "FAC", False),
    ("FAC.SRV", "Sala de servidores", "FAC", False),
]

LOCATIONS = [
    ("DC-GT01", "Centro de datos — Ciudad de Guatemala"),
    ("DC-GT02", "Centro de datos secundario (DR)"),
    ("OF-CENTRAL", "Oficina central"),
    ("OF-REGIONAL", "Oficina regional"),
    ("CLOUD-01", "Proveedor cloud — región primaria"),
]


def seed_orm():
    """Siembra vía ORM (usa `db.session` del contexto de aplicación activo); es idempotente
    porque solo inserta lo que no existe por código. Pensado para pruebas (que crean el
    esquema con `db.create_all()`, sin pasar por Alembic) y para cualquier arranque que no
    use migraciones."""
    from .extensions import db
    from .models import CiClass, Location, Process, ProcessState, ProcessTransition

    if db.session.scalar(db.select(Process.id).limit(1)):
        return  # ya sembrado
    for code, name, ticket_type in PROCESSES:
        p = Process(code=code, name=name, ticket_type=ticket_type)
        db.session.add(p)
        db.session.flush()
        for scode, sname, is_initial, is_final in STATES[code]:
            db.session.add(ProcessState(process_id=p.id, code=scode, name=sname,
                                        is_initial=is_initial, is_final=is_final))
        for frm, to, action, perm in TRANSITIONS[code]:
            db.session.add(ProcessTransition(process_id=p.id, from_code=frm, to_code=to,
                                             action=action, required_perm=perm))
    ids_by_code = {}
    for code, name, parent_code, requires_ip in CI_CLASSES:
        cls = CiClass(code=code, name=name, parent_id=ids_by_code.get(parent_code),
                      is_active=True, requires_ip=requires_ip)
        db.session.add(cls)
        db.session.flush()
        ids_by_code[code] = cls.id
    for code, name in LOCATIONS:
        db.session.add(Location(code=code, name=name, is_active=True))
    db.session.commit()
