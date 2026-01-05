"""create storage_configs table

Revision ID: 029
Revises: 028
Create Date: 2026-01-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '029'
down_revision = '028'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建storage_configs表
    op.create_table(
        'storage_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, comment='配置名称'),
        sa.Column('storage_type', sa.String(length=50), nullable=False, comment='存储类型'),
        sa.Column('endpoint', sa.String(length=255), nullable=False, comment='存储端点'),
        sa.Column('access_key', sa.String(length=255), nullable=False, comment='访问密钥'),
        sa.Column('secret_key', sa.Text(), nullable=False, comment='密钥'),
        sa.Column('bucket_name', sa.String(length=100), nullable=False, comment='存储桶名称'),
        sa.Column('region', sa.String(length=50), server_default='us-east-1', comment='区域'),
        sa.Column('is_secure', sa.Boolean(), server_default='false', comment='是否使用HTTPS'),
        sa.Column('public_url', sa.String(length=255), nullable=True, comment='公开访问URL'),
        sa.Column('is_active', sa.Boolean(), server_default='true', comment='是否启用'),
        sa.Column('is_default', sa.Boolean(), server_default='false', comment='是否为默认配置'),
        sa.Column('extra_config', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='额外配置'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 创建索引
    op.create_index('ix_storage_configs_is_default', 'storage_configs', ['is_default'])
    op.create_index('ix_storage_configs_is_active', 'storage_configs', ['is_active'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_storage_configs_is_active')
    op.drop_index('ix_storage_configs_is_default')
    # 删除表
    op.drop_table('storage_configs')
