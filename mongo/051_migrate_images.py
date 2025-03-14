import asyncio
import base64
import io
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from pymongo import MongoClient
from minio import Minio
# from ..db.db import get_object_storage, get_db

# Update these settings
# MONGODB_URI = "mongodb://localhost:27017"
# MONGODB_DB = "cms"
# MINIO_ENDPOINT = "localhost:9000"
# MINIO_ACCESS_KEY = "minioaccesskey"
# MINIO_SECRET_KEY = "miniosecretkey"
# MINIO_BUCKET = "your-bucket-name"
# SECURE = False  # Set to True if using HTTPS

import os
from dotenv import load_dotenv

# Build the path to the .env file located in the project root folder
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Retrieve the environment variables with fallback default values if not defined in .env
MONGODB_URI = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("DATABASE_NAME", "cms")
MINIO_ENDPOINT = os.getenv("MINIO_SERVER", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_USERNAME", "minioaccesskey")
MINIO_SECRET_KEY = os.getenv("MINIO_PASSWORD", "miniosecretkey")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "your-bucket-name")
# Convert the SECURE value to a boolean; accepts "True", "true", "1", etc.
SECURE = os.getenv("SECURE", "False").lower() in ['true', '1', 't']


# Basic functions
def connect_to_mongodb():
    print(f"Connecting to MongoDB...")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB]
    # Verify collections exist
    print(f"Available collections: {db.list_collection_names()}")
    return db

def connect_to_minio():
    print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

def upload_to_minio(data, filename, content_type, minio_client, folder="profile_photos"):
    """Simple function to upload a file to MinIO"""
    # Generate a unique ID for the file
    file_id = str(uuid.uuid4())
    
    # Get file extension from the filename
    if '.' in filename:
        file_extension = filename.split('.')[-1].lower()
    else:
        file_extension = 'jpg'  # Default to jpg
    
    # Create the object name (path in the bucket)
    object_name = f"{folder}/{file_id}.{file_extension}"
    
    # Upload to MinIO
    print(f"Uploading file to {object_name}...")
    file_size = len(data)
    
    # Upload the file
    minio_client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        data=io.BytesIO(data),
        length=file_size,
        content_type=content_type
    )
    
    # Create file info for database
    unique_string = file_id[:8]
    
    return {
        "file_id": file_id,
        "filename": filename,
        "file_type": content_type,
        "file_extension": file_extension,
        "size": file_size,
        "object_name": object_name,
        "unique_string": unique_string,
        "uploaded_at": datetime.now(timezone.utc)
    }

def migrate_users(db, minio_client):
    """Migrate user profile pictures from base64 to MinIO"""
    print("Finding users with base64 profile pictures...")
    # Check if the users collection exists
    if 'users' not in db.list_collection_names():
        print("Error: 'users' collection not found in the database")
        return
        
    # Get the users collection and find documents with profile_picture_base64
    users_collection = db['users']
    users = users_collection.find({"profile_picture_base64": {"$exists": True, "$ne": None}})
    count = 0
    
    for user in users:
        try:
            username = user["username"]
            print(f"Processing user: {username}")
            
            # Get the base64 data
            base64_data = user["profile_picture_base64"]
            
            # Skip if empty
            if not base64_data:
                continue
                
            # Parse the base64 string
            match = re.match(r'data:image/(\w+);base64,(.*)', base64_data)
            if not match:
                print(f"Invalid base64 format for user {username}")
                continue
                
            file_extension, base64_str = match.groups()
            content_type = f"image/{file_extension}"
            
            # Decode base64 to binary
            file_content = base64.b64decode(base64_str)
            
            # Create filename
            filename = f"profile-{username}.{file_extension}"
            
            # Upload to MinIO
            file_info = upload_to_minio(
                data=file_content,
                filename=filename,
                content_type=content_type,
                minio_client=minio_client
            )
            
            # Add a slug
            file_info["slug"] = f"profile-{username.lower()}-{file_info['unique_string']}"
            
            # Save file record in database
            db['files'].insert_one(file_info)
            
            # Update user
            db['users'].update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "profile_picture_file": file_info["file_id"],
                        "profile_photo_id": file_info["file_id"]
                    }
                }
            )
            
            count += 1
            print(f"Migrated user {username}")
            
        except Exception as e:
            print(f"Error with user: {str(e)}")
    
    print(f"Completed user migration: {count} users")

def migrate_articles(db, minio_client):
    """Migrate article images from base64 to MinIO"""
    print("Finding articles with base64 images...")
    # Check if the articles collection exists
    if 'articles' not in db.list_collection_names():
        print("Error: 'articles' collection not found in the database")
        return
        
    # Get the articles collection and find documents with images
    articles_collection = db['articles']
    articles = articles_collection.find({"image": {"$exists": True, "$ne": None}})
    count = 0
    
    for article in articles:
        try:
            article_id = article["_id"]
            slug = article["slug"]
            print(f"Processing article: {slug}")
            
            # Get the base64 data
            base64_data = article["image"]
            
            # Skip if empty
            if not base64_data:
                continue
                
            # Parse the base64 string
            match = re.match(r'data:image/(\w+);base64,(.*)', base64_data)
            if not match:
                print(f"Invalid base64 format for article {slug}")
                continue
                
            file_extension, base64_str = match.groups()
            content_type = f"image/{file_extension}"
            
            # Decode base64 to binary
            file_content = base64.b64decode(base64_str)
            
            # Create filename
            filename = f"article-{slug}.{file_extension}"
            
            # Upload to MinIO
            file_info = upload_to_minio(
                data=file_content,
                filename=filename,
                content_type=content_type,
                minio_client=minio_client,
                folder="article_images"
            )
            
            # Add a slug
            file_info["slug"] = f"article-{slug}-{file_info['unique_string']}"
            
            # Save file record in database
            db['files'].insert_one(file_info)
            
            # Update article
            db['articles'].update_one(
                {"_id": article_id},
                {
                    "$set": {
                        "image_file": file_info["file_id"],
                        "image_id": file_info["file_id"]
                    }
                }
            )
            
            count += 1
            print(f"Migrated article {slug}")
            
        except Exception as e:
            print(f"Error with article: {str(e)}")
    
    print(f"Completed article migration: {count} articles")

def simple_test():
    """Simple connection test"""
    try:
        print("Testing MinIO connection...")
        minio_client = connect_to_minio()
        
        # Check bucket
        if not minio_client.bucket_exists(MINIO_BUCKET):
            print(f"Bucket {MINIO_BUCKET} doesn't exist - will create it")
        else:
            print(f"Bucket {MINIO_BUCKET} exists")
            
        return True
    except Exception as e:
        print(f"MinIO test failed: {str(e)}")
        return False

def main():
    """Main function"""
    
    # First do a simple test
    if not simple_test():
        print("Connection test failed. Please check your settings.")
        return
    
    # Connect to databases
    db = connect_to_mongodb()
    minio_client = connect_to_minio()
    
    # Create bucket if it doesn't exist
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
        print(f"Created bucket: {MINIO_BUCKET}")
    
    # Migrate users
    print("\n--- MIGRATING USERS ---")
    migrate_users(db, minio_client)
    
    # Migrate articles
    print("\n--- MIGRATING ARTICLES ---")
    migrate_articles(db, minio_client)
    
    print("\nMigration complete!")

if __name__ == "__main__":
    main()