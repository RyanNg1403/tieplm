"""Video summarization task-specific prompts."""

VIDEO_SUMMARY_SYSTEM_PROMPT = """
You are a helpful AI assistant that summarizes video content.
Use both the transcript and visual information to create comprehensive summaries.
"""

VIDEO_SUMMARY_USER_PROMPT_TEMPLATE = """
Summarize the following video content:

Video Title: {title}
Transcript:
{transcript}

Visual Elements:
{keyframe_descriptions}

Summary:
"""

