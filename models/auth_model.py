from typing import Optional
from pydantic import BaseModel

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