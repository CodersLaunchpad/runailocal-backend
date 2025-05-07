from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from dependencies.auth import CurrentActiveUser, AdminUser, OptionalUser, get_current_user_optional, get_current_active_user
from fastapi.responses import Response, StreamingResponse
from fastapi.requests import Request
from minio import Minio
from db.db import get_object_storage, get_db
import io
from config import settings
import os

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
# @router.post("/images/{bucket_name}/{object_name}")
@router.post("/images/upload")
async def upload_image(
    # bucket_name: str,
    # object_name: str, 
    # request: Request, 
    # minio_client: Minio = Depends(get_object_storage),
    current_user = Depends(get_current_active_user),
    minio_client: Minio = Depends(get_object_storage),
    image: Optional[UploadFile] = File(None)
    ):
    try:
        # Read the image data from the request
        # data = await request.body()
        
        # # Upload the image to MinIO
        # minio_client.put_object(bucket_name, object_name, io.BytesIO(data), len(data))
        print(f"[Create Article] current_user: {current_user}")
        if image and image.filename:
            try:
                print(f"[Create Article] Processing image upload: {image.filename}")
                
                # Get MongoDB collection for file metadata
                from db.db import get_db
                mongo_collection = await get_db()
                mongo_collection = mongo_collection.files
                print(f"[Create Article] MongoDB collection retrieved: files")
                
                # Generate a unique file ID
                from services.minio_service import generate_unique_file_id, create_slug
                file_id = await generate_unique_file_id(mongo_collection)
                print(f"[Create Article] Generated file_id: {file_id}")
                
                # Organize by user_id/article_id/files
                # folder = f"{current_user.id}/articles"
                folder = f"articles/media/{current_user.id}"
                print(f"[Create Article] Storage folder path: {folder}")
                
                # Save the image to MinIO
                from services.minio_service import upload_to_minio
                file_data = await upload_to_minio(
                    data=await image.read(),
                    filename=image.filename,
                    content_type=image.content_type,
                    minio_client=minio_client,
                    folder=folder
                )
                print(f"[Create Article] Image saved to MinIO: {file_data['object_name']}")

                 # Generate base slug from filename
                base_slug = await create_slug(os.path.splitext(image.filename)[0])
                
                # Check if slug exists and append number until unique
                slug = base_slug
                counter = 1
                while await mongo_collection.find_one({"slug": slug}):
                    slug = f"{base_slug}-{file_data['file_id'][:8]}-{counter}"
                    counter += 1
                
                # Update the slug in file_data
                file_data["slug"] = slug
                
                # Store file metadata in MongoDB with additional user_id
                file_data["user_id"] = str(current_user.id)
                print(f"[Create Article] File data: {file_data}")
                # Save to database
                result = await mongo_collection.insert_one(file_data)
                print(f"[Create Article] File metadata stored in MongoDB: {result.inserted_id}")
                file_id = file_data.get("file_id")
                
                # Set the image-related fields
                image_file = file_id
                image_id = file_id
                image_url = file_data.get("url")
                
                # Create main_image_file structure
                main_image_file = {
                    "file_id": file_data["file_id"],
                    "file_type": file_data["file_type"],
                    "file_extension": file_data["file_extension"],
                    "size": file_data["size"],
                    "object_name": file_data["object_name"],
                    "slug": file_data["slug"],
                    "unique_string": file_data["file_id"].split("-")[0]  # First part of UUID
                }
                
            except Exception as e:
                print(f"[Create Article] Error processing image: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error processing image: {str(e)}"
                )
            finally:
                await image.close()

        else:
            print("[Create Article] No image provided with the article")

        
        return main_image_file
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )