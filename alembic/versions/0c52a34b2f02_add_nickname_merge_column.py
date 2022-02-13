"""add nickname_merge column

Revision ID: 0c52a34b2f02
Revises: 03261d93c01c
Create Date: 2022-02-13 15:16:28.753430

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0c52a34b2f02'
down_revision = '03261d93c01c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('level', sa.Column('nickname_merge', sa.Boolean, nullable=False, server_default='0'))


def downgrade():
    op.drop_column('level', 'nickname_merge')
