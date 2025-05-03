from fastapi import APIRouter, HTTPException, Response, status, Depends, Query
from models.notifications_model import NotificationResponse
from db.schemas.users_schema import UserInDB
from dependencies.auth import get_current_active_user
from dependencies.notifications import NotificationServiceDep

router = APIRouter(
    # prefix="/notifications",
    # tags=["notifications"]
)

@router.get("/", response_model=list[NotificationResponse])
async def get_user_notifications(
    current_user: UserInDB = Depends(get_current_active_user),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    notification_service: NotificationServiceDep = None
):
    """Get all notifications for the current user
    
    Parameters:
    - unread_only: If True, returns only unread notifications
    """
    try:
        notifications = await notification_service.get_user_notifications(
            str(current_user.id), 
            unread_only
        )
        return notifications
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get notifications: {str(e)}"
        )

@router.post("/mark-as-read/{notification_id}", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    notification_service: NotificationServiceDep = None
):
    """Mark a specific notification as read"""
    try:
        notification = await notification_service.mark_notification_as_read(
            notification_id,
            str(current_user.id)
        )
        return notification
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to mark notification as read: {str(e)}"
        )

@router.post("/mark-all-as-read/", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_as_read(
    current_user: UserInDB = Depends(get_current_active_user),
    notification_service: NotificationServiceDep = None
):
    """Mark all notifications for the current user as read"""
    try:
        await notification_service.mark_all_notifications_as_read(str(current_user.id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    notification_service: NotificationServiceDep = None
):
    """Delete a specific notification"""
    try:
        await notification_service.delete_notification(
            notification_id,
            str(current_user.id)
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete notification: {str(e)}"
        )

# Internal endpoints for creating notifications (typically called by other services)
@router.post("/internal/article-post/{article_id}/{commenter_id}", status_code=status.HTTP_201_CREATED)
async def create_article_post_notification(
    article_id: str,
    commenter_id: str,
    article_owner_id: str,
    notification_service: NotificationServiceDep = None
):
    """Internal endpoint to create a notification when someone posts on an article"""
    try:
        notification = await notification_service.create_article_post_notification(
            article_id,
            commenter_id,
            article_owner_id
        )
        return notification
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create article post notification: {str(e)}"
        )

@router.post("/internal/follow/{follower_id}/{followed_id}", status_code=status.HTTP_201_CREATED)
async def create_follow_notification(
    follower_id: str,
    followed_id: str,
    notification_service: NotificationServiceDep = None
):
    """Internal endpoint to create a notification when someone follows a user"""
    try:
        notification = await notification_service.create_follow_notification(
            follower_id,
            followed_id
        )
        return notification
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create follow notification: {str(e)}"
        )