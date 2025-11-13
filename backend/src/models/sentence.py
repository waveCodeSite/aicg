"""
句子模型 - 最小视频生成单元
严格按照data-model.md规范实现
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base

if TYPE_CHECKING:
    pass


class SentenceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Sentence(Base):
    """句子模型 - 最小视频生成单元"""
    __tablename__ = 'sentences'

    # 基础字段
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    paragraph_id = Column(String, nullable=False, index=True)  # 外键索引，无约束
    content = Column(Text, nullable=False)

    # 结构信息
    order_index = Column(Integer, nullable=False)  # 在段落中的顺序
    word_count = Column(Integer, default=0)
    character_count = Column(Integer, default=0)

    # 生成资源
    image_url = Column(String(500), nullable=True)  # 生成的图片URL
    image_prompt = Column(Text, nullable=True)  # 图片生成提示词
    audio_url = Column(String(500), nullable=True)  # 生成的音频URL

    # 时间轴信息（来自ASR）
    start_time = Column(Float, nullable=True)  # 音频开始时间（秒）
    end_time = Column(Float, nullable=True)  # 音频结束时间（秒）
    duration = Column(Float, nullable=True)  # 音频时长（秒）
    confidence_score = Column(Float, nullable=True)  # ASR置信度

    # 语音设置
    voice_settings = Column(Text, nullable=True)  # JSON格式的语音合成参数
    voice_type = Column(String(50), nullable=True)
    speech_rate = Column(Float, default=1.0)
    pitch = Column(Float, default=1.0)
    volume = Column(Float, default=1.0)

    # 处理状态
    status = Column(String(20), default=SentenceStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # 用户编辑
    edited_content = Column(Text, nullable=True)
    edited_prompt = Column(Text, nullable=True)
    is_manual_edited = Column(Boolean, default=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

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


__all__ = [
    "Sentence",
    "SentenceStatus",
]
