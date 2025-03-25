from typing import Optional, Dict, Any
from bson import ObjectId
from models.models import AppSettings
from db.db import get_db

class SettingsRepository:
    """Repository for managing application settings"""
    
    def __init__(self):
        self.db = get_db()
        self.collection = self.db.settings
    
    async def get_settings(self) -> Optional[Dict[str, Any]]:
        """Get current application settings"""
        settings = await self.collection.find_one()
        if not settings:
            # Create default settings if none exist
            default_settings = AppSettings()
            await self.collection.insert_one(default_settings.model_dump(by_alias=True))
            return default_settings.model_dump(by_alias=True)
        return settings
    
    async def update_settings(self, settings_data: Dict[str, Any], updated_by: str) -> Dict[str, Any]:
        """Update application settings"""
        settings_data["updated_at"] = get_current_utc_time()
        settings_data["updated_by"] = updated_by
        
        # Update or insert settings
        result = await self.collection.update_one(
            {},
            {"$set": settings_data},
            upsert=True
        )
        
        # Get updated settings
        updated_settings = await self.get_settings()
        return updated_settings
    
    async def get_auto_publish_setting(self) -> bool:
        """Get the auto-publish articles setting"""
        settings = await self.get_settings()
        return settings.get("auto_publish_articles", False) 