from typing import Dict, List, Optional, Any
from bson.objectid import ObjectId
from helpers.time import get_current_utc_time 
from motor.motor_asyncio import AsyncIOMotorDatabase
from schemas.user_schema import UserInDB
from db.mongodb import handle_mongodb_id, convert_object_id
from core.exceptions import NotFoundException
from datetime import datetime

class UserRepository:
    """Repository for user data access operations"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.collection = database.users
    
    async def create(self, user_data: Dict[str, Any]) -> UserInDB:
        """Create a new user in the database"""
        result = await self.collection.insert_one(user_data)
        created_user = await self.collection.find_one({"_id": result.inserted_id})
        if created_user is None:
            raise NotFoundException("User creation failed")
        return UserInDB(**created_user)
    
    async def find_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Find a user by ID"""
        try:
            object_id = convert_object_id(user_id)
            user = await self.collection.find_one({"_id": object_id})
            if user is None:
                return None
            return UserInDB(**user)
        except:
            return None
    
    async def find_by_email(self, email: str) -> Optional[UserInDB]:
        """Find a user by email"""
        user = await self.collection.find_one({"email": email})
        if user is None:
            return None
        return UserInDB(**user)
    
    async def find_by_username(self, username: str) -> Optional[UserInDB]:
        """Find a user by username"""
        user = await self.collection.find_one({"username": username})
        if user is None:
            return None
        return UserInDB(**user)
    
    async def update(self, user_id: str, update_data: Dict[str, Any]) -> Optional[UserInDB]:
        """Update a user in the database"""
        object_id = convert_object_id(user_id)
        result = await self.collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )
        if result.modified_count == 0:
            return None
        
        updated_user = await self.collection.find_one({"_id": object_id})
        if updated_user is None:
            return None
        
        return UserInDB(**updated_user)
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login time"""
        object_id = convert_object_id(user_id)
        result = await self.collection.update_one(
            {"_id": object_id},
            {"$set": {"last_login": get_current_utc_time()}}
        )
        return result.modified_count > 0
    
    async def delete(self, user_id: str) -> bool:
        """Delete a user from the database"""
        object_id = convert_object_id(user_id)
        result = await self.collection.delete_one({"_id": object_id})
        return result.deleted_count > 0
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserInDB]:
        """List users with pagination"""
        users = []
        cursor = self.collection.find().skip(skip).limit(limit)
        async for user in cursor:
            users.append(UserInDB(**user))
        return users