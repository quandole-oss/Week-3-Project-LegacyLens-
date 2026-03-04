from enum import Enum
from dataclasses import dataclass

from pydantic_settings import BaseSettings
from functools import lru_cache


class Verbosity(str, Enum):
    SUCCINCT = "succinct"
    CONCISE = "concise"
    REGULAR = "regular"
    DETAILED = "detailed"


@dataclass(frozen=True)
class VerbosityProfile:
    max_tokens: int
    generation_model: str
    use_query_expansion: bool
    use_reranker: bool
    reranker_initial_top_k: int
    reranker_final_top_k: int
    max_chunks: int
    trim_after_rank: int
    trim_char_limit: int
    prompt_suffix: str


VERBOSITY_PROFILES: dict[Verbosity, VerbosityProfile] = {
    Verbosity.SUCCINCT: VerbosityProfile(
        max_tokens=512,
        generation_model="claude-haiku-4-5-20251001",
        use_query_expansion=False,
        use_reranker=False,
        reranker_initial_top_k=10,
        reranker_final_top_k=3,
        max_chunks=3,
        trim_after_rank=2,
        trim_char_limit=800,
        prompt_suffix="Answer in 2-3 sentences max.",
    ),
    Verbosity.CONCISE: VerbosityProfile(
        max_tokens=1024,
        generation_model="claude-sonnet-4-6",
        use_query_expansion=False,
        use_reranker=True,
        reranker_initial_top_k=10,
        reranker_final_top_k=3,
        max_chunks=5,
        trim_after_rank=3,
        trim_char_limit=800,
        prompt_suffix="Be concise: short paragraphs, 2-3 key points.",
    ),
    Verbosity.REGULAR: VerbosityProfile(
        max_tokens=2048,
        generation_model="claude-sonnet-4-6",
        use_query_expansion=True,
        use_reranker=True,
        reranker_initial_top_k=10,
        reranker_final_top_k=5,
        max_chunks=7,
        trim_after_rank=3,
        trim_char_limit=800,
        prompt_suffix="",
    ),
    Verbosity.DETAILED: VerbosityProfile(
        max_tokens=4096,
        generation_model="claude-sonnet-4-6",
        use_query_expansion=True,
        use_reranker=True,
        reranker_initial_top_k=20,
        reranker_final_top_k=5,
        max_chunks=10,
        trim_after_rank=5,
        trim_char_limit=800,
        prompt_suffix="Provide thorough detail with all sections.",
    ),
}


class Settings(BaseSettings):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = "legacylens"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    generation_model: str = "claude-sonnet-4-6"
    rerank_model: str = "claude-haiku-4-5-20251001"

    use_reranker: bool = False
    reranker_initial_top_k: int = 10
    reranker_final_top_k: int = 5
    use_query_expansion: bool = True
    use_intent_detection: bool = True
    retrieval_top_k: int = 10
    chunk_batch_size: int = 100

    lapack_data_dir: str = "data/lapack"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "https://legacylens-murex.vercel.app"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
