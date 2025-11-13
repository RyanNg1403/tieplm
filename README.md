# Tieplm AI Assistant

NotebookLM-like AI assistant for CS431 Deep Learning video course content.

## Introduction

This project provides an intelligent assistant for CS431 video course content with four main features:
- **Text Summarization**: Generate hierarchical summaries from video transcripts with inline citations
- **Q&A**: Answer questions based on course content (planned)
- **Video Summarization**: Timestamp-based video summaries (planned)
- **Quiz Generation**: Auto-generate quizzes from course material (planned)

The system uses **Retrieval-Augmented Generation (RAG)** with hybrid search (Vector + BM25), cross-encoder reranking, and contextual retrieval to provide accurate, source-cited responses.

**Current Status**: ✅ Text Summarization fully implemented with ChatGPT-like web interface

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

## Installation & Setup

### 1. Environment Setup

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env: Add OPENAI_API_KEY and configure hyperparameters

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Start databases
docker-compose up -d

# Verify databases are running
cd backend
python ../scripts/verify_databases.py
cd ..
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

**Backend (Terminal 1):**
```bash
cd backend
source ../.venv/bin/activate

# Load .env and start backend (port from BACKEND_PORT in .env)
uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}

# Or explicitly:
# uvicorn app.main:app --reload --port 8000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm install  # First time only

# Start frontend (port from FRONTEND_PORT in .env, defaults to 3000)
npm start
# Frontend: http://localhost:3000
```

**Note:** 
- **Single `.env` file at project root** - controls both backend & frontend
- Backend must be running before starting frontend
- Make sure Docker containers (PostgreSQL + Qdrant) are running
- Ports configurable via `BACKEND_PORT` and `FRONTEND_PORT` in `.env`
- `frontend/.env` is a symlink to root `.env` for React compatibility

## Configuration

All settings are configured via single `.env` file in project root:

**Core Settings:**
- `OPENAI_API_KEY` - Required for embeddings and LLM
- `MODEL_NAME` - LLM for text generation (default: `gpt-5-mini`)
- `LLM_MAX_COMPLETION_TOKENS` - Max tokens for response (default: `3000`)
- `EMBEDDING_MODEL_NAME` - Embedding model (default: `text-embedding-3-small`)
- `EMBEDDING_DIMENSION` - Vector dimension (default: `1536`)

**RAG & Retrieval:**
- `RAG_TOP_K_VECTOR` - Initial vector search results (default: `150`)
- `RAG_TOP_K_BM25` - Initial BM25 search results (default: `150`)
- `ENABLE_RERANKING` - Use cross-encoder reranking (default: `true`)
- `RERANKER_MODEL` - Cross-encoder model (default: `cross-encoder/ms-marco-MiniLM-L-6-v2`)
- `FINAL_CONTEXT_CHUNKS` - Chunks in LLM prompt (default: `10`)

**Chunking Settings (Ingestion):**
- `TIME_WINDOW` - Chunk duration in seconds (default: `60`)
- `CHUNK_OVERLAP` - Overlap between chunks (default: `10`)
- `CONTEXT_TOKEN_LIMIT` - Max tokens for contextual prefix (default: `300`)

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
- **API Layer**: FastAPI endpoints with SSE streaming
  - Universal APIs: `/api/sessions/*` (session management for all tasks)
  - Task-specific APIs: `/api/text-summary/*`, `/api/qa/*`, `/api/video-summary/*`, `/api/quiz/*`
- **Core Modules**: Text summary (complete), Q&A, video summary, quiz (skeletons)
- **Shared Infrastructure**: RAG retriever (Vector + BM25 + RRF), local cross-encoder reranker, LLM client, database clients
- **Status**: ✅ Text summarization fully implemented and tested

### Frontend
React TypeScript UI with ChatGPT-like interface:
- **Text Summary**: ✅ Complete with streaming, citations, chapter filtering (8 chapters)
- **Session History**: ✅ ChatGPT-style sidebar (Today/Yesterday/Older grouping)
- **Chat Interface**: ✅ Real-time SSE streaming with followup questions
- **State Management**: ✅ Zustand store
- **Styling**: ✅ Chakra UI v2 + Vite (zero vulnerabilities)
- **Other Tasks**: Skeleton components (Q&A, Video Summary, Quiz)

### Evaluation
Metrics and test scripts for all four tasks (not yet implemented).

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Frontend**: React 18, TypeScript, Vite, Chakra UI v2, Zustand, TanStack React Query
- **Databases**: PostgreSQL, Qdrant
- **RAG**: Hybrid search (Vector + BM25), Cross-encoder reranking
- **LLM**: OpenAI gpt-5-mini (text generation)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Transcription**: OpenAI Whisper large-v3 (local)
- **Video Processing**: yt-dlp, FFmpeg

## Current Status

### ✅ Phase 1: Ingestion Pipeline - COMPLETE
- 62 videos downloaded and transcribed
- 1059 chunks embedded with contextual enrichment
- Qdrant + PostgreSQL databases populated

### ✅ Phase 2: Backend - COMPLETE (Text Summarization)
- RAG pipeline (Vector + BM25 + RRF)
- Local cross-encoder reranking
- SSE streaming with gpt-5-mini
- Session management APIs

### ✅ Phase 3: Frontend - COMPLETE (Text Summarization)
- ChatGPT-style interface with sidebar
- Real-time streaming responses
- Session history management
- Chapter filtering (8 chapters: Chương 2-9)
- Clickable citations with timestamps

### ⏳ Phase 4: Other Tasks - TODO
- Q&A interface
- Video Summary interface
- Quiz Generation interface
- Evaluation metrics

---

## Documentation

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - Detailed architecture design
- [`ingestion/README.md`](./ingestion/README.md) - Ingestion pipeline guide
- [`backend/README.md`](./backend/README.md) - Backend module guide
- [`frontend/README.md`](./frontend/README.md) - Frontend module guide
- API Docs (when running): http://localhost:8000/docs

