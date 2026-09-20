from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.config import get_settings
from src.indexer import DriveIndexer
from src.rag import DriveRAG

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

_index_lock = threading.Lock()
_index_state: dict[str, Any] = {
    "status": "idle",
    "stats": None,
    "error": None,
}


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)


def _run_index() -> None:
    global _index_state
    try:
        settings = get_settings()
        indexer = DriveIndexer(settings)
        stats = indexer.index_drive()
        with _index_lock:
            _index_state = {
                "status": "done",
                "stats": {
                    **stats,
                    "total_chunks": indexer.chunk_count,
                },
                "error": None,
            }
    except Exception as exc:
        with _index_lock:
            _index_state = {
                "status": "error",
                "stats": None,
                "error": str(exc),
            }


def create_app() -> FastAPI:
    app = FastAPI(title="Drive RAG", version="1.0.0")

    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        settings = get_settings()
        indexer = DriveIndexer(settings)
        llm_model = (
            settings.groq_model
            if settings.llm_provider == "groq"
            else settings.ollama_llm_model
        )
        return {
            "llm_provider": settings.llm_provider,
            "llm_model": llm_model,
            "embed_model": settings.ollama_embed_model,
            "chunk_count": indexer.chunk_count,
            "authenticated": settings.google_token_path.exists(),
            "drive_folder_id": settings.drive_folder_id,
            "top_k": settings.top_k,
        }

    @app.get("/api/index/status")
    def get_index_status() -> dict[str, Any]:
        with _index_lock:
            return dict(_index_state)

    @app.post("/api/index")
    def start_index() -> dict[str, str]:
        with _index_lock:
            if _index_state["status"] == "running":
                raise HTTPException(status_code=409, detail="Indexing already in progress")
            _index_state.update({"status": "running", "stats": None, "error": None})

        thread = threading.Thread(target=_run_index, daemon=True)
        thread.start()
        return {"status": "running"}

    @app.post("/api/query")
    def query_documents(payload: QueryRequest) -> dict[str, Any]:
        settings = get_settings()
        rag = DriveRAG(settings)
        try:
            return rag.query(payload.question.strip(), top_k=payload.top_k)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/")
    def index_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
