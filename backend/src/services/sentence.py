"""
句子管理服务 - 负责句子的创建、更新、删除和查询
"""

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.logging import get_logger
from src.models.chapter import Chapter
from src.models.paragraph import Paragraph
from src.models.sentence import Sentence, SentenceStatus
from src.services.base import BaseService
from src.core.exceptions import NotFoundError, BusinessLogicError

logger = get_logger(__name__)


class SentenceService(BaseService):
    """
    句子管理服务
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        super().__init__(db_session)

    async def create_sentence(
            self,
            paragraph_id: str,
            content: str,
            order_index: Optional[int] = None
    ) -> Sentence:
        """
        创建新句子
        """
        # 验证段落是否存在
        paragraph = await self.get(Paragraph, paragraph_id)
        if not paragraph:
            raise NotFoundError(
                "段落不存在",
                resource_type="paragraph",
                resource_id=paragraph_id
            )

        # 检查章节是否已确认
        chapter = await self.get(Chapter, paragraph.chapter_id)
        if chapter and chapter.is_confirmed:
            raise BusinessLogicError(
                "已确认的章节不能添加句子",
                business_rule="confirmed_chapter_add_sentence",
                context={"chapter_id": paragraph.chapter_id, "paragraph_id": paragraph_id}
            )

        # 如果未指定顺序，则添加到最后
        if order_index is None:
            # 获取当前最大顺序
            result = await self.execute(
                select(func.max(Sentence.order_index))
                .where(Sentence.paragraph_id == paragraph_id)
            )
            max_order = result.scalar() or 0
            order_index = max_order + 1

        sentence = Sentence(
            paragraph_id=paragraph_id,
            content=content,
            order_index=order_index,
            word_count=len(content.replace(' ', '')),
            character_count=len(content),
            status=SentenceStatus.PENDING.value
        )

        self.add(sentence)
        await self.commit()
        await self.refresh(sentence)

        logger.info(f"创建句子成功: ID={sentence.id}, 段落={paragraph_id}")
        return sentence

    async def get_sentence_by_id(self, sentence_id: str) -> Sentence:
        """
        根据ID获取句子
        """
        sentence = await self.get(Sentence, sentence_id)
        if not sentence:
            raise NotFoundError(
                "句子不存在",
                resource_type="sentence",
                resource_id=sentence_id
            )
        return sentence

    async def update_sentence(
            self,
            sentence_id: str,
            content: Optional[str] = None,
            image_prompt: Optional[str] = None
    ) -> Sentence:
        """
        更新句子内容或图片提示词
        """
        sentence = await self.get_sentence_by_id(sentence_id)

        # 检查章节是否已确认
        paragraph = await self.get(Paragraph, sentence.paragraph_id)
        chapter = await self.get(Chapter, paragraph.chapter_id)
        
        # 只有更新内容时才需要检查章节是否已确认
        if content is not None and content != sentence.content:
            if chapter and chapter.is_confirmed:
                raise BusinessLogicError(
                    "已确认的章节不能修改句子内容",
                    business_rule="confirmed_chapter_update_sentence",
                    context={"chapter_id": paragraph.chapter_id, "sentence_id": sentence_id}
                )
            
            sentence.content = content
            sentence.word_count = len(content.replace(' ', ''))
            sentence.character_count = len(content)
            # 重置状态为pending，因为内容变了可能需要重新生成
            sentence.status = SentenceStatus.PENDING.value
                    
        # 更新图片提示词不需要检查章节是否已确认
        if image_prompt is not None:
            sentence.image_prompt = image_prompt
            
        await self.commit()
        await self.refresh(sentence)

        logger.info(f"更新句子成功: ID={sentence_id}")
        return sentence

    async def get_sentences_by_paragraph(self, paragraph_id: str) -> List[Sentence]:
        """
        获取段落的所有句子
        
        Args:
            paragraph_id: 段落ID
            
        Returns:
            句子列表，按order_index排序
        """
        sentences = await Sentence.get_by_paragraph_id(self.db_session, paragraph_id)
        logger.debug(f"获取段落句子: 段落={paragraph_id}, 数量={len(sentences)}")
        return sentences

    async def delete_sentence(self, sentence_id: str) -> bool:
        """
        删除句子
        """
        sentence = await self.get_sentence_by_id(sentence_id)

        # 检查章节是否已确认
        paragraph = await self.get(Paragraph, sentence.paragraph_id)
        chapter = await self.get(Chapter, paragraph.chapter_id)
        if chapter and chapter.is_confirmed:
            raise BusinessLogicError(
                "已确认的章节不能删除句子",
                business_rule="confirmed_chapter_delete_sentence",
                context={"chapter_id": paragraph.chapter_id, "sentence_id": sentence_id}
            )
        
        self.delete(sentence)
        await self.commit()

        logger.info(f"删除句子成功: ID={sentence_id}")
        return True
