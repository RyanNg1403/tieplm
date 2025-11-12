# Ingestion Module

Process YouTube videos: download → transcribe → embed → store in databases.

## 📁 Structure

```
ingestion/
├── videos/        # Downloaded videos
├── transcripts/   # JSON transcripts
└── pipeline/      # Processing scripts
    ├── download.py           # Download from YouTube
    ├── transcribe_videos.py  # Transcribe with Whisper
    ├── embeddings.py         # Generate embeddings
    ├── keyframes.py          # Extract video frames
    └── storage.py            # Store in databases
```

## ✅ Implemented

- ✅ Download script (`download.py`)
- ✅ Transcription with Whisper (`transcribe_videos.py`)
- ✅ Support for all Whisper models (tiny → large-v3)
- ✅ Batch processing with progress bars
- ✅ Resume capability (skips completed)
- ✅ Word-level timestamps

## ❌ TODO

- ❌ Embedding generation (`embeddings.py`)
- ❌ Keyframe extraction (`keyframes.py`)
- ❌ Database storage (`storage.py`)
- ❌ Chunking strategy (time-based)
- ❌ Integration with vector DB (Qdrant)
- ❌ Integration with PostgreSQL

## 🚀 Quick Start

```bash
cd ingestion/pipeline

# 1. Download videos
python download.py --all

# 2. Transcribe (choose model based on speed/quality trade-off)
python transcribe_videos.py --all --model medium  # Recommended
# or
python transcribe_videos.py --all --model large-v3  # Best quality

# 3. Generate embeddings (TODO)
# python embeddings.py --all
```

## ⚙️ Whisper Models

| Model | Speed | Quality | Time (62 videos) |
|-------|-------|---------|------------------|
| tiny | Very Fast | Basic | ~10 min |
| small | Fast | Good | ~30 min |
| **medium** | Medium | Very Good | **~1 hour** ⭐ |
| large-v3 | Slow | Best | ~3-4 hours |

**Recommendation**: Use `medium` for balance of speed/quality.

## 📊 Output

Each video → JSON file with:
- Full transcript text
- Language detected
- Segments with timestamps
- Word-level timestamps

**Next Step**: Generate embeddings from transcripts.
