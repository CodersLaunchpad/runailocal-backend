from fastapi import Depends
from typing import Annotated

from db.db import get_db
from repos.notification_repo import NotificationRepository
from services.notification_service import NotificationService
from dependencies.article import get_article_repository
from repos.user_repo import UserInDB
from dependencies.user import get_user_repository

def get_notification_repository(db=Depends(get_db)):
    """Create and return a CommentRepository instance"""
    return NotificationRepository(db)

async def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repository),
    user_repo: UserInDB = Depends(get_user_repository)  # Add this
) -> NotificationService:
    return NotificationService(notification_repo, user_repo)

# Create a type alias for dependency injection
NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]