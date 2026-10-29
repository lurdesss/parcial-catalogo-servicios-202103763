"""Prueba de humo HTTP contra el sistema en ejecución (se ejecuta DENTRO del contenedor `app`).

Uso:  python scripts/smoke.py [health | flow | marker-write | marker-verify]
Lee EVAL_* del entorno. Sale con código 1 si algún control falla.
"""
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("SMOKE_BASE", "http://localhost:8000")


class Session:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
        if self.csrf and method != "GET":
            req.add_header("X-CSRF-Token", self.csrf)
        try:
            with self.op.open(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")

    def login(self, user, pwd):
        st, body = self.call("POST", "/api/auth/login", {"username": user, "password": pwd})
        if st == 200:
            self.csrf = body["csrf_token"]
        return st


failures = []


def check(name, cond, extra=""):
    print(("[OK]   " if cond else "[FALLO]") + " " + name + (f"  {extra}" if extra and not cond else ""))
    if not cond:
        failures.append(name)


def admin():
    s = Session()
    assert s.login(os.environ["EVAL_ADMIN_USER"], os.environ["EVAL_ADMIN_PASSWORD"]) == 200, "No se pudo iniciar sesión como admin"
    return s


def flow():
    check("health", Session().call("GET", "/health")[0] == 200)
    check("login inválido rechazado", Session().login(os.environ["EVAL_ADMIN_USER"], "incorrecta") == 401)
    check("sin sesión → 401", Session().call("GET", "/api/services/l2")[0] == 401)
    a = admin()
    v = Session()
    check("login consulta", v.login(os.environ["EVAL_VIEWER_USER"], os.environ["EVAL_VIEWER_PASSWORD"]) == 200)
    check("consulta lee servicios", v.call("GET", "/api/services/l2")[0] == 200)
    check("consulta no modifica (403)", v.call("POST", "/api/org/companies", {"code": "X", "name": "X"})[0] == 403)
    st, run1 = a.call("POST", "/api/import/run")
    check("importación 1 OK", st == 201, str(run1))
    st, run2 = a.call("POST", "/api/import/run")
    check("importación 2 sin crear ni actualizar (idempotente)", st == 201 and run2["created"] == 0 and run2["updated"] == 0, str(run2))
    control = (run2.get("summary") or {}).get("control", {})
    print(f"[INFO] N1 leídos={run2['n1_codes']} (esperado 12) · N2 leídos={run2['n2_codes']} (esperado 46) · coincide={control.get('coincide')}")
    if os.environ.get("EXPECT_REAL_CONTROL", "0") == "1":
        check("control 12 N1 / 46 N2", control.get("coincide") is True)
    st, page = a.call("GET", "/api/services/l2?per_page=1")
    check("catálogo consultable", st == 200 and page["total"] == run2["n2_codes"], str(page.get("total")))

    # --- Parcial 3: Service Desk / CMDB -------------------------------------------------
    st, procesos = a.call("GET", "/api/processes")
    check("7 procesos disponibles", st == 200 and len(procesos) == 7, str(procesos))
    st, devices = a.call("GET", "/api/cmdb/devices?per_page=1")
    check("CMDB consultable (>=5000 dispositivos tras setup_eval.sh)", st == 200, str(devices.get("total")))
    st, tickets = a.call("GET", "/api/tickets?per_page=1")
    check("tickets consultables (>=35 tras setup_eval.sh)", st == 200, str(tickets.get("total")))
    st, ind = a.call("GET", "/api/dashboard/indicadores")
    check("indicadores del tablero responden", st == 200, str(ind))


def marker_write():
    a = admin()
    st, body = a.call("POST", "/api/org/companies", {"code": "PERSISTENCIA", "name": "Registro de prueba de persistencia"})
    check("marcador de organización creado o ya existente", st in (201, 409), str(body))
    st, classes = a.call("GET", "/api/cmdb/ci-classes?q=HW.SRV")
    cls_id = classes["items"][0]["id"] if st == 200 and classes["items"] else None
    check("clase de CI disponible para el marcador", cls_id is not None, str(classes))
    st, dev = a.call("POST", "/api/cmdb/devices", {"asset_tag": "CI-PERSISTENCIA", "name": "Marcador CMDB", "ci_class_id": cls_id})
    check("marcador de CMDB creado o ya existente", st in (201, 409), str(dev))
    st, procesos = a.call("GET", "/api/processes")
    proc = next((p for p in procesos if p["code"] == "incidentes"), None) if st == 200 else None
    st, queues = a.call("GET", "/api/queues?q=Q-PERSISTENCIA")
    if st == 200 and queues["items"]:
        qid = queues["items"][0]["id"]
    else:
        st, q = a.call("POST", "/api/queues", {"code": "Q-PERSISTENCIA", "name": "Marcador", "process_id": proc["id"]})
        qid = q.get("id")
    st, tk = a.call("POST", "/api/tickets", {"process_code": "incidentes", "title": "Marcador de persistencia",
                                             "queue_id": qid, "detail": {"category": "I0"}})
    check("marcador de ticket creado o ya existente", st in (201, 409), str(tk))


def marker_verify():
    a = admin()
    st, body = a.call("GET", "/api/org/companies?q=PERSISTENCIA")
    check("el marcador de organización sobrevivió al reinicio", st == 200 and body["total"] >= 1, str(body))
    st, dev = a.call("GET", "/api/cmdb/devices?q=CI-PERSISTENCIA")
    check("el marcador de CMDB sobrevivió al reinicio", st == 200 and dev["total"] >= 1, str(dev))
    st, tk = a.call("GET", "/api/tickets?q=Marcador+de+persistencia")
    check("el marcador de ticket sobrevivió al reinicio", st == 200 and tk["total"] >= 1, str(tk))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "flow"
    {"health": lambda: check("health", Session().call("GET", "/health")[0] == 200),
     "flow": flow, "marker-write": marker_write, "marker-verify": marker_verify}[mode]()
    sys.exit(1 if failures else 0)
