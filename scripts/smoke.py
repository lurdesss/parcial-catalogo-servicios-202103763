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


def marker_write():
    a = admin()
    st, body = a.call("POST", "/api/org/companies", {"code": "PERSISTENCIA", "name": "Registro de prueba de persistencia"})
    check("marcador creado o ya existente", st in (201, 409), str(body))


def marker_verify():
    a = admin()
    st, body = a.call("GET", "/api/org/companies?q=PERSISTENCIA")
    check("el marcador sobrevivió al reinicio", st == 200 and body["total"] >= 1, str(body))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "flow"
    {"health": lambda: check("health", Session().call("GET", "/health")[0] == 200),
     "flow": flow, "marker-write": marker_write, "marker-verify": marker_verify}[mode]()
    sys.exit(1 if failures else 0)
