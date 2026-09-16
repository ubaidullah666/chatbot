"""
CPU Latency & Throughput Benchmark Script for Assignment 1.
Measures Time-to-First-Token (TTFT), tokens per second (tok/s),
and total response duration for local Q4 quantized model on CPU.
"""

import sys
import os
import time
import asyncio

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.conversation_manager import Session
from app.llm_engine import llm_engine

BENCHMARK_PROMPTS = [
    "What SUV options do you offer and what is the daily rate?",
    "I need a quote for an Electric car for 4 days with Zero Excess insurance.",
    "Can you write a Python script to sort a list?"  # Guardrail prompt
]

async def run_single_inference(prompt: str, run_id: int):
    session = Session(session_id=f"bench-{run_id}")
    session.add_message("user", prompt)
    prompt_msgs = session.get_prompt_messages(max_turns=settings.MAX_HISTORY_TURNS)

    print(f"\n--- Run {run_id}: '{prompt[:45]}...' ---")
    gen = llm_engine.stream_chat(prompt_msgs)

    final_metrics = None
    chunks = []

    async for chunk, metrics in gen:
        if chunk:
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        if metrics:
            final_metrics = metrics

    print()
    if final_metrics:
        print(f"-> TTFT: {final_metrics.ttft_ms:.2f} ms")
        print(f"-> Throughput: {final_metrics.tokens_per_sec:.2f} tokens/sec")
        print(f"-> Total Time: {final_metrics.total_duration_ms / 1000.0:.2f} s ({final_metrics.tokens_generated} tokens)")
    return final_metrics

async def main():
    print("=" * 65)
    print("  ApexDrive AI - Local CPU Inference Benchmark")
    print(f"  Model: {settings.OLLAMA_MODEL} (Local Quantized Q4 via Ollama)")
    print("=" * 65)

    is_ready, msg = await llm_engine.check_health()
    if not is_ready:
        print(f"ERROR: Ollama is not ready: {msg}")
        return

    metrics_list = []
    run_idx = 1

    for p in BENCHMARK_PROMPTS:
        m = await run_single_inference(p, run_idx)
        if m:
            metrics_list.append(m)
        run_idx += 1

    if metrics_list:
        avg_ttft = sum(m.ttft_ms for m in metrics_list) / len(metrics_list)
        avg_tps = sum(m.tokens_per_sec for m in metrics_list) / len(metrics_list)
        avg_duration = sum(m.total_duration_ms for m in metrics_list) / len(metrics_list)

        print("\n" + "=" * 65)
        print("  BENCHMARK SUMMARY (Local Hardware / CPU)")
        print("=" * 65)
        print(f"  Total Runs Evaluated:        {len(metrics_list)}")
        print(f"  Average Time to First Token: {avg_ttft:.2f} ms ({avg_ttft/1000:.2f}s)")
        print(f"  Average Generation Speed:    {avg_tps:.2f} tokens/second")
        print(f"  Average Response Duration:   {avg_duration/1000:.2f} seconds")
        print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())
