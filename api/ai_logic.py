import os
import logging
import asyncio
from typing import List, Optional, AsyncGenerator
from groq import AsyncGroq, RateLimitError
import google.generativeai as genai
from huggingface_hub import AsyncInferenceClient

log = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Multiple keys for Groq (legacy support)
        keys_str = os.getenv("GROQ_API_KEYS", os.getenv("GROQ_API_KEY", ""))
        self.groq_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self.current_groq_index = 0
        self.groq_clients: List[AsyncGroq] = [AsyncGroq(api_key=k) for k in self.groq_keys]
        
        # New Engines
        self.hf_token = os.getenv("HF_TOKEN")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Mult-Engine Streaming Situation Report.
        Tries: All Groq Keys -> Gemini -> HF.
        """
        # --- PHASE 1: GROQ ---
        for i in range(len(self.groq_clients)):
            client = self.groq_clients[self.current_groq_index]
            try:
                stream = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a professional conflict intelligence analyst for ConflictIQ. Provide tactical, objective, and strategic sitreps. Output in professional markdown."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True,
                    temperature=0.2
                )
                async for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content: yield content
                return # Success
            except RateLimitError:
                log.warning(f"Groq key {self.current_groq_index} limited. Rotating...")
                self.current_groq_index = (self.current_groq_index + 1) % len(self.groq_clients)
            except Exception as e:
                log.error(f"Groq Streaming Error: {e}")
                break

        # --- PHASE 2: GEMINI ---
        if self.gemini_key:
            log.info("Attempting Gemini Streaming Fallback...")
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                full_prompt = f"SYSTEM: You are a professional conflict intelligence analyst for ConflictIQ. Provide tactical, objective, and strategic sitreps in markdown.\n\nUSER: {prompt}"
                # Gemini's async generate_content with stream
                response = await asyncio.to_thread(model.generate_content, full_prompt, stream=True)
                for chunk in response:
                    if chunk.text: yield chunk.text
                return # Success
            except Exception as e:
                log.error(f"Gemini Streaming Error: {e}")

        # --- PHASE 3: HF INFERENCE ---
        if self.hf_token:
            log.info("Attempting HF Inference Fallback...")
            try:
                client = AsyncInferenceClient(token=self.hf_token)
                stream = client.chat_completion(
                    model="meta-llama/Llama-3.3-70B-Instruct",
                    messages=[
                        {"role": "system", "content": "You are a professional conflict intelligence analyst. Provide tactical, objective, and strategic sitreps in markdown."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=1000,
                    stream=True,
                    temperature=0.2
                )
                async for chunk in await stream:
                    content = chunk.choices[0].delta.content
                    if content: yield content
                return # Success
            except Exception as e:
                log.error(f"HF Streaming Error: {e}")

        # FINAL ERROR
        yield "\n\n[CRITICAL ERROR: ALL INTELLIGENCE ENGINES ARE OFFLINE OR RATE-LIMITED]"

ai_service = AIService()
