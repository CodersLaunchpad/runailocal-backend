# app/services/minio_service.py
from typing import Any, Dict, Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from minio import Minio
import io
import uuid
from datetime import datetime, timezone
import base64
import re
from db.db import get_db
from config import settings
from PIL import Image
import os

# Global minio client - will be initialized by get_object_storage
minio_client = None

async def process_image(image_data: bytes, max_size: Tuple[int, int] = (1920, 1080), quality: int = 85) -> Tuple[bytes, str]:
    """
    Process and compress an image, converting it to WebP format
    
    Args:
        image_data: Raw image data in bytes
        max_size: Maximum dimensions (width, height)
        quality: Compression quality (1-100)
    
    Returns:
        Tuple of (processed_image_bytes, content_type)
    """
    try:
        print(f"[Image Processing] Starting image processing...")
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
        print(f"[Image Processing] Original image size: {image.size}, mode: {image.mode}")
        
        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA'):
            print(f"[Image Processing] Converting from {image.mode} to RGB with white background")
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            print(f"[Image Processing] Converting from {image.mode} to RGB")
            image = image.convert('RGB')
        
        # Resize if larger than max_size while maintaining aspect ratio
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            print(f"[Image Processing] Resizing image from {image.size} to max {max_size}")
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save as WebP
        print(f"[Image Processing] Converting to WebP format with quality {quality}")
        output = io.BytesIO()
        image.save(output, format='WEBP', quality=quality, optimize=True)
        processed_data = output.getvalue()
        print(f"[Image Processing] Successfully converted to WebP. New size: {len(processed_data)} bytes")
        
        return processed_data, 'image/webp'
        
    except Exception as e:
        print(f"[Image Processing] Error processing image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process image: {str(e)}"
        )

async def upload_to_minio(
    data: bytes, 
    filename: str, 
    content_type: str, 
    minio_client: Minio,
    folder: str = "profile_photos"
) -> Dict[str, Any]:
    """
    Common function to upload any data to MinIO
    
    Args:
        data: The file content as bytes
        filename: Original filename or generated name
        content_type: MIME type of the file
        minio_client: MinIO client instance
        folder: The folder path in the bucket
    
    Returns:
        Dict with file metadata and MinIO information
    """
    try:
        print(f"[MinIO Upload] Starting upload process for file: {filename}")
        print(f"[MinIO Upload] Content type: {content_type}")
        print(f"[MinIO Upload] Original file size: {len(data)} bytes")
        
        # Process image if it's an image file
        if content_type.startswith('image/'):
            print(f"[MinIO Upload] Detected image file, proceeding with image processing")
            processed_data, content_type = await process_image(data)
            data = processed_data
            # Change extension to webp
            filename = os.path.splitext(filename)[0] + '.webp'
            print(f"[MinIO Upload] Image processed successfully. New filename: {filename}")
        else:
            print(f"[MinIO Upload] Not an image file, skipping processing")
        
        # Generate file ID and get extension
        file_id = str(uuid.uuid4())
        file_extension = filename.split('.')[-1].lower()
        print(f"[MinIO Upload] Generated file_id: {file_id}")
        
        # Setup bucket info
        bucket_name = settings.MINIO_BUCKET
        object_name = f"{folder}/{file_id}.{file_extension}"
        print(f"[MinIO Upload] Will upload to bucket: {bucket_name}, object: {object_name}")
        
        # Upload to MinIO
        file_size = len(data)
        print(f"[MinIO Upload] Uploading file of size: {file_size} bytes")
        minio_client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(data),
            length=file_size,
            content_type=content_type
        )
        print(f"[MinIO Upload] Successfully uploaded to MinIO")
        
        # Generate a unique string for the slug
        unique_string = file_id[:8]  # Using first 8 chars of UUID for uniqueness
        print(f"[MinIO Upload] Generated unique string: {unique_string}")
            
        # Return file information
        return {
            "file_id": file_id,
            "filename": filename,
            "file_type": content_type,
            "file_extension": file_extension,
            "size": file_size,
            "object_name": object_name,
            "unique_string": unique_string,
        }
        
    except Exception as e:
        print(f"[MinIO Upload] Error uploading to MinIO: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to upload file: {str(e)}"
        )


async def upload_profile_picture(profile_picture: UploadFile, username: str, minio_client: Minio) -> Dict[str, Any]:
    """
    Upload a profile picture to MinIO and create a file record
    
    Returns the created file record including file_id, slug, etc.
    """
    try:
        # Validate image type
        content_type = profile_picture.content_type
        if not content_type or not content_type.startswith('image/'):
            raise ValueError("Uploaded file must be an image")
        
        # Read file content
        file_content = await profile_picture.read()
        
        # Use common upload function
        file_info = await upload_to_minio(
            data=file_content,
            filename=profile_picture.filename,
            content_type=content_type,
            minio_client=minio_client
        )
        
        # Create a unique slug using username and the unique string
        file_info["slug"] = f"profile-{username.lower()}-{file_info['unique_string']}"
        file_info["uploaded_at"] = datetime.now(timezone.utc)
        
        # Save to database
        db = await get_db()
        file_collection = db.files
        await file_collection.insert_one(file_info)
        
        return file_info
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error uploading profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Failed to upload profile picture: {str(e)}"
        )


async def upload_base64_profile_picture(base64_data: str, username: str, minio_client: Minio) -> Dict[str, Any]:
    """
    Upload a base64 encoded profile picture to MinIO and create a file record
    
    Returns the created file record including file_id, slug, etc.
    """
    try:
        # Parse the base64 data
        match = re.match(r'data:image/(\w+);base64,(.*)', base64_data)
        if not match:
            raise ValueError("Invalid base64 image format")
        
        file_extension, base64_str = match.groups()
        
        # Convert to bytes
        try:
            file_content = base64.b64decode(base64_str)
        except Exception:
            raise ValueError("Invalid base64 encoding")
        
        # Generate filename
        filename = f"avatar-{username}.{file_extension}"
        content_type = f"image/{file_extension}"
        
        # Use common upload function
        file_info = await upload_to_minio(
            data=file_content,
            filename=filename,
            content_type=content_type,
            minio_client=minio_client
        )
        
        # Create a unique slug using username and the unique string
        file_info["slug"] = f"profile-{username.lower()}-{file_info['unique_string']}"
        file_info["uploaded_at"] = datetime.now(timezone.utc)
        
        # Save to database
        db = await get_db()
        file_collection = db.files
        await file_collection.insert_one(file_info)
        
        return file_info
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Error uploading base64 profile picture: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile picture: {str(e)}"
        )


async def get_file_by_id(file_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a file record by its file_id
    """
    try:
        db = await get_db()
        file_collection = db.files
        file_record = await file_collection.find_one({"file_id": file_id})
        return file_record
    except Exception as e:
        print(f"Error retrieving file: {str(e)}")
        return None