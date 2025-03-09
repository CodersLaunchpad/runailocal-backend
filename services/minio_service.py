# app/services/minio_service.py
from fastapi import UploadFile, HTTPException, status
from minio import Minio
import io
import uuid
from datetime import datetime, timedelta
import base64
from db.db import get_db
from config import settings  # Import your settings

# Global minio client - will be initialized by get_object_storage
minio_client = None

async def upload_profile_picture(profile_picture: UploadFile, username: str, minio_client: Minio) -> dict:
    """
    Upload a profile picture to MinIO and save record to MongoDB
    Returns the file record with ID and URL
    """
    try:
        # Read file content
        content = await profile_picture.read()
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        
        # Get file extension
        filename = profile_picture.filename
        file_extension = filename.split('.')[-1] if '.' in filename and '.' in filename.split('/')[-1] else "jpg"
        
        # Create object name (path in MinIO)
        object_name = f"profile_photos/{file_id}.{file_extension}"
        
        # Upload to MinIO
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=io.BytesIO(content),
            length=len(content),
            content_type=profile_picture.content_type or f"image/{file_extension}"
        )
        
        # Generate URL
        file_url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(hours=1)
        )
        
        # Create file record
        file_record = {
            "file_id": file_id,
            "filename": f"{username}-profile.{file_extension}",
            "file_type": profile_picture.content_type or f"image/{file_extension}",
            "file_extension": file_extension,
            "file_url": file_url,
            "slug": f"profile-{username}",
            "size": len(content),
            "object_name": object_name,
            "uploaded_at": datetime.utcnow()
        }
        
        # Save to MongoDB
        db = await get_db()
        await db["files"].insert_one(file_record)
        
        # Reset file pointer
        await profile_picture.seek(0)
        
        return file_record
    
    except Exception as e:
        print(f"Error uploading profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to upload profile picture: {str(e)}"
        )

async def upload_base64_profile_picture(base64_data: str, username: str, minio_client: Minio) -> dict:
    """
    Upload a base64 encoded profile picture
    Returns the file record with ID and URL
    """
    try:
        # Clean up base64 data
        if "base64," in base64_data:
            content_type = base64_data.split(';')[0].split(':')[1] if ';base64,' in base64_data else "image/jpeg"
            base64_data = base64_data.split("base64,")[1]
        else:
            content_type = "image/jpeg"
        
        # Decode base64
        image_data = base64.b64decode(base64_data)
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        
        # Get file extension from content type
        file_extension = content_type.split('/')[-1] if '/' in content_type else "jpg"
        
        # Create object name
        object_name = f"profile_photos/{file_id}.{file_extension}"
        
        # Upload to MinIO
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=io.BytesIO(image_data),
            length=len(image_data),
            content_type=content_type
        )
        
        # Generate URL
        file_url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(hours=1)
        )
        
        # Create file record
        file_record = {
            "file_id": file_id,
            "filename": f"{username}-profile.{file_extension}",
            "file_type": content_type,
            "file_extension": file_extension,
            "file_url": file_url,
            "slug": f"profile-{username}",
            "size": len(image_data),
            "object_name": object_name,
            "uploaded_at": datetime.utcnow()
        }
        
        # Save to MongoDB
        db = await get_db()
        await db["files"].insert_one(file_record)
        
        return file_record
    
    except Exception as e:
        print(f"Error uploading base64 profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile picture: {str(e)}"
        )

async def get_file_by_id(file_id: str):
    """Get a file record by ID"""
    db = await get_db()
    return await db["files"].find_one({"file_id": file_id})