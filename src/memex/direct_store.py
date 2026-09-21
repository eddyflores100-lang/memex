"""memex.direct_store — direct ChromaDB access without mem0 dependency.

AliceLabs proprietary addition. Replaces the mem0.Memory wrapper with
direct ChromaDB + Ollama calls, eliminating the hard dependency on mem0ai.

Benefits:
  - No mem0 telemetry (even if MEM0_TELEMETRY defaults to False)
  - No mem0's broken score_and_rank wrapper (bypassed in upstream too)
  - Faster boot (no mem0 config validation)
  - Fewer dependencies = smaller attack surface
  - Direct control over embeddings and vector store

Usage:
    from memex.direct_store import DirectStore
    store = DirectStore()
    store.add("memory text", user_id="agent")
    results = store.search("query", user_id="agent", limit=5)

This module is a drop-in replacement for mem0.Memory with the same
interface that server.py expects.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("memex.direct_store")


class DirectStore:
    """Direct ChromaDB + Ollama store — no mem0 dependency.

    Drop-in replacement for mem0.Memory with the interface that
    server.py and recall.py expect:
      - .add(text, user_id=...) → store
      - .search(query, user_id=..., limit=...) → query
      - .get_all(user_id=...) → list all
      - .vector_store → ChromaDB collection
      - .embedding_model → Ollama embedder
    """

    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.store_path = Path(cfg.get("store_path", str(Path.home() / ".memex" / "store")))
        self.collection_name = cfg.get("collection", "memex_memory")
        self.ollama_url = cfg.get("ollama_url", "http://127.0.0.1:11434")
        self.embed_model = cfg.get("embed_model", "nomic-embed-text")
        self._client = None
        self._collection = None
        self._embedder = None

    def _ensure_client(self) -> None:
        """Lazy-init ChromaDB client and collection."""
        if self._client is not None:
            return

        import chromadb
        self.store_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.store_path))

        # Get or create collection
        try:
            self._collection = self._client.get_collection(self.collection_name)
        except Exception:
            self._collection = self._client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        # Init Ollama embedder
        try:
            import ollama
            self._embedder = ollama.Client(host=self.ollama_url)
            # Verify connection
            self._embedder.list()
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.ollama_url}: {e}"
            ) from e

    def _embed(self, text: str, memory_action: str = "search") -> list[float]:
        """Generate embedding via Ollama."""
        self._ensure_client()

        # Use nomic prefixes for better retrieval
        prefix = "search_query: " if memory_action == "search" else "search_document: "
        response = self._embedder.embeddings(
            model=self.embed_model,
            prompt=prefix + text,
        )
        return response["embedding"]

    def add(self, text: str, user_id: str = "agent", metadata: dict | None = None) -> dict[str, Any]:
        """Store a memory verbatim (no LLM extraction)."""
        self._ensure_client()

        memory_id = str(uuid.uuid4())
        embedding = self._embed(text, memory_action="store")

        payload_meta = {
            "user_id": user_id,
            "data": text,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            payload_meta.update(metadata)

        self._collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[payload_meta],
        )

        return {"id": memory_id, "text": text}

    def search(
        self,
        query: str,
        user_id: str = "agent",
        limit: int = 5,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories via vector similarity."""
        self._ensure_client()

        embedding = self._embed(query, memory_action="search")

        where_filter = {"user_id": user_id}
        if filters:
            where_filter.update(filters)

        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            where=where_filter,
        )

        memories = []
        if results and results.get("ids"):
            for i, mid in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                # Convert to similarity: 1 - distance/2
                score = max(0.0, 1.0 - distance / 2)
                payload = results["metadatas"][0][i] if results.get("metadatas") else {}
                text = payload.get("data", results["documents"][0][i] if results.get("documents") else "")

                memories.append({
                    "id": mid,
                    "text": text,
                    "score": round(score, 3),
                    "metadata": payload,
                })

        return memories

    def get_all(self, user_id: str = "agent", limit: int = 100000) -> dict[str, Any]:
        """Get all memories for a user."""
        self._ensure_client()

        results = self._collection.get(
            where={"user_id": user_id},
            limit=limit,
        )

        memories = []
        if results and results.get("ids"):
            for i, mid in enumerate(results["ids"]):
                payload = results["metadatas"][i] if results.get("metadatas") else {}
                text = payload.get("data", results["documents"][i] if results.get("documents") else "")

                memories.append({
                    "id": mid,
                    "text": text,
                    "metadata": payload,
                })

        return {"results": memories}

    def count(self, user_id: str = "agent") -> int:
        """Count memories for a user."""
        self._ensure_client()
        try:
            return self._collection.count()
        except Exception:
            return 0

    def delete(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        self._ensure_client()
        self._collection.delete(ids=[memory_id])

    @property
    def vector_store(self):
        """Expose the ChromaDB collection for compatibility."""
        self._ensure_client()
        return _VectorStoreWrapper(self._collection)

    @property
    def embedding_model(self):
        """Expose embedder for compatibility."""
        self._ensure_client()
        return _EmbedderWrapper(self._embedder, self.embed_model)


class _VectorStoreWrapper:
    """Wrapper to match mem0's vector_store interface."""

    def __init__(self, collection):
        self.collection = collection

    def search(self, query: str = "", vectors=None, top_k: int = 5, filters: dict | None = None):
        """Search matching mem0's vector_store.search interface."""
        # This is used by server.py's /query endpoint
        # which bypasses mem0's broken score_and_rank
        results = self.collection.query(
            query_embeddings=vectors if vectors else [],
            query_texts=[query] if query else [],
            n_results=top_k,
            where=filters,
        )

        # Convert to mem0-like result objects
        from collections import namedtuple
        Result = namedtuple("Result", ["id", "score", "payload"])

        items = []
        if results and results.get("ids") and results["ids"][0]:
            for i, mid in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 0
                payload = results["metadatas"][0][i] if results.get("metadatas") else {}

                items.append(Result(
                    id=mid,
                    score=distance,
                    payload=payload,
                ))

        return items


class _EmbedderWrapper:
    """Wrapper to match mem0's embedding_model interface."""

    def __init__(self, ollama_client, model_name: str):
        self.client = ollama_client
        self.model_name = model_name

    def embed(self, text: str, memory_action: str = "search") -> list[float]:
        """Generate embedding via Ollama."""
        prefix = "search_query: " if memory_action == "search" else "search_document: "
        response = self.client.embeddings(
            model=self.model_name,
            prompt=prefix + text,
        )
        return response["embedding"]


def create_direct_store(cfg: dict[str, Any]) -> DirectStore:
    """Factory function to create a DirectStore from config."""
    return DirectStore(cfg)
