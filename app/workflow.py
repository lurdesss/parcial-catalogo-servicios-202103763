"""Grafo 2 (Service Desk): estados y transiciones de cada uno de los 7 procesos
(`process_states`/`process_transitions`, sembrados en la migración 0002 — ver
docs/PROCESOS.md). El motor de tickets usa `find_transition` para aceptar o rechazar un
salto de estado: nunca se permite un salto que no sea una arista explícita del grafo."""
from .extensions import db
from .models import ProcessState, ProcessTransition


def states_of(process_id):
    return db.session.scalars(db.select(ProcessState).where(ProcessState.process_id == process_id)).all()


def transitions_of(process_id):
    return db.session.scalars(db.select(ProcessTransition).where(ProcessTransition.process_id == process_id)).all()


def find_transition(process_id, from_code, action):
    return db.session.scalar(db.select(ProcessTransition).where(
        ProcessTransition.process_id == process_id,
        ProcessTransition.from_code == from_code,
        ProcessTransition.action == action,
    ))


def initial_state(process_id):
    return db.session.scalar(db.select(ProcessState).where(
        ProcessState.process_id == process_id, ProcessState.is_initial.is_(True)))


def is_final(process_id, code):
    st = db.session.scalar(db.select(ProcessState).where(
        ProcessState.process_id == process_id, ProcessState.code == code))
    return bool(st and st.is_final)


def graph_dict(process):
    return {
        "process": {"code": process.code, "name": process.name, "ticket_type": process.ticket_type},
        "states": [{"code": s.code, "name": s.name, "is_initial": s.is_initial, "is_final": s.is_final}
                   for s in states_of(process.id)],
        "transitions": [{"from": t.from_code, "to": t.to_code, "action": t.action, "required_perm": t.required_perm}
                         for t in transitions_of(process.id)],
    }
