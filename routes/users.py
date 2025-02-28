import base64
import io
import os
import random
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Response, status, Depends
from datetime import datetime, timedelta, timezone
from typing import List
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
        # object_id = PyObjectId(author_id)
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

        # Check if already following
        if object_id not in following_ids:
            # Ensure the user ID is also properly converted to ObjectId
            user_object_id = ensure_object_id(str(current_user.id))
            result = await db.users.update_one(
                {"_id": user_object_id},
                {"$addToSet": {"following": object_id}}
            )

            if result.modified_count:
                return {"status": "success", "message": "Author followed successfully"}
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
