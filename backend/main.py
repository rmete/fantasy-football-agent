from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.redis_client import redis_cache
from app.tools.sleeper_client import sleeper_client
from app.api import sleeper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Fantasy Football AI Manager API")
    await redis_cache.connect()
    yield
    # Shutdown
    logger.info("Shutting down API")
    await sleeper_client.close()
    await redis_cache.close()

app = FastAPI(
    title="Fantasy Football AI Manager API",
    description="AI-powered fantasy football team management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sleeper.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Fantasy Football AI Manager API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
