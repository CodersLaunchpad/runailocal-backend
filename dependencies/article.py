from fastapi import Depends
from typing import Annotated

from db.db import get_db
from repos.article_repo import ArticleRepository

def get_article_repository(db=Depends(get_db)):
    """Create and return an ArticleRepository instance"""
    return ArticleRepository(db)

# Create a type alias for dependency injection
ArticleRepositoryDep = Annotated[ArticleRepository, Depends(get_article_repository)]