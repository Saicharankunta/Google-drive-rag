from __future__ import annotations

import chromadb

from src.config import Settings
from src.embeddings import OllamaEmbeddings
from src.llm import LLMClient


class DriveRAG:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings = OllamaEmbeddings(settings)
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._llm = LLMClient(settings)

    @property
    def chunk_count(self) -> int:
        return self._collection.count()

    def query(self, question: str, top_k: int | None = None) -> dict:
        if self.chunk_count == 0:
            raise ValueError("No indexed chunks found. Run `python main.py index` first.")

        k = top_k or self._settings.top_k
        query_embedding = self._embeddings.embed_query(question)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        context_blocks: list[str] = []
        sources: list[dict] = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            file_name = meta.get("file_name", "unknown")
            context_blocks.append(f"[{file_name}]\n{doc}")
            sources.append(
                {
                    "file_name": file_name,
                    "file_id": meta.get("file_id"),
                    "chunk_index": meta.get("chunk_index"),
                    "distance": distance,
                }
            )

        context = "\n\n".join(context_blocks)
        answer = self._llm.generate(question, context)

        return {
            "question": question,
            "answer": answer,
            "provider": self._settings.llm_provider,
            "sources": sources,
        }
