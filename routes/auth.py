from fastapi import APIRouter, HTTPException, status, Depends
from models.models import Token
from datetime import datetime, timedelta

from fastapi.security import OAuth2PasswordRequestForm
from helpers.auth import create_access_token, authenticate_user
from db.db import get_db

from config import JWT_ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login time
    await db.users.update_one(
        {"_id": user.id}, 
        {"$set": {"last_login": datetime.now(datetime.timezone.utc)}}
    )
    
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username, 
            "id": str(user.id), 
            "type": user.user_details.get("type", "normal")
        },
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
