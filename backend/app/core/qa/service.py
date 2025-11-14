"""Q&A service - orchestration logic."""
import os
import uuid
from typing import AsyncGenerator, Dict, Any, List, Optional
from datetime import datetime

from ...shared.rag.retriever import RAGRetriever, get_rag_retriever
from ...shared.rag.reranker import LocalReranker, get_local_reranker
from ...shared.llm.client import LLMClient, get_llm_client
from ...shared.database.postgres import PostgresClient, get_postgres_client
from ...shared.database.models import ChatSession, ChatMessage

from .prompts import (
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT_TEMPLATE,
    FOLLOWUP_QA_PROMPT_TEMPLATE
)


class QAService:
    """
    Service for Q&A using RAG pipeline.
    
    Pipeline:
    1. Retrieve top-K chunks (vector + BM25)
    2. Rerank with cross-encoder
    3. Build prompt with numbered sources
    4. Stream LLM response
    5. Save to chat history
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
        
        # Load configuration
        self.enable_reranking = os.getenv("ENABLE_RERANKING", "true").lower() == "true"
        self.retrieval_top_k = int(os.getenv("RETRIEVAL_INITIAL_K", "150"))
        self.final_top_k = int(os.getenv("FINAL_CONTEXT_CHUNKS", "10"))
    
    async def answer(
        self,
        query: str,
        chapters: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Answer a question with streaming response.
        
        Args:
            query: User question
            chapters: Optional list of chapters to filter
            session_id: Optional existing session ID (for followup), otherwise creates new
        
        Yields:
            Dict events for SSE:
            - {"type": "token", "content": str}
            - {"type": "sources", "sources": list}
            - {"type": "done", "content": str, "sources": list, "session_id": str}
        """
        # Step 0: Create or get session BEFORE streaming
        created_session_id = await self._create_or_get_session(
            session_id=session_id,
            query=query
        )
        
        # Step 1: Retrieve relevant chunks
        print(f"📚 Retrieving chunks for question: {query[:50]}...")
        retrieved_chunks = await self.retriever.retrieve(
            query=query,
            top_k=self.retrieval_top_k,
            chapter_filter=chapters,
            use_bm25=True
        )
        print(f"✅ Retrieved {len(retrieved_chunks)} chunks")
        
        if not retrieved_chunks:
            # No results found
            yield {
                "type": "error",
                "content": "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
            }
            return
        
        # Step 2: Rerank (if enabled)
        if self.enable_reranking and len(retrieved_chunks) > self.final_top_k:
            print(f"🔄 Reranking {len(retrieved_chunks)} chunks...")
            reranked_chunks = self.reranker.rerank(
                query=query,
                results=retrieved_chunks,
                top_k=self.final_top_k
            )
            print(f"✅ Reranked to top-{len(reranked_chunks)} chunks")
        else:
            reranked_chunks = retrieved_chunks[:self.final_top_k]
        
        # Step 3: Format sources for prompt and response
        sources_for_prompt = self._format_sources_for_prompt(reranked_chunks)
        sources_for_response = self._format_sources_for_response(reranked_chunks)
        
        # Step 4: Build prompt
        prompt = QA_USER_PROMPT_TEMPLATE.format(
            query=query,
            sources=sources_for_prompt
        )
        
        # Step 5: Stream LLM response
        print("🤖 Generating answer with LLM...")
        full_response = ""
        async for event in self.llm.stream_with_sources(
            prompt=prompt,
            system_prompt=QA_SYSTEM_PROMPT,
            sources=sources_for_response
        ):
            if event["type"] == "token":
                full_response += event["content"]
            
            # Add session_id to "done" event (now guaranteed to be set)
            if event["type"] == "done":
                event["session_id"] = created_session_id
            
            yield event
        
        # Step 6: Save messages to database (session already exists)
        await self._save_messages(
            query=query,
            response=full_response,
            sources=sources_for_response,
            session_id=created_session_id
        )
        
        print("✅ Answer generated and saved")
    
    async def followup(
        self,
        session_id: str,
        query: str,
        chapters: Optional[List[str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle followup question in existing session.
        
        Args:
            session_id: Existing session ID
            query: Followup question
            chapters: Optional chapter filter
        
        Yields:
            SSE events
        """
        # Step 1: Retrieve conversation history
        history = await self._get_session_history(session_id)
        
        # Step 2: Retrieve new chunks for followup
        retrieved_chunks = await self.retriever.retrieve(
            query=query,
            top_k=self.retrieval_top_k,
            chapter_filter=chapters,
            use_bm25=True
        )
        
        if not retrieved_chunks:
            yield {
                "type": "error",
                "content": "Không tìm thấy thông tin liên quan."
            }
            return
        
        # Step 3: Rerank
        if self.enable_reranking and len(retrieved_chunks) > self.final_top_k:
            reranked_chunks = self.reranker.rerank(
                query=query,
                results=retrieved_chunks,
                top_k=self.final_top_k
            )
        else:
            reranked_chunks = retrieved_chunks[:self.final_top_k]
        
        # Step 4: Format sources and build prompt
        sources_for_prompt = self._format_sources_for_prompt(reranked_chunks)
        sources_for_response = self._format_sources_for_response(reranked_chunks)
        
        prompt = FOLLOWUP_QA_PROMPT_TEMPLATE.format(
            history=history,
            sources=sources_for_prompt,
            query=query
        )
        
        # Step 5: Stream response
        full_response = ""
        async for event in self.llm.stream_with_sources(
            prompt=prompt,
            system_prompt=QA_SYSTEM_PROMPT,
            sources=sources_for_response
        ):
            if event["type"] == "token":
                full_response += event["content"]
            
            # Add session_id to "done" event for consistency
            if event["type"] == "done":
                event["session_id"] = session_id
            
            yield event
        
        # Step 6: Save messages to database
        await self._save_messages(
            query=query,
            response=full_response,
            sources=sources_for_response,
            session_id=session_id
        )
    
    def _format_sources_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Format sources with numbering for LLM prompt."""
        formatted = []
        for idx, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            video_title = metadata.get("video_title", "Unknown")
            start_time = metadata.get("start_time", 0)
            end_time = metadata.get("end_time", 0)
            text = metadata.get("text", "")
            
            # Format timestamp
            start_min, start_sec = divmod(start_time, 60)
            end_min, end_sec = divmod(end_time, 60)
            timestamp = f"{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}"
            
            formatted.append(
                f"[{idx}] Video: {video_title} ({timestamp})\n{text}"
            )
        
        return "\n\n".join(formatted)
    
    def _format_sources_for_response(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for frontend response."""
        sources = []
        for idx, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            sources.append({
                "index": idx,
                "video_id": metadata.get("video_id", ""),
                "chapter": metadata.get("chapter", ""),
                "video_title": metadata.get("video_title", ""),
                "video_url": metadata.get("video_url", ""),
                "start_time": metadata.get("start_time", 0),
                "end_time": metadata.get("end_time", 0),
                "text": metadata.get("text", ""),
                "score": chunk.get("rerank_score", chunk.get("rrf_score", chunk.get("score", 0)))
            })
        return sources
    
    async def _create_or_get_session(
        self,
        session_id: Optional[str],
        query: str
    ) -> str:
        """
        Create new session or validate existing one BEFORE streaming.
        
        Returns:
            session_id (str): ID of created or validated session
        """
        with self.postgres.session_scope() as session:
            if session_id:
                # Validate existing session
                chat_session = session.query(ChatSession).filter_by(id=session_id).first()
                if not chat_session:
                    raise ValueError(f"Session {session_id} not found")
                
                # Update timestamp
                chat_session.updated_at = datetime.utcnow()
                return chat_session.id
            else:
                # Create new session
                new_session = ChatSession(
                    id=str(uuid.uuid4()),
                    task_type="qa",
                    title=query[:100],  # Use first 100 chars of query as title
                    user_id="default_user"
                )
                session.add(new_session)
                session.commit()
                return new_session.id
    
    async def _save_messages(
        self,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        session_id: str
    ):
        """Save user and assistant messages to existing session."""
        with self.postgres.session_scope() as session:
            # Save user message
            user_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=query
            )
            session.add(user_message)
            
            # Save assistant message with sources
            assistant_message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=response,
                sources=sources  # JSON column
            )
            session.add(assistant_message)
    
    async def _get_session_history(self, session_id: str) -> str:
        """Get conversation history as formatted string."""
        with self.postgres.session_scope() as session:
            messages = session.query(ChatMessage).filter_by(
                session_id=session_id
            ).order_by(ChatMessage.created_at).all()
            
            history_lines = []
            for msg in messages:
                role = "Người dùng" if msg.role == "user" else "Trợ lý AI"
                history_lines.append(f"{role}: {msg.content[:200]}")  # Truncate for context
            
            return "\n\n".join(history_lines)


# Singleton instance
_qa_service = None

def get_qa_service() -> QAService:
    """Get singleton Q&A service."""
    global _qa_service
    if _qa_service is None:
        _qa_service = QAService()
    return _qa_service

