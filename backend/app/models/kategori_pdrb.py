"""
Model: KategoriPdrb
17 Kategori PDRB (A–R,S,T,U) + subkategori sesuai BPS SNA 2008.
Hierarki: level 1 = kategori, level 2 = subkategori, level 3 = sub-subkategori, level 4 = komoditas.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KategoriPdrb(Base):
    __tablename__ = "kategori_pdrb"
    __table_args__ = (
        UniqueConstraint('kode', name='uq_kategori_pdrb_kode'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kode: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True,
        comment="Kode hierarkis, mis: '1', '1.1', '1.1.a'"
    )
    nama: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_kode: Mapped[str | None] = mapped_column(
        String(10),
        ForeignKey("kategori_pdrb.kode", ondelete="RESTRICT"),
        nullable=True,
        comment="NULL untuk kategori utama (1-17)",
    )
    level: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="1=kategori utama, 2=subkategori, 3=sub-subkategori, 4=komoditas",
    )
    metode_adhb: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="'Produksi'|'Deflasi'|'Revaluasi'|'Langsung'|'CommodityFlow'|'DoubleDflasi'",
    )
    metode_adhk: Mapped[str | None] = mapped_column(String(50), nullable=True)
    urutan: Mapped[int] = mapped_column(Integer, nullable=False, comment="Urutan tampilan LK")

    # Relasi
    children: Mapped[list[KategoriPdrb]] = relationship(
        "KategoriPdrb",
        foreign_keys=[parent_kode],
        back_populates="parent",
        order_by="KategoriPdrb.urutan",
        lazy="select",
    )
    parent: Mapped[KategoriPdrb | None] = relationship(
        "KategoriPdrb",
        foreign_keys=[parent_kode],
        back_populates="children",
        remote_side="KategoriPdrb.kode",
    )
    komoditas_list: Mapped[list] = relationship(
        "Komoditas",
        foreign_keys="Komoditas.kategori_kode",
        primaryjoin="KategoriPdrb.kode == foreign(Komoditas.kategori_kode)",
        lazy="select",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<KategoriPdrb kode={self.kode!r} nama={self.nama!r} level={self.level}>"

    @property
    def kode_singkat(self) -> str:
        """Kode huruf BPS: '1' → 'A', '2' → 'B', dst."""
        _map = {
            "1": "A", "2": "B", "3": "C", "4": "D", "5": "E",
            "6": "F", "7": "G", "8": "H", "9": "I", "10": "J",
            "11": "K", "12": "L", "13": "M,N", "14": "O", "15": "P",
            "16": "Q", "17": "R,S,T,U",
        }
        root = self.kode.split(".")[0]
        return _map.get(root, self.kode)
