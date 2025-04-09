import base64
import io
import os
import random
from bson import ObjectId
from fastapi import APIRouter, Body, File, Form, HTTPException, Response, UploadFile, status, Depends, Request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from datetime import datetime

from minio import Minio
from pydantic import EmailStr
from db.db import get_object_storage
from dependencies.user import UserServiceDep, get_user_service
from models.models import get_current_utc_time

from fastapi.responses import JSONResponse
from models.models import ArticleInDB, clean_document, ensure_object_id
from models.users_model import UserCreate, UserUpdate
from mappers.users_mapper import UserResponse
from dependencies.auth import OptionalUser, AdminUser, CurrentActiveUser, get_current_active_user
from services import minio_service
from services.user_service import UserService

router = APIRouter()
# User routes
@router.post("/register") # response_model=UserResponse
async def create_user(
    username: str = Form(...),
    email: EmailStr = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    password: str = Form(...),
    user_type: Optional[str] = Form("normal"),
    region: Optional[str] = Form(None),
    date_of_birth: str = Form(...),
    profile_picture_initials: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    user_service: UserService = Depends(get_user_service),
    minio_client: Minio = Depends(get_object_storage)
):
    """Create a new user and return the user details"""
    try:
        # Create a base user data dictionary
        user_data = {
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": password,
            "user_type": user_type,
            "region": region,
            "date_of_birth": date_of_birth,
            "profile_picture_initials": profile_picture_initials
        }
        
        # Handle profile picture upload if provided
        if profile_picture and profile_picture.filename:
            # Upload to MinIO and create file record
            from services.minio_service import upload_profile_picture
            file_record = await upload_profile_picture(
                profile_picture=profile_picture,
                username=username,
                minio_client=minio_client
            )
            # Pass the file_id to the user creation
            user_data["profile_photo_id"] = file_record["file_id"]
        
        # Create user
        user = UserCreate(**user_data)
        created_user = await user_service.create_user(user)

        print("Created User with info: ", created_user)
        
        return created_user
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
@router.get("/me", status_code=status.HTTP_200_OK)
async def read_users_me(
    current_user: CurrentActiveUser, user_service: UserServiceDep
):
    """
    Get current user's detailed profile with statistics

    Retrieve detailed information for the currently authenticated user including:
    - Basic user information
    - Follower and following lists with user details
    - Article statistics
    - Bookmark information
    
    Authentication is required.
    """
    try:
        user_data = await user_service.get_user_profile(current_user.id)
        return JSONResponse(content=user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/me/likes", response_model=List[Dict[str, Any]])
async def get_likes(
    current_user: CurrentActiveUser, user_service: UserServiceDep
):
    """Get current user's liked articles"""
    try:
        likes = await user_service.get_user_likes(current_user)
        return likes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.put("/me", response_model=UserResponse)
async def update_user(
    current_user: CurrentActiveUser,
    user_service: UserService = Depends(get_user_service),
    minio_client: Minio = Depends(get_object_storage),
    username: Optional[str] = Form(None),
    email: Optional[EmailStr] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    bio: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None)
):
    """Update current user's profile"""
    try:
        # Create a dictionary with the form data
        filtered_data = {
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "bio": bio,
            "date_of_birth": date_of_birth
        }
        
        # Remove None values
        filtered_data = {k: v for k, v in filtered_data.items() if v is not None}
        
        # Create a UserUpdate object from the filtered data
        user_update = UserUpdate(**filtered_data)
        
        # Handle profile picture upload if provided
        if profile_picture and profile_picture.filename and profile_picture.filename is not None:
            try:
                print(f"[Update User] Processing profile picture upload: {profile_picture.filename}")
                
                # Get MongoDB collection for file metadata
                from db.db import get_db
                mongo_collection = await get_db()
                mongo_collection = mongo_collection.files
                print(f"[Update User] MongoDB collection retrieved: files")
                
                # Generate a unique file ID
                from services.minio_service import generate_unique_file_id
                file_id = await generate_unique_file_id(mongo_collection)
                print(f"[Update User] Generated file_id: {file_id}")
                
                # Organize by user_id/profile/files
                folder = f"{current_user.id}/profile"
                print(f"[Update User] Storage folder path: {folder}")
                
                # Save the image to MinIO
                from services.minio_service import upload_to_minio
                file_data = await upload_to_minio(
                    data=await profile_picture.read(),
                    filename=profile_picture.filename,
                    content_type=profile_picture.content_type,
                    minio_client=minio_client,
                    folder=folder
                )
                print(f"[Update User] Image saved to MinIO: {file_data['object_name']}")
                
                # Store file metadata in MongoDB with additional user_id
                file_data["user_id"] = str(current_user.id)
                
                # Generate slug for the file
                from services.minio_service import create_slug
                base_slug = await create_slug(os.path.splitext(profile_picture.filename)[0])
                file_data["slug"] = f"{base_slug}-{file_data['unique_string']}"
                
                # Save to database
                result = await mongo_collection.insert_one(file_data)
                print(f"[Update User] File metadata stored in MongoDB: {result.inserted_id}")
                
                # Set the profile picture fields
                user_update.profile_photo_id = file_data["file_id"]
                
                # Create profile_picture_file structure
                profile_picture_file = {
                    "file_id": file_data["file_id"],
                    "file_type": file_data["file_type"],
                    "file_extension": file_data["file_extension"],
                    "size": file_data["size"],
                    "object_name": file_data["object_name"],
                    "slug": file_data["slug"],
                    "unique_string": file_data["unique_string"]
                }
                
                # Ensure these fields are included in the update data
                update_data = user_update.model_dump(exclude_unset=True)
                update_data["profile_photo_id"] = file_data["file_id"]
                update_data["profile_picture_file"] = profile_picture_file
                update_data["updated_at"] = get_current_utc_time()
                
                # Create a new UserUpdate object with the complete data
                user_update = UserUpdate(**update_data)
                
            except Exception as e:
                print(f"[Update User] Error processing profile picture: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error processing profile picture: {str(e)}"
                )
            finally:
                await profile_picture.close()
        else:
            print("[Update User] No profile picture provided with the update")
            # If no profile picture update, just add the timestamp
            update_data = user_update.model_dump(exclude_unset=True)
            update_data["updated_at"] = get_current_utc_time()
            user_update = UserUpdate(**update_data)
        
        # Update the user
        updated_user = await user_service.update_user(current_user.id, user_update)
        
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return updated_user
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: CurrentActiveUser, 
    user_service: UserServiceDep
):
    """Get a user by ID"""
    try:
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
@router.get("/", response_model=List[UserResponse])
async def get_all_users(current_user: AdminUser, user_service: UserServiceDep):
    """Get all users (admin only)"""
    try:
        users = await user_service.get_all_users()
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@router.put("/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: AdminUser,
    user_service: UserServiceDep
):
    """Admin update for any user"""
    try:
        updated_user = await user_service.update_user(user_id, user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: AdminUser,
    user_service: UserServiceDep
):
    """Delete a user (admin only)"""
    try:
        success = await user_service.delete_user(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
# Following authors
@router.post("/follow/{author_id}", status_code=status.HTTP_200_OK)
async def follow_author(
    author_id: str,
    current_user: CurrentActiveUser,
    user_service: UserServiceDep
):
    """Follow an author by username or ID"""
    try:
        result = await user_service.follow_author(current_user.id, author_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
@router.post("/unfollow/{author_id}", status_code=status.HTTP_200_OK)
async def unfollow_author(
    author_id: str,
    current_user: CurrentActiveUser,
    user_service: UserServiceDep
):
    """Unfollow an author by username or ID"""
    try:
        result = await user_service.unfollow_author(current_user.id, author_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
        
@router.get("/me/following", response_model=List[UserResponse])
async def get_following(current_user: CurrentActiveUser, user_service: UserServiceDep):
    """Get users that the current user follows"""
    try:
        following_users = await user_service.get_following(current_user)
        return following_users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/user/{user_identifier}/stats", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
async def get_user_statistics(
    user_identifier: str,
    current_user: OptionalUser,
    user_service: UserServiceDep
):
    """Get comprehensive statistics for a user"""
    try:
        user_stats = await user_service.get_user_statistics(user_identifier, current_user)
        return user_stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
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
    current_user: CurrentActiveUser,
    user_service: UserServiceDep
):
    """Bookmark an article"""
    try:
        result = await user_service.bookmark_article(current_user.id, article_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
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
    current_user: CurrentActiveUser,
    user_service: UserServiceDep
):
    """Remove an article bookmark"""
    try:
        result = await user_service.remove_bookmark(current_user.id, article_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
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

@router.get("/me/bookmarks")
async def get_bookmarks(current_user: CurrentActiveUser, user_service: UserServiceDep):
    """Get current user's bookmarked articles"""
    try:
        bookmarks = await user_service.get_user_bookmarks(current_user.id)
        return bookmarks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
    
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