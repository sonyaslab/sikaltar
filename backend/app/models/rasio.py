"""
Model: RasioReferensi & RasioOverride
Tabel rasio BPS berdasarkan SUT 2019.
Jenis rasio: OS (Output Sekunder/Ikutan), WIP, CBR, KA (Konsumsi Antara), ADJ (Adjustment).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RasioReferensi(Base):
    """
    Rasio referensi nasional dari SUT 2019 BPS.
    Berlaku sebagai default jika tidak ada override per wilayah.
    """
    __tablename__ = "rasio_referensi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    komoditas_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("komoditas.id", ondelete="CASCADE"),
        nullable=True, index=True,
        comment="NULL jika rasio berlaku untuk seluruh kategori (komoditas_id=NULL + kategori_kode diisi)",
    )
    kategori_kode: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("kategori_pdrb.kode", ondelete="CASCADE"),
        nullable=True, index=True,
        comment="Kode kategori/subkategori; diisi jika rasio berlaku untuk seluruh subkategori",
    )
    jenis_rasio: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="'OS' | 'WIP' | 'CBR' | 'KA' | 'ADJ'",
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    nilai: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False,
        comment="Nilai desimal, mis: 0.1515 untuk 15.15%",
    )
    berlaku_untuk: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="'ADHB' | 'ADHK' | 'KEDUANYA'",
    )

    __table_args__ = (
        UniqueConstraint(
            "komoditas_id", "kategori_kode", "jenis_rasio", "tahun", "berlaku_untuk",
            name="uq_rasio_referensi",
        ),
    )

    komoditas: Mapped = relationship("Komoditas", foreign_keys=[komoditas_id], lazy="joined")

    def __repr__(self) -> str:
        scope = f"komoditas={self.komoditas_id}" if self.komoditas_id else f"kategori={self.kategori_kode}"
        return (
            f"<RasioReferensi {scope} jenis={self.jenis_rasio!r} "
            f"tahun={self.tahun} nilai={self.nilai} berlaku={self.berlaku_untuk!r}>"
        )


class RasioOverride(Base):
    """
    Override rasio per wilayah (kabupaten/kota).
    Prioritas lebih tinggi dari RasioReferensi.
    Digunakan untuk penyesuaian lokal yang berbeda dari nasional.
    """
    __tablename__ = "rasio_override"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    komoditas_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("komoditas.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    kategori_kode: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("kategori_pdrb.kode", ondelete="CASCADE"),
        nullable=True, index=True,
    )
    jenis_rasio: Mapped[str] = mapped_column(String(20), nullable=False)
    wilayah_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("wilayah.kode", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    nilai: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    berlaku_untuk: Mapped[str] = mapped_column(String(10), nullable=False)
    keterangan: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Alasan override, mis: 'Kondisi lokal Kab. Malinau berbeda dari nasional'",
    )

    __table_args__ = (
        UniqueConstraint(
            "komoditas_id", "kategori_kode", "jenis_rasio", "wilayah_kode", "tahun", "berlaku_untuk",
            name="uq_rasio_override",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RasioOverride wilayah={self.wilayah_kode!r} jenis={self.jenis_rasio!r} "
            f"tahun={self.tahun} nilai={self.nilai}>"
        )
