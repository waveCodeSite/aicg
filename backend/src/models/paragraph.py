"""
段落模型 - 章节内的文本段落
严格按照data-model.md规范实现
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base

if TYPE_CHECKING:
    pass


class ParagraphAction(str, Enum):
    KEEP = "keep"
    EDIT = "edit"
    DELETE = "delete"
    IGNORE = "ignore"


class Paragraph(Base):
    """段落模型 - 章节内的文本段落"""
    __tablename__ = 'paragraphs'

    # 基础字段
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id = Column(String, nullable=False, index=True)  # 外键索引，无约束
    content = Column(Text, nullable=False)

    # 结构信息
    order_index = Column(Integer, nullable=False)  # 在章节中的顺序
    word_count = Column(Integer, default=0)
    sentence_count = Column(Integer, default=0)

    # 编辑控制
    action = Column(String(10), default=ParagraphAction.KEEP, index=True)
    edited_content = Column(Text, nullable=True)  # 编辑后的内容
    is_confirmed = Column(Boolean, default=False)
    ignore_reason = Column(Text, nullable=True)  # 忽略原因

    # 生成信息
    audio_url = Column(String(500), nullable=True)  # 段落音频URL
    audio_duration = Column(Integer, nullable=True)  # 音频时长（秒）

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


__all__ = [
    "Paragraph",
    "ParagraphAction",
]
