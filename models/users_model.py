from typing import Dict
from bson import ObjectId


async def get_author_data(db, author_id: ObjectId) -> Dict:
    """Get author data with follower count."""
    author_data = await db.users.find_one(
        {"_id": author_id},
        projection={
            "_id": 1,
            "username": 1,
            "first_name": 1,
            "last_name": 1,
            "profile_picture_base64": 1,
            "followers": 1,
            "following": 1,
            "bookmarks": 1,  # Include bookmarks field in the projection
        }
    )
    
    # Add follower_count to author data
    if author_data and "followers" in author_data:
        author_data["follower_count"] = len(author_data["followers"])
        # Remove the followers array if you don't need the actual follower details
        del author_data["followers"]
    else:
        if author_data:
            author_data["follower_count"] = 0
        else:
            return None
        
    if author_data and "following" in author_data:
        author_data["following_count"] = len(author_data["following"])
        # Remove the followers array if you don't need the actual follower details
        del author_data["following"]
    else:
        if author_data:
            author_data["following_count"] = 0
        else:
            return None
    
    #  Convert ObjectIds in the bookmarks array to strings, if it exists
    if "bookmarks" in author_data:
        author_data["bookmarks"] = [str(b) for b in author_data["bookmarks"]]
    
    return author_data

async def get_category_data(db, category_id: ObjectId) -> Dict:
    """Get category data."""
    if category_id:
        return await db.categories.find_one({"_id": category_id})
    return None