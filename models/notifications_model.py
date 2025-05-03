from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from bson import ObjectId

# 1. First fix the NotificationType implementation
class NotificationType(str, Enum):
    ARTICLE_POST = "article_post"
    FOLLOW = "follow"
    BADGE = "badge"

# 2. Then define your models
class NotificationCreate(BaseModel):
    recipient_id: str
    sender_id: str
    sender_username: str
    notification_type: NotificationType  # This now works correctly
    source_id: str
    message: str

    class Config:
        json_encoders = {ObjectId: str}

class NotificationResponse(BaseModel):
    id: str
    recipient_id: str
    sender_id: str
    sender_username: str
    notification_type: NotificationType
    source_id: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

    class Config:
        json_encoders = {ObjectId: str}