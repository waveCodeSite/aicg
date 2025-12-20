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
    ShotProduceRequest, CharacterUpdateRequest
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
    # 这里的逻辑比较简单，直接 dispatch 任务，也可以移入 Service
    task = movie_produce_shot.delay(shot_id, req.api_key_id, req.model)
    return {"task_id": task.id, "message": "视频生产任务已提交"}
