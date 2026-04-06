"""ChromaDB vector store operations."""

import logging
from typing import Optional

from core.rag import add_document, chunk_text, get_collection, query_documents

logger = logging.getLogger(__name__)


async def index_document(doc_id: str, text: str, doc_type: str) -> int:
    """Index a document's text into the vector store.

    Returns:
        Number of chunks indexed.
    """
    chunks = chunk_text(text, chunk_size=300, overlap=30)
    if not chunks:
        logger.warning("No chunks generated for document %s", doc_id)
        return 0

    metadata = [
        {"doc_id": doc_id, "doc_type": doc_type, "chunk_index": i}
        for i in range(len(chunks))
    ]

    await add_document(doc_id, chunks, metadata)
    logger.info("Indexed %d chunks for document %s (%s)", len(chunks), doc_id, doc_type)
    return len(chunks)


async def search_context(
    query: str,
    doc_ids: Optional[list[str]] = None,
    n_results: int = 5,
) -> str:
    """Search for relevant context from indexed documents.

    Returns:
        Concatenated text of top matching chunks.
    """
    where = None
    if doc_ids:
        where = {"doc_id": {"$in": doc_ids}}

    results = await query_documents(query, n_results=n_results, where=where)
    if not results:
        return ""

    context_parts = [r["text"] for r in results]
    return "\n\n".join(context_parts)


def clear_document(doc_id: str) -> None:
    """Remove all chunks for a document from the vector store."""
    collection = get_collection()
    try:
        collection.delete(where={"doc_id": doc_id})
        logger.info("Cleared vector store entries for document %s", doc_id)
    except Exception as e:
        logger.error("Failed to clear document %s: %s", doc_id, e)
