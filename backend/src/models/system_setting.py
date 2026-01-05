"""
系统设置数据模型
"""

from sqlalchemy import Column, String, Boolean, Text, JSON
from src.models.base import BaseModel


class SystemSetting(BaseModel):
    """系统设置模型"""
    __tablename__ = 'system_settings'

    key = Column(String(100), unique=True, nullable=False, comment="设置键")
    value = Column(Text, nullable=True, comment="设置值")
    value_type = Column(String(20), default='string', comment="值类型: string, boolean, json")
    description = Column(String(255), nullable=True, comment="设置描述")
    category = Column(String(50), default='general', comment="设置分类")
    is_public = Column(Boolean, default=False, comment="是否公开(前端可访问)")

    @classmethod
    async def get_value(cls, db_session, key: str, default=None):
        """获取设置值"""
        from sqlalchemy import select
        result = await db_session.execute(select(cls).filter(cls.key == key))
        setting = result.scalar_one_or_none()

        if not setting:
            return default

        # 根据类型转换值
        if setting.value_type == 'boolean':
            return setting.value.lower() in ('true', '1', 'yes')
        elif setting.value_type == 'json':
            import json
            try:
                return json.loads(setting.value)
            except:
                return default
        else:
            return setting.value

    @classmethod
    async def set_value(cls, db_session, key: str, value, value_type: str = 'string', description: str = None, category: str = 'general'):
        """设置值"""
        from sqlalchemy import select
        result = await db_session.execute(select(cls).filter(cls.key == key))
        setting = result.scalar_one_or_none()

        # 转换值为字符串
        if value_type == 'boolean':
            str_value = 'true' if value else 'false'
        elif value_type == 'json':
            import json
            str_value = json.dumps(value)
        else:
            str_value = str(value)

        if setting:
            setting.value = str_value
            setting.value_type = value_type
            if description:
                setting.description = description
        else:
            setting = cls(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description,
                category=category
            )
            db_session.add(setting)

        await db_session.commit()
        return setting


__all__ = ["SystemSetting"]
