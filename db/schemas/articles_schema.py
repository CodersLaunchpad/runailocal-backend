from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from utils.time import get_current_utc_time
from bson import ObjectId
from db.mongodb import PyObjectId
from models.models import ArticleStatus

class ArticleBase(BaseModel):
    """Base article fields shared across different article models"""
    name: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    image: Optional[str] = None
    read_time: int
    status: str = "draft" # TODO: make it an enum

class ArticleCreate(ArticleBase):
    """Model for creating a new article"""
    category_id: str
    tags: Optional[List[str]] = []
    is_spotlight: bool = False
    is_popular: bool = False

class ArticleUpdate(BaseModel):
    """Model for updating an existing article"""
    name: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category_id: Optional[str] = None
    image: Optional[str] = None
    read_time: Optional[int] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    is_spotlight: Optional[bool] = None
    is_popular: Optional[bool] = None

class ArticleInDB(ArticleBase):
    """Database representation of an article document"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    category_id: PyObjectId
    author_id: PyObjectId
    tags: List[str] = []
    created_at: datetime = Field(default_factory=get_current_utc_time)
    updated_at: datetime = Field(default_factory=get_current_utc_time)
    views: int = 0
    likes: int = 0
    comments: List[Dict[str, Any]] = []
    bookmarked_by: List[PyObjectId] = []
    is_spotlight: bool = False
    is_popular: bool = False

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }
    
    @field_validator('bookmarked_by', mode='before')
    @classmethod
    def convert_object_ids(cls, v):
        """Ensure lists of IDs are properly handled"""
        if isinstance(v, list):
            return [str(x) if isinstance(x, ObjectId) else x for x in v]
        return v

class ArticleResponse(ArticleBase):
    """Model for returning article information to clients"""
    id: str
    category: Optional[Dict[str, Any]] = None
    author: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    views: int
    likes: int
    comments: List[Dict[str, Any]] = []
    bookmarked_by: List[str] = []
    tags: List[str] = []
    is_spotlight: bool = False
    is_popular: bool = False
    
    # model_config helps with API docs
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "name": "Article Title",
                    "slug": "article-title",
                    "content": "Article content here",
                    "excerpt": "Brief excerpt",
                    "image": "image_url.jpg",
                    "read_time": 5,
                    "status": "published",
                    "category": {
                        "id": "507f1f77bcf86cd799439012",
                        "name": "Technology",
                        "slug": "technology"
                    },
                    "author": {
                        "id": "507f1f77bcf86cd799439013",
                        "username": "johndoe",
                        "first_name": "John",
                        "last_name": "Doe",
                        "profile_picture_base64": "base64string"
                    },
                    "created_at": "2023-01-01T00:00:00",
                    "updated_at": "2023-01-02T12:30:45",
                    "views": 120,
                    "likes": 25,
                    "comments": [
                        {
                            "id": "507f1f77bcf86cd799439014",
                            "user_id": "507f1f77bcf86cd799439015",
                            "content": "Great article!",
                            "created_at": "2023-01-03T15:45:00"
                        }
                    ],
                    "bookmarked_by": ["507f1f77bcf86cd799439016"],
                    "tags": ["tech", "programming"],
                    "is_spotlight": True,
                    "is_popular": True
                }
            ]
        }
    }