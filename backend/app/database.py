"""
SIMULTAN — Database Connection & Session Management
PostgreSQL + SQLAlchemy 2.x
"""
from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://simultan:simultan2024@localhost:5432/simultan_db",
)

# Engine dengan pool yang sesuai untuk lingkungan BPS (koneksi terbatas)
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,          # Cek koneksi sebelum digunakan
    pool_recycle=3600,           # Recycle koneksi tiap 1 jam
    echo=os.getenv("APP_ENV", "production") == "development",
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base class untuk semua model SQLAlchemy."""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency FastAPI untuk mendapatkan database session.
    Penggunaan:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Verifikasi koneksi database aktif."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[DATABASE] Koneksi gagal: {e}")
        return False
