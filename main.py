# main.py
from fastapi import FastAPI
import uvicorn

from db.db import init_db, close_db_connection
from routes.routes import setup_routes
from logger.logger import logger

# Try to import config - if any required configs are missing, 
# the app will exit before starting
try:
    import config
except Exception as e:
    logger.critical(f"Failed to load configuration: {e}")
    import sys
    sys.exit(1)


# Initialize FastAPI app
app = FastAPI(title="Content Management System API")

# Setup routes
setup_routes(app)

# Startup and shutdown events
@app.on_event("startup")
async def startup_db_client():
     # Validation can be done here too if needed
    logger.info("Starting up application")
    await init_db()

@app.on_event("shutdown")
async def shutdown_db_client():
    logger.info("Shutting down application")
    await close_db_connection()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)