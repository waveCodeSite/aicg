"""
图片生成相关的Pydantic模式
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """生成图片请求模型"""
    chapter_id: UUID = Field(..., description="章节ID")
    api_key_id: UUID = Field(..., description="API密钥ID")


class ImageGenerateResponse(BaseModel):
    """生成图片响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
