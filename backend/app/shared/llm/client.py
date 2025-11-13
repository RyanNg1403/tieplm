"""LLM client with streaming support."""
import os
import json
from typing import AsyncGenerator, Dict, Any, Optional, List
from openai import OpenAI, AsyncOpenAI


class LLMClient:
    """
    OpenAI LLM client with streaming support for SSE.
    
    Supports both sync and async streaming for FastAPI SSE responses.
    """
    
    def __init__(
        self, 
        api_key: str = None,
        model: str = None,
        temperature: float = None,
        max_retries: int = None,
        timeout: int = None
    ):
        """
        Initialize LLM client.
        
        Args:
            api_key: OpenAI API key (default from env)
            model: Model name (default from env)
            temperature: Sampling temperature (default from env)
            max_retries: Max retry attempts (default from env)
            timeout: Request timeout in seconds (default from env)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        
        self.model = model or os.getenv("MODEL_NAME", "gpt-5-mini")
        # Note: gpt-5 models don't support temperature parameter
        self.temperature = None if self.model.startswith("gpt-5") else (temperature or float(os.getenv("LLM_TEMPERATURE", "1.0")))
        self.max_retries = max_retries or int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "60"))
        
        # Initialize OpenAI clients
        self.client = OpenAI(
            api_key=self.api_key,
            max_retries=self.max_retries,
            timeout=self.timeout
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            max_retries=self.max_retries,
            timeout=self.timeout
        )
    
    def generate(
        self, 
        prompt: str, 
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate text (non-streaming).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Use env var default if not specified
        if max_tokens is None:
            max_tokens = int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "3000"))
        
        # Build params (exclude temperature for gpt-5)
        params = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens
        }
        if self.temperature is not None:
            params["temperature"] = temperature or self.temperature
        
        response = self.client.chat.completions.create(**params)
        
        return response.choices[0].message.content
    
    async def generate_async(
        self, 
        prompt: str, 
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Generate text async (non-streaming).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Use env var default if not specified
        if max_tokens is None:
            max_tokens = int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "3000"))
        
        # Build params (exclude temperature for gpt-5)
        params = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens
        }
        if self.temperature is not None:
            params["temperature"] = temperature or self.temperature
        
        response = await self.async_client.chat.completions.create(**params)
        
        return response.choices[0].message.content
    
    async def stream(
        self, 
        prompt: str, 
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate text with streaming (async generator).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Optional temperature override
            max_tokens: Maximum tokens to generate
        
        Yields:
            Token strings as they're generated
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Use env var default if not specified
        if max_tokens is None:
            max_tokens = int(os.getenv("LLM_MAX_COMPLETION_TOKENS", "3000"))
        
        # Build params (exclude temperature for gpt-5)
        params = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "stream": True
        }
        if self.temperature is not None:
            params["temperature"] = temperature or self.temperature
        
        stream = await self.async_client.chat.completions.create(**params)
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def stream_with_sources(
        self,
        prompt: str,
        system_prompt: str = None,
        sources: List[Dict[str, Any]] = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate text with streaming + emit sources at the end.
        
        This is designed for SSE responses where we want to:
        1. Stream tokens as they're generated
        2. Send sources metadata at the end
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            sources: List of source references to send at the end
            temperature: Optional temperature override
            max_tokens: Maximum tokens to generate
        
        Yields:
            Dict events: {"type": "token"|"sources"|"done", "content": str, "sources": list}
        """
        # Stream tokens
        full_response = ""
        async for token in self.stream(prompt, system_prompt, temperature, max_tokens):
            full_response += token
            yield {
                "type": "token",
                "content": token
            }
        
        # Send sources at the end
        if sources:
            yield {
                "type": "sources",
                "sources": sources
            }
        
        # Send done signal
        yield {
            "type": "done",
            "content": full_response,
            "sources": sources or []
        }
    
    def build_rag_prompt(
        self,
        query: str,
        sources: List[Dict[str, Any]],
        task_prompt_template: str
    ) -> str:
        """
        Build RAG prompt with numbered sources.
        
        Args:
            query: User query
            sources: List of source chunks with metadata
            task_prompt_template: Task-specific prompt template with {sources} and {query} placeholders
        
        Returns:
            Formatted prompt with numbered sources
        """
        # Format sources with numbering
        formatted_sources = []
        for idx, source in enumerate(sources, start=1):
            metadata = source.get("metadata", {})
            video_title = metadata.get("video_title", "Unknown")
            start_time = metadata.get("start_time", 0)
            end_time = metadata.get("end_time", 0)
            text = metadata.get("text", "")
            
            # Format timestamp (MM:SS)
            start_min, start_sec = divmod(start_time, 60)
            end_min, end_sec = divmod(end_time, 60)
            timestamp = f"{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}"
            
            formatted_sources.append(
                f"[{idx}] Video: {video_title} ({timestamp})\n{text}"
            )
        
        sources_text = "\n\n".join(formatted_sources)
        
        # Fill in template
        prompt = task_prompt_template.format(
            sources=sources_text,
            query=query
        )
        
        return prompt


# Singleton instance
_llm_client = None

def get_llm_client() -> LLMClient:
    """Get singleton LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
