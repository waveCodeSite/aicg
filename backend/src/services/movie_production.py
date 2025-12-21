"""
电影制作服务 - 协调视觉生成与 Vector Engine 视频渲染
"""

import asyncio
import base64
import httpx
import uuid
import io
from typing import Optional, List, Any
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from fastapi import UploadFile

from src.core.logging import get_logger
from src.models.movie import MovieShot, MovieScene, MovieScript, MovieCharacter
from src.models.chapter import Chapter
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.services.visual_identity_service import visual_identity_service
from src.services.dialogue_prompt_engine import dialogue_prompt_engine
from src.utils.storage import storage_client
from datetime import timedelta

logger = get_logger(__name__)

# ============================================================
# 独立 Worker 函数 (参照 image.py 规范)
# ============================================================

async def _sync_one_shot_worker(
    shot: MovieShot,
    api_key,
    semaphore: asyncio.Semaphore
):
    """
    单个镜头的同步 Worker - 不负责数据库 IO，只负责状态查询和内存更新
    """
    async with semaphore:
        try:
            vector_provider = ProviderFactory.create(
                provider="vectorengine", 
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )
            
            status_resp = await vector_provider.get_task_status(shot.video_task_id) # type: ignore
            logger.info(f"Worker 同步状态 [shot_id={shot.id}]: {status_resp}")
            status = status_resp.get("status")
            
            if status == "completed":
                video_url = status_resp.get("video_url")
                if video_url:
                    logger.info(f"下载视频: {video_url}")
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        resp = await client.get(video_url)
                        resp.raise_for_status()
                        video_data = resp.content
                    
                    # 上传到 MinIO
                    file_id = str(uuid.uuid4())
                    owner_id = str(shot.scene.script.chapter.project.owner_id)
                    
                    upload_file = UploadFile(
                        filename=f"{file_id}.mp4",
                        file=io.BytesIO(video_data),
                    )
                    
                    storage_result = await storage_client.upload_file(
                        user_id=owner_id,
                        file=upload_file,
                        metadata={"shot_id": str(shot.id), "type": "video"}
                    )
                    shot.video_url = storage_result["object_key"]
                    shot.status = "completed"
                    shot.last_error = None
                    logger.info(f"视频同步并存储完成: shot_id={shot.id}, key={shot.video_url}")
                else:
                    shot.status = "failed"
                    shot.last_error = "Vector Engine 返回的任务已完成但缺少视频链接"
            elif status == "failed":
                shot.status = "failed"
                shot.last_error = status_resp.get("error") or "Vector Engine 任务失败"
            
            return True
        except Exception as e:
            logger.error(f"Worker 同步异常 [shot_id={shot.id}]: {e}")
            if "not found" in str(e).lower():
                shot.status = "failed"
                shot.last_error = "任务不存在"
            return False

