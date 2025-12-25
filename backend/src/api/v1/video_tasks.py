"""
视频任务管理API
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.video_task import (
    VideoTaskCreate,
    VideoTaskDeleteResponse,
    VideoTaskListResponse,
    VideoTaskResponse,
    VideoTaskRetryResponse,
    VideoTaskStatsResponse,
)
from src.core.database import get_db
from src.core.logging import get_logger
from src.models.user import User
from src.models.video_task import VideoTaskStatus
from src.services.video_task import VideoTaskService
from src.services.chapter import ChapterService
from src.services.project import ProjectService
from src.tasks.generate import synthesize_video

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=VideoTaskResponse)
async def create_video_task(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        task_data: VideoTaskCreate
):
    """创建视频生成任务"""
    from src.models.video_task import VideoTaskType
    
    video_task_service = VideoTaskService(db)
    chapter_service = ChapterService(db)
    project_service = ProjectService(db)

    # 获取章节并验证权限
    chapter = await chapter_service.get_chapter_by_id(str(task_data.chapter_id))
    await project_service.get_project_by_id(str(chapter.project_id), str(current_user.id))

    # 创建任务
    task = await video_task_service.create_video_task(
        user_id=str(current_user.id),
        project_id=str(chapter.project_id),
        chapter_id=str(task_data.chapter_id),
        task_type=task_data.task_type,
        api_key_id=str(task_data.api_key_id) if task_data.api_key_id else None,
        bgm_id=str(task_data.bgm_id) if task_data.bgm_id else None,
        gen_setting=task_data.gen_setting
    )

    # 根据任务类型触发不同的Celery任务
    if task_data.task_type == VideoTaskType.MOVIE_COMPOSITION.value:
        from src.tasks.movie_composition import movie_compose_video
        movie_compose_video.delay(str(task.id))
    else:
        # 默认：图解说视频
        synthesize_video.delay(str(task.id))

    # 获取章节和项目标题
    response_data = task.to_dict()
    response_data['chapter_title'] = chapter.title
    response_data['project_title'] = (await project_service.get_project_by_id(str(chapter.project_id), str(current_user.id))).title

    return VideoTaskResponse.from_dict(response_data)



@router.get("/", response_model=VideoTaskListResponse)
async def get_video_tasks(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(20, ge=1, le=100, description="每页大小"),
        status: Optional[str] = Query(None, description="状态过滤"),
        chapter_id: Optional[str] = Query(None, description="章节ID过滤"),
        project_id: Optional[str] = Query(None, description="项目ID过滤"),
        sort_by: str = Query("created_at", description="排序字段"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序")
):
    """获取用户的视频任务列表"""
    video_task_service = VideoTaskService(db)

    # 处理状态过滤
    status_filter = None
    if status and status.strip():
        try:
            status_filter = VideoTaskStatus(status.strip())
        except ValueError:
            logger.warning(f"无效的任务状态: {status}")

    tasks, total = await video_task_service.list_user_tasks(
        user_id=str(current_user.id),
        page=page,
        size=size,
        status=status_filter,
        chapter_id=chapter_id,
        project_id=project_id,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # 转换为响应模型
    task_responses = []
    for task in tasks:
        task_dict = task.to_dict()
        if task.chapter:
            task_dict['chapter_title'] = task.chapter.title
        if task.project:
            task_dict['project_title'] = task.project.title
        task_responses.append(VideoTaskResponse.from_dict(task_dict))
    total_pages = (total + size - 1) // size

    return VideoTaskListResponse(
        tasks=task_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=VideoTaskStatsResponse)
async def get_video_task_stats(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db)
):
    """获取用户的视频任务统计信息"""
    video_task_service = VideoTaskService(db)
    stats = await video_task_service.get_task_stats(str(current_user.id))
    return VideoTaskStatsResponse(**stats)


@router.get("/{task_id}", response_model=VideoTaskResponse)
async def get_video_task(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        task_id: str
):
    """获取视频任务详情"""
    video_task_service = VideoTaskService(db)
    task = await video_task_service.get_video_task_by_id(task_id)

    # 验证权限
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此任务"
        )

    # 获取关联信息
    response_data = task.to_dict()
    
    # 获取章节和项目信息
    try:
        chapter_service = ChapterService(db)
        chapter = await chapter_service.get_chapter_by_id(str(task.chapter_id))
        response_data['chapter_title'] = chapter.title
        
        project_service = ProjectService(db)
        project = await project_service.get_project_by_id(str(chapter.project_id), str(current_user.id))
        response_data['project_title'] = project.title
    except Exception as e:
        logger.warning(f"获取关联信息失败: {e}")

    return VideoTaskResponse.from_dict(response_data)


@router.delete("/{task_id}", response_model=VideoTaskDeleteResponse)
async def delete_video_task(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        task_id: str
):
    """删除视频任务"""
    video_task_service = VideoTaskService(db)
    task = await video_task_service.get_video_task_by_id(task_id)

    # 验证权限
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此任务"
        )

    # 删除任务
    await video_task_service.delete_video_task(task_id)

    return VideoTaskDeleteResponse(
        success=True,
        message="删除成功",
        task_id=task_id
    )


@router.post("/{task_id}/retry", response_model=VideoTaskRetryResponse)
async def retry_video_task(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        task_id: str
):
    """重试失败的视频任务"""
    video_task_service = VideoTaskService(db)
    task = await video_task_service.get_video_task_by_id(task_id)

    # 验证权限
    if str(task.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权重试此任务"
        )

    # 只有失败的任务才能重试
    if task.status != VideoTaskStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有失败的任务才能重试"
        )

    # 重置任务状态
    retried_task = await video_task_service.retry_task(task_id)

    # 重新触发Celery任务
    synthesize_video.delay(task_id)

    response_data = retried_task.to_dict()
    return VideoTaskRetryResponse(
        success=True,
        message="任务已重新提交",
        task=VideoTaskResponse.from_dict(response_data)
    )


__all__ = ["router"]
