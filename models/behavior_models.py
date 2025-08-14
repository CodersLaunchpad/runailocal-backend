from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from utils.time import get_current_utc_time
from bson import ObjectId
from db.mongodb import PyObjectId
from models.enums import ActionType, ReadingFrequency, ContentLength, SubscriptionTier

class UserActivityLog(BaseModel):
    """Model for tracking user activity and behavior"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: PyObjectId
    action: ActionType
    article_id: Optional[PyObjectId] = None
    category_id: Optional[PyObjectId] = None
    author_id: Optional[PyObjectId] = None
    search_query: Optional[str] = None
    session_id: str
    timestamp: datetime = Field(default_factory=get_current_utc_time)
    
    # Reading behavior metrics
    reading_time: Optional[int] = None  # seconds spent reading
    scroll_percentage: Optional[float] = None  # 0.0 to 1.0
    click_position: Optional[Dict[str, Any]] = None  # x, y coordinates
    
    # Additional context
    device_type: Optional[str] = None  # mobile, desktop, tablet
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    referrer: Optional[str] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = {}

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class UserActivityCreate(BaseModel):
    """Model for creating user activity logs"""
    action: ActionType
    article_id: Optional[str] = None
    category_id: Optional[str] = None
    author_id: Optional[str] = None
    search_query: Optional[str] = None
    reading_time: Optional[int] = None
    scroll_percentage: Optional[float] = None
    click_position: Optional[Dict[str, Any]] = None
    device_type: Optional[str] = None
    referrer: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class UserPreferences(BaseModel):
    """Model for user reading preferences and behavior settings"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: PyObjectId
    
    # Content preferences
    preferred_categories: List[str] = []
    preferred_tags: List[str] = []
    disliked_categories: List[str] = []
    disliked_tags: List[str] = []
    
    # Reading behavior preferences
    reading_frequency: ReadingFrequency = ReadingFrequency.WEEKLY
    content_length_preference: ContentLength = ContentLength.ANY
    preferred_authors: List[str] = []
    
    # Subscription and notification settings
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    email_notifications: bool = True
    push_notifications: bool = False
    recommendation_emails: bool = True
    
    # Time-based preferences
    preferred_reading_times: List[int] = []  # Hours in 24h format, e.g., [9, 18] for 9 AM and 6 PM
    timezone: Optional[str] = "UTC"
    
    # Content discovery settings
    show_trending: bool = True
    show_similar_articles: bool = True
    cross_category_recommendations: bool = True
    
    # Privacy settings
    track_reading_behavior: bool = True
    share_reading_stats: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=get_current_utc_time)
    updated_at: datetime = Field(default_factory=get_current_utc_time)

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class UserPreferencesCreate(BaseModel):
    """Model for creating user preferences"""
    preferred_categories: Optional[List[str]] = []
    preferred_tags: Optional[List[str]] = []
    disliked_categories: Optional[List[str]] = []
    disliked_tags: Optional[List[str]] = []
    reading_frequency: Optional[ReadingFrequency] = ReadingFrequency.WEEKLY
    content_length_preference: Optional[ContentLength] = ContentLength.ANY
    preferred_authors: Optional[List[str]] = []
    email_notifications: Optional[bool] = True
    push_notifications: Optional[bool] = False
    recommendation_emails: Optional[bool] = True
    preferred_reading_times: Optional[List[int]] = []
    timezone: Optional[str] = "UTC"
    show_trending: Optional[bool] = True
    show_similar_articles: Optional[bool] = True
    cross_category_recommendations: Optional[bool] = True
    track_reading_behavior: Optional[bool] = True
    share_reading_stats: Optional[bool] = False

class UserPreferencesUpdate(BaseModel):
    """Model for updating user preferences"""
    preferred_categories: Optional[List[str]] = None
    preferred_tags: Optional[List[str]] = None
    disliked_categories: Optional[List[str]] = None
    disliked_tags: Optional[List[str]] = None
    reading_frequency: Optional[ReadingFrequency] = None
    content_length_preference: Optional[ContentLength] = None
    preferred_authors: Optional[List[str]] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    recommendation_emails: Optional[bool] = None
    preferred_reading_times: Optional[List[int]] = None
    timezone: Optional[str] = None
    show_trending: Optional[bool] = None
    show_similar_articles: Optional[bool] = None
    cross_category_recommendations: Optional[bool] = None
    track_reading_behavior: Optional[bool] = None
    share_reading_stats: Optional[bool] = None

class ReadingSession(BaseModel):
    """Model for tracking detailed reading sessions"""
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    user_id: PyObjectId
    article_id: PyObjectId
    session_id: str
    
    # Session metrics
    start_time: datetime = Field(default_factory=get_current_utc_time)
    end_time: Optional[datetime] = None
    total_time: Optional[int] = None  # seconds
    max_scroll_percentage: float = 0.0
    scroll_events: List[Dict[str, Any]] = []  # Detailed scroll tracking
    
    # Reading behavior
    reading_speed: Optional[float] = None  # words per minute
    pauses: List[Dict[str, Any]] = []  # Pause events with timestamps
    interactions: List[Dict[str, Any]] = []  # Clicks, highlights, etc.
    
    # Device and context
    device_type: Optional[str] = None
    screen_size: Optional[Dict[str, int]] = None  # width, height
    
    # Session completion
    completed: bool = False  # Did user read to the end
    completion_percentage: float = 0.0

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }

class ReadingSessionCreate(BaseModel):
    """Model for creating reading sessions"""
    article_id: str
    device_type: Optional[str] = None
    screen_size: Optional[Dict[str, int]] = None

class ReadingSessionUpdate(BaseModel):
    """Model for updating reading sessions"""
    end_time: Optional[datetime] = None
    total_time: Optional[int] = None
    max_scroll_percentage: Optional[float] = None
    scroll_events: Optional[List[Dict[str, Any]]] = None
    reading_speed: Optional[float] = None
    pauses: Optional[List[Dict[str, Any]]] = None
    interactions: Optional[List[Dict[str, Any]]] = None
    completed: Optional[bool] = None
    completion_percentage: Optional[float] = None