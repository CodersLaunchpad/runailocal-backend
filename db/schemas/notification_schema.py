from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, validator
from enum import Enum

class NotificationType(str, Enum):
    ARTICLE_POST = "article_post"
    FOLLOW = "follow"
    BADGE = "badge"  # For future use

class NotificationInDB(BaseModel):
    """
    Database model for notifications
    """
    id: str = Field(..., alias="_id")
    recipient_id: str
    sender_id: str
    sender_username: str
    notification_type: NotificationType
    source_id: str  # article_id for posts, follower_id for follows
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda dt: dt.isoformat()
        }

    @validator('id', 'recipient_id', 'sender_id', 'source_id', pre=True)
    def convert_objectid_to_str(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        return v

class NotificationCreate(BaseModel):
    """
    Model for creating new notifications
    """
    recipient_id: str
    sender_id: str
    sender_username: str
    notification_type: NotificationType
    source_id: str
    message: str

    @validator('recipient_id', 'sender_id', 'source_id', pre=True)
    def convert_str_to_objectid(cls, v):
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        return v

class NotificationResponse(BaseModel):
    """
    API response model for notifications
    """
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
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

def notification_db_to_response(notification_db: NotificationInDB) -> NotificationResponse:
    """
    Convert a NotificationInDB model to a NotificationResponse model
    """
    return NotificationResponse(
        id=str(notification_db.id),
        recipient_id=str(notification_db.recipient_id),
        sender_id=str(notification_db.sender_id),
        sender_username=notification_db.sender_username,
        notification_type=notification_db.notification_type,
        source_id=str(notification_db.source_id),
        message=notification_db.message,
        is_read=notification_db.is_read,
        created_at=notification_db.created_at,
        read_at=notification_db.read_at
    )