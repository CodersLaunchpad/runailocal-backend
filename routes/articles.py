import os
import uuid
import json
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Response, status, UploadFile, Request
from typing import Any, Dict, List, Optional

from fastapi.responses import JSONResponse
from db.db import get_object_storage
from models.models import ArticleStatus, clean_document
from db.schemas.articles_schema import ArticleCreate, ArticleUpdate
from dependencies.article import ArticleServiceDep
from dependencies.auth import CurrentActiveUser, AdminUser, OptionalUser, get_current_user_optional, get_current_active_user
# from dependencies.minio import Minio
from minio import Minio

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_article(
    article: ArticleCreate,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """
    Create a new article and save it to the database.
    
    The category_id and author_id are converted from string to ObjectId.
    """
    try:
        created_article = await article_service.create_article(article, str(current_user.id))
        return created_article
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/", response_model=List[Dict[str, Any]])
async def read_articles(
    category: Optional[str] = None,
    author: Optional[str] = None,
    tag: Optional[str] = None,
    featured: Optional[bool] = None,
    article_status: Optional[ArticleStatus] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: OptionalUser = None,
    article_service: ArticleServiceDep = None
):
    """Get a list of articles with optional filtering"""
    try:
        articles = await article_service.get_articles(
            category, author, tag, featured, article_status, skip, limit
        )
        return JSONResponse(content=articles)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

    
@router.get("/{id_or_slug}", response_model=Dict[str, Any])
async def read_article(
    id_or_slug: str,
    article_status: Optional[ArticleStatus] = None,
    article_service: ArticleServiceDep = None,
    current_optional_active_user= Depends(get_current_user_optional)
):
    """Get a single article by ID or slug"""
    try:
        article = await article_service.get_article_by_id_or_slug(id_or_slug, article_status, current_optional_active_user)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=clean_document(article))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}", response_model=Dict[str, Any])
async def update_article(
    id: str,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep,
    minio_client: Minio = Depends(get_object_storage),
    name: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    excerpt: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    read_time: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    tags: Optional[list] = Form(None),
    is_spotlight: Optional[bool] = Form(None),
    is_popular: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """
    Update an article.
    Admins can edit any article while non-admins can only edit their own.
    """
    try:
        # Create a dictionary with the form data
        filtered_data = {
            "name": name,
            "content": content,
            "excerpt": excerpt,
            "category_id": category_id,
            "read_time": read_time,
            "status": status,
            "tags": tags,
            "is_spotlight": is_spotlight,
            "is_popular": is_popular
        }
        
        # Remove None values
        filtered_data = {k: v for k, v in filtered_data.items() if v is not None}
        
        # Create an ArticleUpdate object from the filtered data
        article_update = ArticleUpdate(**filtered_data)
        
        # Handle image upload if provided
        if image and image.filename:
            print(f"Processing image: {image.filename}, content-type: {image.content_type}")
            # Get MongoDB collection for file metadata
            from db.db import get_db
            mongo_collection = await get_db()
            mongo_collection = mongo_collection.files
            
            # Generate a unique file ID
            from services.minio_service import generate_unique_file_id
            file_id = await generate_unique_file_id(mongo_collection)
            
            # Organize by user_id/article_id/files
            folder = f"{current_user.id}/{id}"
            
            # Save the image to MinIO
            from services.minio_service import upload_to_minio
            file_data = await upload_to_minio(
                data=await image.read(),
                filename=image.filename,
                content_type=image.content_type,
                minio_client=minio_client,
                folder=folder
            )
            
            # Store file metadata in MongoDB with additional user_id and article_id
            file_data["user_id"] = str(current_user.id)
            file_data["article_id"] = id
            
            # Save to database
            await mongo_collection.insert_one(file_data)
            
            # Set the image-related fields
            article_update.image_file = file_id
            article_update.image_id = file_id
            
            # Create main_image_file structure
            article_update.main_image_file = {
                "file_id": file_data["file_id"],
                "file_type": file_data["file_type"],
                "file_extension": file_data["file_extension"],
                "size": file_data["size"],
                "object_name": file_data["object_name"],
                "slug": file_data["slug"],
                "unique_string": file_data["file_id"].split("-")[0]  # First part of UUID
            }
        
        # Update the article
        updated_article = await article_service.update_article(id, article_update, str(current_user.id))
        
        if not updated_article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=updated_article)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error in update_article: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/home/", response_model=Dict[str, Any])
