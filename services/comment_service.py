from typing import Dict, Any, List
from datetime import datetime, timezone
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
            # Check if article exists
            article = await self.article_repo.get_article_by_id(comment.article_id)
            if not article:
                raise ValueError("Article not found")
            
            # Prepare comment data using a Pydantic model
            comment_data = CommentCreate(
            text=comment.text,
            article_id=comment.article_id,
            parent_comment_id = comment.parent_comment_id,
            user_id=current_user.id,
            username=current_user.username,
            user_type=current_user.user_details.get("type", "normal"),
            created_at=datetime.now(timezone.utc)
            )
        
            # Convert the Pydantic model to a dictionary
            comment_data_dict = comment_data.dict()  # Convert to dictionary
        
            # Call repository to save comment
            comment_db = await self.comment_repo.add_comment_to_article(comment.article_id,comment_data_dict)
            
            comment_db['id'] = (comment_db['_id'])
            comment_db['user_id'] = current_user.id
            comment_db['username'] = current_user.username
            comment_db['user_first_name'] = current_user.first_name
            comment_db['user_last_name'] = current_user.last_name
            comment_db['user_type'] = current_user.user_details.get("type", "normal")
            comment_db['created_at'] = datetime.now(timezone.utc)
            # Convert to API response model
            return comment_db_to_response(comment_db)
        except Exception as e:
            raise Exception(f"Error creating comment: {str(e)}")
    
    async def update_comment(self, article_id: str, comment_id: str, text: str, current_user: UserInDB) -> CommentResponse:
        """Update an existing comment"""
        try:
            # Check if article exists
            article = await self.article_repo.get_article_by_id(article_id)
            if not article:
                raise ValueError("Article not found")
            
            # Get the comment
            comment_db = await self.comment_repo.get_comment_from_article(article_id, comment_id)
            if not comment_db:
                raise ValueError("Comment not found")
            
            # Check if user is comment author or admin
            if str(comment_db.user_id) != str(current_user.id) and current_user.user_type != "admin":
                raise PermissionError("Not enough permissions")
            
            # Update data
            update_data = {
                "text": text,
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Call repository to update comment
            updated_comment_db = await self.comment_repo.update_comment_in_article(article_id, comment_id, update_data)
            if not updated_comment_db:
                raise ValueError("Failed to update comment")
            
            # Convert to API response model
            return comment_db_to_response(updated_comment_db)
        except Exception as e:
            raise Exception(f"Error updating comment: {str(e)}")
    
    async def delete_comment(self, article_id: str, comment_id: str, current_user: UserInDB) -> bool:
        """Delete a comment"""
        try:
            # Check if article exists
            article = await self.article_repo.get_article_by_id(article_id)
            if not article:
                raise ValueError("Article not found")
            
            # Get the comment
            comment_db = await self.comment_repo.get_comment_from_article(article_id, comment_id)
            if not comment_db:
                raise ValueError("Comment not found")
            
            # Check if user is comment author or admin
            if str(comment_db.user_id) != str(current_user.id) and current_user.user_type != "admin":
                raise PermissionError("Not enough permissions")
            
            # Call repository to delete the comment
            success = await self.comment_repo.delete_comment_from_article(article_id, comment_id)
            if not success:
                raise ValueError("Failed to delete comment")
                
            return True
        except Exception as e:
            raise Exception(f"Error deleting comment: {str(e)}")
    
    async def get_all_comments(self, article_id: str) -> List[CommentResponse]:
        """Get all comments for an article"""
        try:
            # Check if article exists
            article = await self.article_repo.get_article_by_id(article_id)
            if not article:
                raise ValueError("Article not found")
            
            # Get all comments
            comments_db = await self.comment_repo.get_all_comments_for_article(article_id)
            
            # Convert to API response models
            return [comment_db_to_response(comment) for comment in comments_db]
        except Exception as e:
            raise Exception(f"Error getting comments: {str(e)}")