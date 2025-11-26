"""
后台任务模块
"""

from .task import celery_app, process_uploaded_file

__all__ = [
    # Celery应用和任务
    "celery_app",
    "process_uploaded_file",
]