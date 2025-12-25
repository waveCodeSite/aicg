"""
服务基类 - 提供统一的数据库会话管理和基础功能
"""

from typing import Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger

if TYPE_CHECKING:
    from typing import Any, Dict, Optional

logger = get_logger(__name__)


class BaseService:
    """
    服务基类
    要求外部注入 AsyncSession。
    """

    def __init__(self, db_session: AsyncSession):
        """
        初始化服务实例
        Args:
            db_session: 必须提供异步数据库会话
        """
        self._db_session = db_session

    @property
    def db_session(self) -> AsyncSession:
        """获取并验证当前绑定的数据库会话"""
        if self._db_session is None:
            raise RuntimeError(f"{self.__class__.__name__} 尚未绑定数据库会话")
        return self._db_session

    async def commit(self):
        """提交当前事务"""
        await self.db_session.commit()

    async def rollback(self):
        """回滚当前事务"""
        await self.db_session.rollback()

    async def flush(self):
        """刷新当前会话"""
        await self.db_session.flush()

    async def refresh(self, obj):
        """刷新对象数据"""
        await self.db_session.refresh(obj)

    async def execute(self, query, params: Optional[dict] = None):
        """执行SQL查询"""
        return await self.db_session.execute(query, params)

    def add(self, obj):
        """添加对象到会话"""
        self.db_session.add(obj)

    def delete(self, obj):
        """从会话中删除对象"""
        self.db_session.delete(obj)

    async def get(self, model_class, identifier):
        """根据ID获取对象"""
        return await self.db_session.get(model_class, identifier)


__all__ = ["BaseService"]
