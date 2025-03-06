from fastapi import Depends
from typing import Annotated

from db.db import get_db
from repos.article_repo import ArticleRepository
from dependencies.category import get_category_repository
from dependencies.user import get_user_repository
from services.article_service import ArticleService

def get_article_repository(db=Depends(get_db)):
    """Create and return an ArticleRepository instance"""
    return ArticleRepository(db)

def get_article_service(
        article_repo=Depends(get_article_repository),
        user_repo=Depends(get_user_repository),
        category_repo=Depends(get_category_repository)
    ):
    """Create and return an ArticleService instance"""
    return ArticleService(article_repo, user_repo, category_repo)

# Create a type alias for dependency injection
ArticleRepositoryDep = Annotated[ArticleRepository, Depends(get_article_repository)]
ArticleServiceDep = Annotated[ArticleService, Depends(get_article_service)]