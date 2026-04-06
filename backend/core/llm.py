"""Ollama LLM wrapper for InterviewPilot."""

import json
import logging
from typing import Any

import httpx

from config import OLLAMA_BASE_URL, LLM_MODEL, LLM_TEMPERATURE, LLM_TIMEOUT

logger = logging.getLogger(__name__)


class OllamaLLM:
    """Async wrapper for Ollama API with structured output support."""

    def __init__(
        self,
        model: str = LLM_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        temperature: float = LLM_TEMPERATURE,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature

    async def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate text from a prompt."""
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                return response.json()["response"]
            except httpx.HTTPError as e:
                logger.error("Ollama generate failed: %s", e)
                raise RuntimeError(f"LLM generation failed: {e}") from e

    async def generate_json(self, prompt: str, max_tokens: int = 2048) -> dict[str, Any]:
        """Generate structured JSON output from a prompt."""
        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, no code fences. "
            "Just the raw JSON object."
        )
        raw = await self.generate(json_prompt, max_tokens)
        cleaned = raw.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from LLM response: %s", cleaned[:200])
            return {"error": "Failed to parse LLM response", "raw": cleaned[:500]}

    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 2048) -> str:
        """Chat completion with message history."""
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
            except httpx.HTTPError as e:
                logger.error("Ollama chat failed: %s", e)
                raise RuntimeError(f"LLM chat failed: {e}") from e

    async def check_health(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = [m["name"] for m in response.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            return False


# Singleton instance
llm = OllamaLLM()
