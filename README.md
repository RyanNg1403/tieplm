# Tieplm AI Assistant

NotebookLM-like AI assistant for CS431 video course content with Q&A, text summarization, video summarization, and quiz generation.

## Architecture

- **Backend**: FastAPI (modular monolith)
- **Frontend**: React TypeScript  
- **Databases**: PostgreSQL (metadata) + Qdrant (vector embeddings)
- **Ingestion**: Standalone pipeline with contextual retrieval

## Project Structure

```
tieplm/
├── .env.example              # Configuration template
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # PostgreSQL + Qdrant
│
├── backend/
│   ├── app/
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Business logic (Q&A, quiz, etc.)
│   │   └── shared/          # Shared utilities
│   │       ├── database/    # PostgreSQL + Qdrant clients
│   │       ├── embeddings/  # Embedding & chunking logic
│   │       ├── rag/         # RAG pipeline
│   │       └── config/      # Settings management
│   └── alembic/             # Database migrations
│
├── ingestion/
│   ├── pipeline/            # Download, transcribe, embed
│   ├── videos/              # Downloaded videos
│   └── transcripts/         # Generated transcripts
│
├── frontend/                # React UI
├── evaluation/              # Evaluation scripts
└── scripts/                 # Utility scripts
```

## Quick Start

### 1. Environment Setup

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env: Add OPENAI_API_KEY and configure hyperparameters

# Install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start databases
docker-compose up -d
python scripts/verify_databases.py
```

### 2. Data Setup (Choose One)

#### Option A: Restore from Exports (Recommended for Team)

Download the pre-processed data exports (shared separately) and place them in the project root:
- `tieplm_db_dump.sql` - PostgreSQL database dump
- `qdrant_snapshot.snapshot` - Qdrant vector database snapshot

Then restore:

```bash
# 1. Restore PostgreSQL database
docker exec -i tieplm-postgres psql -U tieplm -d tieplm < tieplm_db_dump.sql

# 2. Upload Qdrant snapshot
curl -X POST 'http://localhost:6333/collections/cs431_course_transcripts/snapshots/upload' \
  -F 'snapshot=@qdrant_snapshot.snapshot'
```

#### Option B: Run Full Ingestion Pipeline

```bash
cd ingestion

# Download videos from YouTube
python pipeline/download.py --all

# Transcribe with Whisper
python pipeline/transcribe_videos.py --all

# Generate embeddings with contextual chunking
python pipeline/embed_videos.py --all
```

See [`ingestion/README.md`](./ingestion/README.md) for details.

### 3. Run Application

```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install && npm start
```

Visit: http://localhost:3000

## Configuration

All hyperparameters are configured via `.env` file:

**Core Settings:**
- `OPENAI_API_KEY` - Required for embeddings and LLM
- `MODEL_NAME` - LLM for contextual chunking (default: `gpt-5-mini`)
- `EMBEDDING_MODEL_NAME` - Embedding model (default: `text-embedding-3-small`)
- `EMBEDDING_DIMENSION` - Vector dimension (default: `1536`)

**Chunking Settings:**
- `TIME_WINDOW` - Chunk duration in seconds (default: `60`)
- `CHUNK_OVERLAP` - Overlap between chunks (default: `10`)
- `CONTEXT_TOKEN_LIMIT` - Max tokens for context (default: `200`)

**Database Settings:**
- `POSTGRES_*` - PostgreSQL configuration
- `QDRANT_*` - Qdrant vector database configuration

See `.env.example` for full configuration options.

## Module Overview

### Ingestion Pipeline
Download, transcribe, and embed video content with contextual retrieval.
- **Download**: YouTube videos via `yt-dlp`
- **Transcription**: Open-source Whisper (large-v3)
- **Embedding**: Contextual chunking + OpenAI embeddings

### Backend (Modular Monolith)
- **API Layer**: FastAPI endpoints for each task
- **Core Modules**: Q&A, text summary, video summary, quiz generation
- **Shared Infrastructure**: Database clients, RAG pipeline, embeddings

### Frontend
React TypeScript UI with ChatGPT-like interface and task switching.

### Evaluation
Metrics and test scripts for all four tasks.

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Databases**: PostgreSQL, Qdrant
- **LLM**: OpenAI gpt-5-mini, gpt-5-mini
- **Embeddings**: OpenAI text-embedding-3-small
- **Transcription**: OpenAI Whisper (local)
- **Video Processing**: yt-dlp, FFmpeg

## Documentation

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - Detailed architecture design
- [`ingestion/README.md`](./ingestion/README.md) - Ingestion pipeline guide
- API Docs (when running): http://localhost:8000/docs

