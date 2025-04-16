import asyncio
import os
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Configuration
MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("DATABASE_NAME", "cms")

# Sample categories to insert
categories = [
    {
        "_id": ObjectId(),
        "name": "Artificial Intelligence",
        "slug": "artificial-intelligence",
        "description": "Latest developments in AI technology",
        "icon_url": None,
        "color": None
    },
    {
        "_id": ObjectId(),
        "name": "General",
        "slug": "general",
        "description": "General articles",
        "icon_url": None,
        "color": None
    },
    {
        "_id": ObjectId(),
        "name": "VLM",
        "slug": "vlm",
        "description": "Video Language Models",
        "icon_url": None,
        "color": None
    },
    {
        "_id": ObjectId(),
        "name": "Machine Learning",
        "slug": "machine-learning",
        "description": "Advancements in machine learning algorithms and applications",
        "icon_url": None,
        "color": None
    },
    {
        "_id": ObjectId(),
        "name": "Robotics",
        "slug": "robotics",
        "description": "The latest in robotics research and development",
        "icon_url": None,
        "color": None
    },
    {
        "_id": ObjectId(),
        "name": "Tech Ethics",
        "slug": "tech-ethics",
        "description": "Exploring ethical questions in technology",
        "icon_url": None,
        "color": None
    }
]

async def insert_categories():
    """Insert categories into MongoDB"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[MONGO_DB]
        
        # Check if categories collection exists
        collections = await db.list_collection_names()
        if "categories" not in collections:
            print("Creating categories collection...")
            await db.create_collection("categories")
        
        # Insert categories
        result = await db.categories.insert_many(categories)
        print(f"Successfully inserted {len(result.inserted_ids)} categories")
        
        # Print inserted categories
        cursor = db.categories.find({})
        async for document in cursor:
            print(f"Category: {document['name']} (slug: {document['slug']})")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close the connection
        client.close()

if __name__ == "__main__":
    asyncio.run(insert_categories()) 