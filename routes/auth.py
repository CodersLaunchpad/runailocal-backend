from fastapi import APIRouter, HTTPException, status, Form
from datetime import timedelta

from models.auth_model import Token
from dependencies.auth import AuthServiceDep

from dependencies.db import DB

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    auth_service: AuthServiceDep = None
):
    """
    Authenticate user and return JWT access token
    """
    try:
        token = await auth_service.generate_user_token(username, password)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token
    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )

@router.get("/check-availability")
async def check_availability(
    collection: str, 
    field: str, 
    value: str,
    case_sensitive: bool = False,
    db = DB
):
    """
    Check if a given value for a specified field is available in a collection.

    Query Parameters:
      - collection: The collection name (e.g., "users", "categories").
      - field: The field to check (e.g., "username", "email", "name").
      - value: The value to verify.
      - case_sensitive: Whether the search should be case sensitive (default is False).
    
    Returns:
      - available (bool): True if the value is not taken; False otherwise.
      - message (str): A message indicating the status.
    """
    try:
        coll = db[collection]
        if not case_sensitive:
            # Case-insensitive: use a regex that matches the entire string (ignoring case)
            query = {field: {"$regex": f"^{value}$", "$options": "i"}}
        else:
            query = {field: value}
        
        document = await coll.find_one(query)
        if document:
            return {"available": False, "message": f"{field} is already taken."}
        return {"available": True, "message": f"{field} is available."}
    except Exception:
        return {"available": False, "message": "Unable to check availability currently."}