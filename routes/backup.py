from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from db.db import get_db, get_object_storage
from minio import Minio
from datetime import datetime
import os
import io
import zipfile
import hashlib
import json
from config import settings
import asyncio
from typing import Optional, Any
import tempfile
from bson import ObjectId

router = APIRouter()

class MongoDBEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

async def calculate_checksum(data: bytes) -> str:
    """Calculate SHA-256 checksum of data"""
    return hashlib.sha256(data).hexdigest()

async def backup_mongodb(db) -> bytes:
    """Backup MongoDB collections to JSON"""
    collections = await db.list_collection_names()
    backup_data = {}
    
    for collection_name in collections:
        if collection_name.startswith('system.'):
            continue
            
        collection = db[collection_name]
        documents = await collection.find({}).to_list(length=None)
        backup_data[collection_name] = documents
    
    return json.dumps(backup_data, indent=2, cls=MongoDBEncoder).encode('utf-8')

async def backup_minio(minio_client: Minio) -> bytes:
    """Backup MinIO bucket contents"""
    bucket_name = settings.MINIO_BUCKET
    objects = minio_client.list_objects(bucket_name, recursive=True)
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_path = temp_file.name
    temp_file.close()  # Close the file so we can use it with ZipFile
    
    try:
        # Create zip file
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for obj in objects:
                try:
                    data = minio_client.get_object(bucket_name, obj.object_name)
                    zipf.writestr(obj.object_name, data.read())
                    data.close()  # Close the MinIO object
                except Exception as e:
                    print(f"Error backing up {obj.object_name}: {str(e)}")
        
        # Read the zip file contents
        with open(temp_path, 'rb') as f:
            backup_data = f.read()
        
        return backup_data
    
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_path}: {str(e)}")

@router.get("/")
async def create_backup(
    db = Depends(get_db),
    minio_client: Minio = Depends(get_object_storage)
):
    """Create a complete backup of MongoDB and MinIO data"""
    try:
        # Create timestamp for backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.zip"
        
        # Create in-memory zip file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            try:
                # Backup MongoDB
                print("Starting MongoDB backup...")
                mongo_data = await backup_mongodb(db)
                zipf.writestr('mongodb_backup.json', mongo_data)
                print("MongoDB backup completed successfully")
            except Exception as e:
                print(f"Error during MongoDB backup: {str(e)}")
                raise
            
            try:
                # Backup MinIO
                print("Starting MinIO backup...")
                minio_data = await backup_minio(minio_client)
                zipf.writestr('minio_backup.zip', minio_data)
                print("MinIO backup completed successfully")
            except Exception as e:
                print(f"Error during MinIO backup: {str(e)}")
                raise
            
            try:
                # Add checksum file
                print("Calculating checksum...")
                zip_buffer.seek(0)
                checksum = await calculate_checksum(zip_buffer.getvalue())
                zipf.writestr('checksum.txt', checksum)
                print("Checksum calculation completed")
            except Exception as e:
                print(f"Error during checksum calculation: {str(e)}")
                raise
        
        # Reset buffer position and get the size
        zip_buffer.seek(0)
        zip_size = len(zip_buffer.getvalue())
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={backup_filename}",
                "Content-Length": str(zip_size),
                "X-Backup-Checksum": checksum
            }
        )
    
    except Exception as e:
        print(f"Backup failed with error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating backup: {str(e)}"
        )

@router.get("/verify")
async def verify_backup(
    backup_file: bytes,
    expected_checksum: Optional[str] = None
):
    """Verify the integrity of a backup file"""
    try:
        # Calculate checksum of the provided backup file
        actual_checksum = await calculate_checksum(backup_file)
        
        if expected_checksum and actual_checksum != expected_checksum:
            return {
                "status": "failed",
                "message": "Checksum mismatch",
                "expected": expected_checksum,
                "actual": actual_checksum
            }
        
        return {
            "status": "success",
            "message": "Backup verification successful",
            "checksum": actual_checksum
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying backup: {str(e)}"
        ) 