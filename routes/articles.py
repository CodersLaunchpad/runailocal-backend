import os
import uuid
from fastapi import APIRouter, Body, File, Form, HTTPException, Response, status, UploadFile
from typing import Any, Dict, List, Optional

from fastapi.responses import JSONResponse
from models.models import ArticleStatus
from db.schemas.articles_schema import ArticleCreate, ArticleUpdate
from dependencies.article import ArticleServiceDep
from dependencies.auth import CurrentActiveUser, AdminUser, OptionalUser

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
    article_service: ArticleServiceDep = None
):
    """Get a single article by ID or slug"""
    try:
        article = await article_service.get_article_by_id_or_slug(id_or_slug, article_status)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=article)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}", response_model=Dict[str, Any])
async def update_article(
    id: str,
    article_update: ArticleUpdate,
    current_user: CurrentActiveUser,
    article_service: ArticleServiceDep
):
    """
    Update an article.
    Admins can edit any article while non-admins can only edit their own.
    """
    try:
        updated_article = await article_service.update_article(id, article_update, str(current_user.id))
        
        if not updated_article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        return JSONResponse(content=updated_article)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


@router.get("/home/", response_model=Dict[str, Any])
async def get_home_page_articles(article_service: ArticleServiceDep):
    """
    Get articles for the home page including spotlighted, popular,
    and articles grouped by category.
    """
    try:
        home_data = await article_service.get_home_page_articles()
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
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

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