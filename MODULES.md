# Module Overview

Quick reference for all project modules and their status.

## 📦 Modules

### 1. **Ingestion** (`ingestion/`)
**Purpose**: Process videos → transcripts → embeddings → database

**Status**: 🟢 Complete
- ✅ Download videos from YouTube (`download.py` with yt-dlp, audio-only)
- ✅ Transcribe with Whisper large-v3 local model (`transcribe_videos.py`)
- ✅ Generate embeddings with contextual chunking (`embed_videos.py`)
  - Time-window chunking (60s + 10s overlap)
  - LLM-driven contextual enrichment (gpt-5-mini with minimal reasoning)
  - OpenAI text-embedding-3-small
  - UUID-based Qdrant point IDs
  - Retry logic for LLM token limits (300→400→500)
- ✅ Store in databases (Qdrant + PostgreSQL with Alembic)
- ✅ Video mapping utilities with Unicode normalization
- ❌ Extract keyframes (skeleton only)

**Current Data**: 62 videos, 1059 chunks embedded

---

### 2. **Backend** (`backend/`)
**Purpose**: FastAPI backend with 4 AI tasks

**Status**: 🟡 In Progress (Text Summarization ✅ Complete)
- ✅ Project structure
- ✅ API endpoints:
  - Universal session management (`sessions.py`) - ✅ Complete
  - Text summarization (`text_summary.py`) - ✅ Complete
  - Q&A, Video Summary, Quiz - ❌ Skeletons
- ✅ Pydantic models
- ✅ Database clients (PostgreSQL + Qdrant with chapter filtering)
- ✅ Database models (Video, Chunk, ChatSession, ChatMessage, QuizQuestion)
- ✅ Embedding system (OpenAIEmbedder, ContextualChunker with contextual retrieval)
- ✅ Shared RAG library (RAGRetriever with Vector + BM25 + RRF)
- ✅ Local cross-encoder reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- ✅ LLM client (OpenAI with SSE streaming, `gpt-5-mini` support)
- ✅ Text summarization module (full implementation with session management)
- ❌ Q&A, Video Summary, Quiz modules (skeletons only)


---

### 3. **Frontend** (`frontend/`)
**Purpose**: React web UI with ChatGPT-like interface

**Status**: 🟡 In Progress (Text Summarization ✅ Complete)
- ✅ Project structure (Vite + React 18 + TypeScript)
- ✅ API service layer with universal session APIs
- ✅ State management (Zustand)
- ✅ SSE streaming hook (`useSSE`)
- ✅ Chat components (ChatContainer, MessageList, Message, ChatInput, Sidebar)
- ✅ Session history sidebar (Today/Yesterday/Older grouping)
- ✅ Task switcher in chat input
- ✅ Chapter filtering (8 chapters: Chương 2-9)
- ✅ Clickable citations with timestamp navigation
- ✅ Real-time streaming responses
- ❌ Q&A, Video Summary, Quiz interfaces (skeletons only)
- ❌ Video player component

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

### ✅ Completed (Phase 1: Text Summarization)
1. ✅ **Ingestion**: Download, transcription, embeddings (62 videos, 1059 chunks)
2. ✅ **Backend**: Database clients (PostgreSQL + Qdrant with chapter filtering)
3. ✅ **Backend**: Database models and Alembic migrations
4. ✅ **Backend**: Embedding system with contextual retrieval
5. ✅ **Backend**: Shared RAG library (Vector + BM25 + RRF)
6. ✅ **Backend**: Local cross-encoder reranker
7. ✅ **Backend**: LLM client (OpenAI with SSE streaming)
8. ✅ **Backend**: Text summarization module (full implementation)
9. ✅ **Backend**: Universal session management API
10. ✅ **Frontend**: Text summarization interface (ChatGPT-like with streaming)

### 🔄 Next (Phase 2: Remaining Tasks)
1. 🔄 **Backend**: Q&A module implementation
2. 🔄 **Backend**: Video summarization module (with VLM)
3. 🔄 **Backend**: Quiz generation module
4. 🔄 **Frontend**: Q&A interface
5. 🔄 **Frontend**: Video summary interface
6. 🔄 **Frontend**: Quiz interface
7. 🔄 **Evaluation**: Build evaluation datasets and metrics

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

