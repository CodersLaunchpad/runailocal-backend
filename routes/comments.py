from fastapi import APIRouter, HTTPException, Response, status, Depends
from models.comments_model import CommentCreate, CommentResponse
from db.schemas.users_schema import UserInDB
from dependencies.auth import get_current_active_user
from dependencies.comment import CommentServiceDep

router = APIRouter()

@router.post("/", response_model=CommentResponse)
async def create_comment(
    comment: CommentCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    comment_service: CommentServiceDep = None
):
    """Create a new comment on an article"""
    try:
        comment_response = await comment_service.create_comment(comment, current_user)
        return comment_response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create comment: {str(e)}")

@router.put("/{article_id}/{comment_id}", response_model=CommentResponse)
async def update_comment(
    article_id: str,
    comment_id: str,
    text: str,
    current_user: UserInDB = Depends(get_current_active_user),
    comment_service: CommentServiceDep = None
):
    """Update an existing comment"""
    try:
        updated_comment = await comment_service.update_comment(
            article_id, comment_id, text, current_user
        )
        return updated_comment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update comment: {str(e)}")

@router.delete("/{article_id}/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    article_id: str,
    comment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    comment_service: CommentServiceDep = None
):
    """Delete a comment"""
    try:
        await comment_service.delete_comment(article_id, comment_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete comment: {str(e)}")

@router.get("/{article_id}", response_model=list[CommentResponse])
async def get_article_comments(
    article_id: str,
    comment_service: CommentServiceDep = None
):
    """Get all comments for an article"""
    try:
        comments = await comment_service.get_all_comments(article_id)
        return comments
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get comments: {str(e)}")