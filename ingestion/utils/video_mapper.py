"""Video URL mapping utilities."""
import json
import os
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional


def load_chapters_urls(chapters_file: str = None) -> Dict:
    """Load chapters URLs from JSON file.
    
    Args:
        chapters_file: Path to chapters_urls.json. If None, looks in project root.
    
    Returns:
        Dict with chapter information.
    """
    if chapters_file is None:
        # Look for chapters_urls.json in project root (parent of ingestion/)
        project_root = Path(__file__).parent.parent.parent
        chapters_file = project_root / "chapters_urls.json"
    
    with open(chapters_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_video_title(full_title: str) -> str:
    """Extract clean video title by removing prefix before '：' or ':'.
    
    Args:
        full_title: Full video title like "[CS431 - Chương 4] Part 1: Title"
    
    Returns:
        Clean title like "Title"
    """
    if "：" in full_title:
        return full_title.split("：", 1)[1].strip()
    elif ":" in full_title:
        return full_title.split(":", 1)[1].strip()
    return full_title


def find_video_by_transcript_filename(
    transcript_filename: str,
    chapters_data: Dict
) -> Optional[Dict[str, str]]:
    """Find video metadata by matching transcript filename.
    
    Args:
        transcript_filename: Name of transcript JSON file (e.g., "[CS431 - Chương 4] Part 1...json")
        chapters_data: Loaded chapters_urls data.
    
    Returns:
        Dict with 'chapter', 'title', 'url' or None if not found.
        Note: The 'chapter' returned is from the JSON key (ground truth), not from the video title.
    """
    # Skip non-transcript JSON files
    if transcript_filename in ["transcript_metadata.json", "transcription_summary.json"]:
        return None
    
    # Remove .json extension
    base_name = transcript_filename.replace(".json", "")
    normalized_base = normalize_title(base_name)
    
    # Search through all chapters
    # The JSON key is the ground truth chapter, not what's in the video title
    chapters = chapters_data.get("chapters", {})
    
    for chapter_key, videos in chapters.items():
        for video in videos:
            if isinstance(video, dict):
                video_title = video.get("title", "")
                normalized_video = normalize_title(video_title)
                
                # Match by normalized title
                if normalized_video == normalized_base:
                    # Return the chapter from JSON key (ground truth), not from video title
                    return {
                        "chapter": chapter_key,  # This is the ground truth chapter
                        "title": video_title,
                        "url": video.get("url", "")
                    }
    
    return None


def normalize_title(title: str) -> str:
    """Normalize title for comparison by replacing separators and removing extra spaces.
    
    Args:
        title: Video title string.
    
    Returns:
        Normalized title.
    """
    # CRITICAL: Normalize Unicode to NFC form first (macOS uses NFD for filenames)
    normalized = unicodedata.normalize('NFC', title)
    # Replace both full-width colon, regular colon, and hyphen with space
    # This handles: "Part 1： Title", "Part 1: Title", "Part 1-Title"
    normalized = normalized.replace("：", " ").replace(":", " ").replace("-", " ")
    # Replace underscores with spaces for comparison
    normalized = normalized.replace("_", " ")
    # Remove extra spaces
    normalized = " ".join(normalized.split())
    # Convert to lowercase for case-insensitive comparison
    normalized = normalized.lower()
    return normalized


def get_all_video_mappings(
    transcripts_dir: str,
    chapters_file: str = None
) -> List[Dict[str, str]]:
    """Get video mappings for all transcript files.
    
    Args:
        transcripts_dir: Path to directory containing transcript JSON files.
        chapters_file: Path to chapters_urls.json.
    
    Returns:
        List of dicts with 'transcript_path', 'chapter', 'title', 'url'.
    """
    chapters_data = load_chapters_urls(chapters_file)
    
    mappings = []
    transcripts_path = Path(transcripts_dir)
    
    for transcript_file in transcripts_path.glob("*.json"):
        video_metadata = find_video_by_transcript_filename(
            transcript_file.name,
            chapters_data
        )
        
        if video_metadata:
            mappings.append({
                "transcript_path": str(transcript_file),
                "chapter": video_metadata["chapter"],
                "title": video_metadata["title"],
                "url": video_metadata["url"]
            })
        else:
            print(f"Warning: No video mapping found for transcript: {transcript_file.name}")
    
    return mappings

