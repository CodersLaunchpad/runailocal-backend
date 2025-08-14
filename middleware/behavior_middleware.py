from fastapi import Request, Response
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import uuid
from services.behavior_service import BehaviorService
from models.behavior_models import UserActivityCreate
from models.enums import ActionType
from dependencies.db import get_db
import jwt
from config import JWT_SECRET_KEY, JWT_ALGORITHM
import re
import asyncio

class BehaviorTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track user behavior"""
    
    def __init__(self, app, track_anonymous: bool = False):
        super().__init__(app)
        self.track_anonymous = track_anonymous
        self.behavior_service = None
        
        # Patterns to match article views
        self.article_view_patterns = [
            re.compile(r"/articles/([a-f0-9]{24})$"),
            re.compile(r"/articles/([a-f0-9]{24})/.*"),
        ]
        
        # Patterns to match search requests
        self.search_patterns = [
            re.compile(r"/search/.*"),
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Initialize behavior service if not already done
        if self.behavior_service is None:
            db = await get_db()
            self.behavior_service = BehaviorService(db)
        
        # Get or create session ID
        session_id = self._get_or_create_session_id(request)
        
        # Extract user info
        user_id = await self._get_user_id(request)
        
        # Process request
        response = await call_next(request)
        
        # Track behavior asynchronously (don't wait for completion)
        if user_id or self.track_anonymous:
            asyncio.create_task(
                self._track_request_behavior(
                    request, response, user_id, session_id, start_time
                )
            )
        
        # Add session ID to response headers
        response.headers["X-Session-ID"] = session_id
        
        return response
    
    def _get_or_create_session_id(self, request: Request) -> str:
        """Get existing session ID or create new one"""
        # Check for existing session ID in headers or cookies
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            session_id = request.cookies.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        
        return session_id
    
    async def _get_user_id(self, request: Request) -> str:
        """Extract user ID from JWT token"""
        try:
            # Check for Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return None
            
            # Extract token
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                return payload.get("id")  # User ID
            
        except Exception:
            # If token is invalid or expired, continue without user ID
            pass
        
        return None
    
    async def _track_request_behavior(
        self, 
        request: Request, 
        response: Response,
        user_id: str, 
        session_id: str, 
        start_time: float
    ):
        """Track user behavior based on request patterns"""
        try:
            path = request.url.path
            method = request.method
            processing_time = time.time() - start_time
            
            # Extract additional context
            user_agent = request.headers.get("User-Agent", "")
            device_type = self._detect_device_type(user_agent)
            referrer = request.headers.get("Referer")
            
            # Track article views
            if method == "GET" and response.status_code == 200:
                article_id = self._extract_article_id(path)
                if article_id:
                    await self._track_article_view(
                        user_id, article_id, session_id, device_type, referrer
                    )
            
            # Track search queries
            elif method == "GET" and any(pattern.match(path) for pattern in self.search_patterns):
                search_query = request.query_params.get("q") or request.query_params.get("query")
                if search_query:
                    await self._track_search(
                        user_id, search_query, session_id, device_type
                    )
            
            # Track API interactions
            elif response.status_code in [200, 201] and user_id:
                await self._track_api_interaction(
                    user_id, path, method, session_id, processing_time
                )
                
        except Exception as e:
            # Log error but don't interrupt request flow
            print(f"Error tracking behavior: {e}")
    
    def _extract_article_id(self, path: str) -> str:
        """Extract article ID from URL path"""
        for pattern in self.article_view_patterns:
            match = pattern.match(path)
            if match:
                return match.group(1)
        return None
    
    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        user_agent_lower = user_agent.lower()
        
        if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone", "ipad"]):
            if "ipad" in user_agent_lower or "tablet" in user_agent_lower:
                return "tablet"
            return "mobile"
        return "desktop"
    
    async def _track_article_view(
        self, 
        user_id: str, 
        article_id: str, 
        session_id: str,
        device_type: str,
        referrer: str
    ):
        """Track article view"""
        if user_id:
            await self.behavior_service.track_article_view(
                user_id=user_id,
                article_id=article_id,
                session_id=session_id,
                device_type=device_type,
                referrer=referrer
            )
    
    async def _track_search(
        self, 
        user_id: str, 
        search_query: str, 
        session_id: str,
        device_type: str
    ):
        """Track search queries"""
        if user_id:
            await self.behavior_service.log_activity(
                user_id=user_id,
                activity=UserActivityCreate(
                    action=ActionType.SEARCH,
                    search_query=search_query,
                    device_type=device_type
                ),
                session_id=session_id
            )
    
    async def _track_api_interaction(
        self, 
        user_id: str, 
        path: str, 
        method: str, 
        session_id: str,
        processing_time: float
    ):
        """Track general API interactions"""
        # Track specific API patterns
        if "/articles/" in path and method == "POST":
            # Article interactions (like, bookmark, etc.)
            if "/like" in path:
                article_id = self._extract_article_id_from_interaction(path)
                if article_id:
                    await self.behavior_service.log_activity(
                        user_id=user_id,
                        activity=UserActivityCreate(
                            action=ActionType.LIKE,
                            article_id=article_id
                        ),
                        session_id=session_id
                    )
            
            elif "/bookmark" in path:
                article_id = self._extract_article_id_from_interaction(path)
                if article_id:
                    await self.behavior_service.log_activity(
                        user_id=user_id,
                        activity=UserActivityCreate(
                            action=ActionType.BOOKMARK,
                            article_id=article_id
                        ),
                        session_id=session_id
                    )
        
        elif "/users/follow/" in path and method == "POST":
            # Follow actions
            author_id = path.split("/follow/")[-1]
            if author_id:
                await self.behavior_service.log_activity(
                    user_id=user_id,
                    activity=UserActivityCreate(
                        action=ActionType.FOLLOW,
                        author_id=author_id
                    ),
                    session_id=session_id
                )
    
    def _extract_article_id_from_interaction(self, path: str) -> str:
        """Extract article ID from interaction paths like /articles/{id}/like"""
        parts = path.split("/")
        if len(parts) >= 3 and parts[1] == "articles":
            return parts[2]
        return None


class ReadingSessionMiddleware(BaseHTTPMiddleware):
    """Middleware specifically for tracking detailed reading sessions"""
    
    def __init__(self, app):
        super().__init__(app)
        self.behavior_service = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Initialize behavior service if not already done
        if self.behavior_service is None:
            db = await get_db()
            self.behavior_service = BehaviorService(db)
        
        response = await call_next(request)
        
        # Only track for article pages with successful responses
        if (request.method == "GET" and 
            response.status_code == 200 and 
            "/articles/" in request.url.path):
            
            user_id = await self._get_user_id(request)
            article_id = self._extract_article_id(request.url.path)
            
            if user_id and article_id:
                # Start reading session (this can be enhanced with frontend integration)
                session_id = await self.behavior_service.start_reading_session(
                    user_id=user_id,
                    session=ReadingSessionCreate(
                        article_id=article_id,
                        device_type=self._detect_device_type(
                            request.headers.get("User-Agent", "")
                        )
                    )
                )
                response.headers["X-Reading-Session"] = session_id
        
        return response
    
    async def _get_user_id(self, request: Request) -> str:
        """Extract user ID from JWT token"""
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                return payload.get("id")
        except Exception:
            pass
        return None
    
    def _extract_article_id(self, path: str) -> str:
        """Extract article ID from URL path"""
        match = re.match(r"/articles/([a-f0-9]{24})", path)
        return match.group(1) if match else None
    
    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        user_agent_lower = user_agent.lower()
        
        if any(mobile in user_agent_lower for mobile in ["mobile", "android", "iphone", "ipad"]):
            if "ipad" in user_agent_lower or "tablet" in user_agent_lower:
                return "tablet"
            return "mobile"
        return "desktop"