from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

def utc_now():
    return datetime.now(timezone.utc)

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=utc_now)

class SessionCreateResponse(BaseModel):
    session_id: str
    assistant_name: str
    domain: str
    welcome_message: str

class SessionInfoResponse(BaseModel):
    session_id: str
    message_count: int
    created_at: datetime
    last_active: datetime
    history: List[ChatMessage]

class HealthResponse(BaseModel):
    status: str
    model: str
    ollama_connected: bool
    active_sessions: int
    uptime_seconds: float

# WebSocket Protocol Payloads

class WSIncomingMessage(BaseModel):
    type: str = "user_message"
    session_id: Optional[str] = None
    content: Optional[str] = None

class LatencyMetrics(BaseModel):
    ttft_ms: float = 0.0
    total_duration_ms: float = 0.0
    tokens_generated: int = 0
    tokens_per_sec: float = 0.0

class WSTokenMessage(BaseModel):
    type: Literal["token"] = "token"
    session_id: str
    delta: str

class WSEndTurnMessage(BaseModel):
    type: Literal["end_turn"] = "end_turn"
    session_id: str
    full_response: str
    metrics: LatencyMetrics

class WSErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    session_id: Optional[str] = None
    message: str
    code: str = "INTERNAL_ERROR"

class WSSessionResetMessage(BaseModel):
    type: Literal["session_reset"] = "session_reset"
    session_id: str
    welcome_message: str

class BenchmarkResult(BaseModel):
    model: str
    test_runs: int
    avg_ttft_ms: float
    avg_tokens_per_sec: float
    avg_total_duration_ms: float
    raw_runs: List[Dict[str, Any]]
