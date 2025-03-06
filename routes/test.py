from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, Response
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse
from minio import Minio
from minio.error import S3Error
import os
import io
import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import motor.motor_asyncio
import pymongo
import re
import unicodedata

# Create router instead of app
router = APIRouter()

# MinIO client configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uploads")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

# MongoDB configuration
MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("DATABASE_NAME", "file_storage")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "files")

# Initialize MinIO client
def get_minio_client():
    return Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE
    )

# Initialize MongoDB client
def get_mongo_client():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client[MONGO_DB]
    return db[MONGO_COLLECTION]

# Custom slug creation function
def create_slug(text):
    """
    Create a URL-friendly slug from the given text.
    
    Args:
        text: The text to convert to a slug
    
    Returns:
        A lowercase string with spaces and special chars replaced by hyphens
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', str(text))
    
    # Replace non-alphanumeric characters with hyphens
    text = re.sub(r'[^\w\s-]', '-', text.lower())
    
    # Replace whitespace with hyphens
    text = re.sub(r'[\s]+', '-', text)
    
    # Replace multiple hyphens with a single hyphen
    text = re.sub(r'[-]+', '-', text)
    
    # Remove leading/trailing hyphens
    return text.strip('-')

# Function to ensure bucket exists - call this when including the router
def ensure_minio_bucket():
    client = get_minio_client()
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            print(f"Created bucket {MINIO_BUCKET}")
        return True
    except S3Error as err:
        print(f"Error initializing MinIO bucket: {err}")
        return False

# Function to ensure MongoDB collection has proper indexes
async def ensure_mongodb_indexes():
    collection = get_mongo_client()
    await collection.create_index([("file_id", pymongo.ASCENDING)], unique=True)
    await collection.create_index([("slug", pymongo.ASCENDING)])
    print(f"Ensured MongoDB indexes for {MONGO_COLLECTION}")

class UploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    object_name: str
    url: Optional[str] = None
    file_id: str
    slug: str
    uploaded_at: datetime

# Function to generate unique file ID
async def generate_unique_file_id(collection):
    """
    Generate a unique file ID that doesn't exist in MongoDB.
    
    Args:
        collection: MongoDB collection to check against
    
    Returns:
        Unique file ID string
    """
    while True:
        file_id = str(uuid.uuid4())
        # Check if this ID already exists in MongoDB
        existing = await collection.find_one({"file_id": file_id})
        if not existing:
            return file_id

# Separate function for saving files to MinIO
async def save_file_to_minio(
    file: UploadFile,
    file_id: str,
    folder: str = "",
    client: Minio = None
) -> Dict[str, Any]:
    """
    Upload a file to MinIO using a pre-generated file ID and return metadata.
    
    Args:
        file: The file to upload
        file_id: Unique file identifier
        folder: Optional folder path within the bucket
        client: MinIO client instance
    
    Returns:
        Dictionary with file metadata including URL
    
    Raises:
        S3Error: If there's an issue with the MinIO upload
    """
    if client is None:
        client = get_minio_client()
    
    # Get file details
    content_type = file.content_type or "application/octet-stream"
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
    
    # Use the file_id as part of the object name
    object_name = f"{folder}/{file_id}{file_extension}" if folder else f"{file_id}{file_extension}"
    object_name = object_name.lstrip("/")
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Upload to MinIO
    client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        data=io.BytesIO(content),
        length=file_size,
        content_type=content_type
    )
    
    # Generate pre-signed URL for accessing the file
    url = client.presigned_get_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        expires=timedelta(hours=1)
    )
    
    # Create a slug from the filename using our custom function
    slug = create_slug(os.path.splitext(file.filename)[0])
    
    # Get the current timestamp
    uploaded_at = datetime.utcnow()
    
    return {
        "filename": file.filename,
        "size": file_size,
        "content_type": content_type,
        "object_name": object_name,
        "url": url,
        "file_id": file_id,
        "slug": slug,
        "uploaded_at": uploaded_at,
        "file_extension": file_extension.lstrip('.')
    }

# Function to store file metadata in MongoDB
async def store_file_metadata_in_mongodb(
    file_data: Dict[str, Any],
    collection = None
) -> Dict[str, Any]:
    """
    Store file metadata in MongoDB.
    
    Args:
        file_data: Dictionary containing file metadata
        collection: MongoDB collection to use
    
    Returns:
        Stored document with MongoDB _id
    
    Raises:
        HTTPException: If there's an issue with MongoDB operations
    """
    if collection is None:
        collection = get_mongo_client()
    
    try:
        # Extract the relevant metadata to store
        metadata = {
            "file_id": str(file_data["file_id"]),
            "filename": str(file_data["filename"]),
            "file_type": str(file_data["content_type"]),
            "file_extension": str(file_data["file_extension"]),
            "file_url": str(file_data["url"]),
            "slug": str(file_data["slug"]),
            "uploaded_at": file_data["uploaded_at"],
            "size": file_data["size"],
            "object_name": str(file_data["object_name"])
        }
        
        # Insert the document
        result = await collection.insert_one(metadata)
        
        # Ensure the document was inserted
        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store file metadata in MongoDB"
            )
        
        # Return the metadata with the MongoDB _id
        metadata["_id"] = str(result.inserted_id)
        return metadata
    
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File ID {file_data['file_id']} already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MongoDB error: {str(e)}"
        )

@router.post("/upload/", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "",
    minio_client: Minio = Depends(get_minio_client)
):
    try:
        # Get MongoDB collection
        mongo_collection = get_mongo_client()
        
        # Generate a unique file ID
        file_id = await generate_unique_file_id(mongo_collection)
        
        # Upload file to MinIO
        file_data = await save_file_to_minio(file, file_id, folder, minio_client)
        
        # Store metadata in MongoDB
        await store_file_metadata_in_mongodb(file_data, mongo_collection)
        
        return UploadResponse(**file_data)
    
    except S3Error as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MinIO S3 error: {err}"
        )
    finally:
        await file.close()

@router.post("/upload-multiple/", response_model=List[UploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    folder: str = "",
    minio_client: Minio = Depends(get_minio_client)
):
    responses = []
    mongo_collection = get_mongo_client()
    
    for file in files:
        try:
            # Generate a unique file ID
            file_id = await generate_unique_file_id(mongo_collection)
            
            # Upload file to MinIO
            file_data = await save_file_to_minio(file, file_id, folder, minio_client)
            
            # Store metadata in MongoDB
            await store_file_metadata_in_mongodb(file_data, mongo_collection)
            
            responses.append(UploadResponse(**file_data))
        
        except S3Error as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"MinIO S3 error on file {file.filename}: {err}"
            )
        finally:
            await file.close()
    
    return responses

# Health check endpoint
@router.get("/health")
async def health_check(
    minio_client: Minio = Depends(get_minio_client)
):
    status_results = {
        "minio": {"status": "unknown"},
        "mongodb": {"status": "unknown"}
    }
    
    # Check MinIO connection
    try:
        if minio_client.bucket_exists(MINIO_BUCKET):
            status_results["minio"] = {
                "status": "healthy", 
                "message": f"Connected to MinIO, bucket '{MINIO_BUCKET}' exists"
            }
        else:
            status_results["minio"] = {
                "status": "warning", 
                "message": f"Connected to MinIO, but bucket '{MINIO_BUCKET}' does not exist"
            }
    except S3Error as err:
        status_results["minio"] = {
            "status": "unhealthy", 
            "message": f"MinIO connection error: {err}"
        }
    
    # Check MongoDB connection
    try:
        mongo_collection = get_mongo_client()
        count = await mongo_collection.count_documents({})
        status_results["mongodb"] = {
            "status": "healthy",
            "message": f"Connected to MongoDB, collection has {count} documents"
        }
    except Exception as e:
        status_results["mongodb"] = {
            "status": "unhealthy",
            "message": f"MongoDB connection error: {str(e)}"
        }
    
    # Overall status is the worst of the individual statuses
    if "unhealthy" in [status_results["minio"]["status"], status_results["mongodb"]["status"]]:
        status_results["overall"] = "unhealthy"
    elif "warning" in [status_results["minio"]["status"], status_results["mongodb"]["status"]]:
        status_results["overall"] = "warning"
    else:
        status_results["overall"] = "healthy"
    
    return status_results

# Get file metadata by slug
@router.get("/files/by-slug/{slug}", response_model=dict)
async def get_file_by_slug(slug: str):
    collection = get_mongo_client()
    minio_client = get_minio_client()
    
    # Get file metadata from MongoDB
    file = await collection.find_one({"slug": slug})
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with slug '{slug}' not found"
        )
    
    # Convert ObjectId to string for JSON serialization
    file["_id"] = str(file["_id"])
    
    # Generate a fresh pre-signed URL with 1-hour expiration
    try:
        object_name = file["object_name"]
        fresh_url = minio_client.presigned_get_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            expires=timedelta(hours=1)
        )
        
        # Update the URL in the response with a fresh one
        file["file_url"] = fresh_url
        
    except Exception as e:
        # If there's an error generating the URL, log it but return the original metadata
        print(f"Error generating fresh URL: {e}")
        # You could also raise an HTTPException here if you prefer
    
    return file

# Get file metadata by ID
@router.get("/files/{file_id}", response_model=dict)
async def get_file_by_id(file_id: str):
    collection = get_mongo_client()
    file = await collection.find_one({"file_id": file_id})
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found"
        )
    
    # Convert ObjectId to string for JSON serialization
    file["_id"] = str(file["_id"])
    return file