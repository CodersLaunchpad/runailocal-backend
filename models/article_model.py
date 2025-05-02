from typing import Dict, Union
from bson import ObjectId
from fastapi import HTTPException
from models.users_model import get_author_data


async def get_category_data(db, category_id: Union[str, ObjectId]) -> Dict:
    """Get category data."""
    try:
        if category_id:
            # Convert string to ObjectId if necessary
            if isinstance(category_id, str):
                category_id = ObjectId(category_id)
            return await db.categories.find_one({"_id": category_id})
        return None
    except Exception as e:
        print(f"Error in get_category_data: {str(e)}")
        return None

# TODO: can refactor and remove this
async def enrich_article_data(db, article: Dict) -> Dict:
    """Add related data to an article."""
    try:
        print(f"Starting article enrichment for article: {article.get('_id')}")
        print(f"Full article data: {article}")
        
        # Get the related category
        category_data = None
        if "category_id" in article and article["category_id"]:
            print(f"Found category_id: {article['category_id']}")
            try:
                category_data = await get_category_data(db, article["category_id"])
                print(f"Retrieved category data: {category_data}")
            except Exception as e:
                print(f"Error retrieving category data: {str(e)}")
                category_data = None
        else:
            print("No category_id found in article")
        
        # Get the related author
        author_data = None
        if "author_id" in article and article["author_id"]:
            print(f"Found author_id: {article['author_id']}")
            try:
                # Convert author_id to ObjectId if it's a string
                author_id = article["author_id"]
                if isinstance(author_id, str):
                    author_id = ObjectId(author_id)
                author_data = await get_author_data(db, author_id)
                print(f"Retrieved author data: {author_data}")
            except Exception as e:
                print(f"Error retrieving author data: {str(e)}")
                print(f"Author ID that caused the error: {article['author_id']}")
                print(f"Author ID type: {type(article['author_id'])}")
                author_data = None
        else:
            print("No author_id found in article")

        # Handle file data if present
        main_image_file = None
        if "image_id" in article and article["image_id"]:
            print(f"Found image_id: {article['image_id']}")
            try:
                file_dict = await db.files.find_one({"file_id": article["image_id"]})
                if file_dict:
                    main_image_file = {
                        "file_id": file_dict.get("file_id"),
                        "file_type": file_dict.get("file_type"),
                        "file_extension": file_dict.get("file_extension"),
                        "size": file_dict.get("size"),
                        "object_name": file_dict.get("object_name"),
                        "slug": file_dict.get("slug"),
                        "unique_string": file_dict.get("unique_string")
                    }
                    print(f"Retrieved file data: {main_image_file}")
                else:
                    print(f"No file found for image_id: {article['image_id']}")
            except Exception as e:
                print(f"Error retrieving file data: {str(e)}")
                main_image_file = None

        # Build response with safe dictionary access
        enriched_article = {
            **article,
            "category": category_data if category_data else None,
            "author": author_data if author_data else None,
            "main_image_file": main_image_file if main_image_file else None,
            "image": "DEPRECIATED"  # Mark the old image field as deprecated
        }
        print(f"Successfully enriched article: {enriched_article.get('_id')}")
        return enriched_article
        
    except Exception as e:
        print(f"Error in enrich_article_data: {str(e)}")
        print(f"Article data at time of error: {article}")
        raise Exception(f"Error enriching article: {str(e)}")

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