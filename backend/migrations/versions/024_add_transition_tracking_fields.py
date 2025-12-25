"""add api_key_id and user_id to movie_shot_transitions

Revision ID: 024_add_transition_tracking_fields
Revises: 023_add_scene_image_fields
Create Date: 2025-12-25 14:04:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '024'
down_revision = '023'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 api_key_id 字段
    op.add_column('movie_shot_transitions', 
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=True, comment='使用的API Key')
    )
    
    # 添加 user_id 字段
    op.add_column('movie_shot_transitions', 
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, comment='所属用户')
    )
    
    # 创建索引
    op.create_index(
        'ix_movie_shot_transitions_api_key_id', 
        'movie_shot_transitions', 
        ['api_key_id'], 
        unique=False
    )
    
    op.create_index(
        'ix_movie_shot_transitions_user_id', 
        'movie_shot_transitions', 
        ['user_id'], 
        unique=False
    )
    
    # 创建外键约束
    op.create_foreign_key(
        'fk_movie_shot_transitions_api_key_id', 
        'movie_shot_transitions', 
        'api_keys', 
        ['api_key_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_movie_shot_transitions_user_id', 
        'movie_shot_transitions', 
        'users', 
        ['user_id'], 
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # 删除外键约束
    op.drop_constraint('fk_movie_shot_transitions_user_id', 'movie_shot_transitions', type_='foreignkey')
    op.drop_constraint('fk_movie_shot_transitions_api_key_id', 'movie_shot_transitions', type_='foreignkey')
    
    # 删除索引
    op.drop_index('ix_movie_shot_transitions_user_id', table_name='movie_shot_transitions')
    op.drop_index('ix_movie_shot_transitions_api_key_id', table_name='movie_shot_transitions')
    
    # 删除列
    op.drop_column('movie_shot_transitions', 'user_id')
    op.drop_column('movie_shot_transitions', 'api_key_id')
