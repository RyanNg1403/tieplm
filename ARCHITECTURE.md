# Notebook-LM AI Assistant - Architecture Document

## Project Overview

A video course AI assistant that helps students interact with course content through 4 main capabilities:
1. **Q&A**: Ask questions and get answers with exact video timestamps
2. **Text Summarization**: Get concise summaries on specific topics
3. **Video Summarization**: Summarize content of specific course videos
4. **Quiz Generation**: Generate Yes/No and MCQ quizzes from video content

**Source Material**: YouTube course videos  
**Architecture**: Modular Monolith (Python backend, React frontend)  
**Team Size**: 4 developers working in parallel

---

## Tech Stack

### Core Technologies
- **Backend**: Python with FastAPI
- **Frontend**: React with TypeScript
- **Databases**: 
  - PostgreSQL (video metadata, chunks, timestamps, chat history, quizzes)
  - Qdrant (vector embeddings for transcript chunks)
- **Transcription**: Whisper large-v3 (local, open-source model)
- **Embeddings**: OpenAI text-embedding-3-small with contextual chunking (Anthropic's approach)
- **Contextual LLM**: OpenAI gpt-5-mini for chunk context generation
- **Video Processing**: FFmpeg or OpenCV for keyframe extraction (not yet implemented)
- **Orchestration**: Custom implementation

### Infrastructure
- Docker Compose for local development (Postgres + Qdrant)
- Qdrant data persisted locally in `qdrant_data/` (not in git)
- PostgreSQL data persisted locally in `postgres_data/` (not in git)
- Alembic for database migrations
- Environment variables in `.env` (single root-level file)

---

## Architecture: Modular Monolith

### Why Modular Monolith?
✅ Clear module boundaries for parallel development  
✅ Shared RAG library easily accessible  
✅ Simpler development and debugging  
✅ Single deployment, less operational overhead  
✅ Can evolve to microservices later if needed

### System Components
```
┌─────────────┐     ┌──────────────────────────────────┐     ┌─────────────┐
│   Frontend  │────▶│       Backend (FastAPI)          │────▶│  Databases  │
│  React/TS   │     │  ┌────────────────────────────┐  │     │             │
│             │     │  │ API Layer (4 endpoints)    │  │     │ PostgreSQL  │
│ - Chat UI   │     │  ├────────────────────────────┤  │     │ Vector DB   │
│ - Task      │     │  │ Core Modules (4 tasks)     │  │     │             │
│   Switcher  │     │  ├────────────────────────────┤  │     └─────────────┘
│ - Video     │     │  │ Shared Components:         │  │
│   Player    │     │  │ - RAG Library             │  │
└─────────────┘     │  │ - LLM Clients             │  │
                    │  │ - DB Layer                │  │
                    │  │ - Config Manager          │  │
                    │  └────────────────────────────┘  │
                    └──────────────────────────────────┘
                                    ▲
                                    │
                    ┌───────────────┴────────────────┐
                    │  Ingestion Pipeline (Separate) │
                    │  - Download YouTube videos     │
                    │  - Transcribe audio           │
                    │  - Extract keyframes          │
                    │  - Generate embeddings        │
                    │  - Store in databases         │
                    └────────────────────────────────┘
```

---

## Detailed Folder Structure

```
tieplm/
├── frontend/                    # React/TypeScript Web UI
│   ├── src/
│   │   ├── components/         # UI components
│   │   │   ├── Chat/          # Chat interface (ChatGPT-like)
│   │   │   ├── TaskSwitcher/  # Toggle between 4 tasks
│   │   │   ├── VideoPlayer/   # Video with timestamp navigation
│   │   │   └── shared/        # Reusable components
│   │   ├── pages/             # Main pages
│   │   ├── services/          # API client services
│   │   ├── hooks/             # React hooks
│   │   ├── types/             # TypeScript types
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                     # Python Modular Monolith
│   ├── app/
│   │   ├── api/                # API Routes (one file per task)
│   │   │   ├── __init__.py
│   │   │   ├── qa.py          # Q&A endpoints
│   │   │   ├── text_summary.py # Text summarization endpoints
│   │   │   ├── video_summary.py # Video summarization endpoints
│   │   │   ├── quiz.py        # Quiz generation endpoints
│   │   │   └── health.py      # Health check
│   │   │
│   │   ├── core/               # Business Logic (module per task)
│   │   │   ├── qa/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py     # Q&A orchestration
│   │   │   │   └── prompts.py    # Task-specific prompts
│   │   │   ├── text_summary/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py
│   │   │   │   └── prompts.py
│   │   │   ├── video_summary/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── service.py
│   │   │   │   └── prompts.py
│   │   │   └── quiz/
│   │   │       ├── __init__.py
│   │   │       ├── service.py
│   │   │       └── prompts.py
│   │   │
│   │   ├── shared/             # Shared Components ⭐
│   │   │   ├── rag/           # Shared RAG Library
│   │   │   │   ├── __init__.py
│   │   │   │   ├── retriever.py   # Vector search logic
│   │   │   │   ├── reranker.py    # Optional reranking
│   │   │   │   └── pipeline.py    # RAG orchestration
│   │   │   ├── llm/           # LLM Clients
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py      # LLM API wrapper
│   │   │   │   └── vlm.py         # Vision LLM for video frames
│   │   │   ├── embeddings/    # Embedding utilities
│   │   │   │   ├── __init__.py
│   │   │   │   └── embedder.py
│   │   │   ├── database/      # DB Access Layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── postgres.py    # PostgreSQL client
│   │   │   │   ├── vector_db.py   # Vector DB client
│   │   │   │   └── models.py      # SQLAlchemy models
│   │   │   └── config/        # Configuration Management
│   │   │       ├── __init__.py
│   │   │       ├── settings.py    # Static configs (Pydantic)
│   │   │       └── dynamic.py     # DB-backed dynamic configs
│   │   │
│   │   ├── models/             # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── requests.py    # API request models
│   │   │   ├── responses.py   # API response models
│   │   │   └── entities.py    # Domain entities
│   │   │
│   │   ├── utils/              # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── youtube.py     # YouTube video helpers
│   │   │   └── timestamps.py  # Timestamp formatting
│   │   │
│   │   └── main.py             # FastAPI app entry point
│   │
│   ├── requirements.txt
│   └── README.md
│
├── ingestion/                   # Standalone Ingestion Pipeline
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── download.py        # Download YouTube videos/audio
│   │   ├── transcribe.py      # Whisper/Deepgram transcription
│   │   ├── keyframes.py       # Extract keyframes with FFmpeg
│   │   ├── embeddings.py      # Generate embeddings
│   │   └── storage.py         # Store in vector + Postgres DB
│   ├── config/
│   │   └── courses.yaml       # Course structure: chapters, URLs
│   ├── main.py                # CLI entry point
│   ├── requirements.txt
│   └── README.md
│
├── evaluation/                  # Evaluation Module
│   ├── datasets/               # Test datasets (not in git)
│   │   ├── qa_eval.json
│   │   ├── summary_eval.json
│   │   ├── video_eval.json
│   │   └── quiz_eval.json
│   ├── scripts/
│   │   ├── run_qa_eval.py
│   │   ├── run_summary_eval.py
│   │   ├── run_video_eval.py
│   │   └── run_quiz_eval.py
│   ├── metrics/                # Evaluation metrics
│   │   ├── __init__.py
│   │   └── evaluator.py
│   ├── requirements.txt
│   └── README.md
│
├── docker-compose.yml           # Postgres + Vector DB
├── .env.example                 # Environment variables template
├── .gitignore
└── README.md                    # Project overview
```

---

## Module Ownership (4 Team Members)

### 👤 **Person 1: Frontend + Integration**
**Responsibility**: User interface and API integration
- `frontend/` - Entire React application
- Chat interface (ChatGPT-like)
- Task switcher component (toggle between 4 tasks)
- Video player with timestamp navigation
- API integration layer

**Dependencies**: Needs API contracts from backend team

---

### 👤 **Person 2: Q&A + Text Summarization**
**Responsibility**: First two AI tasks
- `backend/app/api/qa.py` + `backend/app/api/text_summary.py`
- `backend/app/core/qa/` + `backend/app/core/text_summary/`
- Task-specific prompts and orchestration
- Both modules use shared RAG library

**Dependencies**: Shared RAG library from Person 4

---

### 👤 **Person 3: Video Summarization + Quiz Generation**
**Responsibility**: Second two AI tasks
- `backend/app/api/video_summary.py` + `backend/app/api/quiz.py`
- `backend/app/core/video_summary/` + `backend/app/core/quiz/`
- VLM integration for keyframe analysis
- Task-specific prompts and orchestration

**Dependencies**: Shared RAG library and VLM client from Person 4

---

### 👤 **Person 4: Ingestion Pipeline + Shared Infrastructure**
**Responsibility**: Data pipeline and shared components
- `ingestion/` - Entire ingestion pipeline
- `backend/app/shared/` - RAG library, LLM clients, DB layer, config
- Docker setup and database schemas
- Core infrastructure that others depend on

**Dependencies**: None (foundational work)

---

## Key Shared Components

### 1. Shared RAG Library (`backend/app/shared/rag/`)

**Used by**: Q&A, Text Summarization, Quiz Generation

**Common RAG Flow**:
1. Embed user query
2. Search vector database
3. Retrieve relevant chunks with metadata
4. Return results with source info (video URL, timestamps)

**Task-Specific**: Each task uses different prompts and post-processing logic

**Benefits**:
- Code reuse across multiple tasks
- Consistent retrieval behavior
- Easier to optimize and maintain

---

### 2. Configuration System (`backend/app/shared/config/`)

**Two-tier system for easy migration**:

- `settings.py`: Static configurations (hardcoded, from env vars)
- `dynamic.py`: Runtime configurations stored in Postgres

**Migration Path**:
- **Phase 1 (MVP)**: Hardcode prompts in `core/*/prompts.py`
- **Phase 2**: Move prompts to Postgres via `dynamic.py`
- **Phase 3**: Add UI to edit prompts dynamically

**Implementation**: Config loader checks DB first, falls back to static files

---

### 3. Database Layer (`backend/app/shared/database/`)

**PostgreSQL Schema** (✅ Implemented with Alembic):
- `videos`: Video metadata (id, chapter, title, url, duration, transcript_path)
- `chunks`: Transcript chunks (id, video_id, start_time, end_time, text, qdrant_id)
- `chat_sessions`: Chat sessions (id, user_id, task_type, title, created_at, updated_at)
- `chat_messages`: Chat messages with sources (id, session_id, role, content, sources, created_at)
- `quiz_questions`: Generated quiz questions and answers (skeleton)

**Qdrant Collection** (✅ Implemented):
- Collection: `cs431_course_transcripts`
- Vector dimension: 1536 (text-embedding-3-small)
- Payload: chapter, video_title, video_url, full_title, start_time, end_time, text
- Chunking strategy: 60s time windows with 10s overlap
- Context enrichment: LLM-generated contextual prefix per chunk

---

## Implementation Status

### ✅ Fully Implemented Components

**Ingestion Pipeline** (`ingestion/pipeline/`):
- `download.py`: Download videos/audio from YouTube using yt-dlp (audio-only with fallback)
- `transcribe_videos.py`: Transcribe with local Whisper large-v3 model
- `embed_videos.py`: CLI script for embedding pipeline with:
  - Time-window chunking (60s + 10s overlap)
  - LLM-driven contextual enrichment (gpt-5-mini with minimal reasoning effort)
  - Batch embedding with OpenAI text-embedding-3-small
  - Storage in both Qdrant and PostgreSQL
  - `--reset` flag for clearing existing data
  - UUID-based Qdrant point IDs for compatibility
- `tmp_embed_new_transcripts.py`: Temporary script for embedding newly added transcripts

**Database Clients** (`backend/app/shared/database/`):
- `models.py`: SQLAlchemy models (Video, Chunk, ChatSession, ChatMessage, QuizQuestion)
- `postgres.py`: Full PostgreSQL client with session management
- `vector_db.py`: Full Qdrant client with CRUD operations and chapter filtering

**Embedding System** (`backend/app/shared/embeddings/`):
- `embedder.py`: OpenAIEmbedder + ContextualChunker classes
- Implements Anthropic's Contextual Retrieval approach with:
  - Vietnamese-optimized LLM prompts with examples
  - Retry logic for token limit overflow (300→400→500 tokens)
  - Hardcoded `reasoning_effort="minimal"` for gpt-5-mini
  - Unicode normalization (NFC) for cross-platform filename compatibility

**RAG Pipeline** (`backend/app/shared/rag/`):
- `retriever.py`: RAGRetriever with hybrid search (Vector + BM25 + RRF)
  - Vector search via Qdrant
  - BM25 lexical search via rank-bm25
  - Reciprocal Rank Fusion for combining results
  - Chapter filtering support
- `reranker.py`: LocalReranker with cross-encoder model
  - Uses `cross-encoder/ms-marco-MiniLM-L-6-v2`
  - Reranks top-K results for better relevance

**LLM Client** (`backend/app/shared/llm/`):
- `client.py`: OpenAI LLM client with SSE streaming
  - Support for `gpt-5-mini` with reasoning effort
  - Synchronous and asynchronous generation
  - Server-Sent Events (SSE) streaming for real-time responses
  - Automatic parameter handling (temperature, max_completion_tokens)

**Backend API Layer** (`backend/app/api/`):
- `sessions.py`: Universal session management (all tasks)
  - `GET /api/sessions` - List all sessions with optional task_type filter
  - `GET /api/sessions/{id}/messages` - Get session messages
  - `DELETE /api/sessions/{id}` - Delete session
- `text_summary.py`: Text summarization endpoints (✅ Complete)
  - `POST /api/text-summary/summarize` - SSE streaming summarization
  - `POST /api/text-summary/sessions/{id}/followup` - Followup questions
- `qa.py`, `video_summary.py`, `quiz.py`: Task endpoints (skeletons)
- `health.py`: Health check endpoint

**Text Summarization Module** (`backend/app/core/text_summary/`): ✅ Complete
- `service.py`: Full RAG pipeline orchestration
  - Hybrid retrieval (Vector + BM25 + RRF)
  - Cross-encoder reranking
  - Session management (create, retrieve, update)
  - Streaming LLM responses with inline citations
  - Chapter filtering support
- `prompts.py`: Task-specific prompts for hierarchical summaries

**Frontend** (`frontend/`): ✅ Text Summarization Complete
- React 18 + TypeScript with Vite bundler
- Zustand state management
- TanStack React Query for API calls
- Chakra UI v2 for styling
- **Components**:
  - `ChatContainer.tsx`: Main orchestration
  - `Sidebar.tsx`: Session history (Today/Yesterday/Older grouping)
  - `MessageList.tsx`: Message display with streaming
  - `Message.tsx`: Individual messages with clickable citations
  - `ChatInput.tsx`: Input with task switcher and chapter filter
- **Features**:
  - Real-time SSE streaming responses
  - Session history management
  - Inline citations [1], [2], etc. (open video at timestamp)
  - Chapter filtering (8 chapters: Chương 2-9)
  - Followup questions in same session

**Infrastructure**:
- Docker Compose setup (PostgreSQL + Qdrant)
- Alembic migrations for PostgreSQL schema management
- Single `.env` configuration file at project root
- Video mapping utilities (`ingestion/utils/video_mapper.py`) with:
  - Unicode NFC normalization for macOS filesystem compatibility
  - Flexible separator matching (`:`, `：`, `-`) for filename variations
- Database verification scripts (`scripts/verify_databases.py`, `scripts/check_postgres_data.py`)

### 🚧 Skeleton Components (Not Yet Implemented)

- Q&A module (`backend/app/core/qa/`)
- Video Summarization module (`backend/app/core/video_summary/`)
- Quiz Generation module (`backend/app/core/quiz/`)
- Vision LLM client (`backend/app/shared/llm/vlm.py`)
- Frontend: Q&A, Video Summary, Quiz interfaces
- Evaluation module (entire `evaluation/` directory)
- Keyframe extraction (`ingestion/pipeline/keyframes.py`)

---

## Data Flow Examples

### Example 1: Q&A Task
```
User: "What are the benefits of ResNet?"
   │
   ▼
[Frontend] POST /api/qa
   │
   ▼
[API Layer] qa.py endpoint
   │
   ▼
[Core] qa/service.py
   ├─▶ [Shared] embeddings.embedder → Embed query
   ├─▶ [Shared] rag.retriever → Search vector DB
   │   └─▶ Returns: [chunk1, chunk2, ...] with (video_id, timestamp)
   ├─▶ [Shared] llm.client → Generate answer
   │   └─▶ Prompt from qa/prompts.py
   ▼
[Response]
{
  "answer": "ResNet introduces skip connections that...",
  "sources": [
    {
      "video_url": "https://youtube.com/watch?v=abc",
      "timestamp": "15:30",
      "chapter": "Deep Learning Architectures"
    }
  ]
}
```

---

### Example 2: Quiz Generation Task
```
User: Select video → "Generate MCQ Quiz"
   │
   ▼
[Frontend] POST /api/quiz
   │
   ▼
[API Layer] quiz.py endpoint
   │
   ▼
[Core] quiz/service.py
   ├─▶ [Shared] database.postgres → Fetch transcript + keyframes
   ├─▶ [Shared] llm.vlm → Analyze keyframes with VLM
   ├─▶ [Shared] llm.client → Generate MCQs
   │   └─▶ Prompt from quiz/prompts.py
   ├─▶ [Shared] database.postgres → Store questions
   ▼
[Response]
{
  "quiz_id": "123",
  "questions": [
    {
      "question": "What type of connection does ResNet use?",
      "options": ["A) Skip", "B) Dense", "C) Recurrent", "D) Pooling"],
      "correct_answer": "A",
      "timestamp": "16:45",
      "video_url": "https://youtube.com/watch?v=abc"
    }
  ]
}
```

---

## Development Workflow

### Phase 1: Setup (Week 1)
1. **All**: Review architecture, assign modules
2. **Person 4**: 
   - Initialize project structure
   - Set up Docker Compose (Postgres + Vector DB)
   - Define database schemas
3. **Person 1**: Initialize React app skeleton
4. **All**: Define API contracts (request/response models)

---

### Phase 2: Foundation (Week 2-3)
1. **Person 4**: 
   - Build ingestion pipeline
   - Implement shared RAG library
   - Set up LLM clients
   - Populate databases with course data
2. **Persons 2 & 3**: Can start working with mocked RAG responses
3. **Person 1**: Build UI components with mocked API responses

---

### Phase 3: Core Development (Week 4-6)
1. **Person 2**: Implement Q&A and Text Summarization modules
2. **Person 3**: Implement Video Summarization and Quiz Generation modules
3. **Person 1**: Complete frontend implementation
4. **Person 4**: Support others, optimize shared components

---

### Phase 4: Integration & Testing (Week 7-8)
1. **All**: Integration testing
2. **All**: Bug fixes and refinements
3. **All**: Set up evaluation module
4. **All**: Run evaluations and optimize

---

## Docker Compose Services (✅ Implemented)

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-tieplm}
      POSTGRES_USER: ${POSTGRES_USER:-tieplm}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-tieplm}
    ports:
      - "5432:5432"
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-tieplm} -d ${POSTGRES_DB:-tieplm}"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
```

**Note**: 
- Both `postgres_data/` and `qdrant_data/` are mounted locally (not in git)
- Database credentials read from `.env` file
- Each team member runs embedding pipeline once: `python ingestion/pipeline/embed_videos.py --all --reset`
- Alembic handles schema migrations for PostgreSQL

---

## Evaluation Strategy

### End-to-End Task Evaluation

Each task has separate evaluation dataset and script:

1. **Q&A Evaluation** (`evaluation/scripts/run_qa_eval.py`)
   - Metrics: Answer accuracy, source relevance, timestamp precision
   - Dataset: Pre-defined questions with ground truth answers

2. **Text Summarization Evaluation** (`evaluation/scripts/run_summary_eval.py`)
   - Metrics: ROUGE scores, factual consistency, conciseness
   - Dataset: Topics with human-written reference summaries

3. **Video Summarization Evaluation** (`evaluation/scripts/run_video_eval.py`)
   - Metrics: Coverage, coherence, key point extraction
   - Dataset: Videos with human-written summaries

4. **Quiz Evaluation** (`evaluation/scripts/run_quiz_eval.py`)
   - Metrics: Question quality, difficulty distribution, answer correctness
   - Dataset: Manual review of generated quizzes

**Workflow**: 
1. Manually create evaluation datasets
2. Run evaluation scripts that call main system
3. Collect metrics and analyze results
4. Iterate on prompts and RAG strategies

---

## Configuration Migration Example

### Phase 1: Hardcoded Prompts
```python
# backend/app/core/qa/prompts.py
QA_SYSTEM_PROMPT = """
You are a helpful AI assistant for a video course.
Answer questions based on the provided context.
Always cite video sources with timestamps.
"""
```

### Phase 2: DB-backed Prompts
```python
# backend/app/shared/config/dynamic.py
def get_prompt(task: str, prompt_type: str) -> str:
    # Try DB first
    db_prompt = fetch_from_postgres(task, prompt_type)
    if db_prompt:
        return db_prompt
    
    # Fallback to static
    from ..core.qa.prompts import QA_SYSTEM_PROMPT
    return QA_SYSTEM_PROMPT
