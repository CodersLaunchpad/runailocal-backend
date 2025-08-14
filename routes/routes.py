from fastapi import FastAPI
from .users import router as users_router
from .auth import router as auth_router
from .articles import router as articles_router
from .categories import router as categories_router
from .comments import router as comments_router
from .messages import router as message_routes
from .storage import router as storage_router
from .test import router as test_router
from .search import router as search_router
from .settings import router as settings_router
from .backup import router as backup_router

# Phase 1: Behavior Tracking and Content Quality Routes
from .behavior_routes import router as behavior_router
from .content_quality_routes import router as content_quality_router

def setup_routes(app: FastAPI):
    # You can add other routes directly to app here if needed
    @app.get("/")
    async def root():
        return {"message": "API is alive!"}

    # Include the router with a prefix
    app.include_router(
        auth_router,
        prefix="/auth",
        tags=["auth"],
    )
    
    app.include_router(
        users_router,
        prefix="/users",
        tags=["users"],
    )

    app.include_router(
        articles_router,
        prefix="/articles",
        tags=["articles"],
    )

    app.include_router(
        categories_router,
        prefix="/categories",
        tags=["categories"],
    )

    app.include_router(
        comments_router,
        prefix="/comments",
        tags=["comments"],
    )

    app.include_router(
        message_routes,
        prefix="/messages",
        tags=["messages"],
    )

    app.include_router(
        storage_router,
        prefix="/storage",
        tags=["storage"],
    )

    app.include_router(
        test_router,
        prefix="/test",
        tags=["test"],
    )

    app.include_router(
        search_router,
        prefix="/search",
        tags=["search"],
    )

    app.include_router(
        settings_router,
        prefix="/settings",
        tags=["settings"],
    )

    app.include_router(
        backup_router,
        prefix="/backup",
        tags=["backup"],
    )

    # Phase 1: Behavior Tracking and Content Quality Routes
    app.include_router(
        behavior_router,
        prefix="/api",
        tags=["behavior"],
    )

    app.include_router(
        content_quality_router,
        prefix="/api",
        tags=["content-quality"],
    )