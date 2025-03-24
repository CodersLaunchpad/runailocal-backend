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
            # # Add comment to article
            # result = await self.db.articles.update_one(
            #     {"_id": article_object_id},
            #     {"$push": {"comments": comment_obj}}
            # )
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
            
            # Update the comment with deleted_at timestamp
            result = await self.db.comments.find_one_and_update(
            {"_id": comment_object_id},
            {
                "$set": {
                    "deleted_at": datetime.now(timezone.utc)
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
            # Query for all comments for this article where deleted_at doesn't exist
            cursor = self.db.comments.find({
                "article_id": article_id,
                "deleted_at": {"$exists": False}
            })
            
            # Convert cursor to list
            comments = await cursor.to_list(length=100)
            
            # Convert ObjectIds to strings for JSON serialization
            for comment in comments:
                if isinstance(comment.get("_id"), ObjectId):
                    comment["_id"] = str(comment["_id"])
                if isinstance(comment.get("user_id"), ObjectId):
                    comment["user_id"] = str(comment["user_id"])
                if isinstance(comment.get("article_id"), ObjectId):
                    comment["article_id"] = str(comment["article_id"])
                  
           
            return comments
        
        except Exception as e:
            raise Exception(f"Error in get_all_comments_for_article: {str(e)}")