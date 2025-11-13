"""create content tables: chapters, paragraphs, sentences

Revision ID: 004
Revises: 002
Create Date: 2025-11-13 08:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create chapters table
    op.create_table('chapters',
        sa.Column('id', sa.String(), nullable=False, comment='主键ID'),
        sa.Column('project_id', sa.String(), nullable=False, comment='外键索引，无约束'),
        sa.Column('title', sa.String(length=500), nullable=False, comment='章节标题'),
        sa.Column('content', sa.Text(), nullable=False, comment='章节内容'),
        sa.Column('chapter_number', sa.Integer(), nullable=False, comment='章节序号'),
        sa.Column('word_count', sa.Integer(), default=0, comment='字数统计'),
        sa.Column('paragraph_count', sa.Integer(), default=0, comment='段落数量'),
        sa.Column('sentence_count', sa.Integer(), default=0, comment='句子数量'),
        sa.Column('status', sa.String(length=20), default='pending', comment='处理状态'),
        sa.Column('is_confirmed', sa.Boolean(), default=False, comment='是否确认'),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True, comment='确认时间'),
        sa.Column('edited_content', sa.Text(), nullable=True, comment='编辑后的内容'),
        sa.Column('editing_notes', sa.Text(), nullable=True, comment='编辑备注'),
        sa.Column('generation_settings', sa.Text(), nullable=True, comment='JSON格式生成配置'),
        sa.Column('video_url', sa.String(length=500), nullable=True, comment='生成的视频URL'),
        sa.Column('video_duration', sa.Integer(), nullable=True, comment='视频时长（秒）'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_chapter_project', 'project_id'),
        sa.Index('idx_chapter_number', 'chapter_number'),
        sa.Index('idx_chapter_status', 'status'),
        comment='章节表'
    )

    # Create paragraphs table
    op.create_table('paragraphs',
        sa.Column('id', sa.String(), nullable=False, comment='主键ID'),
        sa.Column('chapter_id', sa.String(), nullable=False, comment='外键索引，无约束'),
        sa.Column('content', sa.Text(), nullable=False, comment='段落内容'),
        sa.Column('order_index', sa.Integer(), nullable=False, comment='在章节中的顺序'),
        sa.Column('word_count', sa.Integer(), default=0, comment='字数统计'),
        sa.Column('sentence_count', sa.Integer(), default=0, comment='句子数量'),
        sa.Column('action', sa.String(length=10), default='keep', comment='操作类型: keep, edit, delete, ignore'),
        sa.Column('edited_content', sa.Text(), nullable=True, comment='编辑后的内容'),
        sa.Column('is_confirmed', sa.Boolean(), default=False, comment='是否确认'),
        sa.Column('ignore_reason', sa.Text(), nullable=True, comment='忽略原因'),
        sa.Column('audio_url', sa.String(length=500), nullable=True, comment='段落音频URL'),
        sa.Column('audio_duration', sa.Integer(), nullable=True, comment='音频时长（秒）'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_paragraph_chapter', 'chapter_id'),
        sa.Index('idx_paragraph_order', 'order_index'),
        sa.Index('idx_paragraph_action', 'action'),
        sa.Index('idx_paragraph_confirmed', 'is_confirmed'),
        comment='段落表'
    )

    # Create sentences table
    op.create_table('sentences',
        sa.Column('id', sa.String(), nullable=False, comment='主键ID'),
        sa.Column('paragraph_id', sa.String(), nullable=False, comment='外键索引，无约束'),
        sa.Column('content', sa.Text(), nullable=False, comment='句子内容'),
        sa.Column('order_index', sa.Integer(), nullable=False, comment='在段落中的顺序'),
        sa.Column('word_count', sa.Integer(), default=0, comment='字数统计'),
        sa.Column('character_count', sa.Integer(), default=0, comment='字符数统计'),
        sa.Column('image_url', sa.String(length=500), nullable=True, comment='生成的图片URL'),
        sa.Column('image_prompt', sa.Text(), nullable=True, comment='图片生成提示词'),
        sa.Column('audio_url', sa.String(length=500), nullable=True, comment='生成的音频URL'),
        sa.Column('start_time', sa.Float(), nullable=True, comment='音频开始时间（秒）'),
        sa.Column('end_time', sa.Float(), nullable=True, comment='音频结束时间（秒）'),
        sa.Column('duration', sa.Float(), nullable=True, comment='音频时长（秒）'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='ASR置信度'),
        sa.Column('voice_settings', sa.Text(), nullable=True, comment='JSON格式语音合成参数'),
        sa.Column('voice_type', sa.String(length=50), nullable=True, comment='语音类型'),
        sa.Column('speech_rate', sa.Float(), default=1.0, comment='语速'),
        sa.Column('pitch', sa.Float(), default=1.0, comment='音调'),
        sa.Column('volume', sa.Float(), default=1.0, comment='音量'),
        sa.Column('status', sa.String(length=20), default='pending', comment='处理状态'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('retry_count', sa.Integer(), default=0, comment='重试次数'),
        sa.Column('edited_content', sa.Text(), nullable=True, comment='编辑后的内容'),
        sa.Column('edited_prompt', sa.Text(), nullable=True, comment='编辑后的提示词'),
        sa.Column('is_manual_edited', sa.Boolean(), default=False, comment='是否手动编辑'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True, comment='完成时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_sentence_paragraph', 'paragraph_id'),
        sa.Index('idx_sentence_order', 'order_index'),
        sa.Index('idx_sentence_status', 'status'),
        sa.Index('idx_sentence_start_time', 'start_time'),
        sa.Index('idx_sentence_end_time', 'end_time'),
        comment='句子表'
    )

    # Create update time trigger function for chapters
    op.execute("""
        CREATE OR REPLACE FUNCTION update_chapters_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create update time trigger function for paragraphs
    op.execute("""
        CREATE OR REPLACE FUNCTION update_paragraphs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create update time trigger function for sentences
    op.execute("""
        CREATE OR REPLACE FUNCTION update_sentences_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create triggers for each table
    op.execute("""
        CREATE TRIGGER update_chapters_updated_at
            BEFORE UPDATE ON chapters
            FOR EACH ROW
            EXECUTE FUNCTION update_chapters_updated_at();
    """)

    op.execute("""
        CREATE TRIGGER update_paragraphs_updated_at
            BEFORE UPDATE ON paragraphs
            FOR EACH ROW
            EXECUTE FUNCTION update_paragraphs_updated_at();
    """)

    op.execute("""
        CREATE TRIGGER update_sentences_updated_at
            BEFORE UPDATE ON sentences
            FOR EACH ROW
            EXECUTE FUNCTION update_sentences_updated_at();
    """)


def downgrade():
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_chapters_updated_at ON chapters")
    op.execute("DROP TRIGGER IF EXISTS update_paragraphs_updated_at ON paragraphs")
    op.execute("DROP TRIGGER IF EXISTS update_sentences_updated_at ON sentences")

    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS update_chapters_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS update_paragraphs_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS update_sentences_updated_at()")

    # Drop tables
    op.drop_table('sentences')
    op.drop_table('paragraphs')
    op.drop_table('chapters')