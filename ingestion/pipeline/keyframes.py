"""Extract keyframes from videos using FFmpeg."""


class KeyframeExtractor:
    """Extract keyframes from video files."""
    
    def __init__(self, output_dir: str = "./keyframes"):
        self.output_dir = output_dir
    
    async def extract_keyframes(self, video_path: str, interval: int = 60) -> list[str]:
        """Extract keyframes at regular intervals."""
        pass

