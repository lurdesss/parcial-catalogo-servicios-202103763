"""Grafo 1 (CMDB): ciclos y recorrido de dependencias entre elementos de configuración (CI).

Hay dos grafos distintos y no deben confundirse:
  - jerarquía de clasificación (`ci_classes.parent_id`): un árbol; se valida con
    `would_create_cycle_classification`.
  - relaciones técnicas entre dispositivos (`device_relations`): `depende_de` y `alojado_en`
    son dirigidas y NO admiten ciclos; `conectado_a` es de conectividad y SÍ los admite.
"""
from .extensions import db
from .models import CiClass, DeviceRelation, ServiceCiLink

NO_CYCLE_RELATION_TYPES = {"depende_de", "alojado_en"}
CYCLE_ALLOWED_RELATION_TYPES = {"conectado_a"}
RELATION_TYPES = NO_CYCLE_RELATION_TYPES | CYCLE_ALLOWED_RELATION_TYPES


def would_create_cycle_classification(class_id, new_parent_id):
    """¿Reasignar class_id bajo new_parent_id crearía un ciclo en la jerarquía de clasificación?"""
    if class_id is None or new_parent_id is None:
        return False
    if class_id == new_parent_id:
        return True
    node = db.session.get(CiClass, new_parent_id)
    seen = set()
    while node is not None:
        if node.id == class_id:
            return True
        if node.id in seen:
            break  # ciclo preexistente ajeno a esta operación; no es nuestro problema aquí
        seen.add(node.id)
        node = node.parent
    return False


def would_create_cycle_relation(from_id, to_id, relation_type):
    """¿Agregar from_id --relation_type--> to_id crearía un ciclo? Solo depende_de/alojado_en
    lo impiden; conectado_a lo admite siempre (es un grafo de conectividad, no de dependencia)."""
    if relation_type not in NO_CYCLE_RELATION_TYPES:
        return False
    if from_id == to_id:
        return True
    rows = db.session.execute(
        db.select(DeviceRelation.from_device_id, DeviceRelation.to_device_id)
        .where(DeviceRelation.relation_type == relation_type)
    ).all()
    edges = {}
    for f, t in rows:
        edges.setdefault(f, []).append(t)
    seen, stack = set(), [to_id]
    while stack:
        n = stack.pop()
        if n == from_id:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(edges.get(n, []))
    return False


def impact_of(device_id, max_depth=10):
    """Dispositivos que podrían verse afectados si `device_id` falla: recorre en reversa
    depende_de/alojado_en (quién depende de / está alojado en el nodo actual) y en ambos
    sentidos conectado_a. BFS acotado por profundidad con guarda de visitados (evita ciclos
    en conectado_a). Devuelve [(device_id, profundidad, relation_type), ...]."""
    rows = db.session.execute(
        db.select(DeviceRelation.from_device_id, DeviceRelation.to_device_id, DeviceRelation.relation_type)
    ).all()
    reverse_edges, undirected_edges = {}, {}
    for f, t, rt in rows:
        if rt in NO_CYCLE_RELATION_TYPES:
            reverse_edges.setdefault(t, []).append((f, rt))
        elif rt in CYCLE_ALLOWED_RELATION_TYPES:
            undirected_edges.setdefault(f, []).append((t, rt))
            undirected_edges.setdefault(t, []).append((f, rt))
    seen = {device_id}
    frontier = [(device_id, 0)]
    out = []
    while frontier:
        node, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for neighbor, rt in reverse_edges.get(node, []) + undirected_edges.get(node, []):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            out.append((neighbor, depth + 1, rt))
            frontier.append((neighbor, depth + 1))
    return out


def affected_services(device_id, max_depth=10):
    """Servicios N2 potencialmente afectados por un CI (el propio CI + sus dependientes),
    vía service_ci_links. No afirma que la dependencia implique una interrupción efectiva."""
    ids = {device_id} | {d for d, _, _ in impact_of(device_id, max_depth=max_depth)}
    return db.session.execute(
        db.select(ServiceCiLink.service_l2_id, ServiceCiLink.device_id).where(ServiceCiLink.device_id.in_(ids))
    ).all()
