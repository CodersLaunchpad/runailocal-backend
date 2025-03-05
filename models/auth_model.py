from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    profile_picture_base64: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    user_type: Optional[str] = None