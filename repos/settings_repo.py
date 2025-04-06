from typing import Optional, Dict, Any
from bson import ObjectId
from models.models import AppSettings, AppSettingsUpdate
from utils.time import get_current_utc_time
import os

class SettingsRepository:
    """Repository for managing application settings"""
    
    def __init__(self, db):
        self.db = db
        self.collection = self.db.settings
    
    async def get_settings(self) -> Optional[Dict[str, Any]]:
        """Get current application settings"""
        try:
            settings = await self.collection.find_one()
            if not settings:
                # Create default settings if none exist
                default_settings = AppSettings()
                
                # Override with environment variables if they exist
                auto_publish_env = os.getenv("AUTO_PUBLISH_ARTICLES", "false").lower() == "true"
                auto_upload_env = os.getenv("AUTO_UPLOAD", "false").lower() == "true"
                
                default_settings.auto_publish_articles = auto_publish_env
                default_settings.auto_upload = auto_upload_env
                
                await self.collection.insert_one(default_settings.model_dump(by_alias=True))
                return default_settings.model_dump(by_alias=True)
            return settings
        except Exception as e:
            print(f"Error in get_settings: {str(e)}")
            raise Exception(f"Failed to get settings: {str(e)}")
    
    async def update_settings(self, settings_data: AppSettingsUpdate, updated_by: str) -> Dict[str, Any]:
        """Update application settings"""
        # Convert update model to dict and remove None values
        update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise ValueError("No valid settings to update")
            
        update_data["updated_at"] = get_current_utc_time()
        update_data["updated_by"] = updated_by
        
        # Update or insert settings
        result = await self.collection.update_one(
            {},
            {"$set": update_data},
            upsert=True
        )
        
        # Get updated settings
        updated_settings = await self.get_settings()
        return updated_settings
    
    async def get_auto_publish_setting(self) -> bool:
        """Get the auto-publish articles setting"""
        try:
            settings = await self.get_settings()
            if not settings:
                print("No settings found, creating default settings")
                # Create default settings if none exist
                default_settings = AppSettings()
                
                # Override with environment variables if they exist
                auto_publish_env = os.getenv("AUTO_PUBLISH_ARTICLES", "false").lower() == "true"
                default_settings.auto_publish_articles = auto_publish_env
                
                await self.collection.insert_one(default_settings.model_dump(by_alias=True))
                return default_settings.auto_publish_articles
            
            print(f"Current settings: {settings}")
            # Convert the settings dict to AppSettings model to ensure proper field access
            app_settings = AppSettings(**settings)
            return app_settings.auto_publish_articles
        except Exception as e:
            print(f"Error in get_auto_publish_setting: {str(e)}")
            raise Exception(f"Failed to get auto-publish setting: {str(e)}")
    
    async def get_auto_upload_setting(self) -> bool:
        """Get the auto-upload setting"""
        try:
            settings = await self.get_settings()
            if not settings:
                print("No settings found, creating default settings")
                default_settings = AppSettings()
                
                # Override with environment variables if they exist
                auto_upload_env = os.getenv("AUTO_UPLOAD", "false").lower() == "true"
                default_settings.auto_upload = auto_upload_env
                
                await self.collection.insert_one(default_settings.model_dump(by_alias=True))
                return default_settings.auto_upload
            
            print(f"Current settings: {settings}")
            app_settings = AppSettings(**settings)
            return app_settings.auto_upload
        except Exception as e:
            print(f"Error in get_auto_upload_setting: {str(e)}")
            raise Exception(f"Failed to get auto-upload setting: {str(e)}") 