async def get_home_page_articles(
    article_service: ArticleServiceDep,
    get_optional_current_user = Depends(get_current_user_optional)
    ):
    """
    Get articles for the home page including spotlighted, popular,
    and articles grouped by category.
    """
    try:
        home_data = await article_service.get_home_page_articles(get_optional_current_user)
        # Transform _id to id in the response data
        # if "by_category" in home_data:
        #     for category in home_data["by_category"]:
        #         for article in category["articles"]:
        #             if "_id" in article:
        #                 article["id"] = article.pop("_id")
        #             if "author" in article and "_id" in article["author"]:
        #                 article["author"]["id"] = article["author"].pop("_id")
        return JSONResponse(content=home_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.post("/{id}/request-publish", status_code=200)
async def request_article_publish(
    id: str,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """Request to publish an article (only for article authors)"""
    try:
        result = await article_service.request_article_publish(id, str(current_user.id))
        
        if not result:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=result)
    except ValueError as e:
        # Handle validation errors from the service layer
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        # Log the full error for debugging
        print(f"Error in request_article_publish: {str(e)}")
        # Return a more specific error message
        raise HTTPException(
            status_code=500,
            detail=f"Error requesting article publish: {str(e)}"
        )

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """Delete an article (author or admin only)"""
    try:
        result = await article_service.delete_article(
            article_id, 
            str(current_user.id),
            current_user.user_type
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
@router.post("/{article_id}/images")
async def upload_article_image(
    article_id: str,
    file: UploadFile = File(...),
    is_main: bool = Form(False),
    is_thumbnail: bool = Form(False),
    caption: Optional[str] = Form(None),
    current_user: CurrentActiveUser = None,
    article_service: ArticleServiceDep = None
):
    """Upload an image for an article"""
    try:
        # This would normally save file to storage (S3, etc.)
        # For demo, we'll just create a placeholder URL
        file_extension = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_extension}"
        file_path = f"/uploads/articles/{article_id}/{file_name}"
        
        # Call service to add image to article
        updated_article = await article_service.article_repo.upload_article_image(
            article_id, file_path, is_main, is_thumbnail, caption
        )
        
        if not updated_article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=updated_article)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.delete("/{article_id}/images/{image_index}")
async def delete_article_image(
    article_id: str,
    image_index: int,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """Delete an image from an article"""
    try:
        updated_article = await article_service.article_repo.delete_article_image(
            article_id, image_index
        )
        
        if not updated_article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=updated_article)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.post("/{article_id}/like", status_code=status.HTTP_200_OK)
async def like_article(
    article_id: str,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """Like an article"""
    try:
        result = await article_service.like_article(article_id, str(current_user.id))
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.post("/{article_id}/unlike", status_code=status.HTTP_200_OK)
async def unlike_article(
    article_id: str,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """Unlike an article"""
    try:
        result = await article_service.unlike_article(article_id, str(current_user.id))
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/{article_id}/likes", response_model=List[str])
async def get_article_likes_users(
    article_id: str,
    article_service: ArticleServiceDep
):
    """Get the list of user IDs who liked an article"""
    try:
        # Get users who liked the article
        user_ids = await article_service.get_article_likes_users(article_id)
        return user_ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/{article_id}/likes/count", response_model=int)
async def get_article_likes_users(
    article_id: str,
    article_service: ArticleServiceDep
):
    """Get the count of users who liked an article"""
    try:
        # Get users who liked the article
        count = await article_service.get_article_likes_count(article_id)
        return count
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.post("/{article_id}/approve", status_code=status.HTTP_200_OK)
async def approve_article(
    article_id: str,
    current_user: AdminUser,
    article_service: ArticleServiceDep
):
    """Approve an article for publication (admin only)"""
    try:
        result = await article_service.article_repo.approve_article(article_id)
        return JSONResponse(content=result)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")