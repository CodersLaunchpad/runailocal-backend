from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from utils.time import get_current_utc_time
from bson import ObjectId
from db.mongodb import PyObjectId

class CommentInDB(BaseModel):
    id: PyObjectId = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    text: str
    user_id: PyObjectId
    username: str
    user_type: str
    created_at: datetime = Field(default_factory=get_current_utc_time)
    updated_at: Optional[datetime] = None

    model_config = {
        "arbitrary_types_allowed": True,
        "populate_by_name": True,
        "json_encoders": {
            ObjectId: str
        }
    }
