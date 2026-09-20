from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    llm_provider: str
    groq_model: str
    ollama_base_url: str
    ollama_llm_model: str
    ollama_embed_model: str
    chroma_path: Path
    collection_name: str
    google_credentials_path: Path
    google_token_path: Path
    drive_folder_id: str | None
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5


def get_settings() -> Settings:
    return Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        llm_provider=os.getenv("LLM_PROVIDER", "groq").lower(),
        groq_model=os.getenv("GROQ_MODEL", "qwen/qwen3-32b"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_llm_model=os.getenv("OLLAMA_LLM_MODEL", "qwen3.5:9b"),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b"),
        chroma_path=Path(os.getenv("CHROMA_PATH", "./chroma_data")),
        collection_name=os.getenv("COLLECTION_NAME", "drive_docs"),
        google_credentials_path=Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "./credentials.json")),
        google_token_path=Path(os.getenv("GOOGLE_TOKEN_PATH", "./token.json")),
        drive_folder_id=os.getenv("DRIVE_FOLDER_ID") or None,
    )
