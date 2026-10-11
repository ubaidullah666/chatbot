"""
FastAPI Server for ApexDrive Conversational AI.
Exposes REST management endpoints and a real-time streaming WebSocket endpoint (/ws/chat).
"""

import time
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    SessionCreateResponse,
    SessionInfoResponse,
    HealthResponse,
    WSIncomingMessage,
    WSTokenMessage,
    WSEndTurnMessage,
    WSErrorMessage,
    WSSessionResetMessage,
    BenchmarkResult,
    LatencyMetrics
)
from app.domain_config import (
    DOMAIN_METADATA,
    FLEET_CATALOG,
    INSURANCE_TIERS,
    OPTIONAL_ADDONS,
    RENTAL_POLICIES,
    CONVERSATION_STAGES
)
from app.conversation_manager import conversation_manager
from app.llm_engine import llm_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")
SERVER_START_TIME = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.ASSISTANT_NAME} server on {settings.HOST}:{settings.PORT}")
    # Health check to Ollama
    is_ready, msg = await llm_engine.check_health()
    if is_ready:
        logger.info(f"Ollama local LLM status: {msg}")
    else:
        logger.warning(f"Ollama local LLM warning: {msg}")
    # Warm local model/index before accepting traffic; failure leaves chat usable.
    from app.retrieval import retriever
    await retriever.retrieve("rental policies")
    yield
    logger.info("Shutting down ApexDrive server.")

