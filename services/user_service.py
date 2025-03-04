from typing import List, Optional
from models.user_model import UserCreate, UserResponse, UserUpdate, Token
from schemas.user_schema import UserInDB
from repositories.user_repository import UserRepository
from mappers.user_mapper import user_db_to_response, create_user_dict, apply_user_update
from core.security import get_password_hash, verify_password, create_access_token
from core.exceptions import NotFoundException, BadRequestException, UnauthorizedException
from datetime import timedelta

class UserService:
    """Service for user-related operations"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    async def create_user(self, user_create: UserCreate) -> UserResponse:
        """Create a new user"""
        # Check if user with same email or username already exists
        existing_email = await self.user_repository.find_by_email(user_create.email)
        if existing_email:
            raise BadRequestException("Email already registered")
        
        existing_username = await self.user_repository.find_by_username(user_create.username)
        if existing_username:
            raise BadRequestException("Username already taken")
        
        # Hash the password
        hashed_password = get_password_hash(user_create.password)
        
        # Create user dict for database
        user_data = create_user_dict(user_create, hashed_password)
        
        # Store in database
        new_user = await self.user_repository.create(user_data)
        
        # Convert to response model
        return user_db_to_response(new_user)
    
    async def get_user(self, user_id: str) -> UserResponse:
        """Get a user by ID"""
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise NotFoundException("User not found")
        return user_db_to_response(user)
    
    async def authenticate_user(self, username: str, password: str) -> Token:
        """Authenticate a user and return access token"""
        user = await self.user_repository.find_by_username(username)
        if not user:
            raise UnauthorizedException("Invalid username or password")
        
        if not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid username or password")
        
        # Update last login time
        await self.user_repository.update_last_login(str(user.id))
        
        # Create access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.username}, 
            expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token)
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> UserResponse:
        """Update a user"""
        # Check if user exists
        current_user = await self.user_repository.find_by_id(user_id)
        if current_user is None:
            raise NotFoundException("User not found")
        
        # Check if trying to update to an existing email
        if user_update.email and user_update.email != current_user.email:
            existing_email = await self.user_repository.find_by_email(user_update.email)
            if existing_email:
                raise BadRequestException("Email already registered")
        
        # Check if trying to update to an existing username
        if user_update.username and user_update.username != current_user.username:
            existing_username = await self.user_repository.find_by_username(user_update.username)
            if existing_username:
                raise BadRequestException("Username already taken")
        
        # Get only the fields that are being updated
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Update in database
        updated_user = await self.user_repository.update(user_id, update_data)
        if updated_user is None:
            raise NotFoundException("User not found or update failed")
        
        return user_db_to_response(updated_user)
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        result = await self.user_repository.delete(user_id)
        if not result:
            raise NotFoundException("User not found")
        return True
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """List all users with pagination"""
        users = await self.user_repository.list_users(skip, limit)
        return [user_db_to_response(user) for user in users]