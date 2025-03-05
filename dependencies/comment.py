from fastapi import Depends
from typing import Annotated

from db.db import get_db
from repos.comment_repo import CommentRepository
from services.comment_service import CommentService
from dependencies.article import get_article_repository

def get_comment_repository(db=Depends(get_db)):
    """Create and return a CommentRepository instance"""
    return CommentRepository(db)

def get_comment_service(
    comment_repo=Depends(get_comment_repository),
    article_repo=Depends(get_article_repository)
):
    """Create and return a CommentService instance with required repositories"""
    return CommentService(comment_repo, article_repo)

# Create a type alias for dependency injection
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]