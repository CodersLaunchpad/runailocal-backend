from typing import Dict, Any, List
from db.schemas.articles_schema import ArticleResponse, ArticleInDB, ArticleCreate
from models.models import clean_document

def article_db_to_response(article_db: ArticleInDB) -> ArticleResponse:
    """Convert database article schema to API response model"""
    article_dict = article_db.model_dump(by_alias=False)
    
    # Only include fields that are in the ArticleResponse model
    response_fields = ArticleResponse.model_fields.keys()
    filtered_article = {k: v for k, v in article_dict.items() if k in response_fields}
    
    return ArticleResponse(**filtered_article)

def article_dict_to_response(article_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a dictionary representation of an article to a response format"""
    # Clean up MongoDB specific fields
    cleaned_dict = clean_document(article_dict)
    
    # Return the cleaned dictionary
    return cleaned_dict

def create_article_dict(article_create: ArticleCreate) -> Dict[str, Any]:
    """Create a dict for MongoDB article document from ArticleCreate model"""
    article_dict = article_create.model_dump()
    return article_dict

def convert_to_response_list(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a list of article dictionaries to response format"""
    return [article_dict_to_response(article) for article in articles]