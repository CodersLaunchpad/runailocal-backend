from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from datetime import datetime
from models.models import ArticleStatus
from repos.article_repo import ArticleRepository
from repos.user_repo import UserRepository
from db.db import get_db
from dependencies.auth import get_current_user
from bson.objectid import ObjectId
from dependencies.auth import CurrentActiveUser, AdminUser, OptionalUser, get_current_user_optional

router = APIRouter()

@router.get("/articles")
async def search_articles(
    query: str = Query(..., description="Search query string"),
    category: Optional[str] = Query(None, description="Filter by category slug or ID"),
    author: Optional[str] = Query(None, description="Filter by author username or ID"),
    start_date: Optional[datetime] = Query(None, description="Filter articles created after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter articles created before this date"),
    skip: int = Query(0, description="Number of results to skip"),
    limit: Optional[int] = Query(None, description="Maximum number of results to return. If not provided, returns all matching articles."),
    db = Depends(get_db),
    current_user = Depends(get_current_user)  # Optional dependency
):
    """
    Public search endpoint for articles.
    Only shows published articles.
    Search across article name, content, author name, and author username.
    Returns all matching articles by default unless limit is specified.
    If user is authenticated, includes bookmark information for each article.
    """
    article_repo = ArticleRepository(db)
    
    # First, find matching authors
    author_query = {
        "$or": [
            {"username": {"$regex": query, "$options": "i"}},
            {"first_name": {"$regex": query, "$options": "i"}},
            {"last_name": {"$regex": query, "$options": "i"}}
        ]
    }
    matching_authors = await db.users.find(author_query).to_list(None)
    author_ids = [author["_id"] for author in matching_authors]
    
    # Build the search query
    search_query = {
        "status": "published",  # Only show published articles
        "$or": [
            {"$text": {"$search": query}},  # Search in article text fields
            {"author_id": {"$in": author_ids}}  # Include articles by matching authors
        ]
    }
    
    # Add filters if provided
    if category:
        if ObjectId.is_valid(category):
            search_query["category_id"] = ObjectId(category)
        else:
            category_obj = await db.categories.find_one({"slug": category})
            if category_obj:
                search_query["category_id"] = category_obj["_id"]
    
    if author:
        if ObjectId.is_valid(author):
            search_query["author_id"] = ObjectId(author)
        else:
            author_obj = await db.users.find_one({"username": author})
            if author_obj:
                search_query["author_id"] = author_obj["_id"]
    
    if start_date or end_date:
        search_query["created_at"] = {}
        if start_date:
            search_query["created_at"]["$gte"] = start_date
        if end_date:
            search_query["created_at"]["$lte"] = end_date
    
    # Get total count for pagination
    total_count = await db.articles.count_documents(search_query)
    
    # Get articles with the search query
    # If limit is None, we'll get all articles by setting a very high limit
    effective_limit = limit if limit is not None else total_count
    
    articles = await article_repo.get_articles(
        query=search_query,
        skip=skip,
        limit=effective_limit,  # Use effective_limit instead of None
        current_user=current_user  # Pass current_user to include bookmark information
    )
    
    return {
        "articles": articles,
        "total": total_count,
        "skip": skip,
        "limit": limit  # Return the original limit (None if not specified)
    } 

@router.get("/users")
async def search_users(
    query: str = Query(..., description="Search query string"),
    skip: int = Query(0, description="Number of results to skip"),
    limit: Optional[int] = Query(None, description="Maximum number of results to return. If not provided, returns all matching users."),
    db = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Public search endpoint for users.
    Search across first name, last name, and username.
    Returns all matching users by default unless limit is specified.
    Includes is_following flag for each user if request is authenticated.
    """
    user_repo = UserRepository(db)
    
    # Build the search query for users
    search_query = {
        "$or": [
            {"username": {"$regex": query, "$options": "i"}},
            {"first_name": {"$regex": query, "$options": "i"}},
            {"last_name": {"$regex": query, "$options": "i"}}
        ]
    }
    
    # Get total count for pagination
    total_count = await db.users.count_documents(search_query)
    
    # Get users with the search query
    # If limit is None, we'll get all users by setting a very high limit
    effective_limit = limit if limit is not None else total_count
    
    users = await user_repo.get_users(
        query=search_query,
        skip=skip,
        limit=effective_limit,
        current_user=current_user  # Pass current_user to check following status
    )
    
    return {
        "users": users,
        "total": total_count,
        "skip": skip,
        "limit": limit  # Return the original limit (None if not specified)
    }