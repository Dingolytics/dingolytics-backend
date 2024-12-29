"""
Revision ID: 001_74f95d883b60
Revises: 
Create Date: 2024-12-29 16:24:57.248085
"""
from alembic import op
import sqlalchemy as sa

revision = '001_74f95d883b60'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('queries', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=True))
        batch_op.create_index(batch_op.f('ix_queries_is_published'), ['is_published'], unique=False)


def downgrade():
    with op.batch_alter_table('queries', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_queries_is_published'))
        batch_op.drop_column('is_published')
