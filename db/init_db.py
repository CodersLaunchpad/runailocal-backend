from pymongo import ASCENDING, TEXT

async def init_db_indexes(db):
    """
    Initialize database with required indexes and configurations
    """
    # Create text index for article search
    await db.articles.create_index([
        ("title", TEXT),
        ("content", TEXT),
        ("tags", TEXT)
    ])
    
    # Create other indexes if needed
    await db.articles.create_index([("created_at", ASCENDING)])
    await db.articles.create_index([("category_id", ASCENDING)])
    await db.articles.create_index([("author_id", ASCENDING)])
    await db.articles.create_index([("status", ASCENDING)]) 