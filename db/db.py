from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from config import (
    DATABASE_URL, 
    DATABASE_NAME,
    DB_MAX_POOL_SIZE,
    DB_MAX_RECONNECT_ATTEMPTS,
    DB_RECONNECT_DELAY,
    DB_SERVER_SELECTION_TIMEOUT_MS,
    DB_CONNECT_TIMEOUT_MS
)
from logger.logger import logger

import asyncio
from typing import Optional

# Global client with connection pool
client: Optional[AsyncIOMotorClient] = None
db = None

async def init_db():
    """Initialize database connection with retries"""
    global client, db
    
    for attempt in range(DB_MAX_RECONNECT_ATTEMPTS):
        try:
            if client is None:
                # Create client with connection pool
                client = AsyncIOMotorClient(
                    DATABASE_URL,
                    maxPoolSize=DB_MAX_POOL_SIZE,
                    serverSelectionTimeoutMS=DB_SERVER_SELECTION_TIMEOUT_MS,
                    connectTimeoutMS=DB_CONNECT_TIMEOUT_MS,
                    retryWrites=True,
                    retryReads=True
                )
                db = client[DATABASE_NAME]
            
            # Test connection
            await client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            return
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB (attempt {attempt+1}/{DB_MAX_RECONNECT_ATTEMPTS}): {e}")
            if attempt < DB_MAX_RECONNECT_ATTEMPTS - 1:
                await asyncio.sleep(DB_RECONNECT_DELAY)
            else:
                logger.error("Max reconnection attempts reached. Running with degraded database functionality.")
                # Don't exit, continue with possible degraded functionality

async def get_db():
    """
    Dependency function to get database connection.
    For use with FastAPI Depends().
    """
    if client is None:
        # Try to initialize if not already connected
        await init_db()
        
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable"
        )
        
    try:
        # Check if connection is alive before returning
        await client.admin.command('ping')
        return db
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        # Try to reconnect
        await init_db()
        
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable"
            )
        return db

async def close_db_connection():
    """Close database connection"""
    global client
    if client:
        client.close()
        client = None
        logger.info("DB connection closed")

