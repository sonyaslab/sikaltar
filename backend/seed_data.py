import os
import sys
from sqlalchemy.orm import Session
from sqlalchemy import text

# Tambahkan path aplikasi agar bisa import module app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.wilayah import Wilayah
from app.models.kategori_pdrb import KategoriPdrb
from app.models.komoditas import Komoditas
from app.models.input_data import InputHarga, InputProduksi

def seed_data():
    print("Memulai proses seeding Master Data...")
    db: Session = SessionLocal()
    
    try:
        # 1. Pastikan tabel terbuat (meski biasanya alembic yang urus, kita pastikan saja)
        Base.metadata.create_all(bind=engine)

        # 2. SEED WILAYAH
        if db.query(Wilayah).count() == 0:
            print("Seeding Wilayah...")
            wilayah_data = [
                Wilayah(kode="65", nama="Kalimantan Utara", level="provinsi", parent_kode=None),
                Wilayah(kode="6501", nama="Kabupaten Malinau", level="kabupaten", parent_kode="65"),
                Wilayah(kode="6502", nama="Kabupaten Bulungan", level="kabupaten", parent_kode="65"),
                Wilayah(kode="6503", nama="Kabupaten Tana Tidung", level="kabupaten", parent_kode="65"),
                Wilayah(kode="6504", nama="Kabupaten Nunukan", level="kabupaten", parent_kode="65"),
                Wilayah(kode="6571", nama="Kota Tarakan", level="kota", parent_kode="65"),
            ]
            db.add_all(wilayah_data)
            db.commit()

        # 3. SEED KATEGORI PDRB
        if db.query(KategoriPdrb).count() == 0:
            print("Seeding Kategori PDRB...")
            kategori_data = [
                # Kategori A: Pertanian
                KategoriPdrb(kode="1", nama="Pertanian, Kehutanan, dan Perikanan", level=1, urutan=1),
                KategoriPdrb(kode="1.1", nama="Pertanian, Peternakan, Perburuan dan Jasa Pertanian", parent_kode="1", level=2, urutan=2),
                KategoriPdrb(kode="1.1.a", nama="Tanaman Pangan", parent_kode="1.1", level=3, metode_adhb="Produksi", urutan=3),
                KategoriPdrb(kode="1.1.b", nama="Tanaman Hortikultura", parent_kode="1.1", level=3, metode_adhb="Produksi", urutan=4),
                KategoriPdrb(kode="1.1.c", nama="Perkebunan", parent_kode="1.1", level=3, metode_adhb="Produksi", urutan=5),
                
                # Kategori B: Pertambangan
                KategoriPdrb(kode="2", nama="Pertambangan dan Penggalian", level=1, urutan=6),
                KategoriPdrb(kode="2.1", nama="Pertambangan Minyak, Gas dan Panas Bumi", parent_kode="2", level=2, urutan=7),
                KategoriPdrb(kode="2.1.a", nama="Pertambangan Minyak dan Gas Bumi", parent_kode="2.1", level=3, metode_adhb="Produksi", urutan=8),
                KategoriPdrb(kode="2.2", nama="Pertambangan Batu Bara dan Lignit", parent_kode="2", level=2, metode_adhb="Produksi", urutan=9),
            ]
            db.add_all(kategori_data)
            db.commit()

        # 4. SEED KOMODITAS
        if db.query(Komoditas).count() == 0:
            print("Seeding Komoditas...")
            komoditas_data = [
                # Komoditas Tanaman Pangan (1.1.a)
                Komoditas(kode_internal="11a01", kategori_kode="1.1.a", nama="Padi Sawah", wujud_produksi="GKG", satuan_produksi="Ton", satuan_harga="Rp/Kg", faktor_konversi=1000.00, aktif=True),
                Komoditas(kode_internal="11a02", kategori_kode="1.1.a", nama="Jagung", wujud_produksi="Pipilan Kering", satuan_produksi="Ton", satuan_harga="Rp/Kg", faktor_konversi=1000.00, aktif=True),
                Komoditas(kode_internal="11a03", kategori_kode="1.1.a", nama="Singkong", wujud_produksi="Umbi Basah", satuan_produksi="Ton", satuan_harga="Rp/Kg", faktor_konversi=1000.00, aktif=True),
                
                # Komoditas Hortikultura (1.1.b)
                Komoditas(kode_internal="11b01", kategori_kode="1.1.b", nama="Bawang Merah", wujud_produksi="Umbi Kering", satuan_produksi="Ton", satuan_harga="Rp/Kg", faktor_konversi=1000.00, aktif=True),
                Komoditas(kode_internal="11b02", kategori_kode="1.1.b", nama="Cabai Rawit", wujud_produksi="Buah Segar", satuan_produksi="Ton", satuan_harga="Rp/Kg", faktor_konversi=1000.00, aktif=True),
                
                # Komoditas Perkebunan (1.1.c)
                Komoditas(kode_internal="11c01", kategori_kode="1.1.c", nama="Kelapa Sawit", wujud_produksi="TBS", satuan_produksi="Ton", satuan_harga="Rp/Kg", faktor_konversi=1000.00, aktif=True),
                
                # Komoditas Pertambangan Migas (2.1.a)
                Komoditas(kode_internal="21a01", kategori_kode="2.1.a", nama="Minyak Bumi", wujud_produksi="Minyak Mentah", satuan_produksi="Barel", satuan_harga="US$/Barel", faktor_konversi=1.00, aktif=True),
                
                # Komoditas Batu Bara (2.2)
                Komoditas(kode_internal="2201", kategori_kode="2.2", nama="Batu Bara", wujud_produksi="Batu Bara Curah", satuan_produksi="Ton", satuan_harga="Rp/Ton", faktor_konversi=1.00, aktif=True),
            ]
            db.add_all(komoditas_data)
            db.commit()

        # 5. SEED INPUT HARGA (tahun dasar 2010 & berjalan 2024)
        if db.query(InputHarga).count() == 0:
            print("Seeding Data Harga...")
            all_kom = db.query(Komoditas).all()
            kom_map = {k.kode_internal: k.id for k in all_kom}
            harga_2010 = {
                "11a01": 3_200_000, "11a02": 1_800_000, "11a03": 750_000,
                "11b01": 15_000_000, "11b02": 12_000_000,
                "11c01": 1_350_000, "21a01": 800_000, "2201": 400_000,
            }
            harga_2024 = {
                "11a01": 6_500_000, "11a02": 3_200_000, "11a03": 1_500_000,
                "11b01": 30_000_000, "11b02": 25_000_000,
                "11c01": 2_800_000, "21a01": 1_200_000, "2201": 900_000,
            }
            rows = []
            for kode, harga in harga_2010.items():
                kid = kom_map.get(kode)
                if kid:
                    rows.append(InputHarga(komoditas_id=kid, wilayah_kode="65", tahun=2010,
                        triwulan=None, harga_berlaku=harga, harga_konstan_2010=harga, sumber_data="BPS"))
            for kode, harga in harga_2024.items():
                kid = kom_map.get(kode)
                if kid:
                    rows.append(InputHarga(komoditas_id=kid, wilayah_kode="65", tahun=2024,
                        triwulan=None, harga_berlaku=harga, sumber_data="BPS"))
            db.add_all(rows)
            db.commit()

        # 6. SEED INPUT PRODUKSI 2024
        if db.query(InputProduksi).count() == 0:
            print("Seeding Data Produksi...")
            all_kom = db.query(Komoditas).all()
            kom_map = {k.kode_internal: k.id for k in all_kom}
            produksi_2024 = {
                "11a01": 98_450.5, "11a02": 4_250.3, "11a03": 6_750.0,
                "11b01": 320.5,   "11b02": 280.0,
                "11c01": 520_000.0, "21a01": 5_200_000.0, "2201": 18_000_000.0,
            }
            rows = []
            for kode, kuantum in produksi_2024.items():
                kid = kom_map.get(kode)
                if kid:
                    rows.append(InputProduksi(komoditas_id=kid, wilayah_kode="65", tahun=2024,
                        triwulan=None, kuantum=kuantum, sumber_data="Dinas Pertanian", status="sementara"))
            db.add_all(rows)
            db.commit()

        print("✅ Seeding selesai! Master Data berhasil dimasukkan.")
        print("Silakan refresh halaman S1.H atau S1.P di browser Anda.")
        
    except Exception as e:
        print(f"❌ Error saat seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
