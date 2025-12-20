"""
视觉身份服务 - 负责角色形象固化（一致性）和场景/首帧图像生成
"""

from typing import List, Optional
from src.core.logging import get_logger
from src.models.movie import MovieCharacter, MovieShot, MovieScene
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.utils.storage import get_storage_client

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
                response = await img_provider.generate_image(
                    prompt=final_prompt,
                    model="flux-pro" # 示例模型
                )
                
                # 获取图片 URL（假设返回的是 URL 列表或单个 URL）
                # 注意：实际生产中需要下载并存储到 MinIO
                image_url = response.data[0].url
                
                # 更新角色参考图
                character.reference_images = [image_url]
                await self.db_session.commit()
                return [image_url]
                
            except Exception as e:
                logger.error(f"生成角色参考图失败: {e}")
                raise

    async def generate_shot_first_frame(self, shot_id: str, api_key_id: str) -> str:
        """
        为分镜生成首帧图（综合角色一致性和场景描述）
        """
        async with self:
            shot = await self.db_session.get(MovieShot, shot_id)
            if not shot: raise ValueError("未找到分镜")
            
            # 这里需要复杂的 Prompt Engineering，将角色参考图的视觉特征融合进分镜描述
            # 简化版：
            first_frame_prompt = f"{shot.visual_description}, high quality movie still, 8k."
            
            # ... 生成逻辑同上 ...
            shot.first_frame_url = "https://placeholder-url.com/frame.png"
            await self.db_session.commit()
            return shot.first_frame_url

visual_identity_service = VisualIdentityService()
__all__ = ["VisualIdentityService", "visual_identity_service"]
