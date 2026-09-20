from __future__ import annotations

import click

from src.config import get_settings
from src.indexer import DriveIndexer
from src.rag import DriveRAG


@click.group()
def cli() -> None:
    """Simple Google Drive RAG with ChromaDB, Ollama embeddings, and Groq/Ollama LLM."""


@cli.command()
def auth() -> None:
    """Authenticate with Google Drive (opens browser once)."""
    from src.drive_client import DriveClient

    settings = get_settings()
    DriveClient(settings)
    click.echo(f"Authenticated. Token saved to {settings.google_token_path}")


@cli.command()
def index() -> None:
    """Fetch Drive documents and index them into ChromaDB."""
    settings = get_settings()
    indexer = DriveIndexer(settings)
    stats = indexer.index_drive()
    click.echo(
        f"Indexed {stats['files_indexed']}/{stats['files_found']} files "
        f"({stats['chunks_indexed']} chunks). Total chunks: {indexer.chunk_count}"
    )


@cli.command()
@click.argument("question")
@click.option("--top-k", default=None, type=int, help="Number of chunks to retrieve")
def ask(question: str, top_k: int | None) -> None:
    """Ask a question over indexed Drive documents."""
    settings = get_settings()
    rag = DriveRAG(settings)
    result = rag.query(question, top_k=top_k)

    click.echo(f"\nProvider: {result['provider']}")
    click.echo(f"\nAnswer:\n{result['answer']}\n")
    click.echo("Sources:")
    for source in result["sources"]:
        click.echo(
            f"  - {source['file_name']} (chunk {source['chunk_index']}, distance={source['distance']:.4f})"
        )


@cli.command()
def status() -> None:
    """Show current index and provider configuration."""
    settings = get_settings()
    indexer = DriveIndexer(settings)
    click.echo(f"LLM provider: {settings.llm_provider}")
    if settings.llm_provider == "groq":
        click.echo(f"Groq model: {settings.groq_model}")
    else:
        click.echo(f"Ollama LLM model: {settings.ollama_llm_model}")
    click.echo(f"Ollama embed model: {settings.ollama_embed_model}")
    click.echo(f"Chroma path: {settings.chroma_path}")
    click.echo(f"Indexed chunks: {indexer.chunk_count}")
    if settings.drive_folder_id:
        click.echo(f"Drive folder filter: {settings.drive_folder_id}")
