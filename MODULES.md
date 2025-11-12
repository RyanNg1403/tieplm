# Module Overview

Quick reference for all project modules and their status.

## 📦 Modules

### 1. **Ingestion** (`ingestion/`)
**Purpose**: Process videos → transcripts → embeddings → database

**Status**: 🟡 In Progress
- ✅ Download videos from YouTube
- ✅ Transcribe with Whisper (all models)
- ❌ Generate embeddings
- ❌ Extract keyframes
- ❌ Store in databases

**Owner**: Person 4

---

### 2. **Backend** (`backend/`)
**Purpose**: FastAPI backend with 4 AI tasks

**Status**: 🔴 Not Started
- ✅ Project structure
- ✅ API endpoint skeletons
- ✅ Pydantic models
- ❌ Shared RAG library
- ❌ LLM clients
- ❌ Database clients
- ❌ All 4 task implementations

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

1. ✅ **Ingestion**: Finish transcription (in progress)
2. 🔄 **Ingestion**: Implement embeddings module (next)
3. 🔄 **Backend**: Shared RAG library
4. 🔄 **Backend**: Database clients
5. 🔄 **Backend**: Task implementations

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

