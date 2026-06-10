# SIKALTARA backend — image produksi
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Dependensi sistem minimal (psycopg2-binary tidak butuh compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Install dependency Python lebih dulu (cache layer)
COPY backend/pyproject.toml /srv/backend/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "fastapi>=0.111" "uvicorn[standard]>=0.29" "gunicorn>=22" \
        "sqlalchemy>=2.0.30" "alembic>=1.13" "psycopg2-binary>=2.9.9" \
        "celery>=5.3" "redis>=5.0" "pydantic>=2.7" "pydantic-settings>=2.2" \
        "python-jose[cryptography]>=3.3" "passlib[bcrypt]>=1.7.4" \
        "python-multipart>=0.0.9" "python-dotenv>=1.0" "structlog>=24.1"

# Salin source
COPY backend /srv/backend
COPY frontend /srv/frontend
WORKDIR /srv/backend

EXPOSE 8000

# Entrypoint: jalankan migrasi lalu start server (4 worker uvicorn via gunicorn)
CMD ["bash", "-lc", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 --timeout 120"]
