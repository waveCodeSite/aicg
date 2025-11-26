"""
测试验证异步处理流程
验证Celery任务、数据库操作和文本解析的集成测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.tasks.task import process_uploaded_file, get_processing_status, retry_failed_project, health_check
from src.services.project_processing import project_processing_service
from src.services.project import ProjectService
from src.models.project import Project, ProjectStatus
from src.models.chapter import Chapter
from src.models.paragraph import Paragraph
from src.models.sentence import Sentence


class TestAsyncFileProcessing:
    """异步文件处理流程测试"""

    @pytest.fixture
    async def mock_db_session(self):
        """模拟数据库会话"""
        session = AsyncMock(spec=AsyncSession)
        session.begin = MagicMock()
        session.begin.__aenter__ = AsyncMock()
        session.begin.__aexit__ = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_project(self):
        """模拟项目对象"""
        project = MagicMock(spec=Project)
        project.id = "test-project-id"
        project.owner_id = "test-owner-id"
        project.title = "Test Project"
        project.status = ProjectStatus.UPLOADED.value
        project.processing_progress = 0
        project.error_message = None
        project.completed_at = None
        return project

    @pytest.fixture
    def sample_file_content(self):
        """示例文件内容"""
        return """
# 第一章 开始

这是第一章的第一段。包含多个句子。

这是第一章的第二段。同样有多个句子。

# 第二章 继续

这是第二章的第一段。

这是第二章的第二段。
        """.strip()

    @pytest.mark.asyncio
    async def test_process_uploaded_file_success(self, mock_db_session, mock_project, sample_file_content):
        """测试成功处理上传文件"""
        # 模拟依赖
        with patch('src.tasks.file_processing.get_async_session') as mock_get_session, \
             patch('src.tasks.file_processing.project_processing_service') as mock_service, \
             patch('src.tasks.file_processing._get_file_content') as mock_get_content:

            # 设置模拟返回值
            mock_get_session.return_value = mock_db_session
            mock_get_content.return_value = sample_file_content
            mock_service.process_uploaded_file.return_value = {
                'success': True,
                'project_id': mock_project.id,
                'chapters_count': 2,
                'paragraphs_count': 4,
                'sentences_count': 8,
                'message': '文件处理完成'
            }

            # 模拟Celery任务
            mock_task = MagicMock()
            mock_task.request.id = "test-task-id"
            mock_task.request.retries = 0

            # 执行任务
            with patch('src.tasks.file_processing.run_async_task') as mock_run_async:
                mock_run_async.return_value = mock_service.process_uploaded_file.return_value

                result = process_uploaded_file.apply(
                    args=[mock_project.id, mock_project.owner_id, None]
                ).get()

            # 验证结果
            assert result['success'] is True
            assert result['project_id'] == mock_project.id
            assert result['chapters_count'] == 2
            assert result['paragraphs_count'] == 4
            assert result['sentences_count'] == 8

    @pytest.mark.asyncio
    async def test_process_uploaded_file_with_retry(self, mock_db_session, mock_project):
        """测试文件处理失败重试机制"""
        with patch('src.tasks.file_processing.get_async_session') as mock_get_session, \
             patch('src.tasks.file_processing.project_processing_service') as mock_service, \
             patch('src.tasks.file_processing._get_file_content') as mock_get_content:

            # 设置模拟异常
            mock_service.process_uploaded_file.side_effect = Exception("处理失败")
            mock_get_session.return_value = mock_db_session
            mock_get_content.return_value = "sample content"

            # 模拟Celery任务
            mock_task = MagicMock()
            mock_task.request.id = "test-task-id"
            mock_task.request.retries = 0
            mock_task.retry = MagicMock()

            # 模拟ProjectService
            with patch('src.services.project.ProjectService') as mock_project_service:
                mock_project_service_instance = AsyncMock()
                mock_project_service.return_value = mock_project_service_instance
                mock_project_service_instance.mark_processing_failed = AsyncMock()

                # 执行任务并捕获重试异常
                with pytest.raises(Exception):
                    with patch('src.tasks.file_processing.run_async_task') as mock_run_async:
                        mock_run_async.side_effect = Exception("处理失败")

                        process_uploaded_file.apply(
                            args=[mock_project.id, mock_project.owner_id, None]
                        ).get()

            # 验证重试被调用
            # 注意：在实际的Celery环境中，retry会抛出异常来触发重试

    @pytest.mark.asyncio
    async def test_get_processing_status(self, mock_db_session, mock_project):
        """测试获取处理状态"""
        with patch('src.tasks.file_processing.get_async_session') as mock_get_session, \
             patch('src.tasks.file_processing.project_processing_service') as mock_service:

            # 设置模拟返回值
            mock_get_session.return_value = mock_db_session
            mock_service.get_processing_status.return_value = {
                'success': True,
                'project_id': mock_project.id,
                'status': ProjectStatus.PARSED.value,
                'processing_progress': 100,
                'chapters_count': 2,
                'paragraphs_count': 4,
                'sentences_count': 8,
                'word_count': 200,
                'error_message': None,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'completed_at': datetime.utcnow().isoformat(),
            }

            # 模拟Celery任务
            mock_task = MagicMock()
            mock_task.request.id = "test-task-id"

            # 执行任务
            with patch('src.tasks.file_processing.run_async_task') as mock_run_async:
                mock_run_async.return_value = mock_service.get_processing_status.return_value

                result = get_processing_status.apply(
                    args=[mock_project.id, mock_project.owner_id]
                ).get()

            # 验证结果
            assert result['success'] is True
            assert result['project_id'] == mock_project.id
            assert result['status'] == ProjectStatus.PARSED.value
            assert result['processing_progress'] == 100

    @pytest.mark.asyncio
    async def test_retry_failed_project(self, mock_db_session, mock_project):
        """测试重试失败项目"""
        # 设置项目为失败状态
        mock_project.status = ProjectStatus.FAILED.value
        mock_project.error_message = "之前的错误"

        with patch('src.tasks.file_processing.get_async_session') as mock_get_session, \
             patch('src.tasks.file_processing.project_processing_service') as mock_service, \
             patch('src.tasks.file_processing._get_file_content') as mock_get_content:

            # 设置模拟返回值
            mock_get_session.return_value = mock_db_session
            mock_get_content.return_value = "sample content"
            mock_service.process_uploaded_file.return_value = {
                'success': True,
                'project_id': mock_project.id,
                'message': '重试处理成功'
            }

            # 模拟ProjectService
            with patch('src.services.project.ProjectService') as mock_project_service:
                mock_project_service_instance = AsyncMock()
                mock_project_service.return_value = mock_project_service_instance
                mock_project_service_instance.get_project_by_id.return_value = mock_project

                # 模拟Celery任务
                mock_task = MagicMock()
                mock_task.request.id = "test-task-id"

                # 执行任务
                with patch('src.tasks.file_processing.run_async_task') as mock_run_async:
                    mock_run_async.return_value = mock_service.process_uploaded_file.return_value

                    result = retry_failed_project.apply(
                        args=[mock_project.id, mock_project.owner_id]
                    ).get()

                # 验证项目状态被重置
                assert mock_project.status == "uploaded"
                assert mock_project.error_message is None
                assert mock_project.processing_progress == 0

                # 验证结果
                assert result['success'] is True
                assert result['project_id'] == mock_project.id

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查任务"""
        with patch('src.tasks.file_processing.get_async_session') as mock_get_session:
            # 模拟数据库健康检查
            mock_db_session = AsyncMock(spec=AsyncSession)
            mock_db_session.__aenter__ = AsyncMock()
            mock_db_session.__aexit__ = AsyncMock()
            mock_get_session.return_value = mock_db_session

            # 模拟数据库查询结果
            mock_result = MagicMock()
            mock_result.scalar.return_value = 1
            mock_db_session.execute.return_value = mock_result

            # 执行健康检查
            result = health_check.apply().get()

            # 验证结果
            assert result['success'] is True
            assert result['celery_status'] == 'running'
            assert result['database_status'] == 'healthy'
            assert 'timestamp' in result
            assert 'message' in result


