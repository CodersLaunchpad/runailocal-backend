from fastapi import HTTPException
from typing import Dict, Any, Optional, List
from bson import ObjectId
from pymongo import ReturnDocument
from utils.time import get_current_utc_time 
from models.models import ArticleStatus, clean_document, ensure_object_id, prepare_mongo_document
from models.article_model import enrich_article_data

class ArticleRepository:
    """
    Repository for article-related database operations
    Handles all direct interactions with the database for articles
    """
    
    def __init__(self, db):
        self.db = db

    def check_if_bookmarked(self, article, current_user):
        if current_user is not None:
            try:
                user_id = ObjectId(current_user.id)
                # Check if user's ID is in the bookmarks array
                bookmarks = article.get("bookmarked_by", [])
                # Set is_bookmarked to True only if user_id is found in bookmarks
                is_bookmarked = any(str(bookmark_id) == str(user_id) for bookmark_id in bookmarks)
            except:
                # If ObjectId conversion fails, set is_bookmarked to False
                is_bookmarked = False
        else:
            # If no current_user, set is_bookmarked to False
            is_bookmarked = False
        return is_bookmarked
    
    def check_if_liked(self, article, current_user):
        """
        Check if an article is liked by the current user and return the total like count
        Returns a tuple of (is_liked, like_count)
        """
        # Initialize like count from the liked_by array
        liked_by = article.get("liked_by", [])
        like_count = len(liked_by)
        
        # Check if user has liked the article
        if current_user is not None:
            try:
                user_id = ObjectId(current_user.id)
                # Check if user's ID is in the liked_by array
                # Set is_liked to True only if user_id is found in liked_by
                is_liked = any(str(liker_id) == str(user_id) for liker_id in liked_by)
            except:
                # If ObjectId conversion fails, set is_liked to False
                is_liked = False
        else:
            # If no current_user, set is_liked to False
            is_liked = False
        
        return is_liked, like_count
    
    async def create_article(self, article_dict: Dict[str, Any]) -> Dict[str, Any]:
            """
            Create a new article
            Returns the created article
            """
            try:
                # Insert article into database
                result = await self.db.articles.insert_one(article_dict)
                
                # Get the created article
                created_article = await self.db.articles.find_one({"_id": result.inserted_id})
                
                # Clean the document before returning
                return clean_document(prepare_mongo_document(created_article))
            except Exception as e:
                raise Exception(f"Error creating article: {str(e)}")
        
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

    async def get_article_by_id_or_slug(self, id_or_slug: str, article_status: Optional[ArticleStatus] = None, current_user=None) -> Optional[Dict[str, Any]]:
        """
        Get an article by ID or slug with optional status filter
        Returns the article if found, None otherwise
        """
        try:
            # Check if the id_or_slug is a valid ObjectId
            if ObjectId.is_valid(id_or_slug):
                # Search by ID
                query = {"_id": ObjectId(id_or_slug)}
            else:
                # Search by slug
                query = {"slug": id_or_slug}
            
            # Apply published filter if needed
            if article_status:
                query["status"] = article_status.value
            
            # Find the article
            article = await self.db.articles.find_one(query)
            
            if not article:
                return None
            
            # Add is_bookmarked field if current_user is valid
            article["is_bookmarked"] = self.check_if_bookmarked(article, current_user)
            article["is_liked"], article["likes"]  = self.check_if_liked(article, current_user)
                
            enriched_article = await enrich_article_data(self.db, article)
            
            return prepare_mongo_document(enriched_article)
        except Exception as e:
            raise Exception(f"Error getting article by ID or slug: {str(e)}")
    
            # Clean the document before returning
            # return clean_document(prepare_mongo_document(article))
            return clean_document(prepare_mongo_document(enriched_article))
        # except Exception as e:
        #     raise Exception(f"Error in get_article_by_id_or_slug: {str(e)}")    

    async def check_article_exists(self, article_id: str) -> bool:
        """
        Check if an article exists
        Returns True if the article exists, False otherwise
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Check if the article exists
            count = await self.db.articles.find_one({"_id": article_object_id})
            
            return count > 0
        except Exception as e:
            raise Exception(f"Error in check_article_exists: {str(e)}")
        
    async def build_query(self, 
                        category: Optional[str] = None,
                        author: Optional[str] = None,
                        tag: Optional[str] = None,
                        featured: Optional[bool] = None,
                        status: Optional[ArticleStatus] = None) -> Dict[str, Any]:
        """
        Build a query for filtering articles
        Returns None if category or author does not exist
        """
        query = {}
    
        # Filter by category
        if category:
            if ObjectId.is_valid(category):
                query["category_id"] = ObjectId(category)
            else:
                # Find category by slug
                category_obj = await self.db.categories.find_one({"slug": category})
                if category_obj:
                    query["category_id"] = category_obj["_id"]
                else:
                    return None  # No matching category found
        
        # Filter by author
        if author:
            if ObjectId.is_valid(author):
                query["author_id"] = ObjectId(author)
            else:
                # Find author by username
                author_obj = await self.db.users.find_one({"username": author})
                if author_obj:
                    query["author_id"] = author_obj["_id"]
                else:
                    return None  # No matching author found
        
        # Filter by tag
        if tag:
            query["tags"] = tag
        
        # Filter by featured status
        if featured is not None:
            query["featured"] = featured
        
        # Uncomment if you want to filter published articles
        # Filter by article status (using the enum value)
        # Filter by article status (if provided)
        if status is not None:
            # Use status.value if available, otherwise assume status is already a string
            query["status"] = status.value if hasattr(status, "value") else status
        
        return query
    
    async def get_articles(self, query: Dict[str, Any], skip: int = 0, limit: int = 20, current_user=None) -> List[Dict[str, Any]]:
        """
        Get a list of articles based on query
        Returns a list of enriched articles
        """
        try:
            # Fetch articles
            cursor = self.db.articles.find(query).sort("created_at", -1).skip(skip).limit(limit)
            
            articles = []
            async for article in cursor:
                # Add is_bookmarked field if current_user is valid
                article["is_bookmarked"] = self.check_if_bookmarked(article, current_user)
                article["is_liked"], article["likes"]  = self.check_if_liked(article, current_user)
                
                # Enrich article with related data
                enriched_article = await enrich_article_data(self.db, article)
                articles.append(prepare_mongo_document(enriched_article))
            
            return clean_document(articles)
        except Exception as e:
            raise Exception(f"Error getting articles: {str(e)}")

    async def enrich_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich an article with related data (category and author)
        """
        enriched_article = await enrich_article_data(self.db, article)
        return clean_document(prepare_mongo_document(enriched_article))
    
    async def update_article(self, article_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an article
        Returns the updated article
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Update the article
            updated_article = await self.db.articles.find_one_and_update(
                {"_id": article_object_id},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            
            if not updated_article:
                return None
                
            # Clean the document before returning
            return clean_document(prepare_mongo_document(updated_article))
        except Exception as e:
            raise Exception(f"Error updating article: {str(e)}")
    
    async def get_articles_by_query(self, query: Dict[str, Any], sort_field: str = "created_at", limit: int = 10, current_user=None) -> List[Dict[str, Any]]:
        """
        Get articles based on query with sorting and limit
        Returns a list of enriched articles
        """
        try:
            cursor = self.db.articles.find(query).sort(sort_field, -1).limit(limit)
            
            articles = []
            async for article in cursor:
                # Add is_bookmarked field if current_user is valid
                article["is_bookmarked"] = self.check_if_bookmarked(article, current_user)
                article["is_liked"], article["likes"]  = self.check_if_liked(article, current_user)
                    
                # Enrich article with related data
                enriched_article = await enrich_article_data(self.db, article)
                articles.append(prepare_mongo_document(enriched_article))
            
            return clean_document(articles)
        except Exception as e:
            raise Exception(f"Error getting articles by query: {str(e)}")
    
    async def get_articles_by_category(self, limit: int = 4, current_user=None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get articles grouped by category
        Returns a dictionary with category names as keys and lists of articles as values
        """
        try:
            # Get all categories
            categories = await self.db.categories.find().to_list(length=100)
            
            by_category = {}
            for category in categories:
                # Get articles for this category
                cat_query = {"status": "published", "category_id": category["_id"]}
                cursor = self.db.articles.find(cat_query).sort("updated_at", -1).limit(limit)
                
                cat_articles = []
                async for article in cursor:
                    # Add is_bookmarked field if current_user is valid
                    article["is_bookmarked"] = self.check_if_bookmarked(article, current_user)
                    article["is_liked"], article["likes"]  = self.check_if_liked(article, current_user)
                    
                    enriched = await enrich_article_data(self.db, article)
                    # Override category with the current category document
                    enriched["category"] = prepare_mongo_document(category)
                    cat_articles.append(enriched)
                
                # Only include categories with articles
                if cat_articles:
                    by_category[category["name"]] = clean_document(cat_articles)
            
            return by_category
        except Exception as e:
            raise Exception(f"Error getting articles by category: {str(e)}")
    
    async def delete_article(self, article_id: str) -> bool:
        """
        Delete an article
        Returns True if deleted, False otherwise
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Delete the article
            result = await self.db.articles.delete_one({"_id": article_object_id})
            
            # Return whether deletion was successful
            return result.deleted_count > 0
        except Exception as e:
            raise Exception(f"Error deleting article: {str(e)}")
    
    async def remove_from_bookmarks(self, article_id: str) -> None:
        """
        Remove an article from all users' bookmarks
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Remove from bookmarks
            await self.db.users.update_many(
                {"bookmarks": article_object_id},
                {"$pull": {"bookmarks": article_object_id}}
            )
        except Exception as e:
            raise Exception(f"Error removing article from bookmarks: {str(e)}")            
        
    async def add_article_to_likes(self, article_id: str, user_id: str) -> Dict[str, str]:
        """
        Add an article to a user's likes and update the article's liked_by list
        Returns status message
        """
        try:
            # Convert IDs to ObjectId
            article_object_id = ensure_object_id(article_id)
            user_object_id = ensure_object_id(user_id)
            
            # Check if article exists
            article = await self.db.articles.find_one({"_id": article_object_id})
            if not article:
                raise ValueError("Article not found")
            
            # Get the user
            user = await self.db.users.find_one({"_id": user_object_id})
            if not user:
                raise ValueError("User not found")
            
            # Convert likes list to ObjectId objects
            user_likes = user.get("likes", [])
            user_likes_obj = [ensure_object_id(str(like_id)) for like_id in user_likes]
            
            # Check if article's liked_by list exists
            article_liked_by = article.get('liked_by', [])
            article_liked_by_ids = [ensure_object_id(str(_id)) for _id in article_liked_by]
            
            # Check if already liked
            already_in_likes = article_object_id in user_likes_obj
            already_in_liked_by = user_object_id in article_liked_by_ids
            
            if not already_in_likes and not already_in_liked_by:
                # Update user's likes list
                user_result = await self.db.users.update_one(
                    {"_id": user_object_id},
                    {"$addToSet": {"likes": article_object_id}}
                )
                
                # Update the article's liked_by list
                article_result = await self.db.articles.update_one(
                    {"_id": article_object_id},
                    {"$addToSet": {"liked_by": user_object_id}}
                )
                
                if user_result.modified_count and article_result.modified_count:
                    return {"status": "success", "message": "Article liked successfully"}
                elif user_result.modified_count:
                    return {"status": "partial", "message": "Added to your likes, but couldn't update article's liked_by list"}
                else:
                    raise Exception("Failed to update likes/liked_by lists")
            else:
                # Handle different cases of partial relationship
                if already_in_likes and not already_in_liked_by:
                    # Fix one-sided relationship
                    article_result = await self.db.articles.update_one(
                        {"_id": article_object_id},
                        {"$addToSet": {"liked_by": user_object_id}}
                    )
                    if article_result.modified_count:
                        return {"status": "fixed", "message": "Fixed one-sided like relationship"}
                    else:
                        raise Exception("Failed to update article's liked_by list")
                elif not already_in_likes and already_in_liked_by:
                    # Fix one-sided relationship
                    user_result = await self.db.users.update_one(
                        {"_id": user_object_id},
                        {"$addToSet": {"likes": article_object_id}}
                    )
                    if user_result.modified_count:
                        return {"status": "fixed", "message": "Fixed one-sided like relationship"}
                    else:
                        raise Exception("Failed to update likes list")
                else:
                    return {"status": "info", "message": "Article already liked"}
                
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error adding article to likes: {str(e)}")
    
    async def remove_article_from_likes(self, article_id: str, user_id: str) -> Dict[str, str]:
        """
        Remove an article from a user's likes and update the article's liked_by list
        Returns status message
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ensure_object_id(article_id)
            
            # Check if article exists
            article = await self.db.articles.find_one({"_id": article_object_id})
            if not article:
                raise ValueError("Article not found")
            
            # Get the user
            user_object_id = ensure_object_id(user_id)
            
            # Remove article from user's likes list
            user_result = await self.db.users.update_one(
                {"_id": user_object_id},
                {"$pull": {"likes": article_object_id}}
            )
            
            # Remove user from article's liked_by list
            article_result = await self.db.articles.update_one(
                {"_id": article_object_id},
                {"$pull": {"liked_by": user_object_id}}
            )
            
            # Check results and return appropriate response
            if user_result.modified_count and article_result.modified_count:
                return {"status": "success", "message": "Article removed from likes successfully"}
            elif user_result.modified_count:
                return {"status": "partial", "message": "Removed from your likes, but couldn't update article's liked_by list"}
            elif article_result.modified_count:
                return {"status": "partial", "message": "Removed from article's liked_by list, but couldn't update your likes"}
            else:
                # If nothing was modified despite the checks indicating a relationship existed
                return {"status": "warning", "message": "No changes made to like relationship"}
                
        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"Error removing article from likes: {str(e)}")
        
    async def get_article_likes_count(self, article_id: str) -> int:
        """
        Get the number of likes for an article
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Get the article
            article = await self.db.articles.find_one(
                {"_id": article_object_id},
                projection={"likes": 1}
            )
            
            if not article:
                return 0
                
            return article.get("likes", 0)
        except Exception as e:
            raise Exception(f"Error getting article likes count: {str(e)}")
        
    async def get_article_likes_users(self, article_id: str) -> List[str]:
        """
        Get the list of user IDs who liked an article
        Returns a list of user IDs as strings
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Find all users who have this article in their likes
            cursor = self.db.users.find(
                {"likes": article_object_id},
                projection={"_id": 1}
            )
            
            # Extract user IDs
            user_ids = []
            async for user in cursor:
                user_ids.append(str(user["_id"]))
                
            return user_ids
        except Exception as e:
            raise Exception(f"Error getting users who liked the article: {str(e)}")        
            
    async def upload_article_image(self, article_id: str, file_path: str, is_main: bool, is_thumbnail: bool, caption: Optional[str]) -> Dict[str, Any]:
        """
        Add an image to an article
        Returns the updated article
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Create image object
            image = {
                "url": file_path,
                "is_main": is_main,
                "is_thumbnail": is_thumbnail,
                "caption": caption
            }
            
            # If setting as main or thumbnail, unset others
            if is_main:
                await self.db.articles.update_one(
                    {"_id": article_object_id, "images.is_main": True},
                    {"$set": {"images.$.is_main": False}}
                )
            
            if is_thumbnail:
                await self.db.articles.update_one(
                    {"_id": article_object_id, "images.is_thumbnail": True},
                    {"$set": {"images.$.is_thumbnail": False}}
                )
            
            # Add image to article
            updated_article = await self.db.articles.find_one_and_update(
                {"_id": article_object_id},
                {"$push": {"images": image}},
                return_document=ReturnDocument.AFTER
            )
            
            if not updated_article:
                return None
                
            # Clean the document before returning
            return clean_document(prepare_mongo_document(updated_article))
        except Exception as e:
            raise Exception(f"Error uploading article image: {str(e)}")
    
    async def delete_article_image(self, article_id: str, image_index: int) -> Dict[str, Any]:
        """
        Delete an image from an article
        Returns the updated article
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Get the article
            article = await self.db.articles.find_one({"_id": article_object_id})
            
            if not article:
                return None
                
            # Check if image index exists
            images = article.get("images", [])
            
            if image_index < 0 or image_index >= len(images):
                raise HTTPException(status_code=404, detail="Image not found")
            
            # Remove image from article
            images.pop(image_index)
            
            # Update article
            updated_article = await self.db.articles.find_one_and_update(
                {"_id": article_object_id},
                {"$set": {"images": images}},
                return_document=ReturnDocument.AFTER
            )
            
            # Clean the document before returning
            return clean_document(prepare_mongo_document(updated_article))
        except HTTPException:
            raise
        except Exception as e:
            raise Exception(f"Error deleting article image: {str(e)}")
            
    async def approve_article(self, article_id: str) -> Dict[str, Any]:
        """
        Approve an article (admin function)
        Returns the updated article
        """
        try:
            # Convert article_id to ObjectId
            article_object_id = ObjectId(article_id)
            
            # Approve article by setting status to published
            updated_article = await self.db.articles.find_one_and_update(
                {"_id": article_object_id, "status": "pending"},
                {"$set": {"status": "published", "updated_at": get_current_utc_time()}},
                return_document=ReturnDocument.AFTER
            )
            
            if not updated_article:
                article = await self.db.articles.find_one({"_id": article_object_id})
                
                if not article:
                    raise HTTPException(status_code=404, detail="Article not found")
                elif article.get("status") == "published":
                    raise HTTPException(status_code=400, detail="Article is already published")
                else:
                    raise HTTPException(status_code=400, detail=f"Article is in {article.get('status')} status, cannot be approved")
            
            # Clean the document before returning
            return clean_document(prepare_mongo_document(updated_article))
        except HTTPException:
            raise
        except Exception as e:
            raise Exception(f"Error approving article: {str(e)}")     
        