async def _produce_one_shot_worker(
    shot: MovieShot,
    owner_id: str,
    api_key,
    ref_images: List[str],
    model: str,
    semaphore: asyncio.Semaphore,
    llm_provider,
    service_instance
):
    """
    单个镜头的生产 Worker
    """
    async with semaphore:
        try:
            # 1. 生成提示词 (如果需要)
            if not shot.video_prompt:
                shot.video_prompt = await service_instance._polish_prompt_to_english_with_provider(
                    llm_provider,
                    shot.visual_description,
                    shot.camera_movement,
                    shot.performance_prompt,
                    shot.dialogue
                )

            # 2. 预签名图片 URL (首帧 + 尾帧 + 角色参考)
            all_raw_images = [shot.first_frame_url]
            if shot.last_frame_url:
                all_raw_images.append(shot.last_frame_url)
                
            # 角色参考图
            # all_raw_images.extend(ref_images)
            
            all_signed_images = []
            for img in all_raw_images:
                if img and not img.startswith("http"):
                    all_signed_images.append(storage_client.get_presigned_url(img, timedelta(hours=24)))
                else:
                    all_signed_images.append(img)

            # 3. 转换为 Base64
            all_base64_images = await asyncio.gather(*[service_instance._to_base64(url) for url in all_signed_images])

            # 4. 提交到 Vector Engine
            vector_provider = ProviderFactory.create(
                provider="vectorengine",
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            shot.status = "processing"
            task_resp = await vector_provider.create_video( # type: ignore
                prompt=shot.video_prompt,
                images=all_base64_images,
                model=model,
                use_character_ref=True if ref_images else False
            )
            
            shot.video_task_id = task_resp.get("id")
            shot.last_error = None
            return True
        except Exception as e:
            logger.error(f"Worker 生产异常 [shot_id={shot.id}]: {e}")
            shot.status = "failed"
            shot.last_error = str(e)
            return False


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
            return image_url

    async def _polish_prompt_to_english_with_provider(self, llm_provider, visual_desc: str, camera_movement: Optional[str] = None, performance_prompt: Optional[str] = None, dialogue: Optional[str] = None) -> str:
        """
        内部逻辑：使用已创建的 Provider 优化提示词
        """
        system_prompt = (
            "You are a professional AI video prompt engineer. Translate and polish the given scene description into a high-quality, detailed English prompt for video generation.\n"
            "CRITICAL: If 'Dialogue' is provided, you MUST append a specific instruction at the end of the prompt to render bilingual subtitles at the bottom of the video.\n"
            "The subtitle format should be: '[Chinese Dialogue] / [English Translation]'.\n"
            "Avoid outputting anything other than the prompt itself."
        )
        user_content = f"Visual Description: {visual_desc}\nCamera Movement: {camera_movement or 'None'}\nPerformance/Action: {performance_prompt or 'None'}\nDialogue: {dialogue or 'None'}"
        
        try:
            logger.info("创建提示词，调用 LLM Provider")
            response = await llm_provider.completions(
                model="gemini-3-flash-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
            )
            polished_prompt = response.choices[0].message.content.strip()
            
            if dialogue and "subtitles" not in polished_prompt.lower():
                polished_prompt += f" Display bilingual subtitles at the bottom: '{dialogue} / [Translation]'"
                
            return polished_prompt
        except Exception as e:
            logger.error(f"Prompt polishing failed: {e}")
            return f"{visual_desc}. {camera_movement or ''}. {performance_prompt or ''}"

    async def _polish_prompt_to_english(self, api_key_id: str, owner_id: str, visual_desc: str, camera_movement: Optional[str] = None, performance_prompt: Optional[str] = None, dialogue: Optional[str] = None) -> str:
        """
        [DEPRECATED] 兼容性方法，内部转调 _polish_prompt_to_english_with_provider
        """
        api_key_service = APIKeyService(self.db_session)
        api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
        llm_provider = ProviderFactory.create(
            provider=api_key.provider,
            api_key=api_key.get_api_key(),
            base_url=api_key.base_url
        )
        return await self._polish_prompt_to_english_with_provider(llm_provider, visual_desc, camera_movement, performance_prompt, dialogue)

    async def produce_shot_video(self, shot_id: str, api_key_id: str, model: str = "veo_3_1-fast", force: bool = False) -> str:
        """
        生产单个镜头的视频
        """
        if not api_key_id:
            raise ValueError("必须提供 api_key_id")
            
        async with self:
            stmt = select(MovieShot).where(MovieShot.id == shot_id).options(
                joinedload(MovieShot.scene).joinedload(MovieScene.script).joinedload(MovieScript.chapter).joinedload(Chapter.project)
            )
            shot = (await self.db_session.execute(stmt)).scalars().first()
            if not shot: raise ValueError("分镜不存在")
            
            # 1. 强制依赖检查：必须有首帧
            if not shot.first_frame_url:
                raise ValueError(f"分镜 {shot_id} 缺少首帧图，请先生成首帧")

            if shot.video_url and not force:
                return shot.video_task_id or "completed"

            # 2. 准备资料
            project_id = shot.scene.script.chapter.project_id
            owner_id = str(shot.scene.script.chapter.project.owner_id)
            
            # 3. 预加载相关信息 (如果需要设计表演提示词)
            if shot.dialogue and not shot.performance_prompt:
                await dialogue_prompt_engine.design_performance_prompt(shot_id, None, api_key_id)
                await self.db_session.refresh(shot)

            # 4. 收集角色一致性参考图
            stmt_chars = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            all_chars = (await self.db_session.execute(stmt_chars)).scalars().all()
            
            ref_images = []
            for char in all_chars:
                if char.name in shot.visual_description:
                    if char.avatar_url: ref_images.append(char.avatar_url)
                    if char.reference_images: ref_images.extend(char.reference_images)
            ref_images = list(dict.fromkeys(ref_images))[:3]

            # 5. API Provider
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
            llm_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            # 6. 利用 Worker 逻辑执行
            # 这里虽然是单镜头，但也使用 worker 逻辑以保持一致性
            semaphore = asyncio.Semaphore(1)
            shot.api_key_id = api_key_id
            success = await _produce_one_shot_worker(
                shot, owner_id, api_key, ref_images, model, semaphore, llm_provider, self
            )
            
            if success:
                await self.db_session.commit()
                return shot.video_task_id # type: ignore
            else:
                await self.db_session.commit()
                raise Exception(shot.last_error or "视频生产提交失败")

    async def batch_produce_shot_videos(self, script_id: str, api_key_id: str, model: str = "veo_3_1-fast") -> dict:
        """
        批量生产剧本下的分镜视频 (参考 image.py)
        """
        if not api_key_id:
            raise ValueError("必须提供 api_key_id")

        async with self:
            # 1. 深度加载剧本结构
            script = await self.db_session.get(MovieScript, script_id, options=[
                selectinload(MovieScript.scenes).selectinload(MovieScene.shots),
                joinedload(MovieScript.chapter).joinedload(Chapter.project)
            ])
            if not script: raise ValueError("剧本不存在")
            
            project_id = script.chapter.project_id
            owner_id = str(script.chapter.project.owner_id)
            
            # 2. 预加载角色
            stmt_chars = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
            all_chars = (await self.db_session.execute(stmt_chars)).scalars().all()
            
            # 3. 准备资源 (API Key, Provider)
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
            
            llm_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )
            
            # 4. 筛选符合生产条件的分镜
            pending_shots = []
            for scene in script.scenes:
                for shot in scene.shots:
                    if shot.first_frame_url and (not shot.video_url or shot.status == "failed"):
                        pending_shots.append(shot)
            
            if not pending_shots:
                return {"total": 0, "success": 0, "failed": 0, "message": "没有符合生产条件的分镜（需先有首帧）"}

            # 5. 构建并发任务
            semaphore = asyncio.Semaphore(5)
            tasks = []
            for shot in pending_shots:
                ref_images = []
                for char in all_chars:
                    if char.name in shot.visual_description:
                        if char.avatar_url: ref_images.append(char.avatar_url)
                        if char.reference_images: ref_images.extend(char.reference_images)
                ref_images = list(dict.fromkeys(ref_images))[:3]
                
                shot.api_key_id = api_key_id
                tasks.append(_produce_one_shot_worker(
                    shot, owner_id, api_key, ref_images, model, semaphore, llm_provider, self
                ))

            # 6. 执行并发
            logger.info(f"开始批量分镜生产，并发数 {len(tasks)}")
            results = await asyncio.gather(*tasks)
            
            success_count = sum(1 for r in results if r)
            failed_count = len(results) - success_count
            
            # 7. 统一提交
            await self.db_session.commit()
            
            return {
                "total": len(tasks),
                "success": success_count,
                "failed": failed_count,
                "message": f"批量生产已完成: 成功 {success_count}, 失败 {failed_count}"
            }

    async def sync_all_video_tasks(self) -> dict:
        """
        [Celery Beat 调用] 定时同步所有处理中的视频任务状态
        """
        async with self:
            # 1. 深度查询
            stmt = (
                select(MovieShot)
                .where(MovieShot.status == 'processing', MovieShot.video_task_id != None)
                .options(
                    joinedload(MovieShot.scene)
                    .joinedload(MovieScene.script)
                    .joinedload(MovieScript.chapter)
                    .joinedload(Chapter.project)
                )
            )
            processing_shots = (await self.db_session.execute(stmt)).scalars().all()
            
            if not processing_shots:
                return {"count": 0}
            
            logger.info(f"开始定时同步视频状态: 发现 {len(processing_shots)} 个处理中的分镜")
            
            # 2. 预热 API Keys
            api_key_service = APIKeyService(self.db_session)
            api_keys_map = {}
            
            # 3. 并发任务
            semaphore = asyncio.Semaphore(10)
            tasks = []
            
            for shot in processing_shots:
                api_key_id = shot.api_key_id
                if not api_key_id: continue
                
                try:
                    owner_id = str(shot.scene.script.chapter.project.owner_id)
                except AttributeError:
                    continue
                
                if api_key_id not in api_keys_map:
                    api_keys_map[api_key_id] = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
                
                tasks.append(_sync_one_shot_worker(shot, api_keys_map[api_key_id], semaphore))

            if not tasks:
                return {"count": 0}

            # 4. 执行
            await asyncio.gather(*tasks)
            
            # 5. 提交
            await self.db_session.commit()
            return {"count": len(tasks)}

    async def poll_shot_status(self, shot_id: str, api_key_id: str) -> str:
        """
        [DEPRECATED] 轮询并更新镜头状态
        """
        async with self:
            stmt = select(MovieShot).where(MovieShot.id == shot_id).options(
                joinedload(MovieShot.scene).joinedload(MovieScene.script).joinedload(MovieScript.chapter).joinedload(Chapter.project)
            )
            shot = (await self.db_session.execute(stmt)).scalars().first()
            if not shot or not shot.video_task_id: return "no_task"
            
            owner_id = str(shot.scene.script.chapter.project.owner_id)
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, owner_id)
            
            semaphore = asyncio.Semaphore(1)
            await _sync_one_shot_worker(shot, api_key, semaphore)
            await self.db_session.commit()
            return shot.status

    async def check_script_completion(self, script_id: str) -> dict:
        """
        检查剧本的所有分镜是否已完成视频生成
        """
        async with self:
            script = await self.db_session.get(MovieScript, script_id, options=[
                selectinload(MovieScript.scenes).selectinload(MovieScene.shots)
            ])
            if not script:
                raise ValueError("剧本不存在")
            
            total = 0
            completed = 0
            pending = 0
            failed = 0
            processing = 0
            
            for scene in script.scenes:
                for shot in scene.shots:
                    total += 1
                    if shot.status == "completed" and shot.video_url:
                        completed += 1
                    elif shot.status == "failed":
                        failed += 1
                    elif shot.status == "processing":
                        processing += 1
                    else:
                        pending += 1
            
            is_complete = (total > 0 and completed == total)
            can_transition = is_complete
            
            return {
                "total": total,
                "completed": completed,
                "pending": pending,
                "failed": failed,
                "processing": processing,
                "is_complete": is_complete,
                "can_transition": can_transition,
                "completion_rate": round(completed / total * 100, 2) if total > 0 else 0
            }

movie_production_service = MovieProductionService()
__all__ = ["MovieProductionService", "movie_production_service"]


if __name__ == "__main__":
    import asyncio


    async def test():
        service = MovieProductionService()
        result = await service.sync_all_video_tasks()
        print(result)
        
    async def test_shot():
        service = MovieProductionService()
        result = await service.produce_shot_video(
            shot_id="5c105e52-ba09-4109-83be-aae113aeaa04",
            api_key_id="457f4337-8f54-4749-a2d6-78e1febf9028",
            model="veo_3_1-fast",
            force=True
        )
        print(result)

    # asyncio.run(test_shot())
    asyncio.run(test())