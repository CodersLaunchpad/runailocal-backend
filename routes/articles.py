import os
import uuid
from bson import ObjectId
from fastapi import APIRouter, Body, File, Form, HTTPException, Response, status, Depends, UploadFile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from models.models import prepare_mongo_document
from models.models import PyObjectId, UserInDB, ArticleInDB, ArticleCreate, ArticleUpdate, ensure_object_id
from helpers.auth import get_current_active_user, get_admin_user, get_author_user
from pymongo import ReturnDocument
from db.db import get_db

router = APIRouter()

""" @router.post("/", response_model=ArticleInDB)
async def create_article(
    article: ArticleCreate = Body(...),
    # current_user: UserInDB = Depends(get_author_user),
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    # Check if category exists
    print("got here supaaa firrre")
    category_id = article.category
    if category_id:
        try:
            # object_id = PyObjectId(category_id)
            object_id = ensure_object_id(category_id)
            category = await db.categories.find_one({"_id": object_id})
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
            
            # Set full category info
            article_dict = article.dict()
            # article_dict["category"] = {
            #     "_id": str(category["_id"]),
            #     "name": category["name"],
            #     "slug": category["slug"]
            # }
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
    article_dict["created_at"] = datetime.now(timezone.utc)
    article_dict["images"] = []
    article_dict["comments"] = []
    
    # If user is admin, article can be published immediately
    # if current_user.user_details.get("type") == "admin":
    if current_user.user_type == "admin":
        article_dict["published_at"] = datetime.now(timezone.utc)
    
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
 """

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_article(
    article: ArticleCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    Create a new article and save it to the database.
    
    The category_id and author_id are converted from string to ObjectId.
    """
    try:
        # Convert string IDs to ObjectIds
        category_id = ensure_object_id(article.category_id)
        author_id = ensure_object_id(article.author_id)
        
        # Verify that category exists
        category = await db.categories.find_one({"_id": category_id})
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Verify that author exists
        author = await db.users.find_one({"_id": author_id})
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        
        # Check if the current user is allowed to create this article
        # if str(current_user.id) != article.author_id:
        #     # If the current user is not the author, they need permissions
        #     # You can add permission checks here
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN, 
        #         detail="You don't have permission to create an article for this author"
        #     )
        
        # Prepare article document
        article_doc = article.model_dump(exclude={"category_id", "author_id"})
        article_doc["category_id"] = category_id
        article_doc["author_id"] = author_id

        # TODO: Publishing stats and stuff
        # article_doc["published"] = False
        
        # Add additional fields
        article_doc["created_at"] = datetime.utcnow()
        article_doc["updated_at"] = article_doc["created_at"]
        article_doc["views"] = 0
        article_doc["likes"] = 0
        article_doc["comments"] = []
        
        # Insert article into database
        result = await db.articles.insert_one(article_doc)
        
        # Get the created article with its ID
        created_article = await db.articles.find_one({"_id": result.inserted_id})
        
        # Create a serializable response with string IDs
        response = {
            "message": "Article created successfully",
            "article": {
                "id": str(created_article["_id"]),
                "name": created_article["name"],
                "slug": created_article["slug"],
                "content": created_article["content"],
                "excerpt": created_article.get("excerpt"),
                "category_id": str(created_article["category_id"]),
                "author_id": str(created_article["author_id"]),
                "image": created_article["image"],
                "read_time": created_article["read_time"],
                "created_at": created_article["created_at"].isoformat() if isinstance(created_article["created_at"], datetime) else created_article["created_at"],
                "updated_at": created_article["updated_at"].isoformat() if isinstance(created_article["updated_at"], datetime) else created_article["updated_at"],
                "views": created_article["views"],
                "likes": created_article["likes"]
            }
        }
        
        return response
        
    except Exception as e:
        print(f"Error creating article: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
# @router.get("/", response_model=List[ArticleInDB])
# async def read_articles(
#     category: Optional[str] = None,
#     author: Optional[str] = None,
#     tag: Optional[str] = None,
#     featured: Optional[bool] = None,
#     published_only: bool = True,
#     skip: int = 0,
#     limit: int = 20,
#     db = Depends(get_db)
# ):
#     query = {}
    
#     # Filter by category
#     if category:
#         query["category.slug"] = category
    
#     # Filter by author
#     if author:
#         try:
#             author_id = PyObjectId(author)
#             query["author_id"] = author_id
#         except:
#             # Try to find author by username
#             author_obj = await db.users.find_one({"username": author})
#             if author_obj:
#                 query["author_id"] = author_obj["_id"]
#             else:
#                 return []
    
#     # Filter by tag
#     if tag:
#         query["tags"] = tag
    
#     # Filter by featured status
#     if featured is not None:
#         query["featured"] = featured
    
#     # Only show published articles
#     if published_only:
#         query["published_at"] = {"$ne": None}
    
#     articles = []
#     cursor = db.articles.find(query).skip(skip).limit(limit).sort("created_at", -1)
    
#     async for document in cursor:
#         articles.routerend(document)
    
#     return articles

@router.get("/", response_model=List[Dict[str, Any]])
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
    """Get a list of articles with optional filtering"""
    try:
        # Build query filter
        query = {}
        
        # Filter by category
        if category:
            if ObjectId.is_valid(category):
                query["category_id"] = ObjectId(category)
            else:
                # Find category by slug
                category_obj = await db.categories.find_one({"slug": category})
                if category_obj:
                    query["category_id"] = category_obj["_id"]
                else:
                    return []
        
        # Filter by author
        if author:
            if ObjectId.is_valid(author):
                query["author_id"] = ObjectId(author)
            else:
                # Find author by username
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
        # if published_only:
        #     query["published_at"] = {"$ne": None}
        
        # Fetch articles
        cursor = db.articles.find(query).sort("created_at", -1).skip(skip).limit(limit)
        
        articles = []
        async for article in cursor:
            # Get the related category
            category_data = None
            if "category_id" in article:
                category_data = await db.categories.find_one({"_id": article["category_id"]})
            
            # Get the related author (with limited fields)
            author_data = None
            if "author_id" in article:
                author_data = await db.users.find_one(
                    {"_id": article["author_id"]},
                    projection={
                        "_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "last_name": 1,
                        "profile_picture_base64": 1
                    }
                )
            
            # Build response
            article_with_relations = prepare_mongo_document({
                **article,
                "category": category_data,
                "author": author_data
            })
            
            articles.append(article_with_relations)
        
        return articles
    
    except Exception as e:
        print(f"Error in read_articles: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

# @router.get("/{article_id}", response_model=ArticleInDB)
# async def read_article(article_id: str, db = Depends(get_db)):
#     try:
#         object_id = PyObjectId(article_id)
#         article = await db.articles.find_one({"_id": object_id})
        
#         if article:
#             # Check if article is published
#             if article.get("published_at") is None:
#                 raise HTTPException(status_code=404, detail="Article not found or not published")
            
#             return article
        
#         raise HTTPException(status_code=404, detail="Article not found")
#     except:
#         # Try to find by slug
#         article = await db.articles.find_one({"slug": article_id})
        
#         if article:
#             # Check if article is published
#             if article.get("published_at") is None:
#                 raise HTTPException(status_code=404, detail="Article not found or not published")
            
#             return article
        
#         raise HTTPException(status_code=404, detail="Article not found")
    
@router.get("/{id_or_slug}", response_model=Dict[str, Any])
async def read_article(
    id_or_slug: str,
    published_only: bool = True,
    db = Depends(get_db)
):
    """Get a single article by ID or slug"""
    try:
        # Check if the id_or_slug is a valid ObjectId
        if ObjectId.is_valid(id_or_slug):
            # Search by ID
            query = {"_id": ObjectId(id_or_slug)}
        else:
            # Search by slug
            query = {"slug": id_or_slug}
        
        # Apply published filter if needed
        # if published_only:
        #     query["published_at"] = {"$ne": None}
        
        # Find the article
        article = await db.articles.find_one(query)
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Get the related category
        category_data = None
        if "category_id" in article:
            category_data = await db.categories.find_one({"_id": article["category_id"]})
        
        # Get the related author
        author_data = None
        if "author_id" in article:
            author_data = await db.users.find_one(
                {"_id": article["author_id"]},
                projection={
                    "_id": 1,
                    "username": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "profile_picture_base64": 1
                }
            )
        
        # Build response with prepare_mongo_document to handle ObjectId conversion
        article_with_relations = prepare_mongo_document({
            **article,
            "category": category_data if category_data else None,
            "author": author_data if author_data else None
        })
        
        return article_with_relations
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

""" @router.put("/{article_id}", response_model=ArticleInDB)
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
        # if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
        if str(article["author_id"]) != str(current_user.id) and current_user.user_type != "admin":
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
        update_data["updated_at"] = datetime.now(timezone.utc)
        
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
 """

# @router.get("/home")
@router.get("/testing", response_model=Dict[str, Any])
async def get_home_page_articles(
    db = Depends(get_db)
):
    try:
        print("Going to get all the articles")
        return {"testing": "foobar"}
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Detailed error: {error_details}")
        print(f"Detailed error: {error_details}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Edit article route - admins can edit all, users can edit their own
@router.put("/{id}", response_model=Dict[str, Any])
async def update_article(
    id: str,
    article_update: ArticleUpdate,
    current_user = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Update an article (admins can edit all, users can only edit their own)"""
    try:
        # Check if user is authenticated
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate ID
        if not ObjectId.is_valid(id):
            raise HTTPException(status_code=400, detail="Invalid article ID")
        
        # Get the article
        article_id = ObjectId(id)
        article = await db.articles.find_one({"_id": article_id})
        
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # print("current user details: ", current_user)
        print("current user type: ", current_user.user_type)
        # print("current user type: ", current_user["user_type"])
        
        # Check permissions
        # is_admin = current_user["user_type"] == "admin"
        # is_admin = current_user.user_type == "admin"
        # is_author = str(article["author_id"]) == str(current_user["_id"])
        is_admin = current_user.user_type == "admin"  # ✅ Correct access
        is_author = str(article["author_id"]) == str(current_user.id)  # ✅ Use .id instead of ["_id"]
        
        if not (is_admin or is_author):
            raise HTTPException(status_code=403, detail="You don't have permission to edit this article")
        
        # Prepare update data
        update_data = {k: v for k, v in article_update.dict(exclude_unset=True).items() if v is not None}
        
        # If slug is being updated, check uniqueness
        if "slug" in update_data:
            existing = await db.articles.find_one({"slug": update_data["slug"], "_id": {"$ne": article_id}})
            if existing:
                raise HTTPException(status_code=400, detail="Slug already exists")
        
        # Handle category ID conversion
        if "category_id" in update_data and update_data["category_id"]:
            if not ObjectId.is_valid(update_data["category_id"]):
                raise HTTPException(status_code=400, detail="Invalid category ID")
            category = await db.categories.find_one({"_id": ObjectId(update_data["category_id"])})
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
            update_data["category_id"] = ObjectId(update_data["category_id"])
        
        # If no data to update, return the current article
        if not update_data:
            # Get updated article with relations
            category_data = None
            if "category_id" in article:
                category_data = await db.categories.find_one({"_id": article["category_id"]})
            
            author_data = await db.users.find_one(
                {"_id": article["author_id"]},
                projection={
                    "_id": 1,
                    "username": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "profile_picture_base64": 1
                }
            )
            
            return prepare_mongo_document({
                **article,
                "category": category_data,
                "author": author_data
            })
        
        # Add updated_at timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update the article
        await db.articles.update_one(
            {"_id": article_id},
            {"$set": update_data}
        )
        
        # Get updated article
        updated_article = await db.articles.find_one({"_id": article_id})
        
        # Get related data
        category_data = None
        if "category_id" in updated_article:
            category_data = await db.categories.find_one({"_id": updated_article["category_id"]})
        
        author_data = await db.users.find_one(
            {"_id": updated_article["author_id"]},
            projection={
                "_id": 1,
                "username": 1,
                "first_name": 1,
                "last_name": 1,
                "profile_picture_base64": 1
            }
        )
        
        # Return updated article with relations
        return prepare_mongo_document({
            **updated_article,
            "category": category_data,
            "author": author_data
        })
        
    except Exception as e:
        print(f"Error updating article: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


    
# Route for home page content
# @router.get("/home", response_model=Dict[str, Any])
# async def get_home_page_articles(
#     # db = Depends(get_db)
# ):
#     """Get articles for the home page - spotlighted, popular, and by category"""
#     try:
#         print("Going to get all the articles")
#         return {"testing" : "foobar"}
        result = {}
        
        # 1. Get spotlighted articles (max 3)
        spotlight_query = {"status": "published", "is_spotlight": True}
        print(f"Spotlight query: {spotlight_query}")
        # spotlight_cursor = db.articles.find(spotlight_query).sort("published_at", -1).limit(3)
        # todo sort out all the published stuff
        spotlight_cursor = db.articles.find(spotlight_query).sort("updated_at", -1).limit(3)
        
        spotlighted = []
        async for article in spotlight_cursor:
            # Get related data
            category_data = None
            if "category_id" in article:
                category_data = await db.categories.find_one({"_id": article["category_id"]})
            
            author_data = await db.users.find_one(
                {"_id": article["author_id"]},
                projection={
                    "_id": 1,
                    "username": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "profile_picture_base64": 1
                }
            )
            
            spotlighted.append(prepare_mongo_document({
                **article,
                "category": category_data,
                "author": author_data
            }))
        
        result["spotlighted"] = spotlighted
        
        # 2. Get popular articles
        popular_query = {"status": "published", "is_popular": True}
        # popular_cursor = db.articles.find(popular_query).sort("published_at", -1).limit(6)
        popular_cursor = db.articles.find(popular_query).sort("updated_at", -1).limit(6)
        
        popular = []
        async for article in popular_cursor:
            # Get related data
            category_data = None
            if "category_id" in article:
                category_data = await db.categories.find_one({"_id": article["category_id"]})
            
            author_data = await db.users.find_one(
                {"_id": article["author_id"]},
                projection={
                    "_id": 1,
                    "username": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "profile_picture_base64": 1
                }
            )
            
            popular.append(prepare_mongo_document({
                **article,
                "category": category_data,
                "author": author_data
            }))
        
        result["popular"] = popular
        
        # 3. Get articles by category
        # First get all categories
        categories = await db.categories.find().to_list(length=100)
        
        by_category = {}
        for category in categories:
            cat_id = category["_id"]
            cat_name = category["name"]
            
            # Get published articles in this category
            cat_query = {"status": "published", "category_id": cat_id}
            # cat_cursor = db.articles.find(cat_query).sort("published_at", -1).limit(4)
            cat_cursor = db.articles.find(cat_query).sort("updated_at", -1).limit(4)
            
            cat_articles = []
            async for article in cat_cursor:
                # Get author data
                author_data = await db.users.find_one(
                    {"_id": article["author_id"]},
                    projection={
                        "_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "last_name": 1,
                        "profile_picture_base64": 1
                    }
                )
                
                cat_articles.append(prepare_mongo_document({
                    **article,
                    "category": prepare_mongo_document(category),
                    "author": author_data
                }))
            
            if cat_articles:  # Only include categories with articles
                by_category[cat_name] = cat_articles
        
        result["by_category"] = by_category
        
        return result
        
    except Exception as e:
        print(f"Error getting homepage articles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        # if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
        if str(article["author_id"]) != str(current_user.id) and current_user.user_type != "admin":
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
        # if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
        if str(article["author_id"]) != str(current_user.id) and current_user.user_type != "admin":
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
        # if str(article["author_id"]) != str(current_user.id) and current_user.user_details.get("type") != "admin":
        if str(article["author_id"]) != str(current_user.id) and current_user.user_type != "admin":
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
            {"$set": {"published_at": datetime.now(timezone.utc)}},
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
