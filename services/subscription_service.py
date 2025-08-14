from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.enums import SubscriptionTier, ContentAccess
from utils.time import get_current_utc_time

class SubscriptionService:
    """Service for managing subscription-based content access and flagging"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.articles_collection = db.articles
        self.users_collection = db.users
        self.subscription_content_collection = db.subscription_content
        
        # Content access rules
        self.access_rules = {
            SubscriptionTier.FREE: {
                'daily_article_limit': 10,
                'monthly_article_limit': 200,
                'premium_content_access': False,
                'enterprise_content_access': False,
                'quality_threshold': 0,  # Can access all quality levels
                'categories_limit': None,  # No category restrictions
                'reading_time_limit': None  # No reading time limits
            },
            SubscriptionTier.PREMIUM: {
                'daily_article_limit': 50,
                'monthly_article_limit': 1000,
                'premium_content_access': True,
                'enterprise_content_access': False,
                'quality_threshold': 0,
                'categories_limit': None,
                'reading_time_limit': None
            },
            SubscriptionTier.ENTERPRISE: {
                'daily_article_limit': None,  # Unlimited
                'monthly_article_limit': None,  # Unlimited
                'premium_content_access': True,
                'enterprise_content_access': True,
                'quality_threshold': 0,
                'categories_limit': None,
                'reading_time_limit': None
            }
        }
    
    async def flag_article_for_subscription(
        self, 
        article_id: str, 
        content_access: ContentAccess,
        premium_features: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Flag an article with subscription requirements"""
        try:
            # Update article with subscription flags
            update_data = {
                'content_access': content_access,
                'subscription_flagged_at': get_current_utc_time(),
                'premium_features': premium_features or {}
            }
            
            # Set subscription-specific flags
            if content_access == ContentAccess.PREMIUM:
                update_data['is_premium_content'] = True
                update_data['is_enterprise_content'] = False
            elif content_access == ContentAccess.ENTERPRISE:
                update_data['is_premium_content'] = True
                update_data['is_enterprise_content'] = True
            else:
                update_data['is_premium_content'] = False
                update_data['is_enterprise_content'] = False
            
            result = await self.articles_collection.update_one(
                {"_id": ObjectId(article_id)},
                {"$set": update_data}
            )
            
            # Create subscription content record for detailed tracking
            subscription_record = {
                'article_id': ObjectId(article_id),
                'content_access': content_access,
                'premium_features': premium_features or {},
                'created_at': get_current_utc_time(),
                'updated_at': get_current_utc_time(),
                'access_count': 0,
                'revenue_generated': 0.0
            }
            
            await self.subscription_content_collection.update_one(
                {"article_id": ObjectId(article_id)},
                {"$set": subscription_record},
                upsert=True
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"Error flagging article {article_id} for subscription: {e}")
            raise
    
    async def check_content_access(
        self, 
        user_id: str, 
        article_id: str
    ) -> Dict[str, Any]:
        """Check if user can access specific content"""
        try:
            # Get user subscription tier
            user = await self.users_collection.find_one(
                {"_id": ObjectId(user_id)},
                projection={"subscription_tier": 1}
            )
            
            user_tier = SubscriptionTier(user.get('subscription_tier', SubscriptionTier.FREE)) if user else SubscriptionTier.FREE
            
            # Get article access requirements
            article = await self.articles_collection.find_one(
                {"_id": ObjectId(article_id)},
                projection={
                    "content_access": 1,
                    "is_premium_content": 1,
                    "is_enterprise_content": 1,
                    "quality_score": 1
                }
            )
            
            if not article:
                return {
                    "can_access": False,
                    "reason": "Article not found",
                    "access_type": "denied"
                }
            
            # Check basic access rules
            content_access = article.get('content_access', ContentAccess.FREE)
            is_premium = article.get('is_premium_content', False)
            is_enterprise = article.get('is_enterprise_content', False)
            
            # Determine access
            can_access = True
            access_type = "full"
            reason = None
            
            # Check subscription tier requirements
            if is_enterprise and user_tier != SubscriptionTier.ENTERPRISE:
                can_access = False
                reason = "Enterprise subscription required"
                access_type = "upgrade_required"
            elif is_premium and user_tier == SubscriptionTier.FREE:
                can_access = False
                reason = "Premium subscription required"
                access_type = "upgrade_required"
            
            # Check daily/monthly limits for free users
            if user_tier == SubscriptionTier.FREE and can_access:
                limits_check = await self._check_usage_limits(user_id, user_tier)
                if not limits_check["within_limits"]:
                    can_access = False
                    reason = limits_check["reason"]
                    access_type = "limit_exceeded"
            
            # Prepare response
            response = {
                "can_access": can_access,
                "access_type": access_type,
                "user_tier": user_tier,
                "content_access": content_access,
                "is_premium": is_premium,
                "is_enterprise": is_enterprise
            }
            
            if reason:
                response["reason"] = reason
            
            if not can_access:
                response["upgrade_suggestions"] = self._get_upgrade_suggestions(user_tier, content_access)
            
            return response
            
        except Exception as e:
            print(f"Error checking content access for user {user_id}, article {article_id}: {e}")
            raise
    
    async def _check_usage_limits(self, user_id: str, user_tier: SubscriptionTier) -> Dict[str, Any]:
        """Check if user is within usage limits"""
        try:
            rules = self.access_rules[user_tier]
            
            # Check daily limit
            if rules['daily_article_limit'] is not None:
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                daily_views = await self.db.user_activities.count_documents({
                    "user_id": ObjectId(user_id),
                    "action": "view",
                    "timestamp": {"$gte": today_start}
                })
                
                if daily_views >= rules['daily_article_limit']:
                    return {
                        "within_limits": False,
                        "reason": f"Daily limit of {rules['daily_article_limit']} articles exceeded",
                        "limit_type": "daily"
                    }
            
            # Check monthly limit
            if rules['monthly_article_limit'] is not None:
                month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                monthly_views = await self.db.user_activities.count_documents({
                    "user_id": ObjectId(user_id),
                    "action": "view",
                    "timestamp": {"$gte": month_start}
                })
                
                if monthly_views >= rules['monthly_article_limit']:
                    return {
                        "within_limits": False,
                        "reason": f"Monthly limit of {rules['monthly_article_limit']} articles exceeded",
                        "limit_type": "monthly"
                    }
            
            return {"within_limits": True}
            
        except Exception as e:
            print(f"Error checking usage limits for user {user_id}: {e}")
            return {"within_limits": True}  # Default to allowing access on error
    
    def _get_upgrade_suggestions(self, user_tier: SubscriptionTier, content_access: ContentAccess) -> Dict[str, Any]:
        """Get upgrade suggestions based on user tier and content requirements"""
        suggestions = {
            "current_tier": user_tier,
            "required_for_content": content_access,
            "available_upgrades": []
        }
        
        if user_tier == SubscriptionTier.FREE:
            suggestions["available_upgrades"].extend([
                {
                    "tier": SubscriptionTier.PREMIUM,
                    "benefits": [
                        "Access to premium content",
                        "50 articles per day",
                        "1000 articles per month",
                        "No ads",
                        "Priority support"
                    ]
                },
                {
                    "tier": SubscriptionTier.ENTERPRISE,
                    "benefits": [
                        "Unlimited article access",
                        "Enterprise exclusive content",
                        "Advanced analytics",
                        "Team collaboration features",
                        "Custom integrations"
                    ]
                }
            ])
        
        elif user_tier == SubscriptionTier.PREMIUM:
            if content_access == ContentAccess.ENTERPRISE:
                suggestions["available_upgrades"].append({
                    "tier": SubscriptionTier.ENTERPRISE,
                    "benefits": [
                        "Enterprise exclusive content",
                        "Unlimited access",
                        "Advanced analytics",
                        "Team features"
                    ]
                })
        
        return suggestions
    
    async def track_content_access(self, user_id: str, article_id: str, access_granted: bool):
        """Track content access for analytics"""
        try:
            # Update subscription content stats
            if access_granted:
                await self.subscription_content_collection.update_one(
                    {"article_id": ObjectId(article_id)},
                    {
                        "$inc": {"access_count": 1},
                        "$set": {"last_accessed": get_current_utc_time()}
                    }
                )
        except Exception as e:
            print(f"Error tracking content access: {e}")
    
    async def get_premium_content_suggestions(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get premium content suggestions to encourage upgrades"""
        try:
            # Get user's reading preferences
            user_activities = await self.db.user_activities.find({
                "user_id": ObjectId(user_id),
                "action": "view"
            }).sort("timestamp", -1).limit(50).to_list(50)
            
            # Extract preferred categories
            preferred_categories = []
            for activity in user_activities:
                if activity.get("article_id"):
                    article = await self.articles_collection.find_one(
                        {"_id": activity["article_id"]},
                        projection={"category_id": 1}
                    )
                    if article and article.get("category_id"):
                        preferred_categories.append(article["category_id"])
            
            # Get premium content in preferred categories
            query = {
                "is_premium_content": True,
                "status": "published"
            }
            
            if preferred_categories:
                query["category_id"] = {"$in": list(set(preferred_categories[-10:]))}  # Last 10 unique categories
            
            premium_articles = await self.articles_collection.find(query).sort("quality_score", -1).limit(limit).to_list(limit)
            
            # Format response
            suggestions = []
            for article in premium_articles:
                suggestions.append({
                    "id": str(article["_id"]),
                    "title": article["name"],
                    "excerpt": article.get("excerpt", ""),
                    "quality_score": article.get("quality_score", 0),
                    "is_premium": article.get("is_premium_content", False),
                    "is_enterprise": article.get("is_enterprise_content", False),
                    "content_access": article.get("content_access", "premium"),
                    "preview_available": True
                })
            
            return suggestions
            
        except Exception as e:
            print(f"Error getting premium content suggestions: {e}")
            return []
    
    async def batch_flag_articles_by_criteria(
        self, 
        criteria: Dict[str, Any],
        content_access: ContentAccess
    ) -> Dict[str, Any]:
        """Batch flag articles based on criteria"""
        try:
            # Build query from criteria
            query = {"status": "published"}
            
            if criteria.get("quality_score_min"):
                query["quality_score"] = {"$gte": criteria["quality_score_min"]}
            
            if criteria.get("category_ids"):
                query["category_id"] = {"$in": [ObjectId(cid) for cid in criteria["category_ids"]]}
            
            if criteria.get("author_ids"):
                query["author_id"] = {"$in": [ObjectId(aid) for aid in criteria["author_ids"]]}
            
            if criteria.get("created_after"):
                query["created_at"] = {"$gte": criteria["created_after"]}
            
            # Find matching articles
            articles = await self.articles_collection.find(query, projection={"_id": 1}).to_list(None)
            
            # Flag articles
            results = {
                "processed": 0,
                "errors": 0,
                "article_ids": []
            }
            
            for article in articles:
                try:
                    article_id = str(article["_id"])
                    success = await self.flag_article_for_subscription(
                        article_id=article_id,
                        content_access=content_access
                    )
                    
                    if success:
                        results["processed"] += 1
                        results["article_ids"].append(article_id)
                    else:
                        results["errors"] += 1
                        
                except Exception as e:
                    print(f"Error flagging article {article['_id']}: {e}")
                    results["errors"] += 1
            
            return results
            
        except Exception as e:
            print(f"Error in batch flagging: {e}")
            raise
    
    async def get_subscription_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get subscription-related analytics"""
        try:
            start_date = get_current_utc_time() - timedelta(days=days)
            
            # Content access analytics
            access_pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$content_access",
                        "total_articles": {"$sum": 1},
                        "total_access_count": {"$sum": "$access_count"},
                        "avg_access_count": {"$avg": "$access_count"}
                    }
                }
            ]
            
            access_stats = await self.subscription_content_collection.aggregate(access_pipeline).to_list(None)
            
            # User tier distribution
            user_pipeline = [
                {
                    "$group": {
                        "_id": "$subscription_tier",
                        "user_count": {"$sum": 1}
                    }
                }
            ]
            
            user_stats = await self.users_collection.aggregate(user_pipeline).to_list(None)
            
            return {
                "period_days": days,
                "content_access_stats": access_stats,
                "user_tier_distribution": user_stats,
                "generated_at": get_current_utc_time()
            }
            
        except Exception as e:
            print(f"Error getting subscription analytics: {e}")
            raise