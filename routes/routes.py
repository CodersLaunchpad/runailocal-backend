from fastapi import FastAPI
from .users import router as users_router
from .auth import router as auth_router
from .articles import router as articles_router
from .categories import router as categories_router
from .comments import router as comments_router
from .messages import router as messages_router

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
        messages_router,
        prefix="/messages",
        tags=["messages"],
    )