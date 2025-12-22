"""
电影相关 API Schema
"""

from typing import List, Optional
from pydantic import BaseModel, UUID4, Field, field_validator
from datetime import datetime, timedelta
from src.utils.storage import storage_client

# --- 剧本相关 ---
class ScriptGenerateRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None

class MovieShotBase(BaseModel):
    id: UUID4
    order_index: int
    visual_description: str
    camera_movement: Optional[str] = None
    dialogue: Optional[str] = None
    performance_prompt: Optional[str] = None
    first_frame_url: Optional[str] = None
    first_frame_prompt: Optional[str] = None
    last_frame_url: Optional[str] = None
    last_frame_prompt: Optional[str] = None
    video_url: Optional[str] = None
    video_prompt: Optional[str] = None
    api_key_id: Optional[str] = None
    status: Optional[str] = "pending"
    last_error: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @field_validator("first_frame_url", "last_frame_url", "video_url", mode="after")
    @classmethod
    def sign_urls(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("http"):
            return storage_client.get_presigned_url(v, timedelta(hours=24))
        return v

class MovieSceneBase(BaseModel):
    id: UUID4
    order_index: int
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    atmosphere: Optional[str] = None
    description: Optional[str] = None
    shots: List[MovieShotBase]
    
    class Config:
        from_attributes = True

class MovieScriptResponse(BaseModel):
    id: UUID4
    chapter_id: UUID4
    status: str
    scenes: List[MovieSceneBase]
    class Config:
        from_attributes = True

# --- 角色相关 ---
class MovieCharacterBase(BaseModel):
    id: UUID4
    name: str
    role_description: Optional[str] = None
    visual_traits: Optional[str] = None
    dialogue_traits: Optional[str] = None
    avatar_url: Optional[str] = None
    reference_images: List[str] = []
    class Config:
        from_attributes = True

    @field_validator("avatar_url", mode="after")
    @classmethod
    def sign_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith("http"):
            return storage_client.get_presigned_url(v, timedelta(hours=24))
        return v

    @field_validator("reference_images", mode="after")
    @classmethod
    def sign_reference_images(cls, v: List[str]) -> List[str]:
        if not v:
            return v
        return [
            storage_client.get_presigned_url(img, timedelta(hours=24))
            if img and not img.startswith("http") else img
            for img in v
        ]

class CharacterExtractRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None

class CharacterUpdateRequest(BaseModel):
    avatar_url: Optional[str] = None
    reference_images: Optional[List[str]] = None

class CharacterGenerateRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None # e.g. "flux-pro"
    style: Optional[str] = "cinematic"
    prompt: Optional[str] = None

class KeyframeGenerateRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None

# --- 生产相关 ---
class ShotProduceRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = "veo_3_1-fast"

class BatchProduceRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None

# --- 更新请求 ---
class ShotUpdateRequest(BaseModel):
    video_prompt: Optional[str] = None
    first_frame_prompt: Optional[str] = None
    last_frame_prompt: Optional[str] = None
    visual_description: Optional[str] = None
    dialogue: Optional[str] = None
    camera_movement: Optional[str] = None
