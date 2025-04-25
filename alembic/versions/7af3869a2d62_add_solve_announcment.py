"""add solve announcment

Revision ID: 7af3869a2d62
Revises: 3ee936487af0
Create Date: 2025-04-25 01:28:52.285281

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7af3869a2d62'
down_revision = '3ee936487af0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('level', sa.Column('announce_solve', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('level', 'announce_solve')
