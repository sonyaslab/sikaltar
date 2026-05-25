"""
Model: Komoditas
Daftar komoditas produksi per subkategori PDRB.
Extended oleh MDM (Prompt 4): kode KBLI/KBKI/KLUI, audit, time-series aktif.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Komoditas(Base):
    __tablename__ = "komoditas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kode_internal: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True,
        comment="Kode unik internal, mis: 'TAN-PANGAN-PADI', 'PKB-TAHUNAN-SAWIT'",
    )
    nama: Mapped[str] = mapped_column(String(255), nullable=False)
    kategori_kode: Mapped[str] = mapped_column(
        String(10), ForeignKey("kategori_pdrb.kode", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    satuan_produksi: Mapped[str | None] = mapped_column(String(30), nullable=True)
    satuan_harga: Mapped[str | None] = mapped_column(String(30), nullable=True)
    faktor_konversi: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    wujud_produksi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ── MDM Extension: Kode Klasifikasi ──────────────────────────────────────
    klui_1990:        Mapped[str | None] = mapped_column(String(20),  nullable=True)
    kbli_2005:        Mapped[str | None] = mapped_column(String(20),  nullable=True)
    kbli_2009:        Mapped[str | None] = mapped_column(String(20),  nullable=True)
    kbki_2010:        Mapped[str | None] = mapped_column(String(20),  nullable=True)
    identitas:        Mapped[str | None] = mapped_column(String(50),  nullable=True)
    pdrb_kbli_kode:   Mapped[str | None] = mapped_column(String(10),  nullable=True)
    pdrb_kbli_uraian: Mapped[str | None] = mapped_column(String(255), nullable=True)
    klui_uraian:      Mapped[str | None] = mapped_column(String(255), nullable=True)
    catatan_varietas: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indeks_deflator:  Mapped[str | None] = mapped_column(String(100), nullable=True)
    indeks_dbl_defl:  Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── MDM Extension: Tampilan & Periode Berlaku ─────────────────────────────
    urutan_tampil:   Mapped[int | None] = mapped_column(Integer, nullable=True, default=999)
    berlaku_mulai:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    berlaku_sampai:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    digantikan_oleh: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("komoditas.id", ondelete="SET NULL"), nullable=True,
    )
    keterangan: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── MDM Extension: Konversi & Metode ─────────────────────────────────────
    produk_jadi:         Mapped[str | None] = mapped_column(String(100), nullable=True)
    punya_wip:           Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    punya_cbr:           Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    punya_output_ikutan: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    metode_harga:        Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── Relasi ────────────────────────────────────────────────────────────────
    kategori: Mapped = relationship(
        "KategoriPdrb",
        foreign_keys=[kategori_kode],
        primaryjoin="Komoditas.kategori_kode == KategoriPdrb.kode",
        lazy="joined", viewonly=True,
    )
    pengganti: Mapped["Komoditas | None"] = relationship(
        "Komoditas", foreign_keys=[digantikan_oleh],
        remote_side="Komoditas.id", lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Komoditas id={self.id} kode={self.kode_internal!r} nama={self.nama!r}>"
