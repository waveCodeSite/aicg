"""
文件处理 Celery 任务模块 - 专注于 Celery 任务定义

该模块仅包含 Celery 任务定义和配置，具体的业务逻辑实现
已迁移到 src.services.project_processing 模块中。

职责：
- Celery 应用配置
- 任务定义和装饰器
- 任务参数验证
- 错误处理和重试策略
- 任务状态管理
"""

import asyncio
from typing import Any, Dict, List

from celery import Celery

from src.core.config import settings
from src.core.logging import get_logger
from src.services.project_processing import project_processing_service
from src.services.prompt import prompt_service
from src.services.image import image_service
from src.services.script_engine import script_engine_service

logger = get_logger(__name__)

# ---------------------------
# Celery 实例与配置
# ---------------------------

celery_app = Celery(
    "file_processing",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.task", "src.tasks.bilibili_task"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT", 600),
    task_soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT", 480),
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    beat_schedule={
        "sync-video-status-every-60s": {
            "task": "movie.sync_all_video_task_status",
            "schedule": 60.0,
        },
    }
)


# ---------------------------
# Celery 任务定义
# ---------------------------

@celery_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="file_processing.process_uploaded_file"
)
def process_uploaded_file(self, project_id: str, owner_id: str) -> Dict[str, Any]:
    """
    处理上传文件的 Celery 任务

    该任务仅负责调用服务层的文件处理逻辑，不包含任何业务逻辑。
    所有的文件处理、状态管理、错误处理都在服务层完成。

    Args:
        project_id: 项目ID
        owner_id: 项目所有者ID

    Returns:
        Dict[str, Any]: 处理结果

    Raises:
        Exception: 当处理失败且需要重试时抛出异常
    """
    logger.info(f"Celery任务开始: process_uploaded_file (project_id={project_id})")

    # 使用辅助函数运行异步任务
    result = run_async_task(project_processing_service.process_file_task(project_id, owner_id))

    logger.info(f"Celery任务成功: process_uploaded_file (project_id={project_id})")
    return result


def run_async_task(coro):
    """
    运行异步任务的辅助函数，确保在新的事件循环中重置数据库连接
    
    Args:
        coro: 要运行的协程对象
        
    Returns:
        协程的执行结果
    """

    async def _wrapper():
        from src.core.database import close_database_connections
        # 在新的事件循环中，必须重置数据库连接，因为旧的连接绑定在已关闭的循环上
        await close_database_connections()
        return await coro

    return asyncio.run(_wrapper())


@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="file_processing.retry_failed_project"
)
def retry_failed_project(self, project_id: str, owner_id: str) -> Dict[str, Any]:
    """
    重试失败项目的 Celery 任务

    该任务仅负责调用服务层的重试逻辑，不包含业务逻辑。

    Args:
        project_id: 项目ID
        owner_id: 项目所有者ID

    Returns:
        Dict[str, Any]: 重试结果
    """
    logger.info(f"Celery任务开始: retry_failed_project (project_id={project_id})")

    try:
        # 使用辅助函数运行异步任务
        result = run_async_task(project_processing_service.retry_failed_project(project_id, owner_id))

        if result.get("success", False):
            logger.info(f"Celery任务成功: retry_failed_project (project_id={project_id})")
        else:
            logger.error(
                f"Celery任务失败: retry_failed_project (project_id={project_id}, error={result.get('message')})")

        return result

    except Exception as e:
        logger.error(f"Celery任务异常: retry_failed_project (project_id={project_id}, error={e})", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="generate.generate_prompts"
)
def generate_prompts(self, chapter_id: str, api_key_id: str, style: str, model: str = None, custom_prompt: str = None):
    """
    为章节生成提示词的 Celery 任务

    该任务仅负责调用服务层的提示词生成逻辑，不包含业务逻辑。

    Args:
        chapter_id: 章节ID
        api_key_id: API密钥ID
        style: 提示词风格
        model: 模型名称
        custom_prompt: 自定义系统提示词

    Returns:
        Dict[str, Any]: 生成结果，包含统计信息
    """
    logger.info(f"Celery任务开始: generate_prompts (chapter_id={chapter_id})")
    result = run_async_task(prompt_service.generate_prompts_batch(chapter_id, api_key_id, style, model, custom_prompt))
    logger.info(f"Celery任务成功: generate_prompts (chapter_id={chapter_id})")
    return result


