"""
视觉身份服务 - 负责角色形象固化（一致性）和场景/首帧图像生成
"""
import asyncio
import uuid
import io
import aiohttp
from typing import List, Optional, Any, Dict
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from fastapi import UploadFile

from src.core.logging import get_logger
from src.models.movie import MovieCharacter, MovieShot, MovieScene, MovieScript
from src.models.chapter import Chapter
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.utils.storage import get_storage_client
from src.services.image import retry_with_backoff

logger = get_logger(__name__)

# ============================================================
# 独立 Worker 函数 (参照 image.py 规范)
# ============================================================

async def _generate_one_frame_worker(
    shot: MovieShot,
    chars: List[MovieCharacter],
    user_id: Any,
    api_key,
    frame_type: str,
    model: Optional[str],
    semaphore: asyncio.Semaphore,
    storage_client,
    ref_images: List[str] = None
):
    """
    单个分镜单帧生成的 Worker - 负责生成、下载、上传，不负责 Commit
    包含角色参考图以确保人物一致性
    """
    async with semaphore:
        try:
            # 1. 构建 Prompt (包含角色信息)
            # 分析镜头运动以生成更流畅的起始帧提示词
            camera_move = (shot.camera_movement or "").lower()
            visual_desc = shot.visual_description
            
            if frame_type == "first":
                if "pan" in camera_move:
                    variation = "Start of the pan shot, framing the initial composition"
                elif "zoom in" in camera_move:
                    variation = "Wide shot, establishing context before the zoom"
                elif "zoom out" in camera_move:
                    variation = "Close-up shot, detail view before zooming out"
                else:
                    variation = "Cinematic establishing shot, start of action"
            else:
                if "pan" in camera_move:
                    variation = "End of the pan shot, revealing the new composition, continuous lighting"
                elif "zoom in" in camera_move:
                    variation = "Close-up shot, result of the zoom in, focused details"
                elif "zoom out" in camera_move:
                    variation = "Wide shot, result of the zoom out, revealing surroundings"
                else:
                    variation = "End of action, evolved state, consistent lighting and atmosphere with start"

            base_prompt = f"{visual_desc}. {shot.camera_movement or ''}. {variation}."
            
            character_context = ""
            for char in chars:
                if char.name in shot.visual_description or (shot.dialogue and char.name in shot.dialogue):
                    character_context += f" Character {char.name}: {char.visual_traits}."

            # 如果有角色参考图，强调一致性
            if ref_images:
                character_context += " IMPORTANT: Maintain strict visual consistency with the provided character reference images. Ensure same face, clothing, and body type."

            final_prompt = f"{base_prompt}. {character_context}. Cinematic movie still, 8k, highly detailed, photorealistic, dramatic lighting."
            
            # 2. Provider 调用 (包含参考图)
            img_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            logger.info(f"生成分镜 {shot.id} {frame_type} 帧, Prompt: {final_prompt}, Refs: {len(ref_images or [])}")
            
            # 准备生成参数
            gen_params = {
                "prompt": final_prompt,
                "model": model
            }
            
            # 某些 provider 支持参考图 (如 SiliconFlow)
            # 这里简化处理，实际可能需要根据 provider 类型调整
            if ref_images and hasattr(img_provider, 'generate_image_with_references'):
                gen_params["reference_images"] = ref_images
            
            result = await retry_with_backoff(
                lambda: img_provider.generate_image(**gen_params)
            )
            
            image_data = result.data[0]
            
            # 3. 获取图片内容 (URL 或 Base64)
            if image_data.b64_json:
                content = base64.b64decode(image_data.b64_json)
            elif image_data.url:
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(image_data.url) as resp:
                        if resp.status != 200:
                            raise Exception(f"下载图片失败: {resp.status}")
                        content = await resp.read()
            else:
                raise Exception("Provider 返回了空的图片数据")

            # 4. 上传存储
            file_id = str(uuid.uuid4())
            upload_file = UploadFile(
                filename=f"{file_id}_{frame_type}.jpg",
                file=io.BytesIO(content),
            )
            
            storage_result = await storage_client.upload_file(
                user_id=str(user_id),
                file=upload_file,
                metadata={"shot_id": str(shot.id), "frame_type": frame_type}
            )
            object_key = storage_result["object_key"]

            # 5. 更新对象属性 (不 Commit)
            if frame_type == "first":
                shot.first_frame_url = object_key
                shot.first_frame_prompt = final_prompt
            else:
                shot.last_frame_url = object_key
                shot.last_frame_prompt = final_prompt
                
            logger.info(f"{frame_type} 帧生成并存储完成: shot_id={shot.id}, key={object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Worker 生成单帧失败 [shot_id={shot.id}]: {e}")
            return False


