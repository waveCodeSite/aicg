"""
文件处理Celery任务模块 - 异步文件处理、状态跟踪与容错优化版本
"""

import asyncio
import traceback
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, TypeVar

from celery import Celery, Task

from src.core.config import settings
from src.core.database import get_async_db
from src.core.logging import get_logger
from src.services.project_processing import project_processing_service

logger = get_logger(__name__)
T = TypeVar("T")

# 创建Celery实例
celery_app = Celery(
    "file_processing",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=getattr(settings, "CELERY_TASK_TIME_LIMIT", 600),
    task_soft_time_limit=getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT", 480),
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ---------------------------
# 辅助函数与装饰器
# ---------------------------

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """同步上下文中运行异步协程"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def async_celery_task(fn: Callable[..., Coroutine[Any, Any, Dict[str, Any]]]):
    """包装异步 Celery 任务执行"""

    def wrapper(self: Task, *args, **kwargs):
        task_id = self.request.id
        task_name = fn.__name__
        try:
            logger.info(f"开始执行任务: {task_name} (ID: {task_id}) 参数: {args}, {kwargs}")
            result = run_async(fn(*args, **kwargs))
            logger.info(f"任务完成: {task_name} (ID: {task_id}) 结果: {result}")
            return result
        except Exception as exc:
            logger.error(f"任务执行失败: {task_name} (ID: {task_id}), 错误: {exc}")
            logger.error(traceback.format_exc())

            if hasattr(self.request, "retries") and self.request.retries < 3:
                delay = 60 * (self.request.retries + 1)
                logger.info(f"任务重试中 ({self.request.retries + 1}/3)... 延迟: {delay}s")
                raise self.retry(countdown=delay, exc=exc)

            return {"success": False, "error": str(exc), "task_id": task_id}

    return celery_app.task(bind=True, name=fn.__name__)(wrapper)


# ---------------------------
# 核心任务实现
# ---------------------------

@async_celery_task
async def process_uploaded_file(project_id: str, owner_id: str) -> Dict[str, Any]:
    """处理上传文件"""
    try:
        async with get_async_db() as db:
            async with db.begin():
                content = await _get_file_content(project_id)
                result = await project_processing_service.process_uploaded_file(
                    db_session=db, project_id=project_id, file_content=content
                )

                # 如果处理失败，在事务外更新失败状态
                if not result.get('success', True):
                    raise Exception(result.get('error', '文件处理失败'))

                return result

    except Exception as e:
        # 在新的会话中更新失败状态，避免事务中止问题
        try:
            async with get_async_db() as db:
                await _mark_project_failed_direct(db, project_id, owner_id, f"文件处理失败: {e}")
        except Exception as db_error:
            logger.error(f"更新项目失败状态时出错: {db_error}")

        raise Exception(f"文件处理失败: {e}")


@async_celery_task
async def get_processing_status(project_id: str, owner_id: str) -> Dict[str, Any]:
    """获取处理状态"""
    async with get_async_db() as db:
        return await project_processing_service.get_processing_status(db, project_id)


@async_celery_task
async def retry_failed_project(project_id: str, owner_id: str) -> Dict[str, Any]:
    """重试失败的项目"""
    from src.services.project import ProjectService

    async with get_async_db() as db:
        service = ProjectService(db)
        project = await service.get_project_by_id(project_id, owner_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        if project.status != "failed":
            return {"success": False, "message": f"项目不是失败状态: {project.status}"}

        # 重置状态
        project.status = "uploaded"
        project.error_message = None
        project.processing_progress = 0
        await db.commit()

        content = await _get_file_content(project_id)
        return await project_processing_service.process_uploaded_file(
            db_session=db, project_id=project_id, file_content=content
        )


@async_celery_task
async def health_check() -> Dict[str, Any]:
    """健康检查"""

    async def test_db():
        from sqlalchemy import text
        async with get_async_db() as db:
            result = await db.execute(text("SELECT 1"))
            return result.scalar() == 1

    healthy = False
    try:
        healthy = await test_db()
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")

    return {
        "success": True,
        "celery_status": "running",
        "database_status": "healthy" if healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "文件处理服务运行正常",
    }


# ---------------------------
# 辅助逻辑
# ---------------------------

async def _get_file_content(project_id: str) -> str:
    """从存储中读取文件"""
    from src.models.project import Project
    from src.utils.storage import get_storage_client

    async with get_async_db() as db:
        project = await db.get(Project, project_id)
        if not project or not project.file_path:
            raise ValueError(f"项目或文件路径无效: {project_id}")

        storage = await get_storage_client()
        data = await storage.download_file(project.file_path)

        # 尝试多种编码方式
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'latin-1']
        content = None
        for encoding in encodings:
            try:
                content = data.decode(encoding)
                logger.info(f"成功下载文件: {project.file_path}, 使用编码: {encoding}, 内容长度: {len(content)}")
                return content
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，使用错误处理并清理非UTF8字符
        content = data.decode('utf-8', errors='replace')
        # 清理可能的问题字符，确保只包含有效的UTF-8字符
        import re
        # 移除控制字符（除了换行、制表符等常用字符）
        content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
        logger.warning(f"文件编码异常，使用UTF-8替换模式并清理字符: {project.file_path}, 内容长度: {len(content)}")
        return content


async def _mark_project_failed(project_id: str, owner_id: str, message: str):
    """统一更新项目失败状态"""
    from src.services.project import ProjectService
    async with get_async_db() as db:
        service = ProjectService(db)
        await service.mark_processing_failed(project_id, owner_id, message)
        logger.warning(f"项目标记为失败: {project_id}, 原因: {message}")


async def _mark_project_failed_direct(db_session, project_id: str, owner_id: str, message: str):
    """直接更新项目失败状态（在已有会话中使用）"""
    from src.services.project import ProjectService
    service = ProjectService(db_session)
    await service.mark_processing_failed(project_id, owner_id, message)
    logger.warning(f"项目标记为失败: {project_id}, 原因: {message}")


__all__ = [
    "celery_app",
    "process_uploaded_file",
    "get_processing_status",
    "retry_failed_project",
    "health_check",
]

if __name__ == "__main__":
    print("开始测试任务...")

    # 🔹 直接执行异步逻辑，不经过 Celery 封装
    result = run_async(
        process_uploaded_file.run(
            "c863bed8-da9a-4b9a-aa05-ee4889cc7ea3",
            "6c11cb2b-d499-4f81-8196-3ea078e9f66a",
        )
    )

    print(f"处理结果: {result}")
