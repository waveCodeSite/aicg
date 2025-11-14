"""
句子模型 - 最小视频生成单元
严格按照data-model.md规范实现
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Dict

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy import select

from .base import BaseModel

if TYPE_CHECKING:
    pass


class SentenceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Sentence(BaseModel):
    """句子模型 - 最小视频生成单元"""
    __tablename__ = 'sentences'

    # 基础字段 (ID, created_at, updated_at 继承自 BaseModel)
    paragraph_id = Column(String, ForeignKey('paragraphs.id'), nullable=False, index=True, comment="段落外键")
    content = Column(Text, nullable=False, comment="句子内容")

    # 结构信息
    order_index = Column(Integer, nullable=False, comment="在段落中的顺序")
    word_count = Column(Integer, default=0, comment="字数统计")
    character_count = Column(Integer, default=0, comment="字符数量")

    # 生成资源
    image_url = Column(String(500), nullable=True, comment="生成的图片URL")
    image_prompt = Column(Text, nullable=True, comment="图片生成提示词")
    audio_url = Column(String(500), nullable=True, comment="生成的音频URL")

    # 时间轴信息（来自ASR）
    start_time = Column(Float, nullable=True, comment="音频开始时间（秒）")
    end_time = Column(Float, nullable=True, comment="音频结束时间（秒）")
    duration = Column(Float, nullable=True, comment="音频时长（秒）")
    confidence_score = Column(Float, nullable=True, comment="ASR置信度")

    # 语音设置
    voice_settings = Column(Text, nullable=True, comment="JSON格式的语音合成参数")
    voice_type = Column(String(50), nullable=True, comment="语音类型")
    speech_rate = Column(Float, default=1.0, comment="语速")
    pitch = Column(Float, default=1.0, comment="音调")
    volume = Column(Float, default=1.0, comment="音量")

    # 处理状态
    status = Column(String(20), default=SentenceStatus.PENDING, index=True, comment="处理状态")
    error_message = Column(Text, nullable=True, comment="错误信息")
    retry_count = Column(Integer, default=0, comment="重试次数")

    # 用户编辑
    edited_content = Column(Text, nullable=True, comment="编辑后的内容")
    edited_prompt = Column(Text, nullable=True, comment="编辑后的提示词")
    is_manual_edited = Column(Boolean, default=False, comment="是否手动编辑")

    # 完成时间
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 关系定义
    paragraph = relationship("Paragraph", back_populates="sentences")

    # 索引定义
    __table_args__ = (
        Index('idx_sentence_paragraph', 'paragraph_id'),
        Index('idx_sentence_order', 'order_index'),
        Index('idx_sentence_status', 'status'),
        Index('idx_sentence_start_time', 'start_time'),
        Index('idx_sentence_end_time', 'end_time'),
    )

    def __repr__(self) -> str:
        content_preview = (self.content[:30] + '...') if len(self.content) > 30 else self.content
        return f"<Sentence(id={self.id}, order={self.order_index}, status={self.status})>"

    # ==================== 批量操作方法 ====================

    @classmethod
    async def batch_create(cls, db_session, sentences_data: List[Dict], paragraph_ids: List[str]) -> List[str]:
        """
        批量创建句子记录

        Args:
            db_session: 数据库会话
            sentences_data: 句子数据列表
            paragraph_ids: 对应的段落ID列表

        Returns:
            创建的句子ID列表
        """
        if not sentences_data:
            return []

        # 生成ID并添加到数据中
        sentence_ids = []
        for i, sentence_data in enumerate(sentences_data):
            sentence_id = str(uuid.uuid4())
            sentence_data['id'] = sentence_id
            sentence_data['paragraph_id'] = paragraph_ids[i]
            sentence_data.setdefault('status', SentenceStatus.PENDING.value)
            sentence_data.setdefault('retry_count', 0)
            sentence_data.setdefault('is_manual_edited', False)
            sentence_ids.append(sentence_id)

        # 批量插入
        await db_session.execute(
            cls.__table__.insert(),
            sentences_data
        )

        # 提交以确保获取ID
        await db_session.flush()

        # 返回插入的ID列表
        return sentence_ids

    @classmethod
    async def batch_update_status(cls, db_session, updates: List[Dict]) -> None:
        """
        批量更新句子状态

        Args:
            db_session: 数据库会话
            updates: 更新数据列表，格式:
                [
                    {
                        'id': str,
                        'status': str,
                        'error_message': str,
                        'retry_count': int
                    },
                    ...
                ]
        """
        if not updates:
            return

        for update in updates:
            sentence_id = update.pop('id')
            # 添加更新时间
            update['updated_at'] = datetime.utcnow()

            await db_session.execute(
                cls.__table__.update()
                .where(cls.__table__.c.id == sentence_id)
                .values(**update)
            )

    @classmethod
    async def batch_mark_completed(cls, db_session, sentence_ids: List[str]) -> None:
        """
        批量标记句子为完成状态

        Args:
            db_session: 数据库会话
            sentence_ids: 句子ID列表
        """
        await db_session.execute(
            cls.__table__.update()
            .where(cls.__table__.c.id.in_(sentence_ids))
            .values(
                status=SentenceStatus.COMPLETED.value,
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
        )

    @classmethod
    async def get_by_paragraph_id(cls, db_session, paragraph_id: str) -> List['Sentence']:
        """
        获取段落的所有句子

        Args:
            db_session: 数据库会话
            paragraph_id: 段落ID

        Returns:
            句子列表
        """
        result = await db_session.execute(
            select(cls).where(cls.paragraph_id == paragraph_id)
                        .order_by(cls.order_index)
        )
        return result.scalars().all()

    @classmethod
    async def count_by_paragraph_id(cls, db_session, paragraph_id: str) -> int:
        """
        统计段落的句子数量

        Args:
            db_session: 数据库会话
            paragraph_id: 段落ID

        Returns:
            句子数量
        """
        from sqlalchemy import func
        result = await db_session.execute(
            select(func.count(cls.id)).where(cls.paragraph_id == paragraph_id)
        )
        return result.scalar()

    @classmethod
    async def get_by_project_id(cls, db_session, project_id: str) -> List['Sentence']:
        """
        获取项目的所有句子

        Args:
            db_session: 数据库会话
            project_id: 项目ID

        Returns:
            句子列表
        """
        # 通过嵌套子查询获取项目的所有句子
        from src.models.paragraph import Paragraph
        from src.models.chapter import Chapter

        result = await db_session.execute(
            select(cls)
            .where(cls.paragraph_id.in_(
                select(Paragraph.id).where(
                    Paragraph.chapter_id.in_(
                        select(Chapter.id).where(Chapter.project_id == project_id)
                    )
                )
            ))
            .order_by(cls.paragraph_id, cls.order_index)
        )
        return result.scalars().all()

    @classmethod
    async def get_pending_sentences(cls, db_session, limit: int = 100) -> List['Sentence']:
        """
        获取待处理的句子

        Args:
            db_session: 数据库会话
            limit: 限制数量

        Returns:
            待处理的句子列表
        """
        result = await db_session.execute(
            select(cls).where(cls.status == SentenceStatus.PENDING.value)
                        .order_by(cls.created_at)
                        .limit(limit)
        )
        return result.scalars().all()


__all__ = [
    "Sentence",
    "SentenceStatus",
]
