"""
电影制作服务 - 协调视觉生成与 Vector Engine 视频渲染
"""

import asyncio
from typing import Optional, List
from src.core.logging import get_logger
from src.models.movie import MovieShot, MovieScene, MovieScript, MovieCharacter
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.services.visual_identity_service import visual_identity_service
from src.services.dialogue_prompt_engine import dialogue_prompt_engine

logger = get_logger(__name__)

class MovieProductionService(SessionManagedService):
    """
    电影生产协调服务
    """

    async def produce_shot_video(self, shot_id: str, api_key_id: str, model: str = "veo3.1-fast") -> str:
        """
        全流程生产单个镜头的视频：
        1. (可选) 生成/更新首帧图
        2. (可选) 生成对话表现提示词
        3. 提交 Vector Engine 任务
        """
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id)
            if not shot: raise ValueError("分镜不存在")
            
            # TODO: 关联角色逻辑 - 暂时简化
            # character_id = ...
            
            # 1. 确保有首帧
            if not shot.first_frame_url:
                await visual_identity_service.generate_shot_first_frame(shot_id, api_key_id)
                await self.db_session.refresh(shot)

            # 2. 确保有对话表现
            if shot.dialogue and not shot.performance_prompt:
                await dialogue_prompt_engine.design_performance_prompt(shot_id, None, api_key_id)
                await self.db_session.refresh(shot)

            # 3. 提交到 Vector Engine
            from src.models.chapter import Chapter
            from sqlalchemy import select
            stmt = select(Chapter).join(MovieScript).join(MovieScene).where(MovieScene.id == shot.scene_id)
            chapter = (await self.db_session.execute(stmt)).scalars().first()
            
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(chapter.project.owner_id))

            # 使用 Factory 创建 Vector Engine Provider
            # 注意：在 ProviderFactory 中我们需要确保返回的是 VectorEngineProvider 实例
            vector_provider = ProviderFactory.create(
                provider="vectorengine",
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            # 综合 Prompt
            final_prompt = f"{shot.visual_description}. {shot.camera_movement or ''}. {shot.performance_prompt or ''}"
            
            try:
                task_resp = await vector_provider.create_video( # type: ignore
                    prompt=final_prompt,
                    images=[shot.first_frame_url],
                    model=model
                )
                
                shot.video_task_id = task_resp.get("id")
                await self.db_session.commit()
                return shot.video_task_id # type: ignore
                
            except Exception as e:
                logger.error(f"提交 Vector Engine 失败: {e}")
                raise

    async def poll_shot_status(self, shot_id: str, api_key_id: str) -> str:
        """
        轮询并更新镜头状态
        """
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id)
            if not shot or not shot.video_task_id: return "no_task"
            
            # 获取 API Key 逻辑简化同上...
            api_key_service = APIKeyService(self.db_session)
            # ...
            
            # 模拟获取到 API KEY
            vector_provider = ProviderFactory.create(provider="vectorengine", api_key="TODO")
            
            status_resp = await vector_provider.get_task_status(shot.video_task_id) # type: ignore
            status = status_resp.get("status")
            
            if status == "completed":
                content_resp = await vector_provider.get_video_content(shot.video_task_id) # type: ignore
                shot.video_url = content_resp.get("video_url")
                await self.db_session.commit()
            
            return status # type: ignore

movie_production_service = MovieProductionService()
__all__ = ["MovieProductionService", "movie_production_service"]
