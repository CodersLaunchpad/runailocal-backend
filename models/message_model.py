from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class MessageBase(BaseModel):
    """Base message fields shared across different message models"""
    content: str
    sender_id: str
    receiver_id: str

class MessageCreate(MessageBase):
    """Model for creating a new message"""
    pass

class MessageResponse(MessageBase):
    """Model for returning message information to clients"""
    id: str
    created_at: datetime
    read_at: Optional[datetime] = None
    is_read: bool = False

    class Config:
        json_encoders = {
            ObjectId: str
        }

class Conversation(BaseModel):
    """Model for conversation between two users"""
    id: str
    participants: List[str]
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0
    updated_at: datetime

    class Config:
        json_encoders = {
            ObjectId: str
        } 