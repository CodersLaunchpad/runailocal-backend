from pydantic import BaseModel, Field, EmailStr
from pydantic import GetCoreSchemaHandler
from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from bson import ObjectId

# Helper functions to handle ObjectId
def ensure_object_id(v):
    """Convert to ObjectId or validate existing ObjectId"""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str):
        try:
            return ObjectId(v)
        except Exception:
            raise ValueError(f"Invalid ObjectId: {v}")
    raise ValueError(f"Cannot convert {type(v)} to ObjectId")

def object_id_to_str(v):
    """Convert ObjectId to string"""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        # Validate it's a valid ObjectId format
        try:
            ObjectId(v)
            return v
        except:
            raise ValueError(f"Invalid ObjectId string: {v}")
    raise ValueError(f"Expected ObjectId or string, got {type(v)}")

# Use Annotated to create a type that validates ObjectId strings
PyObjectId = Annotated[str, Field(default_factory=lambda: str(ObjectId()))]


# Models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True
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

    model_config = {
        "arbitrary_types_allowed": True
    }

class AdminDetails(BaseModel):
    role: str
    department: Optional[str] = None
    super_admin: bool = False

    model_config = {
        "arbitrary_types_allowed": True
    }

class NormalUserDetails(BaseModel):
    signup_date: datetime = Field(default_factory=datetime.utcnow)
    email_notifications: bool = True
    reading_preferences: List[str] = []

    model_config = {
        "arbitrary_types_allowed": True
    }

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
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

    model_config = {
        "arbitrary_types_allowed": True
    }

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

    model_config = {
        "arbitrary_types_allowed": True
    }

class CategoryCreate(CategoryBase):
    pass

class CategoryInDB(CategoryBase):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    color: Optional[str] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class ArticleBase(BaseModel):
    name: str
    slug: str
    body: str
    summary: Optional[str] = None
    category: Dict[str, Any]
    featured: bool = False
    tags: List[str] = []

    model_config = {
        "arbitrary_types_allowed": True
    }

class ArticleCreate(ArticleBase):
    pass

class ArticleImage(BaseModel):
    url: str
    is_main: bool = False
    is_thumbnail: bool = False
    caption: Optional[str] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class ArticleInDB(ArticleBase):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
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

    model_config = {
        "arbitrary_types_allowed": True
    }

class CommentCreate(BaseModel):
    text: str
    article_id: PyObjectId

    model_config = {
        "arbitrary_types_allowed": True
    }

class CommentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()))
    text: str
    user_id: PyObjectId
    username: str
    user_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class MessageCreate(BaseModel):
    recipient_id: PyObjectId
    text: str

    model_config = {
        "arbitrary_types_allowed": True
    }

class MessageInDB(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    sender_id: PyObjectId
    recipient_id: PyObjectId
    text: str
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "arbitrary_types_allowed": True
    }