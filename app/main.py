from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.logging import logger

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="A scalable student-teacher matching system with ML-ready architecture"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix=settings.API_V1_PREFIX, tags=["matching"])


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

