# Team Implementation Guide

**Before Starting:** Read `ARCHITECTURE.md`, `MODULES.md`, and study `text_summary` implementation.

---

## 1. Core Business Logic (`backend/app/core/<task>/`)

### Structure
```
backend/app/core/<task>/
├── service.py    # Main orchestration logic
└── prompts.py    # LLM prompts
```

### What to Do

**`service.py`:**
1. Create `<Task>Service` class with `__init__` importing shared services
2. Define main method (e.g., `answer()`, `generate()`) that:
   - Retrieves chunks via `self.retriever.retrieve(query, chapters)`
   - Reranks via `self.reranker.rerank(query, chunks)`
   - Builds task-specific prompt
   - Streams response via `self.llm.stream_with_sources()`
   - Saves to session using `ChatSession` with `task_type='<task>'`

**`prompts.py`:**
1. Define system prompt for your task
2. Define function to build user prompt with retrieved sources

**Key Pattern:**
```python
async def your_method(query, chapters=None, session_id=None):
    # 1. Get or create session
    # 2. Retrieve → Rerank → Build prompt
    # 3. Stream LLM response
    # 4. Save messages
```

---

## 2. API Design (`backend/app/api/<task>.py`)

### Structure
```python
router = APIRouter(prefix="/<task>", tags=["<task>"])
```

### What to Do

1. **Create main endpoint** (SSE streaming):
   - Use `StreamingResponse` with `media_type="text/event-stream"`
   - Call your service's main method
   - Yield SSE events: `f"data: {json.dumps(event)}\n\n"`

2. **Register router** in `backend/app/main.py`:
   ```python
   from app.api import <task>
   app.include_router(<task>.router, prefix="/api")
   ```

3. **Session management:**
   - ❌ Don't create session endpoints (already exist in `sessions.py`)
   - ✅ Use `ChatSession` with your `task_type`

**Endpoint Pattern:**
```
POST /api/<task>/<action>       # Main action (SSE streaming)
POST /api/<task>/sessions/{id}/followup  # Optional followup
```

---

## 3. Shared Services (`backend/app/shared/`)

### ❌ DO NOT MODIFY - Just Import & Use

**RAG Retriever:**
```python
from backend.app.shared.rag.retriever import RAGRetriever
retriever = RAGRetriever()
chunks = await retriever.retrieve(query, top_k=10, chapter_filter=['Chương 2'])
```

**Reranker:**
```python
from backend.app.shared.rag.reranker import LocalReranker
reranker = LocalReranker()
reranked = reranker.rerank(query, chunks)
```

**LLM Client:**
```python
from backend.app.shared.llm.client import LLMClient
llm = LLMClient()
async for event in llm.stream_with_sources(prompt, system_prompt, sources):
    yield event  # Yields: {type: 'token'|'sources'|'done', content, sources}
```

**Database:**
```python
from backend.app.shared.database.postgres import get_postgres_client
from backend.app.shared.database.models import ChatSession, ChatMessage

postgres = get_postgres_client()
with postgres.session_scope() as session:
    # Query/save data
```

### When to Modify Shared Services

**Never modify unless:**
- Bug fix affecting all tasks
- Performance optimization for all tasks
- Discuss with team first

---

## 4. Frontend Integration (`frontend/`)

### Step 1: Add API Client (`src/services/api.ts`)

```typescript
export const <task>API = {
  getStreamURL: (): string => {
    return `${API_BASE_URL}/api/<task>/<action>`;
  },
};
```

### Step 2: Add Task Type (`src/types/index.ts`)

```typescript
export type TaskType = 'text_summary' | 'qa' | 'video_summary' | 'quiz';
```

### Step 3: Update Chat Input (`src/components/Chat/ChatInput.tsx`)

Add your task to `taskLabels`:
```typescript
const taskLabels: Record<TaskType, string> = {
  text_summary: 'Text Summary',
  qa: 'Q&A',
  video_summary: 'Video Summary',
  quiz: 'Quiz',
};
```

### Step 4: Update Chat Container (`src/components/Chat/ChatContainer.tsx`)

Add case in `handleSend` for your task:
```typescript
if (currentMode === 'qa') {
  url = qaAPI.getStreamURL();
  payload = { query: message, chapters: selectedChapters };
}
```

### What's Already Built (Reuse):

- ✅ `useSSE()` hook - SSE streaming
- ✅ `sessionsAPI` - Session management (list, get, delete)
- ✅ `Sidebar` - History sidebar
- ✅ `Message` - Message display with citations
- ✅ `ChatInput` - Input with mode switcher & chapter filter

---

## Checklist

### Backend
- [ ] Create `core/<task>/service.py` and `prompts.py`
- [ ] Import shared services (retriever, reranker, LLM)
- [ ] Create `api/<task>.py` with SSE endpoint
- [ ] Register router in `main.py`
- [ ] Use `ChatSession` with `task_type='<task>'`
- [ ] Test endpoint: `curl http://localhost:8000/docs`

### Frontend
- [ ] Add `<task>API` to `services/api.ts`
- [ ] Add task type to `types/index.ts`
- [ ] Update `ChatInput.tsx` task labels
- [ ] Add task case in `ChatContainer.tsx`
- [ ] Test in browser: switch mode → send message

---

## Quick Reference

**File Locations:**
- Backend logic: `backend/app/core/<task>/service.py`
- Backend API: `backend/app/api/<task>.py`
- Frontend API: `frontend/src/services/api.ts`
- Frontend UI: `frontend/src/components/Chat/ChatContainer.tsx`

**Shared Services (Import Only):**
- `backend.app.shared.rag.retriever.RAGRetriever`
- `backend.app.shared.rag.reranker.LocalReranker`
- `backend.app.shared.llm.client.LLMClient`
- `backend.app.shared.database.postgres.get_postgres_client`

**Session Management (Use Existing):**
- `GET /api/sessions` - List sessions
- `GET /api/sessions/{id}/messages` - Get messages
- `DELETE /api/sessions/{id}` - Delete session

**Need Help?** Check `text_summary` implementation as reference.

---

**Estimated Time Per Task:** 2-4 hours (backend + frontend)

**Team Can Work in Parallel** - Tasks are independent! 🚀
