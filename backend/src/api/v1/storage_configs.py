"""
存储配置管理API端点
"""

from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.storage_config import StorageConfig
from src.api.v1.auth import get_current_admin_user
from src.models.user import User
from pydantic import BaseModel, Field

router = APIRouter()


class StorageConfigCreate(BaseModel):
    """创建存储配置"""
    name: str = Field(..., max_length=100, description="配置名称")
    storage_type: str = Field(..., description="存储类型: minio, s3, aliyun-oss等")
    endpoint: str = Field(..., description="存储端点")
    access_key: str = Field(..., description="访问密钥")
    secret_key: str = Field(..., description="密钥")
    bucket_name: str = Field(..., description="存储桶名称")
    region: str = Field(default="us-east-1", description="区域")
    is_secure: bool = Field(default=False, description="是否使用HTTPS")
    public_url: Optional[str] = Field(None, description="公开访问URL")
    is_default: bool = Field(default=False, description="是否为默认配置")


class StorageConfigUpdate(BaseModel):
    """更新存储配置"""
    name: Optional[str] = Field(None, max_length=100, description="配置名称")
    storage_type: Optional[str] = Field(None, description="存储类型")
    endpoint: Optional[str] = Field(None, description="存储端点")
    access_key: Optional[str] = Field(None, description="访问密钥")
    secret_key: Optional[str] = Field(None, description="密钥")
    bucket_name: Optional[str] = Field(None, description="存储桶名称")
    region: Optional[str] = Field(None, description="区域")
    is_secure: Optional[bool] = Field(None, description="是否使用HTTPS")
    public_url: Optional[str] = Field(None, description="公开访问URL")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_default: Optional[bool] = Field(None, description="是否为默认配置")


@router.get("")
async def list_storage_configs(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """获取所有存储配置"""
    result = await db.execute(select(StorageConfig).order_by(StorageConfig.created_at.desc()))
    configs = result.scalars().all()
    return [config.to_dict() for config in configs]


@router.get("/default")
async def get_default_storage_config(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """获取默认存储配置"""
    result = await db.execute(
        select(StorageConfig).filter(
            StorageConfig.is_default == True,
            StorageConfig.is_active == True
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到默认存储配置"
        )

    return config.to_dict()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_storage_config(
    config_data: StorageConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """创建存储配置"""
    # 如果设置为默认,取消其他默认配置
    if config_data.is_default:
        result = await db.execute(
            select(StorageConfig).filter(StorageConfig.is_default == True)
        )
        existing_defaults = result.scalars().all()
        for config in existing_defaults:
            config.is_default = False

    # 创建新配置
    config = StorageConfig(**config_data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return config.to_dict()


@router.patch("/{config_id}")
async def update_storage_config(
    config_id: UUID,
    config_update: StorageConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """更新存储配置"""
    result = await db.execute(select(StorageConfig).filter(StorageConfig.id == config_id))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="存储配置不存在"
        )

    # 如果设置为默认,取消其他默认配置
    if config_update.is_default:
        result = await db.execute(
            select(StorageConfig).filter(
                StorageConfig.is_default == True,
                StorageConfig.id != config_id
            )
        )
        existing_defaults = result.scalars().all()
        for c in existing_defaults:
            c.is_default = False

    # 更新字段
    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return config.to_dict()


@router.delete("/{config_id}")
async def delete_storage_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """删除存储配置"""
    result = await db.execute(select(StorageConfig).filter(StorageConfig.id == config_id))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="存储配置不存在"
        )

    # 不能删除默认配置
    if config.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除默认存储配置"
        )

    await db.delete(config)
    await db.commit()

    return {"message": "存储配置已删除"}


@router.post("/{config_id}/set-default")
async def set_default_storage_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
) -> Any:
    """设置为默认存储配置"""
    result = await db.execute(select(StorageConfig).filter(StorageConfig.id == config_id))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="存储配置不存在"
        )

    # 取消其他默认配置
    result = await db.execute(
        select(StorageConfig).filter(
            StorageConfig.is_default == True,
            StorageConfig.id != config_id
        )
    )
    existing_defaults = result.scalars().all()
    for c in existing_defaults:
        c.is_default = False

    config.is_default = True
    await db.commit()

    return {"message": "已设置为默认存储配置"}


__all__ = ["router"]
