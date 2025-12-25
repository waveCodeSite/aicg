"""add error_message to movie_shot_transitions

Revision ID: 025
Revises: 024
Create Date: 2025-12-25 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 error_message 字段
    op.add_column('movie_shot_transitions', 
        sa.Column('error_message', sa.Text(), nullable=True, comment='失败错误信息')
    )


def downgrade():
    # 删除 error_message 字段
    op.drop_column('movie_shot_transitions', 'error_message')
