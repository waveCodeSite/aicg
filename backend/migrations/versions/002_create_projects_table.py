"""create projects table

Revision ID: 002
Revises: 001
Create Date: 2025-11-12 09:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 projects 表 - 严格按照data-model.md规范
    op.create_table('projects',
        sa.Column('id', sa.String(), nullable=False, comment='主键ID'),
        sa.Column('owner_id', sa.String(), nullable=False, comment='外键索引，无约束'),
        sa.Column('title', sa.String(length=200), nullable=False, comment='项目标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='项目描述'),
        sa.Column('file_name', sa.String(length=255), nullable=False, comment='文件名称'),
        sa.Column('file_size', sa.Integer(), nullable=False, comment='文件大小（字节）'),
        sa.Column('file_type', sa.String(length=10), nullable=False, comment='文件类型: txt, md, docx, epub'),
        sa.Column('file_path', sa.String(length=500), nullable=False, comment='MinIO存储路径'),
        sa.Column('file_hash', sa.String(length=64), nullable=True, comment='文件MD5哈希'),
        sa.Column('word_count', sa.Integer(), nullable=True, default=0, comment='字数统计'),
        sa.Column('chapter_count', sa.Integer(), nullable=True, default=0, comment='章节数量'),
        sa.Column('paragraph_count', sa.Integer(), nullable=True, default=0, comment='段落数量'),
        sa.Column('sentence_count', sa.Integer(), nullable=True, default=0, comment='句子数量'),
        sa.Column('status', sa.String(length=20), nullable=True, default='uploaded', comment='处理状态'),
        sa.Column('processing_progress', sa.Integer(), nullable=True, default=0, comment='0-100处理进度'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('generation_settings', sa.Text(), nullable=True, comment='JSON格式存储生成配置'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_project_owner', 'owner_id'),
        sa.Index('idx_project_status', 'status'),
        sa.Index('idx_project_created', 'created_at'),
        sa.Index('idx_project_file_hash', 'file_hash'),
        sa.Index('ix_projects_file_hash', 'file_hash'),
        sa.Index('ix_projects_owner_id', 'owner_id'),
        sa.Index('ix_projects_status', 'status'),
        comment='项目表'
    )

    # 创建更新时间触发器
    op.execute("""
        CREATE OR REPLACE FUNCTION update_projects_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # 为 projects 表创建更新时间触发器
    op.execute("""
        CREATE TRIGGER update_projects_updated_at
            BEFORE UPDATE ON projects
            FOR EACH ROW
            EXECUTE FUNCTION update_projects_updated_at();
    """)


def downgrade():
    # 删除触发器
    op.execute("DROP TRIGGER IF EXISTS update_projects_updated_at ON projects")

    # 删除触发器函数
    op.execute("DROP FUNCTION IF EXISTS update_projects_updated_at()")

    # 删除表
    op.drop_table('projects')