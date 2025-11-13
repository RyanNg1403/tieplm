# Module Overview

Quick reference for all project modules and their status.

## 📦 Modules

### 1. **Ingestion** (`ingestion/`)
**Purpose**: Process videos → transcripts → embeddings → database

**Status**: 🟢 Complete
- ✅ Download videos from YouTube (`download.py` with yt-dlp)
- ✅ Transcribe with Whisper large-v3 local model (`transcribe_videos.py`)
- ✅ Generate embeddings with contextual chunking (`embed_videos.py`)
  - Time-window chunking (60s + 10s overlap)
  - LLM-driven contextual enrichment (gpt-5-mini)
  - OpenAI text-embedding-3-small
- ❌ Extract keyframes (skeleton only)
- ✅ Store in databases (Qdrant + PostgreSQL with Alembic)

**Owner**: Person 4

---

### 2. **Backend** (`backend/`)
**Purpose**: FastAPI backend with 4 AI tasks

**Status**: 🟡 In Progress
- ✅ Project structure
- ✅ API endpoint skeletons
- ✅ Pydantic models
- ✅ Database clients (PostgreSQL + Qdrant, fully implemented)
- ✅ Database models (Video, Chunk, ChatHistory, QuizQuestion)
- ✅ Embedding system (OpenAIEmbedder, ContextualChunker)
- ❌ Shared RAG library (skeleton only)
- ❌ LLM clients (skeleton only)
- ❌ All 4 task implementations (skeletons only)

**Owners**: Person 2 (Q&A, Text Summary), Person 3 (Video Summary, Quiz), Person 4 (Shared)

---

### 3. **Frontend** (`frontend/`)
**Purpose**: React web UI with ChatGPT-like interface

**Status**: 🔴 Not Started
- ✅ Project structure
- ✅ API service layer
- ❌ Chat component
- ❌ Task switcher
- ❌ Video player
- ❌ All UI implementations

**Owner**: Person 1

---

### 4. **Evaluation** (`evaluation/`)
**Purpose**: Evaluate performance of 4 tasks

**Status**: 🔴 Not Started
- ✅ Project structure
- ❌ Evaluation datasets
- ❌ Metrics implementation
- ❌ Evaluation scripts

**Note**: Build after main features complete

---

## 🎯 Current Priority

1. ✅ **Ingestion**: Download, transcription, embeddings (COMPLETE)
2. ✅ **Backend**: Database clients (PostgreSQL + Qdrant) (COMPLETE)
3. ✅ **Backend**: Database models and Alembic migrations (COMPLETE)
4. 🔄 **Backend**: Shared RAG library (NEXT - skeleton exists)
5. 🔄 **Backend**: LLM clients (NEXT - skeleton exists)
6. 🔄 **Backend**: Task implementations (4 tasks)

---

## 📚 Module READMEs

Each module has detailed README:
- [`ingestion/README.md`](ingestion/README.md)
- [`backend/README.md`](backend/README.md)
- [`frontend/README.md`](frontend/README.md)
- [`evaluation/README.md`](evaluation/README.md)

---

## 🚀 Quick Start

See main [`README.md`](README.md) for complete setup instructions.

