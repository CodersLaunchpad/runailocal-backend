import base64
import io
import os
import random
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status, Depends
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from models.models import PyObjectId, Token, UserCreate, UserInDB, ArticleInDB, UserUpdate, ensure_object_id, prepare_mongo_document
from helpers.auth import create_access_token, get_password_hash, get_current_active_user, get_admin_user
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

    return created_user

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
        object_id = ensure_object_id(user_id)
        
        # Let's try to find the document
        user = await db.users.find_one({"_id": object_id})
        if user:
            return prepare_mongo_document(user)
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
        
        # Transform the documents to proper format
        return [prepare_mongo_document(user) for user in users]
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
        # Convert the string ID to PyObjectId
        object_id = ensure_object_id(author_id)
        print(f"Author ID to follow: {author_id}, Object ID: {object_id}")
        print("current user: ", current_user)

        # Check if author exists and is actually an author
        # author = await db.users.find_one({"_id": object_id, "user_details.type": "author"})
        # TODO: figure out author controls later
        author = await db.users.find_one({"_id": object_id})
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")

        print(f"Found author: {author.get('username', 'Unknown')}")

        # Convert current user's following list to PyObjectId objects for comparison
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
    # except InvalidId:
    #     # MongoDB's InvalidId exception for malformed ObjectIds
    #     raise HTTPException(status_code=400, detail="Invalid author ID format")
    except Exception as e:
        print(f"Error following author: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        
@router.post("/unfollow/{author_id}", status_code=status.HTTP_200_OK)
async def unfollow_author(
    author_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        # Convert the string ID to ObjectId
        object_id = ensure_object_id(author_id)
        print(f"Author ID to unfollow: {author_id}, Object ID: {object_id}")
        
        # Check if author exists
        author = await db.users.find_one({"_id": object_id})
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")
            
        print(f"Found author: {author.get('username', 'Unknown')}")
        
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
    
    return following_users

@router.get("/user/{user_identifier}/stats", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_user_statistics(
    user_identifier: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    Retrieve comprehensive statistics for a user including:
    - Follower count
    - Following count
    - Number of articles published
    - Additional engagement metrics
    
    The user can be identified by either:
    - MongoDB ObjectId
    - Username (case insensitive)
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
        
        # Get user's ObjectId for subsequent queries
        object_id = user["_id"]
        
        # Get follower and following counts
        followers = user.get("followers", [])
        following = user.get("following", [])
        follower_count = len(followers)
        following_count = len(following)
        
        # Get all articles written by this user
        articles_cursor = db.articles.find({"user_id": object_id})
        articles = await articles_cursor.to_list(length=100)  # Limit to 100 articles
        
        # Count total articles
        article_count = len(articles)
        
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
        if str(current_user.id) != str(object_id):  # Don't check if viewing own profile
            current_user_object_id = ensure_object_id(str(current_user.id))
            is_following = current_user_object_id in [ensure_object_id(str(f_id)) for f_id in followers]
        
        # Build response
        user_stats = {
            "username": user.get("username", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "follower_count": follower_count,
            "following_count": following_count,
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
        
        return user_stats
        
    except Exception as e:
        print(f"Error getting user statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")