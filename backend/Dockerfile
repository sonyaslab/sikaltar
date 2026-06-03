# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Install ke /build/venv supaya bisa di-copy ke stage final
RUN pip install --no-cache-dir --prefix=/install -e . 2>/dev/null || \
    pip install --no-cache-dir --prefix=/install \
    "fastapi>=0.111.0" "uvicorn[standard]>=0.29.0" \
    "sqlalchemy>=2.0.30" "alembic>=1.13.1" "psycopg2-binary>=2.9.9" \
    "pydantic>=2.7.0" "pydantic-settings>=2.2.0" \
    "python-jose[cryptography]>=3.3.0" "passlib[bcrypt]>=1.7.4" \
    "python-multipart>=0.0.9" "python-dotenv>=1.0.1" "structlog>=24.1.0"

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Non-root user untuk keamanan
RUN useradd -m -u 1000 sikaltara && chown -R sikaltara:sikaltara /app
USER sikaltara

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Jalankan migrasi dulu, baru server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --log-level info"]