@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="generate.generate_prompts_by_ids"
)
def generate_prompts_by_ids(self, sentence_ids: List[str], api_key_id: str, style: str, model: str = None, custom_prompt: str = None):
    """
    为章节生成提示词的 Celery 任务

    该任务仅负责调用服务层的提示词生成逻辑，不包含业务逻辑。

    Args:
        sentence_ids: 句子ID列表
        api_key_id: API密钥ID
        style: 提示词风格
        model: 模型名称
        custom_prompt: 自定义系统提示词

    Returns:
        Dict[str, Any]: 生成结果
    """
    logger.info(f"Celery任务开始: generate_prompts_by_ids (sentence_ids={sentence_ids})")
    result = run_async_task(prompt_service.generate_prompts_by_ids(sentence_ids, api_key_id, style, model, custom_prompt))
    logger.info(f"Celery任务成功: generate_prompts_by_ids (chapter_id={sentence_ids})")
    return result


@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="generate.generate_images"
)
def generate_images(self, api_key_id: str, sentences_ids: list[str], model: str = None):
    """
    为章节或指定句子批量生成图片的 Celery 任务

    该任务仅负责调用服务层的图片生成逻辑，不包含业务逻辑。

    Args:
        api_key_id: API密钥ID
        sentences_ids: 句子ID列表（可选，与chapter_id二选一）
        model: 模型名称

    Returns:
        Dict[str, Any]: 生成结果，包含统计信息
    """

    logger.info(f"Celery任务开始: generate_images (sentences_ids={sentences_ids})")

    result = run_async_task(image_service.generate_images(api_key_id, sentences_ids, model))
    logger.info(f"Celery任务成功: generate_images (sentences_ids={sentences_ids})")
    return result


@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="generate.generate_audio"
)
def generate_audio(self, api_key_id: str, sentences_ids: list[str], voice: str = "alloy", model: str = "tts-1"):
    """
    为章节或指定句子批量生成音频的 Celery 任务

    该任务仅负责调用服务层的音频生成逻辑，不包含业务逻辑。

    Args:
        api_key_id: API密钥ID
        sentences_ids: 句子ID列表
        voice: 语音风格
        model: 模型名称

    Returns:
        Dict[str, Any]: 生成结果，包含统计信息
    """
    from src.services.audio import audio_service

    logger.info(f"Celery任务开始: generate_audio (sentences_ids={sentences_ids})")

    result = run_async_task(audio_service.generate_audio(api_key_id, sentences_ids, voice, model))
    logger.info(f"Celery任务成功: generate_audio (sentences_ids={sentences_ids})")
    return result

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="generate.synthesize_video"
)
def synthesize_video(self, video_task_id: str):
    """
    视频合成的 Celery 任务

    该任务仅负责调用服务层的视频合成逻辑，不包含业务逻辑。

    Args:
        video_task_id: 视频任务ID

    Returns:
        Dict[str, Any]: 合成结果，包含统计信息
    """
    from src.services.video_synthesis import video_synthesis_service

    logger.info(f"Celery任务开始: synthesize_video (video_task_id={video_task_id})")
    result = run_async_task(video_synthesis_service.synthesize_video(video_task_id))
    logger.info(f"Celery任务成功: synthesize_video (video_task_id={video_task_id})")
    return result

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.generate_script"
)
def movie_generate_script(self, chapter_id: str, api_key_id: str, model: str = None):
    logger.info(f"Celery任务开始: movie_generate_script (chapter_id={chapter_id})")
    
    async def on_progress(percent, msg):
        self.update_state(state='PROGRESS', meta={'percent': percent, 'message': msg})
        
    result = run_async_task(script_engine_service.generate_script(chapter_id, api_key_id, model, on_progress=on_progress))
    logger.info(f"Celery任务完成: movie_generate_script")
    return {"script_id": str(result.id)}

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.produce_shot"
)
def movie_produce_shot(self, shot_id: str, api_key_id: str, model: str = "veo_3_1-fast", force: bool = False):
    from src.services.movie_production import movie_production_service
    logger.info(f"Celery任务开始: movie_produce_shot (shot_id={shot_id}, force={force})")
    task_id = run_async_task(movie_production_service.produce_shot_video(shot_id, api_key_id, model, force=force))
    logger.info(f"Celery任务提交: Vector Engine Task ID = {task_id}")
    return {"video_task_id": task_id}

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.extract_characters"
)
def movie_extract_characters(self, script_id: str, api_key_id: str, model: str = None):
    from src.services.movie_character_service import movie_character_service
    logger.info(f"Celery任务开始: movie_extract_characters (script_id={script_id})")
    chars = run_async_task(movie_character_service.extract_characters_from_script(script_id, api_key_id, model))
    logger.info(f"Celery任务完成: movie_extract_characters, extracted {len(chars)} characters")
    return {"character_count": len(chars)}

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.generate_character_avatar"
)
def movie_generate_character_avatar(self, character_id: str, api_key_id: str, model: str = None, prompt: str = None, style: str = "cinematic"):
    from src.services.movie_character_service import movie_character_service
    logger.info(f"Celery任务开始: movie_generate_character_avatar (character_id={character_id})")
    url = run_async_task(movie_character_service.generate_character_avatar(character_id, api_key_id, model, prompt, style))
    logger.info(f"Celery任务完成: movie_generate_character_avatar")
    return {"avatar_url": url}

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.generate_keyframes"
)
def movie_generate_keyframes(self, script_id: str, api_key_id: str, model: str = None):
    from src.services.visual_identity_service import visual_identity_service
    logger.info(f"Celery任务开始: movie_generate_keyframes (script_id={script_id})")
    stats = run_async_task(visual_identity_service.batch_generate_keyframes(script_id, api_key_id, model))
    logger.info(f"Celery任务完成: movie_generate_keyframes")
    return stats

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.batch_produce_shots"
)
def movie_batch_produce_shots(self, script_id: str, api_key_id: str, model: str = "veo_3_1-fast"):
    from src.services.movie_production import movie_production_service
    logger.info(f"Celery任务开始: movie_batch_produce_shots (script_id={script_id})")
    stats = run_async_task(movie_production_service.batch_produce_shot_videos(script_id, api_key_id, model))
    logger.info(f"Celery任务完成: movie_batch_produce_shots")
    return stats

