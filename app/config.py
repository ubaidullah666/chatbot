import os
from pydantic import BaseModel

class Settings(BaseModel):
    # Server configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Ollama Local LLM configuration (CPU execution)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    OLLAMA_TIMEOUT: float = float(os.getenv("OLLAMA_TIMEOUT", "120.0"))

    # LLM Hyperparameters for conversational consistency
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.4"))
    TOP_P: float = float(os.getenv("TOP_P", "0.85"))
    MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "512"))

    # Memory & Context Window Management
    # Max turns to retain in prompt sliding window (each turn = 1 user + 1 assistant)
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "8"))
    MAX_PROMPT_TOKENS: int = int(os.getenv("MAX_PROMPT_TOKENS", "2048"))

    # Business Domain Selection
    DOMAIN_NAME: str = "Car Rental Assistant"
    ASSISTANT_NAME: str = "ApexDrive AI"

settings = Settings()
