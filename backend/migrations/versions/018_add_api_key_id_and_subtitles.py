"""add api_key_id and subtitles to movie_shots

Revision ID: 018
Revises: 017
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('movie_shots', sa.Column('api_key_id', sa.String(length=50), nullable=True, comment='使用的 API Key ID'))


def downgrade():
    op.drop_column('movie_shots', 'api_key_id')
