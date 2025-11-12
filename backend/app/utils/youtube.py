"""YouTube video helpers."""


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL."""
    pass


def format_video_url(video_id: str, timestamp_seconds: int = None) -> str:
    """Format YouTube URL with optional timestamp."""
    if timestamp_seconds:
        return f"https://youtube.com/watch?v={video_id}&t={timestamp_seconds}s"
    return f"https://youtube.com/watch?v={video_id}"

