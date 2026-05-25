"""
004_mdm_tables.py — MDM: ALTER komoditas + CREATE master_versi + audit_master
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── 1. Extend komoditas table ─────────────────────────────────────────────
    with op.batch_alter_table('komoditas') as batch_op:
        batch_op.add_column(sa.Column('klui_1990',        sa.String(20),  nullable=True, comment='Kode KLUI 1990'))
        batch_op.add_column(sa.Column('kbli_2005',        sa.String(20),  nullable=True, comment='Kode KBLI 2005'))
        batch_op.add_column(sa.Column('kbli_2009',        sa.String(20),  nullable=True, comment='Kode KBLI 2009 — standar utama'))
        batch_op.add_column(sa.Column('kbki_2010',        sa.String(20),  nullable=True, comment='Kode KBKI 2010'))
        batch_op.add_column(sa.Column('identitas',        sa.String(50),  nullable=True, comment='Kode identitas gabungan (S0.CK)'))
        batch_op.add_column(sa.Column('pdrb_kbli_kode',   sa.String(10),  nullable=True, comment="Kode subkategori PDRB, mis '1.1.a.'"))
        batch_op.add_column(sa.Column('pdrb_kbli_uraian', sa.String(255), nullable=True, comment='Uraian PDRB sesuai KBLI 2009'))
        batch_op.add_column(sa.Column('klui_uraian',      sa.String(255), nullable=True, comment='Uraian PDRB sesuai KLUI 1990'))
        batch_op.add_column(sa.Column('catatan_varietas', sa.String(255), nullable=True, comment="Catatan varietas/jenis, mis 'Tabama'"))
        batch_op.add_column(sa.Column('indeks_deflator',  sa.String(100), nullable=True, comment='Nama indeks deflator yang digunakan'))
        batch_op.add_column(sa.Column('indeks_dbl_defl',  sa.String(100), nullable=True, comment='Nama indeks double deflasi (jika ada)'))
        batch_op.add_column(sa.Column('urutan_tampil',    sa.Integer(),   nullable=True, server_default='999', comment='Urutan dalam tampilan LK'))
        batch_op.add_column(sa.Column('berlaku_mulai',    sa.Integer(),   nullable=True, comment='Tahun mulai berlaku'))
        batch_op.add_column(sa.Column('berlaku_sampai',   sa.Integer(),   nullable=True, comment='Tahun terakhir berlaku (NULL=masih aktif)'))
        batch_op.add_column(sa.Column('digantikan_oleh',  sa.Integer(),   sa.ForeignKey('komoditas.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('keterangan',       sa.Text(),      nullable=True, comment='Catatan bebas'))
        batch_op.add_column(sa.Column('produk_jadi',      sa.String(100), nullable=True, comment="Mis: 'Gula Hablur', 'Karet Kering', 'CPO'"))
        batch_op.add_column(sa.Column('punya_wip',        sa.Boolean(),   nullable=True, server_default='false', comment='Apakah komoditas punya WIP'))
        batch_op.add_column(sa.Column('punya_cbr',        sa.Boolean(),   nullable=True, server_default='false', comment='Apakah komoditas punya CBR'))
        batch_op.add_column(sa.Column('punya_output_ikutan', sa.Boolean(), nullable=True, server_default='true'))
        batch_op.add_column(sa.Column('metode_harga',     sa.String(50),  nullable=True, comment='Harga Produsen/Perdagangan Besar/Konsumen'))

    # ─── 2. master_versi ───────────────────────────────────────────────────────
    op.create_table(
        'master_versi',
        sa.Column('id',              sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('kode_versi',      sa.String(20),  nullable=False),
        sa.Column('nama_versi',      sa.String(100), nullable=False),
        sa.Column('tahun_terbit',    sa.Integer(),   nullable=False),
        sa.Column('berlaku_mulai_pdrb', sa.Integer(), nullable=True),
        sa.Column('catatan',         sa.Text(),      nullable=True),
        sa.Column('aktif',           sa.Boolean(),   nullable=False, server_default='true'),
        sa.UniqueConstraint('kode_versi', name='uq_master_versi_kode'),
    )

    # Seed master_versi
    op.execute("""
        INSERT INTO master_versi (kode_versi, nama_versi, tahun_terbit, berlaku_mulai_pdrb, catatan, aktif)
        VALUES
          ('KLUI-1990', 'Klasifikasi Lapangan Usaha Indonesia 1990', 1990, 2000,
           'Digunakan sebelum era KBLI. Masih dipakai sebagai referensi historis.', true),
          ('KBLI-2005', 'Klasifikasi Baku Lapangan Usaha Indonesia 2005', 2005, NULL,
           'Versi transisi. Tidak digunakan sebagai standar PDRB.', true),
          ('KBLI-2009', 'Klasifikasi Baku Lapangan Usaha Indonesia 2009', 2009, 2010,
           'Standar utama untuk PDRB Tahun Dasar 2010.', true),
          ('KBKI-2010', 'Klasifikasi Baku Komoditas Indonesia 2010', 2010, 2010,
           'Digunakan untuk referensi komoditas di LK PDRB.', true)
        ON CONFLICT (kode_versi) DO NOTHING
    """)

    # ─── 3. audit_master ───────────────────────────────────────────────────────
    op.create_table(
        'audit_master',
        sa.Column('id',          sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column('tabel_nama',  sa.String(50),  nullable=False),
        sa.Column('record_id',   sa.Integer(),   nullable=False),
        sa.Column('aksi',        sa.String(20),  nullable=False,
                  comment="'INSERT'|'UPDATE'|'DELETE'|'NONAKTIFKAN'"),
        sa.Column('kolom_ubah',  sa.String(100), nullable=True),
        sa.Column('nilai_lama',  sa.Text(),      nullable=True),
        sa.Column('nilai_baru',  sa.Text(),      nullable=True),
        sa.Column('user_id',     sa.Integer(),   nullable=True),
        sa.Column('user_nama',   sa.String(100), nullable=True),
        sa.Column('waktu',       sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column('alasan',      sa.Text(),      nullable=True),
        sa.Column('berlaku_mulai', sa.Integer(), nullable=True,
                  comment='Tahun berlaku khusus untuk perubahan faktor/kode'),
    )
    op.create_index('ix_audit_master_tabel_record', 'audit_master', ['tabel_nama', 'record_id'])
    op.create_index('ix_audit_master_waktu', 'audit_master', ['waktu'])

    # ─── 4. master_satuan ──────────────────────────────────────────────────────
    op.create_table(
        'master_satuan',
        sa.Column('id',          sa.Integer(),   primary_key=True, autoincrement=True),
        sa.Column('kode',        sa.String(20),  nullable=False),
        sa.Column('nama',        sa.String(100), nullable=False),
        sa.Column('keterangan',  sa.Text(),      nullable=True),
        sa.Column('aktif',       sa.Boolean(),   nullable=False, server_default='true'),
        sa.UniqueConstraint('kode', name='uq_master_satuan_kode'),
    )

    # Seed master_satuan
    op.execute("""
        INSERT INTO master_satuan (kode, nama, keterangan, aktif) VALUES
          ('Ton',     'Ton (1.000 Kg)',               'Satuan berat standar pertanian & perkebunan', true),
          ('M3',      'Meter Kubik',                  'Volume kayu, air, dan tambang', true),
          ('Ekor',    'Ekor (hewan)',                 'Satuan peternakan', true),
          ('Brl',     'Barrel (158,99 liter)',        'Minyak bumi', true),
          ('Mscf',    'Thousand Standard Cubic Feet', 'Gas bumi', true),
          ('Kg',      'Kilogram',                     'Satuan kecil, mis rempah', true),
          ('000Ekor', 'Ribuan Ekor',                  'Unggas & ikan', true),
          ('Tgk',     'Tangkai',                      'Bunga dan tanaman hias', true),
          ('Phn',     'Pohon',                        'Tanaman tahunan', true),
          ('Btg',     'Batang',                       'Bambu, tebu per batang', true),
          ('Liter',   'Liter',                        'Minyak atsiri dll', true),
          ('m2',      'Meter Persegi',                'Konstruksi', true)
        ON CONFLICT (kode) DO NOTHING
    """)

    # ─── 5. Tambah kolom berlaku_mulai & berlaku_sampai ke kategori_pdrb ──────
    with op.batch_alter_table('kategori_pdrb') as batch_op:
        batch_op.add_column(sa.Column('berlaku_mulai',  sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('berlaku_sampai', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('keterangan',     sa.Text(),    nullable=True))
        batch_op.add_column(sa.Column('aktif',          sa.Boolean(), nullable=True, server_default='true'))


def downgrade() -> None:
    op.drop_table('master_satuan')
    op.drop_index('ix_audit_master_waktu', 'audit_master')
    op.drop_index('ix_audit_master_tabel_record', 'audit_master')
    op.drop_table('audit_master')
    op.drop_table('master_versi')
    cols = [
        'klui_1990','kbli_2005','kbli_2009','kbki_2010','identitas',
        'pdrb_kbli_kode','pdrb_kbli_uraian','klui_uraian','catatan_varietas',
        'indeks_deflator','indeks_dbl_defl','urutan_tampil','berlaku_mulai',
        'berlaku_sampai','digantikan_oleh','keterangan','produk_jadi',
        'punya_wip','punya_cbr','punya_output_ikutan','metode_harga',
    ]
    with op.batch_alter_table('komoditas') as batch_op:
        for c in cols:
            batch_op.drop_column(c)
    with op.batch_alter_table('kategori_pdrb') as batch_op:
        for c in ['berlaku_mulai','berlaku_sampai','keterangan','aktif']:
            batch_op.drop_column(c)
