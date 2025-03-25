from typing import Dict, Any, List
from datetime import datetime, timezone

from bson import ObjectId

from db.schemas.comments_schema import CommentInDB
from models.comments_model import CommentCreate, CommentResponse
from db.schemas.users_schema import UserInDB
from models.models import ensure_object_id
from repos.comment_repo import CommentRepository
from repos.article_repo import ArticleRepository
from mappers.comments_mapper import comment_db_to_response

class CommentService:
    """
    Service layer for comment-related operations
    Handles business logic between controllers and data access
    """
    
    def __init__(self, comment_repository: CommentRepository, article_repository: ArticleRepository = None):
        self.comment_repo = comment_repository
        self.article_repo = article_repository
    
    async def create_comment(self, comment: CommentCreate, current_user: UserInDB) -> CommentResponse:
        """Create a new comment on an article"""
        try:
            # Check if article exists by ID
            article = await self.article_repo.get_article_by_id(comment.article_id)
            if not article:
                raise ValueError("Article not found")

            # Prepare comment data with all required fields
            comment_data = {
                "text": comment.text,
                "article_id": ObjectId(comment.article_id),
                "parent_comment_id": ObjectId(comment.parent_comment_id) if ObjectId.is_valid(comment.parent_comment_id) else None,
                "user_id": ObjectId(current_user.id),
                "username": current_user.username,
                "user_first_name": current_user.first_name,
                "user_last_name": current_user.last_name,
                "user_type": current_user.user_details.get("type", "normal"),
                "created_at": datetime.now(timezone.utc)
            }

            # Call repository to save comment
            comment_db = await self.comment_repo.add_comment_to_article(comment.article_id, comment_data)
            
            # Ensure all required fields are present in the response
            comment_db["id"] = comment_db["_id"]
            
            # Convert to API response model
            return comment_db_to_response(comment_db)
        except Exception as e:
            raise Exception(f"Error creating comment: {str(e)}")
    
    async def update_comment(self, article_id_or_slug: str, comment_id: str, text: str, current_user: UserInDB) -> CommentResponse:
        """Update an existing comment"""
        try:
            # Get the article by ID or slug if it's provided
            if article_id_or_slug and not ObjectId.is_valid(article_id_or_slug):
                # It's a slug
                article = await self.article_repo.get_article_by_slug(article_id_or_slug)
                if not article:
                    raise ValueError("Article not found")
                article_id = str(article.get("_id"))
            else:
                # It's already an ID
                article_id = article_id_or_slug
            
            # Get the comment 
            comment_db = await self.comment_repo.get_comment_by_id(comment_id)
           
            if not comment_db:
                raise ValueError("Comment not found")
                        
            # Check if user is comment author or admin
            if str(comment_db.get("user_id")) != str(current_user.id) and current_user.user_type != "admin":
                raise PermissionError("Not enough permissions")

            # Update data
            update_data = {
                "text": text,
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Call repository to update comment
            updated_comment = await self.comment_repo.update_comment(comment_id, update_data)
            if not updated_comment:
                raise ValueError("Failed to update comment")
            
            response_data = {
            "id": updated_comment.get("_id"),
            "parent_comment_id": updated_comment["parent_comment_id"],
            "text": updated_comment.get("text"),
            "article_id": article_id,
            "user_id": str(current_user.id),
            "username": current_user.username,
            "user_first_name": current_user.first_name,
            "user_last_name": current_user.last_name,
            "user_type": current_user.user_details.get("type", "normal"),
            "created_at": updated_comment["created_at"],  # Keep original creation time
            "updated_at": updated_comment["updated_at"]  # Use the new update time
            }
            
            
            # Convert to API response model
            return comment_db_to_response(response_data)
        except Exception as e:
            raise Exception(f"Error updating comment: {str(e)}")
    
    async def delete_comment(self, article_id_or_slug: str, comment_id: str, current_user: UserInDB) -> bool:
        """Delete a comment"""
        try:
            # Get the article by ID or slug if provided 
            if article_id_or_slug and not ObjectId.is_valid(article_id_or_slug):
                # It's a slug
                article = await self.article_repo.get_article_by_slug(article_id_or_slug)
                if not article:
                    raise ValueError("Article not found")
            
            # Get the comment
            comment_db = await self.comment_repo.get_comment_by_id(comment_id)
            if not comment_db:
                raise ValueError("Comment not found")

            
            # Check if user is comment author or admin
            if str(comment_db.get("user_id")) != str(current_user.id) and current_user.user_type != "admin":
                raise PermissionError("Not enough permissions")
            
            # Call repository to delete the comment
            success = await self.comment_repo.soft_delete_comment(comment_id)
            if not success:
                raise ValueError("Failed to delete comment")
                
            return True
        except Exception as e:
            raise Exception(f"Error deleting comment: {str(e)}")
    
    async def get_all_comments(self, article_identifier: str) -> List[CommentResponse]:
        """Get all comments for an article"""
        try:
            # Auto-detect if identifier is an ID or slug
            if ObjectId.is_valid(article_identifier):
                article = await self.article_repo.get_article_by_id(article_identifier)
            else:
                article = await self.article_repo.get_article_by_slug(article_identifier)
                
            if not article:
                raise ValueError("Article not found")
            
            # Get the article ID
            article_id = str(article.get("_id"))
            
            # Get all comments
            comments_db = await self.comment_repo.get_all_comments_for_article(article_id)
            # Convert to API response models
            return [comment_db_to_response(comment) for comment in comments_db]
        except Exception as e:
            raise Exception(f"Error getting comments: {str(e)}")
            
    async def get_comments_by_ids(self, comment_ids: List[str]) -> List[CommentResponse]:
        """Get multiple comments by their IDs"""
        try:
            # Validate comment IDs
            if not comment_ids:
                return []
            
            # Get comments by IDs
            comments_db = await self.comment_repo.get_comments_by_ids(comment_ids)
            
            # Convert to API response models
            return [comment_db_to_response(comment) for comment in comments_db]
        except Exception as e:
            raise Exception(f"Error getting comments by IDs: {str(e)}")
            
    async def get_comments_tree(self, article_identifier: str) -> List[Dict[str, Any]]:
        """
        Get hierarchical comments tree for an article
        Returns a structured tree of comments with parent-child relationships
        
        Parameters:
        - article_identifier: Either the ID or slug of the article (auto-detected)
        """
        try:
            # Auto-detect if identifier is an ID or slug
            if ObjectId.is_valid(article_identifier):
                article = await self.article_repo.get_article_by_id(article_identifier)
            else:
                article = await self.article_repo.get_article_by_slug(article_identifier)
                
            if not article:
                raise ValueError("Article not found")
            
            # Get the article ID
            article_id = str(article.get("_id"))
            
            # Convert article_id to ObjectId if it's a string
            if isinstance(article_id, str):
                article_obj_id = ObjectId(article_id)
            else:
                article_obj_id = article_id
                
            # Get all comments for the article
            all_comments = await self.comment_repo.get_all_comments_for_article(str(article_obj_id))
            
            if not all_comments:
                return []
            
            # Process comments to handle ObjectIds
            for comment in all_comments:
                # Ensure we have string IDs
                if "_id" in comment and isinstance(comment["_id"], ObjectId):
                    comment["_id"] = str(comment["_id"])
                if "id" not in comment and "_id" in comment:
                    comment["id"] = comment["_id"]
                if "article_id" in comment and isinstance(comment["article_id"], ObjectId):
                    comment["article_id"] = str(comment["article_id"])
                if "parent_comment_id" in comment and isinstance(comment["parent_comment_id"], ObjectId):
                    comment["parent_comment_id"] = str(comment["parent_comment_id"])
            
            # Create a dictionary of comments by ID
            comments_by_id = {}
            for comment in all_comments:
                comment_id = comment.get("id", comment.get("_id"))
                comment["children"] = []
                comments_by_id[comment_id] = comment
            
            # Build the tree
            root_comments = []
            for comment in all_comments:
                comment_id = comment.get("id", comment.get("_id"))
                parent_id = comment.get("parent_comment_id")
                
                if not parent_id:
                    # This is a root comment
                    root_comments.append(comment)
                else:
                    # Add this comment as a child to its parent
                    if parent_id in comments_by_id:
                        comments_by_id[parent_id]["children"].append(comment)
            
            # Convert to response format
            return self._prepare_comment_tree_response(root_comments)
        except Exception as e:
            import traceback
            print(f"Error in get_comments_tree: {str(e)}")
            print(traceback.format_exc())
            raise Exception(f"Error building comments tree: {str(e)}")
    
    def _prepare_comment_tree_response(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Helper method to convert comments tree to proper response format"""
        result = []
        for comment in comments:
            # Convert current comment to response format
            comment_response = comment_db_to_response(comment)
            response_dict = comment_response.model_dump()
            
            # Process children recursively if present
            if "children" in comment and comment["children"]:
                response_dict["children"] = self._prepare_comment_tree_response(comment["children"])
            else:
                response_dict["children"] = []
                
            result.append(response_dict)
        return result