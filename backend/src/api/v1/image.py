"""
图片生成 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.image import ImageGenerateRequest, ImageGenerateResponse
from src.core.database import get_db
from src.core.exceptions import NotFoundError, BusinessLogicError
from src.core.logging import get_logger
from src.models.chapter import Chapter, ChapterStatus
from src.models.user import User
from src.services.project import ProjectService
from src.tasks.task import generate_images

logger = get_logger(__name__)

router = APIRouter()


@router.post("/generate-images", response_model=ImageGenerateResponse)
async def generate_images_api(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        request: ImageGenerateRequest
):
    """
    为章节批量生成图片
    
    根据章节中每个句子的提示词，调用AI图像生成服务生成图片。
    """
    # 1. 获取章节并验证权限
    stmt = select(Chapter).where(Chapter.id == request.chapter_id)
    result = await db.execute(stmt)
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise NotFoundError(
            "章节不存在",
            resource_type="chapter",
            resource_id=str(request.chapter_id)
        )

    if chapter.status != ChapterStatus.PROMPTS_GENERATED.value:
        raise BusinessLogicError(message=f"任务当前状态为：{chapter.status}，请先生成提示词")

    # 验证项目权限
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    # 2. 投递任务到celery
    result = generate_images.delay(chapter.id.hex, request.api_key_id.hex)

    # 3.更新章节状态为图片生成中
    chapter.status = ChapterStatus.IMAGES_GENERATING.value
    await db.flush()
    await db.commit()

    logger.info(f"成功为章节 {request.chapter_id} 投递图片生成任务，任务ID: {result.id}")
    return ImageGenerateResponse(success=True, message="图片生成任务已提交")


__all__ = ["router"]