"""LLM provider abstraction for InterviewPilot.

Supports multiple backends:
- Ollama (local, default)
- Google Gemini (cloud, free tier available)

Usage:
    from core.llm import get_llm
    llm = get_llm()  # Returns configured provider instance
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OLLAMA_BASE_URL,
)

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate text from a prompt."""

    @abstractmethod
    async def generate_json(self, prompt: str, max_tokens: int = 2048) -> dict[str, Any]:
        """Generate structured JSON output from a prompt."""

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 2048) -> str:
        """Chat completion with message history."""

    def _clean_json_response(self, raw: str) -> dict[str, Any]:
        """Parse JSON from an LLM response, handling markdown fences."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    pass
            # Try array
            start = cleaned.find("[")
            end = cleaned.rfind("]") + 1
            if start != -1 and end > start:
                try:
                    result = json.loads(cleaned[start:end])
                    return {"items": result}
                except json.JSONDecodeError:
                    pass
            logger.warning("Failed to parse JSON from LLM response: %s", cleaned[:200])
            return {"error": "Failed to parse LLM response", "raw": cleaned[:500]}


class OllamaLLM(BaseLLM):
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
        return self._clean_json_response(raw)

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


class GeminiLLM(BaseLLM):
    """Google Gemini API wrapper using the google-generativeai SDK."""

    def __init__(
        self,
        api_key: str = GEMINI_API_KEY,
        model: str = GEMINI_MODEL,
        temperature: float = LLM_TEMPERATURE,
    ):
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. Set it in your environment: "
                "export GEMINI_API_KEY='your-key-here'"
            )
        self.api_key = api_key
        self.model_name = model
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            try:
                from google import generativeai as genai

                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={
                        "temperature": self.temperature,
                    },
                )
            except ImportError:
                raise RuntimeError(
                    "google-generativeai package not installed. "
                    "Run: pip install google-generativeai"
                )
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 2048) -> str:
        """Generate text from a prompt using Gemini."""
        import asyncio

        client = self._get_client()
        try:
            response = await asyncio.to_thread(
                client.generate_content,
                prompt,
                generation_config={"max_output_tokens": max_tokens},
            )
            return response.text
        except Exception as e:
            logger.error("Gemini generate failed: %s", e)
            raise RuntimeError(f"Gemini generation failed: {e}") from e

    async def generate_json(self, prompt: str, max_tokens: int = 2048) -> dict[str, Any]:
        """Generate structured JSON output from Gemini."""
        json_prompt = (
            f"{prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, no code fences. "
            "Just the raw JSON object."
        )
        raw = await self.generate(json_prompt, max_tokens)
        return self._clean_json_response(raw)

    async def chat(self, messages: list[dict[str, str]], max_tokens: int = 2048) -> str:
        """Chat completion with message history using Gemini."""
        import asyncio

        client = self._get_client()

        # Convert standard message format to Gemini format
        gemini_history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        try:
            chat = client.start_chat(history=gemini_history)
            last_msg = messages[-1]["content"] if messages else ""
            response = await asyncio.to_thread(
                chat.send_message,
                last_msg,
                generation_config={"max_output_tokens": max_tokens},
            )
            return response.text
        except Exception as e:
            logger.error("Gemini chat failed: %s", e)
            raise RuntimeError(f"Gemini chat failed: {e}") from e

    async def check_health(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            response = await self.generate("Say 'ok'", max_tokens=10)
            return bool(response)
        except Exception:
            return False


def get_llm(provider: str | None = None) -> BaseLLM:
    """Factory function to get the configured LLM provider.

    Args:
        provider: Override the configured provider. "ollama" or "gemini".

    Returns:
        An instance of the configured LLM provider.
    """
    provider = provider or LLM_PROVIDER
    if provider == "gemini":
        return GeminiLLM()
    return OllamaLLM()


# Default singleton instance — used by all modules
llm: BaseLLM = get_llm()
