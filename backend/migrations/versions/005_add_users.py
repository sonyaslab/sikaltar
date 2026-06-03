"""
005_add_users.py — Buat tabel users + seed 2 akun default

Akun default:
  admin       / admin123    / role=admin    / wilayah_kode=NULL
  operator_test / operator123 / role=operator / wilayah_kode='6501'

Kedua akun di-set must_change_password=True.
Password di-hash dengan bcrypt (passlib).
"""
from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext

revision    = '005'
down_revision = '004'
branch_labels = None
depends_on    = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pre-hashed passwords (bcrypt)
_HASH_ADMIN    = pwd_context.hash("admin123")
_HASH_OPERATOR = pwd_context.hash("operator123")


def upgrade() -> None:
    # ─── 1. Buat ENUM type terlebih dahulu ────────────────────────────────────
    role_enum = sa.Enum("admin", "operator", name="role_enum")
    role_enum.create(op.get_bind(), checkfirst=True)

    # ─── 2. Buat tabel users ──────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",                   sa.Integer(),    primary_key=True, autoincrement=True),
        sa.Column("username",             sa.String(50),   nullable=False),
        sa.Column("email",                sa.String(100),  nullable=True),
        sa.Column("hashed_password",      sa.String(255),  nullable=False),
        sa.Column("role",                 sa.Enum("admin", "operator", name="role_enum"),
                  nullable=False, server_default="operator"),
        sa.Column("wilayah_kode",         sa.String(10),   nullable=True,
                  comment="NULL = akses semua (admin)"),
        sa.Column("nama",                 sa.String(100),  nullable=True),
        sa.Column("is_active",            sa.Boolean(),    nullable=False, server_default=sa.true()),
        sa.Column("must_change_password", sa.Boolean(),    nullable=False, server_default=sa.true()),
        sa.Column("created_at",           sa.DateTime(),   nullable=False, server_default=sa.func.now()),
        sa.Column("last_login",           sa.DateTime(),   nullable=True),
    )

    # ─── 3. Index & Constraint ────────────────────────────────────────────────
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email",    "users", ["email"],    unique=True)

    # ─── 4. Seed akun default ─────────────────────────────────────────────────
    op.execute(
        f"""
        INSERT INTO users (username, email, hashed_password, role, wilayah_kode, nama,
                           is_active, must_change_password)
        VALUES
          ('admin',          'admin@sikaltara.bps.go.id',
           '{_HASH_ADMIN}',    'admin',    NULL,   'Administrator SIKALTARA', true, true),
          ('operator_test',  'operator@sikaltara.bps.go.id',
           '{_HASH_OPERATOR}', 'operator', '6501', 'Operator Kab. Malinau',  true, true)
        ON CONFLICT (username) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_email",    "users")
    op.drop_index("ix_users_username", "users")
    op.drop_table("users")
    sa.Enum(name="role_enum").drop(op.get_bind(), checkfirst=True)
