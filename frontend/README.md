# Frontend Module

React TypeScript web UI with ChatGPT-like interface for 4 AI tasks.

## 📁 Folder Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat/          # ✅ ChatGPT-like interface (complete)
│   │   │   ├── ChatContainer.tsx  # Main chat orchestration
│   │   │   ├── ChatInput.tsx      # Input + task switcher + filters
│   │   │   ├── Message.tsx        # Individual message with citations
│   │   │   ├── MessageList.tsx    # Message display with streaming
│   │   │   ├── Sidebar.tsx        # Session history sidebar
│   │   │   └── SessionItem.tsx    # Session list item
│   │   ├── TaskSwitcher/  # ❌ Placeholder (task switching in ChatInput)
│   │   ├── VideoPlayer/   # ❌ Placeholder (timestamp navigation)
│   │   └── shared/        # ❌ Reusable components (planned)
│   ├── stores/            # ✅ Zustand state management
│   ├── services/          # ✅ API client (axios + SSE)
│   ├── hooks/             # ✅ Custom React hooks (useSSE)
│   ├── types/             # ✅ TypeScript types
│   └── App.tsx            # ✅ App entry point
├── index.html             # ✅ Vite entry point
├── vite.config.ts         # ✅ Vite configuration
└── package.json           # ✅ Dependencies
```

## Installation

> **Prerequisites:** Complete backend setup from root [README.md](../README.md) first.

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server (uses FRONTEND_PORT from root .env, default: 3000)
npm start  # or npm run dev

# Visit: http://localhost:3000
```

**Note:** Frontend `.env` is a symlink to root `.env` for Vite compatibility.

## ✅ Implemented

### Core Infrastructure
- ✅ Vite bundler (fast, zero vulnerabilities)
- ✅ TypeScript types (`types/index.ts`)
- ✅ API service layer with universal session APIs (`services/api.ts`)
- ✅ Zustand state management (`stores/chatStore.ts`)
- ✅ SSE streaming hook (`hooks/useSSE.ts`)
- ✅ Chakra UI v2 styling

### Text Summarization (Complete)
- ✅ ChatGPT-like interface with streaming
- ✅ Session history sidebar (Today/Yesterday/Older grouping)
- ✅ Task switcher in chat input
- ✅ Chapter filtering (8 chapters: Chương 2-9)
- ✅ Clickable citation links [1], [2], etc. (open video at timestamp)
- ✅ Followup questions in same session
- ✅ New chat / Load session / Delete session

## ❌ TODO (Future Work)

- ❌ Q&A interface (skeleton only)
- ❌ Video Summary interface (skeleton only)
- ❌ Quiz interface (skeleton only)
- ❌ VideoPlayer component with timestamp navigation
- ❌ Mobile responsive sidebar (collapsible)

## 📦 Tech Stack

- **Bundler**: Vite (fast, modern, zero vulnerabilities)
- **UI Framework**: React 18 + TypeScript
- **Component Library**: Chakra UI v2
- **State Management**: Zustand
- **API Client**: TanStack React Query (caching + SSE)
- **Icons**: Chakra UI Icons

## 🎯 Scripts

- `npm start` / `npm run dev` - Start dev server
- `npm run build` - Production build (outputs to `/build`)
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

