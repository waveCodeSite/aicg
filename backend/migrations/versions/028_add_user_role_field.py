"""add user role field

Revision ID: 028
Revises: 027
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028'
down_revision = '027'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加role字段
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=False, server_default='user', comment='用户角色: admin, user'))


def downgrade() -> None:
    # 删除role字段
    op.drop_column('users', 'role')
