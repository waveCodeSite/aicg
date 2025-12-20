"""create movie tables: movie_scripts, movie_scenes, movie_shots, movie_characters

Revision ID: 014
Revises: 013
Create Date: 2025-12-20 15:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    # Create movie_scripts table
    op.create_table('movie_scripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('chapter_id', postgresql.UUID(as_uuid=True), nullable=False, comment='章节外键'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending', comment='剧本状态'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_movie_script_chapter', 'chapter_id'),
        sa.Index('idx_movie_script_status', 'status'),
        comment='电影剧本表'
    )

    # Create movie_scenes table
    op.create_table('movie_scenes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('script_id', postgresql.UUID(as_uuid=True), nullable=False, comment='剧本外键'),
        sa.Column('order_index', sa.Integer(), nullable=False, comment='场景顺序'),
        sa.Column('location', sa.String(length=200), nullable=True, comment='拍摄地点'),
        sa.Column('time_of_day', sa.String(length=50), nullable=True, comment='拍摄时间'),
        sa.Column('atmosphere', sa.String(length=200), nullable=True, comment='氛围描述'),
        sa.Column('description', sa.Text(), nullable=True, comment='场景文本描述'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_movie_scene_script', 'script_id'),
        sa.Index('idx_movie_scene_order', 'order_index'),
        comment='电影场景表'
    )

    # Create movie_shots table
    op.create_table('movie_shots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('scene_id', postgresql.UUID(as_uuid=True), nullable=False, comment='场景外键'),
        sa.Column('order_index', sa.Integer(), nullable=False, comment='镜头顺序'),
        sa.Column('visual_description', sa.Text(), nullable=False, comment='画面描述提示词'),
        sa.Column('camera_movement', sa.String(length=200), nullable=True, comment='镜头运动描述'),
        sa.Column('dialogue', sa.Text(), nullable=True, comment='人物对话内容'),
        sa.Column('performance_prompt', sa.Text(), nullable=True, comment='表演/对话表现提示词'),
        sa.Column('first_frame_url', sa.String(length=500), nullable=True, comment='分镜首帧图URL'),
        sa.Column('video_url', sa.String(length=500), nullable=True, comment='生成的视频URL'),
        sa.Column('video_task_id', sa.String(length=100), nullable=True, comment='Vector Engine 任务ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_movie_shot_scene', 'scene_id'),
        sa.Index('idx_movie_shot_order', 'order_index'),
        comment='电影分镜表'
    )

    # Create movie_characters table
    op.create_table('movie_characters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False, comment='项目外键'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='角色名称'),
        sa.Column('role_description', sa.Text(), nullable=True, comment='角色描述/背景'),
        sa.Column('visual_traits', sa.Text(), nullable=True, comment='视觉特征描述'),
        sa.Column('dialogue_traits', sa.Text(), nullable=True, comment='对话特征描述'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='头像URL'),
        sa.Column('reference_images', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='参考图URL列表'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_movie_character_project', 'project_id'),
        comment='电影角色表'
    )

    # Create triggers for updated_at
    for table in ['movie_scripts', 'movie_scenes', 'movie_shots', 'movie_characters']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade():
    # Drop triggers
    for table in ['movie_scripts', 'movie_scenes', 'movie_shots', 'movie_characters']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")

    # Drop tables
    op.drop_table('movie_characters')
    op.drop_table('movie_shots')
    op.drop_table('movie_scenes')
    op.drop_table('movie_scripts')
