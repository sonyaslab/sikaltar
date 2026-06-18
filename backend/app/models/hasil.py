# File: app/models/hasil.py
# TAMBAHKAN kolom ini di class PdrbRekap (sudah ada di kode Anda, tapi pastikan urutannya benar):

"""
Models: LkHasil & PdrbRekap
Cache hasil perhitungan LK PDRB.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey,
    Integer, Numeric, String, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LkHasil(Base):
    """
    Cache hasil perhitungan per komoditas.
    """
    __tablename__ = "lk_hasil"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    komoditas_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("komoditas.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    wilayah_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("wilayah.kode", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    triwulan: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="NULL = tahunan (agregasi 4 triwulan)"
    )

    # ── Komponen ADHB (Atas Dasar Harga Berlaku) ─────────────────────
    output_utama_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Kuantum × Harga Berlaku / 1.000.000 (Juta Rp)",
    )
    output_ikutan_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Output Utama × Rasio OS_ADHB",
    )
    wip_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Work In Progress = Output Utama × Rasio WIP_ADHB",
    )
    output_sekunder_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Dihitung di level subkategori (sum dari komoditas)",
    )
    adj_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Adjustment = Output Primer × Rasio ADJ_ADHB",
    )
    output_total_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="= Output Utama + Ikutan + WIP + Sekunder + ADJ",
    )
    rasio_ka_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True,
        comment="Rasio Konsumsi Antara yang digunakan",
    )
    ka_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Konsumsi Antara = Output Total × Rasio KA_ADHB",
    )
    ntb_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Nilai Tambah Bruto = Output Total − KA (Juta Rp)",
    )

    # ── Komponen ADHK (Atas Dasar Harga Konstan 2010) ────────────────
    output_utama_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_ikutan_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    wip_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_sekunder_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    adj_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_total_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    rasio_ka_adhk: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    ka_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ntb_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_valid: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="False = input sudah berubah, hasil perlu di-recalculate",
    )

    __table_args__ = (
        UniqueConstraint("komoditas_id", "wilayah_kode", "tahun", "triwulan",
                         name="uq_lk_hasil"),
        CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL",
                         name="ck_lk_hasil_triwulan"),
    )

    komoditas: Mapped = relationship("Komoditas", foreign_keys=[komoditas_id], lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<LkHasil komoditas={self.komoditas_id} wilayah={self.wilayah_kode!r} "
            f"tahun={self.tahun} tw={self.triwulan} ntb_adhb={self.ntb_adhb}>"
        )


class PdrbRekap(Base):
    """
    Rekap agregat PDRB per kategori — sumber data untuk tabel publikasi BPS.
    SESUAI FLOWCHART: NTB_final = NTB_hitung + adjustment_manual
    """
    __tablename__ = "pdrb_rekap"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kategori_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("kategori_pdrb.kode", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    wilayah_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("wilayah.kode", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)
    triwulan: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Output ADHB ──────────────────────────────────────────────────
    output_primer_adhb: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_sekunder_adhb: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_lainnya_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True, comment="WIP + ADJ"
    )
    output_total_adhb: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ka_adhb: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    
    # NTB Hitung (sebelum adjustment manual)
    ntb_hitung_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True, 
        comment="NTB sebelum adjustment manual (Output Total - KA + Output Sekunder)"
    )
    
    # Adjustment Manual (USER INPUT - bisa + atau -)
    adjustment_manual_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True, 
        comment="Adjustment manual user (Juta Rp) - bisa positif atau negatif"
    )
    
    # NTB Final (hasil akhir)
    ntb_final_adhb: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True, 
        comment="NTB Final = ntb_hitung_adhb + adjustment_manual_adhb"
    )

    # ── Output ADHK ──────────────────────────────────────────────────
    output_primer_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_sekunder_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_lainnya_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    output_total_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ka_adhk: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    
    # NTB Hitung (sebelum adjustment manual)
    ntb_hitung_adhk: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="NTB sebelum adjustment manual (Output Total - KA + Output Sekunder)"
    )
    
    # Adjustment Manual (USER INPUT - bisa + atau -)
    adjustment_manual_adhk: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="Adjustment manual user (Juta Rp) - bisa positif atau negatif"
    )
    
    # NTB Final (hasil akhir)
    ntb_final_adhk: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
        comment="NTB Final = ntb_hitung_adhk + adjustment_manual_adhk"
    )

    # ── Indikator Turunan ─────────────────────────────────────────────
    distribusi_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True,
        comment="% kontribusi terhadap total PDRB ADHB",
    )
    laju_pertumbuhan_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True,
        comment="Laju pertumbuhan NTB ADHK year-on-year (%)",
    )
    indeks_implisit: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True,
        comment="(NTB_Final_ADHB / NTB_Final_ADHK) × 100 — indeks deflasi implisit",
    )
    laju_implisit_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4), nullable=True,
        comment="Laju perubahan indeks implisit YoY (%)",
    )

    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("kategori_kode", "wilayah_kode", "tahun", "triwulan",
                         name="uq_pdrb_rekap"),
        CheckConstraint("triwulan IN (1,2,3,4) OR triwulan IS NULL",
                         name="ck_rekap_triwulan"),
    )

    kategori: Mapped = relationship("KategoriPdrb", foreign_keys=[kategori_kode],
                                    primaryjoin="PdrbRekap.kategori_kode == KategoriPdrb.kode",
                                    lazy="joined", viewonly=True)

    def __repr__(self) -> str:
        return (
            f"<PdrbRekap kategori={self.kategori_kode!r} wilayah={self.wilayah_kode!r} "
            f"tahun={self.tahun} tw={self.triwulan} ntb_final_adhb={self.ntb_final_adhb}>"
        )