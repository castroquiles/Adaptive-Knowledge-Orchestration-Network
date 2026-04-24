"""
Axon Backend — FastAPI Application Entry Point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os

from src.api.routes import learner, session, curriculum, assessment, progress
from src.auth import router as auth_router
from src.db.connection import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("axon")

app = FastAPI(
    title="Axon",
    description="Adaptive Knowledge Orchestration Network — API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Axon backend started")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Axon backend stopped")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# Routes
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(learner.router, prefix="/learner", tags=["learner"])
app.include_router(session.router, prefix="/session", tags=["session"])
app.include_router(curriculum.router, prefix="/curriculum", tags=["curriculum"])
app.include_router(assessment.router, prefix="/assessment", tags=["assessment"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
