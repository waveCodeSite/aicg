"""add video production fields

Revision ID: 016
Revises: 015
Create Date: 2024-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 video_prompt 列
    op.add_column('movie_shots', sa.Column('video_prompt', sa.Text(), nullable=True, comment='用于生成视频的最终提示词（包含一致性特征）'))
    
    # 添加 status 列
    op.add_column('movie_shots', sa.Column('status', sa.String(length=20), nullable=True, comment='镜头生产状态'))
    
    # 设置默认值并添加索引
    op.execute("UPDATE movie_shots SET status = 'pending' WHERE status IS NULL")
    op.alter_column('movie_shots', 'status', nullable=False, server_default='pending')
    op.create_index('ix_movie_shots_status', 'movie_shots', ['status'], unique=False)


def downgrade():
    op.drop_index('ix_movie_shots_status', table_name='movie_shots')
    op.drop_column('movie_shots', 'status')
    op.drop_column('movie_shots', 'video_prompt')
