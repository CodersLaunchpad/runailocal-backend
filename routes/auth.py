from fastapi import APIRouter, HTTPException, status, Depends
from models.models import Token
from datetime import datetime, timedelta, timezone

from fastapi.security import OAuth2PasswordRequestForm
from helpers.auth import create_access_token, authenticate_user
from db.db import get_db

from config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    # print(form_data)
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    await db.users.update_one(
        {"_id": user.id}, 
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    # access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expires = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username, 
            "id": str(user.id), 
            # "type": user.user_details.get("type", "normal"),
            "type": user.user_type
        },
        expires_delta=access_token_expires
    )
    print("profile_picture_base64", user.profile_picture_base64)
    # return {"access_token": access_token, "token_type": "bearer", "profile_picture_base64": user.profile_picture_base64}
    data_to_return = {"access_token": access_token, "token_type": "bearer", "profile_picture_base64": user.profile_picture_base64}
    print("data to return", data_to_return)
    return data_to_return

@router.get("/check-availability")
async def check_availability(
    collection: str, 
    field: str, 
    value: str,
    case_sensitive: bool = False,
    db = Depends(get_db)
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