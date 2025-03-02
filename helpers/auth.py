from fastapi import Depends, HTTPException, status
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from db.db import get_db
from config import oauth2_scheme, pwd_context, JWT_SECRET_KEY, JWT_ALGORITHM, oauth2_scheme_optional
from models.models import UserInDB, TokenData, object_id_to_str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# async def get_user(username: str, db = Depends(get_db)):
async def get_user(username: str, db=get_db()):
    """
    Retrieve a user by username with case-insensitive matching.
    
    Args:
        username: The username to search for (case-insensitive)
        db: Database connection
        
    Returns:
        UserInDB object if found, None otherwise
    """
    # Use a case-insensitive regex query to find the user
    user = await db.users.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
    
    if user:
        user["_id"] = str(user["_id"])  # Convert ObjectId to string
    
    return UserInDB(**user) if user else None

async def authenticate_user(username: str, password: str, db):
    user = await get_user(username,db)
    # print(user)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print("checknt 1")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print(payload)
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        user_type: str = payload.get("type")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=user_id, user_type=user_type)
    except jwt.PyJWTError:
        raise credentials_exception
    user = await get_user(username=token_data.username, db= await get_db())
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    print("chkpnt 3")
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: UserInDB = Depends(get_current_active_user)):
    # if current_user.user_details.get("type") != "admin":
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_author_user(current_user: UserInDB = Depends(get_current_active_user)):
    print("chkpnt 2")
    print(current_user)
    # if current_user.user_details.get("type") not in ["author", "admin"]:
    if current_user.user_type not in ["author", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional)
) -> Optional[UserInDB]:
    """
    Similar to get_current_user but returns None instead of raising an exception
    when the token is missing or invalid.
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token)
    except HTTPException:
        return None