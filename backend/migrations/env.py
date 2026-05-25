"""Alembic migrations environment configuration."""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv()

# Alembic Config object — akses ke nilai alembic.ini
config = context.config

# Override URL dari environment variable
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Setup Python logging dari alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import semua model agar Alembic bisa detect schema
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.database import Base
from app.models import (  # noqa: F401 — import untuk metadata detection
    Wilayah, KategoriPdrb, Komoditas,
    RasioReferensi, RasioOverride,
    InputProduksi, InputHarga, InputIndeksDeflator,
    LkHasil, PdrbRekap,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Jalankan migrasi tanpa koneksi aktif (generate SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Jalankan migrasi dengan koneksi aktif ke database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
