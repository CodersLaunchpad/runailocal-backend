#!/usr/bin/env python3
"""
Migration script to add new user profile fields:
- bio
- date_of_birth  
- social_media_links

This script will update existing user documents to include these fields with default values.
"""

import asyncio
import motor.motor_asyncio
from datetime import datetime
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

async def migrate_user_profile_fields():
    """Migrate existing users to include new profile fields"""
    
    # Connect to MongoDB
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    
    try:
        print("Starting migration: Adding user profile fields...")
        
        # Get all users
        users_collection = db.users
        users = await users_collection.find({}).to_list(length=None)
        
        print(f"Found {len(users)} users to migrate")
        
        # Update each user to include the new fields
        updated_count = 0
        for user in users:
            user_id = user.get("_id")
            
            # Prepare update data
            update_data = {}
            
            # Add bio field if it doesn't exist
            if "bio" not in user:
                update_data["bio"] = ""
            
            # Add date_of_birth field if it doesn't exist
            if "date_of_birth" not in user:
                update_data["date_of_birth"] = None
            
            # Add social_media_links field if it doesn't exist
            if "social_media_links" not in user:
                update_data["social_media_links"] = []
            
            # Only update if there are fields to add
            if update_data:
                # Add migration timestamp
                update_data["profile_fields_migrated_at"] = datetime.utcnow()
                
                # Update the user document
                result = await users_collection.update_one(
                    {"_id": user_id},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    print(f"Updated user {user.get('username', 'Unknown')} (ID: {user_id})")
                else:
                    print(f"No changes needed for user {user.get('username', 'Unknown')} (ID: {user_id})")
            else:
                print(f"User {user.get('username', 'Unknown')} (ID: {user_id}) already has all required fields")
        
        print(f"\nMigration completed successfully!")
        print(f"Updated {updated_count} users")
        
        # Verify the migration
        print("\nVerifying migration...")
        users_without_fields = await users_collection.count_documents({
            "$or": [
                {"bio": {"$exists": False}},
                {"date_of_birth": {"$exists": False}},
                {"social_media_links": {"$exists": False}}
            ]
        })
        
        if users_without_fields == 0:
            print("✅ All users now have the required profile fields")
        else:
            print(f"⚠️  {users_without_fields} users still missing required fields")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        raise
    finally:
        client.close()

async def main():
    """Main function to run the migration"""
    print("User Profile Fields Migration Script")
    print("=" * 40)
    
    try:
        await migrate_user_profile_fields()
        print("\n🎉 Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
