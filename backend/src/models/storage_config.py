"""
存储配置数据模型
"""

from sqlalchemy import Column, String, Boolean, Text, JSON
from src.models.base import BaseModel


class StorageConfig(BaseModel):
    """存储配置模型"""
    __tablename__ = 'storage_configs'

    name = Column(String(100), nullable=False, comment="配置名称")
    storage_type = Column(String(50), nullable=False, comment="存储类型: minio, s3, aliyun-oss等")
    endpoint = Column(String(255), nullable=False, comment="存储端点")
    access_key = Column(String(255), nullable=False, comment="访问密钥")
    secret_key = Column(Text, nullable=False, comment="密钥(加密存储)")
    bucket_name = Column(String(100), nullable=False, comment="存储桶名称")
    region = Column(String(50), default='us-east-1', comment="区域")
    is_secure = Column(Boolean, default=False, comment="是否使用HTTPS")
    public_url = Column(String(255), nullable=True, comment="公开访问URL")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否为默认配置")
    extra_config = Column(JSON, nullable=True, comment="额外配置(JSON)")

    def to_dict(self) -> dict:
        """转换为字典(不包含敏感信息)"""
        return {
            "id": str(self.id),
            "name": self.name,
            "storage_type": self.storage_type,
            "endpoint": self.endpoint,
            "bucket_name": self.bucket_name,
            "region": self.region,
            "is_secure": self.is_secure,
            "public_url": self.public_url,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


__all__ = ["StorageConfig"]
