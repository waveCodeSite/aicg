"""
项目管理服务 - 简洁实现，严格按照data-model.md规范
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.project import Project, ProjectStatus

logger = get_logger(__name__)


class ProjectServiceError(Exception):
    """项目服务异常"""
    pass


class ProjectService:
    """项目管理服务 - 简洁实现"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_project(
            self,
            owner_id: str,
            title: str,
            description: Optional[str] = None,
            file_name: Optional[str] = None,
            file_size: Optional[int] = 0,
            file_type: Optional[str] = "txt",
            file_path: Optional[str] = "",
            file_hash: Optional[str] = None
    ) -> Project:
        """
        创建新项目

        Args:
            owner_id: 所有者用户ID
            title: 项目标题
            description: 项目描述
            file_name: 文件名称
            file_size: 文件大小（字节）
            file_type: 文件类型
            file_path: MinIO存储路径
            file_hash: 文件MD5哈希

        Returns:
            创建的项目
        """
        try:
            project = await Project.create_project(
                db_session=self.db_session,
                owner_id=owner_id,
                title=title,
                description=description,
                file_name=file_name or f"project_{title}",
                file_size=file_size,
                file_type=file_type,
                file_path=file_path,
                file_hash=file_hash
            )

            await self.db_session.commit()
            await self.db_session.refresh(project)

            logger.info(f"创建项目成功: {project.id}, 所有者: {owner_id}")
            return project

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"创建项目失败: {e}")
            raise ProjectServiceError(f"创建项目失败: {str(e)}")

    async def get_project_by_id(
            self,
            project_id: str,
            owner_id: Optional[str] = None
    ) -> Optional[Project]:
        """
        根据ID获取项目

        Args:
            project_id: 项目ID
            owner_id: 所有者ID（可选，用于权限检查）

        Returns:
            项目信息
        """
        try:
            query = select(Project).filter(Project.id == project_id)

            if owner_id:
                query = query.filter(Project.owner_id == owner_id)

            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"获取项目失败: {e}")
            return None

    async def get_owner_projects(
            self,
            owner_id: str,
            status: Optional[ProjectStatus] = None,
            page: int = 1,
            size: int = 20,
            search: Optional[str] = None,
            sort_by: str = "created_at",
            sort_order: str = "desc"
    ) -> Tuple[List[Project], int]:
        """
        获取用户的项目列表

        Args:
            owner_id: 所有者ID
            status: 项目状态过滤
            page: 页码
            size: 每页大小
            search: 搜索关键词
            sort_by: 排序字段
            sort_order: 排序顺序

        Returns:
            项目列表和总数
        """
        try:
            # 构建查询
            query = select(Project).filter(Project.owner_id == owner_id)

            # 状态过滤
            if status:
                query = query.filter(Project.status == status.value)

            # 搜索过滤
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Project.title.ilike(search_term),
                        Project.description.ilike(search_term),
                        Project.file_name.ilike(search_term)
                    )
                )

            # 获取总数
            count_query = select(func.count(Project.id)).filter(Project.owner_id == owner_id)

            if status:
                count_query = count_query.filter(Project.status == status.value)

            if search:
                search_term = f"%{search}%"
                count_query = count_query.filter(
                    or_(
                        Project.title.ilike(search_term),
                        Project.description.ilike(search_term),
                        Project.file_name.ilike(search_term)
                    )
                )

            total_result = await self.db_session.execute(count_query)
            total = total_result.scalar()

            # 排序
            if hasattr(Project, sort_by):
                sort_column = getattr(Project, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
            else:
                query = query.order_by(desc(Project.created_at))

            # 分页
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)

            result = await self.db_session.execute(query)
            projects = result.scalars().all()

            return list(projects), total

        except Exception as e:
            logger.error(f"获取用户项目失败: {e}")
            raise ProjectServiceError(f"获取用户项目失败: {str(e)}")

    async def update_project(
            self,
            project_id: str,
            owner_id: str,
            **updates
    ) -> Optional[Project]:
        """
        更新项目信息

        Args:
            project_id: 项目ID
            owner_id: 所有者ID
            **updates: 更新字段

        Returns:
            更新后的项目
        """
        try:
            project = await self.get_project_by_id(project_id, owner_id)
            if not project:
                raise ProjectServiceError(f"项目不存在或无权限: {project_id}")

            # 更新字段
            for field, value in updates.items():
                if hasattr(project, field):
                    setattr(project, field, value)

            await self.db_session.commit()
            await self.db_session.refresh(project)

            logger.info(f"更新项目成功: {project_id}")
            return project

        except ProjectServiceError:
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"更新项目失败: {e}")
            raise ProjectServiceError(f"更新项目失败: {str(e)}")

    async def archive_project(
            self,
            project_id: str,
            owner_id: str
    ) -> Optional[Project]:
        """
        归档项目（不可逆操作）

        Args:
            project_id: 项目ID
            owner_id: 所有者ID

        Returns:
            归档后的项目
        """
        try:
            project = await self.get_project_by_id(project_id, owner_id)
            if not project:
                raise ProjectServiceError(f"项目不存在或无权限: {project_id}")

            # 检查是否已归档
            if project.is_archived():
                raise ProjectServiceError(f"项目已经归档: {project_id}")

            # 执行归档操作
            project.archive_project()
            await self.db_session.commit()
            await self.db_session.refresh(project)

            logger.info(f"归档项目成功: {project_id}")
            return project

        except ProjectServiceError:
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"归档项目失败: {e}")
            raise ProjectServiceError(f"归档项目失败: {str(e)}")

    async def delete_project(
            self,
            project_id: str,
            owner_id: str
    ) -> bool:
        """
        删除项目

        Args:
            project_id: 项目ID
            owner_id: 所有者ID

        Returns:
            是否删除成功
        """
        try:
            project = await self.get_project_by_id(project_id, owner_id)
            if not project:
                raise ProjectServiceError(f"项目不存在或无权限: {project_id}")

            await self.db_session.delete(project)
            await self.db_session.commit()

            logger.info(f"删除项目成功: {project_id}")
            return True

        except ProjectServiceError:
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"删除项目失败: {e}")
            raise ProjectServiceError(f"删除项目失败: {str(e)}")

    async def get_project_statistics(self, owner_id: str) -> Dict[str, Any]:
        """
        获取用户项目统计信息

        Args:
            owner_id: 所有者ID

        Returns:
            统计信息
        """
        try:
            # 总项目数
            total_query = select(func.count(Project.id)).filter(Project.owner_id == owner_id)
            total_result = await self.db_session.execute(total_query)
            total_projects = total_result.scalar()

            # 按状态分组统计
            status_query = select(
                Project.status,
                func.count(Project.id)
            ).filter(Project.owner_id == owner_id).group_by(Project.status)

            status_result = await self.db_session.execute(status_query)
            status_stats = {row[0]: row[1] for row in status_result}

            # 按文件类型统计
            file_type_query = select(
                Project.file_type,
                func.count(Project.id)
            ).filter(
                Project.owner_id == owner_id,
                Project.file_type.isnot(None)
            ).group_by(Project.file_type)

            file_type_result = await self.db_session.execute(file_type_query)
            file_type_stats = {row[0]: row[1] for row in file_type_result}

            return {
                "total_projects": total_projects or 0,
                "status_distribution": status_stats,
                "file_type_distribution": file_type_stats,
            }

        except Exception as e:
            logger.error(f"获取项目统计失败: {e}")
            return {}

    async def update_processing_progress(self, project_id: str, owner_id: str, progress: int) -> Optional[Project]:
        """
        更新项目处理进度

        Args:
            project_id: 项目ID
            owner_id: 所有者ID
            progress: 进度百分比 (0-100)

        Returns:
            更新后的项目
        """
        try:
            project = await self.get_project_by_id(project_id, owner_id)
            if not project:
                raise ProjectServiceError(f"项目不存在或无权限: {project_id}")

            # 更新进度
            project.update_processing_progress(progress)

            await self.db_session.commit()
            await self.db_session.refresh(project)

            logger.info(f"更新项目进度: {project_id} -> {progress}%")
            return project

        except ProjectServiceError:
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"更新项目进度失败: {e}")
            raise ProjectServiceError(f"更新项目进度失败: {str(e)}")

    async def mark_processing_failed(self, project_id: str, owner_id: str, error_message: str) -> Optional[Project]:
        """
        标记项目处理失败

        Args:
            project_id: 项目ID
            owner_id: 所有者ID
            error_message: 错误信息

        Returns:
            更新后的项目
        """
        try:
            project = await self.get_project_by_id(project_id, owner_id)
            if not project:
                raise ProjectServiceError(f"项目不存在或无权限: {project_id}")

            # 标记失败
            project.mark_as_failed(error_message)

            await self.db_session.commit()
            await self.db_session.refresh(project)

            logger.info(f"标记项目处理失败: {project_id}")
            return project

        except ProjectServiceError:
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"标记项目处理失败: {e}")
            raise ProjectServiceError(f"标记项目处理失败: {str(e)}")

    async def mark_processing_completed(self, project_id: str, owner_id: str) -> Optional[Project]:
        """
        标记项目处理完成

        Args:
            project_id: 项目ID
            owner_id: 所有者ID

        Returns:
            更新后的项目
        """
        try:
            project = await self.get_project_by_id(project_id, owner_id)
            if not project:
                raise ProjectServiceError(f"项目不存在或无权限: {project_id}")

            # 标记完成
            project.mark_as_completed()

            await self.db_session.commit()
            await self.db_session.refresh(project)

            logger.info(f"标记项目处理完成: {project_id}")
            return project

        except ProjectServiceError:
            raise
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"标记项目处理完成失败: {e}")
            raise ProjectServiceError(f"标记项目处理完成失败: {str(e)}")


__all__ = [
    "ProjectService",
    "ProjectServiceError",
]
