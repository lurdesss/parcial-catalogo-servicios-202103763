"""Generador reproducible de dispositivos sintéticos de la CMDB (enunciado §8).

- Determinista: con la misma semilla produce la misma distribución y los mismos
  `asset_tag` (`CI-{seed:04d}-{i:05d}`); repetir la carga con la misma semilla ACTUALIZA
  los registros existentes en vez de duplicarlos (upsert por asset_tag).
- Distribuye los dispositivos entre las clases hoja activas de `ci_classes` (ver migración
  0002) con pesos fijos que aproximan una organización real (más estaciones/aplicaciones que
  licencias o instalaciones).
- Nunca asigna IP a clases que no la requieren (`ci_classes.requires_ip`), y ni siquiera a
  todas las que sí la requieren (nunca es obligatoria, ver docs/MODELO.md).
- No usa IA ni dependencias externas: solo `random.Random(seed)` sobre listas curadas.
"""
import random

from .extensions import db
from .models import CiClass, Device, DeviceRelation, Location, ServiceCiLink, ServiceL2, User

# code -> (peso relativo, prefijo de nombre)
WEIGHTS = {
    "HW.WKS": (30, "WKS"), "HW.SRV": (10, "SRV"), "HW.NET": (8, "NET"), "HW.STO": (5, "STO"),
    "HW.PER": (12, "PER"), "SW.OS": (5, "OS"), "SW.APP": (20, "APP"), "SW.DB": (4, "DB"),
    "SW.LIC": (4, "LIC"), "DOC.MAN": (1, "MAN"), "DOC.PROC": (1, "PROC"), "FAC.DC": (0.1, "DC"),
    "FAC.SRV": (0.1, "SALA"),
}
OS_CHOICES = ["Windows Server 2022", "Windows 11", "Ubuntu 22.04", "RHEL 9", "macOS 15"]


def _leaf_classes():
    all_classes = db.session.scalars(db.select(CiClass).where(CiClass.is_active.is_(True))).all()
    parents = {c.parent_id for c in all_classes if c.parent_id is not None}
    return [c for c in all_classes if c.id not in parents]


def _attributes(rng, code):
    if code == "HW.SRV":
        return {"cpu_cores": rng.choice([8, 16, 32, 64]), "ram_gb": rng.choice([32, 64, 128, 256]),
                "os": rng.choice(OS_CHOICES)}
    if code == "HW.WKS":
        return {"cpu_cores": rng.choice([4, 6, 8]), "ram_gb": rng.choice([8, 16, 32]), "os": rng.choice(OS_CHOICES)}
    if code == "HW.NET":
        return {"puertos": rng.choice([8, 24, 48]), "firmware": f"{rng.randint(1, 9)}.{rng.randint(0, 9)}"}
    if code == "HW.STO":
        return {"capacidad_tb": rng.choice([4, 8, 16, 32, 64])}
    if code in ("SW.APP", "SW.OS", "SW.DB"):
        return {"version": f"{rng.randint(1, 20)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}"}
    if code == "SW.LIC":
        return {"asientos": rng.choice([5, 10, 25, 50, 100])}
    return {}


