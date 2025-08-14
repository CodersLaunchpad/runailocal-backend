#!/usr/bin/env python3
"""
Setup script for Phase 1 of the Recommendation System
This script integrates all the new behavior tracking and content analysis components.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def setup_phase1():
    """Setup Phase 1 components"""
    print("[PHASE 1] Setting up Phase 1: Foundation Enhancement")
    print("=" * 50)
    
    try:
        # Import required modules
        from dependencies.db import get_db
        from services.behavior_service import BehaviorService
        from services.content_quality_service import ContentQualityService
        from services.subscription_service import SubscriptionService
        from utils.content_preprocessing import ContentPreprocessor
        
        # Get database connection
        print("[DB] Connecting to database...")
        db = await get_db()
        
        # Initialize services
        print("[SETUP] Initializing services...")
        behavior_service = BehaviorService(db)
        quality_service = ContentQualityService(db)
        subscription_service = SubscriptionService(db)
        preprocessor = ContentPreprocessor()
        
        # Create database indexes for performance
        print("[INDEX] Creating database indexes...")
        await create_indexes(db)
        
        # Process existing articles for quality scores
        print("[PROCESS] Processing existing articles...")
        await process_existing_articles(quality_service, limit=50)
        
        # Create sample user preferences for testing
        print("[USER] Setting up sample user preferences...")
        await setup_sample_preferences(behavior_service)
        
        print("\n[OK] Phase 1 setup completed successfully!")
        print("\n[SUMMARY] Summary of what was set up:")
        print("   • User behavior tracking models and services")
        print("   • Content quality scoring system")
        print("   • Subscription-based content flagging")
        print("   • Content preprocessing utilities")
        print("   • Database indexes for performance")
        print("   • API endpoints for all new features")
        
        print("\n[NEXT] Next steps:")
        print("   1. Add the new routes to your main FastAPI app:")
        print("      - Include behavior_routes")
        print("      - Include content_quality_routes")
        print("   2. Add the middleware to your app:")
        print("      - BehaviorTrackingMiddleware")
        print("   3. Test the new endpoints with your frontend")
        print("   4. Start collecting user behavior data")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Error during setup: {e}")
        import traceback
        traceback.print_exc()
        return False

async def create_indexes(db):
    """Create database indexes for optimal performance"""
    try:
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
        
        # Enhanced article indexes
        await db.articles.create_index([("quality_score", -1)])
        await db.articles.create_index([("is_premium_content", 1)])
        await db.articles.create_index([("content_access", 1)])
        
        # Enhanced user indexes  
        await db.users.create_index([("subscription_tier", 1)])
        
        print("   [OK] Database indexes created successfully")
        
    except Exception as e:
        print(f"   [WARN]  Warning: Could not create all indexes: {e}")

async def process_existing_articles(quality_service, limit=50):
    """Process existing articles for quality scores"""
    try:
        print(f"   📝 Processing up to {limit} articles for quality scoring...")
        
        # This will process articles in the background
        result = await quality_service.batch_calculate_quality_scores(limit=limit)
        
        print(f"   [OK] Processed {result.get('processed', 0)} articles")
        if result.get('errors', 0) > 0:
            print(f"   [WARN]  {result['errors']} articles had errors during processing")
            
    except Exception as e:
        print(f"   [WARN]  Warning: Could not process articles: {e}")

async def setup_sample_preferences(behavior_service):
    """Set up sample user preferences for testing"""
    try:
        from models.behavior_models import UserPreferencesCreate, ReadingFrequency, ContentLength, SubscriptionTier
        
        # This is just a placeholder - in real usage, preferences will be created when users interact with the system
        print("   [USER] Sample user preferences structure ready")
        print("   [INFO]  User preferences will be created automatically when users interact with the system")
        
    except Exception as e:
        print(f"   [WARN]  Warning: Could not set up sample preferences: {e}")

def print_integration_instructions():
    """Print instructions for integrating with the main app"""
    print("\n[SETUP] Integration Instructions:")
    print("=" * 30)
    
    print("""
1. Update your main FastAPI app (app.py or main.py):

```python
from middleware.behavior_middleware import BehaviorTrackingMiddleware
from routes import behavior_routes, content_quality_routes

# Add middleware
app.add_middleware(BehaviorTrackingMiddleware, track_anonymous=False)

# Include new routes
app.include_router(behavior_routes.router, prefix="/api")
app.include_router(content_quality_routes.router, prefix="/api")
```

2. Update user registration to include subscription tier:

```python
# In your user creation endpoint
user_data = UserCreate(
    # ... existing fields ...
    subscription_tier=SubscriptionTier.FREE  # Default for new users
)
```

3. Test the new endpoints:
   - GET /api/behavior/preferences
   - POST /api/behavior/track
   - GET /api/content/quality/insights
   - POST /api/content/subscription/flag/{article_id}

4. Frontend Integration:
   - Add scroll tracking for reading behavior
   - Implement subscription upgrade prompts
   - Show content quality indicators
   - Track user preferences
""")

if __name__ == "__main__":
    print("Starting Phase 1 setup...")
    success = asyncio.run(setup_phase1())
    
    if success:
        print_integration_instructions()
        print("\n[SUCCESS] Phase 1 setup completed successfully!")
        print("   You can now start Phase 2: ChromaDB Integration")
    else:
        print("\n[FAIL] Setup failed. Please check the errors above.")
        sys.exit(1)