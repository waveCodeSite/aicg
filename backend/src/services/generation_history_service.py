"""
生成历史记录服务 - 统一管理所有类型的生成历史
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.models.movie import MovieGenerationHistory, GenerationType, MediaType
from src.services.base import BaseService

logger = get_logger(__name__)


class GenerationHistoryService(BaseService):
    """生成历史记录服务"""
    
    async def create_history(
        self,
        resource_type: str,
        resource_id: str,
        result_url: str,
        prompt: str,
        media_type: str,
        model: Optional[str] = None,
        api_key_id: Optional[str] = None
    ) -> MovieGenerationHistory:
        """
        创建生成历史记录
        
        Args:
            resource_type: 资源类型 (scene_image/shot_keyframe/character_avatar/transition_video)
            resource_id: 资源ID
            result_url: 生成结果URL
            prompt: 生成提示词
            media_type: 媒体类型 (image/video)
            model: 模型名称
            api_key_id: API Key ID
            
        Returns:
            创建的历史记录对象
        """
        # 1. 将该资源的其他历史记录设置为未选中
        await self._unselect_all_history(resource_type, resource_id)
        
        # 2. 创建新的历史记录（默认选中）
        history = MovieGenerationHistory(
            resource_type=resource_type,
            resource_id=resource_id,
            result_url=result_url,
            prompt=prompt,
            media_type=media_type,
            model=model,
            api_key_id=api_key_id,
            is_selected=True
        )
        
        self.db_session.add(history)
        await self.db_session.flush()
        
        logger.info(f"创建生成历史记录: type={resource_type}, resource_id={resource_id}, media={media_type}")
        
        return history
    
    async def get_history(
        self,
        resource_type: str,
        resource_id: str,
        limit: Optional[int] = None
    ) -> List[MovieGenerationHistory]:
        """
        获取资源的所有历史记录
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            limit: 限制返回数量（可选）
            
        Returns:
            历史记录列表（按创建时间倒序）
        """
        stmt = (
            select(MovieGenerationHistory)
            .where(
                and_(
                    MovieGenerationHistory.resource_type == resource_type,
                    MovieGenerationHistory.resource_id == resource_id
                )
            )
            .order_by(MovieGenerationHistory.created_at.desc())
        )
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.db_session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_selected_history(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[MovieGenerationHistory]:
        """
        获取当前选中的历史记录
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            
        Returns:
            选中的历史记录，如果没有则返回None
        """
        stmt = (
            select(MovieGenerationHistory)
            .where(
                and_(
                    MovieGenerationHistory.resource_type == resource_type,
                    MovieGenerationHistory.resource_id == resource_id,
                    MovieGenerationHistory.is_selected == True
                )
            )
        )
        
        result = await self.db_session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def select_history(
        self,
        history_id: str,
        resource_type: str,
        resource_id: str
    ) -> MovieGenerationHistory:
        """
        选择某条历史记录作为当前使用的版本
        
        Args:
            history_id: 历史记录ID
            resource_type: 资源类型
            resource_id: 资源ID
            
        Returns:
            选中的历史记录对象
        """
        # 1. 将该资源的所有历史记录设置为未选中
        await self._unselect_all_history(resource_type, resource_id)
        
        # 2. 将指定的历史记录设置为选中
        history = await self.db_session.get(MovieGenerationHistory, history_id)
        if not history:
            raise ValueError(f"历史记录不存在: {history_id}")
        
        if history.resource_type != resource_type or str(history.resource_id) != str(resource_id):
            raise ValueError(f"历史记录不属于该资源")
        
        history.is_selected = True
        await self.db_session.flush()
        
        logger.info(f"选择历史记录: history_id={history_id}, type={resource_type}, resource_id={resource_id}")
        
        return history
    
    async def _unselect_all_history(
        self,
        resource_type: str,
        resource_id: str
    ):
        """
        将资源的所有历史记录设置为未选中
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
        """
        stmt = (
            update(MovieGenerationHistory)
            .where(
                and_(
                    MovieGenerationHistory.resource_type == resource_type,
                    MovieGenerationHistory.resource_id == resource_id
                )
            )
            .values(is_selected=False)
        )
        
        await self.db_session.execute(stmt)
    
    async def delete_history(
        self,
        history_id: str
    ) -> bool:
        """
        删除历史记录
        
        Args:
            history_id: 历史记录ID
            
        Returns:
            是否删除成功
        """
        history = await self.db_session.get(MovieGenerationHistory, history_id)
        if not history:
            return False
        
        # 如果删除的是选中的记录，需要选择最新的一条作为选中
        if history.is_selected:
            # 获取同资源的其他历史记录
            other_histories = await self.get_history(
                history.resource_type,
                str(history.resource_id),
                limit=2  # 获取最新的2条（包括当前要删除的）
            )
            
            # 如果还有其他记录，选中最新的一条
            if len(other_histories) > 1:
                for h in other_histories:
                    if str(h.id) != history_id:
                        h.is_selected = True
                        break
        
        await self.db_session.delete(history)
        await self.db_session.flush()
        
        logger.info(f"删除历史记录: history_id={history_id}")
        
        return True


__all__ = ["GenerationHistoryService"]
