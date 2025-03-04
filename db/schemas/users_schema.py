from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime
from helpers.time import get_current_utc_time
from bson import ObjectId
from db.mongodb import PyObjectId
from models.users_model import UserBase

class UserInDB(BaseModel):
    """Database representation of a user document"""    
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password_hash: str
    user_type: str
    user_details: Dict[str, Any] = {}
    profile_picture_base64:  Optional[str] = None 

    # Relationships with other users
    favorites: List[PyObjectId] = []
    following: List[PyObjectId] = []
    followers: List[PyObjectId] = []
    bookmarks: List[PyObjectId] = []
    
    # Metadata
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=get_current_utc_time)
    is_active: bool = True

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }

    # NOTE: if you add a new list of IDs, add the field in this field validator
    @field_validator('favorites', 'following', 'followers', 'bookmarks', mode='before')
    @classmethod
    def convert_object_ids(cls, v):
        """Ensure lists of IDs are properly handled"""
        if isinstance(v, list):
            return [str(x) if isinstance(x, ObjectId) else x for x in v]
        return v
