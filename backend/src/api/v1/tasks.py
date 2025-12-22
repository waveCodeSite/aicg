"""
任务管理 API（优化版）
"""

from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user_required
from src.api.schemas.task import TaskStatusResponse
from src.core.logging import get_logger
from src.models.user import User
from src.tasks.task import celery_app

logger = get_logger(__name__)

router = APIRouter()


def safe_result(task_result: AsyncResult):
    """
    将 Celery 返回的 result 转为可序列化结构。
    避免返回 Python Exception 导致 FastAPI 500。
    """
    status = task_result.status
    result = task_result.result

    # SUCCESS or PROGRESS – 直接返回正常结果
    if status in ["SUCCESS", "PROGRESS"]:
        return result

    # FAILURE – 将异常对象序列化
    if status == "FAILURE":
        if isinstance(result, Exception):
            return {
                "error": result.__class__.__name__,
                "message": str(result)
            }
        return {"message": str(result)}

    # 其他状态：PENDING / RETRY / STARTED
    return None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """
    获取任务状态（优化：不会因异常对象导致 500）
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    result = safe_result(task_result)
    statistics = None
    
    # 如果结果是字典且包含统计信息，提取出来
    if isinstance(result, dict) and ('total' in result or 'success' in result or 'failed' in result):
        statistics = result

    return TaskStatusResponse(
        task_id=task_id,
        status=task_result.status,
        result=result,
        statistics=statistics
    )


@router.post("/{task_id}/terminate")
async def terminate_task(
    task_id: str,
    current_user: User = Depends(get_current_user_required)
):
    """
    终止正在运行的任务
    """
    task_result = AsyncResult(task_id, app=celery_app)
    # terminate=True allows killing the worker process if it's currently executing the task
    # signal='SIGTERM' is usually enough
    task_result.revoke(terminate=True, signal='SIGTERM')
    return {"message": "任务终止请求已发送"}


__all__ = ["router"]
