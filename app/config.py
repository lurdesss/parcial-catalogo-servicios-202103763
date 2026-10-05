import os


def _url(value: str) -> str:
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = _url(os.environ.get("DATABASE_URL", "sqlite:///dev.db"))
    SESSION_COOKIE_NAME = "catalogo_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    SESSION_HOURS = int(os.environ.get("SESSION_HOURS", "8"))
    CATALOG_XLSX = os.environ.get("CATALOG_XLSX", "data/CatalogoServicios.xlsx")
    IMPORT_MAPPING = os.environ.get("IMPORT_MAPPING", "data/mapeo_importacion.json")
