"""Video summarization service - orchestration logic."""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from ...shared.rag.retriever import RAGRetriever, get_rag_retriever
from ...shared.rag.reranker import LocalReranker, get_local_reranker
from ...shared.llm.client import LLMClient, get_llm_client
from ...shared.database.postgres import PostgresClient, get_postgres_client
from ...shared.database.models import Video, Chunk, VideoSummary

from .prompts import (
    VIDEO_SUMMARY_SYSTEM_PROMPT,
    VIDEO_SUMMARY_USER_PROMPT_TEMPLATE,
)


class VideoSummaryService:
    """
    Service for video summarization using RAG pipeline.
    
    Pipeline:
    1. Get video metadata (title, chapter, duration)
    2. Retrieve all chunks for the video
    3. Format chunks as numbered sources with timestamps
    4. Build prompt with video info and chunks
    5. Stream LLM response
    6. Save to chat history
    """
    
    def __init__(
        self,
        retriever: RAGRetriever = None,
        reranker: LocalReranker = None,
        llm_client: LLMClient = None,
        postgres: PostgresClient = None
    ):
        self.retriever = retriever or get_rag_retriever()
        self.reranker = reranker or get_local_reranker()
        self.llm = llm_client or get_llm_client()
        self.postgres = postgres or get_postgres_client()
    
    async def summarize_video(
        self,
        video_id: str,
        regenerate: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Summarize a specific video with streaming response.

        Args:
            video_id: ID of video to summarize
            regenerate: If True, regenerate summary even if it exists

        Yields:
            Dict events for SSE:
            - {"type": "token", "content": str}
            - {"type": "sources", "sources": list}
            - {"type": "done", "content": str, "sources": list}
        """
        # Step 1: Check if pre-computed summary exists
        with self.postgres.session_scope() as session:
            video = session.query(Video).filter(Video.id == video_id).first()
            if not video:
                yield {
                    "type": "error",
                    "content": f"Video với ID {video_id} không tồn tại."
                }
                return

            # Copy video attributes
            video_title = video.title
            video_chapter = video.chapter
            video_duration = video.duration or 0

            # Check for existing summary
            existing_summary = session.query(VideoSummary).filter(
                VideoSummary.video_id == video_id
            ).first()

            if existing_summary and not regenerate:
                # Return pre-computed summary with word-by-word streaming
                print(f"📽️  Streaming pre-computed summary for: {video_title}")

                summary_text = existing_summary.summary
                sources = existing_summary.sources or []

                # Stream word-by-word
                async for event in self._stream_precomputed_summary(summary_text, sources):
                    yield event

                print("✅ Pre-computed summary streamed")
                return

        print(f"📽️  Generating new summary for: {video_title}")

        # Step 2: Retrieve all chunks for this video (sorted by time)
        retrieved_chunks = await self._get_video_chunks(video_id)

        if not retrieved_chunks:
            yield {
                "type": "error",
                "content": f"Không tìm thấy chunks cho video {video_title}."
            }
            return

        print(f"✅ Retrieved {len(retrieved_chunks)} chunks from video")

        # Step 3: Format sources for prompt and response
        sources_for_prompt = self._format_sources_for_prompt(retrieved_chunks)
        sources_for_response = self._format_sources_for_response(retrieved_chunks)

        # Step 4: Build prompt with video metadata
        prompt = VIDEO_SUMMARY_USER_PROMPT_TEMPLATE.format(
            video_title=video_title,
            chapter=video_chapter,
            duration=video_duration,
            sources=sources_for_prompt
        )

        # Step 5: Stream LLM response
        print("🤖 Generating video summary with LLM...")
        full_response = ""
        async for event in self.llm.stream_with_sources(
            prompt=prompt,
            system_prompt=VIDEO_SUMMARY_SYSTEM_PROMPT,
            sources=sources_for_response
        ):
            if event["type"] == "token":
                full_response += event["content"]

            yield event

        # Step 6: Save to VideoSummary table (upsert)
        await self._save_summary(
            video_id=video_id,
            summary=full_response,
            sources=sources_for_response
        )

        print("✅ Video summary generated and saved")
    
    async def _get_video_chunks(self, video_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a video, sorted by start_time."""
        with self.postgres.session_scope() as session:
            chunks = session.query(Chunk).filter(
                Chunk.video_id == video_id
            ).order_by(Chunk.start_time).all()
            
            # Convert to dicts to avoid DetachedInstanceError
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
    
    def _format_sources_for_response(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format chunks as source references for response/citations."""
        sources = []
        
        # Get video info for metadata (we need video_id from chunks)
        video_id = chunks[0]["video_id"] if chunks else None
        if not video_id:
            return sources
        
        with self.postgres.session_scope() as session:
            video = session.query(Video).filter(Video.id == video_id).first()
            
            for idx, chunk in enumerate(chunks, 1):
                sources.append({
                    "index": idx,
                    "video_id": chunk["video_id"],
                    "chapter": video.chapter if video else "",
                    "video_title": video.title if video else "",
                    "video_url": video.url if video else "",
                    "start_time": chunk["start_time"],
                    "end_time": chunk["end_time"],
                    "text": chunk["text"],
                })
        
        return sources
    
    def _format_timestamp(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    async def _stream_precomputed_summary(
        self,
        summary: str,
        sources: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream pre-computed summary chunk-by-chunk for faster streaming.

        Args:
            summary: Pre-computed summary text
            sources: List of source references

        Yields:
            SSE events with tokens and sources
        """
        # Split summary into chunks (e.g., 50 characters per chunk)
        chunk_size = 50  # Adjust this value for desired speed
        chunks = [summary[i:i + chunk_size] for i in range(0, len(summary), chunk_size)]

        # Stream chunks one by one
        for chunk in chunks:
            yield {
                "type": "token",
                "content": chunk
            }

            # Small delay between chunks for smoother streaming
            await asyncio.sleep(0.05)  # 50ms delay between chunks

        # Send sources after all tokens
        yield {
            "type": "sources",
            "sources": sources
        }

        # Send done event
        yield {
            "type": "done",
            "content": summary,
            "sources": sources
        }

    async def _save_summary(
        self,
        video_id: str,
        summary: str,
        sources: List[Dict[str, Any]]
    ) -> None:
        """
        Save or update video summary in database.

        Args:
            video_id: ID of the video
            summary: Generated summary text
            sources: List of source references
        """
        with self.postgres.session_scope() as session:
            # Check if summary already exists
            existing = session.query(VideoSummary).filter(
                VideoSummary.video_id == video_id
            ).first()

            if existing:
                # Update existing summary
                existing.summary = summary
                existing.sources = sources
                existing.updated_at = datetime.utcnow()
                print(f"✅ Updated existing summary for video {video_id}")
            else:
                # Create new summary
                new_summary = VideoSummary(
                    video_id=video_id,
                    summary=summary,
                    sources=sources,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(new_summary)
                print(f"✅ Created new summary for video {video_id}")

            session.commit()


def get_video_summary_service() -> VideoSummaryService:
    """Factory function for dependency injection."""
    return VideoSummaryService()

