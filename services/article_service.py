from typing import Dict, List, Optional, Any
from utils.time import get_current_utc_time 
from models.models import ArticleStatus, ensure_object_id
from db.schemas.articles_schema import ArticleCreate, ArticleUpdate

from repos.article_repo import ArticleRepository
from repos.user_repo import UserRepository
from repos.category_repo import CategoryRepository

class ArticleService:
    """
    Service layer for article-related operations
    Handles business logic between controllers and data access
    """
    
    def __init__(
            self, 
            article_repository: ArticleRepository, 
            user_repository: UserRepository,
            category_repository: CategoryRepository,
        ):
        self.article_repo = article_repository
        self.user_repo = user_repository
        self.category_repo = category_repository
    
    async def create_article(self, article_data: ArticleCreate, author_id: str) -> Dict[str, Any]:
        """
        Create a new article and return the created article
        """
        try:
            # Validate category and author
            await self.category_repo.validate_category(article_data.category_id)
            await self.user_repo.validate_user(author_id)
            
            # Prepare article document
            article_dict = article_data.model_dump(exclude={"category_id", "author_id"})
            article_dict["category_id"] = ensure_object_id(article_data.category_id)
            article_dict["author_id"] = ensure_object_id(author_id)
            
            # Add additional fields
            article_dict["created_at"] = get_current_utc_time()
            article_dict["updated_at"] = article_dict["created_at"]
            article_dict["views"] = 0
            article_dict["likes"] = 0
            article_dict["comments"] = []
            article_dict["bookmarked_by"] = []
            
            # Create the article
            created_article = await self.article_repo.create_article(article_dict)
            
            # Enrich article with related data
            enriched_article = await self.article_repo.enrich_article(created_article)
            
            return {
                "message": "Article created successfully",
                "article": enriched_article
            }
            
        except Exception as e:
            raise e
    
    async def get_articles(self, 
                          category: Optional[str] = None,
                          author: Optional[str] = None,
                          tag: Optional[str] = None,
                          featured: Optional[bool] = None,
                          article_status: Optional[ArticleStatus] = None,
                          skip: int = 0,
                          limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get a list of articles with optional filtering
        """
        try:
            # Build query filter
            query = await self.article_repo.build_query(
                category, author, tag, featured, article_status
            )
            
            if query is None:
                return []  # No matching category or author
            
            # Fetch and enrich articles
            articles = await self.article_repo.get_articles(query, skip, limit)
            
            return articles
            
        except Exception as e:
            raise e
    
    async def get_article_by_id_or_slug(self, id_or_slug: str, article_status: Optional[ArticleStatus] = None) -> Dict[str, Any]:
        """
        Get a single article by ID or slug
        """
        try:
            article = await self.article_repo.get_article_by_id_or_slug(id_or_slug, article_status)
            
            if not article:
                return None
                
            # Enrich article with related data
            enriched_article = await self.article_repo.enrich_article(article)
            
            return enriched_article
            
        except Exception as e:
            raise e
    
    async def update_article(self, article_id: str, article_update: ArticleUpdate, current_user_id: str) -> Dict[str, Any]:
        """
        Update an article if the user has permission
        """
        try:
            # Get the article
            article = await self.article_repo.get_article_by_id(article_id)
            
            if not article:
                return None
                
            # Check permissions (admin or author)
            user_data = await self.user_repo.get_user_by_id(current_user_id)
            is_admin = user_data.user_type == "admin"
            is_author = str(article.get("author_id")) == current_user_id
            
            if not (is_admin or is_author):
                return None  # Will be converted to 403 in the route
            
            # Prepare update data
            update_data = {
                k: v
                for k, v in article_update.model_dump(exclude_unset=True).items()
                if v is not None
            }
            
            # If there's nothing to update, return the current article
            if not update_data:
                return await self.article_repo.enrich_article(article)
            
            # If category_id is being updated, validate it
            if "category_id" in update_data and update_data["category_id"]:
                await self.category_repo.validate_category(update_data["category_id"])
                update_data["category_id"] = ensure_object_id(update_data["category_id"])
            
            # Add updated timestamp
            update_data["updated_at"] = get_current_utc_time()
            
            # Update the article
            updated_article = await self.article_repo.update_article(article_id, update_data)
            
            # Enrich and return
            return await self.article_repo.enrich_article(updated_article)
            
        except Exception as e:
            raise e
    
    async def get_home_page_articles(self) -> Dict[str, Any]:
        """
        Get articles for the home page including spotlighted, popular, and articles by category
        """
        try:
            # Get spotlighted articles (max 3)
            spotlighted = await self.article_repo.get_articles_by_query(
                {"status": "published", "is_spotlight": True},
                sort_field="updated_at",
                limit=3
            )
            
            # Get popular articles (max 6)
            popular = await self.article_repo.get_articles_by_query(
                {"status": "published", "is_popular": True},
                sort_field="updated_at",
                limit=6
            )
            
            # Get articles by category
            by_category = await self.article_repo.get_articles_by_category(limit=4)
            
            # Build response
            result = {
                "spotlighted": spotlighted,
                "popular": popular,
                "by_category": by_category
            }
            
            return result
            
        except Exception as e:
            raise e
    
    async def request_article_publish(self, article_id: str, current_user_id: str) -> Dict[str, Any]:
        """
        Request to publish an article (only for article authors)
        """
        try:
            # Get the article
            article = await self.article_repo.get_article_by_id(article_id)
            
            if not article:
                return None
                
            # Check if user is the author
            if str(article.get("author_id")) != current_user_id:
                return None  # Will be converted to 403 in the route
            
            # Check if article is already published or pending
            if article.get("status") in ["pending", "published"]:
                return None  # Will be converted to 400 in the route with specific message
            
            # Update article status to pending
            update_data = {
                "status": "pending",
                "updated_at": get_current_utc_time()
            }
            
            # Update the article
            updated_article = await self.article_repo.update_article(article_id, update_data)
            
            # Enrich and return
            return await self.article_repo.enrich_article(updated_article)
            
        except Exception as e:
            raise e
    
    async def delete_article(self, article_id: str, current_user_id: str, current_user_type: str) -> bool:
        """
        Delete an article if the user has permission
        """
        try:
            # Get the article
            article = await self.article_repo.get_article_by_id(article_id)
            
            if not article:
                return False
                
            # Check if user is author or admin
            is_author = str(article.get("author_id")) == current_user_id
            is_admin = current_user_type == "admin"
            
            if not (is_author or is_admin):
                return False  # Will be converted to 403 in the route
            
            # Delete the article
            result = await self.article_repo.delete_article(article_id)
            
            # If successful, update author's article count and remove from favorites
            if result:
                # Decrement author's article count
                await self.user_repo.decrement_author_articles_count(article.get("author_id"))
                
                # Remove article from favorites
                await self.article_repo.remove_from_bookmarks(article_id)
            
            return result
            
        except Exception as e:
            raise e
    
    async def like_article(self, article_id: str, user_id: str) -> Dict[str, str]:
        """
        Like an article
        """
        try:
            # Add article to user's likes
            result = await self.article_repo.add_article_to_likes(article_id, user_id)
            return result
            
        except Exception as e:
            raise e
    
    async def unlike_article(self, article_id: str, user_id: str) -> Dict[str, str]:
        """
        Unlike an article
        """
        try:
            # Remove article from user's likes
            result = await self.article_repo.remove_article_from_likes(article_id, user_id)
            return result
            
        except Exception as e:
            raise e
        
    async def get_article_likes_count(self, article_id: str) -> int:
        """
        Get the count of users who liked an article
        Returns the count of users as int
        """
        try:
            # Call repository method to get user IDs
            count = await self.article_repo.get_article_likes_count(article_id)
            return count
            
        except Exception as e:
            raise e     
   
    async def get_article_likes_users(self, article_id: str) -> List[str]:
        """
        Get the list of user IDs who liked an article
        Returns a list of user IDs as strings
        """
        try:
            # Call repository method to get user IDs
            user_ids = await self.article_repo.get_article_likes_users(article_id)
            return user_ids
            
        except Exception as e:
            raise e        