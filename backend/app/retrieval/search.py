"""Pinecone similarity search for code retrieval."""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    text: str
    file_path: str
    routine_name: str
    routine_type: str
    start_line: int
    end_line: int
    language: str
    score: float

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "file_path": self.file_path,
            "routine_name": self.routine_name,
            "routine_type": self.routine_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
            "score": round(self.score, 4),
        }


class EmbeddingCache:
    """Simple LRU cache for query embeddings to avoid redundant API calls."""

    def __init__(self, max_size: int = 256):
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> list[float] | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            self.hits += 1
            return self._cache[key]
        self.misses += 1
        return None

    def put(self, key: str, value: list[float]) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
        self._cache[key] = value


class CodeSearcher:
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = OpenAIEmbeddings(
            model=self.settings.embedding_model,
            openai_api_key=self.settings.openai_api_key,
            dimensions=self.settings.embedding_dimensions,
        )
        pc = Pinecone(api_key=self.settings.pinecone_api_key)
        self.index = pc.Index(self.settings.pinecone_index)
        self._embedding_cache = EmbeddingCache()

    def _embed_query(self, query: str) -> list[float]:
        """Embed a query with LRU caching."""
        cached = self._embedding_cache.get(query)
        if cached is not None:
            logger.debug(f"Embedding cache hit for query: '{query[:50]}...'")
            return cached
        vector = self.embeddings.embed_query(query)
        self._embedding_cache.put(query, vector)
        return vector

    def search(self, query: str, top_k: int = None) -> list[SearchResult]:
        """Search for code chunks relevant to the query."""
        top_k = top_k or self.settings.retrieval_top_k

        # Embed the query (with caching)
        query_vector = self._embed_query(query)

        # Query Pinecone
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )

        search_results = []
        for match in results.matches:
            meta = match.metadata
            search_results.append(SearchResult(
                text=meta.get("text", ""),
                file_path=meta.get("file_path", ""),
                routine_name=meta.get("routine_name", ""),
                routine_type=meta.get("routine_type", ""),
                start_line=int(meta.get("start_line", 0)),
                end_line=int(meta.get("end_line", 0)),
                language=meta.get("language", ""),
                score=match.score,
            ))

        return search_results
