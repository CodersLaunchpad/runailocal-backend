from models.comments_model import CommentResponse, AuthorInfo
from db.schemas.comments_schema import CommentInDB
from typing import Dict, Any, Optional
from db.mongodb import convert_to_object_id
from models.models import prepare_mongo_document, clean_document
from datetime import datetime


def comment_db_to_response(comment_db: CommentInDB) -> CommentResponse:
    """Convert database comment schema to API response model"""
    comment_dict = clean_document(prepare_mongo_document(comment_db))
    
    # Ensure all required fields are present with default values
    response_data = {
        "id": str(comment_dict.get("_id", comment_dict.get("id", ""))),
        "text": comment_dict.get("text", ""),
        "article_id": str(comment_dict.get("article_id", "")),
        "parent_comment_id": str(comment_dict.get("parent_comment_id")) if comment_dict.get("parent_comment_id") else None,
        "user_id": str(comment_dict.get("user_id", "")),
        "username": comment_dict.get("username", "Unknown User"),
        "user_first_name": comment_dict.get("user_first_name", "Unknown"),
        "user_last_name": comment_dict.get("user_last_name", "User"),
        "user_type": comment_dict.get("user_type", "normal"),
        "created_at": comment_dict.get("created_at", datetime.utcnow()),
        "updated_at": comment_dict.get("updated_at")
    }
    
    # Create author info object
    author_info = {
        "id": str(comment_dict.get("user_id", "")),
        "username": comment_dict.get("username", "Unknown User"),
        "first_name": comment_dict.get("user_first_name", "Unknown"),
        "last_name": comment_dict.get("user_last_name", "User"),
        "profile_picture_base64": "DEPRECIATED",
        "bookmarks": comment_dict.get("bookmarks", []),
        "profile_photo_id": comment_dict.get("profile_photo_id"),
        "profile_file": comment_dict.get("profile_file"),
        "user_type": comment_dict.get("user_type", "normal")
    }
    
    # Add author info to response data
    response_data["author"] = author_info
    
    return CommentResponse(**response_data)

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
    
    if "parent_comment_id" in prepared_data and isinstance(prepared_data["parent_comment_id"], str):
        prepared_data["parent_comment_id"] = convert_to_object_id(prepared_data["parent_comment_id"])
    
    return prepared_data