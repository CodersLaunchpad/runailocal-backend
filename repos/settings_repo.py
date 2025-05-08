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
                default_settings = AppSettings(
                    auto_publish_articles=os.getenv("AUTO_PUBLISH_ARTICLES", "false").lower() == "true",
                    auto_upload=os.getenv("AUTO_UPLOAD", "false").lower() == "true",
                    dev_mode=os.getenv("DEV_MODE", "false").lower() == "true",
                    dev_mode_email=os.getenv("DEV_MODE_EMAIL")
                )
                await self.collection.insert_one(default_settings.model_dump(by_alias=True))
                return default_settings.model_dump(by_alias=True)
            return settings
        except Exception as e:
            print(f"Error in get_settings: {str(e)}")
            raise Exception(f"Failed to get settings: {str(e)}")
    
    async def update_settings(self, settings_update: AppSettingsUpdate) -> Dict[str, Any]:
        """Update application settings"""
        try:
            update_data = settings_update.model_dump(exclude_unset=True)
            update_data["updated_at"] = get_current_utc_time()
            
            result = await self.collection.update_one(
                {},
                {"$set": update_data},
                upsert=True
            )
            
            if result.modified_count == 0 and not result.upserted_id:
                raise Exception("Failed to update settings")
            
            # Get updated settings
            updated_settings = await self.get_settings()
            if not updated_settings:
                raise Exception("Failed to retrieve updated settings")
            
            return updated_settings
            
        except Exception as e:
            print(f"Error in update_settings: {str(e)}")
            raise Exception(f"Failed to update settings: {str(e)}")
    
    async def get_auto_publish_setting(self) -> bool:
        """Get the auto-publish articles setting"""
        try:
            settings = await self.get_settings()
            if not settings:
                print("No settings found, creating default settings")
                # Create default settings if none exist
                default_settings = AppSettings()
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
                await self.collection.insert_one(default_settings.model_dump(by_alias=True))
                return default_settings.auto_upload
            
            print(f"Current settings: {settings}")
            app_settings = AppSettings(**settings)
            return app_settings.auto_upload
        except Exception as e:
            print(f"Error in get_auto_upload_setting: {str(e)}")
            raise Exception(f"Failed to get auto-upload setting: {str(e)}")
    
    async def initialize_settings_from_env(self) -> Dict[str, Any]:
        """Initialize settings from environment variables if they don't exist in the database"""
        try:
            # Get current settings
            current_settings = await self.get_settings()
            
            # Create default settings from environment variables
            default_settings = AppSettings(
                auto_publish_articles=os.getenv("AUTO_PUBLISH_ARTICLES", "false").lower() == "true",
                auto_upload=os.getenv("AUTO_UPLOAD", "false").lower() == "true",
                dev_mode=os.getenv("DEV_MODE", "false").lower() == "true",
                dev_mode_email=os.getenv("DEV_MODE_EMAIL")
            )
            
            # If no settings exist, insert the default settings
            if not current_settings:
                await self.collection.insert_one(default_settings.model_dump(by_alias=True))
                return default_settings.model_dump(by_alias=True)
            
            # If settings exist but some fields are missing, update them
            update_data = {}
            for field, value in default_settings.model_dump(by_alias=True).items():
                if field not in current_settings:
                    update_data[field] = value
            
            if update_data:
                update_data["updated_at"] = get_current_utc_time()
                await self.collection.update_one(
                    {},
                    {"$set": update_data},
                    upsert=True
                )
                # Get updated settings
                return await self.get_settings()
            
            return current_settings
            
        except Exception as e:
            print(f"Error in initialize_settings_from_env: {str(e)}")
            raise Exception(f"Failed to initialize settings from environment: {str(e)}") 