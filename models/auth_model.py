from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
from db.schemas.files_schema import FileInDB

class Token(BaseModel):
    access_token: str
    profile_picture_base64: str = None
    profile_file: Optional[FileInDB] = None  # Added field for file information
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = None

class PasswordResetRequest(BaseModel):
    """Model for requesting a password reset"""
    email: EmailStr

class PasswordReset(BaseModel):
    """Model for resetting password with code"""
    email: EmailStr
    code: str
    new_password: str

class PasswordResetCode(BaseModel):
    """Model for storing password reset codes in database"""
    email: EmailStr
    code: str
    created_at: datetime
    is_active: bool = True