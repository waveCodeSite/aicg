"""
文件处理 Celery 任务模块 - Celery 5.3+ 原生异步任务
支持自动重试、失败状态标记，同时本地测试和 Celery 使用统一函数
"""

import asyncio
import traceback
from datetime import datetime
from typing import Any, Dict

from celery import Celery

from src.core.config import settings
from src.core.database import get_async_db
from src.core.logging import get_logger
from src.models.project import Project
from src.services.project_processing import project_processing_service
from src.utils.encoding_detector import decode_file_content
from src.utils.file_handlers import get_file_handler
from src.utils.storage import get_storage_client

logger = get_logger(__name__)

# ---------------------------
# Celery 实例与配置
# ---------------------------

celery_app = Celery(
    "file_processing",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
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
)


# ---------------------------
# 核心实现函数（纯异步逻辑）
# ---------------------------

async def _process_uploaded_file_impl(project_id: str, owner_id: str) -> Dict[str, Any]:
    """核心逻辑: 处理上传文件"""
    try:
        # 使用异步上下文管理器确保正确的会话管理
        async with project_processing_service:
            # ProjectProcessingService现在独立管理数据库会话
            content = await _get_file_content(project_id)
            result = await project_processing_service.process_uploaded_file(
                project_id=project_id,
                file_content=content
            )

            if not result.get("success", True):
                raise Exception(result.get("error", "文件处理失败"))

            logger.info(f"任务成功: process_uploaded_file (project_id={project_id})")
            return result

    except Exception as e:
        await _mark_failed_safely(project_id, owner_id, f"文件处理失败: {e}")
        logger.error(traceback.format_exc())
        raise


async def _get_processing_status_impl(project_id: str) -> Dict[str, Any]:
    # ProjectProcessingService现在独立管理数据库会话
    async with project_processing_service:
        return await project_processing_service.get_processing_status(project_id)


async def _retry_failed_project_impl(project_id: str, owner_id: str) -> Dict[str, Any]:
    from src.services.project import ProjectService

    # 对于ProjectService，我们仍然需要数据库会话，因为它需要事务管理
    async with get_async_db() as db:
        service = ProjectService(db)
        project = await service.get_project_by_id(project_id, owner_id)

        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        if project.status != "failed":
            return {"success": False, "message": f"项目不是失败状态: {project.status}"}

        project.status = "uploaded"
        project.error_message = None
        project.processing_progress = 0
        await db.commit()

        # ProjectProcessingService现在独立管理数据库会话
        content = await _get_file_content(project_id)
        return await project_processing_service.process_uploaded_file(
            project_id=project_id,
            file_content=content
        )


async def _health_check_impl() -> Dict[str, Any]:
    async def test_db():
        from sqlalchemy import text
        async with get_async_db() as db:
            result = await db.execute(text("SELECT 1"))
            return result.scalar() == 1

    try:
        db_ok = await test_db()
    except:
        db_ok = False

    return {
        "success": True,
        "celery_status": "running",
        "database_status": "healthy" if db_ok else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------
# Celery 异步任务，直接调用实现函数
# ---------------------------

@celery_app.task(
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
async def process_uploaded_file(self, project_id: str, owner_id: str):
    return await _process_uploaded_file_impl(project_id, owner_id)


@celery_app.task(bind=True)
async def get_processing_status(self, project_id: str):
    return await _get_processing_status_impl(project_id)


@celery_app.task(bind=True)
async def retry_failed_project(self, project_id: str, owner_id: str):
    return await _retry_failed_project_impl(project_id, owner_id)


@celery_app.task(bind=True)
async def health_check(self):
    return await _health_check_impl()


# ---------------------------
# 辅助逻辑
# ---------------------------

async def _get_file_content(project_id: str):
    async with get_async_db() as db:
        project = await db.get(Project, project_id)
        if not project or not project.file_path:
            raise ValueError(f"项目或文件路径无效: {project_id}")

        storage = await get_storage_client()
        data = await storage.download_file(project.file_path)

    file_type = project.file_type
    handler = get_file_handler(file_type)

    import tempfile, os
    from pathlib import Path

    suffix = Path(project.file_path).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
        fp.write(data)
        temp_path = fp.name

    try:
        content = await handler.read_file(temp_path)
        return content
    except Exception:
        try:
            return decode_file_content(data, project.file_path)
        except:
            raise ValueError(f"无法解码文件: {project.file_path}")
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass


async def _mark_failed_safely(project_id: str, owner_id: str, message: str):
    from src.services.project import ProjectService
    try:
        # 对于ProjectService，仍然需要外部数据库会话
        async with get_async_db() as db:
            service = ProjectService(db)
            await service.mark_processing_failed(project_id, owner_id, message)
    except Exception as e:
        logger.error(f"更新项目失败状态时出错: {e}")


# ---------------------------
# 本地测试逻辑
# ---------------------------

async def main():
    project_id = "c8f5fccd-84ce-45ea-b3d4-b42e48bbdfe7"
    owner_id = "6c11cb2b-d499-4f81-8196-3ea078e9f66a"

    print("=== 测试文件处理逻辑 ===")
    result = await _process_uploaded_file_impl(project_id, owner_id)
    print("处理结果:", result)

    print("=== 测试状态查询 ===")
    status = await _get_processing_status_impl(project_id)
    print("状态:", status)

    print("=== 测试失败重试 ===")
    retry_result = await _retry_failed_project_impl(project_id, owner_id)
    print("重试结果:", retry_result)

    print("=== 测试健康检查 ===")
    health = await _health_check_impl()
    print("健康检查:", health)


if __name__ == "__main__":
    asyncio.run(main())
