from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CommentBase(BaseModel):
    text: str
    article_id: str
    parent_comment_id: Optional[str] = None

class CommentCreate(CommentBase):
    pass

class AuthorInfo(BaseModel):
    """Model for author information in comments"""
    id: str
    username: str
    first_name: str
    last_name: str
    profile_picture_base64: Optional[str] = "DEPRECIATED"
    bookmarks: List[str] = Field(default_factory=list)
    profile_photo_id: Optional[str] = None
    profile_file: Optional[Dict[str, Any]] = None
    user_type: Optional[str] = "normal"

class CommentResponse(CommentBase):
    """Model for returning comment information to clients"""
    id: str
    user_id: str
    username: str
    user_first_name: str
    user_last_name: str
    user_type: str
    author: AuthorInfo
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: List["CommentResponse"] = Field(default_factory=list)

# Add this line to resolve the forward reference
CommentResponse.model_rebuild()