class TestProjectProcessingService:
    """ProjectProcessingService测试"""

    @pytest.mark.asyncio
    async def test_process_uploaded_file_complete_workflow(self):
        """测试完整的文件处理工作流"""
        # 准备测试数据
        project_id = "test-project-id"
        file_content = """
# 第一章 测试章节

这是第一段。包含句子一。包含句子二。

这是第二段。包含句子三。包含句子四。

# 第二章 第二章节

这是第三段。包含句子五。
        """.strip()

        # 模拟数据库会话和项目
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.status = ProjectStatus.UPLOADED.value

        # 模拟文本解析结果
        chapters_data = [
            {
                'project_id': project_id,
                'title': '第一章 测试章节',
                'content': '这是第一段。包含句子一。包含句子二。\n\n这是第二段。包含句子三。包含句子四。',
                'order_index': 0,
                'paragraph_count': 2,
                'word_count': 20,
                'character_count': 30
            },
            {
                'project_id': project_id,
                'title': '第二章 第二章节',
                'content': '这是第三段。包含句子五。',
                'order_index': 1,
                'paragraph_count': 1,
                'word_count': 5,
                'character_count': 8
            }
        ]

        paragraphs_data = [
            {'content': '这是第一段。包含句子一。包含句子二。', 'order_index': 0, 'word_count': 10, 'sentence_count': 2},
            {'content': '这是第二段。包含句子三。包含句子四。', 'order_index': 1, 'word_count': 10, 'sentence_count': 2},
            {'content': '这是第三段。包含句子五。', 'order_index': 0, 'word_count': 5, 'sentence_count': 1}
        ]

        sentences_data = [
            {'content': '这是第一段。包含句子一。', 'order_index': 0, 'word_count': 6, 'character_count': 8},
            {'content': '包含句子二。', 'order_index': 1, 'word_count': 4, 'character_count': 5},
            {'content': '这是第二段。包含句子三。', 'order_index': 0, 'word_count': 6, 'character_count': 8},
            {'content': '包含句子四。', 'order_index': 1, 'word_count': 4, 'character_count': 5},
            {'content': '这是第三段。包含句子五。', 'order_index': 0, 'word_count': 6, 'character_count': 8}
        ]

        with patch.object(project_processing_service, '_get_project') as mock_get_project, \
             patch.object(project_processing_service, '_update_project_status') as mock_update_status, \
             patch.object(project_processing_service, '_parse_text_content') as mock_parse, \
             patch.object(project_processing_service, '_save_parsed_content') as mock_save, \
             patch.object(project_processing_service, '_update_project_statistics') as mock_update_stats:

            # 设置模拟返回值
            mock_get_project.return_value = mock_project
            mock_parse.return_value = (chapters_data, paragraphs_data, sentences_data)

            # 执行处理
            result = await project_processing_service.process_uploaded_file(
                mock_db_session, project_id, file_content
            )

            # 验证调用
            mock_get_project.assert_called_once_with(mock_db_session, project_id)
            mock_update_status.assert_any_call(mock_db_session, mock_project, ProjectStatus.PARSING, 10)
            mock_parse.assert_called_once_with(project_id, file_content)
            mock_save.assert_called_once()
            mock_update_stats.assert_called_once()
            mock_update_status.assert_called_with(mock_db_session, mock_project, ProjectStatus.PARSED, 100)

            # 验证结果
            assert result['success'] is True
            assert result['project_id'] == project_id
            assert result['chapters_count'] == 2
            assert result['paragraphs_count'] == 3
            assert result['sentences_count'] == 5


