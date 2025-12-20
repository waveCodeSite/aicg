"""
电影服务 - 负责协调电影生成的各个环节
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.movie import MovieScript, MovieScene, MovieShot, MovieCharacter, ScriptStatus
from src.core.logging import get_logger
from src.services.base import BaseService

logger = get_logger(__name__)

class MovieService(BaseService):
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)

    async def get_script(self, chapter_id: str) -> Optional[MovieScript]:
        """
        获取章节关联的剧本详情
        包含场景和分镜的完整层级结构
        """
        stmt = select(MovieScript).where(MovieScript.chapter_id == chapter_id).where(MovieScript.status == ScriptStatus.COMPLETED).options(
            selectinload(MovieScript.scenes).selectinload(MovieScene.shots)
        )
        
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def get_script_by_id(self, script_id: str) -> Optional[MovieScript]:
        """
        根据ID获取剧本
        """
        stmt = select(MovieScript).where(MovieScript.id == script_id)
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def create_script_task(self, chapter_id: str, api_key_id: str, model: Optional[str] = None):
        """
        创建剧本生成任务
        如果已存在剧本，将其删除以避免重复
        """
        # 查找现有剧本
        stmt = select(MovieScript).where(MovieScript.chapter_id == chapter_id)
        result = await self.db_session.execute(stmt)
        existing_script = result.scalars().first()
        
        if existing_script:
            await self.db_session.delete(existing_script)
            await self.db_session.commit()
            logger.info(f"Deleted existing script {existing_script.id} for chapter {chapter_id}")
        
        from src.tasks.task import movie_generate_script
        task = movie_generate_script.delay(chapter_id, api_key_id, model)
        return task.id

    async def list_characters(self, project_id: str) -> List[MovieCharacter]:
        """
        获取项目下的所有角色
        """
        stmt = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def update_character(self, character_id: str, data: dict) -> Optional[MovieCharacter]:
        """
        更新角色信息
        """
        char = await self.db_session.get(MovieCharacter, character_id)
        if not char:
            return None
            
        if 'avatar_url' in data:
            char.avatar_url = data['avatar_url']
        if 'reference_images' in data:
            char.reference_images = data['reference_images']
            
        await self.db_session.commit()
        await self.db_session.refresh(char)
        return char

