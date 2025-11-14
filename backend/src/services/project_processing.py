"""
项目文件处理服务 - 协调文本解析和数据保存
按照现有架构规范实现，遵循单一职责原则
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.core.logging import get_logger
from src.models.chapter import Chapter
from src.models.paragraph import Paragraph
from src.models.project import Project, ProjectStatus
from src.models.sentence import Sentence

logger = get_logger(__name__)


class ProjectProcessingService:
    """项目文件处理服务 - 协调文本解析和数据保存"""

    def __init__(self):
        self.text_parser_service = None
        # 延迟导入text_parser_service避免循环依赖

    async def _get_text_parser_service(self):
        """延迟导入text_parser_service"""
        if self.text_parser_service is None:
            from src.services.text_parser import text_parser_service
            self.text_parser_service = text_parser_service
        return self.text_parser_service

    async def process_uploaded_file(self, db_session, project_id: str, file_content: str) -> Dict:
        """
        处理上传的文件 - 完整的文本解析和数据保存流程

        Args:
            db_session: 数据库会话
            project_id: 项目ID
            file_content: 文件内容

        Returns:
            处理结果字典
        """
        try:
            # 1. 获取项目信息
            project = await self._get_project(db_session, project_id)

            # 2. 更新项目状态为处理中
            await self._update_project_status(db_session, project, ProjectStatus.PARSING, 10)

            # 3. 解析文本内容
            logger.info(f"开始解析项目 {project_id} 的文本内容，长度: {len(file_content)} 字符")
            chapters_data, paragraphs_data, sentences_data = await self._parse_text_content(
                project_id, file_content
            )

            # 4. 更新进度到30%（解析完成）
            await self._update_project_status(db_session, project, ProjectStatus.PARSING, 30)

            # 5. 批量保存到数据库
            await self._save_parsed_content(
                db_session, project_id, chapters_data, paragraphs_data, sentences_data
            )

            # 6. 更新项目统计信息
            await self._update_project_statistics(db_session, project)

            # 7. 标记项目为已解析
            await self._update_project_status(db_session, project, ProjectStatus.PARSED, 100)

            logger.info(f"项目 {project_id} 文件处理完成")

            return {
                'success': True,
                'project_id': project_id,
                'chapters_count': len(chapters_data),
                'paragraphs_count': len(paragraphs_data),
                'sentences_count': len(sentences_data),
                'message': '文件处理完成'
            }

        except Exception as e:
            logger.error(f"项目 {project_id} 文件处理失败: {str(e)}")

            # 返回错误信息，让调用者处理事务回滚
            return {
                'success': False,
                'project_id': project_id,
                'error': str(e),
                'message': '文件处理失败'
            }

    async def _get_project(self, db_session, project_id: str) -> Project:
        """获取项目信息"""
        project = await db_session.get(Project, project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        return project

    async def _update_project_status(self, db_session, project: Project, status: ProjectStatus,
                                     progress: int, error_message: Optional[str] = None) -> None:
        """更新项目状态和进度"""
        project.status = status.value
        project.processing_progress = progress
        if error_message:
            project.error_message = error_message
        elif status == ProjectStatus.PARSED:
            project.error_message = None
            project.completed_at = datetime.utcnow()

        await db_session.flush()

    async def _parse_text_content(self, project_id: str, file_content: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        解析文本内容

        Args:
            project_id: 项目ID
            file_content: 文件内容

        Returns:
            (chapters_data, paragraphs_data, sentences_data)
        """
        text_parser_service = await self._get_text_parser_service()

        # 根据项目设置解析选项
        parse_options = {
            'min_chapter_length': 1000,  # 最小章节长度
        }

        return await text_parser_service.parse_to_models(project_id, file_content, parse_options)

    async def _save_parsed_content(self, db_session, project_id: str, chapters_data: List[Dict],
                                   paragraphs_data: List[Dict], sentences_data: List[Dict]) -> None:
        """
        保存解析的内容到数据库

        Args:
            db_session: 数据库会话
            project_id: 项目ID
            chapters_data: 章节数据
            paragraphs_data: 段落数据
            sentences_data: 句子数据
        """
        logger.info(f"开始保存解析内容: {len(chapters_data)} 章节, {len(paragraphs_data)} 段落, {len(sentences_data)} 句子")

        # 1. 批量保存章节
        chapter_ids = await Chapter.batch_create(db_session, chapters_data)
        logger.info(f"成功保存 {len(chapter_ids)} 个章节")

        # 2. 更新段落数据中的chapter_id，并批量保存段落
        current_para_index = 0
        para_chapter_mapping = []

        for chapter_idx, chapter_data in enumerate(chapters_data):
            # 计算当前章节的段落数量
            chapter_paragraph_count = chapter_data['paragraph_count']
            if current_para_index + chapter_paragraph_count > len(paragraphs_data):
                # 数据不一致，使用实际可用的数量
                chapter_paragraph_count = len(paragraphs_data) - current_para_index

            # 更新段落的chapter_id
            for i in range(chapter_paragraph_count):
                para_index = current_para_index + i
                if para_index < len(paragraphs_data):
                    paragraphs_data[para_index]['chapter_id'] = chapter_ids[chapter_idx]
                    para_chapter_mapping.append(chapter_ids[chapter_idx])

            current_para_index += chapter_paragraph_count

        # 批量保存段落
        paragraph_ids = await Paragraph.batch_create(db_session, paragraphs_data[:current_para_index], para_chapter_mapping)
        logger.info(f"成功保存 {len(paragraph_ids)} 个段落")

        # 3. 更新句子数据中的paragraph_id，并批量保存句子
        current_sent_index = 0
        sent_para_mapping = []

        for para_idx, paragraph_data in enumerate(paragraphs_data[:current_para_index]):
            # 计算当前段落的句子数量
            para_sentence_count = paragraph_data.get('sentence_count', 0)
            if current_sent_index + para_sentence_count > len(sentences_data):
                # 数据不一致，使用实际可用的数量
                para_sentence_count = len(sentences_data) - current_sent_index

            # 更新句子的paragraph_id
            for i in range(para_sentence_count):
                sent_index = current_sent_index + i
                if sent_index < len(sentences_data):
                    sentences_data[sent_index]['paragraph_id'] = paragraph_ids[para_idx]
                    sent_para_mapping.append(paragraph_ids[para_idx])

            current_sent_index += para_sentence_count

        # 批量保存句子
        sentence_ids = await Sentence.batch_create(db_session, sentences_data[:current_sent_index], sent_para_mapping)
        logger.info(f"成功保存 {len(sentence_ids)} 个句子")

    async def _update_project_statistics(self, db_session, project: Project) -> None:
        """
        更新项目统计信息

        Args:
            db_session: 数据库会话
            project: 项目对象
        """
        try:
            # 统计章节数量
            chapter_count = await Chapter.count_by_project_id(db_session, project.id)
            project.chapter_count = chapter_count

            # 统计段落数量
            paragraphs = await Paragraph.get_by_project_id(db_session, project.id)
            project.paragraph_count = len(paragraphs)

            # 统计句子数量
            sentences = await Sentence.get_by_project_id(db_session, project.id)
            project.sentence_count = len(sentences)

            # 统计总字数
            total_word_count = 0
            for paragraph in paragraphs:
                total_word_count += paragraph.word_count or 0
            project.word_count = total_word_count

            await db_session.flush()
            logger.info(f"项目 {project.id} 统计信息更新完成: {chapter_count}章节, {len(paragraphs)}段落, {len(sentences)}句子, {total_word_count}字")

        except Exception as e:
            logger.error(f"更新项目统计信息失败: {e}")
            # 不抛出异常，允许流程继续

    async def get_processing_status(self, db_session, project_id: str) -> Dict:
        """
        获取处理状态

        Args:
            db_session: 数据库会话
            project_id: 项目ID

        Returns:
            状态信息字典
        """
        try:
            project = await self._get_project(db_session, project_id)

            # 获取各层级的统计
            chapter_count = await Chapter.count_by_project_id(db_session, project_id)
            paragraph_count = len(await Paragraph.get_by_project_id(db_session, project_id))
            sentence_count = len(await Sentence.get_by_project_id(db_session, project_id))

            return {
                'success': True,
                'project_id': project_id,
                'status': project.status,
                'processing_progress': project.processing_progress,
                'chapters_count': chapter_count,
                'paragraphs_count': paragraph_count,
                'sentences_count': sentence_count,
                'word_count': project.word_count or 0,
                'error_message': project.error_message,
                'created_at': project.created_at.isoformat() if project.created_at else None,
                'updated_at': project.updated_at.isoformat() if project.updated_at else None,
                'completed_at': project.completed_at.isoformat() if project.completed_at else None,
            }

        except Exception as e:
            logger.error(f"获取项目 {project_id} 处理状态失败: {e}")
            return {
                'success': False,
                'project_id': project_id,
                'error': str(e),
                'message': '获取处理状态失败'
            }


# 全局实例
project_processing_service = ProjectProcessingService()

__all__ = [
    'ProjectProcessingService',
    'project_processing_service',
]
