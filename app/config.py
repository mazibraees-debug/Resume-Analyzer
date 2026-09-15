"""
Centralized application configuration.

All values can be overridden via environment variables or a `.env` file
placed next to this project (see `.env.example`).
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        extra="ignore",
    )

    # --- General ---
    app_name: str = "AI Job Application Agent"
    environment: str = "development"

    # --- Database ---
    # Defaults to a local SQLite file so the project runs with zero setup.
    # In docker-compose this is overridden to point at the Postgres service.
    database_url: str = "sqlite:///./data/app.db"

    # --- Vector store (Chroma) ---
    chroma_db_path: str = "./data/chroma_db"
    chroma_collection_name: str = "cv_chunks"

    # --- Embeddings ---
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # --- LLM provider ---
    # "anthropic" or "openai". The graph/nodes talk to a single thin
    # wrapper (app.llm.client.LLMClient) so swapping providers requires
    # no changes anywhere else in the codebase.
    llm_provider: str = "openai"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    openrouter_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "openai/gpt-4o-mini"

    # --- Uploads ---
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 10

    # --- Matching ---
    # Cosine-similarity threshold above which a JD requirement is
    # considered "matched" by something in the candidate's CV.
    match_threshold: float = 0.20
    top_k_matches: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
