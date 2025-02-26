from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status, Depends
from datetime import datetime, timezone
from typing import List
from models.models import PyObjectId, UserCreate, UserInDB, ArticleInDB, UserUpdate
from helpers.auth import get_password_hash, get_current_active_user, get_admin_user
from db.db import get_db
from pymongo import ReturnDocument

router = APIRouter()

# User routes
@router.post("/", response_model=UserInDB)
async def create_user(user: UserCreate, db = Depends(get_db)):
    # Check if username already exists
    existing_user = await db.users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user object
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict(exclude={"password"})
    user_dict["password_hash"] = hashed_password
    user_dict["created_at"] = datetime.now(timezone.utc)
    
    # Set user details based on type
    if user.user_type == "normal":
        user_dict["user_details"] = {
            "type": "normal",
            "signup_date": datetime.now(timezone.utc),
            "email_notifications": True,
            "reading_preferences": []
        }
    elif user.user_type == "author":
        user_dict["user_details"] = {
            "type": "author",
            "bio": "",
            "slug": user.username.lower().replace(" ", "-"),
            "picture_url": "",
            "articles_count": 0
        }
    elif user.user_type == "admin":
        # Only existing admins can create new admins, otherwise default to normal user
        user_dict["user_details"] = {
            "type": "normal",
            "signup_date": datetime.now(timezone.utc),
            "email_notifications": True
        }
    
    user_dict["favorites"] = []
    user_dict["following"] = []
    
    # Insert into database
    result = await db.users.insert_one(user_dict)
    
    # Get the created user
    created_user = await db.users.find_one({"_id": result.inserted_id})
    # Convert ObjectId to string before returning
    if created_user and isinstance(created_user.get("_id"), ObjectId):
        created_user["_id"] = str(created_user["_id"])
        
    return created_user

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return current_user

# TODO: rename to get_user_favorites
@router.get("/me/favorites", response_model=List[ArticleInDB])
async def get_favorites(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    favorite_articles = []
    
    for article_id in current_user.favorites:
        article = await db.articles.find_one({"_id": article_id})
        if article and article.get("published_at"):
            favorite_articles.routerend(article)
    
    return favorite_articles

@router.put("/me", response_model=UserInDB)
async def update_user(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    update_data = {k: v for k, v in user_update.dict(exclude_unset=True).items() if v is not None}
    
    if update_data:
        updated_user = await db.users.find_one_and_update(
            {"_id": current_user.id},
            {"$set": update_data},
            return_document=ReturnDocument.AFTER
        )
        if updated_user:
            return updated_user
    
    return current_user

@router.get("/{user_id}", response_model=UserInDB)
async def get_user_by_id(
    user_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(user_id)
        user = await db.users.find_one({"_id": object_id})
        if user:
            return user
        raise HTTPException(status_code=404, detail="User not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

@router.put("/{user_id}", response_model=UserInDB)
async def admin_update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_admin_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(user_id)
        update_data = {k: v for k, v in user_update.dict(exclude_unset=True).items() if v is not None}
        
        if update_data:
            updated_user = await db.users.find_one_and_update(
                {"_id": object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            if updated_user:
                return updated_user
        
        raise HTTPException(status_code=404, detail="User not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(get_admin_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(user_id)
        delete_result = await db.users.delete_one({"_id": object_id})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Also delete user's articles, comments, and messages
        await db.articles.delete_many({"author_id": object_id})
        await db.messages.delete_many({"$or": [{"sender_id": object_id}, {"recipient_id": object_id}]})
        
        # Update articles to remove user's comments
        await db.articles.update_many(
            {},
            {"$pull": {"comments": {"user_id": object_id}}}
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
# Following authors
@router.post("/follow/{author_id}", status_code=status.HTTP_200_OK)
async def follow_author(
    author_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(author_id)
        
        # Check if author exists and is actually an author
        author = await db.users.find_one({"_id": object_id, "user_details.type": "author"})
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
        
        # Add author to following list if not already following
        if object_id not in current_user.following:
            await db.users.update_one(
                {"_id": current_user.id},
                {"$addToSet": {"following": object_id}}
            )
            return {"status": "success", "message": "Author followed successfully"}
        else:
            return {"status": "info", "message": "Already following this author"}
    except:
        raise HTTPException(status_code=400, detail="Invalid author ID")

@router.post("/unfollow/{author_id}", status_code=status.HTTP_200_OK)
async def unfollow_author(
    author_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(author_id)
        
        # Remove author from following list
        await db.users.update_one(
            {"_id": current_user.id},
            {"$pull": {"following": object_id}}
        )
        
        return {"status": "success", "message": "Author unfollowed successfully"}
    except:
        raise HTTPException(status_code=400, detail="Invalid author ID")

@router.get("/me/following", response_model=List[UserInDB])
async def get_following(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    following_users = []
    
    for author_id in current_user.following:
        author = await db.users.find_one({"_id": author_id})
        if author:
            following_users.routerend(author)
    
    return following_users
