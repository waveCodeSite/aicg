"""create system_settings table

Revision ID: 030
Revises: 029
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '030'
down_revision = '029'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建system_settings表
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(length=100), unique=True, nullable=False, comment='设置键'),
        sa.Column('value', sa.Text(), nullable=True, comment='设置值'),
        sa.Column('value_type', sa.String(length=20), server_default='string', comment='值类型'),
        sa.Column('description', sa.String(length=255), nullable=True, comment='设置描述'),
        sa.Column('category', sa.String(length=50), server_default='general', comment='设置分类'),
        sa.Column('is_public', sa.Boolean(), server_default='false', comment='是否公开'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 创建索引
    op.create_index('ix_system_settings_key', 'system_settings', ['key'], unique=True)
    op.create_index('ix_system_settings_category', 'system_settings', ['category'])

    # 插入默认设置
    op.execute("""
        INSERT INTO system_settings (id, key, value, value_type, description, category, is_public)
        VALUES (
            gen_random_uuid(),
            'enable_registration',
            'true',
            'boolean',
            '是否允许用户注册',
            'auth',
            true
        )
    """)


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_system_settings_category')
    op.drop_index('ix_system_settings_key')
    # 删除表
    op.drop_table('system_settings')
