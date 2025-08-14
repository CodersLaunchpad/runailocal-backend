from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from utils.content_preprocessing import ContentPreprocessor
from utils.time import get_current_utc_time
import math

class ContentQualityService:
    """Service for calculating and managing article quality scores"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.preprocessor = ContentPreprocessor()
        self.articles_collection = db.articles
        self.quality_scores_collection = db.article_quality_scores
    
    async def calculate_article_quality_score(self, article_id: str) -> Dict[str, Any]:
        """Calculate comprehensive quality score for an article"""
        try:
            # Fetch article data
            article = await self.articles_collection.find_one({"_id": ObjectId(article_id)})
            if not article:
                raise ValueError(f"Article {article_id} not found")
            
            # Calculate content quality features
            content_features = self.preprocessor.extract_content_quality_features(article)
            
            # Calculate engagement metrics
            engagement_score = await self._calculate_engagement_score(article)
            
            # Calculate social signals
            social_score = await self._calculate_social_score(article)
            
            # Calculate author credibility score
            author_score = await self._calculate_author_credibility_score(article['author_id'])
            
            # Calculate recency score
            recency_score = self._calculate_recency_score(article['created_at'])
            
            # Combine all scores with weights
            final_score = self._combine_quality_scores(
                content_score=content_features['quality_score'],
                engagement_score=engagement_score,
                social_score=social_score,
                author_score=author_score,
                recency_score=recency_score
            )
            
            # Create quality record
            quality_record = {
                'article_id': ObjectId(article_id),
                'overall_score': final_score,
                'content_score': content_features['quality_score'],
                'engagement_score': engagement_score,
                'social_score': social_score,
                'author_score': author_score,
                'recency_score': recency_score,
                'content_features': content_features,
                'calculated_at': get_current_utc_time(),
                'version': '1.0'
            }
            
            # Upsert quality score
            await self.quality_scores_collection.update_one(
                {"article_id": ObjectId(article_id)},
                {"$set": quality_record},
                upsert=True
            )
            
            # Update article with quality score
            await self.articles_collection.update_one(
                {"_id": ObjectId(article_id)},
                {"$set": {
                    "quality_score": final_score,
                    "content_quality": self._categorize_quality_score(final_score),
                    "last_quality_update": get_current_utc_time()
                }}
            )
            
            return quality_record
            
        except Exception as e:
            print(f"Error calculating quality score for article {article_id}: {e}")
            raise
    
    async def _calculate_engagement_score(self, article: Dict[str, Any]) -> float:
        """Calculate engagement score based on user interactions"""
        views = article.get('views', 0)
        likes = article.get('likes', 0)
        bookmarks = len(article.get('bookmarked_by', []))
        comments = len(article.get('comments', []))
        
        # Calculate engagement rates
        if views > 0:
            like_rate = likes / views
            bookmark_rate = bookmarks / views
            comment_rate = comments / views
        else:
            like_rate = bookmark_rate = comment_rate = 0
        
        # Weight different engagement types
        engagement_score = (
            (like_rate * 30) +      # Likes are common, lower weight
            (bookmark_rate * 50) +  # Bookmarks show intent to read later
            (comment_rate * 70) +   # Comments show deeper engagement
            (min(views / 100, 1) * 20)  # View bonus (capped)
        )
        
        return min(engagement_score, 100)  # Cap at 100
    
    async def _calculate_social_score(self, article: Dict[str, Any]) -> float:
        """Calculate social signals score"""
        author_id = article['author_id']
        
        # Get author's follower count
        author = await self.db.users.find_one(
            {"_id": author_id},
            projection={"followers": 1}
        )
        
        follower_count = len(author.get('followers', [])) if author else 0
        
        # Check if article is spotlighted or popular
        is_spotlight = article.get('is_spotlight', False)
        is_popular = article.get('is_popular', False)
        
        # Calculate social score
        social_score = 0
        
        # Follower influence (0-30 points)
        if follower_count > 1000:
            social_score += 30
        elif follower_count > 100:
            social_score += 20
        elif follower_count > 10:
            social_score += 10
        
        # Editorial signals (0-40 points)
        if is_spotlight:
            social_score += 25
        if is_popular:
            social_score += 15
        
        # Category performance (0-30 points)
        category_score = await self._calculate_category_performance_score(
            article['category_id'], 
            article['_id']
        )
        social_score += category_score
        
        return min(social_score, 100)
    
    async def _calculate_category_performance_score(
        self, 
        category_id: ObjectId, 
        article_id: ObjectId
    ) -> float:
        """Calculate how well an article performs within its category"""
        try:
            # Get articles in the same category from the last 30 days
            thirty_days_ago = get_current_utc_time() - timedelta(days=30)
            
            category_articles = await self.articles_collection.find({
                "category_id": category_id,
                "created_at": {"$gte": thirty_days_ago},
                "_id": {"$ne": article_id}
            }).to_list(None)
            
            if not category_articles:
                return 15  # Average score if no comparison data
            
            # Get current article stats
            current_article = await self.articles_collection.find_one({"_id": article_id})
            if not current_article:
                return 0
            
            current_views = current_article.get('views', 0)
            current_likes = current_article.get('likes', 0)
            
            # Calculate percentile rank within category
            view_ranks = [art.get('views', 0) for art in category_articles]
            like_ranks = [art.get('likes', 0) for art in category_articles]
            
            view_percentile = self._calculate_percentile(current_views, view_ranks)
            like_percentile = self._calculate_percentile(current_likes, like_ranks)
            
            # Combine percentiles
            category_score = (view_percentile + like_percentile) / 2 * 30
            return min(category_score, 30)
            
        except Exception:
            return 15  # Return average score on error
    
    def _calculate_percentile(self, value: int, comparison_values: List[int]) -> float:
        """Calculate percentile rank of a value within a list"""
        if not comparison_values:
            return 0.5
        
        rank = sum(1 for x in comparison_values if x <= value)
        return rank / len(comparison_values)
    
    async def _calculate_author_credibility_score(self, author_id: ObjectId) -> float:
        """Calculate author credibility score"""
        try:
            # Get author stats
            pipeline = [
                {"$match": {"author_id": author_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_articles": {"$sum": 1},
                        "total_views": {"$sum": "$views"},
                        "total_likes": {"$sum": "$likes"},
                        "avg_quality": {"$avg": "$quality_score"}
                    }
                }
            ]
            
            author_stats = await self.articles_collection.aggregate(pipeline).to_list(1)
            
            if not author_stats:
                return 20  # New author baseline
            
            stats = author_stats[0]
            
            credibility_score = 0
            
            # Article count contribution (0-25 points)
            article_count = stats.get('total_articles', 0)
            if article_count > 50:
                credibility_score += 25
            elif article_count > 20:
                credibility_score += 20
            elif article_count > 10:
                credibility_score += 15
            elif article_count > 5:
                credibility_score += 10
            elif article_count > 0:
                credibility_score += 5
            
            # Performance contribution (0-35 points)
            total_views = stats.get('total_views', 0)
            total_likes = stats.get('total_likes', 0)
            
            if total_views > 10000:
                credibility_score += 20
            elif total_views > 1000:
                credibility_score += 15
            elif total_views > 100:
                credibility_score += 10
            
            if total_likes > 500:
                credibility_score += 15
            elif total_likes > 100:
                credibility_score += 10
            elif total_likes > 20:
                credibility_score += 5
            
            # Average quality contribution (0-40 points)
            avg_quality = stats.get('avg_quality') or 50
            if avg_quality > 80:
                credibility_score += 40
            elif avg_quality > 70:
                credibility_score += 30
            elif avg_quality > 60:
                credibility_score += 20
            elif avg_quality > 50:
                credibility_score += 10
            
            return min(credibility_score, 100)
            
        except Exception:
            return 20  # Return baseline score on error
    
    def _calculate_recency_score(self, created_at: datetime) -> float:
        """Calculate recency score - newer content gets higher scores"""
        now = get_current_utc_time()
        age_days = (now - created_at).days
        
        # Exponential decay with slower decline
        if age_days <= 1:
            return 100
        elif age_days <= 7:
            return 90
        elif age_days <= 30:
            return 70
        elif age_days <= 90:
            return 50
        elif age_days <= 365:
            return 30
        else:
            return 20
    
    def _combine_quality_scores(
        self,
        content_score: float,
        engagement_score: float,
        social_score: float,
        author_score: float,
        recency_score: float
    ) -> float:
        """Combine different quality scores with weights"""
        weights = {
            'content': 0.30,    # Content quality is important
            'engagement': 0.25, # User engagement matters
            'social': 0.20,     # Social signals
            'author': 0.15,     # Author credibility
            'recency': 0.10     # Freshness bonus
        }
        
        final_score = (
            (content_score * weights['content']) +
            (engagement_score * weights['engagement']) +
            (social_score * weights['social']) +
            (author_score * weights['author']) +
            (recency_score * weights['recency'])
        )
        
        return min(round(final_score, 2), 100)
    
    def _categorize_quality_score(self, score: float) -> str:
        """Categorize quality score into labels"""
        if score >= 80:
            return "excellent"
        elif score >= 65:
            return "good"
        elif score >= 50:
            return "average"
        elif score >= 35:
            return "poor"
        else:
            return "very_poor"
    
    async def batch_calculate_quality_scores(
        self, 
        article_ids: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Calculate quality scores for multiple articles"""
        try:
            # If no specific articles provided, get articles that need quality calculation
            if not article_ids:
                # Find articles without quality scores or outdated ones
                one_week_ago = get_current_utc_time() - timedelta(days=7)
                
                pipeline = [
                    {
                        "$match": {
                            "$or": [
                                {"quality_score": {"$exists": False}},
                                {"last_quality_update": {"$lt": one_week_ago}},
                                {"last_quality_update": {"$exists": False}}
                            ],
                            "status": "published"
                        }
                    },
                    {"$limit": limit},
                    {"$project": {"_id": 1}}
                ]
                
                articles = await self.articles_collection.aggregate(pipeline).to_list(limit)
                article_ids = [str(art["_id"]) for art in articles]
            
            # Calculate quality scores
            results = {
                'processed': 0,
                'errors': 0,
                'article_results': []
            }
            
            for article_id in article_ids:
                try:
                    quality_record = await self.calculate_article_quality_score(article_id)
                    results['article_results'].append({
                        'article_id': article_id,
                        'quality_score': quality_record['overall_score'],
                        'status': 'success'
                    })
                    results['processed'] += 1
                except Exception as e:
                    results['article_results'].append({
                        'article_id': article_id,
                        'error': str(e),
                        'status': 'error'
                    })
                    results['errors'] += 1
            
            return results
            
        except Exception as e:
            print(f"Error in batch quality calculation: {e}")
            raise
    
    async def get_quality_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get quality insights and statistics"""
        try:
            start_date = get_current_utc_time() - timedelta(days=days)
            
            pipeline = [
                {
                    "$match": {
                        "calculated_at": {"$gte": start_date}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_overall_score": {"$avg": "$overall_score"},
                        "avg_content_score": {"$avg": "$content_score"},
                        "avg_engagement_score": {"$avg": "$engagement_score"},
                        "avg_social_score": {"$avg": "$social_score"},
                        "avg_author_score": {"$avg": "$author_score"},
                        "total_articles": {"$sum": 1},
                        "excellent_articles": {
                            "$sum": {"$cond": [{"$gte": ["$overall_score", 80]}, 1, 0]}
                        },
                        "good_articles": {
                            "$sum": {"$cond": [
                                {"$and": [
                                    {"$gte": ["$overall_score", 65]},
                                    {"$lt": ["$overall_score", 80]}
                                ]}, 
                                1, 0
                            ]}
                        }
                    }
                }
            ]
            
            results = await self.quality_scores_collection.aggregate(pipeline).to_list(1)
            
            if results:
                stats = results[0]
                return {
                    "period_days": days,
                    "total_articles_analyzed": stats['total_articles'],
                    "average_scores": {
                        "overall": round(stats['avg_overall_score'], 2),
                        "content": round(stats['avg_content_score'], 2),
                        "engagement": round(stats['avg_engagement_score'], 2),
                        "social": round(stats['avg_social_score'], 2),
                        "author": round(stats['avg_author_score'], 2)
                    },
                    "quality_distribution": {
                        "excellent": stats['excellent_articles'],
                        "good": stats['good_articles'],
                        "average_or_below": stats['total_articles'] - stats['excellent_articles'] - stats['good_articles']
                    }
                }
            else:
                return {
                    "period_days": days,
                    "total_articles_analyzed": 0,
                    "message": "No quality data available for the specified period"
                }
                
        except Exception as e:
            print(f"Error getting quality insights: {e}")
            raise
    
    async def get_article_quality_details(self, article_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed quality information for an article"""
        try:
            quality_record = await self.quality_scores_collection.find_one(
                {"article_id": ObjectId(article_id)}
            )
            
            if quality_record:
                quality_record["_id"] = str(quality_record["_id"])
                quality_record["article_id"] = str(quality_record["article_id"])
                return quality_record
            
            return None
            
        except Exception as e:
            print(f"Error getting quality details for article {article_id}: {e}")
            raise