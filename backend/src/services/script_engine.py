"""
电影剧本生成引擎 - 将小说章节改编为剧本/分镜
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.models.movie import MovieScript, MovieScene, MovieShot, ScriptStatus
from src.models.chapter import Chapter
from src.services.base import SessionManagedService
from src.services.provider.factory import ProviderFactory
from src.services.api_key import APIKeyService

logger = get_logger(__name__)

class ScriptEngineService(SessionManagedService):
    """
    剧本引擎服务
    1. 改编剧本：章节 -> 场景 (Scenes)
    2. 拆分分镜：场景 -> 镜头 (Shots)
    """

    ADAPT_CHAPTER_PROMPT = """
你是一个顶级的电影编剧和导演。你的任务是将以下小说章节改编成电影剧本（Screenplay）并拆分为详细的分镜（Storyboard）。

### 输出要求：
必须以 JSON 格式输出，结构如下：
{{
  "scenes": [
    {{
      "order_index": 1,
      "location": "场景地点",
      "time_of_day": "日/夜/傍晚等",
      "atmosphere": "场景氛围描述",
      "description": "整个场景的简要概括",
      "shots": [
        {{
          "order_index": 1,
          "visual_description": "具体的画面描述，包含人物动作、构图、光影等。生成的视频将以此为主要依据。",
          "camera_movement": "镜头运动（如：推、拉、摇、移、特写、全景等）",
          "dialogue": "角色对话内容（如果没有对话则为空）",
          "performance_description": "角色的神情、语气、动作表现建议"
        }}
      ]
    }}
  ]
}}

### 创作准则：
1. **视觉化**：将抽象的心理描写转化为具体的可视化动作。
2. **节奏感**：镜头拆分要合理，动作戏分镜要快，情感戏分镜要稳。
3. **一致性**：确保人物在不同场景中的行为符合逻辑。
4. **对话**：保留小说中的核心对话，并根据电影表现进行适当精炼。

待改编小说内容：
---
{text}
---
"""

    async def generate_script(self, chapter_id: str, api_key_id: str, model: str = None) -> MovieScript:
        """
        根据章节内容生成剧本和分镜
        """
        async with self:
            # 1. 加载章节和API Key
            chapter = await self.db_session.get(Chapter, chapter_id, options=[selectinload(Chapter.project)])
            if not chapter:
                raise ValueError("未找到章节")

            api_key_service = APIKeyService(self.db_session)
            api_key = await api_key_service.get_api_key_by_id(api_key_id, str(chapter.project.owner_id))
            
            # 2. 调用 LLM
            llm_provider = ProviderFactory.create(
                provider=api_key.provider,
                api_key=api_key.get_api_key(),
                base_url=api_key.base_url
            )
            
            # 更新剧本状态
            script = MovieScript(chapter_id=chapter.id, status=ScriptStatus.GENERATING)
            self.db_session.add(script)
            await self.db_session.flush()

            try:
                prompt = self.ADAPT_CHAPTER_PROMPT.format(text=chapter.content)
                response = await llm_provider.completions(
                    model=model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的电影剧本JSON生成器。只输出JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={ "type": "json_object" }
                )
                
                content = response.choices[0].message.content.strip()
                # 兼容某些模型不带 json_object 的情况，手动清理代码块
                if content.startswith("```json"):
                    content = content[7:-3].strip()
                elif content.startswith("```"):
                    content = content[3:-3].strip()
                    
                script_data = json.loads(content)
                
                # 3. 解析并保存数据
                for scene_data in script_data.get("scenes", []):
                    scene = MovieScene(
                        script_id=script.id,
                        order_index=scene_data.get("order_index"),
                        location=scene_data.get("location"),
                        time_of_day=scene_data.get("time_of_day"),
                        atmosphere=scene_data.get("atmosphere"),
                        description=scene_data.get("description")
                    )
                    self.db_session.add(scene)
                    await self.db_session.flush()
                    
                    for shot_data in scene_data.get("shots", []):
                        shot = MovieShot(
                            scene_id=scene.id,
                            order_index=shot_data.get("order_index"),
                            visual_description=shot_data.get("visual_description"),
                            camera_movement=shot_data.get("camera_movement"),
                            dialogue=shot_data.get("dialogue"),
                            performance_prompt=shot_data.get("performance_description")
                        )
                        self.db_session.add(shot)
                
                script.status = ScriptStatus.COMPLETED
                await self.db_session.commit()
                return script
                
            except Exception as e:
                logger.error(f"生成剧本失败: {e}")
                script.status = ScriptStatus.FAILED
                await self.db_session.commit()
                raise

script_engine_service = ScriptEngineService()
__all__ = ["ScriptEngineService", "script_engine_service"]
