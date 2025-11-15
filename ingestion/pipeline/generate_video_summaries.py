#!/usr/bin/env python3
"""
Video Summary Generation Pipeline

This script generates comprehensive summaries for all videos in the database
and saves them to a JSON file for bulk import into PostgreSQL.

Usage:
    python generate_video_summaries.py --all
    python generate_video_summaries.py --chapters "Chương 1" "Chương 2"
    python generate_video_summaries.py --video-id "Chương 1_xyz123"
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.shared.database.postgres import PostgresClient
from backend.app.shared.database.models import Video, Chunk
from backend.app.shared.llm.client import LLMClient, get_llm_client
from backend.app.core.video_summary.prompts import (
    VIDEO_SUMMARY_SYSTEM_PROMPT,
    VIDEO_SUMMARY_USER_PROMPT_TEMPLATE,
)


# Set up logging
def setup_logging():
    """Set up logging configuration."""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_path = log_dir / "video_summary_generation.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


class VideoSummaryGenerator:
    """Generator for pre-computing video summaries."""

    def __init__(self, output_dir: str):
        """
        Initialize generator.

        Args:
            output_dir: Directory to save video_summaries.json
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.postgres = PostgresClient()
        self.llm = get_llm_client()
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initialized VideoSummaryGenerator")

    def _format_timestamp(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def _get_video_chunks(self, video_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a video, sorted by start_time."""
        with self.postgres.session_scope() as session:
            chunks = session.query(Chunk).filter(
                Chunk.video_id == video_id
            ).order_by(Chunk.start_time).all()

            result = []
            for chunk in chunks:
                result.append({
                    "id": chunk.qdrant_id,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "text": chunk.text,
                    "video_id": chunk.video_id,
                })
            return result

    def _format_sources_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks as markdown sources for prompt."""
        sources_text = ""
        for idx, chunk in enumerate(chunks, 1):
            start_time_str = self._format_timestamp(chunk["start_time"])
            end_time_str = self._format_timestamp(chunk["end_time"])

            sources_text += f"""[{idx}] **[{start_time_str} - {end_time_str}]**
{chunk["text"]}

"""
        return sources_text

    def _format_sources_for_json(self, chunks: List[Dict[str, Any]], video: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format chunks as source references for JSON export."""
        sources = []
        for idx, chunk in enumerate(chunks, 1):
            sources.append({
                "index": idx,
                "video_id": chunk["video_id"],
                "chapter": video["chapter"],
                "video_title": video["title"],
                "video_url": video["url"],
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "text": chunk["text"],
            })
        return sources

    async def generate_summary(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary for a single video.

        Args:
            video: Video dictionary with id, title, chapter, duration

        Returns:
            Dictionary with video_id, summary, and sources
        """
        video_id = video["id"]
        self.logger.info(f"📽️  Generating summary for: {video['title']}")

        # Get all chunks for this video
        chunks = self._get_video_chunks(video_id)

        if not chunks:
            self.logger.warning(f"⚠️  No chunks found for video {video_id}")
            return None

        self.logger.info(f"✅ Retrieved {len(chunks)} chunks")

        # Format sources and build prompt
        sources_for_prompt = self._format_sources_for_prompt(chunks)
        prompt = VIDEO_SUMMARY_USER_PROMPT_TEMPLATE.format(
            video_title=video["title"],
            chapter=video["chapter"],
            duration=video["duration"],
            sources=sources_for_prompt
        )

        # Generate summary (non-streaming for batch generation)
        self.logger.info("🤖 Generating summary with LLM...")
        summary = await self.llm.generate_async(
            prompt=prompt,
            system_prompt=VIDEO_SUMMARY_SYSTEM_PROMPT,
            max_tokens=10000  # Higher limit for comprehensive video summaries
        )

        # Format sources for JSON
        sources_for_json = self._format_sources_for_json(chunks, video)

        self.logger.info(f"✅ Summary generated ({len(summary)} chars)")

        return {
            "video_id": video_id,
            "summary": summary,
            "sources": sources_for_json
        }

    async def generate_all(
        self,
        chapters: List[str] = None,
        video_ids: List[str] = None,
        process_all: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Generate summaries for multiple videos.

        Args:
            chapters: List of chapters to process
            video_ids: List of specific video IDs to process
            process_all: If True, process all videos

        Returns:
            List of summary dictionaries
        """
        # Get videos from database
        with self.postgres.session_scope() as session:
            query = session.query(Video).order_by(Video.chapter, Video.title)

            if video_ids:
                video_objs = query.filter(Video.id.in_(video_ids)).all()
            elif chapters:
                video_objs = query.filter(Video.chapter.in_(chapters)).all()
            elif process_all:
                video_objs = query.all()
            else:
                self.logger.error("No videos specified. Use --all, --chapters, or --video-id.")
                return []

            # Convert to dicts to avoid DetachedInstanceError
            videos = []
            for v in video_objs:
                videos.append({
                    "id": v.id,
                    "chapter": v.chapter,
                    "title": v.title,
                    "url": v.url,
                    "duration": v.duration or 0
                })

        if not videos:
            self.logger.warning("No videos found matching criteria")
            return []

        self.logger.info(f"🚀 Generating summaries for {len(videos)} videos")

        # Generate summaries and save incrementally
        summaries = []
        for i, video in enumerate(videos, 1):
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"Progress: {i}/{len(videos)}")
            self.logger.info(f"{'='*80}")

            try:
                summary_data = await self.generate_summary(video)
                if summary_data:
                    summaries.append(summary_data)

                    # Save incrementally after each summary
                    self.save_to_json(summaries)
                    self.logger.info(f"💾 Saved progress: {len(summaries)}/{len(videos)} summaries")

            except Exception as e:
                self.logger.error(f"❌ Failed to generate summary for {video['id']}: {e}")
                import traceback
                traceback.print_exc()
                continue

        self.logger.info(f"\n✅ Generated {len(summaries)} summaries")
        return summaries

    def save_to_json(self, summaries: List[Dict[str, Any]], filename: str = "video_summaries.json"):
        """
        Save summaries to JSON file.

        Args:
            summaries: List of summary dictionaries
            filename: Output filename
        """
        output_path = self.output_dir / filename

        data = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_summaries": len(summaries),
            "summaries": summaries
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"💾 Saved summaries to: {output_path}")
        return output_path


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate video summaries and save to JSON"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all videos"
    )

    parser.add_argument(
        "--chapters",
        type=str,
        nargs="+",
        help="Process specific chapters (e.g., 'Chương 1' 'Chương 2')"
    )

    parser.add_argument(
        "--video-id",
        type=str,
        nargs="+",
        help="Process specific video IDs"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="./video_summaries",
        help="Output directory for JSON file (default: ./video_summaries)"
    )

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Set up logging
    logger = setup_logging()
    logger.info("Starting video summary generation pipeline")

    # Create generator
    generator = VideoSummaryGenerator(output_dir=args.output_dir)

    # Generate summaries (saves incrementally during generation)
    summaries = await generator.generate_all(
        chapters=args.chapters,
        video_ids=args.video_id,
        process_all=args.all
    )

    if summaries:
        output_path = generator.output_dir / "video_summaries.json"
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ Pipeline complete!")
        logger.info(f"📄 Generated {len(summaries)} summaries")
        logger.info(f"💾 Saved incrementally to: {output_path}")
        logger.info(f"{'='*80}")
    else:
        logger.error("No summaries generated")

    logger.info("Video summary generation pipeline finished")


if __name__ == "__main__":
    asyncio.run(main())
