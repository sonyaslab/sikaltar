"""
create_admin.py  —  Buat / reset akun login TANPA seed data lain.
Letakkan di backend/ lalu jalankan di server:

    docker compose -f docker-compose.prod.yml exec api python create_admin.py \
        --username admin --password "PasswordBaruKuat" --role admin

    # operator wilayah tertentu:
    docker compose ... exec api python create_admin.py \
        --username operator_malinau --password "xxx" --role operator --wilayah 6501

Tanpa argumen → buat admin default (admin / ganti-saya) HANYA jika belum ada.
Idempoten: jika username sudah ada, password-nya di-update.
"""
from __future__ import annotations

import argparse
import sys

from passlib.context import CryptContext
from app.database import SessionLocal
from app.models.user import User, RoleEnum

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upsert_user(username, password, role, wilayah, nama, email):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        hashed = pwd.hash(password)
        if u:
            u.hashed_password = hashed
            u.role = RoleEnum(role)
            u.wilayah_kode = wilayah
            u.is_active = True
            u.must_change_password = True
            aksi = "DIPERBARUI"
        else:
            u = User(
                username=username, email=email, hashed_password=hashed,
                role=RoleEnum(role), wilayah_kode=wilayah, nama=nama,
                is_active=True, must_change_password=True,
            )
            db.add(u)
            aksi = "DIBUAT"
        db.commit()
        print(f"✓ User {username!r} ({role}, wilayah={wilayah or 'SEMUA'}) {aksi}.")
        print("  ⚠ Akun ditandai must_change_password=True — ganti password saat login pertama.")
    finally:
        db.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--username", default="admin")
    p.add_argument("--password", default="ganti-saya")
    p.add_argument("--role", default="admin", choices=["admin", "operator"])
    p.add_argument("--wilayah", default=None, help="Kode wilayah untuk operator (mis. 6501). Admin = kosong.")
    p.add_argument("--nama", default="Administrator SIKALTARA")
    p.add_argument("--email", default="admin@sikaltara.local")
    a = p.parse_args()

    wilayah = a.wilayah if a.role == "operator" else None
    upsert_user(a.username, a.password, a.role, wilayah, a.nama, a.email)


if __name__ == "__main__":
    sys.exit(main())
