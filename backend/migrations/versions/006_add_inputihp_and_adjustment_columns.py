"""
006_add_inputihp_and_adjustment_columns.py

Add InputIHP table and adjustment columns to PdrbRekap.
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create input_ihp table
    op.create_table(
        'input_ihp',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('kategori_kode', sa.String(length=10), nullable=False),
        sa.Column('komoditas_id', sa.Integer(), nullable=True),
        sa.Column('wilayah_kode', sa.String(length=10), nullable=False),
        sa.Column('tahun', sa.Integer(), nullable=False),
        sa.Column('triwulan', sa.Integer(), nullable=True),
        sa.Column('nilai_indeks', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('sumber_data', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('triwulan IN (1, 2, 3, 4) OR triwulan IS NULL', name='ck_ihp_triwulan'),
        sa.ForeignKeyConstraint(['kategori_kode'], ['kategori_pdrb.kode'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['komoditas_id'], ['komoditas.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['wilayah_kode'], ['wilayah.kode'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kategori_kode', 'komoditas_id', 'wilayah_kode', 'tahun', 'triwulan', name='uq_input_ihp')
    )
    op.create_index(op.f('ix_input_ihp_kategori_kode'), 'input_ihp', ['kategori_kode'], unique=False)
    op.create_index(op.f('ix_input_ihp_komoditas_id'), 'input_ihp', ['komoditas_id'], unique=False)
    op.create_index(op.f('ix_input_ihp_wilayah_kode'), 'input_ihp', ['wilayah_kode'], unique=False)

    # Add columns to pdrb_rekap
    op.add_column('pdrb_rekap', sa.Column('ntb_sebelum_adj_adhb', sa.Numeric(precision=20, scale=6), nullable=True))
    op.add_column('pdrb_rekap', sa.Column('adjustment_adhb', sa.Numeric(precision=20, scale=6), nullable=True))
    op.add_column('pdrb_rekap', sa.Column('ntb_sebelum_adj_adhk', sa.Numeric(precision=20, scale=6), nullable=True))
    op.add_column('pdrb_rekap', sa.Column('adjustment_adhk', sa.Numeric(precision=20, scale=6), nullable=True))


def downgrade() -> None:
    op.drop_column('pdrb_rekap', 'adjustment_adhk')
    op.drop_column('pdrb_rekap', 'ntb_sebelum_adj_adhk')
    op.drop_column('pdrb_rekap', 'adjustment_adhb')
    op.drop_column('pdrb_rekap', 'ntb_sebelum_adj_adhb')

    op.drop_index(op.f('ix_input_ihp_wilayah_kode'), table_name='input_ihp')
    op.drop_index(op.f('ix_input_ihp_komoditas_id'), table_name='input_ihp')
    op.drop_index(op.f('ix_input_ihp_kategori_kode'), table_name='input_ihp')
    op.drop_table('input_ihp')
