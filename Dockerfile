# syntax=docker/dockerfile:1
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
RUN useradd --system --uid 10001 --home /srv appuser
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY alembic.ini ./
COPY app app
COPY migrations migrations
COPY data data
COPY scripts scripts
RUN chmod +x scripts/*.sh && chown -R appuser /srv
USER appuser
EXPOSE 8000
ENTRYPOINT ["/srv/scripts/entrypoint.sh"]
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "2", "--access-logfile", "-", "app:create_app()"]

# Imagen de pruebas: añade pytest/ruff y el directorio tests (no se usa en producción)
FROM runtime AS test
USER root
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY pytest.ini ruff.toml ./
COPY tests tests
RUN chown -R appuser /srv
USER appuser
CMD ["sh", "scripts/check.sh"]
