# Backend Module

FastAPI backend with modular monolith architecture for CS431 AI assistant.

> **Prerequisites:** Complete setup from root [README.md](../README.md) first.

## 📁 Folder Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── sessions.py   # Universal session management (all tasks)
│   │   ├── text_summary.py  # Text summarization endpoints (SSE streaming)
│   │   ├── qa.py         # Q&A endpoints (skeleton)
│   │   ├── video_summary.py  # Video summary endpoints (skeleton)
│   │   └── quiz.py       # Quiz endpoints (skeleton)
│   ├── core/             # Business logic modules
│   │   ├── text_summary/ # ✅ Complete (RAG + streaming)
│   │   ├── qa/           # ❌ Skeleton
│   │   ├── video_summary/  # ❌ Skeleton
│   │   └── quiz/         # ❌ Skeleton
│   ├── shared/           # Shared infrastructure
│   │   ├── database/     # Database clients + models
│   │   ├── embeddings/   # Embedding & contextual chunking
│   │   ├── rag/          # RAG pipeline (retriever + reranker)
│   │   ├── llm/          # LLM client (OpenAI)
│   │   └── config/       # Settings management
│   └── main.py           # FastAPI app entry point
└── alembic/              # Database migrations (Alembic)
```

## Shared Infrastructure (Implemented)

### Database Clients

**PostgreSQL** (`shared/database/postgres.py`):
- `PostgresClient` - Connection management
- `session_scope()` - Transaction context manager
- Environment-driven configuration

**Qdrant** (`shared/database/vector_db.py`):
- `VectorDBClient` - Vector operations
- `create_collection()` - Initialize collection
- `upsert_points()` - Batch embedding storage
- `search()` - Semantic search with filters

**Models** (`shared/database/models.py`):
- `Video` - Video metadata (chapter, title, URL, duration)
- `Chunk` - Chunk metadata with Qdrant references
- `ChatSession` - Chat sessions (all tasks)
- `ChatMessage` - Chat messages with sources (citations)
- `QuizQuestion` - Generated quizzes (placeholder)

### Embeddings & Chunking

**OpenAI Embedder** (`shared/embeddings/embedder.py`):
- `OpenAIEmbedder` - text-embedding-3-small integration
- `embed()` / `embed_batch()` - Single/batch embedding

**Contextual Chunker** (`shared/embeddings/embedder.py`):
- `ContextualChunker` - Time-window chunking
- `create_time_chunks()` - 60s chunks with 10s overlap
- `generate_context()` - LLM-based context generation
- `create_contextualized_chunks()` - Full pipeline

Implements [Anthropic's Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval).

### Settings

**Embedding Settings** (`shared/config/embedding_settings.py`):
- Centralized configuration management
- Environment variable loading
- Type-safe settings with Pydantic

## Installation

> **Note:** The backend uses the project's shared Python virtual environment. Complete the setup from root [README.md](../README.md) first.

```bash
# Activate virtual environment
source ../.venv/bin/activate

# Verify environment
which python  # Should point to .venv/bin/python
```

## Usage

### Start Backend

```bash
cd backend
source ../.venv/bin/activate

# Start server (uses BACKEND_PORT from root .env, default: 8000)
uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}

# Or explicitly:
# uvicorn app.main:app --reload --port 8000
```

**API Documentation:** http://localhost:8000/docs

**Key Endpoints:**
- `GET /api/sessions` - List all chat sessions
- `POST /api/text-summary/summarize` - Text summarization (SSE stream)
- `GET /api/health` - Health check

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Database Access

```python
from backend.app.shared.database.postgres import get_postgres_client
from backend.app.shared.database.vector_db import get_vector_db_client

# PostgreSQL
postgres = get_postgres_client()
with postgres.session_scope() as session:
    videos = session.query(Video).all()

# Qdrant
qdrant = get_vector_db_client()
results = qdrant.search(query_vector, top_k=20)
```

### Embedding Usage

```python
from backend.app.shared.embeddings.embedder import OpenAIEmbedder, ContextualChunker

# Embed text
embedder = OpenAIEmbedder()
vector = embedder.embed("Your text here")

# Create contextual chunks
chunker = ContextualChunker()
chunks = chunker.create_contextualized_chunks(transcript, video_metadata)
```

## ✅ Implemented

### Shared Infrastructure
- ✅ PostgreSQL + Qdrant database clients
- ✅ SQLAlchemy models with Alembic migrations
- ✅ OpenAI embedder + contextual chunker
- ✅ RAG retriever (Vector + BM25 + RRF)
- ✅ Local cross-encoder reranker
- ✅ LLM client (OpenAI with SSE streaming)

### Text Summarization (Complete)
- ✅ RAG pipeline with hybrid search
- ✅ SSE streaming responses
- ✅ Session management
- ✅ Inline citation generation
- ✅ Chapter filtering
- ✅ Followup questions

### Universal APIs
- ✅ Session management endpoints (`/api/sessions/*`)
- ✅ Health check endpoint

## ❌ TODO

- ❌ Q&A core logic and endpoints
- ❌ Video summarization with VLM
- ❌ Quiz generation logic
- ❌ Implement remaining task endpoints
