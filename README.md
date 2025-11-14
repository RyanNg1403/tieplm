# Tieplm AI Assistant

NotebookLM-like AI assistant for CS431 Deep Learning video course content.

## Introduction

This project provides an intelligent assistant for CS431 video course content with four main features:
- **Text Summarization**: Generate hierarchical summaries from video transcripts with inline citations
- **Q&A**: Answer questions based on course content
- **Video Summarization**: Timestamp-based video summaries
- **Quiz Generation**: Auto-generate quizzes from course material

The system uses **Retrieval-Augmented Generation (RAG)** with hybrid search (Vector + BM25), cross-encoder reranking, and contextual retrieval to provide accurate, source-cited responses.

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
```

### 2. Data Setup (Choose One)

#### Option A: Restore from Exports (Recommended for Team)

Download the pre-processed data exports (shared separately) and place them in the project root:
- `tieplm_db_dump.sql` - PostgreSQL database dump (62 videos, 1059 chunks)
- `qdrant_snapshot.snapshot` - Qdrant vector database snapshot

Then restore:

```bash
# 1. Restore PostgreSQL database (creates old schema)
docker exec -i tieplm-postgres psql -U tieplm -d tieplm < tieplm_db_dump.sql

# 2. Run migrations (updates to latest schema)
cd backend
source ../.venv/bin/activate
alembic upgrade head
cd ..

# 3. Upload Qdrant snapshot
curl -X POST 'http://localhost:6333/collections/cs431_course_transcripts/snapshots/upload' \
  -F 'snapshot=@qdrant_snapshot.snapshot'

# 4. Verify setup
python scripts/verify_databases.py
```

**Note:** Migration updates chat history schema. Videos/chunks data preserved, chat history starts fresh.

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

# Load .env and start backend (port from BACKEND_PORT in .env)
uvicorn app.main:app --reload --port ${BACKEND_PORT:-8000}

# Or explicitly:
# uvicorn app.main:app --reload --port 8000
# $env:BACKEND_PORT = 8000
# uvicorn app.main:app --reload --port $env:BACKEND_PORT
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

All settings are configured via single `.env` file in project root. Copy `.env.example` to `.env` and configure:
- `OPENAI_API_KEY` (required)
- Database credentials (PostgreSQL, Qdrant)
- Model settings, RAG parameters, chunking settings

**See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for complete list of environment variables and configuration options.**

## Modules

### Ingestion Pipeline
Processes video content into searchable embeddings with contextual retrieval.
- **Download**: YouTube videos via `yt-dlp` (audio-only with fallback)
- **Transcription**: Local Whisper large-v3 model with word-level timestamps
- **Embedding**: Time-window chunking (60s + 10s overlap) with LLM-driven contextual enrichment
- **Storage**: Dual storage in PostgreSQL (metadata) and Qdrant (vectors)

### Backend (Modular Monolith)
FastAPI-based backend with modular architecture for four AI tasks.
- **API Layer**: RESTful endpoints with Server-Sent Events (SSE) for streaming
  - Universal session management: `/api/sessions/*`
  - Task-specific endpoints: `/api/text-summary/*`, `/api/qa/*`, `/api/video-summary/*`, `/api/quiz/*`
- **Core Modules**: Business logic for text summarization, Q&A, video summarization, and quiz generation
- **Shared Infrastructure**: 
  - RAG retriever with hybrid search (Vector + BM25 + Reciprocal Rank Fusion)
  - Local cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
  - LLM client with SSE streaming (`gpt-5-mini`)
  - Database clients for PostgreSQL and Qdrant
  - Embedding system with contextual chunking

### Frontend
React TypeScript web application with ChatGPT-like interface.
- **UI Framework**: React 18 + TypeScript with Vite bundler
- **Styling**: Chakra UI v2 for component library
- **State Management**: Zustand for application state
- **API Client**: TanStack React Query with SSE support
- **Key Features**:
  - Real-time streaming responses with inline citations
  - Session history with chronological grouping
  - Task switcher for different AI capabilities
  - Chapter filtering for targeted queries
  - Clickable citations linking to video timestamps

### Evaluation
Framework for measuring performance across all four AI tasks.
- **Datasets**: Ground truth data for each task
- **Metrics**: Task-specific evaluation metrics (ROUGE, accuracy, relevance)
- **Scripts**: Automated evaluation runners

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Frontend**: React 18, TypeScript, Vite, Chakra UI v2, Zustand, TanStack React Query
- **Databases**: PostgreSQL, Qdrant
- **RAG**: Hybrid search (Vector + BM25), Cross-encoder reranking
- **LLM**: OpenAI gpt-5-mini (text generation)
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Transcription**: OpenAI Whisper large-v3 (local)
- **Video Processing**: yt-dlp, FFmpeg


## Documentation

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - Detailed architecture design
- [`ingestion/README.md`](./ingestion/README.md) - Ingestion pipeline guide
- [`backend/README.md`](./backend/README.md) - Backend module guide
- [`frontend/README.md`](./frontend/README.md) - Frontend module guide
- API Docs (when running): http://localhost:8000/docs