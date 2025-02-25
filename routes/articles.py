import os
import uuid
from fastapi import APIRouter, Body, File, Form, HTTPException, Response, status, Depends, UploadFile
from datetime import datetime
from typing import List, Optional
from models.models import PyObjectId, UserInDB, ArticleInDB, ArticleCreate, ArticleUpdate
from helpers.auth import get_current_active_user, get_admin_user, get_author_user
from pymongo import ReturnDocument
from db.db import get_db

router = APIRouter()

@router.post("/", response_model=ArticleInDB)
async def create_article(
    article: ArticleCreate = Body(...),
    current_user: UserInDB = Depends(get_author_user),
    db = Depends(get_db)
):
    # Check if category exists
    category_id = article.category.get("_id")
    if category_id:
        try:
            object_id = PyObjectId(category_id)
            category = await db.categories.find_one({"_id": object_id})
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
            
            # Set full category info
            article_dict = article.dict()
            article_dict["category"] = {
                "_id": str(category["_id"]),
                "name": category["name"],
                "slug": category["slug"]
            }
        except:
            raise HTTPException(status_code=400, detail="Invalid category ID")
    else:
        raise HTTPException(status_code=400, detail="Category ID is required")
    
    # Check if slug is unique
    existing_article = await db.articles.find_one({"slug": article.slug})
    if existing_article:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Article with this slug already exists"
        )
    
    # Add author info
    article_dict["author_id"] = current_user.id
    article_dict["created_at"] = datetime.now(datetime.timezone.utc)
    article_dict["images"] = []
    article_dict["comments"] = []
    
    # If user is admin, article can be published immediately
    if current_user.user_details.get("type") == "admin":
        article_dict["published_at"] = datetime.now(datetime.timezone.utc)
    
    # Insert into database
    result = await db.articles.insert_one(article_dict)
    
    # Increment author's article count
    await db.users.update_one(
        {"_id": current_user.id}, 
        {"$inc": {"user_details.articles_count": 1}}
    )
    
    # Get the created article
    created_article = await db.articles.find_one({"_id": result.inserted_id})
    return created_article

@router.get("/", response_model=List[ArticleInDB])
async def read_articles(
    category: Optional[str] = None,
    author: Optional[str] = None,
    tag: Optional[str] = None,
    featured: Optional[bool] = None,
    published_only: bool = True,
    skip: int = 0,
    limit: int = 20,
    db = Depends(get_db)
):
    query = {}
    
    # Filter by category
    if category:
        query["category.slug"] = category
    
    # Filter by author
    if author:
        try:
            author_id = PyObjectId(author)
            query["author_id"] = author_id
        except:
            # Try to find author by username
            author_obj = await db.users.find_one({"username": author})
            if author_obj:
                query["author_id"] = author_obj["_id"]
            else:
                return []
    
    # Filter by tag
    if tag:
        query["tags"] = tag
    
    # Filter by featured status
    if featured is not None:
        query["featured"] = featured
    
    # Only show published articles
    if published_only:
        query["published_at"] = {"$ne": None}
    
    articles = []
    cursor = db.articles.find(query).skip(skip).limit(limit).sort("created_at", -1)
    
    async for document in cursor:
        articles.routerend(document)
    
    return articles

@router.get("/{article_id}", response_model=ArticleInDB)
async def read_article(article_id: str, db = Depends(get_db)):
    try:
        object_id = PyObjectId(article_id)
        article = await db.articles.find_one({"_id": object_id})
        
        if article:
            # Check if article is published
            if article.get("published_at") is None:
                raise HTTPException(status_code=404, detail="Article not found or not published")
            
            return article
        
        raise HTTPException(status_code=404, detail="Article not found")
    except:
        # Try to find by slug
        article = await db.articles.find_one({"slug": article_id})
        
        if article:
            # Check if article is published
            if article.get("published_at") is None:
                raise HTTPException(status_code=404, detail="Article not found or not published")
            
            return article
        
        raise HTTPException(status_code=404, detail="Article not found")

