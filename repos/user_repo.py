from fastapi import HTTPException
from typing import Dict, List, Optional, Any
from bson import ObjectId
from pymongo import ReturnDocument

from db.schemas.users_schema import UserInDB
from models.models import clean_document, ensure_object_id, prepare_mongo_document
from db.mongodb import convert_to_object_id, overwrite_mongodb_id

# Refactor the schemas
class UserRepository:
    """
    Repository for user-related database operations
    Handles all direct interactions with the database
    """
    
    def __init__(self, db):
        self.db = db
    
    async def find_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Find a user by username with case-insensitive matching
        Returns UserInDB model with profile info if available
        """
        user_dict = await self.db.users.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        
        if not user_dict:
            return None
            
        # If user has a profile photo, fetch the file details
        if user_dict.get("profile_photo_id"):
            file_id = user_dict.get("profile_photo_id")
            file_dict = await self.db.files.find_one({"file_id": file_id})
            
            if file_dict:
                # Create file object with file details
                file_obj = {
                    "file_id": file_dict.get("file_id"),
                    "file_type": file_dict.get("file_type"),
                    "file_extension": file_dict.get("file_extension"),
                    "size": file_dict.get("size"),
                    "object_name": file_dict.get("object_name"),
                    "slug": file_dict.get("slug"),
                    "unique_string": file_dict.get("unique_string")
                }
                user_dict["profile_file"] = file_obj
        
        # Convert ObjectId to string
        if isinstance(user_dict.get("_id"), ObjectId):
            user_dict["_id"] = str(user_dict["_id"])
            
        # Convert to UserInDB model
        return UserInDB(**user_dict)
    
    async def find_by_email(self, email: str) -> Optional[UserInDB]:
        """
        Find a user by email
        Returns UserInDB model with profile info if available
        """
        user_dict = await self.db.users.find_one({"email": email})
        
        if not user_dict:
            return None
            
        # If user has a profile photo, fetch the file details
        if user_dict.get("profile_photo_id"):
            file_id = user_dict.get("profile_photo_id")
            file_dict = await self.db.files.find_one({"file_id": file_id})
            
            if file_dict:
                # Create file object with file details
                file_obj = {
                    "file_id": file_dict.get("file_id"),
                    "file_type": file_dict.get("file_type"),
                    "file_extension": file_dict.get("file_extension"),
                    "size": file_dict.get("size"),
                    "object_name": file_dict.get("object_name"),
                    "slug": file_dict.get("slug"),
                    "unique_string": file_dict.get("unique_string")
                }
                user_dict["profile_file"] = file_obj
        
        # Convert ObjectId to string
        if isinstance(user_dict.get("_id"), ObjectId):
            user_dict["_id"] = str(user_dict["_id"])
            
        # Convert to UserInDB model
        return UserInDB(**user_dict)
    
    async def create_user(self, user_dict: Dict[str, Any]) -> UserInDB:
        """
        Create a new user in the database
        Returns UserInDB model
        """
        result = await self.db.users.insert_one(user_dict)
        
        # Get the created user
        created_user = await self.db.users.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string before returning
        if created_user and isinstance(created_user.get("_id"), ObjectId):
            created_user["_id"] = str(created_user["_id"])
            created_user["id"] = created_user["_id"]  # Add id field for consistency
        
        # Clean document and convert to UserInDB model
        cleaned_user = clean_document(prepare_mongo_document(created_user))
        return UserInDB(**cleaned_user)
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed user profile with related data:
        - Follower and following lists
        - Article statistics
        - Bookmark information
        """
        try:
            # Get user ObjectId
            user_object_id = ensure_object_id(user_id)
            
            # Get user data
            user = await self.db.users.find_one({"_id": user_object_id})
            if not user:
                raise ValueError("User not found")
            
            # If user has a profile photo, fetch the file details
            if user.get("profile_photo_id"):
                file_id = user.get("profile_photo_id")
                file_dict = await self.db.files.find_one({"file_id": file_id})
                
                if file_dict:
                    # Create file object with file details
                    file_obj = {
                        "file_id": file_dict.get("file_id"),
                        "file_type": file_dict.get("file_type"),
                        "file_extension": file_dict.get("file_extension"),
                        "size": file_dict.get("size"),
                        "object_name": file_dict.get("object_name"),
                        "slug": file_dict.get("slug"),
                        "unique_string": file_dict.get("unique_string")
                    }
                    user["profile_file"] = file_obj
                    user["profile_picture_base64"] = "DEPRECIATED"
            
            # Get follower and following IDs
            follower_ids = user.get("followers", [])
            following_ids = user.get("following", [])
            
            # Convert to ObjectId if needed
            follower_object_ids = [ObjectId(str(f_id)) for f_id in follower_ids]
            following_object_ids = [ObjectId(str(f_id)) for f_id in following_ids]
            
            # Get follower and following counts
            follower_count = len(follower_ids)
            following_count = len(following_ids)
            
            # Fetch follower details
            followers_list = []
            if follower_object_ids:
                followers_cursor = self.db.users.find({"_id": {"$in": follower_object_ids}})
                followers_data = await followers_cursor.to_list(length=None)
                
                for follower in followers_data:
                    # Check if current user is following this follower (if they follow you back)
                    is_following_follower = ObjectId(str(follower["_id"])) in following_object_ids

                    # If user has a profile photo, fetch the file details
                    if follower.get("profile_photo_id"):
                        file_id = follower.get("profile_photo_id")
                        file_dict = await self.db.files.find_one({"file_id": file_id})
                        
                        if file_dict:
                            # Create file object with file details
                            file_obj = {
                                "file_id": file_dict.get("file_id"),
                                "file_type": file_dict.get("file_type"),
                                "file_extension": file_dict.get("file_extension"),
                                "size": file_dict.get("size"),
                                "object_name": file_dict.get("object_name"),
                                "slug": file_dict.get("slug"),
                                "unique_string": file_dict.get("unique_string")
                            }
                            follower["profile_file"] = file_obj
                            follower["profile_picture_base64"] = "DEPRECIATED"
                    
                    followers_list.append({
                        "id": str(follower["_id"]),
                        "username": follower.get("username", ""),
                        "first_name": follower.get("first_name", ""),
                        "last_name": follower.get("last_name", ""),
                        "profile_picture_base64": follower.get("profile_picture_base64", ""),
                        "profile_file": follower.get("profile_file", ""),
                        "is_following": is_following_follower
                    })
            
            # Fetch following details
            following_list = []
            if following_object_ids:
                following_cursor = self.db.users.find({"_id": {"$in": following_object_ids}})
                following_data = await following_cursor.to_list(length=None)
                
                for following_user in following_data:
                    # For the /me endpoint, the current user is always following users in their following list
                    # If user has a profile photo, fetch the file details
                    if following_user.get("profile_photo_id"):
                        file_id = following_user.get("profile_photo_id")
                        file_dict = await self.db.files.find_one({"file_id": file_id})
                        
                        if file_dict:
                            # Create file object with file details
                            file_obj = {
                                "file_id": file_dict.get("file_id"),
                                "file_type": file_dict.get("file_type"),
                                "file_extension": file_dict.get("file_extension"),
                                "size": file_dict.get("size"),
                                "object_name": file_dict.get("object_name"),
                                "slug": file_dict.get("slug"),
                                "unique_string": file_dict.get("unique_string")
                            }
                            following_user["profile_file"] = file_obj
                            following_user["profile_picture_base64"] = "DEPRECIATED"
                    following_list.append({
                        "id": str(following_user["_id"]),
                        "username": following_user.get("username", ""),
                        "first_name": following_user.get("first_name", ""),
                        "last_name": following_user.get("last_name", ""),
                        "profile_picture_base64": following_user.get("profile_picture_base64", ""),
                        "profile_file": following_user.get("profile_file", ""),
                        "is_following": True
                    })
            
            # Get article statistics
            article_count = await self.db.articles.count_documents({"author_id": user_object_id})
            
            # Get article details
            articles_cursor = self.db.articles.find({"user_id": user_object_id}).sort("created_at", -1)
            articles = await articles_cursor.to_list(length=None)
            
            recent_articles = []
            total_views = 0
            total_likes = 0
            total_comments = 0
            
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
            
            # Get all totals (separate aggregation for accuracy)
            pipeline = [
                {"$match": {"user_id": user_object_id}},
                {"$group": {
                    "_id": None,
                    "total_views": {"$sum": "$views"},
                    "total_likes": {"$sum": "$likes"}
                }}
            ]
            
            article_stats = await self.db.articles.aggregate(pipeline).to_list(length=1)
            if article_stats:
                total_views = article_stats[0].get("total_views", 0)
                total_likes = article_stats[0].get("total_likes", 0)
            
            # Get bookmark details
            bookmark_ids = user.get("bookmarks", [])
            bookmark_object_ids = [ObjectId(str(b_id)) for b_id in bookmark_ids]
            bookmarks_count = len(bookmark_ids)
            
            # Get bookmark article details
            bookmarks_list = []
            if bookmark_object_ids:
                bookmarks_cursor = self.db.articles.find({"_id": {"$in": bookmark_object_ids}})
                bookmarks_data = await bookmarks_cursor.to_list(length=None)
                
                for bookmark in bookmarks_data:
                    # If article has a main file image, fetch the file details
                    if bookmark.get("image_id"):
                        file_id = bookmark.get("image_id")
                        file_dict = await self.db.files.find_one({"file_id": file_id})
                        
                        if file_dict:
                            # Create file object with file details
                            file_obj = {
                                "file_id": file_dict.get("file_id"),
                                "file_type": file_dict.get("file_type"),
                                "file_extension": file_dict.get("file_extension"),
                                "size": file_dict.get("size"),
                                "object_name": file_dict.get("object_name"),
                                "slug": file_dict.get("slug"),
                                "unique_string": file_dict.get("unique_string")
                            }
                            bookmark["main_image_file"] = file_obj
                            bookmark["image"] = "DEPRECIATED"

                    bookmarks_list.append({
                        "id": str(bookmark.get("_id")),
                        "title": bookmark.get("title", ""),
                        "slug": bookmark.get("slug", ""),
                        "author": bookmark.get("author_name", ""),
                        "image": bookmark.get("image", ""),
                        "main_image_file": bookmark.get("main_image_file", ""),
                        "created_at": bookmark.get("created_at", "")
                    })
            
            # Build custom response
            user_data = {
                "id": str(user_id),
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "user_type": user.get("user_type", ""),
                "created_at": user.get("created_at", ""),
                "last_login": user.get("last_login", ""),
                "profile_picture_base64": user.get("profile_picture_base64", ""),
                "profile_file": user.get("profile_file", ""),
                "user_details": user.get("user_details", {}),
                
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
            
            return clean_document(prepare_mongo_document(user_data))
            
        except Exception as e:
            raise Exception(f"Error getting user profile data: {str(e)}")
    
    async def get_user_likes(self, current_user: UserInDB) -> List[Dict[str, Any]]:
        """Get all liked articles for a user"""
        try:
            liked_articles = []
            
            for article_id in current_user.likes:
                try:
                    # Convert to ObjectId if it's a string
                    object_id = ensure_object_id(article_id)
                    
                    article = await self.db.articles.find_one({"_id": object_id})
                    
                    if article and article.get("status") == "published":
                        # Clean the document to convert ObjectId to string and handle other MongoDB types
                        cleaned_article = clean_document(prepare_mongo_document(article))
                        
                        # Get the related category
                        category_data = None
                        if "category_id" in article:
                            category = await self.db.categories.find_one({"_id": article["category_id"]})
                            if category:
                                category_data = clean_document(prepare_mongo_document(category))
                        
                        # Get the related author
                        author_data = None
                        if "author_id" in article:
                            author = await self.db.users.find_one(
                                {"_id": article["author_id"]},
                                projection={
                                    "_id": 1,
                                    "username": 1,
                                    "first_name": 1,
                                    "last_name": 1,
                                    "profile_picture_base64": 1
                                }
                            )
                            if author:
                                author_data = clean_document(prepare_mongo_document(author))
                        
                        # Add related data to article
                        cleaned_article["category"] = category_data
                        cleaned_article["author"] = author_data
                        
                        liked_articles.append(cleaned_article)
                except Exception as e:
                    # Skip problematic articles but continue processing
                    print(f"Error processing liked article {article_id}: {str(e)}")
                    continue
            
            return liked_articles
            
        except Exception as e:
            raise Exception(f"Error getting user likes: {str(e)}")
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[UserInDB]:
        """
        Update a user's information
        Returns UserInDB model or None
        """
        try:
            updated_user = await self.db.users.find_one_and_update(
                {"_id": ensure_object_id(user_id)},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            
            if not updated_user:
                return None
                
            # Convert ObjectId to string
            if isinstance(updated_user.get("_id"), ObjectId):
                updated_user["_id"] = str(updated_user["_id"])
                
            # Clean document and convert to UserInDB model
            cleaned_user = clean_document(prepare_mongo_document(updated_user))
            return UserInDB(**cleaned_user)
            
        except Exception as e:
            raise Exception(f"Error updating user: {str(e)}")

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """
        Get a user by ID
        Returns UserInDB model or None
        """
        try:
            object_id = ensure_object_id(user_id)
            user_dict = await self.db.users.find_one({"_id": object_id})
            
            if not user_dict:
                return None
                
            # Convert ObjectId to string
            if isinstance(user_dict.get("_id"), ObjectId):
                user_dict["_id"] = str(user_dict["_id"])

            # If article has a main file image, fetch the file details
            if user_dict("profile_photo_id"):
                file_id = user_dict.get("profile_photo_id")
                file_dict = await self.db.files.find_one({"file_id": file_id})
                
                if file_dict:
                    # Create file object with file details
                    file_obj = {
                        "file_id": file_dict.get("file_id"),
                        "file_type": file_dict.get("file_type"),
                        "file_extension": file_dict.get("file_extension"),
                        "size": file_dict.get("size"),
                        "object_name": file_dict.get("object_name"),
                        "slug": file_dict.get("slug"),
                        "unique_string": file_dict.get("unique_string")
                    }
                    user_dict["profile_file"] = file_obj
                    user_dict["profile_picture_base64"] = "DEPRECIATED"
                
            # Clean document and convert to UserInDB model
            cleaned_user = clean_document(prepare_mongo_document(user_dict))
            return UserInDB(**cleaned_user)
            
        except Exception as e:
            raise ValueError(f"Invalid user ID: {str(e)}")
    
    async def validate_user(self, user_id: str) -> None:
        """
        Validate that an author exists
        Raises HTTPException if author is invalid or not found
        """
        try:
            author_id_obj = ObjectId(user_id)
            
            author = await self.db.users.find_one(
                {"_id": author_id_obj},
                projection={"_id": 1}
            )
            if not author:
                raise HTTPException(status_code=404, detail="User not found")
        except HTTPException:
            raise
        except Exception as e:
            raise Exception(f"Error validating user: {str(e)}")

    async def get_all_users(self) -> List[UserInDB]:
        """
        Get all users (admin function)
        Returns list of UserInDB models
        """
        try:
            users_cursor = self.db.users.find({})
            users = await users_cursor.to_list(length=None) # TODO: implement pagination
            
            # Convert to UserInDB models
            result = []
            for user in users:
                # Convert ObjectId to string
                if isinstance(user.get("_id"), ObjectId):
                    user["_id"] = str(user["_id"])
                
                # If article has a main file image, fetch the file details
                if user["profile_photo_id"]:
                    file_id = user.get("profile_photo_id")
                    file_dict = await self.db.files.find_one({"file_id": file_id})
                    print("getting file record")
                    if file_dict:
                        # Create file object with file details
                        print("got file record")
                        file_obj = {
                            "file_id": file_dict.get("file_id"),
                            "file_type": file_dict.get("file_type"),
                            "file_extension": file_dict.get("file_extension"),
                            "size": file_dict.get("size"),
                            "object_name": file_dict.get("object_name"),
                            "slug": file_dict.get("slug"),
                            "unique_string": file_dict.get("unique_string")
                        }
                        user["profile_file"] = file_obj
                        user["profile_picture_base64"] = "DEPRECIATED"

                # Clean document and convert to UserInDB model
                cleaned_user = clean_document(prepare_mongo_document(user))
                result.append(UserInDB(**cleaned_user))
                
            return result
            
        except Exception as e:
            raise Exception(f"Failed to fetch users: {str(e)}")
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user and their associated content"""
        try:
            object_id = ensure_object_id(user_id)
            delete_result = await self.db.users.delete_one({"_id": object_id})
            
            if delete_result.deleted_count == 0:
                return False
            
            # Also delete user's articles, comments, and messages
            await self.db.articles.delete_many({"author_id": object_id})
            await self.db.messages.delete_many({"$or": [{"sender_id": object_id}, {"recipient_id": object_id}]})
            
            # Update articles to remove user's comments
            await self.db.articles.update_many(
                {},
                {"$pull": {"comments": {"user_id": object_id}}}
            )
            
            return True
        except Exception as e:
            raise ValueError(f"Invalid user ID: {str(e)}")
    
    async def follow_author(self, user_id: str, author_identifier: str) -> Dict[str, str]:
        """Follow an author by username or ID"""
        try:
            # Find the author by ID or username
            if ObjectId.is_valid(author_identifier):
                # Search by ID
                author = await self.db.users.find_one({"_id": ObjectId(author_identifier)})
            else:
                # Search by username (case insensitive)
                author = await self.db.users.find_one({"username": {"$regex": f"^{author_identifier}$", "$options": "i"}})
                
            if not author:
                raise ValueError("Author not found")
                
            # Get the author's ObjectId
            author_object_id = author["_id"]
            
            # Get the user
            user_object_id = ensure_object_id(user_id)
            user = await self.db.users.find_one({"_id": user_object_id})
            if not user:
                raise ValueError("User not found")
            
            # Convert following list to ObjectId objects
            following_ids = [ensure_object_id(str(_id)) for _id in user.get("following", [])]
            
            # Check if author's followers list exists
            author_followers = author.get('followers', [])
            author_follower_ids = [ensure_object_id(str(_id)) for _id in author_followers]
            
            # Check if already following
            already_following = author_object_id in following_ids
            already_in_followers = user_object_id in author_follower_ids
            
            if not already_following and not already_in_followers:
                # Update the user's following list
                user_result = await self.db.users.update_one(
                    {"_id": user_object_id},
                    {"$addToSet": {"following": author_object_id}}
                )
                
                # Update the author's followers list
                author_result = await self.db.users.update_one(
                    {"_id": author_object_id},
                    {"$addToSet": {"followers": user_object_id}}
                )

                if user_result.modified_count and author_result.modified_count:
                    return {"status": "success", "message": "Author followed successfully"}
                elif user_result.modified_count:
                    return {"status": "partial", "message": "Added to your following list, but couldn't update author's followers"}
                else:
                    raise Exception("Failed to update following/followers lists")
            else:
                # Handle different cases of partial relationship
                if already_following and not already_in_followers:
                    # Fix one-sided relationship
                    author_result = await self.db.users.update_one(
                        {"_id": author_object_id},
                        {"$addToSet": {"followers": user_object_id}}
                    )
                    if author_result.modified_count:
                        return {"status": "fixed", "message": "Fixed one-sided follow relationship"}
                    else:
                        raise Exception("Failed to update author's followers list")
                elif not already_following and already_in_followers:
                    # Fix one-sided relationship
                    user_result = await self.db.users.update_one(
                        {"_id": user_object_id},
                        {"$addToSet": {"following": author_object_id}}
                    )
                    if user_result.modified_count:
                        return {"status": "fixed", "message": "Fixed one-sided follow relationship"}
                    else:
                        raise Exception("Failed to update following list")
                else:
                    return {"status": "info", "message": "Already following this author"}
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error following author: {str(e)}")
    
    async def unfollow_author(self, user_id: str, author_identifier: str) -> Dict[str, str]:
        """Unfollow an author by username or ID"""
        try:
            # Find the author by ID or username
            if ObjectId.is_valid(author_identifier):
                author = await self.db.users.find_one({"_id": ObjectId(author_identifier)})
            else:
                author = await self.db.users.find_one({"username": {"$regex": f"^{author_identifier}$", "$options": "i"}})
                
            if not author:
                raise ValueError("Author not found")
                
            # Get the author's ObjectId
            author_object_id = author["_id"]
            user_object_id = ensure_object_id(user_id)
            
            # Remove author from user's following list
            user_result = await self.db.users.update_one(
                {"_id": user_object_id},
                {"$pull": {"following": author_object_id}}
            )
            
            # Remove user from author's followers list
            author_result = await self.db.users.update_one(
                {"_id": author_object_id},
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
                return {"status": "warning", "message": "No changes made to follow relationship"}
                
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error unfollowing author: {str(e)}")
    
    async def get_following(self, current_user: UserInDB) -> List[UserInDB]:
        """
        Get list of users that the current user follows
        Returns list of UserInDB models
        """
        following_users = []
        
        for author_id in current_user.following:
            author_dict = await self.db.users.find_one({"_id": ObjectId(author_id)})
            if author_dict:
                # Convert ObjectId to string
                if isinstance(author_dict.get("_id"), ObjectId):
                    author_dict["_id"] = str(author_dict["_id"])
                
                # If article has a main file image, fetch the file details
                if author_dict("profile_photo_id"):
                    file_id = author_dict("profile_photo_id")
                    file_dict = await self.db.files.find_one({"file_id": file_id})
                    
                    if file_dict:
                        # Create file object with file details
                        file_obj = {
                            "file_id": file_dict.get("file_id"),
                            "file_type": file_dict.get("file_type"),
                            "file_extension": file_dict.get("file_extension"),
                            "size": file_dict.get("size"),
                            "object_name": file_dict.get("object_name"),
                            "slug": file_dict.get("slug"),
                            "unique_string": file_dict.get("unique_string")
                        }
                        author_dict["profile_file"] = file_obj
                        author_dict["profile_picture_base64"] = "DEPRECIATED"

                # Convert to UserInDB model
                author = UserInDB(**author_dict)
                following_users.append(author)
        
        return following_users
    
    async def get_user_statistics(self, user_identifier: str, current_user: Optional[UserInDB]) -> Dict[str, Any]:
        """Get comprehensive statistics for a user"""
        try:
            # Check if the identifier is a valid ObjectId
            if ObjectId.is_valid(user_identifier):
                # Search by ID
                query = {"_id": ObjectId(user_identifier)}
            else:
                # Search by username (case insensitive)
                query = {"username": {"$regex": f"^{user_identifier}$", "$options": "i"}}
            
            # Find the user with the query
            user = await self.db.users.find_one(query)
                
            # If not found, raise error
            if not user:
                raise ValueError("User not found")
            
            # User's ObjectId
            user_object_id = user["_id"]

            # If article has a main file image, fetch the file details
            if user.get("profile_photo_id"):
                file_id = user.get("profile_photo_id")
                file_dict = await self.db.files.find_one({"file_id": file_id})
                
                if file_dict:
                    # Create file object with file details
                    file_obj = {
                        "file_id": file_dict.get("file_id"),
                        "file_type": file_dict.get("file_type"),
                        "file_extension": file_dict.get("file_extension"),
                        "size": file_dict.get("size"),
                        "object_name": file_dict.get("object_name"),
                        "slug": file_dict.get("slug"),
                        "unique_string": file_dict.get("unique_string")
                    }
                    user["profile_file"] = file_obj
                    user["profile_picture_base64"] = "DEPRECIATED"
            
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
                followers_cursor = self.db.users.find({"_id": {"$in": follower_object_ids}})
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

                    # If user has a profile photo, fetch the file details
                    if follower.get("profile_photo_id"):
                        file_id = follower.get("profile_photo_id")
                        file_dict = await self.db.files.find_one({"file_id": file_id})
                        
                        if file_dict:
                            # Create file object with file details
                            file_obj = {
                                "file_id": file_dict.get("file_id"),
                                "file_type": file_dict.get("file_type"),
                                "file_extension": file_dict.get("file_extension"),
                                "size": file_dict.get("size"),
                                "object_name": file_dict.get("object_name"),
                                "slug": file_dict.get("slug"),
                                "unique_string": file_dict.get("unique_string")
                            }
                            follower["profile_file"] = file_obj
                            follower["profile_picture_base64"] = "DEPRECIATED"
                    
                    followers_list.append({
                        "id": str(follower["_id"]),
                        "username": follower.get("username", ""),
                        "first_name": follower.get("first_name", ""),
                        "last_name": follower.get("last_name", ""),
                        "profile_picture_base64": follower.get("profile_picture_base64", ""),
                        "profile_file": follower.get("profile_file", ""),
                        "is_following": is_following_follower
                    })
            
            # Fetch following details
            following_list = []
            if following_object_ids:
                following_cursor = self.db.users.find({"_id": {"$in": following_object_ids}})
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

                    #get the profile photo infos
                    # If user has a profile photo, fetch the file details
                    if following_user.get("profile_photo_id"):
                        file_id = following_user.get("profile_photo_id")
                        file_dict = await self.db.files.find_one({"file_id": file_id})
                        
                        if file_dict:
                            # Create file object with file details
                            file_obj = {
                                "file_id": file_dict.get("file_id"),
                                "file_type": file_dict.get("file_type"),
                                "file_extension": file_dict.get("file_extension"),
                                "size": file_dict.get("size"),
                                "object_name": file_dict.get("object_name"),
                                "slug": file_dict.get("slug"),
                                "unique_string": file_dict.get("unique_string")
                            }
                            following_user["profile_file"] = file_obj
                            following_user["profile_picture_base64"] = "DEPRECIATED"
                    
                    following_list.append({
                        "id": str(following_user["_id"]),
                        "username": following_user.get("username", ""),
                        "first_name": following_user.get("first_name", ""),
                        "last_name": following_user.get("last_name", ""),
                        "profile_picture_base64": following_user.get("profile_picture_base64", ""),
                        "profile_file": following_user.get("profile_file", ""),
                        "is_following": is_following_user
                    })
            
            # Get article statistics
            article_count = await self.db.articles.count_documents({"user_id": user_object_id})
            
            # Get article details (limited to 100)
            articles_cursor = self.db.articles.find({"user_id": user_object_id})
            articles = await articles_cursor.to_list(length=100)
            
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
            
            # If user has a profile photo, fetch the file details
            if user.get("profile_photo_id"):
                file_id = user.get("profile_photo_id")
                file_dict = await self.db.files.find_one({"file_id": file_id})
                
                if file_dict:
                    # Create file object with file details
                    file_obj = {
                        "file_id": file_dict.get("file_id"),
                        "file_type": file_dict.get("file_type"),
                        "file_extension": file_dict.get("file_extension"),
                        "size": file_dict.get("size"),
                        "object_name": file_dict.get("object_name"),
                        "slug": file_dict.get("slug"),
                        "unique_string": file_dict.get("unique_string")
                    }
                    user["profile_file"] = file_obj
                    user["profile_picture_base64"] = "DEPRECIATED"
            
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
                "profile_file": user.get("profile_file", ""),
                # "profile_picture_base64": "DEPRECIATED",
            }
            
            return clean_document(user_stats)
            
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error getting user statistics: {str(e)}")
    
    async def bookmark_article(self, user_id: str, article_id: str) -> Dict[str, str]:
        """Bookmark an article"""
        try:
            # Convert article_id to ObjectId
            article_object_id = ensure_object_id(article_id)
            
            # Check if article exists
            article = await self.db.articles.find_one({"_id": article_object_id})
            if not article:
                raise ValueError("Article not found")
            
            # Get the user
            user_object_id = ensure_object_id(user_id)
            user = await self.db.users.find_one({"_id": user_object_id})
            if not user:
                raise ValueError("User not found")
            
            # Convert bookmarks list to ObjectId objects
            bookmarks = user.get("bookmarks", [])
            bookmark_ids = [ensure_object_id(str(_id)) for _id in bookmarks]
            
            # Check if article's bookmarked_by list exists
            article_bookmarked_by = article.get('bookmarked_by', [])
            article_bookmarked_by_ids = [ensure_object_id(str(_id)) for _id in article_bookmarked_by]
            
            # Check if already bookmarked
            already_in_bookmarks = article_object_id in bookmark_ids
            already_in_bookmarked_by = user_object_id in article_bookmarked_by_ids
            
            if not already_in_bookmarks and not already_in_bookmarked_by:
                # Update user's bookmarks list
                user_result = await self.db.users.update_one(
                    {"_id": user_object_id},
                    {"$addToSet": {"bookmarks": article_object_id}}
                )
                
                # Update the article's bookmarked_by list
                article_result = await self.db.articles.update_one(
                    {"_id": article_object_id},
                    {"$addToSet": {"bookmarked_by": user_object_id}}
                )
                
                if user_result.modified_count and article_result.modified_count:
                    return {"status": "success", "message": "Article bookmarked successfully"}
                elif user_result.modified_count:
                    return {"status": "partial", "message": "Added to your bookmarks, but couldn't update article's bookmarked_by list"}
                else:
                    raise Exception("Failed to update bookmarks/bookmarked_by lists")
            else:
                # Handle different cases of partial relationship
                if already_in_bookmarks and not already_in_bookmarked_by:
                    # Fix one-sided relationship
                    article_result = await self.db.articles.update_one(
                        {"_id": article_object_id},
                        {"$addToSet": {"bookmarked_by": user_object_id}}
                    )
                    if article_result.modified_count:
                        return {"status": "fixed", "message": "Fixed one-sided bookmark relationship"}
                    else:
                        raise Exception("Failed to update article's bookmarked_by list")
                elif not already_in_bookmarks and already_in_bookmarked_by:
                    # Fix one-sided relationship
                    user_result = await self.db.users.update_one(
                        {"_id": user_object_id},
                        {"$addToSet": {"bookmarks": article_object_id}}
                    )
                    if user_result.modified_count:
                        return {"status": "fixed", "message": "Fixed one-sided bookmark relationship"}
                    else:
                        raise Exception("Failed to update bookmarks list")
                else:
                    return {"status": "info", "message": "Article already bookmarked"}
                
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error bookmarking article: {str(e)}")
        
    async def remove_bookmark(self, user_id: str, article_id: str) -> Dict[str, str]:
        """Remove an article bookmark"""
        try:
            # Convert article_id to ObjectId
            article_object_id = ensure_object_id(article_id)
            
            # Check if article exists
            article = await self.db.articles.find_one({"_id": article_object_id})
            if not article:
                raise ValueError("Article not found")
            
            # Get the user
            user_object_id = ensure_object_id(user_id)
            
            # Remove article from user's bookmarks list
            user_result = await self.db.users.update_one(
                {"_id": user_object_id},
                {"$pull": {"bookmarks": article_object_id}}
            )
            
            # Remove user from article's bookmarked_by list
            article_result = await self.db.articles.update_one(
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
                
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error removing bookmark: {str(e)}")
    
    async def get_user_bookmarks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all bookmarked articles for a user with full details"""
        try:
            # Get the user and their bookmarks
            user_object_id = ensure_object_id(user_id)
            user = await self.db.users.find_one({"_id": user_object_id})
            if not user:
                raise ValueError("User not found")
                
            bookmarked_articles = []
            
            # Access bookmarks list
            bookmarks = user.get("bookmarks", [])
            for article_id in bookmarks:
                # Convert string ID to ObjectId
                try:
                    object_id = ObjectId(article_id)
                    article = await self.db.articles.find_one({"_id": object_id})
                    
                    if article:
                        # Convert the article to a JSON serializable format
                        article = clean_document(article)

                        # If article has a main file image, fetch the file details
                        if article.get("image_id"):
                            file_id = article.get("image_id")
                            file_dict = await self.db.files.find_one({"file_id": file_id})
                            
                            if file_dict:
                                # Create file object with file details
                                file_obj = {
                                    "file_id": file_dict.get("file_id"),
                                    "file_type": file_dict.get("file_type"),
                                    "file_extension": file_dict.get("file_extension"),
                                    "size": file_dict.get("size"),
                                    "object_name": file_dict.get("object_name"),
                                    "slug": file_dict.get("slug"),
                                    "unique_string": file_dict.get("unique_string")
                                }
                                article["main_image_file"] = file_obj
                                article["image"] = "DEPRECIATED"
                        
                        # Get the related category
                        category_data = None
                        if "category_id" in article:
                            category = await self.db.categories.find_one({"_id": ObjectId(article["category_id"])})
                            if category:
                                category_data = {
                                    "_id": str(category["_id"]),
                                    "name": category.get("name", ""),
                                    "slug": category.get("slug", "")
                                }
                        
                        # Get the related author with followers
                        author_data = None
                        if "author_id" in article:
                            author = await self.db.users.find_one(
                                {"_id": ObjectId(article["author_id"])},
                                projection={
                                    "_id": 1,
                                    "username": 1,
                                    "first_name": 1,
                                    "last_name": 1,
                                    "profile_picture_base64": 1,
                                    "profile_photo_id": 1,
                                    "followers": 1
                                }
                            )
                            
                            if author:
                                # If user has a profile photo, fetch the file details
                                if author.get("profile_photo_id"):
                                    file_id = author.get("profile_photo_id")
                                    file_dict = await self.db.files.find_one({"file_id": file_id})
                                    
                                    if file_dict:
                                        # Create file object with file details
                                        file_obj = {
                                            "file_id": file_dict.get("file_id"),
                                            "file_type": file_dict.get("file_type"),
                                            "file_extension": file_dict.get("file_extension"),
                                            "size": file_dict.get("size"),
                                            "object_name": file_dict.get("object_name"),
                                            "slug": file_dict.get("slug"),
                                            "unique_string": file_dict.get("unique_string")
                                        }
                                        author["profile_file"] = file_obj
                                        author["profile_picture_base64"] = "DEPRECIATED"
                                # Manually convert the author data
                                author_data = {
                                    "_id": str(author["_id"]),
                                    "username": author.get("username", ""),
                                    "first_name": author.get("first_name", ""),
                                    "last_name": author.get("last_name", ""),
                                    "profile_picture_base64": author.get("profile_picture_base64", ""),
                                    "profile_file": author.get("profile_file", "")
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
                        
                        bookmarked_articles.append(article_with_relations)
                except Exception as e:
                    # Skip problematic articles but continue processing others
                    print(f"Error processing bookmark {article_id}: {str(e)}")
                    continue
            
            # Return the clean serializable response
            return clean_document(bookmarked_articles)
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error getting bookmarks: {str(e)}")
        
    async def decrement_author_articles_count(self, author_id: ObjectId) -> None:
        """
        Decrement an author's article count
        """
        try:
            await self.db.users.update_one(
                {"_id": author_id},
                {"$inc": {"user_details.articles_count": -1}}
            )
        except Exception as e:
            raise Exception(f"Error decrementing author's article count: {str(e)}")   

    async def get_users(self, query: dict, skip: int = 0, limit: int = 100, current_user=None) -> List[Dict[str, Any]]:
        """
        Get users based on a search query with pagination
        Returns a list of user dictionaries with limited fields
        Adds is_following flag if current_user is provided
        """
        try:
            # Set up projection to only return required fields
            projection = {
                "_id": 1,
                "username": 1,
                "first_name": 1,
                "last_name": 1,
                "profile_photo_id": 1,
                "followers": 1  # Include followers to check if current user follows this user
            }
            
            # Find users matching the query with projection
            users_cursor = self.db.users.find(query, projection).skip(skip).limit(limit)
            users = await users_cursor.to_list(length=limit)
            
            # Get current user's ID if available
            current_user_id = None
            if current_user:
                current_user_id = ensure_object_id(current_user.id) if hasattr(current_user, 'id') else None
            
            # Process each user
            result = []
            for user in users:
                # Convert ObjectId to string and create id field
                user_id = str(user["_id"]) if "_id" in user else None
                
                # Check if current user follows this user
                is_following = False
                if current_user_id and "followers" in user and user["followers"]:
                    # Convert follower IDs to strings for comparison
                    follower_ids = [str(follower_id) for follower_id in user.get("followers", [])]
                    is_following = str(current_user_id) in follower_ids
                
                # If user has a profile photo, fetch the file details
                profile_file = None
                if user.get("profile_photo_id"):
                    file_id = user.get("profile_photo_id")
                    file_dict = await self.db.files.find_one({"file_id": file_id})
                    
                    if file_dict:
                        # Create file object with file details
                        profile_file = {
                            "file_id": file_dict.get("file_id"),
                            "file_type": file_dict.get("file_type"),
                            "file_extension": file_dict.get("file_extension"),
                            "size": file_dict.get("size"),
                            "object_name": file_dict.get("object_name"),
                            "slug": file_dict.get("slug"),
                            "unique_string": file_dict.get("unique_string")
                        }
                
                # Create filtered user with proper handling of fields
                filtered_user = {
                    "id": user_id,
                    "username": user.get("username", ""),
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "profile_photo_id": user.get("profile_photo_id", ""),
                    "profile_file": profile_file,
                    "is_following": is_following
                }
                
                # Add to result list
                result.append(filtered_user)
            
            return result
            
        except Exception as e:
            raise Exception(f"Error fetching users: {str(e)}")