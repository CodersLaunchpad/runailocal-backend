from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId

# PyObjectId for MongoDB ObjectId compatibility with Pydantic
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

class UserCreate(UserBase):
    password: str
    user_type: str = "normal"  # "normal", "author", "admin" # TODO: make enums

class AuthorDetails(BaseModel):
    bio: Optional[str] = None
    slug: Optional[str] = None
    picture_url: Optional[str] = None
    twitter_profile: Optional[str] = None
    linkedin_profile: Optional[str] = None
    nationality: Optional[Dict[str, Any]] = None
    residence: Optional[Dict[str, Any]] = None
    date_of_birth: Optional[datetime] = None

class AdminDetails(BaseModel):
    role: str
    department: Optional[str] = None
    super_admin: bool = False

class NormalUserDetails(BaseModel):
    signup_date: datetime = Field(default_factory=datetime.utcnow)
    email_notifications: bool = True
    reading_preferences: List[str] = []

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    user_details: Dict[str, Any] = {}
    favorites: List[PyObjectId] = []
    following: List[PyObjectId] = []

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_details: Optional[Dict[str, Any]] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = None

class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryInDB(CategoryBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color: Optional[str] = None

class ArticleBase(BaseModel):
    name: str
    slug: str
    body: str
    summary: Optional[str] = None
    category: Dict[str, Any]
    featured: bool = False
    tags: List[str] = []

class ArticleCreate(ArticleBase):
    pass

class ArticleImage(BaseModel):
    url: str
    is_main: bool = False
    is_thumbnail: bool = False
    caption: Optional[str] = None

class ArticleInDB(ArticleBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    author_id: PyObjectId
    images: List[ArticleImage] = []
    published_at: Optional[datetime] = None
    comments: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class ArticleUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    body: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[Dict[str, Any]] = None
    featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    published_at: Optional[datetime] = None

class CommentCreate(BaseModel):
    text: str
    article_id: PyObjectId

class CommentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId)
    text: str
    user_id: PyObjectId
    username: str
    user_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class MessageCreate(BaseModel):
    recipient_id: PyObjectId
    text: str

class MessageInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    sender_id: PyObjectId
    recipient_id: PyObjectId
    text: str
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)