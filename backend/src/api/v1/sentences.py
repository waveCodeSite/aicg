from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user_required, get_db
from src.api.schemas.sentence import SentenceCreate, SentenceResponse, SentenceUpdate, SentenceListResponse
from src.models.user import User
from src.services.sentence import SentenceService

router = APIRouter()


@router.get("/paragraphs/{paragraph_id}/sentences", response_model=SentenceListResponse)
async def list_sentences(
    *,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    paragraph_id: str
):
    """
    获取段落的句子列表
    
    Args:
        paragraph_id: 段落ID
        
    Returns:
        句子列表，按order_index排序
    """
    sentence_service = SentenceService(db)
    sentences = await sentence_service.get_sentences_by_paragraph(paragraph_id)
    
    # 使用 from_dict 转换
    sentence_responses = [SentenceResponse.from_dict(s.to_dict()) for s in sentences]
    
    return SentenceListResponse(
        sentences=sentence_responses,
        total=len(sentences),
        page=1,
        size=len(sentences) if sentences else 20,
        total_pages=1
    )


@router.post("/paragraphs/{paragraph_id}/sentences", response_model=SentenceResponse, status_code=status.HTTP_201_CREATED)
async def create_sentence(
    *,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    paragraph_id: str,
    sentence_in: SentenceCreate
):
    """
    创建新句子
    """
    sentence_service = SentenceService(db)
    
    sentence = await sentence_service.create_sentence(
        paragraph_id=paragraph_id,
        content=sentence_in.content,
        order_index=sentence_in.order_index
    )
    
    return SentenceResponse.from_dict(sentence.to_dict())


@router.get("/{sentence_id}", response_model=SentenceResponse)
async def get_sentence(
    *,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    sentence_id: str
):
    """
    获取句子详情
    """
    sentence_service = SentenceService(db)
    sentence = await sentence_service.get_sentence_by_id(sentence_id)
    return SentenceResponse.from_dict(sentence.to_dict())


@router.put("/{sentence_id}", response_model=SentenceResponse)
async def update_sentence(
    *,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    sentence_id: str,
    sentence_in: SentenceUpdate
):
    """
    更新句子内容
    """
    sentence_service = SentenceService(db)
    
    sentence = await sentence_service.update_sentence(
        sentence_id=sentence_id,
        content=sentence_in.content
    )
    
    return SentenceResponse.from_dict(sentence.to_dict())


@router.delete("/{sentence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sentence(
    *,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    sentence_id: str
):
    """
    删除句子
    """
    sentence_service = SentenceService(db)
    await sentence_service.delete_sentence(sentence_id)
