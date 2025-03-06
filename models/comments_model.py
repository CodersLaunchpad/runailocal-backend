from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CommentBase(BaseModel):
    text: str
    article_id: str

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    """Model for returning comment information to clients"""
    id: str
    user_id: str
    username: str
    user_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None