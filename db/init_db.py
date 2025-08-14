from pymongo import ASCENDING, TEXT

async def init_db_indexes(db):
    """
    Initialize database with required indexes and configurations
    """
    # Create text index for article search
    await db.articles.create_index([
        ("title", TEXT),
        ("content", TEXT),
        ("tags", TEXT)
    ])
    
    # Create other indexes if needed
    await db.articles.create_index([("created_at", ASCENDING)])
    await db.articles.create_index([("category_id", ASCENDING)])
    await db.articles.create_index([("author_id", ASCENDING)])
    await db.articles.create_index([("status", ASCENDING)])
    
    # Phase 1: Behavior Tracking Indexes
    # User activities indexes
    await db.user_activities.create_index([("user_id", 1), ("timestamp", -1)])
    await db.user_activities.create_index([("action", 1), ("timestamp", -1)])
    await db.user_activities.create_index([("article_id", 1), ("action", 1)])
    await db.user_activities.create_index([("session_id", 1)])
    
    # User preferences indexes
    await db.user_preferences.create_index([("user_id", 1)], unique=True)
    await db.user_preferences.create_index([("subscription_tier", 1)])
    
    # Reading sessions indexes
    await db.reading_sessions.create_index([("user_id", 1), ("start_time", -1)])
    await db.reading_sessions.create_index([("article_id", 1)])
    await db.reading_sessions.create_index([("session_id", 1)], unique=True)
    
    # Quality scores indexes
    await db.article_quality_scores.create_index([("article_id", 1)], unique=True)
    await db.article_quality_scores.create_index([("overall_score", -1)])
    await db.article_quality_scores.create_index([("calculated_at", -1)])
    
    # Subscription content indexes
    await db.subscription_content.create_index([("article_id", 1)], unique=True)
    await db.subscription_content.create_index([("content_access", 1)])
    
    # Enhanced article indexes for Phase 1
    await db.articles.create_index([("quality_score", -1)])
    await db.articles.create_index([("is_premium_content", 1)])
    await db.articles.create_index([("content_access", 1)])
    
    # Enhanced user indexes  
    await db.users.create_index([("subscription_tier", 1)]) 