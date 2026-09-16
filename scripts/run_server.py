"""
ApexDrive Server Launcher Script.
Performs preflight checks and launches Uvicorn server.
"""

import sys
import os
import asyncio
import uvicorn

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.llm_engine import llm_engine

async def preflight():
    print("=" * 60)
    print(f"  Starting {settings.ASSISTANT_NAME} Server")
    print(f"  Domain: {settings.DOMAIN_NAME}")
    print(f"  Host: http://{settings.HOST}:{settings.PORT}")
    print("=" * 60)

    is_ready, msg = await llm_engine.check_health()
    if is_ready:
        print(f"[OK] {msg}")
    else:
        print(f"[WARNING] {msg}")
        print("  Please ensure 'ollama serve' is active.")
    print("=" * 60)

def main():
    asyncio.run(preflight())
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()
