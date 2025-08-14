# Recommendation System Implementation Plan

## Overview

This document outlines a comprehensive plan for implementing a semantic similarity-based recommendation system for the runailocal platform using ChromaDB and Ollama embeddings. The system will suggest articles to users based on their behavior, preferences, and content similarity while respecting subscription tiers.

## Current System Foundation

### Technology Stack
- **Framework**: FastAPI (Python)
- **Database**: MongoDB with Motor (async driver)
- **Authentication**: JWT with bcrypt password hashing
- **File Storage**: MinIO object storage
- **Email Service**: SMTP integration

### Existing Data Models

#### Users Model
```python
# Key user fields for recommendations:
- id: str
- username: str
- email: EmailStr
- user_type: str ("normal", "author", "admin")
- likes: List[str] (article IDs)
- following: List[str] (user IDs)  
- followers: List[str] (user IDs)
- bookmarks: List[str] (article IDs)
- user_details: Dict (reading preferences, etc.)
- last_login: Optional[datetime]
- created_at: datetime
```

#### Articles Model
```python
# Key article fields for recommendations:
- id: str
- name: str (title)
- content: str
- excerpt: Optional[str]
- category_id: str
- author_id: str
- tags: List[str]
- views: int (view count tracking)
- likes: int 
- bookmarked_by: List[str] (user IDs)
- status: str ("draft", "published", etc.)
- is_spotlight: bool
- is_popular: bool
- created_at: datetime
- updated_at: datetime
```

### Available Categories
- Artificial Intelligence
- General
- VLM (Video Language Models)
- Machine Learning
- Robotics
- Tech Ethics

### Current Behavioral Data Sources

#### Explicit Feedback
- ✅ Likes/unlikes on articles
- ✅ Bookmarks/unbookmarks
- ✅ Following/unfollowing authors
- ✅ Comments on articles

#### Implicit Feedback
- ✅ Article view counts (stored but not incremented automatically)
- ✅ User last login timestamps
- ✅ Article creation and update patterns
- ✅ Search queries and results

## System Architecture

### Phase 1: Foundation Enhancement

#### 1. Enhanced User Behavior Tracking
- Add automatic article view tracking middleware
- Implement comprehensive user activity logging
- Track reading time and scroll depth
- Add user preference collection (topics, reading frequency)
- Create subscription tier differentiation

#### 2. Content Analysis Pipeline
- Extract article text features (title, content, excerpt, tags)
- Implement content preprocessing (cleaning, tokenization)
- Add subscription-based content flagging
- Create article quality scoring based on engagement

### Phase 2: ChromaDB Integration

#### 3. Vector Database Setup
- Install and configure ChromaDB
- Create collections for:
  - Article embeddings (title + content + tags)
  - User preference embeddings
  - Category embeddings
- Implement embedding storage and retrieval APIs

#### 4. Ollama Embeddings Service
- Set up Ollama with appropriate embedding model (e.g., `nomic-embed-text`)
- Create embedding generation service
- Implement batch processing for existing articles
- Add real-time embedding generation for new content

### Phase 3: Recommendation Engine

#### 5. Multi-Modal Recommendation Algorithm

**A. Content-Based Filtering (Semantic Similarity)**
- Generate article embeddings using Ollama
- Create user reading profile embeddings based on liked/bookmarked articles
- Use ChromaDB similarity search to find similar articles
- Weight by subscription status and content quality

**B. Collaborative Filtering**
- User-item interaction matrix (likes, bookmarks, views)
- Find similar users based on behavior patterns
- Recommend articles liked by similar users
- Handle cold-start problem for new users

**C. Hybrid Approach**
- Combine semantic similarity (60%) + collaborative filtering (40%)
- Add popularity boosting for trending articles
- Apply subscription tier filtering
- Include social signals (followed authors)

### Phase 4: Implementation Components

#### 6. New Database Collections

**User Activity Logs**
```python
{
  "user_id": str,
  "action": str,  # view, like, bookmark, share, comment
  "article_id": str,
  "timestamp": datetime,
  "session_id": str,
  "reading_time": int,  # seconds
  "scroll_percentage": float
}
```

