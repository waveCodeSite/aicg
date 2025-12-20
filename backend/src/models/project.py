"""
项目数据模型 - 按照data-model.md规范实现
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from src.models.base import BaseModel


class ProjectStatus(str, Enum):
    """项目状态枚举 - 按照data-model.md规范"""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProjectType(str, Enum):
    """项目类型枚举"""
    PICTURE_NARRATIVE = "picture_narrative"  # 图解说/视频解说
    AI_MOVIE = "ai_movie"                    # AI电影


class Project(BaseModel):
    """项目模型 - 按照data-model.md规范实现"""
    __tablename__ = 'projects'

    # 基础字段 - 按照data-model.md规范
    owner_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False, index=True, comment="外键索引，无约束")  # 外键索引，无约束
    title = Column(String(200), nullable=False, comment="项目标题")
    description = Column(Text, nullable=True, comment="项目描述")
    type = Column(String(20), default=ProjectType.PICTURE_NARRATIVE, index=True, comment="项目类型")

    # 文件信息 - 按照data-model.md规范
    file_name = Column(String(255), nullable=False, comment="文件名称")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    file_type = Column(String(10), nullable=False, comment="文件类型: txt, md, docx, epub")
    file_path = Column(String(500), nullable=False, comment="MinIO存储路径")
    file_hash = Column(String(64), nullable=True, index=True, comment="文件MD5哈希")

    # 统计信息 - 按照data-model.md规范
    word_count = Column(Integer, default=0, comment="字数统计")
    chapter_count = Column(Integer, default=0, comment="章节数量")
    paragraph_count = Column(Integer, default=0, comment="段落数量")
    sentence_count = Column(Integer, default=0, comment="句子数量")

    # 处理状态 - 按照data-model.md规范
    status = Column(String(20), default=ProjectStatus.UPLOADED, index=True, comment="处理状态")
    processing_progress = Column(Integer, default=0, comment="0-100处理进度")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 关系定义 - 按照data-model.md规范
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan")
    # generation_tasks = relationship("GenerationTask", back_populates="project", cascade="all, delete-orphan")

    # 索引定义 - 按照data-model.md规范
    __table_args__ = (
        Index('idx_project_owner', 'owner_id'),
        Index('idx_project_status', 'status'),
        Index('idx_project_created', 'created_at'),
        Index('idx_project_file_hash', 'file_hash'),
    )

    
    def update_processing_progress(self, progress: int) -> None:
        """更新处理进度 - 按照data-model.md规范"""
        self.processing_progress = max(0, min(100, progress))

    def mark_as_failed(self, error_message: str) -> None:
        """标记为处理失败 - 按照data-model.md规范"""
        self.status = ProjectStatus.FAILED
        self.error_message = error_message
        self.processing_progress = 0

    def mark_as_completed(self) -> None:
        """标记为处理完成 - 按照data-model.md规范"""
        self.status = ProjectStatus.COMPLETED
        self.processing_progress = 100
        self.error_message = None

    def can_be_processed(self) -> bool:
        """检查是否可以进行处理 - 按照data-model.md规范"""
        return (
                self.status in [ProjectStatus.UPLOADED, ProjectStatus.FAILED] and
                self.file_path and self.file_type in ["txt", "md", "docx", "epub"]
        )

    def is_archived(self) -> bool:
        """检查项目是否已归档 - 按照data-model.md规范"""
        return self.status == ProjectStatus.ARCHIVED

    def archive_project(self) -> None:
        """归档项目（不可逆操作）- 按照data-model.md规范"""
        self.status = ProjectStatus.ARCHIVED
        self.processing_progress = 0
        # 注意：这里需要与任务队列集成来停止正在进行的任务

    @classmethod
    async def get_by_owner_id(cls, db_session, owner_id: str):
        """获取用户的项目列表 - 按照data-model.md规范"""
        from sqlalchemy import select

        result = await db_session.execute(
            select(cls).filter(cls.owner_id == owner_id).order_by(cls.created_at.desc())
        )
        return result.scalars().all()

    @classmethod
    async def get_by_id_and_owner(cls, db_session, project_id: str, owner_id: str):
        """根据ID和用户获取项目 - 按照data-model.md规范"""
        from sqlalchemy import select

        result = await db_session.execute(
            select(cls).filter(
                cls.id == project_id,
                cls.owner_id == owner_id
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def create_project(cls, db_session, owner_id: str, title: str,
                             description: str = None, file_name: str = None,
                             file_size: int = 0, file_type: str = "txt",
                             file_path: str = "", file_hash: str = None,
                             project_type: ProjectType = ProjectType.PICTURE_NARRATIVE):
        """创建新项目 - 按照data-model.md规范"""
        project = cls(
            owner_id=owner_id,
            title=title,
            description=description,
            file_name=file_name or f"project_{title}",
            file_size=file_size,
            file_type=file_type,
            file_path=file_path,
            file_hash=file_hash,
            type=project_type,
            status=ProjectStatus.UPLOADED
        )
        db_session.add(project)
        # 注意：不在这里提交，让调用方控制事务
        await db_session.flush()
        await db_session.refresh(project)
        return project


__all__ = [
    "Project",
    "ProjectStatus",
    "ProjectType",
]
