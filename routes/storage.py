from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from fastapi.requests import Request
from minio import Minio
from db.db import get_object_storage, get_db
import io
from config import settings

router = APIRouter()

@router.get("/files/{file_id_or_slug}")
async def get_file(
    request: Request,
    file_id_or_slug: str, 
    identifier_type: str = Query("auto", description="Type of identifier: 'id', 'slug', or 'auto' for automatic detection"),
    download: bool = Query(False, description="Set to true to download the file instead of viewing it"),
    db = Depends(get_db),
    minio_client = Depends(get_object_storage)
):
    # db = await get_db()
    # minio_client = await get_object_storage()
    
    # Determine if we're looking for a file_id or slug
    if identifier_type == "auto":
        # Try to find by file_id first, then by slug
        file = await db.files.find_one({"file_id": file_id_or_slug})
        if not file:
            file = await db.files.find_one({"slug": file_id_or_slug})
    elif identifier_type == "id":
        file = await db.files.find_one({"file_id": file_id_or_slug})
    elif identifier_type == "slug":
        file = await db.files.find_one({"slug": file_id_or_slug})
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid identifier_type: {identifier_type}. Must be 'id', 'slug', or 'auto'"
        )
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with identifier '{file_id_or_slug}' not found"
        )
    
    # If metadata_only is True, just return the file metadata
    metadata_only = request.query_params.get("metadata_only", "false").lower() == "true"
    if metadata_only:
        # Convert ObjectId to string for JSON serialization
        file["_id"] = str(file["_id"])
        return file
    
    # Stream the file content if object_name exists
    if "object_name" in file:
        try:
            object_name = file["object_name"]
            bucket_name = settings.MINIO_BUCKET
            
            # Get the object from MinIO
            response = minio_client.get_object(bucket_name, object_name)

            # Read the data from the response
            file_data = io.BytesIO(response.read())

            # Reset the pointer to the beginning of the BytesIO object
            file_data.seek(0)
            
            # Set up the content disposition based on whether it's a download
            content_disposition = f"attachment; filename=\"{file.get('filename', 'file')}\""
            if not download:
                content_disposition = f"inline; filename=\"{file.get('filename', 'file')}\""
            
            # Return the file as a streaming response
            return StreamingResponse(
                file_data,
                media_type=file.get("content_type", "application/octet-stream"),
                headers={"Content-Disposition": content_disposition}
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving file: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File has no associated content"
        )

@router.get("/images/{bucket_name}/{object_name}")
async def get_image(bucket_name: str, object_name: str, minio_client: Minio = Depends(get_object_storage)):
    try:
        # Get the object from MinIO
        response = minio_client.get_object(bucket_name, object_name)
        
        # Read the data
        data = response.read()
        
        # Determine content type based on file extension
        content_type = "image/jpeg"  # Default
        if object_name.lower().endswith(".png"):
            content_type = "image/png"
        elif object_name.lower().endswith(".gif"):
            content_type = "image/gif"
        
        # Return the image with the appropriate content type
        return Response(content=data, media_type=content_type)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {str(e)}"
        )


# Add a new route to upload an image
@router.post("/images/{bucket_name}/{object_name}")
async def upload_image(bucket_name: str, object_name: str, request: Request, minio_client: Minio = Depends(get_object_storage)):
    try:
        # Read the image data from the request
        data = await request.body()
        
        # Upload the image to MinIO
        minio_client.put_object(bucket_name, object_name, io.BytesIO(data), len(data))
        
        return {"message": "Image uploaded successfully"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )