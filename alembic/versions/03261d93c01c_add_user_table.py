"""add user table

Revision ID: 03261d93c01c
Revises: 26c9d1946693
Create Date: 2022-02-06 00:48:59.285964

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03261d93c01c'
down_revision = '26c9d1946693'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user',
                    sa.Column('id', sa.String(18), primary_key=True),
                    sa.Column('name', sa.String(32)),
                    sa.Column('nick', sa.String(32)))


def downgrade():
    op.drop_table('user')
