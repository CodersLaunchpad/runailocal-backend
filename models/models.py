from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
from pydantic import GetCoreSchemaHandler
from typing import Annotated, List, Optional, Dict, Any, ClassVar, Type, Union
from datetime import datetime, timezone
from pydantic_core import core_schema
from bson import ObjectId
from utils.time import get_current_utc_time

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

# Custom PyObjectId class for Pydantic integration with MongoDB ObjectId
class PyObjectId(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Type[Any], _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema([
            # Accept ObjectId objects directly
            core_schema.is_instance_schema(ObjectId),
            # Also accept str instances that can be converted to ObjectId
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(
                    lambda v: ObjectId(v) if ObjectId.is_valid(v) else None
                ),
            ]),
        ])
    
    # For better debugging
    def __repr__(self) -> str:
        return f"PyObjectId({super().__repr__()})"


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
    id: PyObjectId = Field(default_factory=lambda: ObjectId(), alias="_id")

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }

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

class ArticleStatus(str, Enum):
    draft = "draft"
    published = "published"
    rejected = "rejected"
    pending = "pending"

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
    read_time: int
    status: ArticleStatus

    model_config = {
        "arbitrary_types_allowed": True
    }

class ArticleCreate(ArticleBase):
    status: ArticleStatus = ArticleStatus.draft  # Default is "draft"

class ArticleImage(BaseModel):
    url: str
    is_main: bool = False
    is_thumbnail: bool = False
    caption: Optional[str] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class ArticleInDB(ArticleBase):
    id: PyObjectId = Field(default_factory=lambda: ObjectId(), alias="_id")
    author_id: PyObjectId
    images: List[ArticleImage] = []
    published_at: Optional[datetime] = None
    comments: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    status: ArticleStatus
    bookmarked_by: List[PyObjectId] = []

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class ArticleUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    # body: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    status: Optional[ArticleStatus] = None
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

class MessageCreate(BaseModel):
    recipient_id: PyObjectId
    text: str

    model_config = {
        "arbitrary_types_allowed": True
    }

class MessageInDB(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: ObjectId(), alias="_id")
    sender_id: PyObjectId
    recipient_id: PyObjectId
    text: str
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "arbitrary_types_allowed": True
    }

class AppSettings(BaseModel):
    """Application-wide settings"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    auto_publish_articles: bool = False
    auto_upload: bool = False
    updated_at: datetime = Field(default_factory=get_current_utc_time)
    updated_by: Optional[str] = None

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "auto_publish_articles": False,
                "auto_upload": False,
                "updated_at": "2024-03-25T12:00:00Z",
                "updated_by": "admin_user_id"
            }
        }