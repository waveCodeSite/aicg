"""
电影相关 API Schema
"""

from typing import List, Optional
from pydantic import BaseModel, UUID4
from datetime import datetime

# --- 剧本相关 ---
class ScriptGenerateRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None

class MovieShotBase(BaseModel):
    order_index: int
    visual_description: str
    camera_movement: Optional[str] = None
    dialogue: Optional[str] = None
    performance_prompt: Optional[str] = None
    first_frame_url: Optional[str] = None
    video_url: Optional[str] = None

class MovieSceneBase(BaseModel):
    order_index: int
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    atmosphere: Optional[str] = None
    description: Optional[str] = None
    shots: List[MovieShotBase]

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

class CharacterExtractRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = None

class CharacterUpdateRequest(BaseModel):
    avatar_url: Optional[str] = None
    reference_images: Optional[List[str]] = None

# --- 生产相关 ---
class ShotProduceRequest(BaseModel):
    api_key_id: str
    model: Optional[str] = "veo3.1-fast"
