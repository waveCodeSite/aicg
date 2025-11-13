"""create users table

Revision ID: 001
Revises:
Create Date: 2025-11-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建 users 表 - 严格按照原始数据模型规范
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False, comment='主键ID'),
        sa.Column('username', sa.String(length=50), nullable=False, comment='用户名'),
        sa.Column('email', sa.String(length=100), nullable=False, comment='邮箱'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='密码哈希'),
        sa.Column('display_name', sa.String(length=100), nullable=True, comment='显示名称'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='头像URL'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='是否激活'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, comment='是否已验证'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True, comment='最后登录时间'),
        sa.Column('preferences', sa.Text(), nullable=True, comment='JSON格式存储偏好设置'),
        sa.Column('timezone', sa.String(length=50), nullable=False, comment='时区'),
        sa.Column('language', sa.String(length=10), nullable=False, comment='语言'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username', name='uq_users_username'),
        sa.UniqueConstraint('email', name='uq_users_email'),
        sa.Index('ix_users_username', 'username'),
        sa.Index('ix_users_email', 'email'),
        comment='用户表'
    )

    # 创建更新时间触发器函数
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # 为 users 表创建更新时间触发器
    op.execute("""
        CREATE TRIGGER update_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade():
    # 删除触发器
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users")

    # 删除触发器函数
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # 删除表
    op.drop_table('users')