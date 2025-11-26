"""
章节管理API - 使用schemas模块中的Pydantic模型
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.api.schemas.chapter import (ChapterConfirmResponse, ChapterCreate, ChapterDeleteResponse, ChapterListResponse,
                                     ChapterResponse,
                                     ChapterStatusResponse, ChapterUpdate)
from src.core.database import get_db
from src.core.logging import get_logger
from src.models.chapter import ChapterStatus as ModelChapterStatus
from src.models.user import User
from src.services.chapter import ChapterService
from src.services.project import ProjectService

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=ChapterListResponse)
async def get_chapters(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        project_id: str = Query(..., description="项目ID"),
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(20, ge=1, le=100, description="每页大小"),
        chapter_status: Optional[str] = Query("", description="状态过滤"),
        is_confirmed: Optional[bool] = Query(None, description="是否已确认过滤"),
        search: Optional[str] = Query("", description="搜索关键词"),
        sort_by: str = Query("chapter_number", description="排序字段"),
        sort_order: str = Query("asc", regex="^(asc|desc)$", description="排序顺序")
):
    """获取项目的章节列表"""
    chapter_service = ChapterService(db)
    project_service = ProjectService(db)

    # 验证项目权限
    await project_service.get_project_by_id(project_id, current_user.id)

    # 处理过滤参数
    status_filter = None
    if chapter_status and chapter_status.strip():
        try:
            status_filter = ModelChapterStatus(chapter_status.strip())
        except ValueError:
            logger.warning(f"无效的章节状态: {chapter_status}")

    search_query = None
    if search and search.strip():
        search_query = search.strip()

    chapters, total = await chapter_service.get_project_chapters(
        project_id=project_id,
        status=status_filter,
        is_confirmed=is_confirmed,
        page=page,
        size=size,
        search=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # 转换为响应模型
    chapter_responses = [ChapterResponse.from_dict(chapter.to_dict()) for chapter in chapters]
    total_pages = (total + size - 1) // size

    return ChapterListResponse(
        chapters=chapter_responses,
        total=total,
        page=page,
        size=size,
        total_pages=total_pages
    )


@router.get("/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str
):
    """获取章节详情"""
    chapter_service = ChapterService(db)
    chapter = await chapter_service.get_chapter_by_id(chapter_id)

    # 验证项目权限
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    return ChapterResponse.from_dict(chapter.to_dict())


@router.post("/", response_model=ChapterResponse)
async def create_chapter(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        project_id: str = Query(..., description="项目ID"),
        chapter_data: ChapterCreate
):
    """创建新章节"""
    chapter_service = ChapterService(db)
    project_service = ProjectService(db)

    # 验证项目权限
    await project_service.get_project_by_id(project_id, current_user.id)

    # 创建章节
    chapter = await chapter_service.create_chapter(
        project_id=project_id,
        title=chapter_data.title,
        content=chapter_data.content,
        chapter_number=chapter_data.chapter_number
    )

    return ChapterResponse.from_dict(chapter.to_dict())


@router.put("/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str,
        chapter_data: ChapterUpdate
):
    """更新章节信息"""
    chapter_service = ChapterService(db)

    # 获取章节并验证权限
    chapter = await chapter_service.get_chapter_by_id(chapter_id)
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    # 准备更新数据
    updates = {}
    if chapter_data.title is not None:
        updates['title'] = chapter_data.title
    if chapter_data.content is not None:
        updates['content'] = chapter_data.content
    if chapter_data.edited_content is not None:
        updates['edited_content'] = chapter_data.edited_content
    if chapter_data.editing_notes is not None:
        updates['editing_notes'] = chapter_data.editing_notes
    if chapter_data.chapter_number is not None:
        updates['chapter_number'] = chapter_data.chapter_number

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供更新字段"
        )

    # 更新章节
    updated_chapter = await chapter_service.update_chapter(
        chapter_id=chapter_id,
        project_id=chapter.project_id,
        **updates
    )

    return ChapterResponse.from_dict(updated_chapter.to_dict())


@router.put("/{chapter_id}/confirm", response_model=ChapterConfirmResponse)
async def confirm_chapter(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str
):
    """确认章节"""
    chapter_service = ChapterService(db)

    # 获取章节并验证权限
    chapter = await chapter_service.get_chapter_by_id(chapter_id)
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    # 确认章节
    confirmed_chapter = await chapter_service.confirm_chapter(
        chapter_id=chapter_id,
        project_id=chapter.project_id
    )

    return ChapterConfirmResponse(
        success=True,
        message="章节确认成功",
        chapter=ChapterResponse.from_dict(confirmed_chapter.to_dict())
    )


@router.delete("/{chapter_id}", response_model=ChapterDeleteResponse)
async def delete_chapter(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str
):
    """删除章节"""
    chapter_service = ChapterService(db)

    # 获取章节并验证权限
    chapter = await chapter_service.get_chapter_by_id(chapter_id)
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    # 删除章节
    await chapter_service.delete_chapter(
        chapter_id=chapter_id,
        project_id=chapter.project_id
    )

    return ChapterDeleteResponse(
        success=True,
        message="删除成功",
        chapter_id=chapter_id
    )


@router.get("/{chapter_id}/status", response_model=ChapterStatusResponse)
async def get_chapter_status(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str
):
    """获取章节的详细状态信息"""
    chapter_service = ChapterService(db)

    # 获取章节并验证权限
    chapter = await chapter_service.get_chapter_by_id(chapter_id)
    project_service = ProjectService(db)
    await project_service.get_project_by_id(chapter.project_id, current_user.id)

    # 判断操作权限
    can_edit = not chapter.is_confirmed and chapter.status in [
        ModelChapterStatus.PENDING,
        ModelChapterStatus.FAILED
    ]
    can_confirm = not chapter.is_confirmed and chapter.status == ModelChapterStatus.COMPLETED
    can_generate = chapter.is_confirmed and chapter.status == ModelChapterStatus.COMPLETED

    return ChapterStatusResponse(
        chapter=ChapterResponse.from_dict(chapter.to_dict()),
        can_edit=can_edit,
        can_confirm=can_confirm,
        can_generate=can_generate
    )


@router.get("/{chapter_id}/sentences", response_model=dict)
async def get_chapter_sentences(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        chapter_id: str
):
    """获取章节的所有句子（一次性加载，用于导演引擎）"""
    from src.api.schemas.sentence import SentenceResponse

    chapter_service = ChapterService(db)

    sentences = await chapter_service.get_sentences(chapter_id=chapter_id)

    # 转换为响应模型
    sentence_responses = [SentenceResponse.from_dict(s.to_dict()) for s in sentences]

    return {
        "sentences": sentence_responses,
        "total": len(sentence_responses)
    }


__all__ = ["router"]
