# centralizes MongoDB utilities
from bson import ObjectId
from typing import Annotated
from pydantic import Field
from typing import Dict, Any, Optional

PyObjectId = Annotated[str, Field(default_factory=lambda: str(ObjectId()))]

# Helper functions for MongoDB operations
def convert_to_object_id(id_value: str) -> ObjectId:
    """Convert string ID to ObjectId for MongoDB queries"""
    return ObjectId(id_value)

def overwrite_mongodb_id(document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB _id to string id for API responses"""
    if document and "_id" in document:
        document["id"] = str(document["_id"])
        del document["_id"]
    return document