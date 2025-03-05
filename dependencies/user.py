from fastapi import Depends
from typing import Annotated

from repos.user_repo import UserRepository
from services.user_service import UserService
from .db import get_db

def get_user_repository(db = Depends(get_db)):
    """
    Dependency to get a user repository instance.
    """
    return UserRepository(db)

def get_user_service(repo = Depends(get_user_repository)):
    """
    Dependency to get a user service instance.
    """
    return UserService(repo)

# Create annotated types for cleaner dependency injection
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]