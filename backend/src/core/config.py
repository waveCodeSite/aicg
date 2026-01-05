"""
应用配置模块 - 精简版
只保留实际使用的配置项
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置类"""

    # =============================================================================
    # 应用基础配置
    # =============================================================================
    APP_NAME: str = "AICG Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # =============================================================================
    # CORS和安全配置
    # =============================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:8080"
    ]
    ALLOWED_HOSTS: List[str] = ["*"]

    # =============================================================================
    # 数据库配置
    # =============================================================================
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://aicg_user:aicg_password@localhost:5432/aicg_platform",
        env="DATABASE_URL"
    )
    DATABASE_POOL_PRE_PING: bool = True
    DATABASE_POOL_RECYCLE: int = 3600

    # =============================================================================
    # Redis和Celery配置
    # =============================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )

    # =============================================================================
    # JWT配置
    # =============================================================================
    JWT_SECRET_KEY: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天 (7 * 24 * 60)

    # =============================================================================
    # 加密配置
    # =============================================================================
    API_KEY_ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        env="API_KEY_ENCRYPTION_KEY"
    )

    # =============================================================================
    # 对象存储配置 (支持S3协议)
    # =============================================================================
    STORAGE_TYPE: str = Field(
        default="minio",
        env="STORAGE_TYPE",
        description="存储类型: minio, s3, aliyun-oss, etc"
    )
    STORAGE_ENDPOINT: str = Field(default="localhost:9000", env="STORAGE_ENDPOINT")
    STORAGE_PUBLIC_URL: Optional[str] = Field(default=None, env="STORAGE_PUBLIC_URL")
    STORAGE_ACCESS_KEY: str = Field(default="minioadmin", env="STORAGE_ACCESS_KEY")
    STORAGE_SECRET_KEY: str = Field(default="minioadmin", env="STORAGE_SECRET_KEY")
    STORAGE_SECURE: bool = Field(default=False, env="STORAGE_SECURE")
    STORAGE_BUCKET_NAME: str = Field(default="aicg-files", env="STORAGE_BUCKET_NAME")
    STORAGE_REGION: str = Field(default="us-east-1", env="STORAGE_REGION")

    # 向后兼容的MinIO配置
    @property
    def MINIO_ENDPOINT(self) -> str:
        return self.STORAGE_ENDPOINT

    @property
    def MINIO_PUBLIC_URL(self) -> Optional[str]:
        return self.STORAGE_PUBLIC_URL

    @property
    def MINIO_ACCESS_KEY(self) -> str:
        return self.STORAGE_ACCESS_KEY

    @property
    def MINIO_SECRET_KEY(self) -> str:
        return self.STORAGE_SECRET_KEY

    @property
    def MINIO_SECURE(self) -> bool:
        return self.STORAGE_SECURE

    @property
    def MINIO_BUCKET_NAME(self) -> str:
        return self.STORAGE_BUCKET_NAME

    @property
    def MINIO_REGION(self) -> str:
        return self.STORAGE_REGION

    # =============================================================================
    # 头像上传配置
    # =============================================================================
    AVATAR_BUCKET_NAME: str = "aicg-avatars"
    MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_AVATAR_TYPES: List[str] = ["jpg", "jpeg", "png", "webp"]
    AVATAR_DEFAULT_SIZE: tuple = (200, 200)

    # =============================================================================
    # 日志配置
    # =============================================================================
    LOG_LEVEL: str = "INFO"
    STRUCTURED_LOGGING: bool = True
    LOG_FILE: Optional[str] = None
    COLORED_LOGS: bool = True

    # =============================================================================
    # 验证器
    # =============================================================================
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError("CORS_ORIGINS必须是字符串或列表")

    @field_validator("ALLOWED_AVATAR_TYPES", mode="before")
    @classmethod
    def assemble_allowed_avatar_types(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip().lower() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return [i.lower() for i in v] if isinstance(v, list) else v
        raise ValueError("ALLOWED_AVATAR_TYPES必须是字符串或列表")

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = ["development", "testing", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"ENVIRONMENT必须是以下之一: {valid_envs}")
        return v

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL必须是以下之一: {valid_levels}")
        return v.upper()

    # =============================================================================
    # 属性方法
    # =============================================================================
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def database_url_sync(self) -> str:
        """同步数据库URL（用于Alembic）"""
        return self.DATABASE_URL.replace("+asyncpg", "")

    @property
    def minio_url(self) -> str:
        """MinIO服务URL"""
        protocol = "https" if self.MINIO_SECURE else "http"
        return f"{protocol}://{self.MINIO_ENDPOINT}"

    @property
    def minio_bucket(self) -> str:
        """MinIO默认存储桶名称"""
        return self.MINIO_BUCKET_NAME

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """获取应用设置（单例模式）"""
    return Settings()


# 导出设置实例
settings = get_settings()
