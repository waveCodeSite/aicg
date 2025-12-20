"""
电影剧本与角色相关模型 - 统一管理
"""

from enum import Enum
from typing import List, Optional
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Index, JSON, select
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship
from .base import BaseModel

class ScriptStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class MovieScript(BaseModel):
    """电影剧本模型 - 关联到章节"""
    __tablename__ = 'movie_scripts'

    chapter_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('chapters.id'), nullable=False, index=True, comment="章节外键")
    status = Column(String(20), default=ScriptStatus.PENDING, index=True, comment="剧本状态")
    
    # 关系
    chapter = relationship("Chapter")
    scenes = relationship("MovieScene", back_populates="script", cascade="all, delete-orphan", order_by="MovieScene.order_index")

    def __repr__(self) -> str:
        return f"<MovieScript(id={self.id}, chapter_id={self.chapter_id}, status={self.status})>"

class MovieScene(BaseModel):
    """电影场景模型 - 剧本中的一个场景"""
    __tablename__ = 'movie_scenes'

    script_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('movie_scripts.id'), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, comment="场景顺序")
    
    location = Column(String(200), comment="拍摄地点")
    time_of_day = Column(String(50), comment="拍摄时间（如：日、夜、傍晚）")
    atmosphere = Column(String(200), comment="氛围描述")
    description = Column(Text, comment="场景文本描述")
    
    # 关系
    script = relationship("MovieScript", back_populates="scenes")
    shots = relationship("MovieShot", back_populates="scene", cascade="all, delete-orphan", order_by="MovieShot.order_index")

    def __repr__(self) -> str:
        return f"<MovieScene(id={self.id}, script_id={self.script_id}, order={self.order_index}, location={self.location})>"

class MovieShot(BaseModel):
    """电影分镜（镜头）模型 - 场景中的一个镜头"""
    __tablename__ = 'movie_shots'

    scene_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('movie_scenes.id'), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, comment="镜头顺序")
    
    visual_description = Column(Text, nullable=False, comment="画面描述提示词")
    camera_movement = Column(String(200), comment="镜头运动描述")
    dialogue = Column(Text, comment="人物对话内容（如果有）")
    performance_prompt = Column(Text, comment="表演/对话表现提示词（如表情、语气）")
    
    # 生成资源
    first_frame_url = Column(String(500), comment="分镜首帧图URL")
    video_url = Column(String(500), comment="生成的视频URL")
    video_task_id = Column(String(100), comment="Vector Engine 任务ID")
    
    # 关系
    scene = relationship("MovieScene", back_populates="shots")

    def __repr__(self) -> str:
        return f"<MovieShot(id={self.id}, scene_id={self.scene_id}, order={self.order_index})>"

class MovieCharacter(BaseModel):
    """电影角色模型"""
    __tablename__ = 'movie_characters'

    project_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('projects.id'), nullable=False, index=True, comment="项目外键")
    name = Column(String(100), nullable=False, comment="角色名称")
    role_description = Column(Text, comment="角色描述/背景")
    visual_traits = Column(Text, comment="视觉特征描述（用于提示词）")
    dialogue_traits = Column(Text, comment="对话特征描述（语气、口癖等）")
    
    # 资源
    avatar_url = Column(String(500), comment="角色头像URL")
    reference_images = Column(JSON, default=list, comment="参考图URL列表（人物一致性关键）")
    
    # 关系
    project = relationship("Project")

    def __repr__(self) -> str:
        return f"<MovieCharacter(id={self.id}, name={self.name})>"
    
    @classmethod
    async def batch_create(cls, db_session, project_id: str, characters_data: List[dict]):
        """批量创建角色"""
        characters = []
        for data in characters_data:
            char = cls(
                project_id=project_id,
                name=data.get('name'),
                role_description=data.get('role_description'),
                visual_traits=data.get('visual_traits'),
                dialogue_traits=data.get('dialogue_traits'),
                avatar_url=data.get('avatar_url'),
                reference_images=data.get('reference_images', [])
            )
            db_session.add(char)
            characters.append(char)
        await db_session.flush()
        return characters
