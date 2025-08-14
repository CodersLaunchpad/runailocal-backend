import re
import html
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import unicodedata
from collections import Counter
import hashlib

class ContentPreprocessor:
    """Utility class for preprocessing article content for analysis and embeddings"""
    
    def __init__(self):
        # Common stop words for content analysis
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'this', 'that', 'these', 'those', 'i',
            'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
            'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves',
            'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is',
            'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
            'do', 'does', 'did', 'doing', 'would', 'should', 'could', 'can', 'will', 'may',
            'might', 'must', 'shall'
        }
        
        # HTML tag patterns
        self.html_pattern = re.compile(r'<[^>]+>')
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Text cleaning patterns
        self.whitespace_pattern = re.compile(r'\s+')
        self.punctuation_pattern = re.compile(r'[^\w\s]')
        self.number_pattern = re.compile(r'\d+')
    
    def clean_html(self, text: str) -> str:
        """Remove HTML tags and decode HTML entities"""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        text = self.html_pattern.sub(' ', text)
        
        # Normalize whitespace
        text = self.whitespace_pattern.sub(' ', text)
        
        return text.strip()
    
    def extract_text_features(self, content: str) -> Dict[str, Any]:
        """Extract various text features from content"""
        if not content:
            return {
                'word_count': 0,
                'sentence_count': 0,
                'paragraph_count': 0,
                'avg_sentence_length': 0,
                'readability_score': 0,
                'complexity_score': 0
            }
        
        # Clean content
        clean_content = self.clean_html(content)
        
        # Count words
        words = clean_content.split()
        word_count = len(words)
        
        # Count sentences (approximate)
        sentences = re.split(r'[.!?]+', clean_content)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Count paragraphs
        paragraphs = clean_content.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        # Calculate average sentence length
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Simple readability score (Flesch-like approximation)
        avg_words_per_sentence = word_count / max(sentence_count, 1)
        long_words = len([word for word in words if len(word) > 6])
        syllable_density = long_words / max(word_count, 1)
        
        readability_score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * syllable_density)
        readability_score = max(0, min(100, readability_score))  # Clamp between 0-100
        
        # Complexity score based on vocabulary diversity
        unique_words = len(set([word.lower() for word in words if word.isalpha()]))
        complexity_score = unique_words / max(word_count, 1) * 100
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
            'avg_sentence_length': round(avg_sentence_length, 2),
            'readability_score': round(readability_score, 2),
            'complexity_score': round(complexity_score, 2),
            'character_count': len(clean_content),
            'unique_word_ratio': round(unique_words / max(word_count, 1), 3)
        }
    
    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[Dict[str, Any]]:
        """Extract keywords from text with frequency scores"""
        if not text:
            return []
        
        # Clean and normalize text
        clean_text = self.clean_html(text).lower()
        clean_text = self.punctuation_pattern.sub(' ', clean_text)
        clean_text = self.number_pattern.sub(' ', clean_text)
        clean_text = unicodedata.normalize('NFKD', clean_text)
        
        # Extract words
        words = [word for word in clean_text.split() 
                if word and len(word) > 2 and word not in self.stop_words]
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Extract top keywords
        keywords = []
        for word, count in word_counts.most_common(max_keywords):
            keywords.append({
                'keyword': word,
                'frequency': count,
                'score': count / len(words) if words else 0
            })
        
        return keywords
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract simple entities like URLs, emails, and mentions"""
        entities = {
            'urls': [],
            'emails': [],
            'mentions': [],  # @username patterns
            'hashtags': []   # #tag patterns
        }
        
        if not text:
            return entities
        
        # Extract URLs
        entities['urls'] = self.url_pattern.findall(text)
        
        # Extract emails
        entities['emails'] = self.email_pattern.findall(text)
        
        # Extract mentions (@username)
        mention_pattern = re.compile(r'@(\w+)')
        entities['mentions'] = mention_pattern.findall(text)
        
        # Extract hashtags (#tag)
        hashtag_pattern = re.compile(r'#(\w+)')
        entities['hashtags'] = hashtag_pattern.findall(text)
        
        return entities
    
    def preprocess_for_embedding(self, title: str, content: str, tags: List[str] = None) -> str:
        """Preprocess article content for embedding generation"""
        if not content and not title:
            return ""
        
        # Clean title and content
        clean_title = self.clean_html(title or "")
        clean_content = self.clean_html(content or "")
        
        # Combine title (with higher weight), content, and tags
        embedding_text_parts = []
        
        if clean_title:
            # Give title higher importance by repeating it
            embedding_text_parts.extend([clean_title] * 3)
        
        if clean_content:
            # Limit content to avoid token limits (approximate)
            if len(clean_content) > 2000:
                # Take first 1500 chars and last 500 chars
                clean_content = clean_content[:1500] + " ... " + clean_content[-500:]
            embedding_text_parts.append(clean_content)
        
        if tags:
            # Add tags as important keywords
            tag_text = " ".join([f"#{tag}" for tag in tags])
            embedding_text_parts.extend([tag_text] * 2)
        
        return " ".join(embedding_text_parts)
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for change detection"""
        if not content:
            return ""
        
        # Normalize content for consistent hashing
        normalized = self.clean_html(content).lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def estimate_reading_time(self, content: str, words_per_minute: int = 200) -> int:
        """Estimate reading time in minutes"""
        if not content:
            return 0
        
        clean_content = self.clean_html(content)
        word_count = len(clean_content.split())
        
        reading_time = max(1, round(word_count / words_per_minute))
        return reading_time
    
    def categorize_content_length(self, word_count: int) -> str:
        """Categorize content by length"""
        if word_count < 300:
            return "short"  # < 1.5 min read
        elif word_count < 1500:
            return "medium"  # 1.5-7.5 min read
        else:
            return "long"   # > 7.5 min read
    
    def extract_content_quality_features(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features that indicate content quality"""
        content = article.get('content', '')
        title = article.get('name', '')
        
        # Text features
        text_features = self.extract_text_features(content)
        
        # Keywords
        keywords = self.extract_keywords(content, max_keywords=10)
        
        # Entities
        entities = self.extract_entities(content)
        
        # Calculate quality indicators
        quality_features = {
            **text_features,
            'title_length': len(title),
            'has_excerpt': bool(article.get('excerpt')),
            'has_image': bool(article.get('image') or article.get('image_id')),
            'tag_count': len(article.get('tags', [])),
            'keyword_diversity': len(keywords),
            'url_count': len(entities['urls']),
            'content_hash': self.calculate_content_hash(content),
            'reading_time_minutes': self.estimate_reading_time(content),
            'content_length_category': self.categorize_content_length(text_features['word_count'])
        }
        
        # Quality score (0-100)
        quality_score = self._calculate_quality_score(quality_features)
        quality_features['quality_score'] = quality_score
        
        return quality_features
    
    def _calculate_quality_score(self, features: Dict[str, Any]) -> float:
        """Calculate overall content quality score"""
        score = 0
        max_score = 100
        
        # Word count contribution (0-25 points)
        word_count = features.get('word_count', 0)
        if word_count > 1000:
            score += 25
        elif word_count > 500:
            score += 20
        elif word_count > 200:
            score += 15
        elif word_count > 100:
            score += 10
        
        # Readability contribution (0-20 points)
        readability = features.get('readability_score', 0)
        if 60 <= readability <= 80:  # Good readability range
            score += 20
        elif 40 <= readability < 60 or 80 < readability <= 90:
            score += 15
        elif 20 <= readability < 40 or 90 < readability <= 100:
            score += 10
        
        # Structure contribution (0-15 points)
        if features.get('paragraph_count', 0) > 3:
            score += 8
        if features.get('sentence_count', 0) > 10:
            score += 7
        
        # Rich content contribution (0-20 points)
        if features.get('has_image'):
            score += 5
        if features.get('has_excerpt'):
            score += 5
        if features.get('tag_count', 0) > 2:
            score += 5
        if features.get('keyword_diversity', 0) > 5:
            score += 5
        
        # Title quality (0-10 points)
        title_length = features.get('title_length', 0)
        if 30 <= title_length <= 70:  # Good title length
            score += 10
        elif 20 <= title_length < 30 or 70 < title_length <= 100:
            score += 7
        
        # Complexity balance (0-10 points)
        complexity = features.get('complexity_score', 0)
        if 15 <= complexity <= 40:  # Good complexity balance
            score += 10
        elif 10 <= complexity < 15 or 40 < complexity <= 50:
            score += 7
        
        return min(score, max_score)
    
    def preprocess_batch_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess multiple articles for batch operations"""
        processed_articles = []
        
        for article in articles:
            try:
                # Extract content features
                quality_features = self.extract_content_quality_features(article)
                
                # Prepare embedding text
                embedding_text = self.preprocess_for_embedding(
                    title=article.get('name', ''),
                    content=article.get('content', ''),
                    tags=article.get('tags', [])
                )
                
                # Create processed article
                processed_article = {
                    **article,
                    'embedding_text': embedding_text,
                    'content_features': quality_features
                }
                
                processed_articles.append(processed_article)
                
            except Exception as e:
                print(f"Error processing article {article.get('_id', 'unknown')}: {e}")
                # Include article even if preprocessing fails
                processed_articles.append({
                    **article,
                    'embedding_text': article.get('name', '') + ' ' + article.get('content', '')[:500],
                    'content_features': {'quality_score': 0}
                })
        
        return processed_articles