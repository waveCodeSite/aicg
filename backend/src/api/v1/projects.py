"""
项目管理API - 简洁实现，严格按照api-contracts.md规范
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required
from src.core.database import get_db
from src.core.logging import get_logger
from src.models.project import ProjectStatus
from src.models.user import User
from src.services.project import ProjectService, ProjectServiceError

logger = get_logger(__name__)

router = APIRouter()


# Pydantic模型 - 简洁定义
class ProjectCreate(BaseModel):
    """创建项目请求模型"""
    title: str = Field(..., min_length=1, max_length=200, description="项目标题")
    description: Optional[str] = Field(None, max_length=1000, description="项目描述")


class ProjectResponse(BaseModel):
    """项目响应模型"""
    id: str
    owner_id: str
    title: str
    description: Optional[str]
    file_name: str
    file_size: int
    file_type: str
    file_path: str
    file_hash: Optional[str]
    word_count: int
    chapter_count: int
    paragraph_count: int
    sentence_count: int
    status: str
    processing_progress: int
    error_message: Optional[str]
    generation_settings: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应模型"""
    projects: List[ProjectResponse]
    total: int
    page: int
    size: int
    total_pages: int


@router.get("/", response_model=ProjectListResponse)
async def get_projects(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1, description="页码"),
        size: int = Query(20, ge=1, le=100, description="每页大小"),
        project_status: Optional[str] = Query("", description="状态过滤"),
        search: Optional[str] = Query("", description="搜索关键词"),
        sort_by: str = Query("created_at", description="排序字段"),
        sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序")
):
    """获取用户的项目列表"""
    try:
        project_service = ProjectService(db)

        # 处理过滤参数
        status_filter = None
        if project_status and project_status.strip():
            try:
                status_filter = ProjectStatus(project_status.strip())
            except ValueError:
                logger.warning(f"无效的项目状态: {project_status}")

        search_query = None
        if search and search.strip():
            search_query = search.strip()

        projects, total = await project_service.get_owner_projects(
            owner_id=current_user.id,
            status=status_filter,
            page=page,
            size=size,
            search=search_query,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 转换为响应模型
        project_responses = [ProjectResponse(**project.to_dict()) for project in projects]
        total_pages = (total + size - 1) // size

        return ProjectListResponse(
            projects=project_responses,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )

    except ProjectServiceError as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取项目列表失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取项目列表异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目列表失败"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        project_id: str
):
    """获取项目详情"""
    try:
        project_service = ProjectService(db)
        project = await project_service.get_project_by_id(project_id, current_user.id)

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )

        return ProjectResponse(**project.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目详情失败"
        )


@router.post("/", response_model=ProjectResponse)
async def create_project(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        project_data: ProjectCreate
):
    """创建新项目（基础版本，不包含文件上传）"""
    try:
        project_service = ProjectService(db)
        project = await project_service.create_project(
            owner_id=current_user.id,
            title=project_data.title,
            description=project_data.description
        )

        return ProjectResponse(**project.to_dict())

    except ProjectServiceError as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建项目失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"创建项目异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建项目失败"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        project_id: str,
        project_data: ProjectCreate
):
    """更新项目信息"""
    try:
        project_service = ProjectService(db)

        updates = {}
        if project_data.title is not None:
            updates['title'] = project_data.title
        if project_data.description is not None:
            updates['description'] = project_data.description

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供更新字段"
            )

        project = await project_service.update_project(
            project_id=project_id,
            owner_id=current_user.id,
            **updates
        )

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在或无权限"
            )

        return ProjectResponse(**project.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新项目失败"
        )


@router.delete("/{project_id}")
async def delete_project(
        *,
        current_user: User = Depends(get_current_user_required),
        db: AsyncSession = Depends(get_db),
        project_id: str
):
    """删除项目"""
    try:
        project_service = ProjectService(db)
        success = await project_service.delete_project(
            project_id=project_id,
            owner_id=current_user.id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在或无权限"
            )

        return {
            "success": True,
            "message": "删除成功",
            "project_id": project_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除项目失败"
        )


__all__ = ["router"]
