"""Document upload and parsing API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import UPLOAD_DIR
from db.database import get_document, save_document
from db.vector_store import index_document
from models.schemas import DocumentResponse, DocumentUploadRequest
from parsers.jd_parser import parse_job_description
from parsers.resume_parser import extract_text_from_pdf, parse_resume

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(request: DocumentUploadRequest):
    """Upload and parse a resume or job description."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Document text cannot be empty.")

    doc_type = request.doc_type
    if doc_type not in ("resume", "job_description"):
        raise HTTPException(status_code=400, detail="doc_type must be 'resume' or 'job_description'.")

    # Parse the document
    logger.info("Parsing %s document (%d chars)...", doc_type, len(text))
    if doc_type == "resume":
        parsed = await parse_resume(text)
    else:
        parsed = await parse_job_description(text)

    # Save to database
    doc_id = await save_document(doc_type, text, parsed)

    # Index in vector store for RAG
    try:
        chunks_count = await index_document(doc_id, text, doc_type)
        logger.info("Indexed %d chunks for %s", chunks_count, doc_id)
    except Exception as e:
        logger.warning("Vector indexing failed (non-critical): %s", e)

    return DocumentResponse(
        id=doc_id,
        doc_type=doc_type,
        parsed_data=parsed,
        created_at="now",
    )


@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    doc_type: str = Form("resume"),
):
    """Upload a PDF file for parsing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Save uploaded file
    file_path = UPLOAD_DIR / f"{file.filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Extract text from PDF
    text = extract_text_from_pdf(str(file_path))
    if not text:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    # Parse the document
    if doc_type == "resume":
        parsed = await parse_resume(text)
    else:
        parsed = await parse_job_description(text)

    doc_id = await save_document(doc_type, text, parsed)

    try:
        await index_document(doc_id, text, doc_type)
    except Exception as e:
        logger.warning("Vector indexing failed: %s", e)

    return DocumentResponse(
        id=doc_id,
        doc_type=doc_type,
        parsed_data=parsed,
        created_at="now",
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document_by_id(doc_id: str):
    """Get a parsed document by ID."""
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentResponse(
        id=doc["id"],
        doc_type=doc["type"],
        parsed_data=doc["parsed_data"],
        created_at=str(doc["created_at"]),
    )
