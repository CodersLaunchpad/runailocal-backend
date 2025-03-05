from typing import Dict, Any, Optional
from bson import ObjectId
from models.models import clean_document

class ArticleRepository:
    """
    Repository for article-related database operations
    Handles all direct interactions with the database for articles
    """
    
    def __init__(self, db):
        self.db = db
    
    async def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an article by ID
        Returns the article if found, None otherwise
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Get the article
            article = await self.db.articles.find_one({"_id": article_object_id})
            
            if not article:
                return None
                
            # Clean the document before returning
            return clean_document(article)
        except Exception as e:
            raise Exception(f"Error in get_article_by_id: {str(e)}")
    
    async def get_article_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Get an article by slug
        Returns the article if found, None otherwise
        """
        try:
            # Get the article
            article = await self.db.articles.find_one({"slug": slug})
            
            if not article:
                return None
                
            # Clean the document before returning
            return clean_document(article)
        except Exception as e:
            raise Exception(f"Error in get_article_by_slug: {str(e)}")
    
    async def check_article_exists(self, article_id: str) -> bool:
        """
        Check if an article exists
        Returns True if the article exists, False otherwise
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Check if the article exists
            count = await self.db.articles.count_documents({"_id": article_object_id})
            
            return count > 0
        except Exception as e:
            raise Exception(f"Error in check_article_exists: {str(e)}")