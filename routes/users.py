import base64
import io
import os
import random
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status, Depends
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi.responses import JSONResponse
from config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from models.models import PyObjectId, Token, UserCreate, UserInDB, ArticleInDB, UserUpdate, clean_document, ensure_object_id, prepare_mongo_document
from helpers.auth import create_access_token, get_current_user_optional, get_password_hash, get_current_active_user, get_admin_user
from db.db import get_db
from pymongo import ReturnDocument
from PIL import Image, ImageDraw, ImageFont

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
    
    # Process profile picture or generate avatar
    profile_picture_base64 = None
    
    if user.profile_picture:
        try:
            # The user.profile_picture is already in base64 format from the frontend
            # Just clean it up if needed
            if ',' in user.profile_picture:
                # Keep the full data URL format for frontend display
                profile_picture_base64 = user.profile_picture
            else:
                # Add the data URL prefix if it's missing
                profile_picture_base64 = f"data:image/jpeg;base64,{user.profile_picture}"
                
        except Exception as e:
            # Log the error but continue with registration
            print(f"Error processing profile picture: {str(e)}")
            # Fall back to generating an avatar
            if user.first_name and user.last_name:
                initials = (user.first_name[0] + user.last_name[0]).upper()
            else:
                initials = user.username[:2].upper()
            profile_picture_base64 = generate_initials_avatar_base64(initials)
    
    elif user.profile_picture_initials:
        # Generate an avatar with the provided initials
        profile_picture_base64 = generate_initials_avatar_base64(user.profile_picture_initials)
    
    else:
        # Generate default initials from username
        initials = user.username[:2].upper()
        profile_picture_base64 = generate_initials_avatar_base64(initials)
    
    # Create user object
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict(exclude={"password"})
    user_dict["password_hash"] = hashed_password
    user_dict["created_at"] = datetime.now(timezone.utc)
    user_dict["profile_picture_base64"] = profile_picture_base64
    
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
    user_dict["followers"] = []
    
    # Insert into database
    result = await db.users.insert_one(user_dict)
    
    # Get the created user
    created_user = await db.users.find_one({"_id": result.inserted_id})
    # Convert ObjectId to string before returning
    if created_user and isinstance(created_user.get("_id"), ObjectId):
        created_user["_id"] = str(created_user["_id"])

    # return created_user
    serializable_response = clean_document(prepare_mongo_document(create_user))
    return JSONResponse(content=serializable_response)

@router.post("/register", response_model=Token)
async def register_user(user: UserCreate, db = Depends(get_db)):
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
    
    # Process profile picture or generate avatar
    profile_picture_base64 = None
    
    if user.profile_picture:
        try:
            # The user.profile_picture is already in base64 format from the frontend
            # Just clean it up if needed
            if ',' in user.profile_picture:
                # Keep the full data URL format for frontend display
                profile_picture_base64 = user.profile_picture
            else:
                # Add the data URL prefix if it's missing
                profile_picture_base64 = f"data:image/jpeg;base64,{user.profile_picture}"
                
        except Exception as e:
            # Log the error but continue with registration
            print(f"Error processing profile picture: {str(e)}")
            # Fall back to generating an avatar
            if user.first_name and user.last_name:
                initials = (user.first_name[0] + user.last_name[0]).upper()
            else:
                initials = user.username[:2].upper()
            profile_picture_base64 = generate_initials_avatar_base64(initials)
    
    elif user.profile_picture_initials:
        # Generate an avatar with the provided initials
        profile_picture_base64 = generate_initials_avatar_base64(user.profile_picture_initials)
    
    else:
        # Generate default initials from username
        initials = user.username[:2].upper()
        profile_picture_base64 = generate_initials_avatar_base64(initials)
    
    # Create user object
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict(exclude={"password", "profile_picture", "profile_picture_initials"})
    user_dict["password_hash"] = hashed_password
    user_dict["created_at"] = datetime.now(timezone.utc)
    user_dict["profile_picture_base64"] = profile_picture_base64
    
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
            "profile_picture": profile_picture_base64,  # Use the profile picture here too
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
    user_dict["followers"] = []
    
    # Insert into database
    result = await db.users.insert_one(user_dict)
    
    # Get the created user
    created_user = await db.users.find_one({"_id": result.inserted_id})
    # Convert ObjectId to string before returning
    if created_user and isinstance(created_user.get("_id"), ObjectId):
        created_user["_id"] = str(created_user["_id"])
    
    print("created user object: ", created_user)

    # access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expires = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": created_user["username"],
            "id": created_user["_id"],
            "type": created_user["user_type"]
        },
        expires_delta=access_token_expires
    )
    
    # Return the token and profile picture as base64
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "profile_picture_base64": profile_picture_base64
    }

