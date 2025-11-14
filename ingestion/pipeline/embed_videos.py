#!/usr/bin/env python3
"""
Embedding pipeline: Create contextual chunks and embed them into Qdrant.

This script:
1. Loads transcripts from ingestion/transcripts/
2. Creates time-window chunks (configurable via TIME_WINDOW and CHUNK_OVERLAP env vars)
3. Generates contextual information using LLM (configurable via MODEL_NAME env var)
4. Embeds contextualized chunks using embedding model (configurable via EMBEDDING_MODEL_NAME env var)
5. Stores embeddings in Qdrant and metadata in PostgreSQL

All hyperparameters can be configured via environment variables in .env file.
"""
import argparse
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
from dotenv import load_dotenv

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.shared.embeddings.embedder import OpenAIEmbedder, ContextualChunker
from backend.app.shared.database.vector_db import VectorDBClient
from backend.app.shared.database.postgres import PostgresClient
from backend.app.shared.database.models import Video, Chunk
from ingestion.utils.video_mapper import get_all_video_mappings


# Set up logging
def setup_logging(log_file: str = None):
    """Set up logging configuration."""
    log_dir_name = os.getenv("LOG_DIR", "logs")
    log_dir = Path(__file__).parent.parent / log_dir_name
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / (log_file or "embedding.log")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