@router.put("/{article_id}", response_model=ArticleInDB)
async def update_article(
    article_id: str,
    article_update: ArticleUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # Get the article
        article = await db.articles.find_one({"_id": object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Check if user is author or admin
        if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Check if slug is being updated and is unique
        if article_update.slug:
            existing_article = await db.articles.find_one({
                "slug": article_update.slug,
                "_id": {"$ne": object_id}
            })
            if existing_article:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Article with this slug already exists"
                )
        
        # Check if category is being updated
        if article_update.category and article_update.category.get("_id"):
            category_id = article_update.category.get("_id")
            try:
                cat_object_id = PyObjectId(category_id)
                category = await db.categories.find_one({"_id": cat_object_id})
                if not category:
                    raise HTTPException(status_code=404, detail="Category not found")
                
                # Update full category info
                article_update.category = {
                    "_id": str(category["_id"]),
                    "name": category["name"],
                    "slug": category["slug"]
                }
            except:
                raise HTTPException(status_code=400, detail="Invalid category ID")
        
        update_data = {k: v for k, v in article_update.dict(exclude_unset=True).items() if v is not None}
        update_data["updated_at"] = datetime.now(datetime.timezone.utc)
        
        if update_data:
            updated_article = await db.articles.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            
            if updated_article:
                return updated_article
        
        raise HTTPException(status_code=404, detail="Article not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID")

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # Get the article
        article = await db.articles.find_one({"_id": object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Check if user is author or admin
        if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        delete_result = await db.articles.delete_one({"_id": object_id})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Decrement author's article count
        await db.users.update_one(
            {"_id": article["author_id"]},
            {"$inc": {"user_details.articles_count": -1}}
        )
        
        # Remove article from favorites
        await db.users.update_many(
            {"favorites": object_id},
            {"$pull": {"favorites": object_id}}
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID")
    
# Upload article image
@router.post("/{article_id}/images", response_model=ArticleInDB)
async def upload_article_image(
    article_id: str,
    file: UploadFile = File(...),
    is_main: bool = Form(False),
    is_thumbnail: bool = Form(False),
    caption: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # Get the article
        article = await db.articles.find_one({"_id": object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Check if user is author or admin
        if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Save file to storage (this would normally upload to S3 or similar)
        # For demo, we'll just create a placeholder URL
        file_extension = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_extension}"
        file_path = f"/uploads/articles/{article_id}/{file_name}"
        
        # Create image object
        image = {
            "url": file_path,
            "is_main": is_main,
            "is_thumbnail": is_thumbnail,
            "caption": caption
        }
        
        # If setting as main or thumbnail, unset others
        if is_main:
            await db.articles.update_one(
                {"_id": object_id, "images.is_main": True},
                {"$set": {"images.$.is_main": False}}
            )
        
        if is_thumbnail:
            await db.articles.update_one(
                {"_id": object_id, "images.is_thumbnail": True},
                {"$set": {"images.$.is_thumbnail": False}}
            )
        
        # Add image to article
        updated_article = await db.articles.find_one_and_update(
            {"_id": object_id},
            {"$push": {"images": image}},
            return_document=ReturnDocument.AFTER
        )
        
        return updated_article
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID or file")

# Delete article image
@router.delete("/{article_id}/images/{image_index}", response_model=ArticleInDB)
async def delete_article_image(
    article_id: str,
    image_index: int,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # Get the article
        article = await db.articles.find_one({"_id": object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Check if user is author or admin
        if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Check if image index exists
        if image_index < 0 or image_index >= len(article.get("images", [])):
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Remove image from article
        images = article.get("images", [])
        images.pop(image_index)
        
        updated_article = await db.articles.find_one_and_update(
            {"_id": object_id},
            {"$set": {"images": images}},
            return_document=ReturnDocument.AFTER
        )
        
        return updated_article
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID or image index")

# Favorite articles
@router.post("/{article_id}/favorite", status_code=status.HTTP_200_OK)
async def favorite_article(
    article_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # Check if article exists
        article = await db.articles.find_one({"_id": object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Add article to favorites if not already favorited
        if object_id not in current_user.favorites:
            await db.users.update_one(
                {"_id": current_user.id},
                {"$addToSet": {"favorites": object_id}}
            )
            return {"status": "success", "message": "Article added to favorites"}
        else:
            return {"status": "info", "message": "Article already in favorites"}
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID")

@router.post("/{article_id}/unfavorite", status_code=status.HTTP_200_OK)
async def unfavorite_article(
    article_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # Remove article from favorites
        await db.users.update_one(
            {"_id": current_user.id},
            {"$pull": {"favorites": object_id}}
        )
        
        return {"status": "success", "message": "Article removed from favorites"}
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID")

# Admin routerroval of articles
@router.post("/{article_id}/routerrove", response_model=ArticleInDB)
async def routerrove_article(
    article_id: str,
    current_user: UserInDB = Depends(get_admin_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(article_id)
        
        # routerrove article by setting published date
        updated_article = await db.articles.find_one_and_update(
            {"_id": object_id, "published_at": None},
            {"$set": {"published_at": datetime.now(datetime.timezone.utc)}},
            return_document=ReturnDocument.AFTER
        )
        
        if not updated_article:
            article = await db.articles.find_one({"_id": object_id})
            if not article:
                raise HTTPException(status_code=404, detail="Article not found")
            elif article.get("published_at"):
                raise HTTPException(status_code=400, detail="Article is already published")
        
        return updated_article
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID")
