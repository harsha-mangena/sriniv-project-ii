"""RAG pipeline using ChromaDB for document retrieval."""

import logging
from typing import List, Optional

import chromadb

from config import CHROMA_DB_PATH
from core.embeddings import generate_embedding

logger = logging.getLogger(__name__)

# Initialize ChromaDB
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Get or create ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return _chroma_client


def get_collection(name: str = "documents"):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


async def add_document(
    doc_id: str,
    chunks: List[str],
    metadata: Optional[List[dict]] = None,
    collection_name: str = "documents",
) -> None:
    """Add document chunks to the vector store."""
    collection = get_collection(collection_name)
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    embeddings = []
    for chunk in chunks:
        emb = await generate_embedding(chunk)
        embeddings.append(emb)

    meta = metadata or [{"doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=meta,
    )
    logger.info("Added %d chunks for document %s", len(chunks), doc_id)


async def query_documents(
    query: str,
    n_results: int = 5,
    collection_name: str = "documents",
    where: Optional[dict] = None,
) -> List[dict]:
    """Query the vector store for relevant document chunks."""
    collection = get_collection(collection_name)
    query_embedding = await generate_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )

    documents = []
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            documents.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
    return documents


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks
