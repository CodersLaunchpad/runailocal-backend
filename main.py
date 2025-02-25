# main.py
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorClient

import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from pymongo import ReturnDocument

# Import routers
from routes import setup_routes


# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Content Management System API")

# TODO: move to a db folder
# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(DATABASE_URL)
db = client.cms_database

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Setup routes
setup_routes(app)

# Startup and shutdown events
@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(DATABASE_URL)
    app.mongodb = app.mongodb_client.get_database("cms_database")

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)