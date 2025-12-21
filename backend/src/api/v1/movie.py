"""
电影路由 - 处理剧本生成、角色管理和视频生产
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.logging import get_logger
from src.models.user import User
from src.api.dependencies import get_current_user_required
from src.services.movie import MovieService
from src.api.schemas.movie import (
    MovieScriptResponse, ScriptGenerateRequest, 
    MovieCharacterBase, CharacterExtractRequest,
    ShotProduceRequest, CharacterUpdateRequest,
    CharacterGenerateRequest, KeyframeGenerateRequest
)
from src.tasks.task import movie_produce_shot

logger = get_logger(__name__)

router = APIRouter()

@router.post("/chapters/{chapter_id}/script", summary="为章节启动剧本生成任务")
async def create_script_task(
    chapter_id: str, 
    req: ScriptGenerateRequest,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db)
):
    """
    提交由章节改编为剧本的任务到 Celery
    """
    movie_service = MovieService(db)
    
    # 验证章节所属权 (可选，MovieService 内部或此处处理)
    # 此处简化，直接提交任务
    
    task_id = await movie_service.create_script_task(chapter_id, req.api_key_id, req.model)
    return {"task_id": task_id, "message": "剧本生成任务已提交"}

@router.get("/chapters/{chapter_id}/script", response_model=Optional[MovieScriptResponse])
async def get_script(
    chapter_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    获取章节关联的剧本详情
    """
    movie_service = MovieService(db)
    script = await movie_service.get_script(chapter_id)
    return script

@router.post("/scripts/{script_id}/extract-characters")
async def extract_characters(
    script_id: str, 
    req: CharacterExtractRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    从剧本中提取角色（异步任务）
    """
    from src.tasks.task import movie_extract_characters
    task = movie_extract_characters.delay(script_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "角色提取任务已提交"}

@router.get("/projects/{project_id}/characters", response_model=List[MovieCharacterBase])
async def list_characters(
    project_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    列出项目下的所有电影角色
    """
    movie_service = MovieService(db)
    chars = await movie_service.list_characters(project_id)
    return chars

@router.put("/characters/{character_id}", response_model=MovieCharacterBase)
async def update_character(
    character_id: str,
    req: CharacterUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    更新角色信息（头像、参考图）
    """
    movie_service = MovieService(db)
    updated_char = await movie_service.update_character(character_id, req.dict(exclude_unset=True))
    if not updated_char:
        raise HTTPException(status_code=404, detail="Character not found")
    return updated_char

@router.post("/characters/{character_id}/generate", summary="生成角色头像")
async def generate_character_avatar(
    character_id: str,
    req: CharacterGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    提交角色头像生成任务到 Celery
    """
    from src.tasks.task import movie_generate_character_avatar
    task = movie_generate_character_avatar.delay(character_id, req.api_key_id, req.model, req.prompt, req.style)
    return {"task_id": task.id, "message": "角色头像生成任务已提交"}

@router.post("/scripts/{script_id}/generate-keyframes", summary="生成剧本分镜首帧图")
async def generate_keyframes(
    script_id: str,
    req: KeyframeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    提交剧本分镜首帧图批量生成任务到 Celery
    """
    from src.tasks.task import movie_generate_keyframes
    task = movie_generate_keyframes.delay(script_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "分镜首帧生成任务已提交"}

@router.post("/shots/{shot_id}/produce", summary="启动单个镜头的视频生产")
async def produce_shot(
    shot_id: str, 
    req: ShotProduceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    提交镜头的视频生产任务到 Celery
    """
    from src.tasks.task import movie_produce_shot
    task = movie_produce_shot.delay(shot_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "视频生产任务已提交"}

@router.post("/scripts/{script_id}/batch-produce", summary="批量生产剧本下分镜视频")
async def batch_produce_videos(
    script_id: str,
    req: ShotProduceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    提交剧本所有分镜的批量视频生产任务到 Celery
    """
    from src.tasks.task import movie_batch_produce_shots
    task = movie_batch_produce_shots.delay(script_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "批量视频生产任务已提交"}

@router.post("/shots/{shot_id}/regenerate-keyframe", summary="重新生成单个分镜首帧")
async def regenerate_keyframe(
    shot_id: str,
    req: KeyframeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    强制重新生成某个分镜的首帧 (异步)
    """
    from src.tasks.task import movie_regenerate_keyframe
    task = movie_regenerate_keyframe.delay(shot_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "首帧重制任务已提交"}

@router.post("/shots/{shot_id}/regenerate-last-frame", summary="重新生成单个分镜尾帧")
async def regenerate_last_frame(
    shot_id: str,
    req: KeyframeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    强制重新生成某个分镜的尾帧 (异步)
    """
    from src.tasks.task import movie_regenerate_last_frame
    task = movie_regenerate_last_frame.delay(shot_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "尾帧重制任务已提交"}

@router.post("/shots/{shot_id}/regenerate-video", summary="重新生成单个分镜视频")
async def regenerate_video(
    shot_id: str,
    req: ShotProduceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    强制重新启动某个分镜的视频生产 (异步)
    """
    from src.tasks.task import movie_produce_shot
    task = movie_produce_shot.delay(shot_id, req.api_key_id, req.model, force=True)
    return {"task_id": task.id, "message": "视频重制任务已提交"}
