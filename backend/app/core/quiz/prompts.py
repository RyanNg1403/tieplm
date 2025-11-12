"""Quiz generation task-specific prompts."""

QUIZ_SYSTEM_PROMPT = """
You are a helpful AI assistant that generates educational quiz questions.
Create questions that test understanding of the video content.
Include the exact timestamp where the answer can be found.
"""

MCQ_GENERATION_PROMPT_TEMPLATE = """
Based on the following video content, generate multiple choice questions (MCQs).

Video Content:
{transcript}

Generate {num_questions} MCQ questions with 4 options each.
For each question, provide:
1. The question
2. Four options (A, B, C, D)
3. The correct answer
4. The timestamp in the video where this content is discussed

Format as JSON.
"""

YES_NO_GENERATION_PROMPT_TEMPLATE = """
Based on the following video content, generate yes/no questions.

Video Content:
{transcript}

Generate {num_questions} yes/no questions.
For each question, provide:
1. The question
2. The correct answer (Yes/No)
3. The timestamp in the video where this content is discussed

Format as JSON.
"""

