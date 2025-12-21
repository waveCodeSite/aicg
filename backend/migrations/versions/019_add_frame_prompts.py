"""add frame prompts to movie shots

Revision ID: 019
Revises: 018
Create Date: 2025-12-21 17:40:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '019'
down_revision = '018'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('movie_shots', sa.Column('first_frame_prompt', sa.Text(), nullable=True, comment='首帧生成提示词'))
    op.add_column('movie_shots', sa.Column('last_frame_prompt', sa.Text(), nullable=True, comment='尾帧生成提示词'))


def downgrade():
    op.drop_column('movie_shots', 'last_frame_prompt')
    op.drop_column('movie_shots', 'first_frame_prompt')
