"""Q&A task-specific prompts."""

QA_SYSTEM_PROMPT = """
You are a helpful AI assistant for a video course.
Answer questions based on the provided context from video transcripts.
Always cite video sources with timestamps.
"""

QA_USER_PROMPT_TEMPLATE = """
Based on the following context from the course videos, please answer the question.

Context:
{context}

Question: {question}

Answer:
"""

