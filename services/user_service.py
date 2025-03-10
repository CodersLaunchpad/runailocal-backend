import io
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import random
import os
from io import BytesIO
import base64
import uuid
from PIL import Image, ImageDraw, ImageFont
from fastapi import UploadFile

from config import Settings
from utils.security import get_password_hash
from models.users_model import UserCreate, UserUpdate
from db.schemas.users_schema import UserInDB
from repos.user_repo import UserRepository
from config import settings

class UserService:
    """
    Service layer for user-related operations
    Handles business logic between controllers and data access
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository
    
    async def create_user(self, user: UserCreate) -> Dict[str, Any]:
        """Create a new user"""
        # Check for existing username/email
        print("hit the creating user route")
        existing_user = await self.user_repo.find_by_username(user.username)
        if existing_user:
            raise ValueError("Username already registered")
        
        existing_email = await self.user_repo.find_by_email(user.email)
        if existing_email:
            raise ValueError("Email already registered")
        
        # Initialize variables
        profile_picture_base64 = None
        profile_photo_id = getattr(user, 'profile_photo_id', None)
        
        # Handle base64 profile picture (backward compatibility)
        if not profile_photo_id and hasattr(user, 'profile_picture') and user.profile_picture:
            try:
                # Get MinIO client
                from db.db import get_object_storage
                from services.minio_service import upload_base64_profile_picture
                minio_client = await get_object_storage()
                
                # Upload to MinIO
                file_record = await upload_base64_profile_picture(
                    base64_data=user.profile_picture,
                    username=user.username,
                    minio_client=minio_client
                )
                profile_photo_id = file_record["file_id"]
            except Exception as e:
                # Fall back to generating avatar
                print(f"Error handling base64 image: {str(e)}")
                initials = user.username[:2].upper()
                profile_picture_base64 = self._generate_initials_avatar_base64(initials)
        
        # Generate avatar if no profile picture
        if not profile_photo_id and not profile_picture_base64:
            initials = user.profile_picture_initials or user.username[:2].upper()
            profile_picture_base64 = self._generate_initials_avatar_base64(initials)
        
        # Create user dictionary
        hashed_password = get_password_hash(user.password)
        user_dict = user.model_dump(exclude={"password", "profile_picture", "profile_picture_initials"})
        user_dict["password_hash"] = hashed_password
        user_dict["created_at"] = datetime.now(timezone.utc)
        
        # Add profile picture info
        if profile_photo_id:
            user_dict["profile_photo_id"] = profile_photo_id
        if profile_picture_base64:
            user_dict["profile_picture_base64"] = profile_picture_base64
        # Create user object
        hashed_password = get_password_hash(user.password)
        user_dict = user.model_dump(exclude={"password", "profile_picture", "profile_picture_initials"})
        user_dict["password_hash"] = hashed_password
        user_dict["created_at"] = datetime.now(timezone.utc)
        
        # Add profile picture information
        if profile_photo_id:
            user_dict["profile_photo_id"] = profile_photo_id
        if profile_picture_base64:
            user_dict["profile_picture_base64"] = profile_picture_base64
        
        # Set user details based on type
        if user.user_type == "normal":
            user_dict["user_details"] = {
                "type": "normal",
                "signup_date": datetime.now(timezone.utc),
                "email_notifications": True,
                "reading_preferences": []
            }
        elif user.user_type == "author":
            user_dict["user_details"] = {
                "type": "author",
                "bio": "",
                "slug": user.username.lower().replace(" ", "-"),
                "profile_picture": profile_picture_base64,
                "articles_count": 0
            }
        elif user.user_type == "admin":
            # Only existing admins can create new admins, otherwise default to normal user
            user_dict["user_details"] = {
                "type": "normal",
                "signup_date": datetime.now(timezone.utc),
                "email_notifications": True
            }
        
        user_dict["likes"] = []
        user_dict["following"] = []
        user_dict["followers"] = []
        user_dict["bookmarks"] = []
        
        # Insert into database
        created_user = await self.user_repo.create_user(user_dict)
        
        # Add profile picture URL to response if available
        if profile_photo_id:
            from services.minio_service import get_file_by_id
            file_record = await get_file_by_id(profile_photo_id)
            if file_record and "file_url" in file_record:
                created_user["profile_picture_url"] = file_record["file_url"]
        
        return created_user
    
    def _generate_initials_avatar_base64(self, initials: str) -> str:
        """Generate an avatar with initials and return as base64"""
        # Ensure we have at least one character
        initials = initials[:2].upper() if initials else "U"
        
        # Create a random background color - using pastel colors
        bg_color = (
            random.randint(100, 200),  # R
            random.randint(100, 200),  # G
            random.randint(100, 200),  # B
        )
        
        # Create a new image with a colored background
        img_size = 200
        img = Image.new('RGB', (img_size, img_size), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, or fall back to default
        try:
            # Try to load a font - adjust the path based on your server
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            if not os.path.exists(font_path):
                font_path = "C:\\Windows\\Fonts\\arial.ttf"
                if not os.path.exists(font_path):
                    font = ImageFont.load_default()
                else:
                    font = ImageFont.truetype(font_path, size=80)
            else:
                font = ImageFont.truetype(font_path, size=80)
        except Exception:
            font = ImageFont.load_default()
        
        # Calculate text size to center it
        try:
            text_bbox = draw.textbbox((0, 0), initials, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            # For older Pillow versions
            text_width, text_height = draw.textsize(initials, font=font)
        
        position = ((img_size - text_width) // 2, (img_size - text_height) // 2)
        
        # Draw the text in white
        draw.text(position, initials, font=font, fill=(255, 255, 255))
        
        # Convert the image to base64 without saving to disk
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Return as data URL format for easy use in img tags
        return f"data:image/png;base64,{img_str}"

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get detailed profile for a user with statistics"""
        return await self.user_repo.get_user_profile(user_id)
    
    async def get_user_likes(self, current_user: UserInDB) -> List[Dict[str, Any]]:
        """Get liked articles for a user"""
        return await self.user_repo.get_user_likes(current_user)
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> Dict[str, Any]:
        """Update a user's information"""
        update_data = {k: v for k, v in user_update.model_dump(exclude_unset=True).items() 
                      if v is not None}

        # Hash the password if it's being updated
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(update_data.pop("password"))
        
        if update_data:
            return await self.user_repo.update_user(user_id, update_data)
        
        # If no updates, return current user
        return await self.user_repo.get_user_by_id(user_id)
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID"""
        return await self.user_repo.get_user_by_id(user_id)
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin function)"""
        return await self.user_repo.get_all_users()
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and their associated content"""
        return await self.user_repo.delete_user(user_id)
    
    async def follow_author(self, user_id: str, author_identifier: str) -> Dict[str, str]:
        """
        Follow an author by username or ID
        Returns status message
        """
        return await self.user_repo.follow_author(user_id, author_identifier)
    
    async def unfollow_author(self, user_id: str, author_identifier: str) -> Dict[str, str]:
        """
        Unfollow an author by username or ID
        Returns status message
        """
        return await self.user_repo.unfollow_author(user_id, author_identifier)
    
    async def get_following(self, current_user: UserInDB) -> List[Dict[str, Any]]:
        """Get list of users that the current user follows"""
        return await self.user_repo.get_following(current_user)
    
    async def get_user_statistics(self, user_identifier: str, current_user: Optional[UserInDB]) -> Dict[str, Any]:
        """Get comprehensive statistics for a user"""
        return await self.user_repo.get_user_statistics(user_identifier, current_user)
    
    async def bookmark_article(self, user_id: str, article_id: str) -> Dict[str, str]:
        """
        Bookmark an article
        Returns status message
        """
        return await self.user_repo.bookmark_article(user_id, article_id)
    
    async def remove_bookmark(self, user_id: str, article_id: str) -> Dict[str, str]:
        """
        Remove an article bookmark
        Returns status message
        """
        return await self.user_repo.remove_bookmark(user_id, article_id)
    
    async def get_user_bookmarks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all bookmarked articles for a user"""
        return await self.user_repo.get_user_bookmarks(user_id)