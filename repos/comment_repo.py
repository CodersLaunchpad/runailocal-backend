from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Coroutine
from bson import ObjectId
from click.testing import Result

from models.models import PyObjectId
from db.schemas.comments_schema import CommentInDB 

class CommentRepository:
    """
    Repository for comment-related database operations
    Handles all direct interactions with the database for comments
    """
    
    def __init__(self, db):
        self.db = db
    
    async def add_comment_to_article(self, article_id: str, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a comment to an article
        Returns the created comment data
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Create comment object with a unique ID
            # comment_obj = {
            #     "id": PyObjectId(),
            #     **comment_data
            # }
            
            result = await self.db.comments.insert_one(comment_data)
            
            # Add comment ID to article's comments array
            await self.db.articles.update_one(
                {"_id": article_object_id},
                {"$push": {"comments": result.inserted_id}}
            )
            
            created_comment = await self.db.comments.find_one({"_id": result.inserted_id})
            if created_comment:
                created_comment["_id"] = str(created_comment["_id"])  # Convert ObjectId to string

            
            return created_comment
        except Exception as e:
            raise Exception(f"Error in add_comment_to_article: {str(e)}")
        
    async def get_comment_by_id(self,comment_id: str):
        """
        Get a specific comment from comment repo
        Returns the comment if found, None otherwise
        """
        try:
            comment_object_id = ObjectId(comment_id)
            result = await self.db.comments.find_one(comment_object_id)
            if not result:
                return None

            return result
        except Exception as e:
            raise Exception(f"Error in get_comment: {str(e)}")
    
    async def get_comment_from_article(self, article_id: str, comment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific comment from an article
        Returns the comment if found, None otherwise
        """
        try:
            # Convert IDs to ObjectId
            article_object_id = ObjectId(article_id)
            comment_object_id = ObjectId(comment_id)
            
            # Use aggregation to find the specific comment
            pipeline = [
                {"$match": {"_id": article_object_id}},
                {"$unwind": "$comments"},
                {"$match": {"comments.id": comment_object_id}},
                {"$project": {"comment": "$comments", "_id": 0}}
            ]
            
            result = await self.db.articles.aggregate(pipeline).to_list(length=1)
            
            if not result:
                return None
                
            return result[0]["comment"]
        except Exception as e:
            raise Exception(f"Error in get_comment_from_article: {str(e)}")

    async def update_comment(self, comment_id: str, update_data: Dict[str, Any]) -> Any | None:
        """
       Update a comment in comments collection
       Returns True if successful, False otherwise
       """
        try:
            comment_object_id = ObjectId(comment_id)
            update_result = await self.db.comments.find_one_and_update(
                    {"_id": comment_object_id},
                    {"$set": update_data},
                    return_document=True
                    )
            if not update_result:
                    return None

                    # Convert ObjectId to string for the response
            if isinstance(update_result.get("_id"), ObjectId):
                update_result["_id"] = str(update_result["_id"])

                return update_result
            
        except Exception as e:
            raise Exception(f"Error in update_comment_in_article: {str(e)}")
        
        
    async def update_comment_in_article(self, article_id: str, comment_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update a comment in an article
        Returns True if successful, False otherwise
        """
        try:
            # Convert IDs to ObjectId
            article_object_id = ObjectId(article_id)
            comment_object_id = ObjectId(comment_id)
            
            # Prepare the update operations
            update_operations = {
                f"comments.$.{key}": value for key, value in update_data.items()
            }
            
            # Update the comment
            result = await self.db.articles.update_one(
                {
                    "_id": article_object_id,
                    "comments.id": comment_object_id
                },
                {"$set": update_operations}
            )
            
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error in update_comment_in_article: {str(e)}")
    
    async def delete_comment_from_article(self, article_id: str, comment_id: str) -> bool:
        """
        Delete a comment from an article
        Returns True if successful, False otherwise
        """
        try:
            # Convert IDs to ObjectId
            article_object_id = ObjectId(article_id)
            comment_object_id = ObjectId(comment_id)
            
            # Remove the comment
            result = await self.db.articles.update_one(
                {"_id": article_object_id},
                {"$pull": {"comments": {"id": comment_object_id}}}
            )
            
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Error in delete_comment_from_article: {str(e)}")


    async def soft_delete_comment(self,comment_id: str) -> bool:
        """
            Delete a comment from comments collections
            Returns True if successful, False otherwise
        """
        try:
            
            # Convert IDs to ObjectId
            comment_object_id = ObjectId(comment_id)
            
            # Get the comment to find its article_id
            comment = await self.db.comments.find_one({"_id": comment_object_id})
            if comment and "article_id" in comment:
                # Remove the comment ID from the article's comments array
                await self.db.articles.update_one(
                    {"_id": comment["article_id"]},
                    {"$pull": {"comments": comment_object_id}}
                )
            
            # Update the comment with deleted_at timestamp
            result = await self.db.comments.find_one_and_update(
            {"_id": comment_object_id},
            {
                "$set": {
                    "deleted_at": datetime.now(timezone.utc),
                    "author": None,
                    "user_type": None,
                    "username":None,
                    "user_first_name":None,
                    "user_last_name": None,
                }
            },
            return_document=True
        )

            return result
        except Exception as e:
            raise Exception(f"Error in delete_comment repo: {str(e)}")

    # async def get_all_comments_for_article(self, article_id: str) -> List[Dict[str, Any]]:
    #     """
    #     Get all comments for an article
    #     Returns a list of comments
        # """
        # try:
        #     # Convert article_id to ObjectId
        #     article_object_id = ObjectId(article_id)
        #     
        #     # Get the article's comments
        #     article = await self.db.articles.find_one(
        #         {"_id": article_object_id},
        #         {"comments": 1, "_id": 0}
        #     )
        #     
        #     if not article:
        #         return []
        #         
        #     return article.get("comments", [])
        # except Exception as e:
        #     raise Exception(f"Error in get_all_comments_for_article: {str(e)}")
        # 
        # 
    async def get_all_comments_for_article(self, article_id: str) -> List[Dict[str, Any]]:
        """
        Get all non-deleted comments for a specific article
        Returns a list of comments, excluding those that have been soft deleted
        """
        try:
            # Convert string ID to ObjectId if needed
            article_obj_id = article_id
            if isinstance(article_id, str) and ObjectId.is_valid(article_id):
                article_obj_id = ObjectId(article_id)
            
            # Query for all comments for this article where deleted_at doesn't exist
            cursor = self.db.comments.find({
                "article_id": article_obj_id,
                "deleted_at": {"$exists": False}
            })
            
            # Convert cursor to list
            comments = await cursor.to_list(length=100)
            
            # Convert ObjectIds to strings for JSON serialization
            for comment in comments:
                if isinstance(comment.get("_id"), ObjectId):
                    comment["_id"] = str(comment["_id"])
                    comment["id"] = comment["_id"]  # Add id field for consistency
                if isinstance(comment.get("article_id"), ObjectId):
                    comment["article_id"] = str(comment["article_id"])
                if isinstance(comment.get("parent_comment_id"), ObjectId):
                    comment["parent_comment_id"] = str(comment["parent_comment_id"])
                
                # Safely get user information if user_id exists
                if "user_id" in comment:
                    user_id = comment["user_id"]
                    if isinstance(user_id, str):
                        user_id = ObjectId(user_id)
                    elif isinstance(user_id, ObjectId):
                        user_id = user_id
                    else:
                        continue  # Skip if user_id is in an invalid format
                        
                    user = await self.db.users.find_one({"_id": user_id})
                    if user:
                        # Basic user information
                        comment["user_id"] = str(user["_id"])
                        comment["username"] = user.get("username")
                        comment["user_first_name"] = user.get("first_name")
                        comment["user_last_name"] = user.get("last_name")
                        comment["user_type"] = user.get("user_details", {}).get("type", "normal")
                        
                        # Add bookmarks for author
                        comment["bookmarks"] = [str(bookmark_id) for bookmark_id in user.get("bookmarks", [])]
                        
                        # Add profile photo information
                        profile_photo_id = user.get("profile_photo_id")
                        if profile_photo_id:
                            comment["profile_photo_id"] = profile_photo_id
                            # Get the file details
                            file = await self.db.files.find_one({"file_id": profile_photo_id})
                            if file:
                                profile_file = {
                                    "file_id": file.get("file_id"),
                                    "file_type": file.get("file_type"),
                                    "file_extension": file.get("file_extension"),
                                    "size": file.get("size"),
                                    "object_name": file.get("object_name"),
                                    "slug": file.get("slug"),
                                    "unique_string": file.get("unique_string")
                                }
                                comment["profile_file"] = profile_file
                    else:
                        # Set default values if user not found
                        comment["user_id"] = str(user_id)
                        comment["username"] = "Unknown User"
                        comment["user_first_name"] = "Unknown"
                        comment["user_last_name"] = "User"
                        comment["user_type"] = "normal"
                        comment["bookmarks"] = []
            
            return comments
        except Exception as e:
            import traceback
            print(f"Error in get_all_comments_for_article: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Error in get_all_comments_for_article: {str(e)}")
            
    async def get_comments_by_ids(self, comment_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple comments by their IDs
        Returns a list of comments, excluding those that have been soft deleted
        """
        try:
            # Convert string IDs to ObjectIds
            object_ids = [ObjectId(comment_id) for comment_id in comment_ids if ObjectId.is_valid(comment_id)]
            
            if not object_ids:
                return []
                
            # Query for comments with matching IDs and where deleted_at doesn't exist
            cursor = self.db.comments.find({
                "_id": {"$in": object_ids},
                "deleted_at": {"$exists": False}
            })
            
            # Convert cursor to list
            comments = await cursor.to_list(length=len(object_ids))
            
            # Get user information for each comment
            for comment in comments:
                # Convert ObjectIds to strings for JSON serialization first
                if isinstance(comment.get("_id"), ObjectId):
                    comment["_id"] = str(comment["_id"])
                    comment["id"] = comment["_id"]  # Add id field for consistency
                if isinstance(comment.get("article_id"), ObjectId):
                    comment["article_id"] = str(comment["article_id"])
                if isinstance(comment.get("parent_comment_id"), ObjectId):
                    comment["parent_comment_id"] = str(comment["parent_comment_id"])
                
                # Safely get user information if user_id exists
                if "user_id" in comment:
                    user_id = comment["user_id"]
                    if isinstance(user_id, str):
                        user_id = ObjectId(user_id)
                    elif isinstance(user_id, ObjectId):
                        user_id = user_id
                    else:
                        continue  # Skip if user_id is in an invalid format
                        
                    user = await self.db.users.find_one({"_id": user_id})
                    if user:
                        # Basic user information
                        comment["user_id"] = str(user["_id"])
                        comment["username"] = user.get("username")
                        comment["user_first_name"] = user.get("first_name")
                        comment["user_last_name"] = user.get("last_name")
                        comment["user_type"] = user.get("user_details", {}).get("type", "normal")
                        
                        # Add bookmarks for author
                        comment["bookmarks"] = [str(bookmark_id) for bookmark_id in user.get("bookmarks", [])]
                        
                        # Add profile photo information
                        profile_photo_id = user.get("profile_photo_id")
                        if profile_photo_id:
                            comment["profile_photo_id"] = profile_photo_id
                            # Get the file details
                            file = await self.db.files.find_one({"file_id": profile_photo_id})
                            if file:
                                profile_file = {
                                    "file_id": file.get("file_id"),
                                    "file_type": file.get("file_type"),
                                    "file_extension": file.get("file_extension"),
                                    "size": file.get("size"),
                                    "object_name": file.get("object_name"),
                                    "slug": file.get("slug"),
                                    "unique_string": file.get("unique_string")
                                }
                                comment["profile_file"] = profile_file
                    else:
                        # Set default values if user not found
                        comment["user_id"] = str(user_id)
                        comment["username"] = "Unknown User"
                        comment["user_first_name"] = "Unknown"
                        comment["user_last_name"] = "User"
                        comment["user_type"] = "normal"
                        comment["bookmarks"] = []
            
            return comments
        
        except Exception as e:
            raise Exception(f"Error in get_comments_by_ids: {str(e)}")