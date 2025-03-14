from fastapi import HTTPException, status
from typing import Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import jwt

from utils.security import verify_password
from repos.user_repo import UserRepository
from mappers.users_mapper import user_db_to_response
from models.auth_model import Token, TokenData
from config import (
    JWT_SECRET_KEY, 
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES
)

class AuthService:
    """
    Service layer for authentication-related operations
    Handles login, token validation, and related business logic
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository
    
    async def generate_user_token(self, username: str, password: str) -> Token:
        """
        Authenticate a user with username and password
        Returns user token if authentication succeeds, None otherwise
        """
        # Find user by username
        user_db = await self.user_repo.find_by_username(username)
        
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Verify password
        if not verify_password(password, user_db.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token with extended expiry
        access_token_expires = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            TokenData(
                username=user_db.username,
                user_id=user_db.id,
                user_type=user_db.user_type
            ),
            expires_delta=access_token_expires
        )

        # TODO: add refresh token

        # Update last login time
        await self.update_last_login(user_db.id)

        print("user info retrieved: ", user_db)
        print("file info retrieved: ", user_db.profile_file)

        return Token(
            access_token=access_token, 
            token_type="bearer", 
            # profile_picture_base64=user_db.profile_picture_base64,
            profile_picture_base64="DEPRECIATED",
            profile_file=user_db.profile_file

        )
    
    def create_access_token(self, data: TokenData, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=15)
        
        token_data = {
            "sub": data.username, 
            "id": data.user_id, 
            "type": data.user_type,
            "exp": expire
        }
        encoded_jwt = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    async def update_last_login(self, user_id: str) -> None:
        """Update the last login timestamp for a user"""
        update_data = {"last_login": datetime.now(timezone.utc)}
        await self.user_repo.update_user(user_id, update_data)