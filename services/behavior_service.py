from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.behavior_models import (
    UserActivityLog, UserActivityCreate,
    UserPreferences, UserPreferencesCreate, UserPreferencesUpdate,
    ReadingSession, ReadingSessionCreate, ReadingSessionUpdate
)
from models.enums import ActionType, SubscriptionTier
from utils.time import get_current_utc_time
import uuid
from collections import defaultdict

class BehaviorService:
    """Service for managing user behavior tracking and analytics"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.activity_collection = db.user_activities
        self.preferences_collection = db.user_preferences
        self.sessions_collection = db.reading_sessions
    
    async def log_activity(
        self, 
        user_id: str, 
        activity: UserActivityCreate,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log user activity"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        activity_log = UserActivityLog(
            user_id=ObjectId(user_id),
            action=activity.action,
            article_id=ObjectId(activity.article_id) if activity.article_id else None,
            category_id=ObjectId(activity.category_id) if activity.category_id else None,
            author_id=ObjectId(activity.author_id) if activity.author_id else None,
            search_query=activity.search_query,
            session_id=session_id,
            reading_time=activity.reading_time,
            scroll_percentage=activity.scroll_percentage,
            click_position=activity.click_position,
            device_type=activity.device_type,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=activity.referrer,
            metadata=activity.metadata or {}
        )
        
        result = await self.activity_collection.insert_one(activity_log.model_dump(by_alias=True))
        return str(result.inserted_id)
    
    async def track_article_view(
        self, 
        user_id: str, 
        article_id: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Track article view and increment view count"""
        # Log the activity
        await self.log_activity(
            user_id=user_id,
            activity=UserActivityCreate(
                action=ActionType.VIEW,
                article_id=article_id,
                **kwargs
            ),
            session_id=session_id
        )
        
        # Increment article view count
        await self.db.articles.update_one(
            {"_id": ObjectId(article_id)},
            {"$inc": {"views": 1}}
        )
        
        return True
    
    async def get_user_activity_history(
        self, 
        user_id: str,
        action_types: Optional[List[ActionType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get user activity history with optional filtering"""
        query = {"user_id": ObjectId(user_id)}
        
        if action_types:
            query["action"] = {"$in": action_types}
        
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["timestamp"] = date_query
        
        cursor = self.activity_collection.find(query).sort("timestamp", -1).limit(limit)
        activities = []
        async for activity in cursor:
            activity["_id"] = str(activity["_id"])
            activity["user_id"] = str(activity["user_id"])
            if activity.get("article_id"):
                activity["article_id"] = str(activity["article_id"])
            if activity.get("category_id"):
                activity["category_id"] = str(activity["category_id"])
            if activity.get("author_id"):
                activity["author_id"] = str(activity["author_id"])
            activities.append(activity)
        
        return activities
    
    async def get_user_reading_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user reading statistics for the specified period"""
        start_date = get_current_utc_time() - timedelta(days=days)
        
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "timestamp": {"$gte": start_date},
                    "action": {"$in": [ActionType.VIEW, ActionType.READ_TIME]}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_articles_read": {
                        "$sum": {"$cond": [{"$eq": ["$action", ActionType.VIEW]}, 1, 0]}
                    },
                    "total_reading_time": {
                        "$sum": {"$cond": [
                            {"$and": [
                                {"$eq": ["$action", ActionType.READ_TIME]},
                                {"$ne": ["$reading_time", None]}
                            ]},
                            "$reading_time",
                            0
                        ]}
                    },
                    "articles_by_day": {
                        "$push": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$timestamp"
                            }
                        }
                    }
                }
            }
        ]
        
        result = await self.activity_collection.aggregate(pipeline).to_list(1)
        if not result:
            return {
                "total_articles_read": 0,
                "total_reading_time": 0,
                "average_reading_time": 0,
                "reading_days": 0,
                "reading_streak": 0
            }
        
        stats = result[0]
        
        # Calculate daily reading frequency
        reading_days = len(set(stats.get("articles_by_day", [])))
        
        # Calculate average reading time
        avg_reading_time = (
            stats["total_reading_time"] / max(stats["total_articles_read"], 1)
        )
        
        return {
            "total_articles_read": stats["total_articles_read"],
            "total_reading_time": stats["total_reading_time"],
            "average_reading_time": round(avg_reading_time, 2),
            "reading_days": reading_days,
            "reading_frequency": round(reading_days / days, 2)
        }
    
    async def create_user_preferences(
        self, 
        user_id: str, 
        preferences: UserPreferencesCreate
    ) -> str:
        """Create user preferences"""
        user_prefs = UserPreferences(
            user_id=ObjectId(user_id),
            **preferences.model_dump()
        )
        
        result = await self.preferences_collection.insert_one(
            user_prefs.model_dump(by_alias=True)
        )
        return str(result.inserted_id)
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """Get user preferences"""
        prefs = await self.preferences_collection.find_one({"user_id": ObjectId(user_id)})
        if prefs:
            prefs["_id"] = str(prefs["_id"])
            prefs["user_id"] = str(prefs["user_id"])
        return prefs
    
    async def update_user_preferences(
        self, 
        user_id: str, 
        preferences: UserPreferencesUpdate
    ) -> bool:
        """Update user preferences"""
        update_data = {k: v for k, v in preferences.model_dump().items() if v is not None}
        update_data["updated_at"] = get_current_utc_time()
        
        result = await self.preferences_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": update_data},
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None
    
    async def start_reading_session(
        self, 
        user_id: str, 
        session: ReadingSessionCreate
    ) -> str:
        """Start a new reading session"""
        session_id = str(uuid.uuid4())
        
        reading_session = ReadingSession(
            user_id=ObjectId(user_id),
            article_id=ObjectId(session.article_id),
            session_id=session_id,
            device_type=session.device_type,
            screen_size=session.screen_size
        )
        
        result = await self.sessions_collection.insert_one(
            reading_session.model_dump(by_alias=True)
        )
        return session_id
    
    async def update_reading_session(
        self, 
        session_id: str, 
        session_update: ReadingSessionUpdate
    ) -> bool:
        """Update reading session"""
        update_data = {k: v for k, v in session_update.model_dump().items() if v is not None}
        
        result = await self.sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def get_user_engagement_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user engagement metrics"""
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id)}},
            {
                "$group": {
                    "_id": "$action",
                    "count": {"$sum": 1},
                    "avg_reading_time": {
                        "$avg": {
                            "$cond": [
                                {"$ne": ["$reading_time", None]},
                                "$reading_time",
                                None
                            ]
                        }
                    },
                    "avg_scroll_percentage": {
                        "$avg": {
                            "$cond": [
                                {"$ne": ["$scroll_percentage", None]},
                                "$scroll_percentage",
                                None
                            ]
                        }
                    }
                }
            }
        ]
        
        result = await self.activity_collection.aggregate(pipeline).to_list(None)
        
        metrics = defaultdict(int)
        for item in result:
            metrics[item["_id"]] = {
                "count": item["count"],
                "avg_reading_time": item.get("avg_reading_time"),
                "avg_scroll_percentage": item.get("avg_scroll_percentage")
            }
        
        return dict(metrics)
    
    async def get_popular_content_for_user(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Get popular content based on user's activity patterns"""
        # Get user's preferred categories and tags from activity
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id), "action": ActionType.VIEW}},
            {
                "$lookup": {
                    "from": "articles",
                    "localField": "article_id",
                    "foreignField": "_id",
                    "as": "article"
                }
            },
            {"$unwind": "$article"},
            {
                "$group": {
                    "_id": None,
                    "categories": {"$addToSet": "$article.category_id"},
                    "tags": {"$addToSet": {"$arrayElemAt": ["$article.tags", 0]}}
                }
            }
        ]
        
        user_patterns = await self.activity_collection.aggregate(pipeline).to_list(1)
        
        if not user_patterns:
            return []
        
        # Find popular articles in user's preferred categories
        categories = user_patterns[0].get("categories", [])
        
        popular_pipeline = [
            {
                "$match": {
                    "category_id": {"$in": categories},
                    "status": "published"
                }
            },
            {
                "$addFields": {
                    "engagement_score": {
                        "$add": [
                            {"$multiply": ["$views", 1]},
                            {"$multiply": ["$likes", 2]},
                            {"$multiply": [{"$size": "$bookmarked_by"}, 3]}
                        ]
                    }
                }
            },
            {"$sort": {"engagement_score": -1}},
            {"$limit": limit}
        ]
        
        popular_articles = await self.db.articles.aggregate(popular_pipeline).to_list(limit)
        
        for article in popular_articles:
            article["_id"] = str(article["_id"])
            article["category_id"] = str(article["category_id"])
            article["author_id"] = str(article["author_id"])
            article["bookmarked_by"] = [str(bid) for bid in article.get("bookmarked_by", [])]
        
        return popular_articles
    
    async def update_subscription_tier(self, user_id: str, tier: SubscriptionTier) -> bool:
        """Update user subscription tier in preferences"""
        result = await self.preferences_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$set": {
                    "subscription_tier": tier,
                    "updated_at": get_current_utc_time()
                }
            },
            upsert=True
        )
        return result.modified_count > 0 or result.upserted_id is not None