# Tieplm AI Assistant

A NotebookLM-like AI assistant for video course content, supporting Q&A, text summarization, video summarization, and quiz generation.

## Features

- **Q&A**: Ask questions about course content with exact video timestamp citations
- **Text Summarization**: Get concise summaries on specific topics across videos
- **Video Summarization**: Summarize individual video content using transcripts and keyframes
- **Quiz Generation**: Generate MCQ and Yes/No quizzes based on video content

## Architecture

- **Backend**: Python FastAPI (Modular Monolith)
- **Frontend**: React TypeScript
- **Databases**: PostgreSQL (metadata) + Qdrant (vector embeddings)
- **Ingestion**: Standalone pipeline for processing YouTube videos

## Project Structure

```
tieplm/
├── backend/          # FastAPI backend
├── frontend/         # React frontend
├── ingestion/        # Video processing pipeline
├── evaluation/       # Evaluation scripts
└── docker-compose.yml
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- FFmpeg (for video/audio processing)

### 2. Setup Databases

```bash
# Start PostgreSQL + Qdrant
docker-compose up -d
```

### 3. Install Python Dependencies

```bash
# Install all Python dependencies from root
pip install -r requirements.txt
```

### 4. Download & Process Videos

```bash
cd ingestion/pipeline

# Step 1: Download videos from YouTube
python download.py --all

# Step 2: Transcribe videos
python transcribe_videos.py --all

# Step 3: Generate embeddings & store (coming soon)
# python embed_transcripts.py --all
```

### 5. Setup Frontend

```bash
cd frontend
npm install
```

### 6. Run Application

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm start
```

Visit: http://localhost:3000

## Project Structure

```
tieplm/
├── requirements.txt      # All Python dependencies
├── chapters_urls.json    # Video URLs by chapter
│
├── ingestion/            # Video processing pipeline
│   ├── videos/          # Downloaded video files
│   ├── transcripts/     # JSON transcripts
│   └── pipeline/        # Processing scripts
│       ├── download.py  # Download videos
│       ├── transcribe_videos.py  # Transcribe videos
│       ├── embeddings.py
│       ├── keyframes.py
│       └── storage.py
│
├── backend/              # FastAPI backend
├── frontend/             # React frontend
└── docker-compose.yml    # Databases
```

## Development Workflow

### Module Ownership (4-Person Team)

- **Person 1**: Frontend + Integration
- **Person 2**: Q&A + Text Summarization modules
- **Person 3**: Video Summarization + Quiz Generation modules
- **Person 4**: Ingestion Pipeline + Shared Infrastructure

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation.

## API Documentation

Once backend is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

Key environment variables (see `.env.example`):
- `OPENAI_API_KEY`: For LLM and embeddings
- `WHISPER_API_KEY`: For transcription
- `POSTGRES_*`: Database configuration
- `VECTOR_DB_*`: Vector database configuration

## Evaluation

```bash
cd evaluation
source venv/bin/activate

# Run evaluations
python scripts/run_qa_eval.py
python scripts/run_summary_eval.py
python scripts/run_video_eval.py
python scripts/run_quiz_eval.py
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Qdrant
- **Frontend**: React, TypeScript
- **LLM**: OpenAI GPT-4
- **Embeddings**: OpenAI text-embedding-3-small
- **Transcription**: Whisper API / Deepgram
- **Video Processing**: yt-dlp, FFmpeg

## License

University Project - Educational Use Only

## Team

4-person development team  
Project: AI Assistant for Video Course Content