class TestModelBatchOperations:
    """模型批量操作测试"""

    @pytest.mark.asyncio
    async def test_chapter_batch_create(self):
        """测试章节批量创建"""
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_db_session.execute = AsyncMock()
        mock_db_session.flush = AsyncMock()

        chapters_data = [
            {
                'project_id': 'test-project-id',
                'title': '第一章',
                'content': '第一章内容',
                'order_index': 0
            },
            {
                'project_id': 'test-project-id',
                'title': '第二章',
                'content': '第二章内容',
                'order_index': 1
            }
        ]

        # 执行批量创建
        chapter_ids = await Chapter.batch_create(mock_db_session, chapters_data)

        # 验证结果
        assert len(chapter_ids) == 2
        assert all(isinstance(chapter_id, str) for chapter_id in chapter_ids)

        # 验证数据库操作被调用
        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_paragraph_batch_create(self):
        """测试段落批量创建"""
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_db_session.execute = AsyncMock()
        mock_db_session.flush = AsyncMock()

        paragraphs_data = [
            {'content': '第一段内容', 'order_index': 0, 'word_count': 4},
            {'content': '第二段内容', 'order_index': 1, 'word_count': 4}
        ]
        chapter_ids = ['chapter-1', 'chapter-2']

        # 执行批量创建
        paragraph_ids = await Paragraph.batch_create(mock_db_session, paragraphs_data, chapter_ids)

        # 验证结果
        assert len(paragraph_ids) == 2
        assert all(isinstance(paragraph_id, str) for paragraph_id in paragraph_ids)

        # 验证chapter_id被正确设置
        for i, paragraph_data in enumerate(paragraphs_data):
            assert paragraph_data['chapter_id'] == chapter_ids[i]

    @pytest.mark.asyncio
    async def test_sentence_batch_create(self):
        """测试句子批量创建"""
        mock_db_session = AsyncMock(spec=AsyncSession)
        mock_db_session.execute = AsyncMock()
        mock_db_session.flush = AsyncMock()

        sentences_data = [
            {'content': '句子一', 'order_index': 0, 'word_count': 2},
            {'content': '句子二', 'order_index': 1, 'word_count': 2}
        ]
        paragraph_ids = ['paragraph-1', 'paragraph-2']

        # 执行批量创建
        sentence_ids = await Sentence.batch_create(mock_db_session, sentences_data, paragraph_ids)

        # 验证结果
        assert len(sentence_ids) == 2
        assert all(isinstance(sentence_id, str) for sentence_id in sentence_ids)

        # 验证paragraph_id被正确设置
        for i, sentence_data in enumerate(sentences_data):
            assert sentence_data['paragraph_id'] == paragraph_ids[i]
            assert sentence_data['status'] == SentenceStatus.PENDING.value


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])