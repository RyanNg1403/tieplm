# Notebook-LM AI Assistant - Architecture Document

## Project Overview

A video course AI assistant that helps students interact with course content through 4 main capabilities:
1. **Q&A**: Ask questions and get answers with exact video timestamps
2. **Text Summarization**: Get concise summaries on specific topics
3. **Video Summarization**: Summarize content of specific course videos
4. **Quiz Generation**: Generate Yes/No and MCQ quizzes from video content

**Source Material**: YouTube course videos  
**Architecture**: Modular Monolith (Python backend, React frontend)

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

## Project Structure (Module & Task Level)

```
tieplm/
│
├── frontend/                    # React/TypeScript Web UI
│   ├── src/
│   │   ├── components/         # UI components
│   │   │   ├── Chat/          # ChatGPT-like interface
│   │   │   ├── TaskSwitcher/  # Task switching UI
│   │   │   ├── VideoPlayer/   # Video with timestamp navigation
│   │   │   └── shared/        # Reusable components
│   │   ├── stores/            # Zustand state management
│   │   ├── services/          # API client (axios + SSE)
│   │   ├── hooks/             # Custom React hooks
│   │   └── types/             # TypeScript types
│   └── ...
│
├── backend/                     # Python Modular Monolith
│   ├── app/
│   │   ├── api/                # API endpoints
│   │   │   ├── sessions.py    # Universal session management
│   │   │   ├── text_summary.py # Text summarization
│   │   │   ├── qa.py          # Q&A
│   │   │   ├── video_summary.py # Video summarization
│   │   │   ├── quiz.py        # Quiz generation
│   │   │   └── health.py      # Health check
│   │   │
│   │   ├── core/               # Business logic (one module per task)
│   │   │   ├── text_summary/  # Text summarization
│   │   │   ├── qa/            # Q&A
│   │   │   ├── video_summary/ # Video summarization
│   │   │   └── quiz/          # Quiz generation
│   │   │
│   │   └── shared/             # Shared infrastructure ⭐
│   │       ├── rag/           # RAG library (retriever, reranker)
│   │       ├── llm/           # LLM clients (OpenAI, VLM)
│   │       ├── embeddings/    # Embedding & contextual chunking
│   │       ├── database/      # DB clients (PostgreSQL, Qdrant)
│   │       └── config/        # Configuration management
│   ├── alembic/                # Database migrations
│   └── ...
│
├── ingestion/                   # Standalone ingestion pipeline
│   ├── pipeline/               # Download, transcribe, embed scripts
│   ├── utils/                  # Video mapping utilities
│   ├── videos/                 # Downloaded videos (not in git)
│   ├── transcripts/            # Generated transcripts
│   └── ...
│
├── evaluation/                  # Evaluation module (task-specific folders)
│   ├── text_summary/           # Text summary eval (DONE)
│   ├── qa/                     # Q&A eval (TODO)
│   ├── video_summary/          # Video summary eval (TODO)
│   └── quiz/                   # Quiz eval (TODO)
│
├── scripts/                     # Utility scripts (DB verification, etc.)
├── docker-compose.yml           # PostgreSQL + Qdrant
├── .env.example                 # Environment variables template
└── README.md                    # Project overview
```

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

**PostgreSQL Schema**:
- `videos`: Video metadata (id, chapter, title, url, duration, transcript_path)
- `chunks`: Transcript chunks (id, video_id, start_time, end_time, text, qdrant_id)
- `chat_sessions`: Chat sessions (id, user_id, task_type, title, created_at, updated_at)
- `chat_messages`: Chat messages with sources (id, session_id, role, content, sources, created_at)
- `quiz_questions`: Generated quiz questions and answers

**Qdrant Collection**:
- Collection: `cs431_course_transcripts`
- Vector dimension: 1536 (text-embedding-3-small)
- Payload: chapter, video_title, video_url, full_title, start_time, end_time, text
- Chunking strategy: 60s time windows with 10s overlap
- Context enrichment: LLM-generated contextual prefix per chunk

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

## Docker Compose Services

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

Each task has its own folder in `evaluation/` with task-specific evaluation service, runner script, and test dataset.

**Evaluation Metrics by Task:**
1. **Q&A**: Answer accuracy, source relevance, timestamp precision (TODO)
2. **Text Summarization**: ✅ **DeepEval QAG-based metrics**
   - Coverage Score: Detail inclusion from original text
   - Alignment Score: Factual accuracy (no hallucinations)
   - Overall Score: min(coverage, alignment)
   - 50 test questions covering all 8 chapters
3. **Video Summarization**: Coverage, coherence, key point extraction (TODO)
4. **Quiz Generation**: Question quality, difficulty distribution, answer correctness (TODO)

**Evaluation Workflow** (Text Summarization - Implemented):
1. Test questions stored in `evaluation/text_summary/test_questions.json`
2. Runner script (`run_eval.py`) generates summaries via RAG pipeline
3. DeepEval's QAG framework evaluates using closed-ended questions
4. Results saved as JSON with statistics (mean, min, max, chapter distribution)
5. Iterate on prompts/RAG strategies based on results

**Configuration**:
```bash
EVAL_MODEL=gpt-5-mini                    # Model for evaluation
EVAL_SUMMARIZATION_THRESHOLD=0.5         # Pass/fail threshold
```

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