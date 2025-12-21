"""add last_frame and error fields to movie_shots

Revision ID: 017
Revises: 016
Create Date: 2024-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('movie_shots', sa.Column('last_frame_url', sa.String(length=500), nullable=True, comment='分镜尾帧图URL'))
    op.add_column('movie_shots', sa.Column('last_error', sa.Text(), nullable=True, comment='最后一次生产错误信息'))


def downgrade():
    op.drop_column('movie_shots', 'last_error')
    op.drop_column('movie_shots', 'last_frame_url')
