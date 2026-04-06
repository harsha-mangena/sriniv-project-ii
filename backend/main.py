"""InterviewPilot — AI Interview Coach Backend."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from api.router import api_router
from db.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("interviewpilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting InterviewPilot backend...")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down InterviewPilot backend.")


app = FastAPI(
    title="InterviewPilot",
    description="AI-powered interview preparation and coaching engine using AoT+ToT hybrid reasoning.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "interviewpilot", "version": "0.1.0"}


@app.get("/api/settings")
async def get_settings():
    """Get current LLM provider settings."""
    return {
        "llm_provider": config.LLM_PROVIDER,
        "ollama_url": config.OLLAMA_BASE_URL,
        "ollama_model": config.LLM_MODEL,
        "gemini_model": config.GEMINI_MODEL,
        "gemini_api_key_set": bool(config.GEMINI_API_KEY),
    }


class SettingsUpdate(BaseModel):
    llm_provider: str | None = None
    ollama_url: str | None = None
    ollama_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None


@app.post("/api/settings")
async def update_settings(request: SettingsUpdate):
    """Update LLM provider settings at runtime."""
    import core.llm as llm_module

    if request.llm_provider is not None:
        config.LLM_PROVIDER = request.llm_provider
    if request.ollama_url is not None:
        config.OLLAMA_BASE_URL = request.ollama_url
    if request.ollama_model is not None:
        config.LLM_MODEL = request.ollama_model
    if request.gemini_api_key is not None:
        config.GEMINI_API_KEY = request.gemini_api_key
    if request.gemini_model is not None:
        config.GEMINI_MODEL = request.gemini_model

    # Reinitialize the singleton LLM instance
    llm_module.llm = llm_module.get_llm()

    return {
        "status": "updated",
        "llm_provider": config.LLM_PROVIDER,
        "ollama_url": config.OLLAMA_BASE_URL,
        "ollama_model": config.LLM_MODEL,
        "gemini_model": config.GEMINI_MODEL,
        "gemini_api_key_set": bool(config.GEMINI_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
