from flask import jsonify, request
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None, extra=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or {}
        self.extra = extra or {}


def _payload(code, message, fields=None, extra=None):
    body = {"error": {"code": code, "message": message, "fields": fields or {}}}
    body["error"].update(extra or {})
    return jsonify(body)


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e):
        return _payload(e.code, e.message, e.fields, e.extra), e.status

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if request.path.startswith("/api/"):
            return _payload(e.name.lower().replace(" ", "_"), e.description), e.code
        return e

    @app.errorhandler(Exception)
    def _unexpected(e):
        app.logger.exception("Error no controlado")
        if request.path.startswith("/api/"):
            return _payload("internal_error", "Error interno del servidor."), 500
        raise e