```

### Phase 3: UI for Editing
```typescript
// frontend/src/components/Admin/PromptEditor.tsx
// Admin interface to edit prompts stored in Postgres
```

---

## Shared Redundancies Identified

### 1. RAG Pipeline
- **Used by**: Q&A, Text Summarization, Quiz Generation
- **Shared**: Embedding, retrieval, vector search
- **Different**: Prompts, post-processing

### 2. Video Metadata Retrieval
- **Used by**: All tasks
- **Shared**: Fetch video info, chapters, timestamps from Postgres

### 3. LLM Client
- **Used by**: All tasks
- **Shared**: API calling, error handling, token management
- **Different**: Prompts and parameters

### 4. Source Citation
- **Used by**: Q&A, Text Summarization, Quiz Generation
- **Shared**: Format video URLs with timestamps

---

## API Endpoints Overview

### Q&A
- `POST /api/qa/ask` - Ask a question
- `GET /api/qa/history` - Get chat history

### Text Summarization
- `POST /api/text-summary/summarize` - Summarize topic
- `POST /api/text-summary/filter` - Get relevant videos for topic

### Video Summarization
- `POST /api/video-summary/summarize` - Summarize specific video
- `GET /api/video-summary/videos` - List available videos

### Quiz Generation
- `POST /api/quiz/generate` - Generate quiz for video
- `GET /api/quiz/{quiz_id}` - Retrieve generated quiz
- `POST /api/quiz/validate` - Validate user answers

### Common
- `GET /api/health` - Health check
- `GET /api/videos` - List all videos with metadata
- `GET /api/chapters` - List course chapters

---

## Environment Variables

```bash
# .env.example (✅ Implemented)

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tieplm
POSTGRES_USER=tieplm
POSTGRES_PASSWORD=tieplm

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=cs431_course_transcripts

