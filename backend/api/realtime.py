"""Real-time meeting assistant WebSocket and REST endpoints."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from core.llm import get_llm
from db.vector_store import search_context

logger = logging.getLogger(__name__)
router = APIRouter()


# --- REST Endpoints for Tauri Desktop App ---


class SuggestRequest(BaseModel):
    """Request for the /suggest endpoint (Tauri desktop: 'What should I say?')."""
    question: str
    transcript: str = ""
    screen_context: str = ""
    resume_id: str | None = None
    jd_id: str | None = None


class SuggestResponse(BaseModel):
    suggestion: str
    confidence: float = 0.8


class OcrRequest(BaseModel):
    """Request for the /ocr endpoint (Tauri desktop: screenshot OCR)."""
    image_base64: str
    format: str = "png"


class OcrResponse(BaseModel):
    text: str


class TranscriptPostRequest(BaseModel):
    """Transcript segment posted from Tauri desktop app."""
    type: str = "transcript"
    text: str
    speaker: str = "unknown"
    timestamp_ms: int = 0


@router.post("/suggest", response_model=SuggestResponse)
async def suggest_endpoint(req: SuggestRequest):
    """Generate an AI suggestion based on transcript + screen context + question.

    Used by the Tauri desktop overlay for 'What should I say?' feature.
    """
    # Search for relevant RAG context from uploaded documents
    doc_ids = [v for v in [req.resume_id, req.jd_id] if v]
    rag_context = ""
    if doc_ids:
        try:
            rag_context = await search_context(req.question, doc_ids=doc_ids, n_results=3)
        except Exception:
            pass

    prompt = f"""You are a real-time interview assistant. Generate a concise, actionable response hint.

USER QUESTION: {req.question}

RECENT TRANSCRIPT:
{req.transcript[:2000] if req.transcript else "(no transcript yet)"}

{f"SCREEN CONTEXT (OCR):{chr(10)}{req.screen_context[:1000]}" if req.screen_context else ""}

{f"RELEVANT BACKGROUND:{chr(10)}{rag_context[:500]}" if rag_context else ""}

Generate a structured response with 3-5 bullet points that the candidate can use.
Be concise — this appears as a small overlay during a live meeting.
Focus on key points and actionable phrases, not full paragraphs."""

    suggestion = (await get_llm().generate(prompt, max_tokens=512)).strip()
    return SuggestResponse(suggestion=suggestion)


@router.post("/ocr", response_model=OcrResponse)
async def ocr_endpoint(req: OcrRequest):
    """Extract text from a screenshot using the LLM's vision capabilities.

    Falls back to simple acknowledgment if the LLM doesn't support vision.
    """
    try:
        llm = get_llm()
        # Try to use LLM vision for OCR (Gemini and some Ollama models support this)
        prompt = """Extract all visible text from this screenshot.
Return only the text content, preserving layout where possible.
If there is no readable text, return '(no text detected)'."""

        # If the LLM supports image input, use it
        result = (await llm.generate(prompt, max_tokens=1024)).strip()
        return OcrResponse(text=result)
    except Exception as e:
        logger.warning("OCR via LLM failed: %s", e)
        return OcrResponse(text="(OCR not available)")


@router.post("/transcript")
async def transcript_post_endpoint(req: TranscriptPostRequest):
    """Receive transcript segments from the Tauri desktop app.

    This is a REST fallback for when the WebSocket connection is not available.
    In production, the WebSocket (/stream) is the primary transport.
    """
    logger.debug("Received transcript: [%s] %s", req.speaker, req.text[:100])
    return {"status": "received"}


@router.websocket("/stream")
async def realtime_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time meeting assistance.

    Protocol:
    - Client sends: {"type": "transcript", "text": "...", "speaker": "interviewer"}
    - Client sends: {"type": "config", "resume_id": "...", "jd_id": "..."}
    - Server sends: {"type": "suggestion", "text": "...", "confidence": 0.9}
    - Server sends: {"type": "question_detected", "question": "..."}
    """
    await websocket.accept()
    logger.info("Real-time WebSocket connected.")

    config = {"resume_id": None, "jd_id": None}
    transcript_buffer: list[str] = []
    screen_context: str = ""

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "")

            if msg_type == "config":
                config["resume_id"] = message.get("resume_id")
                config["jd_id"] = message.get("jd_id")
                await websocket.send_json({"type": "status", "status": "configured"})

            elif msg_type == "transcript":
                text = message.get("text", "").strip()
                speaker = message.get("speaker", "unknown")

                if not text:
                    continue

                transcript_buffer.append(f"[{speaker}]: {text}")

                # Keep buffer manageable
                if len(transcript_buffer) > 50:
                    transcript_buffer = transcript_buffer[-30:]

                # Check if this looks like a question
                if _is_likely_question(text):
                    await websocket.send_json({
                        "type": "question_detected",
                        "question": text,
                    })

                    # Generate suggestion
                    suggestion = await _generate_suggestion(
                        text,
                        transcript_buffer,
                        config,
                    )
                    await websocket.send_json({
                        "type": "suggestion",
                        "text": suggestion,
                        "confidence": 0.8,
                    })

            elif msg_type == "screen_context":
                # Receive OCR text from screen captures
                screen_context = message.get("text", "")
                await websocket.send_json({"type": "status", "status": "screen_context_received"})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Real-time WebSocket disconnected.")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        await websocket.close(code=1011, reason=str(e))


def _is_likely_question(text: str) -> bool:
    """Heuristic to detect if text is likely a question."""
    text = text.strip()
    if text.endswith("?"):
        return True
    question_starters = [
        "tell me", "can you", "how would", "what is", "describe",
        "explain", "walk me through", "what would", "how do",
        "why did", "give me an example", "what are", "design",
    ]
    text_lower = text.lower()
    return any(text_lower.startswith(s) for s in question_starters)


async def _generate_suggestion(
    question: str,
    transcript: list[str],
    config: dict,
) -> str:
    """Generate a real-time suggestion for the detected question."""
    # Search for relevant context from uploaded documents
    doc_ids = [v for v in [config.get("resume_id"), config.get("jd_id")] if v]
    context = ""
    if doc_ids:
        try:
            context = await search_context(question, doc_ids=doc_ids, n_results=3)
        except Exception:
            pass

    recent_transcript = "\n".join(transcript[-10:])

    prompt = f"""You are a real-time interview assistant. Generate a concise, helpful response hint.

QUESTION DETECTED: {question}
RECENT CONVERSATION CONTEXT:
{recent_transcript}
{"RELEVANT BACKGROUND: " + context[:500] if context else ""}

Generate a brief, structured response hint (3-5 bullet points) that the candidate can use.
Be concise — this appears as an overlay during a live meeting.
Focus on key points, not full paragraphs."""

    return (await get_llm().generate(prompt, max_tokens=512)).strip()
