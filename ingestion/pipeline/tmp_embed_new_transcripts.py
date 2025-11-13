#!/usr/bin/env python3
"""
Temporary script to embed only newly added transcripts.

This script uses the exact same logic as embed_videos.py but only processes
the specific transcripts that were recently added.
"""
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
    
    log_path = log_dir / (log_file or "embedding_new_transcripts.log")
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


# List of newly added transcript files
NEW_TRANSCRIPTS = [
    "[CS431 - Chương 2] Part 1-Mô hình học tổng quát.json",
    "[CS431 - Chương 2] Part 2a_1-Mô hình hồi quy tuyến tính (Linear Regression).json",
    "[CS431 - Chương 2] Part 2a_2-Mô hình hồi quy tuyến tính (Linear Regression).json",
    "[CS431 - Chương 2] Part 2b_1-Cài đặt mô hình linear regression.json",
    "[CS431 - Chương 2] Part 2b_2-Cài đặt mô hình linear regression.json",
    "[CS431 - Chương 2] Part 2b_3-Cài đặt mô hình linear regression.json",
    "[CS431 - Chương 2] Part 3a-Mô hình hồi quy luận lý (Logistic Regression).json",
    "[CS431 - Chương 2] Part 3b_1-Cài đặt mô hình logistic regression.json",
    "[CS431 - Chương 2] Part 3b_2-Cài đặt mô hình logistic regression.json",
    "[CS431 - Chương 2] Part 4_3-Kiến trúc Transformer： Bộ Encoder.json",
    "[CS431 - Chương 2] Part 4a-Mô hình hồi quy Softmax (SoftmaxRegression).json",
    "[CS431 - Chương 2] Part 4b-Cài đặt mô hình softmax regression.json",
    "[CS431 - Chương 2] Part 5a-Mạng neural Network (Neural Network).json",
    "[CS431 - Chương 2] Part 5b_1-Cài đặt mạng neural network.json",
    "[CS431 - Chương 2] Part 5b_2-Cài đặt mạng neural network.json",
    "[CS431 - Chương 3] Part 1-Giới thiệu mạng CNN.json",
    "[CS431 - Chương 3] Part 2_1-Một số thành phần của mạng CNN.json",
    "[CS431 - Chương 3] Part 2_2-Một số thành phần của mạng CNN.json",
    "[CS431 - Chương 3] Part 3_1-Cài đặt mạng CNN.json",
    "[CS431 - Chương 3] Part 3_2-Cài đặt mạng CNN.json",
    "[CS431 - Chương 3] Part 3_3-Cài đặt mạng CNN.json",
    "[CS431 - Chương 3] Part 4_1-Trực quan hóa mạng CNN.json",
    "[CS431 - Chương 3] Part 4_2-Trực quan hóa mạng CNN.json",
]


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
    
    def run_for_new_transcripts(self):
        """Run the embedding pipeline for newly added transcripts only."""
        # Ensure Qdrant collection exists
        try:
            self.vector_db.create_collection(recreate=False)
        except Exception as e:
            self.logger.error(f"Failed to create Qdrant collection: {e}")
            return
        
        # Get all video mappings
        self.logger.info("Loading video mappings...")
        all_mappings = get_all_video_mappings(str(self.transcripts_dir))
        
        # Filter to only new transcripts
        mappings_to_process = []
        for mapping in all_mappings:
            transcript_filename = Path(mapping["transcript_path"]).name
            if transcript_filename in NEW_TRANSCRIPTS:
                mappings_to_process.append(mapping)
        
        if not mappings_to_process:
            self.logger.warning("No matching new transcripts found.")
            self.logger.info(f"Looking for transcripts in: {self.transcripts_dir}")
            self.logger.info(f"Expected {len(NEW_TRANSCRIPTS)} files")
            return
        
        self.logger.info(f"Found {len(mappings_to_process)} new transcripts to process")
        
        # Process each video with progress bar
        total_chunks = 0
        for mapping in tqdm(mappings_to_process, desc="Embedding new transcripts"):
            chunks_count = self.process_video(mapping)
            total_chunks += chunks_count
        
        self.logger.info(f"Pipeline complete! Embedded {total_chunks} total chunks from {len(mappings_to_process)} new videos.")


def main():
    """Main entry point."""
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logger = setup_logging()
    logger.info("=" * 80)
    logger.info("Starting temporary embedding pipeline for new transcripts")
    logger.info("=" * 80)
    logger.info(f"Processing {len(NEW_TRANSCRIPTS)} new transcript files")
    
    # Create pipeline
    transcripts_dir = Path(__file__).parent.parent / "transcripts"
    pipeline = EmbeddingPipeline(transcripts_dir=str(transcripts_dir))
    
    # Run pipeline for new transcripts only
    pipeline.run_for_new_transcripts()
    
    logger.info("=" * 80)
    logger.info("Embedding pipeline finished")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

