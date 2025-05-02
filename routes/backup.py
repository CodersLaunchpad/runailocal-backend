from fastapi import APIRouter, Depends, HTTPException, UploadFile, status, BackgroundTasks, Query
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
from typing import Optional, Any, Dict, Tuple
import tempfile
from bson import ObjectId
import asyncio

# Constants
CHECKSUMS_FILENAME = 'checksums.json'
MONGODB_BACKUP_FILENAME = 'mongodb_backup.json'
MINIO_BACKUP_FILENAME = 'minio_backup.zip'
DEFAULT_TIMEOUT = 300  # 5 minutes timeout for operations

router = APIRouter()

class MongoDBEncoder(json.JSONEncoder):
    """JSON encoder for MongoDB specific types"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

# ----- Utility Functions -----

async def calculate_checksum(data: bytes) -> str:
    """Calculate SHA-256 checksum of data"""
    return hashlib.sha256(data).hexdigest()

async def execute_with_timeout(coro, timeout=DEFAULT_TIMEOUT):
    """Execute a coroutine with a timeout"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Operation timed out after {timeout} seconds"
        )

def generate_backup_paths(timestamp: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Generate backup filename and paths.
    Returns (backup_filename, absolute_path, relative_path)
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_filename = f"backup_{timestamp}.zip"
    relative_path = backup_filename.replace('\\', '/')
    absolute_path = os.path.abspath(os.path.join(settings.BACKUP_DIR, backup_filename)).replace('\\', '/')
    
    return backup_filename, absolute_path, relative_path

def resolve_backup_path(stored_path: str) -> Tuple[str, str]:
    """
    Resolve a stored backup path to absolute path and filename.
    Returns (absolute_path, backup_filename)
    """
    if not stored_path:
        return None, None
        
    # Convert stored path to absolute path if it's relative
    if not os.path.isabs(stored_path):
        absolute_path = os.path.abspath(os.path.join(settings.BACKUP_DIR, stored_path))
    else:
        absolute_path = stored_path
    
    # Normalize path to use forward slashes
    absolute_path = absolute_path.replace('\\', '/')
    backup_filename = os.path.basename(absolute_path)
    
    return absolute_path, backup_filename

# ----- Database Operations -----

async def get_last_backup_checksums(db) -> Dict[str, Any]:
    """Retrieve the checksums of the last backup from the database"""
    try:
        backup_info = await db.backups.find_one({}, sort=[("timestamp", -1)])
        if not backup_info:
            return {}
        return {
            "mongo_checksum": backup_info.get("mongo_checksum"),
            "minio_checksum": backup_info.get("minio_checksum"),
            "combined_checksum": backup_info.get("combined_checksum")
        }
    except Exception as e:
        return {}

async def get_backup_by_mongo_checksum(db, mongo_checksum: str) -> Optional[Dict[str, Any]]:
    """Find a backup record by MongoDB checksum"""
    try:
        return await db.backups.find_one({"mongo_checksum": mongo_checksum}, sort=[("timestamp", -1)])
    except Exception as e:
        return None

async def store_backup_info(db, mongo_checksum: str, minio_checksum: str, combined_checksum: str, relative_path: str, absolute_path: str) -> None:
    """Store backup checksums and paths in the database for future reference"""
    try:
        await db.backups.insert_one({
            "timestamp": datetime.now(),
            "mongo_checksum": mongo_checksum,
            "minio_checksum": minio_checksum, 
            "combined_checksum": combined_checksum,
            "relative_path": relative_path,
            "absolute_path": absolute_path
        })
        print(f"Stored backup info: {mongo_checksum[:8]}..., {minio_checksum[:8]}...")
    except Exception as e:
        print(f"Error storing backup info: {str(e)}")
        raise e

# ----- Backup Operations -----

async def backup_mongodb(db) -> bytes:
    """Backup MongoDB collections to JSON"""
    try:
        collections = await db.list_collection_names()
        collections = sorted(collections) # Sort collections for consistent ordering
        backup_data = {}
        
        for collection_name in collections:
            # Skip system collections and the backups collection
            if collection_name.startswith('system.') or collection_name == 'backups':
                continue
                
            collection = db[collection_name]
            documents = await collection.find({}).to_list(length=None)

            # Sort documents by _id for consistent ordering
            documents = sorted(documents, key=lambda x: str(x.get('_id', '')))
            backup_data[collection_name] = documents
        
        # Use a deterministic JSON format (sorted keys, fixed indentation)
        return json.dumps(backup_data, sort_keys=True, indent=2, cls=MongoDBEncoder).encode('utf-8')
    except Exception as e:
        raise e

async def backup_minio(minio_client: Minio) -> bytes:
    """Backup MinIO bucket contents"""
    bucket_name = settings.MINIO_BUCKET
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_path = temp_file.name
    temp_file.close()  # Close the file so we can use it with ZipFile
    
    try:
        # Create zip file
        with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for obj in minio_client.list_objects(bucket_name, recursive=True):
                try:
                    data = minio_client.get_object(bucket_name, obj.object_name)
                    zipf.writestr(obj.object_name, data.read())
                    data.close()  # Close the MinIO object
                except Exception as e:
                    print(f"Error backing up {obj.object_name}: {str(e)}")
                    raise e
        
        # Read the zip file contents
        with open(temp_path, 'rb') as f:
            backup_data = f.read()
        
        return backup_data
    
    except Exception as e:
        print(f"Error in MinIO backup: {str(e)}")
        raise e
    
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            print(f"Warning: Could not delete temporary file {temp_path}: {str(e)}")

async def create_backup_zip(mongo_data: bytes, minio_data: bytes) -> Tuple[io.BytesIO, str, str, str]:
    """
    Create a ZIP file containing all backup data and checksums.
    Returns the zip buffer, mongo_checksum, minio_checksum, and combined_checksum.
    """
    # Calculate checksums
    mongo_checksum = await calculate_checksum(mongo_data)
    minio_checksum = await calculate_checksum(minio_data)
    combined_checksum = await calculate_checksum(mongo_checksum.encode() + minio_checksum.encode())
    
    # Create zip file with NO compression to ensure binary consistency
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zipf:
        # Set fixed timestamps for all files (Jan 1, 2025)
        fixed_date = (2025, 1, 1, 0, 0, 0)
        
        # Create a ZipInfo object for each file with fixed metadata
        mongo_info = zipfile.ZipInfo(MONGODB_BACKUP_FILENAME, fixed_date)
        minio_info = zipfile.ZipInfo(MINIO_BACKUP_FILENAME, fixed_date)
        checksum_info = zipfile.ZipInfo(CHECKSUMS_FILENAME, fixed_date)
        
        # Write the files using ZipInfo to control all metadata
        zipf.writestr(mongo_info, mongo_data)
        zipf.writestr(minio_info, minio_data)

        # Include the checksums in a metadata file
        metadata = {
            "mongo_checksum": mongo_checksum,
            "minio_checksum": minio_checksum,
            "combined_checksum": combined_checksum,
        }

        # Use a deterministic JSON format (sorted keys, no whitespace)
        json_data = json.dumps(metadata, sort_keys=True, separators=(',', ':'))
        zipf.writestr(checksum_info, json_data.encode('utf-8'))
    
    zip_buffer.seek(0)
    return zip_buffer, mongo_checksum, minio_checksum, combined_checksum

# ----- Verification Operations -----

async def extract_checksums_from_zip(content_bytes: bytes) -> Dict[str, str]:
    """Extract checksums from a backup ZIP file"""
    try:
        with zipfile.ZipFile(io.BytesIO(content_bytes)) as zipf:
            if CHECKSUMS_FILENAME in zipf.namelist():
                metadata = json.loads(zipf.read(CHECKSUMS_FILENAME).decode('utf-8'))
                return {
                    "mongo_checksum": metadata.get('mongo_checksum'),
                    "minio_checksum": metadata.get('minio_checksum'),
                    "combined_checksum": metadata.get('combined_checksum')
                }
    except (KeyError, zipfile.BadZipFile):
        # These are expected cases when the file isn't a zip or doesn't contain checksums
        return {}
    except Exception as e:
        # Only print unexpected errors
        print(f"Unexpected error extracting checksums: {str(e)}")
        return {}

async def verify_zip_contents(zipf, expected_checksums: Dict[str, str]) -> Dict[str, Any]:
    """Verify the contents of a backup ZIP file against expected checksums"""
    try:
        # Verify MongoDB backup
        mongo_data = zipf.read(MONGODB_BACKUP_FILENAME)
        mongo_checksum = await calculate_checksum(mongo_data)
        
        if mongo_checksum != expected_checksums.get("mongo_checksum"):
            return {
                "status": "failed",
                "message": "MongoDB checksum mismatch",
                "expected": expected_checksums.get("mongo_checksum"),
                "actual": mongo_checksum
            }
        
        # If MongoDB checksum matches, verify MinIO
        minio_data = zipf.read(MINIO_BACKUP_FILENAME)
        minio_checksum = await calculate_checksum(minio_data)
        
        if minio_checksum != expected_checksums.get("minio_checksum"):
            return {
                "status": "failed",
                "message": "MinIO checksum mismatch",
                "expected": expected_checksums.get("minio_checksum"),
                "actual": minio_checksum
            }
        
        # Calculate combined checksum
        combined_checksum = await calculate_checksum(mongo_checksum.encode() + minio_checksum.encode())
        
        if expected_checksums.get("combined_checksum") and combined_checksum != expected_checksums.get("combined_checksum"):
            return {
                "status": "failed",
                "message": "Combined checksum mismatch",
                "expected": expected_checksums.get("combined_checksum"),
                "actual": combined_checksum
            }
        
        return {
            "status": "success",
            "message": "Backup verification successful",
            "checksum": combined_checksum
        }
    except KeyError as e:
        return {
            "status": "failed",
            "message": f"Missing file in backup: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error verifying backup: {str(e)}"
        }

# ----- Route Handlers -----

@router.get("/", response_description="Create and download a complete backup")
async def create_backup(
    background_tasks: BackgroundTasks,
    timeout: Optional[int] = Query(DEFAULT_TIMEOUT, description="Operation timeout in seconds"),
    db = Depends(get_db),
    minio_client: Minio = Depends(get_object_storage)
):
    try:
        # Get last backup checksums
        last_backup = await db.backups.find_one({}, sort=[("timestamp", -1)])
        
        # Create the MongoDB backup (excluding the backups collection)
        mongo_data = await execute_with_timeout(backup_mongodb(db), timeout)
        mongo_checksum = await calculate_checksum(mongo_data)
        
        # Check if MongoDB has changed
        if last_backup and mongo_checksum == last_backup.get("mongo_checksum"):
            # MongoDB hasn't changed, use the previous backup
            stored_path = last_backup.get("relative_path")
            absolute_path, backup_filename = resolve_backup_path(stored_path)
            
            if absolute_path and os.path.exists(absolute_path):
                # Read the existing backup file
                with open(absolute_path, 'rb') as f:
                    backup_data = f.read()
                
                return StreamingResponse(
                    io.BytesIO(backup_data),
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={backup_filename}",
                        "Content-Length": str(len(backup_data)),
                        "X-Backup-Checksum": last_backup.get("combined_checksum")
                    }
                )
        
        # If we get here, we need to create a new backup
        backup_filename, absolute_path, relative_path = generate_backup_paths()
        
        minio_data = await execute_with_timeout(backup_minio(minio_client), timeout)
        minio_checksum = await calculate_checksum(minio_data)
        combined_checksum = await calculate_checksum(mongo_checksum.encode() + minio_checksum.encode())
        
        # Create zip file with fixed metadata
        zip_buffer, _, _, combined_checksum = await create_backup_zip(mongo_data, minio_data)
        zip_size = len(zip_buffer.getvalue())
        zip_buffer.seek(0)
        
        # Ensure backup directory exists and store the backup file
        os.makedirs(settings.BACKUP_DIR, exist_ok=True)
        with open(absolute_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        # Store new backup info with relative path and absolute path
        background_tasks.add_task(
            store_backup_info, db, mongo_checksum, minio_checksum, combined_checksum, relative_path, absolute_path
        )
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={backup_filename}",
                "Content-Length": str(zip_size),
                "X-Backup-Checksum": combined_checksum
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating backup: {str(e)}"
        )

