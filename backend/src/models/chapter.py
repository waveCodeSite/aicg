"""
章节模型 - 文档的逻辑分割单元
严格按照data-model.md规范实现
"""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from enum import Enum
from typing import TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .project import Project
    from .paragraph import Paragraph


class ChapterStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Chapter(Base):
    """章节模型 - 文档的逻辑分割单元"""
    __tablename__ = 'chapters'

    # 基础字段
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False, index=True)  # 外键索引，无约束
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)  # 章节原始内容

    # 结构信息
    chapter_number = Column(Integer, nullable=False)
    word_count = Column(Integer, default=0)
    paragraph_count = Column(Integer, default=0)
    sentence_count = Column(Integer, default=0)

    # 处理状态
    status = Column(String(20), default=ChapterStatus.PENDING, index=True)
    is_confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime, nullable=True)

    # 编辑信息
    edited_content = Column(Text, nullable=True)  # 用户编辑后的内容
    editing_notes = Column(Text, nullable=True)  # 编辑备注

    # 生成信息
    generation_settings = Column(Text, nullable=True)  # 章节级生成配置
    video_url = Column(String(500), nullable=True)  # 最终视频URL
    video_duration = Column(Integer, nullable=True)  # 视频时长（秒）

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    project = relationship("Project", back_populates="chapters")
    paragraphs = relationship("Paragraph", back_populates="chapter", cascade="all, delete-orphan")

    # 索引定义
    __table_args__ = (
        Index('idx_chapter_project', 'project_id'),
        Index('idx_chapter_status', 'status'),
        Index('idx_chapter_number', 'chapter_number'),
    )

    def __repr__(self) -> str:
        return f"<Chapter(id={self.id}, title='{self.title[:50]}...', number={self.chapter_number})>"


__all__ = [
    "Chapter",
    "ChapterStatus",
]