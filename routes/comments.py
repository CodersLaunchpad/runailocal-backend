from fastapi import APIRouter, HTTPException, Response, status, Depends
from datetime import datetime
from models.models import PyObjectId, UserInDB, CommentInDB, CommentCreate
from helpers.auth import get_current_active_user
from pymongo import ReturnDocument
from db.db import get_db

router = APIRouter()

@router.post("/", response_model=CommentInDB)
async def create_comment(
    comment: CommentCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        object_id = PyObjectId(comment.article_id)
        
        # Check if article exists
        article = await db.articles.find_one({"_id": object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Create comment object
        comment_obj = {
            "id": PyObjectId(),
            "text": comment.text,
            "user_id": current_user.id,
            "username": current_user.username,
            "user_type": current_user.user_details.get("type", "normal"),
            "created_at": datetime.now(datetime.timezone.utc)
        }
        
        # Add comment to article
        updated_article = await db.articles.find_one_and_update(
            {"_id": object_id},
            {"$push": {"comments": comment_obj}},
            return_document=ReturnDocument.AFTER
        )
        
        if not updated_article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Return the new comment
        return comment_obj
    except:
        raise HTTPException(status_code=400, detail="Invalid article ID")

@router.put("/{article_id}/{comment_id}", response_model=CommentInDB)
async def update_comment(
    article_id: str,
    comment_id: str,
    text: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        article_object_id = PyObjectId(article_id)
        comment_object_id = PyObjectId(comment_id)
        
        # Get the article
        article = await db.articles.find_one({"_id": article_object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Find the comment
        comment = None
        for c in article.get("comments", []):
            if str(c.get("id")) == str(comment_object_id):
                comment = c
                break
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user is comment author or admin
        if str(comment.get("user_id")) != str(current_user.id) and current_user.user_details.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Update the comment
        updated_article = await db.articles.find_one_and_update(
            {
                "_id": article_object_id,
                "comments.id": comment_object_id
            },
            {
                "$set": {
                    "comments.$.text": text,
                    "comments.$.updated_at": datetime.now(datetime.timezone.utc)
                }
            },
            return_document=ReturnDocument.AFTER
        )
        
        if not updated_article:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Find the updated comment
        updated_comment = None
        for c in updated_article.get("comments", []):
            if str(c.get("id")) == str(comment_object_id):
                updated_comment = c
                break
        
        return updated_comment
    except:
        raise HTTPException(status_code=400, detail="Invalid article or comment ID")

@router.delete("/{article_id}/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    article_id: str,
    comment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db = Depends(get_db)
):
    try:
        article_object_id = PyObjectId(article_id)
        comment_object_id = PyObjectId(comment_id)
        
        # Get the article
        article = await db.articles.find_one({"_id": article_object_id})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        
        # Find the comment
        comment = None
        for c in article.get("comments", []):
            if str(c.get("id")) == str(comment_object_id):
                comment = c
                break
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user is comment author or admin
        if str(comment.get("user_id")) != str(current_user.id) and current_user.user_details.get("type") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        
        # Remove the comment
        await db.articles.update_one(
            {"_id": article_object_id},
            {"$pull": {"comments": {"id": comment_object_id}}}
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise HTTPException(status_code=400, detail="Invalid article or comment ID")
