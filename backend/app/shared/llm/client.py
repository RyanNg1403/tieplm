"""LLM API wrapper."""


class LLMClient:
    """Client for interacting with LLM APIs."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
    
    async def generate(self, prompt: str, system_prompt: str = None):
        """Generate text using LLM."""
        pass

