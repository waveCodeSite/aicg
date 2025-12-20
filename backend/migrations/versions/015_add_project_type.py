"""add project type

Revision ID: 015
Revises: 014
Create Date: 2024-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 添加 type 列，允许为空
    op.add_column('projects', sa.Column('type', sa.String(length=20), nullable=True, comment='项目类型'))
    
    # 2. 为现有项目设置默认值 'picture_narrative'
    op.execute("UPDATE projects SET type = 'picture_narrative' WHERE type IS NULL")
    
    # 3. 设置为不可为空并添加索引
    op.alter_column('projects', 'type', nullable=False)
    op.create_index('idx_project_type', 'projects', ['type'])


def downgrade():
    op.drop_index('idx_project_type', table_name='projects')
    op.drop_column('projects', 'type')
