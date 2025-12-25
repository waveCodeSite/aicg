"""
项目管理服务 - 简洁实现，严格按照data-model.md规范

提供服务：
- 项目的创建、查询、更新、删除
- 项目状态管理
- 项目统计信息
- 处理进度跟踪

设计原则：
- 使用BaseService统一管理数据库会话
- 异常处理遵循统一策略
- 方法职责单一，保持简洁
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BusinessLogicError, NotFoundError
from src.core.logging import get_logger
from src.models.project import Project, ProjectStatus, ProjectType
from src.services.base import BaseService

logger = get_logger(__name__)


class ProjectService(BaseService):
    """
    项目管理服务

    负责项目的完整生命周期管理，包括创建、查询、更新、删除和状态管理。
    所有数据库操作都通过基类提供的会话管理功能进行。

    使用方式：
        # 在API中（通过依赖注入）：
        @router.post("/projects")
        async def create_project(project_data: ProjectCreate,
                                db: AsyncSession = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
            project_service = ProjectService(db)
            return await project_service.create_project(...)

        # 在后台任务中（独立会话管理）：
        async def process_project():
            async with ProjectService() as service:
                project = await service.get_project_by_id(...)
                # 自动管理会话和事务
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        初始化项目管理服务

        Args:
            db_session: 可选的数据库会话。在FastAPI中通常通过依赖注入提供，
                       在后台任务中可以不提供，让服务自己管理会话
        """
        super().__init__(db_session)
        logger.debug(f"ProjectService 初始化完成，会话管理: {'外部注入' if db_session else '自管理'}")

    async def create_project(
            self,
            owner_id: str,
            title: str,
            description: Optional[str] = None,
            file_name: Optional[str] = None,
            file_size: Optional[int] = 0,
            file_type: Optional[str] = "txt",
            file_path: Optional[str] = "",
            file_hash: Optional[str] = None,
            project_type: ProjectType = ProjectType.PICTURE_NARRATIVE
    ) -> Project:
        """
        创建新项目

        创建一个新项目并初始化基本信息。如果提供文件相关信息，将一并设置。
        操作会自动包含在事务中，失败时回滚。

        Args:
            owner_id: 所有者用户ID
            title: 项目标题，必填，最大200字符
            description: 项目描述，可选
            file_name: 上传的文件名称
            file_size: 文件大小（字节）
            file_type: 文件类型，默认为"txt"
            file_path: MinIO存储路径
            file_hash: 文件MD5哈希，用于去重检查

        Returns:
            Project: 创建成功的项目对象，包含生成的ID和创建时间

        Raises:
            ValidationError: 当参数验证失败时
            DatabaseError: 当数据库操作失败时
        """
        try:
            # 创建项目对象（使用flush获取ID）
            project = Project(
                owner_id=owner_id,
                title=title,
                description=description,
                file_name=file_name or f"project_{title}",
                file_size=file_size,
                file_type=file_type,
                file_path=file_path,
                file_hash=file_hash,
                type=project_type,
                status=ProjectStatus.UPLOADED
            )

            self.add(project)
            await self.flush()  # 获取数据库生成的ID

            # 提交事务
            await self.commit()
            await self.refresh(project)  # 确保获取最新数据

            logger.info(f"创建项目成功: ID={project.id}, 标题={title}, 所有者={owner_id}")
            return project

        except Exception:
            await self.rollback()
            raise  # 重新抛出异常，由中间件处理

    async def create_project_from_text(
            self,
            owner_id: str,
            title: str,
            content: str,
            description: Optional[str] = None,
            project_type: ProjectType = ProjectType.PICTURE_NARRATIVE
    ) -> Project:
        """
        从文本内容创建项目

        将文本内容转换为文件并上传到MinIO，然后创建项目。

        Args:
            owner_id: 所有者用户ID
            title: 项目标题
            content: 文本内容
            description: 项目描述，可选

        Returns:
            Project: 创建成功的项目对象

        Raises:
            ValidationError: 当参数验证失败时
            DatabaseError: 当数据库操作失败时
        """
        import hashlib
        import os
        import tempfile
        from fastapi import UploadFile
        from src.utils.storage import get_storage_client

        try:
            # 1. 生成文件hash
            file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            file_size = len(content.encode('utf-8'))

            # 2. 创建临时文件
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                suffix='.txt',
                delete=False
            ) as f:
                f.write(content)
                temp_path = f.name

            try:
                # 3. 上传到MinIO
                storage_client = await get_storage_client()

                with open(temp_path, 'rb') as f:
                    # 生成安全的文件名
                    safe_title = "".join(
                        c for c in title if c.isalnum() or c in (' ', '-', '_')
                    ).strip()[:50]
                    if not safe_title:
                        safe_title = "project"

                    # 确保文件指针在开头
                    f.seek(0)
                    
                    upload_file = UploadFile(
                        filename=f"{safe_title}.txt",
                        file=f
                    )
                    result = await storage_client.upload_file(
                        user_id=owner_id,
                        file=upload_file,
                        metadata={
                            "user_id": owner_id,
                            "file_type": "text/plain",
                            "original_filename": f"{safe_title}.txt",
                            "created_from": "text_import"
                        }
                    )

                # 4. 创建项目
                project = await self.create_project(
                    owner_id=owner_id,
                    title=title,
                    description=description or "通过文本导入创建",
                    file_name=f"{safe_title}.txt",
                    file_size=file_size,
                    file_type="txt",
                    file_path=result["object_key"],
                    file_hash=file_hash,
                    project_type=project_type
                )

                logger.info(
                    f"从文本创建项目成功: ID={project.id}, 标题={title}, "
                    f"文本长度={len(content)}, 所有者={owner_id}"
                )
                return project

            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception:
            await self.rollback()
            raise

    async def get_project_by_id(
            self,
            project_id: str,
            owner_id: Optional[str] = None
    ) -> Project:
        """
        根据ID获取项目

        查询指定ID的项目，可选择进行所有者权限验证。

        Args:
            project_id: 项目ID，必须是有效的UUID格式
            owner_id: 所有者ID，可选。如果提供，将验证项目是否属于该用户

        Returns:
            Project: 查询到的项目对象

        Raises:
            NotFoundError: 当项目不存在或无权限访问时
            ValidationError: 当project_id格式无效时
        """
        query = select(Project).filter(Project.id == project_id)
        if owner_id:
            query = query.filter(Project.owner_id == owner_id)

        result = await self.execute(query)
        project = result.scalar_one_or_none()

        if not project:
            error_message = f"项目不存在或无权限访问" if owner_id else "项目不存在"
            raise NotFoundError(
                error_message,
                resource_type="project",
                resource_id=project_id
            )

        logger.debug(f"获取项目成功: ID={project_id}, 标题={project.title}")
        return project

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
        获取用户的项目列表（分页）

        支持多种过滤条件、搜索和排序方式，返回分页结果。

        Args:
            owner_id: 所有者用户ID，必填
            status: 项目状态过滤，可选。支持ProjectStatus枚举值
            page: 页码，从1开始，默认1
            size: 每页大小，默认20，最大100
            search: 搜索关键词，支持在标题、描述、文件名中搜索
            sort_by: 排序字段，默认created_at，支持title、updated_at、status等
            sort_order: 排序顺序，默认desc，支持asc/desc

        Returns:
            Tuple[List[Project], int]: (项目列表, 总记录数)

        Raises:
            ValidationError: 当分页参数无效时
            DatabaseError: 当数据库查询失败时
        """
        # 参数验证
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = min(max(size, 1), 100)

        # 构建基础查询
        query = select(Project).filter(Project.owner_id == owner_id)

        # 状态过滤
        if status:
            query = query.filter(Project.status == status.value)

        # 搜索过滤 - 在标题、描述、文件名中搜索
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Project.title.ilike(search_term),
                    Project.description.ilike(search_term),
                    Project.file_name.ilike(search_term)
                )
            )

        # 获取总数的查询（复用过滤条件）
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

        # 执行总数查询
        total_result = await self.execute(count_query)
        total = total_result.scalar()

        # 排序处理
        if hasattr(Project, sort_by):
            sort_column = getattr(Project, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        else:
            # 默认按创建时间倒序
            query = query.order_by(desc(Project.created_at))

        # 分页处理
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        # 执行主查询
        result = await self.execute(query)
        projects = result.scalars().all()

        logger.debug(f"查询项目列表: 所有者={owner_id}, 总数={total}, 当前页={page}, 数量={len(projects)}")
        return list(projects), total

    async def update_project(
            self,
            project_id: str,
            owner_id: str,
            **updates
    ) -> Project:
        """
        更新项目信息

        Args:
            project_id: 项目ID
            owner_id: 所有者ID
            **updates: 更新字段

        Returns:
            更新后的项目
        """
        project = await self.get_project_by_id(project_id, owner_id)

        # 更新字段
        for field, value in updates.items():
            if hasattr(project, field):
                setattr(project, field, value)

        await self.commit()
        await self.refresh(project)

        logger.info(f"更新项目成功: ID={project_id}, 更新字段={list(updates.keys())}")
        return project

    async def archive_project(
            self,
            project_id: str,
            owner_id: str
    ) -> Project:
        """
        归档项目（不可逆操作）

        Args:
            project_id: 项目ID
            owner_id: 所有者ID

        Returns:
            归档后的项目
        """
        project = await self.get_project_by_id(project_id, owner_id)

        # 检查是否已归档
        if project.is_archived():
            raise BusinessLogicError(
                message="项目已经归档",
                business_rule="archive_validation",
                context={"project_id": project_id, "current_status": project.status}
            )

        # 执行归档操作
        project.archive_project()
        await self.commit()
        await self.refresh(project)

        logger.info(f"归档项目成功: ID={project_id}, 标题={project.title}")
        return project

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
        project = await self.get_project_by_id(project_id, owner_id)

        self.delete(project)
        await self.commit()

        logger.info(f"删除项目成功: ID={project_id}, 标题={project.title}")
        return True

    async def get_project_statistics(self, owner_id: str) -> Dict[str, Any]:
        """
        获取用户项目统计信息

        Args:
            owner_id: 所有者ID

        Returns:
            统计信息
        """
        # 总项目数
        total_query = select(func.count(Project.id)).filter(Project.owner_id == owner_id)
        total_result = await self.execute(total_query)
        total_projects = total_result.scalar()

        # 按状态分组统计
        status_query = select(
            Project.status,
            func.count(Project.id)
        ).filter(Project.owner_id == owner_id).group_by(Project.status)

        status_result = await self.execute(status_query)
        status_stats = {row[0]: row[1] for row in status_result}

        # 按文件类型统计
        file_type_query = select(
            Project.file_type,
            func.count(Project.id)
        ).filter(
            Project.owner_id == owner_id,
            Project.file_type.isnot(None)
        ).group_by(Project.file_type)

        file_type_result = await self.execute(file_type_query)
        file_type_stats = {row[0]: row[1] for row in file_type_result}

        return {
            "total_projects": total_projects or 0,
            "status_distribution": status_stats,
            "file_type_distribution": file_type_stats,
        }

    async def update_processing_progress(self, project_id: str, owner_id: str, progress: int) -> Project:
        """
        更新项目处理进度

        Args:
            project_id: 项目ID
            owner_id: 所有者ID
            progress: 进度百分比 (0-100)

        Returns:
            更新后的项目
        """
        project = await self.get_project_by_id(project_id, owner_id)

        # 更新进度
        project.update_processing_progress(progress)

        await self.commit()
        await self.refresh(project)

        logger.info(f"更新项目进度: ID={project_id}, 进度={progress}%")
        return project

    async def mark_processing_failed(self, project_id: str, owner_id: str, error_message: str) -> Project:
        """
        标记项目处理失败

        Args:
            project_id: 项目ID
            owner_id: 所有者ID
            error_message: 错误信息

        Returns:
            更新后的项目
        """
        project = await self.get_project_by_id(project_id, owner_id)

        # 标记失败
        project.mark_as_failed(error_message)

        await self.commit()
        await self.refresh(project)

        logger.info(f"标记项目处理失败: ID={project_id}, 错误={error_message[:50]}...")
        return project

    async def mark_processing_completed(self, project_id: str, owner_id: str) -> Project:
        """
        标记项目处理完成

        Args:
            project_id: 项目ID
            owner_id: 所有者ID

        Returns:
            更新后的项目
        """
        project = await self.get_project_by_id(project_id, owner_id)

        # 标记完成
        project.mark_as_completed()

        await self.commit()
        await self.refresh(project)

        logger.info(f"标记项目处理完成: ID={project_id}")
        return project


__all__ = [
    "ProjectService",
]
