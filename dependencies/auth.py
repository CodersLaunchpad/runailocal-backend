# dependencies/auth.py
from fastapi import Depends, HTTPException, status
import jwt
from typing import Optional, Annotated
from services.auth_service import AuthService
from dependencies.user import get_user_repository
from utils.security import verify_password

from db.schemas.users_schema import UserInDB
from .db import DB
from config import (
    oauth2_scheme, 
    oauth2_scheme_optional,
    JWT_SECRET_KEY, 
    JWT_ALGORITHM
)
from models.auth_model import TokenData

# Database dependency
async def get_user(username: str, db: DB) -> Optional[UserInDB]:
    """
    Retrieve a user by username with case-insensitive matching.
    """
    # Use a case-insensitive regex query to find the user
    user = await db.users.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
    
    if user:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
    
    return UserInDB(**user) if user else None

async def authenticate_user(username: str, password: str, db: DB) -> Optional[UserInDB]:
    """Authenticate a user with username and password."""
    user = await get_user(username, db)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: DB = None) -> UserInDB:
    """Get the current authenticated user from the JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        user_type: str = payload.get("type")
        
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username, user_id=user_id, user_type=user_type)
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = await get_user(username=token_data.username, db=db)
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_active_user(current_user = Depends(get_current_user)) -> UserInDB:
    """Get the current authenticated user and verify they are active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user = Depends(get_current_active_user)) -> UserInDB:
    """Get the current authenticated user and verify they have admin privileges."""
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_author_user(current_user = Depends(get_current_active_user)) -> UserInDB:
    """Get the current authenticated user and verify they have author or admin privileges."""
    if current_user.user_type not in ["author", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional),
    db: DB = None
) -> Optional[UserInDB]:
    """Similar to get_current_user but returns None when token is missing or invalid."""
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = await get_user(username=username, db=db)
        return user
    except jwt.PyJWTError:
        return None

def get_auth_service(user_repo = Depends(get_user_repository)):
    """
    Dependency to get an auth service instance.
    """
    return AuthService(user_repo)

# Create annotated types for cleaner dependency injection
CurrentUser = Annotated[UserInDB, Depends(get_current_user)]
CurrentActiveUser = Annotated[UserInDB, Depends(get_current_active_user)]
OptionalUser = Annotated[Optional[UserInDB], Depends(get_current_user_optional)]
AdminUser = Annotated[UserInDB, Depends(get_admin_user)]
AuthorUser = Annotated[UserInDB, Depends(get_author_user)]

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