class VisualIdentityService(SessionManagedService):
    """
    视觉身份服务
    """

    async def generate_character_references(self, character_id: str, api_key_id: str, prompt_override: Optional[str] = None) -> List[str]:
        """
        为角色生成一致性参考图 (单条任务)
        """
        async with self:
            character = await self.db_session.get(MovieCharacter, character_id, options=[joinedload(MovieCharacter.project)])
            if not character: raise ValueError("未找到角色")

            owner_id = str(character.project.owner_id)
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
            
            img_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            base_prompt = f"Character design sheet, {character.name}, {character.visual_traits}, frontal view, profile view, and back view, high quality digital art, consistent features, neutral background."
            final_prompt = prompt_override or base_prompt

            try:
                response = await retry_with_backoff(
                    lambda: img_provider.generate_image(
                        prompt=final_prompt,
                        model="flux-pro"
                    )
                )
                
                image_url = response.data[0].url
                
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(image_url) as resp:
                        if resp.status != 200: raise Exception(f"下载失败: {resp.status}")
                        content = await resp.read()

                storage_client = await get_storage_client()
                file_id = str(uuid.uuid4())
                upload_file = UploadFile(
                    filename=f"{file_id}.jpg",
                    file=io.BytesIO(content),
                )
                
                storage_result = await storage_client.upload_file(
                    user_id=owner_id,
                    file=upload_file,
                    metadata={"character_id": str(character.id), "type": "reference"}
                )
                object_key = storage_result["object_key"]

                character.reference_images = [object_key]
                await self.db_session.commit()
                return [object_key]
                
            except Exception as e:
                logger.error(f"生成角色参考图失败: {e}")
                raise

    async def generate_shot_first_frame(self, shot_id: str, api_key_id: str, model: Optional[str] = None) -> str:
        """为分镜生成首帧图"""
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id, options=[
                joinedload(MovieShot.scene).joinedload(MovieScene.script).joinedload(MovieScript.chapter).joinedload(Chapter.project)
            ])
            if not shot: raise ValueError("未找到分镜")
            
            project_id = shot.scene.script.chapter.project_id
            user_id = shot.scene.script.chapter.project.owner_id
            
            stmt = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            chars = (await self.db_session.execute(stmt)).scalars().all()
            
            # 收集角色参考图
            ref_images = []
            for char in chars:
                if char.name in shot.visual_description or (shot.dialogue and char.name in shot.dialogue):
                    if char.avatar_url:
                        ref_images.append(char.avatar_url)
                    if char.reference_images:
                        ref_images.extend(char.reference_images)
            ref_images = list(dict.fromkeys(ref_images))[:3]  # 去重并限制数量
            
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(user_id))
            
            storage_client = await get_storage_client()
            semaphore = asyncio.Semaphore(1)
            
            success = await _generate_one_frame_worker(shot, chars, user_id, api_key, "first", model, semaphore, storage_client, ref_images)
            if success:
                await self.db_session.commit()
                return shot.first_frame_url # type: ignore
            else:
                raise Exception("生成分镜首帧失败")

    async def generate_shot_last_frame(self, shot_id: str, api_key_id: str, model: Optional[str] = None) -> str:
        """为分镜生成尾帧图"""
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id, options=[
                joinedload(MovieShot.scene).joinedload(MovieScene.script).joinedload(MovieScript.chapter).joinedload(Chapter.project)
            ])
            if not shot: raise ValueError("未找到分镜")
            
            project_id = shot.scene.script.chapter.project_id
            user_id = shot.scene.script.chapter.project.owner_id
            
            stmt = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            chars = (await self.db_session.execute(stmt)).scalars().all()
            
            # 收集角色参考图
            ref_images = []
            for char in chars:
                if char.name in shot.visual_description or (shot.dialogue and char.name in shot.dialogue):
                    if char.avatar_url:
                        ref_images.append(char.avatar_url)
                    if char.reference_images:
                        ref_images.extend(char.reference_images)
            ref_images = list(dict.fromkeys(ref_images))[:3]  # 去重并限制数量
            
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(user_id))
            
            storage_client = await get_storage_client()
            semaphore = asyncio.Semaphore(1)
            
            success = await _generate_one_frame_worker(shot, chars, user_id, api_key, "last", model, semaphore, storage_client, ref_images)
            if success:
                await self.db_session.commit()
                return shot.last_frame_url # type: ignore
            else:
                raise Exception("生成分镜尾帧失败")

    async def regenerate_shot_keyframe(self, shot_id: str, api_key_id: str, model: Optional[str] = None) -> str:
        """重新生成分镜首帧图(异步任务入口)"""
        return await self.generate_shot_first_frame(shot_id, api_key_id, model)

    async def batch_generate_keyframes(self, script_id: str, api_key_id: str, model: Optional[str] = None) -> dict:
        """
        批量为剧本下的所有分镜生成首帧 (参考 image.py)
        """
        async with self:
            # 1. 深度加载
            script = await self.db_session.get(MovieScript, script_id, options=[
                selectinload(MovieScript.scenes).selectinload(MovieScene.shots),
                joinedload(MovieScript.chapter).joinedload(Chapter.project)
            ])
            if not script: raise ValueError("剧本不存在")
            
            project_id = script.chapter.project_id
            user_id = script.chapter.project.owner_id
            
            # 2. 预加载角色
            stmt_chars = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            chars = (await self.db_session.execute(stmt_chars)).scalars().all()

            # 3. 准备资源
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(user_id))
            storage_client = await get_storage_client()

            # 4. 筛选待处理任务
            tasks = []
            semaphore = asyncio.Semaphore(5)
            
            for scene in script.scenes:
                for shot in scene.shots:
                    # 检查是否需要生成首帧
                    if not shot.first_frame_url:
                        # 收集角色参考图
                        ref_images = []
                        for char in chars:
                            if char.name in shot.visual_description or (shot.dialogue and char.name in shot.dialogue):
                                if char.avatar_url:
                                    ref_images.append(char.avatar_url)
                                if char.reference_images:
                                    ref_images.extend(char.reference_images)
                        ref_images = list(dict.fromkeys(ref_images))[:3]
                        
                        tasks.append(
                            _generate_one_frame_worker(shot, chars, user_id, api_key, "first", model, semaphore, storage_client, ref_images)
                        )
                    
                    # 检查是否需要生成尾帧
                    if not shot.last_frame_url:
                        # 重复收集参考图逻辑 (也可以提取为 helper)
                        ref_images = []
                        for char in chars:
                            if char.name in shot.visual_description or (shot.dialogue and char.name in shot.dialogue):
                                if char.avatar_url:
                                    ref_images.append(char.avatar_url)
                                if char.reference_images:
                                    ref_images.extend(char.reference_images)
                        ref_images = list(dict.fromkeys(ref_images))[:3]
                        
                        tasks.append(
                            _generate_one_frame_worker(shot, chars, user_id, api_key, "last", model, semaphore, storage_client, ref_images)
                        )
            
            if not tasks:
                return {"total": 0, "success": 0, "failed": 0, "message": "所有分镜已有首尾帧"}

            # 6. 执行并发
            results = await asyncio.gather(*tasks)
            
            success_count = sum(1 for r in results if r)
            failed_count = len(results) - success_count
            
            # 7. 提交
            await self.db_session.commit()
            
            return {
                "total": len(tasks),
                "success": success_count,
                "failed": failed_count,
                "message": f"批量生成完成: 成功 {success_count}, 失败 {failed_count}"
            }

visual_identity_service = VisualIdentityService()
__all__ = ["VisualIdentityService", "visual_identity_service"]
