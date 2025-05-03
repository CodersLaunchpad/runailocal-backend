from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from bson import ObjectId

class NotificationRepository:
    """
    Repository for notification-related database operations
    Handles all direct interactions with the database for notifications
    """
    
    def __init__(self, db):
        self.db = db
    
    async def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new notification
        Returns the created notification data
        """
        try:
            # Insert the notification
            result = await self.db.notifications.insert_one(notification_data)
            
            # Get the created notification
            created_notification = await self.db.notifications.find_one({"_id": result.inserted_id})
            
            if created_notification:
                # Convert ObjectId to string for the response
                created_notification["_id"] = str(created_notification["_id"])
                created_notification["id"] = created_notification["_id"]
            
            return created_notification
        except Exception as e:
            raise Exception(f"Error creating notification: {str(e)}")
    
    async def get_user_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all notifications for a user
        If unread_only is True, returns only unread notifications
        """
        try:
            query = {"recipient_id": ObjectId(user_id)}
            
            if unread_only:
                query["is_read"] = False
            
            cursor = self.db.notifications.find(query).sort("created_at", -1)  # Newest first
            
            notifications = await cursor.to_list(length=100)  # Limit to 100 notifications
            
            # Convert ObjectIds to strings
            for notification in notifications:
                notification["_id"] = str(notification["_id"])
                notification["id"] = notification["_id"]
                notification["recipient_id"] = str(notification["recipient_id"])
                notification["sender_id"] = str(notification["sender_id"])
                notification["source_id"] = str(notification["source_id"])
            
            return notifications
        except Exception as e:
            raise Exception(f"Error getting user notifications: {str(e)}")
    
    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Mark a specific notification as read
        Returns the updated notification if found, None otherwise
        """
        try:
            # First verify the notification belongs to the user
            notification = await self.db.notifications.find_one({
                "_id": ObjectId(notification_id),
                "recipient_id": ObjectId(user_id)
            })
            
            if not notification:
                return None
            
            # Update the notification
            updated_notification = await self.db.notifications.find_one_and_update(
                {"_id": ObjectId(notification_id)},
                {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}},
                return_document=True
            )
            
            if updated_notification:
                # Convert ObjectIds to strings
                updated_notification["_id"] = str(updated_notification["_id"])
                updated_notification["id"] = updated_notification["_id"]
                updated_notification["recipient_id"] = str(updated_notification["recipient_id"])
                updated_notification["sender_id"] = str(updated_notification["sender_id"])
                updated_notification["source_id"] = str(updated_notification["source_id"])
            
            return updated_notification
        except Exception as e:
            raise Exception(f"Error marking notification as read: {str(e)}")
    
    async def mark_all_notifications_as_read(self, user_id: str) -> bool:
        """
        Mark all unread notifications for a user as read
        Returns True if successful, False otherwise
        """
        try:
            result = await self.db.notifications.update_many(
                {
                    "recipient_id": ObjectId(user_id),
                    "is_read": False
                },
                {
                    "$set": {
                        "is_read": True,
                        "read_at": datetime.now(timezone.utc)
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error marking all notifications as read: {str(e)}")
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """
        Delete a notification
        Returns True if successful, False otherwise
        """
        try:
            # First verify the notification belongs to the user
            notification = await self.db.notifications.find_one({
                "_id": ObjectId(notification_id),
                "recipient_id": ObjectId(user_id)
            })
            
            if not notification:
                return False
            
            # Delete the notification
            result = await self.db.notifications.delete_one({"_id": ObjectId(notification_id)})
            
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Error deleting notification: {str(e)}")
    
    async def get_notification_by_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific notification by ID
        Returns the notification if found, None otherwise
        """
        try:
            notification = await self.db.notifications.find_one({"_id": ObjectId(notification_id)})
            
            if notification:
                # Convert ObjectIds to strings
                notification["_id"] = str(notification["_id"])
                notification["id"] = notification["_id"]
                notification["recipient_id"] = str(notification["recipient_id"])
                notification["sender_id"] = str(notification["sender_id"])
                notification["source_id"] = str(notification["source_id"])
            
            return notification
        except Exception as e:
            raise Exception(f"Error getting notification by ID: {str(e)}")