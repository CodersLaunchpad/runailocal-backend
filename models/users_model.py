from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId

class UserBase(BaseModel):
    """Base user fields shared across different user models"""
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    """Model for creating a new user"""    
    password: str
    user_type: str = "normal"  # "normal", "author", "admin" # TODO: make enums
    region: Optional[str] = None
    profile_picture: Optional[str] = None
    profile_picture_initials: Optional[str] = None
    date_of_birth: str

class UserUpdate(BaseModel):
    """Model for updating an existing user"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_details: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    """Model for returning user information to clients"""
    id: str
    user_type: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    # model_config helps with API docs
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "username": "johndoe",
                    "email": "john@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "user_type": "normal",
                    "created_at": "2023-01-01T00:00:00",
                    "last_login": "2023-01-02T12:30:45",
                    "is_active": True
                }
            ]
        }
    }


async def get_author_data(db, author_id: ObjectId) -> Dict:
    """Get author data with follower count."""
    author_data = await db.users.find_one(
        {"_id": author_id},
        projection={
            "_id": 1,
            "username": 1,
            "first_name": 1,
            "last_name": 1,
            "profile_picture_base64": 1,
            "followers": 1,
            "following": 1,
            "bookmarks": 1,  # Include bookmarks field in the projection
        }
    )
    
    # Add follower_count to author data
    if author_data and "followers" in author_data:
        author_data["follower_count"] = len(author_data["followers"])
        # Remove the followers array if you don't need the actual follower details
        del author_data["followers"]
    else:
        if author_data:
            author_data["follower_count"] = 0
        else:
            return None
        
    if author_data and "following" in author_data:
        author_data["following_count"] = len(author_data["following"])
        # Remove the followers array if you don't need the actual follower details
        del author_data["following"]
    else:
        if author_data:
            author_data["following_count"] = 0
        else:
            return None
    
    #  Convert ObjectIds in the bookmarks array to strings, if it exists
    if "bookmarks" in author_data:
        author_data["bookmarks"] = [str(b) for b in author_data["bookmarks"]]
    
    return author_data

async def get_category_data(db, category_id: ObjectId) -> Dict:
    """Get category data."""
    if category_id:
        return await db.categories.find_one({"_id": category_id})
    return None