def generate(seed, count=5000, batch_size=500):
    rng = random.Random(seed)
    leaves = {c.code: c for c in _leaf_classes()}
    weighted = [(code, w) for code, (w, _) in WEIGHTS.items() if code in leaves]
    if not weighted:
        raise RuntimeError("No hay clases hoja activas de CMDB; ejecute las migraciones primero.")
    codes, weights = zip(*weighted)
    locations = db.session.scalars(db.select(Location).where(Location.is_active.is_(True))).all()
    users = db.session.scalars(db.select(User).where(User.is_active.is_(True))).all()
    services = db.session.scalars(db.select(ServiceL2).where(ServiceL2.is_active.is_(True))).all()
    if not locations:
        raise RuntimeError("No hay ubicaciones activas; ejecute las migraciones primero.")

    existing = {d.asset_tag: d for d in db.session.scalars(
        db.select(Device).where(Device.asset_tag.like(f"CI-{seed:04d}-%"))).all()}

    created = updated = 0
    per_class_count = {}
    by_class_devices = {}
    for i in range(1, count + 1):
        code = rng.choices(codes, weights=weights, k=1)[0]
        cls = leaves[code]
        prefix = WEIGHTS[code][1]
        asset_tag = f"CI-{seed:04d}-{i:05d}"
        name = f"{prefix}-{i:05d}"
        location = rng.choice(locations)
        owner = rng.choice(users) if users and rng.random() < 0.6 else None
        status = rng.choices(["activo", "activo", "activo", "inactivo", "retirado"], k=1)[0]
        ip = None
        if cls.requires_ip and rng.random() < 0.9:
            ip = f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
        attrs = _attributes(rng, code)

        dev = existing.get(asset_tag)
        if dev:
            dev.name, dev.ci_class_id, dev.status = name, cls.id, status
            dev.location_id, dev.owner_user_id = location.id, (owner.id if owner else None)
            dev.ip_address, dev.attributes, dev.is_active = ip, attrs, True
            updated += 1
        else:
            dev = Device(asset_tag=asset_tag, name=name, ci_class_id=cls.id, status=status,
                         location_id=location.id, owner_user_id=owner.id if owner else None,
                         ip_address=ip, attributes=attrs, is_active=True, generator_seed=seed)
            db.session.add(dev)
            created += 1
        per_class_count[code] = per_class_count.get(code, 0) + 1
        by_class_devices.setdefault(code, []).append(dev)
        if i % batch_size == 0:
            db.session.flush()

    db.session.flush()
    relations = _link_relations(rng, by_class_devices)
    links = _link_services(rng, by_class_devices, services)
    db.session.commit()

    by_root = {}
    for code, n in per_class_count.items():
        root = code.split(".")[0]
        by_root[root] = by_root.get(root, 0) + n
    return {
        "seed": seed, "created": created, "updated": updated, "total": created + updated,
        "por_clase": per_class_count, "por_nivel_raiz": by_root,
        "relaciones_creadas": relations, "vinculos_servicio_creados": links,
    }


def _link_relations(rng, by_class_devices):
    apps = by_class_devices.get("SW.APP", [])
    servers = by_class_devices.get("HW.SRV", [])
    storages = by_class_devices.get("HW.STO", [])
    nets = by_class_devices.get("HW.NET", [])
    created = 0
    existing_pairs = {(r.from_device_id, r.to_device_id, r.relation_type)
                      for r in db.session.scalars(db.select(DeviceRelation)).all()}

    def add(frm, to, rtype):
        nonlocal created
        if frm.id == to.id or (frm.id, to.id, rtype) in existing_pairs:
            return
        db.session.add(DeviceRelation(from_device_id=frm.id, to_device_id=to.id, relation_type=rtype))
        existing_pairs.add((frm.id, to.id, rtype))
        created += 1

    if servers:
        for app in apps:
            if rng.random() < 0.2:
                add(app, rng.choice(servers), "alojado_en")
        for srv in servers:
            if storages and rng.random() < 0.15:
                add(srv, rng.choice(storages), "depende_de")
            if nets and rng.random() < 0.15:
                add(srv, rng.choice(nets), "depende_de")
    if len(nets) > 1:
        for net in nets:
            if rng.random() < 0.1:
                add(net, rng.choice([n for n in nets if n.id != net.id] or [net]), "conectado_a")
    return created


def _link_services(rng, by_class_devices, services):
    if not services:
        return 0
    created = 0
    pool = [d for devs in by_class_devices.values() for d in devs]
    existing = {(link.service_l2_id, link.device_id) for link in db.session.scalars(db.select(ServiceCiLink)).all()}
    for dev in pool:
        if rng.random() < 0.05:
            svc = rng.choice(services)
            if (svc.id, dev.id) not in existing:
                db.session.add(ServiceCiLink(service_l2_id=svc.id, device_id=dev.id))
                existing.add((svc.id, dev.id))
                created += 1
    return created
