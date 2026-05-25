"""
Migration 001: Create all tables
Urutan: dependency-safe (parent sebelum child)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. wilayah
    op.create_table(
        "wilayah",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kode", sa.String(10), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("parent_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="RESTRICT"), nullable=True),
    )
    op.create_index("ix_wilayah_kode", "wilayah", ["kode"], unique=True)

    # 2. kategori_pdrb
    op.create_table(
        "kategori_pdrb",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kode", sa.String(10), nullable=False),
        sa.Column("nama", sa.String(255), nullable=False),
        sa.Column("parent_kode", sa.String(10), sa.ForeignKey("kategori_pdrb.kode", ondelete="RESTRICT"), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("metode_adhb", sa.String(50), nullable=True),
        sa.Column("metode_adhk", sa.String(50), nullable=True),
        sa.Column("urutan", sa.Integer(), nullable=False),
    )
    op.create_index("ix_kategori_pdrb_kode", "kategori_pdrb", ["kode"], unique=True)

    # 3. komoditas
    op.create_table(
        "komoditas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kode_internal", sa.String(30), nullable=False),
        sa.Column("nama", sa.String(255), nullable=False),
        sa.Column("kategori_kode", sa.String(10), sa.ForeignKey("kategori_pdrb.kode", ondelete="RESTRICT"), nullable=False),
        sa.Column("satuan_produksi", sa.String(30), nullable=True),
        sa.Column("satuan_harga", sa.String(30), nullable=True),
        sa.Column("faktor_konversi", sa.Numeric(10, 6), nullable=True),
        sa.Column("wujud_produksi", sa.String(100), nullable=True),
        sa.Column("aktif", sa.Boolean(), default=True, nullable=False),
    )
    op.create_index("ix_komoditas_kode_internal", "komoditas", ["kode_internal"], unique=True)
    op.create_index("ix_komoditas_kategori_kode", "komoditas", ["kategori_kode"])

    # 4. rasio_referensi
    op.create_table(
        "rasio_referensi",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("komoditas_id", sa.Integer(), sa.ForeignKey("komoditas.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kategori_kode", sa.String(10), sa.ForeignKey("kategori_pdrb.kode", ondelete="CASCADE"), nullable=True),
        sa.Column("jenis_rasio", sa.String(20), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("nilai", sa.Numeric(10, 6), nullable=False),
        sa.Column("berlaku_untuk", sa.String(10), nullable=False),
        sa.UniqueConstraint("komoditas_id", "kategori_kode", "jenis_rasio", "tahun", "berlaku_untuk",
                            name="uq_rasio_referensi"),
    )

    # 5. rasio_override
    op.create_table(
        "rasio_override",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("komoditas_id", sa.Integer(), sa.ForeignKey("komoditas.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kategori_kode", sa.String(10), sa.ForeignKey("kategori_pdrb.kode", ondelete="CASCADE"), nullable=True),
        sa.Column("jenis_rasio", sa.String(20), nullable=False),
        sa.Column("wilayah_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="CASCADE"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("nilai", sa.Numeric(10, 6), nullable=False),
        sa.Column("berlaku_untuk", sa.String(10), nullable=False),
        sa.Column("keterangan", sa.Text(), nullable=True),
        sa.UniqueConstraint("komoditas_id", "kategori_kode", "jenis_rasio", "wilayah_kode", "tahun", "berlaku_untuk",
                            name="uq_rasio_override"),
    )

    # 6. input_produksi
    op.create_table(
        "input_produksi",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("komoditas_id", sa.Integer(), sa.ForeignKey("komoditas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("wilayah_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="RESTRICT"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("triwulan", sa.Integer(), nullable=True),
        sa.Column("kuantum", sa.Numeric(20, 6), nullable=True),
        sa.Column("sumber_data", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), default="sementara"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("komoditas_id", "wilayah_kode", "tahun", "triwulan", name="uq_input_produksi"),
        sa.CheckConstraint("tahun >= 2008", name="ck_produksi_tahun_min"),
        sa.CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL", name="ck_produksi_triwulan"),
    )

    # 7. input_harga
    op.create_table(
        "input_harga",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("komoditas_id", sa.Integer(), sa.ForeignKey("komoditas.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("wilayah_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="RESTRICT"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("triwulan", sa.Integer(), nullable=True),
        sa.Column("harga_berlaku", sa.Numeric(20, 2), nullable=True),
        sa.Column("harga_konstan_2010", sa.Numeric(20, 2), nullable=True),
        sa.Column("sumber_data", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("komoditas_id", "wilayah_kode", "tahun", "triwulan", name="uq_input_harga"),
        sa.CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL", name="ck_harga_triwulan"),
    )

    # 8. input_indeks_deflator
    op.create_table(
        "input_indeks_deflator",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kategori_kode", sa.String(10), sa.ForeignKey("kategori_pdrb.kode", ondelete="RESTRICT"), nullable=False),
        sa.Column("wilayah_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="RESTRICT"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("triwulan", sa.Integer(), nullable=True),
        sa.Column("nilai_indeks", sa.Numeric(10, 4), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("kategori_kode", "wilayah_kode", "tahun", "triwulan", name="uq_input_indeks_deflator"),
        sa.CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL", name="ck_deflator_triwulan"),
    )

    # 9. lk_hasil
    op.create_table(
        "lk_hasil",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("komoditas_id", sa.Integer(), sa.ForeignKey("komoditas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wilayah_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="CASCADE"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("triwulan", sa.Integer(), nullable=True),
        # ADHB
        sa.Column("output_utama_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_ikutan_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("wip_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_sekunder_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("adj_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_total_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("rasio_ka_adhb", sa.Numeric(10, 6), nullable=True),
        sa.Column("ka_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("ntb_adhb", sa.Numeric(20, 6), nullable=True),
        # ADHK
        sa.Column("output_utama_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_ikutan_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("wip_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_sekunder_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("adj_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_total_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("rasio_ka_adhk", sa.Numeric(10, 6), nullable=True),
        sa.Column("ka_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("ntb_adhk", sa.Numeric(20, 6), nullable=True),
        # Metadata
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("is_valid", sa.Boolean(), default=True),
        sa.UniqueConstraint("komoditas_id", "wilayah_kode", "tahun", "triwulan", name="uq_lk_hasil"),
        sa.CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL", name="ck_lk_hasil_triwulan"),
    )

    # 10. pdrb_rekap
    op.create_table(
        "pdrb_rekap",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kategori_kode", sa.String(10), sa.ForeignKey("kategori_pdrb.kode", ondelete="CASCADE"), nullable=False),
        sa.Column("wilayah_kode", sa.String(10), sa.ForeignKey("wilayah.kode", ondelete="CASCADE"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("triwulan", sa.Integer(), nullable=True),
        # ADHB
        sa.Column("output_primer_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_sekunder_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_lainnya_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_total_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("ka_adhb", sa.Numeric(20, 6), nullable=True),
        sa.Column("ntb_adhb", sa.Numeric(20, 6), nullable=True),
        # ADHK
        sa.Column("output_primer_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_sekunder_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_lainnya_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("output_total_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("ka_adhk", sa.Numeric(20, 6), nullable=True),
        sa.Column("ntb_adhk", sa.Numeric(20, 6), nullable=True),
        # Indikator turunan
        sa.Column("distribusi_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("laju_pertumbuhan_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("indeks_implisit", sa.Numeric(10, 4), nullable=True),
        sa.Column("laju_implisit_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("calculated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("kategori_kode", "wilayah_kode", "tahun", "triwulan", name="uq_pdrb_rekap"),
        sa.CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL", name="ck_rekap_triwulan"),
    )


def downgrade() -> None:
    op.drop_table("pdrb_rekap")
    op.drop_table("lk_hasil")
    op.drop_table("input_indeks_deflator")
    op.drop_table("input_harga")
    op.drop_table("input_produksi")
    op.drop_table("rasio_override")
    op.drop_table("rasio_referensi")
    op.drop_table("komoditas")
    op.drop_table("kategori_pdrb")
    op.drop_table("wilayah")
