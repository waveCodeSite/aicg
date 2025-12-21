"""
电影制作服务 - 协调视觉生成与 Vector Engine 视频渲染
"""

import asyncio
import base64
import httpx
from typing import Optional, List
from src.core.logging import get_logger
from src.models.movie import MovieShot, MovieScene, MovieScript, MovieCharacter
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.services.visual_identity_service import visual_identity_service
from src.services.dialogue_prompt_engine import dialogue_prompt_engine
from src.utils.storage import storage_client
from datetime import timedelta

logger = get_logger(__name__)

class MovieProductionService(SessionManagedService):
    """
    电影生产协调服务
    """
    
    async def _to_base64(self, image_url: str) -> str:
        """
        获取图片并转换为 Base64
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_url, timeout=30.0)
                resp.raise_for_status()
                encoded = base64.b64encode(resp.content).decode('utf-8')
                return f"data:image/png;base64,{encoded}"
        except Exception as e:
            logger.error(f"Failed to convert image to base64: {e}")
            return image_url # 兜底返回原 URL

    async def _polish_prompt_to_english(self, api_key_id: str, owner_id: str, visual_desc: str, camera_movement: Optional[str] = None, performance_prompt: Optional[str] = None) -> str:
        """
        将中文描述转换为高质量的英文视频提示词
        """
        api_key_service = APIKeyService(self.db_session)
        api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
        
        llm_provider = ProviderFactory.create(
            provider=api_key.provider,
            api_key=api_key.get_api_key(),
            base_url=api_key.base_url
        )

        system_prompt = "You are a professional AI video prompt engineer. Translate and polish the given scene description into a high-quality, detailed English prompt for video generation. Avoid outputting anything other than the prompt itself."
        user_content = f"Visual Description: {visual_desc}\nCamera Movement: {camera_movement or 'None'}\nPerformance/Action: {performance_prompt or 'None'}"
        
        try:
            response = await llm_provider.completions(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Prompt polishing failed: {e}")
            # 回退：简单合并（虽然非英文效果较差，但保证流程通畅）
            return f"{visual_desc}. {camera_movement or ''}. {performance_prompt or ''}"

    async def produce_shot_video(self, shot_id: str, api_key_id: str, model: str = "veo_3_1-fast", force: bool = False) -> str:
        """
        生产单个镜头的视频
        """
        if not api_key_id:
            raise ValueError("必须提供 api_key_id")
            
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id)
            if not shot: raise ValueError("分镜不存在")
            
            # 1. 强制依赖检查：必须有首帧
            if not shot.first_frame_url:
                raise ValueError(f"分镜 {shot_id} 缺少首帧图，请先生成首帧")

            # 已经生成过且不强制重制，则返回
            if shot.video_url and not force:
                return shot.video_task_id or "completed"

            # 2. 准备对话表现 (如果需要)
            if shot.dialogue and not shot.performance_prompt:
                await dialogue_prompt_engine.design_performance_prompt(shot_id, None, api_key_id)
                await self.db_session.refresh(shot)

            # 3. 收集项目信息和角色一致性参考图 (使用 joinedload 避免异步环境下的 lazy load 异常)
            from src.models.chapter import Chapter
            from src.models.project import Project
            from sqlalchemy import select
            from sqlalchemy.orm import joinedload
            
            stmt = select(Chapter).join(MovieScript).join(MovieScene).where(MovieScene.id == shot.scene_id).options(joinedload(Chapter.project))
            result = await self.db_session.execute(stmt)
            chapter = result.scalars().first()
            if not chapter: raise ValueError("无法找到分镜关联的章节")
            
            project_id = chapter.project_id
            owner_id = str(chapter.project.owner_id) if chapter.project else None
            if not owner_id:
                 # 兜底查询 owner_id
                 from src.models.project import Project
                 project = await self.db_session.get(Project, project_id)
                 owner_id = str(project.owner_id)

            stmt_chars = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            all_chars = (await self.db_session.execute(stmt_chars)).scalars().all()
            
            ref_images = []
            for char in all_chars:
                # 检查角色是否在描述中被提及，或者通过对话关联
                if char.name in shot.visual_description:
                    if not char.avatar_url:
                        raise ValueError(f"角色 {char.name} 缺少形象，请先生成角色形象")
                    ref_images.append(char.avatar_url)
                    if char.reference_images:
                        ref_images.extend(char.reference_images)
            
            ref_images = list(dict.fromkeys(ref_images))[:3]

            # 4. 生成英文提示词并保存
            final_english_prompt = await self._polish_prompt_to_english(
                api_key_id, owner_id, 
                shot.visual_description, 
                shot.camera_movement, 
                shot.performance_prompt
            )
            shot.video_prompt = final_english_prompt

            # 5. 提交到 Vector Engine
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)

            vector_provider = ProviderFactory.create(
                provider="vectorengine",
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            # 预签名图片 URL
            all_raw_images = [shot.first_frame_url]
            all_raw_images.extend(ref_images)
            
            logger.info(f"准备提交视频生成: shot_id={shot_id}, refs={len(ref_images)}")
            
            all_signed_images = []
            for img in all_raw_images:
                if img and not img.startswith("http"):
                    all_signed_images.append(storage_client.get_presigned_url(img, timedelta(hours=24)))
                else:
                    all_signed_images.append(img)

            # 转换为 Base64 (用户要求)
            logger.info(f"转换图片为 Base64...")
            all_base64_images = await asyncio.gather(*[self._to_base64(url) for url in all_signed_images])

            try:
                shot.status = "processing"
                await self.db_session.flush()

                logger.info(f"正在调用 Vector Provider: model={model}, images={len(all_base64_images)}")
                task_resp = await vector_provider.create_video( # type: ignore
                    prompt=final_english_prompt,
                    images=all_base64_images,
                    model=model,
                    use_character_ref=True if ref_images else False
                )
                
                shot.video_task_id = task_resp.get("id")
                logger.info(f"Vector Engine 已返回任务 ID: {shot.video_task_id}")
                await self.db_session.commit()
                return shot.video_task_id # type: ignore
                
            except Exception as e:
                shot.status = "failed"
                await self.db_session.commit()
                logger.error(f"提交 Vector Engine 失败 [shot_id={shot_id}]: {e}")
                raise

    async def batch_produce_shot_videos(self, script_id: str, api_key_id: str, model: str = "veo_3_1-fast") -> dict:
        """
        批量生产剧本下的分镜视频
        """
        if not api_key_id:
            raise ValueError("必须提供 api_key_id")

        async with self:
            from sqlalchemy.orm import selectinload
            script = await self.db_session.get(MovieScript, script_id, options=[
                selectinload(MovieScript.scenes).selectinload(MovieScene.shots)
            ])
            if not script: raise ValueError("剧本不存在")
            
            pending_shots = []
            for scene in script.scenes:
                for shot in scene.shots:
                    # 只有具备首帧且尚未生产（或生产失败）的才加入队列
                    if shot.first_frame_url and (not shot.video_url or shot.status == "failed"):
                        pending_shots.append(str(shot.id))
            
            if not pending_shots:
                return {"total": 0, "message": "没有符合生产条件的分镜（需先有首帧）"}

            # 这里由于涉及外部 API 调用和 LLM 翻译，不建议太高并发，限制为 3
            semaphore = asyncio.Semaphore(3)
            
            async def task_wrapper(sid):
                async with semaphore:
                    try:
                        from src.services.movie_production import MovieProductionService
                        async with MovieProductionService() as svc:
                            await svc.produce_shot_video(sid, api_key_id, model)
                        return (True, None)
                    except Exception as e:
                        return (False, str(e))

            tasks = [task_wrapper(sid) for sid in pending_shots]
            results = await asyncio.gather(*tasks)
            
            success = len([r for r in results if r[0]])
            failed = len([r for r in results if not r[0]])
            
            return {
                "total": len(pending_shots),
                "success": success,
                "failed": failed,
                "message": f"批量生产已启动: 成功 {success}, 失败 {failed}"
            }

    async def poll_shot_status(self, shot_id: str, api_key_id: str) -> str:
        """
        轮询并更新镜头状态
        """
        async with self:
            from src.models.chapter import Chapter
            from sqlalchemy import select
            
            shot = await self.db_session.get(MovieShot, shot_id)
            if not shot or not shot.video_task_id: return "no_task"
            
            if shot.status == "completed": return "completed"

            # 获取 API Key 所需的 owner_id
            stmt = select(Chapter).join(MovieScript).join(MovieScene).where(MovieScene.id == shot.scene_id)
            result = await self.db_session.execute(stmt)
            chapter = result.scalars().first()
            owner_id = str(chapter.project.owner_id)

            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
            
            vector_provider = ProviderFactory.create(
                provider="vectorengine", 
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )
            
            status_resp = await vector_provider.get_task_status(shot.video_task_id) # type: ignore
            status = status_resp.get("status") # pending, processing, completed, failed
            
            if status == "completed":
                content_resp = await vector_provider.get_video_content(shot.video_task_id) # type: ignore
                shot.video_url = content_resp.get("video_url")
                shot.status = "completed"
                await self.db_session.commit()
            elif status == "failed":
                shot.status = "failed"
                await self.db_session.commit()
            
            return status # type: ignore

movie_production_service = MovieProductionService()
__all__ = ["MovieProductionService", "movie_production_service"]
