"""
Models: InputProduksi, InputHarga, InputIndeksDeflator
Tabel input data dari petugas BPS.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InputProduksi(Base):
    """
    Data volume/kuantum produksi per komoditas per wilayah per periode.
    Sumber: Dinas Pertanian, Dinas Kehutanan, Dinas ESDM, dll.
    """
    __tablename__ = "input_produksi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    komoditas_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("komoditas.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    wilayah_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("wilayah.kode", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    triwulan: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="1|2|3|4; NULL = data tahunan langsung (bukan agregasi triwulanan)",
    )
    kuantum: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Volume produksi dalam satuan_produksi komoditas",
    )
    sumber_data: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Mis: 'Dinas Pertanian Kab. Nunukan', 'Statistik Pertanian BPS'",
    )
    status: Mapped[str] = mapped_column(
        String(20), default="sementara",
        comment="'sementara' (angka masih bisa berubah) | 'tetap' (sudah final/BRS)",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("komoditas_id", "wilayah_kode", "tahun", "triwulan",
                         name="uq_input_produksi"),
        CheckConstraint("tahun >= 2008", name="ck_produksi_tahun_min"),
        CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL",
                         name="ck_produksi_triwulan"),
    )

    komoditas: Mapped = relationship("Komoditas", foreign_keys=[komoditas_id], lazy="joined")
    wilayah: Mapped = relationship("Wilayah", foreign_keys=[wilayah_kode],
                                   primaryjoin="InputProduksi.wilayah_kode == Wilayah.kode",
                                   lazy="joined", viewonly=True)

    def __repr__(self) -> str:
        return (
            f"<InputProduksi komoditas={self.komoditas_id} wilayah={self.wilayah_kode!r} "
            f"tahun={self.tahun} tw={self.triwulan} kuantum={self.kuantum}>"
        )


class InputHarga(Base):
    """
    Data harga produsen per komoditas per wilayah per periode.
    harga_konstan_2010: tetap sama untuk semua tahun (harga tahun dasar 2010).
    """
    __tablename__ = "input_harga"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    komoditas_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("komoditas.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    wilayah_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("wilayah.kode", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    triwulan: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="NULL = harga tahunan/rata-rata",
    )
    harga_berlaku: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True,
        comment="Harga produsen tahun berjalan (Rp/satuan); diisi tiap tahun/triwulan",
    )
    harga_konstan_2010: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True,
        comment=(
            "Harga produsen tahun 2010 (Rp/satuan). "
            "Nilainya TETAP — simpan sekali di tahun=2010, triwulan=NULL. "
            "Hanya berubah jika ada revisi tahun dasar."
        ),
    )
    sumber_data: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("komoditas_id", "wilayah_kode", "tahun", "triwulan",
                         name="uq_input_harga"),
        CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL",
                         name="ck_harga_triwulan"),
    )

    komoditas: Mapped = relationship("Komoditas", foreign_keys=[komoditas_id], lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<InputHarga komoditas={self.komoditas_id} wilayah={self.wilayah_kode!r} "
            f"tahun={self.tahun} tw={self.triwulan} berlaku={self.harga_berlaku}>"
        )


class InputIndeksDeflator(Base):
    """
    Indeks deflator untuk kategori dengan metode Deflasi.
    Mis: Konstruksi (6), Pemerintahan (14), sebagian Perdagangan (7.2).
    Output_ADHK = Output_ADHB / (nilai_indeks / 100)
    Basis: tahun 2010 = 100.
    """
    __tablename__ = "input_indeks_deflator"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kategori_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("kategori_pdrb.kode", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    wilayah_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("wilayah.kode", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    triwulan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nilai_indeks: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False,
        comment="Indeks dengan basis 100 pada tahun 2010; mis: 125.40 berarti inflasi 25.4%",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("kategori_kode", "wilayah_kode", "tahun", "triwulan",
                         name="uq_input_indeks_deflator"),
        CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL",
                         name="ck_deflator_triwulan"),
    )

    def __repr__(self) -> str:
        return (
            f"<InputIndeksDeflator kategori={self.kategori_kode!r} wilayah={self.wilayah_kode!r} "
            f"tahun={self.tahun} tw={self.triwulan} indeks={self.nilai_indeks}>"
        )