# Helper function to generate an avatar with initials and return as base64
def generate_initials_avatar_base64(initials):
    # Ensure we have at least one character
    initials = initials[:2].upper() if initials else "U"
    
    # Create a random background color - using pastel colors
    bg_color = (
        random.randint(100, 200),  # R
        random.randint(100, 200),  # G
        random.randint(100, 200),  # B
    )
    
    # Create a new image with a colored background
    img_size = 200
    img = Image.new('RGB', (img_size, img_size), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, or fall back to default
    try:
        # Try to load a font - adjust the path based on your server
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        if not os.path.exists(font_path):
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
            if not os.path.exists(font_path):
                font = ImageFont.load_default()
            else:
                font = ImageFont.truetype(font_path, size=80)
        else:
            font = ImageFont.truetype(font_path, size=80)
    except Exception:
        font = ImageFont.load_default()
    
    # Calculate text size to center it
    try:
        text_bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    except AttributeError:
        # For older Pillow versions
        text_width, text_height = draw.textsize(initials, font=font)
    
    position = ((img_size - text_width) // 2, (img_size - text_height) // 2)
    
    # Draw the text in white
    draw.text(position, initials, font=font, fill=(255, 255, 255))
    
    # Convert the image to base64 without saving to disk
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Return as data URL format for easy use in img tags
    return f"data:image/png;base64,{img_str}"



# @router.get("/me", response_model=UserInDB)
# async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
#     return current_user

@router.get("/me", status_code=status.HTTP_200_OK)
async def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    Retrieve detailed information for the currently authenticated user including:
    - Basic user information
    - Follower and following lists with user details
    - Article statistics
    - Bookmark information
    
    Authentication is required.
    """
    from bson.objectid import ObjectId
    
    try:
        # Get user ObjectId
        user_id = current_user.id
        
        # Get follower and following IDs
        follower_ids = current_user.followers
        following_ids = current_user.following
        
        # Convert PyObjectId to ObjectId if needed
        follower_object_ids = [ObjectId(str(f_id)) for f_id in follower_ids]
        following_object_ids = [ObjectId(str(f_id)) for f_id in following_ids]
        
        # Get follower and following counts
        follower_count = len(follower_ids)
        following_count = len(following_ids)
        
        # Fetch follower details
        followers_list = []
        if follower_object_ids:
            followers_cursor = db.users.find({"_id": {"$in": follower_object_ids}})
            followers_data = await followers_cursor.to_list(length=None)
            
            for follower in followers_data:
                # Check if current user is following this follower (if they follow you back)
                is_following_follower = ObjectId(str(follower["_id"])) in following_object_ids
                
                followers_list.append({
                    "id": str(follower["_id"]),
                    "username": follower.get("username", ""),
                    "first_name": follower.get("first_name", ""),
                    "last_name": follower.get("last_name", ""),
                    "profile_picture_base64": follower.get("profile_picture_base64", ""),
                    "is_following": is_following_follower
                })
        
        # Fetch following details
        following_list = []
        if following_object_ids:
            following_cursor = db.users.find({"_id": {"$in": following_object_ids}})
            following_data = await following_cursor.to_list(length=None)
            
            for following_user in following_data:
                # For the /me endpoint, the current user is always following users in their following list
                following_list.append({
                    "id": str(following_user["_id"]),
                    "username": following_user.get("username", ""),
                    "first_name": following_user.get("first_name", ""),
                    "last_name": following_user.get("last_name", ""),
                    "profile_picture_base64": following_user.get("profile_picture_base64", ""),
                    "is_following": True
                })
        
        # Get article statistics
        # article_count = await db.articles.count_documents({"user_id": ObjectId(str(user_id))})
        total_views = 0
        total_likes = 0
        total_comments = 0
        
        # Get article details (limited to 5 most recent for basic stats)
        # articles_cursor = db.articles.find({"user_id": ObjectId(str(user_id))}).sort("created_at", -1).limit(5)
        articles_cursor = db.articles.find({"user_id": ObjectId(str(user_id))}).sort("created_at", -1)
        # articles = await articles_cursor.to_list(length=5)
        articles = await articles_cursor.to_list()
        article_count = await db.articles.count_documents({"author_id": ensure_object_id(user_id)})

        
        recent_articles = []
        for article in articles:
            comment_count = len(article.get("comments", []))
            
            article_data = {
                "id": str(article.get("_id")),
                "title": article.get("title", ""),
                "slug": article.get("slug", ""),
                "likes": article.get("likes", 0),
                "views": article.get("views", 0),
                "comment_count": comment_count,
                "created_at": article.get("created_at", ""),
            }
            
            recent_articles.append(article_data)
            
            # Update totals
            total_views += article.get("views", 0)
            total_likes += article.get("likes", 0)
            total_comments += comment_count
        
        # Get all totals (separate aggregation for accuracy across all articles)
        pipeline = [
            {"$match": {"user_id": ObjectId(str(user_id))}},
            {"$group": {
                "_id": None,
                "total_views": {"$sum": "$views"},
                "total_likes": {"$sum": "$likes"}
            }}
        ]
        
        article_stats = await db.articles.aggregate(pipeline).to_list(length=1)
        if article_stats:
            total_views = article_stats[0].get("total_views", 0)
            total_likes = article_stats[0].get("total_likes", 0)
        
        # Get bookmark details
        bookmark_ids = current_user.bookmarks
        bookmark_object_ids = [ObjectId(str(b_id)) for b_id in bookmark_ids]
        bookmarks_count = len(bookmark_ids)
        print("bookmark object ids: ", bookmark_object_ids)
        
        # Get bookmark article details (limited to 5 most recent)
        bookmarks_list = []
        if bookmark_object_ids:
            # bookmarks_cursor = db.articles.find({"_id": {"$in": bookmark_object_ids}}).limit(5)
            bookmarks_cursor = db.articles.find({"_id": {"$in": bookmark_object_ids}})
            # bookmarks_data = await bookmarks_cursor.to_list(length=5)
            bookmarks_data = await bookmarks_cursor.to_list()
            
            for bookmark in bookmarks_data:
                # print("bookmark returned article data: ", bookmark)
                bookmarks_list.append({
                    "id": str(bookmark.get("_id")),
                    "title": bookmark.get("title", ""),
                    "slug": bookmark.get("slug", ""),
                    "author": bookmark.get("author_name", ""),
                    "created_at": bookmark.get("created_at", "")
                })
                print("bookmark list thing: ", bookmarks_list)
        
        # Build custom response
        user_data = {
            "id": str(user_id),
            "username": current_user.username,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "user_type": current_user.user_type,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login,
            "profile_picture_base64": current_user.profile_picture_base64,
            "user_details": current_user.user_details,
            
            # Connection stats
            "follower_count": follower_count,
            "following_count": following_count,
            "followers": followers_list,
            "following": following_list,
            
            # Article stats
            "article_count": article_count,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "recent_articles": recent_articles,
            
            # Bookmark stats
            "bookmarks_count": bookmarks_count,
            "bookmarks": bookmarks_list
        }
        # print("user data is: ", user_data)
        # return user_data

        serializable_response = clean_document(prepare_mongo_document(user_data))
        print("user data is: ", serializable_response)

        return JSONResponse(content=serializable_response)
        
    except Exception as e:
        print(f"Error getting user profile data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
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
            # return updated_user
            
            serializable_response = clean_document(prepare_mongo_document(updated_user))
            return JSONResponse(content=serializable_response)
    
    # return current_user
    serializable_response = clean_document(prepare_mongo_document(current_user))
    return JSONResponse(content=serializable_response)

@router.get("/{user_id}", response_model=UserInDB)
async def get_user_by_id(
    user_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = ensure_object_id(user_id)
        
        # Let's try to find the document
        user = await db.users.find_one({"_id": object_id})
        if user:
            # return prepare_mongo_document(user)
            serializable_response = clean_document(prepare_mongo_document(user))
            return JSONResponse(content=serializable_response)
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
@router.get("/", response_model=List[UserInDB])
async def get_all_users(
    current_user: UserInDB = Depends(get_admin_user),
    db = Depends(get_db)
):
    # Check if current user has admin privileges
    # if not current_user.get("is_admin", False):
    #     raise HTTPException(
    #         status_code=403, 
    #         detail="Not authorized. Admin privileges required."
    #     )
    
    try:
        # Fetch all users from the database
        users_cursor = db.users.find({})
        users = await users_cursor.to_list(length=None)
        response_obj = [prepare_mongo_document(user) for user in users]
        # Transform the documents to proper format
        # return [prepare_mongo_document(user) for user in users]
        serializable_response = clean_document(response_obj)
        return JSONResponse(content=serializable_response)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch users: {str(e)}"
        )

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
                # return updated_user
                serializable_response = clean_document(prepare_mongo_document(updated_user))
                return JSONResponse(content=serializable_response)
        
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
@router.post("/follow/{author_identifier}", status_code=status.HTTP_200_OK)
async def follow_author(
    author_identifier: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        # First determine if author_identifier is an ID or username
        
        # Find the author by ID or username
        if ObjectId.is_valid(author_identifier):
            # Search by ID
            author = await db.users.find_one({"_id": ObjectId(author_identifier)})
            print(f"Looking up author by ID: {author_identifier}")
        else:
            # Search by username (case insensitive)
            author = await db.users.find_one({"username": {"$regex": f"^{author_identifier}$", "$options": "i"}})
            print(f"Looking up author by username: {author_identifier}")
            
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
            
        # Get the author's ObjectId
        object_id = author["_id"]
        print(f"Found author: {author.get('username', 'Unknown')}, ID: {object_id}")

        # Convert current user's following list to ObjectId objects for comparison
        following_ids = [ensure_object_id(str(_id)) for _id in current_user.following]
        
        # Convert the user ID to ObjectId for comparison
        user_object_id = ensure_object_id(str(current_user.id))
        
        # Check if author's followers list exists and if user is already in it
        author_followers = author.get('followers', [])
        author_follower_ids = [ensure_object_id(str(_id)) for _id in author_followers]
        
        # Check if already following (on both sides)
        already_following = object_id in following_ids
        already_in_followers = user_object_id in author_follower_ids
        
        if not already_following and not already_in_followers:
            # Ensure the user ID is also properly converted to ObjectId
            user_object_id = ensure_object_id(str(current_user.id))
            
            # Update the current user's following list
            user_result = await db.users.update_one(
                {"_id": user_object_id},
                {"$addToSet": {"following": object_id}}
            )
            
            # Update the author's followers list
            author_result = await db.users.update_one(
                {"_id": object_id},
                {"$addToSet": {"followers": user_object_id}}
            )

            if user_result.modified_count and author_result.modified_count:
                return {"status": "success", "message": "Author followed successfully"}
            elif user_result.modified_count:
                # If only the user was updated but not the author
                return {"status": "partial", "message": "Added to your following list, but couldn't update author's followers"}
            else:
                raise HTTPException(status_code=500, detail="Failed to update following/followers lists")
        else:
            # Handle different cases of partial relationship
            if already_following and not already_in_followers:
                # Fix one-sided relationship by updating author's followers
                author_result = await db.users.update_one(
                    {"_id": object_id},
                    {"$addToSet": {"followers": user_object_id}}
                )
                if author_result.modified_count:
                    return {"status": "fixed", "message": "Fixed one-sided follow relationship"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to update author's followers list")
            elif not already_following and already_in_followers:
                # Fix one-sided relationship by updating user's following
                user_result = await db.users.update_one(
                    {"_id": user_object_id},
                    {"$addToSet": {"following": object_id}}
                )
                if user_result.modified_count:
                    return {"status": "fixed", "message": "Fixed one-sided follow relationship"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to update following list")
            else:
                return {"status": "info", "message": "Already following this author"}
    except Exception as e:
        print(f"Error following author: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")      
      
@router.post("/unfollow/{author_identifier}", status_code=status.HTTP_200_OK)
async def unfollow_author(
    author_identifier: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        # First determine if author_identifier is an ID or username
        
        # Find the author by ID or username
        if ObjectId.is_valid(author_identifier):
            # Search by ID
            author = await db.users.find_one({"_id": ObjectId(author_identifier)})
            print(f"Looking up author by ID: {author_identifier}")
        else:
            # Search by username (case insensitive)
            author = await db.users.find_one({"username": {"$regex": f"^{author_identifier}$", "$options": "i"}})
            print(f"Looking up author by username: {author_identifier}")
            
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
            
        # Get the author's ObjectId
        object_id = author["_id"]
        print(f"Found author: {author.get('username', 'Unknown')}, ID: {object_id}")
        
        # Ensure the user ID is properly converted to ObjectId
        user_object_id = ensure_object_id(str(current_user.id))
        
        # Convert current user's following list to ObjectId objects for comparison
        following_ids = [ensure_object_id(str(_id)) for _id in current_user.following]
        
        # Check if author's followers list exists and if user is in it
        author_followers = author.get('followers', [])
        author_follower_ids = [ensure_object_id(str(_id)) for _id in author_followers]
        
        # Check the state of the follow relationship
        is_following = object_id in following_ids
        is_follower = user_object_id in author_follower_ids
        
        # No follow relationship exists
        if not is_following and not is_follower:
            return {"status": "info", "message": "You are not following this author"}
            
        # Prepare for updates - we'll attempt both sides regardless of current state
        # to ensure consistency
        
        # Remove author from user's following list
        user_result = await db.users.update_one(
            {"_id": user_object_id},
            {"$pull": {"following": object_id}}
        )
        
        # Remove user from author's followers list
        author_result = await db.users.update_one(
            {"_id": object_id},
            {"$pull": {"followers": user_object_id}}
        )
        
        # Check results and return appropriate response
        if user_result.modified_count and author_result.modified_count:
            return {"status": "success", "message": "Author unfollowed successfully"}
        elif user_result.modified_count:
            return {"status": "partial", "message": "Removed from your following list, but couldn't update author's followers"}
        elif author_result.modified_count:
            return {"status": "partial", "message": "Removed from author's followers, but couldn't update your following list"}
        else:
            # If nothing was modified despite the checks indicating a relationship existed
            return {"status": "warning", "message": "No changes made to follow relationship"}
            
    except Exception as e:
        print(f"Error unfollowing author: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        
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
    
    # return following_users
    serializable_response = clean_document(prepare_mongo_document(following_users))
    return JSONResponse(content=serializable_response)
    

@router.get("/user/{user_identifier}/stats", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_user_statistics(
    user_identifier: str,
    current_user: Optional[UserInDB] = Depends(get_current_user_optional),
    db = Depends(get_db)
):
    """
    Retrieve comprehensive statistics for a user including:
    - Follower count and list of followers with user details
    - Following count and list of following with user details
    - Number of articles published
    - Additional engagement metrics
    
    The user can be identified by either:
    - MongoDB ObjectId
    - Username (case insensitive)
    
    Authentication is optional. If a current_user is provided, the "is_following" field
    will reflect whether the current user follows the requested user.
    """
    
    try:
        # Check if the identifier is a valid ObjectId
        if ObjectId.is_valid(user_identifier):
            # Search by ID
            query = {"_id": ObjectId(user_identifier)}
        else:
            # Search by username (case insensitive)
            query = {"username": {"$regex": f"^{user_identifier}$", "$options": "i"}}
        
        # Find the user with the query
        user = await db.users.find_one(query)
            
        # If not found, raise 404
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # User's ObjectId is already available in user["_id"]
        
        # Get follower and following IDs
        follower_ids = user.get("followers", [])
        following_ids = user.get("following", [])
        
        # Convert string IDs to ObjectId if needed
        follower_object_ids = [ObjectId(str(f_id)) if not isinstance(f_id, ObjectId) else f_id for f_id in follower_ids]
        following_object_ids = [ObjectId(str(f_id)) if not isinstance(f_id, ObjectId) else f_id for f_id in following_ids]
        
        # Get follower and following counts
        follower_count = len(follower_ids)
        following_count = len(following_ids)
        
        # Fetch follower details
        followers_list = []
        if follower_object_ids:
            followers_cursor = db.users.find({"_id": {"$in": follower_object_ids}})
            followers_data = await followers_cursor.to_list(length=None)
            
            for follower in followers_data:
                # Check if current user is following this follower
                is_following_follower = False
                if current_user:
                    current_user_object_id = ObjectId(str(current_user.id))
                    is_following_follower = current_user_object_id in [
                        ObjectId(str(f_id)) if not isinstance(f_id, ObjectId) else f_id 
                        for f_id in follower.get("followers", [])
                    ]
                
                followers_list.append({
                    "id": str(follower["_id"]),
                    "username": follower.get("username", ""),
                    "first_name": follower.get("first_name", ""),
                    "last_name": follower.get("last_name", ""),
                    "profile_picture_base64": follower.get("profile_picture_base64", ""),
                    "is_following": is_following_follower
                })
        
        # Fetch following details
        following_list = []
        if following_object_ids:
            following_cursor = db.users.find({"_id": {"$in": following_object_ids}})
            following_data = await following_cursor.to_list(length=None)
            
            for following_user in following_data:
                # Check if current user is following this user
                is_following_user = False
                if current_user:
                    current_user_object_id = ObjectId(str(current_user.id))
                    is_following_user = current_user_object_id in [
                        ObjectId(str(f_id)) if not isinstance(f_id, ObjectId) else f_id 
                        for f_id in following_user.get("followers", [])
                    ]
                
                following_list.append({
                    "id": str(following_user["_id"]),
                    "username": following_user.get("username", ""),
                    "first_name": following_user.get("first_name", ""),
                    "last_name": following_user.get("last_name", ""),
                    "profile_picture_base64": following_user.get("profile_picture_base64", ""),
                    "is_following": is_following_user
                })
        
        # Get all articles written by this user
        article_count = await db.articles.count_documents({"user_id": user["_id"]})
        
        # Get article details (limited to 100) as in the original function
        articles_cursor = db.articles.find({"user_id": user["_id"]})
        articles = await articles_cursor.to_list(length=100)  # Limit to 100 articles
        
        # Process article data
        article_list = []
        total_views = 0
        total_likes = 0
        total_comments = 0
        
        for article in articles:
            # Calculate comment count
            comment_count = len(article.get("comments", []))
            
            # Get article metadata
            article_data = {
                "id": str(article.get("_id")),
                "title": article.get("title", ""),
                "slug": article.get("slug", ""),
                "url": f"/articles/{article.get('slug', '')}",
                "likes": article.get("likes", 0),
                "views": article.get("views", 0),
                "comment_count": comment_count,
                "created_at": article.get("created_at", ""),
                "excerpt": article.get("body", "")[:150] + "..." if len(article.get("body", "")) > 150 else article.get("body", ""),
            }
            
            # Add to article list
            article_list.append(article_data)
            
            # Update totals
            total_views += article.get("views", 0)
            total_likes += article.get("likes", 0)
            total_comments += comment_count
        
        # Sort articles by creation date (newest first)
        article_list = sorted(article_list, key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Check if current user is following this user
        is_following = False
        if current_user and str(current_user.id) != str(user["_id"]):
            # Only perform this check if a current_user is provided and not viewing own profile
            current_user_object_id = ObjectId(str(current_user.id))
            is_following = current_user_object_id in [ObjectId(str(f_id)) for f_id in follower_ids]
        
        # Build response
        user_stats = {
            "username": user.get("username", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "follower_count": follower_count,
            "following_count": following_count,
            "followers": followers_list,
            "following": following_list,
            "article_count": article_count,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "articles": article_list,
            "is_following": is_following,
            "joined_date": user.get("created_at", ""),
            "profile_picture_base64": user.get("profile_picture_base64", ""),
            # Include additional stats as needed
        }
        
        # return user_stats
        serializable_response = clean_document(user_stats)
        return JSONResponse(content=serializable_response)
        
    except Exception as e:
        print(f"Error getting user statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
    
@router.post("/bookmark/{article_id}", status_code=status.HTTP_200_OK)
async def bookmark_article(
    article_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        # Convert article_id to ObjectId
        article_object_id = ensure_object_id(article_id)
        
        # Check if article exists
        article = await db.articles.find_one({"_id": article_object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Convert current user's bookmarks list to ObjectId objects for comparison
        bookmarks = getattr(current_user, 'bookmarks', [])
        bookmark_ids = [ensure_object_id(str(_id)) for _id in bookmarks]
        
        # Convert the user ID to ObjectId for comparison
        user_object_id = ensure_object_id(str(current_user.id))
        
        # Check if article's bookmarked_by list exists and if user is already in it
        article_bookmarked_by = article.get('bookmarked_by', [])
        article_bookmarked_by_ids = [ensure_object_id(str(_id)) for _id in article_bookmarked_by]
        
        # Check if already bookmarked (on both sides)
        already_in_bookmarks = article_object_id in bookmark_ids
        already_in_bookmarked_by = user_object_id in article_bookmarked_by_ids
        
        if not already_in_bookmarks and not already_in_bookmarked_by:
            # Update user's bookmarks list
            user_result = await db.users.update_one(
                {"_id": ensure_object_id(str(current_user.id))},
                {"$addToSet": {"bookmarks": article_object_id}}
            )
            
            # Update the article's bookmarked_by list
            article_result = await db.articles.update_one(
                {"_id": article_object_id},
                {"$addToSet": {"bookmarked_by": user_object_id}}
            )
            
            if user_result.modified_count and article_result.modified_count:
                return {"status": "success", "message": "Article bookmarked successfully"}
            elif user_result.modified_count:
                # If only the user was updated but not the article
                return {"status": "partial", "message": "Added to your bookmarks, but couldn't update article's bookmarked_by list"}
            else:
                raise HTTPException(status_code=500, detail="Failed to update bookmarks/bookmarked_by lists")
        else:
            # Handle different cases of partial relationship
            if already_in_bookmarks and not already_in_bookmarked_by:
                # Fix one-sided relationship by updating article's bookmarked_by
                article_result = await db.articles.update_one(
                    {"_id": article_object_id},
                    {"$addToSet": {"bookmarked_by": user_object_id}}
                )
                if article_result.modified_count:
                    return {"status": "fixed", "message": "Fixed one-sided bookmark relationship"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to update article's bookmarked_by list")
            elif not already_in_bookmarks and already_in_bookmarked_by:
                # Fix one-sided relationship by updating user's bookmarks
                user_result = await db.users.update_one(
                    {"_id": ensure_object_id(str(current_user.id))},
                    {"$addToSet": {"bookmarks": article_object_id}}
                )
                if user_result.modified_count:
                    return {"status": "fixed", "message": "Fixed one-sided bookmark relationship"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to update bookmarks list")
            else:
                return {"status": "info", "message": "Article already bookmarked"}
            
    except Exception as e:
        print(f"Error bookmarking article: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        
@router.delete("/bookmark/{article_id}", status_code=status.HTTP_200_OK)
async def delete_bookmark_article(
    article_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        # Convert article_id to ObjectId
        article_object_id = ensure_object_id(article_id)
        
        # Check if article exists
        article = await db.articles.find_one({"_id": article_object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Ensure the user ID is properly converted to ObjectId
        user_object_id = ensure_object_id(str(current_user.id))
        
        # Convert current user's bookmarks list to ObjectId objects for comparison
        bookmark_ids = [ensure_object_id(str(_id)) for _id in current_user.bookmarks]
        
        # Check if article's bookmarked_by list exists and if user is in it
        article_bookmarked_by = article.get('bookmarked_by', [])
        article_bookmarked_by_ids = [ensure_object_id(str(_id)) for _id in article_bookmarked_by]
        
        # Check the state of the bookmark relationship
        is_bookmarked = article_object_id in bookmark_ids
        is_in_bookmarked_by = user_object_id in article_bookmarked_by_ids
        
        # No bookmark relationship exists
        if not is_bookmarked and not is_in_bookmarked_by:
            return {"status": "info", "message": "Article is not in your bookmarks"}
            
        # Prepare for updates - we'll attempt both sides regardless of current state
        # to ensure consistency
        
        # Remove article from user's bookmarks list
        user_result = await db.users.update_one(
            {"_id": user_object_id},
            {"$pull": {"bookmarks": article_object_id}}
        )
        
        # Remove user from article's bookmarked_by list
        article_result = await db.articles.update_one(
            {"_id": article_object_id},
            {"$pull": {"bookmarked_by": user_object_id}}
        )
        
        # Check results and return appropriate response
        if user_result.modified_count and article_result.modified_count:
            return {"status": "success", "message": "Article removed from bookmarks successfully"}
        elif user_result.modified_count:
            return {"status": "partial", "message": "Removed from your bookmarks, but couldn't update article's bookmarked_by list"}
        elif article_result.modified_count:
            return {"status": "partial", "message": "Removed from article's bookmarked_by list, but couldn't update your bookmarks"}
        else:
            # If nothing was modified despite the checks indicating a relationship existed
            return {"status": "warning", "message": "No changes made to bookmark relationship"}
            
    except Exception as e:
        print(f"Error removing bookmark: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        
""" @router.get("/me/bookmarks", response_model=List[Dict[str, Any]])
async def get_bookmarks(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    # "" "Get all bookmarked articles with full article details and author information"" "
    bookmarked_articles = []

    # print("current user info: ", current_user)
    
    # Access bookmarks attribute directly from Pydantic model
    bookmarks = current_user.bookmarks if hasattr(current_user, 'bookmarks') else []
    for article_id in bookmarks:
        print("muchos bookmarks: ", bookmarks)
        print("got here")
        object_id = ensure_object_id(article_id)
        article = await db.articles.find_one({"_id": object_id})
        if article:
            print("found zi articles: ", article)
            # Get the related category
            category_data = None
            if "category_id" in article:
                category_data = await db.categories.find_one({"_id": article["category_id"]})
            
            # Get the related author with followers
            author_data = None
            if "author_id" in article:
                author_data = await db.users.find_one(
                    {"_id": article["author_id"]},
                    projection={
                        "_id": 1,
                        "username": 1,
                        "first_name": 1,
                        "last_name": 1,
                        "profile_picture_base64": 1,
                        "followers": 1
                    }
                )
                
                # Add follower_count to author data
                if author_data and "followers" in author_data:
                    author_data["follower_count"] = len(author_data["followers"])
                    # Remove the followers array if you don't need the actual follower details
                    del author_data["followers"]
                else:
                    author_data["follower_count"] = 0
            
            # Build complete article with relations
            article_with_relations = prepare_mongo_document({
                **article,
                "category": prepare_mongo_document(category_data) if category_data else None,
                "author": prepare_mongo_document(author_data) if author_data else None
            })
            
            bookmarked_articles.append(article_with_relations)
    
    return bookmarked_articles
 """    

from datetime import datetime

@router.get("/me/bookmarks")
async def get_bookmarks(
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """Get all bookmarked articles with full article details and author information"""
    try:
        # Helper function to convert MongoDB documents to JSON serializable objects
        def clean_document(doc):
            if isinstance(doc, dict):
                return {k: clean_document(v) for k, v in doc.items()}
            elif isinstance(doc, list):
                return [clean_document(i) for i in doc]
            elif isinstance(doc, ObjectId):
                return str(doc)
            elif isinstance(doc, datetime):
                return doc.isoformat()
            else:
                return doc
        
        bookmarked_articles = []
        
        # Access bookmarks attribute directly from Pydantic model
        bookmarks = current_user.bookmarks if hasattr(current_user, 'bookmarks') else []
        for article_id in bookmarks:
            # Convert string ID to ObjectId
            try:
                object_id = ObjectId(article_id)
                article = await db.articles.find_one({"_id": object_id})
                
                if article:
                    # Convert the article to a JSON serializable format
                    article = clean_document(article)
                    
                    # Get the related category
                    category_data = None
                    if "category_id" in article:
                        category = await db.categories.find_one({"_id": ObjectId(article["category_id"])})
                        if category:
                            category_data = {
                                "_id": str(category["_id"]),
                                "name": category.get("name", ""),
                                "slug": category.get("slug", "")
                            }
                    
                    # Get the related author with followers
                    author_data = None
                    if "author_id" in article:
                        author = await db.users.find_one(
                            {"_id": ObjectId(article["author_id"])},
                            projection={
                                "_id": 1,
                                "username": 1,
                                "first_name": 1,
                                "last_name": 1,
                                "profile_picture_base64": 1,
                                "followers": 1
                            }
                        )
                        
                        if author:
                            # Manually convert the author data
                            author_data = {
                                "_id": str(author["_id"]),
                                "username": author.get("username", ""),
                                "first_name": author.get("first_name", ""),
                                "last_name": author.get("last_name", ""),
                                "profile_picture_base64": author.get("profile_picture_base64", "")
                            }
                            
                            # Calculate follower count
                            followers = author.get("followers", [])
                            author_data["follower_count"] = len(followers)
                    
                    # Build complete article with relations
                    article_with_relations = {
                        **article,
                        "category": category_data,
                        "author": author_data
                    }
                    
                    # Convert any remaining ObjectIds to strings
                    bookmarked_articles.append(article_with_relations)
            except Exception as e:
                print(f"Error processing bookmark {article_id}: {str(e)}")
                continue
        
        # Return the JSON response directly
        # Clean the entire response one more time to ensure all objects are serializable
        serializable_response = clean_document(bookmarked_articles)
        return JSONResponse(content=serializable_response)
    except Exception as e:
        print(f"Error in get_bookmarks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))