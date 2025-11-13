"""Embedding generation and contextual chunking for transcripts."""
import os
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI


class OpenAIEmbedder:
    """Generate embeddings using OpenAI's text-embedding model."""
    
    def __init__(self, api_key: str = None, model: str = None):
        """Initialize OpenAI embedder.
        
        Args:
            api_key: OpenAI API key. If None, will load from OPENAI_API_KEY env var.
            model: Embedding model name. If None, will load from EMBEDDING_MODEL_NAME env var.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY env var or pass api_key parameter.")
        
        self.model = model or os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
        self.client = OpenAI(api_key=self.api_key)
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Input text to embed.
        
        Returns:
            Embedding vector as list of floats.
        """
        response = self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of input texts to embed.
        
        Returns:
            List of embedding vectors.
        """
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]


class ContextualChunker:
    """
    Time-window chunking with contextual enrichment using LLM.
    
    Implements Anthropic's Contextual Retrieval approach:
    https://www.anthropic.com/engineering/contextual-retrieval
    """
    
    def __init__(
        self,
        chunk_duration: int = None,
        overlap_duration: int = None,
        context_token_limit: int = None,
        api_key: str = None,
        model_name: str = None
    ):
        """Initialize contextual chunker.
        
        Args:
            chunk_duration: Duration of each chunk in seconds. If None, reads from TIME_WINDOW env var (default 60).
            overlap_duration: Overlap between chunks in seconds. If None, reads from CHUNK_OVERLAP env var (default 10).
            context_token_limit: Max tokens for contextual prefix. If None, reads from CONTEXT_TOKEN_LIMIT env var (default 200).
            api_key: OpenAI API key. If None, will load from OPENAI_API_KEY env var.
            model_name: LLM model name. If None, reads from MODEL_NAME env var (default gpt-5-mini).
        """
        self.chunk_duration = chunk_duration or int(os.getenv("TIME_WINDOW", "60"))
        self.overlap_duration = overlap_duration or int(os.getenv("CHUNK_OVERLAP", "10"))
        self.context_token_limit = context_token_limit or int(os.getenv("CONTEXT_TOKEN_LIMIT", "200"))
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required.")
        
        self.model_name = model_name or os.getenv("MODEL_NAME", "gpt-5-mini")
        self.client = OpenAI(api_key=self.api_key)
    
    @staticmethod
    def extract_video_title(full_title: str) -> str:
        """Extract clean video title by removing prefix before '：' or ':'.
        
        Args:
            full_title: Full video title like "[CS431 - Chương 4] Part 1: Title"
        
        Returns:
            Clean title like "Title"
        """
        # Try Vietnamese colon first, then English colon
        if "：" in full_title:
            return full_title.split("：", 1)[1].strip()
        elif ":" in full_title:
            return full_title.split(":", 1)[1].strip()
        return full_title
    
    def create_time_chunks(self, transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create time-window chunks from transcript segments.
        
        Args:
            transcript: Transcript dict with 'segments' list.
        
        Returns:
            List of chunk dictionaries with start_time, end_time, and text.
        """
        segments = transcript.get("segments", [])
        if not segments:
            return []
        
        chunks = []
        current_chunk_start = 0
        
        while True:
            current_chunk_end = current_chunk_start + self.chunk_duration
            
            # Collect segments within this time window
            chunk_segments = []
            for seg in segments:
                seg_start = seg.get("start", 0)
                seg_end = seg.get("end", 0)
                
                # Include segment if it overlaps with current chunk window
                if seg_start < current_chunk_end and seg_end > current_chunk_start:
                    chunk_segments.append(seg)
            
            if not chunk_segments:
                break
            
            # Combine text from all segments in chunk
            chunk_text = " ".join([seg.get("text", "").strip() for seg in chunk_segments])
            
            # Actual start/end times based on included segments
            actual_start = min([seg.get("start", 0) for seg in chunk_segments])
            actual_end = max([seg.get("end", 0) for seg in chunk_segments])
            
            chunks.append({
                "start_time": actual_start,
                "end_time": actual_end,
                "text": chunk_text.strip()
            })
            
            # Move to next chunk with overlap
            current_chunk_start = current_chunk_end - self.overlap_duration
            
            # Stop if we've passed the last segment
            if current_chunk_start >= segments[-1].get("end", 0):
                break
        
        return chunks
    
    def generate_context(
        self,
        chunk: Dict[str, Any],
        prev_chunk: Optional[Dict[str, Any]],
        next_chunk: Optional[Dict[str, Any]],
        video_metadata: Dict[str, str]
    ) -> str:
        """Generate contextual information for a chunk using gpt-5-mini.
        
        Args:
            chunk: Current chunk dict with text, start_time, end_time.
            prev_chunk: Previous chunk (or None if first chunk).
            next_chunk: Next chunk (or None if last chunk).
            video_metadata: Dict with 'chapter', 'title', 'url'.
        
        Returns:
            Contextual prefix text (max context_token_limit tokens).
        """
        chapter = video_metadata.get("chapter", "")
        full_title = video_metadata.get("title", "")
        clean_title = self.extract_video_title(full_title)
        
        # Build context about surrounding chunks
        prev_summary = ""
        if prev_chunk:
            prev_text = prev_chunk.get("text", "")
            prev_summary = f"\nPrevious chunk (ends at {prev_chunk.get('end_time', 0):.1f}s): {prev_text}..."
        
        next_summary = ""
        if next_chunk:
            next_text = next_chunk.get("text", "")
            next_summary = f"\nNext chunk (starts at {next_chunk.get('start_time', 0):.1f}s): {next_text}..."
        
        # Prompt for gpt-5-mini to generate concise context with Vietnamese examples
        prompt = f"""Bạn đang phân tích transcript video bài giảng. Tạo context ngắn gọn (tối đa {self.context_token_limit} tokens) cho đoạn này.

QUAN TRỌNG: HÃY NGẮN GỌN VÀ XÚC TÍCH! Không viết dài dòng.

Thông tin Video:
- Chương: {chapter}
- Video: {clean_title}
- Timestamp: {chunk.get('start_time', 0):.1f}s đến {chunk.get('end_time', 0):.1f}s

Nội dung chunk:
{chunk.get('text', '')}
{prev_summary}
{next_summary}

VÍ DỤ OUTPUT MONG MUỐN (NGẮN GỌN):

Ví dụ 1:
Input: [Chunk về cấu trúc LSTM với forget gate, input gate...]
Output: "Chương 8, Part 1: Mạng LSTM - Giải thích cấu trúc cell LSTM với forget gate và input gate, cách giải quyết vanishing gradient. Tiếp theo phần giới thiệu RNN."

Ví dụ 2:
Input: [Chunk về Word2Vec skip-gram model...]
Output: "Chương 6, Part 4: Mô hình Word2Vec - Trình bày skip-gram model, cách dự đoán context từ target word. Trước đó đã giới thiệu word embeddings."

Ví dụ 3:
Input: [Chunk về backpropagation trong CNN...]
Output: "Chương 5, Part 2: CNN và backpropagation - Tính gradient cho convolutional layers, pooling layers. Liên quan đến phần trước về forward pass."

Tạo context NGẮN GỌN tương tự (max {self.context_token_limit} tokens) cho chunk trên. Tập trung vào chủ đề chính và ngữ cảnh."""

        # Retry logic: try up to 3 times with increasing token limits (+100 each time)
        max_retries = 3
        for attempt in range(max_retries):
            current_token_limit = self.context_token_limit + (attempt * 100)
            
            try:
                if attempt > 0:
                    print(f"  Retry {attempt}/{max_retries-1}: Increasing token limit to {current_token_limit}")
                
                # gpt-5-mini: use minimal reasoning effort for simple contextual summaries (fastest + cheapest)
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "Bạn là trợ lý tạo context ngắn gọn cho các đoạn transcript bài giảng."},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=current_token_limit,
                    reasoning_effort="minimal"  # Hardcoded for gpt-5-mini
                )
                
                context = response.choices[0].message.content.strip()
                return context
            
            except Exception as e:
                error_str = str(e)
                # Check if it's a token limit error
                if "max_tokens" in error_str or "output limit" in error_str or "max_completion_tokens" in error_str:
                    print(f"  Attempt {attempt + 1}/{max_retries} failed: Token limit exceeded with {current_token_limit} tokens")
                    if attempt < max_retries - 1:
                        continue  # Retry with more tokens
                    else:
                        print(f"  All retries exhausted. Using fallback context.")
                else:
                    # Other error, don't retry
                    print(f"Warning: Failed to generate context with gpt-5-mini: {e}")
                    break
        
        # Fallback to simple context if all retries fail
        return f"Chương {chapter}, Video: {clean_title}, Timestamp: {chunk.get('start_time', 0):.1f}s-{chunk.get('end_time', 0):.1f}s"
    
    def create_contextualized_chunks(
        self,
        transcript: Dict[str, Any],
        video_metadata: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Create time-window chunks with contextual enrichment.
        
        Args:
            transcript: Transcript dict from Whisper output.
            video_metadata: Dict with 'chapter', 'title', 'url'.
        
        Returns:
            List of chunks with 'text', 'contextualized_text', 'start_time', 'end_time', 'metadata'.
        """
        # Step 1: Create time-based chunks
        chunks = self.create_time_chunks(transcript)
        
        if not chunks:
            return []
        
        # Step 2: Generate context for each chunk
        contextualized_chunks = []
        for i, chunk in enumerate(chunks):
            prev_chunk = chunks[i - 1] if i > 0 else None
            next_chunk = chunks[i + 1] if i < len(chunks) - 1 else None
            
            # Generate contextual prefix
            context = self.generate_context(chunk, prev_chunk, next_chunk, video_metadata)
            
            # Combine context with original text
            contextualized_text = f"{context}\n\n{chunk['text']}"
            
            contextualized_chunks.append({
                "text": chunk["text"],
                "contextualized_text": contextualized_text,
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "metadata": {
                    "chapter": video_metadata.get("chapter", ""),
                    "video_title": self.extract_video_title(video_metadata.get("title", "")),
                    "video_url": video_metadata.get("url", ""),
                    "full_title": video_metadata.get("title", "")
                }
            })
        
        return contextualized_chunks

