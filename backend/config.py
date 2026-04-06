"""InterviewPilot configuration settings."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db_files"
UPLOAD_DIR = BASE_DIR / "uploads"

# Ensure directories exist
DB_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# LLM Provider settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" or "gemini"

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Database
SQLITE_DB_PATH = str(DB_DIR / "interviewpilot.db")
CHROMA_DB_PATH = str(DB_DIR / "chroma")

# LLM settings
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 2048
LLM_TIMEOUT = 120.0

# Interview settings
DEFAULT_PREP_QUESTIONS = 30
MAX_PREP_QUESTIONS = 50
MAX_FOLLOW_UPS_PER_QUESTION = 3
ATOM_PASS_THRESHOLD = 0.7
DIFFICULTY_INCREASE_THRESHOLD = 0.85
DIFFICULTY_DECREASE_THRESHOLD = 0.50

# Audio settings
WHISPER_MODEL_SIZE = "base"
AUDIO_SAMPLE_RATE = 16000

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:1420", "tauri://localhost"]
