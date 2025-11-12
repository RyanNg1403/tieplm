"""Vision LLM for video frames."""


class VLMClient:
    """Client for Vision Language Models."""
    
    def __init__(self, api_key: str, model: str = "gpt-4-vision-preview"):
        self.api_key = api_key
        self.model = model
    
    async def analyze_frame(self, image_path: str, prompt: str):
        """Analyze a video frame and generate description."""
        pass

