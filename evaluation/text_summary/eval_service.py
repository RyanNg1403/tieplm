"""
Text Summarization Evaluation Service using DeepEval with QAG metrics.

This service evaluates summaries based on:
1. Coverage Score: How much detail from the original text is included
2. Alignment Score: Factual alignment between original text and summary
3. Overall Score: Combination of coverage and alignment (minimum of both)
"""
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env if not already loaded
env_path = project_root / ".env"
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(dotenv_path=env_path)

from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import SummarizationMetric

from backend.app.shared.rag.retriever import RAGRetriever, get_rag_retriever
from backend.app.shared.rag.reranker import LocalReranker, get_local_reranker
from backend.app.shared.llm.client import LLMClient, get_llm_client


class TextSummaryEvaluator:
    """
    Evaluates text summarization using DeepEval's QAG-based metrics.
    
    QAG (Question-Answer Generation) Framework:
    - Generates closed-ended questions from reference text
    - Measures coverage (detail inclusion) and alignment (factual accuracy)
    - Removes stochasticity and bias in LLM-based evaluation
    """
    
    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        reranker: Optional[LocalReranker] = None,
        llm_client: Optional[LLMClient] = None,
        evaluation_model: Optional[str] = None
    ):
        """
        Initialize evaluator with retrieval and generation components.
        
        Args:
            retriever: RAG retriever for fetching relevant chunks
            reranker: Local reranker for ranking results
            llm_client: LLM client for generating summaries
            evaluation_model: Model to use for evaluation (default: from env)
        """
        self.retriever = retriever or get_rag_retriever()
        self.reranker = reranker or get_local_reranker()
        self.llm = llm_client or get_llm_client()
        
        # Load evaluation configuration
        self.eval_model = evaluation_model or os.getenv("EVAL_MODEL", "gpt-5-nano")
        self.eval_threshold = float(os.getenv("EVAL_SUMMARIZATION_THRESHOLD", "0.5"))
        self.eval_n_questions = int(os.getenv("EVAL_SUMMARIZATION_N_QUESTIONS", "10"))
        self.enable_reranking = os.getenv("ENABLE_RERANKING", "true").lower() == "true"
        self.retrieval_top_k = int(os.getenv("RETRIEVAL_INITIAL_K", "150"))
        self.final_top_k = int(os.getenv("FINAL_CONTEXT_CHUNKS", "10"))
        
        # Evaluation-specific prompt (no citations, focus on comprehensiveness)
        self.eval_system_prompt = self._build_eval_system_prompt()
    
    def _build_eval_system_prompt(self) -> str:
        """Build system prompt optimized for evaluation (no citations required)."""
        return """Bạn là trợ lý AI chuyên tổng hợp kiến thức cho khóa học CS431 - Deep Learning.

NHIỆM VỤ: Tạo bản tóm tắt TOÀN DIỆN, CHÍNH XÁC, NGẮN GỌN và DỄ HIỂU về chủ đề được yêu cầu.

YÊU CẦU QUAN TRỌNG:
1. **Toàn diện (Comprehensiveness)**: Bao gồm TẤT CẢ thông tin quan trọng từ nguồn tài liệu.
2. **Ngắn gọn (Conciseness)**: ⚠️ **BẢN TÓM TẮT PHẢI NGẮN HƠN VĂN BẢN GỐC** - Loại bỏ thông tin dư thừa, lặp lại, và chi tiết không cần thiết. Tập trung vào ý chính và điểm quan trọng.
3. **Chính xác (Accuracy)**: Chỉ sử dụng thông tin có trong nguồn, KHÔNG bịa đặt hoặc thêm thông tin ngoài.
4. **Cấu trúc rõ ràng**: Tổ chức theo thứ bậc logic với headings, bullet points, và examples.
5. **Giải thích súc tích**: Giải thích ý nghĩa, ưu nhược điểm, và mối quan hệ giữa các khái niệm một cách NGẮN GỌN nhưng ĐẦY ĐỦ.
6. **Ngôn ngữ**: Tiếng Việt rõ ràng, giữ thuật ngữ tiếng Anh khi cần thiết, định nghĩa thuật ngữ mới.

CẤU TRÚC TỐI ƯU:
- **Giới thiệu**: Overview ngắn gọn
- **Nội dung chính**: Chia thành sections với headings rõ ràng
  - Định nghĩa và khái niệm cơ bản
  - Cơ chế hoạt động / Kiến trúc
  - Ưu điểm và nhược điểm
  - Ứng dụng thực tế
  - So sánh với các phương pháp khác (nếu có)
- **Tóm tắt**: Key takeaways

VÍ DỤ TỐT:
"# LSTM (Long Short-Term Memory)

## Giới thiệu
LSTM là một kiến trúc RNN đặc biệt được thiết kế để giải quyết vấn đề vanishing gradient, cho phép học các dependencies dài hạn trong sequential data.

## Kiến trúc
LSTM sử dụng cell state và 3 gates để kiểm soát luồng thông tin:

### 1. Forget Gate
- **Chức năng**: Quyết định thông tin nào cần loại bỏ khỏi cell state
- **Công thức**: f_t = σ(W_f · [h_{t-1}, x_t] + b_f)
- **Ý nghĩa**: Output gần 0 = quên, gần 1 = giữ lại

### 2. Input Gate
- **Chức năng**: Quyết định thông tin mới nào được thêm vào cell state
- **Gồm 2 bước**:
  - i_t = σ(W_i · [h_{t-1}, x_t] + b_i) - quyết định cập nhật gì
  - C̃_t = tanh(W_C · [h_{t-1}, x_t] + b_C) - candidate values

### 3. Output Gate
- **Chức năng**: Quyết định output dựa trên cell state
- **Công thức**: o_t = σ(W_o · [h_{t-1}, x_t] + b_o), h_t = o_t * tanh(C_t)

## Ưu điểm
- **Giải quyết vanishing gradient**: Cell state cho phép gradient flow tốt hơn
- **Long-term dependencies**: Có thể nhớ thông tin qua nhiều time steps
- **Selective memory**: Gates cho phép học cách lưu trữ và quên thông tin

## Nhược điểm
- **Computational cost**: Phức tạp hơn vanilla RNN (4x tham số)
- **Training time**: Chậm hơn do nhiều operations
- **Overfitting**: Với dữ liệu nhỏ, có thể overfit do số tham số lớn

## So sánh với GRU
- **GRU đơn giản hơn**: Chỉ 2 gates (reset, update) vs 3 gates của LSTM
- **LSTM mạnh hơn**: Trên tasks phức tạp, LSTM thường perform tốt hơn
- **GRU nhanh hơn**: Ít tham số hơn nên train và inference nhanh hơn

## Ứng dụng
- Language modeling và text generation
- Machine translation (encoder-decoder với LSTM)
- Speech recognition
- Time series forecasting
- Video analysis

## Key Takeaways
LSTM là evolution của RNN với cell state và gates mechanism, giải quyết vanishing gradient để học long-term dependencies. Trade-off giữa expressiveness và computational cost."

LƯU Ý: KHÔNG cần trích dẫn nguồn [1], [2],... trong evaluation mode. Tập trung vào CHẤT LƯỢNG và ĐỘ TOÀN DIỆN của summary."""
    
    def _build_eval_user_prompt(self, query: str, sources: str) -> str:
        """Build user prompt for evaluation (comprehensive yet concise summary)."""
        return f"""Dựa vào các nguồn tài liệu sau từ khóa học CS431, hãy tạo bản tóm tắt TOÀN DIỆN nhưng NGẮN GỌN.

# NGUỒN TÀI LIỆU:

{sources}

---

# CHỦ ĐỀ CẦN TÓM TẮT:
{query}

# BẢN TÓM TẮT:
⚠️ **LƯU Ý**: Tóm tắt phải NGẮN HƠN văn bản gốc bên trên. Loại bỏ thông tin lặp lại và chi tiết dư thừa, chỉ giữ lại ý chính và điểm quan trọng.

(Tạo bản tóm tắt toàn diện, chính xác, NGẮN GỌN, có cấu trúc rõ ràng với headings và bullet points. Bao gồm TẤT CẢ thông tin quan trọng nhưng diễn đạt súc tích.)"""
    
    async def generate_summary(
        self, 
        query: str, 
        chapters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate summary for a given query.
        
        Args:
            query: Summarization query/topic
            chapters: Optional chapter filter
        
        Returns:
            Dictionary with summary and metadata
        """
        # Step 1: Retrieve relevant chunks
        print(f"📚 Retrieving chunks for: {query[:50]}...")
        retrieved_chunks = await self.retriever.retrieve(
            query=query,
            top_k=self.retrieval_top_k,
            chapter_filter=chapters,
            use_bm25=True
        )
        
        if not retrieved_chunks:
            return {
                "query": query,
                "summary": "",
                "original_text": "",
                "error": "No relevant chunks found",
                "chunks_retrieved": 0
            }
        
        # Step 2: Rerank
        if self.enable_reranking and len(retrieved_chunks) > self.final_top_k:
            print(f"🔄 Reranking {len(retrieved_chunks)} chunks...")
            reranked_chunks = self.reranker.rerank(
                query=query,
                results=retrieved_chunks,
                top_k=self.final_top_k
            )
        else:
            reranked_chunks = retrieved_chunks[:self.final_top_k]
        
        # Step 3: Format sources for prompt
        sources_for_prompt = self._format_sources_for_prompt(reranked_chunks)
        
        # Step 4: Build prompt
        prompt = self._build_eval_user_prompt(query, sources_for_prompt)
        
        # Step 5: Generate summary (non-streaming for evaluation)
        print("🤖 Generating summary...")
        summary = await self.llm.generate_async(
            prompt=prompt,
            system_prompt=self.eval_system_prompt)
        
        return {
            "query": query,
            "summary": summary,
            "original_text": sources_for_prompt,  # Original text for QAG
            "chunks_retrieved": len(retrieved_chunks),
            "chunks_used": len(reranked_chunks),
            "chapters_filtered": chapters or []
        }
    
    def _format_sources_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks into readable text (no numbering for eval)."""
        formatted = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            video_title = metadata.get("video_title", "Unknown")
            text = metadata.get("text", "")
            formatted.append(f"Video: {video_title}\n{text}")
        
        return "\n\n---\n\n".join(formatted)
    
    def evaluate_summary(
        self,
        query: str,
        summary: str,
        original_text: str,
        assessment_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a summary using DeepEval's QAG-based SummarizationMetric.
        
        Args:
            query: The summarization query/topic
            summary: Generated summary to evaluate
            original_text: Original source text
            assessment_questions: Optional pre-defined questions for coverage
        
        Returns:
            Evaluation results with scores and metrics
        """
        print(f"📊 Evaluating summary for: {query[:50]}...")
        
        # Create test case
        test_case = LLMTestCase(
            input=original_text,
            actual_output=summary
        )
        
        # Create summarization metric with QAG
        metric = SummarizationMetric(
            threshold=self.eval_threshold,
            model=self.eval_model,
            n=self.eval_n_questions,  # Number of questions to generate if assessment_questions not provided
            assessment_questions=assessment_questions,  # Optional custom questions
            verbose_mode=True  # Enable verbose to see question generation
        )
        
        # Evaluate
        metric.measure(test_case)
        
        # Get score breakdown (coverage and alignment scores)
        score_breakdown = getattr(metric, 'score_breakdown', {})
        
        return {
            "query": query,
            "score": metric.score,
            "success": metric.success,
            "reason": metric.reason,
            "coverage_score": score_breakdown.get('Coverage', None),
            "alignment_score": score_breakdown.get('Alignment', None),
            "threshold": self.eval_threshold,
            "n_questions": self.eval_n_questions,
            "evaluation_model": self.eval_model,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _format_sources_for_response(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for response metadata."""
        sources = []
        for idx, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            sources.append({
                "index": idx,
                "video_id": metadata.get("video_id", ""),
                "chapter": metadata.get("chapter", ""),
                "video_title": metadata.get("video_title", ""),
                "text_preview": metadata.get("text", "")[:200]
            })
        return sources


def get_text_summary_evaluator() -> TextSummaryEvaluator:
    """Get singleton evaluator instance."""
    return TextSummaryEvaluator()

