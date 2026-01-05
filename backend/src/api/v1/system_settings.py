"""
系统设置管理API端点
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.core.database import get_db
from src.models.system_setting import SystemSetting
from src.api.v1.auth import get_current_admin_user
from src.models.user import User

router = APIRouter()


class SystemSettingResponse(BaseModel):
    """系统设置响应"""
    key: str
    value: str
    value_type: str
    description: Optional[str]
    category: str
    is_public: bool


class SystemSettingUpdate(BaseModel):
    """系统设置更新"""
    value: str = Field(..., description="设置值")
    description: Optional[str] = Field(None, description="设置描述")


@router.get("")
async def list_system_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """获取所有系统设置（管理员）"""
    query = select(SystemSetting)

    if category:
        query = query.filter(SystemSetting.category == category)

    result = await db.execute(query.order_by(SystemSetting.category, SystemSetting.key))
    settings = result.scalars().all()

    return [
        SystemSettingResponse(
            key=s.key,
            value=s.value,
            value_type=s.value_type,
            description=s.description,
            category=s.category,
            is_public=s.is_public
        )
        for s in settings
    ]


@router.get("/public")
async def get_public_settings(
    db: AsyncSession = Depends(get_db)
) -> Any:
    """获取公开的系统设置（无需认证）"""
    result = await db.execute(
        select(SystemSetting).filter(SystemSetting.is_public == True)
    )
    settings = result.scalars().all()

    return {s.key: s.value for s in settings}


@router.get("/{key}")
async def get_system_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """获取单个系统设置（管理员）"""
    result = await db.execute(select(SystemSetting).filter(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置不存在"
        )

    return SystemSettingResponse(
        key=setting.key,
        value=setting.value,
        value_type=setting.value_type,
        description=setting.description,
        category=setting.category,
        is_public=setting.is_public
    )


@router.patch("/{key}")
async def update_system_setting(
    key: str,
    setting_update: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """更新系统设置（管理员）"""
    result = await db.execute(select(SystemSetting).filter(SystemSetting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设置不存在"
        )

    setting.value = setting_update.value
    if setting_update.description:
        setting.description = setting_update.description

    await db.commit()
    await db.refresh(setting)

    return SystemSettingResponse(
        key=setting.key,
        value=setting.value,
        value_type=setting.value_type,
        description=setting.description,
        category=setting.category,
        is_public=setting.is_public
    )


__all__ = ["router"]
