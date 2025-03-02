from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.requests import Request
from minio import Minio
from db.db import get_object_storage
import io

router = APIRouter()

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