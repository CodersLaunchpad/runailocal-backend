from fastapi import FastAPI
from users import router as users_router



def setup_routes(app: FastAPI):
    # You can add other routes directly to app here if needed
    @app.get("/")
    async def root():
        return {"message": "Welcome to the API"}

    # Include the router with a prefix
    app.include_router(
        users_router,
        prefix="/auth",
        tags=["auth"],
    )
    
    app.include_router(
        users_router,
        prefix="/users",
        tags=["users"],
    )

    app.include_router(
        users_router,
        prefix="/articles",
        tags=["articles"],
    )

    app.include_router(
        users_router,
        prefix="/categories",
        tags=["categories"],
    )

    app.include_router(
        users_router,
        prefix="/comments",
        tags=["comments"],
    )

    app.include_router(
        users_router,
        prefix="/messages",
        tags=["messages"],
    )