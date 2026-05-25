"""
Model: Wilayah
Tabel referensi wilayah administratif Kalimantan Utara.
Provinsi (65) + 4 Kabupaten + 1 Kota.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Wilayah(Base):
    __tablename__ = "wilayah"

    __table_args__ = (
        UniqueConstraint('kode', name='uq_wilayah_kode'),  # ← WAJIB untuk self-referential FK!
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kode: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True,
                                       comment="Kode BPS wilayah, mis: '65', '6501', '6571'")
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False,
                                        comment="'provinsi' | 'kabupaten' | 'kota'")
    parent_kode: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("wilayah.kode", ondelete="RESTRICT"),
        nullable=True,
        unique=False,
        comment="Kode provinsi induk untuk kab/kota; NULL untuk provinsi",
    )

    # Self-referential: parent → children
    children: Mapped[list[Wilayah]] = relationship(
        "Wilayah",
        foreign_keys=[parent_kode],
        back_populates="parent",
        lazy="select",
    )
    parent: Mapped[Wilayah | None] = relationship(
        "Wilayah",
        foreign_keys=[parent_kode],
        back_populates="children",
        remote_side="Wilayah.kode",
    )

    def __repr__(self) -> str:
        return f"<Wilayah kode={self.kode!r} nama={self.nama!r} level={self.level!r}>"

    @property
    def is_provinsi(self) -> bool:
        return self.level == "provinsi"

    @property
    def is_kabkota(self) -> bool:
        return self.level in ("kabupaten", "kota")
