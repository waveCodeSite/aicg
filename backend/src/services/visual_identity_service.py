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
from src.services.base import BaseService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.utils.storage import get_storage_client
from src.services.image import retry_with_backoff

logger = get_logger(__name__)

# ============================================================
# 辅助函数
# ============================================================

def _normalize_character_name(name: str) -> str:
    """标准化角色名称,移除括号内容"""
    import re
    return re.sub(r'\s*\([^)]*\)', '', name).strip()


def _character_appears_in_shot(char_name: str, shot: MovieShot) -> bool:
    """
    智能判断角色是否出现在镜头中
    使用多种策略:
    1. 完整名称匹配
    2. 标准化名称匹配(移除括号)
    3. 名字部分匹配(中文名或英文名)
    """
    import re
    
    # 合并镜头描述和对白
    full_text = f"{shot.shot or ''} {shot.dialogue or ''}"
    
    # 策略1: 完整名称匹配
    if char_name in full_text:
        return True
    
    # 策略2: 标准化名称匹配
    normalized_char = _normalize_character_name(char_name)
    if normalized_char and normalized_char in full_text:
        return True
    
    # 策略3: 提取括号内的英文名或中文名分别匹配
    # 例如 "阿尔德里克 (Aldric)" -> ["阿尔德里克", "Aldric"]
    parts = re.findall(r'([^\(\)]+)', char_name)
    for part in parts:
        part = part.strip()
        if part and len(part) > 1 and part in full_text:
            return True
    
    return False


def _collect_character_references(chars: List[MovieCharacter], shot: MovieShot, max_refs: int = 3) -> List[str]:
    """
    收集镜头中出现角色的参考图
    
    Args:
        chars: 所有角色列表
        shot: 镜头对象
        max_refs: 最大参考图数量
        
    Returns:
        参考图URL列表(去重)
    """
    ref_images = []
    matched_chars = []
    
    for char in chars:
        if _character_appears_in_shot(char.name, shot):
            matched_chars.append(char.name)
            if char.avatar_url:
                ref_images.append(char.avatar_url)
    
    # 去重并限制数量
    ref_images = list(dict.fromkeys(ref_images))[:max_refs]
    
    if matched_chars:
        logger.info(f"分镜 {str(shot.id)[:8]} 匹配到角色: {matched_chars}, 参考图数量: {len(ref_images)}")
    
    return ref_images

# ============================================================
# 独立 Worker 函数 (参照 image.py 规范)
# ============================================================

async def _generate_keyframe_worker(
    shot: MovieShot,
    chars: List[MovieCharacter],
    user_id: Any,
    api_key,
    model: Optional[str],
    semaphore: asyncio.Semaphore,
    storage_client,
    ref_images: List[str] = None
):
    """
    单个分镜关键帧生成的 Worker - 负责生成、下载、上传，不负责 Commit
    包含角色参考图以确保人物一致性
    
    注意：新架构下，每个分镜只有一个关键帧（keyframe_url）
    """
    import base64
    
    async with semaphore:
        try:
            # 1. 构建 Prompt (包含角色信息)
            base_prompt = shot.shot
            
            character_context = ""
            # 从shot.characters字段获取角色列表
            shot_characters = shot.characters if hasattr(shot, 'characters') and shot.characters else []
            
            for char in chars:
                if char.name in shot_characters:
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

            logger.info(f"生成分镜 {shot.id} 关键帧, Prompt: {final_prompt[:100]}..., Refs: {len(ref_images or [])}")
            
            # 准备生成参数
            gen_params = {
                "prompt": final_prompt,
                "model": model
            }
            
            if ref_images:
                gen_params["reference_images"] = ref_images
            
            # 某些 provider 支持参考图 (如 SiliconFlow)        
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
                filename=f"{file_id}_keyframe.jpg",
                file=io.BytesIO(content),
            )
            
            storage_result = await storage_client.upload_file(
                user_id=str(user_id),
                file=upload_file,
                metadata={"shot_id": str(shot.id), "type": "keyframe"}
            )
            object_key = storage_result["object_key"]

            # 5. 更新对象属性 (不 Commit) - 使用新的keyframe_url字段
            shot.keyframe_url = object_key
                
            logger.info(f"关键帧生成并存储完成: shot_id={shot.id}, key={object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Worker 生成关键帧失败 [shot_id={shot.id}]: {e}")
            return False