app = FastAPI(
    title=f"{settings.ASSISTANT_NAME} API",
    description="Local CPU-based Conversational AI System for Car Rental Booking",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for local frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================
# REST Endpoints
# ============================================================

@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the ChatGPT-style frontend."""
    return FileResponse("static/index.html")

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """System health check and Ollama connectivity status."""
    is_connected, _ = await llm_engine.check_health()
    active_sessions = len(await conversation_manager.list_sessions())
    uptime = time.time() - SERVER_START_TIME
    return HealthResponse(
        status="healthy" if is_connected else "degraded",
        model=settings.OLLAMA_MODEL,
        ollama_connected=is_connected,
        active_sessions=active_sessions,
        uptime_seconds=round(uptime, 1)
    )

@app.get("/api/domain/info")
async def get_domain_info():
    """Returns domain metadata, fleet catalog, insurance plans, and rental policies."""
    return {
        "metadata": DOMAIN_METADATA,
        "fleet": FLEET_CATALOG,
        "insurance": INSURANCE_TIERS,
        "addons": OPTIONAL_ADDONS,
        "policies": RENTAL_POLICIES,
        "stages": CONVERSATION_STAGES
    }

@app.post("/api/sessions", response_model=SessionCreateResponse)
async def create_session():
    """Creates a new conversational session."""
    session = await conversation_manager.get_or_create_session()
    welcome = conversation_manager.get_welcome_message()
    session.add_message("assistant", welcome)
    return SessionCreateResponse(
        session_id=session.session_id,
        assistant_name=settings.ASSISTANT_NAME,
        domain=settings.DOMAIN_NAME,
        welcome_message=welcome
    )

@app.get("/api/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    """Retrieves full conversation history and state for a session."""
    session = await conversation_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionInfoResponse(
        session_id=session.session_id,
        message_count=len(session.history),
        created_at=session.created_at,
        last_active=session.last_active,
        history=session.history
    )

@app.post("/api/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """Resets conversation history for an existing session."""
    session = await conversation_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.clear()
    welcome = conversation_manager.get_welcome_message()
    session.add_message("assistant", welcome)
    return {"status": "success", "session_id": session_id, "welcome_message": welcome}

@app.post("/api/benchmark", response_model=BenchmarkResult)
async def run_benchmark(runs: int = 3):
    """Runs a programmatic CPU inference benchmark and returns metrics."""
    test_prompt = "I need an SUV for 3 days starting Friday. What are your rates and insurance options?"
    raw_results = []

    for i in range(runs):
        temp_session = await conversation_manager.get_or_create_session()
        temp_session.add_message("user", test_prompt)
        prompt_messages = await conversation_manager.prepare_messages(temp_session)

        gen = llm_engine.stream_chat(prompt_messages)
        final_metrics = None
        full_text = []

        async for chunk, metrics in gen:
            if chunk:
                full_text.append(chunk)
            if metrics:
                final_metrics = metrics

        if final_metrics:
            raw_results.append({
                "run": i + 1,
                "ttft_ms": final_metrics.ttft_ms,
                "total_duration_ms": final_metrics.total_duration_ms,
                "tokens_generated": final_metrics.tokens_generated,
                "tokens_per_sec": final_metrics.tokens_per_sec
            })
        await conversation_manager.delete_session(temp_session.session_id)

    if not raw_results:
        raise HTTPException(status_code=500, detail="Benchmark failed to generate tokens.")

    avg_ttft = sum(r["ttft_ms"] for r in raw_results) / len(raw_results)
    avg_tps = sum(r["tokens_per_sec"] for r in raw_results) / len(raw_results)
    avg_total = sum(r["total_duration_ms"] for r in raw_results) / len(raw_results)

    return BenchmarkResult(
        model=settings.OLLAMA_MODEL,
        test_runs=len(raw_results),
        avg_ttft_ms=round(avg_ttft, 2),
        avg_tokens_per_sec=round(avg_tps, 2),
        avg_total_duration_ms=round(avg_total, 2),
        raw_runs=raw_results
    )

# ============================================================
# WebSocket Endpoint: /ws/chat
# ============================================================

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time, streaming conversational chat.
    Protocol:
      Incoming JSON:
        - {"type": "user_message", "session_id": "...", "content": "..."}
        - {"type": "reset_session", "session_id": "..."}
        - {"type": "ping"}
      Outgoing JSON:
        - {"type": "token", "session_id": "...", "delta": "..."}
        - {"type": "end_turn", "session_id": "...", "full_response": "...", "metrics": {...}}
        - {"type": "session_reset", "session_id": "...", "welcome_message": "..."}
        - {"type": "pong"}
        - {"type": "error", "session_id": "...", "message": "...", "code": "..."}
    """
    await websocket.accept()
    current_session = None

    try:
        while True:
            # Receive raw text message
            raw_data = await websocket.receive_text()

            # Handle JSON parsing robustly
            try:
                msg_dict = json.loads(raw_data)
                req = WSIncomingMessage(**msg_dict)
            except Exception as parse_err:
                await websocket.send_text(
                    WSErrorMessage(
                        message=f"Malformed JSON payload: {str(parse_err)}",
                        code="INVALID_JSON"
                    ).model_dump_json()
                )
                continue

            # Heartbeat ping
            if req.type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # Retrieve or create session
            session = await conversation_manager.get_or_create_session(req.session_id)
            current_session = session

            # Reset session request
            if req.type == "reset_session":
                session.clear()
                welcome = conversation_manager.get_welcome_message()
                session.add_message("assistant", welcome)
                await websocket.send_text(
                    WSSessionResetMessage(
                        session_id=session.session_id,
                        welcome_message=welcome
                    ).model_dump_json()
                )
                continue

            if req.type != "user_message":
                await websocket.send_text(
                    WSErrorMessage(
                        session_id=session.session_id,
                        message=f"Unsupported message type: '{req.type}'",
                        code="UNSUPPORTED_TYPE"
                    ).model_dump_json()
                )
                continue

            # Process user message
            if req.type == "user_message":
                user_content = (req.content or "").strip()
                if not user_content:
                    await websocket.send_text(
                        WSErrorMessage(
                            session_id=session.session_id,
                            message="Empty message content provided.",
                            code="EMPTY_CONTENT"
                        ).model_dump_json()
                    )
                    continue

                # Ensure turn-taking safety with per-session lock
                async with session.lock:
                    session.add_message("user", user_content)
                    prompt_messages = await conversation_manager.prepare_messages(session)

                    accumulated_response = []
                    last_metrics = None

                    try:
                        # Stream response from local LLM engine
                        async for token_delta, metrics in llm_engine.stream_chat(prompt_messages):
                            if token_delta:
                                accumulated_response.append(token_delta)
                                await websocket.send_text(
                                    WSTokenMessage(
                                        session_id=session.session_id,
                                        delta=token_delta
                                    ).model_dump_json()
                                )

                            if metrics:
                                last_metrics = metrics

                        # Conclude the turn
                        full_reply = "".join(accumulated_response)
                        session.add_message("assistant", full_reply)

                        end_msg = WSEndTurnMessage(
                            session_id=session.session_id,
                            full_response=full_reply,
                            metrics=last_metrics or LatencyMetrics()
                        )
                        await websocket.send_text(end_msg.model_dump_json())

                    except Exception as stream_err:
                        logger.exception(f"Streaming error on session {session.session_id}: {stream_err}")
                        await websocket.send_text(
                            WSErrorMessage(
                                session_id=session.session_id,
                                message=f"Inference error: {str(stream_err)}",
                                code="INFERENCE_FAILED"
                            ).model_dump_json()
                        )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected safely (Session: {current_session.session_id if current_session else 'None'})")
    except Exception as e:
        logger.exception(f"Unexpected WebSocket error: {e}")
        try:
            await websocket.send_text(
                WSErrorMessage(
                    session_id=current_session.session_id if current_session else None,
                    message="A server error occurred.",
                    code="SERVER_ERROR"
                ).model_dump_json()
            )
        except Exception:
            pass
