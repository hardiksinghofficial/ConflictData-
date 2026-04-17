import os
import logging
import asyncio
from typing import List, Optional, AsyncGenerator
from groq import AsyncGroq, RateLimitError

log = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Keys can be passed as a comma-separated string in the GROQ_API_KEYS env var
        keys_str = os.getenv("GROQ_API_KEYS", "")
        self.keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self.current_key_index = 0
        self.clients: List[AsyncGroq] = [AsyncGroq(api_key=k) for k in self.keys]
        
    def get_next_client(self) -> Optional[AsyncGroq]:
        if not self.clients:
            log.warning("No Groq API keys configured. AI features will be limited.")
            return None
        
        client = self.clients[self.current_key_index]
        # Rotate index for next call (Round Robin)
        self.current_key_index = (self.current_key_index + 1) % len(self.clients)
        return client

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Streams a situation report with automatic failover to next key on RateLimit.
        """
        max_attempts = len(self.clients) if self.clients else 0
        attempts = 0
        
        while attempts < max_attempts:
            client = self.clients[self.current_key_index]
            try:
                stream = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a Senior Military Intelligence Analyst for ConflictIQ. Provide professional, objective, and tactical situation reports based on the data provided."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                return # Success, exit
                
            except RateLimitError as e:
                log.error(f"Rate limit hit on key {self.current_key_index}. Rotating...")
                self.current_key_index = (self.current_key_index + 1) % len(self.clients)
                attempts += 1
                if attempts >= max_attempts:
                    yield "\n\n[System: High traffic detected. All intelligence channels are currently at capacity. Please try again in 60 seconds.]"
                    break
            except Exception as e:
                log.error(f"AI Streaming Error: {e}")
                yield f"\n\n[Intelligence Link Failure: {str(e)}]"
                break

ai_service = AIService()
