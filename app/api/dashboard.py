"""Tablero de indicadores. Declaración de cálculo (ver docs/PROCESOS.md §Indicadores):
- Los objetivos (`queues.targets`) y todos los tiempos se miden en TIEMPO CALENDARIO (24/7),
  no tiempo hábil; se declara explícitamente por ser la opción más simple y verificable.
- "Antigüedad" = ahora - fecha de creación, solo tickets abiertos (closed_at IS NULL).
- "Primera atención" = primera vez que el ticket tuvo un responsable (bitácora: acción
  'tomado' o 'asignado') menos la fecha de creación; tickets sin asignar aún no cuentan.
- "Resolución" = fecha de la última entrada a un estado resolutivo (resuelto/recuperado)
  menos la creación; si el ticket se reabre y se resuelve de nuevo, se usa la más reciente
  (ver app/ticket_engine.py::apply_transition).
- "Cumplimiento" = % de tickets resueltos cuyo tiempo de resolución está dentro del objetivo
  configurado en `queues.targets[prioridad]` (minutos); tickets sin objetivo configurado para
  su prioridad no se cuentan ni a favor ni en contra.
- Esta versión no implementa pausas explícitas de SLA (no son un estado exigido por el
  enunciado): el tiempo de resolución se mide de extremo a extremo. Se documenta como
  limitación conocida en docs/RESOLUCION.md.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import func

from ..extensions import db
from ..models import Process, Queue, Ticket, TicketHistory

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@bp.get("/resumen")
def resumen():
    def counts(col):
        rows = db.session.execute(db.select(col, func.count()).group_by(col)).all()
        return {str(k): v for k, v in rows}

    return jsonify({
        "por_estado": counts(Ticket.state), "por_prioridad": counts(Ticket.priority),
        "por_cola": {q.code: n for q, n in db.session.execute(
            db.select(Queue, func.count(Ticket.id)).join(Ticket, Ticket.queue_id == Queue.id, isouter=True)
            .group_by(Queue.id)).all()},
        "por_proceso": {p.code: n for p, n in db.session.execute(
            db.select(Process, func.count(Ticket.id)).join(Ticket, Ticket.process_id == Process.id, isouter=True)
            .group_by(Process.id)).all()},
        "total": db.session.scalar(db.select(func.count()).select_from(Ticket)) or 0,
        "abiertos": db.session.scalar(db.select(func.count()).select_from(Ticket).where(Ticket.closed_at.is_(None))) or 0,
    })


@bp.get("/indicadores")
def indicadores():
    now = _now()
    open_tickets = db.session.scalars(db.select(Ticket).where(Ticket.closed_at.is_(None))).all()
    antiguedad_horas = [(now - t.created_at).total_seconds() / 3600 for t in open_tickets]

    first_action = {}
    rows = db.session.execute(
        db.select(TicketHistory.ticket_id, func.min(TicketHistory.created_at))
        .where(TicketHistory.action.in_(("tomado", "asignado"))).group_by(TicketHistory.ticket_id)
    ).all()
    for tid, ts in rows:
        first_action[tid] = ts
    created_by_id = dict(db.session.execute(db.select(Ticket.id, Ticket.created_at)).all())
    primera_atencion_horas = [(ts - created_by_id[tid]).total_seconds() / 3600
                              for tid, ts in first_action.items() if tid in created_by_id]

    resolved = db.session.scalars(db.select(Ticket).where(Ticket.resolved_at.is_not(None))).all()
    resolucion_horas = [(t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved]

    queues_by_id = {q.id: q for q in db.session.scalars(db.select(Queue)).all()}
    cumplidos = evaluados = 0
    for t in resolved:
        targets = (queues_by_id.get(t.queue_id).targets or {}) if queues_by_id.get(t.queue_id) else {}
        objetivo_min = targets.get(t.priority)
        if objetivo_min is None:
            continue
        evaluados += 1
        minutos = (t.resolved_at - t.created_at).total_seconds() / 60
        if minutos <= objetivo_min:
            cumplidos += 1

    def avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    return jsonify({
        "antiguedad_horas_promedio_abiertos": avg(antiguedad_horas),
        "primera_atencion_horas_promedio": avg(primera_atencion_horas),
        "resolucion_horas_promedio": avg(resolucion_horas),
        "cumplimiento_objetivo_pct": round(100 * cumplidos / evaluados, 1) if evaluados else None,
        "tickets_evaluados_cumplimiento": evaluados,
        "tiempo": "calendario",  # declarado: no es tiempo hábil
    })