# Embedding Hyperparameters
EMBEDDING_DIMENSION=1536
EMBEDDING_MODEL_NAME=text-embedding-3-small
EMBEDDING_PROVIDER=openai
TIME_WINDOW=60
CHUNK_OVERLAP=10
EMBEDDING_BATCH_SIZE=100

# LLM for Contextual Chunking
MODEL_NAME=gpt-5-mini
MODEL_PROVIDER=openai
CONTEXT_TOKEN_LIMIT=300  # Initial limit; retries with +100 tokens (up to 3 attempts: 300->400->500)
LLM_TEMPERATURE=1.0  # gpt-5-mini only supports default temperature=1.0
# Note: reasoning_effort="minimal" is hardcoded in embedder.py for gpt-5-mini

# Logging
LOG_DIR=logs
LOG_LEVEL=INFO
```

---

## Next Steps for Development

### ✅ Completed Foundation
1. ✅ Project structure created
2. ✅ Docker environment set up (PostgreSQL + Qdrant with local persistence)
3. ✅ Ingestion pipeline fully implemented and battle-tested
4. ✅ Database clients and models implemented with Alembic migrations
5. ✅ **62 course videos** downloaded, transcribed, and embedded (1059 chunks total)

### 🔄 Next Immediate Tasks

**Priority 1: Shared RAG Library** (`backend/app/shared/rag/`)
- Implement `retriever.py`: Query embedding + vector search + metadata retrieval
- Implement `pipeline.py`: End-to-end RAG orchestration
- Test with existing Qdrant embeddings

**Priority 2: LLM Client** (`backend/app/shared/llm/`)
- Implement `client.py`: OpenAI API wrapper for text generation
- Implement `vlm.py`: Vision LLM for keyframe analysis

**Priority 3: Core Task Implementation**
- Person 2: Q&A + Text Summarization services
- Person 3: Video Summarization + Quiz Generation services

**Priority 4: API Layer**
- Connect core services to FastAPI endpoints
- Define request/response schemas

**Priority 5: Frontend**
- Person 1: React UI with ChatGPT-like interface

### Current Data Status
- **62 videos** from CS431 course (Chapters 2-10)
- All transcribed with Whisper large-v3 (local model)
- All embedded in Qdrant with contextual chunking (**1059 total chunks**)
- Metadata stored in PostgreSQL (videos, chunks with timestamps and Qdrant IDs)
- Ready for RAG retrieval tasks

---

**Document Version**: 2.1  
**Last Updated**: November 13, 2025  
**Team Size**: 4 developers  
**Project Type**: University AI Assistant Project  
**Phase**: Foundation Complete - 62 Videos Embedded - Ready for RAG & Task Implementation