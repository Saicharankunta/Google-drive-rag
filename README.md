# Google Drive RAG

A Retrieval-Augmented Generation (RAG) chatbot that connects to Google Drive, indexes documents, retrieves relevant information using vector search, and generates answers grounded in the retrieved content.

## Architecture

```text
Google Drive
     ↓
Document Extraction
     ↓
Chunking
     ↓
Embeddings (Ollama)
     ↓
ChromaDB
     ↓
User Question
     ↓
Similarity Search
     ↓
Relevant Document Chunks
     ↓
Qwen LLM
     ↓
Answer with Sources
```

## Core Components

* **Google Drive API** — retrieves documents from Google Drive
* **Ollama** — generates local document embeddings
* **ChromaDB** — stores embeddings and performs vector similarity search
* **Qwen LLM** — generates answers from retrieved context
* **Groq** — optional cloud inference provider
* **FastAPI** — provides the web application backend

## Supported Documents

The system supports:

* Google Docs
* PDF files
* `.txt`
* `.md`
* `.csv`

## How It Works

### 1. Authenticate

The application authenticates with Google Drive using OAuth 2.0.

### 2. Index Documents

Documents are retrieved from Google Drive and converted into text.

The text is divided into smaller chunks and converted into embeddings using Ollama.

These embeddings are stored persistently in ChromaDB.

### 3. Ask a Question

When a user asks a question:

```text
User Question
      ↓
Question Embedding
      ↓
ChromaDB Similarity Search
      ↓
Top-k Relevant Chunks
      ↓
LLM
      ↓
Context-aware Answer
```

The LLM receives the retrieved document content as context and generates the final response.

## LLM Options

The project supports two inference approaches.

### Groq

Cloud-based inference can be used with a Groq API key.

Example configuration:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_api_key
GROQ_MODEL=qwen/qwen3-32b
```

### Ollama

The LLM can also run locally using Ollama.

```env
LLM_PROVIDER=ollama
OLLAMA_LLM_MODEL=qwen3.5:9b
```

Using Ollama locally allows the complete RAG pipeline to run without sending document content to an external LLM provider.

## Prerequisites

* Python 3.11+
* Ollama
* Google Cloud project
* Google Drive API enabled
* Google OAuth 2.0 Desktop credentials

For local embeddings:

```bash
ollama pull qwen3-embedding:0.6b
```

For local LLM inference:

```bash
ollama pull qwen3.5:9b
```

## Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the environment file:

```bash
cp .env.example .env
```

Configure the required environment variables.

Place your Google OAuth credentials in:

```text
credentials.json
```

**Do not commit `credentials.json`, `token.json`, or `.env` to GitHub.**

## CLI Usage

Authenticate with Google Drive:

```bash
python main.py auth
```

Index documents:

```bash
python main.py index
```

Ask questions:

```bash
python main.py ask "What are the key points in my project notes?"
```

Check system status:

```bash
python main.py status
```

## Web Application

The project also includes a lightweight web interface.

Start the application:

```bash
python run_web.py
```

Then open:

```text
http://127.0.0.1:7860
```

The interface provides:

* Document indexing
* Question answering
* Retrieved-source information
* System status

## Project Structure

```text
google-drive-rag/
├── main.py
├── run_web.py
├── static/
├── src/
│   ├── config.py
│   ├── drive_client.py
│   ├── embeddings.py
│   ├── indexer.py
│   ├── llm.py
│   ├── rag.py
│   ├── server.py
│   └── cli.py
├── chroma_data/
├── credentials.json
└── token.json
```

Generated and sensitive files such as `chroma_data/`, `credentials.json`, `token.json`, and `.env` should remain excluded from version control.

## Re-indexing

Running:

```bash
python main.py index
```

updates the document index.

When documents change, the system can re-index their content so that future queries use the latest available information.

## Key Concepts Demonstrated

This project demonstrates the main components of a practical RAG system:

* Document ingestion
* Text extraction
* Chunking
* Embedding generation
* Vector databases
* Similarity search
* Context retrieval
* LLM-based generation
* Source-grounded question answering
* Google Drive API integration

## Future Improvements

Possible extensions include:

* Better document chunking strategies
* Metadata-based filtering
* Improved retrieval and reranking
* Conversation memory
* Authentication and user-specific Drive access
* Hybrid keyword + vector search
* Evaluation of retrieval accuracy
* Streaming LLM responses
