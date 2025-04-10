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
from typing import Optional
import tempfile

router = APIRouter()

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
        # Convert ObjectId to string for JSON serialization
        for doc in documents:
            doc['_id'] = str(doc['_id'])
        backup_data[collection_name] = documents
    
    return json.dumps(backup_data, indent=2).encode('utf-8')

async def backup_minio(minio_client: Minio) -> bytes:
    """Backup MinIO bucket contents"""
    bucket_name = settings.MINIO_BUCKET
    objects = minio_client.list_objects(bucket_name, recursive=True)
    
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for obj in objects:
                try:
                    data = minio_client.get_object(bucket_name, obj.object_name)
                    zipf.writestr(obj.object_name, data.read())
                except Exception as e:
                    print(f"Error backing up {obj.object_name}: {str(e)}")
        
        with open(temp_file.name, 'rb') as f:
            backup_data = f.read()
        
        os.unlink(temp_file.name)
        return backup_data

@router.get("/backup")
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
            # Backup MongoDB
            mongo_data = await backup_mongodb(db)
            zipf.writestr('mongodb_backup.json', mongo_data)
            
            # Backup MinIO
            minio_data = await backup_minio(minio_client)
            zipf.writestr('minio_backup.zip', minio_data)
            
            # Add checksum file
            zip_buffer.seek(0)
            checksum = await calculate_checksum(zip_buffer.getvalue())
            zipf.writestr('checksum.txt', checksum)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={backup_filename}",
                "X-Backup-Checksum": checksum
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating backup: {str(e)}"
        )

@router.get("/backup/verify")
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