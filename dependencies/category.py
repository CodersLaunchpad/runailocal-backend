from fastapi import Depends
from typing import Annotated

from db.db import get_db
from repos.category_repo import CategoryRepository

def get_category_repository(db=Depends(get_db)):
    """Create and return a CategoryRepository instance"""
    return CategoryRepository(db)

# Create a type alias for dependency injection
CategoryRepositoryDep = Annotated[CategoryRepository, Depends(get_category_repository)]
