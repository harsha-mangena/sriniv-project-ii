"""Embedding generation via Ollama."""

import logging
from typing import List

import httpx

from config import OLLAMA_BASE_URL, EMBED_MODEL, LLM_TIMEOUT

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]
        except httpx.HTTPError as e:
            logger.error("Embedding generation failed: %s", e)
            raise RuntimeError(f"Embedding failed: {e}") from e


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": EMBED_MODEL, "input": texts},
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except httpx.HTTPError as e:
            logger.error("Batch embedding failed: %s", e)
            raise RuntimeError(f"Batch embedding failed: {e}") from e
