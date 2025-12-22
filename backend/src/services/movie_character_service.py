"""
电影角色服务 - 负责角色提取、视觉特征建模、对话风格设计
"""

import json
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.models.movie import MovieCharacter, MovieScript, MovieScene, MovieShot
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService
from src.services.image import retry_with_backoff
from src.utils.storage import get_storage_client
import uuid
import io
import aiohttp
from fastapi import UploadFile

logger = get_logger(__name__)

class MovieCharacterService(SessionManagedService):
    """
    角色管理服务
    """

    EXTRACT_CHARACTERS_PROMPT = """
你是一个资深的选角导演。请分析以下电影剧本片段，提取出其中出现的所有主要角色。

### 输出要求：
必须以 JSON 格式输出，结构如下：
{{
  "characters": [
    {{
      "name": "角色姓名",
      "role_description": "角色的身份、背景、性格特点",
      "visual_traits": "详细的视觉特征描述（如：年龄、发色、发型、穿着、面部特征、体型），用于AI生图。",
      "dialogue_traits": "角色的对话风格（如：冷静、粗鲁、幽默、书生气、口音特点等）"
    }}
  ]
}}

待分析剧本：
---
{text}
---
"""

    async def extract_characters_from_script(self, script_id: str, api_key_id: str, model: str = None) -> List[MovieCharacter]:
        """
        从剧本中提取角色
        """
        async with self:
            # 1. 加载剧本内容
            script = await self.db_session.get(MovieScript, script_id, options=[
                selectinload(MovieScript.scenes).selectinload(MovieScene.shots)
            ])
            if not script:
                raise ValueError("未找到剧本")
            
            # 拼凑剧本全文用于分析
            script_text = ""
            for scene in script.scenes:
                script_text += f"场景 {scene.order_index}: {scene.location} - {scene.description}\n"
                for shot in scene.shots:
                    if shot.dialogue:
                        script_text += f"镜头 {shot.order_index} 对话: {shot.dialogue}\n"

            # 2. 加载 API Key
            from src.models.chapter import Chapter
            chapter = await self.db_session.get(Chapter, script.chapter_id, options=[selectinload(Chapter.project)])
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(chapter.project.owner_id))
            
            llm_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )

            try:
                prompt = self.EXTRACT_CHARACTERS_PROMPT.format(text=script_text[:5000]) # 限制长度
                response = await llm_provider.completions(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的选角导演JSON生成器。"},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={ "type": "json_object" }
                )
                
                content = response.choices[0].message.content.strip()
                if content.startswith("```json"): content = content[7:-3].strip()
                elif content.startswith("```"): content = content[3:-3].strip()
                
                char_data = json.loads(content)
                
                created_characters = []
                for char in char_data.get("characters", []):
                    # 检查是否已存在同名角色
                    stmt = select(MovieCharacter).where(
                        MovieCharacter.project_id == chapter.project_id,
                        MovieCharacter.name == char.get("name")
                    )
                    existing = await self.db_session.execute(stmt)
                    if existing.scalar_one_or_none():
                        continue
                        
                    character = MovieCharacter(
                        project_id=chapter.project_id,
                        name=char.get("name"),
                        role_description=char.get("role_description"),
                        visual_traits=char.get("visual_traits"),
                        dialogue_traits=char.get("dialogue_traits")
                    )
                    self.db_session.add(character)
                    created_characters.append(character)
                
                await self.db_session.commit()
                return created_characters
                
            except Exception as e:
                logger.error(f"提取角色失败: {e}")
                raise
    
    async def generate_character_avatar(self, character_id: str, api_key_id: str, model: str = None, prompt: str = None, style: str = "cinematic") -> str:
        """
        生成角色头像/定妆照
        """
        async with self:
            char = await self.db_session.get(MovieCharacter, character_id)
            if not char:
                raise ValueError("未找到角色")
            
            # 加载 API Key
            from src.models.project import Project
            project = await self.db_session.get(Project, char.project_id)
            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(project.owner_id))

            image_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )
            
            try:
                # 增强提示词，让AI模型在图片左上角生成角色名称
                enhanced_prompt = f"{prompt}. IMPORTANT: Include the text '{char.name}' in the top-left corner of the image, clearly visible and readable."
                
                # 4. 调用生图模型
                logger.info(f"生成角色头像提示词: {enhanced_prompt}")
                result = await retry_with_backoff(
                    lambda: image_provider.generate_image(
                        prompt=enhanced_prompt,
                        model=model
                    )
                )
                
                image_data = result.data[0]
                image_url = image_data.url
                
                # 5. 下载图片并上传 MinIO
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
                    user_id=str(project.owner_id),
                    file=upload_file,
                    metadata={"character_id": str(char.id)}
                )
                object_key = storage_result["object_key"]

                # 6. 更新角色信息
                char.avatar_url = object_key
                
                # 更新参考图列表
                refs = list(char.reference_images) if char.reference_images else []
                if object_key not in refs:
                    refs.insert(0, object_key)
                    char.reference_images = refs
                
                await self.db_session.commit()
                return object_key
                
            except Exception as e:
                logger.error(f"生成角色头像失败: {e}")
                raise

movie_character_service = MovieCharacterService()
__all__ = ["MovieCharacterService", "movie_character_service"]