@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.regenerate_keyframe"
)
def movie_regenerate_keyframe(self, shot_id: str, api_key_id: str, model: str = None):
    from src.services.visual_identity_service import visual_identity_service
    logger.info(f"Celery任务开始: movie_regenerate_keyframe (shot_id={shot_id})")
    url = run_async_task(visual_identity_service.regenerate_shot_keyframe(shot_id, api_key_id, model))
    logger.info(f"Celery任务完成: movie_regenerate_keyframe")
    return {"first_frame_url": url}


@celery_app.task(
    bind=True,
    max_retries=1,
    autoretry_for=(Exception,),
    name="movie.regenerate_last_frame"
)
def movie_regenerate_last_frame(self, shot_id: str, api_key_id: str, model: str = None):
    from src.services.visual_identity_service import visual_identity_service
    logger.info(f"Celery任务开始: movie_regenerate_last_frame (shot_id={shot_id})")
    url = run_async_task(visual_identity_service.generate_shot_last_frame(shot_id, api_key_id, model))
    logger.info(f"Celery任务完成: movie_regenerate_last_frame")
    return {"last_frame_url": url}

@celery_app.task(name="movie.sync_all_video_task_status")
def sync_all_video_task_status():
    """
    [Periodic Task] 同步所有处理中的视频任务
    """
    from src.services.movie_production import movie_production_service
    logger.info("Celery定时任务开始: sync_all_video_task_status")
    result = run_async_task(movie_production_service.sync_all_video_tasks())
    return result

# ---------------------------
# 导出的任务列表
# ---------------------------

__all__ = [
    'celery_app',
    'process_uploaded_file',
    'retry_failed_project',
    'generate_prompts',
    'generate_prompts_by_ids',
    'generate_images',
    'generate_audio',
    'synthesize_video',
    'movie_generate_script',
    'movie_produce_shot',
    'movie_extract_characters',
    'movie_generate_character_avatar',
    'movie_generate_keyframes',
    'movie_batch_produce_shots',
    'movie_regenerate_keyframe',
    'movie_regenerate_last_frame',
    'sync_all_video_task_status',
]
