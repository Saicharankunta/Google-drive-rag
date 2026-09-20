from __future__ import annotations

import hashlib

import chromadb

from src.config import Settings
from src.drive_client import DriveClient, DriveDocument
from src.embeddings import OllamaEmbeddings


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


class DriveIndexer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings = OllamaEmbeddings(settings)
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def chunk_count(self) -> int:
        return self._collection.count()

    def index_drive(self) -> dict[str, int]:
        drive = DriveClient(self._settings)
        documents = drive.fetch_all_documents()

        indexed_files = 0
        indexed_chunks = 0

        for doc in documents:
            chunks = chunk_text(
                doc.text,
                self._settings.chunk_size,
                self._settings.chunk_overlap,
            )
            if not chunks:
                continue

            self._delete_file_chunks(doc.file_id)
            embeddings = self._embeddings.embed_documents(chunks)
            ids = [self._chunk_id(doc.file_id, index) for index in range(len(chunks))]
            metadatas = [
                {
                    "file_id": doc.file_id,
                    "file_name": doc.name,
                    "mime_type": doc.mime_type,
                    "chunk_index": index,
                }
                for index in range(len(chunks))
            ]

            self._collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas,
            )
            indexed_files += 1
            indexed_chunks += len(chunks)

        return {
            "files_found": len(documents),
            "files_indexed": indexed_files,
            "chunks_indexed": indexed_chunks,
        }

    def _delete_file_chunks(self, file_id: str) -> None:
        existing = self._collection.get(where={"file_id": file_id})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

    @staticmethod
    def _chunk_id(file_id: str, chunk_index: int) -> str:
        digest = hashlib.sha1(f"{file_id}:{chunk_index}".encode()).hexdigest()
        return digest