**User Preferences**
```python
{
  "user_id": str,
  "preferred_categories": List[str],
  "preferred_tags": List[str],
  "reading_frequency": str,  # daily, weekly, monthly
  "content_length_preference": str,  # short, medium, long
  "subscription_tier": str  # free, premium
}
```

**Article Embeddings Cache**
```python
{
  "article_id": str,
  "embedding": List[float],
  "content_hash": str,
  "generated_at": datetime,
  "model_version": str
}
```

#### 7. New API Endpoints

**Recommendation APIs**
```python
GET /recommendations/for-me  # Personalized recommendations
GET /recommendations/similar/{article_id}  # Similar articles
GET /recommendations/trending  # Popular content
GET /recommendations/category/{category_id}  # Category-based
```

**Behavior Tracking APIs**
```python
POST /behavior/view  # Track article views
POST /behavior/reading-session  # Track reading metrics
GET /behavior/preferences  # Get user preferences
PUT /behavior/preferences  # Update user preferences
```

**Embeddings Management**
```python
POST /embeddings/generate/{article_id}  # Generate embeddings
POST /embeddings/batch-generate  # Bulk embedding generation
GET /embeddings/similar  # Find similar content
```

### Phase 5: Recommendation Logic Flow

#### Real-time Recommendation Pipeline

**For Logged-in Users:**
1. Fetch user behavior data (likes, bookmarks, views, reading time)
2. Generate user preference embedding from historical data
3. Query ChromaDB for semantically similar articles
4. Apply collaborative filtering based on similar users
5. Filter by subscription tier and content availability
6. Boost articles from followed authors
7. Apply diversity and freshness factors
8. Return ranked recommendations

**For Anonymous Users:**
1. Use trending/popular articles as base
2. Apply category-based recommendations
3. Use session behavior if available
4. Focus on free content only

### Phase 6: Advanced Features

#### 9. Personalization Enhancements
- Time-based recommendations (morning vs evening reading)
- Seasonal content boosting
- Reading streak maintenance
- Cross-category discovery suggestions

#### 10. Performance Optimization
- Precompute recommendations for active users
- Cache embedding results
- Implement incremental learning
- Add A/B testing framework for recommendation algorithms

### Phase 7: Analytics & Monitoring

#### 11. Recommendation Quality Metrics
- Click-through rates on recommendations
- Reading completion rates
- User engagement improvement
- Content discovery success rate
- Subscription conversion tracking

#### 12. System Performance Monitoring
- Embedding generation latency
- ChromaDB query performance
- Recommendation API response times
- Model accuracy metrics

## Technical Implementation Strategy

### ChromaDB Setup
- Use persistent storage for production
- Implement collection management utilities
- Add backup and recovery procedures
- Configure appropriate similarity metrics (cosine, euclidean)

### Ollama Integration
- Deploy Ollama service (local or containerized)
- Select optimal embedding model for text similarity
- Implement retry and error handling
- Add embedding versioning for model updates

### Data Pipeline
- Create batch job for historical article embedding
- Implement real-time embedding for new content
- Add data quality validation
- Create embedding refresh procedures

## Implementation Timeline

### Week 1-2: Foundation
- Enhance user behavior tracking
- Set up ChromaDB and Ollama services
- Create new database collections

### Week 3-4: Core Engine
- Implement embedding generation pipeline
- Build basic recommendation algorithms
- Create new API endpoints

### Week 5-6: Integration & Testing
- Integrate recommendation system with existing APIs
- Implement caching and optimization
- Add comprehensive testing

### Week 7-8: Advanced Features
- Add personalization enhancements
- Implement analytics and monitoring
- Performance tuning and optimization

## Success Metrics

- **User Engagement**: Increase in article views and reading time
- **Content Discovery**: Improved cross-category article consumption
- **User Retention**: Higher return visit rates
- **Subscription Conversion**: Increased premium subscriptions through better content matching
- **System Performance**: Sub-100ms recommendation response times

## Risk Mitigation

- **Cold Start Problem**: Use popularity-based recommendations for new users
- **Computational Overhead**: Implement caching and batch processing
- **Data Privacy**: Ensure all user behavior tracking complies with privacy regulations
- **Model Drift**: Regular retraining and validation of embedding models