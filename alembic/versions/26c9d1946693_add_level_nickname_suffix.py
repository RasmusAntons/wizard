"""add Level.nickname_suffix

Revision ID: 26c9d1946693
Revises: 
Create Date: 2021-12-19 01:00:04.535321

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26c9d1946693'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('level', sa.Column('nickname_suffix', sa.String, nullable=True))


def downgrade():
    op.drop_column('level', 'nickname_suffix')
