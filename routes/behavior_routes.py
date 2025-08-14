from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from services.behavior_service import BehaviorService
from models.behavior_models import (
    UserActivityCreate, UserPreferencesCreate, UserPreferencesUpdate,
    ReadingSessionCreate, ReadingSessionUpdate
)
from models.enums import ActionType, SubscriptionTier
from dependencies.db import get_db
from dependencies.auth import get_current_user_optional, get_current_user
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid

router = APIRouter(prefix="/behavior", tags=["behavior"])

async def get_behavior_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> BehaviorService:
    """Dependency to get behavior service"""
    return BehaviorService(db)

@router.post("/track")
async def track_user_activity(
    activity: UserActivityCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Track user activity"""
    try:
        session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())
        user_agent = request.headers.get("User-Agent")
        
        # Get client IP (considering proxy headers)
        ip_address = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.headers.get("X-Real-IP") or
            request.client.host if request.client else None
        )
        
        activity_id = await behavior_service.log_activity(
            user_id=str(current_user.id),
            activity=activity,
            session_id=session_id,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        return {
            "message": "Activity tracked successfully",
            "activity_id": activity_id,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track activity: {str(e)}")

@router.post("/view/{article_id}")
async def track_article_view(
    article_id: str,
    request: Request,
    reading_time: Optional[int] = None,
    scroll_percentage: Optional[float] = None,
    current_user: dict = Depends(get_current_user_optional),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Track article view with optional reading metrics"""
    try:
        if not current_user:
            # For anonymous users, we could track basic metrics if needed
            return {"message": "View tracked (anonymous)"}
        
        session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())
        user_agent = request.headers.get("User-Agent")
        device_type = _detect_device_type(user_agent)
        
        success = await behavior_service.track_article_view(
            user_id=str(current_user.id),
            article_id=article_id,
            session_id=session_id,
            device_type=device_type,
            reading_time=reading_time,
            scroll_percentage=scroll_percentage,
            referrer=request.headers.get("Referer")
        )
        
        return {
            "message": "Article view tracked successfully",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track view: {str(e)}")

@router.post("/reading-session/start")
async def start_reading_session(
    session: ReadingSessionCreate,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Start a new reading session"""
    try:
        session_id = await behavior_service.start_reading_session(
            user_id=str(current_user.id),
            session=session
        )
        
        return {
            "message": "Reading session started",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")

@router.put("/reading-session/{session_id}")
async def update_reading_session(
    session_id: str,
    session_update: ReadingSessionUpdate,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Update reading session with metrics"""
    try:
        success = await behavior_service.update_reading_session(
            session_id=session_id,
            session_update=session_update
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Reading session not found")
        
        return {"message": "Reading session updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")

@router.get("/activity")
async def get_user_activity(
    action_types: Optional[List[ActionType]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Get user activity history"""
    try:
        activities = await behavior_service.get_user_activity_history(
            user_id=str(current_user.id),
            action_types=action_types,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "activities": activities,
            "total": len(activities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get activities: {str(e)}")

@router.get("/stats")
async def get_reading_stats(
    days: int = 30,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Get user reading statistics"""
    try:
        stats = await behavior_service.get_user_reading_stats(
            user_id=str(current_user.id),
            days=days
        )
        
        return {
            "stats": stats,
            "period_days": days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/engagement")
async def get_engagement_metrics(
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Get user engagement metrics"""
    try:
        metrics = await behavior_service.get_user_engagement_metrics(
            user_id=str(current_user.id)
        )
        
        return {
            "engagement_metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get engagement metrics: {str(e)}")

# User Preferences Endpoints

@router.post("/preferences")
async def create_user_preferences(
    preferences: UserPreferencesCreate,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Create user preferences"""
    try:
        preferences_id = await behavior_service.create_user_preferences(
            user_id=str(current_user.id),
            preferences=preferences
        )
        
        return {
            "message": "User preferences created successfully",
            "preferences_id": preferences_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create preferences: {str(e)}")

@router.get("/preferences")
async def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Get user preferences"""
    try:
        preferences = await behavior_service.get_user_preferences(
            user_id=str(current_user.id)
        )
        
        if not preferences:
            # Return default preferences if none exist
            return {
                "preferences": None,
                "message": "No preferences found. Using defaults."
            }
        
        return {"preferences": preferences}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get preferences: {str(e)}")

@router.put("/preferences")
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Update user preferences"""
    try:
        success = await behavior_service.update_user_preferences(
            user_id=str(current_user.id),
            preferences=preferences
        )
        
        return {
            "message": "User preferences updated successfully",
            "updated": success
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

@router.put("/preferences/subscription/{tier}")
async def update_subscription_tier(
    tier: SubscriptionTier,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Update user subscription tier"""
    try:
        success = await behavior_service.update_subscription_tier(
            user_id=str(current_user.id),
            tier=tier
        )
        
        return {
            "message": f"Subscription tier updated to {tier}",
            "updated": success
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")

@router.get("/popular-content")
async def get_popular_content_for_user(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Get popular content based on user behavior patterns"""
    try:
        articles = await behavior_service.get_popular_content_for_user(
            user_id=str(current_user.id),
            limit=limit
        )
        
        return {
            "articles": articles,
            "total": len(articles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get popular content: {str(e)}")

# Utility endpoints for frontend integration

@router.post("/scroll-tracking")
async def track_scroll_events(
    article_id: str,
    scroll_events: List[Dict[str, Any]],
    session_id: str,
    current_user: dict = Depends(get_current_user_optional),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Track detailed scroll events during reading"""
    try:
        if not current_user:
            return {"message": "Scroll events tracked (anonymous)"}
        
        # Log scroll events as activity
        for event in scroll_events:
            await behavior_service.log_activity(
                user_id=str(current_user.id),
                activity=UserActivityCreate(
                    action=ActionType.SCROLL,
                    article_id=article_id,
                    scroll_percentage=event.get("scroll_percentage"),
                    metadata={
                        "scroll_direction": event.get("direction"),
                        "viewport_height": event.get("viewport_height"),
                        "document_height": event.get("document_height")
                    }
                ),
                session_id=session_id
            )
        
        return {"message": "Scroll events tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track scroll events: {str(e)}")

@router.post("/reading-time")
async def track_reading_time(
    article_id: str,
    reading_time: int,  # in seconds
    words_read: Optional[int] = None,
    current_user: dict = Depends(get_current_user_optional),
    behavior_service: BehaviorService = Depends(get_behavior_service)
):
    """Track time spent reading an article"""
    try:
        if not current_user:
            return {"message": "Reading time tracked (anonymous)"}
        
        await behavior_service.log_activity(
            user_id=str(current_user.id),
            activity=UserActivityCreate(
                action=ActionType.READ_TIME,
                article_id=article_id,
                reading_time=reading_time,
                metadata={
                    "words_read": words_read,
                    "reading_speed_wpm": (words_read * 60 / reading_time) if words_read and reading_time > 0 else None
                }
            )
        )
        
        return {"message": "Reading time tracked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track reading time: {str(e)}")

def _detect_device_type(user_agent: str) -> str:
    """Detect device type from user agent"""
    if not user_agent:
        return "unknown"
    
    user_agent_lower = user_agent.lower()
    
    if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone"]):
        return "mobile"
    elif any(tablet in user_agent_lower for tablet in ["ipad", "tablet"]):
        return "tablet"
    else:
        return "desktop"