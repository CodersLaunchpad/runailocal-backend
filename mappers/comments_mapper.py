from models.comments_model import CommentResponse
from db.schemas.comments_schema import CommentInDB
from typing import Dict, Any
from db.mongodb import convert_to_object_id

def comment_db_to_response(comment_db: CommentInDB) -> CommentResponse:
    """Convert database comment schema to API response model"""
    comment_dict = comment_db.model_dump(by_alias=False)
    
    # Only include fields that are in the CommentResponse model
    response_fields = CommentResponse.model_fields.keys()
    filtered_comment = {k: v for k, v in comment_dict.items() if k in response_fields}
    
    # Ensure IDs are strings for JSON serialization
    if "id" in filtered_comment:
        filtered_comment["id"] = str(filtered_comment["id"])
    if "user_id" in filtered_comment:
        filtered_comment["user_id"] = str(filtered_comment["user_id"])
    if "article_id" in filtered_comment:
        filtered_comment["article_id"] = str(filtered_comment["article_id"])
    
    return CommentResponse(**filtered_comment)

def prepare_comment_data(comment_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare comment data for database insertion
    Converts string IDs to ObjectId objects using utility functions
    """
    prepared_data = comment_dict.copy()
    
    # Convert string IDs to ObjectId using existing utility function
    if "user_id" in prepared_data and isinstance(prepared_data["user_id"], str):
        prepared_data["user_id"] = convert_to_object_id(prepared_data["user_id"])
    
    if "article_id" in prepared_data and isinstance(prepared_data["article_id"], str):
        prepared_data["article_id"] = convert_to_object_id(prepared_data["article_id"])
    
    if "id" in prepared_data and isinstance(prepared_data["id"], str):
        prepared_data["id"] = convert_to_object_id(prepared_data["id"])
    
    return prepared_data