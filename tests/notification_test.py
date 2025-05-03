import pytest
from models.notifications_model import NotificationCreate, NotificationResponse, NotificationType
from datetime import datetime

def test_notification_models():
    # Test model creation
    notification = NotificationCreate(
        recipient_id="67dfef1ceca125f9a0b71237", # User's ID
        sender_id="67dfef1ceca125f9a0b7123a", # Author's ID
        sender_username="test_user",
        notification_type=NotificationType.ARTICLE_POST,
        source_id="67dfef1ceca125f9a0b71240", # ARticle ID
        message="Test message"
    )
    print("This has worked")
    assert notification.notification_type == "article_post"
    
    # Test response model
    response = NotificationResponse(
        id="1",
        recipient_id="507f1f77bcf86cd799439011",
        sender_id="607f1f77bcf86cd799439022",
        sender_username="test_user",
        notification_type=NotificationType.FOLLOW,
        source_id="707f1f77bcf86cd799439033",
        message="Test message",
        is_read=False,
        created_at=datetime.utcnow(),
        read_at=None
    )
    
    assert response.notification_type == "follow"