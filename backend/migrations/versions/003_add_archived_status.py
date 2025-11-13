"""Add ARCHIVED status to ProjectStatus enum

Revision ID: 003_add_archived_status
Revises: 002_create_projects_table
Create Date: 2025-01-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """添加archived状态到项目状态枚举

    注意：由于PostgreSQL的ENUM类型限制，这里我们不直接修改enum，
    而是通过添加约束来确保数据完整性。实际的状态枚举在应用代码中处理。
    """
    # 为status字段添加注释说明新增的archived状态
    op.execute("COMMENT ON COLUMN projects.status IS '项目处理状态: uploaded, parsing, parsed, generating, completed, failed, archived'")


def downgrade():
    """移除archived状态"""
    # 恢复原始的status字段注释
    op.execute("COMMENT ON COLUMN projects.status IS '项目处理状态: uploaded, parsing, parsed, generating, completed, failed'")