@router.post("/verify", response_description="Verify a backup file")
async def verify_backup(
    backup_file: UploadFile,
    background_tasks: BackgroundTasks,
    expected_checksum: Optional[str] = None,
    quick_verify: bool = Query(True, description="Use fast verification if possible"),
    db = Depends(get_db)
):
    """
    Verify the integrity of a backup file.
    
    When quick_verify=True (default), the verification will first try to match the backup's
    checksum against previously verified backups to avoid reading the full contents.
    If no match is found or quick_verify=False, the verification process will read and
    verify the actual file contents.
    """
    try:
        # Read initial portion of the file to extract checksums
        content_bytes = await backup_file.read(1024 * 1024)  # Read first MB
        
        # Try to extract checksums from the first MB
        checksums = await extract_checksums_from_zip(content_bytes)
        
        # If checksums not found in first MB, read more data
        if not checksums:
            # Reset position and read the whole file
            await backup_file.seek(0)
            full_content = await backup_file.read()
            
            checksums = await extract_checksums_from_zip(full_content)
            
            # If still no checksums, verify whole file
            if not checksums:
                actual_checksum = await calculate_checksum(full_content)
                
                if expected_checksum and actual_checksum != expected_checksum:
                    return {
                        "status": "failed",
                        "message": "Checksum mismatch (whole file)",
                        "expected": expected_checksum,
                        "actual": actual_checksum
                    }
                
                return {
                    "status": "success",
                    "message": "Backup verification successful (whole file)",
                    "checksum": actual_checksum
                }
        
        # If expected_checksum is provided, verify against it first
        if expected_checksum:
            if checksums.get("combined_checksum") and checksums["combined_checksum"] != expected_checksum:
                return {
                    "status": "failed",
                    "message": "Checksum mismatch (checked against expected checksum)",
                    "expected": expected_checksum,
                    "actual": checksums["combined_checksum"]
                }
        
        # Quick verification using stored checksums if possible
        if quick_verify:
            existing_backup = await get_backup_by_mongo_checksum(db, checksums.get("mongo_checksum", ""))
            
            if existing_backup and existing_backup.get("combined_checksum") == checksums.get("combined_checksum"):
                # No need to create a new record, just return success
                return {
                    "status": "success",
                    "message": "Backup verification successful (using fast verification)",
                    "checksum": checksums.get("combined_checksum")
                }
        
        # Need to verify by reading actual content
        await backup_file.seek(0)
        full_content = await backup_file.read()
        
        with zipfile.ZipFile(io.BytesIO(full_content)) as zipf:
            verification_result = await verify_zip_contents(zipf, checksums)
            
            # Only store new backup info if this is a new backup (not found in quick verify)
            if verification_result["status"] == "success":
                _, absolute_path, relative_path = generate_backup_paths()
                
                # Double check we don't already have this backup
                existing_backup = await get_backup_by_mongo_checksum(db, checksums.get("mongo_checksum", ""))
                if not existing_backup or existing_backup.get("combined_checksum") != checksums.get("combined_checksum"):
                    background_tasks.add_task(
                        store_backup_info,
                        db, 
                        checksums.get("mongo_checksum", ""), 
                        checksums.get("minio_checksum", ""), 
                        verification_result["checksum"],
                        relative_path,
                        absolute_path
                    )
            
            return verification_result
    
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid ZIP file"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying backup: {str(e)}"
        )