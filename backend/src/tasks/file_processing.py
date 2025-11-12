"""
文件处理Celery任务模块 - 简洁实现
"""

import tempfile
import traceback
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from celery import Celery

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# 创建Celery实例
celery_app = Celery(
    'file_processing',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=getattr(settings, 'CELERY_TASK_TIME_LIMIT', 300),
    task_soft_time_limit=getattr(settings, 'CELERY_TASK_SOFT_TIME_LIMIT', 240),
)


def run_async_task(coro):
    """在同步上下文中运行异步任务"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(bind=True, name='process_uploaded_file')
def process_uploaded_file(self, project_id: str, owner_id: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    处理上传的文件

    Args:
        project_id: 项目ID
        owner_id: 所有者ID
        file_path: 文件路径（可选）

    Returns:
        处理结果字典
    """
    task_id = self.request.id
    logger.info(f"开始处理文件任务: {task_id}, 项目ID: {project_id}")

    async def _process_file():
        from src.core.database import get_async_session
        from src.services.project import ProjectService

        async_session = get_async_session()

        async with async_session() as db:
            # 获取项目信息
            project_service = ProjectService(db)
            project = await project_service.get_project_by_id(project_id, owner_id)

            if not project:
                raise ValueError(f"项目不存在: {project_id}")

            # 更新项目状态为处理中
            project.status = "parsing"
            await db.commit()

            # 获取文件内容并进行分析
            content = await _get_file_content(project, file_path)
            analysis_result = await _analyze_file_content(content, project.file_type)

            # 更新项目统计信息
            project.word_count = analysis_result['word_count']
            project.chapter_count = analysis_result['chapter_count']
            project.paragraph_count = analysis_result['paragraph_count']
            project.sentence_count = analysis_result['sentence_count']
            project.status = "parsed"
            await db.commit()

            logger.info(f"文件处理完成: {task_id}")

            return {
                'success': True,
                'project_id': project_id,
                'analysis': analysis_result,
                'message': '文件处理完成'
            }

    try:
        return run_async_task(_process_file())

    except Exception as exc:
        logger.error(f"文件处理失败: {task_id}, 错误: {str(exc)}")
        logger.error(traceback.format_exc())

        # 更新处理状态为失败
        async def _update_error_status():
            from src.core.database import get_async_session
            from src.services.project import ProjectService

            async_session = get_async_session()

            async with async_session() as db:
                project_service = ProjectService(db)
                project = await project_service.get_project_by_id(project_id, owner_id)
                if project:
                    project.status = "failed"
                    await db.commit()

        try:
            run_async_task(_update_error_status())
        except Exception as db_error:
            logger.error(f"更新项目状态失败: {db_error}")

        # 重试逻辑
        if self.request.retries < 3:
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=exc)

        return {
            'success': False,
            'project_id': project_id,
            'error': str(exc),
            'message': '文件处理失败'
        }


# 辅助函数
async def _get_file_content(project, file_path: Optional[str]) -> str:
    """获取文件内容"""
    if file_path and Path(file_path).exists():
        # 从本地文件读取
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    else:
        # 从存储下载
        from src.utils.storage import get_storage_client
        storage_client = await get_storage_client()
        content_bytes = await storage_client.download_file(project.file_path)
        return content_bytes.decode('utf-8', errors='ignore')


async def _analyze_file_content(content: str, file_type: Optional[str]) -> Dict[str, Any]:
    """分析文件内容"""
    if not content:
        return {
            'word_count': 0,
            'paragraph_count': 0,
            'sentence_count': 0,
            'chapter_count': 0,
            'character_count': 0
        }

    # 基础统计
    word_count = len(content.split())
    character_count = len(content)

    # 段落统计（简单实现：按空行分割）
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    # 句子统计（简单实现：按句号、问号、感叹号分割）
    import re
    sentences = re.split(r'[.!?。！？]+', content)
    sentence_count = len([s for s in sentences if s.strip()])

    result = {
        'word_count': word_count,
        'paragraph_count': paragraph_count,
        'sentence_count': sentence_count,
        'character_count': character_count,
        'chapter_count': 0
    }

    # 根据文件类型进行特定分析
    if file_type == 'md':
        result['chapter_count'] = _count_markdown_chapters(content)

    return result


def _count_markdown_chapters(content: str) -> int:
    """统计Markdown文件中的章节数"""
    import re
    # 匹配 # ## ### 等标题
    headings = re.findall(r'^#{1,6}\s+.+$', content, re.MULTILINE)
    return len(headings)


__all__ = [
    'celery_app',
    'process_uploaded_file',
]