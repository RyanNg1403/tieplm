# Backend Module

FastAPI backend with modular monolith architecture for CS431 AI assistant.

> **Prerequisites:** Complete setup from root [README.md](../README.md) first.

## Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   ├── core/             # Business logic modules
│   │   ├── qa/
│   │   ├── text_summary/
│   │   ├── video_summary/
│   │   └── quiz/
│   ├── shared/           # Shared infrastructure
│   │   ├── database/     # Database clients
│   │   ├── embeddings/   # Embedding & chunking
│   │   ├── rag/          # RAG pipeline
│   │   ├── llm/          # LLM clients
│   │   └── config/       # Settings management
│   └── main.py           # FastAPI app
└── alembic/              # Database migrations
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
- `Video` - Video metadata
- `Chunk` - Chunk metadata with Qdrant references
- `ChatHistory` - User conversations
- `QuizQuestion` - Generated quizzes

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

## Usage

### Start Backend

```bash
cd backend
uvicorn app.main:app --reload
```

API Documentation: http://localhost:8000/docs

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

## Development Tasks

- [ ] Implement RAG retrieval module
- [ ] Build Q&A core logic
- [ ] Build text summarization
- [ ] Build video summarization with VLM
- [ ] Build quiz generation
- [ ] Create API endpoints for all tasks