class VisualIdentityService(BaseService):
    """
    视觉身份服务
    要求外部注入 AsyncSession。
    """
    
    def __init__(self, db_session: Any):
        super().__init__(db_session)

    async def generate_character_references(self, character_id: str, api_key_id: str, prompt_override: Optional[str] = None) -> List[str]:
        """
        为角色生成一致性参考图 (单条任务)
        """
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

    async def generate_shot_keyframe(self, shot_id: str, api_key_id: str, model: Optional[str] = None) -> str:
        """为分镜生成关键帧图"""
        shot = await self.db_session.get(MovieShot, shot_id, options=[
            joinedload(MovieShot.scene).joinedload(MovieScene.script).joinedload(MovieScript.chapter).joinedload(Chapter.project)
        ])
        if not shot: raise ValueError("未找到分镜")
        
        project_id = shot.scene.script.chapter.project_id
        user_id = shot.scene.script.chapter.project.owner_id
        
        stmt = select(MovieCharacter).where(MovieCharacter.project_id == project_id)
        chars = (await self.db_session.execute(stmt)).scalars().all()
        
        # 收集角色参考图
        ref_images = _collect_character_references(chars, shot)
        
        api_key_service = APIKeyService(self.db_session)
        api_key = await api_key_service.get_api_key_by_id(api_key_id, str(user_id))
        
        storage_client = await get_storage_client()
        semaphore = asyncio.Semaphore(1)
        
        success = await _generate_keyframe_worker(shot, chars, user_id, api_key, model, semaphore, storage_client, ref_images)
        if success:
            await self.db_session.commit()
            return shot.keyframe_url # type: ignore
        else:
            raise Exception("生成分镜关键帧失败")

    # Removed: generate_shot_last_frame - obsolete, shots now only have single keyframe
    # Removed: regenerate_shot_keyframe - use generate_shot_keyframe instead

    async def batch_generate_keyframes(self, script_id: str, api_key_id: str, model: Optional[str] = None) -> dict:
        """
        批量为剧本下的所有分镜生成关键帧
        新架构：每个分镜只有一个关键帧（keyframe_url）
        """
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

        # 4. 筛选待处理任务 - 只生成缺少keyframe的分镜
        tasks = []
        semaphore = asyncio.Semaphore(5)
        
        for scene in script.scenes:
            for shot in scene.shots:
                # 检查是否需要生成关键帧
                if not shot.keyframe_url:
                    ref_images = _collect_character_references(chars, shot)
                    tasks.append(
                        _generate_keyframe_worker(shot, chars, user_id, api_key, model, semaphore, storage_client, ref_images)
                    )
        
        # 5. 无任务则返回
        if not tasks:
            return {"total": 0, "success": 0, "failed": 0, "message": "所有分镜已有关键帧"}

        # 6. 执行并发
        results = await asyncio.gather(*tasks)
        
        success_count = sum(1 for r in results if r)
        failed_count = len(results) - success_count
        
        # 7. 提交
        await self.db_session.commit()
        
        logger.info(f"批量关键帧生成完成: 总计 {len(tasks)}, 成功 {success_count}, 失败 {failed_count}")
        
        return {
            "total": len(tasks),
            "success": success_count,
            "failed": failed_count,
            "message": f"批量生成完成: 成功 {success_count}, 失败 {failed_count}"
        }

__all__ = ["VisualIdentityService"]


if __name__ == "__main__":
    # 测试关键帧生成
    import asyncio
    
    async def test():
        from src.core.database import get_async_db
        async with get_async_db() as session:
            vis_service = VisualIdentityService(session)
            script_id = "cd1b2680-5d39-4b08-8bf1-968ec05a1571"
            api_key_id = "457f4337-8f54-4749-a2d6-78e1febf9028"
            stats = await vis_service.batch_generate_keyframes(script_id, api_key_id, model="gemini-3-pro-image-preview")
            print(stats)

    asyncio.run(test())