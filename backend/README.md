# Backend Module

FastAPI backend for AI assistant with 4 tasks: Q&A, Text Summary, Video Summary, Quiz Generation.

## 📁 Structure

```
backend/app/
├── api/              # API endpoints (5 files)
├── core/             # Business logic (4 task modules)
│   ├── qa/
│   ├── text_summary/
│   ├── video_summary/
│   └── quiz/
├── shared/           # Shared components
│   ├── rag/         # RAG library
│   ├── llm/         # LLM clients
│   ├── embeddings/  # Embedding utils
│   ├── database/    # DB clients
│   └── config/      # Configuration
├── models/           # Pydantic schemas
└── utils/            # Helper functions
```

## ✅ Implemented

- ✅ Project structure
- ✅ API endpoint skeletons
- ✅ Pydantic models (requests/responses)
- ✅ Database models (SQLAlchemy)
- ✅ Config management (static + dynamic)
- ✅ Utility functions (YouTube, timestamps)

## ❌ TODO

- ❌ Shared RAG library (`shared/rag/`)
- ❌ LLM clients (`shared/llm/`)
- ❌ Embeddings module (`shared/embeddings/`)
- ❌ Database clients (`shared/database/`)
- ❌ Q&A service (`core/qa/`)
- ❌ Text Summary service (`core/text_summary/`)
- ❌ Video Summary service (`core/video_summary/`)
- ❌ Quiz service (`core/quiz/`)
- ❌ API endpoint implementations

## 🚀 Run

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# Visit: http://localhost:8000/docs
```

