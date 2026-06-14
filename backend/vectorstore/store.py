"""ChromaDB vector store with lazy initialization and semantic retrieval."""
from __future__ import annotations
import os
import chromadb
from chromadb.utils import embedding_functions
from .seed_data import SEED_DOCUMENTS

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "incident_playbooks"

_client: chromadb.Client | None = None
_collection: chromadb.Collection | None = None


def _get_ef():
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    # Use sentence-transformers locally (no API key needed) for embeddings
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is not None:
        return _collection
    _client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = _get_ef()
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    if _collection.count() == 0:
        _seed_collection(_collection)
    return _collection


def _seed_collection(collection: chromadb.Collection) -> None:
    collection.add(
        ids=[doc["id"] for doc in SEED_DOCUMENTS],
        documents=[doc["content"] for doc in SEED_DOCUMENTS],
        metadatas=[{"title": doc["title"]} for doc in SEED_DOCUMENTS],
    )


def retrieve_similar_playbooks(query: str, top_k: int = 3) -> list[str]:
    """Return top_k playbook texts most similar to the query."""
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas"],
    )
    playbooks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        playbooks.append(f"## {meta['title']}\n{doc}")
    return playbooks
