from typing import Dict, Any, List
from datetime import datetime, timezone

from bson import ObjectId
from pydantic import BaseModel

from db.schemas.users_schema import UserInDB
from models.models import ensure_object_id
from models.notifications_model import NotificationType, NotificationCreate, NotificationResponse
from repos.notification_repo import NotificationRepository
from repos.user_repo import UserInDB


class NotificationService:
    """
    Service layer for notification-related operations
    Handles business logic between controllers and data access
    """
    
    def __init__(self, notification_repository: NotificationRepository, user_repository: UserInDB):
        self.notification_repo = notification_repository
        self.user_repo = user_repository  # Add this

    async def create_notification(self, notification: NotificationCreate) -> NotificationResponse:
        """Create a new notification"""
        try:
            # Prepare notification data
            notification_data = {
                "recipient_id": ObjectId(notification.recipient_id),
                "sender_id": ObjectId(notification.sender_id),
                "sender_username" : notification.sender_username,
                "notification_type": notification.notification_type,
                "source_id": ObjectId(notification.source_id),
                "message": notification.message,
                "created_at": datetime.now(timezone.utc),
                "is_read": False
            }

            # Call repository to save notification
            notification_db = await self.notification_repo.create_notification(notification_data)
            
            # Convert to API response model
            return self._notification_db_to_response(notification_db)
        except Exception as e:
            raise Exception(f"Error creating notification: {str(e)}")
    
    async def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[NotificationResponse]:
        """Get all notifications for a user"""
        try:
            notifications_db = await self.notification_repo.get_user_notifications(user_id, unread_only)
            return [self._notification_db_to_response(notification) for notification in notifications_db]
        except Exception as e:
            raise Exception(f"Error getting notifications: {str(e)}")
    
    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> NotificationResponse:
        """Mark a notification as read and return it"""
        try:
            notification_db = await self.notification_repo.mark_notification_as_read(notification_id, user_id)
            if not notification_db:
                raise ValueError("Notification not found or already read")
            
            return self._notification_db_to_response(notification_db)
        except Exception as e:
            raise Exception(f"Error marking notification as read: {str(e)}")
    
    async def mark_all_notifications_as_read(self, user_id: str) -> bool:
        """Mark all notifications for a user as read"""
        try:
            success = await self.notification_repo.mark_all_notifications_as_read(user_id)
            if not success:
                raise ValueError("Failed to mark notifications as read")
            return True
        except Exception as e:
            raise Exception(f"Error marking notifications as read: {str(e)}")
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        try:
            success = await self.notification_repo.delete_notification(notification_id, user_id)
            if not success:
                raise ValueError("Notification not found or not deleted")
            return True
        except Exception as e:
            raise Exception(f"Error deleting notification: {str(e)}")
    
    async def create_article_post_notification(self, article_id: str, commenter_id: str, article_owner_id: str) -> NotificationResponse:
        """Create a notification when someone posts on your article"""
        try:
            # In a real implementation, you would fetch user details here
            # For simplicity, we'll just create a generic message
            commenter = await self.user_repo.get_user_by_id(commenter_id)
            message = f"{commenter_id.username} commented on your article"
            
            notification = NotificationCreate(
                recipient_id=article_owner_id,
                sender_id=commenter_id,
                notification_type=NotificationType.ARTICLE_POST,
                source_id=article_id,
                message=message
            )
            
            return await self.create_notification(notification)
        except Exception as e:
            raise Exception(f"Error creating article post notification: {str(e)}")
    
    async def create_follow_notification(self, follower_id: str, followed_id: str) -> NotificationResponse:
        """Create a notification when someone follows you"""
        try:
            # Get follower details
            follower = await self.user_repo.get_user_by_id(follower_id)
            if not follower:
                raise ValueError("Follower not found")
            
            notification = NotificationCreate(
                recipient_id=followed_id,
                sender_id=follower_id,
                sender_username=follower.username,  # Use actual username
                notification_type=NotificationType.FOLLOW,
                source_id=follower_id,
                message=f"{follower.username} started following you"  # More descriptive
            )
            
            return await self.create_notification(notification)
        except Exception as e:
            raise Exception(f"Error creating follow notification: {str(e)}")

    
    def _notification_db_to_response(self, notification_db: Dict[str, Any]) -> NotificationResponse:
        """Convert a notification DB model to a response model"""
        notification_db["id"] = str(notification_db["_id"])
        notification_db["recipient_id"] = str(notification_db["recipient_id"])
        notification_db["sender_id"] = str(notification_db["sender_id"])
        notification_db["source_id"] = str(notification_db["source_id"])
        
        return NotificationResponse(**notification_db)