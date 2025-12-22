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

    GENERATE_FRAME_PROMPT = """
你是一个专业的电影分镜提示词生成专家。根据以下分镜信息，生成用于AI图像生成的详细提示词。

### 分镜信息：
- 场景：{location} ({time_of_day})
- 氛围：{atmosphere}
- 画面描述：{visual_description}
- 镜头运动：{camera_movement}
- 对话：{dialogue}

### 输出要求：
必须以 JSON 格式输出，包含首帧和尾帧的提示词：
{{
  "first_frame_prompt": "首帧的详细英文提示词，描述镜头开始时的画面",
  "last_frame_prompt": "尾帧的详细英文提示词，描述镜头结束时的画面"
}}

### 提示词要求：
1. **英文输出**：所有提示词必须用英文
2. **视觉细节**：包含光影、构图、色调、人物表情、动作等
3. **连贯性**：首帧和尾帧要体现动作的起始和结束
4. **风格统一**：保持电影质感，cinematic style
5. **简洁明确**：避免冗余，每个提示词控制在100词以内
"""

    async def _generate_shot_prompts(self, shot: MovieShot, scene: MovieScene, llm_provider, model: str = None) -> Dict[str, str]:
        """
        为单个分镜生成首尾帧提示词
        
        Args:
            shot: 分镜对象
            scene: 场景对象
            llm_provider: LLM提供者
            model: 模型名称
            
        Returns:
            包含 first_frame_prompt 和 last_frame_prompt 的字典
        """
        try:
            prompt = self.GENERATE_FRAME_PROMPT.format(
                location=scene.location,
                time_of_day=scene.time_of_day,
                atmosphere=scene.atmosphere,
                visual_description=shot.visual_description,
                camera_movement=shot.camera_movement or "无特殊运动",
                dialogue=shot.dialogue or "无对话"
            )
            
            response = await llm_provider.completions(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的电影分镜提示词生成专家。只输出JSON。"},
                    {"role": "user", "content": prompt},
                ],
                response_format={ "type": "json_object" }
            )
            
            content = response.choices[0].message.content.strip()
            # 兼容某些模型不带 json_object 的情况
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            prompts = json.loads(content)
            return prompts
            
        except Exception as e:
            logger.error(f"生成分镜 {shot.id} 提示词失败: {e}")
            # 返回默认提示词
            return {
                "first_frame_prompt": f"Cinematic shot, {shot.visual_description}",
                "last_frame_prompt": f"Cinematic shot, {shot.visual_description}, end frame"
            }

    async def _generate_all_frame_prompts(
        self, 
        scenes: List[MovieScene], 
        llm_provider, 
        model: str, 
        max_concurrent: int = 5,
        on_progress: Callable[[float, str], Any] = None
    ):
        """
        并发生成所有分镜的首尾帧提示词
        
        Args:
            scenes: 场景列表（包含已 populated 的 shots）
            llm_provider: LLM提供者
            model: 模型名称
            max_concurrent: 最大并发数
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_shot(shot: MovieShot, scene: MovieScene):
            async with semaphore:
                logger.info(f"生成分镜 {shot.id} 的提示词")
                prompts = await self._generate_shot_prompts(shot, scene, llm_provider, model)
                shot.first_frame_prompt = prompts.get("first_frame_prompt")
                shot.last_frame_prompt = prompts.get("last_frame_prompt")
                return True
        
        tasks = []
        for scene in scenes:
            for shot in scene.shots:
                tasks.append(process_shot(shot, scene))
        
        total_tasks = len(tasks)
        if total_tasks == 0:
            return

        logger.info(f"开始并发生成 {total_tasks} 个分镜的提示词")
        
        # We can wrap tasks to report partial progress if we want, but gather is simpler.
        # Let's just report half-way if we are doing many.
        if on_progress:
            await on_progress(0.5, f"正在生成 {total_tasks} 个分镜的绘图提示词...")

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if r is True)
        failed_count = len(results) - success_count
        logger.info(f"提示词生成完成: 成功 {success_count}, 失败 {failed_count}")


    async def generate_script(
        self, 
        chapter_id: str, 
        api_key_id: str, 
        model: str = None,
        on_progress: Callable[[float, str], Any] = None
    ) -> MovieScript:
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
                if on_progress:
                    await on_progress(0.1, "正在生成剧本结构...")
                
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
                created_scenes = []
                for scene_data in script_data.get("scenes", []):
                    scene = MovieScene(
                        script_id=script.id,
                        order_index=scene_data.get("order_index"),
                        location=scene_data.get("location"),
                        time_of_day=scene_data.get("time_of_day"),
                        atmosphere=scene_data.get("atmosphere"),
                        description=scene_data.get("description")
                    )
                    created_scenes.append(scene)
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
                        scene.shots.append(shot)
                        self.db_session.add(shot)
                
                if on_progress:
                    await on_progress(0.4, "剧本结构生成完成，开始生成精细提示词...")

                script.status = ScriptStatus.COMPLETED
                
                # 4. 并发生成所有分镜的首尾帧提示词
                logger.info("开始生成分镜提示词...")
                await self._generate_all_frame_prompts(created_scenes, llm_provider, model, on_progress=on_progress)
                
                if on_progress:
                    await on_progress(0.9, "提示词生成完成，正在保存...")

                await self.db_session.commit()
                return script
                
            except Exception as e:
                logger.error(f"生成剧本失败: {e}")
                script.status = ScriptStatus.FAILED
                await self.db_session.commit()
                raise

script_engine_service = ScriptEngineService()
__all__ = ["ScriptEngineService", "script_engine_service"]

if __name__ == "__main__":
    import asyncio

    async def test():
        """
        测试剧本生成和提示词生成
        
        使用方法：
        1. 确保有一个已创建的章节，并获取其 chapter_id
        2. 确保有一个可用的 API Key，并获取其 api_key_id
        3. 替换下面的 chapter_id 和 api_key_id
        4. 运行: python -m src.services.script_engine
        """
        service = ScriptEngineService()
        
        # TODO: 替换为实际的 chapter_id 和 api_key_id
        chapter_id = "your-chapter-id-here"
        api_key_id = "your-api-key-id-here"
        model = "gemini-2.0-flash-exp"  # 或其他模型
        
        try:
            print(f"开始生成剧本: chapter_id={chapter_id}")
            script = await service.generate_script(
                chapter_id=chapter_id,
                api_key_id=api_key_id,
                model=model
            )
            print(f"剧本生成成功: script_id={script.id}")
            print(f"场景数量: {len(script.scenes)}")
            
            # 打印第一个场景的第一个分镜的提示词
            if script.scenes and script.scenes[0].shots:
                first_shot = script.scenes[0].shots[0]
                print("\n第一个分镜的提示词:")
                print(f"  首帧: {first_shot.first_frame_prompt}")
                print(f"  尾帧: {first_shot.last_frame_prompt}")
                
        except Exception as e:
            print(f"测试失败: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(test())
