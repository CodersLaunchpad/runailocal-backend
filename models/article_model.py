from typing import Dict
from bson import ObjectId
from fastapi import HTTPException
from models.users_model import get_author_data


async def get_category_data(db, category_id: ObjectId) -> Dict:
    """Get category data."""
    if category_id:
        return await db.categories.find_one({"_id": category_id})
    return None

# TODO: can refactor and remove this
async def enrich_article_data(db, article: Dict) -> Dict:
    """Add related data to an article."""
    # Get the related category
    category_data = None
    if "category_id" in article:
        category_data = await get_category_data(db, article["category_id"])
    
    # Get the related author
    author_data = None
    if "author_id" in article:
        author_data = await get_author_data(db, article["author_id"])
    
    # Build response
    return {
        **article,
        "category": category_data,
        "author": author_data
    }

async def get_article(db, article_id: str) -> dict:
    """Validate article id and retrieve article from the DB."""
    if not ObjectId.is_valid(article_id):
        raise HTTPException(status_code=400, detail="Invalid article ID")
    article = await db.articles.find_one({"_id": ObjectId(article_id)})
    # Convert ObjectIds in "bookmarked_by" to strings, if the field exists.
    article["bookmarked_by"] = [str(oid) for oid in article.get("bookmarked_by", [])]
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article

async def get_category(db, category_id: str) -> dict:
    """Validate and retrieve a category by its id."""
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=400, detail="Invalid category ID")
    category = await db.categories.find_one({"_id": ObjectId(category_id)})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

# async def get_author(db, author_id, include_followers: bool = True) -> dict:
#     """Retrieve author data with a configurable projection.
#        If include_followers is True, also calculate follower_count.
#     """
#     projection = {
#         "_id": 1,
#         "username": 1,
#         "first_name": 1,
#         "last_name": 1,
#         "profile_picture_base64": 1,
#     }
#     if include_followers:
#         projection["followers"] = 1

#     author = await db.users.find_one({"_id": author_id}, projection=projection)
#     if include_followers:
#         if author and "followers" in author:
#             author["follower_count"] = len(author["followers"])
#             del author["followers"]
#         else:
#             author["follower_count"] = 0
#     return author