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
- **Backend**: Python with FastAPI (or Flask)
- **Frontend**: React with TypeScript
- **Databases**: 
  - PostgreSQL (video metadata, chapters, timestamps, chat history, quizzes)
  - Vector DB - options: Qdrant/pgvector/Weaviate (embeddings)
- **Transcription**: Whisper API / Deepgram
- **Video Processing**: FFmpeg or OpenCV for keyframe extraction
- **Orchestration**: LangChain / LlamaIndex (or custom implementation)

### Infrastructure
- Docker Compose for local development (Postgres + Vector DB)
- Vector DB data tracked in git (shared embeddings)
- Postgres data NOT in git (schema only)

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

**PostgreSQL Schema**:
- `videos`: Video metadata (URL, title, duration, course_id)
- `chapters`: Course chapter structure
- `transcripts`: Full transcripts with timestamps
- `chat_history`: User sessions and conversations
- `quiz_questions`: Generated quiz questions and answers
- `dynamic_configs`: Runtime configuration overrides

**Vector DB Schema**:
- Transcript embeddings (chunked by time segments)
- Keyframe descriptions embeddings
- Metadata: video_id, timestamp_start, timestamp_end, chunk_text

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

## Docker Compose Services

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: tieplm
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  vector_db:
    image: qdrant/qdrant  # or alternative (pgvector, weaviate)
    ports:
      - "6333:6333"
    volumes:
      - vector_data:/qdrant/storage

volumes:
  postgres_data:
  vector_data:
```

**Note**: 
- Vector DB data can be committed to git (manageable size)
- Postgres data NOT in git (only schema migrations)
- Each team member runs ingestion pipeline once to populate local DBs

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
# .env.example

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=tieplm
POSTGRES_USER=user
POSTGRES_PASSWORD=password

# Vector DB
VECTOR_DB_TYPE=qdrant  # or pgvector, weaviate
VECTOR_DB_HOST=localhost
VECTOR_DB_PORT=6333

# LLM APIs
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here  # optional

# Transcription
WHISPER_API_KEY=your_key_here
# or
DEEPGRAM_API_KEY=your_key_here

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## Next Steps for Team Discussion

### Questions to Discuss:
1. **Tech Stack Finalization**:
   - Vector DB choice: Qdrant, pgvector, or Weaviate?
   - LLM provider: OpenAI, Anthropic, or open-source?
   - Orchestration: LangChain, LlamaIndex, or custom?

2. **Module Assignment**:
   - Confirm 4-person split outlined above
   - Any preferences for specific modules?

3. **Timeline**:
   - Project deadline?
   - Milestone dates for each phase?

4. **Course Content**:
   - How many videos in the course?
   - Average video length?
   - Course structure (chapters/modules)?

5. **Evaluation**:
   - Who will create evaluation datasets?
   - Success criteria for each task?

### Ready to Start?
Once team agrees on architecture:
1. Create initial project structure
2. Set up Docker environment
3. Define detailed API contracts
4. Begin parallel development!

---

**Document Version**: 1.0  
**Last Updated**: November 11, 2025  
**Team Size**: 4 developers  
**Project Type**: University AI Assistant Project