class EmbeddingPipeline:
    """Pipeline for embedding video transcripts with contextual chunking."""
    
    def __init__(
        self,
        transcripts_dir: str,
        chunk_duration: int = None,
        overlap_duration: int = None,
        batch_size: int = None
    ):
        """Initialize embedding pipeline.
        
        Args:
            transcripts_dir: Directory containing transcript JSON files.
            chunk_duration: Chunk duration in seconds. If None, reads from TIME_WINDOW env var.
            overlap_duration: Overlap duration in seconds. If None, reads from CHUNK_OVERLAP env var.
            batch_size: Number of chunks to embed at once. If None, reads from EMBEDDING_BATCH_SIZE env var.
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.batch_size = batch_size or int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
        
        # Read chunk settings from environment if not provided
        chunk_duration = chunk_duration or int(os.getenv("TIME_WINDOW", "60"))
        overlap_duration = overlap_duration or int(os.getenv("CHUNK_OVERLAP", "10"))
        
        # Initialize components
        self.logger = logging.getLogger(__name__)
        self.embedder = OpenAIEmbedder()
        self.chunker = ContextualChunker(
            chunk_duration=chunk_duration,
            overlap_duration=overlap_duration
        )
        self.vector_db = VectorDBClient()
        self.postgres = PostgresClient()
        
        self.logger.info(f"Initialized embedding pipeline with TIME_WINDOW={chunk_duration}s, CHUNK_OVERLAP={overlap_duration}s, BATCH_SIZE={self.batch_size}")
    
    def process_video(self, video_mapping: Dict[str, str]) -> int:
        """Process a single video transcript.
        
        Args:
            video_mapping: Dict with transcript_path, chapter, title, url.
        
        Returns:
            Number of chunks created.
        """
        transcript_path = video_mapping["transcript_path"]
        chapter = video_mapping["chapter"]
        title = video_mapping["title"]
        url = video_mapping["url"]
        
        self.logger.info(f"Processing: {Path(transcript_path).name}")
        
        # Load transcript
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load transcript {transcript_path}: {e}")
            return 0
        
        # Create video metadata
        video_metadata = {
            "chapter": chapter,
            "title": title,
            "url": url
        }
        
        # Create contextualized chunks
        try:
            chunks = self.chunker.create_contextualized_chunks(transcript, video_metadata)
        except Exception as e:
            self.logger.error(f"Failed to create chunks for {title}: {e}")
            return 0
        
        if not chunks:
            self.logger.warning(f"No chunks created for {title}")
            return 0
        
        self.logger.info(f"Created {len(chunks)} chunks for {title}")
        
        # Generate video ID (use URL hash or chapter+title)
        video_id = f"{chapter}_{url.split('/')[-1]}"
        
        # Store video metadata in PostgreSQL
        try:
            with self.postgres.session_scope() as session:
                # Check if video already exists
                existing_video = session.query(Video).filter_by(id=video_id).first()
                
                if existing_video:
                    self.logger.info(f"Video {video_id} already exists in database, updating...")
                    existing_video.chapter = chapter
                    existing_video.title = title
                    existing_video.url = url
                    existing_video.transcript_path = transcript_path
                else:
                    # Create new video entry
                    video = Video(
                        id=video_id,
                        chapter=chapter,
                        title=title,
                        url=url,
                        transcript_path=transcript_path
                    )
                    session.add(video)
        except Exception as e:
            self.logger.error(f"Failed to store video metadata: {e}")
            return 0
        
        # Embed and store chunks
        embedded_count = 0
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            
            try:
                # Extract contextualized texts for embedding
                texts_to_embed = [chunk["contextualized_text"] for chunk in batch]
                
                # Generate embeddings
                embeddings = self.embedder.embed_batch(texts_to_embed)
                
                # Prepare Qdrant payloads
                payloads = []
                qdrant_ids = []
                
                for chunk, embedding in zip(batch, embeddings):
                    # Generate UUID for Qdrant point ID (Qdrant requires UUID or unsigned int)
                    chunk_id = str(uuid.uuid4())
                    qdrant_ids.append(chunk_id)
                    
                    payload = {
                        "video_id": video_id,
                        "chapter": chunk["metadata"]["chapter"],
                        "video_title": chunk["metadata"]["video_title"],
                        "video_url": chunk["metadata"]["video_url"],
                        "start_time": chunk["start_time"],
                        "end_time": chunk["end_time"],
                        "text": chunk["text"],
                        "contextualized_text": chunk["contextualized_text"]
                    }
                    payloads.append(payload)
                
                # Upsert to Qdrant
                self.vector_db.upsert_points(
                    vectors=embeddings,
                    payloads=payloads,
                    ids=qdrant_ids
                )
                
                # Store chunk metadata in PostgreSQL
                with self.postgres.session_scope() as session:
                    for chunk, qdrant_id in zip(batch, qdrant_ids):
                        chunk_entry = Chunk(
                            video_id=video_id,
                            start_time=int(chunk["start_time"]),
                            end_time=int(chunk["end_time"]),
                            text=chunk["text"],
                            contextualized_text=chunk["contextualized_text"],
                            qdrant_id=qdrant_id
                        )
                        session.add(chunk_entry)
                
                embedded_count += len(batch)
                self.logger.info(f"Embedded batch {i // self.batch_size + 1}: {len(batch)} chunks")
                
            except Exception as e:
                self.logger.error(f"Failed to embed batch: {e}")
                continue
        
        self.logger.info(f"Successfully embedded {embedded_count}/{len(chunks)} chunks for {title}")
        return embedded_count
    
    def reset_databases(self):
        """Reset both Qdrant and PostgreSQL databases."""
        self.logger.info("🔄 Resetting databases...")
        
        try:
            # Reset Qdrant collection
            self.logger.info("Deleting Qdrant collection...")
            self.vector_db.delete_collection()
            self.vector_db.create_collection()
            self.logger.info("✅ Qdrant collection reset")
        except Exception as e:
            self.logger.error(f"Failed to reset Qdrant: {e}")
        
        try:
            # Initialize PostgreSQL tables if they don't exist
            self.logger.info("Initializing PostgreSQL tables...")
            self.postgres.init_db()
            
            # Clear PostgreSQL tables
            self.logger.info("Clearing PostgreSQL tables...")
            with self.postgres.session_scope() as session:
                chunks_deleted = session.query(Chunk).delete()
                videos_deleted = session.query(Video).delete()
                self.logger.info(f"✅ PostgreSQL cleared: {videos_deleted} videos, {chunks_deleted} chunks deleted")
        except Exception as e:
            self.logger.error(f"Failed to reset PostgreSQL: {e}")
    
    def run(
        self,
        chapters: List[str] = None,
        video_urls: List[str] = None,
        process_all: bool = False,
        reset: bool = False
    ):
        """Run the embedding pipeline.
        
        Args:
            chapters: List of chapters to process (e.g., ["Chương 4", "Chương 5"]).
            video_urls: List of specific video URLs to process.
            process_all: If True, process all transcripts.
            reset: If True, clear all existing data before processing.
        """
        # Reset databases if requested
        if reset:
            self.reset_databases()
        
        # Ensure Qdrant collection exists
        try:
            self.vector_db.create_collection(recreate=False)
        except Exception as e:
            self.logger.error(f"Failed to create Qdrant collection: {e}")
            return
        
        # Get video mappings
        self.logger.info("Loading video mappings...")
        all_mappings = get_all_video_mappings(str(self.transcripts_dir))
        
        # Filter mappings based on arguments
        if process_all:
            mappings_to_process = all_mappings
        elif chapters:
            mappings_to_process = [m for m in all_mappings if m["chapter"] in chapters]
        elif video_urls:
            mappings_to_process = [m for m in all_mappings if m["url"] in video_urls]
        else:
            self.logger.error("No videos specified. Use --all, --chapters, or --urls.")
            return
        
        if not mappings_to_process:
            self.logger.warning("No videos found matching the criteria.")
            return
        
        self.logger.info(f"Processing {len(mappings_to_process)} videos...")
        
        # Process each video with progress bar
        total_chunks = 0
        for mapping in tqdm(mappings_to_process, desc="Embedding videos"):
            chunks_count = self.process_video(mapping)
            total_chunks += chunks_count
        
        self.logger.info(f"Pipeline complete! Embedded {total_chunks} total chunks from {len(mappings_to_process)} videos.")


def main():
    """Main entry point for embedding pipeline."""
    parser = argparse.ArgumentParser(
        description="Embed video transcripts with contextual chunking"
    )
    
    parser.add_argument(
        "--transcripts_dir",
        type=str,
        default="./transcripts",
        help="Directory containing transcript JSON files (default: ./transcripts)"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all transcripts"
    )
    
    parser.add_argument(
        "--chapters",
        type=str,
        nargs="+",
        help="Process specific chapters (e.g., 'Chương 4' 'Chương 5')"
    )
    
    parser.add_argument(
        "--urls",
        type=str,
        nargs="+",
        help="Process specific video URLs"
    )
    
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=None,
        help="Chunk duration in seconds (default: from TIME_WINDOW env var or 60)"
    )
    
    parser.add_argument(
        "--overlap",
        type=int,
        default=None,
        help="Overlap duration in seconds (default: from CHUNK_OVERLAP env var or 10)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Number of chunks to embed at once (default: from EMBEDDING_BATCH_SIZE env var or 100)"
    )
    
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset databases (delete all existing data) before embedding"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logger = setup_logging()
    logger.info("Starting embedding pipeline")
    
    # Create pipeline
    pipeline = EmbeddingPipeline(
        transcripts_dir=args.transcripts_dir,
        chunk_duration=args.chunk_duration,
        overlap_duration=args.overlap,
        batch_size=args.batch_size
    )
    
    # Run pipeline
    pipeline.run(
        chapters=args.chapters,
        video_urls=args.urls,
        process_all=args.all,
        reset=args.reset
    )
    
    logger.info("Embedding pipeline finished")


if __name__ == "__main__":
    main()

