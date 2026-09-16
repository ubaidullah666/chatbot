"""
LLM Engine for local quantized inference via Ollama.
Streams token-by-token responses asynchronously over HTTP using httpx.
Measures latency metrics (TTFT, tokens/sec, total time).
"""

import json
import time
import logging
from typing import AsyncGenerator, List, Dict, Any, Tuple, Optional
import httpx

from app.config import settings
from app.models import LatencyMetrics

logger = logging.getLogger("llm_engine")

class LLMEngine:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.temperature = settings.TEMPERATURE
        self.top_p = settings.TOP_P

    async def check_health(self) -> Tuple[bool, str]:
        """Checks if Ollama daemon is reachable and whether the target model is available."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    if any(self.model in m for m in models):
                        return True, f"Model '{self.model}' is ready."
                    return True, f"Ollama reachable, but '{self.model}' not in {models}."
                return False, f"Ollama returned HTTP {res.status_code}"
        except Exception as e:
            return False, f"Cannot connect to Ollama at {self.base_url}: {str(e)}"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[Tuple[str, Optional[LatencyMetrics]], None]:
        """
        Async generator that yields (token_delta, metrics).
        - While streaming: yields (token_chunk, None)
        - At completion: yields ("", LatencyMetrics)
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "num_predict": settings.MAX_OUTPUT_TOKENS
            }
        }

        start_time = time.perf_counter()
        first_token_time: Optional[float] = None
        token_count = 0
        full_text = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        logger.error(f"Ollama error {response.status_code}: {err_text.decode('utf-8', errors='ignore')}")
                        yield (f"[Error: LLM Engine returned HTTP {response.status_code}]", None)
                        return

                    async for raw_line in response.aiter_lines():
                        if not raw_line or not raw_line.strip():
                            continue

                        try:
                            data = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue

                        # Extract delta token
                        msg_chunk = data.get("message", {})
                        delta = msg_chunk.get("content", "")

                        if delta:
                            if first_token_time is None:
                                first_token_time = time.perf_counter()
                            token_count += 1
                            full_text.append(delta)
                            yield (delta, None)

                        # Check if generation finished
                        if data.get("done", False):
                            end_time = time.perf_counter()
                            ttft_ms = ((first_token_time - start_time) * 1000.0) if first_token_time else 0.0
                            total_ms = (end_time - start_time) * 1000.0

                            # Use Ollama reported token counts if provided, otherwise counted chunks
                            eval_count = data.get("eval_count", token_count)
                            eval_duration_ns = data.get("eval_duration", 0)

                            if eval_duration_ns > 0:
                                tok_per_sec = eval_count / (eval_duration_ns / 1e9)
                            elif total_ms > 0:
                                tok_per_sec = eval_count / (total_ms / 1000.0)
                            else:
                                tok_per_sec = 0.0

                            metrics = LatencyMetrics(
                                ttft_ms=round(ttft_ms, 2),
                                total_duration_ms=round(total_ms, 2),
                                tokens_generated=eval_count,
                                tokens_per_sec=round(tok_per_sec, 2)
                            )
                            yield ("", metrics)
                            return

        except httpx.ConnectError:
            logger.error("Failed to connect to Ollama.")
            yield ("\n[Error: Unable to connect to local Ollama engine. Please ensure Ollama is running.]", None)
        except httpx.ReadTimeout:
            logger.error("Ollama inference timed out.")
            yield ("\n[Error: Generation timed out on CPU. Please try a shorter message.]", None)
        except Exception as e:
            logger.exception(f"Unexpected error in stream_chat: {e}")
            yield (f"\n[System Error: {str(e)}]", None)

llm_engine = LLMEngine()
