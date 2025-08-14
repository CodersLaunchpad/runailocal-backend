#!/usr/bin/env python3
"""
Test script for Phase 1 implementation
Validates all components work together without actual database operations
"""

def test_imports():
    """Test all imports work correctly"""
    print("Testing Phase 1 imports...")
    
    try:
        # Test enum imports
        from models.enums import ActionType, SubscriptionTier, ContentAccess, ReadingFrequency, ContentLength
        print("[PASS] Enums imported successfully")
        
        # Test model imports
        from models.behavior_models import (
            UserActivityLog, UserActivityCreate, 
            UserPreferences, UserPreferencesCreate,
            ReadingSession, ReadingSessionCreate
        )
        print("[PASS] Behavior models imported successfully")
        
        # Test service imports  
        from services.behavior_service import BehaviorService
        from services.content_quality_service import ContentQualityService
        from services.subscription_service import SubscriptionService
        print("[PASS] Services imported successfully")
        
        # Test utility imports
        from utils.content_preprocessing import ContentPreprocessor
        print("[PASS] Utilities imported successfully")
        
        # Test middleware imports
        from middleware.behavior_middleware import BehaviorTrackingMiddleware, ReadingSessionMiddleware
        print("[PASS] Middleware imported successfully")
        
        # Test route imports
        from routes.behavior_routes import router as behavior_router
        from routes.content_quality_routes import router as content_router
        print("[PASS] Routes imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] Unexpected error: {e}")
        return False

def test_model_creation():
    """Test model creation without database operations"""
    print("\nTesting Testing model creation...")
    
    try:
        from models.behavior_models import UserActivityCreate, UserPreferencesCreate
        from models.enums import ActionType, SubscriptionTier, ReadingFrequency
        
        # Test activity creation
        activity = UserActivityCreate(
            action=ActionType.VIEW,
            article_id="507f1f77bcf86cd799439011",
            reading_time=120,
            scroll_percentage=0.8,
            device_type="desktop"
        )
        print("[PASS] UserActivityCreate model works")
        
        # Test preferences creation
        preferences = UserPreferencesCreate(
            preferred_categories=["AI", "ML"],
            reading_frequency=ReadingFrequency.WEEKLY,
            subscription_tier=SubscriptionTier.FREE
        )
        print("[PASS] UserPreferencesCreate model works")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Model creation error: {e}")
        return False

def test_content_preprocessing():
    """Test content preprocessing utilities"""
    print("\nTesting Testing content preprocessing...")
    
    try:
        from utils.content_preprocessing import ContentPreprocessor
        
        processor = ContentPreprocessor()
        
        # Test HTML cleaning
        html_content = "<p>This is <b>test content</b> with <a href='#'>links</a></p>"
        clean_text = processor.clean_html(html_content)
        assert "test content" in clean_text
        assert "<" not in clean_text
        print("[PASS] HTML cleaning works")
        
        # Test feature extraction
        content = "This is a sample article with multiple sentences. It contains various words and punctuation."
        features = processor.extract_text_features(content)
        assert features['word_count'] > 0
        assert features['sentence_count'] > 0
        print("[PASS] Feature extraction works")
        
        # Test keyword extraction
        keywords = processor.extract_keywords(content, max_keywords=5)
        assert isinstance(keywords, list)
        print("[PASS] Keyword extraction works")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Content preprocessing error: {e}")
        return False

def test_enum_values():
    """Test enum values are correct"""
    print("\nTesting Testing enum values...")
    
    try:
        from models.enums import ActionType, SubscriptionTier, ContentAccess
        
        # Test ActionType
        assert ActionType.VIEW == "view"
        assert ActionType.LIKE == "like"
        assert ActionType.BOOKMARK == "bookmark"
        print("[PASS] ActionType enum values correct")
        
        # Test SubscriptionTier
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.PREMIUM == "premium"
        assert SubscriptionTier.ENTERPRISE == "enterprise"
        print("[PASS] SubscriptionTier enum values correct")
        
        # Test ContentAccess
        assert ContentAccess.FREE == "free"
        assert ContentAccess.PREMIUM == "premium"
        print("[PASS] ContentAccess enum values correct")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Enum test error: {e}")
        return False

def test_route_configuration():
    """Test route configuration"""
    print("\nTesting Testing route configuration...")
    
    try:
        from routes.behavior_routes import router as behavior_router
        from routes.content_quality_routes import router as content_router
        
        # Check route prefixes
        assert behavior_router.prefix == "/behavior"
        assert content_router.prefix == "/content"
        print("[PASS] Route prefixes correct")
        
        # Check route tags
        assert "behavior" in behavior_router.tags
        assert "content-quality" in content_router.tags
        print("[PASS] Route tags correct")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Route configuration error: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("[PHASE 1] Phase 1 Integration Test Suite")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_model_creation, 
        test_content_preprocessing,
        test_enum_values,
        test_route_configuration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            break  # Stop on first failure
    
    print(f"\n[RESULTS] Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed! Phase 1 implementation is ready.")
        print("\n[OK] Ready for integration:")
        print("   • All imports working correctly")
        print("   • Models can be created successfully")  
        print("   • Content preprocessing functional")
        print("   • Routes configured properly")
        print("   • Enums have correct values")
        
        print("\n[NEXT] Next steps:")
        print("   1. Run: python setup_phase1_integration.py")
        print("   2. Add routes to your main FastAPI app")
        print("   3. Add middleware to your app")
        print("   4. Test with real data")
        
        return True
    else:
        print("[FAIL] Some tests failed. Please fix issues before proceeding.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    if not success:
        exit(1)