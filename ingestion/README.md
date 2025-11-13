# Ingestion Pipeline

Processes YouTube videos into searchable embeddings with contextual retrieval.

> **Prerequisites:** Complete setup from root [README.md](../README.md) first.

## 📁 Folder Structure

```
ingestion/
├── pipeline/
│   ├── download.py           # ✅ YouTube download (yt-dlp)
│   ├── transcribe_videos.py  # ✅ Whisper transcription
│   └── embed_videos.py       # ✅ Contextual embedding
├── utils/
│   └── video_mapper.py       # ✅ Transcript-to-URL mapping
├── videos/                   # Downloaded videos (gitignored)
├── transcripts/              # ✅ JSON transcripts (62 videos)
└── logs/                     # Pipeline logs
```

## Usage

### 1. Download Videos

```bash
python pipeline/download.py --all
# Or: --chapters "Chương 4" "Chương 5"
# Or: --urls "https://youtu.be/..."
```

Downloads from `chapters_urls.json` to `videos/`

### 2. Transcribe Videos

```bash
python pipeline/transcribe_videos.py --all
# Or: --videos "video1.mp4" "video2.mp4"
```

Uses Whisper large-v3 (local), saves to `transcripts/`

### 3. Embed with Contextual Chunking

```bash
python pipeline/embed_videos.py --all
# Or: --chapters "Chương 4"
# Or: --urls "https://youtu.be/..."
```

**Process:**
1. Creates time-based chunks (configurable via `TIME_WINDOW` and `CHUNK_OVERLAP`)
2. Generates context using LLM (`MODEL_NAME` in .env)
3. Embeds with `EMBEDDING_MODEL_NAME`
4. Stores in Qdrant + PostgreSQL

**Contextual Retrieval (Anthropic's Approach):**
Each chunk is enriched with context (chapter, video title, topic, prev/next summaries) before embedding, improving retrieval accuracy by 49%.

### CLI Options

Override environment variables via CLI arguments:
```bash
python pipeline/embed_videos.py --all \
  --chunk-duration 90 \
  --overlap 15 \
  --batch-size 50
```

## Output

### PostgreSQL
- `videos` table: Video metadata (chapter, title, URL)
- `chunks` table: Chunk metadata (timestamps, Qdrant IDs)

### Qdrant
- **Collection**: `cs431_course_transcripts`
- **Vectors**: 1536-dimensional embeddings
- **Payload**: Chapter, video title, URL, timestamps, original text, contextualized text

## ✅ Implemented

- ✅ YouTube video download (`download.py`)
  - Audio-only download with fallback to video
  - Support for `--all`, `--chapters`, `--urls` filters
- ✅ Whisper transcription (`transcribe_videos.py`)
  - Local Whisper large-v3 model
  - Word-level timestamps
  - Support for `--all`, `--videos` filters
- ✅ Contextual embedding (`embed_videos.py`)
  - Time-window chunking (60s + 10s overlap)
  - LLM-driven context generation (gpt-5-mini)
  - OpenAI text-embedding-3-small
  - Batch embedding with retry logic
  - Qdrant + PostgreSQL storage
  - Support for `--all`, `--chapters`, `--urls`, `--reset` flags
- ✅ Video mapping utilities with Unicode normalization
- ✅ **Current Data**: 62 videos, 1059 chunks embedded

## ❌ TODO

- ❌ Keyframe extraction (skeleton only)
- ❌ Video quality optimization
- ❌ Multi-language support
- ❌ Incremental updates (currently full pipeline only)

## Reference

- [Anthropic's Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)
