# dependencies/database.py
from fastapi import Depends, HTTPException, status
from typing import Annotated

async def get_db():
    """
    Dependency for database access.
    Returns MongoDB database connection from the connection pool.
    """
    from db.db import get_db as db_connection
    db = await db_connection()
    return db

async def get_object_storage():
    """
    Dependency for object storage access.
    Returns MinIO client connection.
    """
    from db.db import get_object_storage as object_storage
    storage = await object_storage()
    return storage

# MongoDB database dependency for use with FastAPI Depends
DB = Annotated[object, Depends(get_db)]
ObjectStorage = Annotated[object, Depends(get_object_storage)]