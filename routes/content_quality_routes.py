from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
from services.content_quality_service import ContentQualityService
from services.subscription_service import SubscriptionService
from models.enums import ContentAccess
from dependencies.db import get_db
from dependencies.auth import get_current_user, get_admin_user
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(prefix="/content", tags=["content-quality"])

async def get_content_quality_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> ContentQualityService:
    """Dependency to get content quality service"""
    return ContentQualityService(db)

async def get_subscription_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> SubscriptionService:
    """Dependency to get subscription service"""
    return SubscriptionService(db)

@router.post("/quality/calculate/{article_id}")
async def calculate_article_quality(
    article_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_user),
    quality_service: ContentQualityService = Depends(get_content_quality_service)
):
    """Calculate quality score for a specific article"""
    try:
        # Run in background to avoid blocking
        background_tasks.add_task(quality_service.calculate_article_quality_score, article_id)
        
        return {
            "message": "Quality calculation started",
            "article_id": article_id,
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate quality: {str(e)}")

@router.post("/quality/batch-calculate")
async def batch_calculate_quality(
    article_ids: Optional[List[str]] = None,
    limit: int = 100,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_admin_user),
    quality_service: ContentQualityService = Depends(get_content_quality_service)
):
    """Batch calculate quality scores for multiple articles"""
    try:
        # Run in background for large batches
        background_tasks.add_task(
            quality_service.batch_calculate_quality_scores,
            article_ids,
            limit
        )
        
        return {
            "message": "Batch quality calculation started",
            "article_count": len(article_ids) if article_ids else f"up to {limit}",
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start batch calculation: {str(e)}")

@router.get("/quality/insights")
async def get_quality_insights(
    days: int = 30,
    current_user: dict = Depends(get_admin_user),
    quality_service: ContentQualityService = Depends(get_content_quality_service)
):
    """Get content quality insights and analytics"""
    try:
        insights = await quality_service.get_quality_insights(days=days)
        return {
            "insights": insights,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")

@router.get("/quality/{article_id}")
async def get_article_quality_details(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    quality_service: ContentQualityService = Depends(get_content_quality_service)
):
    """Get detailed quality information for an article"""
    try:
        details = await quality_service.get_article_quality_details(article_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Quality details not found")
        
        return {
            "quality_details": details,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quality details: {str(e)}")

# Subscription-based content routes

@router.post("/subscription/flag/{article_id}")
async def flag_article_for_subscription(
    article_id: str,
    content_access: ContentAccess,
    premium_features: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_admin_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Flag an article with subscription requirements"""
    try:
        success = await subscription_service.flag_article_for_subscription(
            article_id=article_id,
            content_access=content_access,
            premium_features=premium_features
        )
        
        return {
            "message": f"Article flagged as {content_access} content",
            "article_id": article_id,
            "success": success
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to flag article: {str(e)}")

@router.get("/subscription/access/{article_id}")
async def check_content_access(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Check if current user can access specific content"""
    try:
        access_info = await subscription_service.check_content_access(
            user_id=str(current_user.id),
            article_id=article_id
        )
        
        # Track the access check
        await subscription_service.track_content_access(
            user_id=str(current_user.id),
            article_id=article_id,
            access_granted=access_info["can_access"]
        )
        
        return {
            "access_info": access_info,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check access: {str(e)}")

@router.get("/subscription/premium-suggestions")
async def get_premium_content_suggestions(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get premium content suggestions for user"""
    try:
        suggestions = await subscription_service.get_premium_content_suggestions(
            user_id=str(current_user.id),
            limit=limit
        )
        
        return {
            "suggestions": suggestions,
            "total": len(suggestions),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")

@router.post("/subscription/batch-flag")
async def batch_flag_articles(
    criteria: Dict[str, Any],
    content_access: ContentAccess,
    current_user: dict = Depends(get_admin_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Batch flag articles based on criteria"""
    try:
        results = await subscription_service.batch_flag_articles_by_criteria(
            criteria=criteria,
            content_access=content_access
        )
        
        return {
            "message": f"Batch flagging completed",
            "results": results,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch flag: {str(e)}")

@router.get("/subscription/analytics")
async def get_subscription_analytics(
    days: int = 30,
    current_user: dict = Depends(get_admin_user),
    subscription_service: SubscriptionService = Depends(get_subscription_service)
):
    """Get subscription-related analytics"""
    try:
        analytics = await subscription_service.get_subscription_analytics(days=days)
        
        return {
            "analytics": analytics,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

# Content preprocessing endpoints

@router.post("/preprocess/{article_id}")
async def preprocess_article_content(
    article_id: str,
    current_user: dict = Depends(get_admin_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Preprocess article content and extract features"""
    try:
        from utils.content_preprocessing import ContentPreprocessor
        from bson import ObjectId
        
        processor = ContentPreprocessor()
        
        # Get article
        article = await db.articles.find_one({"_id": ObjectId(article_id)})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Process content
        quality_features = processor.extract_content_quality_features(article)
        embedding_text = processor.preprocess_for_embedding(
            title=article.get('name', ''),
            content=article.get('content', ''),
            tags=article.get('tags', [])
        )
        keywords = processor.extract_keywords(article.get('content', ''))
        
        # Update article with processed data
        await db.articles.update_one(
            {"_id": ObjectId(article_id)},
            {"$set": {
                "content_features": quality_features,
                "embedding_text": embedding_text,
                "keywords": keywords,
                "processed_at": datetime.utcnow()
            }}
        )
        
        return {
            "message": "Article preprocessed successfully",
            "article_id": article_id,
            "content_features": quality_features,
            "keyword_count": len(keywords),
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preprocess: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for content services"""
    return {
        "status": "healthy",
        "services": [
            "content_quality_service",
            "subscription_service",
            "content_preprocessing"
        ],
        "timestamp": datetime.utcnow()
    }