"""
视觉身份服务 - 负责角色形象固化（一致性）和场景/首帧图像生成
"""
import asyncio
from typing import List, Optional, Any, Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.core.logging import get_logger
from src.models.movie import MovieCharacter, MovieShot, MovieScene, MovieScript
from src.models.chapter import Chapter
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.utils.storage import get_storage_client
from src.services.image import retry_with_backoff
import uuid
import io
import aiohttp
from fastapi import UploadFile

logger = get_logger(__name__)

class VisualIdentityService(SessionManagedService):
    """
    视觉身份服务
    """

    async def generate_character_references(self, character_id: str, api_key_id: str, prompt_override: Optional[str] = None) -> List[str]:
        """
        为角色生成一致性参考图（三视图/角色卡）
        """
        async with self:
            character = await self.db_session.get(MovieCharacter, character_id)
            if not character: raise ValueError("未找到角色")

            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(character.project.owner_id))
            
            # 使用图像生成 Provider（如 SiliconFlow/OpenAI）
            img_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            # 设计参考图提示词
            base_prompt = f"Character design sheet, {character.name}, {character.visual_traits}, frontal view, profile view, and back view, high quality digital art, consistent features, neutral background."
            final_prompt = prompt_override or base_prompt

            try:
                # 调用图像生成
                logger.info(f"生成角色参考图提示词: {final_prompt}")
                response = await retry_with_backoff(
                    lambda: img_provider.generate_image(
                        prompt=final_prompt,
                        model="flux-pro" # 示例模型
                    )
                )
                
                image_data = response.data[0]
                image_url = image_data.url
                
                # 下载并存储到 MinIO
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(image_url) as resp:
                        if resp.status != 200:
                            raise Exception(f"下载图片失败: {resp.status}")
                        content = await resp.read()

                storage_client = await get_storage_client()
                file_id = str(uuid.uuid4())
                upload_file = UploadFile(
                    filename=f"{file_id}.jpg",
                    file=io.BytesIO(content),
                )
                
                storage_result = await storage_client.upload_file(
                    user_id=str(character.project.owner_id),
                    file=upload_file,
                    metadata={"character_id": str(character.id), "type": "reference"}
                )
                object_key = storage_result["object_key"]

                # 更新角色参考图
                character.reference_images = [object_key]
                await self.db_session.commit()
                return [object_key]
                
            except Exception as e:
                logger.error(f"生成角色参考图失败: {e}")
                raise

    async def generate_shot_first_frame(self, shot_id: str, api_key_id: str, model: Optional[str] = None) -> str:
        """
        为分镜生成首帧图（单机入口，管理自己的 Session）
        """
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id, options=[
                selectinload(MovieShot.scene)
                .selectinload(MovieScene.script)
                .selectinload(MovieScript.chapter)
                .selectinload(Chapter.project)
            ])
            if not shot: raise ValueError("未找到分镜")
            
            # 1. 加载项目角色用于一致性
            project_id = shot.scene.script.chapter.project_id
            user_id = shot.scene.script.chapter.project.owner_id
            stmt = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            chars = (await self.db_session.execute(stmt)).scalars().all()
            
            url = await self._generate_shot_first_frame_impl(shot, chars, user_id, api_key_id, model)
            if url:
                await self.db_session.commit()
            return url

    async def _generate_shot_first_frame_impl(self, shot: MovieShot, chars: List[MovieCharacter], user_id: Any, api_key_id: str, model: Optional[str] = None) -> str:
        """
        内部实现逻辑：不管理 Session，由外部控制 commit()
        """
        # 2. 构建 Prompt
        # 基础描述
        base_prompt = f"{shot.visual_description}. {shot.camera_movement or ''}"
        
        # 寻找提及的角色并注入特征
        character_context = ""
        for char in chars:
            if char.name in shot.visual_description or (shot.dialogue and char.name in shot.dialogue):
                character_context += f" Character {char.name}: {char.visual_traits}."

        final_prompt = f"{base_prompt}. {character_context}. Cinematic movie still, 8k, highly detailed."
        
        # 3. 获取 API Key & Provider
        api_key_service = APIKeyService(self.db_session)
        api_key = await api_key_service.get_api_key_by_id(api_key_id, str(user_id))
        
        img_provider = ProviderFactory.create(
            provider=api_key.provider,
            api_key=api_key.get_api_key(),
            base_url=api_key.base_url
        )

        try:
            # 4. 生成图像
            logger.info(f"生成分镜 {shot.id} 首帧, Prompt: {final_prompt}")
            result = await retry_with_backoff(
                lambda: img_provider.generate_image(
                    prompt=final_prompt,
                    model=model
                )
            )
            
            image_data = result.data[0]
            image_url = image_data.url
            
            # 5. 下载并上传 MinIO
            async with aiohttp.ClientSession() as http_session:
                async with http_session.get(image_url) as resp:
                    if resp.status != 200:
                        raise Exception(f"下载图片失败: {resp.status}")
                    content = await resp.read()

            storage_client = await get_storage_client()
            file_id = str(uuid.uuid4())
            upload_file = UploadFile(
                filename=f"{file_id}.jpg",
                file=io.BytesIO(content),
            )
            
            storage_result = await storage_client.upload_file(
                user_id=str(user_id),
                file=upload_file,
                metadata={"shot_id": str(shot.id)}
            )
            object_key = storage_result["object_key"]

            # 6. 更新数据库 (不在此处 commit，由异步上下文管理或主流程统一 commit)
            shot.first_frame_url = object_key
            logger.info(f"首帧生成并存储完成: shot_id={shot.id}, key={object_key}")
            return object_key
            
        except Exception as e:
            logger.error(f"生成分镜首帧失败 [shot_id={shot.id}]: {e}")
            raise

    async def regenerate_shot_keyframe(self, shot_id: str, api_key_id: str, model: Optional[str] = None) -> str:
        """
        重新生成分镜首帧图(异步任务入口)
        """
        logger.info(f"正在重制分镜首帧: shot_id={shot_id}")
        # 直接复用 generate_shot_first_frame，它已经实现了 Session 管理和 Commit
        url = await self.generate_shot_first_frame(shot_id, api_key_id, model)
        logger.info(f"分镜首帧重制完成: shot_id={shot_id}")
        return url

    async def batch_generate_keyframes(self, script_id: str, api_key_id: str, model: Optional[str] = None) -> dict:
        """
        批量为剧本下的所有分镜生成首帧 (统一 Session 管理)
        """
        async with self:
            script = await self.db_session.get(MovieScript, script_id, options=[
                selectinload(MovieScript.scenes).selectinload(MovieScene.shots)
                .selectinload(MovieShot.scene) # 确保有层级关系
            ])
            if not script: raise ValueError("剧本不存在")
            
            # 加载章节和项目信息以获取 user_id
            stmt_chapter = select(Chapter).where(Chapter.id == script.chapter_id).options(selectinload(Chapter.project))
            chapter = (await self.db_session.execute(stmt_chapter)).scalar_one_or_none()
            if not chapter: raise ValueError("关联章节不存在")
            user_id = chapter.project.owner_id
            project_id = chapter.project_id

            # 一次性加载所有角色
            stmt_chars = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            chars = (await self.db_session.execute(stmt_chars)).scalars().all()

            pending_shots = []
            for scene in script.scenes:
                for shot in scene.shots:
                    if not shot.first_frame_url:
                        pending_shots.append(shot)
            
            if not pending_shots:
                return {"total": 0, "success": 0, "failed": 0, "message": "所有分镜已有首帧"}

            # 并发控制
            semaphore = asyncio.Semaphore(5)
            
            async def task_wrapper(shot_obj):
                async with semaphore:
                    try:
                        # 传入已经加载好的对象和数据，共用 self.db_session
                        await self._generate_shot_first_frame_impl(shot_obj, chars, user_id, api_key_id, model)
                        return (True, None)
                    except Exception as e:
                        return (False, str(e))

            tasks = [task_wrapper(s) for s in pending_shots]
            results = await asyncio.gather(*tasks)
            
            # 统计并统一提交
            success_results = [r for r in results if r[0]]
            fail_messages = [r[1] for r in results if not r[0]]
            
            # 批量提交
            if success_results:
                await self.db_session.commit()
            
            success = len(success_results)
            failed = len(fail_messages)
            
            stats = {
                "total": len(pending_shots),
                "success": success,
                "failed": failed
            }
            if failed > 0:
                stats["message"] = f"部分生成失败 ({failed}/{len(pending_shots)})。详情: {fail_messages[0]}"
                
            return stats

visual_identity_service = VisualIdentityService()
__all__ = ["VisualIdentityService", "visual_identity_service"]
