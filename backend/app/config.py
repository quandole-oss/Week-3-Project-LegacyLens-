from pydantic_settings import BaseSettings
from functools import lru_cache


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

    use_reranker: bool = True
    reranker_initial_top_k: int = 20
    reranker_final_top_k: int = 5
    use_query_expansion: bool = True
    use_intent_detection: bool = True
    retrieval_top_k: int = 10
    chunk_batch_size: int = 100

    lapack_data_dir: str = "data/lapack"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
