from decimal import Decimal, InvalidOperation

from .errors import ApiError


class Validator:
    """Acumula errores por campo y los lanza juntos con check()."""

    def __init__(self, data):
        if not isinstance(data, dict):
            raise ApiError(400, "invalid_body", "El cuerpo de la petición debe ser un objeto JSON.")
        self.data = data
        self.errors = {}

    def _blank(self, v):
        return v is None or (isinstance(v, str) and not v.strip())

    def text(self, field, label, required=True, max_len=200, lower=False):
        v = self.data.get(field)
        if self._blank(v):
            if required:
                self.errors[field] = f"{label} es obligatorio."
            return None
        if not isinstance(v, str):
            self.errors[field] = f"{label} debe ser texto."
            return None
        v = v.strip()
        if len(v) > max_len:
            self.errors[field] = f"{label} no puede exceder {max_len} caracteres."
            return None
        return v.lower() if lower else v

    def integer(self, field, label, required=True):
        v = self.data.get(field)
        if self._blank(v):
            if required:
                self.errors[field] = f"{label} es obligatorio."
            return None
        if isinstance(v, bool):
            self.errors[field] = f"{label} debe ser un entero."
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            self.errors[field] = f"{label} debe ser un entero."
            return None

    def decimal(self, field, label):
        v = self.data.get(field)
        if self._blank(v):
            return None  # ausente NO se convierte en cero
        if isinstance(v, bool):
            self.errors[field] = f"{label} debe ser numérico."
            return None
        try:
            d = Decimal(str(v).strip())
        except InvalidOperation:
            self.errors[field] = f"{label} debe ser numérico."
            return None
        if not d.is_finite():
            self.errors[field] = f"{label} debe ser un número finito."
            return None
        return d

    def boolean(self, field, label, default=None):
        v = self.data.get(field, default)
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        self.errors[field] = f"{label} debe ser verdadero o falso."
        return default

    def choice(self, field, label, options, required=True):
        v = self.text(field, label, required=required, max_len=50)
        if v is not None and v not in options:
            self.errors[field] = f"{label} debe ser uno de: {', '.join(options)}."
            return None
        return v

    def check(self):
        if self.errors:
            raise ApiError(400, "validation", "Hay datos inválidos; revise los campos indicados.", fields=self.errors)


def like_escape(term):
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
