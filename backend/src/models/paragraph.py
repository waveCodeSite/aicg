"""
段落模型 - 章节内的文本段落
严格按照data-model.md规范实现
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Dict

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy import select

from .base import BaseModel

if TYPE_CHECKING:
    pass


class ParagraphAction(str, Enum):
    KEEP = "keep"
    EDIT = "edit"
    DELETE = "delete"
    IGNORE = "ignore"


class Paragraph(BaseModel):
    """段落模型 - 章节内的文本段落"""
    __tablename__ = 'paragraphs'

    # 基础字段 (ID, created_at, updated_at 继承自 BaseModel)
    chapter_id = Column(String, ForeignKey('chapters.id'), nullable=False, index=True, comment="章节外键")
    content = Column(Text, nullable=False, comment="段落内容")

    # 结构信息
    order_index = Column(Integer, nullable=False, comment="在章节中的顺序")
    word_count = Column(Integer, default=0, comment="字数统计")
    sentence_count = Column(Integer, default=0, comment="句子数量")

    # 编辑控制
    action = Column(String(10), default=ParagraphAction.KEEP, index=True, comment="操作类型")
    edited_content = Column(Text, nullable=True, comment="编辑后的内容")
    is_confirmed = Column(Boolean, default=False, comment="是否已确认")
    ignore_reason = Column(Text, nullable=True, comment="忽略原因")

    # 生成信息
    audio_url = Column(String(500), nullable=True, comment="段落音频URL")
    audio_duration = Column(Integer, nullable=True, comment="音频时长（秒）")

    # 关系定义
    chapter = relationship("Chapter", back_populates="paragraphs")
    sentences = relationship("Sentence", back_populates="paragraph", cascade="all, delete-orphan")

    # 索引定义
    __table_args__ = (
        Index('idx_paragraph_chapter', 'chapter_id'),
        Index('idx_paragraph_order', 'order_index'),
        Index('idx_paragraph_action', 'action'),
        Index('idx_paragraph_confirmed', 'is_confirmed'),
    )

    def __repr__(self) -> str:
        content_preview = (self.content[:30] + '...') if len(self.content) > 30 else self.content
        return f"<Paragraph(id={self.id}, order={self.order_index}, action={self.action})>"

    # ==================== 批量操作方法 ====================

    @classmethod
    async def batch_create(cls, db_session, paragraphs_data: List[Dict], chapter_ids: List[str]) -> List[str]:
        """
        批量创建段落记录

        Args:
            db_session: 数据库会话
            paragraphs_data: 段落数据列表
            chapter_ids: 对应的章节ID列表

        Returns:
            创建的段落ID列表
        """
        if not paragraphs_data:
            return []

        # 生成ID并添加到数据中
        paragraph_ids = []
        for i, paragraph_data in enumerate(paragraphs_data):
            paragraph_id = str(uuid.uuid4())
            paragraph_data['id'] = paragraph_id
            paragraph_data['chapter_id'] = chapter_ids[i]
            paragraph_data.setdefault('action', ParagraphAction.KEEP.value)
            paragraph_data.setdefault('is_confirmed', False)
            paragraph_ids.append(paragraph_id)

        # 批量插入
        await db_session.execute(
            cls.__table__.insert(),
            paragraphs_data
        )

        # 提交以确保获取ID
        await db_session.flush()

        # 返回插入的ID列表
        return paragraph_ids

    @classmethod
    async def batch_update_sentence_counts(cls, db_session, updates: List[Dict]) -> None:
        """
        批量更新段落的句子统计

        Args:
            db_session: 数据库会话
            updates: 更新数据列表，格式:
                [
                    {
                        'id': str,
                        'sentence_count': int
                    },
                    ...
                ]
        """
        if not updates:
            return

        for update in updates:
            paragraph_id = update.pop('id')
            await db_session.execute(
                cls.__table__.update()
                .where(cls.__table__.c.id == paragraph_id)
                .values(**update)
            )

    @classmethod
    async def get_by_chapter_id(cls, db_session, chapter_id: str) -> List['Paragraph']:
        """
        获取章节的所有段落

        Args:
            db_session: 数据库会话
            chapter_id: 章节ID

        Returns:
            段落列表
        """
        result = await db_session.execute(
            select(cls).where(cls.chapter_id == chapter_id)
                        .order_by(cls.order_index)
        )
        return result.scalars().all()

    @classmethod
    async def count_by_chapter_id(cls, db_session, chapter_id: str) -> int:
        """
        统计章节的段落数量

        Args:
            db_session: 数据库会话
            chapter_id: 章节ID

        Returns:
            段落数量
        """
        from sqlalchemy import func
        result = await db_session.execute(
            select(func.count(cls.id)).where(cls.chapter_id == chapter_id)
        )
        return result.scalar()

    @classmethod
    async def get_by_project_id(cls, db_session, project_id: str) -> List['Paragraph']:
        """
        获取项目的所有段落

        Args:
            db_session: 数据库会话
            project_id: 项目ID

        Returns:
            段落列表
        """
        # 通过子查询获取项目的所有段落
        from src.models.chapter import Chapter

        result = await db_session.execute(
            select(cls)
            .where(cls.chapter_id.in_(
                select(Chapter.id).where(Chapter.project_id == project_id)
            ))
            .order_by(cls.chapter_id, cls.order_index)
        )
        return result.scalars().all()


__all__ = [
    "Paragraph",
    "ParagraphAction",
]
