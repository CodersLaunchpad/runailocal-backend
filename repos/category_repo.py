from fastapi import HTTPException
from bson import ObjectId

class CategoryRepository:
    """
    Repository for category-related database operations
    Handles all direct interactions with the database for articles
    """
    
    def __init__(self, db):
        self.db = db

    async def validate_category(self, category_id: str) -> None:
        """
        Validate that a category exists
        Raises HTTPException if category is invalid or not found
        """
        try:

            category_id_obj = ObjectId(category_id)
        
            # Verify that category exists
            category = await self.db.categories.find_one({"_id": category_id_obj})
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
        except HTTPException as e:
            raise e
        except Exception as e:
            raise Exception(f"Error validating category: {str(e)}")
