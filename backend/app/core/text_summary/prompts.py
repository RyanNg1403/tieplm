"""Text summarization task-specific prompts."""

SUMMARY_SYSTEM_PROMPT = """
You are a helpful AI assistant that creates concise summaries of video course content.
Synthesize information from multiple sources and provide a clear, structured summary.
"""

SUMMARY_USER_PROMPT_TEMPLATE = """
Based on the following context from the course videos, provide a concise summary about: {topic}

Context:
{context}

Summary:
"""

