from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CommentBase(BaseModel):
    text: str
    article_id: str
    parent_comment_id: Optional[str] = None

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    """Model for returning comment information to clients"""
    id: str
    user_id: str
    user_first_name: str
    user_last_name: str
    username: str
    user_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: List["CommentResponse"] = Field(default_factory=list)

# Add this line to resolve the forward reference
CommentResponse.model_rebuild()