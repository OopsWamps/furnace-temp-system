from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import settings, setup_logging
from app.api import api_router

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting furnace backend service...")
    logger.info(f"Service will run on {settings.HOST}:{settings.PORT}")
    yield
    logger.info("Shutting down furnace backend service...")


app = FastAPI(
    title="退火炉温度预测系统 API",
    description="退火炉全流程温度预测与过热报警系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


if __name__ == "__main__":
    import sys
    import uvicorn

    is_frozen = getattr(sys, 'frozen', False)
    uvicorn.run(
        app if is_frozen else "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG and not is_frozen,
    )
