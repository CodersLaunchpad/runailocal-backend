from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import random
import os
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont

from utils.security import get_password_hash
from models.users_model import UserCreate, UserUpdate
from db.schemas.users_schema import UserInDB
from repos.user_repo import UserRepository

class UserService:
    """
    Service layer for user-related operations
    Handles business logic between controllers and data access
    """
    
    def __init__(self, user_repository: UserRepository):
        self.user_repo = user_repository
    
    async def create_user(self, user: UserCreate) -> Dict[str, Any]:
        """Create a new user"""
        # Check for existing username
        existing_user = await self.user_repo.find_by_username(user.username)
        if existing_user:
            raise ValueError("Username already registered")
        
        # Check for existing email
        existing_email = await self.user_repo.find_by_email(user.email)
        if existing_email:
            raise ValueError("Email already registered")
        
        # Process profile picture or generate avatar
        profile_picture_base64 = None
        
        if user.profile_picture:
            try:
                # The user.profile_picture is already in base64 format from the frontend
                # Just clean it up if needed
                if ',' in user.profile_picture:
                    # Keep the full data URL format for frontend display
                    profile_picture_base64 = user.profile_picture
                else:
                    # Add the data URL prefix if it's missing
                    profile_picture_base64 = f"data:image/jpeg;base64,{user.profile_picture}"
            except Exception as e:
                # TODO: log this error
                print(f"Error processing profile picture: {str(e)}")
                # Fall back to generating an avatar
                if user.first_name and user.last_name:
                    initials = (user.first_name[0] + user.last_name[0]).upper()
                else:
                    initials = user.username[:2].upper()
                profile_picture_base64 = self._generate_initials_avatar_base64(initials)
        
        elif user.profile_picture_initials:
            # Generate an avatar with the provided initials
            profile_picture_base64 = self._generate_initials_avatar_base64(user.profile_picture_initials)
        
        else:
            # Generate default initials from username
            initials = user.username[:2].upper()
            profile_picture_base64 = self._generate_initials_avatar_base64(initials)
        
        # Create user object
        hashed_password = get_password_hash(user.password)
        user_dict = user.model_dump(exclude={"password", "profile_picture", "profile_picture_initials"})
        user_dict["password_hash"] = hashed_password
        user_dict["created_at"] = datetime.now(timezone.utc)
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
        """Get favorite articles for a user"""
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