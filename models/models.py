from pydantic import BaseModel, Field, EmailStr, validator
from pydantic import GetCoreSchemaHandler
from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime, timezone
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

def prepare_mongo_document(doc):
    """
    Convert all ObjectId values to strings and rename _id fields to id
    """
    if doc is None:
        return None
        
    # Handle lists
    if isinstance(doc, list):
        return [prepare_mongo_document(item) for item in doc]
        
    # If not a dict, return as is
    if not isinstance(doc, dict):
        return doc
        
    result = {}
    
    for key, value in doc.items():
        # Convert _id to id
        if key == "_id":
            result["id"] = str(value)
            continue
            
        # Convert ObjectId values to strings
        if isinstance(value, ObjectId):
            result[key] = str(value)
            continue
            
        # Convert datetime to ISO format string
        if isinstance(value, datetime):
            result[key] = value.isoformat()
            continue
            
        # Handle nested dicts
        if isinstance(value, dict):
            result[key] = prepare_mongo_document(value)
            continue
            
        # Handle lists that might contain dicts or ObjectIds
        if isinstance(value, list):
            result[key] = prepare_mongo_document(value)
            continue
            
        # For all other types, use as is
        result[key] = value
        
    return result

def clean_document(doc):
    if isinstance(doc, dict):
        return {k: clean_document(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [clean_document(i) for i in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc

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
    region: Optional[str] = None
    profile_picture: Optional[str] = None
    profile_picture_initials: Optional[str] = None
    date_of_birth: str

# class UserCreate(BaseModel):
#     password: str
#     user_type: str = "normal"  # "normal", "author", "admin" # TODO: make enums
#     region: Optional[str] = None
#     username: str
#     email: EmailStr
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     is_active: bool = True

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True
    }

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
    user_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    user_details: Dict[str, Any] = {}
    favorites: List[PyObjectId] = []
    following: List[PyObjectId] = []
    followers: List[PyObjectId] = []
    profile_picture_base64:  str
    bookmarks: List[PyObjectId] = []

    # Add validators to ensure ObjectId conversion in lists
    @validator('following', 'favorites', 'followers', 'bookmarks', pre=True)
    def convert_object_ids(cls, v):
        if isinstance(v, list):
            return [PyObjectId(x) for x in v]
        return v

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        },
        # Add this to allow Pydantic to automatically convert ObjectId to string
        "json_schema_extra": {
            "example": {
                "_id": "67beed4f38b4657e1f23cc80",
                "password_hash": "hashed_password",
                "created_at": "2023-01-01T00:00:00",
                "user_details": {},
                "favorites": [],
                "following": [],
                "bookmarks": []
            }
        }
    }
    
    # Add this method to handle conversion
    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj.get("_id"), ObjectId):
            obj["_id"] = str(obj["_id"])
        return super().model_validate(obj, *args, **kwargs)

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
    profile_picture_base64: str
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

class CategoryResponse(CategoryBase):
    id: str

    class Config:
        # This lets you map fields from the source model to different names
        field_customizations = {
            "id": {"alias": "_id"}
        }

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
    content: str
    excerpt: Optional[str] = None
    # category: Dict[str, Any]
    # featured: bool = False
    # tags: List[str] = []
    # category: PyObjectId
    # author: PyObjectId
    category_id: str
    author_id: str
    image: str
    read_time: str


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
    bookmarked_by: List[PyObjectId] = []

    

class ArticleUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    # body: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    published_at: Optional[datetime] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class ArticleStatusUpdate(BaseModel):
    status: str = Field(..., description="Status can be: draft, pending, published, rejected")
    featured: Optional[bool] = None
    is_popular: Optional[bool] = None
    is_spotlight: Optional[bool] = None
    rejection_reason: Optional[str] = None

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